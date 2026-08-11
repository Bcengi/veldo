#!/usr/bin/env python3
"""VELDO two-key rule (veldo.two_key/v1): the SECOND KEY PATH on top of the execution organ, the
gate through which an IRREVERSIBLE or DATA-MUTATING remediation may finally execute. This is the W7
organ of PLAN-0012 and the sharpest edge of Invention #3's design center: an agent with production
access can destroy a company by doing the wrong thing there, so the dangerous rung is not one key
but TWO, held by two parties, and one mind - even a good one - does not touch data alone.

WHAT W6 LEFT OPEN, AND WHAT THIS CLOSES. The execution organ (.veldo/action_executor.py, W6) executes
only the strictly reversible, non-data-mutating case at L2 behind a single human confirmation, and it
REFUSES anything irreversible or data-mutating (requires_two_key), because the two keys were not yet
built. This module builds them. For any action classed irreversible or data-mutating (or a remedy
whose required_authorization is two_key), execution requires BOTH keys, each BOUND TO THE PROPOSAL
DIGEST (never command text, C4):

  KEY 1 - a recorded HUMAN AUTHORIZATION (the veldo.approval-style record extended to remediation):
  a human decides "approved" and the record binds to the exact proposal_digest it authorizes. A
  MACHINE-authored key 1 refuses (key 1 is a human; no self-authorization, NG4).

  KEY 2 - an INDEPENDENT FRESH-CONTEXT CONFIRMATION (the veldo.verdict-style review pattern extended
  to remediation): a fresh context that did NOT propose the remedy confirms two things - that the
  DIAGNOSIS SUPPORTS THE ACTION and that the ACTION DOES ONLY WHAT IT CLAIMS - and the verdict binds
  to the same proposal_digest. A SELF-authored key 2 refuses (the confirmer cannot be the
  proposer/producer, the executor, or the human authorizer; a responder or executor organ identity is
  by definition not independent, NG4 - the independent-review self-separation extended to remediation).

EITHER KEY ALONE REFUSES (fail closed, degrade DOWN never up, C3): a human authorization without the
independent confirmation refuses; an independent confirmation without the human authorization refuses;
both present but bound to a DIFFERENT proposal digest (a foreign or stale key) refuse; an expired key -
or one whose declared expiry cannot be verified because no clock was supplied (WARP-1212) - refuses; a
key naming a foreign incident refuses. Both keys present, granting, unexpired,
self-separated, and bound to the SAME proposal digest AUTHORIZE the execution, and only then does the
executor run the action against the FAKE system (NG1). The refusals ARE the product (C1): every guard
that does not pass returns a NAMED reason from the closed taxonomy below, so a two-key refusal is
diagnosable from the result alone (the stranger question - every future responder is a stranger to the
code).

RISK: this organ OPENS the irreversible/data-mutating execution path (behind the two keys), so per C2
"data-mutating execution paths carry the CRITICAL tier": WARP-1207 is CRITICAL (two independent reviews
plus a recorded founder approval to land), where W6 was HIGH precisely because it built NO such path.

SEPARATION AND REUSE (C4/C6, no second parser, no second gate, ONE truth for the binding). This module
is a PURE gate over already-parsed records: it computes no digest and parses no file - the executor
computes the proposal digest with W6's proposal_digest (the ONE canonical binding, imported here only
in the standalone demo so the CLI reuses it too) and PASSES it in, and the executor re-validates the
proposal through W1 and resolves the action through W5 before it ever reaches this gate. The keys are
plain records the caller supplies; the gate binds them to the passed digest and decides. It holds no
credential, opens no connection, runs nothing against any live system, and starts no process, thread,
or timer (NG3, no-detach): dependency free by construction (pathlib and json at module top for the
standalone demo only; importlib LAZILY in the demo).

HONEST DEFERRALS (the plan's ordered delivery, not a dodge): the compressed loop and reconciliation
that would DRIVE an incident through this gate are WARP-1208 (W8); the support metrics are WARP-1210
(W10); landing a check into validate.py run_all and the init lay-down are WARP-1211 (W11). Nothing here
pretends those later organs are built. Live target wiring remains a separate per-system human-approved
enablement act (NG1); this gate authorizes execution against fake systems only.
"""
from pathlib import Path
import json

SCHEMA = "veldo.two_key/v1"

