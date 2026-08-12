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


# ONE full run, shared by the rows below, because composing and installing seven packs is the
# expensive part and doing it per row would multiply the cost with no gain in teeth.
_IAR_OK, _IAR_REP = IAR.check()
_IAR_LINES = IAR.report_lines(_IAR_REP)


# ---------------------------------------------------------------------------------------
# AC1. IT INSTALLS FROM THE COMPOSED PACK, NOT FROM THIS REPOSITORY.
#
# FALSIFIED BY: point the installer at this repository's own scaffolder, and the row below
# (no engine/ in the tree it ran from) must go red.
# ---------------------------------------------------------------------------------------


def _iar_ac1():
    expect("VELDO-0007 AC1: every install ran from a tree with NO engine/ directory - the COMPOSED "
           "PACK shape, where the base has been laid into the pack and the pack root IS the template "
           "source. That absence is the exact condition 1.0 broke on, and running from this "
           "repository (which HAS engine/) is what hid it, because every test ran against the one "
           "tree nobody installs",
           _IAR_REP["results"]
           and all(r["pack_has_engine_dir"] is False for r in _IAR_REP["results"]))
    expect("VELDO-0007 AC1: the scaffolder that ran is the PACK'S OWN copy, asserted by the path "
           "each result records - under the composed pack, never under this repository",
           all(r["installed_from"].endswith("/packs/" + r["pack"])
               for r in _IAR_REP["results"]))
    expect("VELDO-0007 AC1 NEGATIVE CONTROL: THIS repository does have engine/, so the property "
           "above is a real distinction rather than one that holds everywhere. Were the installer "
           "pointed here, the row above would red",
           (ROOT / "engine").is_dir())


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
# FALSIFIED BY: write anywhere outside the temporary directory, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _iar_ac4():
    before = _iar_sp.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                         capture_output=True, text=True).stdout
    ok2, rep2 = IAR.check(only=_IAR_REP["composed"][0])
    after = _iar_sp.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                        capture_output=True, text=True).stdout
    expect("VELDO-0007 AC4: the repository's own tracked state is UNCHANGED across a full run - "
           "compose, install and a nested gate is a great deal of writing, and every byte of it "
           "lands under a temporary directory. A check that mutated the tree it is checking is the "
           "shape that makes a green gate meaningless",
           before == after and ok2 is True)
    expect("VELDO-0007 AC4: the temporary directory is REMOVED - the paths every result recorded no "
           "longer exist after the run returns, so a sweep of runs cannot fill the disk",
           all(not Path(r["installed_from"]).exists() for r in rep2["results"]))

    import ast as _iar_ast
    src = (ROOT / "scripts" / "check_install_and_run.py").read_text()
    names = set()
    for node in _iar_ast.walk(_iar_ast.parse(src)):
        if isinstance(node, _iar_ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, _iar_ast.Name):
            names.add(node.id)
    expect("VELDO-0007 AC4: it makes no network call and starts no detached process - no urlopen, "
           "no requests, no Popen, no fork, no daemon. AST identifiers rather than substrings, "
           "because prose describing what it refuses to do is prose",
           not (names & {"urlopen", "requests", "Popen", "fork", "daemon", "socket"})
           and "mkdtemp" in names and "rmtree" in names)


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
