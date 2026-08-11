#!/usr/bin/env python3
"""veldo work: the fleet worker loop.

A worker joins the pool with a set of capabilities and an optional scope and then, with
no central coordinator, repeatedly:

  1. asks the frontier what is claimable for it (WARP-0702),
  2. atomically claims the next unit it can (WARP-0701),
  3. DISPATCHES it - a build or a review - and
  4. releases the claim, then loops, stopping when nothing is claimable (drained).

The loop's control logic (claim, dispatch, release, drain) is mechanical and gate-tested
here over a fake dispatcher with no live agent. The DISPATCH itself is delegated: building
a spec and reviewing one are agent work, so a real Dispatcher hands them to the agent (via
the executor / veldo run for a build, a fresh-context reviewer for a review) and makes the
outcome durable (a landed build flips the spec to shipped, so it leaves the frontier). The
loop holds the claim across the dispatch so no other worker takes the same unit, and always
releases after, so a failed unit becomes claimable again for a retry. Because claimable() is
a snapshot and the claim gates ownership only (not done-ness), the loop re-checks after each
claim that the unit is still the work it saw (claim-then-recheck) and releases + skips it if
another worker finished it in the claim-time window, so two workers never dispatch the same
unit. Pure stdlib control logic; Unix-only via the claim ledger. This is the loop only; the
serialized lander is Y4."""
import importlib.util
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FR = _load("veldo_frontier_wk", ".veldo/frontier.py")
CL = _load("veldo_claim_wk", ".veldo/claim.py")


class Dispatcher:
    """The seam a worker dispatches a claimed unit through. A real dispatcher delegates to
    the agent: a build unit is built and landed (the executor / veldo run), a review unit is
    reviewed (a fresh-context reviewer), and the durable outcome (spec shipped, or verdict
    recorded) is what removes the unit from the frontier. Returns {ok: bool, ...}."""

    def dispatch(self, unit):
        raise NotImplementedError(
            "inject a Dispatcher; building and reviewing are delegated agent steps")


# The bounded dispatch RECEIPT (WARP-0909). A long-running session that drives many specs
# in one loop (an autonomous or multi-spec run) must stay a THIN DISPATCHER: it hands each
# spec's build and review to a FRESH sub-context and keeps only a small receipt per spec,
# never the sub-context's transcript. Its memory then stays flat across any number of specs
# instead of growing as the sum of all of them. On 2026-07-19 an orchestrator that drove
# spec after spec INLINE, accumulating every build context plus every review transcript in
# one process, reached ~17.8 GB and was OOM-killed. This is the mechanical half of that rule:
# the exact bounded value the loop retains per spec.

# The allowlist of small summary fields a receipt may carry. Everything else, a full nested
# executor result, a build transcript, file contents, a fat land record, full review
# reasoning, is DROPPED. Failing closed (an allowlist, never a denylist) is deliberate: an
# unknown field a future dispatch adds cannot silently smuggle unbounded content through.
RECEIPT_FIELDS = ("spec", "kind", "ok", "status", "verdict", "commit",
                  "proof_digest", "gate", "halted_at", "reason")


def dispatch_receipt(outcome, fields=RECEIPT_FIELDS):
    """Project a dispatch outcome to its BOUNDED receipt: a new dict carrying only the
    allowlisted summary fields that are present in the outcome, and nothing else. Pure - it
    reads one mapping and copies scalars, no I/O. This is the value a thin orchestrator keeps
    per spec so its footprint stays flat across a long loop (the 2026-07-19 OOM cure). It
    fails CLOSED: an outcome that also carries a full nested `result`, a `transcript`, `land`
    details, file contents, or any other bulky field has those DROPPED, because only
    allowlisted keys survive. The mechanical dispatch (dispatch.py) may return such fields in
    its own single-call outcome; the receipt is the bounded thing the LOOP retains, so
    orchestrator memory cannot grow without bound even when a dispatch outcome does."""
    src = outcome or {}
    return {k: src[k] for k in fields if k in src}


