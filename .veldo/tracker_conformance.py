#!/usr/bin/env python3
"""Tracker conformance: prove the whole tracker integration end to end, offline (W8 of PLAN-0006).

The per-item selftests prove each piece; this proves the SURFACE - a ticket becomes a routing-resolved
spec draft (intake), a spec's lifecycle mirrors back onto its tracker child (spec mirror), and a plan
builds its epic and children (epic mirror) - all over the deterministic FakeTracker with no live
network, and it holds the two load-bearing regression journeys the plan names:

  RJ1  routing-resolved intake + event-driven read-only mirror behave, AND a broken mapping FAILS the
       conformance by name (no rubber-stamp).
  RJ2  the tracker never becomes a writer of work definition - the whole journey mutates ONLY the
       tracker (through the audited seam writes) and NEVER the repository (the spec and plan indices
       it reads are byte-unchanged afterward), so the repository stays the single source of truth.

conformance_findings(config) runs the journey and returns a list of NAMED findings; an empty list is
conformance. A broken routing or status mapping, a mirror that is not idempotent on replay, or a
projection that wrote back into the repository each surfaces a named finding, so the selftest can
assert conformance on a good config and a NAMED failure on a broken one - the non-rubber-stamp teeth.

Pure stdlib, no network. It composes the shipped pieces (tracker.py routing, tracker_adapter.py seam
+ FakeTracker, tracker_intake.py intake, tracker_mirror.py mirror); it adds no new machinery.

  python3 .veldo/tracker_conformance.py check   # run the conformance and print findings
"""
import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_adapter = _load("veldo_tracker_adapter", "tracker_adapter.py")
_intake = _load("veldo_tracker_intake", "tracker_intake.py")
_mirror = _load("veldo_tracker_mirror", "tracker_mirror.py")

FakeTracker = _adapter.FakeTracker
intake_item = _intake.intake_item
IntakeError = _intake.IntakeError
mirror_events = _mirror.mirror_events
mirror_plan_events = _mirror.mirror_plan_events

# The seam's only write operations. A conformance run must touch nothing outside this set - anything
# else would mean the tracker projection reached beyond status/comments/structure/assignment.
_SEAM_WRITE_OPS = {"comment", "set_status", "assign", "create_or_update_epic", "create_or_update_child"}

GOOD_CONFIG = {
    "schema": "veldo.tracker/v1",
    "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
    "status_map": {"ready": "To Do", "blocked": "Blocked", "shipped": "Done"},
    "repos": [{"id": "repo-a", "tracker": "jira", "project": "PROJ"}],
}


def _fixtures():
    """The canonical conformance fixtures: an intake ticket, the spec index and lifecycle events for
    the drafted work item, and the plan index and events for its epic. Deterministic; no network."""
    ticket = {"id": "BUG-1", "title": "checkout 500 on empty cart",
              "body": "POST /checkout 500s when the cart is empty", "labels": ["veldo-repo:repo-a", "bug"]}
    unroutable = {"id": "BUG-2", "title": "no route", "body": "x", "labels": ["bug"]}
    spec_index = {"VELDO-C001": {"id": "VELDO-C001", "plan": "PLAN-C001", "work": "W1",
                                "tracker_repo": "repo-a", "title": "checkout 500 on empty cart"}}
    spec_events = [
        {"id": "c-e1", "type": "spec.ready", "correlation_id": "VELDO-C001", "at": "2026-01-01T00:00:00Z"},
        {"id": "c-e2", "type": "spec.shipped", "correlation_id": "VELDO-C001",
         "at": "2026-01-01T02:00:00Z", "commit": "abc123"},
    ]
    plan_index = {"PLAN-C001": {"id": "PLAN-C001", "title": "checkout hardening", "tracker_repo": "repo-a",
                                "status": "ready",
                                "work": [{"item": "W1", "spec": "VELDO-C001", "title": "empty-cart 500",
                                          "spec_status": "shipped"}]}}
    plan_events = [{"id": "c-p1", "type": "plan.created", "correlation_id": "PLAN-C001", "at": "2026-01-01T00:00:00Z"}]
    return ticket, unroutable, spec_index, spec_events, plan_index, plan_events


