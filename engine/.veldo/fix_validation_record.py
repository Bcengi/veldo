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


_FULL_COMMIT_ID = re.compile(r"[0-9a-fA-F]{40}")


def start_line_from_policy(policy: dict) -> str:
    """WHERE THE RULE BEGINS, as the owner recorded it: fix_validation.from_commit in the policy, or
    empty when none is recorded. Read from the policy and NOWHERE ELSE, for the same reason the flag
    is: a check that works out whether it applies from a field the author writes binds only the
    authors who volunteer it, and the party this rule gates is the author of a fix. The policy file
    is a protected path, so the owner sets the line and the gated party cannot move it."""
    block = (policy or {}).get(FLAG_KEY)
    if isinstance(block, dict):
        return str(block.get("from_commit", "")).strip().strip("'\"")
    return ""


def _is_ancestor(repo, older: str, newer: str):
    """Did `newer` come after `older` in THIS repository's history?

    THREE ANSWERS, NOT TWO. git returns 0 for yes, 1 for no, and anything else, usually 128, for
    "I cannot answer": the commonest cause is a shallow clone, where the objects exist but the
    history between them does not. Collapsing that third answer into "no" excluded the bundle,
    which is the fail-OPEN direction, and on an ordinary shallow CI checkout it switched the whole
    rule off while printing a false statement about history. None means unanswerable, and the
    caller keeps the bundle in scope."""
    r = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
                       capture_output=True, timeout=60)
    if r.returncode in (0, 1):
        return r.returncode == 0
    return None


def bundle_landed_at(repo, proof_dir):
    """The commit that last changed this bundle, as THIS repository's history records it.

    The manifest's own `commit` field is written by the author of the fix, and the rule the start
    line serves exists to gate that author. Left to the manifest alone, backdating one field
    exempted the bundle: name a commit from before the line and the rule stops applying. So the
    bundle's position is also asked of git, which the author cannot edit from inside the bundle.
    None when the bundle is not committed yet, which is the ordinary case while it is being built."""
    r = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%H", "--", str(proof_dir)],
                       capture_output=True, text=True, timeout=60)
    out = (r.stdout or "").strip()
    return out if r.returncode == 0 and out else None


def start_line_scope(repo, start: str, commit: str, landed=None) -> dict:
    """Whether this bundle is on the near side of the start line, and why.

    FAILS CLOSED, in both directions that matter. No line recorded leaves every bundle in scope,
    which is the behaviour VELDO-0104 shipped. A line this repository cannot resolve, from a typo or
    from a history nobody has, ALSO leaves every bundle in scope and says so. The dangerous
    direction is the other one: a single wrong character in a commit id quietly exempting the whole
    corpus, which would look exactly like a rule that works."""
    if not start:
        return {"recorded": "", "resolved": False, "excluded": False, "reason": "no start line recorded"}
    # A COMMIT ID, by shape, before anything is resolved. A branch or tag name resolves today and
    # to something else tomorrow, and the ref namespace is not a protected path, so the owner's
    # line could move without the owner. An abbreviated id becomes ambiguous as history grows. And
    # a value like 0123456 is a general parser's integer coercion showing through, which silently
    # drops the leading zero and names a different commit. All three are refused here, and refused
    # is IN SCOPE: a mistyped line must not exempt anything.
    if not _FULL_COMMIT_ID.fullmatch(start):
        return {"recorded": start, "resolved": False, "excluded": False,
                "reason": (f"the recorded start line {start!r} is not a commit id; it must be forty "
                           "hexadecimal characters, not a branch, a tag or an abbreviation")}
    if not _commit_exists(repo, start):
        return {"recorded": start, "resolved": False, "excluded": False,
                "reason": f"the recorded start line {start[:12]} is not a commit in this repository"}
    # EVERY position this bundle can be said to occupy is asked, and ANY of them being at or after
    # the line keeps it in scope. The manifest's commit is the author's claim; the commit that last
    # touched the bundle is the repository's. Taking the union means backdating the claim buys
    # nothing, and it is the fail-closed direction when the two disagree.
    answers = {}
    for name, c in (("manifest", commit), ("history", landed)):
        if not c:
            continue
        answers[name] = _is_ancestor(repo, start, c)
    if any(a is True for a in answers.values()):
        where = ", ".join(n for n, a in answers.items() if a is True)
        return {"recorded": start, "resolved": True, "excluded": False, "positions": answers,
                "reason": f"at or after the start line {start[:12]} (by {where})"}
    if any(a is None for a in answers.values()) or not answers:
        return {"recorded": start, "resolved": True, "excluded": False, "positions": answers,
                "reason": (f"git cannot say whether this bundle is after the start line {start[:12]}, "
                           "usually a shallow clone; kept in scope")}
    return {"recorded": start, "resolved": True, "excluded": True, "positions": answers,
            "reason": f"the bundle landed at {str(commit)[:12]}, before the start line {start[:12]}"}


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


