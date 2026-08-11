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


def _path(unit_id, root=None):
    return os.path.join(claims_root(root), _safe(unit_id) + ".json")


def capability_ok(worker_caps, unit_reqs):
    """A claim is grantable only when every requirement is in the worker's capabilities."""
    return set(unit_reqs or []) <= set(worker_caps or [])


def _read(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _is_stale(rec, now_epoch=None):
    hb = (rec or {}).get("heartbeat_at")
    if not hb:
        return True
    try:
        hb_epoch = datetime.strptime(hb, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return True
    now = now_epoch if now_epoch is not None else _now_epoch()
    return (now - hb_epoch) > STALE_AFTER_SECONDS


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
    lacks a required capability), 'claimed' (held live by another worker).

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
        if cur is not None and cur.get("worker_id") != worker_id and not _is_stale(cur):
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
