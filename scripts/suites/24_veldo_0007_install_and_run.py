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

# EVERY WAY A PYTHON FILE COULD REACH A NETWORK, as identifiers, and every way a SHELL SCRIPT could,
# as tokens. ONE definition of each, used for this file AND for the children it launches, so the
# question asked of the stage and the question asked of the publisher and the nested gate cannot
# drift into two different questions that happen to agree.
_IAR_NETWORK = {"urlopen", "requests", "socket", "urlretrieve", "Popen", "fork", "forkpty", "daemon",
                "httpx", "urllib3", "http", "ftplib", "smtplib", "telnetlib", "paramiko"}
_IAR_NET_CMDS = (r"\bcurl\b", r"\bwget\b", r"\bnc\b", r"\bncat\b", r"\bssh\b", r"\bscp\b",
                 r"\brsync\b", r"\bpip\s+install\b", r"\bnpm\s+(install|i)\b",
                 r"\bgit\s+(push|fetch|pull|clone|ls-remote|remote\s+add)\b")


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
# FOUND VACUOUS TWICE, AT TWO DEPTHS, AND BOTH ARE DRIVEN BELOW.
#   1. The rows read `installed_from` and `pack_has_engine_dir`, which describe the directory
#      install_and_run was HANDED. Swapping the launched executable for this repository's own
#      scaffolder left every row green while the stage printed `(engine/ present: False)` for all
#      seven packs, every install having in fact been laid from engine/.
#   2. The rows then read a record built from an argv list assigned ONE LINE ABOVE the call. Changing
#      the CALL alone - the record untouched - left every row of this criterion green again, and the
#      stage printed `(engine/ in that tree: False)` for a launch out of the tree that has engine/.
# A RECORD OF AN ARGUMENT IS NOT A RECORD OF A LAUNCH, at either depth. The record is now
# subprocess's own args off the CompletedProcess, and a recorder wrapping the one funnel observes the
# argv independently, so the row's subject is what ran rather than what was written down near it.
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
    expect("VELDO-0007 AC1: the scaffolder that ran is the PACK'S OWN copy - the executable path read "
           "OFF THE COMPLETED LAUNCH is the pack directory plus %s, and it sits under /packs/<pack>, "
           "so the launch is under the composed pack and never under this repository. An unanswerable "
           "record (an argv naming no scaffolder, or several) reds this row by its own name rather "
           "than raising out of the reader. Recorded: %r"
           % (IAR.SCAFFOLDER, [r["scaffolder_ran"] for r in _IAR_REP["results"]][:2]),
           _IAR_REP["results"]
           and all(r["scaffolder_ran"] and r["scaffolder_tree"]
                   and Path(r["scaffolder_ran"]) == Path(r["installed_from"]) / IAR.SCAFFOLDER
                   and r["scaffolder_ran"].endswith("/packs/%s/%s" % (r["pack"], IAR.SCAFFOLDER))
                   and Path(r["scaffolder_tree"]).resolve() != ROOT.resolve()
                   for r in _IAR_REP["results"]))
    # THE RECORD IS THE LAUNCH, AND THAT IS OBSERVED RATHER THAN TRUSTED. Both earlier versions of
    # this criterion asserted over a record built NEAR the call - first from the directory the
    # function was passed, then from a list assigned one line above it - and each was driven green by
    # a mutation that changed the call alone. So the argv every child actually received is recorded AT
    # THE LAUNCHER, by a recorder wrapping the one funnel, and the result's own record must be the
    # scaffolder argv that recorder saw, with that path UNDER the composed pack root.
    class _IarArgvRecorder:
        def __init__(self, real):
            self._real, self.argvs = real, []

        def run(self, argv, *a, **kw):
            self.argvs.append([str(x) for x in argv])
            return self._real.run(argv, *a, **kw)

        def __getattr__(self, k):
            return getattr(self._real, k)

    with tempfile.TemporaryDirectory() as _iar_d:
        _iar_pub = Path(_iar_d) / "public"
        IAR.compose(_iar_pub, ROOT)
        _iar_pk = IAR.composed_packs(_iar_pub)[0]
        _iar_pack_root = _iar_pub / "packs" / _iar_pk
        _iar_real_sp1 = IAR.subprocess
        IAR.subprocess = _IarArgvRecorder(_iar_real_sp1)
        try:
            # gate=False: the subject is the LAUNCH of the scaffolder, so the nested gate is not
            # bought again here. The full sweep above already ran it for every pack.
            _iar_res_a = IAR.install_and_run(_iar_pack_root, Path(_iar_d) / "fresh-argv", gate=False)
        finally:
            _iar_argv_rec, IAR.subprocess = IAR.subprocess, _iar_real_sp1
        _iar_seen = [a for a in _iar_argv_rec.argvs
                     if any(x.endswith(IAR.SCAFFOLDER) for x in a)]
        expect("VELDO-0007 AC1 THE RECORD IS THE LAUNCH, OBSERVED AT THE LAUNCHER: a recorder wrapping "
               "the one funnel captured the argv every child really received, exactly ONE of them names "
               "a scaffolder, the result's own scaffolder_argv IS that argv, and the executable in it "
               "sits UNDER the composed pack root. Driven because a record built beside the call is "
               "not a record of the call: with the record naming the pack's copy and only the call "
               "swapped for this repository's scaffolder, every row of this criterion stayed green. "
               "Observed: %r" % (_iar_seen[:1],),
               len(_iar_seen) == 1
               and _iar_res_a["scaffolder_argv"] == _iar_seen[0]
               and _iar_res_a["scaffolder_ran"] in _iar_seen[0]
               and Path(_iar_res_a["scaffolder_ran"]).is_relative_to(_iar_pack_root)
               and _iar_res_a["init_returncode"] == 0)
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
           "stages of an adopter's first ten minutes share a spelling. ONE ENUMERATION COMPARED FOR "
           "EQUALITY, not two lists that agree today: a name added to the module and not here, or "
           "here and not in the module, reds this row",
           len(set(IAR.FAILURES)) == len(IAR.FAILURES)
           and {IAR.FAIL_COMPOSE, IAR.FAIL_NO_PACKS, IAR.FAIL_INIT, IAR.FAIL_COMMIT, IAR.FAIL_GATE}
           == set(IAR.FAILURES))


