#!/usr/bin/env python3
"""VELDO execution organ (veldo.executor/v1): the separate, privileged, laddered executor that
runs ONLY whitelisted actions with validated parameters bound to a proposal digest, on its OWN
credential and code path, behind the standing safeguards. This is the W6 organ of PLAN-0012 and
the enforcement core on the execution side made operational: the pillar of Invention #3 that an
agent with production access cannot destroy a company by simply doing the wrong thing there,
because its safety is not a policy it follows but an architecture it cannot escape.

NOTE ON THE NAME: this is NOT .veldo/executor.py. That module (WARP-0401, capability
executor_driver) is the VELDO BUILD-LOOP executor that drives a ready spec through
resolve/build/gate/proof/review/merge. This is a DIFFERENT organ - the production-support ACTION
executor that runs a remediation proposal's whitelisted action against a system. The two share no
code, so this organ lives in its own module and the build executor is untouched.

THE DESIGN CENTER this module ENCODES, fail closed and degrade DOWN never up (the refusals are the
product, C1/C3):

  SEPARATION IS STRUCTURAL (C4). The executor runs on its OWN credential (ExecutorCredential), a
  distinct type from the responder's read-only credential and ReadHandle: it has no query/read
  method, it holds a secret REFERENCE resolved at the D4 seam (never a raw literal, C5/D4), and it
  shares no credential and no code path with the responder. It accepts ONLY a whitelist action
  reference plus validated parameters BOUND TO A PROPOSAL DIGEST, never command text: the action is
  resolved through W5's store (.veldo/action.py resolve_action / require_action / validate_parameters
  - reused, no second resolver, no second parser), and it refuses if the action is not whitelisted,
  the parameters are invalid, or the proposal digest does not match what a human confirmed.

  THE AUTONOMY LADDER (O3, D2). Constructed per system by a human, read by the executor, never
  raised by it (NG4). L0 and L1 are the read-only floor and NEVER execute (refuse by name). L2
  executes only provably-REVERSIBLE, non-data-mutating whitelisted actions after an explicit human
  confirmation BOUND TO THE PROPOSAL DIGEST. L3 is DISABLED by default and, per D2, may never be
  enabled (never enabling it is a legitimate permanent state); even if a deployment ever set it, L3
  auto-executes the LOWEST risk class alone, and because the whitelist floor is high (W5/C2) no
  whitelisted action is ever the lowest class, so L3 can auto-execute nothing here.

  ANYTHING IRREVERSIBLE OR DATA-MUTATING TAKES TWO KEYS (THE TWO-KEY RULE, WARP-1207 / W7). L2's
  single human confirmation authorizes ONLY the strictly reversible, non-data-mutating case. An action
  or a remedy that is irreversible, costly, or data-mutating, or a remedy whose required_authorization
  is two_key, routes to the TWO-KEY GATE (.veldo/two_key.py, reused - no second gate): execution then
  requires BOTH a recorded human authorization AND an independent fresh-context confirmation, each
  bound to the proposal digest, and EITHER key alone refuses (fail closed, C3). Because this path lets
  an irreversible or data-mutating action actually run (behind the two keys), W7 reaches the CRITICAL
  tier per C2, where W6 was HIGH precisely because it built no such path.

  THE STANDING SAFEGUARDS. A KILL SWITCH any human trips instantly with no ceremony halts everything
  first, and reset requires a recorded highest-tier approval (D5). An action BUDGET refuses once
  exhausted. A TIMEOUT refuses an over-budget run. CANARY-FIRST: when the action declares canary
  support, the canary demonstrably runs BEFORE the main action, and a failed canary refuses without
  running the main action.

  NO SELF-ESCALATION (NG4). The executor exposes no method to raise its own level or to edit the
  ladder, the whitelist, the kill switch, or the budget - those are human-owned controls it only
  reads (and consumes the budget, which is not editing its limit).

The intelligent act against a real system is a DELEGATED seam (TargetSystem): the reference
LiveTargetSystem FAILS LOUD (raises rather than touch a live system), exactly as
executor.LiveLoop.build/review, evidence.LiveEvidencePlane, and the responder's LiveResponder
refuse to fabricate, and the FakeActionSystem is the offline proof (NG1). Everything here is proven
OFFLINE against fake systems; wiring a real target is a separate per-system human-approved
enablement act. Dependency free by construction: pathlib, json, and hashlib at module top (json and
hashlib for the proposal's own digest), importlib LAZILY in the credential seam and the CLI; it
starts no process, thread, or timer (NG3, no-detach) and opens no live connection.

Honest deferrals (the plan's ordered delivery, not a dodge): the two-key rule an irreversible or
data-mutating proposal binds to is now built and integrated (WARP-1207 / W7, the two-key gate this
organ routes to); the compressed loop and reconciliation that close an incident are WARP-1208 (W8);
the support metrics are WARP-1210 (W10); landing an executor check into validate.py run_all and
lay-down via init is WARP-1211 (W11). Nothing here pretends those later organs are built.
"""
from pathlib import Path
import json
import hashlib

SCHEMA = "veldo.executor/v1"

# The autonomy ladder (O3, D2), ordered low -> high. L0/L1 are the read-only floor and NEVER
# execute; L2 is the only executing rung in this build; L3 is disabled by default (D2).
AUTONOMY_LEVELS = ("L0", "L1", "L2", "L3")
_LEVEL_ORDER = {lvl: i for i, lvl in enumerate(AUTONOMY_LEVELS)}
EXECUTION_FLOOR = ("L0", "L1")     # these levels never execute (the read-only floor)
EXECUTION_LEVELS = ("L2", "L3")    # the execution rungs a proposal may request

