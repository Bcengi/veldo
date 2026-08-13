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
  QUEUED      no complete bundle and no run claiming it, WHATEVER STATUS ITS SPEC DECLARES
  UNRECORDED  finished artifacts no run claimed, WHERE THIS REGISTRY WAS RECORDING WHEN THEY LANDED

THE TWO WORDS ABOVE IN CAPITALS ARE CORRECTIONS, EACH FROM A MEASUREMENT.
QUEUED used to be documented as "ready, unclaimed" and never filtered on the declared status:
measured here, 73 queued was 30 ready, 34 shipped, 6 draft, 1 blocked and 2 declaring nothing, and
an operator reading the count read a work queue. Deciding what QUEUED should MEAN is a change to
the taxonomy this module's spec declares, so what changed is the report: the declared status
travels with every item and report_lines prints the composition beside the count.
UNRECORDED used to be every done item no run claimed, which is a POPULATION and not a defect set.
A registry starts empty, and this one was flattened at migration, so it has claimed nothing about
work that landed before it existed: creating ONE run folder here took the report from 2 lines to
144, of which 142 were UNRECORDED lines naming specs that landed weeks earlier. The domain is now
the bundles this registry was in a position to judge, from its own earliest recorded run start and
each manifest's own produced_at, and everything else keeps its paths under a count with the reason.

AND ONE LINE THAT IS NOT A STATE. A bundle is written in two stages, the producer's manifest and
then a reviewer's verdict, so an item that is BUILT AND AWAITING REVIEW has a manifest and no
verdict - which is QUEUED, the bucket for work nobody has started, printed with no line and no
path. That is this reader answering its own scenario wrongly, so report_lines names it BUILT AND
UNREVIEWED with the path. Still no fifth state: a state is the spec's taxonomy, a line is not.

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
# DONE AND ABORTED ARE TWO ANSWERS, NOT ONE. They were collapsed into LIVENESS_DONE and
# report_lines prints only that word, so a run that ABORTED 25 hours ago was handed to an operator
# under the reassuring word for the opposite fact while `run_said` carried "aborted" into the JSON
# nobody reads first. A module whose stated discipline is that states are never collapsed may not
# collapse this one.
LIVENESS_ACTIVE = "active"
LIVENESS_BLOCKED = "blocked"
LIVENESS_DONE = "run_recorded_done"
LIVENESS_ABORTED = "run_recorded_aborted"
LIVENESS_UNCONFIRMED = "LIVENESS_UNCONFIRMED"

# The one spelling runlog writes and the only one runlog.classify reads.
RUNLOG_STAMP = "%Y-%m-%dT%H:%M:%SZ"

# WHAT THE HEARTBEAT READ ANSWERED, EACH CAUSE NAMED. An age of None used to mean three different
# things and report_lines printed the strongest available negative for all of them: "no heartbeat
# ever recorded", which this module's own docstring defines as liveness never having been confirmed
# once. MEASURED: a heartbeat stamped two seconds ago in an offset-bearing ISO spelling read as
# never-recorded, because the parser accepted exactly one spelling. So the spelling is widened AND
# the causes are separated, for the reason finding 67 records - a reader that cannot answer must
# NAME the state it is in rather than borrow the answer for a different one.
HEARTBEAT_NEVER = "no heartbeat ever recorded for this run"
HEARTBEAT_UNREADABLE = ("the heartbeat stamp %r is UNREADABLE by this reader, which is NOT the same "
                        "fact as a run that never wrote one: liveness is unconfirmed here because "
                        "the stamp could not be parsed, not because none exists")
HEARTBEAT_FUTURE = ("the heartbeat is stamped %d second(s) in the FUTURE, which is what clock skew "
                    "across the machines this registry is shared between produces, so it confirms "
                    "nothing and the age beside it is not a confirmation either")

# The stand-down reasons, each naming which half could not answer and why. A zero would not
# distinguish "no run has ever been recorded here" from "no run is in flight".
STANDDOWN_NO_REGISTRY = ("no run registry exists under the git common dir: no run has ever "
                         "recorded itself here, which is NOT the same fact as no run being in "
                         "flight, so the run half of this report answers nothing")
STANDDOWN_NO_GIT = ("the run registry root cannot be resolved because this tree has no git "
                    "common dir, so the run half of this report answers nothing")
