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

ENROLLED FACTORY WORK (VELDO-0049). In a repository enrolled with the authority (VELDO-0029), or
whenever a FloorAuthority is wired, the spec file's status line is not the handoff and this module
never writes it: _set_status refuses (status_projection_owned). Every step moves through ONE
registered store command, floor_transition, whose transition runs inside the store's own
transaction and reads what it judges itself:

  accept_build   a built unit becomes reviewable only with ACCEPTED PROOF and a GREEN GATE: the
                 authority reads proof/<unit>/manifest.json from Git at the built commit, binds its
                 digest, validates it, requires the implementation it names to be that commit or
                 an ancestor with nothing but that proof changed since, requires the claim holder at
                 its generation and the build's own VELDO-0039 dispatch (exited 0 under that claim).
                 The builder becomes the unit's producer.
  assign_review  a signed assignment (the journal record) of one ELIGIBLE reviewer principal, never
                 the builder, never a second position for one principal, bound to the exact source
                 commit and proof digest.
  record_review  the reviewer's own receipt: signed with the reviewer's active key, bound to the
                 assignment, the source and the proof, printed by a separate VELDO-0039 review
                 dispatch (its recorded output digest) that was launched with exactly the assignment
                 as its input (a fresh context). A blocking finding is recorded as an obligation; a
                 failing verdict returns the unit for a fix.
  dispose_finding an explicit, signed disposition of one blocking finding by the owner (a person) or
                 the reviewer who raised it, never the builder; a rejected ruling leaves it open.
  handoff        the review policy (the retained engineering-review policy, policy.yaml risk_tiers
                 reviews, held by the authority as review-policy:<repository>) counted in DISTINCT
                 passing reviewers on the current attempt, and no unresolved blocking finding from
                 any attempt. No later pass erases a finding.

