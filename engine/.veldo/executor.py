#!/usr/bin/env python3
"""VELDO executor: drive a ready spec through the whole loop.

The loop is: resolve a ready spec, enforce the plan (for a planned spec), build,
gate, proof, independent review, and merge readiness. The point of the executor
is that a human APPROVES and STEERS rather than hand-driving every step: the
executor sequences the steps, runs the mechanical ones itself, delegates and
PAUSES for the agent and human ones, halts the loop the instant a step fails,
and records the human minutes the run cost.

The split is deliberate and honest:

  MECHANICAL, the executor runs itself - the step sequencing, the halt on a
  failed step, running the gate over the gate seam, assembling and validating
  the proof, emitting the loop events (carrying human_minutes), and assembling
  the receipt. This is pure control logic over seams and is gate-tested here
  with fake step callables and no live agent or backend.

  DELEGATED, the executor pauses for - build, review, and approve/steer. These
  are agent and human work; the executor calls the injected callable and uses
  whatever it returns. It cannot fabricate a build, a verdict, or an approval.

HALT ON FAILURE is load-bearing. A failed step stops the loop: a red gate does
NOT proceed to proof, review, or merge; a fail verdict does NOT proceed to
merge; two failed review cycles stop and bring in the human (at that point the
defect is almost always in the specification). run() returns a state - halted at
a named step with the reason, or ready with the receipt - and the human minutes
for the run either way.

The deploy-of-work surfaces (the real gate command, the event log, the spec
files, the plan check) are a seam: LoopSteps is the interface, LiveLoop is the
reference wired to the real seams with the agent and human steps failing LOUD
rather than pretending. The control logic below (Executor.run, loop_respected)
talks only to the seam so it is testable with a fake, exactly as the release
runner drives a fake deployer.

OBSERVED RUNS (WARP-0502): the executor takes an OPTIONAL run-observer, a second
seam that is DEFAULT OFF. When an observer is injected the executor reports its
live progress through it as it moves the loop - a step at each phase it enters,
a heartbeat while it works, a block with the question when it pauses for a human,
and a terminal finish that reflects the outcome. The reference RunLogObserver
bridges those hooks to the WARP-0501 run registry (runlog): the durable
milestones (run.started, run.blocked, run.resumed, run.done, run.aborted) and the
high-volume per-step and heartbeat progress all land in the run folder's
live.jsonl, never the committed events.jsonl. The observer is pure side effect:
run() ignores every return value and computes its result from the loop alone, so
an observed run and an unobserved run reach byte-identical results and the halt
semantics do not change. The thin veldo_run driver allocates a run, wires the
observer, drives the executor, and hands back the receipt plus the run id.

INTERACTION (WARP-0505): a human can answer, steer, or abort a running or
blocked build COOPERATIVELY, through the run inbox (runlog.post_command). The
run process that owns the build acts on the commands at its own SAFE CHECKPOINTS
(between loop steps, and while it is blocked waiting on a human); nothing
external ever signals or kills the process. handle_run_commands drains the inbox
at one checkpoint and acts - an answer to a blocked run records the answer and
RESUMES it, an abort requests the loop stop and finish the run aborted at THIS
checkpoint, and a steer is recorded and surfaced to the agent for its next turn
- acking each command exactly once so it is never reprocessed. run_checkpoint_loop
is the reference cooperative driver: it runs the build's units of work and calls
that handler at each safe checkpoint, honoring an abort by finishing aborted and
STOPPING (no further step runs) and a blocked-wait by resuming on an answer. All
of this is inbox read/write plus cooperative checkpoint control over runlog; the
separate RULE that an answer changing a requirement or a durable decision must be
committed to the spec (or an ADR) before the build is accepted - so a chat answer
never becomes hidden engineering truth - is a documented PROCEDURE for the agent
(see the run skill), not code enforced here.
"""
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The ordered steps of the loop. plan_check runs only for a planned spec; the
# rest run for every spec. A step that is not "ok" halts before the next one.
STEP_SEQUENCE = ("resolve", "plan_check", "build", "gate", "proof", "review",
                 "merge_ready")