# THE ORGAN THIS READER NEEDS IS NOT IN THIS TREE. Two of them are absent from what
# .veldo/init_scaffold.py lays down, so this is the state EVERY adopter is in until finding 61's
# other repair lands: the report says which organ it could not find and which half of the answer
# went with it, instead of exiting 1 with a traceback.
STANDDOWN_NO_ORGAN = ("the organ that declares which verdict values conclude a review "
                      "(.veldo/executor.py) is not in this tree, so DONE is unanswerable here and "
                      "no item is reported done or not done: an item's state is UNKNOWN rather than "
                      "queued, because reporting queued would state that nothing has been reviewed")
STANDDOWN_NO_RUNLOG = ("the run registry organ (.veldo/runlog.py) is not in this tree, so the run "
                       "half answers nothing: this is a different fact from no run being in flight")

# WHY UNRECORDED IS NOT EVERY UNCLAIMED BUNDLE, AND WHAT THE THREE REASONS ARE.
# UNRECORDED says "artifacts exist that no run ever claimed" and the printed line called it work a
# dead session left behind. A registry is created empty and this one was FLATTENED at migration, so
# it has claimed nothing about anything that landed before it existed. MEASURED on this repository:
# creating ONE run folder took the report from 2 lines to 144, of which 142 were UNRECORDED lines
# naming specs that landed weeks earlier, and the one genuinely interesting line - a run with a
# stale heartbeat - was buried under them. The organ whose stated product is a path to look at
# handed the operator 142 paths, all wrong.
# THE FIX IS THE DOMAIN, NOT THE COMPARISON, which is ledger findings 51 and 63. An unclaimed
# bundle is a DEFECT only if this registry WAS recording when the bundle landed, and both halves of
# that are read from bytes already on disk: the registry's earliest recorded run start, and the
# manifest's own produced_at. Everything the registry cannot speak to is reported as a COUNT WITH
# THE REASON and kept, with its paths, under unrecorded_out_of_reach - not dropped, which would be
# a confident zero, and not shouted, which is the defect above. The narrow set that remains is a
# defect set BY CONSTRUCTION, so growth cannot add to it.
OUT_OF_REACH_NO_WINDOW = ("this registry records no run with a readable start time, so it cannot "
                          "say when it began recording: an unclaimed bundle cannot be told apart "
                          "from one that predates the registry, and neither is called unrecorded")
OUT_OF_REACH_PREDATES = ("the manifest records this bundle as produced BEFORE the earliest run this "
                         "registry records (%s), so the registry was not recording when the work "
                         "landed and cannot say it went unclaimed. Each item's own produced_at is "
                         "kept beside its paths")
OUT_OF_REACH_UNDATED = ("the manifest records no readable produced_at (%r), which is not a required "
                        "proof key, so this bundle cannot be placed against the registry's window")

REPORT_KEYS = ("runs_stood_down", "runs_standdown_reason", "corpus_patterns", "items", "runs",
               "counts", "unrecorded", "unconcluded",
               # The artifact half can stand down too, for the same reason the run half can.
               "artifacts_stood_down", "artifacts_standdown_reason", "unanswerable",
               # The unclaimed bundles this registry is in no position to judge, each with the
               # reason, plus the window that decided it.
               "unrecorded_out_of_reach", "registry_recording_since",
               # WHICH COUNTS ARE NOT MEASUREMENTS, for a consumer reading the dict rather than the
               # lines. counts keeps its integer shape so no consumer breaks, and this names the
               # keys whose value is a CONSEQUENCE of a stand-down instead of a count of anything.
               "counts_unmeasurable")

# HOW THIS READER FINDS THE CORPUS PATTERNS IT WALKS: a module-level name in verdict_corpus
# ending in this suffix, whose value is a string, IS one of that module's declared corpus
# patterns. THE RULE IS THE DELEGATION. A list of the values here would be a second spelling of
# the set, and set equality between two spellings of the same constants cannot detect the copy on
# the day it is written - only on the day it drifts, which is the day it is too late. So the set
# is derived from the declaring module's own declarations, and the suite proves the delegation by
# SUBSTITUTING a verdict_corpus that declares different patterns.
CORPUS_PATTERN_SUFFIX = "_PATTERN"


