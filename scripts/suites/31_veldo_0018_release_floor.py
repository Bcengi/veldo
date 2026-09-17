"""VELDO-0018: release and behavior-floor integration contracts (PLAN-0019 W3).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 31_veldo_0018_release_floor

WHAT IS UNDER TEST. .veldo/release_floor_contract.py: the membership forest and its unique
ownership (AC1), release execution acceptance over exact member revisions and observed regression
receipts (AC2), behavior-floor eligibility over applicable floors and affected pins (AC3), and the
cancellation dispositions plus the no-deployment boundary (AC4). Relation and cancellation types are
enumerated from the module's own tables; the four declared falsifiers are applied to a COPY of the
module and required to turn their named row red while the unmutated module passes it.
"""
import importlib.util as _v18_ilu
import shutil as _v18_shutil

_v18_spec = _v18_ilu.spec_from_file_location("v18_release_floor", ROOT / ".veldo" / "release_floor_contract.py")
RF18 = _v18_ilu.module_from_spec(_v18_spec)
_v18_spec.loader.exec_module(RF18)
_v18_src = (ROOT / ".veldo" / "release_floor_contract.py").read_text()


def _v18_mutated(old, new):
    d = Path(tempfile.mkdtemp(prefix="v18mut"))
    src = _v18_src
    assert src.count(old) == 1, (old[:60], src.count(old))
    (d / "release_floor_contract.py").write_text(src.replace(old, new))
    # the copy loads its sibling organs from the REAL engine: ROOT is derived from the file's parent
    (d / "release_floor_contract.py").write_text((d / "release_floor_contract.py").read_text().replace(
        "ROOT = Path(__file__).resolve().parent.parent", "ROOT = Path(%r)" % str(ROOT)))
    spec = _v18_ilu.spec_from_file_location("v18_mut_%s" % d.name, d / "release_floor_contract.py")
    m = _v18_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v18_shutil.rmtree(d, ignore_errors=True)
    return m