# The two keys reuse existing VELDO record shapes, extended to bind to a PROPOSAL DIGEST rather than a
# commit: KEY 1 is a veldo.approval-style human authorization; KEY 2 is a veldo.verdict-style independent
# fresh-context confirmation. The gate reads the fields it needs and never a raw credential or command.
SCHEMA_AUTHORIZATION = "veldo.approval/v1"
SCHEMA_CONFIRMATION = "veldo.verdict/v1"

# KEY 1 grants when a HUMAN decides approved (the veldo.approval decision vocabulary).
APPROVE_DECISION = "approved"
# KEY 2 confirms when the fresh-context verdict passes (the veldo.verdict vocabulary) AND both
# remediation attestations are true. A "fail" or "escalate" verdict does not confirm.
CONFIRM_VERDICTS = frozenset({"pass", "pass_with_notes"})

# Machine actors that may NEVER stand in for the HUMAN authorization (KEY 1): key 1 is a human, so a
# machine-authored authorization refuses (NG4). Mirrors action_executor.MACHINE_ACTORS; a selftest
# binds the two so they cannot drift.
MACHINE_ACTORS = frozenset({
    "veldo-executor", "veldo-responder", "executor", "responder", "machine",
    "agent", "bot", "ava", "automation",
})

# Organ / automation identities that can NEVER be the INDEPENDENT confirmer (KEY 2): the responder that
# proposes and the executor that runs are, by definition, not an independent fresh context. A confirmer
# in this set is not independent (NG4). A legitimate confirmer is a distinct fresh-context reviewer or a
# second human, never the proposing/executing organ.
NON_INDEPENDENT_ACTORS = frozenset({
    "veldo-executor", "veldo-responder", "executor", "responder", "machine", "automation",
})

# The required_authorization value on a remedy that must take two keys (mirrors incident.AUTHORIZATIONS).
TWO_KEY_AUTHORIZATION = "two_key"

# THE NAMED REFUSAL TAXONOMY (C1/C3): the refusals are the product. Every guard that does not pass
# returns one of these, so the failure mode is legible from the result rather than inferred. Both keys
# absent returns REQUIRES_TWO_KEY, the exact value the W6 fence used, so the executor's pre-two-key
# behavior is preserved byte-for-byte (a selftest binds this value to action_executor.REFUSE_REQUIRES_TWO_KEY).
REQUIRES_TWO_KEY = "requires_two_key"                                # both keys absent
MISSING_HUMAN_AUTHORIZATION = "missing_human_authorization"          # confirmation present, authorization absent
MISSING_INDEPENDENT_CONFIRMATION = "missing_independent_confirmation"  # authorization present, confirmation absent
AUTHORIZATION_NOT_GRANTED = "authorization_not_granted"              # KEY 1 decision is not approved / names no approver
CONFIRMATION_NOT_GRANTED = "confirmation_not_granted"                # KEY 2 verdict not confirming / an attestation is not true / no confirmer
SELF_AUTHORIZATION = "self_authorization_refused"                    # KEY 1 machine-authored, or authorizer is the executor
CONFIRMATION_NOT_INDEPENDENT = "confirmation_not_independent"        # KEY 2 confirmer is the proposer/executor/authorizer/organ
FOREIGN_AUTHORIZATION = "foreign_authorization"                      # KEY 1 bound to a different digest / foreign incident
FOREIGN_CONFIRMATION = "foreign_confirmation"                        # KEY 2 bound to a different digest / foreign incident
AUTHORIZATION_EXPIRED = "authorization_expired"                      # KEY 1 expired, declares no expiry, or unverifiable (no clock)
CONFIRMATION_EXPIRED = "confirmation_expired"                        # KEY 2 expired, declares no expiry, or unverifiable (no clock)


class TwoKeyError(RuntimeError):
    """The two-key gate was called malformed (a non-mapping remedy or a missing digest). Raised by name
    so a bad CALL never silently no-ops, parallel to ExecutorError. A GUARDED refusal is NOT an
    exception: it is a named (reason, detail) result, which is the product (C1)."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_bool(v):
    """The value as a real boolean, or None. The one front-matter parser leaves an unquoted true/false
    as the string "true"/"false", so a boolean field can arrive as that string; accept the string forms
    and a real bool and nothing else, the idiom the sibling organs use, so a truthy-looking value is
    never silently accepted."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


def _norm(v):
    """An identity normalized for comparison (lowercased, trimmed), so a case variant of the same party
    cannot slip past the self-separation guard. A non-string normalizes to None."""
    return v.strip().lower() if isinstance(v, str) else None