class WorkLoop:
    """The claim/dispatch/release/drain loop. Control logic only; dispatch is delegated."""

    def __init__(self, worker_id, capabilities, dispatcher, scope=None,
                 repo_root=None, claims_root=None):
        self.worker_id = worker_id
        self.caps = list(capabilities or [])
        self.dispatcher = dispatcher
        self.scope = scope
        self.repo_root = repo_root
        self.claims_root = claims_root
        # Units this worker dispatched and that failed: it releases them (for a human or
        # another worker or a later retry) but does NOT re-claim them itself, so one worker
        # never hot-loops its own failing unit.
        self._failed = set()

    def _still_claimable(self, unit):
        """After an atomic claim, re-check the unit is still the work we saw on the frontier.
        claimable() is a snapshot and the claim gates OWNERSHIP only, not done-ness, so between
        the snapshot and our claim another worker may have finished the unit. Its deps only ever
        go ready -> shipped (monotonic) and capability/scope do not change, so the only thing
        that can regress in that window is the spec's own status: a build unit must still be
        ready, a review unit must still be in review. If not, another worker finished it."""
        expected = "review" if unit.get("kind") == "review" else "ready"
        return FR.current_status(unit["spec"], self.repo_root) == expected

    def _claim_next(self):
        """Claim the next claimable unit this worker can take, or None if none claimable.
        Skips units this worker already failed, and tries each candidate until one claim
        succeeds (another worker may have raced us). After a successful claim, re-checks the
        unit is still claimable (claim-then-recheck) and releases + skips it if another worker
        finished it in the claim-time window, so two workers never dispatch the same unit."""
        for u in FR.claimable(worker_caps=self.caps, scope=self.scope,
                              repo_root=self.repo_root, claims_root=self.claims_root):
            if u["spec"] in self._failed:
                continue
            ok, _reason = CL.claim(u["spec"], self.worker_id, self.caps,
                                   u.get("requires"), root=self.claims_root)
            if not ok:
                continue
            if not self._still_claimable(u):
                CL.release(u["spec"], self.worker_id, root=self.claims_root)
                continue
            return u
        return None

    def step(self):
        """Claim the next unit, dispatch it, and release the claim. Returns the outcome
        {unit, result}, or None if nothing is claimable (drained). The claim is held across
        the dispatch and always released after, even if the dispatch raises."""
        unit = self._claim_next()
        if unit is None:
            return None
        try:
            result = self.dispatcher.dispatch(unit)
        except Exception as e:  # a crashed dispatch is a failed unit, not a stuck claim
            result = {"ok": False, "error": repr(e)}
        finally:
            CL.release(unit["spec"], self.worker_id, root=self.claims_root)
        if not (result or {}).get("ok"):
            # released above for a human / another worker / a later retry, but this worker
            # will not re-claim it, so it moves on to other work instead of hot-looping.
            self._failed.add(unit["spec"])
        return {"unit": unit, "result": result}

    def run(self, max_units=10000):
        """Run steps until drained (nothing claimable) or max_units, and return the outcomes.
        max_units is a runaway backstop, not the normal stop - the normal stop is drain."""
        outcomes = []
        for _ in range(max_units):
            out = self.step()
            if out is None:
                break
            outcomes.append(out)
        return outcomes


def veldo_work(dispatcher, worker_id=None, capabilities=None, scope=None,
              repo_root=None, claims_root=None, max_units=10000):
    """Front door: allocate a worker id, run the loop with the given dispatcher, return the
    outcomes. A real caller injects a Dispatcher that delegates build/review to the agent."""
    wid = worker_id or ("worker-" + uuid.uuid4().hex[:12])
    loop = WorkLoop(wid, capabilities, dispatcher, scope=scope,
                    repo_root=repo_root, claims_root=claims_root)
    return {"worker_id": wid, "outcomes": loop.run(max_units=max_units)}