def _split_unquoted(text: str, sep: str, maxsplit: int = -1) -> list:
    """Split on SEP, ignoring any separator inside single or double quotes.

    The naive split was a BYPASS, not a tidiness problem. `{required: true, note: "leave this,
    required: false"}` split at the comma inside the note, the fragment after it parsed as a second
    `required` pair, and it overwrote the owner's own setting: the armed rule read as OFF and every
    bundle it should have refused passed with zero errors. A quoted string is one value."""
    out, cur, quote = [], [], None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            cur.append(ch)
            continue
        if ch == sep and (maxsplit < 0 or len(out) < maxsplit):
            out.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    out.append("".join(cur))
    return out


def read_policy(policy_path) -> dict:
    """The fix_validation block of the policy file, as a mapping. A deliberately small reader for the
    ONE key this organ owns: the block written inline ({required: true}) or as indented lines, at any
    indentation, with a trailing comment or quotes in either form. The AUTHORITY on the flag is
    flag_from_policy, which takes an already-parsed mapping; THIS reader is what produces that
    mapping everywhere the owner's two settings are read - the proof-bundle check in this module, the
    command line and the rows.

    The validator's general front-matter parser must NOT be used for this file: it strips a
    whole-line comment and not a trailing one, so `required: true  # armed` reads as false, and it
    coerces a digit-only value to an integer, so a start line of 0123456 loses its leading zero. It
    is not taught to do better because 55 of this repository's 328 specifications and plans parse
    differently under that change, measured by VELDO-0106's own row rather than pinned here.

    THREE ANSWERS. No policy file, or a file with no fix_validation key at all, is an empty mapping:
    a repository that never adopted the rule is advisory and that is correct. A block this reader can
    read is that block. A fix_validation key that is PRESENT and yields nothing raises, because the
    one answer this reader must never give is a quiet "off" for a setting the owner did write: every
    way of failing here has to land on the strict side."""
    try:
        lines = Path(policy_path).read_text().splitlines()
    except OSError:
        return {}
    for i, raw in enumerate(lines):
        stripped = raw.lstrip()
        # AT ANY INDENTATION. Anchoring on column zero meant that indenting the document - which the
        # general parser reads perfectly well - made this reader answer "no such key", and no such
        # key reads as advisory. The owner's armed rule switched itself off over whitespace.
        if not stripped.startswith(FLAG_KEY + ":"):
            continue
        indent = len(raw) - len(stripped)
        rest = _strip_comment(stripped[len(FLAG_KEY) + 1:]).strip()
        pairs = []
        if rest.startswith("{"):
            if not rest.endswith("}"):
                raise ValidationError(
                    f"{policy_path}: the {FLAG_KEY} inline mapping is not closed: {rest!r}")
            pairs = [p for p in _split_unquoted(rest[1:-1], ",") if p.strip()]
        elif rest:
            raise ValidationError(
                f"{policy_path}: {FLAG_KEY} must be a mapping, written inline or as indented lines; "
                f"it carries the scalar {rest!r}")
        else:
            member_indent = None
            for nxt in lines[i + 1:]:
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    continue
                nind = len(nxt) - len(nxt.lstrip())
                if nind <= indent:
                    break
                if member_indent is None:
                    member_indent = nind
                if nind != member_indent:
                    continue  # deeper: part of a member's own value, not a member of this block
                pairs.append(_strip_comment(nxt).strip())
        block = {}
        for pair in pairs:
            parts = _split_unquoted(pair, ":", 1)
            if len(parts) == 2:
                block[parts[0].strip()] = parts[1].strip()
        if not block:
            raise ValidationError(
                f"{policy_path}: {FLAG_KEY} is present but this reader parsed no settings from it; "
                "a setting the owner wrote must never read as absent")
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

