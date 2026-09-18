#!/usr/bin/env python3
"""Revocation and authorization rechecks (PLAN-0019 W11, VELDO-0026, R14, R39, R50, R69, R70).

WHAT THIS MODULE IS. The reusable acceptance guard for the nine R39 boundaries (command acceptance,
proposal commit, assignment acceptance, claim, dispatch acceptance, privileged-tool use, result
acceptance, decision settlement, landing publication), each a registered callable that judges one
action against the CURRENT committed state of the control store: the actor's membership and
roles through the authority contract, the revocation ledger, and every input the caller read into
its snapshot (membership, policy, scope, decisions, dependencies, and the prerequisites those
dependencies reference, indirectly) compared version by version with what the store holds now.
Anything that moved, was withdrawn or was newly inserted since the snapshot refuses by name; the
refusal is written to the store as a durable denial before it is returned, and a denial that
cannot be written stands the boundary down (nothing is allowed on an unrecorded refusal).

Revocation and effect acceptance are store commands registered by attach(): both name the ONE
revocation-ledger entity as an expected version, so their order is established by the store's
transaction and never argued about afterwards. A revocation that commits first leaves zero new
effects for the revoked principal; an effect accepted first is recorded by the revocation as IN
FLIGHT with a stop obligation, and closure is not effective until every in-flight effect is
reconciled by evidence (stopped, completed or failed). Stop obligations are journaled entities:
a process killed after the revocation commit and before it notified anyone loses nothing, because
replay and the pending-stop query rebuild them. Outputs submitted by a revoked principal stay
evidence (their digests are recorded) but satisfy no obligation without fresh, version-bound
authorization.

WHAT IT IS NOT. It runs no receiver and undoes no external effect; a real local receiver proves
serialized acceptance, and the floor and channel consumers that must invoke these guards are
Packages C and E. Standard library only; the authority contract, the control store and the
membership organ are loaded as sibling organs by path.

FAULT POINTS. Under VELDO_CONTROL_TEST_HARNESS=1, VELDO_DENIAL_WRITE_FAIL=1 makes the denial
writer fail as a disk write would, so the stand-down path is exercised for real.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

SCHEMA = "veldo.control_revocation/v1"
LEDGER_ENTITY = "authority:revocations"
REVOCATION_OPERATIONS = ("revoke_authorization", "accept_effect", "reconcile_effect", "record_denial", "submit_output", "reauthorize")
EFFECT_STATES = ("accepted", "in_flight", "stopped", "completed", "failed")
STOP_STATES = ("requested", "satisfied")
REFUSALS = ("unknown_boundary", "not_authorized", "revoked", "stale_read", "dependency_withdrawn", "denial_not_recorded", "stand_down",
            "effect_refused", "output_is_evidence_only", "reauthorization_required")


def _organ(name):
    spec = importlib.util.spec_from_file_location("veldo_revocation_" + name, Path(__file__).resolve().parent / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AC = _organ("authority_contract")
CM = _organ("control_membership")


class RevocationRefused(Exception):
    def __init__(self, code, detail):
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail = code, detail


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def digest_of(obj):
    return "sha256:" + hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# ---------------------------------------------------------------------------------------------
# The ledger and the registered transitions (attach() puts them in the store's registry).
# ---------------------------------------------------------------------------------------------

def _ledger(before):
    cur = dict((before.get(LEDGER_ENTITY) or {}).get("data") or {"revocation_version": 0, "revoked": {}})
    cur.setdefault("revoked", {})
    return cur


def _bump_ledger(before, revoked_update=None):
    cur = _ledger(before)
    cur["revocation_version"] = int(cur.get("revocation_version", 0)) + 1
    if revoked_update:
        cur["revoked"] = dict(cur["revoked"], **revoked_update)
    return {"kind": "revocation_ledger", "data": cur}


def _t_revoke(params, before, StoreRefused):
    """Revoke a principal's authorization at `at`: the ledger records it; every effect of that
    principal already accepted becomes in_flight with a stop obligation; nothing external is undone."""
    if not _is_str(params.get("principal")) or not _is_num(params.get("at")) or not _is_str(params.get("reason")):
        raise StoreRefused("transition_refused", "revoke_authorization needs principal, at and reason")
    changes = {LEDGER_ENTITY: _bump_ledger(before, {params["principal"]: {"at": params["at"], "reason": params["reason"], "by": params.get("revoked_by")}})}
    for eid, e in before.items():
        if e["kind"] == "effect" and e["data"].get("principal") == params["principal"] and e["data"].get("state") == "accepted":
            changes[eid] = {"kind": "effect", "data": dict(e["data"], state="in_flight", revoked_at=params["at"])}
            changes["stop:" + eid] = {"kind": "stop_obligation", "data": {"effect": eid, "principal": params["principal"], "state": "requested",
                                                                        "requested_at": params["at"], "receiver": e["data"].get("receiver")}}
    return changes


def _t_accept_effect(params, before, StoreRefused):
    """A receiver accepts an external effect for a principal. Refused inside the transaction when
    the ledger already holds the principal's revocation: revocation first means zero new effects."""
    for f in ("effect_id", "principal", "receiver", "kind"):
        if not _is_str(params.get(f)):
            raise StoreRefused("transition_refused", "accept_effect needs %s" % f)
    if params["effect_id"] in before:
        raise StoreRefused("transition_refused", "effect %s already exists" % params["effect_id"])
    if params["principal"] in _ledger(before)["revoked"]:
        raise StoreRefused("transition_refused", "revoked: %s was revoked before this effect was accepted; zero new effects" % params["principal"])
    return {params["effect_id"]: {"kind": "effect", "data": {"principal": params["principal"], "receiver": params["receiver"], "kind": params["kind"],
                                                             "state": "accepted", "accepted_at": params.get("at")}},
            LEDGER_ENTITY: _bump_ledger(before)}


