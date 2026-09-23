#!/usr/bin/env python3
"""Refuse a suite reference to a module attribute that does not exist (repo-only check).

    python3 scripts/suite_attr_check.py

**THE BUG THIS EXISTS FOR IS A GREEN TEST OF NOTHING.** A conformance fake wrote
`TA_RR.TrackerError(...)` where the adapter's class is `TrackerAdapterError`. The name resolved to
nothing, raised `AttributeError`, the reconcile's broad `except Exception` caught it, the assertion
saw a held request and passed. The scenario was named "the tracker is unreachable" and was testing a
typo. It was written twice, a night apart, because nothing mechanical was looking.

That failure is invisible to the suite itself by construction: the test passes. Only something
reading the source against the real module can see it.

**WHY IT CHECKS ONLY UNIQUELY-BOUND ALIASES, AND WHY THAT IS THE WHOLE DESIGN.** Every suite
fragment execs into ONE shared namespace, so a module alias is a global. But `mod`, `m` and `CLI`
are also rebound in loops and function bodies, and static analysis that ignores scope reports every
one of those as missing. A first cut did exactly that: 40-odd findings, all false, which is a check
somebody switches off within a week - and then the real one ships.

So the rule is: an alias bound EXACTLY ONCE in the scope a reference resolves to is unambiguous, and
only those are checked. Scope is Python's own: a name bound in a function is that function's
variable, a free name is found in the nearest enclosing function and then the module, and every
binding form counts (assignment and unpacking, loop and comprehension targets, with ... as, the
walrus, del, parameters and PEP 695 type parameters, imports, def and class names, except ... as,
match captures, global and nonlocal writes). Which module an alias holds is taken from the source
only where the source decides it: from a spec variable bound once, or one whose every binding is a
spec call or a `del` standing as a plain statement of a fragment's module body (those run in line
order). A spec variable rebound anywhere else (in a function, under an if or a loop, by plain
assignment, through global or nonlocal), or read from another scope while bound more than once,
depends on control flow or call order and maps no alias. The resolver is judged against CPython's
symtable over the real corpus by a suite row, not only against a fixture. Narrowing the SCOPE to
keep the signal clean is right; lowering the BAR by allowlisting the noisy names would not be.

NOT MODELED, stated as limits (the corpus has none of them): a star import, a write through
globals(), locals() or vars(), and exec() without its own namespace rebind names this reader cannot
see; and private-name mangling (`__M` inside a class compiles to `_K__M`) is not applied.

A module that cannot be imported standalone (one that needs helpers injected by its caller) is
UNVERIFIABLE, not passed, and is reported as such.
"""
import ast
import collections
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUITES = ROOT / "scripts/suites"


def _rel_of_spec_call(node):
    """`spec_from_file_location(<name>, ROOT / "rel")` -> `"rel"`, including `ROOT / "a" / "b"`."""
    f = node.func
    if not (isinstance(f, ast.Attribute) and f.attr == "spec_from_file_location"):
        return None
    if len(node.args) < 2:
        return None
    parts, cur = [], node.args[1]
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        if isinstance(cur.right, ast.Constant) and isinstance(cur.right.value, str):
            parts.append(cur.right.value)
        cur = cur.left
    if isinstance(cur, ast.Name) and cur.id == "ROOT" and parts:
        return "/".join(reversed(parts))
    return None


def _spec_var_of_module_call(node):
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr == "module_from_spec" and node.args:
        if isinstance(node.args[0], ast.Name):
            return node.args[0].id
    return None


MODULE = "<module>"   # the ONE namespace every fragment execs into, in manifest order
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_COMPOUND = tuple(getattr(ast, n) for n in ("If", "For", "AsyncFor", "While", "Try", "TryStar",
                                              "With", "AsyncWith", "Match") if hasattr(ast, n))


