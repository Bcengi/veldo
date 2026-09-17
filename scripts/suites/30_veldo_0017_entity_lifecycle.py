"""VELDO-0017: entity identity and lifecycle schemas (PLAN-0019 W2).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 30_veldo_0017_entity_lifecycle

WHAT IS UNDER TEST. .veldo/entity_contract.py: the identity envelope (AC1), the six lifecycle
vocabularies with declared edges and entry predicates (AC2), the ownership cardinality registry
(AC3) and the alias rules with the canonical unit-id check before any artifact (AC4). Every
registry is compared with a fixture universe in both directions, every Cartesian transition pair is
driven, and the four declared falsifiers are applied to a COPY of the module and required to turn
their named row red while the unmutated module passes it.
"""
import importlib.util as _v17_ilu
import shutil as _v17_shutil

_v17_spec = _v17_ilu.spec_from_file_location("v17_entity_contract", ROOT / ".veldo" / "entity_contract.py")
EC17 = _v17_ilu.module_from_spec(_v17_spec)
_v17_spec.loader.exec_module(EC17)
_v17_cspec = _v17_ilu.spec_from_file_location("v17_claim", ROOT / ".veldo" / "claim.py")
CL17 = _v17_ilu.module_from_spec(_v17_cspec)
_v17_cspec.loader.exec_module(CL17)

_V17_DOMAIN = "11111111-1111-4111-8111-111111111111"
_V17_REPO = "22222222-2222-4222-8222-222222222222"
_V17_PROV = {"source": "fixture", "created_by": "dmitry", "created_at": "2026-09-17T12:00:00Z"}


def _v17_uuid(n):
    return "%08x-0000-4000-8000-%012x" % (n, n)


def _v17_entity(etype, n, **extra):
    """A valid entity of `etype` with every envelope field, the repository uuid where scoped, and the
    scope revision where the type declares one."""
    e = {"domain_uuid": _V17_DOMAIN, "entity_type": etype, "uuid": _v17_uuid(n), "schema_version": 1,
         "provenance": dict(_V17_PROV), "concurrency_version": 1, "alias": "%s-%03d" % (etype.upper()[:4], n)}
    if etype in EC17.REPOSITORY_SCOPED:
        e["repository_uuid"] = _V17_REPO
    sf = EC17.SCOPE_REVISION_FIELD.get(etype)
    if sf:
        e[sf] = 1
    e.update(extra)
    return e


def _v17_mutated(old, new, count=1):
    """The contract module with ONE textual mutation applied to a copy under a temporary directory,
    loaded from there; the original is never touched."""
    d = Path(tempfile.mkdtemp(prefix="v17mut"))
    src = (ROOT / ".veldo" / "entity_contract.py").read_text()
    assert src.count(old) == count, (old[:60], src.count(old))
    (d / "entity_contract.py").write_text(src.replace(old, new))
    spec = _v17_ilu.spec_from_file_location("v17_mut_%s" % d.name, d / "entity_contract.py")
    m = _v17_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v17_shutil.rmtree(d, ignore_errors=True)
    return m


# ---------------------------------------------------------------------------------------------
# AC1: the identity envelope.
# ---------------------------------------------------------------------------------------------
_V17_UNIVERSE = {"project", "objective", "backlog_item", "admission_request", "execution_unit", "attempt", "contract",
                 "artifact", "receipt", "assignment", "station", "team_configuration", "dispatch", "decision",
                 "reservation", "release_execution"}
_v17_fixtures = {t: _v17_entity(t, i + 1) for i, t in enumerate(sorted(_V17_UNIVERSE))}
expect("VELDO-0017 AC1 entity-schema/registry: the entity type registry equals the schema universe the cited clauses "
       "name (sixteen types) in both directions, and a valid fixture of every type passes the envelope",
       set(EC17.ENTITY_TYPES) == _V17_UNIVERSE and len(EC17.ENTITY_TYPES) == 16
       and all(EC17.identity_problems(e) == [] for e in _v17_fixtures.values()))
_v17_missing = {}
for _v17_t, _v17_e in sorted(_v17_fixtures.items()):
    for _v17_f in EC17.IDENTITY_FIELDS:
        _v17_bad = {k: v for k, v in _v17_e.items() if k != _v17_f}
        if not any(_v17_f in p for p in EC17.identity_problems(_v17_bad)):
            _v17_missing[(_v17_t, _v17_f)] = EC17.identity_problems(_v17_bad)