def _digest_of(key):
    """The proposal digest a key binds to, read from top-level proposal_digest OR scope.proposal_digest
    (the veldo.approval scope idiom), whichever the key carries."""
    d = key.get("proposal_digest")
    if d is None and isinstance(key.get("scope"), dict):
        d = key["scope"].get("proposal_digest")
    return d


def _incident_of(key):
    """The incident a key names, from top-level incident OR scope.incident, or None."""
    i = key.get("incident")
    if i is None and isinstance(key.get("scope"), dict):
        i = key["scope"].get("incident")
    return i


def _expired(key, now):
    """True iff the key is expired, its declared expiry cannot be VERIFIED for want of a clock, or it
    fails to declare an expiry at all (fail closed, C3). A key MUST carry an expires_at (a key with no
    expiry is treated as expired). The expiry is enforced by a lexicographic ISO compare against an
    INJECTED CLOCK (monotonic for a fixed width, the incident.py idiom - no calendar math, no
    dependency): the key is fresh ONLY when a real clock (now) proves a declared expiry lies in the
    future. With NO clock the declared expiry cannot be evaluated, so the key is treated as expired and
    REFUSES - the two-key freshness control fails CLOSED when there is no clock to verify it, never open
    (WARP-1212, hardening the WARP-1207 review finding: an expired-but-declared key must not slip past
    the freshness check just because a caller omitted the clock; a clock is required on this path)."""
    exp = key.get("expires_at")
    if not _is_str(exp):
        return True
    if not _is_str(now):
        return True  # WARP-1212: no clock to verify a declared expiry -> fail closed (refuse), never open
    return now > exp


def _confirmer_of(key):
    """The independent confirmer's identity, from confirmer OR reviewer (the veldo.verdict reviewer
    field), whichever the key carries."""
    c = key.get("confirmer")
    if c is None:
        c = key.get("reviewer")
    return c