# The one tier ladder the method uses (mirrors action.RISK_CLASSES / validate.RISKS). L3, if it
# were ever enabled, would auto-execute only the LOWEST class; the whitelist floor is high, so this
# is unreachable here (a designed dead end, not an omission).
RISK_CLASSES = ("low", "standard", "high", "critical")
L3_LOWEST_CLASS = "low"

# The reversibility classes (mirror action.REVERSIBILITY_CLASSES). L2 executes only the strictly
# reversible, non-data-mutating case; costly and irreversible route to the two-key rule (W7).
PROVABLY_REVERSIBLE = "reversible"

# The kill-switch reset needs a recorded approval at the highest tier (D5).
HIGHEST_TIER = "critical"

# The human confirmation the L2 key requires. A confirmation decides "confirmed" and binds to the
# exact proposal digest it confirms; anything else refuses.
CONFIRM_DECISION = "confirmed"

# Actor identities that may NEVER stand in for a human confirmation (NG4, no self-authorization).
# A confirmation whose confirmed_by is a machine (or the executor's own actor) is refused: the
# executor never authorizes its own execution, the way the responder never approves its own proposal.
MACHINE_ACTORS = frozenset({
    "veldo-executor", "veldo-responder", "executor", "responder", "machine",
    "agent", "bot", "ava", "automation",
})

# The redaction marker mirrors evidence.REDACTION_MARKER (the single redaction string across the
# method); a selftest asserts the two are equal so they cannot drift. A resolved secret never
# surfaces its raw value - it redacts itself here (C5/D4).
REDACTION_MARKER = "***redacted***"

# The refusal reason codes: a closed, NAMED taxonomy (C1/C3). Every guard that does not pass returns
# one, so the failure mode is legible from the result rather than inferred.
REFUSE_KILL_SWITCH = "kill_switch_tripped"
REFUSE_INVALID_PROPOSAL = "invalid_proposal"
REFUSE_BELOW_FLOOR = "below_execution_floor"
REFUSE_L3_DISABLED = "l3_disabled"
REFUSE_L3_LOWEST_CLASS_ONLY = "l3_lowest_class_only"
REFUSE_AUTONOMY_INSUFFICIENT = "autonomy_level_insufficient"
REFUSE_ACTION_NOT_WHITELISTED = "action_not_whitelisted"
REFUSE_INVALID_PARAMETERS = "invalid_parameters"
REFUSE_REQUIRES_TWO_KEY = "requires_two_key"
REFUSE_MISSING_CONFIRMATION = "missing_human_confirmation"
REFUSE_FOREIGN_CONFIRMATION = "foreign_confirmation"
REFUSE_SELF_AUTHORIZATION = "self_authorization_refused"
REFUSE_BUDGET_EXHAUSTED = "action_budget_exhausted"
REFUSE_TIMEOUT = "timeout_exceeded"
# WARP-0621 (W8): a risky action must additionally carry an EXECUTION BINDING whose six bound
# facts still hold at the moment of execution. The single name covers every binding refusal; the
# specific one (expired, replayed, parameters changed, ...) is carried in the detail and in the
# `binding_reason` field of the result, so nothing here has to enumerate that module's vocabulary.
REFUSE_BINDING = "execution_binding_refused"
REFUSE_CANARY_FAILED = "canary_failed"

# The mutator method names a SELF-ESCALATING executor would carry. The executor must have NONE of
# them: NG4 says no machine raises its own level or edits the ladder, whitelist, kill switch, or
# budget. The no-escalation negative test asserts hasattr is false for every one, and a mutation
# adding any of them turns the test red (non-vacuous), mirroring the responder's
# FORBIDDEN_EXECUTION_METHODS enumeration.
FORBIDDEN_ESCALATION_METHODS = (
    "raise_level", "set_level", "escalate", "promote", "enable_l3", "set_l3_enabled",
    "edit_whitelist", "set_whitelist", "add_action", "grant", "reset_kill_switch",
    "trip_kill_switch", "arm", "set_budget", "set_limit", "raise_budget",
)


class ExecutorError(RuntimeError):
    """The executor refused a malformed CALL, a delegated live seam is not wired, or a control is
    misconstructed. Raised by name so a failure never silently no-ops (parallels ResponderError,
    EvidencePlaneError, and ActionContractError). A GUARDED refusal is NOT an exception: it is a
    named result (executed False, refused <reason>), which is the product (C1)."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_bool(v):
    """The value as a real boolean, or None when it is neither. The one front-matter parser leaves
    an unquoted true/false as the string "true"/"false" (it coerces only integers), so a boolean
    contract field arrives as that string; accept the string forms and a real bool and refuse
    anything else, exactly as incident.py and action.py do, so a truthy-looking value is never
    silently accepted."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


