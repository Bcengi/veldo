#!/usr/bin/env python3
"""VELDO incident and remediation contracts (veldo.incident/v1 and veldo.remedy/v1):
the two foundational artifacts of the production support responder, and their
structural validator that fails closed.

This is the W1 organ of PLAN-0012 and the mechanism behind the method's "The
Incident" invention. When agents author everything, the five-minute diagnosis
that used to be a free byproduct of authorship is gone: whoever gets paged is a
stranger to the code. The responder that replaces the hero has to be built on
systems, and the FIRST system is a pair of readable contracts that make the
safety architecture structural rather than a policy anyone has to remember.

  veldo.incident/v1 - the incident RECORD: what broke (signal), the affected
  behavior (and, softly, the spec or contract area it traces to), the severity
  class, a timeline that carries the time-to-diagnosis, and a lifecycle status.
  An incident is intent arriving from production; this record is how it enters
  the loop.

  veldo.remedy/v1 - the remediation PROPOSAL artifact: a diagnosis derived from
  artifacts, the evidence WITH query citations that supports it, the proposed
  whitelist action and its parameters, the risk class and the autonomy level the
  action needs, a reversibility analysis, a rollback plan, a canary shape, and
  the human authorization the execution will require.

THE DESIGN CENTER this validator ENCODES, fail closed (the refusals are the
product, C1):

  A REMEDY IS A PROPOSAL, NEVER AN EXECUTION. Diagnosis and execution are
  separate organs. This contract is the diagnosis/proposal side; the execution
  organ is WARP-1206 (W6), not built here. The artifact carries NO execution
  capability at all: a remedy that claims to be self-executing or auto-applied,
  or whose status claims it already executed, is REFUSED by name. The responder
  emits a proposal; it structurally cannot say "and I ran it."

  A REMEDY NAMES ITS RISK CLASS AND ITS AUTONOMY LEVEL, and anything irreversible
  or data-mutating requires the strongest human authorization. The two-key rule
  itself (a recorded human authorization PLUS an independent fresh-context
  confirmation) is WARP-1207 (W7); this contract records that a remedy classed
  irreversible or data-mutating must declare required_authorization: two_key, so
  the two-key path downstream has something exact to bind to. A remedy that omits
  its rollback plan, or omits the required authorization, is REFUSED.

  A PROPOSAL MISSING ANY ELEMENT IS INVALID. Unknown kinds are rejected at
  contract time, so nothing malformed reaches the ladder, the executor, or the
  two-key path.

This module validates the artifacts STRUCTURALLY, the same way .veldo/decision.py
validates a decision record and .veldo/arch.py validates the architecture
contract: required fields present, closed vocabularies honored, an element
rejected at record time when it is absent, and every cross-artifact reference
resolving. A remedy binds to the incident it remediates (bind_remedy) and a
remedy whose incident does not resolve is refused (referenced but absent).

Two postures, both shared with the sibling contract organs:
  ADOPTION SAFE. A repository with no .veldo/incidents/ and no .veldo/remedies/
  directory is untouched: check_records stands down and returns clean, so a
  repository that never configures the responder is byte-identically unaffected.
  The moment a record exists it is validated and fails closed.
  FAIL CLOSED. A malformed record, an out-of-vocabulary status/severity/risk
  class/autonomy level/reversibility class/authorization, a timeline with no
  opened_at (or a diagnosed incident with no diagnosed_at, or a diagnosed_at
  before the opened_at), evidence with no query citation, a proposed action with
  no action reference or parameters, a remedy that claims self-execution, a
  remedy missing its rollback or its required authorization, an irreversible or
  data-mutating remedy not requiring two keys, a remedy whose incident does not
  resolve, and a duplicate id each REFUSE by name.

Dependency free by construction: the caller passes in the front-matter parser
and the failure reporter it already owns (validate.parse_yamlish and
validate.fail), so this module adds no second YAML parser and no import cycle,
exactly as decision.py and arch.py receive theirs. The evidence plane (W2), the
intent corpus (W3), the responder loop (W4), the action whitelist (W5), the
executor (W6), and the two-key rule (W7) are honestly later items; nothing here
pretends to do their work, and this contract carries no execution capability.
"""
from pathlib import Path

