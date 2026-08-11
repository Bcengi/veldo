#!/usr/bin/env python3
"""VELDO authorization module (veldo.authorization/v1): the matrix behind every gate in the
human-decision surface. It answers ONE question correctly - is THIS human decision authorized?
Who is allowed to approve this touchpoint at this tier, are there enough INDEPENDENT approvers,
is the approver someone other than the person (or agent) who proposed the work, did they attest
with REAL reasoning rather than a bare yes, and - for an irreversible, money, or external action -
is the frozen two-key contract satisfied. This is the W6 organ of PLAN-0016 (human decisions through
Jira). It composes on W2 (veldo.request/v1, WARP-0615) as the thing being authorized and REUSES the
shipped safety core unchanged: two_key.py (WARP-1207) for the second key, and the same policy.yaml
that policy_check.py reads. It is a sibling of decision.py / two_key.py / policy_check.py and is
distributed the same way - all eight engine copies, byte-identical.

TWO SAFETY PROPERTIES ARE LOAD BEARING.

  IT SHIPS INERT. The approver policy it reads is a human_decisions block in .veldo/policy.yaml. That
  block does NOT exist in any shipped policy.yaml, so until it is added (a separate, protected,
  human-approved edit, VEL-3) this engine authorizes NOTHING: is_authorized returns authorized=False
  for EVERY request. Shipping the engine switches nothing on. Adding the block is out of scope here,
  and this module never edits policy.yaml (it reads it read-only and writes nothing anywhere).

  IT FAILS CLOSED. An absent OR malformed policy block, a request with no id, an absent verified proposer,
  a short quorum, a faked or undeclared independence, a self-approval, an approval by the agent or a service
  account, a bare (unstructured) yes, a risk_acceptance that resolves to false, a blanket (not-per-request)
  approval, a stale attestation whose bound artifact digest changed, a non-list or malformed impact, or a
  missing two-key each resolve to authorized=False with a NAMED reason from the closed taxonomy below, never
  to authorized. The refusals ARE the product: every decision reports exactly why it was authorized or
  refused, so a stranger sees the outcome from the record alone.

ANTI-RUBBER-STAMP (the reason the surface exists). An approval counts only when it carries a STRUCTURED
attestation - a non-empty rationale, an explicit risk_acceptance, and (for a review-disposition
touchpoint) a finding_disposition - never a bare yes; the attestation binds to THIS request (no bulk or
blanket approve, enforced per request id); and a MATERIAL CHANGE to the bound artifact (its digest
differs from the digest the attestation was made against) INVALIDATES that attestation, which is then
denied until re-attested.

SEPARATION OF DUTIES AND QUORUM. An authorizing approver identity MUST differ from the VERIFIED PROPOSER of
the work and can NEVER be the agent or a service account (the machine actors two_key refuses, mirrored here
and bound by a selftest so the two cannot drift). The verified proposer is NOT read from the request record:
veldo.request/v1 carries no proposer field, and a self-declared request field would be spoofable, so the W5
inbound edge - which derives the true proposer from the attributed changelog - SUPPLIES it to is_authorized
as an explicit input (the `proposer` argument). When no verified proposer is supplied, separation of duties
cannot be proven, so is_authorized REFUSES (proposer_identity_required) rather than skip the check: a safety
authorizer refuses when it lacks what it needs to prove a property. quorum(tier).count DISTINCT approvers are
required (one identity is never counted twice) and min_independence distinct independence groups are enforced;
an approver whose registry entry declares NO independence group is never silently treated as independent (it
joins one shared undeclared group, and an undeclared group is refused whenever min_independence > 1). For a
request whose impact is irreversible, money, or external, the FROZEN two_key.authorize contract (KEY 1 a
recorded human authorization plus KEY 2 an independent fresh-context confirmation, each bound to the proposal
digest) MUST additionally be satisfied, reused UNCHANGED - this module builds no second gate and edits
two_key.py not at all; a non-list or malformed impact fails CLOSED (the second key is NOT dropped).

SEPARATION AND REUSE (no second parser, no second gate). This is a set of PURE functions over already
parsed inputs: the request envelope, the attestations, the approver registry, and (for the second key)
the two frozen key records. It reads the human_decisions block from .veldo/policy.yaml the way
policy_check.py reads that same file - ROOT-relative and read-only - and parses only that block, reusing
the ONE front-matter parser (validate.parse_yamlish, loaded by path the way the engine loads its
siblings) rather than shipping a second parser; in the INERT state (no block) it never parses at all.
It holds no credential, opens no connection, runs nothing, and starts no process, thread, or timer
(NG3, no-detach): dependency free by construction (pathlib and json at module top; importlib lazily,
only when a policy block is present or the two-key path is reached).

HONEST DEFERRALS. The inbound command-and-receipt edge (W5, WARP-0619) is the caller that will DRIVE a
request through this matrix and record the settlement; the outbound projection (W3, WARP-0617) and the
doorbell (W4, WARP-0618) are already shipped. Nothing here pretends those are this module's work, and
switching the engine on (the policy.yaml edit) remains a separate protected-path approval (VEL-3).
"""
from pathlib import Path
import json

