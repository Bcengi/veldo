"""VELDO-0019: combined dependency graph and decision observation rules (PLAN-0019 W4).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 32_veldo_0019_combined_graph

WHAT IS UNDER TEST. .veldo/graph_contract.py: the union of every execution prerequisite edge family
and its acyclicity, independent of the release membership forest (AC1); dependency resolution to
exact accepted revisions or completion receipts over the full target-state matrix (AC2); the
reverse-closure invalidation of dependents, checked against an independent small-graph oracle
written here (AC3); and decision bindings, settlement and observation freshness (AC4). The four
declared falsifiers are applied to a COPY of the module and required to turn their named row red
while the unmutated module passes it.
"""
import importlib.util as _v19_ilu
import shutil as _v19_shutil

_v19_spec = _v19_ilu.spec_from_file_location("v19_graph", ROOT / ".veldo" / "graph_contract.py")
GC19 = _v19_ilu.module_from_spec(_v19_spec)
_v19_spec.loader.exec_module(GC19)
_v19_src = (ROOT / ".veldo" / "graph_contract.py").read_text()


def _v19_mutated(old, new):
    d = Path(tempfile.mkdtemp(prefix="v19mut"))
    assert _v19_src.count(old) == 1, (old[:60], _v19_src.count(old))
    src = _v19_src.replace(old, new).replace("ROOT = Path(__file__).resolve().parent.parent", "ROOT = Path(%r)" % str(ROOT))
    (d / "graph_contract.py").write_text(src)
    spec = _v19_ilu.spec_from_file_location("v19_mut_%s" % d.name, d / "graph_contract.py")
    m = _v19_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v19_shutil.rmtree(d, ignore_errors=True)
    return m


# ---------------------------------------------------------------------------------------------
# AC1: the union is acyclic before authorization; membership is not an edge.
# ---------------------------------------------------------------------------------------------
expect("VELDO-0019 AC1 combined-graph/registry: the edge-family registry is exactly the five R14 families and the adapter "
       "table equals it in both directions",
       set(GC19.EDGE_FAMILIES) == {"plan_work", "spec_depends_on", "project_dependency", "decision_prerequisite", "release_execution_order"}
       and set(GC19.GRAPH_ADAPTERS) == set(GC19.EDGE_FAMILIES) and all(callable(f) for f in GC19.GRAPH_ADAPTERS.values()))
_v19_plans = [{"id": "PLAN-X", "work": [{"item": "W1", "spec": "S-A", "depends_on": ["S-B"]}, {"item": "W2", "spec": "S-B", "depends_on": []}]}]
_v19_specs = [{"id": "S-B", "depends_on": ["S-C"]}, {"id": "S-C", "depends_on": []}]
_v19_projects = [{"alias": "P1", "dependencies": ["P2"]}, {"alias": "P2", "dependencies": []}]
_v19_decisions = [{"id": "DEC-1", "status": "draft", "binding": {"subjects": [{"id": "S-C"}]}}, {"id": "DEC-2", "status": "decided", "binding": {"subjects": [{"id": "S-A"}]}}]
_v19_execs = [{"alias": "RX-2", "after": ["RX-1"]}]
_v19_edges = {fam: GC19.GRAPH_ADAPTERS[fam](src) for fam, src in (("plan_work", _v19_plans), ("spec_depends_on", _v19_specs), ("project_dependency", _v19_projects),
                                                                   ("decision_prerequisite", _v19_decisions), ("release_execution_order", _v19_execs))}
expect("VELDO-0019 AC1 combined-graph/adapters: each adapter derives its family's edges from plain records (plan work, spec "
       "depends_on, project dependencies, unsettled decision prerequisites only, release execution order), and the union "
       "of these acyclic families is acyclic",
       _v19_edges["plan_work"] == {("S-A", "S-B")} and _v19_edges["spec_depends_on"] == {("S-B", "S-C")}
       and _v19_edges["project_dependency"] == {("P1", "P2")} and _v19_edges["decision_prerequisite"] == {("S-C", "DEC-1")}
       and _v19_edges["release_execution_order"] == {("RX-2", "RX-1")}
       and GC19.authorization_problems(_v19_edges) == [])