# ---------------------------------------------------------------------------------------------
# AC1: the forest stays typed; ownership is unique; a contribution owns nothing.
# ---------------------------------------------------------------------------------------------
_v18_recs = {"REL-0001": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0019"}, {"kind": "release", "target": "REL-0002"}]}},
             "REL-0002": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0001"}]}}}
_v18_plans = ["PLAN-0019", "PLAN-0001", "PLAN-0002"]
_v18_projects = [{"alias": "P1", "owns": ["REL-0001", "PLAN-0002"]}]
_v18_objectives = [{"alias": "O2", "project": "P2", "contributions": [{"kind": "plan", "target": "PLAN-0019"}, {"kind": "specification", "target": "VELDO-0018"}]}]
expect("VELDO-0018 AC1 release-ownership/relations: the relation table has the two typed membership relations of "
       "veldo.release/v1, the two owning relations of R65 and the non-owning contribution link; permitted member "
       "endpoints are release and plan only",
       [r["relation"] for r in RF18.RELEASE_RELATIONS] == ["release_groups_release", "release_groups_plan", "project_owns_release_tree",
                                                          "project_owns_standalone_plan", "objective_contributes"]
       and [r["owning"] for r in RF18.RELEASE_RELATIONS] == [False, False, True, True, False]
       and RF18.MEMBER_KINDS == ("release", "plan"))
expect("VELDO-0018 AC1 release-ownership/forest: a well-formed forest with one owner per root and standalone plan and a "
       "cross-project contribution has no problem; a specification member, a member declared twice, a ring, two "
       "parents, a root with no owner, a root with two owners and a member owned separately are each refused by name",
       RF18.release_ownership_problems(_v18_recs, _v18_plans, _v18_projects, _v18_objectives) == []
       and any("is not a plan id" in p for p in RF18.membership_problems({"REL-1": {"fm": {"members": [{"kind": "plan", "target": "VELDO-0018"}]}}}))
       and any("declared twice" in p for p in RF18.membership_problems({"REL-1": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0001"}, {"kind": "plan", "target": "PLAN-0001"}]}}}))
       and any("member ring" in p for p in RF18.membership_problems({"REL-1": {"fm": {"members": [{"kind": "release", "target": "REL-2"}]}},
                                                                     "REL-2": {"fm": {"members": [{"kind": "release", "target": "REL-1"}]}}}))
       and any("claimed as a member by 2 releases" in p for p in RF18.membership_problems({"REL-1": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0001"}]}},
                                                                                            "REL-2": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0001"}]}}}))
       and any("REL-0001 has 0 owning project(s)" in p for p in RF18.release_ownership_problems(_v18_recs, _v18_plans, [{"alias": "P1", "owns": ["PLAN-0002"]}]))
       and any("REL-0001 has 2 owning project(s)" in p for p in RF18.release_ownership_problems(_v18_recs, _v18_plans, _v18_projects + [{"alias": "P2", "owns": ["REL-0001"]}]))
       and any("owned through its tree" in p for p in RF18.release_ownership_problems(_v18_recs, _v18_plans, _v18_projects + [{"alias": "P2", "owns": ["PLAN-0019"]}])))
expect("VELDO-0018 AC1 release-ownership/contribution: an objective in another project contributing to PLAN-0019 adds no "
       "owner (owners_of reads project ownership only), a contribution flagged owning is refused, and an unknown "
       "contribution kind is refused",
       RF18.owners_of("PLAN-0019", _v18_projects) == []  # a member, owned through its tree
       and RF18.owners_of("REL-0001", _v18_projects) == ["P1"]
       and any("never confers ownership" in p for p in RF18.release_ownership_problems(
           _v18_recs, _v18_plans, _v18_projects, [{"alias": "O2", "contributions": [{"kind": "plan", "target": "PLAN-0002", "owning": True}]}]))
       and any("a contribution is" in p for p in RF18.release_ownership_problems(
           _v18_recs, _v18_plans, _v18_projects, [{"alias": "O2", "contributions": [{"kind": "objective", "target": "x"}]}])))
# THE DECLARED FALSIFIER: treat a contribution as a second project owner in a copy; the row reds.
_V18_M1 = _v18_mutated('''    return sorted(p.get("alias") or p.get("uuid") for p in projects
                  if isinstance(p, dict) and target in (p.get("owns") or []))
''', '''    owners = [p.get("alias") or p.get("uuid") for p in projects if isinstance(p, dict) and target in (p.get("owns") or [])]
    for o in _CONTRIBUTIONS_SEEN:
        if any(c.get("target") == target for c in (o.get("contributions") or [])):
            owners.append(o.get("project"))
    return sorted(owners)
''')
_V18_M1._CONTRIBUTIONS_SEEN = [{"project": "P2", "contributions": [{"kind": "release", "target": "REL-0001"}]}]
expect("VELDO-0018 AC1 release-ownership/contribution DRIVEN (the declared falsifier): with a contribution counted as a "
       "second project owner in a copy, REL-0001 (owned by P1, contributed to by P2's objective) reads as owned by two "
       "projects and the forest is refused, so the row reds; unmutated the contribution adds no owner",
       any("REL-0001 has 2 owning project(s)" in p for p in _V18_M1.release_ownership_problems(_v18_recs, _v18_plans, _v18_projects))
       and RF18.release_ownership_problems(_v18_recs, _v18_plans, _v18_projects,
                                           [{"alias": "O2", "project": "P2", "contributions": [{"kind": "release", "target": "REL-0001"}]}]) == [])

# ---------------------------------------------------------------------------------------------
# AC2: acceptance over exact member revisions and observed regression receipts.
# ---------------------------------------------------------------------------------------------
_v18_snap = {"release_revision": 2, "release_status": "in_progress", "candidate": "sha256:cand", "environment": "staging",
             "members": [{"id": "PLAN-0019", "digest": "d19"}, {"id": "REL-0002", "digest": "d02"}, {"id": "PLAN-0001", "digest": "d01"}],
             "journeys": [{"id": "J-signup"}, {"id": "J-refill"}]}
_v18_ex = {"uuid": "00000000-0000-4000-8000-000000000042", "alias": "RX-1", "state": "ACTIVE", "release_revision": 2, "concurrency_version": 3}
_v18_rc = [{"kind": "member_outcome", "member": "PLAN-0019", "digest": "d19", "result": "accepted", "observed": True},
           {"kind": "member_outcome", "member": "REL-0002", "digest": "d02", "result": "accepted", "observed": True},
           {"kind": "member_outcome", "member": "PLAN-0001", "digest": "d01", "result": "passed", "observed": True},
           {"kind": "journey_execution", "journey": "J-signup", "candidate": "sha256:cand", "environment": "staging", "result": "passed", "observed": True},
           {"kind": "journey_execution", "journey": "J-refill", "candidate": "sha256:cand", "environment": "staging", "result": "passed", "observed": True}]
_v18_auth = {"signed_by": "dmitry", "subject": "release_execution_acceptance", "release_revision": 2}
_v18_accepted, _v18_acc_problems = RF18.accept_release_execution(_v18_ex, _v18_snap, _v18_rc, _v18_auth)
expect("VELDO-0018 AC2 release-acceptance/complete: with every resolved member's outcome receipt at its exact digest, every "
       "declared journey's execution receipt against the snapshot's candidate and environment, and the acceptance "
       "authority's signed receipt for the exact revision, the execution moves ACTIVE -> ACCEPTED with "
       "deployment_authorized False and its concurrency version bumped",
       _v18_acc_problems == [] and _v18_accepted["state"] == "ACCEPTED" and _v18_accepted["deployment_authorized"] is False
       and _v18_accepted["concurrency_version"] == 4 and _v18_accepted["accepted_against"]["release_revision"] == 2)


def _v18_without(receipts, pred):
    return [r for r in receipts if not pred(r)]


_v18_dup = _v18_rc + [dict(_v18_rc[3])]
expect("VELDO-0018 AC2 release-acceptance/set-equality: a deleted member receipt, a stale member digest, a duplicated "
       "journey receipt, a receipt for a member the snapshot does not resolve, a wrong candidate, a wrong environment, "
       "a declaration result that is not an observation, a different release revision, a non-ACTIVE execution, and a "
       "released status string with no receipts are each refused by name",
       any("PLAN-0001 has no outcome receipt" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, _v18_without(_v18_rc, lambda r: r.get("member") == "PLAN-0001")))
       and any("stale or wrong member revision" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, [dict(r, digest="old") if r.get("member") == "REL-0002" else r for r in _v18_rc]))
       and any("J-signup has 2 execution receipts" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, _v18_dup))
       and any("does not resolve as a member" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, _v18_rc + [{"kind": "member_outcome", "member": "PLAN-0002", "digest": "x", "result": "accepted", "observed": True}]))
       and any("not the snapshot's 'sha256:cand'" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, [dict(r, candidate="sha256:other") if r.get("journey") == "J-refill" else r for r in _v18_rc]))
       and any("environment 'prod', not the snapshot's" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, [dict(r, environment="prod") if r.get("journey") == "J-refill" else r for r in _v18_rc]))
       and any("not an accepted observation" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, [dict(r, observed=False) if r.get("journey") == "J-refill" else r for r in _v18_rc]))
       and any("exact accepted revision" in p for p in RF18.acceptance_problems(dict(_v18_ex, release_revision=1), _v18_snap, _v18_rc))
       and any("only ACTIVE executions are accepted" in p for p in RF18.acceptance_problems(dict(_v18_ex, state="BLOCKED"), _v18_snap, _v18_rc))
       and any("released string alone" in p for p in RF18.acceptance_problems(_v18_ex, dict(_v18_snap, release_status="released"), []))
       and RF18.accept_release_execution(_v18_ex, _v18_snap, _v18_rc, {"signed_by": "dmitry", "subject": "release_execution_acceptance", "release_revision": 1})[0] is None)