SCHEMA_INCIDENT = "veldo.incident/v1"
SCHEMA_REMEDY = "veldo.remedy/v1"

# The incident lifecycle status: an incident opens, is diagnosed from artifacts,
# and is closed by reconciliation (the compressed loop is WARP-1208, W8).
INCIDENT_STATUSES = {"open", "diagnosed", "closed"}
# Severity mirrors the risk tiers (validate.RISKS): the severity/risk class an
# incident carries, drawn from the one tier ladder the method already uses.
SEVERITIES = {"low", "standard", "high", "critical"}

# The remedy is a PROPOSAL: its status is drawn from a proposal-only vocabulary.
# No status can say the proposal executed - execution is a separate organ (W6).
REMEDY_STATUSES = {"proposed", "superseded", "withdrawn"}
# Statuses that would claim the proposal executed. A remedy carrying one is
# refused: the artifact has no execution capability, so it cannot have run.
EXECUTION_CLAIM_STATUSES = {"executed", "applied", "auto_applied", "auto-applied",
                            "running", "in_progress", "done"}
# Fields whose presence (truthy) would give the artifact an execution capability
# it must never have. A remedy carrying any of these is refused by name.
EXECUTION_CAPABILITY_FIELDS = ("self_executing", "auto_apply", "auto_applied",
                               "applied", "executed", "execute", "execution",
                               "run", "command", "shell")

RISK_CLASSES = {"low", "standard", "high", "critical"}
# The autonomy ladder (PLAN-0012 O3): L0 investigate, L1 propose, L2 whitelisted
# reversible with human confirmation, L3 autonomous (disabled by default, D2).
# A remedy names the level the proposed action needs; the ladder is enforced by
# the executor (W6), never here - this contract only closes the vocabulary.
AUTONOMY_LEVELS = {"L0", "L1", "L2", "L3"}
# Reversibility mirrors the reversal-cost class the decision record uses (D5's
# ladder), so "irreversible" means the same thing across the method.
REVERSIBILITY_CLASSES = {"reversible", "costly", "irreversible"}
# The human authorization the execution will require. A remedy always names one
# (a proposal is nothing until a human authorizes it); anything irreversible or
# data-mutating must name the strongest, two_key (the recorded human
# authorization plus the independent fresh-context confirmation, W7).
AUTHORIZATIONS = {"human_confirmation", "two_key"}

# The incident lifecycle the event vocabulary gains (PLAN-0012 W1). The contract
# owns this set; the emitter (.veldo/events.py) carries it and a selftest binds
# the two so they cannot drift. Emission and the gate's event-validator
# recognition are wired when incidents actually flow (WARP-1208, W8).
INCIDENT_EVENT_TYPES = {
    "incident.opened", "incident.diagnosed", "remedy.proposed", "incident.closed",
}


class IncidentContractError(ValueError):
    """An incident or remedy record is malformed. Raised by name so a bad record
    never silently no-ops (parallels DecisionRecordError and ArchContractError)."""


def default_incidents_dir(root=None):
    return Path(root or ".") / ".veldo" / "incidents"


def default_remedies_dir(root=None):
    return Path(root or ".") / ".veldo" / "remedies"


def _load(path, parse, kind):
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise IncidentContractError("%s record unreadable: %s" % (kind, e))
    try:
        data = parse(text)
    except ValueError as e:
        raise IncidentContractError("%s record outside the record subset: %s" % (kind, e))
    if not isinstance(data, dict):
        raise IncidentContractError("%s record must be a mapping at the top level" % kind)
    return data


def load_incident(path, parse):
    """Parse an incident record through the caller's front-matter parser (the VELDO
    yamlish subset). The single place an incident is read, so W4/W8 reuse it."""
    return _load(path, parse, "incident")


