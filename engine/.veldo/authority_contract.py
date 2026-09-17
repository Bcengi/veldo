#!/usr/bin/env python3
"""Signing and authority contracts for enrolled channels (PLAN-0019 W5, VELDO-0020).

WHAT THIS MODULE IS. Pure predicates over plain data, plus one seam to the operating system's
OpenSSH tooling: the principal types, scoped membership and the conjunctive role, quorum,
named-principal and independence requirements at every authorization boundary (R36, R37, R39,
AC1); the OpenSSH-envelope Ed25519 command signature that binds the complete request and the
active delegation, verified by recomputing the canonical command digest from the command to be
executed and never trusting transport (R36, R38, AC2); the restricted edge key and
presentation-bound canonical attribution every enrolled channel needs (R38, R60, R72, AC3); and
the single settlement of one request version in Veldo with originating-channel attribution, a
quorum counted by distinct principal and one atomic result (R40, R41, R72, AC4). Standard
library only. Signature verification shells out to `ssh-keygen -Y verify` (the installed OpenSSH,
not a Python dependency), through a seam a fixture can replace; nothing else runs anything.

WHAT IT REUSES. The machine-actor set mirrors authorization.MACHINE_ACTORS (the suite binds them);
the canonical digest shape is request.request_digest's (sha256 over a sorted JSON of the substance).
Nothing here enrolls a principal, holds a private key or activates a channel: enrollment is Dmitry's
act through the bootstrap command (R37), and activation is Package E's.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.authority_contract/v1"


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


MACHINE_ACTORS = frozenset({"veldo-executor", "veldo-responder", "executor", "responder", "machine",
                            "agent", "bot", "ava", "automation", "service", "service_account", "service-account"})

# ---------------------------------------------------------------------------------------------
# AC1: principal types, scoped membership, conjunctive requirements at every boundary.
# ---------------------------------------------------------------------------------------------

PRINCIPAL_TYPES = ("person", "service", "policy", "agent_run")
# The scoped roles R37 names. Dmitry is the only enrolled named authority; every other name is
# enrolled by him through the bootstrap command, never invented here.
ROLES = ("membership_steward", "project_owner", "admission_authority", "priority_authority",
         "technical_authority", "security_authority", "operations_authority")
# The boundaries R39 rechecks authorization at, and which principal types may act at each.
BOUNDARIES = {
    "command_acceptance": ("person", "service"),
    "proposal_commit": ("person", "service", "agent_run"),
    "assignment_acceptance": ("person", "agent_run"),
    "claim": ("agent_run", "service"),
    "dispatch_acceptance": ("service",),
    "privileged_tool_use": ("service",),
    "result_acceptance": ("person", "service"),
    "decision_settlement": ("person", "policy"),
    "landing_publication": ("service",),
}
REFUSALS = ("unknown_boundary", "unknown_principal", "principal_type_not_admitted", "membership_revoked",
            "membership_expired", "role_not_satisfied", "named_principal_not_satisfied", "quorum_not_met",
            "independence_not_met", "requirement_expired", "attestation_stale")


def membership_entry(membership, principal):
    for m in membership or []:
        if isinstance(m, dict) and m.get("principal") == principal:
            return m
    return None


def active_member(entry, now):
    """(active, refusal): a membership entry is active when it exists, is not revoked at `now`
    and has not expired. Revocation blocks new operations the moment it is recorded (R39)."""
    if entry is None:
        return False, "unknown_principal"
    if entry.get("revoked_at") is not None and entry["revoked_at"] <= now:
        return False, "membership_revoked"
    if entry.get("expires_at") is not None and entry["expires_at"] <= now:
        return False, "membership_expired"
    if entry.get("principal_type") not in PRINCIPAL_TYPES:
        return False, "unknown_principal"
    return True, None


def authorize(boundary, requirement, attestations, membership, now):
    """(authorized, refusals): whether the attestations satisfy `requirement` at `boundary`
    (R36, R37, R39). Every requirement is CONJUNCTIVE: the boundary admits the attester's
    principal type; each attester is an active member; every required role is held by at least
    one valid attester; every named principal has attested in person (a named-person predicate
    is satisfied by that person's own attestation and by nothing else: never an agent, a service,
    a display name or a delegate); at least `quorum` DISTINCT principals attested; at least
    `min_independence` distinct independence groups are represented; the requirement has not
    expired; and no attestation is stale (bound to another subject digest). Refusals are named,
    all of them, so a reader sees every unmet condition at once."""
    refusals = []
    admitted = BOUNDARIES.get(boundary)
    if admitted is None:
        return False, ["unknown_boundary"]
    if requirement.get("expires_at") is not None and now > requirement["expires_at"]:
        refusals.append("requirement_expired")
    valid = []
    for a in attestations or []:
        if not isinstance(a, dict):
            continue
        entry = membership_entry(membership, a.get("principal"))
        ok, why = active_member(entry, now)
        if not ok:
            refusals.append("%s:%s" % (why, a.get("principal")))
            continue
        if entry["principal_type"] not in admitted:
            refusals.append("principal_type_not_admitted:%s" % a.get("principal"))
            continue
        if requirement.get("subject_digest") is not None and a.get("subject_digest") != requirement["subject_digest"]:
            refusals.append("attestation_stale:%s" % a.get("principal"))
            continue
        valid.append((a, entry))
    held_roles = {r for _a, e in valid for r in (e.get("roles") or [])}
    for role in requirement.get("roles") or []:
        if role not in held_roles:
            refusals.append("role_not_satisfied:%s" % role)
    for name in requirement.get("named_principals") or []:
        if not any(a.get("principal") == name and e.get("principal_type") == "person" for a, e in valid):
            refusals.append("named_principal_not_satisfied:%s" % name)
    principals = {a.get("principal") for a, _e in valid}
    if len(principals) < int(requirement.get("quorum") or 1):
        refusals.append("quorum_not_met:%d<%d" % (len(principals), int(requirement.get("quorum") or 1)))
    groups = {e.get("independence_group") for _a, e in valid if e.get("independence_group")}
    if len(groups) < int(requirement.get("min_independence") or 0):
        refusals.append("independence_not_met:%d<%d" % (len(groups), int(requirement.get("min_independence") or 0)))
    return (not refusals), refusals


# ---------------------------------------------------------------------------------------------
# AC2: the signed command envelope and the key lifecycle.
# ---------------------------------------------------------------------------------------------

ENVELOPE_SCHEMA = "veldo.command_envelope/v1"
# Every field the envelope binds (R36). The canonical command digest covers the operation, the
# target and the COMPLETE parameters, an enrollment public key included.
ENVELOPE_FIELDS = ("schema", "domain_uuid", "repository_uuid", "store_uuid", "command_id", "request_revision",
                   "nonce", "expires_at", "membership_version", "delegation_version", "principal", "command_digest")
COMMAND_FIELDS = ("operation", "target", "parameters")
SIGNATURE_NAMESPACE = "veldo-command"


def canonical_command_digest(command):
    """The one canonical digest of a command to be executed: sha256 over the sorted JSON of its
    operation, target and complete parameters. Any other encoding is a second spelling."""
    payload = {k: command.get(k) for k in COMMAND_FIELDS}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


def canonical_envelope_bytes(envelope):
    """The bytes the signature covers: the sorted JSON of every envelope field, so a signer and a
    verifier on different hosts agree on what was signed."""
    payload = {k: envelope.get(k) for k in ENVELOPE_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def active_key(keyring, principal, at):
    """The verification key of `principal` active at `at`, or None: effective at or before `at`,
    not retired and not revoked at `at`. Retired keys are preserved (R38) and never verify a new
    command; the times are recorded on the entry."""
    for k in keyring or []:
        if not isinstance(k, dict) or k.get("principal") != principal:
            continue
        if k.get("effective_at") is not None and k["effective_at"] > at:
            continue
        if k.get("retired_at") is not None and k["retired_at"] <= at:
            continue
        if k.get("revoked_at") is not None and k["revoked_at"] <= at:
            continue
        return k
    return None


def envelope_problems(envelope, command, authority, now, seen_nonces, keyring, membership, delegations=None):
    """Why a signed command may NOT execute, by name (R36, R38): a missing envelope field; a
    digest that does not equal the canonical digest RECOMPUTED from the command to be executed
    (so a substituted parameter, an enrollment public key among them, refuses before execution);
    a domain, repository or store other than this authority's; a replayed nonce; an expired
    envelope; a membership or delegation version behind the authority's current one; a principal
    with no active membership or no active verification key at `now`. The signature itself is
    checked by verify_signature; this function is the everything-else, and it refuses first."""
    problems = []
    for f in ENVELOPE_FIELDS:
        if f not in (envelope or {}):
            problems.append("envelope lacks %s" % f)
    if problems:
        return problems
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        problems.append("envelope schema %r is not %s" % (envelope.get("schema"), ENVELOPE_SCHEMA))
    if envelope["command_digest"] != canonical_command_digest(command):
        problems.append("envelope digest %s does not match the canonical digest of the command to be executed %s: refused "
                        "before execution (R36)" % (envelope["command_digest"], canonical_command_digest(command)))
    for f in ("domain_uuid", "repository_uuid", "store_uuid"):
        if envelope.get(f) != authority.get(f):
            problems.append("envelope %s %r is not this authority's %r (wrong repository, domain or store)" % (f, envelope.get(f), authority.get(f)))
    if envelope["nonce"] in (seen_nonces or set()):
        problems.append("nonce %r was already consumed: a replayed command is refused" % envelope["nonce"])
    if envelope["expires_at"] <= now:
        problems.append("envelope expired at %r" % envelope["expires_at"])
    for f in ("membership_version", "delegation_version"):
        if envelope.get(f) != authority.get(f):
            problems.append("envelope %s %r is not the authority's current %r: a command signed against stale membership or delegation "
                            "is refused" % (f, envelope.get(f), authority.get(f)))
    ok, why = active_member(membership_entry(membership, envelope["principal"]), now)
    if not ok:
        problems.append("principal %r: %s" % (envelope["principal"], why))
    if active_key(keyring, envelope["principal"], now) is None:
        problems.append("principal %r has no active verification key at %r (retired, revoked or not yet effective)" % (envelope["principal"], now))
    return problems


def ssh_keygen_verify(message, signature, allowed_signers_text, principal, namespace=SIGNATURE_NAMESPACE):
    """The default signature verifier: `ssh-keygen -Y verify` over the installed OpenSSH, with the
    allowed_signers content and the signature written to a private temporary directory. Returns
    (verified, detail). No Python dependency, no key material of our own: OpenSSH does the
    cryptography, this function only asks the question."""
    with tempfile.TemporaryDirectory(prefix="veldo-verify") as d:
        signers = Path(d) / "allowed_signers"
        sig = Path(d) / "message.sig"
        signers.write_text(allowed_signers_text)
        sig.write_text(signature)
        try:
            r = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", principal, "-n", namespace, "-s", str(sig)],
                               input=message, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, "ssh-keygen unavailable or timed out: %s" % e
        return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace").strip()


def allowed_signers_line(principal, public_key, namespace=SIGNATURE_NAMESPACE):
    """One .veldo/keys/allowed_signers line binding a principal to a verification key for the
    command namespace. `public_key` is the OpenSSH public key text (type and base64)."""
    return '%s namespaces="%s" %s' % (principal, namespace, " ".join(public_key.split()[:2]))


def verify_signed_command(envelope, command, signature, authority, now, seen_nonces, keyring, membership, verifier=None):
    """(accepted, problems): the whole check for one signed command. envelope_problems first (a
    malformed or mismatched envelope is refused before any cryptography), then the signature over
    the canonical envelope bytes against the principal's ACTIVE key at `now` (never a retired key,
    never a key from a worker's branch: the key comes from the keyring the authority holds). SSH
    transport authentication is not consulted: only the command's own signature counts."""
    problems = envelope_problems(envelope, command, authority, now, seen_nonces, keyring, membership)
    if problems:
        return False, problems
    key = active_key(keyring, envelope["principal"], now)
    verify = verifier if verifier is not None else ssh_keygen_verify
    ok, detail = verify(canonical_envelope_bytes(envelope), signature, allowed_signers_line(envelope["principal"], key["public_key"]), envelope["principal"])
    if not ok:
        return False, ["signature does not verify for %s with the active key: %s" % (envelope["principal"], detail)]
    return True, []


