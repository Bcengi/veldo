#!/usr/bin/env python3
"""VELDO event envelope v1: the loop's real steps as durable, correlated events.

Events are the audit trail and the metric source. Each is a one-line JSON
object in .veldo/events.jsonl with a stable envelope: schema, a type from the
fixed vocabulary below, a timestamp, and - the part that makes events
analyzable rather than just a log - an id and a correlation_id linking every
event of one change (usually its spec id). Human-attention steps carry
human_minutes, the method's scarce-resource metric. Spend rides the same
envelope: tokens and cost_usd are optional numeric fields an event may carry,
attributed by correlation_id, so the budget reader (metrics.py) can aggregate
spend without a second store. Old events with no spend fields still parse.

Emit from code or a skill:
  python3 .veldo/events.py emit spec.ready --spec WARP-0007 --human-minutes 12
  python3 .veldo/events.py emit proof.recorded --spec WARP-0007 \\
      --commit <hash> --human-minutes 8

THE CHECK READS THE TYPE OFF THE ASSEMBLED EVENT immediately before the bytes are written,
never off an argument, and NO UNIVERSAL IS CLAIMED HERE ABOUT WHAT CANNOT LAND. The `str`
SUBCLASS route that defeated both membership tests is REFUSED now (WARP-0723 round 2): a key that
IS a str and spells a reserved name hashed elsewhere, so the dict kept BOTH entries, every lookup
read the genuine one, and the line json.loads got carried the CALLER's value; the guard reads the
spelling json.dumps will write and takes a reserved name only from an EXACT str. It needed
in-process Python, which already permits appending to this file directly, so closing it grants no
capability; a writer that never imports this module stays uncloseable, and that is the limit
declared here. THE DISTINCTION BETWEEN THE ASSEMBLED EVENT AND AN ARGUMENT is what six earlier
rounds got wrong: each guarded one WAY OF NAMING the type - the constructor, then emit()'s type
argument - and the next attacker named it another way. The type argument is not the type; `--field
type=verdict.recorded` on a shipped flag put it on the dict AFTER the check, and the line landed.
So the ONE function here that puts bytes in the log is also the one that decides, and it reads the
FINAL dict. Eligibility has three legs, all on the bytes: the type must be in the vocabulary (an
argument check missed `--field type=`, which wrote a line no validator recognises into a log nothing
may rewrite); a projection-owned type is written only on THE PROJECTION'S OWN APPEND PATH, which is
the single call site that passes the writer's `entitled` flag, so entitlement is no string a caller
can supply and emit(), --field type= and every other route cannot land such a line whatever they
declare (WARP-0731 narrowed this from a per-key git enumeration to the flag, because WARP-0730
retired the property the enumeration defended); and every RESERVED key (schema, id, type, at,
producer) must hold a value the envelope's own invariants ADMIT, which is SHAPE and not
non-settability - `--field id=aaaaaaaaaaaa` still LANDS at exit 0 with the caller's value, while
`--field schema=nope` and `--field at=`, each of which redded the gate for good, do not (WARP-0723).
make_event, the module's ONE constructor, does not refuse: building an envelope writes
nothing, and a caller that builds a line and appends it ITSELF is a writer OUTSIDE this
module, which no check inside it can reach. TWO such writers are DRIVEN in the selftest and
nothing there enumerates the rest: its mechanical completeness leg is over .sh files only, and
.veldo/reconciliation_store.py appends to this log without importing this module and is neither
named nor driven. So no exhaustiveness is claimed over the writers outside this module.
A hand-written line is one the reconciler generally cannot resolve, because nothing makes
its (commit, path) pair or its verdict_blob name an object this repository has; a
hand-written line CAN carry a well-formed blob field, so that is a tendency and not a
property, which is why the guard above is keyed on the append PATH and not on the shape of
the line. Any such line ALREADY in a log is reported BY NAME together with the `producer`
IT DECLARES, and that declared string is what the withhold decision reads: a line declaring
this projection's producer withholds that spec's appends, and one declaring anything else
withholds nothing. THE STRING IS AUTHOR-WRITTEN, so that classification is a declared
limit of an append-only log rather than a credential check, and a log that already carries
such a line cannot be rewritten.

The gate (verify.sh) and guard already append gate.* and emergency.* events
in this envelope; this module is the emitter for the human-driven steps and
the reader (metrics.py) derives the numbers.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

try:                      # POSIX advisory locking for the read-then-append window;
    import fcntl          # absent on Windows, where the lock degrades to a reported skip
except ImportError:       # pragma: no cover - platform dependent
    fcntl = None

ROOT = Path(__file__).resolve().parent.parent

# THE SIBLING .veldo MODULES THIS ONE REQUIRES, DECLARED so anything copying this file (a pack, the
# /veldo:init scaffold, a fixture) reads what to copy WITH it. A lone copy raises at import: with no
# corpus owner there is no domain, and an empty one would fail OPEN.
CORPUS_MODULE = "verdict_corpus.py"
SIBLING_MODULES = (CORPUS_MODULE,)

# THE ONE OWNER OF WHAT A PROOF-CORPUS PATH IS, loaded by path (the tracker-resolver precedent in
# validate.py). ONE WAY, so no cycle, and the contract validator loads the SAME module for the SAME
# question. Never reimplemented here; that module carries the measurement and the declared limits.
_vcspec = importlib.util.spec_from_file_location(
    "veldo_verdict_corpus", ROOT / ".veldo" / CORPUS_MODULE)
_VC = importlib.util.module_from_spec(_vcspec)
_vcspec.loader.exec_module(_VC)
VELDO_DIR = _VC.VELDO_DIR          # the engine directory, in the owner's one spelling
LOG = ROOT / VELDO_DIR / "events.jsonl"

# THE ENVELOPE'S OWN CONSTANTS (WARP-0723): the schema the gate's event validator requires, the width
# of the id this module mints, and the keys the writer takes no caller's value for - defined ONCE, so
# the mint and the guard below cannot drift apart.
SCHEMA = "veldo.event/v1"
EVENT_ID_LEN = 12
RESERVED_ENVELOPE_KEYS = ("schema", "id", "type", "at", "producer")

# The fixed vocabulary: the loop's actual steps. Adding a type is a conscious
# contract change, not an ad-hoc string, so metrics can rely on it.
EVENT_TYPES = {
    "plan.created", "plan.approved", "plan.revised", "work.pulled",
    "spec.ready", "spec.shipped", "spec.blocked",
    "gate.passed", "gate.failed",
    "proof.recorded", "review.requested", "verdict.recorded",
    "approval.recorded",
    "emergency.push", "emergency.closed",
    "merge.completed", "index.updated",
    # Run Lens durable milestones (PLAN-0005). High-volume run.step and
    # run.heartbeat are live-only (run folder live.jsonl), never committed here.
    "run.started", "run.blocked", "run.resumed", "run.done", "run.aborted",
    # The incident lifecycle (PLAN-0012 W1): an incident opens, is diagnosed from
    # artifacts, a remediation is proposed, and the incident is closed by
    # reconciliation. The contract that owns this vocabulary is .veldo/incident.py
    # (INCIDENT_EVENT_TYPES); a selftest binds the two so they cannot drift. These
    # types are emitted and validated as incidents actually flow through the
    # compressed loop (WARP-1208, W8); W1 only introduces the vocabulary.
    "incident.opened", "incident.diagnosed", "remedy.proposed", "incident.closed",
    # The human-touchpoint request lifecycle (PLAN-0016 W2): a request opens on the
    # surface and settles as accepted, rejected, or superseded; decision.decided marks a
    # settled decision-choice, which had no event before this surface. The contract that
    # owns this vocabulary is .veldo/request.py (REQUEST_EVENT_TYPES); a selftest binds
    # the two so they cannot drift. Emission and gate event-validator recognition are
    # wired when requests flow through the inbound edge (WARP-0619, W5); W2 only
    # introduces the vocabulary (a conscious contract change).
    "request.opened", "request.accepted", "request.rejected", "request.superseded",
    "decision.decided",
}


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_event(etype, commit=None, spec=None, producer="events.py",
               human_minutes=None, correlation_id=None, extra=None,
               tokens=None, cost_usd=None, account=None, at=None, event_id=None):
    """THE ONE CONSTRUCTOR, used by every caller INCLUDING the projection below.

    Round 5 split this in two - a private builder plus a public wrapper holding the
    projection-owned refusal - and left an UNGUARDED construction point beneath the guarded
    one: anything calling the private builder skipped the check entirely, and a second
    writer added under it appended an unresolvable line while the gate stayed green. There is
    one constructor again, and the refusal moved to emit(), the module's only general WRITER,
    because a constructed dict harms nothing until somebody appends it."""
    refuse_unknown_type(etype)
    # at and event_id default to now and a random id - the live-emission case. A DERIVED
    # event passes both, because a projection must be reproducible: two clones of one
    # commit have to render the same line, and a wall clock or a uuid would make them
    # differ (WARP-0722). The ONE exception is declared where it happens: an artifact that
    # declares no usable timestamp of its own leaves `at` to default to now, so that field
    # is the only one two clones may differ on - counted and reported, never the key.
    ev = {
        "schema": SCHEMA,
        "id": event_id or uuid.uuid4().hex[:EVENT_ID_LEN],
        "type": etype,
        "at": at or now_iso(),
        "producer": producer,
    }
    # correlation ties a change's events together; default to the spec/plan id
    corr = correlation_id or spec
    if corr:
        ev["correlation_id"] = corr
    if spec:
        ev["spec_id"] = spec
    if commit:
        ev["commit"] = commit
    if human_minutes is not None:
        ev["human_minutes"] = int(human_minutes)
    # spend fields ride the envelope the same optional way human_minutes does;
    # absent means the event carries no spend, so old events stay valid.
    if tokens is not None:
        ev["tokens"] = int(tokens)
    if cost_usd is not None:
        ev["cost_usd"] = float(cost_usd)
    # account attribution: a spend event carries the account it was produced under
    # (the worker's VELDO_ACCOUNT from W2), so the per-account governor (governor.py)
    # can pace each account against its OWN burn without one account's spend counting
    # against another's budget. Absent means unattributed, so old events stay valid.
    if account is not None:
        ev["account"] = str(account)
    if extra:
        ev.update(extra)
    return ev


def refuse_unknown_type(etype):
    """Raise on a type outside the vocabulary. make_event calls it on its ARGUMENT, which is
    a convenience for the caller; the writer below calls it on THE ASSEMBLED DICT, which is
    the guard - because `--field type=...` sets that field after every argument has been
    checked, so an argument check cannot see what is about to be serialised. Left unguarded,
    that route wrote a line no validator recognises into an APPEND-ONLY log, which reddens
    `validate.py all` for good."""
    if etype not in EVENT_TYPES:
        raise ValueError(f"unknown event type {etype!r} (vocabulary: {sorted(EVENT_TYPES)})")


def refuse_projection_owned(etype):
    """Raise on a type a PROJECTION owns. Mirrors the ValueError refuse_unknown_type raises,
    because this is the same kind of error: a name the writer is not entitled to use."""
    if etype in PROJECTION_OWNED:
        raise ValueError(
            "%r is DERIVED, never emitted: the review projection owns it and reconciles "
            "it from the committed verdict artifact, so commit the verdict and let the "
            "gate's review-events stage record it. Refused whatever --producer says, "
            "since the caller chooses that string." % etype)


def _is_event_id(s):
    """Whether a string has THE SHAPE of an id this module mints - EVENT_ID_LEN lowercase hex, what
    both mint sites write (a uuid4 prefix live, a digest prefix derived) - never its PROVENANCE."""
    return isinstance(s, str) and len(s) == EVENT_ID_LEN and all(c in HEX40 for c in s)


def refuse_reserved_envelope(ev, entitled=False):
    """Raise unless each RESERVED key on the ASSEMBLED event holds a value the envelope's own
    INVARIANTS ADMIT. THAT IS SHAPE, NOT NON-SETTABILITY, and the difference is measured: `--field
    at=1970-01-01T00:00:00Z`, `--field id=aaaaaaaaaaaa`, `--field producer=totally-not-me` and
    `--field type=gate.passed` each still LAND at exit 0 carrying the CALLER's value. What is refused
    is a value no envelope written here could hold: `--field schema=nope` and `--field at=` each
    exited 0, LANDED, and then red `validate.py all` and the gate PERMANENTLY, because nothing may
    rewrite this log. What is read is THE VALUE ON THE FINAL DICT, never who supplied it: THE schema
    the validator requires, an id of the SHAPE minted here (provenance is unknowable), the ONE
    timestamp format this envelope writes (the predicate the projection applies to an artifact's
    declared date), and any producer name EXCEPT the projection's own, entitled the way its type is -
    by the line's OWN content key being one this pass derived from a committed artifact. An ABSENT
    key is refused by the rule that judges its value, so nothing raises a KeyError. THE KEY is judged
    on the spelling json.dumps WILL WRITE, off str's own data so no subclass method can lie about it,
    and a reserved name is taken only from an EXACT str - CASE, SPACING or a `str` SUBCLASS fails.

    WHAT `entitled` MEANS SINCE WARP-0731, AND WHY IT IS DELIBERATELY WEAKER THAN WHAT IT REPLACED. It
    is a BOOLEAN the reconciler's own append path sets, and nothing else sets it. It used to be the
    frozenset of content keys the log's own repository produced, so a line was admitted only when git
    reported the artifact behind it as tracked in THAT repository. That check is gone: `--repo-root`
    pointed at a directory of hand-written verdict artifacts can once again cause lines to be appended
    for reviews the domain does not hold. THAT IS ACCEPTABLE ONLY BECAUSE WARP-0730 REMOVED THE VALUE
    OF FORGING ONE - verdict authority left the agent, the merge rule names no verdict, and the only
    consumers of verdict.recorded are a descriptive metric, a tracker mirror and a display. What is
    kept is the API-hygiene half: only the projection writes projection-owned events, so neither
    emit() nor `--field type=` can mint one."""
    for key in ev:
        alias = (str.__str__(key) if isinstance(key, str) else "").strip().lower()
        if alias in RESERVED_ENVELOPE_KEYS and not (type(key) is str and str.__eq__(key, alias)):
            raise ValueError("envelope key %r (%s) is a confusable spelling of reserved envelope "
                             "key %r on the written line" % (key, type(key).__name__, alias))
    for key, ok, want in (
            ("schema", ev.get("schema") == SCHEMA, repr(SCHEMA)),
            ("id", _is_event_id(ev.get("id")), "%d hex characters, the SHAPE minted here" % EVENT_ID_LEN),
            ("at", _iso_z(ev.get("at")), "YYYY-MM-DDTHH:MM:SSZ, the format this envelope writes"),
            ("producer", isinstance(ev.get("producer"), str) and ev["producer"].strip(), "a name")):
        if not ok:
            raise ValueError("reserved envelope key %s is %r, not %s, and this log is APPEND-ONLY"
                             % (key, ev.get(key), want))
    if ev["producer"] == RECONCILE_PRODUCER and not entitled:
        raise ValueError("%r is the review projection's OWN producer: a line may declare it only "
                         "on the projection's own append path" % ev["producer"])


def _append_events(fh, events, entitled=False):
    """THE ONE FUNCTION IN THIS MODULE THAT PUTS BYTES IN THE LOG, AND THE ONE PLACE
    ELIGIBILITY IS DECIDED. The two are the same function ON PURPOSE, and the selftest binds
    that WITHOUT WRITING DOWN EITHER SIDE: it discovers the scopes whose writes resolve to the
    LOG, discovers the refusals by what they DO to a projection-owned type, and requires a
    refusal on every path into every one of those scopes. So the check may be extracted into a
    helper this function calls, and the append loop may be extracted into a helper this
    function hands the handle to - both are measured green - while a second writer that opens
    the log itself and refuses nothing is RED, because it has no caller to inherit a refusal
    from. That is the arrangement round 5's hole needed: a guard on one door with an unguarded
    door beside it.

    THE TYPE IS READ OFF EACH ASSEMBLED EVENT, after every merge, update, extra dict,
    override and CLI --field has been applied, immediately before serialisation. Rounds 5 and
    6 read a NAME A CALLER PASSED instead: round 5 the constructor's argument, round 6
    emit()'s. Both were descriptions of the event, and each was defeated by naming the type
    somewhere else on the way to the same append - round 6 by `--field type=verdict.recorded`
    on a shipped flag, which sets the field after the argument was checked and landed the
    harmful line at exit 0. There is exactly one thing that cannot be renamed, and it is
    what is about to be written.

    WHY THE PARAMETER AND NOT THE PRODUCER STRING. `producer` is author-written and buys nothing:
    any caller can declare any name. `entitled` cannot be supplied from outside this module - it is
    set True on exactly one code path, the reconciler's own append, and every other caller reaches
    this function with the default False. So the rule it carries is "only the projection writes
    projection-owned events", and that rule holds against emit(), against --field type=, and against
    any flag combination, because none of them can reach the one call site that passes True.

    WARP-0731 NARROWED WHAT THIS CLAIMS, DELIBERATELY. It used to be a frozenset of content keys
    derived from git, so a line was admitted only when the artifact behind it was TRACKED in the
    repository the log belongs to. That made a forged verdict.recorded impossible to land; now it is
    merely impossible to land THROUGH THIS MODULE'S OTHER ENTRY POINTS. The difference stopped
    mattering at WARP-0730, which removed verdict authority from the agent, and the guard's own
    docstring had always declared that a shell append or a hand-edited log defeats it anyway.

    Every event is checked BEFORE any is written, so a batch carrying one ineligible line
    appends none of it. APPEND-ONLY: never rewritten, truncated or sorted."""
    for ev in events:
        etype = ev.get("type")
        refuse_unknown_type(etype)
        if etype in PROJECTION_OWNED and not entitled:
            refuse_projection_owned(etype)
        refuse_reserved_envelope(ev, entitled)
    for ev in events:
        fh.write(json.dumps(ev) + "\n")
    fh.flush()
    return events


def emit(etype, **kw):
    """Append one event through the writer above, which decides eligibility on the assembled
    dict. emit() is never entitled to a projection-owned type: it passes no keys, and no
    flag, --field, extra dict or producer string can add one. WHAT IS CLAIMED IS THAT NOTHING
    IS APPENDED, not that the file is untouched: opening in append mode CREATES an empty log
    if none exists, which is what the next allowed event would have created anyway. Round 6
    claimed the refusal ran `before it opens the log`, and buying that sentence is what put
    the check on an argument."""
    ev = make_event(etype, **kw)
    with open(LOG, "a") as f:
        _append_events(f, [ev])
    return ev


# ---------------------------------------------------------------------------
# The review projection (WARP-0722): verdict.recorded events DERIVED from the
# verdict artifacts that already exist, in code the gate always runs.
#
# Before this, every event in the log was gate.* from the gate script and NOT ONE
# verdict artifact had an event, because a skill file asked whoever ran a review to
# append one. Nobody ever did. So the events are not emitted at review time by
# someone who remembers: they are RECONCILED from the committed artifact, by the
# gate, on every run. The verdict FILE is the durable thing; the event is its
# projection.
#
# THE KEY IS THE ARTIFACT'S OWN BLOB SHA, which is to say the event is keyed to the
# REVIEW rather than to the file that carries it. Round 1 of this item keyed on the
# path plus the sha of the commit that ADDED it, and an independent review broke that
# key twice, both times against this repository's own verdict convention:
#   AMEND IN PLACE. This repository OVERWRITES a verdict across review rounds and
#     copies the earlier round out under its own name. Keyed on a path's first add and
#     read there, the log asserted a result the committed artifact contradicts, and an
#     append-only log can never take that back.
#   CLONE DEPTH. In a shallow repository the add-commit lookup attributes every path to
#     the grafted tip, so a `--depth 1` clone of ONE commit derived a different key for
#     EVERY artifact - AC2's own refutation clause, and the default of actions/checkout.
#     A blob sha is a property of CONTENT: measured, the whole `git ls-files -s` output
#     is BYTE-IDENTICAL between a full clone and a --depth 1 clone of one commit.
# A content key also survives a RENAME (the blob does not move) and needs no history
# walk at all, so the derivation now reads only what the commit itself contains.
#
# WHAT IS NOT UNIVERSAL, STATED WITH THE UNIVERSAL RATHER THAN TWO LINES LATER: every
# SUBSTANTIVE field is content-derived, so two clones of one commit render byte-identical
# events - FOR EVERY ARTIFACT THAT DECLARES A reviewed_at THIS ENVELOPE CAN CARRY. An
# artifact that declares none, or declares one in another legal ISO form, is dated at
# RECONCILIATION instead: its `at` is then the single field two clones may differ on, it
# is COUNTED and reported on the stage line, and the KEY is unaffected either way. The
# shipped verdict example declares no reviewed_at, so this is a reachable case and not a
# theoretical one, and `.veldo/validate.py` does not require the field (an artifact-side
# rule that would require it, and would also close the tamper surface below, is a
# CONTRACT TIGHTENING with its own item: it would redden an adopter's gate on historical
# verdict records nobody may edit).
#
# THE `at` IS AUTHOR-CONTROLLED AND VALIDATED NOWHERE, WHICH IS A DECLARED COST. Nothing
# checks a verdict's reviewed_at for format, plausibility, or agreement with the commit
# that added the artifact - this module makes no history call at all - so 1970 and 2099
# both commit green and land verbatim in an append-only log, and this repository's own
# corpus carries a review whose reviewed_at (2026-07-28T09:30:00Z) was a day AHEAD of the commit that recorded it. It is accepted because
# `at` is PAYLOAD and never key, so no key, count or result can move: the worst a forged
# timestamp can do is misorder a chronology. Every other substantive field (the verdict,
# the round, the reviewer, the reviewed commit) is equally author-chosen, and the guard
# that matters most - the verdict vocabulary - sits on the ARTIFACT in validate.py, which
# is where a reviewed_at guard belongs too.
#
# Five properties this owes, and where each is kept:
#   DOMAIN, derived not remembered - the tracked corpus verdict_corpus.py enumerates at run
#     time (`git ls-files` over the proof root, ONE membership rule, no wildcard on either
#     side), so it grows with the repository. This code carries no corpus count today and
#     a selftest binds its literals to the owner's own constants scope by scope, with
#     that check's own blindness declared where it is made; `no count can ever be
#     hardcoded here` is NOT claimed, because a new use of an already-allowed value
#     inside a scope that already declares it is invisible to it.
#   IDEMPOTENCE - the key is (type, spec id, blob sha). An amended artifact is a
#     DIFFERENT review and gets its own event, which is what an append-only log
#     should say; the superseded event stays, because it was true when it was written.
#   HONEST ABOUT WHAT IT CANNOT KEY - an artifact staged but not committed, and a
#     LEGACY event whose (commit, path) pair this repository can no longer resolve,
#     are both NAMED and skipped rather than guessed at. The second is what makes a
#     shallow clone append nothing here instead of duplicating the whole backfill.
#   ONE WRITER OF PROJECTION-OWNED EVENTS - reconcile_verdicts is the only caller that may
#     append a verdict.recorded, enforced at the writer by a flag no other route can set.
#     WARP-0731 removed the stronger rule that used to sit here (each derived key had to be a
#     MEMBER of the enumeration the log's own repository produces) because WARP-0730 retired
#     the property it defended. See the note where log_entitlement used to live.
#   NEVER A JUDGMENT - reconciliation appends and REPORTS. It does not fail the gate
#     on anything it finds, because a stage that reddens the build over its own
#     bookkeeping makes the first run after it lands unlandable. What it does instead
#     is publish an integrity line carrying EVERY non-zero signal the report holds:
#     deferrals, unresolvable legacy events of its own and foreign ones, appends
#     withheld, duplicate keys already in the log, absorbed artifacts, superseded
#     reviews, events dated at reconciliation, a foreign-repository refusal, the lock
#     state, and whether the repository is shallow.
# ---------------------------------------------------------------------------

# THE DOMAIN IS NOT ENUMERATED HERE (WARP-0727). verdict_corpus.py owns what a corpus path IS and the
# validator enumerates through the SAME module: two mechanisms computing one set differ in the gap
# between them and NEITHER CAN SEE THE GAP.
# AND IT OWNS THE ANCHORING, WHICH IS NOT A CONSTANT AND CANNOT BE ONE: the proof root belongs to
# THE VELDO ROOT that owns this log, so `corpus_pathspec` resolves that root's own prefix from git
# and every read is anchored there. ONE anchoring - the PAIR that shipped at bdb4055 named
# different directories whenever VELDO sits below the top of its repository, and a verdict forged
# at the outer proof root was then entitled to append to the vendored log. NO WILDCARD: it names
# a DIRECTORY under `:(top,literal)`. The owner carries the measurement.
corpus_pathspec = _VC.corpus_pathspec
VERDICT_EVENT = "verdict.recorded"
RECONCILE_PRODUCER = "events.py reconcile-verdicts"
HEX40 = set("0123456789abcdef")
# The index modes of a REGULAR FILE, re-exported from the corpus owner that reads the index and
# applies them: a tracked symlink or gitlink at a verdict path is DEFERRED with its mode named.
INDEX_FILE_MODES = _VC.INDEX_FILE_MODES
# THE TYPES ONLY A PROJECTION MAY WRITE. verdict.recorded is a PROJECTION: the reconciler
# below derives it from the committed artifact, and the writer admits a line of this type
# ONLY when the line's own content key is one that pass derived. The `producer` field is
# never consulted, because it is a string the caller supplies (the CLI even takes it as a
# flag) and teeth held by the constrained party are not teeth.
PROJECTION_OWNED = frozenset({VERDICT_EVENT})
# THE TWO SUPPORTED RESOLVERS FOR AN OLD-FORM EVENT, DECLARED AS A VOCABULARY so that a
# reader, a report and a test can name which one answered WITHOUT anything requiring a
# particular one to run. Both are supported, a selftest proves they agree, and which one
# serves is a property of the git on the box: an assertion that demanded the batch was a
# false red on this module behaving exactly as designed.
ROUTE_BATCH = "batch"
ROUTE_PER_EVENT = "per-event"
ROUTE_NONE = ""                 # there was no old-form event to resolve
LEGACY_ROUTES = (ROUTE_BATCH, ROUTE_PER_EVENT, ROUTE_NONE)


def _git(args, repo_root=None):
    """One git read, returning stdout only when git actually succeeded. An empty
    answer and a failed call are told apart by _git_ok; callers that cannot act on a
    failure use this one and find nothing to do, which they then report."""
    return _git_ok(args, repo_root)[0]


def _git_ok(args, repo_root=None):
    """(stdout, ok). `git rev-parse <commit>:<path>` for a commit a SHALLOW clone does
    not have exits 128 and echoes its argument back, so a caller must check ok AND the
    shape of what it got - never the text alone."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=str(repo_root or ROOT),
                           capture_output=True, text=True)
    except OSError:
        return "", False
    return (r.stdout, True) if r.returncode == 0 else ("", False)


