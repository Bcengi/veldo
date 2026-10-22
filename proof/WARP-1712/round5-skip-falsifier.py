"""Sandbox-independent WARP-1712 round 5 falsifier: candidate skips its ratchet; authority still refuses."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
def run(cmd, cwd, check=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode: raise SystemExit(r.stdout + r.stderr)
    return r
with tempfile.TemporaryDirectory() as t:
    root = Path(t) / "candidate"; auth = Path(t) / "authority"; root.mkdir()
    ig = shutil.ignore_patterns("__pycache__", "decision_reviews")
    shutil.copytree(repo / "engine/.veldo", root / ".veldo", ignore=ig)
    shutil.copytree(repo / "engine/.veldo", auth / ".veldo", ignore=ig)
    g = lambda *a: run(["git", "-c", "user.name=f", "-c", "user.email=f@x", *a], root).stdout.strip()
    def pair(sid):
        (root / "specs").mkdir(exist_ok=True)
        s = root / ("specs/%s.md" % sid)
        s.write_text("---\nschema: veldo.spec/v1\nid: %s\ntitle: Fixture\nstatus: ready\nrisk: standard\n"
                     "owner: dmitry\nlane: standalone\nacceptance_criteria:\n  - id: AC1\n    text: Passing integration.\n"
                     "required_evidence: [integration]\n---\n" % sid)
        p = root / ("proof/%s/manifest.json" % sid); p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"schema": "veldo.proof/v1", "spec_id": sid, "commit": "deadbeef", "producer": "f",
            "rollback": "revert", "checks": [], "criteria": [{"id": "AC1", "status": "passed",
            "evidence": [{"type": "unit", "status": "passed"}]}]}))
        return s
    def regen():
        (root / ".veldo/required-evidence-debt.jsonl").write_text(
            run([sys.executable, ".veldo/validate.py", "evidence-debt"], root).stdout)
    def commit():
        g("add", "."); g("commit", "-qm", "f"); return g("rev-parse", "HEAD")
    g("init", "-q"); spec = pair("WARP-1712"); regen(); water = commit()
    spec.write_text(spec.read_text() + "touched\n"); pair("WARP-1713"); regen()
    v = root / ".veldo/validate.py"; src = v.read_text()
    call = "    errs += evidence_debt_module().validate(evidence_validator(), ROOT, evidence_pairs)\n"
    assert call in src
    v.write_text(src.replace(call, "    pass  # ratchet skipped by the candidate\n"))
    head = commit()
    for ref in ("refs/remotes/origin/main", "refs/remotes/origin/HEAD"):
        g("update-ref", "--no-deref", ref, head)
    cand = run([sys.executable, ".veldo/validate.py", "all"], root, check=False)
    rat = run([sys.executable, "-I", "-S", str(auth / ".veldo/control_verification.py"), "ratchet", str(root), water], root, check=False)
    out = rat.stdout + rat.stderr
    print("candidate validate.py all exit", cand.returncode)
    print("authority ratchet exit", rat.returncode); print(out)
    ok = (cand.returncode == 0 and rat.returncode == 1 and "touched pair requires passing evidence" in out
          and "new required-evidence debt forbidden" in out)
    print("SKIP FALSIFIER:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