_iar_block("AC2", _iar_ac2)


# ---------------------------------------------------------------------------------------
# AC3. THE ADOPTER'S OWN GATE MUST GO GREEN, AND THE PROOF IS A BROKEN ONE GOING RED.
#
# FALSIFIED BY: ignore the nested gate's exit status, and THE INVALID-STARTER-PLAN row must go red.
# NOT the corrupted-substrate row, and this comment used to name that one: the corruption breaks init
# before the gate is ever consulted, so the failure is INIT_FAILED and that row accepts either name.
# Driven under exactly that mutation, the invalid-starter row is the only red.
#
# AND FALSIFIED BY: skip the commit, and the row requiring the adopter's one required check to have
# reached MORE THAN ZERO files must go red, because that check enumerates through `git ls-files`.
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

    # WHAT THAT GREEN CONTAINS, AND IT USED TO CONTAIN A SCAN OF NOTHING. A review measured the
    # stage laying 83 files down while the shipped catalog's ONLY `required:` slot
    # (scripts/secret_inventory.py) reported "0 scanned" under a green labelled "GATE: GREEN
    # (no-git)": the stage ran `git init` and never committed, and that check enumerates through
    # `git ls-files`. The tree is now committed between init and the gate, which is also what a real
    # adopter's first ten minutes look like.
    #
    # THE ASSERTION IS A PROPERTY OVER A DEFECT SET, NEVER A PINNED COUNT. Nothing here says how
    # many files exist, how many are tracked or how many get scanned: it says that a commit HAPPENED,
    # that the index the gate reads is not empty, and that the required check reached MORE THAN ZERO
    # files. A tree that grows moves every one of those numbers and reds none of these rows; a
    # regression to an uncommitted tree reds all of them.
    expect("VELDO-0007 AC3 THE ADOPTER'S GREEN IS A MEASUREMENT AND NOT A SCAN OF NOTHING: every "
           "scaffolded tree was COMMITTED before its own gate ran, the index the gate reads is "
           "non-empty, and the one `required:` slot the shipped catalog carries reached MORE THAN "
           "ZERO files. No count is pinned - a growing template moves all of these numbers and reds "
           "nothing - because what is a defect by construction is a green whose required check "
           "inspected an empty corpus. Measured: %r"
           % ([(r["pack"], r["commit_returncode"], r["tracked_files"],
                (r["gate_substance"] or {}).get("scanned")) for r in _IAR_REP["results"]],),
           _IAR_REP["results"]
           and all(r["commit_returncode"] == 0
                   and (r["tracked_files"] or 0) > 10
                   and r["gate_substance"] is not None
                   and (r["gate_substance"]["scanned"] or 0) > 0
                   and (r["gate_substance"]["catalog_run"] or 0) >= 1
                   and r["gate_substance"]["commit"] not in (None, "", "no-git")
                   for r in _IAR_REP["results"]))

    # RECORDED IS NOT REPORTED, which is PLAN-0018 finding 64 in a new place. The nested gate stands
    # two built-ins down (no releases directory, no architecture contract) and counts both as passes.
    # That is correct for an adoption-safe gate and invisible in the word GREEN, so this stage must
    # NAME them on its own lines rather than leave them in a dict for nobody.
    _iar_sd = [sd for r in _IAR_REP["results"] for sd in (r["gate_substance"] or {}).get(
        "stand_downs", [])]
    expect("VELDO-0007 AC3 A STAND-DOWN THE NESTED GATE RECORDED IS REPORTED BY THIS STAGE: every "
           "stand-down line the adopter's gate emitted appears on this stage's own output, named, "
           "with the catalog split and the scan reach beside it. A stand-down counted into a green "
           "and never printed reads exactly like a measurement, and an operator cannot tell them "
           "apart. Reported %d stand-down line(s)" % (len(_iar_sd),),
           bool(_iar_sd)
           and all(any(sd in ln for ln in _IAR_LINES) for sd in _iar_sd)
           and any("their gate:" in ln for ln in _IAR_LINES)
           and any("stood down (recorded, not measured)" in ln for ln in _IAR_LINES)
           and any("the required check scanned" in ln for ln in _IAR_LINES))

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

    # THE COMMIT LEG'S OWN TEETH, DRIVEN THROUGH REAL GIT AND NOT A STUB. A commit that silently
    # failed would put the stage straight back in the state this leg exists to leave: a gate reading
    # an empty index and a required check scanning nothing, under the word GREEN. So the target is
    # given a .git that is a FILE, which real git refuses, while init still lays the repository down
    # happily - so the failure is attributable to the commit alone and carries its own name.
    with tempfile.TemporaryDirectory() as d:
        pub = Path(d) / "public"
        proc = IAR.compose(pub, ROOT)
        pack = pub / "packs" / IAR.composed_packs(pub)[0]
        broken = Path(d) / "fresh-commit"
        broken.mkdir(parents=True)
        (broken / ".git").write_text("not a git directory at all\n")
        res3 = IAR.install_and_run(pack, broken)
        expect("VELDO-0007 AC3 THE COMMIT'S OWN TEETH: with real git unable to commit the scaffolded "
               "tree, init still SUCCEEDS and lays the repository down, and the stage fails BY ITS "
               "OWN NAME (COMMIT_FAILED) instead of running a gate over an empty index. Driven "
               "against real git rather than a stub, because a stubbed commit proves the stub. What "
               "it said: %r" % (res3["commit_tail"][:120],),
               res3["init_returncode"] == 0 and res3["files_created"] > 10
               and res3["failure"] == IAR.FAIL_COMMIT
               and res3["commit_returncode"] not in (0, None)
               and res3["tracked_files"] is None
               and res3["gate_returncode"] is None)
        expect("VELDO-0007 AC3: a COMMIT_FAILED result QUOTES what git said, on the stage's own "
               "reported lines, because a stage that refuses without a reason sends nobody anywhere",
               res3["commit_tail"]
               and any("could NOT be committed" in ln and res3["commit_tail"].splitlines()[0] in ln
                       for ln in IAR.report_lines(
                           {"composed": [res3["pack"]], "installed": [res3["pack"]],
                            "results": [res3], "failure": res3["failure"], "note": None})))
    # ADDITIVE CONTROL for the two rows above: the same real path over an UNBROKEN target commits,
    # so COMMIT_FAILED is a measurement of a broken commit rather than a name this stage always
    # reaches. Asserted against the shared run, whose every result committed.
    expect("VELDO-0007 AC3 NEGATIVE CONTROL for the commit leg: over the shared run, every pack's "
           "target committed cleanly and NONE of them reported COMMIT_FAILED, so the refusal above "
           "measures the broken target rather than firing always",
           _IAR_REP["results"]
           and all(r["failure"] != IAR.FAIL_COMMIT for r in _IAR_REP["results"])
           and all(r["commit_returncode"] == 0 for r in _IAR_REP["results"]))


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
        # WHAT THIS ROW MEASURES, STATED EXACTLY, because the sentence it used to carry outran it.
        # It said "a sweep of runs cannot fill the disk". It observes a run that RETURNS: the rmtree
        # sits in a `finally`, which a killed process never reaches, and a review found 302MB of
        # leftover trees on this machine whose timestamps matched three earlier interrupted runs.
        # That is a real limit of the cleanup and it is NOT a defect this row can see, so the row now
        # claims the property it actually drives and names the one it does not. The scope stays the
        # directory this row created: the machine's /tmp is live state nobody owns and pinning it
        # empty would red on somebody else's leftovers.
        expect("VELDO-0007 AC4: the temporary directory is REMOVED BY A RUN THAT RETURNS - the "
               "TMPDIR handed to that run holds no veldo-install-and-run-* tree once it came back, "
               "and the run demonstrably did the work. THE LIMIT IS NAMED RATHER THAN CLAIMED AWAY: "
               "the removal is in a `finally`, so a KILLED process leaves its tree behind and this "
               "row cannot see that - a review found 302MB of leftovers matching three interrupted "
               "runs. Asserted over the directory this row created, never over the machine's /tmp, "
               "which is live state nobody owns",
               [p.name for p in run_tmp.glob("veldo-install-and-run-*")] == []
               and "install-and-run: pass" in proc.stdout)
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
           not (names & _IAR_NETWORK)
           and "mkdtemp" in names and "rmtree" in names)

    # AND THE SAME QUESTION ASKED OF THE CHILDREN, because a scan of ONE file says nothing about what
    # that file launches. This stage starts exactly two kinds of child with an interpreter or a
    # shell - the real publisher, and the pack's copy of the adopter gate - plus git. A review checked
    # both by hand and reported the gap: the file used to inject VELDO_NO_NETWORK=1 into every child,
    # which read as a kill-switch and was read by NOTHING in this repository, so the property rested
    # on a scan of one file and a hand check nobody would repeat. The flag is gone and the children
    # are scanned instead: an inert control is worse than none, because it stops the reader looking.
    _iar_pub_names = set()
    for node in _iar_ast.walk(_iar_ast.parse((ROOT / "scripts" / "publish.py").read_text())):
        if isinstance(node, _iar_ast.Attribute):
            _iar_pub_names.add(node.attr)
        elif isinstance(node, _iar_ast.Name):
            _iar_pub_names.add(node.id)
    expect("VELDO-0007 AC4 THE PUBLISHER, THE CHILD THIS STAGE LAUNCHES FIRST, MAKES NO NETWORK "
           "CALL EITHER - the same AST identifier set asked of scripts/publish.py, whose own "
           "contract is that producing a public tree and publishing it are two acts. Found by a "
           "review: the no-network property was asserted over ONE file and the file it runs was "
           "checked only by hand. Identifiers that would have failed: %r"
           % (sorted(_iar_pub_names & _IAR_NETWORK),),
           not (_iar_pub_names & _IAR_NETWORK))
    _iar_gate_src = (ROOT / "engine" / "scripts" / "verify.sh").read_text()
    _iar_gate_hits = sorted(t for t in _IAR_NET_CMDS if _iar_re.search(t, _iar_gate_src))
    expect("VELDO-0007 AC4 AND THE NESTED GATE - the shipped scripts/verify.sh, which is what the "
           "pack's copy is a byte-for-byte descendant of - reaches no network either: no curl, wget, "
           "nc, ssh, scp, pip or npm, and no git subcommand that talks to a remote (push, fetch, "
           "pull, clone, ls-remote). A shell script has no AST, so this is a token scan and it says "
           "so. Hits: %r" % (_iar_gate_hits,),
           _iar_gate_hits == [] and "CHECK_" in _iar_gate_src)
    # THE CONTROL ADDS THE THING AND REQUIRES IT FOUND, rather than removing something and watching
    # a row stay green: a scan that never fires reports the same empty answer as a clean file.
    _iar_ctrl_names = set()
    for node in _iar_ast.walk(_iar_ast.parse("urlopen('x')\nsocket.socket()\nrequests.get('y')\n")):
        if isinstance(node, _iar_ast.Attribute):
            _iar_ctrl_names.add(node.attr)
        elif isinstance(node, _iar_ast.Name):
            _iar_ctrl_names.add(node.id)
    _iar_ctrl_cmds = sorted(t for t in _IAR_NET_CMDS if _iar_re.search(
        t, "curl -s http://x\ngit push origin main\npip install veldo\n"))
    expect("VELDO-0007 AC4 NEGATIVE CONTROL for the two rows above, ADDITIVE: source carrying "
           "urlopen, socket and requests is DETECTED by the same identifier set, and a script "
           "carrying curl, `git push` and `pip install` is DETECTED by the same token set - so the "
           "empty answers above are measurements and not a scan that cannot fire. Found in the "
           "control: %r and %r" % (sorted(_iar_ctrl_names & _IAR_NETWORK), _iar_ctrl_cmds),
           len(_iar_ctrl_names & _IAR_NETWORK) >= 3 and len(_iar_ctrl_cmds) >= 3)
    # ASKED OF THE CODE AND NOT OF THE PROSE. The docstring explains why the flag is gone and must be
    # free to say so, which a substring scan over the file cannot allow: string CONSTANTS the module
    # would hand a child are the subject, docstrings excluded by identity.
    # clean=False, because get_docstring's default DEDENTS what it returns and the raw Constant it
    # came from would then not compare equal - the exclusion would silently exclude nothing.
    _iar_docs = {_iar_ast.get_docstring(n, clean=False)
                 for n in _iar_ast.walk(_iar_mod)
                 if isinstance(n, (_iar_ast.Module, _iar_ast.FunctionDef, _iar_ast.ClassDef))}
    def _iar_env_tokens(tree, docs=()):
        """Every spelling a module could name an environment variable by, EXCEPT its prose.

        String constants AND call keyword names, because the shape this row exists to refuse was
        `dict(os.environ, VELDO_NO_NETWORK="1")` - a KEYWORD, where the flag is an identifier and
        never a string. A constant-only scan reported clean over exactly that line, which is the
        same blind spot start_new_session=True walked through two rows above."""
        out = {n.value for n in _iar_ast.walk(tree)
               if isinstance(n, _iar_ast.Constant) and isinstance(n.value, str)}
        out -= set(docs)
        out |= {k.arg for n in _iar_ast.walk(tree) if isinstance(n, _iar_ast.Call)
                for k in n.keywords if k.arg}
        return out

    _iar_env = _iar_env_tokens(_iar_mod, _iar_docs)
    _iar_env_ctrl = _iar_env_tokens(_iar_ast.parse('dict(os.environ, VELDO_NO_NETWORK="1")'))
    expect("VELDO-0007 AC4 THE INERT CONTROL IS GONE: the module hands no child a VELDO_NO_NETWORK "
           "variable, because nothing in this repository ever read one - a control that appears to "
           "enforce and executes nothing is worse than no control, since it stops the reader looking, "
           "and the two rows above are what carries the property now. Asserted over string CONSTANTS "
           "AND CALL KEYWORD NAMES with docstrings excluded, so the file stays free to explain in "
           "prose why the flag went while the exact shape it had - a keyword, not a string - is still "
           "caught. The additive control carrying that line IS caught: %r"
           % (sorted(t for t in _iar_env_ctrl if "NETWORK" in t),),
           not any("VELDO_NO_NETWORK" in t for t in _iar_env)
           and bool(_iar_env)
           and any("VELDO_NO_NETWORK" in t for t in _iar_env_ctrl))

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
# AC5. IT IS A REQUIRED CATALOG ITEM IN THIS REPOSITORY'S GATE. ONE GATE, NOT BOTH.
#
# FALSIFIED BY: declare the stage `na` in scripts/verify.sh, and the two rows below must go red.
#
# THE REGISTRATION HAS LANDED AND THIS BLOCK'S HEADER USED TO DENY IT. It said the criterion "REPORTS
# until the registration lands and REFUSES after", which was true while the protected-path edit waited
# for approval and false from the moment Dmitry approved it on 2026-08-12: the slot is `required:` and
# the reporting branch is gone on purpose, because DRIVING showed a posture derived from the live gate
# passes both branches when the registration is removed entirely. A posture cannot catch its own
# removal.
#
# ONE GATE, NOT BOTH, and this repository's own capability-honesty check is what corrected it: the
# script does not ship to an adopter and an adopter does not publish packs, so a required slot in the
# shipped template would be a check they cannot run. THE TEMPLATE MAY STILL NAME IT: what is refused
# there is a REGISTRATION, not a mention, and `scope: repo-only` in the shipped capability manifest is
# what keeps the mention honest.
# ---------------------------------------------------------------------------------------