def authorize(remedy, digest, human_authorization, independent_confirmation,
              executor_actor=None, now=None):
    """THE TWO-KEY GATE. Decide whether an irreversible or data-mutating remediation may execute.
    Returns (reason, detail): (None, detail) when BOTH keys authorize the exact proposal; a NAMED reason
    from the taxonomy above otherwise (fail closed, C3). Pure over already-parsed records - it computes
    no digest and parses no file (the executor computes the digest with W6's proposal_digest and passes
    it in, so the binding has ONE truth) and it never sees command text (C4).

    Both keys bind to `digest`. KEY 1 (human_authorization) must decide approved, name a HUMAN approver
    (a machine-authored key 1 refuses, NG4), bind to the digest, name no foreign incident, and be
    unexpired. KEY 2 (independent_confirmation) must carry a confirming verdict AND attest both that the
    diagnosis supports the action and that the action does only what it claims, name a confirmer, bind to
    the digest, name no foreign incident, and be unexpired. SELF-SEPARATION (NG4): the confirmer cannot
    be an executor/responder organ identity, the human authorizer, the executor's own actor, or the
    remedy's declared proposer (a self-authored confirmation refuses); the human authorizer cannot be the
    executor's own actor. EITHER KEY ALONE REFUSES."""
    if not isinstance(remedy, dict):
        raise TwoKeyError("the two-key gate needs a remedy record (mapping) to bind the keys to")
    if not _is_str(digest):
        raise TwoKeyError("the two-key gate needs the proposal digest (computed with W6's proposal_digest)")

    have_h = isinstance(human_authorization, dict)
    have_c = isinstance(independent_confirmation, dict)
    if not have_h and not have_c:
        return REQUIRES_TWO_KEY, (
            "execution of an irreversible or data-mutating action requires TWO keys bound to the "
            "proposal digest: a recorded human authorization AND an independent fresh-context "
            "confirmation (WARP-1207). Neither was supplied; a single confirmation cannot stand in.")
    if not have_h:
        return MISSING_HUMAN_AUTHORIZATION, (
            "the independent confirmation is present but the recorded HUMAN AUTHORIZATION is missing: "
            "EITHER key alone refuses (fail closed, C3)")
    if not have_c:
        return MISSING_INDEPENDENT_CONFIRMATION, (
            "the human authorization is present but the INDEPENDENT FRESH-CONTEXT CONFIRMATION is "
            "missing: EITHER key alone refuses (fail closed, C3)")

    # --- KEY 1: the recorded human authorization (veldo.approval-style, bound to the digest) ---------
    if human_authorization.get("decision") != APPROVE_DECISION:
        return AUTHORIZATION_NOT_GRANTED, (
            "the human authorization decision is %r, not %r: an ungranted authorization does not "
            "execute" % (human_authorization.get("decision"), APPROVE_DECISION))
    approver = human_authorization.get("approver")
    if not _is_str(approver):
        return AUTHORIZATION_NOT_GRANTED, "the human authorization names no approver (KEY 1 is a human decision)"
    if _norm(approver) in MACHINE_ACTORS:
        return SELF_AUTHORIZATION, (
            "the human authorization is authored by a MACHINE actor (%r): KEY 1 must be a human, so no "
            "self-authorization (NG4)" % approver)
    if _digest_of(human_authorization) != digest:
        return FOREIGN_AUTHORIZATION, (
            "the human authorization is bound to proposal digest %r but this proposal is %r: a key binds "
            "to the EXACT proposal; a foreign or stale key refuses (C3)" % (_digest_of(human_authorization), digest))
    h_inc = _incident_of(human_authorization)
    if h_inc is not None and h_inc != remedy.get("incident"):
        return FOREIGN_AUTHORIZATION, (
            "the human authorization names incident %r but the proposal remediates %r (foreign)"
            % (h_inc, remedy.get("incident")))
    if _expired(human_authorization, now):
        return AUTHORIZATION_EXPIRED, (
            "the human authorization is expired, declares no expiry, or its declared expiry cannot be "
            "verified because no clock was supplied on the two-key path (fail closed, C3; WARP-1212)")

    # --- KEY 2: the independent fresh-context confirmation (veldo.verdict-style, bound to the digest) -
    if independent_confirmation.get("verdict") not in CONFIRM_VERDICTS:
        return CONFIRMATION_NOT_GRANTED, (
            "the confirmation verdict is %r, not a confirming verdict (%s): an unconfirmed diagnosis "
            "does not execute" % (independent_confirmation.get("verdict"), sorted(CONFIRM_VERDICTS)))
    if _as_bool(independent_confirmation.get("diagnosis_supports_action")) is not True:
        return CONFIRMATION_NOT_GRANTED, (
            "the confirmation does not attest diagnosis_supports_action true: the confirmer must confirm "
            "the DIAGNOSIS SUPPORTS THE ACTION (the review pattern extended to remediation)")
    if _as_bool(independent_confirmation.get("action_does_only_what_it_claims")) is not True:
        return CONFIRMATION_NOT_GRANTED, (
            "the confirmation does not attest action_does_only_what_it_claims true: the confirmer must "
            "confirm the ACTION DOES ONLY WHAT IT CLAIMS")
    confirmer = _confirmer_of(independent_confirmation)
    if not _is_str(confirmer):
        return CONFIRMATION_NOT_GRANTED, "the confirmation names no confirmer (an independent fresh context)"
    if _digest_of(independent_confirmation) != digest:
        return FOREIGN_CONFIRMATION, (
            "the confirmation is bound to proposal digest %r but this proposal is %r: a foreign or stale "
            "confirmation refuses (C3)" % (_digest_of(independent_confirmation), digest))
    c_inc = _incident_of(independent_confirmation)
    if c_inc is not None and c_inc != remedy.get("incident"):
        return FOREIGN_CONFIRMATION, (
            "the confirmation names incident %r but the proposal remediates %r (foreign)"
            % (c_inc, remedy.get("incident")))
    if _expired(independent_confirmation, now):
        return CONFIRMATION_EXPIRED, (
            "the confirmation is expired, declares no expiry, or its declared expiry cannot be verified "
            "because no clock was supplied on the two-key path (fail closed, C3; WARP-1212)")

    # --- SELF-SEPARATION (NG4): the two keys are TWO PARTIES, and KEY 2 is INDEPENDENT of the proposer,
    #     the executor, and the human authorizer. The confirmer cannot be the proposer/producer (a
    #     self-authored confirmation), an executor/responder organ, the executor's actor, or KEY 1's
    #     approver; and the human authorizer cannot be the executor's own actor. ---------------------
    cf = _norm(confirmer)
    if cf in NON_INDEPENDENT_ACTORS:
        return CONFIRMATION_NOT_INDEPENDENT, (
            "the confirmer %r is an executor/responder organ identity, not an independent fresh context "
            "(NG4)" % confirmer)
    if cf == _norm(approver):
        return CONFIRMATION_NOT_INDEPENDENT, (
            "the confirmer is the SAME party as the human authorizer (%r): the two keys are two parties "
            "(NG4)" % confirmer)
    if executor_actor is not None and cf == _norm(executor_actor):
        return CONFIRMATION_NOT_INDEPENDENT, (
            "the confirmer is the executor's own actor (%r): the executor never confirms its own "
            "execution (NG4)" % confirmer)
    proposer = remedy.get("proposed_by")
    if _is_str(proposer) and cf == _norm(proposer):
        return CONFIRMATION_NOT_INDEPENDENT, (
            "the confirmer is the PROPOSER of this remedy (%r): a self-authored confirmation refuses - "
            "the confirmer cannot be the proposer/producer (NG4, the independent-review self-separation "
            "extended to remediation)" % confirmer)
    if executor_actor is not None and _norm(approver) == _norm(executor_actor):
        return SELF_AUTHORIZATION, (
            "the human authorizer is the executor's own actor (%r): the executor never authorizes its "
            "own execution (NG4)" % approver)

    return None, (
        "both keys are present, granting, unexpired, self-separated, and bound to the proposal digest "
        "%s: the two-key rule is satisfied (KEY 1 human authorization %r, KEY 2 independent confirmation "
        "%r)" % (digest, approver, confirmer))