# A review verdict that lets the loop proceed to merge readiness. Anything else
# is a failed cycle.
PASSING_VERDICTS = ("pass", "pass_with_notes")


class ExecutorError(RuntimeError):
    """A step the executor cannot run because its surface is absent, or a spec
    that cannot be resolved. Named and loud: the executor never silently
    fabricates a build, a verdict, an approval, or a gate result."""


def _load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LoopSteps:
    """The loop-surface seam. A concrete implementation supplies the mechanical
    surfaces (resolve, run_check, gate, assemble_proof, validate_proof,
    merge_ready, emit) and the delegated agent/human steps (build, review,
    approve). The executor talks only to this interface, so its control logic is
    surface agnostic and testable with a fake."""

    def resolve(self, spec_id):
        """Return the spec front matter as a mapping (at least id and status),
        or raise ExecutorError if it cannot be resolved."""
        raise NotImplementedError

    def run_check(self, spec):
        """For a planned spec: return (ok, reason). ok False refuses the build
        (an unshipped dependency or a stale plan revision)."""
        raise NotImplementedError

    def build(self, spec):
        """AGENT step, run in a FRESH sub-context. Return a mapping with ok
        (default True), commit, and an evidence map. The executor pauses here and
        cannot fabricate the result. CLEAN-CONTEXT CONTRACT (WARP-0909): a
        long-running orchestrator dispatches this step to a fresh sub-agent and
        retains only its compact receipt (the bounded projection in work.py,
        dispatch_receipt / RECEIPT_FIELDS), never the build transcript, so a
        many-spec loop's memory stays flat instead of accumulating every spec."""
        raise NotImplementedError

    def gate(self):
        """MECHANICAL. Return {green: bool, detail: str}. The reference runs the
        canonical gate command."""
        raise NotImplementedError

    def assemble_proof(self, spec, build):
        """MECHANICAL. Build the proof manifest mapping for the built change."""
        raise NotImplementedError

    def validate_proof(self, proof):
        """MECHANICAL. Return (ok, errors) for the assembled manifest."""
        raise NotImplementedError

    def review(self, spec, proof):
        """AGENT step, run in a FRESH sub-context. Return {verdict, human_minutes}.
        CLEAN-CONTEXT CONTRACT (WARP-0909): a long-running orchestrator dispatches
        this step to a fresh sub-agent and holds only its receipt (the verdict and
        summary via work.py dispatch_receipt), never the reviewer's full reasoning
        transcript, so the orchestrator's footprint does not grow per spec."""
        raise NotImplementedError

    def merge_ready(self, spec, proof, verdict):
        """MECHANICAL. Return (ready, awaiting) - awaiting is what a human must
        do before merge, or None when policy is clear."""
        raise NotImplementedError

    def approve(self, spec, receipt_bits):
        """HUMAN step. The executor pauses for the approve/steer decision.
        Return {decision, human_minutes, note}."""
        raise NotImplementedError

    def emit(self, etype, spec=None, commit=None, human_minutes=None, **fields):
        """MECHANICAL. Append a loop event. The reference appends to the event
        log via the event emitter."""
        raise NotImplementedError


