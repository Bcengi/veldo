"""Required-kind/outcome matrix, shared with the recorded old-code falsifier driver."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def _w1712_exercise(validator, report):
    with tempfile.TemporaryDirectory(prefix="warp1712-") as directory:
        root = Path(directory)
        spec = root / "spec.md"
        proof = root / "proof" / "WARP-1712" / "manifest.json"
        proof.parent.mkdir(parents=True)

        def check(label, kind="integration", evidence=None, checks=None, passes=False,
                  old_refusal=False):
            spec.write_text("---\nrequired_evidence: [" + kind + "]\n---\n")
            proof.write_text(json.dumps({"criteria": [{"id": "AC1", "status": "passed",
                                                       "evidence": evidence or []}],
                                         "checks": checks or []}))
            with contextlib.redirect_stdout(io.StringIO()):
                actual = validator.check_required_evidence(spec, proof) == 0
            report(label, actual == passes, old_refusal)

        check("generic test is not integration", evidence=[{"type": "test", "status": "passed"}],
              old_refusal=True)
        check("unit is not integration", evidence=[{"type": "unit", "status": "passed"}])
        check("passing unit check is not integration", checks=[{"name": "unit", "status": "passed"}])
        check("empty proof refuses")
        check("unknown required kind refuses", kind="invented")

        outcomes = [{}, {"status": None}, {"status": "failed"}, {"status": "pending"},
                    {"status": "not_run"}, {"status": "pass"}, {"status": "PASSED"},
                    {"status": True}, {"status": "passed, 12 tests"}, {"result": "failed"},
                    {"result": "pending"}, {"result": "not run"}, {"result": "green"},
                    {"result": None}, {"status": "failed", "result": "pass"},
                    {"status": "passed", "result": "fail"}]
        for outcome in outcomes:
            suffix = json.dumps(outcome, sort_keys=True)
            check("evidence refuses " + suffix,
                  evidence=[dict(type="integration", **outcome)], old_refusal=True)
            check("check refuses " + suffix,
                  checks=[dict(name="integration", **outcome)], old_refusal=True)
        for outcome in ({"status": "passed"}, {"result": "pass"}, {"result": "passed"},
                        {"status": "passed", "result": "pass"}):
            suffix = json.dumps(outcome, sort_keys=True)
            check("passing evidence " + suffix, evidence=[dict(type="integration", **outcome)], passes=True)
            check("passing check " + suffix, checks=[dict(name="integration", **outcome)], passes=True)

        # This is an independently stated compatibility contract, not the implementation's table.
        aliases = {"unit": ("unit", "test"), "integration": ("integration",),
                   "journeys": ("journeys", "journey", "e2e"),
                   "ui_states": ("ui_states", "state_capture"),
                   "figma_composite": ("figma_composite", "composite", "visual"),
                   "interaction_recording": ("interaction_recording", "recording", "video"),
                   "baseline": ("baseline", "visual_baselines"),
                   "device_matrix": ("device_matrix", "matrix"),
                   "operational": ("operational",), "staging_run": ("staging_run", "staging")}
        for kind, names in aliases.items():
            for name in names:
                check("passing alias " + kind + "/" + name, kind=kind,
                      evidence=[{"type": name, "status": "passed"}], passes=True)
                check("absent outcome alias " + kind + "/" + name, kind=kind,
                      evidence=[{"type": name}], old_refusal=True)
        check("failed integration plus passed unit refuses",
              evidence=[{"type": "integration", "status": "failed"}, {"type": "test", "status": "passed"}],
              old_refusal=True)
        check("matching passing entry survives unrelated failure",
              evidence=[{"type": "integration", "status": "failed"},
                        {"type": "integration", "status": "passed"}], passes=True)
        check("a pass on another entry cannot bless missing integration outcome",
              evidence=[{"type": "integration"}, {"type": "unit", "status": "passed"}],
              old_refusal=True)
        check("every required kind needs a pass", kind="unit, integration",
              evidence=[{"type": "unit", "status": "passed"}, {"type": "integration"}],
              old_refusal=True)
        check("both required kinds passed", kind="unit, integration",
              evidence=[{"type": "unit", "status": "passed"}, {"type": "integration", "status": "passed"}],
              passes=True)
        check("no declared requirements is unchanged", kind="", passes=True)

        check("absent design verdict refuses", kind="design_review")
        review = proof.with_name("design-verdict.json")
        for verdict in ({}, {"verdict": "fail"}, {"verdict": "pending"},
                        {"verdict": "escalate"}, [], {"verdict": "passed"}):
            review.write_text(json.dumps(verdict))
            check("design verdict refuses " + json.dumps(verdict), kind="design_review", old_refusal=True)
        review.write_text("not json")
        check("unreadable design verdict refuses", kind="design_review", old_refusal=True)
        for verdict in ("pass", "pass_with_notes"):
            review.write_text(json.dumps({"verdict": verdict}))
            check("passing design verdict " + verdict, kind="design_review", passes=True)


def _w1712_cli(repo, report, validator_source=None):
    """Exercise run_all's spec/proof join through the shipped CLI in a temporary adopter."""
    with tempfile.TemporaryDirectory(prefix="warp1712-cli-") as directory:
        root = Path(directory)
        shutil.copytree(repo / "engine/.veldo", root / ".veldo",
                        ignore=shutil.ignore_patterns("__pycache__", "decision_reviews"))
        if validator_source is not None:
            (root / ".veldo/validate.py").write_text(validator_source)
        (root / "specs").mkdir()
        (root / "specs/WARP-1712.md").write_text(
            "---\nschema: veldo.spec/v1\nid: WARP-1712\ntitle: Fixture\nstatus: ready\n"
            "risk: standard\nowner: dmitry\nlane: standalone\nacceptance_criteria:\n  - id: AC1\n"
            "    text: A passing integration test.\nrequired_evidence: [integration]\n---\n")
        proof = root / "proof/WARP-1712/manifest.json"
        proof.parent.mkdir(parents=True)
        cases = [("integration passes", [{"type": "integration", "status": "passed"}], [], True),
                 ("generic test refuses", [{"type": "test", "status": "passed"}], [], False),
                 ("missing result refuses", [{"type": "integration"}], [], False),
                 ("failed result refuses", [{"type": "integration", "status": "failed"}], [], False),
                 ("pending result refuses", [{"type": "integration", "status": "pending"}], [], False),
                 ("bare check refuses", [{"type": "unit", "status": "passed"}], [{"name": "integration"}], False),
                 ("passing check passes", [{"type": "unit", "status": "passed"}],
                  [{"name": "integration", "status": "passed"}], True)]
        for label, evidence, checks, passes in cases:
            proof.write_text(json.dumps({"schema": "veldo.proof/v1", "spec_id": "WARP-1712",
                                         "commit": "deadbeef", "producer": "fixture", "rollback": "revert",
                                         "criteria": [{"id": "AC1", "status": "passed", "evidence": evidence}],
                                         "checks": checks}))
            run = subprocess.run([sys.executable, str(root / ".veldo/validate.py"), "all"],
                                 cwd=root, text=True, capture_output=True)
            output = run.stdout + run.stderr
            ok = run.returncode == (0 if passes else 1)
            if not passes:
                ok = ok and "required evidence kind 'integration'" in output
            report("CLI " + label + ("\n" + output if not ok else ""), ok, not passes)


