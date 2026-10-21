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
        shutil.copytree(repo / "engine/.veldo", root / ".veldo", ignore=shutil.ignore_patterns("__pycache__"))
        if validator_source is not None:
            (root / ".veldo/validate.py").write_text(validator_source)
        (root / "specs").mkdir()
        (root / "specs/WARP-1712.md").write_text(
            "---\nschema: veldo.spec/v1\nid: WARP-1712\ntitle: Fixture\nstatus: ready\n"
            "risk: standard\nowner: dmitry\nacceptance_criteria:\n  - id: AC1\n"
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


for _w1712_relative in ("engine/.veldo/validate.py", ".veldo/validate.py"):
    _w1712_loader = importlib.util.spec_from_file_location("w1712_validator", ROOT / _w1712_relative)
    _w1712_validator = importlib.util.module_from_spec(_w1712_loader)
    _w1712_loader.loader.exec_module(_w1712_validator)
    _w1712_exercise(_w1712_validator, lambda label, ok, old_refusal:
                   expect("WARP-1712 " + _w1712_relative + ": " + label, ok))
_w1712_cli(ROOT, lambda label, ok, old_refusal: expect("WARP-1712 " + label, ok))
