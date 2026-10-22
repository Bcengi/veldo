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


def _w1712_review(repo, report, old_sources=None):
    """Independent-review regressions through real Git histories and the shipped CLI."""
    cases = [
        ("R1 manifest relabeled", False, True),
        ("R1 manifest deleted", False, True),
        ("R1 spec deleted", False, True),
        ("R1 requirements emptied", False, True),
        ("R1 requirements reduced", False, True),
        ("R1 both ids relabeled", False, True),
        ("R1 spec renamed", False, False),
        ("R1 proof moved", False, False),
        ("R1 real payoff", True, False),
        ("R2 feature upstream touch", False, True),
        ("R2 feature upstream growth", False, True),
        ("R2 explicit policy base", False, False),
        ("R2 invalid policy base", False, False),
        ("R3 vendored unchanged", True, True),
        ("R3 vendored adoption touch", False, True),
        ("R3 vendored payoff", True, True),
        ("R4 moved trunk", True, True),
        ("R4 moved trunk register", True, True),
        ("R5 nonzero exit", False, True),
        ("R5 expected nonzero exit", False, True),
        ("R5 boolean exit", False, True),
        ("R5 zero without outcome", False, False),
        ("R5 zero exit", True, False),
    ]
    for label, passes, old_fails in cases:
        with tempfile.TemporaryDirectory(prefix="warp1712-review-") as directory:
            host = Path(directory)
            root = host / "vendor/v" if label.startswith("R3") else host
            root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(repo / "engine/.veldo", root / ".veldo",
                            ignore=shutil.ignore_patterns("__pycache__", "decision_reviews"))
            for name, source in (old_sources or {}).items():
                (root / ".veldo" / name).write_text(source)
            spec = root / "specs/WARP-1712.md"
            spec.parent.mkdir()
            original_spec = (
                "---\nschema: veldo.spec/v1\nid: WARP-1712\ntitle: Fixture\nstatus: ready\n"
                "risk: standard\nowner: dmitry\nlane: standalone\nacceptance_criteria:\n  - id: AC1\n"
                "    text: Passing evidence.\nrequired_evidence: [unit, integration]\n---\n")
            spec.write_text(original_spec)
            proof = root / "proof/WARP-1712/manifest.json"
            proof.parent.mkdir(parents=True)
            data = {"schema": "veldo.proof/v1", "spec_id": "WARP-1712", "commit": "deadbeef",
                    "producer": "fixture", "rollback": "revert",
                    "criteria": [{"id": "AC1", "status": "passed",
                                  "evidence": [{"type": "unit", "status": "passed"}]}],
                    "checks": [{"name": "unit", "status": "passed"}]}
            proof.write_text(json.dumps(data))

            def git(*args):
                return subprocess.check_output(
                    ["git", "-c", "user.name=Dmitry Grinberg", "-c", "user.email=dmitry@bcengi.com",
                     *args], cwd=host, text=True, stderr=subprocess.STDOUT).strip()

            def commit():
                git("add", ".")
                git("commit", "-qm", "fixture")
                return git("rev-parse", "HEAD")

            def cli(mode="all"):
                return subprocess.run([sys.executable, str(root / ".veldo/validate.py"), mode],
                                      cwd=root, text=True, capture_output=True)

            def regenerate():
                run = cli("evidence-debt")
                assert run.returncode == 0, run.stdout + run.stderr
                register.write_text(run.stdout)

            register = root / ".veldo/required-evidence-debt.jsonl"
            git("init", "-q")
            if label != "R3 vendored adoption touch":
                regenerate()
            base = commit()
            git("update-ref", "refs/remotes/origin/main", base)
            if label == "R1 manifest relabeled":
                data["spec_id"] += "-retired"
                proof.write_text(json.dumps(data))
            elif label == "R1 manifest deleted":
                proof.unlink()
            elif label == "R1 spec deleted":
                spec.unlink()
            elif label in ("R1 requirements emptied", "R1 requirements reduced"):
                spec.write_text(original_spec.replace("[unit, integration]",
                                "[]" if label.endswith("emptied") else "[unit]"))
            elif label == "R1 both ids relabeled":
                spec.write_text(original_spec.replace("id: WARP-1712", "id: WARP-1713"))
                data["spec_id"] = "WARP-1713"
                data["checks"].append({"name": "integration", "status": "passed"})
                proof.write_text(json.dumps(data))
            elif label == "R1 spec renamed":
                spec.rename(spec.with_name("WARP-1712-renamed.md"))
            elif label == "R1 proof moved":
                proof.parent.rename(proof.parent.with_name("WARP-1712-moved"))
            elif label in ("R1 real payoff", "R3 vendored payoff"):
                data["checks"].append({"name": "integration", "status": "passed", "exit_code": 0})
                proof.write_text(json.dumps(data))
            elif label.startswith("R2"):
                if label.endswith("growth"):
                    other_spec = spec.with_name("WARP-1713.md")
                    other_spec.write_text(original_spec.replace("WARP-1712", "WARP-1713"))
                    other_proof = proof.parent.with_name("WARP-1713") / "manifest.json"
                    other_proof.parent.mkdir()
                    other_proof.write_text(json.dumps(dict(data, spec_id="WARP-1713")))
                else:
                    spec.write_text(original_spec + "Touched before the earlier feature push.\n")
                regenerate()
                earlier = commit()
                git("update-ref", "refs/remotes/origin/feature", earlier)
                branch = git("symbolic-ref", "--short", "HEAD")
                git("config", "branch." + branch + ".remote", "origin")
                git("config", "branch." + branch + ".merge", "refs/heads/feature")
                git("config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
                if "policy base" in label:
                    git("update-ref", "refs/remotes/origin/main", earlier)
            elif label == "R3 vendored adoption touch":
                spec.write_text(original_spec + "Touched during adoption.\n")
                (proof.parent / "artifact.txt").write_text("Also touched.\n")
            elif label.startswith("R4"):
                (proof.parent / "mainnote.txt").write_text("Only trunk touched this pair.\n")
                if label.endswith("register"):
                    data["checks"].append({"name": "integration", "status": "passed"})
                    proof.write_text(json.dumps(data))
                    regenerate()
                trunk = commit()
                git("update-ref", "refs/remotes/origin/main", trunk)
                git("reset", "--hard", base)
            elif label.startswith("R5"):
                check = {"name": "integration", "status": "passed", "exit_code": 0}
                if label == "R5 nonzero exit":
                    check["exit_code"] = 1
                elif label == "R5 expected nonzero exit":
                    check.update(exit_code=1, expected_exit=1)
                elif label == "R5 boolean exit":
                    check["exit_code"] = False
                elif label == "R5 zero without outcome":
                    check.pop("status")
                data["checks"].append(check)
                proof.write_text(json.dumps(data))
            regenerate()
            (root / "README.md").write_text("Unrelated followup.\n")
            commit()
            if "policy base" in label:
                policy_path = root / ".veldo/policy_check.py"
                policy_path.write_text(policy_path.read_text().replace(
                    "BASE = None", "BASE = " + repr("absent-trunk" if "invalid" in label else base)))
            run = cli()
            output = run.stdout + run.stderr
            ok = run.returncode == (0 if passes else 1)
            if not passes:
                diagnostic = ("new required-evidence debt forbidden" if label in ("R1 spec renamed", "R1 proof moved")
                              else "historical pair requires passing evidence" if label.startswith("R1")
                              else "new required-evidence debt forbidden" if label.endswith("growth")
                              else "no exemption granted" if "invalid policy" in label
                              else "touched pair requires passing evidence")
                ok = ok and diagnostic in output
            report("review " + label + ("\n" + output if not ok else ""), ok, old_fails)


def _w1712_authority(repo, report, mutable_base=False):
    """The real installed verifier runs a ref-moving candidate stage before contracts."""
    import re
    with tempfile.TemporaryDirectory(prefix="warp1712-authority-") as directory:
        host = Path(directory)
        root, authority = host / "candidate", host / "authority"
        root.mkdir()
        shutil.copytree(repo / "engine/.veldo", root / ".veldo",
                        ignore=shutil.ignore_patterns("__pycache__", "decision_reviews"))
        shutil.copytree(repo / "engine/.veldo", authority / ".veldo",
                        ignore=shutil.ignore_patterns("__pycache__", "decision_reviews"))
        shutil.copytree(repo / "scripts", authority / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        # Only the catalog is fixture-specific. All built-in contracts and the launcher remain real.
        gate = (repo / "scripts/verify.sh").read_text()
        gate = re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$',
                      lambda m: ('CHECK_unit="required:python3 move_refs.py"' if m[1] == "unit"
                                 else 'CHECK_%s="na:fixture"' % m[1]), gate)
        (authority / "scripts/verify.sh").write_text(gate)
        (authority / "scripts/gate_unconfined.json").write_text(json.dumps({
            "schema": "veldo.gate-unconfined/v1", "authority": "D1 fixture candidate stage",
            "stages": {"unit": "python3 move_refs.py"},
            "suites": [{"suite": "move_refs", "reason": "Exercise writable candidate refs"}]}))
        loader = importlib.util.spec_from_file_location("w1712_authority", authority / ".veldo/control_verification.py")
        cv = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(cv)

        def git(*args):
            return subprocess.check_output(
                ["git", "-c", "user.name=Dmitry Grinberg", "-c", "user.email=dmitry@bcengi.com",
                 *args], cwd=root, text=True, stderr=subprocess.STDOUT).strip()

        def commit():
            git("add", ".")
            git("commit", "-qm", "fixture")
            return git("rev-parse", "HEAD")

        def regenerate():
            run = subprocess.run([sys.executable, ".veldo/validate.py", "evidence-debt"],
                                 cwd=root, text=True, capture_output=True)
            assert run.returncode == 0, run.stdout + run.stderr
            (root / ".veldo/required-evidence-debt.jsonl").write_text(run.stdout)

        def pair(sid):
            spec = root / ("specs/" + sid + ".md")
            spec.parent.mkdir(exist_ok=True)
            spec.write_text("---\nschema: veldo.spec/v1\nid: " + sid + "\ntitle: Fixture\n"
                            "status: ready\nrisk: standard\nowner: dmitry\nlane: standalone\n"
                            "acceptance_criteria:\n  - id: AC1\n    text: Passing integration.\n"
                            "required_evidence: [integration]\n---\n")
            proof = root / ("proof/" + sid + "/manifest.json")
            proof.parent.mkdir(parents=True)
            proof.write_text(json.dumps({"schema": "veldo.proof/v1", "spec_id": sid,
                "commit": "deadbeef", "producer": "fixture", "rollback": "revert", "checks": [],
                "criteria": [{"id": "AC1", "status": "passed",
                              "evidence": [{"type": "unit", "status": "passed"}]}]}))
            return spec

        git("init", "-q")
        # Debt-free candidates also require a gate base.
        (root / "move_refs.py").write_text("print('candidate stage ran')\n")
        commit()
        (authority / ".veldo/authority_git_common").write_text(str(root / ".git") + "\n")
        for label, base, diagnostic in (("missing base debt-free", None, "policy_base/invalid"),
                                         ("invalid base", "origin/main", "policy_base/invalid"),
                                         ("absent base", "f" * 40, "policy_base/absent")):
            observed, _ = cv.observe_gate(root, authority, host / label.replace(" ", "-"),
                                          bind_refs=False, base=base)
            output = observed["stdout"] + observed["stderr"]
            ok = observed["exit"] == 1 and diagnostic in output and "GATE: RED" in output
            report("D1 " + label + ("\n" + output if not ok else ""), ok)
        # The ratchet itself refuses a missing authority base before adoption-safe stand-down.
        debt = cv._sibling("w1712_debt_guard", "evidence_debt.py")
        import types
        messages = []
        validator = types.SimpleNamespace(fail=lambda path, message: messages.append(message) or 1)
        refused = debt.validate(validator, root, [], gate=True)
        report("D1 ratchet refuses missing gate BASE", refused == 1 and
               messages == ["gate requires authority BASE; no exemption granted"])
        historical = pair("WARP-1712")
        regenerate()
        watermark = commit()
        git("update-ref", "refs/remotes/origin/main", watermark)
        git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        observed, _ = cv.observe_gate(root, authority, host / "unchanged", bind_refs=False, base=watermark)
        output = observed["stdout"] + observed["stderr"]
        ok = observed["green"] and "contracts: pass" in output
        report("D1 unchanged historical debt passes" + ("\n" + output if not ok else ""), ok)
        historical.write_text(historical.read_text() + "Touched historical spec.\n")
        pair("WARP-1713")
        regenerate()
        (root / "move_refs.py").write_text(
            "import os, subprocess\n"
            "if os.environ.get('VELDO_GATE_LEG') == 'confined': raise SystemExit(0)\n"
            "for ref in ('refs/remotes/origin/main', 'refs/remotes/origin/HEAD'):\n"
            "    subprocess.run(['git', 'update-ref', '--no-deref', ref, 'HEAD'], check=True)\n"
            "print('candidate moved both origin refs to HEAD')\n")
        head = commit()
        if mutable_base:
            # The D1 behavior: discard the supplied watermark at contracts time.
            gate = gate.replace('contracts "$(pwd -P)" "$VELDO_BASE"',
                                'contracts "$(pwd -P)" "$(git rev-parse origin/main)"')
            (authority / "scripts/verify.sh").write_text(gate)
        observed, _ = cv.observe_gate(root, authority, host / "attack", bind_refs=False, base=watermark)
        output = observed["stdout"] + observed["stderr"]
        moved = all(git("rev-parse", ref) == head for ref in ("origin/main", "origin/HEAD"))
        ok = (moved and "candidate moved both origin refs to HEAD" in output
              and output.index("candidate moved both") < output.index("== veldo contracts")
              and "touched pair requires passing evidence" in output
              and "new required-evidence debt forbidden" in output
              and "contracts: FAIL" in output and "GATE: RED" in output
              and observed["exit"] == 1 and not observed["green"])
        report("D1 candidate moves both refs before contracts" + ("\n" + output if not ok else ""), ok, True)


for _w1712_relative in ("engine/.veldo/validate.py", ".veldo/validate.py"):
    _w1712_loader = importlib.util.spec_from_file_location("w1712_validator", ROOT / _w1712_relative)
    _w1712_validator = importlib.util.module_from_spec(_w1712_loader)
    _w1712_loader.loader.exec_module(_w1712_validator)
    _w1712_exercise(_w1712_validator, lambda label, ok, old_refusal:
                   expect("WARP-1712 " + _w1712_relative + ": " + label, ok))
_w1712_cli(ROOT, lambda label, ok, old_refusal: expect("WARP-1712 " + label, ok))

_w1712_ratchet(ROOT, lambda label, ok, old_refusal: expect("WARP-1712 " + label, ok))

_w1712_review(ROOT, lambda label, ok, old_refusal: expect("WARP-1712 " + label, ok))

_w1712_authority(ROOT, lambda label, ok, old_refusal=False: expect("WARP-1712 " + label, ok))