# ---------------------------------------------------------------------------------------------
# AC3: enrolled channels, restricted edge keys, presentation-bound canonical attribution.
# ---------------------------------------------------------------------------------------------

# The channel registry (R38, R60, R72): what canonical evidence each edge must pull from its
# platform, and whether the channel is enrolled. Email stays unenrolled until its attribution is
# qualified; an assertion from an unenrolled channel refuses.
CHANNELS = {
    "telegram_chat": {"enrolled": True, "edge_key_id": "edge-telegram",
                      "attribution": ("platform_message_id", "sender_id", "platform_timestamp")},
    "jira": {"enrolled": True, "edge_key_id": "edge-jira",
             "attribution": ("issue_key", "changelog_id", "account_id", "changelog_timestamp")},
    "signed_cli": {"enrolled": True, "edge_key_id": "edge-cli",
                   "attribution": ("personal_envelope_verified", "command_id", "signed_at")},
    "email": {"enrolled": False, "edge_key_id": "edge-email",
              "attribution": ("message_id", "sender_address", "dkim_verified", "received_at")},
}
DELEGATION_FIELDS = ("principal", "channel", "assertion_kinds", "authority_scope", "request_version",
                     "presentation_version", "expires_at", "edge_key_id")
ASSERTION_KINDS = ("decision_answer", "assignment_acceptance", "review_disposition", "acknowledgement")
# Fields that are TEXT, not evidence: their presence never substitutes for attribution.
TEXT_ONLY_FIELDS = ("text", "display_name", "sender_name")


