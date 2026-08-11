#!/usr/bin/env python3
"""Suite survey: enumerate, from the AST, the state that CROSSES between regions
of one Python source file executed top to bottom in one process.

WHY. Splitting a large single-file test suite is only safe if the module-level
state one region creates and a later region consumes is KNOWN. A careful human
read of sixteen thousand lines is not evidence. This is the mechanical
enumeration that must precede the split, and it is allowed to answer NO.

WHAT A CROSSING IS. A READ at line L of name N whose REACHING DEFINITION - the
last binding of N at or before L in the linear module body - sits in a DIFFERENT
region. Not "N is bound in region A and read in region B": name REUSE (a block
that rebinds a scratch name before reading it) depends on nothing, and the naive
model counts it as a dependency. The reaching-definition model is the
instrument; the naive model is noise.

THE PARTITION IS NOT PINNED. A crossing is only defined relative to a partition,
so a survey pinned to one can be defeated by choosing a different boundary
later. This tool computes the relation ONCE over the FINEST partition the file
admits (one top-level statement per region) and derives every coarser view by
PROJECTION. Coarsening only merges regions, and merging can only remove boundary
pairs, never create them, so every crossing under any coarser partition is a
crossing under the finest one. No later choice of suite boundary can surface a
crossing this survey did not already see.

THE CARRIER SET IS AN ARGUMENT, NOT A CHECKLIST, AND ITS RESIDUE IS DECLARED
BLIND. A value written by earlier code in one process can be observed by later
code only if it lives somewhere; CARRIERS below partitions those places. DETECTED
entries are found here; BLIND entries are named with a reason, so that silence
does not read as coverage.

CLASSIFICATION FAILS CLOSED. UNDETERMINED is the DEFAULT and every other label
needs positive mechanical proof, because a wrong SHARED_FIXTURE licenses a move
that silently breaks an assertion while a wrong UNDETERMINED costs a manual look.

THE EXIT CODE IS NOT THE VERDICT. Exit 0 means the analysis COMPLETED, whatever
it found; NOT_FEASIBLE is an answer, not a failure. Exit 1 means it REFUSED, with
the reason named. An analyst who cannot return a negative result without breaking
the build is not measuring anything.

THE TOOL NEVER WRITES. It opens nothing for writing, creates nothing, deletes
nothing, spawns no process, and prints to stdout. `--emit-report` PRINTS the
published document; the gate stage that regenerates it does the redirect, so the
analyser still cannot touch the tree it measures.

THE PUBLISHED DOCUMENT IS GENERATED, NOT TRANSCRIBED. proof/WARP-0716/crossing
-state.md is the output of `--emit-report`, and the gate asserts that regenerating
it is a NO-OP, exactly as it does for specs/index.md. A hand-written document
guarded by re-derivation was tried first and it was a trap: every figure was
checked, and every ordinary growth of the suite demanded a hand rewrite.

  python3 scripts/suite_survey.py                       # text report, default target
  python3 scripts/suite_survey.py --json                # machine-readable record set
  python3 scripts/suite_survey.py --partition statement # the finest partition
  python3 scripts/suite_survey.py --emit-report         # the published document
  python3 scripts/suite_survey.py --target PATH
"""
import argparse
import ast
import bisect
import builtins
import hashlib
import io
import json
import re
import sys
import textwrap
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# WARP-0712 CUT THE MONOLITH THIS SURVEY WAS BUILT TO MEASURE, and the target STAYS here
# anyway. Pointing it at a suite file was tried and reverted: this tool's own AC3 test
# drives the real check_generated.sh over a FIXTURE TREE whose target is scripts/selftest.py,
# so moving the default breaks the fixture rather than the product. The consequence is
# recorded as a limit in proof/WARP-0712/manifest.json, and the emitted document now opens with a
# caveat saying so: the published survey measures the dispatcher, and its verdict is uninformative
# about today's suite until the fixture tree moves with the target.
DEFAULT_TARGET = "scripts/selftest.py"

# A region header in the target's own convention. Read from COMMENT tokens, never
# from raw text, so a marker that appears inside a string literal (this tool's own
# fixtures do exactly that) is not mistaken for a region boundary.
MARKER = "# ---"

CLASSES = ("SHARED_FIXTURE", "PER_SUITE_LOCAL", "ORDERING_DEPENDENCY", "UNDETERMINED")
VERDICTS = ("FEASIBLE", "FEASIBLE_WITH_PREPARATION", "NOT_FEASIBLE")
PARTITIONS = ("marker", "statement")
REFUSALS = ("TARGET_MISSING", "TARGET_DOES_NOT_PARSE", "STAR_IMPORT",
            "DYNAMIC_NAMESPACE_WRITE", "UNATTRIBUTABLE_READ")

# The verdict rule's three constants, published rather than buried. They are
# JUDGEMENTS and cannot be otherwise; the report prints them beside the
# distribution and a sensitivity line so a reader who disagrees can see what
# changes.
MIN_COMPONENTS = 2
LARGEST_COMPONENT_MAX_SHARE = 0.50
UNDETERMINED_MAX_SHARE = 0.10

TABLE_HEADER = "CROSSING SYMBOLS (name | class | carrier | bound | read sites)"

# The carrier partition. Not a list of symptoms: a partition of the PLACES a
# value written by earlier module-level code can be, such that later code in the
# same process can observe it. A seventh carrier would have to be a place that is
# none of the module dict, an object reachable from it, the interpreter, the
# process, or the filesystem.
CARRIERS = (
    {"id": "C1", "status": "DETECTED", "title": "module namespace",
     "text": "a name bound by one statement (def, class, import, assignment, unpacking, "
             "with-item, for target, except-as, walrus, del) and read by another"},
    {"id": "C2", "status": "DETECTED", "title": "indirection through callables",
     "text": "a callable defined in one region whose body reads a module global, invoked "
             "from another; the value crosses although no name crosses in the plain text"},
    {"id": "C3", "status": "DETECTED", "title": "value mutation",
     "text": "the binding does not move but the object does: container mutation, subscript "
             "store, augmented assignment, attribute store on a module-level object "
             "(monkeypatching a loaded module is this carrier applied to a module object)"},
    {"id": "C4", "status": "DETECTED", "title": "interpreter globals",
     "text": "state inside the interpreter rather than the module dict: recursion limit, "
             "sys.path, sys.modules, warnings filters, locale, random state"},
    {"id": "C5", "status": "DETECTED", "title": "process globals",
     "text": "os.environ, working directory, umask and other per-process state"},
    {"id": "C6", "status": "DETECTED", "title": "filesystem, literal paths",
     "text": "a LITERAL repository-relative path written by one region and read by another"},
    {"id": "B1", "status": "BLIND", "title": "filesystem paths that are not literals",
     "reason": "a path built by an f-string or by os.path.join over variables is not a "
               "string constant, so the AST cannot resolve it, and a literal naming a "
               "DIRECTORY carries no extension and is not indexed either; two regions "
               "sharing such a path look mutually independent to this survey"},
    {"id": "B2", "status": "BLIND", "title": "conditional-binding shadowing",
     "reason": "when a conditional binding is later SHADOWED by an unconditional one, the "
               "crossing that exists on the path where the conditional did not fire is "
               "hidden and carries no flag; the scan is flow-insensitive"},
    {"id": "B3", "status": "BLIND", "title": "reflective namespace reads",
     "reason": "a read performed through getattr on the module object or through a "
               "globals() lookup resolves at runtime; dynamic namespace WRITES are a hard "
               "refusal, but reflective READS cannot be attributed to a name statically"},
)

# Method names whose call mutates the receiver. A receiver rooted at a module-level
# name therefore makes that name an ORDERING_DEPENDENCY.
#
# DERIVED FROM THE INTERPRETER, NOT HAND-WRITTEN. A typed list of mutators is exactly
# the "only looked for what I already knew" failure this survey exists to avoid: the
# first draft of this constant omitted set.difference_update, and the real target
# calls it on a shared module's EVENT_TYPES. So the set is computed as the methods a
# MUTABLE builtin has and its IMMUTABLE counterpart does not, which is what "mutator"
# means, and it tracks the interpreter version instead of a memory.
_MUTABLE_PAIRS = ((list, tuple), (set, frozenset), (dict, type(type.__dict__)),
                  (bytearray, bytes))
# Present only on the mutable side yet non-mutating. Named, because including them
# would demote a name to ORDERING_DEPENDENCY for reading a copy of itself.
_NON_MUTATORS = frozenset({"copy", "fromkeys"})
MUTATOR_METHODS = (frozenset(
    m for mut, imm in _MUTABLE_PAIRS for m in set(dir(mut)) - set(dir(imm))
    if not m.startswith("_")) - _NON_MUTATORS) | frozenset({"__setitem__"})
# The import protocol. `spec.loader.exec_module(M)` fills M as part of loading it,
# which is a LOAD and not a monkeypatch; any OTHER attribute store onto M is C3.
MODULE_LOAD_CALLS = frozenset({
    "spec_from_file_location", "module_from_spec", "exec_module", "import_module",
})
# Calls whose string-literal arguments, AND whose receiver's string literals, name a
# path being WRITTEN. `Path("a/b.json").write_text(x)` carries the path in the
# RECEIVER, so the flag propagates left into the callee chain as well as into the
# arguments. `replace` is deliberately absent: str.replace is far more common than
# Path.replace, and marking a read as a write can EMPTY a path's read set and so
# SUPPRESS a crossing, which is silence rather than over-report.
WRITE_CALLS = frozenset({
    "write_text", "write_bytes", "mkdir", "makedirs", "touch", "unlink", "rmtree",
    "rename", "symlink_to", "copy", "copy2", "copytree", "tmpfile",
})
INTERPRETER_MUTATORS = frozenset({
    "sys.setrecursionlimit", "sys.setswitchinterval", "sys.settrace", "sys.setprofile",
    "sys.addaudithook", "sys.path.append", "sys.path.insert", "sys.path.remove",
    "sys.path.extend", "sys.modules.pop", "sys.modules.clear", "sys.modules.update",
    "warnings.filterwarnings", "warnings.simplefilter", "warnings.resetwarnings",
    "locale.setlocale", "random.seed", "importlib.invalidate_caches",
})
PROCESS_MUTATORS = frozenset({
    "os.environ.pop", "os.environ.update", "os.environ.clear", "os.environ.setdefault",
    "os.putenv", "os.unsetenv", "os.chdir", "os.umask", "os.close", "os.dup2",
})
# A repository-relative path LITERAL: at least one separator and a final segment
# carrying an extension. The extension requirement is what keeps schema identifiers
# of the shape `name.kind/v1` out of the index; the cost is carrier B1.
PATH_RE = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9_.\-]*(/[A-Za-z0-9_.\-]+)*/[A-Za-z0-9_\-]+\.[A-Za-z0-9_]{1,8}$")
BUILTIN_NAMES = frozenset(dir(builtins)) | {"__file__", "__name__", "__doc__"}
# A binding kind whose value is not a stable object of the enclosing region:
# it is scoped to a construct that has already exited, or produced by iteration.
VOLATILE_KINDS = frozenset({"with", "for", "except", "del"})


def carrier_ids(status):
    """The carrier ids at one status, in declaration order."""
    return tuple(c["id"] for c in CARRIERS if c["status"] == status)


class Refusal(Exception):
    """The analysis could not be supported. Named reason, non-zero exit, no table."""

    def __init__(self, reason, detail=""):
        super().__init__("%s: %s" % (reason, detail) if detail else reason)
        self.reason = reason
        self.detail = detail


