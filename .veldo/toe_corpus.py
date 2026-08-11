#!/usr/bin/env python3
"""The Tokens of Effort ground-truth corpus (WARP-1401, W1 of PLAN-0014).

WHAT THIS IS. One per-spec actuals record for every shipped change, joining what the loop already
records (lifecycle events, gate and review cycles, spend when it is present) to the spec's own
mechanical features (acceptance-criteria count, risk tier, protected-path touch, footprint size,
files touched, plan membership). It is the dataset every later TOE layer estimates against, so it
has to be derived rather than typed, and it has to be honest about what it does not have.

DETERMINISTIC AND IDEMPOTENT. Same inputs, same records, every run. Nothing here mints an id, reads
a clock or appends to anything: it reads specs, git and the event log and returns a list. That is
what lets the selftest drive it and what lets it be re-harvested over history without duplicating.

***

THE SPEND FIELDS ARE EMPTY IN THIS REPOSITORY, AND THAT IS A MEASURED FACT, NOT AN OVERSIGHT.

PLAN-0014's W1 says "every input is already recorded today". For the mechanical features and the
cycle counts that is true. For the SPEND inputs it is false, and this module reports the gap rather
than hiding it behind a zero.

Measured 2026-08-02 over this repository's own log: 904 events, of which 658 `gate.passed`, 171
`verdict.recorded` and 75 `gate.failed`. **Not one carries `tokens`, `cost_usd` or `human_minutes`.**
The envelope has always supported those fields, `events.py` accepts `--tokens` and `--cost-usd`, and
three separate readers (`metrics.py`, `entropy.py`, `metrics_support_report.py`) aggregate them.
Nothing anywhere EMITS them.

WHY, AND THIS IS THE ARCHITECTURAL PART: a token count is not knowable from inside the repository.
The gate script cannot see how many tokens an agent spent; that number lives in the agent's harness,
outside everything this codebase can reach. So the missing emitter is not a forgotten line of code,
it is an integration that has to be decided on. Until it exists, `tokens_known` is False on every
record and any estimator built on this corpus is estimating against features and cycles only.

`coverage()` reports that split as a number, so the gap is visible in the data rather than discovered
by whoever first trusts an estimate.
"""
import json
import re
import subprocess
from pathlib import Path

SCHEMA = "veldo.toe_actuals/v1"
ROOT = Path(__file__).resolve().parent.parent

# The spend fields the envelope allows. Declared once so `coverage` and the record builder cannot
# disagree about what "spend is present" means.
SPEND_FIELDS = ("tokens", "cost_usd", "human_minutes")

# The lifecycle events a cycle count is derived from. Gate failures are the rework signal: a change
# that went red three times before green cost three times the gate.
GATE_PASS, GATE_FAIL, VERDICT = "gate.passed", "gate.failed", "verdict.recorded"


def _run(args, cwd=None):
    r = subprocess.run(args, capture_output=True, text=True, cwd=str(cwd or ROOT))
    return r.stdout if r.returncode == 0 else ""


def _front_matter(text):
    """The spec's front matter as raw lines. One reader, and deliberately NOT a second yaml parser:
    only flat scalars and the two counted list shapes are needed here, and reaching for a parser
    this module does not otherwise need would be a second spelling of the contract."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


def footprint_of(text):
    """The declared footprint of one spec, as a list of paths. ONE reader: `spec_features` counts
    it and `build` tests it against the protected set, and an earlier draft of this module spelled
    the same regex out in both places, which is the second-spelling defect this repository has a
    named rule about. A spec with no footprint block has an empty one, not an exception."""
    fm = _front_matter(text)
    m = re.search(r"^footprint:\n((?:\s+-\s+.*\n)+)", fm, re.M)
    if not m:
        return []
    return [f.strip().strip('"') for f in re.findall(r"^\s+-\s+(.+?)\s*$", m.group(1), re.M)]


def spec_features(path):
    """The MECHANICAL features of one spec: everything an estimator may look at before the work is
    done. Every one is read off the spec or off git, never judged, because a feature a human has to
    assess is not a feature, it is an estimate wearing a feature's clothes."""
    text = Path(path).read_text()
    fm = _front_matter(text)
    def scalar(k):
        m = re.search(r"^%s:\s*(.+)$" % k, fm, re.M)
        return m.group(1).strip() if m else None
    # NEVER CRASH ON A MISSING FIELD. This read `.split()[0]` on a possibly empty string, so a
    # file with no risk line raised IndexError out of a corpus BUILD. Widening the spec glob from a
    # prefix to *.md is what exposed it: the generated specs/index.md has no front matter at all.
    _risk = (scalar("risk") or "").split()
    risk = (_risk[0].strip(" -") or None) if _risk else None
    fp = footprint_of(text)
    return {
        "spec_id": scalar("id"),
        "status": scalar("status"),
        "risk": risk,
        "plan": scalar("plan"),
        "lane": scalar("lane"),
        "human_approval": scalar("human_approval"),
        "acceptance_criteria": len(re.findall(r"^\s+-\s+id:\s*AC\d+", fm, re.M)),
        "footprint_declared": len(fp),
        "depends_on": len([d for d in re.findall(r"^depends_on:\s*\[(.*)\]", fm, re.M)
                           for d in d.split(",") if d.strip()]),
        "spec_bytes": len(text),
    }