def edge_assertion_problems(assertion, delegation, now, channels=None):
    """Why a channel edge's assertion is NOT accepted, by name (R38, R72): the channel is unknown or
    not enrolled; the delegation lacks a field, is expired, or binds another principal, channel,
    assertion kind, request version or presentation version than the assertion carries; the edge
    signed with a key that is not this channel's restricted key (an edge never signs for another
    channel); a required attribution field pulled from the platform is missing (message text, a
    display name or a sender name substitutes for nothing); the assertion names no presentation."""
    channels = channels or CHANNELS
    problems = []
    ch = channels.get(assertion.get("channel"))
    if ch is None:
        return ["channel %r is not a registered channel" % (assertion.get("channel"),)]
    for f in DELEGATION_FIELDS:
        if f not in (delegation or {}):
            problems.append("delegation lacks %s" % f)
    if problems:
        return problems
    if not ch.get("enrolled"):
        problems.append("channel %s is not enrolled: its assertions refuse until enrollment and attribution are qualified" % assertion["channel"])
    if delegation["expires_at"] <= now:
        problems.append("delegation expired at %r" % delegation["expires_at"])
    for f in ("principal", "channel", "request_version", "presentation_version"):
        if delegation.get(f) != assertion.get(f):
            problems.append("delegation binds %s %r, the assertion carries %r" % (f, delegation.get(f), assertion.get(f)))
    if assertion.get("assertion_kind") not in ASSERTION_KINDS:
        problems.append("assertion kind %r is not one of %s" % (assertion.get("assertion_kind"), ASSERTION_KINDS))
    elif assertion.get("assertion_kind") not in (delegation.get("assertion_kinds") or []):
        problems.append("delegation permits %s, not %r" % (delegation.get("assertion_kinds"), assertion.get("assertion_kind")))
    if delegation.get("edge_key_id") != ch["edge_key_id"] or assertion.get("edge_key_id") != ch["edge_key_id"]:
        problems.append("the edge key is %r / %r; channel %s signs only with its own restricted key %r"
                        % (delegation.get("edge_key_id"), assertion.get("edge_key_id"), assertion["channel"], ch["edge_key_id"]))
    evidence = assertion.get("attribution") or {}
    for f in ch["attribution"]:
        if f not in evidence or evidence.get(f) in (None, "", False):
            problems.append("attribution lacks %s pulled from the platform: text, a display name or a sender name substitutes for nothing (R72)" % f)
    if not _is_str(assertion.get("presentation_id")) or not _is_str(assertion.get("presentation_digest")):
        problems.append("the assertion names no presentation (id and digest): an answer must identify the presentation it addresses")
    return problems