def load_remedy(path, parse):
    """Parse a remedy proposal through the caller's front-matter parser. The single
    place a remedy is read, so the executor's binding (W6/W7) reuses it."""
    return _load(path, parse, "remedy")


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _as_bool(v):
    """The value as a real boolean, or None when it is neither. The one front-matter
    parser (validate.parse_yamlish) leaves an unquoted true/false as the string
    "true"/"false" (it only coerces integers), so a boolean contract field arrives as
    that string; this accepts the string forms and a real bool and refuses anything
    else, so a truthy-looking value like "yes" or 1 is not silently accepted."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


def _iso_or_none(v):
    """The value as a comparable ISO-ish string, or None. Timeline ordering uses a
    lexicographic compare over ISO-8601 timestamps, which is monotonic for a fixed
    width; the check only needs "not before", not calendar math, so no dependency."""
    return v if _is_str(v) else None


def validate_incident(data, root, record_path, fail):
    """Structural validation of one parsed veldo.incident/v1 record. Reports each
    problem through fail(name, msg) and returns the error count. Pure over the dict,
    so it is reused by the directory scan and the single-file entry point.

    An incident is intent arriving from production. The record must name what broke
    (signal), the affected behavior, a severity from the tier ladder, a timeline
    with an opened_at, and a lifecycle status; a diagnosed or closed incident must
    carry a diagnosed_at that is not before the opened_at, so the time-to-diagnosis
    the metrics derive (WARP-1210) is real, not backdated."""
    errs = 0
    name = str(record_path)

    if data.get("schema") != SCHEMA_INCIDENT:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA_INCIDENT, data.get("schema")))
    for field in ("id", "title", "signal", "affected_behavior"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s" % field)

    status = data.get("status")
    if status not in INCIDENT_STATUSES:
        errs += fail(name, "status must be one of %s (got %r)" % (sorted(INCIDENT_STATUSES), status))
    severity = data.get("severity")
    if severity not in SEVERITIES:
        errs += fail(name, "severity must be one of %s (got %r): the severity/risk class an incident carries" % (sorted(SEVERITIES), severity))

    # Soft cross-plan join fields (C7): a spec or an architecture area the affected
    # behavior traces to, resolved against the corpus by the diagnosis (W3) and the
    # incidents-per-area map (W10). Here they are only required to be non-empty when
    # present; they are never faked and never resolved against a contract in W1.
    for opt in ("affected_spec", "affected_area"):
        if opt in data and not _is_str(data.get(opt)):
            errs += fail(name, "%s, when present, must be a non-empty string" % opt)

    # The timeline carries the time-to-diagnosis. opened_at is always required; a
    # diagnosed or closed incident must carry a diagnosed_at, and it may not predate
    # the opened_at (a negative time-to-diagnosis is a corrupt measure).
    timeline = data.get("timeline")
    if not isinstance(timeline, dict):
        errs += fail(name, "timeline is required: a mapping with at least opened_at (it carries the time-to-diagnosis)")
    else:
        opened = _iso_or_none(timeline.get("opened_at"))
        if opened is None:
            errs += fail(name, "timeline.opened_at is required (when the incident opened)")
        diagnosed = _iso_or_none(timeline.get("diagnosed_at"))
        if status in ("diagnosed", "closed") and diagnosed is None:
            errs += fail(name, "status %r requires timeline.diagnosed_at: a diagnosed incident records when the diagnosis was reached (time-to-diagnosis)" % status)
        if opened is not None and diagnosed is not None and diagnosed < opened:
            errs += fail(name, "timeline.diagnosed_at %r is before opened_at %r: the time-to-diagnosis cannot be negative" % (diagnosed, opened))
        restored = _iso_or_none(timeline.get("restored_at"))
        if opened is not None and restored is not None and restored < opened:
            errs += fail(name, "timeline.restored_at %r is before opened_at %r" % (restored, opened))

    return errs


def validate_remedy(data, root, record_path, fail):
    """Structural validation of one parsed veldo.remedy/v1 proposal. Reports each
    problem through fail(name, msg) and returns the error count. Pure over the dict.

    This is where the safety architecture becomes structural. A remedy is a PROPOSAL
    and carries no execution capability: a remedy that claims to be self-executing or
    auto-applied, or whose status claims it executed, is refused (the
    proposal-not-execution invariant). A proposal missing its rollback plan or its
    required authorization is refused (the two safety omissions). And anything
    irreversible or data-mutating must require two keys, so the two-key path (W7) has
    something exact to bind to."""
    errs = 0
    name = str(record_path)

    if data.get("schema") != SCHEMA_REMEDY:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA_REMEDY, data.get("schema")))
    for field in ("id", "incident", "diagnosis"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s" % field)

    # PROPOSAL-NOT-EXECUTION (the load-bearing safety invariant, O2/C4). The artifact
    # has no execution capability: it may not carry a self-execution or auto-apply
    # field, and its status may not claim it executed. Execution is a separate organ
    # on separate credentials (WARP-1206, W6); the responder proposes and stops.
    for f in EXECUTION_CAPABILITY_FIELDS:
        if f in data:
            errs += fail(name, "a remedy carries no execution capability: field %r is forbidden even set to false (a remedy is a PROPOSAL, never an execution; execution is a separate organ, WARP-1206 W6)" % f)
    status = data.get("status")
    if status in EXECUTION_CLAIM_STATUSES:
        errs += fail(name, "status %r claims the proposal executed: a remedy cannot execute itself (proposal-not-execution); allowed statuses are %s" % (status, sorted(REMEDY_STATUSES)))
    elif status not in REMEDY_STATUSES:
        errs += fail(name, "status must be one of %s (got %r): a remedy is a proposal" % (sorted(REMEDY_STATUSES), status))

    # The diagnosis comes from artifacts: the evidence is a non-empty list and each
    # entry carries a query citation (what artifact or query it rests on). Evidence
    # without a citation is an assertion, not a cited diagnosis.
    evidence = _as_list(data.get("evidence"))
    if not evidence:
        errs += fail(name, "no evidence: a remedy's diagnosis is derived from artifacts, each cited (a non-empty evidence list, every entry with a citation)")
    for i, e in enumerate(evidence):
        if not isinstance(e, dict) or not _is_str(e.get("citation")):
            errs += fail(name, "evidence entry %d needs a citation (the query or artifact it rests on): a diagnosis without citations is not derived from artifacts" % i)

    # The proposed WHITELIST action and its parameters (C4): the executor accepts a
    # whitelist action reference with validated parameters bound to a proposal
    # digest, never command text. Here the proposal must name the action and carry a
    # parameters mapping; the whitelist itself is WARP-1205 (W5).
    action = data.get("proposed_action")
    if not isinstance(action, dict):
        errs += fail(name, "proposed_action is required: a mapping naming the whitelist action and its parameters")
    else:
        if not _is_str(action.get("action")):
            errs += fail(name, "proposed_action.action is required (a whitelist action reference, never command text): the whitelist is WARP-1205 (W5)")
        if not isinstance(action.get("parameters"), dict):
            errs += fail(name, "proposed_action.parameters is required (a mapping of the action's validated parameters)")

    risk = data.get("risk_class")
    if risk not in RISK_CLASSES:
        errs += fail(name, "risk_class must be one of %s (got %r): a remedy names its risk class" % (sorted(RISK_CLASSES), risk))
    autonomy = data.get("autonomy_level")
    if autonomy not in AUTONOMY_LEVELS:
        errs += fail(name, "autonomy_level must be one of %s (got %r): a remedy names the autonomy level its action needs" % (sorted(AUTONOMY_LEVELS), autonomy))

    # Reversibility analysis: the class (mirroring the decision reversal-cost ladder),
    # a stated analysis, and whether the action mutates data. These feed the
    # authorization requirement below.
    rev = data.get("reversibility")
    rev_class, data_mutating = None, None
    if not isinstance(rev, dict):
        errs += fail(name, "reversibility is required: a mapping with a class, an analysis, and data_mutating")
    else:
        rev_class = rev.get("class")
        if rev_class not in REVERSIBILITY_CLASSES:
            errs += fail(name, "reversibility.class must be one of %s (got %r)" % (sorted(REVERSIBILITY_CLASSES), rev_class))
        if not _is_str(rev.get("analysis")):
            errs += fail(name, "reversibility.analysis is required (why the action is or is not reversible)")
        data_mutating = _as_bool(rev.get("data_mutating"))
        if data_mutating is None:
            errs += fail(name, "reversibility.data_mutating is required and must be true or false")

    # ROLLBACK PLAN (a safety omission that fails closed): a proposal that does not
    # say how to undo the action is invalid.
    if not _is_str(data.get("rollback")):
        errs += fail(name, "rollback is required: a remedy that omits its rollback plan is invalid (fail closed)")

    # Canary shape: whether the action runs a canary first and, if so, its shape.
    canary = data.get("canary")
    if not isinstance(canary, dict):
        errs += fail(name, "canary is required: a mapping declaring whether the action runs a canary first (supported) and its shape")
    else:
        supported = _as_bool(canary.get("supported"))
        if supported is None:
            errs += fail(name, "canary.supported is required and must be true or false")
        if supported is True and not _is_str(canary.get("shape")):
            errs += fail(name, "canary.shape is required when canary.supported is true (what the canary runs first)")

    # REQUIRED AUTHORIZATION (the second safety omission, and the two-key binding).
    # A proposal always names the human authorization its execution will require, and
    # anything irreversible or data-mutating must require two keys (the recorded human
    # authorization plus the independent fresh-context confirmation, WARP-1207 W7).
    auth = data.get("required_authorization")
    if auth not in AUTHORIZATIONS:
        errs += fail(name, "required_authorization is required and must be one of %s (got %r): a remedy names the human authorization its execution requires (fail closed)" % (sorted(AUTHORIZATIONS), auth))
    else:
        needs_two_key = (rev_class == "irreversible") or (data_mutating is True)
        if needs_two_key and auth != "two_key":
            errs += fail(name, "an irreversible or data-mutating remedy must set required_authorization: two_key (the recorded human authorization plus an independent fresh-context confirmation, WARP-1207 W7); got %r" % auth)

    return errs


def resolve_incident(incident_id, incidents_dir, parse, loader):
    """The parsed veldo.incident/v1 record whose id is incident_id under incidents_dir,
    or None when none resolves. Reads each record through the injected loader
    (load_incident, the one place a record is read) and matches on the incident schema
    and id, so a remedy-shaped file in the tree is never mistaken for an incident."""
    d = Path(incidents_dir)
    if not d.is_dir():
        return None
    for p in sorted(d.glob("*.yaml")):
        try:
            data = loader(p, parse)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("schema") == SCHEMA_INCIDENT and data.get("id") == incident_id:
            return data
    return None


def bind_remedy(remedy, incident, where, fail):
    """Cross-artifact binding: pair a remedy to the incident it remediates and FAIL
    CLOSED if the incident is malformed or absent. Pure over the two dicts. A remedy
    whose incident does not resolve is refused (referenced but absent), so a proposal
    can never float free of the incident it claims to remediate - the exact thing the
    two-key path (W7) needs to be able to trust."""
    if not isinstance(incident, dict):
        return fail(where, "remedy references incident %r which is malformed or absent (referenced but absent, fail closed)" % remedy.get("incident"))
    return 0


def check_incident(path, root, required, parse, fail):
    """Single-file entry point for an incident record. Absent file: stand down
    (adoption safe) unless required, then fail closed. Present: parse and validate."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "incident record is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_incident(p, parse)
    except IncidentContractError as e:
        return fail(str(p), str(e))
    return validate_incident(data, root, p, fail)


