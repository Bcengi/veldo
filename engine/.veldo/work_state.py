#!/usr/bin/env python3
"""VELDO work state: what is done, what nobody concluded, and what is queued.

THE FAILURE THIS EXISTS TO PREVENT, DATED. On 2026-08-10 a session died with parallel work
in flight. Four items had been fully built. They survived because a human went looking
through worktrees. Nothing in the method could answer "what is done".

THIS HOLDS NO STATE AND WRITES NOTHING. Two sources already exist and neither answers the
question alone:

  THE ARTIFACTS, under the proof root, enumerated through .veldo/verdict_corpus.py - the one
  module that owns what a corpus path is. They say what FINISHED.

  THE RUN REGISTRY, .veldo/runlog.py, under the git common dir, outside git history and
  shared across worktrees, carrying a spec id, the head a run started from, a pid and a
  heartbeat. It says what was CLAIMED.

This is the join, with one hard rule: THE ARTIFACTS DECIDE WHAT IS DONE AND THE REGISTRY
ONLY SAYS WHAT WAS CLAIMED. A process that announced its own success and left nothing behind
is the failure mode, so its own word about itself is exactly what must not be trusted.

FOUR STATES, NEVER COLLAPSED, because the operator's next action differs in each:
  DONE        its manifest is on disk AND a verdict artifact RECORDS a passing review
  UNCONCLUDED a run claimed it and no artifact concludes it - go look at the named folder
  QUEUED      ready, and no run has claimed it
  UNRECORDED  artifacts exist that no run ever claimed - work a dead session left behind

DONE READS THE VERDICT'S BYTES, NEVER THE FILENAME. A file called verdict.json is not a
conclusion; what it RECORDS is. This reader used to call an item done because the file existed,
and measured on this repository that reported twelve REJECTED items as done, the review that
failed this very item among them. An operator told "done" about rejected work stops looking at
exactly the work that needs them, which is the same failure as the one above wearing the
opposite sign.

AND ONE THING IT CANNOT SAY, stated here so no reader infers it from the four states above:
there is NO state for REVIEWED AND REJECTED. An item whose only verdict records a rejection
falls back to UNCONCLUDED when a run claimed it and to QUEUED otherwise, and report_lines names
it with the path of the verdict that rejected it rather than leaving the operator with a bucket.
A fifth state is a change to the taxonomy this module's spec declares, so it is not made here.

AND ONE THING IT REFUSES TO SAY. It reads a heartbeat written by a process it cannot see. A
stale heartbeat means the process may have died, may be paused, or may be a moment from
writing. So a run it cannot confirm is LIVENESS_UNCONFIRMED with THE AGE OF THE HEARTBEAT,
never "running" and never "dead". Both of those would be a guess an operator would act on.
The age is the product: runlog.classify calls 31 seconds and 15 hours the same word, which is
right for liveness and useless to a person who just lost a session.
"""
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The four states. Strings, because they are printed and read by people.
DONE = "done"
UNCONCLUDED = "unconcluded"
QUEUED = "queued"
UNRECORDED = "unrecorded"
STATES = (DONE, UNCONCLUDED, QUEUED, UNRECORDED)

# The liveness answers. ACTIVE and BLOCKED are what the run itself recorded; UNCONFIRMED is
# this module declining to convert a silence into a verdict about a process it cannot see.
LIVENESS_ACTIVE = "active"
LIVENESS_BLOCKED = "blocked"
LIVENESS_DONE = "run_recorded_done"
LIVENESS_UNCONFIRMED = "LIVENESS_UNCONFIRMED"

# The stand-down reasons, each naming which half could not answer and why. A zero would not
# distinguish "no run has ever been recorded here" from "no run is in flight".
STANDDOWN_NO_REGISTRY = ("no run registry exists under the git common dir: no run has ever "
                         "recorded itself here, which is NOT the same fact as no run being in "
                         "flight, so the run half of this report answers nothing")
STANDDOWN_NO_GIT = ("the run registry root cannot be resolved because this tree has no git "
                    "common dir, so the run half of this report answers nothing")

REPORT_KEYS = ("runs_stood_down", "runs_standdown_reason", "corpus_patterns", "items", "runs",
               "counts", "unrecorded", "unconcluded")

