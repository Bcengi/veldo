#!/usr/bin/env python3
"""Authenticated membership and scoped delegation (PLAN-0019 W10, VELDO-0025, R20, R36, R37, R38).

WHAT THIS MODULE IS. The membership organ of the authority: the administrative commands that
enroll principals, change roles, revoke membership and grant, supersede or revoke delegations, each
accepted only from an OpenSSH-envelope Ed25519 signed command whose canonical digest is RECOMPUTED
from the operation, target and complete parameters to be executed (an enrollment public key among
them) and verified against the signer's ACTIVE key in the store's committed keyring, against the
store's CURRENT membership and delegation versions, with the nonce consumed by the same transaction
that commits the change. Nothing is persisted on failure. The policy the changes must satisfy
(R37): only a person holding membership_steward changes membership; a service, policy or agent run
never enrolls or grants itself anything (the signer is never the target of its own enrollment, and
a non-person signer changes no membership); an enrollee proves possession of its key by
co-signing the envelope; a delegation is granted by the delegating person (or the steward) within
that person's own roles and supersedes by naming the delegation it replaces. The owner bootstrap
is preserved: with no membership at all, exactly one enrollment is accepted, a person carrying
project_owner and membership_steward, self-signed with the key being enrolled; no two-person
enrollment rule is invented. Every transition is a registered store command (attach() registers
them into the store module the authority process uses), so the control store commits it
atomically with the journal record, the nonce, and the authority versions, which are ONE entity
whose expected version every membership command names: two changes racing one version have one
winner.

Delegated use (R38) is judged conjunctively: an active, current (not superseded, revoked or
expired) delegation for that principal on that channel, permitting that assertion kind, covering
the request's scope at the request's version, with the role, named-principal, actor-kind, quorum
and independence predicates of the boundary applied through the authority contract. A cached
delegation across its committed supersession is stale and refused by the version check.

WHAT IT IS NOT. Key custody is W12, revocation delivery W11; no live channel, additional person or
real key is enrolled by this module in this repository. Standard library only; the authority
contract and the control store are loaded as sibling organs by path.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

SCHEMA = "veldo.control_membership/v1"
VERSIONS_ENTITY = "authority:versions"
MEMBERSHIP_OPERATIONS = ("enroll_principal", "change_roles", "revoke_membership")
DELEGATION_OPERATIONS = ("grant_delegation", "supersede_delegation", "revoke_delegation")
ADMIN_OPERATIONS = MEMBERSHIP_OPERATIONS + DELEGATION_OPERATIONS
STEWARD_ROLE = "membership_steward"
BOOTSTRAP_ROLES = frozenset({"project_owner", "membership_steward"})
REFUSALS = ("envelope_refused", "signature_invalid", "policy_refused", "bootstrap_refused", "key_possession_unproven",
            "self_grant_refused", "not_a_person", "stale_delegation", "delegation_refused", "store_refused", "scope_refused",
            "journal_signer_required")


def _scope_set(scope):
    """None for the universal scope "*", else the set of named scopes; a malformed scope is empty."""
    if scope == "*":
        return None
    return set(scope) if isinstance(scope, (list, tuple)) else set()


def scope_covers(outer, inner):
    """Whether authority scoped `outer` may act on `inner`: "*" covers everything, only "*" covers
    "*", and a named scope covers a subset of itself.

    `inner` names what is being acted on. A plain string is one named scope (a repository id, a
    project), never "nothing": reading it as the empty set made every named scope cover it. Anything
    that is neither "*", a string nor a list of strings is refused rather than read as empty."""
    o = _scope_set(outer)
    if isinstance(inner, str) and inner != "*":
        i = {inner}
    elif inner == "*" or (isinstance(inner, (list, tuple)) and all(isinstance(x, str) for x in inner)):
        i = _scope_set(inner)
    else:
        return False
    if o is None:
        return True
    if i is None:
        return False
    return i <= o


def _organ(name):
    spec = importlib.util.spec_from_file_location("veldo_membership_" + name, Path(__file__).resolve().parent / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AC = _organ("authority_contract")


class MembershipRefused(Exception):
    def __init__(self, code, detail):
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail = code, detail


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---------------------------------------------------------------------------------------------
# The committed authority state, read from the store's entities.
# ---------------------------------------------------------------------------------------------

def authority_state(store, conn):
    """{membership, delegations, keyring, membership_version, delegation_version} from committed
    entities: kind membership (id = principal), kind delegation (id = delegation id), kind
    verification_key (id = key:<principal>:<n>), and the one versions entity."""
    st = store.materialized_state(conn)["entities"]
    membership, delegations, keyring = [], [], []
    for eid, e in st.items():
        if e["kind"] == "membership":
            membership.append(dict(e["data"], principal=eid, entity_version=e["version"]))
        elif e["kind"] == "delegation":
            delegations.append(dict(e["data"], id=eid, entity_version=e["version"]))
        elif e["kind"] == "verification_key":
            keyring.append(dict(e["data"], key_id=eid))
    versions = st.get(VERSIONS_ENTITY, {}).get("data", {})
    return {"membership": membership, "delegations": delegations, "keyring": keyring, "entities": st,
            "membership_version": int(versions.get("membership_version", 0)), "delegation_version": int(versions.get("delegation_version", 0)),
            "versions_entity_version": st.get(VERSIONS_ENTITY, {}).get("version", 0)}


def _member(state, principal):
    return AC.membership_entry(state["membership"], principal)


# ---------------------------------------------------------------------------------------------
# The registered transitions (attach() puts them in the store's registry).
# ---------------------------------------------------------------------------------------------

def key_entity_id(principal, public_key):
    """The deterministic id of a verification-key entity: key:<principal>:<12 hex of the key's
    sha256>, so a caller can name its expected version before the enrollment commits."""
    return "key:%s:%s" % (principal, hashlib.sha256(" ".join(str(public_key).split()[:2]).encode()).hexdigest()[:12])


def _bump(before, which):
    cur = dict((before.get(VERSIONS_ENTITY) or {}).get("data") or {"membership_version": 0, "delegation_version": 0})
    cur[which] = int(cur.get(which, 0)) + 1
    return {"kind": "authority_versions", "data": cur}


def _t_enroll(params, before, StoreRefused):
    for f in ("principal", "principal_type", "roles", "public_key", "independence_group", "scope"):
        if f not in params:
            raise StoreRefused("transition_refused", "enroll_principal needs %s" % f)
    if not _is_str(params["principal"]) or params["principal_type"] not in AC.PRINCIPAL_TYPES or not isinstance(params["roles"], list) \
            or not all(r in AC.ROLES for r in params["roles"]) or not _is_str(params["public_key"]):
        raise StoreRefused("transition_refused", "enroll_principal: principal, a principal_type in PRINCIPAL_TYPES, roles in ROLES and an OpenSSH public key")
    if params["principal"] in before and before[params["principal"]]["kind"] == "membership" and before[params["principal"]]["data"].get("revoked_at") is None:
        raise StoreRefused("transition_refused", "principal %s is already enrolled; use change_roles" % params["principal"])
    key_id = key_entity_id(params["principal"], params["public_key"])
    at = params.get("enrolled_at", 0)
    changes = {params["principal"]: {"kind": "membership", "data": {"principal_type": params["principal_type"], "roles": sorted(params["roles"]),
                                                                     "independence_group": params["independence_group"], "scope": params["scope"],
                                                                     "revoked_at": None, "expires_at": params.get("expires_at"), "enrolled_by": params.get("enrolled_by")}},
               key_id: {"kind": "verification_key", "data": {"principal": params["principal"], "public_key": " ".join(params["public_key"].split()[:2]),
                                                             "effective_at": at, "retired_at": None, "revoked_at": None}},
               VERSIONS_ENTITY: _bump(before, "membership_version")}
    # A re-enrollment (after revocation) REVOKES every prior key of the principal: only the key
    # being enrolled verifies from now on; the old private key opens nothing.
    for eid, e in before.items():
        if e["kind"] == "verification_key" and e["data"].get("principal") == params["principal"] and eid != key_id and e["data"].get("revoked_at") is None:
            changes[eid] = {"kind": "verification_key", "data": dict(e["data"], revoked_at=at)}
    return changes


def _t_change_roles(params, before, StoreRefused):
    p = params.get("principal")
    if not _is_str(p) or p not in before or before[p]["kind"] != "membership" or not isinstance(params.get("roles"), list) or not all(r in AC.ROLES for r in params["roles"]):
        raise StoreRefused("transition_refused", "change_roles needs an enrolled principal and roles in ROLES")
    return {p: {"kind": "membership", "data": dict(before[p]["data"], roles=sorted(params["roles"]), scope=params.get("scope", before[p]["data"].get("scope")))},
            VERSIONS_ENTITY: _bump(before, "membership_version")}


def _t_revoke_membership(params, before, StoreRefused):
    p = params.get("principal")
    if not _is_str(p) or p not in before or before[p]["kind"] != "membership" or not _is_num(params.get("revoked_at")):
        raise StoreRefused("transition_refused", "revoke_membership needs an enrolled principal and a revoked_at time")
    return {p: {"kind": "membership", "data": dict(before[p]["data"], revoked_at=params["revoked_at"])}, VERSIONS_ENTITY: _bump(before, "membership_version")}


DELEGATION_FIELDS = ("id", "principal", "channel", "assertion_kinds", "authority_scope", "request_version", "presentation_version", "expires_at", "edge_key_id")


def _t_grant_delegation(params, before, StoreRefused):
    for f in DELEGATION_FIELDS:
        if f not in params:
            raise StoreRefused("transition_refused", "grant_delegation needs %s" % f)
    if params["id"] in before or not isinstance(params["authority_scope"], list) or not params["authority_scope"] or not isinstance(params["assertion_kinds"], list) \
            or not _is_num(params["expires_at"]):
        raise StoreRefused("transition_refused", "grant_delegation: a new id, a non-empty authority_scope, assertion kinds and a numeric expiry")
    data = {f: params[f] for f in DELEGATION_FIELDS if f != "id"}
    data.update(revoked_at=None, superseded_by=None, granted_by=params.get("granted_by"))
    return {params["id"]: {"kind": "delegation", "data": data}, VERSIONS_ENTITY: _bump(before, "delegation_version")}


def _t_supersede_delegation(params, before, StoreRefused):
    old = params.get("supersedes")
    if not _is_str(old) or old not in before or before[old]["kind"] != "delegation" or before[old]["data"].get("superseded_by") is not None:
        raise StoreRefused("transition_refused", "supersede_delegation names an active delegation it replaces")
    new = _t_grant_delegation(params, before, StoreRefused)
    new[old] = {"kind": "delegation", "data": dict(before[old]["data"], superseded_by=params["id"])}
    return new


def _t_revoke_delegation(params, before, StoreRefused):
    d = params.get("id")
    if not _is_str(d) or d not in before or before[d]["kind"] != "delegation" or not _is_num(params.get("revoked_at")):
        raise StoreRefused("transition_refused", "revoke_delegation needs an existing delegation and a revoked_at time")
    return {d: {"kind": "delegation", "data": dict(before[d]["data"], revoked_at=params["revoked_at"])}, VERSIONS_ENTITY: _bump(before, "delegation_version")}


def attach(store):
    """Register the six administrative transitions into `store` (the control store MODULE the
    authority process uses). Idempotent. Every transition writes the versions entity, so every
    administrative command must name its expected version (the membership or delegation CAS)."""
    def wrap(fn):
        return lambda params, before: fn(params, before, store.StoreRefused)
    for name, fn in (("enroll_principal", _t_enroll), ("change_roles", _t_change_roles), ("revoke_membership", _t_revoke_membership),
                     ("grant_delegation", _t_grant_delegation), ("supersede_delegation", _t_supersede_delegation), ("revoke_delegation", _t_revoke_delegation)):
        store.COMMAND_REGISTRY[name] = {"transition": wrap(fn), "writes": ("entities", "journal", "commands", "nonces")}
    return sorted(ADMIN_OPERATIONS)


def touched_entities(command, entities=None):
    """The entity ids an administrative command writes, so expected versions can be taken from ONE
    committed snapshot: the target principal or delegation(s), the key being enrolled, every prior
    key of a re-enrolled principal (they are revoked), and the versions entity."""
    p, op = command.get("parameters") or {}, command.get("operation")
    ids = [VERSIONS_ENTITY]
    if op in MEMBERSHIP_OPERATIONS:
        ids.append(p.get("principal"))
    if op == "enroll_principal" and _is_str(p.get("principal")) and _is_str(p.get("public_key")):
        ids.append(key_entity_id(p["principal"], p["public_key"]))
        for eid, e in (entities or {}).items():
            if e["kind"] == "verification_key" and e["data"].get("principal") == p["principal"] and eid not in ids:
                ids.append(eid)
    if op in DELEGATION_OPERATIONS:
        ids.append(p.get("id"))
    if op == "supersede_delegation":
        ids.append(p.get("supersedes"))
    return [i for i in ids if _is_str(i)]


# ---------------------------------------------------------------------------------------------
# Admission of an administrative command: envelope, signature, policy, then the store.
# ---------------------------------------------------------------------------------------------

def policy_problems(state, signer, command, now):
    """Why the accepted policy (R37) refuses this change even though the signature is good: the
    signer is not a person (a service, policy or agent run changes no membership); the signer
    lacks membership_steward for a membership change; the signer is the target of its own
    enrollment or grants itself roles or a delegation (self-grant); a delegation is granted by
    someone other than the delegating person or the steward, or beyond the delegating person's
    roles; a superseding delegation changes principal."""
    problems = []
    entry = _member(state, signer)
    if entry is None or entry.get("principal_type") != "person":
        problems.append("not_a_person: signer %r is not an enrolled person; services, policies and agent runs change no membership" % signer)
        return problems
    p, op = command.get("parameters") or {}, command.get("operation")
    roles = set(entry.get("roles") or [])
    signer_scope = entry.get("scope")
    if op in MEMBERSHIP_OPERATIONS:
        if STEWARD_ROLE not in roles:
            problems.append("policy_refused: %s requires the signer to hold %s" % (op, STEWARD_ROLE))
        if op == "enroll_principal" and p.get("principal") == signer:
            problems.append("self_grant_refused: a principal does not enroll itself")
        if op == "change_roles" and p.get("principal") == signer:
            if set(p.get("roles") or []) - roles:
                problems.append("self_grant_refused: a principal does not grant itself roles it does not hold")
            if "scope" in p and p["scope"] != signer_scope:
                problems.append("self_grant_refused: a principal does not change its own scope (%r to %r)" % (signer_scope, p["scope"]))
        # A steward acts within its OWN scope: the scope it enrolls or sets, and the scope of the
        # principal it changes or revokes, must be covered by the steward's scope (R37).
        target = _member(state, p.get("principal"))
        if op == "enroll_principal" and not scope_covers(signer_scope, p.get("scope")):
            problems.append("scope_refused: steward scope %r does not cover the enrollment scope %r" % (signer_scope, p.get("scope")))
        if op in ("change_roles", "revoke_membership") and target is not None and not scope_covers(signer_scope, target.get("scope")):
            problems.append("scope_refused: steward scope %r does not cover %r's scope %r" % (signer_scope, p.get("principal"), target.get("scope")))
        if op == "change_roles" and "scope" in p and not scope_covers(signer_scope, p["scope"]):
            problems.append("scope_refused: steward scope %r does not cover the new scope %r" % (signer_scope, p["scope"]))
        target_type = p.get("principal_type") if op == "enroll_principal" else (_member(state, p.get("principal")) or {}).get("principal_type")
        if target_type in ("service", "policy", "agent_run") and STEWARD_ROLE in set(p.get("roles") or []):
            problems.append("policy_refused: a non-person principal never holds %s" % STEWARD_ROLE)
    if op in DELEGATION_OPERATIONS:
        target = p.get("principal")
        if op in ("grant_delegation", "supersede_delegation"):
            delegating = _member(state, target)
            if delegating is None or delegating.get("principal_type") != "person":
                problems.append("delegation_refused: delegations are granted for enrolled persons; %r is not one" % target)
            elif signer != target and STEWARD_ROLE not in roles:
                problems.append("delegation_refused: only the delegating person or a %s grants a delegation for %r" % (STEWARD_ROLE, target))
            else:
                # authority_scope is SCOPE (the projects the delegation covers), judged against the
                # delegating person's scope; roles, if the delegation names any, against their roles.
                asc = p.get("authority_scope") or []
                if not scope_covers(delegating.get("scope"), "*" if "*" in asc else asc):
                    problems.append("delegation_refused: authority_scope %s exceeds %r's scope %r" % (sorted(asc), target, delegating.get("scope")))
                if set(p.get("roles") or []) - set(delegating.get("roles") or []):
                    problems.append("delegation_refused: delegation roles %s exceed %r's roles %s" % (sorted(p.get("roles") or []), target, sorted(delegating.get("roles") or [])))
            if op == "supersede_delegation":
                old = next((d for d in state["delegations"] if d["id"] == p.get("supersedes")), None)
                if old is not None and old.get("principal") != target:
                    problems.append("delegation_refused: a superseding delegation keeps the principal (%r, not %r)" % (old.get("principal"), target))
        if op == "revoke_delegation":
            old = next((d for d in state["delegations"] if d["id"] == p.get("id")), None)
            if old is None or (signer != old.get("principal") and STEWARD_ROLE not in roles):
                problems.append("delegation_refused: only the delegating person or a %s revokes a delegation" % STEWARD_ROLE)
    return problems


def bootstrap_problems(state, envelope, command):
    """The owner bootstrap (R37): accepted only while NO membership exists, for exactly one person
    enrolling themself with project_owner and membership_steward, signed with the key being
    enrolled. Anything else with an empty membership is refused; anything at all once membership
    exists goes through the ordinary path."""
    p = command.get("parameters") or {}
    if state["membership"]:
        return ["membership exists; the bootstrap is over"]
    problems = []
    if command.get("operation") != "enroll_principal":
        problems.append("with no membership only the owner enrollment is accepted")
    if p.get("principal") != envelope.get("principal"):
        problems.append("the bootstrap enrollment is self-signed by the owner being enrolled")
    if p.get("principal_type") != "person":
        problems.append("the owner is a person")
    if not BOOTSTRAP_ROLES <= set(p.get("roles") or []):
        problems.append("the owner bootstrap carries %s" % sorted(BOOTSTRAP_ROLES))
    return problems


def _verify(envelope, signature, public_key, verifier):
    verify = verifier if verifier is not None else AC.ssh_keygen_verify
    ok, detail = verify(AC.canonical_envelope_bytes(envelope), signature, AC.allowed_signers_line(envelope["principal"], public_key), envelope["principal"])
    return ok is True, detail


def admit(store, conn, envelope, command, signature, authority_ids, now, verifier=None, enrollee_signature=None, committed_at=None, journal_signer=None):
    """Admit and commit one administrative command, or refuse by name with nothing written.
    Order: the operation must be administrative; the store's committed state is read; the
    bootstrap or the ordinary envelope check (digest RECOMPUTED from `command`, this authority's
    ids, the store's CURRENT membership and delegation versions, unconsumed nonce, expiry, active
    membership and active key) runs; the signature is verified against the signer's active key
    (bootstrap: the key being enrolled); the enrollee's key-possession co-signature is verified
    for an enrollment; the policy is applied; then the store commits the transition with the
    envelope's nonce and expected versions taken from the SAME committed snapshot the checks ran
    against (never the caller's, which are not signed), so a change committed between the check
    and the commit loses by version. `journal_signer` is (identity, sign) for the AUTHORITY's
    signature over the journal record's own bytes; without it nothing is committed."""
    if command.get("operation") not in ADMIN_OPERATIONS:
        raise MembershipRefused("policy_refused", "%r is not an administrative operation" % command.get("operation"))
    if not isinstance(envelope, dict) or envelope.get("command_id") != command.get("command_id") or not _is_str(command.get("command_id")):
        raise MembershipRefused("envelope_refused", "the envelope names command %r, the command to execute is %r: the executed id is the signed id"
                                % ((envelope or {}).get("command_id"), command.get("command_id")))
    if not (isinstance(journal_signer, (tuple, list)) and len(journal_signer) == 2 and _is_str(journal_signer[0]) and callable(journal_signer[1])):
        raise MembershipRefused("journal_signer_required", "the authority's journal signer (identity, sign) is required: a journal record is signed over its own bytes")
    prior = conn.execute("SELECT command_digest, result FROM commands WHERE command_id=?", (command.get("command_id"),)).fetchone()
    if prior is not None:
        # A retry after a lost reply (R22): the same signed command, already committed, is answered
        # from the store; the same id with other content is a conflict. The envelope was verified
        # when it committed; its versions are stale now BECAUSE it committed.
        # The committed command is in the journal: its digest covers the expected versions and the
        # attribution the authority added, which a retry cannot reproduce, so identity is judged on
        # the SIGNED content: operation, target and parameters as the envelope's digest covers them.
        rec = next((r for r in store.export_journal(conn) if r["command_id"] == command.get("command_id")), None)
        if rec is None or rec.get("principal") != envelope.get("principal") or rec.get("nonce") != envelope.get("nonce"):
            raise MembershipRefused("store_refused", "command_content_conflict: %s was committed by another principal or nonce" % command.get("command_id"))
        signed_digest = AC.canonical_command_digest(command)
        if envelope.get("command_digest") != signed_digest:
            raise MembershipRefused("envelope_refused", "the retry's envelope digest is not the digest of the command to execute")
        committed_view = json.loads(conn.execute("SELECT result FROM commands WHERE command_id=?", (command["command_id"],)).fetchone()[0])
        return dict(committed_view, replayed=True)
    state = authority_state(store, conn)
    authority = dict(authority_ids, membership_version=state["membership_version"], delegation_version=state["delegation_version"])
    seen = set(store.materialized_state(conn)["nonces"])
    p = command.get("parameters") or {}
    if not state["membership"]:
        problems = bootstrap_problems(state, envelope, command)
        if problems:
            raise MembershipRefused("bootstrap_refused", "; ".join(problems))
        keyring = [{"principal": envelope.get("principal"), "public_key": p.get("public_key"), "effective_at": 0}]
        membership = [{"principal": envelope.get("principal"), "principal_type": "person", "roles": sorted(p.get("roles") or []), "scope": "*"}]
        problems = AC.envelope_problems(envelope, command, authority, now, seen, keyring, membership)
        if problems:
            raise MembershipRefused("envelope_refused", "; ".join(problems))
        ok, detail = _verify(envelope, signature, p["public_key"], verifier)
        if not ok:
            raise MembershipRefused("signature_invalid", "bootstrap signature does not verify with the key being enrolled: %s" % detail)
    else:
        problems = AC.envelope_problems(envelope, command, authority, now, seen, state["keyring"], state["membership"], state["delegations"])
        if problems:
            raise MembershipRefused("envelope_refused", "; ".join(problems))
        key = AC.active_key(state["keyring"], envelope["principal"], now)
        ok, detail = _verify(envelope, signature, key["public_key"], verifier)
        if not ok:
            raise MembershipRefused("signature_invalid", "signature does not verify for %s with the active key: %s" % (envelope["principal"], detail))
        if command["operation"] == "enroll_principal":
            if not _is_str(enrollee_signature):
                raise MembershipRefused("key_possession_unproven", "an enrollment carries the enrollee's co-signature over the envelope with the key being enrolled")
            ok, detail = _verify(dict(envelope, principal=p.get("principal")), enrollee_signature, p.get("public_key", ""), verifier)
            if not ok:
                raise MembershipRefused("key_possession_unproven", "the enrollee's co-signature does not verify with the key being enrolled: %s" % detail)
        problems = policy_problems(state, envelope["principal"], command, now)
        if problems:
            code = problems[0].split(":", 1)[0]
            raise MembershipRefused(code if code in REFUSALS else "policy_refused", "; ".join(x.split(": ", 1)[1] if x.split(":", 1)[0] in REFUSALS else x for x in problems))
    stored = dict(command, nonce=envelope["nonce"], principal=envelope["principal"])
    stored["parameters"] = _stored_parameters(command, envelope, now)
    # Expected versions from the snapshot the checks ran against: a revocation, role change or
    # supersession committed since then moves a version and the store refuses this commit.
    stored["expected_versions"] = {eid: state["entities"].get(eid, {}).get("version", 0) for eid in touched_entities(stored, state["entities"])}
    try:
        result = store.execute(conn, stored, journal_signer[0], journal_signer[1], authority.get("authority_generation", 1), committed_at=committed_at)
    except store.StoreRefused as e:
        raise MembershipRefused("store_refused", "%s: %s" % (e.code, e.detail))
    return result


def _stored_parameters(command, envelope, now):
    """The parameters as committed: the caller's plus the attribution the authority adds (who
    enrolled or granted, and when an enrollment took effect, which also revokes prior keys)."""
    p = dict(command.get("parameters") or {})
    if command.get("operation") == "enroll_principal":
        p.update(enrolled_by=envelope.get("principal"), enrolled_at=now)
    if command.get("operation") in ("grant_delegation", "supersede_delegation"):
        p["granted_by"] = envelope.get("principal")
    return p


def expected_versions_for(store, conn, command):
    """The expected_versions of an administrative command from the committed state, for a caller
    that wants to see them: admit() derives its own from the snapshot it checked and ignores the
    caller's (they are not a signed field)."""
    ents = store.materialized_state(conn)["entities"]
    return {eid: ents.get(eid, {}).get("version", 0) for eid in touched_entities(command, ents)}


# ---------------------------------------------------------------------------------------------
# Delegated use (R38): every predicate, conjunctively, against the committed delegation.
# ---------------------------------------------------------------------------------------------

def delegated_use_problems(state, envelope, assertion, requirement, now):
    """Why an assertion made under a delegation may NOT be used: the envelope's delegation version
    is not the store's current one (a delegation cached across its committed supersession is
    stale); the delegation does not resolve for the principal, is superseded, revoked or expired;
    the channel, assertion kind, request version or scope is outside it; the principal is not an
    active member; and the boundary's role, named-principal, actor-kind, quorum and independence
    predicates (through the authority contract) are not all met."""
    problems = []
    if envelope.get("delegation_version") != state["delegation_version"]:
        problems.append("stale_delegation: envelope delegation_version %r is not the current %r" % (envelope.get("delegation_version"), state["delegation_version"]))
    d = next((x for x in state["delegations"] if x["id"] == envelope.get("delegation_id") and x.get("principal") == envelope.get("principal")), None)
    if d is None:
        problems.append("delegation_refused: delegation %r does not resolve for %r" % (envelope.get("delegation_id"), envelope.get("principal")))
        return problems
    if d.get("superseded_by") is not None:
        problems.append("stale_delegation: delegation %s was superseded by %s" % (d["id"], d["superseded_by"]))
    if d.get("revoked_at") is not None and d["revoked_at"] <= now:
        problems.append("delegation_refused: delegation %s is revoked" % d["id"])
    if not _is_num(d.get("expires_at")) or d["expires_at"] <= now:
        problems.append("delegation_refused: delegation %s is expired or has no expiry" % d["id"])
    if assertion.get("channel") != d.get("channel"):
        problems.append("delegation_refused: channel %r is not the delegation's %r" % (assertion.get("channel"), d.get("channel")))
    if assertion.get("assertion_kind") not in (d.get("assertion_kinds") or []):
        problems.append("delegation_refused: assertion kind %r is not permitted by the delegation" % assertion.get("assertion_kind"))
    if assertion.get("request_version") != d.get("request_version"):
        problems.append("delegation_refused: request version %r is not the delegation's %r" % (assertion.get("request_version"), d.get("request_version")))
    if assertion.get("presentation_version") != d.get("presentation_version"):
        problems.append("delegation_refused: presentation version %r is not the delegation's %r: an assertion about another presentation" % (assertion.get("presentation_version"), d.get("presentation_version")))
    if assertion.get("principal", envelope.get("principal")) != envelope.get("principal"):
        problems.append("delegation_refused: the assertion names principal %r, the envelope %r" % (assertion.get("principal"), envelope.get("principal")))
    if assertion.get("edge_key_id", d.get("edge_key_id")) != d.get("edge_key_id"):
        problems.append("delegation_refused: edge key %r is not the delegation's %r" % (assertion.get("edge_key_id"), d.get("edge_key_id")))
    scope = requirement.get("scope")
    if scope is not None and "*" not in (d.get("authority_scope") or []) and scope not in (d.get("authority_scope") or []):
        problems.append("delegation_refused: the delegation's authority_scope %s does not cover %r" % (d.get("authority_scope"), scope))
    ok, why = AC.active_member(_member(state, envelope.get("principal")), now)
    if not ok:
        problems.append("delegation_refused: principal %r: %s" % (envelope.get("principal"), why))
    authorized, refusals = AC.authorize(requirement.get("boundary", "decision_settlement"), requirement,
                                        [{"principal": envelope.get("principal"), "subject_digest": requirement.get("subject_digest")}], state["membership"], now)
    if not authorized:
        problems.extend("delegation_refused: %s" % r for r in refusals)
    return problems