expect("VELDO-0017 AC1 entity-schema/required-fields: removing each identity field from each of the sixteen fixtures "
       "in turn is refused naming the field (%d of %d removals)" % (16 * len(EC17.IDENTITY_FIELDS) - len(_v17_missing), 16 * len(EC17.IDENTITY_FIELDS)),
       _v17_missing == {})
expect("VELDO-0017 AC1 entity-schema/envelope: a repository-scoped type without repository_uuid, a malformed uuid, a "
       "non-positive concurrency version, a provenance missing created_by, and a path-like or principal-like alias "
       "are each refused by name; an unscoped type needs no repository uuid",
       any("repository_uuid" in p for p in EC17.identity_problems({k: v for k, v in _v17_fixtures["execution_unit"].items() if k != "repository_uuid"}))
       and any("uuid must be a UUID" in p for p in EC17.identity_problems(dict(_v17_fixtures["project"], uuid="not-a-uuid")))
       and any("concurrency_version" in p for p in EC17.identity_problems(dict(_v17_fixtures["project"], concurrency_version=0)))
       and any("provenance.created_by" in p for p in EC17.identity_problems(dict(_v17_fixtures["project"], provenance={"source": "x", "created_at": "y"})))
       and any("filesystem path" in p for p in EC17.identity_problems(dict(_v17_fixtures["project"], alias="specs/VELDO-0017.md")))
       and any("authentication subject" in p for p in EC17.identity_problems(dict(_v17_fixtures["project"], alias="dmitry@bcengi.com")))
       and EC17.identity_problems(_v17_fixtures["project"]) == [] and "repository_uuid" not in _v17_fixtures["project"])

# Version separation: a concurrency update moves only concurrency_version; a scope change moves the
# scope revision and, being a transaction, the concurrency version; the alias never changes.
_v17_u = _v17_fixtures["execution_unit"]
_v17_u2 = dict(_v17_u, concurrency_version=2, state="READY")
_v17_u3 = dict(_v17_u, concurrency_version=2, admitted_revision=2)
expect("VELDO-0017 AC1 entity-schema/version-separation: a concurrency update bumps concurrency_version by exactly one "
       "and leaves the scope revision and alias alone; a scope change moves the scope revision by one WITH a "
       "concurrency bump and keeps the alias; a concurrency update that also moved the scope revision, an update "
       "that did not bump, a scope change that reused a different alias, and a record whose concurrency version is "
       "taken from its scope revision are each refused",
       EC17.concurrency_update_problems(_v17_u, _v17_u2) == []
       and EC17.scope_change_problems(_v17_u, _v17_u3) == []
       and any("scope revision moves only through a scope change" in p for p in EC17.concurrency_update_problems(_v17_u, _v17_u3))
       and any("increases by exactly one" in p for p in EC17.concurrency_update_problems(_v17_u, dict(_v17_u, state="READY")))
       and any("alias" in p for p in EC17.scope_change_problems(_v17_u, dict(_v17_u3, alias="EXEC-999")))
       and any("never the concurrency version (R22)" in p
               for p in EC17.identity_problems(dict(_v17_u, concurrency_version_from="admitted_revision"))))
# A store that takes the plan revision as the concurrency version: two committed updates without a
# scope change leave the version where the revision is, so the second update does not move it.
_v17_store_before = dict(_v17_u, concurrency_version=1, admitted_revision=1)
_v17_store_after = dict(_v17_store_before, state="READY")          # revision unchanged -> version unchanged
expect("VELDO-0017 AC1 entity-schema/version-separation: a store that uses the plan revision as the concurrency version "
       "cannot bump on a transaction that revises no scope, and that update is refused",
       any("increases by exactly one" in p for p in EC17.concurrency_update_problems(_v17_store_before, _v17_store_after)))
