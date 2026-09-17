#!/usr/bin/env python3
"""Entity identity and lifecycle schemas for the project layer (PLAN-0019 W2, VELDO-0017).

WHAT THIS MODULE IS. Pure schemas and refusing predicates, a contract organ in the sense arch.py,
decision.py and policy_contract.py are: the identity envelope every new durable entity carries
(R04, R22), the lifecycle state vocabularies with their declared edges and entry predicates (R05,
R06, R11, R13, R18, R65), the ownership cardinality registry (R04, R10, R65), and the alias rules
(R04, R10, R73). Standard library only. It persists nothing, allocates nothing and starts nothing:
the store that commits transitions, the scheduler and the alias counter are Package B, F and H
work, and every function here answers a question about plain versioned data with an acceptance or
a refusal by name.

TWO VERSIONS, NEVER ONE. Every entity carries a `concurrency_version`, the monotonically increasing
number a transaction compares and bumps (R22). Entities whose scope can be revised carry a separate
scope revision field (a plan's `revision`, an admission request's `revision`, an objective's
`accepted_revision`): a scope-staleness value, never reused as the concurrency version. The
predicates below refuse the conflation in either direction.

TERMINAL HISTORY IS HISTORY. A terminal state has no outgoing edge; a record in one cannot be
rewritten; continuation after a terminal state is a NEW linked entity (R05, R11, R13).
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.entity_contract/v1"

# ---------------------------------------------------------------------------------------------
# AC1: the identity envelope.
# ---------------------------------------------------------------------------------------------

# EVERY DURABLE ENTITY TYPE the cited clauses introduce. The registry is compared with the fixture
# universe in both directions by the suite, so a type added to the design without a schema here,
# or a schema here for a type no clause names, is a problem by name.
ENTITY_TYPES = (
    "project", "objective", "backlog_item", "admission_request", "execution_unit", "attempt",
    "contract", "artifact", "receipt", "assignment", "station", "team_configuration", "dispatch",
    "decision", "reservation", "release_execution",
)

# The envelope (R04): coordination-domain UUID, entity type, globally unique UUID, schema version,
# creation provenance, monotonically increasing concurrency version; the repository UUID where the
# entity is repository-scoped.
IDENTITY_FIELDS = ("domain_uuid", "entity_type", "uuid", "schema_version", "provenance", "concurrency_version")
PROVENANCE_FIELDS = ("source", "created_by", "created_at")
REPOSITORY_SCOPED = frozenset({"backlog_item", "admission_request", "execution_unit", "attempt", "contract",
                               "dispatch", "reservation", "release_execution"})

# The SCOPE REVISION field of each entity type that has one, distinct from concurrency_version by
# construction: a scope change revises this field and never reuses an alias; a concurrency update
# bumps concurrency_version and never touches this field.
SCOPE_REVISION_FIELD = {
    "project": "charter_revision",
    "objective": "accepted_revision",
    "backlog_item": "decomposition_revision",
    "admission_request": "revision",
    "execution_unit": "admitted_revision",
    "team_configuration": "configuration_version",
    "release_execution": "release_revision",
}

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_PATH_LIKE = re.compile(r"[/\\]|^\.\.?$|^\.|\s|:")


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def is_uuid(v):
    return isinstance(v, str) and bool(_UUID.match(v.lower()))


def alias_problem(alias):
    """Why `alias` cannot be a readable identifier, or None (R04): an alias is a name a person
    reads, never a filesystem path (no separators, no dot-relative form, no whitespace, no drive
    or scheme colon) and never an authentication subject (no '@', no 'user:' or 'principal:'
    prefix). Existing WARP and VELDO identifiers all pass, unchanged."""
    if not _is_str(alias):
        return "an alias must be a non-empty string (got %r)" % (alias,)
    if _PATH_LIKE.search(alias):
        return "alias %r reads as a filesystem path or contains whitespace or a colon: an alias is a name, never a location" % alias
    if "@" in alias or alias.lower().startswith(("user:", "principal:", "actor:")):
        return "alias %r reads as an authentication subject: an alias is a name, never a principal" % alias
    return None


def identity_problems(entity):
    """The envelope problems of one entity dict, by name (R04, R22): unknown or missing type,
    missing or malformed identity fields, a repository-scoped type without repository_uuid, a
    malformed provenance, a non-positive concurrency version, an alias that is a path or a
    principal, and a scope revision that is missing where the type declares one or that is the
    same object as the concurrency version (the conflation R22 forbids, caught when a record
    carries the marker `concurrency_version_from` naming its scope field)."""
    problems = []
    if not isinstance(entity, dict):
        return ["an entity is a mapping (got %s)" % type(entity).__name__]
    etype = entity.get("entity_type")
    if etype not in ENTITY_TYPES:
        problems.append("unknown entity_type %r (known: %s)" % (etype, ", ".join(ENTITY_TYPES)))
    for f in IDENTITY_FIELDS:
        if f not in entity:
            problems.append("missing identity field %s" % f)
    for f in ("domain_uuid", "uuid"):
        if f in entity and not is_uuid(entity.get(f)):
            problems.append("%s must be a UUID (got %r)" % (f, entity.get(f)))
    if etype in REPOSITORY_SCOPED and not is_uuid(entity.get("repository_uuid")):
        problems.append("%s is repository-scoped and needs repository_uuid (got %r)" % (etype, entity.get("repository_uuid")))
    if "schema_version" in entity and not _is_pos_int(entity.get("schema_version")):
        problems.append("schema_version must be an integer >= 1")
    if "concurrency_version" in entity and not _is_pos_int(entity.get("concurrency_version")):
        problems.append("concurrency_version must be an integer >= 1: it is the number a transaction compares and bumps")
    prov = entity.get("provenance")
    if "provenance" in entity:
        if not isinstance(prov, dict):
            problems.append("provenance must be a mapping with %s" % ", ".join(PROVENANCE_FIELDS))
        else:
            for f in PROVENANCE_FIELDS:
                if not _is_str(prov.get(f)):
                    problems.append("provenance.%s is required" % f)
    if "alias" in entity:
        ap = alias_problem(entity.get("alias"))
        if ap:
            problems.append(ap)
    scope_field = SCOPE_REVISION_FIELD.get(etype)
    if scope_field:
        if not _is_pos_int(entity.get(scope_field)):
            problems.append("%s carries its scope revision in %s, which must be an integer >= 1" % (etype, scope_field))
        if entity.get("concurrency_version_from") == scope_field:
            problems.append("concurrency_version is taken from %s: a scope revision is a staleness value and is never the "
                            "concurrency version (R22)" % scope_field)
    return problems


def concurrency_update_problems(before, after):
    """A concurrency update (any committed transaction) bumps concurrency_version by exactly one,
    keeps the identity fields, the alias and the scope revision unchanged, and never rewrites a
    terminal record (R22)."""
    problems = identity_problems(after)
    for f in ("domain_uuid", "repository_uuid", "entity_type", "uuid", "schema_version", "alias"):
        if before.get(f) != after.get(f):
            problems.append("a concurrency update changed %s: identity is immutable" % f)
    if after.get("concurrency_version") != before.get("concurrency_version", 0) + 1:
        problems.append("concurrency_version must move from %r to %r, got %r: it increases by exactly one per committed "
                        "transaction and is never taken from a scope revision"
                        % (before.get("concurrency_version"), before.get("concurrency_version", 0) + 1, after.get("concurrency_version")))
    scope_field = SCOPE_REVISION_FIELD.get(before.get("entity_type"))
    if scope_field and before.get(scope_field) != after.get(scope_field):
        problems.append("a concurrency update changed %s: a scope revision moves only through a scope change" % scope_field)
    return problems


def scope_change_problems(before, after):
    """A scope change revises the scope field by exactly one, is itself a committed transaction
    (so concurrency_version bumps too), and never reuses the alias for a different scope: the
    alias stays, the revision moves (R04, R09, R22)."""
    scope_field = SCOPE_REVISION_FIELD.get(before.get("entity_type"))
    if not scope_field:
        return ["%s has no scope revision: nothing to change" % before.get("entity_type")]
    problems = identity_problems(after)
    for f in ("domain_uuid", "repository_uuid", "entity_type", "uuid", "schema_version", "alias"):
        if before.get(f) != after.get(f):
            problems.append("a scope change changed %s: identity and alias are preserved across revisions" % f)
    if after.get(scope_field) != before.get(scope_field, 0) + 1:
        problems.append("%s must move from %r to %r, got %r" % (scope_field, before.get(scope_field), before.get(scope_field, 0) + 1, after.get(scope_field)))
    if after.get("concurrency_version") != before.get("concurrency_version", 0) + 1:
        problems.append("a scope change is a transaction: concurrency_version must also move by exactly one")
    return problems


# ---------------------------------------------------------------------------------------------
# AC2: lifecycles. Declared edges with entry predicates; terminal states have no exits.
# ---------------------------------------------------------------------------------------------

# Each vocabulary: its states, its terminal states, and its edges as (source, destination,
# (required predicates...)). A predicate is the NAME of a fact the caller supplies as evidence
# (evidence[name] is True); the store that commits a transition checks the same names against
# receipts (Package B). Undeclared edges refuse; every edge out of a terminal state is undeclared
# by construction, asserted below.
LIFECYCLES = {
    "project": {  # R05
        "states": ("DRAFT", "ACTIVE", "PAUSED", "COMPLETED", "CANCELED"),
        "terminal": ("COMPLETED", "CANCELED"),
        "edges": (
            ("DRAFT", "ACTIVE", ("signed_charter", "resolvable_owner", "authority_policy_applies", "bounded_coordination_budget")),
            ("ACTIVE", "PAUSED", ("stop_policy_invoked",)),
            ("PAUSED", "ACTIVE", ("signed_charter", "resolvable_owner", "authority_policy_applies", "bounded_coordination_budget")),
            ("ACTIVE", "COMPLETED", ("objectives_terminal", "assignments_reconciled", "decisions_reconciled",
                                     "dispatches_reconciled", "release_executions_reconciled", "reservations_reconciled")),
            ("PAUSED", "COMPLETED", ("objectives_terminal", "assignments_reconciled", "decisions_reconciled",
                                     "dispatches_reconciled", "release_executions_reconciled", "reservations_reconciled")),
            ("DRAFT", "CANCELED", ("disposition_recorded",)),
            ("ACTIVE", "CANCELED", ("disposition_recorded",)),
            ("PAUSED", "CANCELED", ("disposition_recorded",)),
        ),
    },
    "objective": {  # R06
        "states": ("PROPOSED", "ACCEPTED", "ACTIVE", "BLOCKED", "SATISFIED", "REJECTED", "CANCELED"),
        "terminal": ("SATISFIED", "REJECTED", "CANCELED"),
        "edges": (
            ("PROPOSED", "ACCEPTED", ("acceptance_authority_signed",)),
            ("PROPOSED", "REJECTED", ("acceptance_authority_signed",)),
            ("ACCEPTED", "ACTIVE", ("contribution_linked",)),
            ("ACTIVE", "BLOCKED", ("blocker_recorded",)),
            ("BLOCKED", "ACTIVE", ("blocker_resolved",)),
            ("ACTIVE", "SATISFIED", ("signed_assessment_against_accepted_revision",)),
            ("PROPOSED", "CANCELED", ("disposition_recorded",)),
            ("ACCEPTED", "CANCELED", ("disposition_recorded",)),
            ("ACTIVE", "CANCELED", ("disposition_recorded",)),
            ("BLOCKED", "CANCELED", ("disposition_recorded",)),
        ),
    },
    "backlog_item": {  # R11, R12
        "states": ("RAW", "QUARANTINED", "PREPARED", "AWAITING_GROOMING", "REJECTED", "ADMITTED", "PRIORITIZED",
                   "ACTIVE", "BLOCKED", "DONE", "CANCELED"),
        "terminal": ("REJECTED", "DONE", "CANCELED"),
        "edges": (
            ("RAW", "PREPARED", ("intake_validated",)),
            ("RAW", "QUARANTINED", ("intake_unsafe_or_unresolved",)),
            ("QUARANTINED", "PREPARED", ("quarantine_resolved",)),
            ("PREPARED", "AWAITING_GROOMING", ("grooming_requested",)),
            ("PREPARED", "ADMITTED", ("signed_policy_admission",)),
            ("AWAITING_GROOMING", "ADMITTED", ("admission_authority_receipt",)),
            ("AWAITING_GROOMING", "REJECTED", ("admission_authority_receipt",)),
            ("AWAITING_GROOMING", "PREPARED", ("returned_for_elaboration",)),
            ("ADMITTED", "PRIORITIZED", ("priority_receipt",)),
            ("PRIORITIZED", "ACTIVE", ("first_unit_claimed",)),
            ("ACTIVE", "BLOCKED", ("blocker_recorded",)),
            ("BLOCKED", "ACTIVE", ("resolution_validated",)),
            ("ACTIVE", "DONE", ("required_units_completed_or_reconciled",)),
            ("RAW", "CANCELED", ("disposition_recorded",)),
            ("QUARANTINED", "CANCELED", ("disposition_recorded",)),
            ("PREPARED", "CANCELED", ("disposition_recorded",)),
            ("AWAITING_GROOMING", "CANCELED", ("disposition_recorded",)),
            ("ADMITTED", "CANCELED", ("disposition_recorded",)),
            ("PRIORITIZED", "CANCELED", ("disposition_recorded",)),
            ("ACTIVE", "CANCELED", ("disposition_recorded",)),
            ("BLOCKED", "CANCELED", ("disposition_recorded",)),
        ),
    },
    "execution_unit": {  # R13
        "states": ("PLANNED", "READY", "CLAIMED", "DISPATCHING", "RUNNING", "VERIFYING", "REVIEWING", "READY_TO_LAND",
                   "LANDING", "COMPLETED", "FAILED", "CANCELED", "AWAITING_AUTHORITY"),
        "terminal": ("COMPLETED", "CANCELED"),
        "edges": (
            ("PLANNED", "READY", ("primary_specification_revision_bound", "backlog_item_prioritized")),
            ("READY", "CLAIMED", ("claim_granted",)),
            ("CLAIMED", "DISPATCHING", ("contract_bound",)),
            ("DISPATCHING", "RUNNING", ("launch_receipt",)),
            ("RUNNING", "VERIFYING", ("build_receipt",)),
            ("VERIFYING", "REVIEWING", ("candidate_gate_green",)),
            ("REVIEWING", "READY_TO_LAND", ("review_receipt", "blocking_findings_disposed")),
            ("READY_TO_LAND", "LANDING", ("landing_authorized",)),
            ("LANDING", "COMPLETED", ("publication_receipt",)),
            ("DISPATCHING", "FAILED", ("failure_receipt",)),
            ("RUNNING", "FAILED", ("failure_receipt",)),
            ("VERIFYING", "FAILED", ("failure_receipt",)),
            ("REVIEWING", "FAILED", ("failure_receipt",)),
            ("LANDING", "FAILED", ("failure_receipt",)),
            ("FAILED", "READY", ("scope_unchanged", "previous_attempt_reconciled")),
            ("CLAIMED", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("DISPATCHING", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("RUNNING", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("VERIFYING", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("REVIEWING", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("READY_TO_LAND", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("LANDING", "AWAITING_AUTHORITY", ("interruption_recorded",)),
            ("AWAITING_AUTHORITY", "READY", ("resuming_authority_receipt", "outstanding_effects_reconciled")),
            ("AWAITING_AUTHORITY", "FAILED", ("failure_receipt",)),
            ("PLANNED", "CANCELED", ("disposition_recorded",)),
            ("READY", "CANCELED", ("disposition_recorded",)),
            ("CLAIMED", "CANCELED", ("disposition_recorded",)),
            ("DISPATCHING", "CANCELED", ("disposition_recorded",)),
            ("RUNNING", "CANCELED", ("disposition_recorded",)),
            ("VERIFYING", "CANCELED", ("disposition_recorded",)),
            ("REVIEWING", "CANCELED", ("disposition_recorded",)),
            ("READY_TO_LAND", "CANCELED", ("disposition_recorded",)),
            ("LANDING", "CANCELED", ("disposition_recorded",)),
            ("FAILED", "CANCELED", ("disposition_recorded",)),
            ("AWAITING_AUTHORITY", "CANCELED", ("disposition_recorded",)),
        ),
    },
    "assignment": {  # R18
        "states": ("OFFERED", "ACCEPTED", "IN_PROGRESS", "SUBMITTED", "SATISFIED", "DECLINED", "EXPIRED", "CANCELED"),
        "terminal": ("SATISFIED", "DECLINED", "EXPIRED", "CANCELED"),
        "edges": (
            ("OFFERED", "ACCEPTED", ("actor_predicate_satisfied",)),
            ("ACCEPTED", "IN_PROGRESS", ("work_started",)),
            ("IN_PROGRESS", "SUBMITTED", ("artifact_submitted",)),
            ("SUBMITTED", "SATISFIED", ("receipt_verified",)),
            ("SUBMITTED", "IN_PROGRESS", ("returned_with_findings",)),
            ("OFFERED", "DECLINED", ("actor_declined",)),
            ("OFFERED", "EXPIRED", ("deadline_passed",)),
            ("ACCEPTED", "EXPIRED", ("deadline_passed",)),
            ("IN_PROGRESS", "EXPIRED", ("deadline_passed",)),
            ("OFFERED", "CANCELED", ("disposition_recorded",)),
            ("ACCEPTED", "CANCELED", ("disposition_recorded",)),
            ("IN_PROGRESS", "CANCELED", ("disposition_recorded",)),
            ("SUBMITTED", "CANCELED", ("disposition_recorded",)),
        ),
    },
    "release_execution": {  # R65
        "states": ("PLANNED", "ACTIVE", "BLOCKED", "ACCEPTED", "CANCELED", "FAILED"),
        "terminal": ("ACCEPTED", "CANCELED", "FAILED"),
        "edges": (
            ("PLANNED", "ACTIVE", ("release_revision_accepted", "member_digests_resolved")),
            ("ACTIVE", "BLOCKED", ("blocker_recorded",)),
            ("BLOCKED", "ACTIVE", ("blocker_resolved",)),
            ("ACTIVE", "ACCEPTED", ("required_member_outcomes", "regression_receipts", "acceptance_authority_signed")),
            ("ACTIVE", "FAILED", ("failure_receipt",)),
            ("BLOCKED", "FAILED", ("failure_receipt",)),
            ("PLANNED", "CANCELED", ("disposition_recorded",)),
            ("ACTIVE", "CANCELED", ("disposition_recorded",)),
            ("BLOCKED", "CANCELED", ("disposition_recorded",)),
        ),
    },
}

# The design clauses each vocabulary closes against, so the suite asks the registry rather than
# a person which clause a vocabulary answers to.
LIFECYCLE_CLAUSES = {"project": "R05", "objective": "R06", "backlog_item": "R11", "execution_unit": "R13",
                     "assignment": "R18", "release_execution": "R65"}


def lifecycle_registry_problems():
    """The registry's own closure: every edge's endpoints are declared states, no edge leaves a
    terminal state, every non-terminal state has at least one exit, every edge carries at least
    one predicate, no edge is declared twice, and every vocabulary names its clause."""
    problems = []
    for name, lc in LIFECYCLES.items():
        states, terminal = set(lc["states"]), set(lc["terminal"])
        if not terminal <= states:
            problems.append("%s: terminal states %s are not declared states" % (name, sorted(terminal - states)))
        seen = set()
        exits = {s: 0 for s in states}
        for src, dst, preds in lc["edges"]:
            if src not in states or dst not in states:
                problems.append("%s: edge %s -> %s names an undeclared state" % (name, src, dst))
                continue
            if src in terminal:
                problems.append("%s: edge %s -> %s leaves a terminal state: terminal history cannot be reopened" % (name, src, dst))
            if not preds:
                problems.append("%s: edge %s -> %s has no entry predicate" % (name, src, dst))
            if (src, dst) in seen:
                problems.append("%s: edge %s -> %s is declared twice" % (name, src, dst))
            seen.add((src, dst))
            exits[src] += 1
        for s in sorted(states - terminal):
            if exits[s] == 0:
                problems.append("%s: non-terminal state %s has no exit" % (name, s))
        if name not in LIFECYCLE_CLAUSES:
            problems.append("%s names no design clause" % name)
    return problems


def transition_universe(vocabulary):
    """Every (source, destination) pair of a vocabulary, declared or not: the Cartesian product the
    suite drives, so an undeclared edge is found by enumeration rather than remembered."""
    states = LIFECYCLES[vocabulary]["states"]
    return [(s, d) for s in states for d in states if s != d]


def declared_edge(vocabulary, source, destination):
    for src, dst, preds in LIFECYCLES[vocabulary]["edges"]:
        if src == source and dst == destination:
            return preds
    return None


def transition(vocabulary, source, destination, evidence=None):
    """(allowed, reason) for one transition of one entity of `vocabulary` (R05, R06, R11, R13, R18,
    R65). Refuses by name: an unknown vocabulary or state, a terminal source (history is never
    reopened), an undeclared edge, and a declared edge whose entry predicates the evidence does
    not all establish (evidence[name] must be literally True; a truthy string is not a receipt)."""
    lc = LIFECYCLES.get(vocabulary)
    if lc is None:
        return False, "unknown lifecycle vocabulary %r (known: %s)" % (vocabulary, sorted(LIFECYCLES))
    for s in (source, destination):
        if s not in lc["states"]:
            return False, "%s: %r is not a declared state" % (vocabulary, s)
    if source in lc["terminal"]:
        return False, "%s: %s is terminal; terminal history is never reopened, continuation is a new linked entity" % (vocabulary, source)
    preds = declared_edge(vocabulary, source, destination)
    if preds is None:
        return False, "%s: %s -> %s is not a declared transition (%s)" % (vocabulary, source, destination, LIFECYCLE_CLAUSES[vocabulary])
    evidence = evidence or {}
    missing = [p for p in preds if evidence.get(p) is not True]
    if missing:
        return False, "%s: %s -> %s requires %s; missing %s" % (vocabulary, source, destination, ", ".join(preds), ", ".join(missing))
    return True, "%s: %s -> %s with %s" % (vocabulary, source, destination, ", ".join(preds))


def terminal_rewrite_problems(vocabulary, before, after):
    """A record in a terminal state may gain nothing but appended links (`links`) and a bumped
    concurrency version for that append: any other difference is a rewrite of terminal history and
    is refused by field name (R04, R13)."""
    lc = LIFECYCLES.get(vocabulary)
    if lc is None or before.get("state") not in lc["terminal"]:
        return []
    problems = []
    for k in sorted(set(before) | set(after)):
        if k in ("links", "concurrency_version"):
            continue
        if before.get(k) != after.get(k):
            problems.append("%s in terminal state %s: %s was rewritten; terminal history retains what happened under it"
                            % (vocabulary, before.get("state"), k))
    if not (after.get("links") or []) [len(before.get("links") or []):] and after != before and not problems:
        problems.append("%s in terminal state %s: a change that appends no link is a rewrite" % (vocabulary, before.get("state")))
    return problems


# ---------------------------------------------------------------------------------------------
# AC3: ownership cardinality and authorization.
# ---------------------------------------------------------------------------------------------

# Each relation: the owner type, the owned type, the field on the OWNED entity that names its
# owner(s), and how many owners an owned entity has, exactly (R04, R10, R18, R65). One project per
# objective, one objective per backlog item, one backlog item per unit, one primary specification
# per unit, one actor per assignment, one unit per attempt.
OWNERSHIP = (
    {"relation": "project_owns_objective", "owner": "project", "owned": "objective", "field": "project_uuid", "owners": 1, "clause": "R04"},
    {"relation": "objective_owns_backlog_item", "owner": "objective", "owned": "backlog_item", "field": "objective_uuid", "owners": 1, "clause": "R04"},
    {"relation": "backlog_item_owns_execution_unit", "owner": "backlog_item", "owned": "execution_unit", "field": "backlog_item_uuid", "owners": 1, "clause": "R04, R10"},
    {"relation": "unit_binds_primary_specification", "owner": "specification", "owned": "execution_unit", "field": "primary_specification", "owners": 1, "clause": "R10"},
    {"relation": "actor_holds_assignment", "owner": "actor", "owned": "assignment", "field": "actor", "owners": 1, "clause": "R18"},
    {"relation": "unit_owns_attempt", "owner": "execution_unit", "owned": "attempt", "field": "unit_uuid", "owners": 1, "clause": "R13"},
)
# Owner types that are not entities of this registry (a specification is a file with an alias, an
# actor is a principal): their references are checked for shape, never resolved to an entity.
EXTERNAL_OWNER_TYPES = frozenset({"specification", "actor"})


def _refs(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def ownership_problems(entities):
    """Every owned entity in `entities` names exactly the number of owners its relation declares,
    each resolving to an existing entity of the owner type (or, for an external owner, carrying a
    well-formed reference); two owners where one is declared is a duplicate by name. Also: two
    projects reached through two different backlog items for one unit (the R04 rule that two
    projects cannot own or execute the same unit), and two non-terminal engineering units for one
    admitted specification revision (R10)."""
    problems = []
    by_uuid = {e.get("uuid"): e for e in entities if isinstance(e, dict)}
    for rel in OWNERSHIP:
        for e in entities:
            if not isinstance(e, dict) or e.get("entity_type") != rel["owned"]:
                continue
            refs = _refs(e.get(rel["field"]))
            if len(refs) != rel["owners"]:
                problems.append("%s %s names %d owner(s) in %s; %s declares exactly %d (%s)"
                                % (rel["owned"], e.get("alias") or e.get("uuid"), len(refs), rel["field"], rel["relation"], rel["owners"], rel["clause"]))
                continue
            for r in refs:
                if rel["owner"] in EXTERNAL_OWNER_TYPES:
                    if rel["owner"] == "specification":
                        ok = isinstance(r, dict) and alias_problem(r.get("alias")) is None and _is_pos_int(r.get("revision"))
                        if not ok:
                            problems.append("%s %s: primary_specification must be {alias, revision} with a valid alias (R10)"
                                            % (rel["owned"], e.get("alias") or e.get("uuid")))
                    elif not (isinstance(r, dict) and _is_str(r.get("kind")) and _is_str(r.get("id"))):
                        problems.append("%s %s: actor must be {kind, id} (R18)" % (rel["owned"], e.get("alias") or e.get("uuid")))
                    continue
                owner = by_uuid.get(r)
                if owner is None or owner.get("entity_type") != rel["owner"]:
                    problems.append("%s %s names owner %r in %s, which is not an existing %s (referenced but absent)"
                                    % (rel["owned"], e.get("alias") or e.get("uuid"), r, rel["field"], rel["owner"]))
    # Two projects for one unit, through its items (R04).
    for e in entities:
        if isinstance(e, dict) and e.get("entity_type") == "execution_unit":
            projects = set()
            for item_ref in _refs(e.get("backlog_item_uuid")):
                item = by_uuid.get(item_ref) or {}
                objective = by_uuid.get(item.get("objective_uuid")) or {}
                if objective.get("project_uuid"):
                    projects.add(objective["project_uuid"])
            if len(projects) > 1:
                problems.append("execution_unit %s is owned by %d projects through its backlog items: two projects cannot own or "
                                "execute the same unit (R04)" % (e.get("alias") or e.get("uuid"), len(projects)))
    # Two active engineering units for one admitted specification revision (R10).
    active = {}
    for e in entities:
        if isinstance(e, dict) and e.get("entity_type") == "execution_unit" and e.get("state") not in LIFECYCLES["execution_unit"]["terminal"]:
            spec = e.get("primary_specification") or {}
            if isinstance(spec, dict):
                key = (spec.get("alias"), spec.get("revision"), e.get("admitted_revision"))
                active.setdefault(key, []).append(e.get("alias") or e.get("uuid"))
    for key, units in sorted(active.items(), key=str):
        if len(units) > 1 and key[0]:
            problems.append("%d active execution units (%s) for specification %s revision %r under admitted revision %r: there "
                            "cannot be two active engineering units for one admitted specification revision (R10)"
                            % (len(units), ", ".join(map(str, units)), key[0], key[1], key[2]))
    return problems


def transfer_problems(before, after, receipt):
    """An ownership transfer is an authorized transition with a receipt (R04): the owner field
    changes, nothing else of the identity does, the receipt names the authorizing principal and
    the transition, the concurrency version bumps, and the admission authority is NOT transferred
    with it (after.admission_authority equals before's)."""
    problems = []
    if not isinstance(receipt, dict) or not _is_str(receipt.get("authorized_by")) or receipt.get("transition") != "ownership_transfer":
        problems.append("an ownership transfer needs a receipt naming authorized_by and transition ownership_transfer (R04)")
    if receipt and isinstance(receipt, dict) and _is_str(receipt.get("authorized_by")) and receipt["authorized_by"].strip().lower() in (
            "agent", "bot", "ava", "machine", "automation", "service", "executor", "responder"):
        problems.append("an ownership transfer authorized by %r, a machine actor, is not authorized (R04)" % receipt["authorized_by"])
    if before.get("admission_authority") != after.get("admission_authority"):
        problems.append("the transfer changed admission_authority: a transfer never transfers admission authority implicitly (R04)")
    problems.extend(p for p in concurrency_update_problems(before, after) if "identity is immutable" not in p or "alias" in p)
    return problems


def retry_problems(unit, previous_attempt, new_attempt):
    """A permitted retry creates a NEW attempt under the same unit when the scope is unchanged and
    the previous attempt is reconciled (R13): same unit, a different attempt uuid, the same scope
    digest, a reconciled previous attempt (outcome recorded), and the previous attempt untouched."""
    problems = []
    if new_attempt.get("unit_uuid") != unit.get("uuid") or previous_attempt.get("unit_uuid") != unit.get("uuid"):
        problems.append("a retry binds the same unit: both attempts must name unit %s" % unit.get("uuid"))
    if new_attempt.get("uuid") == previous_attempt.get("uuid"):
        problems.append("a retry is a NEW attempt: the previous attempt is immutable and is never reused")
    if new_attempt.get("scope_digest") != previous_attempt.get("scope_digest") or new_attempt.get("scope_digest") != unit.get("scope_digest"):
        problems.append("a retry requires unchanged scope: the scope digest differs, so this is a new unit under a new prioritization, not a retry")
    if not _is_str(previous_attempt.get("outcome")) or previous_attempt.get("reconciled") is not True:
        problems.append("the previous attempt is not reconciled (outcome recorded and reconciled True): no retry before reconciliation")
    return problems


# ---------------------------------------------------------------------------------------------
# AC4: aliases and the canonical unit-id check before any artifact.
# ---------------------------------------------------------------------------------------------

def historical_aliases(root=None):
    """Every specification and plan identifier this repository already carries, read from the
    front matter of specs/*.md and plans/*.md (the id line), as a population rather than a
    pinned count: these are the aliases R04 says remain unchanged, and each must pass the alias
    rules byte for byte."""
    base = Path(root) if root else ROOT
    out = set()
    for d in ("specs", "plans"):
        for p in sorted((base / d).glob("*.md")):
            if p.name.startswith("TEMPLATE") or p.name == "index.md":
                continue
            try:
                head = p.read_text().split("\n---", 1)[0]
            except (OSError, UnicodeDecodeError):
                continue
            m = re.search(r"(?m)^id:\s*(\S+)\s*$", head)
            if m:
                out.add(m.group(1))
    return out


def envelope_for_alias(alias, entity_type, domain_uuid, uuid, provenance, repository_uuid=None):
    """The identity envelope wrapped around an existing readable identifier: the alias is carried
    BYTE FOR BYTE as `alias`, the identity is the uuid, and the alias is qualified by the
    repository outside it (R04). Refuses an alias that fails the alias rules."""
    ap = alias_problem(alias)
    if ap:
        raise ValueError(ap)
    env = {"domain_uuid": domain_uuid, "entity_type": entity_type, "uuid": uuid, "schema_version": 1,
           "provenance": dict(provenance), "concurrency_version": 1, "alias": alias}
    if repository_uuid:
        env["repository_uuid"] = repository_uuid
        env["qualified_alias"] = "%s:%s" % (repository_uuid, alias)
    return env


def _claim_module():
    spec = importlib.util.spec_from_file_location("veldo_claim_for_entities", ROOT / ".veldo" / "claim.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def admit_unit_artifact(unit_id, write, validator=None):
    """(admitted, reason): the Admission Service's one door for a unit artifact (R10, R73). The
    installed canonical validator, claim.unit_id_problem, is called with the proposed identifier
    BEFORE anything is written; any reported problem refuses admission and `write` is never
    called. No second spelling of the identifier rules lives here: `validator` defaults to the
    installed claim module's function and exists only so a fixture can spy on the order."""
    check = validator if validator is not None else _claim_module().unit_id_problem
    problem = check(unit_id)
    if problem:
        return False, "admission refused before any artifact was written: %s" % problem
    write(unit_id)
    return True, "unit %s admitted after the canonical identifier check" % unit_id