def _t_reconcile_effect(params, before, StoreRefused):
    """Evidence resolves an in-flight effect: stopped, completed or failed, with the receiver's
    evidence digest; the stop obligation is satisfied."""
    eid = params.get("effect_id")
    if eid not in before or before[eid]["kind"] != "effect" or params.get("outcome") not in ("stopped", "completed", "failed") or not _is_str(params.get("evidence_digest")):
        raise StoreRefused("transition_refused", "reconcile_effect needs an existing effect, an outcome (stopped, completed, failed) and evidence")
    changes = {eid: {"kind": "effect", "data": dict(before[eid]["data"], state=params["outcome"], evidence_digest=params["evidence_digest"], reconciled_at=params.get("at"))}}
    stop = "stop:" + eid
    if stop in before:
        changes[stop] = {"kind": "stop_obligation", "data": dict(before[stop]["data"], state="satisfied", satisfied_at=params.get("at"))}
    return changes


def _t_record_denial(params, before, StoreRefused):
    """A durable denial: the boundary, the actor, the refusal codes and the snapshot digest."""
    for f in ("denial_id", "boundary", "actor", "refusals"):
        if f not in params:
            raise StoreRefused("transition_refused", "record_denial needs %s" % f)
    if not isinstance(params["refusals"], list) or not params["refusals"]:
        raise StoreRefused("transition_refused", "a denial names at least one refusal")
    return {params["denial_id"]: {"kind": "denial", "data": {k: params.get(k) for k in ("boundary", "actor", "refusals", "snapshot_digest", "at", "action")}}}


def _t_submit_output(params, before, StoreRefused):
    """A submitted output is evidence: its digest and submitter are kept; whether it satisfies an
    obligation is decided by result acceptance, not by the submission."""
    if not _is_str(params.get("output_id")) or not _is_str(params.get("digest")) or not _is_str(params.get("principal")):
        raise StoreRefused("transition_refused", "submit_output needs output_id, digest and principal")
    revoked = params["principal"] in _ledger(before)["revoked"]
    return {params["output_id"]: {"kind": "output_evidence", "data": {"digest": params["digest"], "principal": params["principal"], "obligation": params.get("obligation"),
                                                                       "submitted_at": params.get("at"), "submitted_after_revocation": revoked, "satisfies": False}}}