Nothing here establishes completion: no action writes a completed state, a shipped status or a
completion receipt. The lander's own receipts are the only completion. The status projection is
published only by the Materializer, VELDO-0035's ordinary materialization of an accepted snapshot
at an explicit watermark. Tracker drafting and promotion are disabled for enrolled repositories in
tracker_bridge.py.
"""
import hashlib
import importlib.util
import json
import re
import uuid
from pathlib import Path

import importlib.util as _yaml_importlib
from pathlib import Path as _YamlPath
_yaml_spec = _yaml_importlib.spec_from_file_location("veldo_yamlish", _YamlPath(__file__).resolve().with_name("yamlish.py"))
_Y = _yaml_importlib.module_from_spec(_yaml_spec)
_yaml_spec.loader.exec_module(_Y)

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
# VELDO-0052: the shared floor eligibility service. With the floor enabled the build, review and
# publication stations each decide over the real store before their effect, against the ticket the
# previous station handed on, and every subscription CLI call goes through a reserved CallHandle.
EL = _load("veldo_eligibility_dsp", ".veldo/control_eligibility.py")
# VELDO-0049: the one Git boundary the authority's reads of the built commit go through.
_git_process = _load("veldo_git_process_dsp", ".veldo/git_process.py")

# Every place the dispatcher changes a spec's status, as (method, status). The suite derives the
# same set from this file's call sites and requires equality. Under enrollment every one of them is
# an authority transition and a materialized projection instead, and the write itself refuses.
STATUS_WRITES = (
    ("Dispatcher._dispatch_build", "review"),
    ("Dispatcher._dispatch_review", "fail_status"),
    ("Dispatcher._dispatch_review", "shipped"),
)


def verdict_passes(rv):
    """A verdict lets a change ship only if it is pass or pass_with_notes, carries zero blocking
    findings, AND neither review dimension (shape fit, security) blocks. The authority judges every
    recorded review receipt with this same function inside its transaction."""
    if (rv or {}).get("verdict") not in EX.PASSING_VERDICTS:
        return False
    if PC.blocking_findings(rv or {}):
        return False
    # BOTH review dimensions, read through the one dimension interface: correct-but-does
    # -not-fit and correct-but-INSECURE are each a legitimate rework verdict, and each
    # fails closed on an unreadable block while an absent dimension does not block.
    return not any(d.dimension_blocks(rv or {}) for d in (SR, SEC))


class Reviewer:
    """The fresh-context review seam. review(spec, unit) returns a verdict mapping
    (at least a 'verdict', optionally 'findings' and 'human_minutes'). A concrete
    reviewer dispatches a genuinely fresh context over the built commit; the
    dispatcher talks only to this interface, so its control logic is testable with
    a fake and its reference cannot fabricate a verdict."""

    def review(self, spec, unit, calls=None):
        """calls, when the floor is enabled, is the station's CallHandle: the reviewer's only path
        to a subscription CLI, every call decided and reserved before launch (VELDO-0052)."""
        raise NotImplementedError


class LiveReviewer(Reviewer):
    """Reference reviewer wired to nothing. Fails LOUD: an adopting runtime must
    inject a reviewer that dispatches a fresh context over the built commit and
    returns its verdict. Refusing to fabricate a verdict is the honest default,
    exactly as the executor's LiveLoop refuses to fabricate a build."""

    def review(self, spec, unit, calls=None):
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
      authority the FloorAuthority of an enrolled repository (VELDO-0049). An
               enrolled repository with none wired stops by name
               (authority_required) before anything is built or reviewed.

    fail_status is the status a spec returns to on a failing verdict (ready by
    default, so the fleet rebuilds and re-enters review; blocked for a defect that
    needs a human)."""

    def __init__(self, repo_root=None, hooks=None, reviewer=None, lander=None,
                 worker_id=None, claims_root=None, fail_status="ready", eligibility=None, calls=None,
                 authority=None):
        self.repo_root = str(repo_root or ROOT)
        self._hooks = hooks
        self._reviewer = reviewer or LiveReviewer()
        self._lander = lander
        self.worker_id = worker_id or ("dispatcher-" + uuid.uuid4().hex[:12])
        self.claims_root = claims_root
        self.fail_status = fail_status
        # VELDO-0052: the shared eligibility Gate and the StationCalls that reserve every
        # subscription CLI call. An enrolled repository with neither wired stops by name.
        self._eligibility = eligibility
        self._calls = calls
        # VELDO-0049: the authority every enrolled build, review and handoff moves through.
        self._authority = authority

    # VELDO-0052 floor wiring

    def _gate(self):
        return EL.gate_for(self.repo_root, self._eligibility)

    def _floor(self, gate=None):
        """VELDO-0049: the wired FloorAuthority; a named stop in an enrolled repository with none
        (authority_required) or with no eligibility Gate; None in an unenrolled tree, which keeps
        the pre-factory status writes unchanged."""
        if self._authority is None:
            if EL.enrolled(self.repo_root):
                raise EL.Stopped("authority_required")
            return None
        if gate is None:
            raise EL.Stopped("eligibility_required")
        return self._authority

    def _context(self, unit, **extra):
        """Whose station this is: the claim holder and generation the work loop handed on."""
        return dict({"holder": (unit or {}).get("holder") or self.worker_id,
                     "generation": (unit or {}).get("generation")}, **extra)

    def _launch(self, station, unit, context, decision):
        """The station's only path to a subscription CLI: the scope of this launch
        (StationCalls.launch). The runner opens THIS dispatch's identity, reserving its worker slot
        (VELDO-0036), because the unit the work loop hands over carries none and must not choose
        one; every call is decided and reserved against that slot, and the slot is retired when the
        launched call returns."""
        if self._calls is None:
            raise EL.Stopped("reservation_required")
        return self._calls.launch(station, unit["spec"], context=context, ticket=decision)

    @staticmethod
    def _refused(kind, sid, decision, **extra):
        return dict({"ok": False, "kind": kind, "spec": sid, "state": "refused",
                     "halted_at": "eligibility", "reason": "; ".join(decision["refusals"]),
                     "refusals": list(decision["refusals"])}, **extra)

    @staticmethod
    def _floor_refused(kind, sid, error, halted_at, **extra):
        return dict({"ok": False, "kind": kind, "spec": sid, "state": "refused", "halted_at": halted_at,
                     "reason": error.code, "refusals": list(error.codes)}, **extra)

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
        the body is never mistaken for it. This is the durable handoff of an
        UNENROLLED tree: a build's ready -> review makes a review unit claimable,
        and a review's review -> shipped removes the unit from the frontier.

        VELDO-0049: an enrolled unit's status is the authority's record and its
        projection is the Materializer's alone, so here it refuses by name and
        the spec file is never touched."""
        if self._authority is not None or EL.enrolled(self.repo_root):
            raise EL.Stopped("status_projection_owned")
        p = self._spec_path(sid)
        text = p.read_text()
        m = _Y.front_matter_match(text)
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
        can subvert - which is what gives the ship-on-pass assertion its teeth.

        VELDO-0049: for enrolled work this is only the dispatcher's own, more conservative
        read of the recorded receipt. The authority judges every receipt with the same
        verdict_passes inside its transaction and alone decides the handoff, so a seam
        that says pass cannot land what the authority refuses."""
        return verdict_passes(rv)

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
        proof) return ok False and DO NOT flip - the change never reaches review.

        VELDO-0049: an enrolled build is handed to review only by the authority's
        accept_build over the built commit, then published by the Materializer."""
        sid = unit["spec"]
        gate = self._gate()
        executor = EX.Executor(self._build_hooks(), eligibility=gate)
        if gate is not None:
            context = self._context(unit)
            decision = gate.decide("build", sid, context=context, ticket=unit.get("eligibility"))
            if not decision["eligible"]:
                return self._refused("build", sid, decision, reviewed=False)
            if self._calls is None:
                raise EL.Stopped("reservation_required")
            # The executor launches the build through the SAME build station, rechecking before the
            # launch against this decision as its ticket. It opens the build's dispatch (its worker
            # slot) only after every pre-launch decision passed, and retires it when the build returns.
            executor = EX.Executor(self._build_hooks(), eligibility=gate, calls=self._calls, station="build",
                                   context=context, ticket=decision)
        floor = self._floor(gate)
        if floor is not None:
            state = (floor.record(sid) or {}).get("state")
            if state not in FLOOR_TRANSITIONS["accept_build"][0]:
                # The authority holds this unit in review or handed off: no builder is launched.
                code = "transition_refused:%s:accept_build" % state
                return {"ok": False, "kind": "build", "spec": sid, "reviewed": False, "state": "refused",
                        "halted_at": "floor_state", "reason": code, "refusals": [code]}
        result = executor.run(sid, stop_after="proof")
        if result.get("state") != "built":
            return {"ok": False, "kind": "build", "spec": sid, "reviewed": False,
                    "state": result.get("state"), "halted_at": result.get("halted_at"),
                    "reason": result.get("reason"), "result": result}
        if floor is not None:
            return self._accept_build(floor, unit, result)
        self._set_status(sid, "review")
        return {"ok": True, "kind": "build", "spec": sid, "reviewed": False,
                "status": "review", "result": result}

    def _accept_build(self, floor, unit, result):
        """VELDO-0049: hand the built commit to the authority. It reads and judges the proof and the
        build's dispatch itself; this passes only the coordinates and the gate's observation."""
        sid = unit["spec"]
        steps = {step.get("name"): step for step in result.get("steps") or []}
        gate_step = steps.get("gate") or {}
        observation = {"green": gate_step.get("ok") is True, "detail": gate_step.get("detail")}
        context = self._context(unit)
        try:
            floor.accept_build(sid, commit=(steps.get("build") or {}).get("commit"), gate=observation,
                               holder=context["holder"], generation=context["generation"])
        except FloorRefused as error:
            return self._floor_refused("build", sid, error, "build_acceptance", reviewed=False, result=result)
        projection = floor.publish(sid)
        return {"ok": True, "kind": "build", "spec": sid, "reviewed": False, "status": "review",
                "projection": projection, "result": result}

    def _dispatch_review(self, unit):
        """REVIEW path: a fresh-context verdict over the built commit, then land.

        On a passing verdict land the evidence through the serialized lander and
        flip review -> shipped (the spec leaves the frontier). On a failing verdict
        return the spec to fail_status (ready by default) for a fix - never
        shipped, never landed. A land that itself fails leaves the spec in review
        (not shipped) so the land can be retried.

        VELDO-0049: an enrolled review is assigned, recorded and handed off only
        through the authority, and nothing here writes shipped (_review_floor)."""
        sid = unit["spec"]
        gate = self._gate()
        decision = None
        context = None
        if gate is not None:
            # THE REVIEW STATION: the same draft-plan, decision, dependency and admission questions
            # as build, plus reviewer independence, decided before any reviewer is launched.
            context = self._context(unit, reviewer=getattr(self._reviewer, "identity", None))
            decision = gate.decide("review", sid, context=context, ticket=unit.get("eligibility"))
            if not decision["eligible"]:
                return self._refused("review", sid, decision, verdict=None, shipped=False, landed=False)
        floor = self._floor(gate)
        if floor is not None:
            return self._review_floor(floor, unit, context, decision)
        spec = self._resolve(sid)
        if decision is None:
            rv = self._reviewer.review(spec, unit) or {}
        else:
            # A refusal at the open, or inside the review at a call's own boundary, is this station's
            # named refusal: nothing is shipped or landed and the spec keeps its status for a retry.
            try:
                with self._launch("review", unit, context, decision) as handle:
                    rv = self._reviewer.review(spec, unit, calls=handle) or {}
            except EL.Refused as error:
                codes = (error.decision or {}).get("refusals") or [error.code]
                return self._refused("review", sid, {"refusals": list(codes)}, verdict=None, shipped=False,
                                     landed=False)
        verdict = rv.get("verdict")
        if not self._verdict_passes(rv):
            self._set_status(sid, self.fail_status)
            return {"ok": False, "kind": "review", "spec": sid, "verdict": verdict,
                    "shipped": False, "landed": False, "status": self.fail_status}
        land = self._land(unit, decision) or {}
        if not land.get("ok"):
            return {"ok": False, "kind": "review", "spec": sid, "verdict": verdict,
                    "shipped": False, "landed": False, "land": land}
        self._set_status(sid, "shipped")
        return {"ok": True, "kind": "review", "spec": sid, "verdict": verdict,
                "shipped": True, "landed": True, "status": "shipped", "land": land}

    def _review_floor(self, floor, unit, context, decision):
        """VELDO-0049: the enrolled review. The authority assigns this reviewer (never the builder,
        never a second position), the reviewer is launched with exactly that assignment, its signed
        receipt is recorded, and only the authority's handoff lets the lander run. Completion is
        the lander's: this writes no shipped status and no completion receipt."""
        sid = unit["spec"]
        if (floor.record(sid) or {}).get("state") == "handoff":
            # A land that failed after the handoff is retried; the reviews it was handed off on stand.
            return self._land_handed_off(floor, unit, decision, None, None)
        refused = dict(verdict=None, shipped=False, landed=False)
        try:
            assignment = floor.assign_review(sid, getattr(self._reviewer, "identity", None))
        except FloorRefused as error:
            return self._floor_refused("review", sid, error, "review_assignment", **refused)
        spec = dict(self._resolve(sid), status="review", assignment=assignment)
        try:
            with self._launch("review", unit, context, decision) as handle:
                rv = self._reviewer.review(spec, unit, calls=handle) or {}
        except EL.Refused as error:
            codes = (error.decision or {}).get("refusals") or [error.code]
            return self._refused("review", sid, {"refusals": list(codes)}, **refused)
        try:
            record = floor.record_review(sid, assignment["assignment"], rv.get("receipt"),
                                         return_to=self.fail_status)
        except FloorRefused as error:
            return self._floor_refused("review", sid, error, "review_record", **refused)
        review = record["reviews"][-1]
        verdict = review["body"]["verdict"]
        projection = floor.publish(sid)
        if record["state"] != "review" or not self._verdict_passes(review["body"]):
            return {"ok": False, "kind": "review", "spec": sid, "verdict": verdict, "shipped": False,
                    "landed": False, "status": record["state"], "projection": projection}
        try:
            floor.handoff(sid)
        except FloorRefused as error:
            return self._floor_refused("review", sid, error, "handoff", verdict=verdict, shipped=False,
                                       landed=False, status="review", projection=projection)
        return self._land_handed_off(floor, unit, decision, verdict, floor.publish(sid))

    def _land_handed_off(self, floor, unit, decision, verdict, projection):
        """The handed-off unit to the lander. A failed land leaves the handoff standing so a later
        dispatch of the unit retries it; nothing here establishes completion."""
        sid = unit["spec"]
        land = self._land(unit, decision) or {}
        if not land.get("ok"):
            return {"ok": False, "kind": "review", "spec": sid, "verdict": verdict, "shipped": False,
                    "landed": False, "status": "handoff", "land": land, "projection": projection}
        return {"ok": True, "kind": "review", "spec": sid, "verdict": verdict, "shipped": False,
                "landed": True, "status": "handoff", "land": land, "projection": projection}

    def _land(self, unit, ticket=None):
        """Land the built evidence through the serialized lander. The lander is
        reused machinery, but the built ref it lands is context the real worker
        supplies, so an unwired lander refuses rather than pretend a build reached
        the trunk (the same fail-loud posture as the delegated agent steps).

        VELDO-0052: with the floor enabled the PUBLICATION station decides first, against the
        review station's decision as its ticket, so an input that moved during review (a withdrawn
        dependency, a changed authority or admission) is a named refusal and nothing is landed.

        VELDO-0049: an enrolled unit lands only from the authority's handoff state."""
        gate = self._gate()
        floor = self._floor(gate)
        if floor is not None:
            state = (floor.record(unit["spec"]) or {}).get("state")
            if state != "handoff":
                return {"ok": False, "kind": "publication", "spec": unit["spec"], "state": "refused",
                        "halted_at": "handoff", "reason": "not_handed_off:%s" % state,
                        "refusals": ["not_handed_off:%s" % state], "landed": False}
        if gate is not None:
            decision = gate.decide("publication", unit["spec"], context=self._context(unit), ticket=ticket)
            if not decision["eligible"]:
                return self._refused("publication", unit["spec"], decision, landed=False)
        if self._lander is None:
            raise EX.ExecutorError(
                "no lander is wired; inject a serialized lander over GitLandOps for "
                "the built ref. Refusing to pretend a build reached the trunk.")
        return self._lander.land(unit)


