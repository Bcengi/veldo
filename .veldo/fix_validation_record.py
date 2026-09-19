"""The validation record and the proof check: what turns the runner's four mechanical results into a
closure, and what refuses a landed proof that never got one (VELDO-0104).

The runner beside this module (.veldo/fix_validation.py) answers a mechanical question per finding:
did the reviewer's reproduction behave as it should on each commit, and is the author's row sensitive
to the defect. It closes nothing and says so. THIS module is where a closure is decided, because a
closure also needs a reader who saw the diff (.veldo/fix_assessor.py), and it is where the rule lives
that refuses a proof bundle whose item was fixed after its review and carries no such record.

Two modules rather than one because they answer different questions, and a reader coming to either
should not have to read the other to find the one they want.

Standard library only.

    python3 .veldo/fix_validation_record.py record <runner-record.json> <assessment-record.json> <proof-dir>
"""
from __future__ import annotations

import fnmatch
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def _runner():
    """The runner module, loaded once by path the way every organ here loads its siblings. Its
    ValidationError and RESULT_KEYS are THIS module's too, so a caller catching one catches both."""
    global _RUNNER
    if _RUNNER is None:
        spec = importlib.util.spec_from_file_location("veldo_fix_validation", Path(__file__).resolve().parent / "fix_validation.py")
        _RUNNER = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_RUNNER)
    return _RUNNER


_RUNNER = None
ValidationError = _runner().ValidationError
RESULT_KEYS = _runner().RESULT_KEYS
SCHEMA = _runner().SCHEMA                        # the runner record's schema, which this one composes from
_load = _runner()._load


RECORD_SCHEMA = "veldo.fix-validation-record/v1"
RECORD_FILE = "validation.json"
RECORD_DIR = "validation"          # the bundle's earlier records, one per fix commit it has validated
CAPSULE_DIR = "capsules"           # where the review's own capsules are kept inside the bundle
ROUND_CAP = 2
FLAG_KEY = "fix_validation"
# A commit is a fix round when it changes the code or the suites. Bookkeeping is not a round: the proof
# bundle, the specs (a status flip, the index), the gate stamp and the event log. Deliberately NOT
# filtered by the spec's declared footprint, because the fix commit can rewrite that footprint.
NOT_A_ROUND = ("proof/", "specs/", ".veldo/last_verify", ".veldo/events.jsonl", ".veldo/lessons.jsonl")
# The error taxonomy, one code per way a bundle fails the rule.
NO_RECORD = "no-validation-record"
FINDING_NOT_CLOSED = "finding-not-closed"
ASSESSOR_NOT_CLOSED = "assessor-not-closed"
FINDING_NOT_COVERED = "finding-not-covered"
ROUND_CAP_EXCEEDED = "round-cap-exceeded"
RECORD_WRONG_COMMIT = "validation-record-does-not-name-this-commit"
RECORD_MISMATCH = "validation-record-does-not-match-the-bundle"
PARKED_SHIPPED = "parked-item-shipped"


def _commit_exists(repo, commit: str) -> bool:
    """Is this commit an object in THIS repository? Asked before anything is counted between two
    commits, because a range over a history nobody has is not a question with an answer."""
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
                       capture_output=True, timeout=60)
    return r.returncode == 0


def _git(repo, *args: str) -> list:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise ValidationError(f"git {' '.join(args)} failed: {r.stderr.strip()[:300]}")
    return [line for line in r.stdout.splitlines() if line.strip()]


# --- the owner flag -------------------------------------------------------------------------------

def flag_from_policy(policy: dict) -> bool:
    """THE RULE. The flag is required under fix_validation in the policy mapping, and it is true only
    when it is exactly true; anything else, including absent, is advisory. Takes the PARSED policy, so
    the reading of the file is the caller's and this repository's one front-matter parser is used
    rather than a second one written here."""
    block = (policy or {}).get(FLAG_KEY)
    if isinstance(block, dict):
        return str(block.get("required", "")).strip().strip("'\"").lower() == "true"
    return False