# THE DECLARED FALSIFIER: remove the conflation refusal from a copy; the version-separation row reds.
_V17_M1 = _v17_mutated('''        if entity.get("concurrency_version_from") == scope_field:
''', '''        if False:
''')
expect("VELDO-0017 AC1 entity-schema/version-separation DRIVEN (the declared falsifier): with the conflation refusal "
       "removed, a record whose concurrency version is taken from its scope revision passes the envelope, so the "
       "row reds; unmutated it is refused",
       _V17_M1.identity_problems(dict(_v17_u, concurrency_version_from="admitted_revision")) == []
       and EC17.identity_problems(dict(_v17_u, concurrency_version_from="admitted_revision")) != [])

# ---------------------------------------------------------------------------------------------
# AC2: lifecycles over the Cartesian universe.
# ---------------------------------------------------------------------------------------------
_V17_STATES = {
    "project": {"DRAFT", "ACTIVE", "PAUSED", "COMPLETED", "CANCELED"},
    "objective": {"PROPOSED", "ACCEPTED", "ACTIVE", "BLOCKED", "SATISFIED", "REJECTED", "CANCELED"},
    "backlog_item": {"RAW", "QUARANTINED", "PREPARED", "AWAITING_GROOMING", "REJECTED", "ADMITTED", "PRIORITIZED",
                     "ACTIVE", "BLOCKED", "DONE", "CANCELED"},
    "execution_unit": {"PLANNED", "READY", "CLAIMED", "DISPATCHING", "RUNNING", "VERIFYING", "REVIEWING", "READY_TO_LAND",
                       "LANDING", "COMPLETED", "FAILED", "CANCELED", "AWAITING_AUTHORITY"},
    "assignment": {"OFFERED", "ACCEPTED", "IN_PROGRESS", "SUBMITTED", "SATISFIED", "DECLINED", "EXPIRED", "CANCELED"},
    "release_execution": {"PLANNED", "ACTIVE", "BLOCKED", "ACCEPTED", "CANCELED", "FAILED"},
}
expect("VELDO-0017 AC2 lifecycle/registry: the six vocabularies are exactly R05, R06, R11, R13, R18 and R65 with the "
       "state sets those clauses spell (assignment carrying its declined, expired and canceled outcomes), and the "
       "registry closes: every edge between declared states, no edge out of a terminal state, every non-terminal "
       "state with an exit, every edge with a predicate (problems: %s)" % EC17.lifecycle_registry_problems(),
       set(EC17.LIFECYCLES) == set(_V17_STATES) and EC17.lifecycle_registry_problems() == []
       and all(set(EC17.LIFECYCLES[v]["states"]) == s for v, s in _V17_STATES.items())
       and EC17.LIFECYCLE_CLAUSES == {"project": "R05", "objective": "R06", "backlog_item": "R11",
                                      "execution_unit": "R13", "assignment": "R18", "release_execution": "R65"})
_v17_bad_pairs = []
_v17_pairs = 0
for _v17_v in sorted(EC17.LIFECYCLES):
    _v17_terminal = set(EC17.LIFECYCLES[_v17_v]["terminal"])
    for _v17_s, _v17_d in EC17.transition_universe(_v17_v):
        _v17_pairs += 1
        _v17_preds = EC17.declared_edge(_v17_v, _v17_s, _v17_d)
        if _v17_preds is None:
            _v17_ok, _v17_why = EC17.transition(_v17_v, _v17_s, _v17_d, {p: True for l in EC17.LIFECYCLES.values() for e in l["edges"] for p in e[2]})
            if _v17_ok or not ("not a declared transition" in _v17_why or "terminal" in _v17_why):
                _v17_bad_pairs.append((_v17_v, _v17_s, _v17_d, "undeclared edge not refused: %s" % _v17_why))
            continue
        if _v17_s in _v17_terminal:
            _v17_bad_pairs.append((_v17_v, _v17_s, _v17_d, "edge out of a terminal state"))
            continue
        if not EC17.transition(_v17_v, _v17_s, _v17_d, {p: True for p in _v17_preds})[0]:
            _v17_bad_pairs.append((_v17_v, _v17_s, _v17_d, "declared edge refused with every predicate"))
        for _v17_p in _v17_preds:
            _v17_ev = {q: True for q in _v17_preds if q != _v17_p}
            _v17_ev[_v17_p] = "yes"  # a truthy string is not a receipt
            _v17_ok, _v17_why = EC17.transition(_v17_v, _v17_s, _v17_d, _v17_ev)
            if _v17_ok or _v17_p not in _v17_why:
                _v17_bad_pairs.append((_v17_v, _v17_s, _v17_d, "predicate %s absent yet allowed or unnamed" % _v17_p))