class LiveLoop(LoopSteps):
    """Reference loop wired to the real seams. The mechanical steps are real and
    hermetic (gate over the canonical verify command, proof validation over the
    contract validator, events over the event emitter, spec resolution over the
    spec files, plan enforcement over the plan ops). The agent and human steps
    fail LOUD, so an adopting runtime must inject an agent-backed build and
    review and a human-backed approve: a loop that silently no-ops a build or a
    review is more dangerous than one that refuses to run."""

    def __init__(self, root=ROOT):
        self.root = Path(root)

    def resolve(self, spec_id):
        V = _load_module("veldo_validate_exec", ".veldo/validate.py")
        specs = self.root / "specs"
        matches = sorted(specs.glob("%s*.md" % spec_id)) if specs.exists() else []
        if not matches:
            raise ExecutorError("cannot resolve spec %r: no matching file under specs/" % spec_id)
        text = matches[0].read_text()
        fm = V.front_matter(text) or {}
        return {
            "id": fm.get("id", spec_id),
            "status": fm.get("status"),
            "lane": fm.get("lane"),
            "plan": fm.get("plan"),
            "work": fm.get("work"),
            "criteria_ids": V.spec_criterion_ids(matches[0]),
            "path": str(matches[0]),
        }

    def run_check(self, spec):
        r = subprocess.run(
            ["python3", str(self.root / ".veldo" / "plan.py"), "run-check",
             str(spec.get("plan")), str(spec.get("id"))],
            capture_output=True, text=True, cwd=str(self.root))
        return (r.returncode == 0, (r.stdout + r.stderr).strip())

    def build(self, spec):
        raise ExecutorError(
            "build is a delegated agent step; LiveLoop has no agent wired. Inject "
            "a build callable that dispatches the implementer and returns its "
            "commit and evidence. Refusing to fabricate a build.")

    def gate(self):
        r = subprocess.run(["bash", str(self.root / "scripts" / "verify.sh")],
                           capture_output=True, text=True, cwd=str(self.root))
        return {"green": r.returncode == 0, "detail": r.stdout.strip().splitlines()[-1]
                if r.stdout.strip() else "gate produced no output"}

    def assemble_proof(self, spec, build):
        """Build a proof manifest from the spec criteria and the build evidence.
        Mechanical: it maps each spec criterion to its evidence from the build,
        so a missing evidence entry becomes a criterion the validator rejects
        rather than a silent pass."""
        evidence = (build or {}).get("evidence") or {}
        criteria = []
        for cid in spec.get("criteria_ids") or []:
            # Every criterion is claimed passed; a criterion with no evidence is
            # left evidence-empty on purpose so the validator rejects the proof
            # (a build that proved nothing must not assemble a clean manifest).
            criteria.append({"id": cid, "status": "passed",
                             "evidence": evidence.get(cid) or []})
        return {
            "schema": "veldo.proof/v1",
            "spec_id": spec.get("id"),
            "commit": (build or {}).get("commit", ""),
            "producer": "executor",
            "criteria": criteria,
            "checks": (build or {}).get("checks") or [{"name": "unit", "status": "passed"}],
            "rollback": (build or {}).get("rollback", "git revert"),
        }

    def validate_proof(self, proof):
        V = _load_module("veldo_validate_exec", ".veldo/validate.py")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as f:
            f.write(json.dumps(proof))
            f.flush()
            errs = V.check_json(f.name, V.PROOF_REQ, "proof")
        return (errs == 0, errs)

    def review(self, spec, proof):
        raise ExecutorError(
            "review is a delegated fresh-context agent step; LiveLoop has no "
            "reviewer wired. Inject a review callable that dispatches the "
            "reviewer and returns its verdict. Refusing to fabricate a verdict.")

    def merge_ready(self, spec, proof, verdict):
        """Ready unless the change touches a human lane or protected paths that
        need an approval the run has not attested. The reference reads the spec
        lane hints; a real control plane replaces this with the policy check."""
        protected = spec.get("protected_paths")
        if protected:
            return (False, "approval for protected paths: %s" % protected)
        if str(spec.get("human_approval", "not_required")).split()[0] != "not_required":
            return (False, "human approval required by the spec")
        return (True, "human go-ahead to merge (policy clear)")

    def approve(self, spec, receipt_bits):
        raise ExecutorError(
            "approve is a human step; LiveLoop has no human wired. Inject an "
            "approve callable that pauses for the human decision. Refusing to "
            "fabricate an approval.")

    def emit(self, etype, spec=None, commit=None, human_minutes=None, **fields):
        EV = _load_module("veldo_events_exec", ".veldo/events.py")
        return EV.emit(etype, spec=spec, commit=commit,
                       human_minutes=human_minutes,
                       producer="executor.py", extra=fields or None)