class _Scope:
    """One Python scope. `key` names it; the module scope of every fragment is the same MODULE."""

    def __init__(self, key, kind, parent, node=None):
        self.key, self.kind, self.parent, self.node = key, kind, parent, node
        self.bound, self.globals, self.nonlocals = set(), set(), set()
        self.depth = 0                                 # compound statements open in this scope

    def local(self, name):
        return name in self.bound and name not in self.globals and name not in self.nonlocals


class _Walk:
    """Collect, per fragment, every scope, every binding and every read, WITH its scope.

    Nothing is resolved while walking: Python decides whether a name is local to a function from
    the WHOLE body (a binding after a read still makes the read local), so resolution runs after
    collection. Every binding form Python has is counted: a stored or deleted Name (assignment,
    augmented and annotated assignment, loop and comprehension targets, with ... as, the walrus),
    parameters, import aliases, def and class names, except ... as, and match captures."""

    def __init__(self, fname, module):
        self.fname, self.bindings, self.events, self.scopes = fname, [], [], []
        self.stack = [module]
        self.top, self.straight = None, []          # the module statement being walked

    def scope(self, node, kind):
        s = _Scope((self.fname, node.lineno, node.col_offset, kind), kind, self.stack[-1], node)
        self.scopes.append(s)
        return s

    def bind(self, name, node, scope=None):
        scope = scope or self.stack[-1]
        if isinstance(node, ast.NamedExpr):
            while scope.kind == "comprehension":      # a walrus binds outside its comprehension
                scope = scope.parent
        scope.bound.add(name)
        self.bindings.append((scope, name))
        if scope.kind == "class" and scope.depth:
            # A class body that binds a name only on a path not taken reads the GLOBAL instead (a
            # function would raise), so a conditional class binding is never the only one.
            self.bindings.append((scope, name))

    def visit(self, node):
        for child in ast.iter_child_nodes(node) if not isinstance(node, list) else node:
            self.one(child)

    def type_params(self, n):
        """PEP 695: `def f[T]` and `class C[T]` bind T in an annotation scope between the enclosing
        scope and the definition, which the body, the signature and nested methods all see."""
        params = getattr(n, "type_params", None) or []
        if not params:
            return False
        scope = self.scope(n, "annotation")
        for p in params:
            self.bind(p.name, p, scope)
        self.stack.append(scope)
        for p in params:
            for part in ("bound", "default_value"):
                if getattr(p, part, None) is not None:
                    self.one(getattr(p, part))
        return True

    def one(self, n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for d in n.decorator_list:
                self.one(d)
            if not isinstance(n, ast.ClassDef):
                self.defaults(n)                       # outside any type-parameter scope
            self.bind(n.name, n)
            pushed = self.type_params(n)
            self.definition(n)
            if pushed:
                self.stack.pop()
        elif isinstance(n, getattr(ast, "TypeAlias", ())):
            self.bind(n.name.id, n)
            pushed = self.type_params(n)
            self.one(n.value)
            if pushed:
                self.stack.pop()
        else:
            self.statement(n)

    def defaults(self, n):
        a = n.args
        for d in a.defaults + [k for k in a.kw_defaults if k is not None]:
            self.one(d)

    def definition(self, n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = n.args
            params = a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]
            for p in params:
                if p.annotation is not None:
                    self.one(p.annotation)
            if getattr(n, "returns", None) is not None:
                self.one(n.returns)
            inner = self.scope(n, "function")
            for p in params:
                self.bind(p.arg, p, inner)
            self.stack.append(inner)
            self.visit(n.body if isinstance(n.body, list) else [n.body])
            self.stack.pop()
        else:
            for d in n.bases + [k.value for k in n.keywords]:
                self.one(d)
            inner = self.scope(n, "class")
            self.stack.append(inner)
            self.visit(n.body)
            self.stack.pop()

    def statement(self, n):
        if isinstance(n, _COMPOUND):
            self.stack[-1].depth += 1
            try:
                self.visit(n)
            finally:
                self.stack[-1].depth -= 1
            return
        if isinstance(n, ast.Lambda):
            self.defaults(n)
            self.definition(n)
        elif isinstance(n, _COMPREHENSIONS):
            first, rest = n.generators[0], n.generators[1:]
            self.one(first.iter)                       # evaluated in the enclosing scope
            inner = self.scope(n, "comprehension")
            self.stack.append(inner)
            self.one(first.target)
            for i in first.ifs:
                self.one(i)
            for g in rest:
                self.one(g.iter); self.one(g.target)
                for i in g.ifs:
                    self.one(i)
            for part in ("elt", "key", "value"):
                if getattr(n, part, None) is not None:
                    self.one(getattr(n, part))
            self.stack.pop()
        elif isinstance(n, ast.NamedExpr):
            self.bind(n.target.id, n)
            self.one(n.value)
        elif isinstance(n, ast.Name):
            if isinstance(n.ctx, (ast.Store, ast.Del)):
                self.bind(n.id, n)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            (self.stack[-1].globals if isinstance(n, ast.Global)
             else self.stack[-1].nonlocals).update(n.names)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name != "*":
                    self.bind(a.asname or a.name.split(".")[0], n)
        elif isinstance(n, ast.ExceptHandler):
            if n.name:
                self.bind(n.name, n)
            self.visit(n)
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)):
            if n.name:
                self.bind(n.name, n)
            self.visit(n)
        elif isinstance(n, ast.MatchMapping):
            if n.rest:
                self.bind(n.rest, n)
            self.visit(n)
        else:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and n.targets \
                    and isinstance(n.targets[0], ast.Name):
                rel = _rel_of_spec_call(n.value)
                if rel:
                    self.events.append((n.lineno, n.col_offset, "spec", self.stack[-1],
                                        n.targets[0].id, rel))
                    if n is self.top and len(n.targets) == 1:
                        self.straight.append((n.targets[0].id, n))
                sv = _spec_var_of_module_call(n.value)
                if sv:
                    self.events.append((n.lineno, n.col_offset, "mod", self.stack[-1],
                                        n.targets[0].id, sv))
            # Reads AND writes: a monkeypatch of a name the module does not have
            # (`M.lauch = spy`) replaces nothing, and the test that relies on it passes having
            # proved nothing, which is exactly the failure this check exists for.
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                    and isinstance(n.value.ctx, ast.Load):
                self.events.append((n.lineno, n.col_offset, "ref", self.stack[-1],
                                    n.value.id, n.attr))
            self.visit(n)