def _t_reauthorize(params, before, StoreRefused):
    """Fresh, version-bound authorization for an obligation: names the revocation version it was
    granted at; a revocation since then (a moved version) makes it stale by the ledger's version."""
    if not _is_str(params.get("obligation")) or not _is_str(params.get("granted_by")) or not isinstance(params.get("revocation_version"), int):
        raise StoreRefused("transition_refused", "reauthorize needs obligation, granted_by and the revocation_version it binds to")
    if params["revocation_version"] != int(_ledger(before).get("revocation_version", 0)):
        raise StoreRefused("transition_refused", "reauthorization names revocation version %r, the ledger is at %r" % (params["revocation_version"], _ledger(before).get("revocation_version", 0)))
    return {"reauth:" + params["obligation"]: {"kind": "reauthorization", "data": {"obligation": params["obligation"], "granted_by": params["granted_by"],
                                                                                   "revocation_version": params["revocation_version"], "at": params.get("at")}}}


def attach(store):
    """Register the six transitions into the store MODULE the authority process uses. Idempotent."""
    def wrap(fn):
        return lambda params, before: fn(params, before, store.StoreRefused)
    for name, fn in (("revoke_authorization", _t_revoke), ("accept_effect", _t_accept_effect), ("reconcile_effect", _t_reconcile_effect),
                     ("record_denial", _t_record_denial), ("submit_output", _t_submit_output), ("reauthorize", _t_reauthorize)):
        store.COMMAND_REGISTRY[name] = {"transition": wrap(fn), "writes": ("entities", "journal", "commands", "nonces")}
    return sorted(REVOCATION_OPERATIONS)


def touched_entities(command, entities):
    """Every entity a revocation-organ command writes, from the committed snapshot: the ledger for
    revocations and acceptances, the principal's accepted effects and their stop obligations for a
    revocation, the effect and its stop for a reconciliation, the denial, output or reauthorization."""
    p, op = command.get("parameters") or {}, command.get("operation")
    ids = []
    if op in ("revoke_authorization", "accept_effect", "submit_output", "reauthorize"):
        ids.append(LEDGER_ENTITY)  # written by the first two, READ by the last two: a revocation in between moves its version and refuses them
    if op == "revoke_authorization":
        for eid, e in entities.items():
            if e["kind"] == "effect" and e["data"].get("principal") == p.get("principal") and e["data"].get("state") == "accepted":
                ids += [eid, "stop:" + eid]
    if op == "accept_effect":
        ids.append(p.get("effect_id"))
    if op == "reconcile_effect":
        ids += [p.get("effect_id"), "stop:" + str(p.get("effect_id"))] if "stop:" + str(p.get("effect_id")) in entities else [p.get("effect_id")]
    if op == "record_denial":
        ids.append(p.get("denial_id"))
    if op == "submit_output":
        ids.append(p.get("output_id"))
    if op == "reauthorize":
        ids.append("reauth:" + str(p.get("obligation")))
    return [i for i in ids if _is_str(i)]


def execute(store, conn, command, journal_signer, now, authority_generation=1):
    """Commit one revocation-organ command with expected versions from the committed snapshot (so
    revocation and acceptance racing the ledger have one winner) and the authority's journal signer."""
    if command.get("operation") not in REVOCATION_OPERATIONS:
        raise RevocationRefused("effect_refused", "%r is not a revocation-organ operation" % command.get("operation"))
    ents = store.materialized_state(conn)["entities"]
    stored = dict(command)
    stored["parameters"] = dict(command.get("parameters") or {}, at=command.get("parameters", {}).get("at", now))
    stored["expected_versions"] = {eid: ents.get(eid, {}).get("version", 0) for eid in touched_entities(stored, ents)}
    try:
        return store.execute(conn, stored, journal_signer[0], journal_signer[1], authority_generation, committed_at=now)
    except store.StoreRefused as e:
        raise RevocationRefused("effect_refused" if "revoked:" not in e.detail else "revoked", "%s: %s" % (e.code, e.detail))