def _strip_comment(line: str) -> str:
    """The line without a trailing comment. A # inside quotes is text, not a comment."""
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def read_policy(policy_path) -> dict:
    """The fix_validation block of the policy file, as a mapping. A deliberately small reader for the
    ONE key this organ owns: the block written inline ({required: true}) or as indented lines, with a
    trailing comment or quotes in either form. The AUTHORITY on the flag is flag_from_policy, which
    takes an already-parsed mapping; validate.py, the one call site, parses the file with this
    repository's own front-matter parser and calls that. This reader serves the command line and the
    rows. An unreadable or absent policy is an empty mapping, which reads as advisory."""
    try:
        lines = Path(policy_path).read_text().splitlines()
    except OSError:
        return {}
    for i, raw in enumerate(lines):
        if not raw.startswith(FLAG_KEY + ":"):
            continue
        rest = _strip_comment(raw[len(FLAG_KEY) + 1:]).strip()
        pairs = []
        if rest.startswith("{"):
            pairs = [p for p in rest.strip("{}").split(",") if p.strip()]
        else:
            for nxt in lines[i + 1:]:
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    continue
                if not nxt.startswith((" ", "\t")):
                    break
                pairs.append(_strip_comment(nxt).strip())
        block = {}
        for pair in pairs:
            k, sep, v = pair.partition(":")
            if sep:
                block[k.strip()] = v.strip()
        return {FLAG_KEY: block}
    return {}


def read_flag(policy_path) -> bool:
    return flag_from_policy(read_policy(policy_path))


# --- what the REVIEWER left in the bundle, which the author cannot forge ---------------------------