def authorized(remedy, digest, human_authorization, independent_confirmation,
               executor_actor=None, now=None):
    """Convenience predicate: True iff authorize returns no refusal reason. The executor uses authorize
    directly (it needs the named reason to fail closed); this is for a caller that only wants the boolean."""
    reason, _ = authorize(remedy, digest, human_authorization, independent_confirmation,
                          executor_actor=executor_actor, now=now)
    return reason is None


def _cli(argv):
    """Standalone runner: build a demo data-mutating remedy and the TWO keys, compute the proposal
    digest with W6's proposal_digest (reused, ONE truth), and print the gate result. With --one-key it
    drops the independent confirmation and honestly REFUSES (either key alone refuses). Offline, no live
    system, no process (NG3); importlib LAZILY here only. Landing a gate check into validate.py run_all
    and the init lay-down is WARP-1211 (W11)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    aspec = importlib.util.spec_from_file_location("veldo_action_executor_twokey", here / "action_executor.py")
    AE = importlib.util.module_from_spec(aspec)
    aspec.loader.exec_module(AE)

    remedy = {
        "schema": "veldo.remedy/v1", "id": "REM-DEMO", "incident": "INC-DEMO",
        "status": "proposed", "diagnosis": "the demo change mutates persistent data and must take two keys",
        "proposed_by": "responder-fresh-context",
        "proposed_action": {"action": "purge_stale_rows", "parameters": {"table": "sessions"}},
        "risk_class": "critical", "autonomy_level": "L2",
        "reversibility": {"class": "irreversible", "analysis": "a purge cannot be undone", "data_mutating": True},
        "rollback": "restore from the pre-purge snapshot", "required_authorization": TWO_KEY_AUTHORIZATION,
    }
    digest = AE.proposal_digest(remedy)
    human = {"schema": SCHEMA_AUTHORIZATION, "decision": APPROVE_DECISION, "approver": "operator",
             "proposal_digest": digest, "incident": "INC-DEMO",
             "recorded_at": "2026-07-23T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z"}
    conf = {"schema": SCHEMA_CONFIRMATION, "verdict": "pass", "confirmer": "independent-reviewer",
            "diagnosis_supports_action": True, "action_does_only_what_it_claims": True,
            "proposal_digest": digest, "incident": "INC-DEMO",
            "confirmed_at": "2026-07-23T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z"}
    if len(argv) > 1 and argv[1] == "--one-key":
        conf = None
    reason, detail = authorize(remedy, digest, human, conf,
                               executor_actor="operator-executor", now="2026-07-23T12:00:00Z")
    print("veldo two-key rule (%s): %s" % (SCHEMA, "AUTHORIZED" if reason is None else "REFUSED (%s)" % reason))
    print(json.dumps({"authorized": reason is None, "reason": reason, "detail": detail,
                      "proposal_digest": digest}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(_cli(sys.argv))
    except TwoKeyError as e:
        print("veldo two-key rule: %s" % e)
        sys.exit(1)