expect("VELDO-0018 AC2 release-acceptance/missing-regression: a declared journey without an execution receipt refuses "
       "acceptance by name, so a journey declaration alone is insufficient (R65)",
       any("J-refill has no execution receipt" in p for p in RF18.acceptance_problems(_v18_ex, _v18_snap, _v18_without(_v18_rc, lambda r: r.get("journey") == "J-refill")))
       and RF18.accept_release_execution(_v18_ex, _v18_snap, _v18_without(_v18_rc, lambda r: r.get("journey") == "J-refill"), _v18_auth)[0] is None)
# THE DECLARED FALSIFIER: accept a journey declaration without an execution receipt in a copy; the row reds.
_V18_M2 = _v18_mutated('''        if not got:
            problems.append("declared journey %s has no execution receipt: a journey declaration alone is insufficient (R65)" % jid)
''', '''        if not got:
            continue  # mutant: the declaration stands for the run
''')
expect("VELDO-0018 AC2 release-acceptance/missing-regression DRIVEN (the declared falsifier): with the missing-receipt "
       "refusal removed in a copy, the execution is ACCEPTED with a journey never run, so the row reds; unmutated it "
       "is refused",
       _V18_M2.accept_release_execution(_v18_ex, _v18_snap, _v18_without(_v18_rc, lambda r: r.get("journey") == "J-refill"), _v18_auth)[0] is not None
       and RF18.accept_release_execution(_v18_ex, _v18_snap, _v18_without(_v18_rc, lambda r: r.get("journey") == "J-refill"), _v18_auth)[0] is None)