def resolve(scope, name):
    """The key of the scope a name READ in `scope` refers to, by Python's rules: a name bound in a
    function is local to it unless declared global or nonlocal; a free name is found in the nearest
    enclosing function scope (class bodies are skipped, except by the annotation scope directly
    inside one), else in the module namespace."""
    if scope.kind == "module" or name in scope.globals:
        return MODULE
    if scope.local(name):
        return scope.key
    prev, cur = scope, scope.parent
    while cur is not None and cur.kind != "module":
        if cur.kind == "class":
            if name == "__class__":
                return cur.key                         # the implicit cell super() reads
            if prev is scope and scope.kind == "annotation" and cur.local(name):
                return cur.key                         # PEP 695: annotation scopes see their class
        elif cur.local(name):
            return cur.key
        elif name in cur.globals:
            return MODULE
        prev, cur = cur, cur.parent
    return MODULE


def _binding_key(scope, name):
    if scope.kind == "module" or name in scope.globals:
        return MODULE
    if name in scope.nonlocals:
        cur = scope.parent
        while cur is not None and cur.kind != "module":
            if cur.kind != "class" and cur.local(name):
                return cur.key
            cur = cur.parent
        return MODULE
    return scope.key


def walk(trees):
    """fname -> _Walk, every fragment sharing ONE module scope, because that is the runtime."""
    module = _Scope(MODULE, "module", None)
    walks = {}
    for fname, tree in trees.items():
        w = _Walk(fname, module)
        for statement in tree.body:
            w.top = statement
            w.one(statement)
            if isinstance(statement, ast.Delete):          # unbinds in line order; never re-points
                w.straight.extend((t.id, statement) for t in statement.targets
                                  if isinstance(t, ast.Name))
        walks[fname] = w
    return walks