SCHEMA = "veldo.authorization/v1"

# The impact FLAGS (veldo.request/v1) that additionally require the frozen two-key rule. data_mutating is
# an impact flag too, but per the surface design the SECOND KEY is required for irreversible / money /
# external actions; the flag set is closed here so a near-miss flag never silently drops the requirement.
TWO_KEY_IMPACTS = frozenset({"irreversible", "money", "external"})

# The touchpoint whose attestation additionally requires a finding_disposition (a review is a DISPOSITION
# of findings, not a bare approval). Mirrors the veldo.request/v1 touchpoint vocabulary.
REVIEW_DISPOSITION = "review_disposition"

# Machine actors that may NEVER stand in for a HUMAN approver: the agent and the service accounts. This is
# a SUPERSET of two_key.MACHINE_ACTORS (the human-authorization refusal there), and a selftest binds the
# two so they cannot drift - the same identity two_key refuses as KEY 1 is refused as an authorizer here.
# An approver whose registry actor kind is one of these, or whose id is one of these, is not a human.
MACHINE_ACTORS = frozenset({
    "veldo-executor", "veldo-responder", "executor", "responder", "machine",
    "agent", "bot", "ava", "automation",
    "service", "service_account", "service-account",
})

# THE NAMED REFUSAL TAXONOMY (fail closed): the refusals are the product. Every path that does not
# authorize returns one of these, so the outcome is legible from the decision record alone.
NO_POLICY = "no_human_decisions_policy"            # INERT: the block is absent or malformed (authorizes nothing)
NO_REQUEST_ID = "no_request_id"                    # the request carries no id (cannot be bound per-request; fail closed)
PROPOSER_IDENTITY_REQUIRED = "proposer_identity_required"  # no VERIFIED proposer supplied (separation of duties unprovable)
NO_ATTESTATION = "no_attestation"                  # no structured attestation was supplied for this request
NOT_PER_REQUEST = "not_per_request"                # no attestation names this request (no bulk/blanket approve)
UNSTRUCTURED_ATTESTATION = "unstructured_attestation"  # a bare yes: missing rationale/risk_acceptance/finding_disposition
STALE_ATTESTATION = "stale_attestation"            # the bound artifact digest changed after the attestation
UNKNOWN_APPROVER = "unknown_approver"              # the attesting identity is not in the approver registry
MACHINE_APPROVER = "machine_approver_refused"
UNESTABLISHED_ACTOR_KIND = "unestablished_actor_kind"  # the tracker reports NO kind for this actor, and
#   humanness must be ESTABLISHED rather than assumed from the absence of evidence (WARP-0624, C3). Before
#   this, an unrecognized actor defaulted to human, which is exactly how the real "Veldo Agent" account
#   could have settled a decision on any surface without a tracker-side fence.      # the approver is the agent or a service account (never a human)
SEPARATION_OF_DUTIES = "separation_of_duties"      # the approver is the VERIFIED proposer of the work (self-approval)
ROLE_NOT_SATISFIED = "role_not_satisfied"          # a required role is not held by any valid approver
QUORUM_NOT_MET = "quorum_not_met"                  # fewer distinct valid approvers than quorum.count
INDEPENDENCE_NOT_MET = "independence_not_met"      # fewer distinct independence groups than min_independence
TWO_KEY_NOT_SATISFIED = "two_key_not_satisfied"    # irreversible/money/external without a satisfied two-key contract
AUTHORIZED = "authorized"                          # every condition holds