def veldo_dispatch(unit, repo_root=None, hooks=None, reviewer=None, lander=None,
                  worker_id=None, claims_root=None, fail_status="ready", eligibility=None, calls=None,
                  authority=None):
    """Front door: build a Dispatcher for a repo and dispatch a single unit. A real
    caller injects the agent-backed build hooks, the fresh-context reviewer, and a
    lander over the built ref; this fabricates none of them."""
    disp = Dispatcher(repo_root=repo_root, hooks=hooks, reviewer=reviewer,
                      lander=lander, worker_id=worker_id, claims_root=claims_root,
                      fail_status=fail_status, eligibility=eligibility, calls=calls,
                      authority=authority)
    return disp.dispatch(unit)


# VELDO-0049: the floor authority. One registered store command, floor_transition, committed
# through control_store's signed journal on the caller's own connection (registered on that
# handle, as VELDO-0039's dispatch_transition is), and the Materializer that alone publishes an
# enrolled unit's status projection (VELDO-0035's ordinary materialization).

FLOOR_SCHEMA = "veldo.floor/v1"
FLOOR_OPERATION = "floor_transition"
FLOOR_KIND = "floor_unit"
ASSIGNMENT_SCHEMA = "veldo.review_assignment/v1"
RECEIPT_SCHEMA = "veldo.review_receipt/v1"
DISPOSITION_SCHEMA = "veldo.finding_disposition/v1"
REVIEW_POLICY_SCHEMA = "veldo.review_policy/v1"
REVIEW_POLICY_KIND = "review_policy"
# The OpenSSH namespace review receipts and finding dispositions are signed under.
REVIEW_NAMESPACE = "veldo-review"
PROOF_PATH = "proof/%s/manifest.json"
RECEIPT_VERDICTS = ("pass", "pass_with_notes", "fail", "escalate")
RULINGS = ("resolved", "rejected")