def binding_counts(trees):
    """How many times each (scope, NAME) is bound. An alias bound more than once in the scope a
    reference resolves to is ambiguous without flow analysis and is deliberately not checked; a
    same-named local in another function is a different variable and does not make it ambiguous."""
    counts = collections.Counter()
    for w in walk(trees).values():
        for scope, name in w.bindings:
            counts[(_binding_key(scope, name), name)] += 1
    return counts


def references(order, trees, counts):
    """(file, line, alias, attr, module_rel) for every attribute read on a uniquely-bound alias.

    Spec variables are resolved IN LINE ORDER and carried ACROSS fragments, because that is what the
    runtime does: one namespace, fragments exec'd in manifest order. A temp name like `_icspec`
    genuinely is reused for two different modules in one file, and last-assignment-wins reports the
    wrong module - which was the second false-positive source before this ordered."""
    walks = walk(trees)
    # WHICH MODULE A SPEC VARIABLE HOLDS is decided from the source only when it is bound once, or
    # when every binding it has is a spec call or a `del` standing as a plain statement of a
    # fragment's module body: those run in line order, fragment after fragment. Any other
    # rebinding (in a function, under an if or a loop, by plain assignment, through global or
    # nonlocal) depends on control flow or call order, and such a variable never maps an alias.
    straight = collections.Counter((MODULE, a) for w in walks.values() for a, _n in w.straight)
    def decidable(key):
        return counts[key] == 1 or counts[key] == straight[key]
    spec_paths, mod_paths, out = {}, {}, []
    for fname in order:
        for line, _col, kind, scope, a, b in sorted(walks[fname].events, key=lambda e: e[:2]):
            if kind == "spec":
                key = (resolve(scope, a), a)
                if decidable(key):
                    spec_paths[key] = b
            elif kind == "mod":
                src = (resolve(scope, b), b)
                # Read from another scope (a function reading a module or enclosing variable), a
                # spec variable is read when the code RUNS; bound more than once, which binding it
                # sees is not decided by the source.
                if src[0] != scope.key and counts[src] > 1:
                    continue
                if src in spec_paths:
                    mod_paths[(resolve(scope, a), a)] = spec_paths[src]
            else:
                key = (resolve(scope, a), a)
                if key in mod_paths and counts[key] == 1:
                    out.append((fname, line, a, b, mod_paths[key]))
    return out


def _encloses(outer, inner):
    cur = inner.parent
    while cur is not None:
        if cur is outer:
            return True
        cur = cur.parent
    return False


def _binder_between(inner, outer, name):
    """Whether a function scope strictly between `inner` and `outer` binds `name`: then `outer` is
    not the NEAREST binder, and a resolver that returned it would be wrong."""
    cur = inner.parent
    while cur is not None and cur is not outer:
        if cur.kind not in ("class", "module") and cur.local(name):
            return True
        cur = cur.parent
    return False