class RunObserver:
    """Optional run-progress observer seam. DEFAULT NO-OP: every hook does
    nothing, so the executor stays pure control logic unless an observer is
    injected, and a concrete observer need only override the hooks it cares
    about. An observer can NEVER change a run's outcome - Executor.run ignores
    every return value and computes its result from the loop steps alone. The
    reference implementation is RunLogObserver, which bridges these hooks to the
    WARP-0501 run registry."""

    def on_start(self, spec_id):
        """The observed run has begun (the run folder is allocated by the
        driver before the loop starts)."""

    def on_step(self, phase, detail=None):
        """The executor is entering a named loop phase (high volume, live-only)."""

    def on_heartbeat(self, phase=None):
        """The executor is working (high volume, live-only)."""

    def on_block(self, question):
        """The executor is pausing for a human decision (a durable milestone)."""

    def on_resume(self):
        """The human decision arrived and the loop is proceeding."""

    def on_finish(self, status, reason=None, receipt=None):
        """Terminal outcome: ready with the receipt, or halted with the reason."""


class RunLogObserver(RunObserver):
    """Bridge the executor's run-observer hooks to the WARP-0501 run registry.

    The run folder is allocated by the driver (veldo_run) via runlog.start_run so
    the run id is known before the loop starts; this observer writes the per-step
    progress, the heartbeats, the blocked question, and the terminal finish for
    that already-allocated run. on_step and on_heartbeat are LIVE-ONLY (they land
    in the run folder's live.jsonl, never the committed events.jsonl);
    on_block/on_resume/on_finish are the durable milestones runlog records. A
    halt is finished ABORTED with its reason recorded on the run state; a ready
    run is finished DONE. A halt that pauses for a human (the two-failed-review
    adjudication) is a block, not a terminal finish, so the run awaits the human
    rather than being reported done."""

    def __init__(self, run_id, root=None, runlog=None):
        self.run_id = run_id
        self.root = root
        self._rl = runlog or _load_module("veldo_runlog_obs", ".veldo/runlog.py")

    def on_step(self, phase, detail=None):
        self._rl.step(self.run_id, phase, detail=detail, root=self.root)

    def on_heartbeat(self, phase=None):
        self._rl.heartbeat(self.run_id, phase=phase, root=self.root)

    def on_block(self, question):
        self._rl.block(self.run_id, question, root=self.root)

    def on_resume(self):
        self._rl.resume(self.run_id, root=self.root)

    def on_finish(self, status, reason=None, receipt=None):
        # ready (whole loop) and built (build-only stop at review) are clean
        # terminals -> done; every other terminal is an abort.
        terminal = "done" if status in ("ready", "built") else "aborted"
        if reason:
            self._rl.set_state(self.run_id, root=self.root, reason=reason)
        self._rl.finish(self.run_id, status=terminal, root=self.root)


