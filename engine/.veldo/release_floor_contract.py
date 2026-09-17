#!/usr/bin/env python3
"""Release and behavior-floor integration contracts for the project layer (PLAN-0019 W3, VELDO-0018).

WHAT THIS MODULE IS. Pure predicates over plain versioned data, a contract organ beside
release_contract.py, behavior_floor.py and entity_contract.py: the release membership forest and
its ownership (R65, AC1), release execution acceptance over exact accepted member revisions with
observed regression receipts (R65, AC2), behavior-floor eligibility over applicable floor
revisions and affected pins (R65, AC3), and the cancellation dispositions plus the boundary that
release acceptance never authorizes deployment (R05, R06, R11, R65, AC4). Standard library only.
It reads no live system, writes nothing, and calls nothing in .veldo/release.py: the rollout
machinery is a separate authority with its own separately receipted authorization, and this
module has no seam to it by construction.

WHAT IT REUSES. The membership forest rules are release_contract.py's own (member_cycles,
member_claims, the member id vocabulary); the release execution lifecycle is
entity_contract.LIFECYCLES["release_execution"]; the floor vocabulary (rulings, dispositions) is
behavior_floor.py's. Nothing here restates a rule another organ owns.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.release_floor_contract/v1"


def _organ(name):
    spec = importlib.util.spec_from_file_location("veldo_release_floor_" + name, ROOT / ".veldo" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


# ---------------------------------------------------------------------------------------------
# AC1: the membership forest stays typed; ownership is unique and never duplicated by a contribution.
# ---------------------------------------------------------------------------------------------

# The relation types of veldo.release/v1 plus the ownership and contribution links R65 adds. The
# suite enumerates permitted and forbidden endpoints from this table.
RELEASE_RELATIONS = (
    {"relation": "release_groups_release", "from": "release", "to": "release", "owning": False, "clause": "R65"},
    {"relation": "release_groups_plan", "from": "release", "to": "plan", "owning": False, "clause": "R65"},
    {"relation": "project_owns_release_tree", "from": "project", "to": "release", "owning": True, "clause": "R65"},
    {"relation": "project_owns_standalone_plan", "from": "project", "to": "plan", "owning": True, "clause": "R65"},
    {"relation": "objective_contributes", "from": "objective", "to": ("release", "plan", "specification"), "owning": False, "clause": "R06, R65"},
)
MEMBER_KINDS = ("release", "plan")
CONTRIBUTION_KINDS = ("release", "plan", "specification")


def membership_problems(records):
    """The forest rules over release records ({release id: {"fm": front matter}}, the shape
    release_contract reads): every member is a release or a plan with an id of that kind (a
    specification is refused: a spec binds to a plan, never to a release), no member is declared
    twice by one release, no member ring, and one parent per member. The ring and parentage rules
    are release_contract's own functions; nothing is restated."""
    RC = _organ("release_contract")
    problems = []
    for rid in sorted(records):
        seen = set()
        for entry in RC._members(records[rid]["fm"]):
            if not isinstance(entry, dict) or entry.get("kind") not in MEMBER_KINDS or not _is_str(entry.get("target")):
                problems.append("%s: a member is {kind: release|plan, target: <id>} (got %r)" % (rid, entry))
                continue
            if not RC.MEMBER_ID_RE[entry["kind"]].fullmatch(entry["target"]):
                problems.append("%s: member %r is not a %s id; a specification or anything else is refused as a member"
                                % (rid, entry["target"], entry["kind"]))
            if entry["target"] in seen:
                problems.append("%s: member %s is declared twice" % (rid, entry["target"]))
            seen.add(entry["target"])
    for ring in RC.member_cycles(records):
        problems.append("member ring: %s" % " -> ".join(ring))
    for target, parents in sorted(RC.member_claims(records).items()):
        if len(parents) > 1:
            problems.append("%s is claimed as a member by %d releases: %s (one parent per member)" % (target, len(parents), ", ".join(parents)))
    return problems