def review_evidence(proof_dir, capsule_mod=None) -> dict:
    """The review's own evidence inside the proof bundle, read from the bundle and never from the
    manifest: the capsules the reviewer saved (proof/<SPEC>/capsules/<finding-id>/, each verified
    against its own digests) and any recorded verdict. Returns {commit, findings, source}. commit is
    the commit the review read; findings are the ids it names. Empty when the bundle carries no review
    evidence, which is what an item that was never reviewed looks like."""
    root = Path(proof_dir)
    out = {"commit": None, "findings": [], "source": None}
    caps = root / CAPSULE_DIR
    if caps.is_dir():
        mod = capsule_mod or _load("fixval_capsule", Path(__file__).resolve().parent / "capsule.py")
        ids, commits = [], []
        for d in sorted(p for p in caps.iterdir() if p.is_dir()):
            try:
                m = mod.load_capsule(d)
            except Exception:  # noqa: BLE001 - a capsule that does not verify is not evidence
                continue
            ids.append(str(m["finding_id"]))
            commits.append(str(m["reviewed_commit"]))
        if ids:
            return {"commit": commits[0], "findings": sorted(set(ids)), "source": f"{len(ids)} capsule(s) in the bundle"}
    for vp in sorted(root.glob("verdict*.json")):
        try:
            v = json.loads(vp.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(v, dict) and v.get("commit"):
            out = {"commit": str(v["commit"]), "findings": [], "source": vp.name}
            break
    return out


def prior_rounds(proof_dir) -> list:
    """The fix commits this bundle has already validated, from its own kept records. A squash can hide
    commits from Git; it cannot remove a record an earlier landing committed."""
    root = Path(proof_dir) / RECORD_DIR
    seen = []
    if root.is_dir():
        for p in sorted(root.glob("*.json")):
            try:
                r = json.loads(p.read_text())
            except (OSError, ValueError):
                continue
            c = r.get("fixed_commit")
            if c and c not in seen:
                seen.append(str(c))
    return seen


def fix_rounds(repo, reviewed: str, fixed: str) -> list:
    """The fix rounds between the review and the landing, DERIVED FROM GIT: a commit that changes
    anything outside the bookkeeping set is one round. Nothing here reads a field anyone can edit, and
    nothing here consults the spec's footprint, which a fix commit could rewrite."""
    rounds = []
    for c in _git(repo, "rev-list", "--reverse", f"{reviewed}..{fixed}"):
        paths = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", c)
        hit = [p for p in paths if not p.startswith(NOT_A_ROUND)]
        if hit:
            rounds.append({"commit": c, "paths": hit[:20]})
    return rounds


def round_count(repo, reviewed: str, fixed: str, proof_dir) -> dict:
    """The round count: the commits Git shows, and the fix commits the bundle's earlier records name,
    whichever is larger. A squashed history shows fewer commits than it had rounds; the kept records
    still name them."""
    from_git = fix_rounds(repo, reviewed, fixed)
    from_records = [c for c in prior_rounds(proof_dir) if c != fixed]
    count = max(len(from_git), len(from_records) + 1 if from_records else len(from_git))
    return {"count": count, "from_git": from_git, "from_records": from_records}


# --- the record -----------------------------------------------------------------------------------

def _digest(obj) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def write_record(runner_record: dict, assessment_record: dict, spec_id: str, repo, proof_dir) -> dict:
    """Compose proof/<SPEC>/validation.json from the runner's record (four results per finding) and the
    assessor's (a verdict per finding). A finding is closed when its four results passed AND the
    assessor said closed. The two records must be about the SAME pair of commits, or there is nothing
    to compose: a verdict on another diff says nothing about this one. The record is also kept under
    validation/<fixed-commit>.json, so a later round cannot lose the count by rewriting history."""
    for key in ("reviewed_commit", "fixed_commit"):
        a, b = runner_record.get(key), assessment_record.get(key)
        if b is not None and a != b:
            raise ValidationError(f"the runner record and the assessment disagree on {key}: {a!r} and {b!r}; "
                                  "an assessment of another fix cannot close this one")
    per = assessment_record.get("per_finding") or {}
    findings = []
    for f in runner_record.get("findings") or []:
        fid = f["finding_id"]
        verdict = per.get(fid) or {"status": "not_closed", "reason": "no assessor verdict for this finding"}
        runner_closed = all(f["results"].get(k, {}).get("status") == "passed" for k in RESULT_KEYS)
        findings.append({"id": fid, "results": f["results"], "assessor": verdict,
                         "closed": runner_closed and verdict.get("status") == "closed"})
    reviewed, fixed = runner_record["reviewed_commit"], runner_record["fixed_commit"]
    counted = round_count(repo, reviewed, fixed, proof_dir)
    rec = {
        "schema": RECORD_SCHEMA,
        "spec_id": spec_id,
        "reviewed_commit": reviewed,
        "fixed_commit": fixed,
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runner_record_digest": _digest(runner_record),
        "assessment_record_digest": _digest(assessment_record),
        "assessor_provenance": assessment_record.get("provenance"),
        "findings": findings,
        "closed": [f["id"] for f in findings if f["closed"]],
        "open": [f["id"] for f in findings if not f["closed"]],
        "rounds": counted,
        "round_cap": ROUND_CAP,
        "parked": counted["count"] > ROUND_CAP,
    }
    out = Path(proof_dir)
    out.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rec, indent=1, sort_keys=True) + "\n"
    (out / RECORD_FILE).write_text(body)
    (out / RECORD_DIR).mkdir(exist_ok=True)
    (out / RECORD_DIR / f"{str(fixed)[:12]}.json").write_text(body)
    return rec


# --- the rule over one bundle ---------------------------------------------------------------------