# ---------------------------------------------------------------------------------------------
# AC3: floor eligibility over applicable floor revisions and affected pins.
# ---------------------------------------------------------------------------------------------
_v18_floors = {"F-claims": {"digest": "fd2", "pins": ["p1", "p2", "p3"], "authority": "dmitry"},
               "F-lander": {"digest": "fl1", "pins": ["q1"], "authority": "dmitry"}}
_v18_sf = [{"floor": "F-claims", "digest": "fd2", "affected_pins": ["p1", "p2"]}, {"floor": "F-lander", "digest": "fl1", "affected_pins": ["q1"]}]
_v18_setts = [{"floor": "F-claims", "floor_digest": "fd2", "settled_by": "dmitry", "scope": ["p1", "p2"], "ruling": "incidental"},
              {"floor": "F-lander", "floor_digest": "fl1", "settled_by": "dmitry", "scope": ["q1"], "ruling": "load_bearing"}]
_v18_req, _v18_req_problems = RF18.required_pins(_v18_sf, _v18_floors)
expect("VELDO-0018 AC3 floor-eligibility/required-set: the required pin set is the join of the snapshot's applicable floors "
       "and affected pins against the floor registry (three pins here, no unexamined member), and correctly bound "
       "settlements make the execution eligible",
       _v18_req == {("F-claims", "p1"), ("F-claims", "p2"), ("F-lander", "q1")} and _v18_req_problems == []
       and RF18.floor_eligibility_problems(_v18_sf, _v18_floors, _v18_setts) == [])
expect("VELDO-0018 AC3 floor-eligibility/blocks: a missing floor, a floor named at another digest, an affected pin the floor "
       "does not declare, a pin with no settlement, the wrong authority, an expanded settlement scope and an unknown "
       "ruling each block by name",
       any("missing from the floor registry" in p for p in RF18.floor_eligibility_problems(_v18_sf + [{"floor": "F-gone", "digest": "x", "affected_pins": ["z"]}], _v18_floors, _v18_setts))
       and any("changed pinned behavior blocks" in p for p in RF18.floor_eligibility_problems([dict(_v18_sf[0], digest="fd1"), _v18_sf[1]], _v18_floors, _v18_setts))
       and any("unexamined member" in p for p in RF18.floor_eligibility_problems([dict(_v18_sf[0], affected_pins=["p1", "p9"]), _v18_sf[1]], _v18_floors, _v18_setts))
       and any("has no settlement" in p for p in RF18.floor_eligibility_problems(_v18_sf, _v18_floors, _v18_setts[1:]))
       and any("designated baseline authority is 'dmitry'" in p for p in RF18.floor_eligibility_problems(_v18_sf, _v18_floors, [dict(_v18_setts[0], settled_by="agent"), _v18_setts[1]]))
       and any("expanded scope" in p for p in RF18.floor_eligibility_problems(_v18_sf, _v18_floors, [dict(_v18_setts[0], scope=["p1", "p2", "p7"]), _v18_setts[1]]))
       and any("ruling 'meh' is not one of" in p for p in RF18.floor_eligibility_problems(_v18_sf, _v18_floors, [dict(_v18_setts[0], ruling="meh"), _v18_setts[1]])))