# action: (the floor states it may move a record from, the state it moves it to). None as a source
# is "no record yet"; None as a target is "decided by the transition" (a failing review returns the
# unit; a disposition leaves the state). No action here moves a unit to completion: only the lander's
# own receipts establish that.
FLOOR_STATES = ("review", "handoff", "returned")
FLOOR_TRANSITIONS = {
    "accept_build": ((None, "returned"), "review"),
    "assign_review": (("review",), "review"),
    "record_review": (("review",), None),
    "dispose_finding": (("review", "returned"), None),
    "handoff": (("review",), "handoff"),
}

FLOOR_TAXONOMY = {
    "invalid_input": "invalid_input", "duplicate_reviewer": "invalid_input", "malformed_command": "invalid_input",
    "command_content_conflict": "invalid_input",
    "missing_authority": "missing_authority", "not_authorized": "missing_authority",
    "reviewer_not_independent": "missing_authority",
    "stale_claim": "stale_subject", "stale_proof": "stale_subject", "stale_assignment": "stale_subject",
    "binding_mismatch": "stale_subject", "transition_refused": "stale_subject", "stale_version": "stale_subject",
    "missing_evidence": "missing_evidence", "awaiting_reviews": "missing_evidence",
    "unresolved_finding": "missing_evidence",
    "unavailable_service": "unavailable_service", "clock_uncertain": "unknown_outcome",
}


def floor_taxonomy(code):
    """The error class of a floor refusal; a code with no class is an unknown outcome, never success."""
    return FLOOR_TAXONOMY.get(str(code).split(":", 1)[0], "unknown_outcome")


class FloorRefused(Exception):
    """A named refusal of one floor transition; nothing was written. `codes` names every reason."""

    def __init__(self, code, detail="", codes=None):
        self.code, self.detail = code, detail
        self.codes = list(codes or [code])
        super().__init__(code + (": " + detail if detail else ""))


_FLOOR_ORGANS = {}


def _floor_organ(name):
    """The authority's organs, loaded on first use beside this file (the unenrolled path never pays)."""
    if name not in _FLOOR_ORGANS:
        _FLOOR_ORGANS[name] = _load("veldo_%s_floor" % name, ".veldo/%s.py" % name)
    return _FLOOR_ORGANS[name]


def floor_id(repository, unit):
    return "floor:" + json.dumps([repository, unit], separators=(",", ":"))


def review_policy_id(repository):
    return "review-policy:" + repository