def _as_number(v):
    """The value as an int or float, or None. A real bool is NOT a number (treating True as 1 would
    let a boolean satisfy a numeric comparison silently)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def proposal_digest(remedy):
    """THE CANONICAL DIGEST of a veldo.remedy/v1 PROPOSAL: sha256 over its full substance. The human
    confirmation (and, later, the two-key rule W7) binds to THIS digest, and the executor recomputes
    it and refuses if a confirmation names a different digest or the proposal changed after it was
    confirmed (a stale proposal fails closed, C3). One canonical digest for one artifact, the same
    idiom as validate.proof_digest and action.action_digest - NOT a second parser: parsing stays
    validate.parse_yamlish, injected by the caller; this only hashes an already-parsed record. W7
    imports this from here rather than redefine it, so the binding has ONE truth."""
    payload = remedy if isinstance(remedy, dict) else {}
    blob = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


# --- the credential seam: the executor's OWN credential (C4/C5/D4) ------------------------------

class ExecutorCredential:
    """The executor's OWN credential, DISTINCT from the responder's read-only credential and
    ReadHandle (C4: separate credentials and code path). It authenticates with a secret resolved at
    the D4 seam (held privately, never surfaced; it redacts itself in every string form, C5/D4) and
    it grants ONLY the ability to invoke a whitelisted action against its declared target system. It
    is NOT a read handle: there is deliberately no query, read, or open_read method on this type, so
    the executor cannot investigate, and it holds nothing the responder holds. The write-toward-a-
    fake-system authority is exercised only through a whitelist reference with validated parameters
    bound to a proposal digest, never command text."""

    GRANT = "execute_whitelisted"
    __slots__ = ("_actor", "_system", "_secret")

    def __init__(self, actor, system, resolved_secret):
        if not _is_str(actor):
            raise ExecutorError("an executor credential names its actor (a non-empty identity)")
        if not _is_str(system):
            raise ExecutorError("an executor credential names the target system it acts against")
        self._actor = actor
        self._system = system
        self._secret = resolved_secret  # never surfaced (C5/D4)

    @property
    def actor(self):
        return self._actor

    @property
    def system(self):
        return self._system

    @property
    def grant(self):
        return self.GRANT

    def context_view(self):
        """What may be seen about this credential: the actor, the system, and the granted role,
        NEVER the secret (C5/D4)."""
        return {"actor": self._actor, "system": self._system, "grant": self.GRANT,
                "secret": REDACTION_MARKER}

    def __repr__(self):
        return "<ExecutorCredential actor=%r system=%r grant=%s secret=%s>" % (
            self._actor, self._system, self.GRANT, REDACTION_MARKER)
    __str__ = __repr__
    # No query, read, open_read, insert, update, or delete: the executor is not an investigator and
    # shares no code path with the responder's read-only handle (C4).


def _load_sibling(name, filename):
    """Load a sibling engine module BY PATH, the same way the sibling organs load validate.py, so
    there is one front-matter parser and no import cycle. importlib is imported LAZILY here (never at
    module top), so the module top imports pathlib/json/hashlib only and starts no process (NG3)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(name, here / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_executor_credential(actor, system, secret_ref, env=None, secret_resolver=None):
    """Resolve the executor's OWN credential at the D4 seam. The secret is a REFERENCE (env: or
    keychain:), resolved via the SHARED evidence-plane seam (reused, not re-implemented: the secret
    seam is a platform capability from W2) and held privately; a raw literal is REFUSED (C5/D4). The
    resulting credential is a distinct type from the responder's, with its own actor and target
    system, so the two organs share no credential (C4). A caller may inject a secret_resolver (for
    an offline test or an alternate seam); the default reuses evidence.resolve_secret_ref."""
    resolve = secret_resolver
    if resolve is None:
        resolve = _load_sibling("veldo_evidence_executor", "evidence.py").resolve_secret_ref
    secret = resolve(secret_ref, env=env)
    return ExecutorCredential(actor, system, secret)


# --- the standing safeguards (D5, O3): kill switch, action budget, autonomy ladder -------------

def _is_highest_tier_approval(approval):
    """True iff the approval is a recorded highest-tier (critical) human approval fit to reset the
    kill switch (D5). It must decide approved, carry tier critical (the highest), and name a human
    approver (not a machine actor). Anything less fails closed."""
    if not isinstance(approval, dict):
        return False
    if approval.get("decision") != "approved":
        return False
    if approval.get("tier") != HIGHEST_TIER:
        return False
    who = approval.get("approver")
    return _is_str(who) and who.strip().lower() not in MACHINE_ACTORS


class KillSwitch:
    """The kill switch (D5): ANY human trips it INSTANTLY with no ceremony, and once tripped the
    executor refuses everything until it is reset. Resetting requires a RECORDED highest-tier
    approval; a reset without one refuses and the switch stays tripped (fail closed). The executor
    only READS is_tripped - it never trips or resets the switch (NG4, a human-owned control)."""

    def __init__(self, tripped=False):
        self._tripped = bool(tripped)
        self._log = []

    def trip(self, by):
        """Any human trips it instantly, no ceremony (D5). Recorded, not gated."""
        self._tripped = True
        self._log.append({"event": "tripped", "by": by})
        return True

    def is_tripped(self):
        return self._tripped

    def reset(self, approval):
        """Reset requires a recorded highest-tier approval (D5). Returns True on a real reset, False
        (and stays tripped) otherwise. This is a human control, not the executor's."""
        if not _is_highest_tier_approval(approval):
            self._log.append({"event": "reset_refused",
                              "reason": "reset requires a recorded highest-tier (critical) human approval (D5)"})
            return False
        self._tripped = False
        self._log.append({"event": "reset", "by": approval.get("approver")})
        return True

    @property
    def log(self):
        return list(self._log)


class ActionBudget:
    """A standing action budget (O3): the executor may run at most `limit` actions; once the budget
    is exhausted every further execution REFUSES (fail closed). The executor CONSUMES the budget when
    it engages the target, but it cannot change the LIMIT (NG4, a human-owned control - consuming a
    slot is not editing the budget)."""

    def __init__(self, limit):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ExecutorError("an action budget limit must be a non-negative integer")
        self._limit = limit
        self._used = 0

    def available(self):
        return self._used < self._limit

    def remaining(self):
        return max(0, self._limit - self._used)

    def consume(self):
        """Record one used action slot. Returns False (and consumes nothing) once exhausted."""
        if self._used >= self._limit:
            return False
        self._used += 1
        return True

    @property
    def limit(self):
        return self._limit

    @property
    def used(self):
        return self._used


class AutonomyLadder:
    """The per-system autonomy ladder (O3, D2). Constructed once by a human; the executor READS it
    and NEVER raises its own level (NG4). Every system defaults to the floor L0. L3 is DISABLED by
    default and, per D2, may never be enabled (never enabling it is a legitimate permanent state).
    There is deliberately no set-level or enable method on this type: the ladder is immutable to the
    executor."""

    def __init__(self, levels=None, default="L0", l3_enabled=False):
        if default not in AUTONOMY_LEVELS:
            raise ExecutorError("the ladder default level must be one of %s (got %r)" % (list(AUTONOMY_LEVELS), default))
        self._levels = {}
        for sysid, lvl in (levels or {}).items():
            if lvl not in AUTONOMY_LEVELS:
                raise ExecutorError("the ladder level for %r must be one of %s (got %r)" % (sysid, list(AUTONOMY_LEVELS), lvl))
            self._levels[sysid] = lvl
        self._default = default
        self._l3_enabled = bool(l3_enabled)

    def level_for(self, system):
        """The configured autonomy level for a system, defaulting to the floor L0 (fail closed: an
        unconfigured system does not execute)."""
        return self._levels.get(system, self._default)

    @property
    def l3_enabled(self):
        return self._l3_enabled

    @property
    def default(self):
        return self._default


# --- the target-system seam: FAKE offline only (NG1) -------------------------------------------

class TargetSystem:
    """The execution seam. A concrete target runs a resolved WHITELIST action reference with
    VALIDATED parameters against its system; it NEVER receives command text (C4). It is split into a
    canary run and a main run so the executor can enforce canary-first. Each method returns a result
    mapping (at least ok and elapsed). A live target is a separate per-system human-approved adapter
    (NG1)."""

    def run_canary(self, action_id, params, system):
        raise NotImplementedError

    def run_action(self, action_id, params, system):
        raise NotImplementedError


class LiveTargetSystem(TargetSystem):
    """The fail-loud live reference (NG1), mirroring evidence.LiveEvidencePlane and
    executor.LiveLoop: every method RAISES, so no live system is touched in the gate. A runtime
    injects a real per-system adapter at enablement, which is a separate human-approved act. A loop
    that silently no-ops an execution is more dangerous than one that refuses to run."""

    def run_canary(self, action_id, params, system):
        raise ExecutorError(
            "live target wiring is a separate per-system human-approved enablement act (NG1); inject "
            "a real adapter at enablement. The gate runs against FAKE systems only.")

    def run_action(self, action_id, params, system):
        raise ExecutorError(
            "live target wiring is a separate per-system human-approved enablement act (NG1); inject "
            "a real adapter at enablement. The gate runs against FAKE systems only.")


class FakeActionSystem(TargetSystem):
    """A FAKE system (NG1): it records an ORDERED operation log and reports a seeded canary health
    and elapsed, mutating no real data, opening no connection, and starting no process, thread, or
    timer (NG3). The ordered log lets a test prove canary-FIRST ordering; the seeded health and
    elapsed let a test prove the canary-failed and timeout refusals non-vacuously."""

    def __init__(self, canary_healthy=True, canary_elapsed=0, action_elapsed=0):
        self.ops = []
        self._canary_healthy = bool(canary_healthy)
        self._canary_elapsed = canary_elapsed
        self._action_elapsed = action_elapsed

    def run_canary(self, action_id, params, system):
        self.ops.append({"op": "canary", "action": action_id, "params": dict(params or {}), "system": system})
        return {"ok": True, "healthy": self._canary_healthy, "elapsed": self._canary_elapsed}

    def run_action(self, action_id, params, system):
        self.ops.append({"op": "action", "action": action_id, "params": dict(params or {}), "system": system})
        return {"ok": True, "elapsed": self._action_elapsed}


# --- the results (named, secret-free) ----------------------------------------------------------

def _refused(reason, detail, **extra):
    """A guarded refusal is a NAMED result, never an exception (the refusals are the product, C1).
    It carries no secret and no command text."""
    out = {"executed": False, "refused": reason, "detail": detail}
    out.update(extra)
    return out


def _executed(action_id, system, canary_ran, sequence, **extra):
    out = {"executed": True, "refused": None, "action": action_id, "system": system,
           "canary_ran": canary_ran, "sequence": sequence}
    out.update(extra)
    return out


class ActionExecutor:
    """The execution organ (W6): separate, privileged, laddered. It runs ONLY whitelisted actions
    with validated parameters bound to a proposal digest, on its OWN credential and code path
    (sharing none with the responder, C4), governed by the per-system autonomy ladder (O3/D2), behind
    the standing safeguards (kill switch, budget, timeout, canary-first). It FAILS CLOSED and degrades
    DOWN never up (C3): every guard that does not pass REFUSES with the reason NAMED, and it NEVER
    raises its own autonomy level or edits the ladder, whitelist, kill switch, or budget (NG4).
    Anything irreversible or data-mutating ROUTES to the two-key rule (WARP-1207, W7) and executes ONLY
    behind BOTH keys bound to the proposal digest, so the data-mutating execution path exists only
    through those two keys (either key alone refuses).

    The whitelist resolution and parameter validation are REUSED from W5 (.veldo/action.py) and the
    proposal is re-validated through W1 (.veldo/incident.py): no second resolver, no second parser."""

    def __init__(self, credential, ladder, kill_switch, budget, target,
                 action_mod, incident_mod, timeout_seconds=None, two_key_mod=None):
        if not isinstance(credential, ExecutorCredential):
            raise ExecutorError(
                "the executor runs on its OWN credential (ExecutorCredential); it shares none with "
                "the responder (C4). A read handle is not an execution credential.")
        if hasattr(credential, "query") or hasattr(credential, "open_read"):
            raise ExecutorError("the executor credential must not be a read/investigation handle (C4, separate code path)")
        if not isinstance(ladder, AutonomyLadder):
            raise ExecutorError("the executor needs an AutonomyLadder (the per-system autonomy ladder, O3/D2)")
        if not isinstance(kill_switch, KillSwitch):
            raise ExecutorError("the executor needs a KillSwitch standing safeguard (D5)")
        if not isinstance(budget, ActionBudget):
            raise ExecutorError("the executor needs an ActionBudget standing safeguard (O3)")
        if target is None or not (hasattr(target, "run_action") and hasattr(target, "run_canary")):
            raise ExecutorError(
                "the executor needs a TargetSystem seam (FakeActionSystem offline, NG1); a live "
                "target is a separate per-system human-approved adapter")
        if action_mod is None or incident_mod is None:
            raise ExecutorError(
                "the executor reuses the W5 whitelist store (.veldo/action.py) and the W1 remedy "
                "contract (.veldo/incident.py): no second resolver, no second parser")
        self._cred = credential
        self._ladder = ladder
        self._kill = kill_switch
        self._budget = budget
        self._target = target
        self._act = action_mod
        self._inc = incident_mod
        self._timeout = timeout_seconds
        # The two-key rule (W7) is a GENERIC engine module (.veldo/two_key.py) the executor routes to
        # for an irreversible or data-mutating action. It is loaded LAZILY (no import cycle: two_key.py
        # imports proposal_digest from this organ only in its standalone demo) and may be injected for
        # an offline test; it is NOT a credential or a control the executor mutates.
        self._tk = two_key_mod
    # Deliberately NO raise_level, set_level, enable_l3, edit_whitelist, reset_kill_switch, or
    # set_budget method: the executor never escalates itself and never edits a human-owned control
    # (NG4). See FORBIDDEN_ESCALATION_METHODS and its non-vacuous negative test.

    @property
    def credential(self):
        return self._cred

    def _two_key_module(self):
        """The two-key gate module (W7), loaded LAZILY by path the same way the credential seam loads
        evidence.py, so the module top stays dependency free and no import cycle forms."""
        if self._tk is None:
            self._tk = _load_sibling("veldo_two_key_executor", "two_key.py")
        return self._tk

    def _check_binding(self, binding, context, action_ref, params, system, digest, now, store):
        """The W8 execution-binding guard. Returns None to proceed, or a NAMED refusal.

        FAILS CLOSED ON AN ABSENT BINDING, and that is the load-bearing choice: a risky action with
        no binding is refused, not waved through. Making it optional would mean the whole guard
        could be skipped by omitting an argument, which is the shape of every defeated guard in
        this repository's history.

        THE NONCE IS CONSUMED BEFORE THE ACTION RUNS, never after. A process that dies mid-action
        then leaves a spent nonce and the action needs re-authorising, which is the correct way to
        fail: a risky action that runs twice is worse than one that runs zero times and says so.
        Consumption is skipped only when the caller supplies no store, and in that case the replay
        check still runs against whatever `consumed` set the context carries."""
        eb = _load_sibling("veldo_execution_binding", "execution_binding.py")
        if binding is None:
            return _refused(REFUSE_BINDING,
                            "this action is irreversible or data-mutating and carries no execution "
                            "binding: two keys prove two humans authorised something, not that they "
                            "authorised THIS execution here, now, once (W8)",
                            binding_reason=eb.BINDING_ABSENT)
        ctx = context if isinstance(context, dict) else {}
        reason, detail = eb.check(
            binding,
            target=action_ref,
            system=system,
            environment=ctx.get("environment"),
            parameters=params,
            state_digest=ctx.get("state_digest"),
            proposal_digest=digest,
            now=now,
            consumed=(eb.spent(store) if store else ctx.get("consumed")),
        )
        if reason != eb.BINDING_OK:
            return _refused(REFUSE_BINDING, detail, binding_reason=reason)
        if store and not eb.consume(store, binding["nonce"]):
            # Lost the race: another executor spent this nonce between the check and here. The
            # atomic create is what decides, never the check above, which is why the check being
            # clean is not enough to proceed.
            return _refused(REFUSE_BINDING,
                            "nonce %s was consumed concurrently: exactly one execution wins an "
                            "authorisation" % binding["nonce"],
                            binding_reason=eb.BINDING_REPLAYED)
        return None

    def execute(self, remedy, whitelist, confirmation=None,
                human_authorization=None, independent_confirmation=None, now=None,
                execution_binding=None, binding_context=None, nonce_store=None):
        """Attempt to execute a remediation PROPOSAL through the whitelist. Returns a NAMED result:
        {executed: True, ...} on a run, or {executed: False, refused: <reason>, detail: ...} on any
        guard (fail closed to a named result; it raises only on a genuinely malformed call). The
        guard order is deliberate - the kill switch and the proposal validity come first, then the
        whitelist resolution, then the ladder, then the two-key determination. A strictly reversible,
        non-data-mutating action takes the L2 single human `confirmation` bound to the digest; an
        irreversible or data-mutating action (or a remedy requiring two_key) takes the TWO-KEY RULE
        (W7) - both `human_authorization` and `independent_confirmation`, each bound to the digest -
        and EITHER key alone refuses. Then the budget, the timeout, and the canary-first run."""
        if not isinstance(remedy, dict):
            return _refused(REFUSE_INVALID_PROPOSAL,
                            "the proposal must be a remedy record (mapping); got %r" % type(remedy).__name__)
        if not isinstance(whitelist, dict):
            return _refused(REFUSE_ACTION_NOT_WHITELISTED,
                            "no effective whitelist supplied: with no admitted action nothing exists to the machine path (C4/NG2)")

        # 1. KILL SWITCH (D5): a tripped switch halts EVERYTHING, first and unconditionally.
        if self._kill.is_tripped():
            return _refused(REFUSE_KILL_SWITCH,
                            "the kill switch is TRIPPED: the executor refuses everything until a "
                            "recorded highest-tier approval resets it (D5); any human trips it instantly")

        # 2. THE PROPOSAL IS RE-VALIDATED (never trusted): a malformed or non-proposed (superseded /
        # withdrawn) remedy is an invalid or stale proposal and refuses (C3).
        problems = []

        def _collect(where, msg):
            problems.append(msg)
            return 1

        errs = self._inc.validate_remedy(remedy, ".", "executor.proposal", _collect)
        if errs:
            return _refused(REFUSE_INVALID_PROPOSAL,
                            "the proposal is invalid at contract time (%d problem(s)): %s" % (errs, "; ".join(problems)))
        if remedy.get("status") != "proposed":
            return _refused(REFUSE_INVALID_PROPOSAL,
                            "the proposal status is %r, not 'proposed': a superseded or withdrawn "
                            "proposal is stale and does not execute (C3)" % remedy.get("status"))

        digest = proposal_digest(remedy)

        # 3. RESOLVE THE ACTION through W5's store and VALIDATE PARAMETERS (reused, no second
        # resolver). Anything not in the whitelist does not exist to the machine path (C4/NG2), and a
        # bad parameter refuses by name.
        pa = remedy.get("proposed_action")
        if not isinstance(pa, dict):
            return _refused(REFUSE_INVALID_PROPOSAL, "the proposal names no proposed_action mapping")
        action_ref = pa.get("action")
        params = pa.get("parameters") or {}
        action, aerr = self._act.require_action(action_ref, whitelist, _collect, "executor")
        if action is None:
            return _refused(REFUSE_ACTION_NOT_WHITELISTED,
                            "action %r is not in the whitelist: it does not exist to the machine path "
                            "(C4/NG2, never interpreted as command text). %s" % (action_ref, "; ".join(problems[-aerr:] or problems)))
        perr = self._act.validate_parameters(action, params, _collect, "executor")
        if perr:
            return _refused(REFUSE_INVALID_PARAMETERS,
                            "the proposed parameters are invalid: %s" % "; ".join(problems[-perr:]))

        # 4. THE LADDER (O3, D2): the per-system level. The floor never executes; L3 is disabled.
        system = action.get("system")
        level = self._ladder.level_for(system)
        laddered = self._check_ladder(level, action, remedy)
        if laddered is not None:
            return laddered

        # 5. THE TWO-KEY DETERMINATION (W7). Is this action irreversible or data-mutating (or does the
        # remedy require two_key)? A malformed reversibility fails closed (invalid_proposal), exactly
        # as W6. This replaces W6's flat two-key fence: irreversible/data-mutating no longer dead-ends,
        # it routes to the two-key gate below.
        needs_two_key, malformed = self._two_key_status(action, remedy)
        if malformed is not None:
            return malformed

        if needs_two_key:
            # THE TWO-KEY RULE (W7): an irreversible or data-mutating action executes ONLY with BOTH a
            # recorded human authorization AND an independent fresh-context confirmation, each bound to
            # the proposal digest and self-separated (NG4). EITHER key alone refuses (fail closed, C3).
            # This is the CRITICAL path (C2): reaching a run here means a data-mutating action ran.
            tk = self._check_two_key(remedy, digest, human_authorization, independent_confirmation, now)
            if tk is not None:
                return tk

            # 5b. THE EXECUTION BINDING (W8, WARP-0621), AFTER the keys and never before them.
            # ORDER IS A PROMISE THIS ITEM MADE: the W6 and W7 guards keep their names and their
            # sequence, so an action with no keys at all still refuses `requires_two_key` rather
            # than complaining about a binding. The binding REFINES an authorisation that must
            # already exist - it answers "did they authorise THIS execution, here, now, once" -
            # and that question is meaningless before there is an authorisation to refine.
            # Putting it first was the first draft and it broke eight existing refusals by
            # answering a later question earlier.
            bind_out = self._check_binding(execution_binding, binding_context, action_ref,
                                           params, system, digest, now, nonce_store)
            if bind_out is not None:
                return bind_out
            provenance = {"two_key": True,
                          "authorized_by": human_authorization.get("approver"),
                          "confirmed_by": (independent_confirmation.get("confirmer")
                                           or independent_confirmation.get("reviewer"))}
        else:
            # 6. THE L2 SINGLE HUMAN CONFIRMATION (W6), bound to the proposal digest: the only path for
            # a strictly reversible, non-data-mutating action, UNCHANGED by W7.
            confirmed = self._check_confirmation(remedy, digest, confirmation)
            if confirmed is not None:
                return confirmed
            provenance = {"two_key": False, "confirmed_by": confirmation.get("confirmed_by")}

        # 7. THE BUDGET (O3): exhausted refuses.
        if not self._budget.available():
            return _refused(REFUSE_BUDGET_EXHAUSTED,
                            "the action budget is exhausted (%d of %d used): the executor refuses "
                            "further actions until the budget is renewed" % (self._budget.used, self._budget.limit))

        # 8. RUN: canary-first (if declared), then the main action, under the timeout.
        return self._run(action, action_ref, params, system, level, digest, provenance)

    def _check_ladder(self, level, action, remedy):
        """The ladder guards (O3, D2). Returns a named refusal or None. L0/L1 never execute; L3 is
        disabled by default and, even if ever enabled, auto-executes the lowest class alone; the
        proposal's requested level may not exceed the system's."""
        if level in EXECUTION_FLOOR:
            return _refused(REFUSE_BELOW_FLOOR,
                            "the system is at the read-only floor %s, which NEVER executes (O3/D2): "
                            "L0 investigates and L1 proposes; execution is L2. Degrade down, never up "
                            "(C3)." % level)
        if level == "L3":
            if not self._ladder.l3_enabled:
                return _refused(REFUSE_L3_DISABLED,
                                "L3 (autonomous execution) is DISABLED by default and, per D2, may "
                                "never be enabled - never enabling it is a legitimate permanent state")
            if action.get("risk_class") != L3_LOWEST_CLASS:
                return _refused(REFUSE_L3_LOWEST_CLASS_ONLY,
                                "L3 auto-executes the LOWEST risk class (%r) alone; this action is %r. "
                                "The whitelist floor is high (W5/C2), so no whitelisted action is ever "
                                "the lowest class - L3 auto-executes nothing here." % (L3_LOWEST_CLASS, action.get("risk_class")))
        needed = remedy.get("autonomy_level")
        if needed not in EXECUTION_LEVELS:
            return _refused(REFUSE_AUTONOMY_INSUFFICIENT,
                            "the proposal requests autonomy %r, which is not an execution rung: only "
                            "L2 (and L3 if ever enabled) execute; a proposal for L0/L1 is not an "
                            "execution request" % needed)
        if _LEVEL_ORDER.get(level, 0) < _LEVEL_ORDER.get(needed, 99):
            return _refused(REFUSE_AUTONOMY_INSUFFICIENT,
                            "the system is at %s but this action needs %s: the executor never raises "
                            "its own level (NG4) and degrades down, never up (C3)" % (level, needed))
        return None

    def _two_key_status(self, action, remedy):
        """Whether execution needs the TWO-KEY RULE (W7): the action's vetted reversibility (W5) OR the
        remedy's declared one (W1) is irreversible, costly, or data-mutating, OR the remedy requires
        two_key. Returns (needs_two_key, malformed_refusal_or_None). A malformed reversibility fails
        closed (invalid_proposal), exactly as W6, so a mismatch or an absent analysis never slips
        through. This is the SAME set of conditions W6's fence used, but it now decides which PATH a
        proposal takes (the two-key gate vs the L2 single confirmation) rather than dead-ending."""
        for label, rec in (("action", action), ("remedy", remedy)):
            rev = rec.get("reversibility")
            if not isinstance(rev, dict):
                return False, _refused(REFUSE_INVALID_PROPOSAL,
                                       "the %s declares no reversibility analysis" % label)
        needs = False
        for rec in (action, remedy):
            rev = rec["reversibility"]
            if _as_bool(rev.get("data_mutating")) is True or rev.get("class") != PROVABLY_REVERSIBLE:
                needs = True
        if remedy.get("required_authorization") == "two_key":
            needs = True
        return needs, None

    def _check_two_key(self, remedy, digest, human_authorization, independent_confirmation, now):
        """THE TWO-KEY RULE (W7): an irreversible or data-mutating action executes ONLY with BOTH a
        recorded human authorization AND an independent fresh-context confirmation, each bound to the
        proposal digest and self-separated (NG4). Returns a NAMED refusal or None. Delegates to the
        generic two-key gate (.veldo/two_key.py, reused - no second gate) passing this executor's OWN
        actor so the gate can refuse a confirmer or authorizer that is the executor itself. Both keys
        absent returns REFUSE_REQUIRES_TWO_KEY, the exact value W6 used, so the pre-two-key behavior is
        preserved; the richer per-key refusals are the gate's named taxonomy, surfaced verbatim."""
        tk = self._two_key_module()
        reason, detail = tk.authorize(remedy, digest, human_authorization, independent_confirmation,
                                      executor_actor=self._cred.actor, now=now)
        if reason is None:
            return None
        return _refused(reason, detail)

    def _check_confirmation(self, remedy, digest, confirmation):
        """The L2 human key: an explicit human confirmation BOUND TO THE PROPOSAL DIGEST. Returns a
        named refusal or None. Missing, non-confirming, machine-authored (self-authorization), or
        digest-mismatched (foreign or stale) confirmations each refuse."""
        if not isinstance(confirmation, dict):
            return _refused(REFUSE_MISSING_CONFIRMATION,
                            "no human confirmation supplied: L2 executes only after an explicit human "
                            "confirmation bound to the proposal (O3)")
        if confirmation.get("decision") != CONFIRM_DECISION:
            return _refused(REFUSE_MISSING_CONFIRMATION,
                            "the confirmation decides %r, not %r: an unconfirmed proposal does not "
                            "execute" % (confirmation.get("decision"), CONFIRM_DECISION))
        who = confirmation.get("confirmed_by")
        if not _is_str(who):
            return _refused(REFUSE_MISSING_CONFIRMATION, "the confirmation names no human (confirmed_by is empty)")
        if who.strip().lower() in MACHINE_ACTORS or who == self._cred.actor:
            return _refused(REFUSE_SELF_AUTHORIZATION,
                            "the confirmation is authored by a machine actor (%r): no self-"
                            "authorization (NG4) - the executor never confirms its own execution, "
                            "the way the responder never approves its own proposal" % who)
        cd = confirmation.get("proposal_digest")
        if cd != digest:
            return _refused(REFUSE_FOREIGN_CONFIRMATION,
                            "the confirmation is bound to proposal digest %r but this proposal is %r: "
                            "a confirmation binds to the EXACT proposal it confirms; a foreign or stale "
                            "confirmation refuses (C3)" % (cd, digest))
        inc = confirmation.get("incident")
        if inc is not None and inc != remedy.get("incident"):
            return _refused(REFUSE_FOREIGN_CONFIRMATION,
                            "the confirmation names incident %r but the proposal remediates %r "
                            "(foreign confirmation)" % (inc, remedy.get("incident")))
        return None

    def _run(self, action, action_ref, params, system, level, digest, provenance):
        """Engage the target under the standing safeguards: consume one budget slot, run the canary
        FIRST when the action declares canary support (a failed canary refuses without running the
        main action), then the main action, refusing on an over-budget timeout. The target receives
        a whitelist action reference and validated parameters, NEVER command text (C4). The executed
        result carries the authorization provenance (two_key true/false and the authorizing/confirming
        identities), so a run is auditable to the exact keys that authorized it."""
        # Consuming a slot when the executor engages the target: an attempt counts against the budget.
        self._budget.consume()
        sequence = []
        canary = action.get("canary") if isinstance(action.get("canary"), dict) else {}
        canary_ran = False
        if _as_bool(canary.get("supported")) is True:
            sequence.append("canary")
            c = self._target.run_canary(action_ref, params, system)
            over = self._over_timeout(c)
            if over is not None:
                return _refused(REFUSE_TIMEOUT,
                                "the canary exceeded the timeout (%s > %s): the main action was NOT "
                                "run" % (over, self._timeout), sequence=sequence)
            if not c.get("healthy"):
                return _refused(REFUSE_CANARY_FAILED,
                                "the canary was NOT healthy: the main action was NOT run (canary-first "
                                "stands guard)", sequence=sequence)
            canary_ran = True
        sequence.append("action")
        a = self._target.run_action(action_ref, params, system)
        over = self._over_timeout(a)
        if over is not None:
            return _refused(REFUSE_TIMEOUT,
                            "the action exceeded the timeout (%s > %s)" % (over, self._timeout),
                            sequence=sequence)
        return _executed(action_ref, system, canary_ran, sequence, level=level,
                         proposal_digest=digest, risk_class=action.get("risk_class"),
                         **provenance)

    def _over_timeout(self, result):
        """The reported elapsed if it exceeds the configured timeout, else None. Offline, the elapsed
        is what the fake operation reports (there is no clock to run and no timer to start, NG3); at
        live enablement a real adapter measures the wall clock. A number comparison, so the guard is
        non-vacuous: neutralizing it lets an over-budget run pass."""
        if self._timeout is None:
            return None
        elapsed = _as_number((result or {}).get("elapsed"))
        if elapsed is not None and elapsed > self._timeout:
            return elapsed
        return None


def _cli(argv):
    """Standalone runner: build a demo executor over the shipped example remedy and the reference
    trio whitelist, against a FAKE system, and print the result of an L2 execution with a confirmation
    bound to the proposal digest. This exercises the organ end to end OFFLINE (NG1); wiring an
    executor check into validate.py run_all and the init lay-down is WARP-1211 (W11). With no
    confirmation it honestly REFUSES (missing the human key). It reuses validate.parse_yamlish (one
    parser) and the W5/W1 sibling modules; it runs nothing against any live system."""
    here = Path(__file__).resolve().parent
    root = here.parent
    V = _load_sibling("veldo_validate_executor", "validate.py")
    ACT = _load_sibling("veldo_action_executor_store", "action.py")
    INC = _load_sibling("veldo_incident_executor", "incident.py")

    # Build the effective whitelist from the shipped reference trio (in a fresh actions view).
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        adir = Path(td) / ".veldo" / "actions"
        adir.mkdir(parents=True)
        for name in ("action-rollback-deploy-example.yaml", "action-restart-service-example.yaml",
                     "action-scale-pool-example.yaml"):
            src = root / ".veldo" / "examples" / name
            if src.is_file():
                (adir / name).write_text(src.read_text())
        whitelist, _ = ACT.build_whitelist(adir, V.parse_yamlish, V.fail)

    remedy = V.parse_yamlish((root / ".veldo" / "examples" / "remedy-example.yaml").read_text())
    ladder = AutonomyLadder(levels={"fake-deploy-controller": "L2"})
    kill = KillSwitch()
    budget = ActionBudget(5)
    target = FakeActionSystem()
    cred = ExecutorCredential("dmitry-executor", "fake-deploy-controller", object())
    ex = ActionExecutor(cred, ladder, kill, budget, target, ACT, INC, timeout_seconds=300)

    confirmation = {"decision": "confirmed", "confirmed_by": "dmitry",
                    "proposal_digest": proposal_digest(remedy), "incident": remedy.get("incident")}
    if len(argv) > 1 and argv[1] == "--no-confirm":
        confirmation = None
    result = ex.execute(remedy, whitelist, confirmation=confirmation)
    print("veldo execution organ (%s): %s" % (SCHEMA, "EXECUTED" if result.get("executed") else "REFUSED (%s)" % result.get("refused")))
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("executed") or result.get("refused") else 1


if __name__ == "__main__":
    import sys
    try:
        sys.exit(_cli(sys.argv))
    except ExecutorError as e:
        print("veldo execution organ: %s" % e)
        sys.exit(1)
