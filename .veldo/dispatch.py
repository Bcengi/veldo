#!/usr/bin/env python3
"""veldo dispatch: the real fleet dispatcher (WARP-0901 / W1 of PLAN-0009).

This fills the work.py Dispatcher seam (WARP-0703). A worker claims a unit and
hands it here; dispatch(unit) routes by the unit's kind and makes the durable
outcome (the spec's status advancing) the thing that removes the unit from the
frontier:

  BUILD (unit kind 'build', spec status ready): drive the executor's build path
    (WARP-0401) over the spec through resolve, plan run-check, build, gate, and
    proof, and STOP at review. On a clean built outcome flip the spec's status
    ready -> review so it becomes a claimable REVIEW unit on the frontier - the
    build worker does NOT review its own work, because independence is preserved
    by making review a separate claimable unit for a genuinely fresh context. A
    red gate, a failed build, or an invalid proof returns {ok: False} and does
    NOT flip the spec, so the loop releases the claim for a retry.

  REVIEW (unit kind 'review', spec status review): run a fresh-context reviewer
    over the built commit for a commit-bound verdict. On a passing verdict (pass
    or pass_with_notes with zero blocking findings) the serialized lander
    (WARP-0704) lands the evidence and the spec flips review -> shipped, leaving
    the frontier; on a failing verdict the spec returns to ready for a fix, never
    shipped. Returns {ok: True} when a verdict was recorded and landed on a pass,
    else {ok: False}.

The split is deliberate and honest, the same split the executor makes:

  MECHANICAL, the dispatcher runs itself - the routing, the status flips, and the
  wiring of gate/proof (the executor) and land (the lander). This is pure control
  logic over seams and is gate-tested with fakes and no live agent.

  DELEGATED, the dispatcher pauses for - the intelligent build and the
  fresh-context review. These are agent work behind seams; the reference
  implementations (the executor's LiveLoop.build and the LiveReviewer here) fail
  LOUD rather than fabricate a build or a verdict. A dispatcher that silently
  no-opped a build or rubber-stamped a review is more dangerous than one that
  refuses to run.

No detached process is ever spawned - the intelligent build and review steps are
performed by the in-session agent through the seam (consistent with the
no-rogue-processes rule and PLAN-0007 NG1). Pure stdlib; the machinery it wires
(executor, lander, claim, frontier) already exists and is reused, not reinvented.

CLEAN-CONTEXT / RECEIPT CONTRACT (WARP-0909). The delegated build and review each
run in a FRESH sub-context (a dispatched sub-agent) that returns a compact outcome,
not a transcript the orchestrator must hold. dispatch() returns a summary dict, but
_dispatch_build / _dispatch_review may still carry a full nested `result` or `land`
for a single call; those are NOT what a long-running loop retains. A thin
orchestrator that drives many specs keeps only the BOUNDED receipt of each outcome
(work.py dispatch_receipt over RECEIPT_FIELDS: an allowlisted set of small summary
fields, failing closed on anything bulky), so its memory stays flat across any
number of specs. That is the mechanical cure for the 2026-07-19 OOM, where one
orchestrator session drove item after item inline, accumulated every build context
and review transcript in one process, grew to ~17.8 GB, and was killed by the kernel.
"""
import importlib.util
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EX = _load("veldo_executor_dsp", ".veldo/executor.py")
WK = _load("veldo_work_dsp", ".veldo/work.py")
LD = _load("veldo_lander_dsp", ".veldo/lander.py")
PC = _load("veldo_policy_check_dsp", ".veldo/policy_check.py")
FR = _load("veldo_frontier_dsp", ".veldo/frontier.py")
# PLAN-0011 W4: the shape-fit review dimension lives in the contracts area; the fleet
# depends on contracts (an allow-listed edge), so the merge gate reads the shape-fit
# dimension of a verdict through it. shape_fit_blocks is pure over the verdict mapping
# and needs no contract or arch here.
SR = _load("veldo_shape_review_dsp", ".veldo/shape_review.py")
# PLAN-0013 W9: the security review dimension, read the same way through the same
# dimension interface. Pure over the verdict mapping, so it needs nothing here.
SEC = _load("veldo_security_review_dsp", ".veldo/security_review.py")


class Reviewer:
    """The fresh-context review seam. review(spec, unit) returns a verdict mapping
    (at least a 'verdict', optionally 'findings' and 'human_minutes'). A concrete
    reviewer dispatches a genuinely fresh context over the built commit; the
    dispatcher talks only to this interface, so its control logic is testable with
    a fake and its reference cannot fabricate a verdict."""

    def review(self, spec, unit):
        raise NotImplementedError