def _w1712_ratchet(repo, report, debt_source=None):
    """Real commits and the shipped CLI: the register is never an exemption for a touch."""
    with tempfile.TemporaryDirectory(prefix="warp1712-ratchet-") as directory:
        root = Path(directory)
        shutil.copytree(repo / "engine/.veldo", root / ".veldo",
                        ignore=shutil.ignore_patterns("__pycache__", "decision_reviews"))
        if debt_source is not None:
            (root / ".veldo/evidence_debt.py").write_text(debt_source)
        (root / "specs").mkdir()
        spec = root / "specs/WARP-1712.md"
        spec.write_text(
            "---\nschema: veldo.spec/v1\nid: WARP-1712\ntitle: Fixture\nstatus: ready\n"
            "risk: standard\nowner: dmitry\nlane: standalone\nacceptance_criteria:\n  - id: AC1\n"
            "    text: A passing integration test.\nrequired_evidence: [integration]\n---\n")
        proof = root / "proof/WARP-1712/manifest.json"
        proof.parent.mkdir(parents=True)
        data = {"schema": "veldo.proof/v1", "spec_id": "WARP-1712", "commit": "deadbeef",
                "producer": "fixture", "rollback": "revert",
                "criteria": [{"id": "AC1", "status": "passed",
                              "evidence": [{"type": "integration"}]}], "checks": []}
        proof.write_text(json.dumps(data))

        def git(*args):
            return subprocess.check_output(
                ["git", "-c", "user.name=Dmitry Grinberg", "-c", "user.email=dmitry@bcengi.com",
                 *args], cwd=root, text=True, stderr=subprocess.STDOUT).strip()

        def commit():
            git("add", ".")
            git("commit", "-qm", "fixture")

        def base():
            git("update-ref", "refs/remotes/origin/main", "HEAD")

        def cli(mode="all"):
            return subprocess.run([sys.executable, str(root / ".veldo/validate.py"), mode],
                                  cwd=root, text=True, capture_output=True)

        def check(label, passes, diagnostic=None):
            run = cli()
            output = run.stdout + run.stderr
            ok = run.returncode == (0 if passes else 1)
            if diagnostic:
                ok = ok and diagnostic in output
            report("ratchet " + label + ("\n" + output if not ok else ""), ok, False)

        git("init", "-q")
        commit()
        base()
        register = root / ".veldo/required-evidence-debt.jsonl"
        generated = cli("evidence-debt")
        report("ratchet generator succeeds", generated.returncode == 0, False)
        original = generated.stdout
        report("ratchet one sorted pair with cause", len(original.splitlines()) == 1
               and "passing result" in original and "specs/WARP-1712.md" in original, False)
        check("unlisted unchanged failure refuses", False, "debt register differs")
        register.write_text(original)
        commit()
        check("untouched historical pair listed passes initial adoption", True)
        base()
        check("untouched historical pair listed passes established register", True)

        spec.write_text(spec.read_text() + "Touched spec.\n")
        commit()
        check("touched historical spec refuses", False, "touched pair requires passing evidence")
        (root / "README.md").write_text("An unrelated followup commit.\n")
        commit()
        check("earlier push commit still activates strict rule", False, "touched pair requires passing evidence")
        base()
        proof.write_text(proof.read_text() + "\n")
        commit()
        check("touched historical manifest refuses", False, "touched pair requires passing evidence")
        base()
        (proof.parent / "runner.txt").write_text("Changed proof artifact.\n")
        commit()
        check("touched historical proof artifact refuses", False, "touched pair requires passing evidence")
        base()
        (proof.parent / "design-verdict-note.txt").write_text("Changed design artifact.\n")
        commit()
        check("touched historical design artifact refuses", False, "touched pair requires passing evidence")
        base()

        row = json.loads(original)
        row["proof"] = "proof/WARP-9999/manifest.json"
        register.write_text(original + json.dumps(row, sort_keys=True) + "\n")
        commit()
        check("hand-added entry refuses", False, "debt register differs")
        register.write_text(original)
        commit()
        check("restored exact register passes", True)
        register.write_text(original + original)
        check("duplicate entry refuses", False, "debt register differs")
        row = json.loads(original)
        row["causes"] = ["hand-edited cause"]
        register.write_text(json.dumps(row, sort_keys=True) + "\n")
        check("hand-edited cause refuses", False, "debt register differs")
        register.write_text("")
        check("removed still-failing entry refuses", False, "debt register differs")
        register.write_text(original)

        data["criteria"][0]["evidence"][0]["status"] = "passed"
        proof.write_text(json.dumps(data))
        commit()
        check("now-passing listed entry refuses", False, "debt register differs")
        register.write_text(cli("evidence-debt").stdout)
        commit()
        check("passing entry removed passes", True)
        base()
        register.unlink()
        commit()
        check("empty adopted register cannot be deleted", False, "adopted debt register missing")
        register.write_text("")
        commit()
        check("retained empty register passes", True)
        base()
        data["criteria"][0]["evidence"][0].pop("status")
        proof.write_text(json.dumps(data))
        commit()
        # Advance the range to demonstrate that even an unchanged failure cannot be
        # laundered into an already-adopted register by running the generator again.
        base()
        check("new unchanged unlisted failure refuses", False, "new required-evidence debt forbidden")
        register.write_text(cli("evidence-debt").stdout)
        commit()
        check("computed new debt cannot grow register", False, "new required-evidence debt forbidden")


for _w1712_relative in ("engine/.veldo/validate.py", ".veldo/validate.py"):
    _w1712_loader = importlib.util.spec_from_file_location("w1712_validator", ROOT / _w1712_relative)
    _w1712_validator = importlib.util.module_from_spec(_w1712_loader)
    _w1712_loader.loader.exec_module(_w1712_validator)
    _w1712_exercise(_w1712_validator, lambda label, ok, old_refusal:
                   expect("WARP-1712 " + _w1712_relative + ": " + label, ok))
_w1712_cli(ROOT, lambda label, ok, old_refusal: expect("WARP-1712 " + label, ok))

_w1712_ratchet(ROOT, lambda label, ok, old_refusal: expect("WARP-1712 " + label, ok))