def check_remedy(path, root, required, parse, fail, incidents_dir=None):
    """Single-file entry point for a remedy proposal. Absent file: stand down unless
    required. Present: validate structurally, and when an incidents_dir is supplied
    also bind it to the incident it remediates, failing closed on anything malformed
    or unbound."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "remedy record is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_remedy(p, parse)
    except IncidentContractError as e:
        return fail(str(p), str(e))
    errs = validate_remedy(data, root, p, fail)
    if incidents_dir is not None:
        incident = resolve_incident(data.get("incident"), incidents_dir, parse, load_incident)
        errs += bind_remedy(data, incident, str(p), fail)
    return errs


def _scan_ids(d, loader, parse, schema):
    """id -> [filenames] for every record of the given schema in directory d."""
    ids = {}
    for p in sorted(Path(d).glob("*.yaml")):
        try:
            data = loader(p, parse)
        except IncidentContractError:
            continue  # already reported by the per-file check
        if isinstance(data, dict) and data.get("schema") == schema and _is_str(data.get("id")):
            ids.setdefault(data["id"], []).append(p.name)
    return ids


def check_records(incidents_dir, remedies_dir, root, parse, fail):
    """The gate entry point over the per-repo incident and remedy records. Adoption
    safe: with no .veldo/incidents/ AND no .veldo/remedies/ directory both stand down
    and this returns clean, so a repository that never configures the responder is
    byte-identically unaffected. Present records each fail closed on anything
    malformed; a duplicate id within either set is refused (an ambiguous reference);
    and every remedy binds to its incident (resolves, or referenced-but-absent
    refuses)."""
    idir, rdir = Path(incidents_dir), Path(remedies_dir)
    if not idir.is_dir() and not rdir.is_dir():
        return 0
    errs = 0
    if idir.is_dir():
        for p in sorted(idir.glob("*.yaml")):
            errs += check_incident(p, root, False, parse, fail)
        for iid, files in sorted(_scan_ids(idir, load_incident, parse, SCHEMA_INCIDENT).items()):
            if len(files) > 1:
                errs += fail(str(idir), "duplicate incident id %r across records: %s" % (iid, ", ".join(sorted(files))))
    if rdir.is_dir():
        for p in sorted(rdir.glob("*.yaml")):
            errs += check_remedy(p, root, False, parse, fail, incidents_dir=idir)
        for rid, files in sorted(_scan_ids(rdir, load_remedy, parse, SCHEMA_REMEDY).items()):
            if len(files) > 1:
                errs += fail(str(rdir), "duplicate remedy id %r across records: %s" % (rid, ", ".join(sorted(files))))
    return errs


def _cli(argv):
    """Standalone runner: validate a repository's incident and remedy records (or a
    single file) reusing validate.py's ONE front-matter parser and failure reporter,
    so there is no second YAML parser. This mirrors how validate.py invokes the
    sibling contract validators; wiring this into validate.py run_all is WARP-1211
    (W11, land the checks in the canonical engine)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("veldo_validate", here / "validate.py")
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    root = here.parent
    arg = argv[1] if len(argv) > 1 else None
    if arg and Path(arg).is_file():
        text = Path(arg).read_text()
        try:
            data = V.parse_yamlish(text)
        except ValueError as e:
            print("  %s: outside the record subset: %s" % (arg, e))
            return 1
        schema = data.get("schema") if isinstance(data, dict) else None
        if schema == SCHEMA_REMEDY:
            # Resolve the referenced incident from the remedy's OWN directory (a
            # co-located example) or the repository's incident records, whichever
            # declares it - the pattern validate.py uses for a co-located review.
            parent = Path(arg).resolve().parent
            repo_incidents = default_incidents_dir(root)
            idir = parent
            if (resolve_incident(data.get("incident"), parent, V.parse_yamlish, load_incident) is None
                    and repo_incidents.is_dir()):
                idir = repo_incidents
            errs = check_remedy(arg, root, False, V.parse_yamlish, V.fail, incidents_dir=idir)
        else:
            errs = check_incident(arg, root, False, V.parse_yamlish, V.fail)
    else:
        errs = check_records(default_incidents_dir(root), default_remedies_dir(root), root, V.parse_yamlish, V.fail)
    if errs:
        print("veldo incident/remedy contracts: %d problem(s)" % errs)
        return 1
    print("veldo incident/remedy contracts: clean")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))