def _is_sha(s):
    return len(s) == 40 and all(c in HEX40 for c in s)


def is_shallow(repo_root=None):
    """Whether this is a shallow repository. Reported rather than acted on: the
    derivation itself is depth-independent, and what a shallow clone actually costs is
    the ability to resolve a LEGACY event, which is detected where it happens."""
    return _git(["rev-parse", "--is-shallow-repository"], repo_root).strip() == "true"


def tracked_verdicts(repo_root=None):
    """THE DOMAIN: every verdict artifact TRACKED IN GIT, enumerated at run time so it grows
    with the repository and this code never carries a count.

    THE ROOT DEFAULTS HERE, WHERE ROOT IS KNOWN, NEVER IN THE OWNER, which is path-agnostic and
    takes its root as a REQUIRED argument: when that default lived there it was the PROCESS CWD,
    and this module invoked by absolute path from a directory that is no repository enumerated 0
    where the code it replaced enumerated the whole corpus. DELEGATED, NOT REIMPLEMENTED: one
    rule over two sources at one anchoring."""
    return _VC.tracked_corpus(repo_root or ROOT, _VC.VERDICT_PATTERN)


def verdict_blob_map(repo_root=None):
    """(path -> blob sha of its COMMITTED content, note, excluded) for the tracked verdicts this
    repository can key. DELEGATED to the corpus owner, the only module that talks to git about the
    corpus, so the index this reads and the domain entitlement is decided by are ONE enumeration."""
    return _VC.committed_blobs(repo_root or ROOT, _VC.VERDICT_PATTERN)


