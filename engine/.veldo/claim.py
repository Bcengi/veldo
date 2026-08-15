#!/usr/bin/env python3
"""VELDO claim ledger: the atomic self-dividing coordination primitive for the fleet.

Independent vanilla workers claim units of work (a spec id, or a review id) with no
central coordinator. A claim is a file under the git common dir at veldo/claims/<unit>.json
(shared across worktrees, outside git history) carrying the holder, its requirements, and
a heartbeat. Two rules make the pool self-divide safely:

  - A claim is granted under a SINGLE per-unit lock that arbitrates the whole decision:
    a live claim by another worker is refused, and otherwise (unclaimed, stale, corrupt,
    or our own) a FULLY-WRITTEN record is published with an atomic os.replace. One lock for
    every claimer means two workers racing for a unit produce exactly one winner and a claim
    that turned fresh while a contender waited is refused, never clobbered; a live claim is
    never stolen. Readers stay lock-free and safe because os.replace is an atomic rename.
  - A claim is granted only when the unit's requirements are a subset of the worker's
    capabilities, so capability-gated work (iOS on a Mac, GPU on a GPU box) routes right.

ONE ID, ONE RECORD. Both rules above are per unit, and a unit IS its id: the record lives at
veldo/claims/<basename>.json and the lock that arbitrates it at <basename>.json.lock. So a unit
id that is not its own basename would share a record, and therefore a lock, with every other id
that maps onto the same basename - and for that pair the whole guarantee of this module is void:
a live claim on either refuses the other (a unit nobody can take) and a release of either drops
the claim the other one is still working under (two workers, one unit). Every path that resolves
a record therefore REFUSES such an id loudly (UnitIdError) instead of addressing somebody else's
record, and callers that mint their own ids ask unit_id_problem() before they mint.

A claim whose heartbeat is older than STALE_AFTER_SECONDS is presumed dead and is
reclaimable by another capable worker. Pure stdlib, but fcntl-based takeover locking makes
this module Unix-only (Linux and macOS, the fleet's target machines); the claims root
resolves from git but is overridable for tests. This is the claim mechanics only; WHICH units are claimable
(across plans, bugs, reviews, and a worker's scope) is Y2 (WARP-0702)."""
import contextlib
import fcntl
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone

STALE_AFTER_SECONDS = 90

# VELDO-0015: a heartbeat AHEAD of the reader's clock by more than this is not "alive", it is a
# CLOCK DISAGREEMENT, and liveness is unanswerable. Generous on purpose: NTP-grade skew plus a
# write-read latency never approaches two minutes, so an alarm here is a real broken clock and
# never noise. The window below (STALE_AFTER_SECONDS) still owns the past direction; this owns the
# future one, and the two directions are different questions with different answers - stale may be
# reclaimed, unanswerable may NOT (finding 76: the one-line symmetric window hands a LIVE claim to
# a second worker, which is worse than the lockout it fixes).
CLOCK_SKEW_TOLERANCE_SECONDS = 120


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_epoch():
    return datetime.now(timezone.utc).timestamp()


def claims_root(override=None):
    """Resolve veldo/claims under the git common dir (shared across worktrees), or an
    explicit override (VELDO_RUNS_ROOT env or argument) for tests."""
    root = override or os.environ.get("VELDO_RUNS_ROOT")
    if not root:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"], text=True).strip()
        root = os.path.join(os.path.abspath(common), "veldo")
    return os.path.join(root, "claims")


def _safe(unit_id):
    """A filesystem-safe basename for a unit id (spec/review id)."""
    s = re.sub(r"[^A-Za-z0-9._-]", "_", str(unit_id))
    return s or "_"


class UnitIdError(ValueError):
    """A unit id this ledger cannot store faithfully, raised rather than returned as a claim
    reason. 'claimed' and 'capability' are ARBITRATION answers about a real unit; this is a
    malformed key, and folding the two into one vocabulary would let a caller read its own bug
    as somebody else holding the work."""


def ledger_basename(unit_id):
    """The basename this ledger stores unit_id's claim record under, without the .json suffix.

    PUBLIC because the ledger's key space is the ledger's own fact. A caller that mints unit
    ids (an authored task id, say, rather than a format-checked spec id) has to be able to ask
    whether two of the ids it accepts are ONE record here, and a copy of the character rule at
    the call site would be two enumerations of one set."""
    return _safe(unit_id)