class Executor:
    """Drive a ready spec through the loop over the LoopSteps seam.

    run(spec_id) sequences the steps, halts on the first failed one, records the
    human minutes the run cost, and assembles the receipt. The control logic is
    entirely here; the seam supplies the surfaces. Nothing is fabricated: a
    build, a verdict, and an approval come from the delegated callables."""

    def __init__(self, hooks, observer=None):
        self.hooks = hooks
        self.observer = observer

    def run(self, spec_id, max_review_cycles=2, stop_after=None):
        """Drive the spec through the loop. stop_after is a DEFAULTED build-only
        hook: with the default None the whole loop runs unchanged (resolve through
        merge readiness). With stop_after='proof' the run finishes cleanly at the
        distinct 'built' state after exactly one build/gate/proof cycle, WITHOUT
        entering review or merge - the fleet dispatcher reviews as a separate,
        independent unit, so a build worker never reviews its own work. Every other
        halt semantic is unchanged, so the existing default-path behavior is
        byte-for-byte identical."""
        if max_review_cycles < 1:
            raise ExecutorError("max_review_cycles must be at least 1")
        steps = []
        state = {"spec_id": spec_id, "human_minutes": 0}

        obs = self.observer

        def ob(method, *args, **kw):
            # Report to the run observer if one is injected; DEFAULT OFF is a
            # no-op so the control logic is untouched. The result is never read,
            # so the observer cannot change the run's outcome or halt semantics.
            if obs is not None:
                getattr(obs, method)(*args, **kw)

        ob("on_start", spec_id)

        def record(name, ok, **extra):
            entry = {"name": name, "ok": bool(ok)}
            entry.update(extra)
            steps.append(entry)
            return entry

        def finish(status, halted_at, reason, awaiting_human,
                   proof=None, gate_green=None, verdict=None):
            criteria = [c.get("id") for c in (proof or {}).get("criteria", [])
                        if c.get("status") == "passed"]
            receipt = {
                "spec_id": spec_id,
                "criteria_proven": criteria,
                "gate": (None if gate_green is None
                         else ("green" if gate_green else "red")),
                "verdict": verdict,
                "human_minutes": state["human_minutes"],
                "awaiting_human": awaiting_human,
            }
            # Report the terminal outcome (or the human block) to the observer.
            # A halt at review is the two-failed-review adjudication: the run is
            # BLOCKED for a human to decide, not aborted, so it awaits the human
            # rather than being finished. Every other halt is a terminal abort;
            # ready is a terminal done.
            if status in ("ready", "built"):
                # a clean terminal: ready is the whole loop done, built is the
                # build-only stop at review (stop_after='proof'). Both report a
                # finish to the observer, never a halt.
                ob("on_finish", status, receipt=receipt)
            elif halted_at == "review":
                ob("on_block", reason)
            else:
                ob("on_finish", "halted", reason=reason)
            return {
                "state": status,
                "halted_at": halted_at,
                "reason": reason,
                "steps": steps,
                "human_minutes": state["human_minutes"],
                "receipt": receipt,
            }

        # 1. resolve - the spec must exist and be ready
        ob("on_step", "resolve")
        try:
            spec = self.hooks.resolve(spec_id)
        except Exception as ex:  # a resolution failure is a clean halt, not a crash
            record("resolve", False, reason=str(ex))
            return finish("halted", "resolve", str(ex), None)
        status = (spec or {}).get("status")
        if status != "ready":
            reason = "spec %s is %r, not ready" % (spec_id, status)
            record("resolve", False, reason=reason)
            return finish("halted", "resolve", reason, None)
        record("resolve", True)

        # 1a. plan enforcement for a planned spec (mechanical refusal)
        if spec.get("plan") and spec.get("work"):
            ob("on_step", "plan_check")
            ok, reason = self.hooks.run_check(spec)
            record("plan_check", ok, reason=reason)
            if not ok:
                return finish("halted", "plan_check", reason, None)

        proof = None
        gate_green = None
        verdict = None
        cycle = 0
        while True:
            cycle += 1
            # 2. build (delegated agent step; the executor pauses here)
            ob("on_step", "build")
            build = self.hooks.build(spec)
            ob("on_heartbeat", "build")
            b_ok = bool(build.get("ok", True))
            record("build", b_ok, cycle=cycle, commit=build.get("commit"))
            if not b_ok:
                return finish("halted", "build",
                              build.get("reason", "build failed"), None,
                              proof, gate_green, verdict)

            # 3. gate (mechanical; the executor runs it itself)
            ob("on_step", "gate")
            g = self.hooks.gate()
            gate_green = bool(g.get("green"))
            record("gate", gate_green, cycle=cycle, detail=g.get("detail"))
            if not gate_green:
                # HALT: a red gate does NOT proceed to proof, review, or merge.
                return finish("halted", "gate",
                              g.get("detail", "gate red"), None,
                              proof, gate_green, verdict)

            # 4. proof (mechanical assemble + validate)
            ob("on_step", "proof")
            proof = self.hooks.assemble_proof(spec, build)
            p_ok, p_err = self.hooks.validate_proof(proof)
            record("proof", p_ok, cycle=cycle, errors=p_err)
            if not p_ok:
                return finish("halted", "proof",
                              "proof did not validate (%s problem(s))" % p_err,
                              None, proof, gate_green, verdict)
            self.hooks.emit("proof.recorded", spec=spec.get("id"),
                            commit=build.get("commit"))

            if stop_after == "proof":
                # BUILD-ONLY STOP: a passing build/gate/proof, then finish at the
                # distinct 'built' state WITHOUT dispatching review or merge. The
                # fleet dispatcher makes review a separate claimable unit for a
                # fresh context, so the build worker never reviews its own work.
                # Exactly one build/gate/proof cycle ran; verdict stays None.
                return finish("built", None, None, None,
                              proof, gate_green, verdict)

            # 5. review (delegated fresh-context agent step; the executor pauses)
            ob("on_step", "review")
            self.hooks.emit("review.requested", spec=spec.get("id"))
            rv = self.hooks.review(spec, proof)
            verdict = rv.get("verdict")
            rmin = int(rv.get("human_minutes", 0) or 0)
            state["human_minutes"] += rmin
            self.hooks.emit("verdict.recorded", spec=spec.get("id"),
                            commit=build.get("commit"),
                            human_minutes=(rmin or None), verdict=verdict)
            passed = verdict in PASSING_VERDICTS
            record("review", passed, cycle=cycle, verdict=verdict)
            if passed:
                break
            # a fail verdict does NOT proceed to merge; steer or stop.
            if cycle >= max_review_cycles:
                reason = ("%d failed review cycle(s); bring in the human "
                          "(the defect is usually in the specification)" % cycle)
                return finish("halted", "review", reason,
                              "human decision: adjudicate the specification",
                              proof, gate_green, verdict)
            # else re-drive the loop for another build/gate/proof/review cycle

        # 6. merge readiness (mechanical policy)
        ob("on_step", "merge_ready")
        ready, awaiting = self.hooks.merge_ready(spec, proof, verdict)
        record("merge_ready", ready, awaiting=awaiting)

        # human approve/steer (delegated human step; the executor PAUSES for the
        # human here - the run is blocked on that decision until the human acts,
        # then resumes - and never merges: merging on the go-ahead is the human's
        # act)
        ob("on_block", "approve or steer: %s" % (awaiting or "merge readiness"))
        approve = self.hooks.approve(spec, {"ready": ready, "awaiting": awaiting})
        ob("on_resume")
        amin = int(approve.get("human_minutes", 0) or 0)
        state["human_minutes"] += amin
        decision = approve.get("decision")
        self.hooks.emit("approval.recorded", spec=spec.get("id"),
                        human_minutes=(amin or None), decision=decision)

        if decision == "approved" and ready:
            awaiting_human = None
        else:
            awaiting_human = approve.get("note") or awaiting or "human approval to merge"
        return finish("ready", None, None, awaiting_human,
                      proof, gate_green, verdict)


