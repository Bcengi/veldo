"""VELDO-0007: install and run, from the artifact an adopter receives.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 24_veldo_0007_install_and_run

WHAT IS UNDER TEST. scripts/check_install_and_run.py, and it is DRIVEN FOR REAL: it composes with
the real publisher, installs from a real composed pack with that pack's own scaffolder, and runs the
scaffolded repository's own gate. Measured at 1.8 seconds for all seven packs, which is why the
expensive-looking thing is done rather than mocked. A mocked install would test the mock, and the
defect this item exists for was invisible to every test that ran against this repository.

THE SPEND IS BOUNDED DELIBERATELY. The full seven-pack sweep runs ONCE here; the mutation rows drive
a SINGLE pack, because the property they test is per-pack and seven copies of it would cost six times
the wall clock for no extra teeth.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
import ast as _iar_ast
import hashlib as _iar_hl
import os as _iar_os
import re as _iar_re
import shutil as _iar_sh
import subprocess as _iar_sp
import sys as _iar_sys

IAR = V._VC._organ("check_install_and_run", ROOT / "scripts" / "check_install_and_run.py")


def _iar_block(label, fn):
    try:
        fn()
    except Exception as _iar_e:                  # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0007 %s: the block ran to completion rather than raising (%r)"
               % (label, _iar_e), False)


def _iar_inventory(root):
    """relative path -> (size, mtime_ns, sha256) for EVERY entry under root, recursively.

    THE OBSERVATION AC4 RESTS ON, AND IT EXCLUDES NOTHING. The assertion this replaced was
    `git status --porcelain` equality, which cannot see a path outside the repository nor an
    ignored path inside it: a review wrote into $HOME on every call and into .veldo/trackers.json
    and scripts/__pycache__/l2probe.txt and the suite stayed at 47 passed / 0 failed. An inventory
    that skipped __pycache__ would have missed one of those exactly, so nothing is skipped and the
    interpreter's own bytecode caching is suppressed with PYTHONDONTWRITEBYTECODE instead: a cache
    the interpreter writes is not this stage writing, while a file the stage writes with any name at
    all, inside __pycache__ included, still moves an entry here. Directories and symlinks are
    entries too, so an empty directory or a relinked path is a change.

    THE MODIFICATION TIME IS PART OF THE RECORD, AND THAT WAS FOUND BY DRIVING. Content and path
    alone leave an IDEMPOTENT write invisible: the review's mutation writes the same bytes on every
    call, so by the second call the digest and the size are unchanged and a content-only inventory
    reported a clean tree while the file had just been clobbered again. st_mtime_ns moves on any
    rewrite, identical bytes included."""
    root = Path(root)
    inv = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        try:
            st = p.lstat()
            if p.is_symlink():
                inv[rel] = ("symlink", st.st_mtime_ns, _iar_os.readlink(p))
            elif p.is_dir():
                inv[rel] = ("dir", st.st_mtime_ns, "")
            else:
                data = p.read_bytes()
                inv[rel] = (len(data), st.st_mtime_ns, _iar_hl.sha256(data).hexdigest())
        except OSError as _iar_e:                # a path that cannot be read is still an OBSERVATION
            inv[rel] = ("unreadable", 0, str(_iar_e))
    return inv


def _iar_changed(before, after):
    """The entries that differ, so a red row NAMES the paths that moved rather than only failing."""
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def _iar_dotted(node):
    """The dotted spelling of a call target: subprocess.run, os.system, run."""
    bits = []
    while isinstance(node, _iar_ast.Attribute):
        bits.append(node.attr)
        node = node.value
    if isinstance(node, _iar_ast.Name):
        bits.append(node.id)
    return ".".join(reversed(bits))


# EVERY WAY THIS FILE COULD START A CHILD, and every keyword that would detach one or interpose a
# shell. The identifier scan below cannot see a keyword argument, which is how start_new_session=True
# passed it, so the keywords are asserted as keywords.
_IAR_LAUNCHERS = {"subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call",
                  "subprocess.check_output", "os.system", "os.popen", "os.spawnv", "os.spawnl",
                  "os.posix_spawn", "os.fork", "os.forkpty", "pty.spawn"}
_IAR_DETACHING = {"start_new_session", "preexec_fn", "creationflags", "process_group", "shell"}
_IAR_LAUNCH_OK = {"cwd", "capture_output", "text", "timeout", "env", "check", "input", "encoding",
                  "errors", "stdin", "stdout", "stderr", "bufsize"}


# ONE full run, shared by the rows below, because composing and installing seven packs is the
# expensive part and doing it per row would multiply the cost with no gain in teeth.
_IAR_OK, _IAR_REP = IAR.check()
_IAR_LINES = IAR.report_lines(_IAR_REP)


# ---------------------------------------------------------------------------------------
# AC1. IT INSTALLS FROM THE COMPOSED PACK, NOT FROM THIS REPOSITORY.
#
# FALSIFIED BY: point the installer at this repository's own scaffolder, and the row below
# (no engine/ in the tree it ran from) must go red.
#
# FOUND VACUOUS BY A REVIEW AND FIXED HERE. Both rows used to read `installed_from` and
# `pack_has_engine_dir`, which describe the directory install_and_run was HANDED. Swapping the
# launched executable for this repository's own scaffolder therefore left every row green while the
# stage printed `(engine/ present: False)` for all seven packs and every install had in fact been
# laid from engine/ - the 1.0 shape, reported as its own absence. The rows now read the argv the
# child was handed and the tree derived from it.
# ---------------------------------------------------------------------------------------


def _iar_ac1():
    expect("VELDO-0007 AC1: every install ran from a tree with NO engine/ directory - the COMPOSED "
           "PACK shape, where the base has been laid into the pack and the pack root IS the template "
           "source. That absence is the exact condition 1.0 broke on, and running from this "
           "repository (which HAS engine/) is what hid it, because every test ran against the one "
           "tree nobody installs. Asserted on the tree the EXECUTED scaffolder belongs to, derived "
           "from the argv the child received, never on the directory the function was passed",
           _IAR_REP["results"]
           and all(r["scaffolder_tree_has_engine_dir"] is False for r in _IAR_REP["results"]))
    expect("VELDO-0007 AC1: the scaffolder that ran is the PACK'S OWN copy - the executable path "
           "recorded from the child's own argv is the pack directory plus %s, and it sits under "
           "/packs/<pack>, so the launch is under the composed pack and never under this repository"
           % IAR.SCAFFOLDER,
           _IAR_REP["results"]
           and all(Path(r["scaffolder_ran"]) == Path(r["installed_from"]) / IAR.SCAFFOLDER
                   and r["scaffolder_ran"].endswith("/packs/%s/%s" % (r["pack"], IAR.SCAFFOLDER))
                   and Path(r["scaffolder_tree"]).resolve() != ROOT.resolve()
                   for r in _IAR_REP["results"]))
    expect("VELDO-0007 AC1 NEGATIVE CONTROL: the alternative the falsification names EXISTS and is "
           "the opposite shape - THIS repository carries %s and DOES have engine/ - so the two rows "
           "above are a measurement of which tree ran rather than a property that holds everywhere. "
           "Point the launch here and both go red" % IAR.SCAFFOLDER,
           (ROOT / "engine").is_dir() and (ROOT / IAR.SCAFFOLDER).is_file())


_iar_block("AC1", _iar_ac1)


# ---------------------------------------------------------------------------------------
# AC2. THE PACK SET IS DERIVED FROM WHAT THE PUBLISHER COMPOSED, NEVER TYPED.
#
# FALSIFIED BY: replace the derived set with a hand-written list naming one pack, and the set
# equality row below must go red.
# ---------------------------------------------------------------------------------------


def _iar_ac2():
    expect("VELDO-0007 AC2: the set installed EQUALS the set the publisher composed, and it is "
           "non-trivial (%d packs). A hand-kept list is the defect this repository has shipped "
           "twice: seven listed pairs guarded nine modules that arrived later"
           % len(_IAR_REP["composed"]),
           set(_IAR_REP["installed"]) == set(_IAR_REP["composed"])
           and len(_IAR_REP["composed"]) >= 2
           and any("composed pack(s) derived from the publisher" in ln for ln in _IAR_LINES))

    with tempfile.TemporaryDirectory() as d:
        empty = Path(d) / "public"
        (empty / "packs").mkdir(parents=True)
        expect("VELDO-0007 AC2: a produced tree with NO composed pack yields an EMPTY derived set, "
               "which the checker turns into NO_PACKS_COMPOSED rather than a clean pass. A loop over "
               "an empty set passes while proving nothing, which is the vacuous shape this repository "
               "keeps finding",
               IAR.composed_packs(empty) == [])
        (empty / "packs" / "notcomposed").mkdir()
        expect("VELDO-0007 AC2: a pack directory WITHOUT the scaffolder is a pack SOURCE, not a "
               "composed artifact, and is excluded - installing from one would be testing the wrong "
               "tree, which is this item's whole subject",
               IAR.composed_packs(empty) == [])
    # THE VACUOUS-RUN GUARD, DRIVEN THROUGH THE COMPOSER SEAM. Found vacuous by driving: the rows
    # above test composed_packs() over a fixture and never reach the guard inside check(), so
    # disabling the guard left the suite green. A guard against an empty pack set that nothing drives
    # is itself the vacuous shape it exists to prevent.
    class _IarEmptyCompose:
        returncode, stdout, stderr = 0, "", ""

    def _iar_empty(dest, root=None):
        (Path(dest) / "packs").mkdir(parents=True, exist_ok=True)
        return _IarEmptyCompose()

    ok_empty, rep_empty = IAR.check(composer=_iar_empty)
    expect("VELDO-0007 AC2 THE GUARD'S OWN TEETH: a composer that produces a tree with NO composed "
           "pack makes the whole stage FAIL by name with NO_PACKS_COMPOSED, rather than passing over "
           "an empty loop. Driven through an injected composer, the way fleet.py's seams are driven, "
           "because the guard lives inside check() and nothing else reaches it",
           ok_empty is False and rep_empty["failure"] == IAR.FAIL_NO_PACKS
           and rep_empty["results"] == []
           and any(IAR.FAIL_NO_PACKS in ln for ln in IAR.report_lines(rep_empty)))
    expect("VELDO-0007 AC2 NEGATIVE CONTROL for the guard: the DEFAULT composer (the real publisher) "
           "produces packs and the stage passes, so the refusal above is a measurement of what was "
           "composed rather than the guard firing always",
           _IAR_OK is True and len(_IAR_REP["composed"]) >= 2)

    expect("VELDO-0007 AC2: each named failure is registered under a unique name, so no two broken "
           "stages of an adopter's first ten minutes share a spelling",
           len(set(IAR.FAILURES)) == len(IAR.FAILURES)
           and {IAR.FAIL_COMPOSE, IAR.FAIL_NO_PACKS, IAR.FAIL_INIT, IAR.FAIL_GATE}
           == set(IAR.FAILURES))


_iar_block("AC2", _iar_ac2)


# ---------------------------------------------------------------------------------------
# AC3. THE ADOPTER'S OWN GATE MUST GO GREEN, AND THE PROOF IS A BROKEN ONE GOING RED.
#
# FALSIFIED BY: ignore the nested gate's exit status, and the corrupted-substrate row must go red.
# ---------------------------------------------------------------------------------------


def _iar_ac3():
    expect("VELDO-0007 AC3: every scaffolded repository's OWN gate exited zero, over all %d packs. "
           "Laying files down is not installing: 1.0 laid nothing and said so, but a scaffolder that "
           "lays a repository whose gate is RED is worse, because the adopter's first act fails and "
           "the failure looks like their fault"
           % len(_IAR_REP["results"]),
           _IAR_OK is True and _IAR_REP["failure"] is None
           and all(r["gate_returncode"] == 0 for r in _IAR_REP["results"])
           and all(r["files_created"] > 10 for r in _IAR_REP["results"]))

    # TEETH, DRIVEN: corrupt a required substrate file inside a composed pack and require the stage
    # to fail by name. One pack, because the property is per-pack.
    with tempfile.TemporaryDirectory() as d:
        pub = Path(d) / "public"
        proc = IAR.compose(pub, ROOT)
        expect("VELDO-0007 AC3: the real publisher composed a tree for the mutation below, so the "
               "teeth are proven against a real artifact rather than a fixture",
               proc.returncode == 0 and IAR.composed_packs(pub))
        pack = pub / "packs" / IAR.composed_packs(pub)[0]
        (pack / ".veldo" / "validate.py").write_text("this is not python(\n")
        res = IAR.install_and_run(pack, Path(d) / "fresh")
        expect("VELDO-0007 AC3 THE TEETH: with a required substrate file CORRUPTED inside the "
               "composed pack, the install-and-run result fails BY NAME rather than passing because "
               "files were laid. Driven against a real composed pack, and the failure is either "
               "INIT_FAILED or ADOPTER_GATE_RED - both are correct, and which one fires is a "
               "property of where the corruption bites, so the row accepts either and requires a "
               "named failure",
               res["failure"] in (IAR.FAIL_INIT, IAR.FAIL_GATE))
        expect("VELDO-0007 AC3: the failing result QUOTES the reason - init's own output or the "
               "adopter's own gate tail - because 'their gate failed' without the reason sends "
               "nobody anywhere",
               (res["init_tail"] or res["gate_tail"]))

    # THE ADOPTER-GATE CHECK NEEDS ITS OWN TEETH, and FOUND VACUOUS BY DRIVING: the row above accepts
    # INIT_FAILED or ADOPTER_GATE_RED, so disabling the gate-status check entirely left the suite
    # green - the corruption above breaks init before the gate is ever consulted. So this row breaks
    # something init lays down HAPPILY and the adopter's gate then REFUSES: an invalid starter plan.
    # Init must SUCCEED here, which is what makes the failure attributable to the gate alone.
    with tempfile.TemporaryDirectory() as d:
        pub = Path(d) / "public"
        proc = IAR.compose(pub, ROOT)
        pack = pub / "packs" / IAR.composed_packs(pub)[0]
        (pack / "plans" / "STARTER.md").write_text(
            "---\nschema: veldo.plan/v1\nid: PLAN-9999\nstatus: donezo\n---\n\nbroken\n")
        res2 = IAR.install_and_run(pack, Path(d) / "fresh-gate")
        expect("VELDO-0007 AC3 THE GATE'S OWN TEETH: with an INVALID STARTER PLAN inside the composed "
               "pack, init SUCCEEDS and lays the repository down happily while the adopter's OWN gate "
               "REFUSES it - so the failure is ADOPTER_GATE_RED and is attributable to the nested gate "
               "alone. Found by driving: without this row, deleting the gate-status check left every "
               "assertion green, because the other mutation breaks init before the gate is consulted",
               res2["init_returncode"] == 0 and res2["files_created"] > 10
               and res2["failure"] == IAR.FAIL_GATE
               and res2["gate_returncode"] not in (0, None))


_iar_block("AC3", _iar_ac3)


# ---------------------------------------------------------------------------------------
# AC4. IT TOUCHES NOTHING OUTSIDE A TEMPORARY DIRECTORY.
#
# FALSIFIED BY: write anywhere outside the temporary directory, and the rows below must go red.
#
# WHAT WAS WRONG, AND IT WAS THE WHOLE CRITERION. This block used to compare
# `git status --porcelain` before and after, plus an AST scan of identifiers. That proxy is blind to
# three things at once, and a review drove all three with the suite at 47 passed / 0 failed: a write
# into $HOME (outside the repository), writes to .veldo/trackers.json and
# scripts/__pycache__/l2probe.txt (ignored INSIDE the repository, so invisible to git status), and
# start_new_session=True in the launcher (a keyword argument, so invisible to an identifier scan).
#
# SO THE PROXY IS GONE AND THE WRITES ARE OBSERVED. The stage is run as a subprocess in a sandbox
# where every root it could legitimately write to is DECLARED - its own copy of the working tree, its
# own HOME, its own TMPDIR - and a recursive inventory of path, size and sha256 over the first two is
# required to be identical across the run while the run demonstrably did the work. The copy is of the
# WORKING TREE and not a clone of HEAD, so a mutation under review is inside the thing observed; a
# clone would run the committed code and report green about a mutation it never executed.
# ---------------------------------------------------------------------------------------


def _iar_ac4():
    sand = Path(tempfile.mkdtemp(prefix="veldo-0007-write-scope-"))
    try:
        repo, home, run_tmp = sand / "repo", sand / "home", sand / "tmp"
        cp = _iar_sp.run(["cp", "-a", str(ROOT), str(repo)], capture_output=True, text=True)
        home.mkdir()
        (home / ".veldo-write-scope-sentinel").write_text(
            "a byte written outside a temporary directory lands in here\n")
        run_tmp.mkdir()
        expect("VELDO-0007 AC4 THE OBSERVATION'S OWN SUBSTRATE: the WORKING TREE was copied - not a "
               "clone of HEAD, so a mutation under review is inside the tree being observed - and "
               "the copy carries the stage and its git directory, so the run below is the real "
               "compose-install-gate path rather than a fixture",
               cp.returncode == 0 and (repo / "scripts" / "check_install_and_run.py").is_file()
               and (repo / ".git").is_dir())
        env = dict(_iar_os.environ, HOME=str(home), TMPDIR=str(run_tmp),
                   PYTHONDONTWRITEBYTECODE="1")
        b_repo, b_home = _iar_inventory(repo), _iar_inventory(home)
        proc = _iar_sp.run([_iar_sys.executable, "scripts/check_install_and_run.py",
                            "--pack", _IAR_REP["composed"][0]],
                           cwd=str(repo), env=env, capture_output=True, text=True, timeout=900)
        a_repo, a_home = _iar_inventory(repo), _iar_inventory(home)
        laid = _iar_re.search(r"installed (\d+) file\(s\) from (\S+)", proc.stdout)
        expect("VELDO-0007 AC4 THE RUN REALLY WROTE A GREAT DEAL, which is what stops the two rows "
               "below being vacuous: the sandboxed stage composed with the real publisher, installed "
               "and ran a nested gate - exit zero, 'install-and-run: pass', more than ten files laid "
               "down - and the pack it installed FROM sits UNDER the TMPDIR it was given, so the "
               "bytes went where the criterion says they go. Said: %r"
               % (proc.stdout.strip()[-300:] + proc.stderr.strip()[-200:],),
               proc.returncode == 0 and "install-and-run: pass" in proc.stdout
               and laid is not None and int(laid.group(1)) > 10
               and laid.group(2).startswith(str(run_tmp) + "/"))
        expect("VELDO-0007 AC4: NOT ONE BYTE of the repository under check changed across that run - "
               "every path, size, modification time and sha256 identical, GIT-IGNORED PATHS INCLUDED, "
               "which is the half a `git status` comparison could not see: a review wrote "
               ".veldo/trackers.json (the one file the ignore rule exists to protect) and a file "
               "inside scripts/__pycache__ and every row stayed green. Entries that moved: %r"
               % (_iar_changed(b_repo, a_repo)[:6],),
               _iar_changed(b_repo, a_repo) == [])
        expect("VELDO-0007 AC4: NOT ONE BYTE outside the repository either - the process ran with a "
               "HOME of its own and that directory, sentinel file included, is byte-identical "
               "afterwards. A review's probe wrote a 36-byte file into $HOME on every single call "
               "and no row noticed, because the old assertion could only see tracked paths inside "
               "this one tree. Entries that moved: %r" % (_iar_changed(b_home, a_home)[:6],),
               _iar_changed(b_home, a_home) == [])
        expect("VELDO-0007 AC4: the temporary directory is REMOVED - the TMPDIR handed to that run "
               "holds no veldo-install-and-run-* tree once it returned, so a sweep of runs cannot "
               "fill the disk. Asserted over the directory this row created, never over the "
               "machine's /tmp, because the machine's temp directory is live state nobody owns",
               [p.name for p in run_tmp.glob("veldo-install-and-run-*")] == [])
    finally:
        _iar_sh.rmtree(sand, ignore_errors=True)

    # AND THE SAME OBSERVATION AGAINST THE LIVE TREE, driven in-process, because the sandbox above
    # cannot see a write to an absolute path that escapes it. PYTHONDONTWRITEBYTECODE is set for the
    # window so that the interpreter's own caching (publish.py loads a module by path, which writes a
    # .pyc) is not mistaken for this stage writing; an explicit write of any name is still caught.
    _iar_pyc = _iar_os.environ.get("PYTHONDONTWRITEBYTECODE")
    _iar_os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        b_live = _iar_inventory(ROOT)
        ok2, rep2 = IAR.check(only=_IAR_REP["composed"][0])
        a_live = _iar_inventory(ROOT)
    finally:
        if _iar_pyc is None:
            _iar_os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        else:
            _iar_os.environ["PYTHONDONTWRITEBYTECODE"] = _iar_pyc
    expect("VELDO-0007 AC4: THIS repository is untouched by a real in-process run too - the whole "
           "tree inventoried by path, size, modification time and sha256 before and after, "
           "ignored paths and .git included, with the run PASSING so the identity is across work "
           "rather than across a no-op. A check that mutated the tree it is checking is the shape "
           "that makes a green gate meaningless. Entries that moved: %r"
           % (_iar_changed(b_live, a_live)[:6],),
           _iar_changed(b_live, a_live) == [] and ok2 is True and rep2["results"])

    src = (ROOT / "scripts" / "check_install_and_run.py").read_text()
    _iar_mod = _iar_ast.parse(src)
    names = set()
    for node in _iar_ast.walk(_iar_mod):
        if isinstance(node, _iar_ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, _iar_ast.Name):
            names.add(node.id)
    expect("VELDO-0007 AC4: it makes no network call - no urlopen, no requests, no socket - and no "
           "second process-launch mechanism. AST identifiers rather than substrings, because prose "
           "describing what it refuses to do is prose. THE DETACHED-PROCESS HALF IS NOT THIS ROW: a "
           "keyword argument has no identifier, which is why start_new_session=True passed this scan "
           "untouched, and the two rows below are what carry it",
           not (names & {"urlopen", "requests", "socket", "urlretrieve", "Popen", "fork", "forkpty",
                         "daemon"})
           and "mkdtemp" in names and "rmtree" in names)

    launches = [(n.lineno, sorted(k.arg for k in n.keywords if k.arg))
                for n in _iar_ast.walk(_iar_mod)
                if isinstance(n, _iar_ast.Call) and _iar_dotted(n.func) in _IAR_LAUNCHERS]
    funnel = [n for n in _iar_ast.walk(_iar_mod)
              if isinstance(n, _iar_ast.FunctionDef) and n.name == "_run"]
    expect("VELDO-0007 AC4 THE SINGLE FUNNEL: every child this stage starts is launched from ONE "
           "helper (_run), asserted over the file's own call graph, which is what makes the keyword "
           "observation below a statement about EVERY child rather than about one call site. Launch "
           "sites found: %r" % (launches,),
           len(launches) == 1 and len(funnel) == 1
           and all(funnel[0].lineno <= ln <= funnel[0].end_lineno for ln, _ in launches))
    expect("VELDO-0007 AC4 STARTS NO DETACHED PROCESS, asserted on the launch's OWN KEYWORD "
           "ARGUMENTS: none of start_new_session, preexec_fn, creationflags, process_group or shell, "
           "and every keyword passed is one of the declared benign set, so a spelling nobody thought "
           "of is red too. A review added start_new_session=True and the identifier scan above could "
           "not see it. Keywords found: %r" % ([kw for _, kw in launches],),
           launches and all(not (set(kw) & _IAR_DETACHING) and set(kw) <= _IAR_LAUNCH_OK
                            for _, kw in launches))

    # AND DRIVEN, not only read: the static rows can be evaded by a computed kwargs dict, and a
    # dynamic recorder only sees what it drives, so both are here.
    class _IarRecorder:
        def __init__(self, real):
            self._real, self.calls = real, []

        def run(self, *a, **kw):
            # THE NAMES, not the values: env carries the whole environment and a failing row has to
            # be readable. The names are what the assertion is about.
            self.calls.append(sorted(kw))
            return self._real.run(*a, **kw)

        def __getattr__(self, k):
            return getattr(self._real, k)

    _iar_real_sp = IAR.subprocess
    IAR.subprocess = _IarRecorder(_iar_real_sp)
    try:
        child = IAR._run([_iar_sys.executable, "-c", "print('veldo-0007 child ran')"])
    finally:
        _iar_rec, IAR.subprocess = IAR.subprocess, _iar_real_sp
    expect("VELDO-0007 AC4 THE LAUNCH IS DRIVEN: the one helper was called for real, a child ran and "
           "its output came back, and the keyword arguments it actually passed were RECORDED - no "
           "detaching spelling among them, all within the benign set. Recorded: %r"
           % (_iar_rec.calls,),
           child.returncode == 0 and "veldo-0007 child ran" in child.stdout
           and _iar_rec.calls
           and all(not (set(kw) & _IAR_DETACHING) and set(kw) <= _IAR_LAUNCH_OK
                   for kw in _iar_rec.calls))


_iar_block("AC4", _iar_ac4)


# ---------------------------------------------------------------------------------------
# AC5. IT IS A REQUIRED CATALOG ITEM IN BOTH GATES.
#
# FALSIFIED BY: declare the stage `na` in scripts/verify.sh, and the row below must go red.
#
# THE REGISTRATION IS A PROTECTED-PATH EDIT AND IS NOT MADE HERE. scripts/verify.sh is a protected
# path, so declaring the slot needs Dmitry's recorded, commit-bound approval. This criterion therefore
# REPORTS until the registration lands and REFUSES after, the same migration posture VELDO-0001 used:
# a criterion that quietly passed while unregistered would be the false-coverage shape this project
# keeps finding.
#
# ONE GATE, NOT BOTH, and this repository's own capability-honesty check is what corrected it: the
# script does not ship to an adopter and an adopter does not publish packs, so a slot in the shipped
# template would be a required check they cannot run.
# ---------------------------------------------------------------------------------------

_IAR_STAGE = "scripts/check_install_and_run.py"
_IAR_GATES = ("scripts/verify.sh",)
# BY ITS COMMAND, not by a slot name. It landed in the EXISTING packaging slot - composing the
# published packs and proving an adopter can install and run them IS packaging verification - so
# asserting a slot name would pin a catalog vocabulary this item never added.
_IAR_DECLARED = {g: (_IAR_STAGE in (ROOT / g).read_text()) for g in _IAR_GATES}
_IAR_REQUIRED = {g: any(ln.strip().startswith("CHECK_") and '="required:' in ln
                        and _IAR_STAGE in ln
                        for ln in (ROOT / g).read_text().splitlines())
                 for g in _IAR_GATES}
_IAR_REGISTERED = all(_IAR_REQUIRED.values())


def _iar_ac5():
    # UNCONDITIONAL, AND THE BRANCH IS GONE ON PURPOSE. This criterion used to REPORT while the
    # protected-path edit waited for approval. Dmitry approved it on 2026-08-12 and the registration
    # landed, so the pending state no longer exists - and DRIVING PROVED THE BRANCH HAD TO GO: with
    # the registration removed entirely, both branches of the posture passed (declared False equals
    # required False), so the enforcing state could be silently reverted to reporting. A posture
    # derived from the live gate cannot catch its own removal. Ledger finding 45, second instance.
    expect("VELDO-0007 AC5: the install-and-run stage is declared `required:` in this repository's "
           "gate, so the proof of an adopter's first ten minutes runs on EVERY gate run rather than "
           "when somebody remembers. Asserted BY ITS COMMAND, not by a slot name: it landed in the "
           "existing packaging slot, because composing the published packs and proving a stranger can "
           "install and run them IS packaging verification",
           all(_IAR_REQUIRED.values()) and _IAR_REQUIRED)
    expect("VELDO-0007 AC5: MENTIONING the stage without REQUIRING it is red - a gate naming the "
           "script in an `na:` slot or a comment is a half-done registration, which is the failure "
           "this row exists for now that the real one has landed",
           _IAR_DECLARED == _IAR_REQUIRED)
    expect("VELDO-0007 AC5: it is DELIBERATELY ABSENT from the shipped template, and must stay "
           "absent: the script does not ship to an adopter and an adopter does not publish packs, so "
           "a required slot in their gate would be a check they cannot run. Corrected by this "
           "repository's own capability-honesty check rather than by me",
           _IAR_STAGE not in (ROOT / "engine/scripts/verify.sh").read_text())
    expect("VELDO-0007 AC5: the checker is EXECUTABLE as a stage runs it - invoked as a subprocess "
           "over one pack, exiting zero",
           _iar_sp.run([_iar_sys.executable, str(ROOT / "scripts" / "check_install_and_run.py"),
                        "--pack", _IAR_REP["composed"][0]],
                       cwd=str(ROOT), capture_output=True, text=True).returncode == 0)


_iar_block("AC5", _iar_ac5)


# WHAT SHIPS IS DECIDED BY ONE PARSE OF ONE GIT READ, so that parse is asserted here rather than
# trusted. Found 2026-08-12 while merging this round: publish.tracked_files() ran `ls-files` with NO
# `-z` and split the result on the literal `\n0` - a typo for `\0` - and then on whitespace. A tracked
# path containing a SPACE became several bogus paths and shipped as none of them, and a top-level path
# sorting at `0` truncated the list, dropping everything after it from every composed pack. It had
# never fired, because this repository happens to have no such path, so it WORKED BY ACCIDENT.
# scripts/migrate_to_veldo.py and scripts/rename_migration.py already did it correctly: three
# implementations of one operation, and the one that differed was the one that decides what an adopter
# receives.
def _iar_publisher_parse():
    _iar_pub = V._VC._organ("veldo_publish", ROOT / "scripts" / "publish.py")
    # THE INDEPENDENT ENUMERATION, asked of git through a route that shares no parsing with the
    # publisher's. Compared in BOTH directions and never as a count, because this repository grows.
    _iar_z = _iar_sp.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                         capture_output=True, text=True, check=True).stdout
    _iar_indep = sorted(p for p in _iar_z.split("\0") if p)
    _iar_seen = _iar_pub.tracked_files()
    expect("VELDO-0007 ride-along: THE PUBLISHER'S TRACKED SET EQUALS AN INDEPENDENT GIT ENUMERATION "
           "in both directions, over this repository's real corpus, with no cardinality asserted. The "
           "publisher decides what every adopter receives, so its one parse of git's output is "
           "checked against git rather than assumed",
           sorted(_iar_seen) == _iar_indep
           and set(_iar_seen) <= set(_iar_indep) and set(_iar_indep) <= set(_iar_seen)
           and bool(_iar_seen))
    # THE DRIVEN CASE, in a throwaway repository, because the property cannot be exercised here: this
    # tree has no path with a space and none sorting at `0`, which is exactly why the defect survived.
    # A fixture is the only way to reach the shape, so the fixture IS the evidence.
    import tempfile as _iar_tf
    with _iar_tf.TemporaryDirectory() as _iar_d:
        for _iar_cmd in (["git", "init", "-q", "."],
                         ["git", "-c", "user.email=a@b", "-c", "user.name=a",
                          "commit", "-q", "--allow-empty", "-m", "init"]):
            _iar_sp.run(_iar_cmd, cwd=_iar_d, capture_output=True, text=True, check=True)
        for _iar_name in ("a file with spaces.md", "0-sorts-first.md", "zz-last.md"):
            (_iar_os.path.join(_iar_d, _iar_name) and
             open(_iar_os.path.join(_iar_d, _iar_name), "w").write("x\n"))
        _iar_sp.run(["git", "add", "-A"], cwd=_iar_d, capture_output=True, text=True, check=True)
        _iar_sp.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "f"],
                    cwd=_iar_d, capture_output=True, text=True, check=True)
        _iar_zf = _iar_sp.run(["git", "-C", _iar_d, "ls-files", "-z"],
                              capture_output=True, text=True, check=True).stdout
        _iar_want = sorted(p for p in _iar_zf.split("\0") if p)
        # THE SUBJECT IS THE PUBLISHER, ASKED ABOUT THE FIXTURE. The first version of this row
        # compared a value against itself and computed the old parse inline, so it never called the
        # publisher at all and stayed GREEN under the mutation - the same vacuous shape this whole
        # round exists to remove, written while removing it. This calls tracked_files(root=...), which
        # is why the root seam exists.
        _iar_got = _iar_pub.tracked_files(root=_iar_d)
        expect("VELDO-0007 ride-along, DRIVEN IN A FIXTURE: THE PUBLISHER ITSELF, asked about a tree "
               "carrying a tracked path with a SPACE and one sorting at `0`, returns git's own set "
               "exactly. This cannot be asked of this repository, which has neither shape - which is "
               "precisely why the defect survived - so the fixture is the only place the property is "
               "observable and tracked_files takes a root in order to be asked here. The old parse "
               "FAILS this tree: it returns the whitespace fragments and loses the real path",
               _iar_got == _iar_want
               and "a file with spaces.md" in _iar_got
               and "zz-last.md" in _iar_got
               and "with" not in _iar_got)


_iar_block("publisher-parse", _iar_publisher_parse)