def run_end_to_end(config, adapter=None):
    """Drive the full tracker surface over one adapter: intake a ticket to a routing-resolved draft,
    mirror the spec's lifecycle onto its child, and mirror the plan onto its epic and children. The
    input indices are deep-copied for the mutation guard. Returns the observations for the checker."""
    ticket, unroutable, spec_index, spec_events, plan_index, plan_events = _fixtures()
    ta = adapter or FakeTracker(intake_items=[ticket, unroutable])
    spec_before, plan_before = copy.deepcopy(spec_index), copy.deepcopy(plan_index)

    draft = intake_item(ta, ticket["id"], config, spec_id="VELDO-C001", owner="conformance")
    refused = False
    try:
        intake_item(ta, unroutable["id"], config, spec_id="VELDO-C002")
    except IntakeError:
        refused = True

    m1 = mirror_events(spec_events, spec_index, config, ta)
    digest_after_first = ta.state_digest()
    m2 = mirror_events(spec_events, spec_index, config, ta)  # replay
    digest_after_replay = ta.state_digest()

    e1 = mirror_plan_events(plan_events, plan_index, config, ta)

    child = None
    try:
        child = ta.snapshot("child:PLAN-C001:W1")
    except Exception:
        child = None
    epic = None
    try:
        epic = ta.snapshot("epic:PLAN-C001")
    except Exception:
        epic = None

    return {
        "draft_repo": draft.get("repo"),
        "intake_refused_unroutable": refused,
        "spec_mirror": m1, "spec_mirror_replay": m2,
        "epic_mirror": e1,
        "child": child, "epic": epic,
        "replay_idempotent": digest_after_first == digest_after_replay,
        "write_ops": {w["op"] for w in ta.writes()},
        "spec_index_unchanged": json.dumps(spec_index, sort_keys=True) == json.dumps(spec_before, sort_keys=True),
        "plan_index_unchanged": json.dumps(plan_index, sort_keys=True) == json.dumps(plan_before, sort_keys=True),
        "closing_comment": _has_closing_comment(child),
    }


def _has_closing_comment(child):
    if not child:
        return False
    return any((c.get("key") or "").endswith(":shipped") for c in child.get("comments") or [])


def conformance_findings(config):
    """Run the end-to-end journey and return NAMED findings; an empty list is conformance. Every
    check fails by name so a broken mapping, a non-idempotent replay, or a write-back into the
    repository is surfaced rather than silently passing."""
    findings = []
    try:
        obs = run_end_to_end(config)
    except Exception as e:
        return ["conformance journey raised %s: %s" % (type(e).__name__, e)]

    # RJ1 intake: a valid ticket routes to its repo, an unroutable ticket is refused
    if obs["draft_repo"] != "repo-a":
        findings.append("intake did not route the ticket to repo-a (got %r) - routing/mapping broken" % obs["draft_repo"])
    if not obs["intake_refused_unroutable"]:
        findings.append("intake did not refuse an unroutable ticket - it would guess a repo")

    # RJ1 spec mirror: the child reached the mapped shipped status and the closing comment posted
    child = obs["child"]
    if not child:
        findings.append("spec mirror did not create the spec's tracker child")
    else:
        want = (config.get("status_map") or {}).get("shipped")
        if not want or child.get("status") != want:
            findings.append("spec mirror did not move the child to the mapped shipped status "
                            "(status_map missing 'shipped' or mapping broken; child=%r)" % child.get("status"))
        if not obs["closing_comment"]:
            findings.append("spec mirror did not post the closing comment on ship")

    # RJ1 idempotency: replaying the spec stream records no new transition/comment and no state change
    if not obs["replay_idempotent"]:
        findings.append("spec mirror replay is not idempotent - the tracker state changed on replay")
    if obs["spec_mirror_replay"].get("transitions", 0) or obs["spec_mirror_replay"].get("comments", 0):
        findings.append("spec mirror replay recorded new transitions/comments - not idempotent")

    # RJ1 epic mirror: the plan built its epic and child
    if not obs["epic"]:
        findings.append("epic mirror did not create the plan's epic")
    if not obs["epic_mirror"].get("children"):
        findings.append("epic mirror created no children from the work DAG")

    # RJ2 one-way: the journey mutated only the tracker, never the repository
    stray = obs["write_ops"] - _SEAM_WRITE_OPS
    if stray:
        findings.append("the tracker projection used non-seam write ops %r - it reached beyond status/comments/structure" % sorted(stray))
    if not obs["spec_index_unchanged"]:
        findings.append("the tracker projection mutated the spec index - the tracker wrote back a definition (RJ2 violation)")
    if not obs["plan_index_unchanged"]:
        findings.append("the tracker projection mutated the plan index - the tracker wrote back a definition (RJ2 violation)")

    return findings


def check(argv=None):
    findings = conformance_findings(GOOD_CONFIG)
    if not findings:
        print("tracker conformance: PASS (intake + mirror + epic end to end over the fake tracker, "
              "idempotent replay, one-way, no write-back)")
        return 0
    print("tracker conformance: FAIL")
    for f in findings:
        print("  - %s" % f)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="tracker integration conformance (offline, over the fake tracker)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="run the end-to-end conformance and print findings")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return check()
    return 2


if __name__ == "__main__":
    sys.exit(main())