def loop_respected(result):
    """The halt-on-failure invariant, as a pure predicate over a run result.

    Two things must hold, and a driver that proceeds past a failure breaks them:
    a failed gate step has no proof, review, or merge_ready step after it; and a
    run that ended on a failed final verdict (halted at review) never reached
    merge_ready, nor does any merge_ready step sit after a failing review. A
    mutant driver that ignored a red gate or a fail verdict and pushed on
    produces exactly those forbidden downstream steps, so this returns False for
    it while the real run returns True. That is what gives the halt assertions
    teeth - they are not vacuous."""
    steps = result.get("steps", [])
    names = [s["name"] for s in steps]
    for i, s in enumerate(steps):
        if s["name"] == "gate" and not s["ok"]:
            if any(later["name"] in ("proof", "review", "merge_ready")
                   for later in steps[i + 1:]):
                return False
    if result.get("state") == "halted" and result.get("halted_at") == "review":
        if "merge_ready" in names:
            return False
    if "merge_ready" in names:
        reviews = [s for s in steps if s["name"] == "review"]
        if not reviews or not reviews[-1]["ok"]:
            return False
    return True


def veldo_run(spec_id, hooks, root=None, head=None, max_review_cycles=2, runlog=None):
    """veldo run <spec>: allocate an observed run in the WARP-0501 registry, drive
    the ready spec through the executor with the run observer ON, and return the
    receipt plus the run id.

    This is the thin registry-plus-executor glue that makes a running build
    stream its live progress while the agent still builds and the human still
    approves. The loop hooks (the agent-backed build and review and the
    human-backed approve) are INJECTED by the caller - the run skill wires them;
    this function fabricates none of them. It allocates the run first (so the run
    id exists before the loop starts, and a reader can watch from the beginning),
    wires a RunLogObserver, and drives the executor. If the loop raises before it
    can finish (for example a loop with no agent-backed build), the run is marked
    aborted with the error recorded so a crashed build never lingers as falsely
    active, and the error is re-raised."""
    rl = runlog or _load_module("veldo_runlog_run", ".veldo/runlog.py")
    run_id = rl.start_run(spec_id, head=head, root=root)
    observer = RunLogObserver(run_id, root=root, runlog=rl)
    ex = Executor(hooks, observer=observer)
    try:
        result = ex.run(spec_id, max_review_cycles=max_review_cycles)
    except BaseException as err:
        rl.set_state(run_id, root=root, reason=repr(err))
        rl.finish(run_id, status="aborted", root=root)
        raise
    return {"run_id": run_id, "result": result, "receipt": result.get("receipt")}