_IAR_STAGE = "scripts/check_install_and_run.py"
_IAR_GATES = ("scripts/verify.sh",)
# BY ITS COMMAND, not by a slot name. It landed in the EXISTING packaging slot - composing the
# published packs and proving an adopter can install and run them IS packaging verification - so
# asserting a slot name would pin a catalog vocabulary this item never added.
_IAR_DECLARED = {g: (_IAR_STAGE in (ROOT / g).read_text()) for g in _IAR_GATES}


def _iar_required_in(text):
    """The `required:` slots naming this stage, as a set of the lines that do the requiring.

    ONE definition, asked of this repository's gate and of the SHIPPED TEMPLATE, because the two
    questions must be the same question. A slot is a REGISTRATION; a reason string and a comment are
    not, which is the distinction the shipped-template row below rests on."""
    return sorted(ln.strip() for ln in text.splitlines()
                  if ln.strip().startswith("CHECK_") and '="required:' in ln and _IAR_STAGE in ln)


_IAR_REQUIRED = {g: bool(_iar_required_in((ROOT / g).read_text())) for g in _IAR_GATES}
_IAR_REGISTERED = all(_IAR_REQUIRED.values())
_IAR_SHIPPED_GATE = (ROOT / "engine/scripts/verify.sh").read_text()
_IAR_SHIPPED_CAPS = (ROOT / "engine/.veldo/capabilities.yaml").read_text()


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
    # WHAT THE SHIPPED TEMPLATE MUST NOT DO IS REQUIRE IT, NOT MENTION IT. This row asserted that the
    # string is ABSENT from engine/scripts/verify.sh, and a review measured the consequence: writing
    # the TRUE reason into the template's `na:` slot - the natural place to record why the slot does
    # not apply to an adopter - reddened this repository's gate. "Mentioning equals requiring" is the
    # right rule for THIS repository's gate, where a slot is the registration; in the shipped template
    # a reason string is documentation and a comment is not a registration. So the subject is the set
    # of `required:` slots naming this stage, which is a DEFECT SET BY CONSTRUCTION - a required check
    # an adopter cannot possibly run - and may be required empty forever. The template growing new
    # slots, or documenting this one, adds nothing to it.
    expect("VELDO-0007 AC5: the shipped template REQUIRES no check an adopter cannot run - no "
           "`required:` slot in engine/scripts/verify.sh names %s, which does not ship to an adopter "
           "and which an adopter has no packs to publish. THE SET IS A DEFECT SET, not live state: a "
           "required slot naming a repo-only script is wrong by construction, so it may be required "
           "empty forever, while DOCUMENTING the exclusion in an `na:` reason is now free - and it "
           "was not, which is how recording the true reason reddened this gate. Required slots "
           "naming it in the template: %r" % (_IAR_STAGE, _iar_required_in(_IAR_SHIPPED_GATE)),
           _iar_required_in(_IAR_SHIPPED_GATE) == []
           and "CHECK_packaging=" in _IAR_SHIPPED_GATE)
    # THE CONTROL APPENDS AND ASSERTS THE ADDITION APPLIED. The first version REPLACED a literal
    # slot line from the template, and driving found it emptied silently: documenting the exclusion
    # changes that line, the replace matched nothing, the control found nothing and the row went red
    # for a reason that had nothing to do with the property. A control derived by regexing another
    # file for a literal is a control that other file can delete.
    _iar_ctrl_gate = _IAR_SHIPPED_GATE + '\nCHECK_probe="required:python3 %s"\n' % _IAR_STAGE
    expect("VELDO-0007 AC5 NEGATIVE CONTROL, ADDITIVE: the same reader DOES find a required slot "
           "when one is ADDED to the template text - so the empty answer above is a measurement and "
           "not a reader that cannot fire. Additive by construction and the addition is asserted to "
           "have applied, because a control that edits a literal another file owns is emptied the "
           "moment that file is edited. Found in the control: %r"
           % (_iar_required_in(_iar_ctrl_gate),),
           len(_iar_ctrl_gate) > len(_IAR_SHIPPED_GATE)
           and _iar_required_in(_iar_ctrl_gate) != []
           and _iar_required_in(_IAR_SHIPPED_GATE) == [])
    # AND THE SHIPPED MANIFEST IS WHAT KEEPS THE NAMING HONEST, which nothing asserted. The template
    # DOES carry this script's path: engine/.veldo/capabilities.yaml declares it as a home, and the
    # scaffolder lays that manifest into every adopter tree as .veldo/capabilities.yaml where the file
    # named does not exist. `scope: repo-only` is the marker that makes that a correct declaration
    # rather than a broken one, and a review found no row reading it.
    _iar_caps_entry = [ln for ln in _IAR_SHIPPED_CAPS.splitlines()
                       if ln.strip().startswith("install_and_run_smoke:")]
    expect("VELDO-0007 AC5: the SHIPPED capability manifest marks this stage `scope: repo-only`, and "
           "that marker is load-bearing: engine/.veldo/capabilities.yaml declares home: %s and the "
           "scaffolder lays that manifest into every adopter tree, where the named file does not "
           "exist. Without the scope marker the shipped manifest would be claiming a home an adopter "
           "does not have. Entry found: %d" % (_IAR_STAGE, len(_iar_caps_entry)),
           len(_iar_caps_entry) == 1
           and "scope: repo-only" in _iar_caps_entry[0]
           and "home: %s" % _IAR_STAGE in _iar_caps_entry[0])
    expect("VELDO-0007 AC5 NEGATIVE CONTROL for the scope marker: `scope: repo-only` is NOT what "
           "every entry in that manifest carries - other capabilities declare homes that do ship - so "
           "reading it on this one is a measurement of this declaration rather than of the file's "
           "house style",
           any(ln.strip().startswith(("behaviour_floor_contract:", "release_contract_registry:"))
               and "scope: repo-only" not in ln
               for ln in _IAR_SHIPPED_CAPS.splitlines()))
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