# ---------------------------------------------------------------------------------------------
# The ledger read, in-flight effects, stop obligations, closure.
# ---------------------------------------------------------------------------------------------

def ledger(store, conn):
    st = store.materialized_state(conn)["entities"]
    return _ledger(st), st


def is_revoked(store, conn, principal, now):
    led, _st = ledger(store, conn)
    r = led["revoked"].get(principal)
    return r is not None and r.get("at", now) <= now


def pending_stop_obligations(store, conn):
    """Stop obligations not yet satisfied, in id order: what a restarted authority must still ask
    receivers to stop. Rebuilt from committed entities (and therefore from the journal by replay)."""
    st = store.materialized_state(conn)["entities"]
    return sorted((eid, e["data"]) for eid, e in st.items() if e["kind"] == "stop_obligation" and e["data"].get("state") == "requested")


def closure_status(store, conn, principal):
    """Whether a revocation is EFFECTIVELY closed: only when the principal is revoked and none of its
    effects is in flight. An effect accepted before the revocation stays in flight until evidence
    reconciles it; closure is reported as not_effective with the in-flight effects named."""
    led, st = ledger(store, conn)
    if principal not in led["revoked"]:
        return {"revoked": False, "effective": False, "in_flight": [], "reason": "not revoked"}
    in_flight = sorted(eid for eid, e in st.items() if e["kind"] == "effect" and e["data"].get("principal") == principal and e["data"].get("state") in ("accepted", "in_flight"))
    return {"revoked": True, "effective": not in_flight, "in_flight": in_flight,
            "reason": "effective: no effect of %s is in flight" % principal if not in_flight else "not effective: %d effect(s) in flight await stop or reconciliation evidence" % len(in_flight)}


# ---------------------------------------------------------------------------------------------
# The nine boundary guards over one snapshot (R39, R70, R14).
# ---------------------------------------------------------------------------------------------

def snapshot(store, conn, read_set):
    """{entity_id: version} for every entity the caller's decision reads, PLUS the indirect
    prerequisites: for every entity of kind dependency in the read set, the entities its
    `prerequisites` name are read too (a withdrawn prerequisite is a changed input). Absent
    entities snapshot at version 0 (their later insertion is a change)."""
    st = store.materialized_state(conn)["entities"]
    ids = set(read_set or [])
    for eid in list(ids):
        e = st.get(eid)
        if e and e["kind"] == "dependency":
            ids |= set(e["data"].get("prerequisites") or [])
    snap = {eid: st.get(eid, {}).get("version", 0) for eid in sorted(ids)}
    snap[LEDGER_ENTITY] = st.get(LEDGER_ENTITY, {}).get("version", 0)
    return {"versions": snap, "digest": digest_of(snap)}


def stale_reads(store, conn, snap):
    """Every input whose version differs now from the snapshot, and every prerequisite withdrawn or
    newly referenced since: named refusals, empty iff the snapshot still holds."""
    st = store.materialized_state(conn)["entities"]
    problems = []
    for eid, v in snap["versions"].items():
        now_v = st.get(eid, {}).get("version", 0)
        if now_v != v:
            e = st.get(eid)
            if e and e["kind"] in ("dependency", "prerequisite") and e["data"].get("status") == "withdrawn":
                problems.append("dependency_withdrawn:%s" % eid)
            else:
                problems.append("stale_read:%s moved from version %r to %r" % (eid, v, now_v))
    for eid, v in list(snap["versions"].items()):
        e = st.get(eid)
        if e and e["kind"] == "dependency":
            for pre in e["data"].get("prerequisites") or []:
                if pre not in snap["versions"]:
                    problems.append("stale_read:%s references prerequisite %s that the snapshot never read" % (eid, pre))
    return problems


def _guard_common(store, conn, membership_state, boundary, actor, requirement, snap, now):
    problems = []
    if boundary not in AC.BOUNDARIES:
        return ["unknown_boundary:%s" % boundary]
    if is_revoked(store, conn, actor, now):
        problems.append("revoked:%s" % actor)
    authorized, refusals = AC.authorize(boundary, dict(requirement, boundary=boundary), [{"principal": actor, "subject_digest": requirement.get("subject_digest")}],
                                        membership_state["membership"], now)
    if not authorized:
        problems += ["not_authorized:%s" % r for r in refusals]
    problems += stale_reads(store, conn, snap)
    return problems


