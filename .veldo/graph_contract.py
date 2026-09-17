#!/usr/bin/env python3
"""Combined dependency graph and decision observation rules (PLAN-0019 W4, VELDO-0019).

WHAT THIS MODULE IS. Pure predicates over plain data, a contract organ beside entity_contract.py
and release_floor_contract.py: the union of every execution prerequisite edge family and its
acyclicity (R14, AC1), dependency resolution to exact accepted artifact revisions or completion
receipts (R14, AC2), the reverse-closure invalidation an amended or withdrawn prerequisite causes
(R14, R39, AC3), and the decision bindings, settlement and observation freshness rules that decide
whether a governing decision authorizes anything (R40, R71, AC4). Standard library only; reads no
live system; writes nothing. The store, the eligibility service and the tripwire production that
consume these predicates are later packages.

WHAT IT REUSES. The release membership forest is release_floor_contract.membership_problems (a
separately valid forest, never an execution edge); the depth-first ring walk is the shape
validate.py's plan DAG check and release_contract.member_cycles use; the machine-actor set mirrors
authorization.MACHINE_ACTORS and the suite binds them.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.graph_contract/v1"


def _organ(name):
    spec = importlib.util.spec_from_file_location("veldo_graph_" + name, ROOT / ".veldo" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


MACHINE_ACTORS = frozenset({"veldo-executor", "veldo-responder", "executor", "responder", "machine",
                            "agent", "bot", "ava", "automation", "service", "service_account", "service-account"})


def _is_person(name):
    return _is_str(name) and name.strip().lower() not in MACHINE_ACTORS


# ---------------------------------------------------------------------------------------------
# AC1: one combined graph, acyclic before authorization; membership is not an edge.
# ---------------------------------------------------------------------------------------------

# THE EDGE FAMILIES R14 names, each with the adapter that derives its edges from plain records.
# Set equality with the adapter table is asserted by the suite, so a family declared without an
# adapter, or an adapter for a family the design does not name, is a problem by name.
EDGE_FAMILIES = ("plan_work", "spec_depends_on", "project_dependency", "decision_prerequisite", "release_execution_order")


def _edges_plan_work(plans):
    """plan.work items: (spec, depends_on spec) for every declared work dependency."""
    out = set()
    for fm in plans or []:
        for w in fm.get("work") or []:
            if isinstance(w, dict) and _is_str(w.get("spec")):
                for d in w.get("depends_on") or []:
                    if _is_str(d):
                        out.add((w["spec"], d))
    return out


def _edges_spec_depends_on(specs):
    out = set()
    for fm in specs or []:
        if isinstance(fm, dict) and _is_str(fm.get("id")):
            for d in fm.get("depends_on") or []:
                if _is_str(d):
                    out.add((fm["id"], d))
    return out


def _edges_project_dependency(projects):
    out = set()
    for p in projects or []:
        if isinstance(p, dict) and _is_str(p.get("alias") or p.get("uuid")):
            for d in p.get("dependencies") or []:
                if _is_str(d):
                    out.add((p.get("alias") or p.get("uuid"), d))
    return out


def _edges_decision_prerequisite(decisions):
    """A governing decision that a subject waits on: (subject, decision id) for every subject the
    decision's binding names while the decision is not settled (R71: unresolved references block)."""
    out = set()
    for d in decisions or []:
        if isinstance(d, dict) and _is_str(d.get("id")) and d.get("status") != "decided":
            for s in (d.get("binding") or {}).get("subjects") or []:
                if isinstance(s, dict) and _is_str(s.get("id")):
                    out.add((s["id"], d["id"]))
    return out


def _edges_release_execution_order(executions):
    out = set()
    for e in executions or []:
        if isinstance(e, dict) and _is_str(e.get("alias") or e.get("uuid")):
            for d in e.get("after") or []:
                if _is_str(d):
                    out.add((e.get("alias") or e.get("uuid"), d))
    return out