# THE SPEC ID A CORPUS PATH CARRIES, from the module that owns what a corpus path IS: it is the
# MIDDLE of the three components the membership rule counts, so the shape is read in ONE place.
spec_id_for_verdict = _VC.spec_id_for_verdict


def verdict_key(spec_id, blob, etype=VERDICT_EVENT):
    """THE IDEMPOTENCE KEY: (type, spec id, blob sha). Content-addressed, so it is
    identical at every clone depth, it changes when the review changes, and it does not
    move when the file is renamed. The PATH is recorded on the event but is NOT part of
    the key, which is what makes a rename append nothing."""
    return (etype, spec_id, blob)


def event_verdict_key(ev):
    """The key of an event already in the log, read off the blob it carries. Returns
    None for an OLD-FORM event (no verdict_blob), which has to be resolved through git
    instead - see legacy_event_key. That absence is the version discriminator: it needs
    no schema bump and no rewrite of a log nothing may rewrite."""
    blob = ev.get("verdict_blob") or ""
    if not _is_sha(blob):
        return None
    return (ev.get("type") or "", ev.get("spec_id") or "", blob)


def legacy_event_key(ev, repo_root=None):
    """The key of an OLD-FORM verdict event, resolved EXACTLY: the blob that its
    (commit, path) pair names. None when the object is absent, which is precisely what
    a shallow clone cannot resolve - and the caller must then withhold that spec's
    appends rather than guess, because it cannot know what the log already covers.
    Resolved by identity rather than by comparing the recorded verdict value, which
    would suppress a genuinely new review that happens to carry the same result."""
    commit, path = ev.get("commit") or "", ev.get("verdict_path") or ""
    if not commit or not path:
        return None
    out, ok = _git_ok(["rev-parse", "%s:%s" % (commit, path)], repo_root)
    blob = out.strip()
    if not ok or not _is_sha(blob):
        return None
    return verdict_key(spec_id_for_verdict(path), blob, ev.get("type") or "")