def handle_run_commands(run_id, root=None, runlog=None):
    """Drain a running build's inbox at ONE safe checkpoint and act cooperatively.

    Reads the pending commands oldest-first (runlog.read_inbox) and, for each:

      answer  records the answer on the run and, if the run is currently
              BLOCKED, RESUMES it (runlog.resume); an answer to a run that is
              not blocked is still recorded but does not force a resume.
      abort   sets abort in the returned decision - the OWNING loop stops and
              finishes the run aborted; this handler never kills a process.
      steer   is recorded and collected into the decision so the caller can
              surface it to the agent at its next turn; it is NOT an answer and
              never resumes or aborts.

    Every command is ack'd EXACTLY ONCE (runlog.ack_command moves it to
    commands/acked/), so a drained command is never reprocessed at the next
    checkpoint. The high-volume record is live-only (append_live 'run.command'),
    never the committed event stream; resume rides the existing run.resumed
    milestone. Returns a decision dict:
      {abort, resumed, answers, steers, acted} - acted is the ack'd command ids.

    This is the mechanical inbox handling. It reuses the WARP-0501 registry
    (read_inbox/ack_command/read_state/set_state/resume/append_live) and adds no
    store or event logic of its own."""
    rl = runlog or _load_module("veldo_runlog_cmd", ".veldo/runlog.py")
    decision = {"abort": False, "resumed": False,
                "answers": [], "steers": [], "acted": []}
    for cmd in rl.read_inbox(run_id, root=root):
        kind = cmd.get("kind")
        cmd_id = cmd.get("cmd_id")
        payload = cmd.get("payload")
        if kind == "abort":
            decision["abort"] = True
            rl.append_live(run_id, "run.command",
                           {"kind": "abort", "cmd_id": cmd_id, "payload": payload},
                           root=root)
        elif kind == "answer":
            decision["answers"].append(payload)
            rl.append_live(run_id, "run.command",
                           {"kind": "answer", "cmd_id": cmd_id, "payload": payload},
                           root=root)
            rl.set_state(run_id, root=root, answer=payload)
            if rl.read_state(run_id, root=root).get("status") == "blocked":
                rl.resume(run_id, root=root)
                decision["resumed"] = True
        elif kind == "steer":
            decision["steers"].append(payload)
            rl.append_live(run_id, "run.command",
                           {"kind": "steer", "cmd_id": cmd_id, "payload": payload},
                           root=root)
        else:
            # An unrecognized kind is recorded and ack'd so it cannot wedge the
            # inbox, but it is neither an answer, a steer, nor an abort.
            rl.append_live(run_id, "run.command",
                           {"kind": kind, "cmd_id": cmd_id, "ignored": True},
                           root=root)
        rl.ack_command(run_id, cmd_id, root=root)
        decision["acted"].append(cmd_id)
    return decision