def roots_and_standalone(records, plan_ids):
    """(release tree roots, standalone plans): the releases no release claims, and the plans no
    release claims. These, and only these, are owned directly; a member is owned through its tree."""
    RC = _organ("release_contract")
    claimed = set(RC.member_claims(records))
    roots = sorted(r for r in records if r not in claimed)
    standalone = sorted(p for p in plan_ids if p not in claimed)
    return roots, standalone


def owners_of(target, projects):
    """The projects that OWN `target` directly: exactly the `owns` lists of the project records,
    and nothing else. A contribution link is not ownership (R06, R65) and is never read here."""
    return sorted(p.get("alias") or p.get("uuid") for p in projects
                  if isinstance(p, dict) and target in (p.get("owns") or []))


def release_ownership_problems(records, plan_ids, projects, objectives=()):
    """Every release tree root and every standalone plan has exactly one owning project; a member
    is owned through its tree and never separately; two owners is a duplicate by name; an
    objective's contribution links name releases, plans or specifications and confer no ownership
    (a contribution flagged as owning, or to an unknown kind, is refused)."""
    problems = list(membership_problems(records))
    roots, standalone = roots_and_standalone(records, plan_ids)
    RC = _organ("release_contract")
    claimed = set(RC.member_claims(records))
    for target in roots + standalone:
        owners = owners_of(target, projects)
        if len(owners) != 1:
            problems.append("%s has %d owning project(s) (%s); each enrolled release tree and standalone plan has exactly one (R65)"
                            % (target, len(owners), ", ".join(owners) or "none"))
    for p in projects:
        for target in (p.get("owns") or []):
            if target in claimed:
                problems.append("%s owns %s, which is a member of a release: a member is owned through its tree, never separately"
                                % (p.get("alias") or p.get("uuid"), target))
    for o in objectives:
        for c in (o.get("contributions") or []):
            if not isinstance(c, dict) or c.get("kind") not in CONTRIBUTION_KINDS or not _is_str(c.get("target")):
                problems.append("objective %s: a contribution is {kind: release|plan|specification, target} (got %r)" % (o.get("alias") or o.get("uuid"), c))
            elif c.get("owning"):
                problems.append("objective %s: contribution to %s is flagged owning; a contribution never confers ownership or execution authority (R06)"
                                % (o.get("alias") or o.get("uuid"), c["target"]))
    return problems


# ---------------------------------------------------------------------------------------------
# AC2: release execution acceptance over exact member revisions and observed regression receipts.
# ---------------------------------------------------------------------------------------------

ACCEPTED_RESULTS = ("accepted", "passed")


def _receipts_by(receipts, kind, key):
    out = {}
    for r in receipts:
        if isinstance(r, dict) and r.get("kind") == kind and _is_str(r.get(key)):
            out.setdefault(r[key], []).append(r)
    return out


