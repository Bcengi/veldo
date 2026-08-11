#!/usr/bin/env python3
"""veldo fleet: launch and elastically size a pool of workers, governed by the token pacer.

`veldo fleet N` runs up to N workers that pull work from the global frontier and land it, with
the token governor (WARP-0706) deciding how many should actually be active right now so the
budget is used without running out. This module is the elastic CONTROL LOOP:

  - Each tick it asks a controller for the desired worker count (the governor's pacing), caps
    it at N, and RECONCILES the active pool to that target - spawning workers when scaling up,
    retiring them when scaling down. Spawning and retiring are an injected WorkerSpawner seam.
  - When the target is zero it distinguishes two cases: the frontier is DRAINED (no work left)
    -> stop and retire all; or the governor is BACKING OFF (budget spent or a limit) while work
    remains -> wait until the governor's resume time, then RE-CHECK the desired count before
    doing anything (so it never resumes straight into the limit).

Two hard constraints shape this:
  - NEVER a detached or headless process. A worker is a real in-session Claude Code worker
    (the same in-session parallel mechanism a human session uses), so the WorkerSpawner's real
    implementation spawns in-session and the multi-account path is a DOCUMENTED PROCEDURE (one
    session per account, CLAUDE_CONFIG_DIR on Linux), not an auto-spawner this module runs.
  - The resume WAIT is an injected seam too, so the gate never sleeps and the opt-in in-session
    waiter is wired by the caller - the loop itself only decides WHEN to wait and re-check.

Grouping is just a scope (a plan id, a label, or a workspace) threaded to every worker. Pure
stdlib control logic; the governor and frontier it consumes are the real read models."""
import importlib.util
import os
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ACCT = _load("veldo_accounts_fl", ".veldo/accounts.py")


class WorkerSpawner:
    """The seam the launcher scales through. The real implementation (InSessionSpawner below)
    starts an IN-SESSION worker, never a detached process; a fake drives the gate. spawn returns
    an opaque handle the launcher hands back to retire."""

    def spawn(self, worker_id, scope):
        raise NotImplementedError(
            "inject a WorkerSpawner; a worker is an in-session session, never a detached process")

    def retire(self, handle):
        raise NotImplementedError


class SpawnPrimitiveError(RuntimeError):
    """Raised by the reference spawn primitive: with no in-session start wired it FAILS LOUD
    rather than fabricate a handle or detach a process."""


class NoAccountAvailableError(RuntimeError):
    """The account spreader was asked for more accounts than are registered - the fleet must be
    capped at the account count so one account is never run as two workers at once."""


def in_session_start(worker_id, env):
    """The fail-loud reference spawn primitive, and the DEFAULT when no in-session mechanism is
    wired. A VELDO worker is a vanilla IN-SESSION Claude Code session (feedback_no_rogue_processes,
    PLAN-0007 NG1): this module NEVER launches a detached or headless process. With no in-session
    start mechanism wired, the reference FAILS LOUD - it does not fabricate a handle and does not
    detach. The REAL fill is WorktreeInSessionStart below (a git-worktree-isolated worker started
    through an injected in-session dispatch); a human without it follows the documented one session
    per account procedure by hand:

        CLAUDE_CONFIG_DIR=<the account profile> claude   # one vanilla session per account

    env carries the worker's assembled environment (its account CLAUDE_CONFIG_DIR, worker id,
    scope, capabilities)."""
    raise SpawnPrimitiveError(
        "no in-session worker start wired for %s: a VELDO worker is a vanilla in-session Claude "
        "Code session, never a detached process. Inject an in-session start primitive, or run "
        "the documented one session per account by hand: %s=%s claude"
        % (worker_id, ACCT.CONFIG_DIR_ENV, (env or {}).get(ACCT.CONFIG_DIR_ENV, "<unset>")))


class WorktreeError(RuntimeError):
    """A git worktree provisioning or teardown step failed: fail loud rather than start a worker
    with no isolation or leak a worktree - never fabricate isolation."""