# The sentinel independence group for an approver whose registry entry declares NO independence group. Every
# such approver shares this ONE object (they are never split into per-identity groups), so undeclared
# independence is not silently counted as independent; when min_independence > 1 an undeclared group is
# refused (independence cannot be proven). A unique object so it can never collide with a real group name.
_UNDECLARED_INDEPENDENCE = object()


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _is_nonneg_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _norm(v):
    """An identity normalized for comparison (lowercased, trimmed), so a case variant of the same party
    cannot slip past the self-separation or machine-actor guard. A non-string normalizes to None."""
    return v.strip().lower() if isinstance(v, str) else None


def _as_bool(v):
    """The value as a real boolean, or None. The one front-matter parser leaves an unquoted true/false as
    the string "true"/"false", so a boolean field can arrive as that string; accept the string forms and a
    real bool and nothing else, the idiom the sibling organs use, so a truthy-looking value is never
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


# The policy: the human_decisions block, read from .veldo/policy.yaml read-only (INERT when absent).

def _repo_root():
    """This engine copy's repository root (.veldo/authorization.py -> its parent's parent), so the policy
    is read ROOT-relative the way policy_check.py reads .veldo/policy.yaml."""
    return Path(__file__).resolve().parent.parent


def _yamlish():
    """The ONE front-matter parser (validate.parse_yamlish), loaded BY PATH from this engine copy's own
    directory the way the engine loads its siblings (spec_from_file_location), so this module ships no
    second parser and there is no import cycle. Called only when a policy block is physically present."""
    import importlib.util
    p = Path(__file__).resolve().parent / "validate.py"
    spec = importlib.util.spec_from_file_location("veldo_validate_authz", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_yamlish


def _extract_block(text, key):
    """The top-level block named `key` (its declaration line plus every following blank, comment, or
    indented line, up to the next top-level key), or None when the block is absent. A cheap, self-contained
    read so the INERT state (no block) never parses anything and never loads the parser."""
    out, capturing = [], False
    for raw in text.splitlines():
        if not capturing:
            if raw[:1] not in (" ", "\t", "#") and raw.split(":", 1)[0].strip() == key and ":" in raw:
                capturing = True
                out.append(raw)
            continue
        if raw.strip() and raw[:1] not in (" ", "\t", "#"):
            break  # the next top-level key ends the block
        out.append(raw)
    return "\n".join(out) if capturing else None


def load_policy(root=None, parse=None):
    """The human_decisions approver policy, read from .veldo/policy.yaml (read-only, ROOT-relative, the way
    policy_check.py reads the same file). Returns the parsed block (a mapping) or None when the file is
    absent, the block is absent, or the block cannot be parsed - INERT / fail closed: with no block,
    is_authorized authorizes NOTHING. The block (when present) is parsed with the ONE parser; a caller may
    inject `parse` (validate.parse_yamlish) to avoid the lazy load."""
    base = Path(root) if root else _repo_root()
    try:
        text = (base / ".veldo" / "policy.yaml").read_text()
    except OSError:
        return None
    block = _extract_block(text, "human_decisions")
    if block is None:
        return None
    p = parse or _yamlish()
    try:
        data = p(block)
    except ValueError:
        return None
    hd = data.get("human_decisions") if isinstance(data, dict) else None
    return hd if isinstance(hd, dict) else None


def required_roles(touchpoint, tier, policy=None):
    """The roles required to authorize `touchpoint` at `tier`, read from the human_decisions policy block
    (roles per touchpoint, plus any tier_roles for the tier). Returns a sorted list. With no policy block
    (INERT) returns [] and is_authorized denies regardless (the block, not this list, is the gate)."""
    pol = policy if policy is not None else load_policy()
    if not isinstance(pol, dict):
        return []
    roles = set()
    by_tp = pol.get("roles")
    if isinstance(by_tp, dict):
        roles |= {r for r in _as_list(by_tp.get(touchpoint)) if _is_str(r)}
    by_tier = pol.get("tier_roles")
    if isinstance(by_tier, dict):
        roles |= {r for r in _as_list(by_tier.get(tier)) if _is_str(r)}
    return sorted(roles)


def quorum(tier, policy=None):
    """The {count, min_independence} required at `tier`, read from the human_decisions policy block.
    Returns None when no block is configured or the tier declares no well-formed quorum (count a positive
    integer, min_independence a non-negative integer) - is_authorized treats a missing quorum as INERT and
    denies (fail closed)."""
    pol = policy if policy is not None else load_policy()
    if not isinstance(pol, dict):
        return None
    q = pol.get("quorum")
    if not isinstance(q, dict):
        return None
    tq = q.get(tier)
    if not isinstance(tq, dict):
        return None
    count, mi = tq.get("count"), tq.get("min_independence")
    if not _is_pos_int(count) or not _is_nonneg_int(mi):
        return None
    return {"count": count, "min_independence": mi}


# The two-key path: the frozen two_key.py, reused UNCHANGED for the second key.

_TWO_KEY = None


def _two_key():
    """The FROZEN two-key gate (.veldo/two_key.py), loaded BY PATH from this engine copy's own directory and
    reused UNCHANGED. Loaded lazily and only on the two-key path (an irreversible/money/external request),
    so a request that does not need the second key never touches it."""
    global _TWO_KEY
    if _TWO_KEY is None:
        import importlib.util
        p = Path(__file__).resolve().parent / "two_key.py"
        spec = importlib.util.spec_from_file_location("veldo_two_key_authz", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _TWO_KEY = mod
    return _TWO_KEY


def _two_key_ok(request, digest, keys, now, executor_actor, proposer):
    """Whether the FROZEN two-key contract is satisfied for `request`, bound to `digest`. Returns
    (ok, reason, detail). Fails closed when no two-key material is supplied or the bound artifact carries no
    digest to bind the keys to; otherwise delegates to two_key.authorize UNCHANGED (KEY 1 human
    authorization, KEY 2 independent fresh-context confirmation, each bound to the digest). The VERIFIED
    proposer (supplied by the caller, never read from the request) is passed as the remedy's proposed_by so
    the frozen gate refuses a KEY 2 confirmation authored by the proposer."""
    if not _is_str(digest):
        return False, TWO_KEY_NOT_SATISFIED, ("the request carries no bound artifact digest to bind the two "
                                              "keys to (an irreversible/money/external action must bind a digest)")
    if not isinstance(keys, dict):
        return False, TWO_KEY_NOT_SATISFIED, ("no two-key material (KEY 1 human authorization and KEY 2 "
                                              "independent confirmation) was supplied")
    tk = _two_key()
    remedy = {"incident": request.get("incident"), "proposed_by": proposer}
    reason, detail = tk.authorize(remedy, digest, keys.get("human_authorization"),
                                  keys.get("independent_confirmation"),
                                  executor_actor=executor_actor, now=now)
    return (reason is None), (TWO_KEY_NOT_SATISFIED if reason else None), detail


# The attestation: structured, per-request, bound, from a separated human approver.

def actor_kind(entry):
    """The kind the TRACKER reported for this actor, normalized to human, machine or unknown.

    WARP-0624. The core never parses a display name to decide this and never sees a raw tracker
    vocabulary: the adapter maps its own `accountType` (or equivalent) to these three values, so a new
    tracker's vocabulary is that adapter's problem and not the core's. An entry that carries no kind is
    UNKNOWN, which is refused elsewhere - it is not quietly read as human."""
    e = entry or {}
    k = e.get("actor_kind")
    if k in ("human", "machine", "unknown"):
        return k
    # BACKWARD COMPATIBLE WITH WHAT REGISTRIES ALREADY DECLARE. An approver entry has always carried
    # an `actor` field, and where it already says "human" that IS the tracker-independent declaration
    # this guard wants; demanding a new field beside it would break every existing registry to learn
    # nothing. A declared machine name still resolves to machine. What stays UNKNOWN, and therefore
    # refused, is an entry that declares NEITHER - which is the case WARP-0620 exposed.
    a = _norm(e.get("actor"))
    if a in MACHINE_ACTORS:
        return "machine"
    if a == "human":
        return "human"
    return "unknown"


def _is_machine(who, entry):
    """Whether an approver is a machine. THREE INDEPENDENT REFUSALS, and the guard is a strict SUPERSET
    of what it replaced: everything the name list refused before is still refused.

    1. The tracker REPORTS machine (WARP-0624). This is the one that works on real identities: the live
       run's agent is called "Veldo Agent", which no list of generic words contains, while Jira reported
       `accountType: app` in the same response and nothing read it.
    2. The normalized approver id is in MACHINE_ACTORS. RETAINED, not replaced, so no case permitted
       today becomes permitted; the same closed set two_key refuses for KEY 1, bound by a selftest.
    3. The registry entry's declared actor is in that set.

    UNKNOWN IS NOT HANDLED HERE. It is not machine-ness, it is the absence of an answer, and it gets its
    own refusal at the call site so an operator is told which of the two happened."""
    if actor_kind(entry) == "machine":
        return True
    if _norm(who) in MACHINE_ACTORS:
        return True
    return _norm(entry.get("actor")) in MACHINE_ACTORS


def _attestation_ok(att, request, bound_digest, proposer, registry):
    """Whether one attestation is a valid authorizing approval of `request`. Returns (ok, reason). It must be
    STRUCTURED (a non-empty rationale, a risk_acceptance that resolves to a GENUINE affirmative - never false
    or a value resolving to false - and a finding_disposition for a review-disposition touchpoint, never a
    bare yes), BOUND to the request's current bound artifact digest (a material change invalidates it, STALE),
    from a KNOWN approver who is NOT a machine and NOT the VERIFIED PROPOSER of the work (separation of
    duties). The verified proposer is supplied by the caller (the W5 edge), never read from the request.
    Per-request binding (the attestation names this request) is enforced by the caller before this is reached."""
    if not _is_str(att.get("rationale")):
        return False, UNSTRUCTURED_ATTESTATION
    # risk_acceptance must be a GENUINE affirmative. Normalize through _as_bool: an explicit non-acceptance
    # (a real bool False, or the string "false" the one parser leaves for an unquoted false) is refused; only
    # a real True, the string "true", or a non-empty free-text acceptance passes.
    ra = att.get("risk_acceptance")
    ra_bool = _as_bool(ra)
    if ra_bool is False or not (ra_bool is True or _is_str(ra)):
        return False, UNSTRUCTURED_ATTESTATION
    if request.get("touchpoint") == REVIEW_DISPOSITION and not _is_str(att.get("finding_disposition")):
        return False, UNSTRUCTURED_ATTESTATION
    if not _is_str(bound_digest) or att.get("bound_digest") != bound_digest:
        return False, STALE_ATTESTATION
    who = att.get("approver")
    entry = registry.get(who) if (_is_str(who) and isinstance(registry, dict)) else None
    if not isinstance(entry, dict):
        return False, UNKNOWN_APPROVER
    if _is_machine(who, entry):
        return False, MACHINE_APPROVER
    # FAIL CLOSED ON AN ACTOR THE TRACKER WILL NOT VOUCH FOR (WARP-0624, C3). Separate from
    # MACHINE_APPROVER on purpose: "we know this is a machine" and "we cannot establish that this is a
    # person" are different operator problems and deserve different names.
    if actor_kind(entry) != "human":
        return False, UNESTABLISHED_ACTOR_KIND
    if _is_str(proposer) and _norm(who) == _norm(proposer):
        return False, SEPARATION_OF_DUTIES
    return True, None


def _evaluate(considered, request, bound_digest, proposer, registry):
    """Partition the per-request attestations into the VALID ones and the first disqualifying reason (so a
    single-fault scenario - a stale, a self-approval, a machine approver - surfaces its exact named reason)."""
    valid, first_bad = [], None
    for att in considered:
        ok, reason = _attestation_ok(att, request, bound_digest, proposer, registry)
        if ok:
            valid.append(att)
        elif first_bad is None:
            first_bad = reason
    return valid, first_bad


def _tally(valid, registry):
    """The distinct approvers (one identity never counted twice), the distinct independence groups, and the
    roles those approvers cover, over the valid attestations. An approver whose registry entry declares NO
    independence group joins the SINGLE _UNDECLARED_INDEPENDENCE sentinel group (never its own per-identity
    group), so undeclared independence is not silently treated as independent."""
    approvers, groups, covered, seen = [], set(), set(), set()
    for att in valid:
        who = att.get("approver")
        if _norm(who) not in seen:
            seen.add(_norm(who))
            approvers.append(who)
        entry = registry.get(who) or {}
        ind = entry.get("independence")
        groups.add(_norm(ind) if _is_str(ind) else _UNDECLARED_INDEPENDENCE)
        covered |= {r for r in _as_list(entry.get("roles")) if _is_str(r)}
    return approvers, groups, covered


# The decision: is THIS human decision authorized?

def _decision(request, tp, tier, rid):
    return {"schema": SCHEMA, "authorized": False, "reason": None, "detail": None,
            "request_id": rid, "touchpoint": tp, "tier": tier,
            "required_roles": [], "quorum": None, "approvers": [], "independence": 0,
            "two_key_required": False, "two_key_satisfied": None}


def _settle(decision, authorized, reason, detail):
    decision["authorized"] = authorized
    decision["reason"] = reason
    decision["detail"] = detail
    return decision


def _decide(decision, req, tier, required, valid, first_bad, approvers, groups, covered, q,
            bound_digest, two_key_keys, now, executor_actor, proposer):
    """The verdict over the tallied attestations, in priority order (fail closed at each guard): a valid
    structured attestation must exist, every required role must be covered, the distinct-approver quorum and
    the min_independence must be met (an undeclared independence group cannot be proven independent), and for
    an irreversible/money/external request the frozen two-key rule must additionally be satisfied (a non-list
    or malformed impact fails closed to two-key-required). Returns the settled decision; the single reason
    names the first guard that did not pass."""
    if not valid:
        return _settle(decision, False, first_bad or NO_ATTESTATION,
                       "no valid structured attestation stands for this request (fail closed)")
    missing = [r for r in required if r not in covered]
    if missing:
        return _settle(decision, False, ROLE_NOT_SATISFIED,
                       "a required role is not held by any valid approver: missing %s" % sorted(missing))
    count = q["count"] if q else 1
    min_ind = q["min_independence"] if q else 0
    if len(approvers) < count:
        return _settle(decision, False, QUORUM_NOT_MET,
                       "quorum is short: %d distinct valid approver(s), %d required" % (len(approvers), count))
    # INDEPENDENCE, fail closed. When more than one independent group is required, a counted approver whose
    # independence group is UNDECLARED cannot be proven independent, so it is refused (never silently treated
    # as its own independent group). The undeclared approvers share one sentinel group (below), so this fires
    # whenever any undeclared approver is counted toward a min_independence > 1 requirement.
    if min_ind > 1 and _UNDECLARED_INDEPENDENCE in groups:
        return _settle(decision, False, INDEPENDENCE_NOT_MET,
                       "independence cannot be proven: a counted approver declares no independence group and "
                       "min_independence is %d (fail closed - an undeclared group is not treated as independent)" % min_ind)
    if len(groups) < min_ind:
        return _settle(decision, False, INDEPENDENCE_NOT_MET,
                       "independence is short: %d distinct independence group(s), %d required (independent "
                       "identities, not one identity counted twice)" % (len(groups), min_ind))
    # TWO-KEY, fail closed on a malformed impact. A well-formed impact is a LIST of flags; an absent impact
    # (None) needs no second key; a non-list / malformed impact must NOT drop the second key (coercing it to
    # [] would), so it fails closed to two-key-required.
    impact = req.get("impact")
    if impact is None:
        needs_2k = False
    elif isinstance(impact, list):
        needs_2k = bool(set(impact) & TWO_KEY_IMPACTS)
    else:
        needs_2k = True
    decision["two_key_required"] = needs_2k
    if needs_2k:
        ok2, _r2, detail2 = _two_key_ok(req, bound_digest, two_key_keys, now, executor_actor, proposer)
        decision["two_key_satisfied"] = ok2
        if not ok2:
            return _settle(decision, False, TWO_KEY_NOT_SATISFIED,
                           "the request impact (irreversible/money/external, or a non-list/malformed impact "
                           "that fails closed) additionally requires the frozen two-key rule, which is not "
                           "satisfied: %s" % detail2)
    return _settle(decision, True, AUTHORIZED,
                   "authorized: %d distinct approver(s) across %d independence group(s) satisfied the "
                   "required roles %s at tier %r%s" % (len(approvers), len(groups), required, tier,
                   " with the two-key rule" if needs_2k else ""))


def is_authorized(request, attestations, approver_registry, policy=None,
                  two_key_keys=None, now=None, executor_actor=None, proposer=None):
    """Decide whether THIS veldo.request/v1 human decision is authorized. Returns a STRUCTURED decision
    {authorized (bool), reason (a named reason from the taxonomy), detail, and the evidence the outcome
    rests on - the required roles, the quorum, the distinct approvers counted, the independence, and whether
    the two-key rule was required and satisfied}. FAILS CLOSED to authorized=False on every guard, and is
    INERT (authorizes nothing) whenever no human_decisions policy block is configured.

      request: a veldo.request/v1 envelope (touchpoint, tier, impact flags, bound_artifact.digest). The
        request record carries NO proposer field - the verified proposer is a separate input (below), never
        read from the record, so a self-declared field cannot spoof separation of duties.
      attestations: the structured approvals gathered (each names this request, carries a rationale + an
        explicit risk_acceptance + a finding_disposition for a review disposition, an approver, and the
        bound_digest it was made against).
      approver_registry: {approver_id: {roles, independence, actor}} - the roles each approver holds, their
        independence group, and their actor kind (a human, or the agent/a service account).
      policy: the parsed human_decisions block; None reads .veldo/policy.yaml (INERT in the shipped state).
      two_key_keys: {human_authorization, independent_confirmation} for the second key (required only for an
        irreversible/money/external request); now / executor_actor are passed to the frozen two-key gate.
      proposer: the VERIFIED identity of the party who proposed the work, SUPPLIED BY THE CALLER (the W5
        inbound edge derives it from the attributed changelog). Separation of duties compares each approver
        against it; when it is absent the property cannot be proven and the request is REFUSED
        (proposer_identity_required), never skipped."""
    req = request if isinstance(request, dict) else {}
    tp, tier, rid = req.get("touchpoint"), req.get("tier"), req.get("id")
    ba = req.get("bound_artifact")
    bound_digest = ba.get("digest") if isinstance(ba, dict) else None
    decision = _decision(req, tp, tier, rid)

    pol = policy if policy is not None else load_policy()
    q = quorum(tier, pol)
    # THE INERT / FAIL-CLOSED CONFIG GATE: with no configured human_decisions block (or no well-formed
    # quorum for this tier) the engine authorizes NOTHING. This single guard is the shipped INERT posture;
    # neutralizing it is what a selftest tooth proves load-bearing.
    if not (isinstance(pol, dict) and pol and q):
        return _settle(decision, False, NO_POLICY,
                       "no human_decisions policy block is configured for this tier: the authorization "
                       "engine is INERT and authorizes nothing until the block is added (fail closed)")
    # FAIL CLOSED on a request with NO id: a null/absent id must never be treated as a per-request match for
    # an attestation that also names no request (None == None), which would let a blanket attestation
    # authorize an idless request. An authorization is per-request, so a request an approver cannot name is
    # refused before any attestation is considered.
    if not _is_str(rid):
        return _settle(decision, False, NO_REQUEST_ID,
                       "the request carries no id: an authorization is per-request and an idless request "
                       "cannot be bound to a per-request attestation (fail closed)")
    # FAIL CLOSED when the VERIFIED proposer identity is absent. veldo.request/v1 carries no proposer field, so
    # the W5 inbound edge derives the true proposer from the attributed changelog and supplies it here.
    # Without it, separation of duties cannot be proven, so the authorizer REFUSES rather than skip the check.
    if not _is_str(proposer):
        return _settle(decision, False, PROPOSER_IDENTITY_REQUIRED,
                       "no verified proposer identity was supplied by the driver (the W5 inbound edge derives "
                       "the true proposer from the attributed changelog): separation of duties cannot be "
                       "proven, so the request is refused (fail closed)")
    required = required_roles(tp, tier, pol)
    decision["required_roles"] = required
    decision["quorum"] = q

    atts = attestations if isinstance(attestations, list) else []
    registry = approver_registry if isinstance(approver_registry, dict) else {}
    # PER-REQUEST (no bulk/blanket approve): only an attestation that names THIS request counts.
    considered = [a for a in atts if isinstance(a, dict) and a.get("request_id") == rid]
    if atts and not considered:
        return _settle(decision, False, NOT_PER_REQUEST,
                       "no attestation names this request %r: an approval is per-request, never a blanket "
                       "or bulk approve" % rid)

    valid, first_bad = _evaluate(considered, req, bound_digest, proposer, registry)
    approvers, groups, covered = _tally(valid, registry)
    decision["approvers"] = list(approvers)
    decision["independence"] = len(groups)
    return _decide(decision, req, tier, required, valid, first_bad, approvers, groups, covered, q,
                   bound_digest, two_key_keys, now, executor_actor, proposer)


def authorized(request, attestations, approver_registry, **kw):
    """Convenience predicate: True iff is_authorized returns authorized. The caller that needs the named
    reason to fail closed uses is_authorized directly; this is for a caller that wants only the boolean."""
    return bool(is_authorized(request, attestations, approver_registry, **kw).get("authorized"))


def _cli(argv):
    """Standalone runner: report the shipped posture over the repository's own policy.yaml. With no
    human_decisions block (the shipped INERT state) it authorizes NOTHING, which it prints honestly.
    Offline, no process (NG3); it reads policy.yaml read-only and writes nothing."""
    pol = load_policy()
    demo_request = {"schema": "veldo.request/v1", "id": "REQ-DEMO", "touchpoint": "spec_approval",
                    "tier": "standard", "impact": [],
                    "bound_artifact": {"kind": "approval", "ref": "proof/DEMO/approval.json",
                                       "digest": "sha256:demodemodemodemo"}}
    demo_att = [{"approver": "reviewer-a", "request_id": "REQ-DEMO", "rationale": "read the change end to end",
                 "risk_acceptance": "I accept the standard-tier risk", "bound_digest": "sha256:demodemodemodemo"}]
    demo_reg = {"reviewer-a": {"roles": ["approver"], "independence": "group-a", "actor": "human"}}
    # The verified proposer is supplied by the caller (never read from the request); "builder" differs from
    # the approver "reviewer-a", so separation holds. In the shipped INERT state the config gate denies first.
    dec = is_authorized(demo_request, demo_att, demo_reg, proposer="builder")
    print("veldo authorization (%s): policy block %s" % (SCHEMA, "configured" if pol else "ABSENT (INERT)"))
    print(json.dumps(dec, indent=2, default=str))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))
