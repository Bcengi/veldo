#!/usr/bin/env python3
"""VELDO policy check: the mechanical reader of .veldo/policy.yaml.

Called by the guard before a push/merge is allowed. Exits 0 (allow) or
prints the reason and exits 1 (block). Checks, for the current HEAD:

1. Protected paths: if the commit range being pushed touches a protected
   path, an approval file (veldo.approval/v1) must exist for exactly HEAD,
   unexpired. Anything may raise risk; nothing lowers it.
2. Emergency debt: an emergency.push event without a later backfill-closing
   event (spec.shipped for its backfill, or an explicit emergency.closed)
   blocks ordinary pushes, as the setup promises.

Proportionate by design: stdlib only, no yaml dependency (reads the simple
policy.yaml shape the template ships).
"""
import datetime, fnmatch, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The proof-corpus enumeration (WARP-0727): the one owner of what a corpus path is, shared
# with .veldo/events.py and .veldo/validate.py. A private glob here would be a THIRD spelling
# of one set, which is the defect that module exists to make unreachable.
_vcspec = importlib.util.spec_from_file_location(
    "veldo_verdict_corpus", ROOT / ".veldo" / "verdict_corpus.py")
_VC = importlib.util.module_from_spec(_vcspec)
_vcspec.loader.exec_module(_VC)


def _corpus_files(pattern):
    """The corpus artifacts of ONE declared pattern, as absolute paths, through the ONE
    enumeration.

    EVERY CORPUS READ IN THIS FILE GOES THROUGH HERE (WARP-0727 round 2). Three private globs
    survived the first round - `proof/*/approval*.json` and two spellings of
    `proof/*/manifest.json` - and each was a SECOND implementation of a set the owner already
    declares a pattern for. They computed the same answer as the owner on this platform, which
    is what makes them a law violation rather than a live divergence: a second spelling is a
    place a future difference can appear where neither side can see it, and the whole point of
    the owner is that there is nowhere for one to appear."""
    return [ROOT / rel for rel in _VC.disk_corpus(ROOT, pattern)]


def _verdict_files():
    """The verdict corpus as absolute paths, through the ONE enumeration."""
    return _corpus_files(_VC.VERDICT_PATTERN)


def protected_patterns():
    pats = []
    text = (ROOT / ".veldo" / "policy.yaml").read_text()
    in_pp = False
    for line in text.splitlines():
        if re.match(r"^protected_paths:", line):
            in_pp = True
            continue
        if in_pp:
            m = re.search(r'path:\s*"([^"]+)"', line)
            if m:
                pats.append(m.group(1))
            elif line and not line.startswith((" ", "#", "-")):
                in_pp = False
    return pats


def _range_specs():
    """The comparison bases to try, in order, for "what is this push".

    THE FALLBACK USED TO DECIDE THE ANSWER, and it made the gate irreproducible. Only
    `@{upstream}..HEAD` and `HEAD~20..HEAD` were tried, and a checkout with no upstream - which is
    EVERY git worktree, detached or on a fresh branch - silently fell through to an arbitrary
    twenty-commit window. Measured at one commit on 2026-08-03: the main checkout saw 2 changed
    files and no protected paths, a worktree of the SAME COMMIT saw 39 and four protected ones, so
    the protected-path check demanded approvals for files that were not part of the change and the
    gate went red on a tree whose code was byte-identical to a green one.

    `origin/main` resolves in every clone and every worktree, so trying it BEFORE the twenty-commit
    guess makes the three agree. The guess stays last, for a repository with no origin at all, but
    it is now the exception rather than the thing that answers whenever tracking is not configured.
    """
    specs = ["@{upstream}..HEAD"]
    for ref in ("origin/HEAD", "origin/main"):
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0 and r.stdout.strip():
            specs.append(ref + "..HEAD")
    specs.append("HEAD~20..HEAD")
    return specs