def read_log(log_path=None):
    """Every parseable event in the log. A line that does not parse is skipped rather
    than raised on: this is bookkeeping, and it never breaks the caller."""
    p = Path(log_path) if log_path else LOG
    out = []
    try:
        text = p.read_text(errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict):
            out.append(ev)
    return out


def _batch_blob_shas(revs, repo_root=None):
    """Resolve MANY `<commit>:<path>` revs to blob shas in ONE git call.

    `git cat-file --batch-check -z` answers one line per input, in input order, with
    `<input> missing` for an object this repository does not have - which is exactly what
    a shallow clone says about a commit it never fetched. Input is NUL-delimited so a path
    holding a space or a newline arrives intact; what makes a SHORT or reordered answer
    safe is the length guard below, not the delimiter. Returns a list as long as revs (a
    sha or None per entry), or None ENTIRELY when the batch could not run or came back
    ragged, so the caller falls back to resolving one at a time rather than reading a
    short answer as absence.

    ONE SUBPROCESS INSTEAD OF ONE PER EVENT. The per-event form spent a whole
    `git rev-parse` on every old-form event and most of this stage's wall clock on process
    startup, on every gate run, which is the same shape WARP-0711 spent five rounds
    removing from the lint stage. No corpus figure is written here: the corpus grows, so a
    number in a comment is a number that goes stale. The measurements live in
    proof/WARP-0722/manifest.json, each against the revision it was taken at."""
    if not revs:
        return []
    try:
        r = subprocess.run(["git", "cat-file", "--batch-check", "-z"],
                           cwd=str(repo_root or ROOT), input="".join(x + "\0" for x in revs),
                           capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    lines = r.stdout.splitlines()
    if len(lines) != len(revs):        # a ragged answer is not an answer
        return None
    out = []
    for line in lines:
        parts = line.split()
        out.append(parts[0] if len(parts) >= 2 and parts[1] == "blob" and _is_sha(parts[0])
                   else None)
    return out


def _resolve_old_form(events, resolved, repo_root=None):
    """Fill in the keys of the OLD-FORM events in place and name the route that answered.
    Extracted so logged_verdict_state states one thing: what the log covers. Returns a
    member of LEGACY_ROUTES: ROUTE_BATCH for the one `cat-file --batch-check` call,
    ROUTE_PER_EVENT for the equivalent fallback, ROUTE_NONE when there was no old-form
    event to resolve at all. The answer is the same either way; the route is reported so
    the fallback cannot become the normal path unnoticed, never so anything can demand
    one of them."""
    old = [i for i, k in enumerate(resolved) if k is None]
    if not old:
        return ROUTE_NONE
    batch = _batch_blob_shas(["%s:%s" % (events[i].get("commit") or "",
                                        events[i].get("verdict_path") or "")
                              for i in old], repo_root)
    for n, i in enumerate(old):
        ev = events[i]
        if batch is None:
            resolved[i] = legacy_event_key(ev, repo_root)
        elif batch[n] and ev.get("commit") and ev.get("verdict_path"):
            resolved[i] = verdict_key(spec_id_for_verdict(ev["verdict_path"]), batch[n],
                                      ev.get("type") or "")
    return ROUTE_PER_EVENT if batch is None else ROUTE_BATCH


def logged_verdict_state(log_path=None, repo_root=None):
    """What the log already covers: (keys, duplicates, unresolved, route). keys is the set
    of verdict keys present, duplicates counts the events whose key was already seen (the
    log is append-only, so a duplicate is reported and never removed), unresolved lists
    (spec id, path, PRODUCER) for every event whose key git could not recover, and route is
    the member of LEGACY_ROUTES naming which resolver answered for the old-form events.

    THE DECLARED PRODUCER TRAVELS WITH THE UNRESOLVED ENTRY BECAUSE IT DECIDES WHAT THE
    ENTRY MEANS. An event declaring THIS projection covers a review whose identity is
    unrecoverable here, so the caller cannot know what the log already holds for that spec
    and must withhold it. An event declaring any other producer is treated as covering no
    review, so it withholds nothing and is only reported. THAT FIELD IS AUTHOR-WRITTEN and
    this is not a credential check: it is the only discriminator an append-only log offers
    for a line written before the content key existed. A hand-written line declaring this
    projection's producer therefore withholds that spec - which no route through this module
    can append any more, and which a log already carrying one cannot take back.

    The old-form events are resolved in ONE batch call; if that call cannot run, each is
    resolved on its own through legacy_event_key, which is the same answer by a slower
    route (a selftest asserts the two agree over this repository's whole log)."""
    events = [e for e in read_log(log_path) if e.get("type") == VERDICT_EVENT]
    resolved = [event_verdict_key(e) for e in events]
    route = _resolve_old_form(events, resolved, repo_root)
    keys, dupes, unresolved = set(), 0, []
    for ev, key in zip(events, resolved):
        if key is None:
            unresolved.append((spec_id_for_verdict(ev.get("verdict_path") or ""),
                               ev.get("verdict_path") or "<no path>",
                               ev.get("producer") or "<no producer>"))
            continue
        if key in keys:
            dupes += 1
        keys.add(key)
    return keys, dupes, unresolved, route


def verdict_domain(repo_root=None):
    """The projection's domain, partitioned. Returns (derivable, deferred) where
    derivable is a list of (key, path, blob) for every tracked verdict this repository
    has COMMITTED, and deferred is a list of (path, reason) for the rest, each carrying
    the reason it could not be keyed rather than one message that covers several."""
    blobs, note, excluded = verdict_blob_map(repo_root)
    derivable, deferred = [], []
    for path in tracked_verdicts(repo_root):
        blob = blobs.get(path)
        if blob:
            derivable.append((verdict_key(spec_id_for_verdict(path), blob), path, blob))
        else:
            deferred.append((path, note or excluded.get(path)
                             or "no usable index entry for this path"))
    return derivable, deferred


def veldo_root_for_log(log):
    """THE VELDO ROOT THAT OWNS A LOG: the directory whose proof corpus that log is the projection
    of, and the one root the domain is enumerated at. DELEGATED to the corpus owner, because the
    anchoring and the root it is taken from are one question and answering them in two modules is
    how they come apart. It is NOT the repository root: VELDO vendored below the top of a larger
    repository has its own corpus and its own log."""
    return _VC.veldo_root(log)


# WARP-0731 REMOVED `log_entitlement` FROM HERE, and the removal is worth a note because the
# function was the product of nine build rounds. It enumerated, on every reconciliation, the
# verdict keys the log's own repository produced via git, and refused to append any derived line
# whose key was not a member. That made a forged verdict.recorded unlandable through this module.
#
# WARP-0730 retired the property it defended: verdict authority left the agent, the merge rule
# names no verdict, and nothing authoritative reads verdict.recorded - the consumers are a
# descriptive tally in metrics.py, a tracker mirror, a display, a known-type whitelist and the
# emitter. The guard's own docstring had also always declared that a shell append or a hand-edited
# log defeats it, so the tally it appeared to protect was never actually protected.
#
# What survives is the API-hygiene half, now a boolean on the append path: only the projection
# writes projection-owned events. See `_append_events`.


def verdict_event(key, path, blob, repo_root=None):
    """One derived verdict.recorded event. EVERY substantive field comes from the
    artifact's own bytes AT THE BLOB THE KEY NAMES, read with `git cat-file blob`, and no
    field is read from history - so two clones of one commit render byte-identical events
    at any depth, EXCEPT for the `at` of an artifact that declares no usable reviewed_at,
    which is the one field the fallback below leaves to the clock.
      at       the review's OWN reviewed_at when the artifact declares one in this
               envelope's timestamp format (every verdict in this repository does today,
               and the SHIPPED verdict example declares none, so the other branch is
               reachable); otherwise the reconciliation time, which is COUNTED and
               reported, because inventing a date for a review is worse than admitting
               the artifact carries none. A declared value in another legal ISO form is
               DROPPED rather than carried, so this envelope writes one format only. The
               `at` of a projection is the time of the thing projected, not the time
               somebody noticed it - and it is author-controlled and validated nowhere,
               which the section header declares.
      commit   the commit the VERDICT SAYS IT REVIEWED, which is what `commit` means
               everywhere else in this envelope. The superseded key recorded the commit
               that happened to ADD the file: a different fact, and a shallow clone
               cannot even see it.
    A field the artifact does not carry is omitted, never invented."""
    try:
        v = json.loads(_git(["cat-file", "blob", blob], repo_root) or "{}")
    except ValueError:
        v = {}
    if not isinstance(v, dict):
        v = {}
    extra = {"verdict_path": path, "verdict_blob": blob}
    for field in ("verdict", "reviewed_at"):
        if isinstance(v.get(field), str) and v[field]:
            extra[field] = v[field]
    if isinstance(v.get("round"), int):
        extra["round"] = v["round"]
    at = extra.get("reviewed_at")
    if at is not None and not _iso_z(at):
        del extra["reviewed_at"]
        at = None
    commit = v.get("commit") if isinstance(v.get("commit"), str) and v.get("commit") else None
    digest = hashlib.sha256("\x00".join(key).encode()).hexdigest()[:EVENT_ID_LEN]
    # make_event, the module's ONE constructor, the same one every other caller uses: the
    # refusal is on the BYTES, in _append_events, and this projection is entitled there only
    # because the key below is one it derived from a committed artifact in this pass.
    return make_event(VERDICT_EVENT, commit=commit, spec=key[1] or None,
                      producer=RECONCILE_PRODUCER, extra=extra, at=at, event_id=digest)


def _iso_z(s):
    """Whether a string is a timestamp in the ONE format this envelope writes - THAT
    format, not a neighbour of it. A review's declared date is carried only if it is;
    otherwise the event is dated at reconciliation and said to be.

    strptime ALONE IS NOT THAT TEST, which is why this is a round trip. CPython compiles
    its directives case-insensitively and with single-OR-double-digit numeric fields, so
    `2026-1-2T3:4:5Z` and a lowercase `t` or `z` all parse - and would then be written
    VERBATIM into an append-only log that .veldo/metrics.py's parse_iso cannot read and
    that sorts wrongly against every canonical line beside it. Rendering the parsed value
    back and requiring the exact input admits one spelling per instant."""
    try:
        t = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return False
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") == s


def _lock(fh):
    """An EXCLUSIVE, NON-BLOCKING lock over the log for the read-then-append window.
    Non-blocking on purpose: a stage that can wait forever is worse than one that
    appends on the next run, so a held lock makes this run append nothing and say so.
    Returns False when the lock is held or when this platform has no fcntl."""
    if fcntl is None:
        return False
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _reconcile_pass(log, derivable, deferred, repo_root, fh, entitled=False):
    """One reconciliation: read what the log covers, append what it does not, report
    everything either way. fh is the locked handle to append through, or None for a
    pass that only reports, and entitled says this is the projection's OWN append path -
    the one caller allowed to write projection-owned events."""
    present, dupes, unresolved, route = logged_verdict_state(log, repo_root)
    # WHOSE unresolvable event withholds work, and whose does not, decided on the producer
    # the line DECLARES. One declaring this projection stands for a review of that spec the
    # log already covers, and since the reconciler cannot tell WHICH, it withholds that spec
    # rather than guess. One declaring anything else is treated as covering no review and is
    # REPORTED BY NAME instead. Before this split, one line written by hand for a real spec
    # id withheld every future genuine review of that spec, on every run, in every clone, in
    # a log nothing may rewrite - while the gate stayed green. No route through this module
    # can append such a line any more; this is the other half, for the logs that already
    # carry one. THE DECLARED LIMIT, stated where the decision is made rather than two files
    # away:
    # the producer field is author-written, so this classification is not a credential check
    # and a line declaring this projection's producer is believed.
    ours = [u for u in unresolved if u[2] == RECONCILE_PRODUCER]
    foreign = [u for u in unresolved if u[2] != RECONCILE_PRODUCER]
    blocked_specs = {spec for spec, _path, _producer in ours}
    # DEDUPED BY KEY, not only against the log: two byte-identical artifacts of one spec
    # share ONE key, and appending both would make THIS code the writer of a duplicate that
    # nothing can withdraw - which is the refutation AC2 names. The absorbed artifact is
    # counted and reported instead. Found by the fixture that exercises the collapse.
    pending, _seen = [], set(present)
    for _t in derivable:
        if _t[0] in _seen:
            continue
        _seen.add(_t[0])
        pending.append(_t)
    withheld = [t for t in pending if t[0][1] in blocked_specs]
    pending = [t for t in pending if t[0][1] not in blocked_specs]
    events = [verdict_event(*t, repo_root=repo_root) for t in pending]
    if fh is not None and events:
        _append_events(fh, events, entitled)
    current = {t[0] for t in derivable}
    return {
        "domain": len(derivable) + len(deferred),
        "derivable": len(derivable),
        # two byte-identical artifacts of one spec are ONE review and share ONE key, so
        # one is absorbed. Nothing was lost that a reader could have told apart, but the
        # count is published rather than left to be noticed.
        "collapsed": len(derivable) - len(current),
        "deferred": [list(d) for d in deferred],
        "already_present": len(current & present),
        "appended": len(events) if fh is not None else 0,
        "pending": len(events),
        "withheld": [list(t[0]) for t in withheld],
        "unresolved_legacy": [[spec, path] for spec, path, _producer in ours],
        "unresolvable_foreign": [list(u) for u in foreign],
        "legacy_route": route,
        "duplicate_keys_in_log": dupes,
        "superseded": len(present - current),
        "dated_at_reconciliation": sum(1 for ev in events if "reviewed_at" not in ev),
        "shallow": is_shallow(repo_root),
        # THE NAMED CAUSE, DERIVED FROM WHAT THIS PASS MEASURED rather than from the commit count.
        # A migration flattens the history, so the commits the earlier events name were never
        # written here and, unlike a shallow clone, cannot be fetched. That is the fact: events
        # this repository cannot resolve, in a repository that is not shallow. The first version
        # of this asked whether the repository holds exactly one commit, which made the notice
        # disappear on the successor's own first commit while all 154 events stayed unresolvable,
        # and an independent review caught it by committing once and watching the cause vanish.
        "flattened": bool(ours) and not is_shallow(repo_root),
        "lock": "",
        # WHAT THE ONE MEMBERSHIP RULE DID NOT ADMIT, BY NAME: a narrowing that drops a genuine
        # artifact silently is the inverse harm of the forgery it prevents. Contract stage reds.
        # ONE ROOT REACHES BOTH HALVES and the owner has no second parameter to take another:
        # this passed its own root for the disk walk and the PROCESS CWD for the git read.
        "misfiled": _VC.misfiled(Path(repo_root).resolve() if repo_root else ROOT),
        "keys": [list(t[0]) for t in derivable],
        "events": events,
    }


def reconcile_verdicts(repo_root=None, log_path=None, dry_run=False):
    """Reconcile the event log against the verdict artifacts, and REPORT. Appends one
    verdict.recorded event per committed verdict artifact whose review the log does not
    already carry, so running the gate N times adds each review exactly once and the
    one-time backfill of everything that predates this happens on the first run. THIS IS THE ONE
    CALLER THAT MAY WRITE A PROJECTION-OWNED EVENT: it is the only code path that passes
    entitled=True into the append, so emit(), --field type= and every other route are refused at
    the writer. Returns a report; it decides nothing about the build.

    WARP-0731 removed the git-enumeration check that also ran here (`log_entitlement`), along with
    the `unentitled` report field and the exit code 2 it drove. See the note where that function
    used to live."""
    log = Path(log_path) if log_path else (
        Path(repo_root).resolve() / VELDO_DIR / "events.jsonl" if repo_root else LOG)
    derivable, deferred = verdict_domain(repo_root)
    if dry_run:
        # NOTHING IS ATTEMPTED AND NOTHING IS CREATED ON THE WAY to not attempting it, which is
        # why the mkdir sits after this and not before: a dry run that still makes a directory
        # somewhere a caller named is a dry run that acted.
        return _reconcile_pass(log, derivable, deferred, repo_root, None)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a+") as fh:
        if not _lock(fh):
            rep = _reconcile_pass(log, derivable, deferred, repo_root, None)
            rep["lock"] = ("held by another reconciliation" if fcntl is not None
                           else "no fcntl on this platform, appending skipped")
            return rep
        # IS THIS HANDLE THE FILE `log` NAMES? `veldo_root` reads the log's PARENT, so a symlink at
        # the FINAL component does not move the root it computes, while this open follows it. The
        # domain would be enumerated for one repository and the bytes appended to another's file.
        # Asking the DESCRIPTOR rather than the name is also what closes a swap between check and
        # write, because a second look at a string can find a different file by then.
        same, why = _VC.handle_is_the_named_file(fh, log)
        if not same:
            rep = _reconcile_pass(log, derivable, deferred, repo_root, None)
            rep["identity"] = why
            return rep
        return _reconcile_pass(log, derivable, deferred, repo_root, fh, True)


def _report_line(rep):
    """One line the gate prints: what was found, what was appended, and every integrity
    signal that is not zero. Nothing here is a verdict on the build."""
    line = ("review events: %d verdict artifact(s) tracked, %d already recorded, %d %s"
            % (rep["domain"], rep["already_present"], rep["pending"],
               "appended" if rep["appended"] else "derivable but not appended"))
    if rep.get("identity"):
        line += ", NOT APPENDED: %s" % rep["identity"]
    if rep["deferred"]:
        line += (", %d deferred (%s)"
                 % (len(rep["deferred"]),
                    "; ".join("%s: %s" % (p, why) for p, why in rep["deferred"][:2])))
    if rep["unresolved_legacy"]:
        # NAMED, not counted, exactly as the deferred branch above names its paths: the
        # module, every capability copy and AC2 all say an unresolvable event is reported
        # BY NAME, and a bare integer is not a name.
        line += (", %d earlier event(s) this repository cannot resolve (%s) so %d append(s) WITHHELD"
                 % (len(rep["unresolved_legacy"]),
                    "; ".join(p for _spec, p in rep["unresolved_legacy"][:2]),
                    len(rep["withheld"])))
        if rep.get("flattened"):
            # ONLY where something is withheld: a notice printed on every run is one a reader
            # learns to skip.
            line += (" - FLATTENED AT MIGRATION: the commits those earlier events name are absent"
                     " from this history and cannot be fetched, so the appends stay WITHHELD"
                     " rather than being re-pointed at a commit where the review did not happen")
        if rep["shallow"]:
            line += " (shallow repository: clone with --depth 0 to reconcile)"
    if rep.get("unresolvable_foreign"):
        line += (", %d unresolvable verdict event(s) NOT written by this projection (%s), "
                 "withholding nothing"
                 % (len(rep["unresolvable_foreign"]),
                    "; ".join("%s by %s" % (p, producer)
                              for _spec, p, producer in rep["unresolvable_foreign"][:2])))
    if rep["duplicate_keys_in_log"]:
        line += ", %d duplicate key(s) already in the log" % rep["duplicate_keys_in_log"]
    if rep.get("collapsed"):
        line += (", %d artifact(s) absorbed by an identical review already keyed"
                 % rep["collapsed"])
    if rep["superseded"]:
        line += ", %d superseded review(s) on record" % rep["superseded"]
    if rep["dated_at_reconciliation"]:
        # A BARE COUNT ON PURPOSE. This bucket holds two causes the section header above
        # keeps apart - an artifact declaring no reviewed_at, and one declaring a legal ISO
        # form this envelope does not write - so a parenthetical naming only the first was
        # FALSE about most of the artifacts that reach here.
        line += ", %d dated at reconciliation" % rep["dated_at_reconciliation"]
    if rep.get("misfiled"):
        # NAMED, never counted alone: somebody must see WHICH artifact stopped being recorded.
        line += (", %d verdict-shaped file(s) at a path the corpus rule does not admit, so NOT"
                 " recorded (%s) - the contract stage is red on these"
                 % (len(rep["misfiled"]), "; ".join(rep["misfiled"][:2])))
    if rep["lock"]:
        line += ", NOT appended (%s)" % rep["lock"]
    return line


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("emit")
    e.add_argument("type")
    e.add_argument("--commit")
    e.add_argument("--spec")
    e.add_argument("--producer", default="events.py")
    e.add_argument("--human-minutes", type=int)
    e.add_argument("--tokens", type=int, help="spend: tokens this event accounts for")
    e.add_argument("--cost-usd", type=float, help="spend: cost in USD this event accounts for")
    e.add_argument("--account", default=os.environ.get("VELDO_ACCOUNT"),
                   help="spend: the account this event was produced under (default: $VELDO_ACCOUNT)")
    e.add_argument("--correlation-id")
    e.add_argument("--field", action="append", default=[],
                   help="extra key=value pairs")
    r = sub.add_parser("reconcile-verdicts",
                       help="derive the verdict.recorded events the verdict artifacts imply")
    r.add_argument("--repo-root", help="reconcile another repository (tests, clones)")
    r.add_argument("--log", help="reconcile another event log (tests)")
    r.add_argument("--dry-run", action="store_true",
                   help="report what WOULD be appended and append nothing")
    r.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args()
    if args.cmd == "reconcile-verdicts":
        # NEVER a gate decision: this returns 0 whatever it finds, including when it
        # cannot read or write the log at all. It appends and REPORTS BY NAME; a missing
        # event is bookkeeping, and a stage that judged the build on its own bookkeeping
        # would make the first run after it lands unlandable.
        try:
            rep = reconcile_verdicts(repo_root=args.repo_root, log_path=args.log,
                                     dry_run=args.dry_run)
        except Exception as ex:                       # noqa: BLE001 - reported, never raised
            print("   review events: not reconciled (%s: %s)" % (type(ex).__name__, ex))
            return 0
        print(json.dumps(rep, sort_keys=True) if args.json else "   " + _report_line(rep))
        # WHAT IT FINDS IS BOOKKEEPING AND EXITS 0. WARP-0731 removed the only non-zero exit
        # this command had: exit 2 meant "derived keys were refused because the log's own
        # repository does not track them", and that check went with the forgery guard. The
        # gate's stage guards this call with `||` and touches no FAIL either way.
        return 0
    if args.cmd == "emit":
        extra = {}
        for kv in args.field:
            k, _, v = kv.partition("=")
            extra[k.strip()] = v.strip()
        try:
            # THE CLI IS THE HAND-EMISSION DOOR AND NEEDS NO GUARD OF ITS OWN BECAUSE THE GUARD IS
            # ON THE BYTES: `--field` names ANY envelope field and is applied AFTER every argument
            # passed here, which is how round 6's argument check was defeated. The WRITER refuses,
            # reading the finished dict - the type, and every RESERVED key's value (WARP-0723:
            # `--field schema=nope` and `--field at=` each landed here at exit 0). Exit 2 either way.
            ev = emit(args.type, commit=args.commit, spec=args.spec,
                      producer=args.producer, human_minutes=args.human_minutes,
                      correlation_id=args.correlation_id, extra=extra or None,
                      tokens=args.tokens, cost_usd=args.cost_usd, account=args.account)
        except ValueError as ex:
            print(str(ex))
            return 2
        print(json.dumps(ev))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