expect("VELDO-0018 AC3 floor-eligibility/stale-settlement: a settlement bound to an earlier floor digest is stale and blocks "
       "by name until the authority settles the exact version",
       any("earlier floor digest is stale" in p for p in RF18.floor_eligibility_problems(_v18_sf, _v18_floors, [dict(_v18_setts[0], floor_digest="fd1"), _v18_setts[1]])))
# THE DECLARED FALSIFIER: accept a settlement for an earlier floor digest in a copy; the row reds.
_V18_M3 = _v18_mutated('''            if s.get("floor_digest") != floor.get("digest"):
''', '''            if False:  # mutant: any digest will do
''')
expect("VELDO-0018 AC3 floor-eligibility/stale-settlement DRIVEN (the declared falsifier): with the digest equality removed "
       "in a copy the stale settlement makes the execution eligible, so the row reds; unmutated it blocks",
       _V18_M3.floor_eligibility_problems(_v18_sf, _v18_floors, [dict(_v18_setts[0], floor_digest="fd1"), _v18_setts[1]]) == []
       and RF18.floor_eligibility_problems(_v18_sf, _v18_floors, [dict(_v18_setts[0], floor_digest="fd1"), _v18_setts[1]]) != [])

# ---------------------------------------------------------------------------------------------
# AC4: cancellation follows ownership disposition; acceptance never activates deployment.
# ---------------------------------------------------------------------------------------------
expect("VELDO-0018 AC4 release-boundary/cancellation-relations: the cancellation table derives from the ownership schema - a "
       "project disposes of its release executions, units, assignments and reservations through disposition records, an "
       "objective disposes of backlog items explicitly, an item of its units, a release execution stops uncompleted work",
       [r["owner"] for r in RF18.CANCELLATION_RELATIONS] == ["project", "objective", "backlog_item", "release_execution"]
       and RF18.CANCELLATION_RELATIONS[0]["disposes"] == ("release_execution", "execution_unit", "assignment", "reservation")
       and RF18.CANCELLATION_RELATIONS[1]["disposes"] == ("backlog_item",))
_v18_P = {"uuid": "p-1", "alias": "P1", "entity_type": "project"}
_v18_owned = [{"uuid": "rx-1", "alias": "RX-1", "entity_type": "release_execution", "state": "ACTIVE"},
              {"uuid": "u-1", "alias": "U-1", "entity_type": "execution_unit", "state": "RUNNING"},
              {"uuid": "u-2", "alias": "U-2", "entity_type": "execution_unit", "state": "COMPLETED"},
              {"uuid": "a-1", "alias": "A-1", "entity_type": "assignment", "state": "OFFERED"}]
_v18_disp = [{"target": "rx-1", "disposition": "stop", "recorded_by": "dmitry"},
             {"target": "u-1", "disposition": "stop", "recorded_by": "dmitry"},
             {"target": "a-1", "disposition": "stop", "recorded_by": "dmitry"}]
expect("VELDO-0018 AC4 release-boundary/project-cancellation: cancelling a project with a disposition for every unfinished "
       "owned record is allowed (the completed unit needs none); a missing disposition, an unknown disposition, and an "
       "alternative outcome without a signed reconciliation are each refused by name",
       RF18.project_cancellation_problems(_v18_P, _v18_owned, _v18_disp) == []
       and any("U-1 undisposed" in p for p in RF18.project_cancellation_problems(_v18_P, _v18_owned, _v18_disp[:1] + _v18_disp[2:]))
       and any("disposition must be one of" in p for p in RF18.project_cancellation_problems(_v18_P, _v18_owned, [dict(_v18_disp[0], disposition="ignore")] + _v18_disp[1:]))
       and any("signed reconciliation" in p for p in RF18.project_cancellation_problems(_v18_P, _v18_owned, [dict(_v18_disp[0], disposition="accept_alternative_outcome")] + _v18_disp[1:])))