def run_checkpoint_loop(run_id, steps, root=None, runlog=None):
    """Reference cooperative interactive run loop (WARP-0505 / F4).

    Drives the build's units of work (steps: an iterable of zero-arg callables,
    each one unit of build work between safe checkpoints) and drains the run
    inbox at each SAFE CHECKPOINT: before the first step, between every pair of
    steps, and once after the last. At each checkpoint it calls
    handle_run_commands and the loop - which OWNS the build - acts on the
    decision cooperatively:

      abort   the loop finishes the run aborted (runlog.finish) at the
              checkpoint and STOPS; no further step runs and nothing is signalled
              or preempted, so an abort is honored at a checkpoint, never
              mid-step.
      blocked while the run is blocked waiting on a human, no step runs; an
              answer arriving in the inbox resumes it at the checkpoint and the
              loop proceeds. If a checkpoint leaves the run still blocked (no
              answer yet), the loop stops with status 'blocked' - it waits
              cooperatively rather than busy-spinning.
      steer   collected across checkpoints and returned so the caller can
              surface it to the agent.

    Returns {status, ran, steers, aborted}: status is aborted, blocked, or
    completed; ran is the names of the steps that actually ran."""
    rl = runlog or _load_module("veldo_runlog_loop", ".veldo/runlog.py")
    steers, ran = [], []

    def checkpoint():
        d = handle_run_commands(run_id, root=root, runlog=rl)
        steers.extend(d["steers"])
        if d["abort"]:
            rl.finish(run_id, status="aborted", root=root)
            return "abort"
        if rl.read_state(run_id, root=root).get("status") == "blocked":
            # still blocked after draining (no answer resumed it): wait
            # cooperatively - do not run work while blocked.
            return "blocked"
        return "go"

    for step in steps:
        gate = checkpoint()
        if gate == "abort":
            return {"status": "aborted", "ran": ran, "steers": steers, "aborted": True}
        if gate == "blocked":
            return {"status": "blocked", "ran": ran, "steers": steers, "aborted": False}
        step()
        ran.append(getattr(step, "__name__", "step"))
    # final checkpoint after the last unit of work
    gate = checkpoint()
    if gate == "abort":
        return {"status": "aborted", "ran": ran, "steers": steers, "aborted": True}
    if gate == "blocked":
        return {"status": "blocked", "ran": ran, "steers": steers, "aborted": False}
    return {"status": "completed", "ran": ran, "steers": steers, "aborted": False}


def _cli():
    import argparse
    ap = argparse.ArgumentParser(
        description="Drive a ready spec through the VELDO loop (LiveLoop reference).")
    ap.add_argument("spec_id", help="the spec id to drive, for example WARP-0401")
    ap.add_argument("--max-review-cycles", type=int, default=2)
    args = ap.parse_args()
    ex = Executor(LiveLoop())
    result = ex.run(args.spec_id, max_review_cycles=args.max_review_cycles)
    print(json.dumps(result, indent=2))
    return 0 if result["state"] == "ready" else 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