class LiveReviewer(Reviewer):
    """Reference reviewer wired to nothing. Fails LOUD: an adopting runtime must
    inject a reviewer that dispatches a fresh context over the built commit and
    returns its verdict. Refusing to fabricate a verdict is the honest default,
    exactly as the executor's LiveLoop refuses to fabricate a build."""

    def review(self, spec, unit):
        raise EX.ExecutorError(
            "review is a delegated fresh-context step; no reviewer is wired. Inject "
            "a reviewer that dispatches a fresh context over the built commit and "
            "returns its verdict. Refusing to fabricate a verdict.")


class Dispatcher(WK.Dispatcher):
    """The real Dispatcher that fills the work-loop seam.

    Constructed with the seams it delegates to, each defaulting to the fail-loud
    reference so a misconfigured dispatcher refuses rather than fabricates:

      hooks    the executor LoopSteps seam for the build path (a fake in tests;
               the executor's LiveLoop, whose agent build fails loud, otherwise).
      reviewer the fresh-context Reviewer seam (a fake in tests; LiveReviewer,
               which fails loud, otherwise).
      lander   the serialized lander for the review path (a fake in tests; a
               real LD.Lander over GitLandOps for the built ref, injected by the
               caller, otherwise). None means no land is wired: the dispatcher
               refuses rather than pretend a build reached the trunk.

    fail_status is the status a spec returns to on a failing verdict (ready by
    default, so the fleet rebuilds and re-enters review; blocked for a defect that
    needs a human)."""

    def __init__(self, repo_root=None, hooks=None, reviewer=None, lander=None,
                 worker_id=None, claims_root=None, fail_status="ready"):
        self.repo_root = str(repo_root or ROOT)
        self._hooks = hooks
        self._reviewer = reviewer or LiveReviewer()
        self._lander = lander
        self.worker_id = worker_id or ("dispatcher-" + uuid.uuid4().hex[:12])
        self.claims_root = claims_root
        self.fail_status = fail_status

    # seam wiring

    def _build_hooks(self):
        """The executor build seam: an injected fake in tests, the executor's
        LiveLoop (its agent build fails loud without an agent) as the reference."""
        return self._hooks if self._hooks is not None else EX.LiveLoop(root=self.repo_root)

    # spec status on disk (the durable handoff between units)

    def _spec_path(self, sid):
        specs = Path(self.repo_root) / "specs"
        matches = sorted(specs.glob("%s*.md" % sid)) if specs.exists() else []
        if not matches:
            raise EX.ExecutorError("cannot resolve spec %r: no matching file under specs/" % sid)
        return matches[0]

    def _set_status(self, sid, new):
        """Flip the spec's front-matter status to new. Only the first status line
        inside the front-matter fence is touched, so a status: token anywhere in
        the body is never mistaken for it. This is the durable handoff: a build's
        ready -> review makes a review unit claimable, and a review's review ->
        shipped removes the unit from the frontier."""
        p = self._spec_path(sid)
        text = p.read_text()
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not m:
            raise EX.ExecutorError("spec %r has no front matter to update" % sid)
        new_fm, n = re.subn(r"(?m)^status: .*$", "status: " + new, m.group(1), count=1)
        if n != 1:
            raise EX.ExecutorError("spec %r front matter has no status line" % sid)
        p.write_text(text[:m.start(1)] + new_fm + text[m.end(1):])
        return True

    def _resolve(self, sid):
        """A light spec view (id, status, path) for the reviewer seam. The real
        reviewer reads the built commit and proof; this hands it the coordinates."""
        return {"id": sid, "status": FR.current_status(sid, self.repo_root),
                "path": str(self._spec_path(sid))}

    # the verdict gate

    def _verdict_passes(self, rv):
        """A verdict lets a change ship only if it is pass or pass_with_notes, carries
        zero blocking findings, AND fits the declared shape. Reuses the executor's
        PASSING_VERDICTS and the policy check's blocking_findings, which fails closed on
        an unreadable findings shape, and the W4 shape-fit dimension (shape_review.shape_fit_blocks,
        which fails closed on an unreadable shape_fit block). The shape-fit read is the
        second review dimension (PLAN-0011 W4, D4): a correct-but-does-not-fit verdict
        (a does_not_fit shape_fit block) blocks the merge like any blocking finding, so the
        spec returns to fail_status for rework; a verdict with no shape_fit dimension is
        unaffected (adoption safe). A method (not a free function) so it is a seam a mutant
        can subvert - which is what gives the ship-on-pass assertion its teeth."""
        if (rv or {}).get("verdict") not in EX.PASSING_VERDICTS:
            return False
        if PC.blocking_findings(rv or {}):
            return False
        # BOTH review dimensions, read through the one dimension interface: correct-but-does
        # -not-fit and correct-but-INSECURE are each a legitimate rework verdict, and each
        # fails closed on an unreadable block while an absent dimension does not block.
        return not any(d.dimension_blocks(rv or {}) for d in (SR, SEC))

    # the routing

    def dispatch(self, unit):
        """Route a claimed unit by its kind and return {ok: bool, ...}. The
        WorkLoop's release/failed semantics apply to the ok flag unchanged."""
        kind = (unit or {}).get("kind")
        if kind == "build":
            return self._dispatch_build(unit)
        if kind == "review":
            return self._dispatch_review(unit)
        return {"ok": False, "kind": kind, "spec": (unit or {}).get("spec"),
                "error": "unknown unit kind %r" % kind}

    def _dispatch_build(self, unit):
        """BUILD path: drive the executor over the spec and STOP at review.

        stop_after='proof' runs exactly one resolve/plan-check/build/gate/proof
        cycle and finishes with the distinct 'built' state without ever entering
        review, so the build worker never reviews its own work. On a clean built
        outcome flip ready -> review (making a review unit claimable); on any halt
        (a non-ready spec, a plan refusal, a failed build, a red gate, an invalid
        proof) return ok False and DO NOT flip - the change never reaches review."""
        sid = unit["spec"]
        result = EX.Executor(self._build_hooks()).run(sid, stop_after="proof")
        if result.get("state") != "built":
            return {"ok": False, "kind": "build", "spec": sid, "reviewed": False,
                    "state": result.get("state"), "halted_at": result.get("halted_at"),
                    "reason": result.get("reason"), "result": result}
        self._set_status(sid, "review")
        return {"ok": True, "kind": "build", "spec": sid, "reviewed": False,
                "status": "review", "result": result}

    def _dispatch_review(self, unit):
        """REVIEW path: a fresh-context verdict over the built commit, then land.

        On a passing verdict land the evidence through the serialized lander and
        flip review -> shipped (the spec leaves the frontier). On a failing verdict
        return the spec to fail_status (ready by default) for a fix - never
        shipped, never landed. A land that itself fails leaves the spec in review
        (not shipped) so the land can be retried."""
        sid = unit["spec"]
        spec = self._resolve(sid)
        rv = self._reviewer.review(spec, unit) or {}
        verdict = rv.get("verdict")
        if not self._verdict_passes(rv):
            self._set_status(sid, self.fail_status)
            return {"ok": False, "kind": "review", "spec": sid, "verdict": verdict,
                    "shipped": False, "landed": False, "status": self.fail_status}
        land = self._land(unit) or {}
        if not land.get("ok"):
            return {"ok": False, "kind": "review", "spec": sid, "verdict": verdict,
                    "shipped": False, "landed": False, "land": land}
        self._set_status(sid, "shipped")
        return {"ok": True, "kind": "review", "spec": sid, "verdict": verdict,
                "shipped": True, "landed": True, "status": "shipped", "land": land}

    def _land(self, unit):
        """Land the built evidence through the serialized lander. The lander is
        reused machinery, but the built ref it lands is context the real worker
        supplies, so an unwired lander refuses rather than pretend a build reached
        the trunk (the same fail-loud posture as the delegated agent steps)."""
        if self._lander is None:
            raise EX.ExecutorError(
                "no lander is wired; inject a serialized lander over GitLandOps for "
                "the built ref. Refusing to pretend a build reached the trunk.")
        return self._lander.land(unit)


def veldo_dispatch(unit, repo_root=None, hooks=None, reviewer=None, lander=None,
                  worker_id=None, claims_root=None, fail_status="ready"):
    """Front door: build a Dispatcher for a repo and dispatch a single unit. A real
    caller injects the agent-backed build hooks, the fresh-context reviewer, and a
    lander over the built ref; this fabricates none of them."""
    disp = Dispatcher(repo_root=repo_root, hooks=hooks, reviewer=reviewer,
                      lander=lander, worker_id=worker_id, claims_root=claims_root,
                      fail_status=fail_status)
    return disp.dispatch(unit)