def canonical(value):
    """The bytes a review receipt or a disposition is signed over: sorted, compact, ASCII JSON."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _hex(value):
    return isinstance(value, str) and len(value) in (40, 64) and set(value) <= set("0123456789abcdef")


def review_policy_record(policy_path):
    """The review policy record the owner accepts into the store at enrollment: each risk tier's
    required count of distinct independent reviews, read from the repository's policy.yaml
    risk_tiers (the retained engineering-review policy), with the digest of the bytes it came from."""
    path = Path(policy_path)
    policy = _Y.read(str(path))
    tiers = (policy or {}).get("risk_tiers") if isinstance(policy, dict) else None
    if not isinstance(tiers, dict) or not tiers:
        raise ValueError("policy risk_tiers must be a non-empty mapping")
    counts = {}
    for name, tier in tiers.items():
        count = tier.get("reviews", 1) if isinstance(tier, dict) else None
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("risk tier %r reviews must be a positive integer" % name)
        counts[name] = count
    return {"schema": REVIEW_POLICY_SCHEMA, "tiers": counts,
            "source": {"path": path.name, "digest": _digest(path.read_bytes())}}


def proof_problems(manifest, unit):
    """Why a proof manifest is not ACCEPTED proof for `unit`, by name: a missing contract field
    (validate.py's PROOF_REQ), another spec, an implementation commit that is not an object id, no
    criteria, or a criterion not passed with evidence."""
    if not isinstance(manifest, dict):
        return ["shape"]
    V = _floor_organ("validate")
    problems = ["field:" + f for f in V.PROOF_REQ if f not in manifest]
    if manifest.get("schema") != "veldo.proof/v1":
        problems.append("schema")
    if manifest.get("spec_id") != unit:
        problems.append("spec_id")
    if not _hex(manifest.get("commit")):
        problems.append("commit")
    criteria = manifest.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        problems.append("criteria")
    else:
        for c in criteria:
            if (not isinstance(c, dict) or c.get("status") != "passed" or not isinstance(c.get("evidence"), list)
                    or not c["evidence"]):
                problems.append("criterion:%s" % (c.get("id") if isinstance(c, dict) else "?"))
    return problems


# Reads inside the transaction.

def _row(conn, identity):
    row = conn.execute("SELECT kind, version, digest, data FROM entities WHERE id=?", (identity,)).fetchone()
    return None if row is None else {"kind": row[0], "version": row[1], "digest": row[2], "data": json.loads(row[3])}


def _member(conn, principal, now, boundary, repository):
    """The active membership of `principal` admitted at `boundary` and scoped to `repository`, or None."""
    AC = _floor_organ("authority_contract")
    CM = _floor_organ("control_membership")
    row = _row(conn, principal) if _text(principal) else None
    entry = dict(row["data"], principal=principal) if row and row["kind"] == "membership" else None
    active, _why = AC.active_member(entry, now)
    if (not active or entry.get("principal_type") not in AC.BOUNDARIES[boundary]
            or not CM.scope_covers(entry.get("scope"), repository)):
        return None
    return entry


def _signed_by(conn, principal, now, body, signature):
    """Whether `signature` is `principal`'s signature over the canonical body, with the principal's
    verification key active at `now`, under the review namespace."""
    AC = _floor_organ("authority_contract")
    keys = [dict(json.loads(data), key_id=identity)
            for identity, data in conn.execute("SELECT id, data FROM entities WHERE kind='verification_key'")]
    key = AC.active_key(keys, principal, now)
    if key is None or not _text(signature) or not signature.isascii():
        return False
    line = AC.allowed_signers_line(principal, key["public_key"], REVIEW_NAMESPACE)
    return AC.ssh_keygen_verify(canonical(body), signature, line, principal, REVIEW_NAMESPACE)[0]


def _commit_exists(repo, commit):
    r = _git_process.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", commit + "^{commit}"],
                         capture_output=True, text=True, timeout=15)
    return r.returncode == 0 and r.stdout.strip() == commit


def _blob(repo, commit, path):
    r = _git_process.run(["git", "-C", str(repo), "cat-file", "blob", commit + ":" + path],
                         capture_output=True, timeout=15)
    return None if r.returncode else r.stdout


def _descends(repo, older, newer):
    r = _git_process.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
                         capture_output=True, timeout=15)
    return r.returncode == 0


def _changed(repo, older, newer):
    r = _git_process.run(["git", "-C", str(repo), "diff", "--name-only", "--no-renames", "--no-ext-diff",
                          "--ignore-submodules=none", "-z", older, newer, "--"], capture_output=True, timeout=30)
    if r.returncode:
        return None
    return [p for p in r.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def _dispatches(conn, domain, repository, unit, station):
    """Every VELDO-0039 dispatch record of `unit` at `station`, newest attempt first."""
    found = []
    for identity, data in conn.execute("SELECT id, data FROM entities WHERE kind='dispatch'"):
        record = json.loads(data)
        contract = record.get("contract") or {}
        if (contract.get("domain"), contract.get("repository"), contract.get("unit"),
                contract.get("station")) == (domain, repository, unit, station):
            found.append(record)
    return sorted(found, key=lambda r: r["contract"].get("attempt") or 0, reverse=True)


def _clean_exit(record):
    termination = (record or {}).get("termination") or {}
    return ((record or {}).get("state") == "exited" and termination.get("returncode") == 0
            and termination.get("signal") is None and termination.get("deadline_stop") is False)


# The transition.

def floor_transition(conn, params, before):
    """THE ONE TRANSITION every floor command commits, inside its store transaction."""
    action, now = params.get("action"), params.get("now")
    if (action not in FLOOR_TRANSITIONS or not isinstance(now, (int, float)) or isinstance(now, bool)
            or not _text(params.get("unit")) or not _text(params.get("repository"))):
        raise FloorRefused("invalid_input", "unknown action, time, unit or repository")
    writer = _member(conn, params.get("principal"), now, "result_acceptance", params["repository"])
    if writer is None or writer.get("principal_type") != "service":
        raise FloorRefused("missing_authority", "not an active service member for this repository")
    unit, repository = params["unit"], params["repository"]
    rid = floor_id(repository, unit)
    current = (before.get(rid) or {}).get("data")
    allowed, _target = FLOOR_TRANSITIONS[action]
    state = current.get("state") if current else None
    if state not in allowed:
        raise FloorRefused("transition_refused:%s:%s" % (state, action))
    u = before.get(unit) or {}
    if u.get("kind") != "execution_unit" or (u.get("data") or {}).get("repository_uuid") != repository:
        raise FloorRefused("missing_authority:unit", unit)
    handler = {"accept_build": _accept_build, "assign_review": _assign_review, "record_review": _record_review,
               "dispose_finding": _dispose_finding, "handoff": _handoff}[action]
    record, unit_data = handler(conn, params, before, copy_record(current), dict(u["data"]))
    record["history"] = list(record.get("history") or []) + [
        {"action": action, "at": now, "principal": params["principal"], "state": record["state"]}]
    changes = {rid: {"kind": FLOOR_KIND, "data": record}}
    if unit_data != u["data"]:
        changes[unit] = {"kind": "execution_unit", "data": unit_data}
    return changes


def copy_record(record):
    return json.loads(json.dumps(record)) if record else None


def _claim_current(before, unit_data, repository, unit, holder, generation):
    """The claim the build ran under is still owned by `holder` at `generation` (VELDO-0031)."""
    CLM = _floor_organ("control_claim")
    cid = CLM.claim_id(repository, unit)
    claim = (before.get(cid) or {}).get("data") or {}
    backlog = (before.get(unit_data.get("backlog_item_uuid")) or {}).get("data") or {}
    status = CLM.ownership(claim, unit_data, backlog)
    if status == "unanswerable":
        raise FloorRefused("clock_uncertain", cid)
    if status != "owned" or not _text(holder) or claim.get("holder") != holder:
        raise FloorRefused("missing_authority:claim", cid)
    if claim.get("generation") != generation:
        raise FloorRefused("stale_claim", cid)


def _build_dispatch(conn, params, holder, generation):
    """The build's own newest VELDO-0039 dispatch, exited cleanly under this claim."""
    builds = _dispatches(conn, params["domain"], params["repository"], params["unit"], "build")
    build = builds[0] if builds else None
    bound = (build or {}).get("contract", {}).get("claim") or {}
    if not _clean_exit(build) or bound.get("holder") != holder or bound.get("generation") != generation:
        raise FloorRefused("missing_evidence:build_dispatch", "no exited build dispatch under this claim")
    return build


def _accepted_proof(repo, commit, unit):
    """(path, bytes, implementation commit) of ACCEPTED proof for `unit` at the built commit: read
    from Git, a valid manifest, naming the built commit or an ancestor with only this proof changed."""
    path = PROOF_PATH % unit
    body = _blob(repo, commit, path)
    if body is None:
        raise FloorRefused("missing_evidence:proof/absent", path)
    try:
        manifest = json.loads(body)
    except ValueError:
        raise FloorRefused("missing_evidence:proof/unreadable", path)
    problems = proof_problems(manifest, unit)
    if problems:
        raise FloorRefused("missing_evidence:proof/" + problems[0], ", ".join(problems))
    implementation = manifest["commit"]
    if not _commit_exists(repo, implementation) or not _descends(repo, implementation, commit):
        raise FloorRefused("stale_proof:not_ancestor", "the proof names a commit the built commit does not contain")
    changed = _changed(repo, implementation, commit)
    evidence = "proof/%s/" % unit
    if changed is None or any(not p.startswith(evidence) for p in changed):
        raise FloorRefused("stale_proof:changed_after_proof",
                           "the built commit changes more than its proof after the commit the proof names")
    return path, body, implementation


def _accept_build(conn, params, before, record, unit_data):
    """A build is accepted only with accepted proof at the exact built commit, a green gate, the
    current claim and its own exited build dispatch."""
    unit, domain, repository = params["unit"], params["domain"], params["repository"]
    commit, holder, generation = params.get("commit"), params.get("holder"), params.get("generation")
    store = _floor_organ("control_store")
    repo = store.bound_repository(conn, domain, repository)
    if repo is None:
        raise FloorRefused("missing_authority:repository", "no accepted repository is bound for this unit")
    if not _hex(commit) or not _commit_exists(repo, commit):
        raise FloorRefused("invalid_input:commit", "the built commit is not an exact commit of the repository")
    _claim_current(before, unit_data, repository, unit, holder, generation)
    gate = params.get("gate")
    if not isinstance(gate, dict) or gate.get("green") is not True:
        raise FloorRefused("missing_evidence:gate", "the gate did not pass on the built commit")
    build = _build_dispatch(conn, params, holder, generation)
    path, body, implementation = _accepted_proof(repo, commit, unit)
    record = record or {"schema": FLOOR_SCHEMA, "unit": unit, "domain": domain, "repository": repository,
                        "attempt": 0, "assignments": {}, "reviews": [], "findings": {}, "dispositions": []}
    record.update(state="review", attempt=record["attempt"] + 1,
                  source={"commit": commit, "implementation": implementation},
                  proof={"path": path, "digest": _digest(body)},
                  gate={"green": True, "detail": gate.get("detail"), "commit": commit},
                  builder=holder, builders=sorted(set(record.get("builders") or []) | {holder}),
                  generation=generation,
                  build={"dispatch": build["dispatch_id"], "process": build.get("process")},
                  handoff=None, returned_to=None)
    # The builder is the unit's producer: the review station's independence predicate reads it.
    return record, dict(unit_data, producer=holder)


def _assign_review(conn, params, before, record, unit_data):
    """A signed assignment of one eligible reviewer, bound to the exact source and proof."""
    reviewer = params.get("reviewer")
    if _member(conn, reviewer, params["now"], "assignment_acceptance", params["repository"]) is None:
        raise FloorRefused("not_authorized:reviewer", str(reviewer))
    if reviewer in (record.get("builders") or [record["builder"]]):
        raise FloorRefused("reviewer_not_independent", "a builder of this unit cannot review it")
    attempt = record["attempt"]
    if any(r["reviewer"] == reviewer and r["attempt"] == attempt for r in record["reviews"]):
        raise FloorRefused("duplicate_reviewer", "one principal fills one review position")
    serial = 1 + sum(1 for a in record["assignments"].values() if a["reviewer"] == reviewer and a["attempt"] == attempt)
    identity = "%s/%d/%s/%d" % (params["unit"], attempt, reviewer, serial)
    for other in record["assignments"].values():
        if other["reviewer"] == reviewer and other["attempt"] == attempt and other["state"] == "open":
            other["state"] = "superseded"
    payload = {"schema": ASSIGNMENT_SCHEMA, "assignment": identity, "unit": params["unit"], "reviewer": reviewer,
               "attempt": attempt, "source": {"commit": record["source"]["commit"]}, "proof": dict(record["proof"])}
    record["assignments"][identity] = {"reviewer": reviewer, "attempt": attempt, "state": "open",
                                       "payload": payload, "payload_digest": _digest(canonical(payload))}
    return record, unit_data


def _review_receipt(receipt):
    """(printed bytes, body, signature) of the reviewer's receipt, or the named missing receipt."""
    if not isinstance(receipt, dict) or not _text(receipt.get("dispatch")) or not isinstance(receipt.get("output"), str):
        raise FloorRefused("missing_evidence:review_receipt", "no signed receipt came back from the reviewer")
    printed = receipt["output"].encode()
    try:
        parsed = json.loads(printed)
        body, signature = parsed["body"], parsed["signature"]
    except (ValueError, TypeError, KeyError):
        raise FloorRefused("missing_evidence:review_receipt", "the receipt is not a signed review")
    if not isinstance(body, dict):
        raise FloorRefused("missing_evidence:review_receipt", "the receipt is not a signed review")
    return printed, body, signature


def _review_dispatch(conn, params, record, assignment, dispatch_id, printed):
    """The review dispatch the receipt names: exited cleanly at this unit's review station, launched
    with exactly the assignment at the assigned commit as the assigned reviewer, and the receipt is
    exactly what that process printed."""
    D = _floor_organ("control_dispatch")
    dispatch = (_row(conn, D.record_id(dispatch_id)) or {}).get("data") or {}
    contract = dispatch.get("contract") or {}
    if (contract.get("station") != "review" or contract.get("unit") != params["unit"]
            or contract.get("domain") != params["domain"] or contract.get("repository") != params["repository"]
            or not _clean_exit(dispatch)):
        raise FloorRefused("missing_evidence:review_dispatch", "the receipt names no exited review dispatch")
    given, payload = contract.get("input") or {}, assignment["payload"]
    if given.get("payload") != payload:
        # A fresh context: the reviewer was launched with exactly its assignment and nothing else.
        raise FloorRefused("binding_mismatch:review_dispatch/payload", "the reviewer was launched with other input")
    if (contract.get("source") or {}).get("commit") != record["source"]["commit"]:
        raise FloorRefused("binding_mismatch:review_dispatch/source", "the reviewer was launched at another commit")
    if (given.get("context") or {}).get("reviewer") != assignment["reviewer"]:
        raise FloorRefused("binding_mismatch:review_dispatch/reviewer", "the dispatch reviewed as another principal")
    if (dispatch.get("termination") or {}).get("output_digest") != _digest(printed):
        raise FloorRefused("binding_mismatch:review_output", "the receipt is not what the review dispatch printed")
    if dispatch.get("process") == (record.get("build") or {}).get("process"):
        raise FloorRefused("reviewer_not_independent:process", "the review ran in the builder's process")
    return dispatch


def _receipt_bound(conn, params, record, reviewer, body, signature):
    """The receipt answers this assignment, is signed by the assigned independent reviewer, and
    reviewed exactly the source and proof the authority accepted."""
    if body.get("schema") != RECEIPT_SCHEMA or body.get("assignment") != params["assignment"] \
            or body.get("unit") != params["unit"]:
        raise FloorRefused("binding_mismatch:assignment", "the receipt answers another assignment")
    if body.get("reviewer") != reviewer:
        raise FloorRefused("binding_mismatch:reviewer", "the receipt names another reviewer")
    if reviewer in (record.get("builders") or [record["builder"]]):
        raise FloorRefused("reviewer_not_independent", "a builder of this unit cannot review it")
    if not _signed_by(conn, reviewer, params["now"], body, signature):
        raise FloorRefused("not_authorized:review_signature", "the receipt is not signed by the assigned reviewer")
    if body.get("source") != record["source"]["commit"]:
        raise FloorRefused("binding_mismatch:source", "the receipt reviewed another commit")
    if body.get("proof") != record["proof"]["digest"]:
        raise FloorRefused("binding_mismatch:proof", "the receipt reviewed another proof")
    if body.get("verdict") not in RECEIPT_VERDICTS:
        raise FloorRefused("invalid_input:verdict", str(body.get("verdict")))


def _record_review(conn, params, before, record, unit_data):
    """The reviewer's own signed receipt, printed by its own review dispatch, bound to the assignment."""
    assignment = record["assignments"].get(params.get("assignment"))
    if not assignment or assignment["state"] != "open" or assignment["attempt"] != record["attempt"]:
        raise FloorRefused("stale_assignment", str(params.get("assignment")))
    reviewer = assignment["reviewer"]
    receipt = params.get("receipt")
    printed, body, signature = _review_receipt(receipt)
    dispatch = _review_dispatch(conn, params, record, assignment, receipt["dispatch"], printed)
    _receipt_bound(conn, params, record, reviewer, body, signature)
    blocking = PC.blocking_findings(body)
    findings = dict(record["findings"])
    raised = []
    for n, finding in enumerate(blocking, 1):
        fid = "%s/F%d" % (params["assignment"], n)
        findings[fid] = {"raised_by": reviewer, "attempt": record["attempt"], "assignment": params["assignment"],
                         "finding": finding, "resolved": None}
        raised.append(fid)
    passes = verdict_passes(body)
    record["findings"] = findings
    record["reviews"].append({"assignment": params["assignment"], "reviewer": reviewer, "attempt": record["attempt"],
                              "verdict": body["verdict"], "passes": passes, "raised": raised, "body": body,
                              "signature_digest": _digest(signature.encode()),
                              "dispatch": receipt["dispatch"], "output_digest": _digest(printed),
                              "process": dispatch.get("process")})
    assignment["state"] = "fulfilled"
    if not passes:
        record["state"], record["returned_to"] = "returned", params.get("return_to")
    return record, unit_data


def _dispose_finding(conn, params, before, record, unit_data):
    """An explicit, signed disposition of one blocking finding. Only the owner (a person) or the
    reviewer who raised it may dispose it, never the builder; a rejected ruling leaves it open."""
    fid = params.get("finding")
    finding = record["findings"].get(fid)
    if not finding:
        raise FloorRefused("invalid_input:finding", str(fid))
    disposition = params.get("disposition")
    body = (disposition or {}).get("body") if isinstance(disposition, dict) else None
    if (not isinstance(body, dict) or body.get("schema") != DISPOSITION_SCHEMA or body.get("finding") != fid
            or body.get("unit") != params["unit"] or body.get("ruling") not in RULINGS or not _text(body.get("by"))):
        raise FloorRefused("invalid_input:disposition", "a disposition names its finding, unit, ruling and signer")
    by = body["by"]
    member = _member(conn, by, params["now"], "assignment_acceptance", params["repository"])
    # Never a builder of any attempt; otherwise the owner (a person) or the reviewer who raised it.
    builder = by in (record.get("builders") or [record["builder"]])
    if builder or member is None or (member.get("principal_type") != "person" and by != finding["raised_by"]):
        raise FloorRefused("not_authorized:disposer", "only the owner or the finding's reviewer disposes it")
    if body.get("source") != record["source"]["commit"]:
        raise FloorRefused("binding_mismatch:source", "the disposition is for another commit")
    if not _signed_by(conn, by, params["now"], body, disposition.get("signature")):
        raise FloorRefused("not_authorized:disposition_signature", "the disposition is not signed by its disposer")
    entry = {"finding": fid, "ruling": body["ruling"], "by": by, "source": body["source"],
             "rationale": body.get("rationale"),
             "signature_digest": _digest(str(disposition.get("signature")).encode())}
    record["dispositions"] = list(record.get("dispositions") or []) + [entry]
    if body["ruling"] == "resolved":
        finding["resolved"] = {"by": by, "source": body["source"]}
    return record, unit_data


def _handoff(conn, params, before, record, unit_data):
    """The retained review policy in distinct passing reviewers, and no unresolved blocking finding."""
    risk = unit_data.get("risk")
    policy = (before.get(review_policy_id(params["repository"])) or {})
    tiers = ((policy.get("data") or {}).get("tiers") or {}) if policy.get("kind") == REVIEW_POLICY_KIND else {}
    need = tiers.get(risk)
    if not _text(risk) or not isinstance(need, int) or isinstance(need, bool) or need < 1:
        raise FloorRefused("missing_authority:review_policy", "no accepted review count for risk %r" % risk)
    attempt = record["attempt"]
    passing = sorted({r["reviewer"] for r in record["reviews"] if r["attempt"] == attempt and r["passes"]})
    unresolved = sorted(fid for fid, f in record["findings"].items() if not f.get("resolved"))
    codes = []
    if len(passing) < need:
        codes.append("awaiting_reviews:%d/%d" % (len(passing), need))
    codes.extend("unresolved_finding:" + fid for fid in unresolved)
    if codes:
        raise FloorRefused(codes[0], "; ".join(codes), codes)
    record["state"] = "handoff"
    record["handoff"] = {"reviewers": passing, "required": need, "risk": risk, "attempt": attempt,
                         "policy": {"version": policy.get("version"), "digest": policy.get("digest")},
                         "source": dict(record["source"]), "proof": dict(record["proof"])}
    return record, unit_data


class FloorAuthority:
    """One domain and repository's floor records over a real control store connection (VELDO-0049).
    `principal` is the service writing (an active `service` member scoped to the repository),
    `sign(bytes) -> text` signs its journal records as `signer`, `repo` is the enrolled repository
    the authority reads the built commits from and `projections` the directory the Materializer
    publishes into."""

    def __init__(self, store, conn, *, domain, repository, repo, projections, principal, signer, sign,
                 generation=1, observe=None, clock=None):
        if not all(_text(v) for v in (domain, repository, principal, signer)):
            raise FloorRefused("invalid_input", "domain, repository, principal and signer are named")
        self.store, self.conn = store, conn
        self.domain, self.repository, self.principal = domain, repository, principal
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        self.clock = clock or __import__("time").time
        self.counts = {"accepted": 0, "refused": 0}
        conn.command_registry[FLOOR_OPERATION] = {"transaction_transition": floor_transition,
                                                  "writes": ("entities", "journal", "commands", "nonces")}
        database = [path for _, name, path in conn.execute("PRAGMA database_list") if name == "main"][0]
        self.materializer = Materializer(store, database, domain=domain, repository=repository, repo=repo,
                                         root=projections, principal=principal, signer=signer, sign=sign,
                                         generation=generation)

    def close(self):
        self.materializer.close()

    # Reads.

    def record(self, unit):
        """The stored floor record of one unit, or None."""
        row = _row(self.conn, floor_id(self.repository, unit)) if _text(unit) else None
        return row["data"] if row and row["kind"] == FLOOR_KIND else None

    def version(self, unit):
        row = _row(self.conn, floor_id(self.repository, unit))
        return row["version"] if row else 0

    def status(self):
        """Metrics: accepted and refused commands, and the units in review, handed off or returned."""
        states = {}
        for (data,) in self.conn.execute("SELECT data FROM entities WHERE kind=?", (FLOOR_KIND,)):
            record = json.loads(data)
            if record.get("domain") == self.domain and record.get("repository") == self.repository:
                states[record["unit"]] = record["state"]
        return dict(self.counts, pending=sorted(u for u, s in states.items() if s == "review"),
                    handoff=sorted(u for u, s in states.items() if s == "handoff"),
                    returned=sorted(u for u, s in states.items() if s == "returned"))

    # Commands.

    def _run(self, action, unit, fields):
        if not _text(unit):
            raise FloorRefused("invalid_input", "a unit is named")
        rid = floor_id(self.repository, unit)
        unit_row = _row(self.conn, unit) or {}
        backlog = (unit_row.get("data") or {}).get("backlog_item_uuid")
        CLM = _floor_organ("control_claim")
        ids = [rid, unit, CLM.claim_id(self.repository, unit), review_policy_id(self.repository)]
        if _text(backlog):
            ids.append(backlog)
        params = dict(fields, action=action, unit=unit, now=self.clock(), principal=self.principal,
                      domain=self.domain, repository=self.repository)
        command_id = "floor/%s/%s/%s" % (action, unit, _command_digest(params))
        expected = {}
        for identity in ids:
            row = self.conn.execute("SELECT version FROM entities WHERE id=?", (identity,)).fetchone()
            expected[identity] = row[0] if row else 0
        command = dict(command_id=command_id, principal=self.principal, operation=FLOOR_OPERATION,
                       parameters=params, expected_versions=expected, artifact_digests=[],
                       nonce="floor/" + command_id)
        event = {"schema": FLOOR_SCHEMA, "operation": action, "domain": self.domain,
                 "repository": self.repository, "unit": unit, "request": command_id,
                 "accepted_versions": dict(expected)}
        try:
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (FloorRefused, self.store.StoreRefused) as error:
            self.counts["refused"] += 1
            codes = list(getattr(error, "codes", None) or [error.code])
            self.observe(dict(event, outcome="refused", refusal=error.code, refusals=codes,
                              taxonomy=floor_taxonomy(error.code)))
            if isinstance(error, FloorRefused):
                raise
            raise FloorRefused(error.code, error.detail) from error
        self.counts["accepted"] += 1
        record = self.record(unit)
        self.observe(dict(event, outcome="accepted", watermark=result["seq"], state=record["state"]))
        return record

    def accept_build(self, unit, *, commit, gate, holder, generation):
        """The build handed to review: accepted proof at `commit`, a green `gate`, the current claim."""
        return self._run("accept_build", unit, {"commit": commit, "gate": gate, "holder": holder,
                                                "generation": generation})

    def assign_review(self, unit, reviewer):
        """One review position for `reviewer`; returns the assignment payload the reviewer is launched with."""
        record = self._run("assign_review", unit, {"reviewer": reviewer})
        attempt = record["attempt"]
        mine = [a for a in record["assignments"].values()
                if a["reviewer"] == reviewer and a["attempt"] == attempt and a["state"] == "open"]
        return dict(mine[-1]["payload"])

    def record_review(self, unit, assignment, receipt, *, return_to=None):
        """The reviewer's signed receipt for `assignment`; returns the updated record."""
        return self._run("record_review", unit, {"assignment": assignment, "receipt": receipt, "return_to": return_to})

    def dispose_finding(self, unit, finding, disposition):
        """A signed disposition {body, signature} of one blocking finding."""
        return self._run("dispose_finding", unit, {"finding": finding, "disposition": disposition})

    def handoff(self, unit):
        """The unit handed to the lander when the review policy is met and nothing blocks it."""
        return self._run("handoff", unit, {})

    def publish(self, unit):
        """The unit's current record published by the Materializer; a refusal is returned, never raised."""
        row = _row(self.conn, floor_id(self.repository, unit))
        event = {"schema": FLOOR_SCHEMA, "operation": "publish", "domain": self.domain,
                 "repository": self.repository, "unit": unit}
        if not row or row["kind"] != FLOOR_KIND:
            self.observe(dict(event, outcome="refused", refusal="missing_authority:floor_record",
                              taxonomy="missing_authority"))
            return {"refused": "missing_authority:floor_record"}
        data = row["data"]
        try:
            published = self.materializer.publish(unit, floor_id(self.repository, unit), data["source"]["commit"],
                                                  {data["proof"]["path"]: data["proof"]["digest"]})
        except self.materializer.refusals + (OSError,) as error:
            code = getattr(error, "code", type(error).__name__)
            self.observe(dict(event, outcome="refused", refusal=code, taxonomy=floor_taxonomy(code)))
            return {"refused": code}
        self.observe(dict(event, outcome="accepted", watermark=published["watermark"],
                          snapshot=published["snapshot"]))
        return published


def _command_digest(value):
    """A short content digest naming one command (idempotent by content, as dispatch commands are)."""
    return hashlib.sha256(canonical(value)).hexdigest()[:24]


class Materializer:
    """THE MATERIALIZER of an enrolled unit's status projection: VELDO-0035's ordinary
    materialization. Each publication accepts the unit's revision (the exact source commit, its
    proof document and the floor record as its status), accepts a snapshot of it, and publishes
    that snapshot's complete bytes at an explicit watermark into a new directory
    <root>/<unit>/<record version>, never updating one already published. It runs on its own store
    connection because VELDO-0035's read-set registration replaces that connection's registration of
    the operation it enables; nothing consumes a publication snapshot."""

    OPERATION = "record_receipt"

    def __init__(self, store, database, *, domain, repository, repo, root, principal, signer, sign, generation=1):
        RS = _floor_organ("control_readset")
        self.SN = RS.SN
        self.refusals = (self.SN.Refused, store.StoreRefused)
        self.store, self.domain, self.repository = store, domain, repository
        self.repo, self.root = str(repo), Path(root)
        self.principal, self.signing = principal, {"signer": signer, "sign": sign, "authority_generation": generation}
        self.conn = store.open_store(database)
        self.revisions = RS.attach_revisions(store, self.conn, domain, {repository: self.repo})
        self.reader = RS.attach(store, self.conn, self.repo, domain, repository)
        self.reader.enable(self.OPERATION, {"revision": "$revision", "entities": {}, "collections": {}})

    def close(self):
        self.conn.close()

    def publish(self, unit, status_entity, commit, documents):
        row = self.conn.execute("SELECT version FROM entities WHERE id=?", (status_entity,)).fetchone()
        current = self.root / unit / ("%06d" % (row[0] if row else 0))
        if (current / "manifest.json").exists():
            # This version is published already: a projection is never rewritten.
            manifest = json.loads((current / "manifest.json").read_text())
            return {"snapshot": manifest.get("snapshot_id"), "path": str(current), "version": row[0],
                    "watermark": manifest.get("watermark"), "manifest": manifest, "reused": True}
        revision = "floor-revision:%s:%s" % (self.repository, unit)
        self.revisions.accept(revision, self.repository, commit, self.principal, documents=dict(documents),
                              statuses={"status/%s.json" % unit: status_entity}, **self.signing)
        snapshot_id = "floor-projection:%s:%s:%s" % (self.repository, unit, uuid.uuid4().hex)
        command = {"command_id": "floor.project:" + snapshot_id, "principal": self.principal,
                   "operation": "accept_snapshot",
                   "parameters": {"snapshot_id": snapshot_id, "operation": self.OPERATION,
                                  "arguments": {"revision": revision}},
                   "expected_versions": {snapshot_id: 0}, "artifact_digests": [], "nonce": "floor.project:" + snapshot_id}
        self.reader.execute(command, **self.signing)
        snapshot = self.SN.load(self.store, self.conn, snapshot_id, self.domain, self.repository)
        version = snapshot["statuses"]["status/%s.json" % unit]["version"]
        destination = self.root / unit / ("%06d" % version)
        manifest = self.SN.materialize(snapshot, self.repo, destination)
        return {"snapshot": snapshot_id, "path": str(destination), "version": version,
                "watermark": manifest["watermark"], "manifest": manifest}