def check_bundle(manifest: dict, record, repo, proof_dir, required: bool, spec_status=None, capsule_mod=None, start_line=None) -> dict:
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
    # WHERE THE RULE BEGINS (VELDO-0105). A gate binds the work that comes after it, not the work
    # that shipped before it existed. Turning the flag on without this reddened thirteen bundles
    # that landed months before the runner and the assessor that produce a validation record.
    scope = start_line_scope(repo, start_line or "", commit, bundle_landed_at(repo, proof_dir))
    out["start_line"] = scope
    if scope["excluded"]:
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
    # READ BY read_policy, NOT by the parser the validator hands in. The handed-in parser strips a
    # whole-line comment and not a trailing one, so `required: true  # armed` read as FALSE and the
    # rule the owner had just armed returned to advisory in silence. read_policy already handles
    # every shape this file takes, and it is not a second parser written here: it predates this
    # item and VELDO-0104's suite already tests it. The handed-in parser is still used for the spec
    # front matter below, which is what it is for.
    #
    # The general parser is deliberately NOT taught to strip trailing comments. That was measured
    # over this repository's corpus first: 55 of its 328 specifications and plans parse differently
    # under it, 49 of them in acceptance-criteria text and the rest in risk, constraints and status
    # fields containing a hash. It would truncate shipped specifications to fix a flag nobody had
    # tripped. VELDO-0106's AC3 row recomputes the count each run rather than pinning it.
    unreadable = ""
    try:
        parsed = read_policy(policy) if policy.is_file() else {}
    except ValidationError as e:
        # FAIL CLOSED, LOUDLY. A fix_validation block the owner wrote and this reader cannot parse is
        # the one case where answering "advisory" would be a lie with consequences: it switches the
        # rule off over a typo, on a protected path, with nothing failing anywhere. So the rule is
        # REQUIRED and the start line is empty, which puts every bundle back in scope. Both moves are
        # in the strict direction, so a malformed policy can only ever make the gate harder to pass.
        unreadable = str(e)
        parsed = {FLAG_KEY: {"required": "true"}}
    required = flag_from_policy(parsed)
    start_line = start_line_from_policy(parsed)
    state = "required" if required else "advisory"
    line_state = f"from {start_line[:12]}" if start_line else "no start line"
    if unreadable:
        print(f"  {path}: the policy could not be read ({unreadable}); the rule is treated as REQUIRED "
              "with every bundle in scope, because a setting the owner wrote must never read as absent")
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
        res = check_bundle(manifest, record, root, proof_dir, required, status, start_line=start_line)
    except ValidationError as e:
        print(f"  {path}: fix validation {state}; could not read the commits it needs: {e}")
        return fail(path, f"fix validation could not read the commits it needs: {e}") if required else 0
    if not res["applicable"]:
        scope = res.get("start_line") or {}
        if scope.get("excluded"):
            why = scope["reason"]
        elif res.get("unknown_commits"):
            why = ("the review evidence names commit(s) this repository does not have, so nothing about "
                   f"it can be counted here: {', '.join(c[:12] for c in res['unknown_commits'])}")
        else:
            why = "the bundle carries no review evidence taken before its own commit"
        print(f"  {path}: fix validation {state}, {line_state} (policy fix_validation); not applicable: {why}")
        return 0
    print(f"  {path}: fix validation {state}, {line_state} (policy fix_validation); review evidence "
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