def protected_touch(footprint, protected):
    """Whether a declared footprint touches any protected path. A protected touch is the single
    strongest mechanical predictor of cost in this method, because it forces an owner approval and
    therefore a wait on a human."""
    return any(f == p or f.startswith(p.rstrip("*")) for f in footprint for p in protected)


def cycles_for(events, spec_id):
    """Gate and review cycles for one spec, from the lifecycle events. Gate FAILURES are the rework
    signal and are counted separately from passes, because a change that went red three times cost
    three gate runs and an estimator that cannot see that cannot learn it."""
    mine = [e for e in events if e.get("spec_id") == spec_id
            or e.get("correlation_id") == spec_id]
    return {
        "gate_passes": sum(1 for e in mine if e.get("type") == GATE_PASS),
        "gate_failures": sum(1 for e in mine if e.get("type") == GATE_FAIL),
        "review_verdicts": sum(1 for e in mine if e.get("type") == VERDICT),
        "events_seen": len(mine),
    }


def spend_for(events, spec_id):
    """Whatever spend the log actually carries for one spec, plus an HONEST flag for whether any of
    it was recorded at all. The flag is the point: a sum of zero because nothing was spent and a sum
    of zero because nothing was ever emitted are different facts, and an estimator that cannot tell
    them apart will confidently learn from nothing."""
    mine = [e for e in events if e.get("spec_id") == spec_id
            or e.get("correlation_id") == spec_id]
    out = {f: 0 for f in SPEND_FIELDS}
    seen = False
    for e in mine:
        for f in SPEND_FIELDS:
            v = e.get(f)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[f] += v
                seen = True
    out["cost_usd"] = round(float(out["cost_usd"]), 6)
    out["spend_recorded"] = seen
    return out


def git_touched(spec_id):
    """WHAT GIT SAYS THE CHANGE FOR THIS SPEC TOUCHED: the commits naming it and the
    repo-relative paths those commits changed. ONE READER, and the reason it returns the paths
    rather than only their count is WARP-1409: the per-area cost-to-change map stands down to
    git-path attribution for a spec that declares no placement, so it needs the paths, and a
    second `git log --grep` spelled out in that module would be this repository's named
    second-spelling defect in a new place. `files_touched` below counts exactly this."""
    out = _run(["git", "log", "--format=%H", "--grep", spec_id, "--all"])
    shas = [s for s in out.split() if s]
    files = set()
    for sha in shas:
        for ln in _run(["git", "show", "--name-only", "--format=", sha]).splitlines():
            if ln.strip():
                files.add(ln.strip())
    return {"commits": sorted(shas), "files": sorted(files)}


def files_touched(spec_id):
    """How many files the change for this spec actually touched, from git rather than from the
    spec's own declaration. The DECLARED footprint is an intention and the touched set is the
    outcome; keeping both is what lets a later layer learn how far intentions drift. Counts what
    `git_touched` reads, so the corpus record and the per-area map can never disagree about
    which commits a spec's change is."""
    t = git_touched(spec_id)
    return {"commits": len(t["commits"]), "files_touched": len(t["files"])}


def build(specs_dir=None, events=None, protected=(), shipped_only=True):
    """The corpus: one record per spec, deterministic and idempotent. `events` is the parsed event
    list (the caller owns reading it, so this stays testable with seeded events and never reaches
    for the real log behind the caller's back)."""
    specs_dir = Path(specs_dir or (ROOT / "specs"))
    evs = events if events is not None else []
    out = []
    # EVERY spec, whatever prefix the repository uses. This globbed "WARP-*.md" and was the
    # only module in the package hardcoding a prefix; every sibling globs *.md. An adopter
    # following the shipped template writes VELDO-0000, matched nothing, and got an empty
    # corpus reported as a successful build.
    for p in sorted(specs_dir.glob("*.md")):
        # A FILE IN specs/ IS NOT AUTOMATICALLY A SPEC. The generated index and the templates live
        # here too. An id in the front matter is what makes one, so that is the test rather than a
        # list of filenames to skip, which would need updating every time one is added.
        if not re.search(r"(?m)^id:\s*\S+", _front_matter(p.read_text(encoding="utf-8", errors="replace"))):
            continue
        f = spec_features(p)
        if not f["spec_id"]:
            continue
        if shipped_only and f["status"] != "shipped":
            continue
        rec = {"schema": SCHEMA, "spec": f["spec_id"], "features": f}
        rec["features"]["protected_touch"] = protected_touch(
            footprint_of(p.read_text()), protected)
        rec["cycles"] = cycles_for(evs, f["spec_id"])
        rec["spend"] = spend_for(evs, f["spec_id"])
        rec["git"] = files_touched(f["spec_id"])
        out.append(rec)
    return out


def coverage(corpus):
    """HOW MUCH OF THE CORPUS IS ACTUALLY USABLE AS GROUND TRUTH, reported as a number rather than
    left for whoever first trusts an estimate to discover. `spend_known` is the count of records
    carrying ANY recorded spend; on a repository whose loop never emits it, that is zero, and a
    zero here means every later TOE layer is estimating from features and cycles alone."""
    n = len(corpus)
    spend = sum(1 for r in corpus if r["spend"]["spend_recorded"])
    cycles = sum(1 for r in corpus if r["cycles"]["events_seen"] > 0)
    return {
        "records": n,
        "spend_known": spend,
        "spend_coverage": round(spend / n, 4) if n else 0.0,
        "cycles_known": cycles,
        "cycles_coverage": round(cycles / n, 4) if n else 0.0,
        "usable_as_ground_truth": spend > 0,
    }