def _dotted(node):
    """`a.b.c` for an Attribute/Name chain rooted at a Name, else None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _root_name(node):
    """The Name at the root of an Attribute/Subscript chain, else None."""
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _is_namespace_call(node):
    """globals() or vars() with no argument: the module namespace as an object."""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ("globals", "vars") and not node.args)


def _target_names(node, out):
    """Every Name bound by an assignment target, recursively through tuples."""
    if isinstance(node, ast.Name):
        out.append(node)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for e in node.elts:
            _target_names(e, out)
    elif isinstance(node, ast.Starred):
        _target_names(node.value, out)


class _Facts:
    """What one deferred callable does to the module namespace when it is CALLED."""

    def __init__(self):
        self.free = set()     # (name, line) read from the module namespace
        self.gwrite = set()   # names rebound through a `global` declaration
        self.gmut = set()     # module-level names whose object is mutated
        self.gmutmod = set()  # roots of a depth-1 method call, pruned if imported
        self.calls = set()    # module-level callables invoked from the body

    def absorb(self, other):
        before = self.size()
        for a in ("free", "gwrite", "gmut", "gmutmod", "calls"):
            getattr(self, a).update(getattr(other, a))
        return before != self.size()

    def size(self):
        return tuple(len(getattr(self, a))
                     for a in ("free", "gwrite", "gmut", "gmutmod", "calls"))


class Survey:
    """One analysis of one file. Construct, run(), then read the attributes."""

    def __init__(self, target, partition="marker", assert_callee="expect"):
        if partition not in PARTITIONS:
            raise ValueError("partition must be one of %s" % (PARTITIONS,))
        self.target = Path(target)
        self.partition = partition
        self.callee = assert_callee
        if not self.target.is_file():
            raise Refusal("TARGET_MISSING", str(self.target))
        self.src = self.target.read_text(encoding="utf-8")
        try:
            self.tree = ast.parse(self.src, filename=str(self.target))
        except SyntaxError as e:
            raise Refusal("TARGET_DOES_NOT_PARSE",
                          "%s line %s: %s" % (self.target, e.lineno, e.msg))
        self.body = list(self.tree.body)
        for i, st in enumerate(self.body):
            for n in ast.walk(st):
                n._si = i
        self.markers = self._marker_lines()
        self._mk = [ln for ln, _ in self.markers]
        self._region = [bisect.bisect_right(self._mk, st.lineno) for st in self.body]
        self.bindings = {}        # name -> [dict(si, line, kind, cond, rhs)]
        self.reads = []           # dict(name, line, si, carrier, via_line, call_func)
        self.mutations = {}       # name -> [dict(si, line, how)]
        self.deferred = {}        # name -> dict(node, si, line, facts)
        self.callsites = {}       # name -> [(si, line)]
        self.process_events = []  # dict(carrier, id, si, line, what)
        self.path_uses = {}       # path -> dict(write=[(si,line)], read=[(si,line)])
        self.module_loads = {}    # literal source path -> [line]
        self.assert_sites = {}    # si -> count
        self.unresolved = set()   # deferred callable names read outside call position
        self.module_objects = set()  # names holding a module object loaded from source

    # ---------- regions ----------

    def _marker_lines(self):
        """Region headers, from COMMENT tokens only."""
        out = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(self.src).readline):
                if tok.type == tokenize.COMMENT and tok.string.startswith(MARKER):
                    out.append((tok.start[0], tok.string.rstrip()))
        except (tokenize.TokenError, IndentationError):
            return []
        return out

    def region_of(self, si, partition=None):
        """The region id of top-level statement si under a partition."""
        p = partition or self.partition
        return si if p == "statement" else self._region[si]

    def region_label(self, rid, partition=None):
        p = partition or self.partition
        if p == "statement":
            return "stmt#%d@L%d" % (rid, self.body[rid].lineno)
        if rid == 0:
            return "(preamble)"
        return self.markers[rid - 1][1][:96]

    def region_count(self, partition=None):
        p = partition or self.partition
        return len(self.body) if p == "statement" else len(self.markers) + 1

    # ---------- refusal scan ----------

    def _scan_refusals(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
                raise Refusal("STAR_IMPORT",
                              "line %d: `from %s import *` defeats name resolution"
                              % (node.lineno, node.module or "."))
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del)) \
                    and _is_namespace_call(node.value):
                raise Refusal("DYNAMIC_NAMESPACE_WRITE",
                              "line %d: a subscript store into globals()/vars()" % node.lineno)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                fid = node.func.id
                if fid in ("exec", "eval"):
                    if len(node.args) < 2:
                        raise Refusal("DYNAMIC_NAMESPACE_WRITE",
                                      "line %d: %s() with no explicit namespace runs in the "
                                      "module namespace" % (node.lineno, fid))
                    if _is_namespace_call(node.args[1]):
                        raise Refusal("DYNAMIC_NAMESPACE_WRITE",
                                      "line %d: %s() into globals()/vars()" % (node.lineno, fid))
                if fid == "setattr" and node.args and _is_namespace_call(node.args[0]):
                    raise Refusal("DYNAMIC_NAMESPACE_WRITE",
                                  "line %d: setattr onto the module namespace" % node.lineno)

    # ---------- module-level collection ----------

    def _bind(self, si, name, line, kind, cond, rhs=None):
        self.bindings.setdefault(name, []).append(
            {"si": si, "line": line, "kind": kind, "cond": bool(cond), "rhs": rhs})

    def _mutate(self, si, name, line, how, module_call=False, via=None):
        """Record one mutation of `name`.

        `via` names the CALLABLE the mutation was attributed through, when the
        mutation happens inside a callable's body rather than at the call site.
        It is STRUCTURED rather than left to be read back out of `how`: the
        emitter derives a published sentence from it, and a sentence derived by
        parsing a prose string is a sentence one rewording away from being wrong.
        """
        if name:
            self.mutations.setdefault(name, []).append(
                {"si": si, "line": line, "how": how, "module_call": module_call,
                 "via": via})

    def _import_only(self, name):
        """True when every binding of the name is an import: it is a MODULE object.

        `os.remove(p)` is a call to a function the module holds, not a mutation of
        the module. A depth-1 method call on an imported name is therefore pruned,
        while `M.attr = x` (a monkeypatch) and `M.SOMETHING.clear()` are kept.
        """
        bs = self.bindings.get(name)
        return bool(bs) and all(b["kind"] == "import" for b in bs)

    def _prune_module_calls(self):
        for name in list(self.mutations):
            if not self._import_only(name):
                continue
            kept = [m for m in self.mutations[name] if not m["module_call"]]
            if kept:
                self.mutations[name] = kept
            else:
                del self.mutations[name]

    def _read(self, si, name, line, carrier="C1", via_line=None, call_func=False):
        if name in BUILTIN_NAMES:
            return
        self.reads.append({"name": name, "line": line, "si": si, "carrier": carrier,
                           "via_line": via_line, "call_func": call_func})

    def _path_use(self, si, node, writing):
        if not isinstance(node.value, str) or not PATH_RE.match(node.value):
            return
        rec = self.path_uses.setdefault(node.value, {"write": [], "read": []})
        rec["write" if writing else "read"].append((si, node.lineno))

    def _scan_module(self):
        for si, stmt in enumerate(self.body):
            self._visit(stmt, si, cond=False, shadow=frozenset(), writing=False)

    def _visit(self, node, si, cond, shadow, writing):
        """Walk module-level code. Deferred callables are registered, not entered.

        The `cond` flag is set for any body that may not execute (if, for, while,
        try, except); a binding made under it can never be promoted past
        UNDETERMINED. A `with` body is not conditional, but its `as` target is a
        VOLATILE binding kind, which is a different and stronger refusal.
        """
        def sub(child, c=cond, sh=shadow, w=writing):
            self._visit(child, si, c, sh, w)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._visit_def(node, si, cond, shadow, writing)
        elif isinstance(node, ast.ClassDef):
            self._visit_class(node, si, cond, shadow, writing)
        elif isinstance(node, ast.Lambda):
            # An inline lambda's free reads are attributed CONSERVATIVELY to its own
            # line rather than to unknown call sites: over-reporting, never silence.
            f = self._callable_facts(node, frozenset())
            for nm, ln in sorted(f.free):
                self._read(si, nm, ln, carrier="C2", via_line=node.lineno)
            for nm in sorted(f.gmut | f.gwrite | f.gmutmod):
                self._mutate(si, nm, node.lineno, "through a lambda at line %d" % node.lineno,
                             module_call=nm in f.gmutmod)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            inner = set(shadow)
            for gen in node.generators:
                inner.update(t.id for t in self._names_of(gen.target))
            for child in ast.iter_child_nodes(node):
                sub(child, sh=frozenset(inner))
        elif isinstance(node, ast.Name):
            self._visit_name(node, si, cond, shadow)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                self._bind(si, a.asname or a.name.split(".")[0], node.lineno,
                           "import", cond, node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                self._assign_target(t, si, cond, shadow, node.value)
            sub(node.value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            self._visit_aug(node, si, cond, shadow, writing)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                sub(item.context_expr)
                for t in self._names_of(item.optional_vars):
                    self._bind(si, t.id, t.lineno, "with", cond)
            for child in node.body:
                sub(child)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            sub(node.iter)
            for t in self._names_of(node.target):
                self._bind(si, t.id, t.lineno, "for", cond)
            for child in node.body + node.orelse:
                sub(child, c=True)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                self._bind(si, node.name, node.lineno, "except", True)
            for child in node.body + ([node.type] if node.type is not None else []):
                sub(child, c=True)
        elif isinstance(node, ast.If):
            sub(node.test)
            for child in node.body + node.orelse:
                sub(child, c=True)
        elif isinstance(node, (ast.Try, ast.While)):
            for child in ast.iter_child_nodes(node):
                sub(child, c=True)
        elif isinstance(node, ast.Delete):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self._bind(si, t.id, t.lineno, "del", cond)
                else:
                    self._visit_member_store(t, si, cond, shadow, writing)
        elif isinstance(node, ast.NamedExpr):
            self._bind(si, node.target.id, node.lineno, "walrus", cond, node.value)
            sub(node.value)
        elif isinstance(node, ast.Call):
            self._visit_call(node, si, cond, shadow, writing)
        elif isinstance(node, ast.Constant):
            self._path_use(si, node, writing)
        elif isinstance(node, (ast.Attribute, ast.Subscript)) \
                and isinstance(node.ctx, ast.Store):
            self._visit_member_store(node, si, cond, shadow, writing)
        else:
            for child in ast.iter_child_nodes(node):
                sub(child)

    @staticmethod
    def _names_of(target):
        out = []
        if target is not None:
            _target_names(target, out)
        return out

    def _visit_name(self, node, si, cond, shadow):
        if node.id in shadow:
            return
        if isinstance(node.ctx, ast.Store):
            self._bind(si, node.id, node.lineno, "assign", cond)
        elif isinstance(node.ctx, ast.Del):
            self._bind(si, node.id, node.lineno, "del", cond)
        else:
            self._read(si, node.id, node.lineno)

    def _assign_target(self, t, si, cond, shadow, value):
        if isinstance(t, ast.Name):
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) \
                    and value.func.attr in MODULE_LOAD_CALLS:
                self.module_objects.add(t.id)
            self._bind(si, t.id, t.lineno, "assign", cond, value)
            if isinstance(value, ast.Lambda):
                self.deferred[t.id] = {"node": value, "si": si, "line": value.lineno}
        elif isinstance(t, (ast.Tuple, ast.List, ast.Starred)):
            for n in self._names_of(t):
                self._bind(si, n.id, n.lineno, "unpack", cond)
        else:
            self._visit_member_store(t, si, cond, shadow, False)

    def _visit_member_store(self, t, si, cond, shadow, writing):
        root = _root_name(t)
        kind = "attribute store" if isinstance(t, ast.Attribute) else "subscript store"
        dotted = _dotted(t.value) if isinstance(t, ast.Subscript) else None
        if dotted == "os.environ":
            self.process_events.append({"carrier": "C5", "si": si, "line": t.lineno,
                                        "what": "os.environ subscript store"})
        elif dotted == "sys.modules":
            self.process_events.append({"carrier": "C4", "si": si, "line": t.lineno,
                                        "what": "sys.modules subscript store"})
        else:
            self._mutate(si, root, t.lineno, kind)
        self._visit(t.value, si, cond, shadow, writing)
        if isinstance(t, ast.Subscript):
            self._visit(t.slice, si, cond, shadow, writing)

    def _visit_aug(self, node, si, cond, shadow, writing):
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value is not None:
                self._bind(si, node.target.id, node.lineno, "assign", cond, node.value)
            if node.value is not None:
                self._visit(node.value, si, cond, shadow, writing)
            return
        if isinstance(node.target, ast.Name):
            self._read(si, node.target.id, node.lineno)
            self._bind(si, node.target.id, node.lineno, "augassign", cond)
            self._mutate(si, node.target.id, node.lineno, "augmented assignment")
        else:
            self._mutate(si, _root_name(node.target), node.lineno, "augmented member assignment")
            self._visit(node.target, si, cond, shadow, writing)
        self._visit(node.value, si, cond, shadow, writing)

    def _visit_call(self, node, si, cond, shadow, writing):
        dotted = _dotted(node.func)
        attr = node.func.attr if isinstance(node.func, ast.Attribute) else None
        w = writing or (attr in WRITE_CALLS) or (
            isinstance(node.func, ast.Name) and node.func.id in WRITE_CALLS) or (
            isinstance(node.func, ast.Name) and node.func.id == "open"
            and any(isinstance(a, ast.Constant) and isinstance(a.value, str)
                    and set("wax") & set(a.value) for a in node.args[1:]))
        if dotted in INTERPRETER_MUTATORS:
            self.process_events.append({"carrier": "C4", "si": si, "line": node.lineno,
                                        "what": dotted + "()"})
        elif dotted in PROCESS_MUTATORS:
            self.process_events.append({"carrier": "C5", "si": si, "line": node.lineno,
                                        "what": dotted + "()"})
        elif isinstance(node.func, ast.Attribute) and node.func.attr in MUTATOR_METHODS:
            self._mutate(si, _root_name(node.func.value), node.lineno,
                         "%s() on a module-level object" % node.func.attr,
                         module_call=isinstance(node.func.value, ast.Name))
        if isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid == self.callee:
                self.assert_sites[si] = self.assert_sites.get(si, 0) + 1
            if fid == "setattr" and node.args:
                self._mutate(si, _root_name(node.args[0]), node.lineno, "setattr()")
            if fid in ("exec", "eval") and len(node.args) > 1:
                self._mutate(si, _root_name(node.args[1]), node.lineno,
                             "%s() into an explicit namespace" % fid)
            if fid in self.deferred:
                self.callsites.setdefault(fid, []).append((si, node.lineno))
            self._read(si, fid, node.func.lineno, call_func=True)
        else:
            self._visit(node.func, si, cond, shadow, w)
        if dotted and dotted.endswith("spec_from_file_location") and node.args \
                and isinstance(node.args[0], ast.Constant):
            # The module NAME. Loads through a spec are NOT cached in sys.modules, so
            # two regions loading one name get two distinct module objects: good news
            # the report should state rather than assume.
            self.module_loads.setdefault(node.args[0].value, []).append(node.lineno)
        if isinstance(node.func, ast.Attribute) and node.func.attr in MODULE_LOAD_CALLS:
            for a in node.args:
                if isinstance(a, ast.Name):
                    self.module_objects.add(a.id)
        for child in node.args + [k.value for k in node.keywords]:
            self._visit(child, si, cond, shadow, w)

    def _visit_def(self, node, si, cond, shadow, writing):
        self._bind(si, node.name, node.lineno, "def", cond, node)
        self.deferred[node.name] = {"node": node, "si": si, "line": node.lineno}
        for d in node.decorator_list:
            self._visit(d, si, cond, shadow, writing)
        for d in list(node.args.defaults) + [x for x in node.args.kw_defaults if x]:
            self._visit(d, si, cond, shadow, writing)

    def _visit_class(self, node, si, cond, shadow, writing):
        self._bind(si, node.name, node.lineno, "class", cond, node)
        # A class body executes NOW, so its free reads are immediate. Its methods are
        # deferred and attached to the class name: any module-level read of the class
        # name is treated as a potential entry into them. Conservative on purpose.
        self.deferred[node.name] = {"node": node, "si": si, "line": node.lineno}
        for d in node.decorator_list + list(node.bases) + [k.value for k in node.keywords]:
            self._visit(d, si, cond, shadow, writing)

    # ---------- deferred callable analysis ----------

    def _own_bound(self, node):
        """Names bound in one callable's own frame (nested bodies excluded)."""
        loc, declared_global = set(), set()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            loc.update(x.arg for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs))
            loc.update(x.arg for x in (a.vararg, a.kwarg) if x)
        own, nested = self._frame(node)
        # A nested def or class binds ITS OWN NAME in this frame, so it is a local
        # here even though its body is a separate frame.
        loc.update(n.name for n in nested if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
        for child in own:
            if isinstance(child, (ast.Global, ast.Nonlocal)):
                declared_global.update(child.names)
            elif isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
                loc.add(child.id)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                loc.add(child.name)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                for al in child.names:
                    loc.add(al.asname or al.name.split(".")[0])
            elif isinstance(child, ast.ExceptHandler) and child.name:
                loc.add(child.name)
        return loc - declared_global, declared_global

    @staticmethod
    def _frame(node):
        """(own nodes, nested callables) for one callable frame.

        The split is the scope boundary: `own` is everything that executes in THIS
        frame, `nested` is every callable defined inside it whose body executes in a
        frame of its own and is analysed separately with this frame's locals in scope.
        """
        own, nested = [], []
        stack = list(node.body if isinstance(node.body, list) else [node.body])
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                              ast.Lambda)):
                nested.append(n)
                continue
            own.append(n)
            stack.extend(ast.iter_child_nodes(n))
        return own, nested

    def _callable_facts(self, node, outer):
        """What this callable does to the module namespace, closures included."""
        loc, declared = self._own_bound(node)
        chain = frozenset(outer) | loc
        f = _Facts()
        own, nested = self._frame(node)
        for n in own:
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) \
                    and n.id not in chain and n.id not in BUILTIN_NAMES:
                f.free.add((n.id, n.lineno))
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id in declared:
                f.gwrite.add(n.id)
            elif isinstance(n, (ast.Attribute, ast.Subscript)) and isinstance(n.ctx, ast.Store):
                r = _root_name(n)
                if r and r not in chain:
                    f.gmut.add(r)
            elif isinstance(n, ast.AugAssign):
                r = _root_name(n.target) if not isinstance(n.target, ast.Name) else n.target.id
                if r and (r not in chain or r in declared):
                    f.gmut.add(r)
            elif isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute) and n.func.attr in MUTATOR_METHODS:
                    r = _root_name(n.func.value)
                    if r and r not in chain:
                        (f.gmutmod if isinstance(n.func.value, ast.Name) else f.gmut).add(r)
                if isinstance(n.func, ast.Name) and n.func.id not in chain:
                    f.calls.add(n.func.id)
        for sub in nested:
            f.absorb(self._callable_facts(sub, chain))
        return f

    def _resolve_deferred(self):
        """Per-callable facts, closed transitively over module-level calls."""
        facts = {}
        for name, info in self.deferred.items():
            facts[name] = self._callable_facts(info["node"], frozenset())
        changed = True
        while changed:
            changed = False
            for name, f in facts.items():
                for g in list(f.calls):
                    if g in facts and g != name and f.absorb(facts[g]):
                        changed = True
                f.calls.discard(name)
        self.facts = facts
        # A deferred callable READ OUTSIDE CALL POSITION escapes: it may be invoked
        # from anywhere, so the CALLABLE is UNDETERMINED. Its free reads are not
        # dropped - they are attributed to the escape site, which is a place from
        # which control can enter it.
        sites = {name: list(s) for name, s in self.callsites.items()}
        for r in self.reads:
            if r["name"] in facts and not r["call_func"]:
                self.unresolved.add(r["name"])
                sites.setdefault(r["name"], []).append((r["si"], r["line"]))
        for name, where in sites.items():
            f = facts.get(name)
            if not f:
                continue
            for si, line in where:
                for nm, ln in f.free:
                    if nm != name:
                        self._read(si, nm, ln, carrier="C2", via_line=line)
                for nm in f.gwrite | f.gmut:
                    self._mutate(si, nm, line, "through %s() at line %d" % (name, line),
                                 via=name)
                for nm in f.gmutmod:
                    self._mutate(si, nm, line, "through %s() at line %d" % (name, line),
                                 module_call=True, via=name)

    # ---------- edges ----------

    def _build_edges(self):
        order = {n: sorted(b["si"] for b in bs) for n, bs in self.bindings.items()}
        by_si = {}
        for n, bs in self.bindings.items():
            for b in bs:
                by_si.setdefault((n, b["si"]), []).append(b)
        self.edges = []
        self.unbound = {}
        for r in self.reads:
            n = r["name"]
            sis = order.get(n)
            if not sis:
                self.unbound.setdefault(n, []).append(r["line"])
                continue
            k = bisect.bisect_right(sis, r["si"]) - 1
            if k < 0:
                self.unbound.setdefault(n, []).append(r["line"])
                continue
            dsi = sis[k]
            b = by_si[(n, dsi)][-1]
            if r["si"] >= len(self.body) or dsi >= len(self.body):
                raise Refusal("UNATTRIBUTABLE_READ",
                              "read of %s at line %d has no owning statement" % (n, r["line"]))
            self.edges.append({"name": n, "def_si": dsi, "def_line": b["line"],
                               "read_si": r["si"], "read_line": r["line"],
                               "carrier": r["carrier"], "via_line": r["via_line"]})

    def crossing_keys(self, partition=None):
        """The crossing set under one partition, PROJECTED from the one edge list."""
        p = partition or self.partition
        out = set()
        for e in self.edges:
            if self.region_of(e["def_si"], p) != self.region_of(e["read_si"], p):
                out.add((e["name"], e["def_line"], e["read_line"], e["via_line"] or -1))
        return out

    def crossing_edges(self, partition=None):
        p = partition or self.partition
        return [e for e in self.edges
                if self.region_of(e["def_si"], p) != self.region_of(e["read_si"], p)]

    # ---------- purity fixpoint ----------

    def _pure_names(self):
        blocked = set(self.mutations) | set(self.unresolved)
        for n, bs in self.bindings.items():
            if any(b["cond"] or b["kind"] in VOLATILE_KINDS for b in bs):
                blocked.add(n)
        pure = set()
        changed = True
        while changed:
            changed = False
            for n, bs in self.bindings.items():
                if n in pure or n in blocked:
                    continue
                if all(self._pure_expr(b["rhs"], b["kind"], pure) for b in bs):
                    pure.add(n)
                    changed = True
        return pure

    def _pure_expr(self, e, kind, pure):
        # An import, a def and a class bind an object the module itself produced,
        # which is pure by construction. Every other binding kind must prove it.
        if kind in ("import", "def", "class"):
            return True
        if kind not in ("assign", "walrus") or e is None:
            return False
        if isinstance(e, ast.Constant):
            return True
        if isinstance(e, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return True
        if isinstance(e, (ast.Tuple, ast.List, ast.Set)):
            return all(self._pure_expr(x, "assign", pure) for x in e.elts)
        if isinstance(e, ast.Dict):
            return all(self._pure_expr(x, "assign", pure) for x in e.keys if x is not None) \
                and all(self._pure_expr(x, "assign", pure) for x in e.values)
        if isinstance(e, ast.JoinedStr):
            return all(self._pure_expr(x, "assign", pure) for x in e.values)
        if isinstance(e, ast.FormattedValue):
            return self._pure_expr(e.value, "assign", pure)
        if isinstance(e, ast.Name):
            return e.id in pure or e.id in BUILTIN_NAMES
        if isinstance(e, ast.Attribute):
            return self._pure_expr(e.value, "assign", pure)
        if isinstance(e, (ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare)):
            return all(self._pure_expr(x, "assign", pure)
                       for x in ast.iter_child_nodes(e) if isinstance(x, ast.expr))
        if isinstance(e, ast.Subscript):
            return self._pure_expr(e.value, "assign", pure) \
                and self._pure_expr(e.slice, "assign", pure)
        if isinstance(e, ast.Call):
            if not self._pure_expr(e.func, "assign", pure):
                return False
            return all(self._pure_expr(a, "assign", pure) for a in e.args) \
                and all(self._pure_expr(k.value, "assign", pure) for k in e.keywords)
        return False

    # ---------- classification ----------

    def _classify(self):
        pure = self._pure_names()
        self.pure = pure
        cross = self.crossing_edges()
        names = {}
        for e in cross:
            names.setdefault(e["name"], []).append(e)
        self.records = []
        for n in sorted(names):
            es = names[n]
            bs = self.bindings.get(n, [])
            muts = self.mutations.get(n, [])
            if not bs:
                cls, why = "UNDETERMINED", "read with no reaching definition (UNBOUND)"
            elif muts:
                cls, why = "ORDERING_DEPENDENCY", muts[0]["how"]
            elif any(b["kind"] in VOLATILE_KINDS for b in bs):
                cls, why = "ORDERING_DEPENDENCY", "bound by a %s target" % bs[0]["kind"]
            elif any(b["cond"] for b in bs):
                cls, why = "UNDETERMINED", "a reaching definition is conditional"
            elif n in self.unresolved:
                cls, why = "UNDETERMINED", "a callable read outside call position: it may be invoked anywhere"
            elif n in pure:
                cls, why = "SHARED_FIXTURE", "every binding unconditional and provably pure"
            else:
                cls, why = "PER_SUITE_LOCAL", "plain data flow inside one residual component"
            carriers = sorted({e["carrier"] for e in es})
            self.records.append({
                "name": n, "class": cls, "reason": why,
                "carrier": carriers[0], "carriers": carriers,
                "module_object": n in self.module_objects,
                "binding_line": bs[0]["line"] if bs else None,
                "binding_lines": sorted({b["line"] for b in bs}),
                "binding_kinds": sorted({b["kind"] for b in bs}),
                "read_lines": sorted({e["read_line"] for e in es}),
                # The CALL SITES through which a C2 read enters: a value crossing by
                # indirection is only auditable if the report names the invocation as
                # well as the read inside the callable's body.
                "via_lines": sorted({e["via_line"] for e in es if e["via_line"]}),
                "read_sites": len(es),
                "mutation_lines": sorted({m["line"] for m in muts})[:12],
                # The callables this name's mutation was attributed THROUGH. The
                # emitter derives its one sentence about the assertion helper's
                # counters from this field, so that sentence cannot disagree with
                # the classification in the tables beside it.
                "mutated_via": sorted({m["via"] for m in muts if m["via"]}),
                "regions": sorted({self.region_of(e["read_si"]) for e in es}
                                  | {self.region_of(e["def_si"]) for e in es}),
            })
        for n in sorted(self.unbound):
            # EVERY key the bound branch emits, including `module_object`. A record
            # shape that varies by branch forces every reader to guess which fields
            # exist, and a reader that guesses with .get() silently reads False for
            # a field the producer simply forgot. The shape is declared here, once.
            self.records.append({
                "name": n, "class": "UNDETERMINED", "reason": "UNBOUND",
                "carrier": "C1", "carriers": ["C1"],
                "module_object": n in self.module_objects, "binding_line": None,
                "binding_lines": [], "binding_kinds": [],
                "read_lines": sorted(set(self.unbound[n])), "via_lines": [],
                "read_sites": len(self.unbound[n]), "mutation_lines": [],
                "mutated_via": [], "regions": [], "status": "UNBOUND"})

    # ---------- components and verdict ----------

    def _components(self, drop_classes=(), drop_names=()):
        cls = {r["name"]: r["class"] for r in self.records}
        nodes = sorted({self.region_of(i) for i in range(len(self.body))})
        parent = {r: r for r in nodes}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for e in self.crossing_edges():
            if cls.get(e["name"]) in drop_classes or e["name"] in drop_names:
                continue
            a, b = find(self.region_of(e["def_si"])), find(self.region_of(e["read_si"]))
            if a != b:
                parent[a] = b
        groups = {}
        for r in nodes:
            groups.setdefault(find(r), []).append(r)
        asserts = {}
        for si, c in self.assert_sites.items():
            rid = self.region_of(si)
            asserts[rid] = asserts.get(rid, 0) + c
        out = []
        for members in groups.values():
            out.append({"regions": sorted(members),
                        "assert_sites": sum(asserts.get(r, 0) for r in members)})
        out.sort(key=lambda c: (-c["assert_sites"], -len(c["regions"]), c["regions"][0]))
        return out

    def _verdict(self, comps, hoist_needed, undet_share):
        total_asserts = sum(c["assert_sites"] for c in comps)
        largest = max((c["assert_sites"] for c in comps), default=0)
        share = (largest / total_asserts) if total_asserts else 0.0
        if len(comps) < MIN_COMPONENTS:
            return "NOT_FEASIBLE", share, (
                "the residual graph has %d component(s), below MIN_COMPONENTS=%d"
                % (len(comps), MIN_COMPONENTS))
        if undet_share > UNDETERMINED_MAX_SHARE:
            return "NOT_FEASIBLE", share, (
                "UNDETERMINED is %.3f of crossing names, over UNDETERMINED_MAX_SHARE=%.2f"
                % (undet_share, UNDETERMINED_MAX_SHARE))
        if share > LARGEST_COMPONENT_MAX_SHARE:
            return "NOT_FEASIBLE", share, (
                "the largest residual component holds %.3f of assertion sites, over "
                "LARGEST_COMPONENT_MAX_SHARE=%.2f, and hoisting is already applied"
                % (share, LARGEST_COMPONENT_MAX_SHARE))
        if not hoist_needed:
            return "FEASIBLE", share, "the graph satisfies all three constants with no hoisting"
        return "FEASIBLE_WITH_PREPARATION", share, (
            "all three constants are satisfied once %d hoistable symbol(s) are lifted"
            % len(hoist_needed))

    def _ranked_blocking(self):
        """Residual crossing names by edge count, SHARED_FIXTURE excluded.

        SHARED_FIXTURE edges are already excluded from the residual graph, so the
        names left are the ones a split would have to REMOVE rather than hoist.
        """
        counts = {}
        for e in self.crossing_edges():
            counts[e["name"]] = counts.get(e["name"], 0) + 1
        cls = {r["name"]: r["class"] for r in self.records}
        ranked = sorted((n for n in counts if cls.get(n) != "SHARED_FIXTURE"),
                        key=lambda n: (-counts[n], n))
        return counts, cls, ranked

    def _preparation(self, undet_share, ranked, limit=40):
        """The preparatory work that WOULD satisfy the constants, NAMED.

        Published whatever the verdict: a NOT_FEASIBLE that one symbol decides is
        a different finding from one that fifty do, and the reader is entitled to
        the difference. Greedy by edge count, so it is an UPPER BOUND on the work
        and not a proven minimum.
        """
        drop = []
        for n in [None] + list(ranked[:limit]):
            if n is not None:
                drop.append(n)
            comps = self._components(drop_classes=("SHARED_FIXTURE",),
                                     drop_names=set(drop))
            _v, share, _r = self._verdict(comps, [], undet_share)
            if share <= LARGEST_COMPONENT_MAX_SHARE and len(comps) >= MIN_COMPONENTS:
                return {"hoist": self.hoistable, "remove": list(drop),
                        "components_after": len(comps),
                        "largest_share_after": round(share, 4), "sufficient": True}
        return {"hoist": self.hoistable, "remove": list(drop),
                "components_after": None, "largest_share_after": None,
                "sufficient": False}

    def _sensitivity(self, undet_share, counts, cls, ranked):
        """What the verdict would be with the top blocking symbols removed."""
        out = []
        for k in (1, 2, 3, 5):
            drop = set(ranked[:k])
            if len(drop) < k:
                break
            comps = self._components(drop_classes=("SHARED_FIXTURE",), drop_names=drop)
            v, share, _ = self._verdict(comps, [], undet_share)
            out.append({"dropped": sorted(drop), "components": len(comps),
                        "largest_share": round(share, 4), "verdict": v})
        self.blocking_rank = [(n, counts[n], cls.get(n, "UNDETERMINED")) for n in ranked[:25]]
        return out

    def _path_crossings(self):
        """The SECONDARY index: a literal path written in one region, read in another.

        Partial by construction, and labelled so: a path built by an f-string or by
        os.path.join over variables is carrier B1 and invisible here.
        """
        out = []
        for p in sorted(self.path_uses):
            u = self.path_uses[p]
            if not u["write"] or not u["read"]:
                continue
            wr = {self.region_of(s) for s, _l in u["write"]}
            rr = {self.region_of(s) for s, _l in u["read"]}
            if rr - wr:
                out.append({"path": p, "carrier": "C6",
                            "written": sorted({l for _s, l in u["write"]}),
                            "read": sorted({l for _s, l in u["read"]}),
                            "write_regions": sorted(wr), "read_regions": sorted(rr)})
        return out

    # ---------- run ----------

    def run(self):
        self._scan_refusals()
        self._scan_module()
        self._resolve_deferred()
        self._prune_module_calls()
        self._build_edges()
        self._classify()
        self.counts = {c: 0 for c in CLASSES}
        for r in self.records:
            # .get rather than a bare increment: a label outside CLASSES must reach the
            # gate's vocabulary assertion as DATA, not kill the run with a KeyError here.
            # The tool reports what it computed; the checker rules on the vocabulary.
            self.counts[r["class"]] = self.counts.get(r["class"], 0) + 1
        self.total = len(self.records)
        undet_share = (self.counts["UNDETERMINED"] / self.total) if self.total else 0.0
        self.undetermined_share = undet_share
        self.hoistable = sorted(r["name"] for r in self.records
                                if r["class"] == "SHARED_FIXTURE")
        self.raw_components = self._components()
        self.components = self._components(drop_classes=("SHARED_FIXTURE",))
        self.verdict, self.largest_share, self.verdict_reason = self._verdict(
            self.components, self.hoistable, undet_share)
        _counts, _cls, _ranked = self._ranked_blocking()
        self.preparation = self._preparation(undet_share, _ranked)
        self.sensitivity = self._sensitivity(undet_share, _counts, _cls, _ranked)
        self.path_crossings = self._path_crossings()
        self.duplicate_loads = sorted(p for p, lines in self.module_loads.items()
                                      if len(lines) > 1)
        for ev in self.process_events:
            ev["region"] = self.region_of(ev["si"])
            ev["affected_regions"] = [r for r in range(self.region_count())
                                      if r > ev["region"]]
        return self

    # ---------- output ----------

    def as_dict(self):
        return {
            "target": str(self.target), "partition": self.partition,
            # The callee whose call sites are counted as assertion sites. Published
            # because the emitter has a sentence to say about it and must NAME it from
            # the measurement rather than from a typed literal.
            "assert_callee": self.callee,
            "regions": self.region_count(), "statements": len(self.body),
            "verdict": self.verdict, "verdict_reason": self.verdict_reason,
            "constants": {"MIN_COMPONENTS": MIN_COMPONENTS,
                          "LARGEST_COMPONENT_MAX_SHARE": LARGEST_COMPONENT_MAX_SHARE,
                          "UNDETERMINED_MAX_SHARE": UNDETERMINED_MAX_SHARE},
            "total_crossing_names": self.total,
            "total_read_sites": sum(r["read_sites"] for r in self.records),
            "counts": self.counts,
            "undetermined_share": round(self.undetermined_share, 4),
            "largest_component_share": round(self.largest_share, 4),
            "components": [{"regions": [self.region_label(r) for r in c["regions"]],
                            "region_ids": c["regions"], "assert_sites": c["assert_sites"]}
                           for c in self.components],
            "raw_components": len(self.raw_components),
            "hoistable": self.hoistable,
            "preparation": self.preparation,
            "blocking": [{"name": n, "edges": k, "class": c} for n, k, c in self.blocking_rank],
            "sensitivity": self.sensitivity,
            "records": self.records,
            "path_crossings": self.path_crossings,
            "process_events": [dict(carrier=ev["carrier"], line=ev["line"],
                                    what=ev["what"], region=ev["region"],
                                    affected_region_count=len(ev["affected_regions"]))
                               for ev in self.process_events],
            "duplicate_module_load_names": self.duplicate_loads,
            "module_object_crossings": [r["name"] for r in self.records
                                        if r["module_object"]],
            "carriers": [dict(c) for c in CARRIERS],
        }

    def render_text(self):
        d = self.as_dict()
        L = ["suite survey: %s" % d["target"],
             "partition: %s (%d regions over %d top-level statements)"
             % (d["partition"], d["regions"], d["statements"]),
             "crossing names: %d over %d read sites"
             % (d["total_crossing_names"], d["total_read_sites"]),
             "per class: " + "  ".join("%s=%d" % (c, d["counts"][c]) for c in CLASSES),
             "undetermined share: %.4f (ceiling %.2f)"
             % (d["undetermined_share"], UNDETERMINED_MAX_SHARE),
             "components: raw=%d residual=%d (MIN_COMPONENTS=%d)"
             % (d["raw_components"], len(d["components"]), MIN_COMPONENTS),
             "largest residual component: %.4f of assertion sites (ceiling %.2f)"
             % (d["largest_component_share"], LARGEST_COMPONENT_MAX_SHARE),
             "path crossings: %d   process events: %d   names loaded more than once: %d"
             % (len(d["path_crossings"]), len(d["process_events"]),
                len(d["duplicate_module_load_names"])),
             "VERDICT: %s - %s" % (d["verdict"], d["verdict_reason"]),
             "PREPARATION that would satisfy the constants (greedy, an UPPER BOUND "
             "on the work, not a proven minimum):",
             "  hoist %d SHARED_FIXTURE symbol(s); remove the ordering dependency on "
             "%s -> %s components, largest %s"
             % (len(d["preparation"]["hoist"]),
                ", ".join(d["preparation"]["remove"]) or "(nothing)",
                d["preparation"]["components_after"],
                d["preparation"]["largest_share_after"]),
             "", "BLOCKING SYMBOLS (residual edges)"]
        L += ["  %-8d %-20s %s" % (b["edges"], b["class"], b["name"])
              for b in d["blocking"][:15]]
        L += ["", "SENSITIVITY (verdict with the top blocking symbols removed)"]
        L += ["  drop %-40s components=%-5d largest=%.3f  %s"
              % (",".join(s["dropped"])[:40], s["components"], s["largest_share"],
                 s["verdict"]) for s in d["sensitivity"]]
        L += ["", "CARRIER COVERAGE"]
        L += ["  %s %-9s %-38s %s" % (c["id"], c["status"], c["title"],
                                      c.get("reason", "")[:52]) for c in CARRIERS]
        L += ["", TABLE_HEADER]
        L += ["  %-34s %-20s %-4s %-7s %d sites %s"
              % (r["name"][:34], r["class"], r["carrier"],
                 r["binding_line"] or "UNBOUND", r["read_sites"], r["read_lines"][:6])
              for r in d["records"]]
        return "\n".join(L)


# ---------------------------------------------------------------------------
# THE REPORT, EMITTED. proof/WARP-0716/crossing-state.md is GENERATED from the
# measurement by render_report(), and the gate's CHECK_generated stage asserts
# that regeneration is a NO-OP - the same contract, in the same stage, as
# specs/index.md and scripts/update_index.py.
#
# WHY, AND IT IS A DEFECT FIX, NOT AN EMBELLISHMENT. The first version of this
# item published a HAND-WRITTEN document and a freshness guard that re-derived
# every figure in it. The guard worked. The document was impossible to satisfy:
# appending assertions to the suite moves the target line count, the statement
# count and the assertion-site totals, so the freshness assertions went red and
# the only remedy was a hand rewrite of about 775 lines. MEASURED TWICE: merging
# WARP-0713, about 800 added lines, took the suite from 3287 passed / 0 failed to
# 3316 passed / 4 FAILED and all four were freshness assertions; appending one
# ordinary two-assertion block reddened three of them. A check with teeth and an
# unbounded manual cost to satisfy is a trap, not a guard.
#
# THE NARRATIVE IS CARRIED, NOT DROPPED. The verdict reasoning, the blind spots
# and the obligations handed forward are the part of the document a reader needs,
# and they live below as prose that is emitted verbatim. Prose line breaks are not
# a measurement and do not rot when the suite grows, so they are stored wrapped.
# Every sentence that states a FIGURE is generated from the measurement instead -
# a branch, never an adjective - so no headline here can outlive its table.
#
# THE ANALYSER STILL NEVER WRITES. render_report() RETURNS a string and main()
# prints it; the gate stage does the redirect. The tool cannot touch the tree it
# measures, which is what the read-only assertion is for.
# ---------------------------------------------------------------------------

REPORT_PATH = "proof/WARP-0716/crossing-state.md"
REPORT_WRAP = 98

# The meaning column of the published constants table. Keyed by the constant's own
# name and REQUIRED to cover all three: retuning a ceiling cannot leave the
# published rule explaining the old one, and adding a fourth constant without its
# meaning makes the emitter REFUSE.
CONSTANT_MEANINGS = {
    "MIN_COMPONENTS": "fewer residual components than this and there is nothing to split",
    "LARGEST_COMPONENT_MAX_SHARE": "of assertion sites; a bigger giant delivers neither "
                                   "parallel lanes nor a fast subset run",
    "UNDETERMINED_MAX_SHARE": "of crossing names; above this the analysis cannot support "
                              "a split decision",
}

# The reader-facing description and the two fixture cases for each carrier, keyed by
# id. REQUIRED to cover CARRIERS exactly: a carrier added to the constant without its
# documentation makes the emitter REFUSE rather than publish an undocumented row, so
# the gate reds instead of the document going quietly incomplete.
CARRIER_DOC = {
    "C1": ("module namespace: a name bound by one statement and read by another",
           "`SHARED_C1` bound in region A, read in region C",
           "`local_c1` bound and read inside region B"),
    "C2": ("indirection: a callable defined in one region whose body reads a global, "
           "invoked from another",
           "`G_C2` read only inside `helper_c2`, called from region C",
           "`arg_c2`, a parameter of a callable crossed by its own name"),
    "C3": ("value mutation: container mutation, subscript store, augmented assignment, "
           "attribute store (a monkeypatch is this carrier applied to a module object)",
           "`ACC` appended to, `SET_C3` narrowed by `difference_update`, `PATCHED.limit` stored",
           "`tmp_c3` bound, mutated and read inside region B"),
    "C4": ("interpreter globals: recursion limit, `sys.path`, `sys.modules`, warnings "
           "filters, locale, random state",
           "`sys.setrecursionlimit(4000)`", "`sys.getrecursionlimit()`, a read"),
    "C5": ("process globals: `os.environ`, cwd, umask",
           "`os.environ[\"S16_FLAG\"] = \"1\"`", "`os.environ.get(\"S16_FLAG\")`, a read"),
    "C6": ("filesystem, LITERAL paths written by one region and read by another",
           "`data/shared_c6.json` written in B, read in C",
           "`data/local_c6.json` written and read in B"),
    "B1": ("filesystem paths that are not literals",
           "none, and none possible from an AST", "none"),
    "B2": ("conditional-binding shadowing", "none", "none"),
    "B3": ("reflective namespace reads", "none", "none"),
}

_P_GENERATED = """\
THIS DOCUMENT IS GENERATED, not transcribed. `python3 scripts/suite_survey.py --emit-report`
emits it whole from one live run of the survey over `%(target)s`, and the gate's
CHECK_generated stage regenerates it and DIFFS: regeneration must be a no-op, exactly as it must
for `specs/index.md`. A stale report cannot reach a green gate: the stage that finds it stale has already
rewritten it and reddened the run with the diff, so the only version that passes is the
emitter's output."""

_P_SUBJECT_MOVED = """\
ONE CAVEAT THAT OUTRANKS EVERY FIGURE BELOW: THE SUBJECT MOVED. WARP-0712 has since cut the
monolith this survey was built to measure into scripts/suites/, leaving at the measured path a
dispatcher that holds no assertion of its own, and the target stays pointed there because this
tool's own fixture tree pins that path (recorded as a limit in proof/WARP-0712/manifest.json). So
the figures and the verdict below describe that dispatcher and, through it, the pre-split monolith
this survey was written for; they are not a statement about today's assertion suite, and the
question of whether that suite can be split has already been answered by splitting it. The
measurement the decomposition actually used is the order-dependence survey in proof/WARP-0712/,
which was driven over the monolith region by region."""

_P_TYPED_PROSE = """\
AND GENERATED DOES NOT MEAN NOTHING WAS TYPED. The tables are derived; the paragraphs between them
are hand-typed constants in the emitter, and one of them USED TO ASSERT A MEASUREMENT: it named the
assertion helper's classification and its counters' classification in prose, an independent review
DROVE one conditional rebinding into the measured file, and this document shipped at a green gate
saying SHARED_FIXTURE in a paragraph while its own tables said UNDETERMINED. Regeneration cannot
see that, and the reason is worth stating exactly: regeneration proves the FILE matches the
EMITTER, and says nothing about whether the EMITTER matches the MEASUREMENT. Two things changed.
That paragraph is now DERIVED from the record set. And before emitting anything, the emitter scans
its OWN source for a typed SENTENCE that carries a backticked name this measurement reports
together with a classification or verdict word, and REFUSES to publish rather than let one be
typed again. What that tooth cannot see is the typed-prose blind spot below, named there rather
than left to silence."""

_P_WHY_GENERATED = """\
THE PREVIOUS VERSION OF THIS DOCUMENT WAS HAND-WRITTEN AND GUARDED, and the guard was the trap. It
re-derived every figure from the suite and compared, which caught staleness exactly as intended,
and which also made the document unsatisfiable: ordinary growth of the suite moves the target line
count, the statement count and the assertion-site totals. Measured twice. Merging an item that
added about 800 lines took the suite from 3287 passed and 0 failed to 3316 passed and 4 FAILED,
all four of them freshness assertions; appending one ordinary two-assertion block reddened three.
Either way the only remedy was a hand rewrite of the whole document. A check with teeth and an
unbounded manual cost to satisfy is not a guard. The teeth are unchanged and the cost is now one
command, because the remedy for a red is to run the emitter and commit its output."""

_P_FROZEN_HISTORY = """\
THE VERSION BEFORE THAT WAS FROZEN INSTEAD, and it published its own failure under Blind spots:
"the cost of the choice is that a stale report stays green". That came true. Commit e9cf123 gave
the one obstructing region a PRIVATE validator instance, which removed the obstruction this survey
had named, and the published verdict stayed NOT_FEASIBLE while the file measured
FEASIBLE_WITH_PREPARATION. Nothing went red, because a prose warning is not a check."""

_P_PROVENANCE = """\
WHY A DIGEST AND NOT A COMMIT. The line above names the exact bytes these figures were read off. A
commit id cannot do that job in a GENERATED file: it would go stale the moment anything else in
the repository was committed, redden this gate on every commit, and rebuild the trap the previous
version was. The digest changes exactly when the measured file changes, which is exactly when the
figures below change, and a reader who wants the tree can find the commit that carries these
bytes."""

_P_EXIT_CODE = """\
A verdict of NOT_FEASIBLE is EXIT 0, and so is this one. The exit code reports whether the
ANALYSIS completed, never what it found. An analyst that cannot return a negative result without
breaking the build is not measuring anything."""

_P_HISTORY_V = """\
THE MEASUREMENT BEFORE e9cf123 SAID NOT_FEASIBLE, and the difference was one commit. Until e9cf123
`V`, the module object for `.veldo/validate.py`, was MUTATED in one of the regions that read it,
which made every region reading it ordering-dependent and welded the giant. Commit e9cf123 gave
that region its own module instance; a private instance bound and
mutated inside a single region does not cross at all and does not appear in this report. The
survey did not change. The file did. What `V` is classified as NOW is a row of the per-symbol
index below, which is emitted, rather than a sentence here, which would be a memory."""

_P_RULE = """\
NOT_FEASIBLE if the residual components are below the minimum or the undetermined share is over
its ceiling or the largest share is over its ceiling with hoisting already applied; FEASIBLE if
all three hold with no preparatory hoisting; FEASIBLE_WITH_PREPARATION otherwise. THE THREE
CONSTANTS ARE JUDGEMENTS, not derivations. They are published here, next to the distribution and
the sensitivity table, precisely so a reader who disagrees with the largest-share ceiling can see
what changes. A reader who reads only the verdict line will not catch that, which is the
thresholds blind spot below."""

_P_PREPARATION_HEAD = """\
Published whatever the verdict. Greedy by edge count, so it is an UPPER BOUND on the work and not
a proven minimum."""

# Item 3 of the named preparation is DERIVED, in _preparation_3() below, and there is
# no constant here to hold it. The paragraph that used to sit at this line typed three
# classification claims - the assertion helper's class and its two counters' class -
# and an independent review inverted all three with ONE conditional rebinding in the
# measured file while regeneration stayed a no-op and the gate stayed green. A
# classification claim is a row of the record set, so it is read off the record set.

_P_TOTALS_HEAD = "Every row here is emitted from the measurement. None of them is typed."

_P_UNDETERMINED_DEFAULT = """\
UNDETERMINED IS THE DEFAULT AND EVERY OTHER LABEL NEEDS POSITIVE MECHANICAL PROOF. SHARED_FIXTURE
requires a purity FIXPOINT: every binding unconditional, every right-hand side an import, a def, a
class, a literal, a literal collection, a module load, or a call whose callee and every argument
are themselves already proven pure, iterated to a least solution. A conditional binding, a
with-item target, any mutation, or a callable read outside call position keeps the name
UNDETERMINED or ORDERING_DEPENDENCY. The costs are not symmetric: a wrong SHARED_FIXTURE licenses
a move that silently breaks an assertion, a wrong UNDETERMINED costs someone a manual look."""

_P_BLOCKING_HEAD = """\
EVERY name the survey classifies ORDERING_DEPENDENCY or UNDETERMINED, which is exactly the set a
split must move together or remove rather than hoist. The table IS the survey's own non-hoistable
record set, emitted whole, so a name entering that class (a new monkeypatch) or leaving it (which
is what e9cf123 did to `V`) changes the document and lands in the diff instead of silently
contradicting a published table. Every row is auditable from the columns alone: open the file at
the binding line and at any read line."""

_P_CARRIERS_NOT_NAMES = "These cross to EVERY later region regardless of any name."

_P_FS_INDEX_HEAD = """\
Literal repository-relative paths written by one region and read by another. Paths built by an
f-string or by `os.path.join` over variables are carrier B1 and INVISIBLE here."""

_P_FS_INDEX_TAIL = """\
WHETHER A GIVEN ROW IS A REAL SHARED-STATE CROSSING or an artifact of a path written into a
temporary clone and read back from the repository IS NOT DECIDED HERE, and no sentence in this
document decides it for every row at once. The previous version of this paragraph did claim that
for every row, which is a universal about a table the suite can grow, and nothing checked it. The
columns are the audit: open the write line and the read line. The index is published as it is
measured."""

_P_BOUNDARY_HEAD = """\
DERIVED FROM THE READ PATTERN, never from the topic names in the region headers. The nodes are
regions, the edges are crossings NOT classified SHARED_FIXTURE, and the boundaries are the
connected components of that graph. A boundary drawn where data actually stops crossing yields
suites that are independent by construction; a boundary drawn around a topic yields suites that
look tidy and share state. Size is measured in `%(callee)s(` sites, not in lines, because
WARP-0712's goal is a developer running one suite in a second and cost tracks assertions."""

_P_BOUNDARY_WHOLE = """\
EVERY residual component, in descending order of assertion sites. This table IS the proposed
boundary set, so it is published whole rather than as a top-N prefix: a truncated table would let
a component merge or divide below the cut without changing a line, and there would be no row count
to pin without pinning a number the suite can grow."""

_P_BOUNDARY_LABEL = """\
The region column is the survey's own region label, normalised the only two ways a markdown cell
forces: a `|` becomes `/` and surrounding whitespace goes."""

_P_BOUNDARY_OBLIGATION = """\
WARP-0712 should re-derive these boundaries after hoisting rather than reading them off this
table: hoisting removes edges, so the component set after preparation is finer than the one here."""

_P_CARRIER_COVERAGE = """\
The completeness claim has two dimensions and they are defended differently. Saying which is which
is the point.

DIMENSION 1, THE BOUNDARY CHOICE: PROVEN. A crossing is only defined relative to a partition, so
the survey computes the relation ONCE at the FINEST partition the file admits, one top-level
statement per region, and derives every coarser view by PROJECTION. Coarsening only merges regions
and merging can only remove boundary pairs, never create them, so every crossing under any coarser
partition is a crossing under the finest one. The selftest asserts that inclusion as a SET RELATION
on the fixture and on the real file. Consequence: no choice of suite boundary WARP-0712 makes can
surface a crossing this survey did not already enumerate.

DIMENSION 2, THE CARRIER SET: ARGUED, with a proven coverage matrix over the declared carriers and
an explicit blind list for the rest. A value written by earlier module-level code can be observed
by later code only if it lives somewhere, and the table below partitions those places. A seventh
carrier would have to be a place a value can be that is none of: this module's namespace, an object
reachable from it, the interpreter, the process, or the filesystem. That enumeration cannot be
PROVEN exhaustive. It is published as a constant with a stated partitioning principle so a reviewer
can NAME the seventh carrier instead of reverse-engineering what was checked.

Each DETECTED carrier has at least one POSITIVE fixture case the tool must report and at least one
NEGATIVE near-miss it must not. A selftest assertion computes, from the survey's own `CARRIERS`
constant and from the case table in the assertion block, that the set of carriers with both kinds
of case EQUALS the set marked DETECTED, that every BLIND carrier has a non-empty reason and no
case, and that the two sets exhaust the constant. Adding a carrier to the code without writing
both cases turns the gate red. Neither side is a literal count. The row below is emitted from that
same constant, and the emitter REFUSES to publish a carrier it has no description for, so an
undocumented carrier cannot reach this table either."""

_P_MUTATOR_METHODS = """\
The tool's `MUTATOR_METHODS` set is DERIVED from the interpreter (the methods a mutable builtin has
and its immutable counterpart does not) rather than typed out. The first draft was typed and
omitted `set.difference_update`, which the target was calling on a validator module's vocabulary at
the time, so the omission cost a real crossing. Whether the target still calls it is a row of the
tables below and not a sentence here: the sentence that used to claim it was a present-tense claim
about the measured file with nothing checking it. The `SET_C3` fixture case exists so a regression
to a hand-written list fails mechanically.

The NEGATIVE CONTROL is a second fixture: a DETANGLED TWIN of the tangled one, same shape with
every crossing removed, over which the survey must report ZERO crossings, ZERO path crossings and
FEASIBLE. Without it, a tool that answered NOT_FEASIBLE to everything would score perfectly on the
tangled fixture and this document's verdict would be an artifact of the analyser rather than a
finding about the file. The twin asserts through `print` rather than a shared `expect`, BECAUSE a
shared assertion helper is itself a crossing. That is not a fixture convenience, it is the finding
restated: even the assertion helper has to be hoisted before any suite can run alone."""

_BLIND_SPOTS = (
    """THE CARRIER ENUMERATION IS AN ARGUMENT AND ITS FAILURE IS TOTALLY SILENT. If a seventh
    carrier exists that nobody named, there is no fixture case for it, the matrix shows every
    declared carrier DETECTED, every assertion is green, this report reads clean, and it is wrong.
    The fail-closed UNDETERMINED default does NOT save this: fail-closed fires on a symbol the tool
    sees and cannot classify, while a carrier nobody looks at produces no symbol at all. Absence of
    a look is indistinguishable from absence of a crossing. This is the largest silent-failure path
    in the item and it is NOT closed.""",
    """COMPUTED FILESYSTEM PATHS ARE INVISIBLE (carrier B1). A region that writes an artifact
    through an f-string path and a later region that reads it look mutually independent, land in
    different components, get split into different suites, and the second then passes alone while
    checking something weaker. Nothing goes red anywhere in that sequence. The literal index above
    is the part that could be measured, not the whole of C6.""",
    """THE FIXTURE PROVES SHAPES, NOT CARRIERS. Within a DETECTED carrier the fixture contains
    particular shapes. A crossing through a class attribute, a default argument evaluated at def
    time, a module-level decorator, or a closure over a loop variable could be missed while every
    fixture case passes green. The matrix asserts one positive and one negative case per carrier; it
    cannot assert that the case is representative.""",
    """THE CONDITIONAL-BINDING MASK (carrier B2). The reaching-definition scan is flow-insensitive
    about whether a conditional binding executed. A conditional reaching definition is marked
    UNDETERMINED, which is visible noise. But when a conditional binding is later SHADOWED by an
    unconditional one, the crossing that existed on the path where the conditional did not fire is
    hidden and carries no flag.""",
    """REGENERATION PROVES THIS DOCUMENT MATCHES THE MEASUREMENT, NOT THAT THE MEASUREMENT IS
    RIGHT. Every figure here comes from the same tool that produced it, so a survey that is WRONG
    about the measured file produces a document that agrees with itself and a green gate.
    Generation closes staleness completely: a stale figure is not merely caught, it cannot reach
    a green gate at all. It cannot close error, and the two are different failures.""",
    """EVERY HARD ASSERTION ABOUT THE TOOL'S BEHAVIOUR IS AGAINST A FIXTURE. The real-file
    assertions that bear on the survey being CORRECT are structural: vocabulary membership,
    provenance of each named binding line, the subset relation between partitions, and the
    assertion block's own prefix containment. None of them can fire on a crossing the survey never
    looked for. That is the definitional blindness of a proxy and it does not go away by being
    mentioned. What partially covers it is the per-symbol index below: any single false entry is
    falsifiable by hand.""",
    """THE THRESHOLDS LAUNDER A JUDGEMENT INTO A VERDICT. A largest component just under the ceiling
    reports FEASIBLE_WITH_PREPARATION and reads as a green light; just over it reports NOT_FEASIBLE.
    The constants are the author's, derived from nothing. The distribution and the sensitivity table
    let a reader catch it; a reader who reads only the verdict line will not.""",
    """THE MARKER CONVENTION IS NOT ENFORCED. A future block that omits its `# --- ` header merges
    into its predecessor's marker region and its crossings disappear from the marker VIEW. The
    per-statement computation still sees them and the marker view is a projection, so the totals do
    not lie, but a reader reading only the region tables sees a tidier file than exists.""",
    """NO DYNAMIC OBSERVATION WAS BUILT. A `sys.settrace` or audit-hook harness would catch computed
    paths and reflective access that an AST cannot. It was rejected here for three reasons: it
    requires executing the full suite; it is the subset runner's job; and it observes only the paths
    one run happens to take, so it is not a superset of the static view. The confirming experiment is
    named as WARP-0712's obligation: run each candidate suite ALONE and in AGGREGATE and compare the
    assertion label sets.""",
    """GENERATION MAKES THE FIGURES UNFALSIFIABLE BY A READER, AND THAT IS A REAL COST. When this
    document was hand-written, a reader who disbelieved a number could compare it to the tool's
    output and find a discrepancy; now the two agree by construction and that particular check is
    gone. What replaces it is stronger for staleness and weaker for nothing else: the emitter is one
    function over the survey's own record set, and the fixture assertions in the suite drive the
    emitter over fixtures whose verdicts DISAGREE with each other so it cannot degenerate into
    printing a constant. No count of fixtures appears in that sentence: the suite can grow one, and
    a number typed here would be the next thing to go stale.""",
    """THE TYPED PROSE IS NOT DERIVED, AND ITS GUARD IS A SHAPE TRIPWIRE RATHER THAN A PROOF. Every
    paragraph in this document is a hand-typed constant in the emitter; only the tables and the
    sentences built from them are derived. One typed paragraph did assert a measurement and shipped
    contradicting the tables beside it at a green gate, which is why the emitter now scans its own
    source and REFUSES a typed SENTENCE that pairs a backticked name this measurement reports with
    a word from the class or verdict vocabulary. THAT IS ALL IT CATCHES. It does not see a claim
    split across two sentences, a class named in lower-case prose rather than in the vocabulary's
    own spelling, a claim about a read count or a region count rather than a class, a claim about a
    name the measurement does not report, or any prose in this document that is simply wrong about
    something the survey never measures. The remedy for those is the same one that found the first
    one: an independent review that drives a mutation and reads the emitted file.""",
)

_P_OBLIGATION = """\
Re-run the survey after restructuring `%(target)s` and let the gate republish this
document; the figures need no human. What is still handed to WARP-0712 by name, because no
generator can do it, is the DYNAMIC confirmation: run each candidate suite ALONE and in AGGREGATE
and compare the assertion label sets. That is the experiment this static survey cannot be."""

_P_SENSITIVITY_HEAD = """\
What the same rule would say with the top blocking symbols removed. Rows after the first assume
the SHARED_FIXTURE hoist is ALREADY applied, which is why they may read FEASIBLE rather than
FEASIBLE_WITH_PREPARATION. Every row is emitted from a re-run of the rule."""

_P_PER_SYMBOL_HEAD = """\
Every crossing symbol the survey reports, so a verdict can be audited without re-running anything:
open `%(target)s` at the binding line, check any read line, and disagree with the class.
Sorted by class then by crossing read sites. The last column carries the first mutation line for a
mutated name, or the first C2 call site for a name that crosses by indirection. This table IS the
survey's record set, emitted whole, so a symbol appearing, vanishing, changing class or moving its
binding line changes the document. It is the section a reader audits by hand, which is why the line
numbers in it are emitted rather than transcribed."""


def _wrap(text, indent=""):
    """One paragraph, wrapped the one way this document wraps."""
    return textwrap.fill(" ".join(text.split()), width=REPORT_WRAP,
                         initial_indent=indent, subsequent_indent=indent,
                         break_long_words=False, break_on_hyphens=False)


def _rel_target(survey):
    """The measured file as the document should name it: repo-relative when it is in
    the repository, and its own path when it is not (a fixture under a temp dir)."""
    try:
        return str(Path(survey.target).resolve().relative_to(ROOT))
    except ValueError:
        return str(survey.target)


def _item(number, text):
    """One numbered list item, hanging-indented under its own marker."""
    marker = "%d. " % number
    return textwrap.fill(" ".join(text.split()), width=REPORT_WRAP,
                         initial_indent=marker, subsequent_indent=" " * len(marker),
                         break_long_words=False, break_on_hyphens=False)


def _n(value):
    """An integer as the document writes integers."""
    return format(value, ",")


def _row(*cells):
    return "| " + " | ".join(cells) + " |"


def _table(headers, rows):
    return [_row(*headers), "|" + "|".join(["---"] * len(headers)) + "|"] + list(rows)


def _lines_plus(values, keep=6):
    """A line list as the document writes one: the first few, then how many more."""
    head = ", ".join(str(v) for v in values[:keep])
    extra = len(values) - keep
    return head + (" +%d more" % extra if extra > 0 else "")


def _class_order(records):
    """Records sorted by class in the vocabulary's order, then by crossing reads."""
    rank = {c: i for i, c in enumerate(CLASSES)}
    return sorted(records, key=lambda r: (rank.get(r["class"], len(CLASSES)),
                                          -r["read_sites"], r["name"]))


def _blocking(records):
    return sorted((r for r in records
                   if r["class"] in ("ORDERING_DEPENDENCY", "UNDETERMINED")),
                  key=lambda r: (-r["read_sites"], r["name"]))


def _tail_cell(rec):
    """The per-symbol index's last column: mutation line, or the C2 entry point."""
    if rec["mutation_lines"]:
        return str(rec["mutation_lines"][0])
    if rec["via_lines"]:
        return "via %d" % rec["via_lines"][0]
    return ""


def _names(names):
    """A prose list of backticked names with the document's `a, b and c` shape."""
    got = ["`%s`" % n for n in names]
    if not got:
        return "(none)"
    if len(got) == 1:
        return got[0]
    return ", ".join(got[:-1]) + " and " + got[-1]


class ReportRefusal(Exception):
    """The emitter will not publish a document it cannot fully describe."""


def _carrier_doc(cid):
    """One carrier's published description and its two fixture cases.

    REFUSES on an unknown id rather than raising KeyError. The pre-flight check in
    render_report() catches this earlier and names every gap at once, but a lookup
    that can only fail one way keeps a future edit to that pre-flight from turning a
    missing description into an uncaught traceback: a crash reports nothing, while a
    refusal names what is missing.
    """
    try:
        return CARRIER_DOC[cid]
    except KeyError:
        raise ReportRefusal(
            "carrier %s has no published description in CARRIER_DOC: a carrier the tool "
            "declares is documented or it is not emitted" % cid)


# The vocabulary a typed sentence is not allowed to attach to a measured name. Both
# halves are the tool's OWN closed vocabularies, so a fifth class or a fourth verdict is
# covered by this guard the moment it is declared, without anything being typed here.
PROSE_VOCABULARY = tuple(CLASSES) + tuple(VERDICTS)

_TICKED = re.compile(r"`([^`]+)`")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
# A backticked INTERPOLATION SLOT: a name will be substituted here at emit time. It
# counts as a name reference, because "`%s` is SHARED_FIXTURE" is the same defect with
# the name derived and the CLASS still typed - which is the harder half to notice.
_SLOT = re.compile(r"(%(\([A-Za-z_][A-Za-z0-9_]*\))?[sdr]|\{[A-Za-z0-9_]*\})\Z")
# A sentence boundary as this document's prose actually punctuates: the terminators, and
# the colon that introduces the claim in "required by honesty: `x` is SHARED_FIXTURE".
_SENTENCE_SPLIT = re.compile(r"(?<=[.;:!?])\s+")


def _sentences(text):
    """One typed string as the sentences a reader reads, whitespace normalised the way
    _wrap() will reflow it, so a claim split over source lines is still one sentence."""
    return [s for s in _SENTENCE_SPLIT.split(" ".join(text.split())) if s]


def prose_claims(source, names, vocabulary=PROSE_VOCABULARY):
    """Every TYPED SENTENCE in `source` that asserts a CLASSIFICATION of a measured name.

    THE DEFECT THIS EXISTS FOR, in one line: regeneration proves the FILE matches the
    EMITTER and says nothing about whether the EMITTER matches the MEASUREMENT. The
    emitter interleaves derived tables with hand-typed paragraphs; one of those
    paragraphs typed the assertion helper's class and its counters' class, one
    conditional rebinding in the measured file inverted all three labels, and the
    regenerated document shipped at a green gate with its prose contradicting its own
    tables. A classification is a row of the record set. Prose may explain what a class
    MEANS; it may not say which class a NAME has.

    So the rule, and it is a SHAPE rule stated exactly: a sentence may not carry a
    backticked bare IDENTIFIER that this measurement reports as a crossing name, or a
    backticked INTERPOLATION SLOT that a name will be substituted into, together with a
    word from `vocabulary`. Returns [(line, label, names, words, sentence)], empty
    iff the source is clean. `names` binds the rule to the MEASUREMENT rather than to a
    list of interesting identifiers: a sentence about a name the survey does not report
    asserts nothing about the measurement, and a sentence about one it does report is a
    claim whether or not anyone meant it as one.

    THE DOMAIN IS DISCOVERED, NEVER LISTED. Every string constant in the source except
    the docstrings is checked, found by walking the AST, so a paragraph typed tomorrow is
    covered on the day it is typed and no registry has to be remembered. Docstrings are
    excluded because they are documentation of the code and are not published; that
    exclusion is the guard's one declared hole in its own domain.

    PURE over a string and a set: the caller supplies the source, which is how the
    refusal path is DRIVEN over a planted-bad emitter without writing to this file.
    Raises ReportRefusal if the source does not parse - a crash reports nothing.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ReportRefusal(
            "the emitter's own source does not parse (%s), so its typed prose cannot be "
            "checked against the measurement and nothing is emitted" % e)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)) and body:
            first = body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                docstrings.add(id(first.value))
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings:
            continue
        for sentence in _sentences(node.value):
            ticked = _TICKED.findall(sentence)
            hit = sorted({t for t in ticked if _IDENT.match(t) and t in names}
                         | {t for t in ticked if _SLOT.match(t)})
            words = sorted({w for w in vocabulary if w in sentence})
            if hit and words:
                out.append((node.lineno, "line %d" % node.lineno, hit, words, sentence))
    return out


def _own_source():
    """This module's own source, for the typed-prose guard. REFUSES rather than crashing
    when it cannot be read: a generator that dies reports nothing, and the gate stage
    redirects this process's stdout, so a traceback is strictly worse than a named red."""
    try:
        return Path(__file__).read_text(encoding="utf-8")
    except OSError as e:
        raise ReportRefusal(
            "the emitter cannot read its own source (%s), so its typed prose cannot be "
            "checked against the measurement and nothing is emitted" % e)


def _preparation_3(d):
    """Item 3 of the named preparation, DERIVED from the record set.

    What this used to be is the whole point: a typed paragraph asserting that the
    assertion helper is SHARED_FIXTURE and that its two counters are ORDERING_DEPENDENCY.
    One conditional rebinding of the helper in the measured file inverted all three and
    the document shipped saying otherwise. Every label below is now read off the records
    the tables are built from, and the callee is named from the survey rather than typed,
    so the sentence and the tables cannot disagree.
    """
    callee = d["assert_callee"]
    by = {r["name"]: r for r in d["records"]}
    rec = by.get(callee)
    counters = sorted((r for r in d["records"] if callee in r["mutated_via"]),
                      key=lambda r: r["name"])
    if rec is None:
        return ("NOT required by the rule but required by honesty: the assertion callee "
                "`%s` is not a crossing name in this measurement at all, so it is not in "
                "the hoist set and there is nothing to carry with it." % callee)
    if not counters:
        return ("NOT required by the rule but required by honesty: the assertion callee "
                "`%s` is classified %s, and this measurement attributes NO name's mutation "
                "to a call of it, so hoisting it carries no counter along. Why the class "
                "is what it is, is the reason column of its row in the per-symbol index."
                % (callee, rec["class"]))
    return ("NOT required by the rule but required by honesty: the assertion callee `%s` "
            "is classified %s, and that is a claim about its BINDING, not about calling it "
            "having no effect. This measurement attributes the mutation of %s to calls of "
            "it, and classifies %s. Hoisting `%s` means hoisting %s with it. Every label in "
            "that sentence is READ OFF the record set the tables below are built from; the "
            "version of it that was typed is what the paragraph at the top of this document "
            "is about."
            % (callee, rec["class"], _names([r["name"] for r in counters]),
               "; ".join("`%s` %s" % (r["name"], r["class"]) for r in counters),
               callee,
               "that counter" if len(counters) == 1 else "those counters"))


def render_report(survey, carriers=CARRIERS, meanings=None, source=None):
    """proof/WARP-0716/crossing-state.md, whole, from one measurement.

    REFUSES rather than emitting a partial document: a carrier or a verdict constant
    with no published description would otherwise reach the file as a blank cell,
    which is the silent incompleteness this whole item exists to refuse.

    AND IT REFUSES A TYPED SENTENCE THAT ASSERTS A MEASUREMENT. The document interleaves
    derived tables with hand-typed paragraphs, so "generated" does not mean "nothing was
    typed": one typed paragraph asserted three classifications, an independent review
    inverted all three with one conditional rebinding in the measured file, and the
    regenerated document shipped at a green gate contradicting its own tables.
    prose_claims() is the tooth, its domain is discovered from this module's AST rather
    than from a list, and its blindness is published as a blind spot.

    `carriers`, `meanings` and `source` are parameters ONLY so the refusal paths can be
    DRIVEN without monkeypatching this module: a test that has to mutate the thing it is
    testing is testing something else.
    """
    meanings = CONSTANT_MEANINGS if meanings is None else meanings
    missing = sorted({c["id"] for c in carriers} ^ set(CARRIER_DOC))
    if missing:
        raise ReportRefusal(
            "CARRIER_DOC and CARRIERS disagree on %s: every carrier the tool declares needs "
            "a published description and its two fixture cases before it can be emitted"
            % ", ".join(missing))
    consts = (("MIN_COMPONENTS", "%d" % MIN_COMPONENTS),
              ("LARGEST_COMPONENT_MAX_SHARE", "%.2f" % LARGEST_COMPONENT_MAX_SHARE),
              ("UNDETERMINED_MAX_SHARE", "%.2f" % UNDETERMINED_MAX_SHARE))
    undocumented = sorted({k for k, _v in consts} - set(meanings))
    if undocumented:
        raise ReportRefusal(
            "CONSTANT_MEANINGS does not describe %s: the rule's judgement constants are "
            "published with their meaning or not at all" % ", ".join(undocumented))
    d = survey.as_dict()
    # THE TYPED-PROSE PRE-FLIGHT, against THIS measurement. Every offending sentence is
    # named at once rather than one per run: a guard that reports the first problem makes
    # a sweep cost as many runs as there are problems.
    claims = prose_claims(_own_source() if source is None else source,
                          {r["name"] for r in d["records"]})
    if claims:
        raise ReportRefusal(
            "a TYPED sentence in the emitter asserts a MEASUREMENT, which regeneration "
            "cannot catch (it proves the file matches the emitter, not that the emitter "
            "matches the measurement): %s. Derive the label from the record set or delete "
            "the sentence."
            % "; ".join("%s names %s with %s in \"%s\""
                        % (label, ", ".join(hit), ", ".join(words), sentence)
                        for _ln, label, hit, words, sentence in claims))
    rel = _rel_target(survey)
    src_lines = len(survey.src.splitlines())
    digest = hashlib.sha256(survey.src.encode("utf-8")).hexdigest()
    asites = sum(c["assert_sites"] for c in d["components"])
    big = d["components"][0]
    recs = d["records"]
    L = ["# WARP-0716 crossing-state survey: can the unit suite be split?", ""]
    L += [_wrap(_P_GENERATED % {"target": rel}), "", _wrap(_P_SUBJECT_MOVED), "",
          _wrap(_P_TYPED_PROSE), "",
          _wrap(_P_WHY_GENERATED), "", _wrap(_P_FROZEN_HISTORY), ""]
    L += ["Measured from: `%s`, %s lines" % (rel, _n(src_lines)),
          "Content digest: sha256 %s" % digest,
          "", _wrap(_P_PROVENANCE), ""]
    L += ["Reproduce: `python3 scripts/suite_survey.py --target %s`" % rel,
          "Machine-readable: the same command with `--json`. Finest partition: "
          "`--partition statement`.",
          "Regenerate: `python3 scripts/suite_survey.py --emit-report`, which is what the gate "
          "runs.", ""]
    # The assertion callee is NAMED FROM THE MEASUREMENT, not typed: `--assert-callee`
    # chooses it, and the detangled twin is surveyed with a different one.
    L += [_wrap("Target: %s lines, %s top-level statements, %d `# --- ` marker regions, %s "
                "`%s(` sites." % (_n(src_lines), _n(d["statements"]), d["regions"],
                                  _n(asites), d["assert_callee"])), ""]
    L += _sec_verdict(d, asites, big, consts, meanings)
    L += _sec_totals(d, src_lines, asites, big, recs)
    L += _sec_blocking(d, recs, rel)
    L += _sec_boundary(d, asites, big)
    L += _sec_carriers(carriers)
    L += _sec_blind_spots(rel)
    L += _sec_sensitivity(d)
    L += _sec_per_symbol(recs, rel)
    return "\n".join(L) + "\n"


def _sec_verdict(d, asites, big, consts, meanings):
    L = ["## Verdict", "", "Verdict: %s" % d["verdict"], ""]
    L += [_wrap("Reason, in the rule's own words: %s." % d["verdict_reason"]), ""]
    L += [_wrap("The residual graph has %d components. Its giant holds %d of %d regions and %s "
                "of %s assertion sites, a share of %.4f against a ceiling of %.2f."
                % (len(d["components"]), len(big["region_ids"]), d["regions"],
                   _n(big["assert_sites"]), _n(asites), d["largest_component_share"],
                   LARGEST_COMPONENT_MAX_SHARE))]
    remove = d["preparation"]["remove"]
    blocking = _blocking(d["records"])
    if remove:
        L += [_wrap("WHAT A SPLIT MUST REMOVE, and it is not nothing: the tool's own greedy "
                    "preparation search reports %s. Until %s removed, hoisting the shared "
                    "fixtures alone does not bring the giant inside the ceiling."
                    % (_names(remove),
                       "that symbol is" if len(remove) == 1 else "those symbols are"))]
    elif blocking:
        L += [_wrap("NO SINGLE SYMBOL DECIDES IT. The tool's own greedy preparation search "
                    "returns an EMPTY removal set and the Totals row for it is 0: once the "
                    "hoistable symbols are lifted the three constants already hold, so this "
                    "report has nothing to tell a reader to remove. The giant is inside the "
                    "ceiling WITHOUT that work rather than over it. The sensitivity table below "
                    "measures what dropping the top blocking symbols would do anyway, because a "
                    "verdict that rests on one symbol is a different finding from one that does "
                    "not.")]
    else:
        L += [_wrap("NOTHING BLOCKS A SPLIT. The survey reports no crossing name classified "
                    "ORDERING_DEPENDENCY or UNDETERMINED at all, so there is neither a removal "
                    "set nor a sensitivity row: the residual graph is already the boundary set.")]
    L += ["", _wrap(_P_HISTORY_V), "", _wrap(_P_EXIT_CODE), ""]
    L += ["### The rule, and the constants it is a rule over", ""]
    L += _table(("constant", "value", "meaning"),
                [_row("`%s`" % k, v, meanings[k]) for k, v in consts])
    L += ["", _wrap(_P_RULE), "", "### The named preparation", "",
          _wrap(_P_PREPARATION_HEAD), ""]
    top = sorted((r for r in d["records"] if r["class"] == "SHARED_FIXTURE"),
                 key=lambda r: (-r["read_sites"], r["name"]))[:3]
    if top:
        L += [_item(1, "HOIST the %d SHARED_FIXTURE symbols into an importable fixture module. "
                       "Every one is unconditionally bound, never mutated, and its right-hand "
                       "side is pure under the fixpoint. The %s that %s most by volume %s %s, and "
                       "their crossing read counts and region counts are rows of the per-symbol "
                       "index below rather than repeated here."
                       % (len(d["hoistable"]), ("one", "two", "three")[len(top) - 1],
                          "matters" if len(top) == 1 else "matter",
                          "is" if len(top) == 1 else "are",
                          _names([r["name"] for r in top])))]
    else:
        L += [_item(1, "HOIST nothing. No crossing name is classified SHARED_FIXTURE, so there "
                       "is no fixture module to extract.")]
    if remove:
        L += [_item(2, "REMOVE the ordering dependency on %s. The greedy search names %s; it is "
                       "an upper bound on the work, not a proven minimum."
                       % (_names(remove), "it" if len(remove) == 1 else "them"))]
    else:
        L += [_item(2, "REMOVE nothing. The greedy search returns an empty removal set, so the "
                       "constants hold on hoisting alone. This step used to name `V` and e9cf123 "
                       "landed it.")]
    L += [_item(3, _preparation_3(d)), ""]
    return L


def _sec_totals(d, src_lines, asites, big, recs):
    figures = (
        ("Target lines", src_lines),
        ("Crossing names", d["total_crossing_names"]),
        ("Crossing read sites", d["total_read_sites"]),
        ("Regions (marker partition)", d["regions"]),
        ("Top-level statements (finest partition)", d["statements"]),
        ("Assertion sites", asites),
        ("Raw components (all crossing edges)", d["raw_components"]),
        ("Residual components (SHARED_FIXTURE edges removed)", len(d["components"])),
        ("Largest residual component, assertion sites", big["assert_sites"]),
        ("Largest residual component, regions", len(big["region_ids"])),
        ("Literal path crossings (carrier C6)", len(d["path_crossings"])),
        ("Interpreter and process events (carriers C4, C5)", len(d["process_events"])),
        ("Module objects crossing regions", len(d["module_object_crossings"])),
        ("Module names loaded more than once", len(d["duplicate_module_load_names"])),
        ("Hoistable symbols (class SHARED_FIXTURE)", len(d["hoistable"])),
        ("Symbols a split must move together or remove", len(_blocking(recs))),
        ("Symbols the greedy preparation search says to remove",
         len(d["preparation"]["remove"])),
    )
    L = ["## Totals", "", _wrap(_P_TOTALS_HEAD), ""]
    L += _table(("measure", "value"), [_row(k, _n(v)) for k, v in figures])
    L += [_row("Largest residual share", "%.4f" % d["largest_component_share"]),
          _row("Undetermined share of crossing names", "%.4f" % d["undetermined_share"]), ""]
    L += ["Total crossing names: %d" % d["total_crossing_names"], ""]
    L += _table(("class", "count"), [_row(c, str(d["counts"][c])) for c in CLASSES])
    L += ["", _wrap(_P_UNDETERMINED_DEFAULT), ""]
    return L


def _sec_blocking(d, recs, rel):
    L = ["## Blocking symbols", "", _wrap(_P_BLOCKING_HEAD), ""]
    rows = []
    for r in _blocking(recs):
        why = (", ".join(str(x) for x in r["mutation_lines"][:3])
               if r["mutation_lines"] else r["reason"])
        rows.append(_row("`%s`" % r["name"], r["class"],
                         str(r["binding_line"]) if r["binding_line"] else "UNBOUND",
                         str(r["read_sites"]), str(len(r["regions"])), why))
    L += _table(("symbol", "class", "bound", "crossing reads", "regions",
                 "mutation lines, or why undetermined"), rows)
    modules = [r["name"] for r in _blocking(recs)
               if r["module_object"] or "import" in r["binding_kinds"]]
    undet = [r["name"] for r in _blocking(recs) if r["class"] == "UNDETERMINED"]
    reasons = sorted({r["reason"] for r in _blocking(recs) if r["class"] == "UNDETERMINED"})
    if not rows:
        L += ["", _wrap("The table is EMPTY, which is the finding: over `%s` the survey classifies "
                        "no crossing name as an ordering dependency or as undetermined, so a "
                        "split has nothing to move together and nothing to remove." % rel), ""]
        return L + _sec_carrier_events(d)
    shapes = []
    if modules:
        shapes.append("THE MONKEYPATCHED SHARED MODULE OBJECT: %s %s a module object (or the "
                      "`sys` module itself) bound once and then PATCHED, which makes every region "
                      "that reads %s ordering-dependent."
                      % (_names(modules), "is" if len(modules) == 1 else "are each",
                         "it" if len(modules) == 1 else "them"))
        shapes.append("THE ACCUMULATOR: a container one region seeds and later regions extend.")
    if undet:
        shapes.append("The %d UNDETERMINED %s a REFUSAL rather than a finding, and the survey "
                      "states why: %s."
                      % (len(undet), "name is" if len(undet) == 1 else "names are",
                         "; ".join('"%s"' % w for w in reasons)))
    lead = "Two shapes account for most of it. " if modules else ""
    L += ["", _wrap(lead + " ".join(shapes)), ""]
    return L + _sec_carrier_events(d)


def _sec_carrier_events(d):
    L = []
    L += ["### The interpreter and process carriers, which are not names", "",
          _wrap(_P_CARRIERS_NOT_NAMES), ""]
    L += _table(("carrier", "line", "what", "later regions affected"),
                [_row(ev["carrier"], str(ev["line"]), ev["what"],
                      str(ev["affected_region_count"])) for ev in d["process_events"]])
    L += ["", "### The filesystem index (carrier C6), a PARTIAL view by construction", "",
          _wrap(_P_FS_INDEX_HEAD), ""]
    L += _table(("path", "written at", "read at", "regions"),
                [_row("`%s`" % p["path"], ", ".join(str(x) for x in p["written"][:3]),
                      ", ".join(str(x) for x in p["read"][:3]),
                      "%d write, %d read" % (len(p["write_regions"]), len(p["read_regions"])))
                 for p in d["path_crossings"]])
    L += ["", _wrap(_P_FS_INDEX_TAIL), "", "### Module loads", ""]
    dupes = d["duplicate_module_load_names"]
    if dupes:
        L += [_wrap(
            "%s %s each loaded more than once through `importlib.util.spec_from_file_location`. "
            "Those loads are NOT cached in `sys.modules`, so each load yields a DISTINCT module "
            "object and the regions doing it are independent of each other. That is good news "
            "the report states rather than assumes, and it is the mechanism e9cf123 used to "
            "remove this survey's one obstruction: a second load of a module costs a line and is "
            "a different object. It does not extend to the %d module objects bound ONCE and read "
            "across regions: those are shared mutable state the moment anything patches them, "
            "which is what the blocking table still demonstrates."
            % (_names(dupes), "is" if len(dupes) == 1 else "are",
               len(d["module_object_crossings"])))]
    else:
        L += [_wrap("No module name is loaded more than once through "
                    "`importlib.util.spec_from_file_location`, so the independence a second "
                    "distinct module object would buy is not in play here.")]
    L += [""]
    return L


def _sec_boundary(d, asites, big):
    bands = (("100 or more", 100, 1 << 40), ("50 to 99", 50, 100), ("10 to 49", 10, 50),
             ("1 to 9", 1, 10), ("0", 0, 1))
    counted = [(nm, sum(1 for c in d["components"] if lo <= c["assert_sites"] < hi))
               for nm, lo, hi in bands]
    L = ["## Proposed suite boundary set", "",
         _wrap(_P_BOUNDARY_HEAD % {"callee": d["assert_callee"]}), "",
         "The distribution, as emitted rows:", ""]
    L += _table(("measure", "value"),
                [_row("Components with %s assertion sites" % nm, str(k)) for nm, k in counted])
    L += ["", _wrap(_P_BOUNDARY_WHOLE), "", _wrap(_P_BOUNDARY_LABEL), ""]
    L += _table(("assertion sites", "regions", "first region in the component"),
                [_row(str(c["assert_sites"]), str(len(c["region_ids"])),
                      c["regions"][0].replace("|", "/").strip()) for c in d["components"]])
    under50 = sum(k for nm, k in counted if nm in ("10 to 49", "1 to 9", "0"))
    under10 = sum(k for nm, k in counted if nm in ("1 to 9", "0"))
    total = len(d["components"])
    tail = ("The tail is what the rows above make of it: %d of the %d residual components hold "
            "fewer than fifty assertions each and %d hold fewer than ten, while the largest holds "
            "%s of %s assertion sites. Under the published constants those numbers give the "
            "verdict %s." % (under50, total, under10, _n(big["assert_sites"]), _n(asites),
                             d["verdict"]))
    if total and under50 * 2 > total:
        tail += (" Most of this suite is therefore ALREADY independent and needs the shared "
                 "fixtures hoisted rather than a rewrite.")
    L += ["", _wrap(tail), ""]
    L += [_wrap(_P_BOUNDARY_OBLIGATION), ""]
    return L


def _sec_carriers(carriers):
    L = ["## Carrier coverage", ""]
    for para in _P_CARRIER_COVERAGE.split("\n\n"):
        L += [_wrap(para), ""]
    L += _table(("id", "status", "carrier", "positive fixture case", "negative fixture case"),
                [_row(c["id"], c["status"], *_carrier_doc(c["id"])) for c in carriers])
    L += [""]
    for para in _P_MUTATOR_METHODS.split("\n\n"):
        L += [_wrap(para), ""]
    return L


def _sec_blind_spots(rel):
    L = ["## Blind spots", "",
         _wrap("Named so that silence does not read as coverage. In descending order of how "
               "badly each could mislead WARP-0712."), ""]
    for i, para in enumerate(_BLIND_SPOTS, 1):
        L += [_item(i, para)]
    L += ["", "### Obligation on WARP-0712", "",
          _wrap(_P_OBLIGATION % {"target": rel}), ""]
    return L


def _sec_sensitivity(d):
    L = ["## Sensitivity", "", _wrap(_P_SENSITIVITY_HEAD), ""]
    rows = [_row("none (as measured)", str(len(d["components"])),
                 "%.4f" % d["largest_component_share"], d["verdict"])]
    rows += [_row(", ".join("`%s`" % n for n in s["dropped"]), str(s["components"]),
                  "%.4f" % s["largest_share"], s["verdict"]) for s in d["sensitivity"]]
    L += _table(("symbols removed", "components", "largest share", "verdict"), rows)
    first = d["sensitivity"][0] if d["sensitivity"] else None
    if first and (first["components"], first["largest_share"]) == (
            len(d["components"]), d["largest_component_share"]):
        moved = ("The verdict does not rest on one symbol: dropping the largest blocking symbol "
                 "changes neither the component count nor the largest share.")
    elif first:
        moved = ("Dropping the largest blocking symbol alone moves the graph to %d components "
                 "and a largest share of %.4f, so the verdict is sensitive to that one name."
                 % (first["components"], first["largest_share"]))
    else:
        moved = "There is no blocking symbol to drop, so the table has no rows after the first."
    L += ["", _wrap(
        "%s Every figure in that claim is an emitted row above or an emitted cell of the "
        "constants table: the residual component count against `MIN_COMPONENTS`, the undetermined "
        "share against `UNDETERMINED_MAX_SHARE`, and the largest residual share against "
        "`LARGEST_COMPONENT_MAX_SHARE`." % moved), ""]
    return L


def _sec_per_symbol(recs, rel):
    L = ["## Per-symbol index", "", _wrap(_P_PER_SYMBOL_HEAD % {"target": rel}), ""]
    L += _table(("symbol", "class", "carrier", "bound", "crossing reads", "read lines",
                 "mutation / via"),
                [_row("`%s`" % r["name"], r["class"], "/".join(r["carriers"]),
                      str(r["binding_line"]) if r["binding_line"] else "UNBOUND",
                      str(r["read_sites"]), _lines_plus(r["read_lines"]), _tail_cell(r))
                 for r in _class_order(recs)])
    return L

def analyse(target=None, partition="marker", assert_callee="expect"):
    return Survey(target or (ROOT / DEFAULT_TARGET), partition, assert_callee).run()


def main(argv=None):
    ap = argparse.ArgumentParser(description="enumerate crossing module-level state")
    ap.add_argument("--target", default=str(ROOT / DEFAULT_TARGET))
    ap.add_argument("--partition", default="marker", choices=list(PARTITIONS))
    ap.add_argument("--assert-callee", default="expect")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit-report", action="store_true",
                    help="print %s, the published document, whole" % REPORT_PATH)
    a = ap.parse_args(argv)
    try:
        s = analyse(a.target, a.partition, a.assert_callee)
        # The emitter REFUSES a document it cannot fully describe, and a refusal is a
        # non-zero exit with the reason named rather than a partial file: the gate stage
        # redirects this stdout, so a half-written document would be worse than a red.
        out = render_report(s) if a.emit_report else None
    except (Refusal, ReportRefusal) as r:
        print("suite survey REFUSED: %s" % r)
        return 1
    if a.emit_report:
        sys.stdout.write(out)
        return 0
    print(json.dumps(s.as_dict(), indent=2, sort_keys=True) if a.json else s.render_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