expect("VELDO-0017 AC2 lifecycle/universe: over all %d Cartesian pairs of the six vocabularies every declared edge is "
       "allowed with its predicates, refused naming each predicate absent in turn (a truthy string is not a "
       "receipt), every undeclared edge refuses, and every edge out of a terminal state refuses as terminal "
       "(failures: %s)" % (_v17_pairs, _v17_bad_pairs[:5]),
       _v17_pairs >= 400 and _v17_bad_pairs == [])
expect("VELDO-0017 AC2 lifecycle/backlog-direct-execution: RAW -> ACTIVE is not a declared transition (no dispatch from "
       "intake, R11), nor RAW -> ADMITTED, PREPARED -> PRIORITIZED or ADMITTED -> ACTIVE; the declared path is "
       "RAW -> PREPARED -> AWAITING_GROOMING -> ADMITTED -> PRIORITIZED -> ACTIVE",
       EC17.transition("backlog_item", "RAW", "ACTIVE", {"intake_validated": True, "first_unit_claimed": True})[0] is False
       and EC17.transition("backlog_item", "RAW", "ADMITTED", {"admission_authority_receipt": True})[0] is False
       and EC17.transition("backlog_item", "PREPARED", "PRIORITIZED", {"priority_receipt": True})[0] is False
       and EC17.transition("backlog_item", "ADMITTED", "ACTIVE", {"first_unit_claimed": True})[0] is False
       and all(EC17.transition("backlog_item", s, d, {p: True})[0] for s, d, p in (
           ("RAW", "PREPARED", "intake_validated"), ("PREPARED", "AWAITING_GROOMING", "grooming_requested"),
           ("AWAITING_GROOMING", "ADMITTED", "admission_authority_receipt"), ("ADMITTED", "PRIORITIZED", "priority_receipt"),
           ("PRIORITIZED", "ACTIVE", "first_unit_claimed"))))
# THE DECLARED FALSIFIER: permit RAW -> ACTIVE in a copy; the row reds.
_V17_M2 = _v17_mutated('''            ("RAW", "PREPARED", ("intake_validated",)),
''', '''            ("RAW", "PREPARED", ("intake_validated",)),
            ("RAW", "ACTIVE", ("intake_validated",)),
''')
expect("VELDO-0017 AC2 lifecycle/backlog-direct-execution DRIVEN (the declared falsifier): with RAW -> ACTIVE declared "
       "in a copy, the transition is allowed, so the row reds; unmutated it is refused as undeclared",
       _V17_M2.transition("backlog_item", "RAW", "ACTIVE", {"intake_validated": True})[0] is True
       and EC17.transition("backlog_item", "RAW", "ACTIVE", {"intake_validated": True})[0] is False)
_v17_done = _v17_entity("execution_unit", 90, state="COMPLETED", links=[])
expect("VELDO-0017 AC2 lifecycle/terminal-history: a record in a terminal state may gain an appended link, and any other "
       "change (a rewritten field, a state change, a change that appends nothing) is refused by field name",
       EC17.terminal_rewrite_problems("execution_unit", _v17_done, dict(_v17_done, links=["VELDO-0018"], concurrency_version=2)) == []
       and any("state was rewritten" in p for p in EC17.terminal_rewrite_problems("execution_unit", _v17_done, dict(_v17_done, state="READY")))
       and any("scope_digest was rewritten" in p for p in EC17.terminal_rewrite_problems("execution_unit", _v17_done, dict(_v17_done, scope_digest="x")))
       and EC17.terminal_rewrite_problems("execution_unit", dict(_v17_done, state="READY"), dict(_v17_done, state="CLAIMED")) == [])