def _result_acceptance_extra(store, conn, actor, requirement):
    """Result acceptance: an output submitted by a revoked principal, or after revocation, is
    evidence only unless a fresh version-bound reauthorization for the obligation exists at the
    ledger's current version."""
    led, st = ledger(store, conn)
    out = st.get(requirement.get("output"))
    if out is None or out["kind"] != "output_evidence":
        return ["output_is_evidence_only: no submitted output %r" % requirement.get("output")]
    if out["data"].get("principal") in led["revoked"] or out["data"].get("submitted_after_revocation"):
        re = st.get("reauth:" + str(requirement.get("obligation")))
        if re is None or re["data"].get("revocation_version") != int(led.get("revocation_version", 0)):
            return ["output_is_evidence_only: output %s was submitted by a revoked principal; it is retained as evidence and satisfies no obligation" % requirement.get("output"),
                    "reauthorization_required: obligation %r needs fresh authorization bound to revocation version %r" % (requirement.get("obligation"), led.get("revocation_version", 0))]
    return []


BOUNDARY_GUARDS = {b: (_result_acceptance_extra if b == "result_acceptance" else None) for b in AC.BOUNDARIES}


def registered_boundaries():
    return sorted(BOUNDARY_GUARDS)


def _denial_write_fails():
    return os.environ.get("VELDO_CONTROL_TEST_HARNESS") == "1" and os.environ.get("VELDO_DENIAL_WRITE_FAIL") == "1"


def accept(store, conn, membership_state, boundary, actor, requirement, snap, now, journal_signer, action=None):
    """The guard at one boundary. Returns {allowed, refusals, denial, stand_down}. Every refusal is
    written as a durable denial BEFORE it is returned; a denial that cannot be written (a read-only
    handle, a disk fault) makes the boundary STAND DOWN: allowed False, stand_down True, and the
    caller stops dispatch. Nothing is ever allowed on an unrecorded refusal."""
    if boundary not in BOUNDARY_GUARDS:
        return {"allowed": False, "refusals": ["unknown_boundary:%s" % boundary], "denial": None, "stand_down": True}
    refusals = _guard_common(store, conn, membership_state, boundary, actor, requirement, snap, now)
    extra = BOUNDARY_GUARDS[boundary]
    if extra is not None and not refusals:
        refusals += extra(store, conn, actor, requirement)
    if not refusals:
        return {"allowed": True, "refusals": [], "denial": None, "stand_down": False}
    denial_id = "denial:%s:%s:%s" % (boundary, actor, digest_of([boundary, actor, action, refusals, snap["digest"], now])[7:23])
    cmd = {"command_id": "denial-" + denial_id.split(":")[-1], "principal": "veldo-authority", "operation": "record_denial", "target": "authority",
           "parameters": {"denial_id": denial_id, "boundary": boundary, "actor": actor, "refusals": refusals, "snapshot_digest": snap["digest"], "action": action},
           "artifact_digests": [], "nonce": "nonce-" + denial_id, "expected_versions": {}}
    try:
        if _denial_write_fails():
            raise store.StoreRefused("incomplete_transaction", "disk write failure injected at the denial journal commit")
        execute(store, conn, cmd, journal_signer, now)
    except (store.StoreRefused, RevocationRefused) as e:
        return {"allowed": False, "refusals": refusals + ["denial_not_recorded: %s" % e], "denial": None, "stand_down": True,
                "note": "the refusal could not be durably recorded: the boundary stands down and dispatch stops until the store accepts writes"}
    return {"allowed": False, "refusals": refusals, "denial": denial_id, "stand_down": False}


def dispatch_permitted(verdict):
    """Whether a caller may proceed to dispatch on a guard verdict: only an allowed verdict, never a
    stand-down and never a refusal."""
    return verdict.get("allowed") is True and verdict.get("stand_down") is not True