# HOW THIS READER FINDS THE CORPUS PATTERNS IT WALKS: a module-level name in verdict_corpus
# ending in this suffix, whose value is a string, IS one of that module's declared corpus
# patterns. THE RULE IS THE DELEGATION. A list of the values here would be a second spelling of
# the set, and set equality between two spellings of the same constants cannot detect the copy on
# the day it is written - only on the day it drifts, which is the day it is too late. So the set
# is derived from the declaring module's own declarations, and the suite proves the delegation by
# SUBSTITUTING a verdict_corpus that declares different patterns.
CORPUS_PATTERN_SUFFIX = "_PATTERN"


def _sibling(name):
    """Load a sibling organ BY PATH, the idiom every organ in this directory uses. Kept to one
    place so there is one spelling of where a sibling lives."""
    spec = importlib.util.spec_from_file_location(
        "veldo_ws_" + name, ROOT / ".veldo" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def corpus_patterns():
    """THE PATTERNS THIS READER WALKS, DERIVED AT CALL TIME from the module that declares them.

    Not a copy of two values and not even a copy of two NAMES: every corpus pattern
    verdict_corpus declares is walked, found by CORPUS_PATTERN_SUFFIX, so renaming a pattern
    there, or adding one, arrives here without an edit. A hand-kept copy of today's values passes
    any equality check written against those same values, which is exactly how this repository
    has already shipped two mechanisms enumerating one set in two spellings with the gap
    invisible to both."""
    vc = _sibling("verdict_corpus")
    return tuple(sorted(v for k, v in vars(vc).items()
                        if k.endswith(CORPUS_PATTERN_SUFFIX) and isinstance(v, str) and v))


def passing_verdicts():
    """THE VERDICT VALUES THAT CONCLUDE A REVIEW, taken from the module that declares them:
    executor.PASSING_VERDICTS, whose own words are "a review verdict that lets the loop proceed to
    merge readiness. Anything else is a failed cycle". Never re-spelled here, for the reason
    corpus_patterns states: one enumeration, kept in the module that owns it."""
    ex = _sibling("executor")
    return frozenset(ex.PASSING_VERDICTS)


def artifact_items(root=None):
    """{spec id: {pattern: [paths]}} for every corpus artifact ON DISK. The artifacts are the
    only thing that makes an item DONE."""
    base = Path(root) if root is not None else ROOT
    vc = _sibling("verdict_corpus")
    out = {}
    for pattern in corpus_patterns():
        for rel in vc.disk_corpus(base, pattern):
            sid = vc.spec_id_for_verdict(rel)
            if not sid:
                continue
            out.setdefault(sid, {}).setdefault(pattern, []).append(rel)
    return out


def recorded_verdict(rel, root=None):
    """THE VERDICT ONE ARTIFACT RECORDS, read from its bytes rather than inferred from its name.

    None when the file cannot be read, is not an object, or carries no verdict string, and None is
    never treated as a conclusion: a file this reader could not read has concluded nothing. Fails
    CLOSED, because the whole point is that the reassuring answer must be earned."""
    base = Path(root) if root is not None else ROOT
    try:
        doc = json.loads((base / rel).read_text(errors="replace"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    v = doc.get("verdict")
    return v if isinstance(v, str) else None


def verdict_records(entry, root=None, vc=None, passing=None):
    """Every verdict artifact of one item WITH THE VERDICT IT RECORDS and whether that verdict
    concludes it: [{path, verdict, concludes}], in path order.

    THE PATHS ARE KEPT, because the product of this organ is somewhere to look: an item that is
    not done because it was REJECTED has to name the file that rejected it, and a count would not.

    The two sibling organs are OPTIONAL ARGUMENTS so ONE report loads them ONCE rather than once
    per item, which is measured rather than guessed: 213 items meant 643 module loads before they
    were passed in. The defaults keep this callable on its own."""
    vc = _sibling("verdict_corpus") if vc is None else vc
    passing = passing_verdicts() if passing is None else passing
    out = []
    for rel in sorted(entry.get(vc.VERDICT_PATTERN) or []):
        v = recorded_verdict(rel, root)
        out.append({"path": rel, "verdict": v, "concludes": v in passing})
    return out


def concluded(entry, root=None, records=None, vc=None, passing=None):
    """An item is CONCLUDED when a manifest is on disk AND some verdict artifact RECORDS A PASSING
    VERDICT. THE ONE SPELLING of that rule; work_report calls this rather than restating it.

    A manifest with no verdict at all is a bundle mid-write, which is a different state from
    finished. A verdict that records a rejection is a conclusion that the item is NOT done, and
    reading the file's EXISTENCE as done reported twelve rejected items on this repository as
    done. A later round that records a pass concludes it, which is how every multi-round review
    here is shaped: the failing round stays on disk as the record."""
    vc = _sibling("verdict_corpus") if vc is None else vc
    if not entry.get(vc.MANIFEST_PATTERN):
        return False
    recs = verdict_records(entry, root, vc=vc, passing=passing) if records is None else records
    return any(r["concludes"] for r in recs)


def ready_specs(root=None):
    """EVERY spec in specs/ with the status it declares: {spec id: {status, path}}. Read with one
    cheap scan of the front matter rather than the full validator, because this reader must answer
    over a tree that may not be valid: an operator asking what is done after a loss is often asking
    BECAUSE something is broken.

    IT FILTERS NOTHING, and the name is historical. This docstring used to claim it returned only
    specs declaring status ready, which was false, and an independent review filed that as a finding
    against the QUEUED bucket: shipped, draft and blocked specs land in it beside genuinely ready
    ones. The status TRAVELS with each item as spec_status so a caller can tell them apart, and the
    finding is open rather than papered over - deciding what QUEUED means is a change to the
    declared taxonomy, not a docstring edit."""
    base = Path(root) if root is not None else ROOT
    sdir = base / "specs"
    out = {}
    if not sdir.is_dir():
        return out
    for p in sorted(sdir.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        sid, status = "", ""
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines()[:60]:
            if line.startswith("id:") and not sid:
                sid = line.split(":", 1)[1].strip()
            elif line.startswith("status:") and not status:
                status = line.split(":", 1)[1].strip().split(" ")[0].strip()
            if line.strip() == "---" and sid:
                break
        if sid:
            out[sid] = {"status": status, "path": str(p.relative_to(base))}
    return out


def _heartbeat_age(state, now_epoch=None):
    """Seconds since the run's last heartbeat, or None when there is no readable heartbeat.
    None is NOT zero: it means liveness was never confirmed even once."""
    hb = state.get("heartbeat_at")
    if not hb:
        return None
    try:
        stamp = datetime.strptime(hb, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    now = now_epoch if now_epoch is not None else time.time()
    return max(0, int(now - stamp.timestamp()))


def liveness(run, now_epoch=None):
    """(answer, age) for one run. The RUN'S OWN terminal and blocked states are reported as it
    recorded them. Everything else goes through the heartbeat, and a heartbeat this module
    cannot confirm produces LIVENESS_UNCONFIRMED WITH THE AGE - never a verdict about whether
    a process it cannot see is alive."""
    state = run.get("state") or {}
    age = _heartbeat_age(state, now_epoch)
    status = state.get("status")
    if status in ("done", "aborted"):
        return LIVENESS_DONE, age
    if status == "blocked":
        return LIVENESS_BLOCKED, age
    rl = _sibling("runlog")
    if rl.classify(state, now_epoch=now_epoch) == "active":
        return LIVENESS_ACTIVE, age
    return LIVENESS_UNCONFIRMED, age


def work_report(root=None, runs_root=None, now_epoch=None):
    """THE JOIN. One key shape whether the run half stood down or not, so a consumer never
    guesses whether a key is missing or genuinely empty."""
    base = Path(root) if root is not None else ROOT
    rep = {"runs_stood_down": True, "runs_standdown_reason": None,
           "corpus_patterns": list(corpus_patterns()), "items": {}, "runs": [],
           "counts": {s: 0 for s in STATES}, "unrecorded": [], "unconcluded": []}

    arts = artifact_items(base)
    specs = ready_specs(base)
    # Loaded ONCE for the whole report and passed down, never once per item.
    vc = _sibling("verdict_corpus")
    passing = passing_verdicts()

    # THE RUN HALF. It stands down loudly rather than reporting zero.
    rl = _sibling("runlog")
    claimed = {}
    try:
        rroot = rl.runs_root(runs_root)
    except Exception:                                # noqa: BLE001 - no git, no registry root
        rroot = None
    if rroot is None:
        rep["runs_standdown_reason"] = STANDDOWN_NO_GIT
    elif not os.path.isdir(rroot):
        rep["runs_standdown_reason"] = STANDDOWN_NO_REGISTRY
    else:
        rep["runs_stood_down"] = False
        for run in rl.list_runs(runs_root):
            meta = run.get("meta") or {}
            answer, age = liveness(run, now_epoch=now_epoch)
            row = {"run_id": meta.get("run_id"), "spec": meta.get("spec_id"),
                   "head": meta.get("head"), "pid": meta.get("pid"),
                   "started_at": meta.get("started_at"),
                   "folder": os.path.join(rroot, str(meta.get("run_id"))),
                   "liveness": answer, "heartbeat_age_seconds": age,
                   "run_said": (run.get("state") or {}).get("status")}
            rep["runs"].append(row)
            if row["spec"]:
                claimed.setdefault(row["spec"], []).append(row)

    # THE PARTITION. Every spec id either half knows about, in one pass.
    for sid in sorted(set(arts) | set(specs) | set(claimed)):
        entry = arts.get(sid, {})
        records = verdict_records(entry, base, vc=vc, passing=passing)
        is_done = concluded(entry, base, records=records, vc=vc)
        state = DONE if is_done else (UNCONCLUDED if sid in claimed else QUEUED)
        rep["items"][sid] = {
            "state": state,
            "artifacts": sorted(p for paths in entry.values() for p in paths),
            "verdicts": records,
            "spec_status": (specs.get(sid) or {}).get("status"),
            "claims": claimed.get(sid, []),
        }
        rep["counts"][state] += 1

    # DISAGREEMENT, IN BOTH DIRECTIONS, because they are different failures. A claim with no
    # artifacts may be half-finished work; artifacts nobody claimed COMPLETED off the record,
    # which is the 2026-08-10 shape and is invisible to any reader that walks only the registry.
    for sid, item in rep["items"].items():
        if item["state"] == UNCONCLUDED:
            rep["unconcluded"].append({"spec": sid, "claims": item["claims"]})
        elif item["state"] == DONE and not item["claims"] and not rep["runs_stood_down"]:
            rep["unrecorded"].append({"spec": sid, "artifacts": item["artifacts"]})
            rep["counts"][UNRECORDED] += 1
    return rep


def report_lines(rep):
    """The report as lines a stranger reads after losing a session. Every line that names a
    problem also names a path, because the product of this organ is somewhere to look."""
    c = rep["counts"]
    lines = ["work state: %d done, %d unconcluded, %d queued (artifacts decide done, never a "
             "run's own word)" % (c[DONE], c[UNCONCLUDED], c[QUEUED])]
    if rep["runs_stood_down"]:
        lines.append("  run half STOOD DOWN, recorded rather than reported as zero: %s"
                     % rep["runs_standdown_reason"])
    for row in rep["runs"]:
        age = row["heartbeat_age_seconds"]
        when = "no heartbeat ever recorded" if age is None else "last heartbeat %ds ago" % age
        lines.append("  run %s spec %s: %s, %s. Started %s at head %s, pid %s. Look in %s"
                     % (row["run_id"], row["spec"], row["liveness"], when, row["started_at"],
                        row["head"], row["pid"], row["folder"]))
    for u in rep["unconcluded"]:
        lines.append("  UNCONCLUDED %s: claimed by %d run(s) and no artifact concludes it"
                     % (u["spec"], len(u["claims"])))
    for u in rep["unrecorded"]:
        lines.append("  UNRECORDED %s: finished artifacts that NO run ever claimed - %s"
                     % (u["spec"], ", ".join(u["artifacts"])))
    # REVIEWED AND NOT CONCLUDED. This report has four states and none of them says REJECTED, so
    # an item whose verdicts all record a rejection would otherwise sit silently in QUEUED beside
    # work nobody has started. It gets a line and A PATH, and the line says what the state cannot.
    for sid, item in rep["items"].items():
        if item["state"] == DONE:
            continue
        rejecting = [r for r in item.get("verdicts") or [] if not r["concludes"]]
        if not rejecting:
            continue
        lines.append("  REVIEWED AND NOT CONCLUDED %s: reported %s because no verdict on disk "
                     "records a passing review - %s. There is no state here for reviewed and "
                     "REJECTED, so read the path rather than the bucket"
                     % (sid, item["state"],
                        "; ".join("%s records %r" % (r["path"], r["verdict"]) for r in rejecting)))
    return lines


def _cli(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("report", "json"):
        print("usage: python3 .veldo/work_state.py report | json")
        return 2
    rep = work_report()
    if argv[0] == "json":
        print(json.dumps(rep, indent=1, sort_keys=True, default=str))
        return 0
    for line in report_lines(rep):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