# ---------------------------------------------------------------------------------------------
# AC3: ownership cardinality and authorization.
# ---------------------------------------------------------------------------------------------
_v17_P = _v17_entity("project", 100)
_v17_P2 = _v17_entity("project", 101)
_v17_O = _v17_entity("objective", 110, project_uuid=_v17_P["uuid"])
_v17_O2 = _v17_entity("objective", 111, project_uuid=_v17_P2["uuid"])
_v17_I = _v17_entity("backlog_item", 120, objective_uuid=_v17_O["uuid"])
_v17_I2 = _v17_entity("backlog_item", 121, objective_uuid=_v17_O2["uuid"])
_v17_SPEC = {"alias": "VELDO-0017", "revision": 1}
_v17_U = _v17_entity("execution_unit", 130, backlog_item_uuid=_v17_I["uuid"], primary_specification=_v17_SPEC,
                     state="READY", scope_digest="sha256:aaa", admission_authority="dmitry")
_v17_A = _v17_entity("attempt", 140, unit_uuid=_v17_U["uuid"], scope_digest="sha256:aaa", outcome="failed", reconciled=True)
_v17_S = _v17_entity("assignment", 150, actor={"kind": "agent", "id": "worker-1"})
_v17_graph = [_v17_P, _v17_P2, _v17_O, _v17_O2, _v17_I, _v17_I2, _v17_U, _v17_A, _v17_S]
expect("VELDO-0017 AC3 ownership/registry: the cardinality registry covers project-objective, objective-item, item-unit, "
       "unit-primary-specification, actor-assignment and unit-attempt, each with exactly one owner, and a well-formed "
       "graph has no problem (%s)" % EC17.ownership_problems(_v17_graph),
       {r["relation"] for r in EC17.OWNERSHIP} == {"project_owns_objective", "objective_owns_backlog_item",
                                                   "backlog_item_owns_execution_unit", "unit_binds_primary_specification",
                                                   "actor_holds_assignment", "unit_owns_attempt"}
       and all(r["owners"] == 1 for r in EC17.OWNERSHIP) and EC17.ownership_problems(_v17_graph) == [])
_v17_zero = [e for e in _v17_graph if e is not _v17_U] + [dict(_v17_U, backlog_item_uuid=None)]
_v17_dup = [e for e in _v17_graph if e is not _v17_U] + [dict(_v17_U, backlog_item_uuid=[_v17_I["uuid"], _v17_I2["uuid"]])]
_v17_dangling = [e for e in _v17_graph if e is not _v17_U] + [dict(_v17_U, backlog_item_uuid=_v17_uuid(999))]
_v17_two_active = _v17_graph + [_v17_entity("execution_unit", 131, backlog_item_uuid=_v17_I["uuid"], primary_specification=_v17_SPEC,
                                            state="RUNNING", scope_digest="sha256:aaa", admission_authority="dmitry")]
_v17_one_terminal = _v17_graph + [_v17_entity("execution_unit", 132, backlog_item_uuid=_v17_I["uuid"], primary_specification=_v17_SPEC,
                                              state="COMPLETED", scope_digest="sha256:aaa", admission_authority="dmitry")]
expect("VELDO-0017 AC3 ownership/cardinality: a unit with zero owners, a unit with two backlog items, a unit whose item "
       "does not exist, an assignment with a malformed actor, a unit with a path-like primary specification alias, "
       "and two active units for one admitted specification revision are each refused by name; a second unit that is "
       "terminal is not a duplicate",
       any("names 0 owner(s)" in p for p in EC17.ownership_problems(_v17_zero))
       and any("names 2 owner(s)" in p for p in EC17.ownership_problems(_v17_dup))
       and any("referenced but absent" in p for p in EC17.ownership_problems(_v17_dangling))
       and any("actor must be" in p for p in EC17.ownership_problems([dict(_v17_S, actor="worker-1")]))
       and any("primary_specification must be" in p for p in EC17.ownership_problems([e for e in _v17_graph if e is not _v17_U]
                                                                                     + [dict(_v17_U, primary_specification={"alias": "specs/x.md", "revision": 1})]))
       and any("cannot be two active engineering units" in p for p in EC17.ownership_problems(_v17_two_active))
       and EC17.ownership_problems(_v17_one_terminal) == [])
expect("VELDO-0017 AC3 ownership/duplicate-project: a unit reached by two projects through two backlog items is refused "
       "as owned by two projects (R04), on top of its duplicate-owner refusal",
       any("owned by 2 projects" in p for p in EC17.ownership_problems(_v17_dup)))