# Every pair of families gets a ring spanning it; each family alone stays acyclic.
_v19_fams = list(GC19.EDGE_FAMILIES)
_v19_pair_failures = []
for _v19_i in range(len(_v19_fams)):
    for _v19_j in range(_v19_i + 1, len(_v19_fams)):
        _v19_a, _v19_b = _v19_fams[_v19_i], _v19_fams[_v19_j]
        _v19_e = {_v19_a: {("N1", "N2")}, _v19_b: {("N2", "N1")}}
        if GC19.authorization_problems({_v19_a: {("N1", "N2")}}) or GC19.authorization_problems({_v19_b: {("N2", "N1")}}):
            _v19_pair_failures.append((_v19_a, _v19_b, "a single family read as cyclic"))
        if not any("has a ring" in p for p in GC19.authorization_problems(_v19_e)):
            _v19_pair_failures.append((_v19_a, _v19_b, "cross-family ring not refused"))
_v19_full = {f: {("N%d" % i, "N%d" % ((i + 1) % 5))} for i, f in enumerate(_v19_fams)}
expect("VELDO-0019 AC1 combined-graph/cross-family-cycle: for every pair of families a ring spanning the pair is refused "
       "while each family alone is acyclic (%d pairs), a ring through all five families is refused, and an unknown "
       "family is refused by name" % (len(_v19_fams) * (len(_v19_fams) - 1) // 2),
       _v19_pair_failures == [] and any("has a ring" in p for p in GC19.authorization_problems(_v19_full))
       and any("unknown edge family" in p for p in GC19.authorization_problems({"telepathy": {("a", "b")}})))
_v19_recs = {"REL-0001": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0007"}, {"kind": "release", "target": "REL-0002"}]}},
             "REL-0002": {"fm": {"members": [{"kind": "plan", "target": "PLAN-0008"}]}}}
expect("VELDO-0019 AC1 combined-graph/membership: a valid release membership forest introduces no edge (the union with an "
       "acyclic graph is still acyclic and the graph has no node for a release the families never name), while an "
       "invalid forest (a ring) blocks by name",
       GC19.authorization_problems(_v19_edges, _v19_recs) == []
       and "REL-0001" not in GC19.combined_graph(_v19_edges)
       and any("release membership: member ring" in p for p in GC19.authorization_problems(
           _v19_edges, {"REL-1": {"fm": {"members": [{"kind": "release", "target": "REL-2"}]}}, "REL-2": {"fm": {"members": [{"kind": "release", "target": "REL-1"}]}}})))
# THE DECLARED FALSIFIER: validate each family separately and omit union-cycle detection.
_V19_M1 = _v19_mutated('''    for ring in cycles(graph):
        problems.append("combined dependency graph has a ring''', '''    for fam in EDGE_FAMILIES:
        graph = combined_graph({fam: edges_by_family.get(fam, ())})  # mutant: one family at a time
    for ring in cycles(graph):
        problems.append("combined dependency graph has a ring''')
expect("VELDO-0019 AC1 combined-graph/cross-family-cycle DRIVEN (the declared falsifier): with families validated one at a "
       "time in a copy, a ring spanning plan_work and spec_depends_on passes, so the row reds; unmutated it is refused",
       _V19_M1.authorization_problems({"plan_work": {("N1", "N2")}, "spec_depends_on": {("N2", "N1")}}) == []
       and GC19.authorization_problems({"plan_work": {("N1", "N2")}, "spec_depends_on": {("N2", "N1")}}) != [])

# ---------------------------------------------------------------------------------------------
# AC2: resolution to exact revisions or completion receipts, over the full target-state matrix.
# ---------------------------------------------------------------------------------------------
_v19_matrix_failures = []
for _v19_fam in GC19.EDGE_FAMILIES:
    _v19_kind = GC19.RESOLVER_KINDS[_v19_fam]
    _v19_good = {"kind": _v19_kind, "revision": 3, "signed": True}
    _v19_cases = {
        "resolved": [_v19_good], "missing": [], "ambiguous": [_v19_good, dict(_v19_good)],
        "inaccessible": [dict(_v19_good, inaccessible=True)], "wrong_revision": [dict(_v19_good, revision=2)],
        "unsupported_receipt": ["shipped"],
    }
    for _v19_state, _v19_cands in _v19_cases.items():
        _v19_r = GC19.resolve_dependency(_v19_fam, "T", 3, _v19_cands)
        if _v19_r["state"] != _v19_state or _v19_r["reference"] != {"family": _v19_fam, "target": "T", "expected_revision": 3} \
                or (_v19_state != "resolved" and not _v19_r["refusal"]) or (_v19_state == "resolved" and _v19_r["refusal"] is not None):
            _v19_matrix_failures.append((_v19_fam, _v19_state, _v19_r))
expect("VELDO-0019 AC2 graph-resolution/matrix: over every family and every target state (%d cells) the resolver answers "
       "the state by name, preserves the reference, and carries a refusal for every state but resolved (failures: %s)"
       % (len(GC19.EDGE_FAMILIES) * len(GC19.TARGET_STATES), _v19_matrix_failures[:3]),
       set(GC19.TARGET_STATES) == {"resolved", "missing", "ambiguous", "inaccessible", "wrong_revision", "unsupported_receipt"}
       and _v19_matrix_failures == [])
expect("VELDO-0019 AC2 graph-resolution/status-only: a shipped status string, an unsigned receipt and a receipt of another "
       "kind are each unsupported_receipt for an engineering edge, never a completion receipt",
       GC19.resolve_dependency("spec_depends_on", "VELDO-0018", 1, ["shipped"])["state"] == "unsupported_receipt"
       and GC19.resolve_dependency("spec_depends_on", "VELDO-0018", 1, [{"kind": "completion_receipt", "revision": 1, "signed": False}])["state"] == "unsupported_receipt"
       and GC19.resolve_dependency("spec_depends_on", "VELDO-0018", 1, [{"kind": "accepted_artifact", "revision": 1, "signed": True}])["state"] == "unsupported_receipt"
       and GC19.resolve_dependency("spec_depends_on", "VELDO-0018", 1, [{"kind": "completion_receipt", "revision": 1, "signed": True}])["state"] == "resolved")
# THE DECLARED FALSIFIER: treat a shipped status string as a completion receipt.
_V19_M2 = _v19_mutated('''    if not isinstance(c, dict):
        return {"reference": ref, "state": "unsupported_receipt",''', '''    if c == "shipped":
        return {"reference": ref, "state": "resolved", "refusal": None}  # mutant: the status string counts
    if not isinstance(c, dict):
        return {"reference": ref, "state": "unsupported_receipt",''')
expect("VELDO-0019 AC2 graph-resolution/status-only DRIVEN (the declared falsifier): with a shipped status string counted as a "
       "completion receipt in a copy, the string resolves, so the row reds; unmutated it is unsupported_receipt",
       _V19_M2.resolve_dependency("spec_depends_on", "VELDO-0018", 1, ["shipped"])["state"] == "resolved"
       and GC19.resolve_dependency("spec_depends_on", "VELDO-0018", 1, ["shipped"])["state"] == "unsupported_receipt")

# ---------------------------------------------------------------------------------------------
# AC3: invalidation closure, checked against an independent oracle written here.
# ---------------------------------------------------------------------------------------------
def _v19_oracle_closure(edges, node):
    """Dependents of node by brute force: repeat 'add every source whose destination is already in
    the set' until nothing changes. Written without reference to the module's walk."""
    dependents = set()
    changed = True
    while changed:
        changed = False
        for src, dst in edges:
            if (dst == node or dst in dependents) and src not in dependents and src != node:
                dependents.add(src)
                changed = True
    return dependents


_v19_chain = {"plan_work": {("U3", "U2")}, "spec_depends_on": {("U2", "U1")}, "project_dependency": {("P9", "U1")},
              "decision_prerequisite": {("U5", "DEC-Z")}, "release_execution_order": {("U4", "U3")}}
_v19_g = GC19.combined_graph(_v19_chain)
_v19_all_edges = {e for es in _v19_chain.values() for e in es}
_v19_closure_failures = [n for n in sorted(_v19_g) if GC19.reverse_closure(_v19_g, n) != _v19_oracle_closure(_v19_all_edges, n)]
expect("VELDO-0019 AC3 graph-invalidation/closure: the module's reverse closure equals the independent oracle's for every "
       "node of a chain spanning all five families (failures: %s)" % _v19_closure_failures,
       _v19_closure_failures == [] and GC19.reverse_closure(_v19_g, "U1") == {"U2", "U3", "U4", "P9"} and GC19.reverse_closure(_v19_g, "U5") == set())
_v19_units = {"U1": {"state": "COMPLETED", "receipts": ["r1"], "ready": False},
              "U2": {"state": "RUNNING", "ready": False, "publication_eligible": True},
              "U3": {"state": "READY", "ready": True, "publication_eligible": False},
              "U4": {"state": "COMPLETED", "receipts": ["r4"], "impact_records": []},
              "P9": {"state": "PLANNED", "ready": False},
              "U5": {"state": "RUNNING", "ready": False, "publication_eligible": True}}
_v19_after = GC19.invalidate(_v19_g, "U1", _v19_units, "prerequisite_withdrawn")
expect("VELDO-0019 AC3 graph-invalidation/effect: withdrawing U1 makes the running dependent U2 publication-ineligible, the "
       "queued dependent U3 not ready, the completed dependent U4 keep its receipts and gain one impact record, leaves "
       "U5 (outside the closure) untouched, and the module's own checker agrees with the oracle over the result",
       _v19_after["U2"]["publication_eligible"] is False and _v19_after["U3"]["ready"] is False
       and _v19_after["U4"]["receipts"] == ["r4"] and len(_v19_after["U4"]["impact_records"]) == 1
       and _v19_after["U4"]["impact_records"][0]["requires"] == "new decision"
       and _v19_after["U5"] == _v19_units["U5"] and _v19_after["U1"] == _v19_units["U1"]
       and GC19.invalidation_problems(_v19_units, _v19_after, _v19_g, "U1") == []
       and all(GC19.invalidation_problems(_v19_units, GC19.invalidate(_v19_g, "U1", _v19_units, ev), _v19_g, "U1") == []
               for ev in GC19.INVALIDATION_EVENTS))
expect("VELDO-0019 AC3 graph-invalidation/running-publication: a result that leaves the running dependent publication-eligible "
       "is refused by the checker by name, and so is a rewritten completed receipt or a changed unit outside the closure",
       any("still publication-eligible" in p for p in GC19.invalidation_problems(_v19_units, dict(_v19_after, U2=dict(_v19_after["U2"], publication_eligible=True)), _v19_g, "U1"))
       and any("receipts were rewritten" in p for p in GC19.invalidation_problems(_v19_units, dict(_v19_after, U4=dict(_v19_after["U4"], receipts=[])), _v19_g, "U1"))
       and any("outside the closure and changed" in p for p in GC19.invalidation_problems(_v19_units, dict(_v19_after, U5=dict(_v19_after["U5"], ready=True)), _v19_g, "U1")))
# THE DECLARED FALSIFIER: leave a running dependent publication-eligible after withdrawal.
_V19_M3 = _v19_mutated('''            u2["ready"] = False
            u2["publication_eligible"] = False
''', '''            u2["ready"] = False
            if u.get("state") != "RUNNING":
                u2["publication_eligible"] = False  # mutant: running work keeps publishing
''')
expect("VELDO-0019 AC3 graph-invalidation/running-publication DRIVEN (the declared falsifier): with running dependents left "
       "publication-eligible in a copy, the checker names U2, so the row reds; unmutated the result is clean",
       any("U2" in p and "still publication-eligible" in p
           for p in GC19.invalidation_problems(_v19_units, _V19_M3.invalidate(_v19_g, "U1", _v19_units, "prerequisite_withdrawn"), _v19_g, "U1"))
       and GC19.invalidation_problems(_v19_units, _v19_after, _v19_g, "U1") == [])

# ---------------------------------------------------------------------------------------------
# AC4: bindings, settlement, observations.
# ---------------------------------------------------------------------------------------------
_v19_authspec = _v19_ilu.spec_from_file_location("v19_authz", ROOT / ".veldo" / "authorization.py")
AUTH19 = _v19_ilu.module_from_spec(_v19_authspec)
_v19_authspec.loader.exec_module(AUTH19)
_v19_binding = {"framing_digest": "sha256:frame", "subjects": [{"kind": k, "id": "%s-1" % k, "digest": "sha256:%s" % k} for k in GC19.BINDING_SUBJECTS]}
expect("VELDO-0019 AC4 decision-observation/binding: a binding names a framing digest and subjects of every R71 kind with id "
       "and digest; a missing framing digest, no subjects, an unknown subject kind and a subject without a digest are "
       "each refused; the machine set is bound to authorization.MACHINE_ACTORS",
       GC19.binding_problems(_v19_binding) == [] and set(GC19.BINDING_SUBJECTS) == {"project", "release_execution", "plan", "backlog_item", "specification", "contract"}
       and any("framing_digest" in p for p in GC19.binding_problems({"subjects": _v19_binding["subjects"]}))
       and any("names no subjects" in p for p in GC19.binding_problems({"framing_digest": "x", "subjects": []}))
       and any("must be {kind in" in p for p in GC19.binding_problems({"framing_digest": "x", "subjects": [{"kind": "moon", "id": "m", "digest": "d"}]}))
       and any("must be {kind in" in p for p in GC19.binding_problems({"framing_digest": "x", "subjects": [{"kind": "plan", "id": "m"}]}))
       and GC19.MACHINE_ACTORS == AUTH19.MACHINE_ACTORS)
_v19_asm_m = {"id": "a-measured", "kind": "measured", "source": "prometheus", "subject_digest": "sha256:s", "max_age": 3600, "expect": 0, "failure_treatment": "blocking"}
_v19_asm_a = {"id": "a-attest", "kind": "attestation", "source": "dmitry", "subject_digest": "sha256:s", "max_age": 86400, "failure_treatment": "blocking"}
_v19_asm_adv = dict(_v19_asm_m, id="a-advisory", failure_treatment="advisory")
_v19_now = 1_000_000
_v19_obs_ok_m = {"kind": "measured", "source": "prometheus", "subject_digest": "sha256:s", "value": 0, "at": _v19_now - 60}
_v19_obs_ok_a = {"kind": "attestation", "source": "dmitry", "subject_digest": "sha256:s", "value": True, "at": _v19_now - 600}
_v19_obs_cases = [
    (_v19_asm_m, None, "missing"), (_v19_asm_m, _v19_obs_ok_m, "current"),
    (_v19_asm_m, dict(_v19_obs_ok_m, at=_v19_now - 4000), "stale"), (_v19_asm_m, dict(_v19_obs_ok_m, value=7), "contradictory"),
    (_v19_asm_m, dict(_v19_obs_ok_m, source="a-blog"), "invalid"), (_v19_asm_m, dict(_v19_obs_ok_m, subject_digest="sha256:other"), "invalid"),
    (_v19_asm_m, {"kind": "measured", "source": "prometheus", "subject_digest": "sha256:s"}, "invalid"),
    (_v19_asm_a, _v19_obs_ok_a, "current"), (_v19_asm_a, dict(_v19_obs_ok_a, at=_v19_now - 90000), "stale"),
    (_v19_asm_a, dict(_v19_obs_ok_a, value="yes"), "contradictory"), (_v19_asm_a, None, "missing"),
    ({"id": "bad", "kind": "gossip", "source": "x", "subject_digest": "d", "max_age": 1}, _v19_obs_ok_m, "invalid"),
]
_v19_obs_failures = [(a["id"], want, GC19.observation_state(a, o, _v19_now)) for a, o, want in _v19_obs_cases
                     if GC19.observation_state(a, o, _v19_now)[0] != want]
expect("VELDO-0019 AC4 decision-observation/matrix: over measured and attestation assumptions crossed with missing, current, "
       "stale, contradictory and invalid observations (%d cells) the state is answered by name; a measured reading "
       "expires exactly as an attestation does (failures: %s)" % (len(_v19_obs_cases), _v19_obs_failures),
       _v19_obs_failures == [] and set(GC19.OBSERVATION_STATES) == {"current", "missing", "stale", "contradictory", "invalid"})
_v19_dec = {"id": "DEC-9", "status": "decided", "binding": _v19_binding}
_v19_obs = {"a-measured": _v19_obs_ok_m, "a-attest": _v19_obs_ok_a, "a-advisory": dict(_v19_obs_ok_m, at=_v19_now - 4000)}
_v19_eff = GC19.eligibility_effect(_v19_dec, [_v19_asm_m, _v19_asm_a, _v19_asm_adv], _v19_obs, _v19_now)
expect("VELDO-0019 AC4 decision-observation/eligibility: a decided decision with a valid binding and current blocking "
       "observations is eligible for all six subjects; a stale ADVISORY assumption only warns; an undecided decision, a "
       "broken binding, and a missing or stale BLOCKING observation each block every subject by name, in one atomic result",
       _v19_eff["eligible"] is True and len(_v19_eff["subjects"]) == 6 and len(_v19_eff["warnings"]) == 1 and "advisory" in _v19_eff["warnings"][0]
       and GC19.eligibility_effect(dict(_v19_dec, status="draft"), [_v19_asm_m], _v19_obs, _v19_now)["eligible"] is False
       and GC19.eligibility_effect(dict(_v19_dec, binding={"subjects": []}), [_v19_asm_m], _v19_obs, _v19_now)["eligible"] is False
       and GC19.eligibility_effect(_v19_dec, [_v19_asm_m], {}, _v19_now)["eligible"] is False
       and any("is missing" in p for p in GC19.eligibility_effect(_v19_dec, [_v19_asm_m], {}, _v19_now)["blocking"]))
expect("VELDO-0019 AC4 decision-observation/stale-measurement: a stale measured governing assumption blocks eligibility and "
       "names itself; the same reading within max_age is current",
       GC19.eligibility_effect(_v19_dec, [_v19_asm_m], {"a-measured": dict(_v19_obs_ok_m, at=_v19_now - 4000)}, _v19_now)["eligible"] is False
       and any("a-measured is stale" in p for p in GC19.eligibility_effect(_v19_dec, [_v19_asm_m], {"a-measured": dict(_v19_obs_ok_m, at=_v19_now - 4000)}, _v19_now)["blocking"])
       and GC19.eligibility_effect(_v19_dec, [_v19_asm_m], {"a-measured": _v19_obs_ok_m}, _v19_now)["eligible"] is True)
# THE DECLARED FALSIFIER: treat a stale measured governing assumption as current.
_V19_M4 = _v19_mutated('''    if age > assumption["max_age"]:
        return "stale", "observation is %r old, the assumption allows %r" % (age, assumption["max_age"])
''', '''    if age > assumption["max_age"] and assumption["kind"] != "measured":
        return "stale", "observation is %r old, the assumption allows %r" % (age, assumption["max_age"])  # mutant: measurements never age
''')
expect("VELDO-0019 AC4 decision-observation/stale-measurement DRIVEN (the declared falsifier): with stale measurements read as "
       "current in a copy the decision is eligible on a 4000-second-old reading against a 3600-second allowance, so the row "
       "reds; unmutated it blocks",
       _V19_M4.eligibility_effect(_v19_dec, [_v19_asm_m], {"a-measured": dict(_v19_obs_ok_m, at=_v19_now - 4000)}, _v19_now)["eligible"] is True
       and GC19.eligibility_effect(_v19_dec, [_v19_asm_m], {"a-measured": dict(_v19_obs_ok_m, at=_v19_now - 4000)}, _v19_now)["eligible"] is False)
_v19_req = {"framing_digest": "sha256:frame", "expires_at": _v19_now + 100, "authorities": ["dmitry"], "settled": False}
_v19_ans = {"framing_digest": "sha256:frame", "decided_by": "dmitry", "ruling": "accept"}
_v19_reviews = [{"principal": "codex", "framing_digest": "sha256:frame", "blocking": False},
                {"principal": "opus", "framing_digest": "sha256:frame", "blocking": True, "disposition": "fixed"}]
expect("VELDO-0019 AC4 decision-observation/settlement: an answer binding the exact framing by a named authority with two "
       "distinct reviewers and every blocking objection disposed settles; a changed framing, an expired request, an "
       "already-settled request, a machine decider, a decider outside the named authorities, two reviews by one principal "
       "counted as one, and an undisposed blocking objection each refuse by name",
       GC19.settlement_problems(_v19_req, _v19_ans, _v19_reviews, 2, _v19_now) == []
       and any("exact framing content" in p for p in GC19.settlement_problems(_v19_req, dict(_v19_ans, framing_digest="sha256:other"), _v19_reviews, 2, _v19_now))
       and any("expired" in p for p in GC19.settlement_problems(_v19_req, _v19_ans, _v19_reviews, 2, _v19_now + 500))
       and any("several winners" in p for p in GC19.settlement_problems(dict(_v19_req, settled=True), _v19_ans, _v19_reviews, 2, _v19_now))
       and any("not a person" in p for p in GC19.settlement_problems(_v19_req, dict(_v19_ans, decided_by="agent"), _v19_reviews, 2, _v19_now))
       and any("not among the request's named authorities" in p for p in GC19.settlement_problems(_v19_req, dict(_v19_ans, decided_by="asya"), _v19_reviews, 2, _v19_now))
       and any("one principal fill one position" in p for p in GC19.settlement_problems(_v19_req, _v19_ans, [dict(_v19_reviews[0]), dict(_v19_reviews[0])], 2, _v19_now))
       and any("without an explicit disposition" in p for p in GC19.settlement_problems(_v19_req, _v19_ans, [_v19_reviews[0], dict(_v19_reviews[1], disposition=None)], 2, _v19_now)))