def check_bundle(manifest: dict, record, repo, proof_dir, required: bool, spec_status=None, capsule_mod=None) -> dict:
    """The rule over one proof bundle. APPLICABILITY IS DERIVED, never declared: the bundle is subject
    to this rule when it carries the reviewer's own evidence (verified capsules, or a recorded verdict)
    taken at a commit earlier than the bundle's own. An author who writes no field and an author who
    writes the wrong one are treated the same way. Returns the flag state, the round count, whether the
    item is parked, the problems found (each {code, text}) and whether they refuse or warn. Never
    raises for a bad record: an unreadable record is no record."""
    commit = manifest.get("commit")
    ev = review_evidence(proof_dir, capsule_mod)
    reviewed = ev.get("commit")
    out = {"applicable": False, "required": bool(required), "rounds": 0, "parked": False, "problems": [],
           "refuses": False, "reviewed_commit": reviewed, "evidence": ev.get("source")}
    if not reviewed or not commit or reviewed == commit:
        return out
    # The commits have to be IN THIS REPOSITORY. A bundle can carry a review taken in a predecessor
    # repository whose history was frozen and not carried over, and this one carries many: their
    # verdicts name commits that do not exist here. Nothing can be counted about a history nobody has,
    # so the rule does not apply, and it says which commit it could not find. Treating that as a
    # failure instead would refuse the whole landed corpus the moment the owner turned the flag on,
    # which is the same as not having the flag.
    missing = [c for c in (reviewed, commit) if not _commit_exists(repo, c)]
    if missing:
        out["unknown_commits"] = missing
        return out
    out["applicable"] = True
    problems = out["problems"]
    if not isinstance(record, dict):
        problems.append({"code": NO_RECORD, "text": f"the bundle carries review evidence at {str(reviewed)[:12]} ({ev.get('source')}) and landed at {str(commit)[:12]}, but has no {RECORD_FILE}"})
    else:
        if record.get("fixed_commit") != commit:
            problems.append({"code": RECORD_WRONG_COMMIT, "text": f"{RECORD_FILE} names fixed_commit {str(record.get('fixed_commit'))[:12]}, the bundle's commit is {str(commit)[:12]}"})
        if record.get("reviewed_commit") != reviewed:
            problems.append({"code": RECORD_MISMATCH, "text": f"{RECORD_FILE} names reviewed_commit {str(record.get('reviewed_commit'))[:12]}, the bundle's review evidence was taken at {str(reviewed)[:12]}"})
        if record.get("schema") != RECORD_SCHEMA:
            problems.append({"code": RECORD_MISMATCH, "text": f"{RECORD_FILE} schema is {record.get('schema')!r}, expected {RECORD_SCHEMA}"})
        if manifest.get("spec_id") and record.get("spec_id") and record["spec_id"] != manifest["spec_id"]:
            problems.append({"code": RECORD_MISMATCH, "text": f"{RECORD_FILE} names spec {record['spec_id']}, the bundle is {manifest['spec_id']}"})
        covered = {str(f.get("id")) for f in (record.get("findings") or [])}
        for fid in ev.get("findings") or []:
            if fid not in covered:
                problems.append({"code": FINDING_NOT_COVERED, "text": f"the review saved a capsule for finding {fid}, which {RECORD_FILE} does not mention"})
        for f in record.get("findings") or []:
            fid = f.get("id")
            for k in RESULT_KEYS:
                st = (f.get("results") or {}).get(k, {}).get("status")
                if st != "passed":
                    problems.append({"code": FINDING_NOT_CLOSED, "text": f"finding {fid}: {k} is {st or 'missing'}"})
            vst = (f.get("assessor") or {}).get("status")
            if vst != "closed":
                problems.append({"code": ASSESSOR_NOT_CLOSED, "text": f"finding {fid}: assessor verdict is {vst or 'missing'}"})
    counted = round_count(repo, reviewed, commit, proof_dir)
    out["rounds"] = counted["count"]
    out["round_detail"] = {"from_git": [r["commit"] for r in counted["from_git"]], "from_records": counted["from_records"]}
    out["parked"] = counted["count"] > ROUND_CAP
    if out["parked"]:
        open_ids = (record or {}).get("open") if isinstance(record, dict) else None
        problems.append({"code": ROUND_CAP_EXCEEDED, "text": f"{counted['count']} fix rounds after the review (cap {ROUND_CAP}); the item is parked with open findings {open_ids if open_ids is not None else 'unknown (no record)'}"})
        if spec_status == "shipped":
            problems.append({"code": PARKED_SHIPPED, "text": "a parked item cannot be shipped; its spec says shipped"})
    out["refuses"] = bool(required and problems)
    return out