GRAPH_ADAPTERS = {
    "plan_work": _edges_plan_work,
    "spec_depends_on": _edges_spec_depends_on,
    "project_dependency": _edges_project_dependency,
    "decision_prerequisite": _edges_decision_prerequisite,
    "release_execution_order": _edges_release_execution_order,
}


def combined_graph(edges_by_family):
    """{node: {successors}} over the UNION of every family's edges, refusing an unknown family by
    name (a family the registry does not know is not silently merged)."""
    unknown = sorted(set(edges_by_family) - set(EDGE_FAMILIES))
    if unknown:
        raise ValueError("unknown edge family %s (known: %s)" % (", ".join(unknown), ", ".join(EDGE_FAMILIES)))
    graph = {}
    for fam in EDGE_FAMILIES:
        for src, dst in edges_by_family.get(fam, ()):
            graph.setdefault(src, set()).add(dst)
            graph.setdefault(dst, set())
    return graph


def cycles(graph):
    """Every ring in the graph, each as the node list in the order the ring closes (iterative
    depth-first search in deterministic order, the plan DAG check's shape)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    rings, seen = [], set()
    for start in sorted(graph):
        if color[start] != WHITE:
            continue
        stack = [(start, iter(sorted(graph[start])))]
        walk = [start]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color.get(nxt, BLACK) == GRAY:
                    ring = walk[walk.index(nxt):] + [nxt]
                    if tuple(ring) not in seen:
                        seen.add(tuple(ring))
                        rings.append(ring)
                elif color.get(nxt, BLACK) == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(sorted(graph[nxt]))))
                    walk.append(nxt)
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
                walk.pop()
    return rings


def authorization_problems(edges_by_family, release_records=None):
    """Why dependent execution may NOT be authorized (R14): a ring anywhere in the UNION of the
    families (a ring spanning two families is a ring; separately valid families are insufficient),
    or an invalid release membership forest. Membership is validated as the typed forest it is and
    contributes NO edge: a valid forest introduces no implicit order and an invalid one blocks."""
    problems = []
    try:
        graph = combined_graph(edges_by_family)
    except ValueError as e:
        return [str(e)]
    for ring in cycles(graph):
        problems.append("combined dependency graph has a ring: %s (cycles block affected items until the technical authority resolves them, R14)"
                        % " -> ".join(ring))
    if release_records is not None:
        RF = _organ("release_floor_contract")
        problems.extend("release membership: %s" % p for p in RF.membership_problems(release_records))
    return problems


# ---------------------------------------------------------------------------------------------
# AC2: dependencies resolve to exact accepted revisions or completion receipts.
# ---------------------------------------------------------------------------------------------

TARGET_STATES = ("resolved", "missing", "ambiguous", "inaccessible", "wrong_revision", "unsupported_receipt")
# What each family's edge resolves TO (R14): engineering edges to a verified completion receipt,
# project and release-execution edges to an accepted artifact revision, a decision edge to a
# settled decision revision. Never a status string, never path existence.
RESOLVER_KINDS = {
    "plan_work": "completion_receipt",
    "spec_depends_on": "completion_receipt",
    "project_dependency": "accepted_artifact",
    "decision_prerequisite": "settled_decision",
    "release_execution_order": "accepted_artifact",
}
RECEIPT_KINDS = ("completion_receipt", "accepted_artifact", "settled_decision")


def resolve_dependency(family, target, expected_revision, candidates):
    """{reference, state, refusal} for one edge's target (R14): `candidates` is what the resolver
    found under the target id (a list of records). resolved needs exactly one candidate of the
    family's receipt kind, signed, at the expected revision. Two candidates are ambiguous; none is
    missing; a candidate marked inaccessible is inaccessible; one at another revision is
    wrong_revision; one of another kind, or a bare status string ("shipped"), is
    unsupported_receipt. The reference and the named refusal are always preserved in the result."""
    ref = {"family": family, "target": target, "expected_revision": expected_revision}
    kind = RESOLVER_KINDS.get(family)
    if kind is None:
        return {"reference": ref, "state": "unsupported_receipt", "refusal": "unknown edge family %r" % (family,)}
    found = [c for c in (candidates or []) if c is not None]
    if not found:
        return {"reference": ref, "state": "missing", "refusal": "no record resolves %s: missing targets block with named unresolved references" % target}
    if len(found) > 1:
        return {"reference": ref, "state": "ambiguous", "refusal": "%d records resolve %s: an ambiguous target blocks" % (len(found), target)}
    c = found[0]
    if not isinstance(c, dict):
        return {"reference": ref, "state": "unsupported_receipt",
                "refusal": "%s resolves to %r, a status string or path, never a completion receipt or accepted revision (R14)" % (target, c)}
    if c.get("inaccessible") is True:
        return {"reference": ref, "state": "inaccessible", "refusal": "%s resolves to a record this authority cannot read: inaccessible targets block" % target}
    if c.get("kind") != kind or c.get("signed") is not True:
        return {"reference": ref, "state": "unsupported_receipt",
                "refusal": "%s resolves to %r; a %s edge needs a signed %s, never a status string" % (target, c.get("kind"), family, kind)}
    if c.get("revision") != expected_revision:
        return {"reference": ref, "state": "wrong_revision",
                "refusal": "%s resolves at revision %r, the edge expects %r: dependencies bind exact accepted revisions" % (target, c.get("revision"), expected_revision)}
    return {"reference": ref, "state": "resolved", "refusal": None}


# ---------------------------------------------------------------------------------------------
# AC3: invalidation of a prerequisite removes readiness and publication permission downstream.
# ---------------------------------------------------------------------------------------------

def reverse_closure(graph, node):
    """Every node that depends on `node`, transitively (the dependents reached by walking the
    edges backwards), not including `node` itself."""
    reverse = {}
    for src, dsts in graph.items():
        for dst in dsts:
            reverse.setdefault(dst, set()).add(src)
    out, stack = set(), [node]
    while stack:
        n = stack.pop()
        for dep in reverse.get(n, ()):
            if dep not in out:
                out.add(dep)
                stack.append(dep)
    return out


INVALIDATION_EVENTS = ("amendment_rejected_revealing_prerequisite", "prerequisite_withdrawn", "prerequisite_invalidated")


def invalidate(graph, prerequisite, units, event):
    """The effect of an invalidation event on `prerequisite` over `units` ({id: unit}), as a NEW
    mapping (R14, R39): every dependent in the reverse closure loses readiness (queued: ready
    False) and publication permission (running: publication_eligible False); a completed dependent
    keeps its receipts untouched and gains an appended impact record requiring a new decision.
    Nothing outside the closure changes; nothing completed is rewritten."""
    if event not in INVALIDATION_EVENTS:
        raise ValueError("unknown invalidation event %r" % (event,))
    affected = reverse_closure(graph, prerequisite)
    out = {}
    for uid, u in units.items():
        if uid not in affected:
            out[uid] = u
            continue
        u2 = dict(u)
        if u.get("state") in ("COMPLETED",):
            u2["impact_records"] = list(u.get("impact_records") or []) + [
                {"event": event, "prerequisite": prerequisite, "requires": "new decision", "receipts_retained": True}]
        else:
            u2["ready"] = False
            u2["publication_eligible"] = False
            u2["invalidated_by"] = {"event": event, "prerequisite": prerequisite}
        out[uid] = u2
    return out


def invalidation_problems(before, after, graph, prerequisite):
    """Check an invalidation RESULT against the rule (the suite's oracle drives this over an
    independent closure): every dependent in the closure is impacted, a running dependent is
    publication-ineligible, a queued one is not ready, a completed one keeps every receipt and
    gained an impact record, and nothing outside the closure changed."""
    problems = []
    affected = reverse_closure(graph, prerequisite)
    for uid, u in before.items():
        a = after.get(uid)
        if a is None:
            problems.append("%s vanished from the result" % uid)
            continue
        if uid not in affected:
            if a != u:
                problems.append("%s is outside the closure and changed" % uid)
            continue
        if u.get("state") == "COMPLETED":
            if a.get("receipts") != u.get("receipts"):
                problems.append("%s is completed and its receipts were rewritten" % uid)
            if len(a.get("impact_records") or []) != len(u.get("impact_records") or []) + 1:
                problems.append("%s is completed and gained no impact record" % uid)
        else:
            if a.get("ready") is not False:
                problems.append("%s is a queued or running dependent and is still ready" % uid)
            if a.get("publication_eligible") is not False:
                problems.append("%s is a dependent and is still publication-eligible after the prerequisite was withdrawn" % uid)
    return problems


# ---------------------------------------------------------------------------------------------
# AC4: decision bindings, settlement and observation freshness.
# ---------------------------------------------------------------------------------------------

BINDING_SUBJECTS = ("project", "release_execution", "plan", "backlog_item", "specification", "contract")
OBSERVATION_KINDS = ("measured", "attestation")
OBSERVATION_STATES = ("current", "missing", "stale", "contradictory", "invalid")
FAILURE_TREATMENTS = ("blocking", "advisory")


def binding_problems(binding):
    """A governing decision's binding names exact subject digests and explicit affected subjects
    (R71): every subject has a kind from the vocabulary, an id and a digest; the framing digest is
    present. An unresolved reference is a problem by name."""
    problems = []
    if not isinstance(binding, dict):
        return ["a decision binding is a mapping"]
    if not _is_str(binding.get("framing_digest")):
        problems.append("binding carries no framing_digest: a decision binds full framing content, not only id and version")
    subjects = binding.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        problems.append("binding names no subjects: a governing decision binds explicit affected subjects")
        return problems
    for s in subjects:
        if not isinstance(s, dict) or s.get("kind") not in BINDING_SUBJECTS or not _is_str(s.get("id")) or not _is_str(s.get("digest")):
            problems.append("binding subject %r must be {kind in %s, id, digest}" % (s, BINDING_SUBJECTS))
    return problems


def observation_state(assumption, observation, now):
    """(state, reason) for one governing assumption against its latest observation at `now` (an
    integer or float epoch, or an ISO date string compared lexically with the observation's)
    (R71): the assumption declares observation kind, trusted source, subject digest and maximum
    age; the observation must exist (else missing), be of that kind from that source about that
    digest and carry a value and a time (else invalid), be within max_age (else stale), and for a
    measured kind meet the declared expectation (else contradictory). A measured reading expires
    exactly as an attestation does."""
    for f in ("id", "kind", "source", "subject_digest", "max_age"):
        if f not in (assumption or {}):
            return "invalid", "assumption declares no %s" % f
    if assumption["kind"] not in OBSERVATION_KINDS:
        return "invalid", "assumption kind %r is not one of %s" % (assumption["kind"], OBSERVATION_KINDS)
    if observation is None:
        return "missing", "no observation of %s" % assumption["id"]
    if not isinstance(observation, dict):
        return "invalid", "observation is not a record"
    for f, want in (("kind", assumption["kind"]), ("source", assumption["source"]), ("subject_digest", assumption["subject_digest"])):
        if observation.get(f) != want:
            return "invalid", "observation %s is %r, the assumption trusts %r" % (f, observation.get(f), want)
    if "at" not in observation or "value" not in observation:
        return "invalid", "observation carries no time or no value"
    try:
        age = now - observation["at"]
    except TypeError:
        return "invalid", "observation time %r cannot be compared with now %r" % (observation["at"], now)
    if age < 0:
        return "invalid", "observation is dated after now"
    if age > assumption["max_age"]:
        return "stale", "observation is %r old, the assumption allows %r" % (age, assumption["max_age"])
    if assumption["kind"] == "measured":
        expected = assumption.get("expect")
        if expected is not None and observation["value"] != expected:
            return "contradictory", "measured %r, the assumption expects %r" % (observation["value"], expected)
    elif observation["value"] is not True:
        return "contradictory", "attestation value is %r, not True" % (observation["value"],)
    return "current", "observed %r within %r" % (observation["value"], assumption["max_age"])


def settlement_problems(request, answer, reviews, required_reviewers, now):
    """Why an answer cannot settle a decision request (R40, R71): the answer's framing digest
    differs from the request's (a settlement binds the exact framing); the request expired; the
    answer's decider is not a person or not among the request's named authorities when it names
    any; fewer DISTINCT authenticated reviewers than required (several reviews by one principal
    fill one position); an unresolved blocking objection; or the request already has a terminal
    settlement (one request version, one settlement)."""
    problems = []
    if request.get("framing_digest") != answer.get("framing_digest"):
        problems.append("answer binds framing %r, the request is %r: a settlement binds the exact framing content" % (answer.get("framing_digest"), request.get("framing_digest")))
    if request.get("expires_at") is not None and now > request["expires_at"]:
        problems.append("the request expired at %r; an expired answer cannot settle" % (request["expires_at"],))
    if request.get("settled") is True:
        problems.append("this request version already has a terminal settlement; several answers cannot create several winners")
    who = answer.get("decided_by")
    if not _is_person(who):
        problems.append("the answer's decider %r is not a person: only a person or a named authority settles" % (who,))
    elif request.get("authorities") and who not in request["authorities"]:
        problems.append("the answer's decider %r is not among the request's named authorities %s" % (who, sorted(request["authorities"])))
    principals = {r.get("principal") for r in reviews or [] if isinstance(r, dict) and _is_person(r.get("principal"))
                  and r.get("framing_digest") == request.get("framing_digest")}
    if len(principals) < required_reviewers:
        problems.append("%d distinct authenticated reviewer(s) of this framing, %d required: several reviews by one principal fill one position"
                        % (len(principals), required_reviewers))
    open_obj = [r for r in reviews or [] if isinstance(r, dict) and r.get("blocking") is True and r.get("disposition") is None]
    if open_obj:
        problems.append("%d blocking objection(s) without an explicit disposition" % len(open_obj))
    return problems


def eligibility_effect(decision, assumptions, observations, now):
    """The atomic eligibility effect of a governing decision on its subjects (R71): {eligible,
    blocking, warnings, subjects}. Eligible only when the decision is settled (status decided
    with a valid binding) AND every BLOCKING assumption's observation is current; a missing,
    stale, contradictory or invalid observation of a blocking assumption blocks every subject and
    names itself; an advisory assumption warns only when it is explicitly classified
    non-authorizing (failure_treatment advisory) and never authorizes anything by being current.
    Returned as one value so a consumer cannot apply half of it."""
    blocking, warnings = [], []
    problems = binding_problems(decision.get("binding"))
    if decision.get("status") != "decided":
        blocking.append("decision %s is %r, not decided: an unsettled governing decision blocks its subjects" % (decision.get("id"), decision.get("status")))
    blocking.extend(problems)
    for a in assumptions or []:
        state, why = observation_state(a, (observations or {}).get(a.get("id")), now)
        treatment = a.get("failure_treatment", "blocking")
        if treatment not in FAILURE_TREATMENTS:
            blocking.append("assumption %s has failure_treatment %r, not one of %s" % (a.get("id"), treatment, FAILURE_TREATMENTS))
            continue
        if state != "current":
            if treatment == "blocking":
                blocking.append("assumption %s is %s (%s): unavailable evidence cannot silently authorize; a review ticket is owed" % (a.get("id"), state, why))
            else:
                warnings.append("advisory assumption %s is %s (%s)" % (a.get("id"), state, why))
    subjects = [s.get("id") for s in ((decision.get("binding") or {}).get("subjects") or []) if isinstance(s, dict)]
    return {"eligible": not blocking, "blocking": blocking, "warnings": warnings, "subjects": subjects}