def _git_worktree(args, cwd=None):
    """Run ONE synchronous, in-line `git worktree` command and return its stdout. This is the ONLY
    external program this module ever runs, and it is git, never a worker: subprocess is imported
    LAZILY here (never at module top) and used only to run `git worktree`, exactly as the fleet
    supervisor's runner imports subprocess lazily and only ever runs systemctl. It is a blocking
    in-line call that completes and returns - it detaches NOTHING, backgrounds NOTHING, and starts
    no worker process (feedback_no_rogue_processes, PLAN-0007 NG1). A non-zero exit FAILS LOUD."""
    import subprocess  # lazy, git-only: provision an isolated worktree, never start a worker
    proc = subprocess.run(["git", "worktree"] + [str(a) for a in args],
                          cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise WorktreeError("git worktree %s failed (rc=%d): %s"
                            % (args[0] if args else "?", proc.returncode, (proc.stderr or "").strip()))
    return proc.stdout


class WorktreeProvisioner:
    """Provisions a git-worktree-isolated workspace per worker and tears it down on retire. A git
    worktree is a real checkout on its own path sharing the one .git, so each worker edits in
    isolation and lands through the serialized lander - the SAME isolation a human running parallel
    sessions uses (the WARP-0406 ephemeral-env idea applied to the worker's source tree). It starts
    NO worker: it only prepares, and later removes, the isolated directory the injected in-session
    dispatch works in.

      add(worker_id) -> path   an in-line `git worktree add` at a fresh per-worker path
      remove(path)             an in-line `git worktree remove --force`, idempotent

    base_dir (VELDO_WORKTREE_DIR, else a stable per-repo temp dir) holds the worktrees OUTSIDE the
    repo working tree. Real git calls run only on this reference path; the gate drives a fake
    provisioner, so no worktree is ever created there."""

    def __init__(self, repo_root=None, base_dir=None):
        self.repo_root = str(repo_root or ROOT)
        self.base_dir = base_dir or os.environ.get("VELDO_WORKTREE_DIR") or os.path.join(
            tempfile.gettempdir(), "veldo-worktrees",
            os.path.basename(self.repo_root.rstrip("/")) or "repo")

    def path_for(self, worker_id):
        return os.path.join(self.base_dir, str(worker_id))

    def add(self, worker_id):
        path = self.path_for(worker_id)
        os.makedirs(self.base_dir, exist_ok=True)
        _git_worktree(["add", "--detach", path], cwd=self.repo_root)
        return path

    def remove(self, path):
        if not path:
            return
        try:
            _git_worktree(["remove", "--force", path], cwd=self.repo_root)
        except WorktreeError:
            pass  # teardown is best-effort and idempotent: a missing worktree is not an error


class WorktreeInSessionStart:
    """The REAL fill for the WorkerSpawner start seam: provision a git-worktree-isolated workspace
    and start an IN-SESSION worker in it, NEVER detaching. It is used as the InSessionSpawner's
    `start` (its __call__) and its `stop`, so a spawn provisions the worktree and dispatches the
    worker and a retire stops the worker cooperatively and removes the worktree.

    The actual worker-agent launch is AGENT-MEDIATED: dispatch(worker_id, env, worktree) starts the
    worker through the coordinator's in-session parallel mechanism - a worktree-isolated in-session
    worker that DIES WITH THE SESSION, the same mechanism a human session uses to run parallel work.
    This module starts no worker process of its own: a pure-Python spawn could only launch a worker
    by DETACHING, which is forbidden (feedback_no_rogue_processes, PLAN-0007 NG1), so the launch is a
    REFERENCE the coordinator provides at runtime. With no dispatch wired it FAILS LOUD (delegating
    to in_session_start), never fabricating a handle and never detaching; and a dispatch that returns
    no worker also fails loud rather than fake a running worker, and its worktree is removed so none
    leaks. env carries the worker's account CLAUDE_CONFIG_DIR (threaded by the spawner), id, scope,
    and capabilities."""

    def __init__(self, dispatch, provisioner=None, dispatch_stop=None, repo_root=None):
        self._dispatch = dispatch
        self._dispatch_stop = dispatch_stop
        self._prov = provisioner or WorktreeProvisioner(repo_root=repo_root)

    def __call__(self, worker_id, env):
        if self._dispatch is None:
            return in_session_start(worker_id, env)   # no in-session mechanism wired: FAIL LOUD
        worktree = self._prov.add(worker_id)           # in-line git worktree, never a detached process
        try:
            worker = self._dispatch(worker_id, env, worktree)   # agent-mediated in-session launch
        except Exception:
            self._prov.remove(worktree)                # no leaked worktree on a failed start
            raise
        if worker is None:
            self._prov.remove(worktree)
            raise SpawnPrimitiveError(
                "in-session dispatch started no worker for %s: it must return an in-session worker "
                "handle, never None; refusing to fabricate a handle or detach a process" % worker_id)
        return {"worker_id": worker_id, "worktree": worktree, "worker": worker}

    def stop(self, handle):
        """Retire: stop the in-session worker cooperatively (it stops pulling work; there is no kill
        of a detached process because none was started) and remove its worktree. Idempotent."""
        rec = handle if isinstance(handle, dict) else {}
        if self._dispatch_stop is not None and rec.get("worker") is not None:
            self._dispatch_stop(rec.get("worker"))
        self._prov.remove(rec.get("worktree"))


class AccountSpreader:
    """Divides the registered accounts across workers, ONE account per worker. assign() hands out
    the next free account and marks it in use; release(name) returns it to the pool. It never
    gives the same account to two live workers, and fails loud when the pool is exhausted, so the
    caller caps the fleet at capacity() rather than doubling an account onto two workers. A single
    pinned name is just a one-account pool (one worker)."""

    def __init__(self, names):
        self._all = list(names)
        self._free = list(names)
        self._in_use = set()

    def capacity(self):
        return len(self._all)

    def assign(self):
        if not self._free:
            raise NoAccountAvailableError(
                "no free account: %d registered, all in use (cap the fleet at %d workers, one "
                "account per worker)" % (len(self._all), len(self._all)))
        name = self._free.pop(0)
        self._in_use.add(name)
        return name

    def release(self, name):
        if name in self._in_use:
            self._in_use.discard(name)
            self._free.append(name)


class InSessionSpawner(WorkerSpawner):
    """The REAL fill for the WorkerSpawner seam: assemble each worker's environment (its account's
    CLAUDE_CONFIG_DIR, worker id, scope, capabilities), start it through an INJECTED in-session
    primitive, track the handle, and retire it, releasing the account back to the pool. It NEVER
    spawns a detached or headless process: the actual start is start(worker_id, env), an injected
    in-session mechanism (a fake in the gate; the reference in_session_start FAILS LOUD). Account
    selection is one account per worker via the AccountSpreader, so a multi-account fleet is N
    concurrent one-account workers self-dividing the one frontier through the claim ledger."""

    def __init__(self, start, selector, capabilities=None, stop=None, accounts_root=None):
        self._start = start
        self._selector = selector
        self._caps = list(capabilities or [])
        self._stop = stop
        self._accounts_root = accounts_root
        self._handles = {}   # worker_id -> record

    def _assemble_env(self, worker_id, scope, account):
        """The worker's environment. Point CLAUDE_CONFIG_DIR at the selected account's profile so
        the in-session worker reuses THAT account's saved login (no relogin), and pass the worker
        id, its account, the scope, and the capabilities. This is the load-bearing account
        threading: a worker that does not carry its account's CLAUDE_CONFIG_DIR would run as the
        wrong account or prompt for a login."""
        return {
            ACCT.CONFIG_DIR_ENV: ACCT.resolve(account, root=self._accounts_root),
            "VELDO_WORKER_ID": worker_id,
            "VELDO_ACCOUNT": account,
            "VELDO_SCOPE": "" if scope is None else str(scope),
            "VELDO_CAPABILITIES": ",".join(self._caps),
        }

    def spawn(self, worker_id, scope):
        """Select one account, assemble the env, and start the worker through the injected
        in-session primitive. Returns the handle (a record carrying the account and env). On a
        failed start the account slot is released so it is never leaked."""
        account = self._selector.assign()   # one account per worker
        try:
            env = self._assemble_env(worker_id, scope, account)
            handle = self._start(worker_id, env)   # injected in-session start, never detached
        except Exception:
            self._selector.release(account)
            raise
        rec = {"worker_id": worker_id, "account": account, "env": env, "handle": handle}
        self._handles[worker_id] = rec
        return rec

    def retire(self, handle):
        """Retire a worker: run the injected stop hook (if any), free its account slot for another
        worker, and drop the handle. Retiring an in-session worker is cooperative (it stops
        pulling work); there is no forceful kill of a detached process because none was spawned."""
        rec = handle if isinstance(handle, dict) else {}
        account = rec.get("account")
        if self._stop is not None:
            self._stop(rec.get("handle"))
        if account is not None:
            self._selector.release(account)
        self._handles.pop(rec.get("worker_id"), None)


class FleetController:
    """What the launcher asks each tick. The real controller reads the governor and the
    frontier; a fake scripts a sequence for the gate.
      desired()      -> the governor's desired active worker count (pacing).
      work_remains() -> whether any claimable work is left in scope (else the fleet drains).
      resume_at()    -> the epoch a backed-off pool may resume (the governor's computation).
      now()          -> the current epoch (a parameter, so the gate is deterministic)."""

    def desired(self):
        raise NotImplementedError

    def work_remains(self):
        raise NotImplementedError

    def resume_at(self):
        raise NotImplementedError

    def now(self):
        raise NotImplementedError


class FleetLauncher:
    """The elastic control loop: reconcile the active worker pool to the governed target, and
    handle backoff (wait + re-check) versus drain (stop). Control logic only; spawning and
    waiting are seams."""

    def __init__(self, spawner, max_workers, scope=None):
        self.spawner = spawner
        self.max_workers = int(max_workers)
        self.scope = scope
        self._active = {}   # worker_id -> handle

    def active_count(self):
        return len(self._active)

    def reconcile(self, target):
        """Scale the active pool to `target` (already capped): spawn up, retire down. Returns
        (spawned, retired). Idempotent - reconciling to the current size does nothing."""
        target = max(0, min(int(target), self.max_workers))
        spawned = retired = 0
        while len(self._active) < target:
            wid = "fleet-worker-" + uuid.uuid4().hex[:12]
            self._active[wid] = self.spawner.spawn(wid, self.scope)
            spawned += 1
        while len(self._active) > target:
            wid, handle = self._active.popitem()
            self.spawner.retire(handle)
            retired += 1
        return spawned, retired

    def run(self, controller, waiter, max_ticks=100000):
        """Drive the fleet until the frontier drains. Each tick: reconcile to the governed
        target; if the target is zero, either stop (drained) or wait for resume and re-check
        (backoff). `waiter.wait_until(epoch)` performs the in-session wait (a fake advances a
        clock in the gate); `waiter.tick()` advances one control interval while workers run.
        Retires every worker on stop. Returns the number of ticks run."""
        ticks = 0
        try:
            for ticks in range(1, max_ticks + 1):
                target = max(0, min(controller.desired(), self.max_workers))
                self.reconcile(target)
                if target == 0:
                    if not controller.work_remains():
                        break  # drained: all work done, stop
                    # backoff: wait until the governor says we may resume, then loop to
                    # RE-CHECK desired() before spawning (never resume straight into the limit)
                    self.reconcile(0)  # release workers while backed off
                    waiter.wait_until(controller.resume_at())
                    continue
                waiter.tick()  # workers are running this interval; advance and re-reconcile
        finally:
            self.reconcile(0)  # retire everything on stop or on an exception
        return ticks


class InSessionWaiter:
    """The REAL fill for the launcher's wait seam (WARP-0903): an IN-SESSION blocking wait that
    dies with the running session, spawning NOTHING and detaching NOTHING (feedback_no_rogue_
    processes, PLAN-0007 NG1). The governor only COMPUTES the resume epoch; this waiter does the
    actual waiting, and the launcher RE-CHECKS the desired count after it returns.

      - wait_until(epoch) blocks in THIS session until the wall clock reaches epoch, sleeping in
        BOUNDED steps (each at most `step`), so a long backoff is a series of short interruptible
        in-session sleeps that end when the session ends - never one long detached timer and never
        a background process. A past-or-now epoch waits not at all.
      - tick() sleeps one control interval while the workers run, then returns so the loop
        re-reconciles.

    clock and sleep are injected seams (default time.time / time.sleep) so the gate drives a
    deterministic fake clock with no real time passing. There is deliberately no process, thread,
    timer, or subprocess here: the ONLY primitive is an in-session sleep."""

    def __init__(self, interval=5.0, step=5.0, clock=time.time, sleep=time.sleep):
        self.interval = float(interval)
        self.step = float(step)
        self._clock = clock
        self._sleep = sleep

    def wait_until(self, epoch):
        """Block in-session until clock() reaches epoch, sleeping in bounded steps. Returns the
        number of sleep steps taken (0 for a past-or-now or missing epoch)."""
        steps = 0
        if epoch is None:
            return steps
        while True:
            now = self._clock()
            if now >= epoch:
                return steps
            self._sleep(min(self.step, epoch - now))
            steps += 1

    def tick(self):
        """Advance one control interval in-session (the workers are running this interval)."""
        self._sleep(self.interval)
        return self.interval


def veldo_fleet(spawner, controller, waiter, max_workers, scope=None, max_ticks=100000):
    """Front door: run an elastic fleet of up to max_workers, governed by controller, until
    the frontier drains. A real caller injects a WorkerSpawner (in-session, never detached), a
    FleetController over the governor + frontier, and a waiter that sleeps in-session."""
    return FleetLauncher(spawner, max_workers, scope=scope).run(controller, waiter, max_ticks)


def make_in_session_spawner(start, account=None, accounts=None, accounts_root=None,
                            capabilities=None, stop=None):
    """Build the account-selecting in-session spawner the launcher scales through. `account`
    pins the fleet to ONE registered account (one worker); otherwise the pool spreads across
    `accounts` (default: every registered account), one account per worker. Every listed
    account is resolved up front, so an unknown account fails BY NAME here rather than mid-fleet.
    Returns (spawner, capacity), where capacity is how many concurrent workers the account pool
    supports; the caller caps max_workers at it so one account is never run as two workers."""
    if account is not None:
        names = [account]
    elif accounts is not None:
        names = list(accounts)
    else:
        names = ACCT.list_accounts(root=accounts_root)
    for n in names:
        ACCT.resolve(n, root=accounts_root)   # unknown account fails by name, before any spawn
    selector = AccountSpreader(names)
    sp = InSessionSpawner(start, selector, capabilities=capabilities, stop=stop,
                          accounts_root=accounts_root)
    return sp, selector.capacity()


def make_worktree_in_session_spawner(dispatch, account=None, accounts=None, accounts_root=None,
                                     capabilities=None, dispatch_stop=None, provisioner=None,
                                     repo_root=None):
    """Build the account-selecting spawner whose start is the REAL worktree-isolated in-session start.
    It threads ONE account per worker (via make_in_session_spawner / AccountSpreader), provisions a
    git worktree per worker, and dispatches an in-session worker through `dispatch` (agent-mediated;
    the coordinator provides it at runtime). With dispatch None the start is the fail-loud reference,
    so a bare fleet still fails loud rather than detach. Returns (spawner, capacity); the caller caps
    max_workers at capacity so one account is never run as two workers. Reuses make_in_session_spawner
    and InSessionSpawner - no second account/handle implementation, and no process is spawned here."""
    starter = WorktreeInSessionStart(dispatch, provisioner=provisioner, dispatch_stop=dispatch_stop,
                                     repo_root=repo_root)
    return make_in_session_spawner(
        starter, account=account, accounts=accounts, accounts_root=accounts_root,
        capabilities=capabilities, stop=starter.stop)


def veldo_account_fleet(controller, waiter, start, account=None, accounts=None,
                       accounts_root=None, capabilities=None, scope=None, stop=None,
                       max_workers=None, max_ticks=100000):
    """Account-aware front door: spread the registered accounts (or pin one with account=NAME,
    the veldo work/fleet --account surface W4 wires) across an elastic in-session fleet, one
    account per worker, governed by controller until the frontier drains. max_workers is capped
    at the account-pool capacity so the spreader never doubles an account. A real caller injects
    `start` (the in-session start; the reference in_session_start fails loud) and a
    governor-backed controller and waiter."""
    spawner, capacity = make_in_session_spawner(
        start, account=account, accounts=accounts, accounts_root=accounts_root,
        capabilities=capabilities, stop=stop)
    cap = capacity if max_workers is None else min(int(max_workers), capacity)
    return FleetLauncher(spawner, cap, scope=scope).run(controller, waiter, max_ticks)