ORGAN_ABSENT = "ORGAN_ABSENT"


def _sibling(name):
    """Load a sibling organ BY PATH, the idiom every organ in this directory uses. Kept to one
    place so there is one spelling of where a sibling lives."""
    spec = importlib.util.spec_from_file_location(
        "veldo_ws_" + name, ROOT / ".veldo" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sibling_or_none(name):
    """The same load, answering None when the organ is not in this tree instead of raising.

    THIS EXISTS BECAUSE THE HEADLINE COMMAND CRASHED FOR EVERY ADOPTER, and the crash was not a bug
    in the loading, it was a bug in assuming. MEASURED 2026-08-13 on a fixture carrying exactly the
    25 modules `.veldo/init_scaffold.py` lays down: `python3 .veldo/work_state.py report` exited 1
    with `FileNotFoundError: .veldo/executor.py`, because init lays this module down and lays down
    neither `executor.py` nor `runlog.py`. PLAN-0018's O1 promises an operator can ask what is done
    after a session died; every adopter got a traceback. Ledger finding 61.
    Dmitry directed BOTH repairs on 2026-08-13: init ships the two organs, AND this reader names an
    absent organ instead of dying, because the second is what protects against the NEXT one. A
    traceback out of a read model is this project's confident zero in its most expensive form - a run
    that could not look is indistinguishable from a run that found nothing."""
    path = ROOT / ".veldo" / (name + ".py")
    if not path.is_file():
        return None
    return _sibling(name)


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
    ex = _sibling_or_none("executor")
    if ex is None:
        return None      # NOT an empty set: unknown and measured-empty invite opposite decisions.
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
        out.append({"path": rel, "verdict": v,
                    # UNKNOWN, never False. With the organ that DECLARES the passing values absent,
                    # this reader does not know whether a verdict concludes; answering False would
                    # silently demote every reviewed item to not-done, which is the confident zero
                    # wearing the opposite sign.
                    "concludes": None if passing is None else v in passing})
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
    if any(r["concludes"] is None for r in recs):
        return None      # The rule is unreadable in this tree, so DONE is unanswerable, not False.
    return any(r["concludes"] for r in recs)


def manifest_produced_at(entry, root=None, vc=None):
    """WHAT THE BUNDLE ITSELF SAYS ABOUT WHEN IT WAS PRODUCED, read from the manifest's bytes the
    way the verdict is read from its own, and returned as the recorded STRING so the report can
    quote it.

    None when there is no manifest, when it cannot be read, or when it records no produced_at -
    that key is not in the required proof key set, so its absence is an ordinary state and not an
    error. None is never converted into a date: it makes the bundle unplaceable against the
    registry's window, which the report says in words."""
    vc = _sibling("verdict_corpus") if vc is None else vc
    base = Path(root) if root is not None else ROOT
    for rel in sorted(entry.get(vc.MANIFEST_PATTERN) or []):
        try:
            doc = json.loads((base / rel).read_text(errors="replace"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("produced_at"), str):
            return doc["produced_at"]
    return None


def out_of_reach_reason(produced, floor_epoch, floor_stamp):
    """Why this registry is in no position to call one unclaimed bundle UNRECORDED, or None when it
    IS in a position to. THE ONE SPELLING of that rule, so the report and its suite cannot disagree.

    The rule is about the registry's window and nothing else: it must know when it began recording,
    and the bundle must say it landed after that. Anything else is reported with the reason instead
    of as an alarm."""
    if floor_epoch is None:
        return OUT_OF_REACH_NO_WINDOW
    stamp = _parse_stamp(produced or "")
    if stamp is None:
        return OUT_OF_REACH_UNDATED % (produced,)
    if stamp < floor_epoch:
        return OUT_OF_REACH_PREDATES % (floor_stamp,)
    return None


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


def _parse_stamp(value):
    """Epoch seconds for a UTC timestamp, or None when the value is not a timestamp at all.

    MORE THAN ONE SPELLING, because refusing the second printed the strongest available negative
    about a live run. runlog writes RUNLOG_STAMP and this reader used to accept only that, so a
    heartbeat written two seconds ago in an offset-bearing ISO spelling was reported as "no
    heartbeat ever recorded". The registry lives under the git common dir, is shared across
    worktrees, and is written by whatever tooling a repository grows around it; a reader of other
    people's files that answers "never" for "I do not recognise this" is stating the reassuring
    negative about the fact it most needs to get right. A stamp with no zone is read as UTC because
    that is what runlog writes, and anything still unreadable is NAMED as unreadable by the caller
    rather than folded into the absent case."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return datetime.strptime(text, RUNLOG_STAMP).replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        pass
    iso = (text[:-1] + "+00:00") if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _heartbeat_age(state, now_epoch=None):
    """(seconds since the run's last heartbeat, NOTE) - three answers, never one bare None.

    None is NOT zero and, just as importantly, the three ways of having no age are not each other:
    a run that never wrote a heartbeat, a stamp this reader cannot parse, and a stamp from the
    FUTURE are different facts with different next actions, and all three used to arrive at
    report_lines as None or as a clamped zero. The future case is the expensive one: max(0, ...)
    turned clock skew across the machines this registry is shared between into "active, last
    heartbeat 0s ago", the most reassuring line this report can emit, from a clock it cannot
    verify. The age is still clamped so no caller sees a negative age, and the NOTE is what says
    the clamp happened."""
    hb = state.get("heartbeat_at")
    if not hb:
        return None, HEARTBEAT_NEVER
    stamp = _parse_stamp(hb)
    if stamp is None:
        return None, HEARTBEAT_UNREADABLE % (hb,)
    now = now_epoch if now_epoch is not None else time.time()
    delta = int(now - stamp)
    if delta < 0:
        return 0, HEARTBEAT_FUTURE % (-delta,)
    return delta, None


def liveness(run, now_epoch=None):
    """(answer, age, note) for one run. The RUN'S OWN terminal and blocked states are reported as it
    recorded them, and DONE and ABORTED are two of them rather than one. Everything else goes
    through the heartbeat, and a heartbeat this module cannot confirm produces LIVENESS_UNCONFIRMED
    WITH THE AGE - never a verdict about whether a process it cannot see is alive."""
    state = run.get("state") or {}
    now = time.time() if now_epoch is None else now_epoch
    age, note = _heartbeat_age(state, now_epoch=now)
    status = state.get("status")
    if status == "done":
        return LIVENESS_DONE, age, note
    if status == "aborted":
        return LIVENESS_ABORTED, age, note
    if status == "blocked":
        return LIVENESS_BLOCKED, age, note
    if age is None or note is not None:
        # A stamp that is absent, unreadable, or from the future is not a confirmation of anything,
        # so the classifier is not asked to turn it into one.
        return LIVENESS_UNCONFIRMED, age, note
    rl = _sibling("runlog")
    # ONE OWNER OF THE STALENESS RULE, ASKED IN ITS OWN SPELLING. runlog.classify owns the window
    # and reads exactly RUNLOG_STAMP; this reader now accepts more spellings than that, so the state
    # handed over is re-stamped from the age already parsed here. Re-spelling the stamp keeps the
    # window in one place, where a second staleness comparison written here would be exactly the
    # duplicate enumeration this module refuses everywhere else.
    canon = dict(state)
    canon["heartbeat_at"] = datetime.fromtimestamp(now - age, timezone.utc).strftime(RUNLOG_STAMP)
    if rl.classify(canon, now_epoch=now) == "active":
        return LIVENESS_ACTIVE, age, note
    return LIVENESS_UNCONFIRMED, age, note


def work_report(root=None, runs_root=None, now_epoch=None):
    """THE JOIN. One key shape whether the run half stood down or not, so a consumer never
    guesses whether a key is missing or genuinely empty."""
    base = Path(root) if root is not None else ROOT
    rep = {"runs_stood_down": True, "runs_standdown_reason": None,
           "artifacts_stood_down": False, "artifacts_standdown_reason": None,
           "corpus_patterns": list(corpus_patterns()), "items": {}, "runs": [],
           "counts": {s: 0 for s in STATES}, "unrecorded": [], "unconcluded": [],
           "unanswerable": [], "unrecorded_out_of_reach": [], "registry_recording_since": None,
           "counts_unmeasurable": []}

    arts = artifact_items(base)
    specs = ready_specs(base)
    # Loaded ONCE for the whole report and passed down, never once per item.
    vc = _sibling("verdict_corpus")
    passing = passing_verdicts()
    if passing is None:
        rep["artifacts_stood_down"] = True
        rep["artifacts_standdown_reason"] = STANDDOWN_NO_ORGAN

    # THE RUN HALF. It stands down loudly rather than reporting zero.
    rl = _sibling_or_none("runlog")
    claimed = {}
    if rl is None:
        rroot = None
        rep["runs_standdown_reason"] = STANDDOWN_NO_RUNLOG
    else:
        try:
            rroot = rl.runs_root(runs_root)
        except Exception:                            # noqa: BLE001 - no git, no registry root
            rroot = None
    if rl is None:
        pass                                         # reason already recorded above
    elif rroot is None:
        rep["runs_standdown_reason"] = STANDDOWN_NO_GIT
    elif not os.path.isdir(rroot):
        rep["runs_standdown_reason"] = STANDDOWN_NO_REGISTRY
    else:
        rep["runs_stood_down"] = False
        for run in rl.list_runs(runs_root):
            meta = run.get("meta") or {}
            answer, age, note = liveness(run, now_epoch=now_epoch)
            row = {"run_id": meta.get("run_id"), "spec": meta.get("spec_id"),
                   "head": meta.get("head"), "pid": meta.get("pid"),
                   "started_at": meta.get("started_at"),
                   "folder": os.path.join(rroot, str(meta.get("run_id"))),
                   "liveness": answer, "heartbeat_age_seconds": age, "heartbeat_note": note,
                   "run_said": (run.get("state") or {}).get("status")}
            rep["runs"].append(row)
            if row["spec"]:
                claimed.setdefault(row["spec"], []).append(row)

    # THE REGISTRY'S OWN WINDOW: the earliest run start it records. This is what makes UNRECORDED
    # answerable at all, and it comes from the registry's own bytes rather than from a file date.
    floor_epoch, floor_stamp = None, None
    for row in rep["runs"]:
        stamp = _parse_stamp(row.get("started_at") or "")
        if stamp is not None and (floor_epoch is None or stamp < floor_epoch):
            floor_epoch, floor_stamp = stamp, row.get("started_at")
    rep["registry_recording_since"] = floor_stamp

    # THE PARTITION. Every spec id either half knows about, in one pass.
    for sid in sorted(set(arts) | set(specs) | set(claimed)):
        entry = arts.get(sid, {})
        records = verdict_records(entry, base, vc=vc, passing=passing)
        is_done = concluded(entry, base, records=records, vc=vc, passing=passing)
        # UNANSWERABLE is not a fifth bucket, it is the ABSENCE of an answer: with the organ that
        # declares the passing verdict values missing, this reader cannot say done and cannot say
        # queued either, because queued would assert that nothing has been reviewed. The item is
        # carried with its state None and the stand-down reason above says why.
        if is_done is None:
            state = None
        else:
            state = DONE if is_done else (UNCONCLUDED if sid in claimed else QUEUED)
        rep["items"][sid] = {
            "state": state,
            "artifacts": sorted(p for paths in entry.values() for p in paths),
            "verdicts": records,
            "spec_status": (specs.get(sid) or {}).get("status"),
            "claims": claimed.get(sid, []),
            # A MANIFEST WITH NO VERDICT AT ALL IS A DISTINCT FACT and the report says so, so these
            # two travel with the item: a bundle awaiting review is BUILT, and reporting it in the
            # same silent bucket as work nobody has started is how this reader answered its own
            # scenario wrongly. produced_at is what places the bundle against the registry's window.
            "has_manifest": bool(entry.get(vc.MANIFEST_PATTERN)),
            "produced_at": manifest_produced_at(entry, base, vc=vc),
        }
        # AN UNANSWERABLE ITEM IS COUNTED IN NO BUCKET, and counted as unanswerable instead. Driven
        # 2026-08-13: incrementing counts[None] raised KeyError out of the CLI, so the repair for a
        # crash introduced a crash, reachable only with a real bundle present and invisible over the
        # empty fixture that had been used to check it.
        if state is None:
            rep["unanswerable"].append(sid)
        else:
            rep["counts"][state] += 1

    # DISAGREEMENT, IN BOTH DIRECTIONS, because they are different failures. A claim with no
    # artifacts may be half-finished work; artifacts nobody claimed COMPLETED off the record,
    # which is the 2026-08-10 shape and is invisible to any reader that walks only the registry.
    for sid, item in rep["items"].items():
        if item["state"] == UNCONCLUDED:
            rep["unconcluded"].append({"spec": sid, "claims": item["claims"]})
        elif item["state"] == DONE and not item["claims"] and not rep["runs_stood_down"]:
            # UNRECORDED ONLY WHERE THIS REGISTRY WAS RECORDING. Everything else keeps its paths and
            # carries the reason the registry cannot judge it, so nothing is dropped and nothing is
            # shouted. See the OUT_OF_REACH_ constants for the measurement that forced this.
            why = out_of_reach_reason(item["produced_at"], floor_epoch, floor_stamp)
            if why is None:
                rep["unrecorded"].append({"spec": sid, "artifacts": item["artifacts"],
                                          "produced_at": item["produced_at"]})
                rep["counts"][UNRECORDED] += 1
            else:
                rep["unrecorded_out_of_reach"].append(
                    {"spec": sid, "artifacts": item["artifacts"],
                     "produced_at": item["produced_at"], "reason": why})

    # WHICH COUNTS ARE NOT MEASUREMENTS. UNCONCLUDED is defined entirely by a registry claim, and
    # QUEUED is "not done and not claimed", so BOTH rest on the half that just announced it answers
    # nothing. With the run half stood down their integers are a consequence of the stand-down, and
    # a consumer reading counts alone would take a zero for a measurement - the confident zero this
    # organ exists to refuse, surviving inside it. report_lines refuses to print them separately.
    if rep["runs_stood_down"]:
        rep["counts_unmeasurable"] = [UNCONCLUDED, QUEUED, UNRECORDED]
    return rep


def report_lines(rep):
    """The report as lines a stranger reads after losing a session. Every line that names a
    problem also names a path, because the product of this organ is somewhere to look."""
    c = rep["counts"]
    if rep["runs_stood_down"]:
        # NO CONFIDENT ZERO IN THE HEADLINE EITHER, which is where an operator reads first. UNCONCLUDED
        # is defined entirely by a registry claim and QUEUED is "not done and not claimed", so with the
        # run half stood down neither is measured: printing "0 unconcluded" beside a stand-down states
        # a zero derived from the half that just announced it answers nothing. The two are reported as
        # ONE number with the reason, which is the honest shape of what was measured.
        lines = ["work state: %d done, %d NOT CONCLUDED - unconcluded and queued are NOT reported "
                 "separately here because both rest on a registry claim and the run half stood down, "
                 "so either zero would be a confident zero (artifacts decide done, never a run's own "
                 "word)" % (c[DONE], c[UNCONCLUDED] + c[QUEUED])]
    else:
        lines = ["work state: %d done, %d unconcluded, %d queued (artifacts decide done, never a "
                 "run's own word)" % (c[DONE], c[UNCONCLUDED], c[QUEUED])]
    # WHAT THE NOT-CONCLUDED NUMBER IS MADE OF, because the bucket's name promises something the
    # predicate does not deliver. QUEUED is every item with no complete bundle and no claim, WHATEVER
    # its spec declares, so shipped, draft and blocked specs sit in it beside genuinely ready ones and
    # the number an operator acts on reads like a work queue. MEASURED on this repository: 73 queued
    # was 30 ready, 34 shipped, 6 draft, 1 blocked and 2 declaring nothing. The status already travels
    # with each item; this prints it, rather than the report carrying a discriminator nobody sees.
    pending = {}
    for item in rep["items"].values():
        if item["state"] in (QUEUED, UNCONCLUDED):
            key = item.get("spec_status") or "(no status declared)"
            pending[key] = pending.get(key, 0) + 1
    if pending:
        lines.append("  NOT CONCLUDED by the status each spec DECLARES: %s. The bucket is 'no "
                     "complete bundle and no claim', which is NOT the same thing as ready to be "
                     "worked on"
                     % ", ".join("%s=%d" % kv for kv in sorted(pending.items())))
    # THE ARTIFACT HALF STANDS DOWN FIRST WHEN IT STANDS DOWN AT ALL, because the headline counts
    # above are its product and a reader who does not know they are unanswerable will act on them.
    # Recorded and NOT reported is the defect VELDO-0001 F2 names: with only the flag set in the
    # report dict, the three zeros above read to an operator exactly like a measurement.
    if rep.get("artifacts_stood_down"):
        lines.insert(0, "ARTIFACT HALF STOOD DOWN: %d item(s) UNANSWERABLE and counted in no bucket "
                     "above. %s" % (len(rep.get("unanswerable") or []),
                                    rep.get("artifacts_standdown_reason")))
    if rep["runs_stood_down"]:
        lines.append("  run half STOOD DOWN, recorded rather than reported as zero: %s"
                     % rep["runs_standdown_reason"])
    for row in rep["runs"]:
        age = row["heartbeat_age_seconds"]
        note = row.get("heartbeat_note")
        if age is None:
            when = note or "no heartbeat age to report and no reason recorded"
        elif note:
            when = "last heartbeat %ds ago, BUT %s" % (age, note)
        else:
            when = "last heartbeat %ds ago" % age
        # THE RUN'S OWN WORD IS PRINTED BESIDE THE ANSWER. It was carried in run_said and never
        # reached the human-readable line, which is how "aborted" arrived at an operator as a
        # liveness answer built from the word done.
        lines.append("  run %s spec %s: %s, %s. The run RECORDED status %r. Started %s at head %s, "
                     "pid %s. Look in %s"
                     % (row["run_id"], row["spec"], row["liveness"], when, row["run_said"],
                        row["started_at"], row["head"], row["pid"], row["folder"]))
    for u in rep["unconcluded"]:
        lines.append("  UNCONCLUDED %s: claimed by %d run(s) and no artifact concludes it"
                     % (u["spec"], len(u["claims"])))
    for u in rep["unrecorded"]:
        lines.append("  UNRECORDED %s: finished artifacts that NO run claimed, and this registry WAS "
                     "recording when they landed (manifest says produced_at %s, registry recording "
                     "since %s) - %s"
                     % (u["spec"], u["produced_at"], rep["registry_recording_since"],
                        ", ".join(u["artifacts"])))
    # THE UNCLAIMED BUNDLES THIS REGISTRY CANNOT JUDGE, as a COUNT PER REASON rather than as one
    # alarm each. They are not dropped: every path is under unrecorded_out_of_reach, and the reason
    # says which of them the registry could not place and why. A line each is what buried the one
    # interesting line of a 144-line report under 142 wrong ones.
    _reasons = {}
    for u in rep["unrecorded_out_of_reach"]:
        _reasons.setdefault(u["reason"], []).append(u["spec"])
    for reason, specs_out in sorted(_reasons.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append("  OUT OF THE REGISTRY'S REACH, %d finished item(s) reported as a count and not "
                     "as alarms, paths under unrecorded_out_of_reach: %s"
                     % (len(specs_out), reason))
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
    # BUILT AND AWAITING REVIEW. THE STATE THIS READER ANSWERED ITS OWN SCENARIO WRONGLY ABOUT.
    # A proof bundle is written in two stages, the producer's manifest and then a reviewer's verdict,
    # so every item that is BUILT and waiting for review has a manifest and NO verdict - and that is
    # reported QUEUED, the same bucket as work nobody has started, with no line and no path. PLAN-0018
    # measures this item by "kill a session mid-flight, start a fresh one, ask what is done, and get
    # the right answer": a fresh session asking was told the built items were queued. There is still no
    # fifth STATE, because that is a change to the taxonomy this item's spec declares; there is a LINE
    # AND A PATH, which is what the same taxonomy already does for reviewed-and-rejected.
    for sid, item in rep["items"].items():
        if item["state"] == DONE or item.get("verdicts") or not item.get("has_manifest"):
            continue
        lines.append("  BUILT AND UNREVIEWED %s: a manifest is on disk and NO verdict artifact of any "
                     "kind is, which is a bundle awaiting review rather than work nobody has started "
                     "- reported %s because a bundle with no verdict cannot be called done, so read "
                     "the path rather than the bucket: %s"
                     % (sid, item["state"] if item["state"] else "UNANSWERABLE",
                        ", ".join(item["artifacts"])))
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