# ---------------------------------------------------------------------------------------------
# AC4: one settlement per request version, attributed to the originating channel.
# ---------------------------------------------------------------------------------------------

PRESENTATION_FIELDS = ("presentation_id", "request_id", "request_version", "request_digest", "subject_digests",
                       "brief_digest", "channel", "external_id", "published_at")
SETTLEMENT_REFUSALS = ("already_settled", "request_expired", "framing_changed", "stale_presentation", "unknown_presentation",
                       "presentation_channel_mismatch", "edge_refused", "principal_not_member", "revoked_key",
                       "quorum_not_met", "no_assertion")


def presentation_problems(receipt):
    return ["presentation receipt lacks %s" % f for f in PRESENTATION_FIELDS if f not in (receipt or {})]


def settle(request, assertions, delegations, presentations, membership, keyring, now, prior_settlement=None):
    """The ONE settlement transition for a request version (R40, R41, R72). Returns one atomic
    result {settled, settlement, refusals, quorum: {principals}, nonce_consumed, projection_obligations,
    decision_effects}. Refuses when the request version already has a terminal settlement, the
    request expired, or the request's framing digest is not the one every valid assertion's
    presentation carries. Each assertion must pass its edge check, name a presentation receipt
    of THIS request version on THIS channel whose digests match the request's current framing
    (a receipt for an earlier brief or a changed subject is stale), come from an active member
    whose key was not revoked, and only then counts toward the quorum BY DISTINCT PRINCIPAL:
    one person answering on two channels is one quorum member. The winner among concurrent
    valid answers is the earliest by platform timestamp, then by channel registry order, and the
    settlement is attributed to that answer's channel; every other channel receives a projection
    obligation, never a second record."""
    result = {"settled": False, "settlement": None, "refusals": [], "quorum": {"principals": []},
              "nonce_consumed": None, "projection_obligations": [], "decision_effects": []}
    if prior_settlement is not None and prior_settlement.get("request_version") == request.get("version"):
        result["refusals"].append("already_settled")
        return result
    if request.get("expires_at") is not None and now > request["expires_at"]:
        result["refusals"].append("request_expired")
        return result
    by_pid = {p.get("presentation_id"): p for p in presentations or [] if isinstance(p, dict) and not presentation_problems(p)}
    valid = []
    for a in assertions or []:
        d = next((x for x in delegations or [] if isinstance(x, dict) and x.get("principal") == a.get("principal") and x.get("channel") == a.get("channel")), None)
        edge = edge_assertion_problems(a, d, now)
        if edge:
            result["refusals"].append("edge_refused:%s:%s" % (a.get("principal"), edge[0]))
            continue
        p = by_pid.get(a.get("presentation_id"))
        if p is None:
            result["refusals"].append("unknown_presentation:%s" % a.get("presentation_id"))
            continue
        if p.get("channel") != a.get("channel"):
            result["refusals"].append("presentation_channel_mismatch:%s" % a.get("presentation_id"))
            continue
        if p.get("request_id") != request.get("id") or p.get("request_version") != request.get("version") \
                or p.get("request_digest") != request.get("framing_digest") or p.get("subject_digests") != request.get("subject_digests") \
                or a.get("presentation_digest") != p.get("brief_digest"):
            result["refusals"].append("stale_presentation:%s" % a.get("presentation_id"))
            continue
        ok, why = active_member(membership_entry(membership, a.get("principal")), now)
        if not ok:
            result["refusals"].append("principal_not_member:%s:%s" % (a.get("principal"), why))
            continue
        if active_key(keyring, a.get("principal"), now) is None:
            result["refusals"].append("revoked_key:%s" % a.get("principal"))
            continue
        valid.append(a)
    principals = sorted({a.get("principal") for a in valid})
    result["quorum"]["principals"] = principals
    if not valid:
        result["refusals"].append("no_assertion")
        return result
    if len(principals) < int(request.get("quorum") or 1):
        result["refusals"].append("quorum_not_met:%d<%d" % (len(principals), int(request.get("quorum") or 1)))
        return result
    order = list(CHANNELS)
    winner = sorted(valid, key=lambda a: (str(a.get("attribution", {}).get("platform_timestamp") or a.get("attribution", {}).get("changelog_timestamp")
                                              or a.get("attribution", {}).get("signed_at") or ""), order.index(a.get("channel"))))[0]
    settlement = {"request_id": request.get("id"), "request_version": request.get("version"), "framing_digest": request.get("framing_digest"),
                  "ruling": winner.get("ruling"), "originating_channel": winner.get("channel"), "presentation_id": winner.get("presentation_id"),
                  "principals": principals, "settled_at": now}
    result.update(settled=True, settlement=settlement, nonce_consumed=request.get("nonce"),
                  projection_obligations=[c for c in order if c != winner.get("channel") and CHANNELS[c]["enrolled"]],
                  decision_effects=[{"binding": request.get("decision_binding"), "effect": "update dependent eligibility atomically (R71)"}])
    return result