def acceptance_problems(execution, snapshot, receipts):
    """Why a release execution may NOT be accepted, by name (R65): it is not ACTIVE; it binds a
    different release revision than the accepted snapshot; a required member (recursively
    resolved in the snapshot) has no outcome receipt, has two, or has one bound to a different
    digest (stale); a receipt names a member the snapshot does not (extra); a declared journey has
    no execution receipt, has two, or its receipt names a different candidate or environment; a
    receipt's result is not an accepted observation (a declaration is not a receipt); or the
    release record's `released` status string stands where receipts should. Empty iff acceptance
    may proceed."""
    problems = []
    if not isinstance(execution, dict) or not isinstance(snapshot, dict):
        return ["an execution and its accepted snapshot are mappings"]
    if execution.get("state") != "ACTIVE":
        problems.append("release execution %s is %r; only ACTIVE executions are accepted (R65)" % (execution.get("alias") or execution.get("uuid"), execution.get("state")))
    if execution.get("release_revision") != snapshot.get("release_revision"):
        problems.append("execution binds release revision %r but the accepted snapshot is revision %r: acceptance is against the exact accepted revision"
                        % (execution.get("release_revision"), snapshot.get("release_revision")))
    members = {m["id"]: m for m in (snapshot.get("members") or []) if isinstance(m, dict) and _is_str(m.get("id"))}
    journeys = {j["id"]: j for j in (snapshot.get("journeys") or []) if isinstance(j, dict) and _is_str(j.get("id"))}
    outcomes = _receipts_by(receipts, "member_outcome", "member")
    runs = _receipts_by(receipts, "journey_execution", "journey")
    for mid, m in sorted(members.items()):
        got = outcomes.get(mid, [])
        if not got:
            problems.append("required member %s has no outcome receipt" % mid)
        elif len(got) > 1:
            problems.append("required member %s has %d outcome receipts; one member, one receipt" % (mid, len(got)))
        else:
            r = got[0]
            if r.get("digest") != m.get("digest"):
                problems.append("member %s outcome receipt is bound to digest %r, the snapshot resolves %r: stale or wrong member revision" % (mid, r.get("digest"), m.get("digest")))
            if r.get("result") not in ACCEPTED_RESULTS or r.get("observed") is not True:
                problems.append("member %s outcome receipt is not an accepted observation (result %r, observed %r)" % (mid, r.get("result"), r.get("observed")))
    for mid in sorted(set(outcomes) - set(members)):
        problems.append("outcome receipt for %s, which the accepted snapshot does not resolve as a member" % mid)
    for jid in sorted(journeys):
        got = runs.get(jid, [])
        if not got:
            problems.append("declared journey %s has no execution receipt: a journey declaration alone is insufficient (R65)" % jid)
        elif len(got) > 1:
            problems.append("declared journey %s has %d execution receipts; one journey, one receipt" % (jid, len(got)))
        else:
            r = got[0]
            if r.get("candidate") != snapshot.get("candidate"):
                problems.append("journey %s was executed against candidate %r, not the snapshot's %r" % (jid, r.get("candidate"), snapshot.get("candidate")))
            if r.get("environment") != snapshot.get("environment"):
                problems.append("journey %s was executed in environment %r, not the snapshot's %r" % (jid, r.get("environment"), snapshot.get("environment")))
            if r.get("result") not in ACCEPTED_RESULTS or r.get("observed") is not True:
                problems.append("journey %s execution receipt is not an accepted observation (result %r, observed %r)" % (jid, r.get("result"), r.get("observed")))
    for jid in sorted(set(runs) - set(journeys)):
        problems.append("execution receipt for journey %s, which the accepted snapshot does not declare" % jid)
    if snapshot.get("release_status") == "released" and not receipts:
        problems.append("the release record says released and no receipt exists: a released string alone cannot establish acceptance (R65)")
    return problems


def accept_release_execution(execution, snapshot, receipts, authority_receipt, deployer=None):
    """(accepted record or None, problems): the one acceptance path. Runs acceptance_problems,
    requires a signed acceptance authority receipt, and moves the execution ACTIVE -> ACCEPTED
    through entity_contract's declared edge with the three predicates established. THE RESULT
    NEVER AUTHORIZES DEPLOYMENT: the accepted record carries deployment_authorized False, and a
    deployer handed to this function is ignored, by construction and by the suite's spy; the
    rollout machinery in .veldo/release.py has its own separately receipted authorization (R65)."""
    problems = acceptance_problems(execution, snapshot, receipts)
    signed = isinstance(authority_receipt, dict) and _is_str(authority_receipt.get("signed_by")) \
        and authority_receipt.get("subject") == "release_execution_acceptance" \
        and authority_receipt.get("release_revision") == snapshot.get("release_revision")
    if not signed:
        problems.append("acceptance requires the named acceptance authority's signed receipt for this exact release revision")
    if problems:
        return None, problems
    EC = _organ("entity_contract")
    ok, why = EC.transition("release_execution", execution.get("state"), "ACCEPTED",
                            {"required_member_outcomes": True, "regression_receipts": True, "acceptance_authority_signed": True})
    if not ok:
        return None, [why]
    _ = deployer  # IGNORED ON PURPOSE: acceptance has no seam to a rollout
    record = dict(execution, state="ACCEPTED", concurrency_version=int(execution.get("concurrency_version", 0)) + 1,
                  deployment_authorized=False, accepted_against={"release_revision": snapshot.get("release_revision"),
                                                                 "candidate": snapshot.get("candidate"), "environment": snapshot.get("environment")})
    return record, []


