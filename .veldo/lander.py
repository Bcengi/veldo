#!/usr/bin/env python3
"""veldo lander: land a completed build to the trunk, serialized across the fleet.

When a worker finishes building a spec on its own branch, the built work has to reach the
trunk without colliding with the other workers landing at the same moment. The lander makes
that safe with two guarantees:

  1. SERIALIZED. A single fleet-wide land lock (a well-known unit in the claim ledger,
     WARP-0701) means only one land runs at a time. The lock is acquired by waiting, held
     with a heartbeat so a long land never looks dead, and released in a finally so a crash
     never wedges the trunk. A fast-forward-only push is the correctness backstop: even if
     the lock were ever stolen from a stalled holder, a stale push simply fails rather than
     clobbering the trunk.

  2. MERGE, NOT REWRITE. The build is MERGED into the trunk (not cherry-picked), so the
     build's implementation and evidence commits keep their shas - which is what keeps the
     proof and verdict, both digest-bound to the implementation commit, valid after landing.
     The trunk may have advanced since the build started (a prior land); the merge replays
     the build onto it, union-resolving the known shared APPEND-ONLY files (the selftest, the
     capability catalogs, the event log) and regenerating the spec index, while a conflict in
     any OTHER file is a real conflict that the build must resolve itself - the lander rejects
     it rather than guessing. The gate re-runs on the merged trunk so the combined result is
     verified, not just each build in isolation.

The lander's control logic (lock, serialize, stage order, abort-and-release, ff-push guard)
is mechanical and gate-tested here over a fake LandOps with no real git; the real git steps
live in GitLandOps. Pure stdlib; Unix-only via the claim ledger."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAND_LOCK_UNIT = "__land_lock__"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CL = _load("veldo_claim_ld", ".veldo/claim.py")

# The shared APPEND-ONLY files two lands can both touch: a union merge keeps both sides'
# additions. Everything else that conflicts is a real conflict the lander refuses to guess at.
UNION_PATHS = (
    "scripts/selftest.py",
    ".veldo/capabilities.yaml",
    "engine/.veldo/capabilities.yaml",
    ".veldo/events.jsonl",
)
# Regenerated deterministically after a merge rather than merged line-by-line.
REGEN_PATHS = ("specs/index.md",)


class LandOps:
    """The steps a land runs through, as a seam so the control logic is testable without git.
    Each returns {ok: bool, ...}. GitLandOps runs them for real; a fake drives the tests."""

    def sync_main(self):
        """Bring the local trunk up to the latest published trunk."""
        raise NotImplementedError

    def reconcile(self, unit):
        """Merge the build into the trunk, union-resolving shared append-only files and
        rejecting a real conflict (return ok False with the conflicting paths)."""
        raise NotImplementedError

    def gate(self):
        """Run the gate on the merged trunk."""
        raise NotImplementedError

    def finalize(self, unit):
        """Policy-check and fast-forward-only push. ok False if the push was rejected."""
        raise NotImplementedError


class Lander:
    """The serialized land: acquire the land lock, run the steps, release the lock. The lock
    is held with a heartbeat so a long land never looks stale, and released in a finally."""

    def __init__(self, worker_id, ops, claims_root=None, lock_timeout=600.0,
                 poll=0.02, hb_interval=None):
        self.worker_id = worker_id
        self.ops = ops
        self.claims_root = claims_root
        self.lock_timeout = lock_timeout
        self.poll = poll
        # heartbeat well under the ledger's staleness threshold so the lock stays live
        self.hb_interval = hb_interval if hb_interval is not None else CL.STALE_AFTER_SECONDS / 3.0
        self._hb_stop = None
        self._hb_thread = None

    def _heartbeat_loop(self):
        # wait() returns True when signalled to stop, False on timeout (time to heartbeat)
        while not self._hb_stop.wait(self.hb_interval):
            try:
                CL.heartbeat(LAND_LOCK_UNIT, self.worker_id, root=self.claims_root)
            except Exception:
                # a transient error (a brief filesystem hiccup) must not kill the keep-alive,
                # or the lock could silently go stale mid-land; just retry on the next tick.
                pass

    def _acquire(self):
        """Wait until the land lock is ours, then start heartbeating it. False on timeout."""
        start = time.monotonic()
        while True:
            ok, _reason = CL.claim(LAND_LOCK_UNIT, self.worker_id, [], [], root=self.claims_root)
            if ok:
                self._hb_stop = threading.Event()
                self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                self._hb_thread.start()
                return True
            if time.monotonic() - start > self.lock_timeout:
                return False
            time.sleep(self.poll)

    def _release(self):
        if self._hb_stop is not None:
            self._hb_stop.set()
        if self._hb_thread is not None:
            self._hb_thread.join(timeout=5.0)
        self._hb_stop = None
        self._hb_thread = None
        CL.release(LAND_LOCK_UNIT, self.worker_id, root=self.claims_root)

    def land(self, unit=None):
        """Land the built unit to the trunk under the land lock. Returns {ok, stage, detail}.
        A failing stage aborts the land (later stages do not run) and the lock is always
        released. Stages run in order: sync_main, reconcile, gate, finalize."""
        if not self._acquire():
            return {"ok": False, "stage": "lock"}
        try:
            stages = (
                ("sync_main", lambda: self.ops.sync_main()),
                ("reconcile", lambda: self.ops.reconcile(unit)),
                ("gate", lambda: self.ops.gate()),
                ("finalize", lambda: self.ops.finalize(unit)),
            )
            for name, fn in stages:
                r = fn() or {}
                if not r.get("ok"):
                    return {"ok": False, "stage": name, "detail": r}
            return {"ok": True, "stage": "landed"}
        finally:
            self._release()


def _conflicted_paths(repo_root):
    out = subprocess.run(["git", "-C", str(repo_root), "diff", "--name-only",
                          "--diff-filter=U"], capture_output=True, text=True)
    return [p for p in out.stdout.splitlines() if p.strip()]


def _union_resolve_one(repo_root, path):
    """Union-merge a single conflicted append-only file from its three index stages so both
    sides' added lines survive with no conflict markers, then stage the result. Returns True
    on a clean union. Returns False WITHOUT writing if the union is not safe - git merge-file
    --union always returns 0 for a text union, so a non-zero code means a binary file (or a
    genuine error), which would otherwise truncate the file to empty; the caller must reject
    the land rather than commit lost content."""
    def _stage(n):
        # git stage syntax is :N:path (1=base, 2=ours, 3=theirs); the leading colon matters.
        r = subprocess.run(["git", "-C", str(repo_root), "show", ":%d:%s" % (n, path)],
                           capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "base")
        ours = os.path.join(td, "ours")
        theirs = os.path.join(td, "theirs")
        for name, n in ((base, 1), (ours, 2), (theirs, 3)):
            with open(name, "w") as f:
                f.write(_stage(n))
        merged = subprocess.run(["git", "merge-file", "-p", "--union", ours, base, theirs],
                                capture_output=True, text=True)
        if merged.returncode != 0:
            return False
        with open(os.path.join(repo_root, path), "w") as f:
            f.write(merged.stdout)
    subprocess.run(["git", "-C", str(repo_root), "add", "--", path], check=True)
    return True


class GitLandOps(LandOps):
    """Real git land: merge the build branch into the trunk, union-resolve the shared
    append-only files, regenerate the index, gate, and fast-forward-only push."""

    def __init__(self, repo_root, build_ref, trunk="main", remote="origin", push=True):
        self.repo_root = str(repo_root)
        self.build_ref = build_ref
        self.trunk = trunk
        self.remote = remote
        self.push = push

    def _git(self, *args, check=True):
        return subprocess.run(["git", "-C", self.repo_root, *args],
                              capture_output=True, text=True, check=check)

    def sync_main(self):
        self._git("checkout", self.trunk)
        if self.push:
            self._git("fetch", self.remote, self.trunk, check=False)
            # fast-forward the local trunk to the published trunk; a non-ff means local has
            # unpushed commits (a prior land in this same process) which is fine to keep.
            self._git("merge", "--ff-only", "%s/%s" % (self.remote, self.trunk), check=False)
        return {"ok": True}

    def reconcile(self, unit):
        merge = self._git("merge", "--no-edit", "--no-ff", self.build_ref, check=False)
        conflicts = _conflicted_paths(self.repo_root)
        if not conflicts:
            return {"ok": merge.returncode == 0, "detail": merge.stderr.strip()}
        real = [c for c in conflicts if c not in UNION_PATHS and c not in REGEN_PATHS]
        if real:
            self._git("merge", "--abort", check=False)
            return {"ok": False, "conflicts": real}
        for c in conflicts:
            if c in UNION_PATHS:
                if not _union_resolve_one(self.repo_root, c):
                    # an unsafe union (a binary file) is not something to guess at either
                    self._git("merge", "--abort", check=False)
                    return {"ok": False, "conflicts": [c], "reason": "union_unsafe"}
        # regenerate any derived files deterministically rather than merging them
        subprocess.run([sys.executable, "scripts/update_index.py"], cwd=self.repo_root,
                       capture_output=True, text=True)
        self._git("add", "-A")
        self._git("commit", "--no-edit", check=False)
        return {"ok": True}

    def gate(self):
        r = subprocess.run(["./scripts/verify.sh"], cwd=self.repo_root,
                           capture_output=True, text=True)
        return {"ok": r.returncode == 0, "detail": r.stdout.strip().splitlines()[-1:]}

    def finalize(self, unit):
        pc = subprocess.run([sys.executable, ".veldo/policy_check.py"], cwd=self.repo_root,
                            capture_output=True, text=True)
        if pc.returncode != 0:
            return {"ok": False, "policy_check": pc.stdout.strip()}
        if not self.push:
            return {"ok": True, "pushed": False}
        # fast-forward-only push: if the trunk advanced under us, this fails rather than
        # clobbering it, and the land is retried from sync_main.
        push = self._git("push", self.remote, self.trunk, check=False)
        return {"ok": push.returncode == 0, "pushed": push.returncode == 0,
                "detail": push.stderr.strip()}


def veldo_land(ops, unit=None, worker_id=None, claims_root=None):
    """Front door: allocate a worker id and land the unit through ops under the land lock."""
    wid = worker_id or ("lander-" + uuid.uuid4().hex[:12])
    return Lander(wid, ops, claims_root=claims_root).land(unit)
