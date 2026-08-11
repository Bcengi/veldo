#!/usr/bin/env python3
"""veldo token pacing governor: use the whole token budget over each window, without running
out early.

Claude Code exposes no live remaining-token count (it appears only in the limit error), so the
governor does not query one. It MEASURES burn from the event stream (the same tokens the budget
enforcer reads through metrics.compute) within each rolling window, and paces the number of
ACTIVE workers so measured burn tracks the target rate for the TIGHTER of the configured
windows - typically a session window (e.g. use the session budget over ~4 hours) and a weekly
window (the 7-day budget). Fewer workers when ahead of pace, more when behind, none while a
window's budget is spent (until it rolls) or during a limit-error backoff.

  - desired_workers(...) is the pacing control law: pure arithmetic over the windows, the
    windowed burn, and a measured per-worker burn rate. The tighter window wins (min).
  - resume_at(...) computes WHEN a backed-off pool may resume: the earliest time enough of the
    oldest in-window spend has aged out of every over-budget window's trailing horizon. This is
    what an opt-in, IN-SESSION resume waiter would sleep until - the governor computes the time,
    it does NOT spawn any process. A detached background resumer is forbidden (a worker runs in
    a real session; pausing on token-out and resuming is an explicit, opt-in, in-session step),
    so wiring an actual waiter is the launcher's concern (Y7) and requires opting in.

Pure stdlib; reuses metrics.parse_at for event timestamps. This is the control law only; the
worker loop (WARP-0703) and the launcher (WARP-0707) consume it."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load("veldo_metrics_gov", ".veldo/metrics.py")


class Window:
    """A rolling budget: at most `tokens` may be spent in any trailing `seconds`."""

    def __init__(self, name, seconds, tokens):
        if seconds <= 0 or tokens <= 0:
            raise ValueError("window %r needs positive seconds and tokens" % name)
        self.name = name
        self.seconds = float(seconds)
        self.tokens = float(tokens)

    def target_rate(self):
        """Tokens per second that uses the whole budget evenly over the window."""
        return self.tokens / self.seconds


def _tokens_at(events):
    """[(epoch, tokens)] for events carrying a spend, dropping any without a parseable time."""
    out = []
    for e in events:
        tk = e.get("tokens")
        if tk is None:
            continue
        dt = M.parse_at(e)
        if dt is None:
            continue
        out.append((dt.timestamp(), int(tk)))
    return out


def windowed_spend(events, now_epoch, seconds):
    """Total tokens spent within the trailing `seconds` ending at now_epoch."""
    cut = now_epoch - seconds
    return sum(tk for (t, tk) in _tokens_at(events) if t >= cut)


def desired_workers(windows, events, now_epoch, per_worker_rate,
                    max_workers, limit_cooldown_until=None):
    """The number of active workers to run right now to track the tighter window's target rate.

    - During a limit-error backoff (now before limit_cooldown_until), run none.
    - If a window's budget is already spent in its trailing horizon, run none until it rolls.
    - Otherwise, for each window, the workers that sustain its target rate is
      target_rate / per_worker_rate; the TIGHTER window (fewest workers) wins. At least one
      worker runs while any budget remains (so the budget is actually used - a single worker
      that outpaces a window self-corrects via the spent-out backoff), capped at max_workers.
    - per_worker_rate <= 0 means burn is not measured yet (bootstrap): allow max_workers; the
      next tick, once burn is on the stream, paces for real."""
    if limit_cooldown_until is not None and now_epoch < limit_cooldown_until:
        return 0
    for w in windows:
        if windowed_spend(events, now_epoch, w.seconds) >= w.tokens:
            return 0  # this window's budget is used up; wait for it to roll off
    if per_worker_rate <= 0:
        return max(0, int(max_workers))
    best = int(max_workers)
    for w in windows:
        n = max(1, int(w.target_rate() / per_worker_rate))  # floor, but use at least one
        best = min(best, n)
    return max(0, min(best, int(max_workers)))


def resume_at(windows, events, now_epoch):
    """The earliest time a backed-off pool may resume: when enough of the oldest in-window
    spend has aged out of EVERY over-budget window (assuming no new spend). Returns now_epoch
    if already runnable. This is the time an opt-in in-session waiter would sleep until; the
    governor only computes it and never sleeps or spawns anything itself."""
    resume = now_epoch
    for w in windows:
        cut = now_epoch - w.seconds
        in_win = sorted((t, tk) for (t, tk) in _tokens_at(events) if t >= cut)
        total = sum(tk for (_t, tk) in in_win)
        if total < w.tokens:
            continue  # this window is not over budget
        dropped = 0
        for (t, tk) in in_win:  # oldest first
            dropped += tk
            if total - dropped < w.tokens:
                # this event ages out of the trailing window at t + seconds
                resume = max(resume, t + w.seconds)
                break
        else:
            # even dropping everything leaves us at/over budget (a single oversized spend):
            # runnable once the last in-window event ages out
            if in_win:
                resume = max(resume, in_win[-1][0] + w.seconds)
    return resume


def measure_per_worker_rate(events, now_epoch, seconds, active_workers):
    """Estimate tokens/sec/worker from recent burn: windowed spend over the horizon divided by
    the horizon and the active worker count. Returns 0.0 if there is no burn or no worker to
    attribute it to (the bootstrap case desired_workers treats as 'allow max')."""
    if active_workers <= 0 or seconds <= 0:
        return 0.0
    spent = windowed_spend(events, now_epoch, seconds)
    return spent / seconds / active_workers


# per-account pacing layer (WARP-0903, W3 of PLAN-0009).
# Several accounts run together, each pacing against its OWN session and weekly windows and its
# OWN measured burn, by REUSING the single-pool control law above per account (desired_workers /
# resume_at, unchanged - this layer holds no pacing arithmetic of its own). The burn feeding one
# account's windows is only the burn produced UNDER that account, keyed by the account tag its
# worker carries (VELDO_ACCOUNT from W2, recorded on the spend event as the `account` field), so
# one account's spend never counts against another's budget and an account with no burn yet
# bootstraps exactly as the single-pool law does. The fleet-wide desired count is the SUM of the
# per-account desired counts capped at the pool max, so an account whose window is spent (or is in
# a limit-error cooldown) contributes zero while every OTHER account keeps pacing and the pool
# never fully stalls while any account still has budget.

ACCOUNT_KEY = "account"   # the spend event's account tag (matches events.py; VELDO_ACCOUNT from W2)


def account_of(event, key=ACCOUNT_KEY):
    """The account an event was produced under (its VELDO_ACCOUNT tag), or None if untagged."""
    v = event.get(key)
    return None if v is None else str(v)


def events_for_account(events, account, key=ACCOUNT_KEY):
    """The subset of the event stream produced under ONE account: its own burn and nothing from
    any other account. This is the per-account burn attribution - filter first, then hand the
    account's own events to the unchanged single-pool law, so one account's spend never counts
    against another's window."""
    account = str(account)
    return [e for e in events if account_of(e, key) == account]