# THE DECLARED FALSIFIER: allow a second project to own the same unit (two owners per unit and no
# two-projects check) in a copy; the duplicate-project row reds.
_V17_M3 = _v17_mutated('''    {"relation": "backlog_item_owns_execution_unit", "owner": "backlog_item", "owned": "execution_unit", "field": "backlog_item_uuid", "owners": 1, "clause": "R04, R10"},
''', '''    {"relation": "backlog_item_owns_execution_unit", "owner": "backlog_item", "owned": "execution_unit", "field": "backlog_item_uuid", "owners": 2, "clause": "R04, R10"},
''')
_v17_src = (ROOT / ".veldo" / "entity_contract.py").read_text()
_V17_M3b = _v17_mutated('''            if len(projects) > 1:
''', '''            if False:
''')
expect("VELDO-0017 AC3 ownership/duplicate-project DRIVEN (the declared falsifier): with two owners per unit declared the "
       "cardinality refusal disappears and only the two-projects rule still refuses; with that rule removed too the "
       "second project owns the unit, so the row reds; unmutated both refuse",
       not any("names 2 owner(s)" in p for p in _V17_M3.ownership_problems(_v17_dup))
       and any("owned by 2 projects" in p for p in _V17_M3.ownership_problems(_v17_dup))
       and not any("owned by 2 projects" in p for p in _V17_M3b.ownership_problems(_v17_dup))
       and any("owned by 2 projects" in p for p in EC17.ownership_problems(_v17_dup)))
_v17_retry = _v17_entity("attempt", 141, unit_uuid=_v17_U["uuid"], scope_digest="sha256:aaa")
expect("VELDO-0017 AC3 ownership/retry: an unchanged-scope retry after a reconciled attempt is a new attempt under the same "
       "unit; a changed scope, an unreconciled previous attempt, a reused attempt uuid and a different unit are each "
       "refused by name",
       EC17.retry_problems(_v17_U, _v17_A, _v17_retry) == []
       and any("unchanged scope" in p for p in EC17.retry_problems(_v17_U, _v17_A, dict(_v17_retry, scope_digest="sha256:bbb")))
       and any("not reconciled" in p for p in EC17.retry_problems(_v17_U, dict(_v17_A, reconciled=False), _v17_retry))
       and any("never reused" in p for p in EC17.retry_problems(_v17_U, _v17_A, dict(_v17_retry, uuid=_v17_A["uuid"])))
       and any("same unit" in p for p in EC17.retry_problems(_v17_U, _v17_A, dict(_v17_retry, unit_uuid=_v17_uuid(5)))))
_v17_moved = dict(_v17_I, objective_uuid=_v17_O2["uuid"], concurrency_version=2)
_v17_receipt = {"authorized_by": "dmitry", "transition": "ownership_transfer"}
expect("VELDO-0017 AC3 ownership/transfer: an ownership transfer with an authorizing person's receipt and a concurrency bump "
       "is allowed; no receipt, a machine authorizer, a transfer that also moved admission_authority, and a transfer "
       "without a concurrency bump are each refused by name",
       EC17.transfer_problems(_v17_I, _v17_moved, _v17_receipt) == []
       and any("needs a receipt" in p for p in EC17.transfer_problems(_v17_I, _v17_moved, None))
       and any("machine actor" in p for p in EC17.transfer_problems(_v17_I, _v17_moved, {"authorized_by": "agent", "transition": "ownership_transfer"}))
       and any("admission authority implicitly" in p for p in EC17.transfer_problems(dict(_v17_I, admission_authority="dmitry"),
                                                                                       dict(_v17_moved, admission_authority="agent"), _v17_receipt))
       and any("exactly one" in p for p in EC17.transfer_problems(_v17_I, dict(_v17_moved, concurrency_version=1), _v17_receipt)))