def symtable_disagreements(sources):
    """Where this module's scope resolution differs from CPython's own symtable, over `sources`
    (fname -> text). Returns (disagreements, scopes_compared). A resolver written to match its own
    fixture agrees with it forever; this judges it against the compiler's reading instead.

    For every function and class scope that both sides can identify uniquely by (kind, name, line),
    every name symtable calls local must be one this module binds there, and vice versa, except a
    comprehension target, which CPython 3.12 inlines into the enclosing function (PEP 709) while it
    stays invisible outside the comprehension at runtime; and every name symtable calls free or
    global must resolve here to an enclosing function or to the module, respectively."""
    import symtable
    out, compared = [], 0
    for fname, text in sources.items():
        tree = ast.parse(text)
        w = walk({fname: tree})[fname]
        mine, by_key = {}, {s.key: s for s in w.scopes}
        for s in w.scopes:
            if s.kind in ("function", "class"):
                mine.setdefault((s.kind, getattr(s.node, "name", "lambda"), s.key[1]), []).append(s)
        comp_targets = collections.defaultdict(set)
        for s in w.scopes:
            if s.kind == "comprehension":
                outer = s.parent
                while outer.kind == "comprehension":
                    outer = outer.parent
                comp_targets[outer.key] |= s.bound
        theirs = {}
        def collect(t):
            for c in t.get_children():
                table_type = c.get_type()
                kind = {"function": "function", "class": "class"}.get(
                    getattr(table_type, "value", table_type))
                if kind:
                    theirs.setdefault((kind, c.get_name(), c.get_lineno()), []).append(c)
                collect(c)
        collect(symtable.symtable(text, fname, "exec"))
        for k, ours in mine.items():
            if len(ours) != 1 or len(theirs.get(k, [])) != 1:
                continue
            s, t = ours[0], theirs[k][0]
            compared += 1
            sym_local = {x.get_name() for x in t.get_symbols() if x.is_local()}
            our_local = {n for n in s.bound if s.local(n)}
            extra = sym_local - our_local - comp_targets[s.key]
            if s.kind == "class":
                extra -= {"__class__", "__classdict__", "__static_attributes__",
                          "__firstlineno__", "__type_params__"}
            if extra or (our_local - sym_local):
                out.append((fname, k, "local", sorted(extra), sorted(our_local - sym_local)))
            for x in t.get_symbols():
                n = x.get_name()
                if n.startswith(".") or n in our_local or n in comp_targets[s.key]:
                    continue                           # ".type_params" and the like are internal
                got = resolve(s, n)
                if x.is_free():
                    # Free: it must be THE enclosing scope that binds it (a class only for the
                    # implicit __class__ cell), not merely "somewhere other than here".
                    owner = by_key.get(got)
                    if not (owner is not None and _encloses(owner, s) and (
                            (owner.kind == "class" and n == "__class__")
                            or (owner.kind != "class" and owner.local(n)))
                            and not _binder_between(s, owner, n)):
                        out.append((fname, k, "free", n, got))
                elif x.is_global() and got != MODULE:
                    out.append((fname, k, "global", n, got))
    return out, compared


def audit():
    """Returns (missing, checked, unverifiable). `missing` is the refusal set."""
    manifest = json.loads((SUITES / "manifest.json").read_text())
    order = [s["file"] for s in manifest["suites"]]
    trees = {f: ast.parse((SUITES / f).read_text()) for f in order}
    refs = references(order, trees, binding_counts(trees))

    cache, unverifiable = {}, {}
    def load(rel):
        if rel not in cache:
            try:
                spec = importlib.util.spec_from_file_location(
                    "suiteattr_" + rel.replace("/", "_").replace(".", "_"), ROOT / rel)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                cache[rel] = mod
            except Exception as exc:                     # a module needing injected helpers
                cache[rel] = None
                unverifiable[rel] = type(exc).__name__
        return cache[rel]

    missing, checked = [], 0
    for fname, line, alias, attr, rel in refs:
        mod = load(rel)
        if mod is None:
            continue
        checked += 1
        if not hasattr(mod, attr):
            missing.append((fname, line, alias, attr, rel))
    return missing, checked, unverifiable


def main():
    missing, checked, unverifiable = audit()
    print("suite attr check: %d reference(s) on uniquely-bound module aliases" % checked)
    if unverifiable:
        print("  unverifiable (needs injected helpers, NOT passed): %s"
              % ", ".join("%s (%s)" % kv for kv in sorted(unverifiable.items())))
    for fname, line, alias, attr, rel in missing:
        print("  %s:%d  %s.%s does not exist on %s - this reference raises AttributeError, and a "
              "broad except upstream turns that into a test that passes while proving nothing"
              % (fname, line, alias, attr, rel))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