class AccountPacer:
    """One account's inputs to the reused control law: its own session + weekly windows, its
    measured per-worker burn rate (0.0 until burn is on its stream, so it bootstraps exactly as the
    single-pool law), its worker cap, and its current limit-error cooldown. It carries no
    arithmetic; it is only the per-account parameters desired_workers / resume_at consume."""

    def __init__(self, name, windows, per_worker_rate=0.0, max_workers=1,
                 limit_cooldown_until=None):
        self.name = str(name)
        self.windows = list(windows)
        self.per_worker_rate = float(per_worker_rate)
        self.max_workers = int(max_workers)
        self.limit_cooldown_until = limit_cooldown_until


class AccountGovernor:
    """The per-account pacing layer: one AccountPacer per account plus the pool-wide cap. It REUSES
    desired_workers / resume_at per account over that account's OWN filtered burn - never a
    reimplementation. desired() sums the per-account desired counts and caps at the pool max;
    resume_at() reports when the earliest fully-backed-off account may resume, each computed over
    ITS own windows and burn. now_epoch stays a parameter, so this layer is deterministic and never
    reads the wall clock or sleeps (the launcher's in-session waiter does the waiting)."""

    def __init__(self, pacers, pool_max, account_key=ACCOUNT_KEY):
        self.pacers = {p.name: p for p in pacers}
        self.pool_max = int(pool_max)
        self.account_key = account_key

    def account_events(self, name, events):
        """One account's own burn, filtered from the shared stream by its account tag."""
        return events_for_account(events, name, self.account_key)

    def account_per_worker_rate(self, name, events, now_epoch, seconds, active_workers):
        """Measure ONE account's per-worker burn rate from its OWN filtered burn (reusing
        measure_per_worker_rate). An account with no burn yet measures 0.0, which desired_workers
        treats as bootstrap - the same behaviour the single-pool law has before burn is measured."""
        return measure_per_worker_rate(
            self.account_events(name, events), now_epoch, seconds, active_workers)

    def account_desired(self, name, events, now_epoch):
        """Desired workers for ONE account: the reused single-pool control law over its own
        windows, its own filtered burn, its own rate, cap, and cooldown. Spent or cooling -> 0;
        otherwise the paced count. This is the whole per-account arithmetic - a straight reuse."""
        p = self.pacers[name]
        return desired_workers(
            p.windows, self.account_events(name, events), now_epoch,
            p.per_worker_rate, p.max_workers, limit_cooldown_until=p.limit_cooldown_until)

    def desired(self, events, now_epoch):
        """Fleet-wide desired = the SUM of the per-account desired counts, capped at the pool max.
        A spent or cooling account contributes 0 while the others keep pacing, so the pool never
        fully stalls while any account still has budget."""
        total = sum(self.account_desired(n, events, now_epoch) for n in self.pacers)
        return max(0, min(total, self.pool_max))

    def account_resume_at(self, name, events, now_epoch):
        """When ONE account may resume: resume_at over its OWN windows and burn, never earlier than
        its own limit cooldown. Computed independently of every other account, so an account
        resumes when ITS window rolls."""
        p = self.pacers[name]
        r = resume_at(p.windows, self.account_events(name, events), now_epoch)
        if p.limit_cooldown_until is not None and p.limit_cooldown_until > r:
            r = p.limit_cooldown_until
        return r

    def resume_at(self, events, now_epoch):
        """When the pool may next resume after a FULL backoff: the earliest resume time across the
        accounts currently contributing 0 (spent or cooling); an account already runnable does not
        gate the wait. Returns now_epoch if nothing is backed off. The launcher waits until this,
        then RE-CHECKS desired before spawning, so it never resumes straight into a spent window."""
        soonest = None
        for name in self.pacers:
            if self.account_desired(name, events, now_epoch) > 0:
                continue
            r = self.account_resume_at(name, events, now_epoch)
            soonest = r if soonest is None else min(soonest, r)
        return now_epoch if soonest is None else soonest
