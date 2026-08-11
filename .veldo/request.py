#!/usr/bin/env python3
"""VELDO human-touchpoint request envelope (veldo.request/v1): the one thin schema
the entire human-decision surface keys on, and its structural validator.

This is the W2 organ of PLAN-0016 (human decisions through Jira). Every other item
of the surface reads and writes the same thing, a human touchpoint: the outbound
projection (W3) reads the brief, the RISK, and the bound digest; the authorization
and quorum logic (W6) reads the tier, the roles, and the quorum; the inbound
command-and-receipt edge (W5) writes the settlement and the status. If that
touchpoint were modeled by EXTENDING the shipped settlement records
(veldo.approval/v1, veldo.decision/v1, veldo.verdict/v1), it would couple the
safety-critical readers those records feed (policy_check, two_key, decision) to the
new surface, and a mistake there would break the merge gate or the two-key rule.

So the touchpoint is a NEW, THIN ENVELOPE that REFERENCES a settlement record by
path and carries all the coupling and projection metadata the frozen readers must
never see. Because those readers ignore unknown fields, the settlement records stay
byte-compatible and this module makes NO change to policy_check.py, two_key.py, or
decision.py. This module builds the envelope, its canonical digest, its fail-closed
validator, and the directory scan, and nothing else; the projection is WARP-0617
(W3), the authorization and quorum logic is WARP-0616 (W6), and the inbound edge is
WARP-0619 (W5), all honestly later items.

The envelope carries id, request_hash, touchpoint, tier, impact, required_roles,
quorum, expires_at, supersedes/superseded_by, bound_artifact, settlement, tracker,
and status. Two hashes live here and must NOT be unified, or a frozen reader breaks:

  request_digest(record) is the ONE canonical integrity hash over the request's
  SUBSTANCE (the ask), parallel to policy_check.proof_digest and
  action_executor.proposal_digest. It is the tamper-detection and material-change
  hash the request carries in request_hash, and it is NEVER handed to a frozen
  reader.

  bound_artifact.digest is POLYMORPHIC per touchpoint - it holds whatever the
  settlement reader for that touchpoint actually binds on: the commit(s)+paths an
  approval that policy_check checks, the action_executor.proposal_digest verbatim a
  two_key risky action checks, the veldo.decision/v1 record digest a decision-choice
  checks. It is the binding the eventual settlement reader uses, SEPARATE from
  request_digest.

Closed vocabularies are validated FAIL CLOSED by name (a near-miss value makes the
record silently inert, which is exactly the failure this validator exists to catch):
touchpoint, tier, and status, plus the impact FLAGS (data_mutating, money, external,
irreversible), which are flags on the request, NEVER a fifth tier. Two derivations
are load bearing and enforced: an irreversible impact must map to the critical tier
(consistent with decision.py's D5), and a decision_choice request's tier is DERIVED
from the bound decision's risk (the single derivation), not set independently.

Two postures, both shared with the decision organ this mirrors:
  ADOPTION SAFE. A repository with no .veldo/requests/ directory is untouched:
  check_requests_dir on an absent directory stands down and returns clean, so
  adding this module changes no existing gate. The moment a record exists it is
  validated and fails closed.
  FAIL CLOSED. A malformed record, an out-of-vocabulary touchpoint/tier/status/
  impact, a missing required field, a non-positive version, a duplicate request id,
  an accepted request whose bound_artifact carries no digest to bind on, a
  settlement record path that does not exist, or a decision_choice tier that is not
  the bound decision's risk each refuse by name.

Dependency free by construction: the caller (.veldo/validate.py) passes in the
front-matter parser and the failure reporter it already owns, so this module adds
no second YAML parser and no import cycle.
"""
import hashlib
import json
from pathlib import Path

SCHEMA = "veldo.request/v1"

# The human touchpoints the surface models. Each maps to a settlement record kind
# (spec/plan approval -> veldo.approval; decision-choice -> veldo.decision;
# review-disposition -> veldo.verdict; risky-action -> two_key over approval+verdict;
# escalation -> no record, a status and required_roles change on the envelope).
TOUCHPOINTS = {
    "spec_approval", "plan_approval", "decision_choice",
    "review_disposition", "risky_action_authorization", "escalation",
}
# The existing risk tiers (mirrors validate.RISKS); the request inherits the same
# ladder so a request's tier and a decision's risk are one vocabulary.
TIERS = {"low", "standard", "high", "critical"}
# The request lifecycle. A request opens, moves through discussion/approval/decision,
# and settles as accepted, rejected, or superseded. There is no machine-settled
# state: the inbound edge (W5) writes a terminal status only from an attributed human
# changelog entry.
STATUSES = {
    "open", "in_discussion", "awaiting_approval", "needs_decision",
    "changes_requested", "blocked", "accepted", "rejected", "superseded",
}
# Impact FLAGS, never a fifth tier: orthogonal properties of the change that raise
# scrutiny. irreversible forces the critical tier (below); money/external are read by
# W6 to require the two-key rule.
IMPACTS = {"data_mutating", "money", "external", "irreversible"}
# The status that means the ask was answered yes and a settlement record now exists:
# such a request MUST be bound to the settlement it accepted (bound_artifact.digest).
ACCEPTED = "accepted"