def changed_files():
    # files changed on this branch vs its upstream (see _range_specs for why the order matters)
    for spec in _range_specs():
        r = subprocess.run(["git", "diff", "--name-only", spec],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            return [f for f in r.stdout.splitlines() if f]
    return []


def head():
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip()


def push_range_commits():
    """Every commit hash being pushed, HEAD first. Same base resolution as
    changed_files, through `_range_specs`, so the two cannot disagree about what the push is."""
    for spec in _range_specs():
        r = subprocess.run(["git", "rev-list", spec],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            return [c for c in r.stdout.splitlines() if c]
    return []


def _approval_covers(approval, path):
    """Path-scoped authorization: an approval only authorizes the paths its
    scope names. Empty scope.paths authorizes nothing (fail closed) - name the
    paths."""
    for pat in approval.get("scope", {}).get("paths", []) or []:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.rstrip("*") + "*"):
            return True
    return False


def valid_approval_for(commits, path=None, producer=None):
    """An approval is valid if it is approved, unexpired, commit-bound to a
    commit in the push range, and - when a path is given - scopes that path.
    Commit binding to HEAD alone is unsatisfiable (the approval lands in an
    evidence commit that cannot name its own hash), so range binding is used.
    Self-separation: an approver who is also the proof producer cannot approve
    their own work."""
    if isinstance(commits, str):
        commits = [commits]
    now = datetime.datetime.now(datetime.timezone.utc)
    for f in _corpus_files(_VC.APPROVAL_PATTERN):
        try:
            a = json.loads(f.read_text())
        except Exception:
            continue
        # A payload that PARSES but is not an object is skipped like one that does not parse at all:
        # `"text"` and `[1,2]` are both valid JSON and neither is an approval. The reader already
        # tolerates a file that does not parse, so tolerating one that parses to the wrong type is
        # the consistent behaviour, not an extra kindness.
        if not isinstance(a, dict):
            continue
        if a.get("decision") != "approved":
            continue
        # SCOPE MAY NOT BE AN OBJECT, and this is not hypothetical. `proof/WARP-0620/
        # approval-dmitry.json` predates the current shape: it declares the same
        # `veldo.approval/v1` schema but carries PROSE in `scope` and its `spec_id` at the top
        # level. Two incompatible shapes under one schema string is the actual defect; the record
        # itself is a faithful account of a decision Dmitry made and is not going to be rewritten
        # to suit a parser.
        #
        # An approval whose scope is not an object cannot be commit-bound, and this function's own
        # contract is that validity REQUIRES commit binding, so skipping is the same answer the
        # next line already gives when `bound` is missing.
        scope = a.get("scope")
        if not isinstance(scope, dict):
            continue
        bound = scope.get("commit")
        if not bound or not any(c.startswith(bound) for c in commits):
            continue
        try:
            exp = datetime.datetime.fromisoformat(a["expires_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if exp <= now:
            continue
        if path is not None and not _approval_covers(a, path):
            continue
        if producer and a.get("approver") and a["approver"] == producer:
            continue  # self-approval: the approver produced the work
        return str(f)
    return None


def open_emergency_debt():
    ev = ROOT / ".veldo" / "events.jsonl"
    if not ev.exists():
        return None
    open_debts = []
    for line in ev.read_text().splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "emergency.push":
            open_debts.append(e)
        elif e.get("type") in ("emergency.closed", "spec.shipped") and open_debts:
            # a shipped backfill (or explicit close) after an emergency closes the oldest debt
            open_debts.pop(0)
    return open_debts[0] if open_debts else None


def blocking_findings(v):
    """Verdict findings come in two canonical shapes: a dict
    {blocking: [...], non_blocking: [...]} or a list of {severity, text}
    with severity blocking|note. Returns the blocking entries. Anything
    outside both shapes counts as blocking: an unreadable finding must
    fail closed, never slip through."""
    f = v.get("findings")
    if f is None:
        return []
    if isinstance(f, dict):
        b = f.get("blocking")
        if b is None:
            return []
        return list(b) if isinstance(b, list) else [b]
    if isinstance(f, list):
        out = []
        for item in f:
            if isinstance(item, dict) and item.get("severity") in ("note", "non_blocking"):
                continue
            out.append(item)
        return out
    return [f]


def unresolved_blocking(commits):
    """THE NEWEST VERDICT PER SPEC IN THE PUSH RANGE, when it carries blocking findings.
    Returns [(spec_id, path, finding), ...], empty when nothing objects.

    WHAT THIS IS AND IS NOT (WARP-0732). It is NOT a forgery defense and must never be
    described as one. An agent that can write this repository can also delete an inconvenient
    verdict file, and WARP-0730 conceded that fight deliberately after nine rounds established
    that a predicate inside the agent's own process cannot win it. What this buys is narrower
    and real: HONEST work does not merge past an outstanding objection, and evading it now takes
    an affirmative destructive act that shows up in the diff rather than the mere absence of a
    file.

    WHY THIS IS SAFE WHERE REQUIRING A PASS WAS NOT, and the whole design rests on it. Requiring
    a pass verdict is forgeable in the DANGEROUS direction: the agent mints its own approval.
    Objecting is forgeable only in the SAFE direction: a forged finding blocks the forger, which
    no attacker wants. And a forged CLEAN verdict clearing an objection gains nothing either,
    because NO VERDICT IS REQUIRED - never writing the objection reaches the same place with
    less work. A rule may safely admit a forgery that buys the forger nothing.

    NEWEST WINS, BY COMMIT ORDER, because the push range holds the branch's own earlier
    candidate commits: a REWORK on the commit before the fix must not block the fix forever.
    Two verdicts on the SAME commit fail closed and blocking wins. So does a findings shape the
    parser does not recognise, which is blocking_findings' own rule and is not weakened here."""
    order = {c: i for i, c in enumerate(commits)}          # 0 is newest (HEAD first)
    newest = {}
    for f in _verdict_files():
        try:
            v = json.loads(f.read_text())
        except Exception:
            continue
        c = v.get("commit") or ""
        rank = next((order[full] for full in order if c and full.startswith(c)), None)
        if rank is None:
            continue
        sid = v.get("spec_id") or ""
        prev = newest.get(sid)
        # same commit -> the objecting verdict wins, so a clean twin cannot clear it
        if prev is None or rank < prev[0] or (rank == prev[0] and blocking_findings(v)):
            newest[sid] = (rank, f, v)
    out = []
    for sid, (_rank, f, v) in sorted(newest.items()):
        for finding in blocking_findings(v):
            out.append((sid, f, finding))
    return out


def proof_digest(manifest):
    """Stable digest of a proof manifest's substance (spec, criteria, checks),
    so a verdict can bind to the exact proof it reviewed. Identical to the
    copy in validate.py; selftest asserts they do not drift."""
    payload = {
        "spec_id": manifest.get("spec_id"),
        "commit": manifest.get("commit"),
        "criteria": manifest.get("criteria"),
        "checks": manifest.get("checks"),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


def _proof_for_spec(spec_id):
    for p in _corpus_files(_VC.MANIFEST_PATTERN):
        if p.parent.name != spec_id:
            continue
        try:
            return p, json.loads(p.read_text())
        except Exception:
            return p, None
    return None, None


def producer_for(spec_id):
    _, m = _proof_for_spec(spec_id)
    return (m or {}).get("producer", "")


def _spec_file_fm(spec_id):
    for p in sorted((ROOT / "specs").glob(f"{spec_id}*.md")):
        m = re.match(r"^---\n(.*?)\n---", p.read_text(), re.S)
        if not m:
            return {}
        fm = {}
        for line in m.group(1).splitlines():
            mm = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
            if mm:
                fm[mm.group(1)] = mm.group(2).strip()
        return fm
    return {}


def ready_boundary_violations():
    """A spec that has a proof manifest must not still be a draft: proof of a
    draft is a boundary someone crossed without the spec being ready."""
    bad = []
    for p in _corpus_files(_VC.MANIFEST_PATTERN):
        try:
            m = json.loads(p.read_text())
        except Exception:
            continue
        sid = m.get("spec_id")
        if not sid:
            continue
        fm = _spec_file_fm(sid)
        if fm.get("status") == "draft":
            bad.append(sid)
    return bad


def spec_revision_stale():
    """If a spec declares a revision higher than the revision its proof was
    produced against, the proof is stale and must be re-run."""
    stale = []
    for p in _corpus_files(_VC.MANIFEST_PATTERN):
        try:
            m = json.loads(p.read_text())
        except Exception:
            continue
        sid = m.get("spec_id")
        pr = m.get("spec_revision")
        if not sid or pr is None:
            continue
        fm = _spec_file_fm(sid)
        try:
            if int(fm.get("revision", 1)) > int(pr):
                stale.append(sid)
        except (ValueError, TypeError):
            stale.append(sid)
    return stale


def valid_verdict_for(commit):
    for f in _verdict_files():
        try:
            v = json.loads(f.read_text())
        except Exception:
            continue
        if v.get("verdict") in ("pass", "pass_with_notes") and commit.startswith(v.get("commit", "\0")):
            if blocking_findings(v):
                continue
            # if the verdict binds to a proof digest, it must match the current
            # proof manifest for that spec - a verdict cannot be reused for a
            # proof it did not review.
            pd = v.get("proof_digest")
            if pd:
                sid = v.get("spec_id")
                _, m = _proof_for_spec(sid) if sid else (None, None)
                if not m or proof_digest(m) != pd:
                    continue
            return str(f)
    return None


def _head_spec_id():
    """The spec id of the change at HEAD, via the verdict bound to HEAD or its
    parent (the evidence-commit case)."""
    h = head()
    parent = subprocess.run(["git", "rev-parse", "HEAD^"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    for f in _verdict_files():
        try:
            v = json.loads(f.read_text())
        except Exception:
            continue
        c = v.get("commit", "")
        if c and (h.startswith(c) or (parent and parent.startswith(c))):
            return v.get("spec_id")
    return None


def main():
    h = head()

    # NO VERDICT IS REQUIRED HERE ANY MORE (WARP-0730). A verdict is an artifact the agent
    # can write, so requiring one asked an agent to certify itself, and nine build rounds were
    # spent trying to stop it forging that certificate. A predicate inside the agent's own
    # process cannot win that fight: it has the filesystem, the repository and the interpreter,
    # and every round closed one spelling while the next opened another.
    # So the authority moved instead of being defended. For ordinary work the GATE decides -
    # a green scripts/verify.sh is done, and it is not something an agent can forge into
    # existence. For protected paths the OWNER decides, enforced by the approval block below,
    # which is unchanged and is the one thing here an agent genuinely cannot produce.
    # valid_verdict_for() is deliberately KEPT and simply no longer consulted at this gate:
    # reviews still run and still report findings for a human to read, they just no longer
    # certify. Deleting the machinery is a separate item, so that a regression in either change
    # can be attributed to the change that caused it.
    #
    # BUT AN OBJECTION STILL STOPS THE PUSH (WARP-0732), and leaving that out was a real gap
    # rather than a consequence of the above. Dmitry, 2026-08-02: "Not good if werdict is rework
    # still would merge. That's fluff and real theater." Requiring a PASS is forgeable in the
    # dangerous direction and stays gone; blocking on a recorded OBJECTION is forgeable only in
    # the safe direction, because a forged finding blocks the forger. See unresolved_blocking.
    rng_f = push_range_commits() or [h]
    objections = unresolved_blocking(rng_f)
    if objections:
        # THE OWNER'S OVERRIDE IS THE APPROVAL BLOCK THAT ALREADY EXISTS, not a new artifact and
        # not a new field: it is the one thing at this gate an agent cannot produce, and an
        # override belongs on that footing. Self-approval is refused by valid_approval_for.
        override = valid_approval_for(rng_f, producer=producer_for(_head_spec_id()))
        if not override:
            print("VELDO policy: blocked. A review objected and the objection is unresolved.")
            for sid, path, finding in objections:
                try:
                    rel = path.relative_to(ROOT)
                except Exception:
                    rel = path
                print(f"  {sid}: {rel}")
                print(f"    {str(finding)[:300]}")
            print("  Resolve it the normal way: fix the work, commit, and let the re-review land")
            print("  a verdict on the newer commit. A review can object but never approve, so no")
            print("  pass verdict is required and none will clear this.")
            print("  To override, record an approval bound to a commit in this push, approved by")
            print("  someone who is not the proof producer.")
            return 1
        print("VELDO policy: review objection OVERRIDDEN by recorded owner approval "
              f"({len(objections)} finding(s)).")

    # protected paths -> commit-bound, unexpired approval required
    pats = protected_patterns()
    touched = []
    for f in changed_files():
        for p in pats:
            if fnmatch.fnmatch(f, p) or fnmatch.fnmatch(f, p.rstrip("*") + "*"):
                touched.append((f, p))
                break
    if touched:
        rng = push_range_commits() or [h]
        # each touched protected path needs an approval that names it, whose
        # approver is not the work's producer (self-separation).
        for tf, p in touched:
            producer = producer_for(_head_spec_id())
            if not valid_approval_for(rng, path=tf, producer=producer):
                print("VELDO policy: blocked. Protected path touched with no valid path-scoped approval.")
                print(f"  {tf}  (protected by {p})")
                print("  Required: an approved, unexpired veldo.approval/v1 whose scope.commit is a")
                print(f"  commit in this push, whose scope.paths covers {tf}, and whose approver")
                print("  is not the proof producer (no self-approval).")
                return 1

    # ready-spec boundary: no draft spec may carry a proof
    drafts = ready_boundary_violations()
    if drafts:
        print("VELDO policy: blocked. A draft spec has a proof manifest (ready-boundary): "
              + ", ".join(drafts))
        print("  A spec must be ready before it is built and proven; promote it or remove the proof.")
        return 1

    # spec-revision invalidation: a proof older than its spec's revision is stale
    stale = spec_revision_stale()
    if stale:
        print("VELDO policy: blocked. Proof is stale versus its spec revision: "
              + ", ".join(stale))
        print("  The spec revised after the proof ran; re-run the gate, proof, and review.")
        return 1

    # emergency debt blocks ordinary pushes
    debt = open_emergency_debt()
    if debt:
        print("VELDO policy: blocked. An emergency backfill debt is open "
              f"(emergency.push at {debt.get('at')}, commit {debt.get('commit','')[:12]}).")
        print("  Land the backfill (spec + proof + review) or record an emergency.closed event; "
              "the setup's promise is that unclosed debt blocks the next ordinary merge.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