# --------------------------------------------------------------------------------------------------
# The one call site, kept here with the rule it applies
# --------------------------------------------------------------------------------------------------

def check_proof_bundle(path, manifest, root, parse_yamlish, front_matter, fail) -> int:
    """What validate.py runs for every proof manifest, in one line there and the whole of it here. The
    validator hands in its own reader of front matter and its own way of reporting a failure, so this
    module never has to know how that validator is put together."""
    policy = Path(root) / ".veldo" / "policy.yaml"
    required = flag_from_policy(parse_yamlish(policy.read_text()) if policy.is_file() else {})
    state = "required" if required else "advisory"
    proof_dir = Path(path).parent
    record = None
    rp = proof_dir / RECORD_FILE
    if rp.is_file():
        try:
            record = json.loads(rp.read_text())
        except Exception as e:  # noqa: BLE001 - an unreadable record is no record, named as such
            print(f"  {path}: {RECORD_FILE} is unreadable ({e}); treated as absent")
    status, sid = None, manifest.get("spec_id")
    for sp in sorted((Path(root) / "specs").glob(f"{sid}-*.md")) if sid else []:
        status = (front_matter(sp.read_text()) or {}).get("status")
        break
    try:
        res = check_bundle(manifest, record, root, proof_dir, required, status)
    except ValidationError as e:
        print(f"  {path}: fix validation {state}; could not read the commits it needs: {e}")
        return fail(path, f"fix validation could not read the commits it needs: {e}") if required else 0
    if not res["applicable"]:
        why = ("the review evidence names commit(s) this repository does not have, so nothing about it can be "
               f"counted here: {', '.join(c[:12] for c in res['unknown_commits'])}" if res.get("unknown_commits")
               else "the bundle carries no review evidence taken before its own commit")
        print(f"  {path}: fix validation {state} (policy fix_validation.required); not applicable: {why}")
        return 0
    print(f"  {path}: fix validation {state} (policy fix_validation.required); review evidence "
          f"{res.get('evidence')} at {str(res.get('reviewed_commit'))[:12]}; fix rounds {res['rounds']}"
          f"{' - PARKED' if res['parked'] else ''}; {len(res['problems'])} problem(s)")
    errs = 0
    for pr in res["problems"]:
        if res["refuses"]:
            errs += fail(path, f"{pr['code']}: {pr['text']}")
        else:
            print(f"  {path}: warning {pr['code']}: {pr['text']} (advisory: fix_validation.required is off)")
    return errs


def main(argv: list) -> int:
    if len(argv) >= 5 and argv[1] == "record":
        runner = json.loads(Path(argv[2]).read_text())
        assessment = json.loads(Path(argv[3]).read_text())
        proof_dir = Path(argv[4]).resolve()
        spec_id = proof_dir.name
        repo = _git_root(proof_dir)
        try:
            rec = write_record(runner, assessment, spec_id, repo, proof_dir)
        except ValidationError as e:
            print(f"REFUSED: {e}")
            return 2
        print(json.dumps({"closed": rec["closed"], "open": rec["open"], "rounds": rec["rounds"]["count"], "parked": rec["parked"]}))
        return 0 if not rec["open"] and not rec["parked"] else 1
    print(__doc__)
    return 64


def _git_root(path: Path) -> Path:
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise ValidationError(f"{path} is not inside a git repository")
    return Path(r.stdout.strip())

if __name__ == "__main__":
    sys.exit(main(sys.argv))