_v18_O = {"uuid": "o-1", "alias": "O1"}
_v18_items = [{"uuid": "i-1", "alias": "I-1", "objective_uuid": "o-1", "state": "ACTIVE"},
              {"uuid": "i-2", "alias": "I-2", "objective_uuid": "o-1", "state": "DONE"},
              {"uuid": "i-3", "alias": "I-3", "objective_uuid": "o-9", "state": "ACTIVE"}]
expect("VELDO-0018 AC4 release-boundary/objective-cancellation: cancelling an objective needs an explicit disposition for "
       "each of its non-terminal backlog items (not for a done item, not for another objective's item), and a "
       "disposition naming a unit directly is refused: units are reached only through their items",
       RF18.objective_cancellation_problems(_v18_O, _v18_items, [{"target": "i-1", "disposition": "stop", "recorded_by": "dmitry"}]) == []
       and any("I-1 without an explicit disposition" in p for p in RF18.objective_cancellation_problems(_v18_O, _v18_items, []))
       and any("names execution unit u-1 directly" in p for p in RF18.objective_cancellation_problems(
           _v18_O, _v18_items, [{"target": "i-1", "disposition": "stop", "recorded_by": "dmitry"},
                                {"target": "u-1", "target_type": "execution_unit", "disposition": "stop", "recorded_by": "dmitry"}])))
_v18_dep_ok = {"kind": "deployment_authorization", "signed_by": "dmitry", "acceptance_uuid": _v18_accepted["uuid"]}
expect("VELDO-0018 AC4 release-boundary/no-deployment: an accepted release execution authorizes no deployment; only a "
       "separate signed deployment_authorization bound to that acceptance does; an acceptance record claiming "
       "deployment_authorized True is refused as a claim acceptance cannot carry",
       any("the acceptance alone authorizes nothing" in p for p in RF18.deployment_authorization_problems(_v18_accepted))
       and RF18.deployment_authorization_problems(_v18_accepted, _v18_dep_ok) == []
       and any("acceptance never carries deployment authority" in p
               for p in RF18.deployment_authorization_problems(dict(_v18_accepted, deployment_authorized=True), _v18_dep_ok))
       and RF18.deployment_authorization_problems(_v18_accepted, dict(_v18_dep_ok, acceptance_uuid="other")) != [])


class _V18Deployer:
    def __init__(self):
        self.calls = []

    def roll_out(self, *a, **k):
        self.calls.append(("roll_out", a, k))


_v18_spy = _V18Deployer()
_v18_rec2, _ = RF18.accept_release_execution(_v18_ex, _v18_snap, _v18_rc, _v18_auth, deployer=_v18_spy)
expect("VELDO-0018 AC4 release-boundary/no-deployment: a deployer handed to the acceptance path is never called (spy "
       "records nothing) and the module names neither roll_out nor release.py: acceptance has no seam to a rollout",
       _v18_rec2 is not None and _v18_spy.calls == [] and "roll_out" not in _v18_src
       and '_organ("release")' not in _v18_src and "import release" not in _v18_src)  # release.py is never loaded here
# THE DECLARED FALSIFIER: invoke rollout authorization on acceptance in a copy; the row reds.
_V18_M4 = _v18_mutated('''    _ = deployer  # IGNORED ON PURPOSE: acceptance has no seam to a rollout
''', '''    if deployer is not None:
        deployer.roll_out(execution)  # mutant: acceptance rolls out
''')
_v18_spy_m = _V18Deployer()
_V18_M4.accept_release_execution(_v18_ex, _v18_snap, _v18_rc, _v18_auth, deployer=_v18_spy_m)
expect("VELDO-0018 AC4 release-boundary/no-deployment DRIVEN (the declared falsifier): with rollout invoked on acceptance "
       "in a copy the deployer spy records a roll_out call, so the row reds; unmutated it records nothing",
       len(_v18_spy_m.calls) == 1 and _v18_spy_m.calls[0][0] == "roll_out" and _v18_spy.calls == [])