# ---------------------------------------------------------------------------------------------
# AC3: behavior-floor eligibility over applicable floor revisions and affected pins.
# ---------------------------------------------------------------------------------------------

def required_pins(snapshot_floors, floors):
    """The pin set an execution snapshot must have examined: for every applicable floor the
    snapshot names, its affected pins joined against the floor registry. Returns
    ({(floor, pin)}, problems): a floor the registry lacks or holds at another digest, and an
    affected pin the floor does not declare, are problems by name."""
    required, problems = set(), []
    for entry in snapshot_floors or []:
        fid = entry.get("floor") if isinstance(entry, dict) else None
        floor = floors.get(fid) if isinstance(floors, dict) else None
        if floor is None:
            problems.append("applicable floor %r is missing from the floor registry: missing required floors block (R65)" % (fid,))
            continue
        if entry.get("digest") != floor.get("digest"):
            problems.append("floor %s is named at digest %r but the registry holds %r: changed pinned behavior blocks until settled" % (fid, entry.get("digest"), floor.get("digest")))
        declared = set(floor.get("pins") or [])
        for pin in entry.get("affected_pins") or []:
            if pin not in declared:
                problems.append("floor %s: affected pin %r is not one the floor declares (unexamined member)" % (fid, pin))
            required.add((fid, pin))
    return required, problems


def floor_eligibility_problems(snapshot_floors, floors, settlements):
    """Why an execution is NOT eligible against its floors, by name (R65): every required pin needs
    a settlement bound to the floor's EXACT current digest (an earlier digest is stale), settled by
    the floor's designated baseline authority (another signer is the wrong authority), whose scope
    is exactly pins the floor declares among the affected set (a wider scope is expanded scope, a
    settlement cannot authorize unrelated scope), carrying a ruling in the floor vocabulary; a
    required pin with no such settlement is unresolved and blocks. Empty iff eligible."""
    BF = _organ("behavior_floor")
    required, problems = required_pins(snapshot_floors, floors)
    for fid, pin in sorted(required):
        floor = floors[fid]
        matching = [s for s in settlements or [] if isinstance(s, dict) and s.get("floor") == fid and pin in (s.get("scope") or [])]
        if not matching:
            problems.append("floor %s pin %s has no settlement: unresolved dispositions block until the authority settles the exact version" % (fid, pin))
            continue
        for s in matching:
            if s.get("floor_digest") != floor.get("digest"):
                problems.append("floor %s pin %s: settlement is bound to digest %r, the floor is at %r: a settlement for an earlier floor digest is stale"
                                % (fid, pin, s.get("floor_digest"), floor.get("digest")))
            if s.get("settled_by") != floor.get("authority"):
                problems.append("floor %s pin %s: settled by %r, the designated baseline authority is %r" % (fid, pin, s.get("settled_by"), floor.get("authority")))
            outside = sorted(set(s.get("scope") or []) - set(floor.get("pins") or []))
            if outside:
                problems.append("floor %s pin %s: settlement scope reaches pins %s the floor does not declare: expanded scope" % (fid, pin, ", ".join(map(str, outside))))
            if s.get("ruling") not in BF.RULINGS:
                problems.append("floor %s pin %s: ruling %r is not one of %s" % (fid, pin, s.get("ruling"), sorted(BF.RULINGS)))
    return problems


# ---------------------------------------------------------------------------------------------
# AC4: cancellation follows ownership disposition; acceptance never activates deployment.
# ---------------------------------------------------------------------------------------------

# Cancellation relation types derived from the ownership schema: what a cancellation of the
# owner must dispose of, and through what.
CANCELLATION_RELATIONS = (
    {"owner": "project", "disposes": ("release_execution", "execution_unit", "assignment", "reservation"), "through": "disposition record", "clause": "R05, R65"},
    {"owner": "objective", "disposes": ("backlog_item",), "through": "explicit backlog disposition", "clause": "R06, R65"},
    {"owner": "backlog_item", "disposes": ("execution_unit",), "through": "item disposition", "clause": "R11"},
    {"owner": "release_execution", "disposes": ("execution_unit",), "through": "stop of uncompleted authorized work", "clause": "R65"},
)
DISPOSITIONS = ("stop", "transfer", "complete_elsewhere", "accept_alternative_outcome")