# The event vocabulary this surface introduces to the shared event stream
# (.veldo/events.py). The request lifecycle emits request.opened/accepted/rejected/
# superseded; decision.decided is added alongside them because a settled decision-choice
# request had NO event before this surface (a decision record moving to decided). Owned
# here as the contract organ and carried by .veldo/events.py, with a selftest drift-guard
# binding the two so the contract and the emitter cannot drift (mirrors incident.py's
# INCIDENT_EVENT_TYPES). Adding these to events.py is a conscious contract change.
REQUEST_EVENT_TYPES = {
    "request.opened", "request.accepted", "request.rejected", "request.superseded",
    "decision.decided",
}

# The request SUBSTANCE request_digest hashes: the ask itself, not the answer. The
# lifecycle fields (status, settlement, tracker projection, supersede links) are
# EXCLUDED so the hash is stable as the request moves through its lifecycle and a
# material change to the ASK is detectable against it (the W5 material-change rule).
DIGEST_FIELDS = ("id", "touchpoint", "tier", "impact", "required_roles",
                 "quorum", "expires_at", "bound_artifact")


class RequestRecordError(ValueError):
    """A request record is malformed. Raised by name so a bad record never silently
    no-ops (parallels DecisionRecordError and ArchContractError)."""


def default_requests_dir(root=None):
    return Path(root or ".") / ".veldo" / "requests"


def request_digest(record):
    """The ONE canonical integrity hash over a request's substance (the ask), parallel
    to policy_check.proof_digest and action_executor.proposal_digest. It is what the
    request carries in request_hash for tamper-detection and the material-change rule,
    and it is SEPARATE from bound_artifact.digest (the polymorphic per-touchpoint
    binding the frozen settlement reader uses) - the two are never unified, or a reader
    breaks. Stable over the substance and content-sensitive; the lifecycle fields are
    excluded so it does not change as the request moves through its states."""
    payload = {k: record.get(k) for k in DIGEST_FIELDS}
    blob = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


def derive_tier(decision_record):
    """The SINGLE derivation: a decision_choice request's tier IS the bound decision's
    risk. Scrutiny scales with the decision's reversal cost (decision.py's D5), so the
    request that settles a foundational choice inherits that choice's tier rather than
    declaring an independent one. Returns the decision's risk, or None if the record
    declares none."""
    return decision_record.get("risk") if isinstance(decision_record, dict) else None


