#!/usr/bin/env python3
"""VELDO global claimable frontier: what a worker may claim right now.

Computes the claimable set across the whole repo, not one plan:
  - BUILD work: a ready spec, found either as an active plan's work item at that plan's
    frontier or as a standalone/bug spec (lane: standalone), and in EITHER case offered
    only when every dependency the spec's own front matter declares is shipped. Two
    different questions, both asked: the plan's work graph orders the plan (item_state
    over the plan's shipped set) and the spec's declared depends_on gates the offer
    (dependency_gate, at the one point every unit passes through).
  - REVIEW work: a spec in status 'review' awaiting its independent verdict.

then filters out anything already claimed (the claim ledger), anything whose
requirements are not a subset of the worker's capabilities, and anything outside the
worker's scope (a plan id or a label). So a build-blocked worker still finds a review
or a standalone spec, and capability-gated work only surfaces to a capable worker.

Reuses the pure plan logic (item_state, shipped set, decision blocks) and the claim
ledger (capability_ok, claimed_units); the repo reading is parametrized by repo_root
so it is testable over a temporary tree. Pure stdlib. This is the read side; claiming
a unit is the claim ledger (WARP-0701) and driving it is the worker loop (WARP-0703)."""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load("veldo_validate_fr", ".veldo/validate.py")
PL = _load("veldo_plan_fr", ".veldo/plan.py")
CL = _load("veldo_claim_fr", ".veldo/claim.py")