def project_cancellation_problems(project, owned, dispositions):
    """A project cancellation closes future authorization and DIRECTS the disposition of its
    unfinished work (R05, R65): every non-terminal owned release execution, unit, assignment and
    reservation in `owned` needs a disposition record naming it, a disposition from the vocabulary
    and the person who recorded it. Nothing landed is erased and no incomplete release is called
    accepted: a disposition of accept_alternative_outcome needs a signed reconciliation."""
    EC = _organ("entity_contract")
    problems = []
    kinds = CANCELLATION_RELATIONS[0]["disposes"]
    by_target = {d.get("target"): d for d in dispositions or [] if isinstance(d, dict)}
    for e in owned:
        if not isinstance(e, dict) or e.get("entity_type") not in kinds:
            continue
        lc = EC.LIFECYCLES.get(e.get("entity_type"))
        if lc and e.get("state") in lc["terminal"]:
            continue
        d = by_target.get(e.get("uuid"))
        name = e.get("alias") or e.get("uuid")
        if d is None:
            problems.append("cancelling project %s leaves %s %s undisposed: cancellation directs the disposition of every unfinished owned record"
                            % (project.get("alias") or project.get("uuid"), e.get("entity_type"), name))
            continue
        if d.get("disposition") not in DISPOSITIONS or not _is_str(d.get("recorded_by")):
            problems.append("%s %s: disposition must be one of %s with recorded_by" % (e.get("entity_type"), name, DISPOSITIONS))
        if d.get("disposition") == "accept_alternative_outcome" and not _is_str(d.get("reconciliation_signed_by")):
            problems.append("%s %s: accepting an alternative outcome needs a signed reconciliation; cancellation never counts as completion" % (e.get("entity_type"), name))
    return problems


def objective_cancellation_problems(objective, items, item_dispositions):
    """Objective cancellation affects units ONLY through an explicit disposition of their owning
    backlog items (R65): every non-terminal item under the objective needs a disposition record;
    a disposition that names a unit directly is refused."""
    EC = _organ("entity_contract")
    problems = []
    terminal = set(EC.LIFECYCLES["backlog_item"]["terminal"])
    by_target = {d.get("target"): d for d in item_dispositions or [] if isinstance(d, dict)}
    item_uuids = {i.get("uuid") for i in items if isinstance(i, dict)}
    for i in items:
        if not isinstance(i, dict) or i.get("objective_uuid") != objective.get("uuid") or i.get("state") in terminal:
            continue
        d = by_target.get(i.get("uuid"))
        if d is None or d.get("disposition") not in DISPOSITIONS or not _is_str(d.get("recorded_by")):
            problems.append("cancelling objective %s leaves backlog item %s without an explicit disposition"
                            % (objective.get("alias") or objective.get("uuid"), i.get("alias") or i.get("uuid")))
    for target, d in by_target.items():
        if target not in item_uuids and d.get("target_type") == "execution_unit":
            problems.append("disposition names execution unit %s directly: objective cancellation reaches units only through their backlog items" % target)
    return problems


def deployment_authorization_problems(acceptance, authorization=None):
    """Why deployment is NOT authorized (R65): an accepted release execution never authorizes it
    (deployment_authorized is False on every acceptance record), and only a separate
    deployment_authorization receipt bound to that acceptance and signed by the deployment
    authority does. Empty iff such a receipt is present."""
    problems = []
    if not isinstance(acceptance, dict) or acceptance.get("state") != "ACCEPTED":
        problems.append("no accepted release execution to deploy")
    elif acceptance.get("deployment_authorized") is not False:
        problems.append("an acceptance record claims deployment_authorized %r: acceptance never carries deployment authority (R65)" % (acceptance.get("deployment_authorized"),))
    if not (isinstance(authorization, dict) and authorization.get("kind") == "deployment_authorization"
            and _is_str(authorization.get("signed_by")) and authorization.get("acceptance_uuid") == (acceptance or {}).get("uuid")):
        problems.append("deployment needs its own deployment_authorization receipt signed by the deployment authority and bound to this acceptance; the acceptance alone authorizes nothing")
    return problems