def unit_id_problem(unit_id):
    """Why unit_id cannot be a key in this ledger, or None.

    THE INVARIANT: a unit id is its OWN ledger basename. Two ids that differ but share a
    basename are one record and one lock, so for that pair this module guarantees nothing: a
    live claim on either refuses the other, and a release of either frees both. A store that
    silently conflates two keys is worse than one that refuses a key, because the conflation
    stays invisible until two workers are already inside one unit of work."""
    if not isinstance(unit_id, str) or not unit_id:
        return ("a unit id must be a non-empty string, got %r: this ledger keys a claim by the "
                "id's own text, so two values that merely print alike would be one record"
                % (unit_id,))
    base = ledger_basename(unit_id)
    if base != unit_id:
        return ("unit id %r is stored under the basename %r, so it would SHARE ONE CLAIM RECORD "
                "with every other id that maps onto %r: a live claim on either would refuse the "
                "other and a release of either would free both. Use an id made only of letters, "
                "digits, '.', '_' and '-'" % (unit_id, base, base))
    return None


def _path(unit_id, root=None):
    """The record path for unit_id, or a REFUSAL. Every read and write path resolves a record
    through here, so an id that cannot be stored faithfully can never reach another unit's
    record from any of them: the one place that knows the mapping is the one place that
    enforces it being injective."""
    problem = unit_id_problem(unit_id)
    if problem is not None:
        raise UnitIdError(problem)
    return os.path.join(claims_root(root), ledger_basename(unit_id) + ".json")


def capability_ok(worker_caps, unit_reqs):
    """A claim is grantable only when every requirement is in the worker's capabilities."""
    return set(unit_reqs or []) <= set(worker_caps or [])