def load_record(path, parse):
    """Parse the record at path into a dict using the caller's front-matter parser (the
    VELDO yamlish subset), raising RequestRecordError on unreadable or unparseable
    input. The single place a record is read, so W3/W5/W6 reuse it rather than parsing
    the file a second way."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise RequestRecordError("request record unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise RequestRecordError("request record outside the record subset: %s" % e)
    if not isinstance(data, dict):
        raise RequestRecordError("request record must be a mapping at the top level")
    return data


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _is_nonneg_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validate_record(data, root, record_path, fail):
    """Structural validation of one parsed veldo.request/v1 record. Reports each problem
    through fail(name, msg) and returns the error count. PURE over the dict (no
    filesystem access), so it is trivially reused by the directory scan and the
    single-file entry point; the two fail-closed checks that need the repository (a
    settlement record path that must exist, a decision_choice tier that must equal the
    bound decision's risk) live in check_record, which holds the parser and the root."""
    errs = 0
    name = str(record_path)

    if data.get("schema") != SCHEMA:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA, data.get("schema")))
    for field in ("id", "touchpoint", "tier", "status", "request_hash"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s" % field)
    if not _is_pos_int(data.get("version")):
        errs += fail(name, "version must be an integer >= 1: a request record is versioned")

    # Self-consistency (the material-change baseline, enforced at CREATION): request_hash MUST equal
    # request_digest(record) recomputed over this record's OWN substance (the same DIGEST_FIELDS). This
    # is the CHEAP, pure, in-memory half of the tamper / material-change rule, so a request whose carried
    # hash does not match its substance fails closed BY NAME here at W2 and no consumer that ships before
    # the inbound edge (the W3 projection, the W4 doorbell) ever trusts an unverified request_hash. The
    # EXPENSIVE half, recomputing request_hash against state rebuilt from the repository / changelog,
    # stays deferred to W5; this is only the record-against-its-own-digest check.
    rh = data.get("request_hash")
    if _is_str(rh) and rh != request_digest(data):
        errs += fail(name, "request_hash %r is not request_digest(record) %r: request_hash MUST equal the canonical digest of the record's own substance (self-consistency enforced at creation; the repo-recompute stays W5)" % (rh, request_digest(data)))

    # Closed vocabularies, fail closed by name. A near-miss touchpoint/tier/status makes
    # the request silently inert on the surface (W3 would not project it, W6 would not
    # authorize it), so an out-of-vocabulary value is refused at record time.
    touchpoint = data.get("touchpoint")
    if _is_str(touchpoint) and touchpoint not in TOUCHPOINTS:
        errs += fail(name, "bad touchpoint %r (allowed: %s)" % (touchpoint, sorted(TOUCHPOINTS)))
    tier = data.get("tier")
    if _is_str(tier) and tier not in TIERS:
        errs += fail(name, "bad tier %r (allowed: %s)" % (tier, sorted(TIERS)))
    status = data.get("status")
    if _is_str(status) and status not in STATUSES:
        errs += fail(name, "bad status %r (allowed: %s)" % (status, sorted(STATUSES)))

    # impact FLAGS (never a fifth tier): an optional list whose every entry is in the
    # closed impact vocabulary. An out-of-vocabulary flag is refused; an irreversible
    # flag forces the critical tier, the same scrutiny-scales-with-reversal-cost rule
    # decision.py enforces on an irreversible choice.
    impact = data.get("impact")
    if impact is not None and not isinstance(impact, list):
        errs += fail(name, "impact must be a list of flags (%s), never a scalar tier" % sorted(IMPACTS))
    else:
        for flag in _as_list(impact):
            if flag not in IMPACTS:
                errs += fail(name, "bad impact flag %r (allowed: %s)" % (flag, sorted(IMPACTS)))
        if "irreversible" in _as_list(impact) and tier != "critical":
            errs += fail(name, "an irreversible impact must map to the critical tier (consistent with decision.py): the irreversible touchpoints carry the highest tier, never a lower one")

    # required_roles: the roles W6 will require; a list of non-empty role names.
    roles = data.get("required_roles")
    if roles is not None:
        if not isinstance(roles, list):
            errs += fail(name, "required_roles must be a list of role names")
        elif not all(_is_str(r) for r in roles):
            errs += fail(name, "each required role must be a non-empty string")

    # quorum {count, min_independence}: how many independent approvals W6 will require.
    quorum = data.get("quorum")
    if quorum is not None:
        if not isinstance(quorum, dict):
            errs += fail(name, "quorum must be a mapping {count, min_independence}")
        else:
            if quorum.get("count") is not None and not _is_pos_int(quorum.get("count")):
                errs += fail(name, "quorum.count must be an integer >= 1")
            if quorum.get("min_independence") is not None and not _is_nonneg_int(quorum.get("min_independence")):
                errs += fail(name, "quorum.min_independence must be an integer >= 0")

    # bound_artifact {kind, ref, digest}: the reference to the settlement the request
    # binds on. kind and ref are the reference; digest is the POLYMORPHIC per-touchpoint
    # binding (the commit(s)+paths, the proposal digest, or the decision-record digest)
    # the eventual settlement reader checks, SEPARATE from request_hash and NEVER handed
    # to a frozen reader. An accepted request MUST carry that digest: accepting an ask
    # means a settlement record now exists and the request is bound to it.
    ba = data.get("bound_artifact")
    if not isinstance(ba, dict):
        errs += fail(name, "missing or malformed bound_artifact: a request REFERENCES a settlement record by {kind, ref, digest}")
    else:
        for field in ("kind", "ref"):
            if not _is_str(ba.get(field)):
                errs += fail(name, "bound_artifact.%s is required (the reference to the settlement record)" % field)
        if ba.get("digest") is not None and not _is_str(ba.get("digest")):
            errs += fail(name, "bound_artifact.digest, when present, must be a non-empty string (the polymorphic per-touchpoint binding)")
    if status == ACCEPTED and not (isinstance(ba, dict) and _is_str(ba.get("digest"))):
        errs += fail(name, "status accepted requires bound_artifact.digest: an accepted request is BOUND to the settlement it accepted (an unbound acceptance binds nothing)")

    # settlement {record, path}: the reference to the shipped settlement record. Empty
    # until accepted; the W5 edge writes it. Structural here (the path must exist is a
    # filesystem check in check_record).
    settlement = data.get("settlement")
    if settlement is not None and not isinstance(settlement, dict):
        errs += fail(name, "settlement must be a mapping {record, path}")

    # tracker {issue, url, projected_at, projection_digest}: the projection metadata W3
    # writes. Optional and structural here.
    tracker = data.get("tracker")
    if tracker is not None and not isinstance(tracker, dict):
        errs += fail(name, "tracker must be a mapping {issue, url, projected_at, projection_digest}")

    # Re-request lifecycle: a superseded request names the request that replaces it, so
    # a reader is never left at a dead reference (mirrors decision.py's superseded_by).
    if status == "superseded" and not _is_str(data.get("superseded_by")):
        errs += fail(name, "status superseded requires superseded_by: a re-request names the request that replaces it")

    return errs


def _check_settlement_path(data, root, name, fail):
    """A settlement record referenced by path must exist (fail closed, referenced but
    absent). Filesystem-touching, so it is separated from the pure validate_record."""
    settlement = data.get("settlement")
    if not isinstance(settlement, dict):
        return 0
    spath = settlement.get("path")
    if not _is_str(spath):
        return 0
    if not (Path(root) / spath).is_file():
        return fail(name, "settlement.path %r does not exist: an accepted request references its settlement record by path and the record must be present (fail closed)" % spath)
    return 0


def _check_decision_choice_tier(data, root, name, parse, fail):
    """A decision_choice request's tier is DERIVED from the bound decision's risk (the
    single derivation): when the bound decision record resolves, the request's tier must
    equal its risk or the derivation was overridden by an independently-set tier, which
    is refused by name. Resolves the decision via bound_artifact.ref (a repo-relative
    path) using the caller's parser, so no second parser and no dependency on
    decision.py; an unresolvable reference stands down here (an accepted request's
    binding is enforced by the bound_artifact.digest and settlement-path checks)."""
    if data.get("touchpoint") != "decision_choice":
        return 0
    ba = data.get("bound_artifact")
    ref = ba.get("ref") if isinstance(ba, dict) else None
    if not _is_str(ref):
        return 0
    dpath = Path(root) / ref
    if not dpath.is_file():
        return 0
    try:
        drec = parse(dpath.read_text())
    except (OSError, ValueError):
        return 0
    if not isinstance(drec, dict) or drec.get("schema") != "veldo.decision/v1":
        return 0
    want = derive_tier(drec)
    if _is_str(want) and data.get("tier") != want:
        return fail(name, "decision_choice tier %r is not the bound decision's risk %r: a decision-choice's tier is DERIVED from the bound decision (single derivation), not set independently" % (data.get("tier"), want))
    return 0


def check_record(path, root, required, parse, fail):
    """Single-file entry point. Absent file: stand down (adoption safe) unless it is
    required, in which case fail closed (referenced but absent). Present file: parse and
    validate structurally, then run the two repository-aware fail-closed checks (the
    settlement path must exist, and a decision_choice's tier must be the bound decision's
    risk)."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "request record is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_record(p, parse)
    except RequestRecordError as e:
        return fail(str(p), str(e))
    errs = validate_record(data, root, p, fail)
    errs += _check_settlement_path(data, root, str(p), fail)
    errs += _check_decision_choice_tier(data, root, str(p), parse, fail)
    return errs


def check_requests_dir(rdir, root, parse, fail):
    """The gate entry point over the per-repo request records. Adoption safe: an absent
    .veldo/requests/ directory stands down and returns clean, so a repository with no
    request records is byte-identically unaffected. Present records each fail closed on
    anything malformed, and a request id declared by more than one record is refused (a
    duplicate id is an ambiguous reference across the set). The exact shape of
    decision.check_decisions_dir: the parser and the reporter are passed in (no second
    YAML parser, no import cycle)."""
    d = Path(rdir)
    if not d.is_dir():
        return 0
    errs = 0
    ids = {}
    for p in sorted(d.glob("*.yaml")):
        errs += check_record(p, root, False, parse, fail)
        try:
            data = load_record(p, parse)
        except RequestRecordError:
            continue  # already reported by check_record above
        rid = data.get("id")
        if _is_str(rid):
            ids.setdefault(rid, []).append(p.name)
    for rid, files in sorted(ids.items()):
        if len(files) > 1:
            errs += fail(str(d), "duplicate request id %r across records: %s" % (rid, ", ".join(sorted(files))))
    return errs