def _spec_index(repo_root):
    """{spec_id: front_matter} for every spec under repo_root/specs."""
    out = {}
    specs = Path(repo_root) / "specs"
    if not specs.exists():
        return out
    for p in sorted(specs.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        # parse with parse_yamlish (not the simple front_matter reader) so inline lists
        # like requires: [macos] and labels: [a, b] come through as real lists.
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        if not m:
            continue
        fm = V.parse_yamlish(m.group(1))
        if fm and fm.get("id"):
            out[fm["id"]] = fm
    return out


def _plans(repo_root):
    """[front_matter] for every plan under repo_root/plans."""
    out = []
    plans = Path(repo_root) / "plans"
    if not plans.exists():
        return out
    for p in sorted(plans.glob("*.md")):
        if p.name.startswith("TEMPLATE"):
            continue
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        if m:
            out.append(V.parse_yamlish(m.group(1)))
    return out


def current_status(sid, repo_root=None):
    """The current on-disk status of spec sid, or None if absent. The worker loop calls this
    right after an atomic claim to re-check that the unit it just claimed is still the work it
    saw on the frontier: another worker may have finished the unit in the window between the
    frontier snapshot and the claim, and the claim ledger gates ownership only, not done-ness."""
    fm = _spec_index(repo_root or ROOT).get(sid)
    return fm.get("status") if fm else None


# A declared dependency naming a spec that does not exist resolves to this state, which is
# NOT a spec status: it is unshipped, so it never satisfies a prerequisite, and it is named
# in the withheld report rather than dropped. A typo that silently satisfied a dependency
# would be the same defect as ignoring the field.
DEP_ABSENT = "absent"

# The one dependency state that releases dependent work. Kept next to DEP_ABSENT so the two
# halves of the rule read together; the same word the plan path's shipped set is built from.
DEP_SHIPPED = "shipped"


def _status_map(idx):
    """{spec_id: status} over a spec index, with '?' for a spec that declares none."""
    return {sid: fm.get("status", "?") for sid, fm in idx.items()}


def _is_standalone_build(fm):
    """A standalone build unit's own shape: the standalone lane (no plan carries its order)
    at status ready. Whether it may be CLAIMED additionally depends on its declared
    dependencies, its requirements, the claim ledger and the placement gate."""
    return fm.get("lane") == "standalone" and fm.get("status") == "ready"


def _is_build_shaped(fm):
    """A spec that build work can be offered for at all: status ready, whatever lane found it.
    LANE-INDEPENDENT on purpose. The withheld report used to ask _is_standalone_build, which
    made it silent about exactly the planned specs the gate below withholds, and a report
    narrower than the rule it explains is this same defect one layer up."""
    return fm.get("status") == "ready"


def unmet_dependencies(fm, status):
    """[(dep_id, state)] for every declared dependency of fm that is not shipped, where state
    is the dependency's on-disk status, or DEP_ABSENT when no spec of that id exists.

    THE ONE SPELLING of "a declared prerequisite is unshipped". The claimability DECISION calls
    it through dependency_gate() and the withheld REPORT calls it directly, so the decision and
    its own explanation cannot disagree. That is not a style preference: the defect this replaced
    was a build path that offered a unit while this function reported the same unit waiting, and
    a predicate contradicting its own report is a defect whichever answer is right.

    It reads each dependency's status and NEVER walks the graph, so a dependency cycle is not a
    special case: every member has an unshipped prerequisite, with nothing to recurse into. A
    dependency naming a spec that does not exist is DEP_ABSENT, so it is unshipped and named in
    the report rather than silently satisfying a prerequisite.

    Takes depends_on in the shape the spec contract declares - a list of whitespace-free spec-id
    strings, typed by validate.check_depends_on - and does not re-guess it here. A mapping member
    is unhashable in the status lookup and a bare scalar iterates its characters, so the shape is
    refused where the field is declared."""
    return [(d, status.get(d, DEP_ABSENT)) for d in (fm.get("depends_on") or [])
            if status.get(d) != DEP_SHIPPED]


def dependency_gate(fm, status, kind):
    """True when a unit must NOT be offered, because the spec's own front matter declares a
    prerequisite that is not shipped.

    ONE POINT OF APPLICATION, and the reason is the defect it closes. This rule used to live on
    the standalone lane only, so the plan lane offered a ready spec whose own declared
    prerequisite was unshipped; and for a spec both lanes could reach, whichever ran first put
    the id into `seen` and the other lane's check never ran at all. Both routes are the same
    mistake - a per-path rule - so the rule is asked once, in _add(), which every offer goes
    through however the unit was found.

    Orthogonal to the plan's work graph, which stays the authority for ORDER WITHIN a plan
    (plan.item_state over the plan's own shipped set). A planned spec must satisfy both: the
    plan says when the plan is ready for it, the spec says what it cannot start without.

    Review units are exempt BY THIS TEST rather than by being routed around it: a review is of an
    already-built spec, so its prerequisites cannot bear on whether it can be reviewed."""
    return kind == "build" and bool(unmet_dependencies(fm, status))


def withheld(repo_root=None, scope=None):
    """The BUILD work a declared prerequisite is holding back, as
    [{spec, unmet: [(dep_id, state)]}] ordered by spec id.

    An ordering rule that hides its own effect looks like an empty queue rather than like a
    queue that is waiting, so this is the diagnostic half of the dependency gate: the CLI
    prints it, and a dependency naming a spec that does not exist appears with state
    DEP_ABSENT instead of vanishing. It covers EVERY ready spec, planned or standalone, because
    dependency_gate withholds every ready spec. Scope is honoured through the same _in_scope
    predicate claimable() uses, with the spec's own declared plan as the plan id, so the report
    answers the question that was asked and not a wider one.

    No claim ledger and no capabilities: this answers "what is waiting and on what", not "what
    may this worker claim". A planned spec that its PLAN holds back (an unshipped work-item
    dependency, an open decision) is the plan burn-down's report, not this one; this report is
    exactly the front-matter rule."""
    idx = _spec_index(repo_root or ROOT)
    status = _status_map(idx)
    out = []
    for sid in sorted(idx):
        fm = idx[sid]
        if not _is_build_shaped(fm) or not _in_scope(fm, fm.get("plan"), scope):
            continue
        unmet = unmet_dependencies(fm, status)
        if unmet:
            out.append({"spec": sid, "unmet": unmet})
    return out


def _in_scope(fm, plan_id, scope):
    if not scope:
        return True
    if scope.get("plan") and plan_id != scope["plan"]:
        return False
    if scope.get("label"):
        labels = fm.get("labels") or ([fm["label"]] if fm.get("label") else [])
        if scope["label"] not in labels:
            return False
    return True


def _plan_build_candidates(repo_root, status):
    """Yield (spec_id, plan_id) for every ready spec an ACTIVE plan's own work graph has reached:
    the work item's declared dependencies are shipped within that plan and no open decision
    blocks it. Only ready/in_progress plans are active - a draft (unapproved) plan yields nothing
    claimable, and released or closed plans have no frontier anyway.

    CANDIDATES, not offers. This answers the plan's ordering question and nothing else; whether a
    candidate may actually be offered is _add's question, and that is where the spec's own
    declared depends_on is asked, for these units exactly as for the standalone ones."""
    for fm in _plans(repo_root):
        if fm.get("status") not in ("ready", "in_progress"):
            continue
        shipped = PL._shipped_set(fm, status)
        blocked = PL._decision_blocks(fm)
        for w in PL._work(fm):
            sid = w.get("spec")
            if (PL.item_state(w, status, shipped, blocked).endswith("(frontier)")
                    and status.get(sid) == "ready"):
                yield sid, fm.get("id")


def claimable(worker_caps=None, scope=None, repo_root=None, claims_root=None):
    """Return the claimable units for a worker with worker_caps, within scope.

    Each unit is {spec, plan, kind ('build'|'review'), requires}. A unit is excluded
    if it is already claimed (live), if its requires are not a subset of worker_caps,
    or if it is out of scope. repo_root defaults to this repo; claims_root is passed
    through to the claim ledger (both overridable for tests)."""
    repo_root = repo_root or ROOT
    caps = set(worker_caps or [])
    idx = _spec_index(repo_root)
    status = _status_map(idx)
    claimed = CL.claimed_units(root=claims_root)
    # Load this repository's architecture contract ONCE (adoption safe: (None, None)
    # when absent). The mandatory placement gate below refuses a BUILD unit whose spec
    # lacks a placement that resolves to a contract area, so a placeless spec is never
    # surfaced as claimable while a contract exists. This is the claim side of the
    # O3/RJ2 property ("never claimed"), enforced at the claimability decision (the
    # right layer: the claim ledger stays a pure coordination primitive that does not
    # read specs) and reusing the one predicate in arch via validate, so it agrees with
    # the ready transition and run-check. Review units are not gated: a review is of an
    # already-built spec, not a build claim.
    arch, contract = V.load_repo_contract(repo_root)
    out, seen = [], set()

    def _add(sid, plan_id, kind):
        if sid in seen or sid in claimed:
            return
        fm = idx.get(sid) or {}
        # THE DEPENDENCY GATE, asked once for every offer however the unit was found: a build
        # unit whose spec declares an unshipped prerequisite is never surfaced, and the same
        # function that decides it explains it in withheld().
        if dependency_gate(fm, status, kind):
            return
        reqs = fm.get("requires") or []
        if not CL.capability_ok(caps, reqs):
            return
        if not _in_scope(fm, plan_id, scope):
            return
        if kind == "build" and contract is not None and arch.placement_gate(fm, contract):
            return  # placeless build with a contract present: never claimed
        seen.add(sid)
        out.append({"spec": sid, "plan": plan_id, "kind": kind, "requires": list(reqs)})

    # BUILD work from every ACTIVE plan's frontier (the plan's ordering question, in
    # _plan_build_candidates), then from the standalone lane, then review work. Every one of
    # them goes through _add, which is where the spec's own declared depends_on is asked.
    for sid, plan_id in _plan_build_candidates(repo_root, status):
        _add(sid, plan_id, "build")
    # BUILD work from standalone/bug specs: a ready spec in the standalone lane, which no plan
    # orders. This loop SELECTS the lane's candidates and nothing more - the dependency rule is
    # not repeated here, because _add asks it for every candidate from either lane.
    for sid, fm in idx.items():
        if _is_standalone_build(fm):
            _add(sid, None, "build")
    # REVIEW work: any spec awaiting its verdict.
    for sid, fm in idx.items():
        if fm.get("status") == "review":
            _add(sid, fm.get("plan"), "review")
    return out


def main(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="veldo frontier",
                                 description="List the claimable units for a worker.")
    ap.add_argument("--caps", default="", help="comma-separated worker capabilities")
    ap.add_argument("--plan", default=None, help="scope to one plan id")
    ap.add_argument("--label", default=None, help="scope to specs carrying this label")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)
    caps = [c.strip() for c in args.caps.split(",") if c.strip()]
    scope = {}
    if args.plan:
        scope["plan"] = args.plan
    if args.label:
        scope["label"] = args.label
    units = claimable(worker_caps=caps, scope=scope or None)
    if args.json:
        print(json.dumps(units, indent=2))
    else:
        if not units:
            print("nothing claimable")
        for u in units:
            print("%-8s %-12s %s%s" % (u["kind"], u["spec"], u["plan"] or "(standalone)",
                                       (" requires " + ",".join(u["requires"])) if u["requires"] else ""))
    # The withheld report goes to STDERR in both modes, so it is always visible next to a short
    # or empty queue while stdout stays exactly the claimable set that callers already parse.
    for h in withheld(scope=scope or None):
        sys.stderr.write("withheld %-12s waiting on %s\n"
                         % (h["spec"], ", ".join("%s (%s)" % (d, s) for d, s in h["unmet"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