def _read(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def liveness(rec, now_epoch=None):
    """One of "live", "stale", "unanswerable" for a claim record (VELDO-0015).

    "stale" means the reclaim rule applies: no heartbeat, an unreadable one, or one older than
    STALE_AFTER_SECONDS. "unanswerable" means the heartbeat is AHEAD of this reader's clock by
    more than CLOCK_SKEW_TOLERANCE_SECONDS: the clocks disagree, no liveness answer is honest,
    and the only safe verdicts are refuse-to-grant and refuse-to-reclaim, with the word surfaced
    so a human looks at a clock. Within tolerance, a slightly-future heartbeat is ordinary skew
    and is "live", so a healthy fleet cannot be flooded with false alarms."""
    hb = (rec or {}).get("heartbeat_at")
    if not hb:
        return "stale"
    try:
        hb_epoch = datetime.strptime(hb, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return "stale"
    now = now_epoch if now_epoch is not None else _now_epoch()
    if (hb_epoch - now) > CLOCK_SKEW_TOLERANCE_SECONDS:
        return "unanswerable"
    return "stale" if (now - hb_epoch) > STALE_AFTER_SECONDS else "live"


def _is_stale(rec, now_epoch=None):
    """May this claim be RECLAIMED? Boolean contract unchanged (VELDO-0015): unanswerable answers
    False here, because "cannot judge" must never authorize a takeover - that is the silent
    double-build. Only a genuinely stale claim may be taken over."""
    return liveness(rec, now_epoch) == "stale"


def _record(unit_id, worker_id, requirements):
    return {
        "unit_id": unit_id,
        "worker_id": worker_id,
        "requirements": list(requirements or []),
        "claimed_at": _now(),
        "heartbeat_at": _now(),
    }


@contextlib.contextmanager
def _unit_lock(path):
    """Hold the per-unit lock (flock) for the whole duration of a write-side decision, so
    claim, heartbeat, and release all serialize on ONE arbiter per unit and no write path
    can publish underneath another. Distinct units use distinct lock files and never contend.
    The lock file (<unit>.json.lock) is not a claim record and is ignored by the readers."""
    os.makedirs(os.path.dirname(path), exist_ok=True)  # so heartbeat/release on a cold
    # claims root do not raise before any claim has created the directory
    lf = os.open(path + ".lock", os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(lf, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lf, fcntl.LOCK_UN)
        os.close(lf)


def _publish(d, path, rec):
    """Publish a record to path with an atomic os.replace (a rename), so a lock-free reader
    always sees a complete old-or-new file. Called only while holding the unit lock. The temp
    is written in the same directory (so the rename is atomic) and cleaned up on any failure."""
    tmp = os.path.join(d, ".tmp.%d.%s" % (os.getpid(), uuid.uuid4().hex))
    with open(tmp, "w") as f:
        f.write(json.dumps(rec, indent=2) + "\n")
    try:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def claim(unit_id, worker_id, worker_caps=None, requirements=None, root=None):
    """Try to claim unit_id for worker_id. Returns (ok, reason).

    Grants only if requirements are a subset of worker_caps AND the unit is unclaimed,
    stale, or already held by this worker. Reasons: 'granted', 'capability' (worker
    lacks a required capability), 'claimed' (held live by another worker), 'unanswerable'
    (VELDO-0015: the holder's heartbeat is ahead of this clock beyond tolerance, so liveness
    cannot be judged; the claim is neither granted nor reclaimable until a human acts or the
    clocks agree).

    Atomicity: a SINGLE per-unit lock (flock) arbitrates the WHOLE claim decision, so the
    fresh-publish and the stale/corrupt/own takeover share one arbiter and can never both
    grant the unit. Under the lock we read the current record and refuse only a live claim by
    another worker; otherwise (unclaimed, stale, corrupt, or our own) we publish our fully-
    written record with an atomic os.replace. Because every claimer serializes on the one
    lock, no unlocked path can publish a competing claim underneath a contender, so a claim
    that turned fresh while we waited is refused, never clobbered. Readers (is_claimed,
    holder, claimed_units) are lock-free and still safe: os.replace is an atomic rename, so a
    reader always sees a complete old-or-new record, never a half-written one."""
    if not capability_ok(worker_caps, requirements):
        return False, "capability"
    d = claims_root(root)
    os.makedirs(d, exist_ok=True)
    path = _path(unit_id, root)
    with _unit_lock(path):
        cur = _read(path)
        if cur is not None and cur.get("worker_id") != worker_id:
            verdict = liveness(cur)
            if verdict == "unanswerable":
                # VELDO-0015: clocks disagree beyond tolerance. Not "claimed" - that word tells an
                # operator to wait, and waiting cannot fix a broken clock. The named refusal is the
                # summons: a human looks at a clock, or releases the claim deliberately.
                return False, "unanswerable"
            if verdict == "live":
                return False, "claimed"  # a live claim by another worker is never stolen
        # Unclaimed, stale, corrupt, or our own: publish our record atomically. os.replace
        # works whether or not the target exists, and we hold the sole arbiter for this unit,
        # so no other claimer can publish underneath us between the read and the replace.
        _publish(d, path, _record(unit_id, worker_id, requirements))
        return True, "granted"


def heartbeat(unit_id, worker_id, root=None):
    """Refresh the heartbeat if this worker holds the claim. Returns True on success. Runs
    under the per-unit lock so a heartbeat cannot clobber a concurrent takeover: if the claim
    was taken over (or removed) since we last saw it, the owner check fails and we do not
    write, rather than overwriting the new holder's record with our refreshed one."""
    path = _path(unit_id, root)
    with _unit_lock(path):
        cur = _read(path)
        if not cur or cur.get("worker_id") != worker_id:
            return False
        cur["heartbeat_at"] = _now()
        _publish(os.path.dirname(path), path, cur)
        return True


def release(unit_id, worker_id, root=None):
    """Release this worker's claim. Returns True if released; False if not the holder. Runs
    under the per-unit lock so a release cannot remove a claim that was taken over by another
    worker since we last saw it: the owner check and the remove are one atomic decision."""
    path = _path(unit_id, root)
    with _unit_lock(path):
        cur = _read(path)
        if not cur or cur.get("worker_id") != worker_id:
            return False
        try:
            os.remove(path)
        except OSError:
            return False
        return True


def holder(unit_id, root=None):
    """Return the worker id currently holding a LIVE claim on unit_id, else None."""
    cur = _read(_path(unit_id, root))
    if not cur or _is_stale(cur):
        return None
    return cur.get("worker_id")


def is_claimed(unit_id, root=None):
    """Whether unit_id has a LIVE claim (a stale claim reads as not claimed)."""
    return holder(unit_id, root) is not None


def claimed_units(root=None):
    """The set of unit ids with a LIVE claim (stale claims excluded)."""
    d = claims_root(root)
    if not os.path.isdir(d):
        return set()
    out = set()
    for name in os.listdir(d):
        if not name.endswith(".json"):
            continue
        cur = _read(os.path.join(d, name))
        if cur and not _is_stale(cur):
            out.add(cur.get("unit_id"))
    return out