# ---------------------------------------------------------------------------------------------
# AC4: aliases and the canonical unit-id check before any artifact.
# ---------------------------------------------------------------------------------------------
_v17_corpus = EC17.historical_aliases(ROOT)
_v17_envelopes = {a: EC17.envelope_for_alias(a, "execution_unit", _V17_DOMAIN, _v17_uuid(7), _V17_PROV, _V17_REPO) for a in _v17_corpus}
expect("VELDO-0017 AC4 identity/historical-aliases: every WARP, VELDO and PLAN identifier this repository carries (%d, a "
       "population, never a pinned count) passes the alias rules and is carried BYTE FOR BYTE as the alias of its "
       "envelope, qualified by the repository outside it, with the uuid as the identity" % len(_v17_corpus),
       len(_v17_corpus) > 100 and all(EC17.alias_problem(a) is None for a in _v17_corpus)
       and all(_v17_envelopes[a]["alias"] == a and _v17_envelopes[a]["alias"].encode() == a.encode() for a in _v17_corpus)
       and all(_v17_envelopes[a]["qualified_alias"] == "%s:%s" % (_V17_REPO, a) and _v17_envelopes[a]["uuid"] == _v17_uuid(7) for a in _v17_corpus)
       and any(a.startswith("WARP-") for a in _v17_corpus) and any(a.startswith("VELDO-") for a in _v17_corpus)
       and any(a.startswith("PLAN-") for a in _v17_corpus))
expect("VELDO-0017 AC4 identity/alias-rules: an alias is never a filesystem path (a separator, a dot-relative form, "
       "whitespace, a colon) nor an authentication subject (an at-sign, a principal prefix), and the envelope refuses "
       "to wrap one",
       all(EC17.alias_problem(a) for a in ("specs/VELDO-0017.md", "..", ".hidden", "a b", "C:x", "dmitry@bcengi.com", "user:dmitry", "", None))
       and EC17.alias_problem("VELDO-0017") is None)
try:
    EC17.envelope_for_alias("a/b", "execution_unit", _V17_DOMAIN, _v17_uuid(8), _V17_PROV)
    _v17_wrapped_path = True
except ValueError:
    _v17_wrapped_path = False
expect("VELDO-0017 AC4 identity/alias-rules: wrapping a path-like alias in an envelope raises", _v17_wrapped_path is False)

# The canonical unit-id check BEFORE any artifact write: the spy records the order.
_v17_calls = []
_v17_spy_validator = lambda u: (_v17_calls.append(("validate", u)), CL17.unit_id_problem(u))[1]
_v17_spy_write = lambda u: _v17_calls.append(("write", u))
_v17_ok1, _ = EC17.admit_unit_artifact("VELDO-0017-U1", _v17_spy_write, validator=_v17_spy_validator)
_v17_ok2, _v17_why2 = EC17.admit_unit_artifact("bad/id", _v17_spy_write, validator=_v17_spy_validator)
expect("VELDO-0017 AC4 identity/canonical-unit-validation: admission calls the canonical validator BEFORE the artifact "
       "write for a good id (order recorded), and for a bad id refuses naming the problem with the write never "
       "called; the default validator IS claim.unit_id_problem (same answer over good and bad ids)",
       _v17_ok1 is True and _v17_ok2 is False
       and _v17_calls == [("validate", "VELDO-0017-U1"), ("write", "VELDO-0017-U1"), ("validate", "bad/id")]
       and "before any artifact was written" in _v17_why2
       and all(EC17.admit_unit_artifact(u, lambda x: None)[0] == (CL17.unit_id_problem(u) is None)
               for u in ("VELDO-0017", "bad/id", "", "a b", "WARP-0001.x_y-z")))
expect("VELDO-0017 AC4 identity/canonical-unit-validation: the contract module spells no second copy of the identifier "
       "rules - it names claim.unit_id_problem and never ledger_basename or the allowed-character set",
       "unit_id_problem" in _v17_src and "ledger_basename" not in _v17_src and "letters, digits" not in _v17_src)
# THE DECLARED FALSIFIER: skip the canonical check before the write in a copy; the row reds.
_V17_M4 = _v17_mutated('''    problem = check(unit_id)
''', '''    problem = None  # mutant: the canonical check is skipped
''')
_v17_calls_m = []
_V17_M4.admit_unit_artifact("bad/id", lambda u: _v17_calls_m.append(("write", u)), validator=_v17_spy_validator)
expect("VELDO-0017 AC4 identity/canonical-unit-validation DRIVEN (the declared falsifier): with the check skipped a bad "
       "id is written, so the row reds; unmutated the write never happens",
       _v17_calls_m == [("write", "bad/id")]
       and EC17.admit_unit_artifact("bad/id", lambda u: _v17_calls_m.append(("write2", u)))[0] is False
       and ("write2", "bad/id") not in _v17_calls_m)
