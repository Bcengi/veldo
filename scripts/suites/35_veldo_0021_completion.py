"""VELDO-0021: completion and executable eligibility predicates (PLAN-0019 W6).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 35_veldo_0021_completion

WHAT IS UNDER TEST. .veldo/completion_contract.py: the four completion facts, each with its own
evidence and none implying another (AC1); the complete authoritative snapshot every execution entry
reads, the named refusals for stale or missing prerequisites and the provider charge reservation
(AC2); the proof, review and outside-verification obligations of engineering completion (AC3); and
the publication transition table with the R32 recovery findings (AC4). The four declared falsifiers
are applied to a COPY of the module and required to turn their named row red while the unmutated
module passes it.
"""
import importlib.util as _v21_ilu
import shutil as _v21_shutil

_v21_spec = _v21_ilu.spec_from_file_location("v21_completion", ROOT / ".veldo" / "completion_contract.py")
CC21 = _v21_ilu.module_from_spec(_v21_spec)
_v21_spec.loader.exec_module(CC21)
_v21_src = (ROOT / ".veldo" / "completion_contract.py").read_text()
_v21_authspec = _v21_ilu.spec_from_file_location("v21_authz", ROOT / ".veldo" / "authorization.py")
AUTH21 = _v21_ilu.module_from_spec(_v21_authspec)
_v21_authspec.loader.exec_module(AUTH21)


def _v21_mutated(old, new):
    d = Path(tempfile.mkdtemp(prefix="v21mut"))
    assert _v21_src.count(old) == 1, (old[:60], _v21_src.count(old))
    (d / "completion_contract.py").write_text(_v21_src.replace(old, new))
    spec = _v21_ilu.spec_from_file_location("v21_mut_%s" % d.name, d / "completion_contract.py")
    m = _v21_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v21_shutil.rmtree(d, ignore_errors=True)
    return m


# ---------------------------------------------------------------------------------------------
# AC1: four facts, own evidence, no implication.
# ---------------------------------------------------------------------------------------------
_v21_subject = {"id": "VELDO-0021", "revision": 1}


def _v21_receipt(kind, **over):
    r = {"fact": kind, "subject": dict(_v21_subject)}
    for f in CC21.COMPLETION_FACTS[kind]["evidence"]:
        r[f] = True
    r.update({"acceptor": "dmitry", "assessor": "dmitry"})
    r.update(over)
    return r


expect("VELDO-0021 AC1 completion/registry: the fact registry is exactly attempt_finished, artifact_accepted, revision_landed and "
       "objective_satisfied, each citing its clause with its evidence fields (R70/R76), and a complete receipt of each kind "
       "establishes its fact; the machine set is bound to authorization.MACHINE_ACTORS",
       tuple(CC21.COMPLETION_FACTS) == CC21.FACT_ORDER == ("attempt_finished", "artifact_accepted", "revision_landed", "objective_satisfied")
       and all(CC21.fact_problems(k, _v21_receipt(k), _v21_subject) == [] for k in CC21.FACT_ORDER)
       and CC21.COMPLETION_FACTS["revision_landed"]["evidence"] == ("publication_receipt", "remote_confirmation", "replicated", "spec_shipped_event")
       and CC21.MACHINE_ACTORS == AUTH21.MACHINE_ACTORS)
_v21_pair_failures = []
for _v21_a in CC21.FACT_ORDER:
    for _v21_b in CC21.FACT_ORDER:
        if _v21_a == _v21_b:
            continue
        _v21_state = CC21.completion_state([_v21_receipt(_v21_a)], _v21_subject)
        if CC21.implies(_v21_a, _v21_b) or not _v21_state[_v21_a] or _v21_state[_v21_b]:
            _v21_pair_failures.append((_v21_a, _v21_b, _v21_state))
        if not any("not %s" % _v21_b in p for p in CC21.fact_problems(_v21_b, _v21_receipt(_v21_a), _v21_subject)):
            _v21_pair_failures.append((_v21_a, _v21_b, "cross-kind receipt accepted"))
expect("VELDO-0021 AC1 completion/non-implication: over every ordered pair of facts, a receipt establishing one leaves the other "
       "unestablished and is refused as evidence for it (failures: %s)" % _v21_pair_failures[:3],
       _v21_pair_failures == [])
_v21_missing_failures = [(k, f) for k in CC21.FACT_ORDER for f in CC21.COMPLETION_FACTS[k]["evidence"]
                         if not any("evidence %s is missing" % f in p for p in CC21.fact_problems(k, _v21_receipt(k, **{f: None}), _v21_subject))]
expect("VELDO-0021 AC1 completion/evidence: every evidence field of every fact is required by name; a wrong subject, a superseded "
       "receipt and a machine acceptor or assessor each refuse (failures: %s)" % _v21_missing_failures,
       _v21_missing_failures == []
       and any("is about VELDO-0021@2" in p for p in CC21.fact_problems("revision_landed", _v21_receipt("revision_landed", subject={"id": "VELDO-0021", "revision": 2}), _v21_subject))
       and any("superseded" in p for p in CC21.fact_problems("artifact_accepted", _v21_receipt("artifact_accepted", superseded_by="r-2"), _v21_subject))
       and any("machine actor" in p for p in CC21.fact_problems("artifact_accepted", _v21_receipt("artifact_accepted", acceptor="agent"), _v21_subject))
       and any("machine actor" in p for p in CC21.fact_problems("objective_satisfied", _v21_receipt("objective_satisfied", assessor="Ava"), _v21_subject)))
expect("VELDO-0021 AC1 completion/build-only: a finished attempt with trusted exit and accounting establishes attempt_finished and "
       "nothing else: revision_landed stays False without its publication receipt",
       CC21.completion_state([_v21_receipt("attempt_finished")], _v21_subject) == {"attempt_finished": True, "artifact_accepted": False, "revision_landed": False, "objective_satisfied": False})
# THE DECLARED FALSIFIER: infer revision landed from attempt finished.
_V21_M1 = _v21_mutated('''        state[kind] = any(not fact_problems(kind, r, subject) for r in mine)
''', '''        state[kind] = any(not fact_problems(kind, r, subject) for r in mine)
        if kind == "revision_landed" and state.get("attempt_finished"):
            state[kind] = True  # mutant: a clean attempt is a landing
''')
expect("VELDO-0021 AC1 completion/build-only DRIVEN (the declared falsifier): with revision_landed inferred from attempt_finished in a "
       "copy, a build-only attempt reads as landed, so the row reds; unmutated it does not",
       _V21_M1.completion_state([_v21_receipt("attempt_finished")], _v21_subject)["revision_landed"] is True
       and CC21.completion_state([_v21_receipt("attempt_finished")], _v21_subject)["revision_landed"] is False)

# ---------------------------------------------------------------------------------------------
# AC2: snapshots, eligibility entries, charge reservation.
# ---------------------------------------------------------------------------------------------
_v21_snap = {"domain_uuid": "d", "repository_uuid": "r", "source_commit": "c1", "journal_sequence": 40, "published_watermark": 40,
             "read_set": {k: {"version": 1, "digest": "sha256:%s" % k} for k in CC21.READ_SET_KINDS}}
_v21_current = {k: {"version": 1, "digest": "sha256:%s" % k} for k in CC21.READ_SET_KINDS}
_v21_all_facts = {p: True for ps in CC21.ENTRY_PREDICATES.values() for p in ps}
expect("VELDO-0021 AC2 eligibility/registry: the entries are exactly the nine of R70 with review asking the draft-plan, decision and "
       "dependency predicates like build; the read-set kinds are the twelve of R70; a complete current snapshot with every "
       "predicate true is eligible at every entry",
       set(CC21.ELIGIBILITY_ENTRIES) == {"selection", "direct_execution", "build", "review", "claim", "redispatch", "provider_request", "result_acceptance", "publication"}
       and set(CC21.ENTRY_PREDICATES) == set(CC21.ELIGIBILITY_ENTRIES) and len(CC21.READ_SET_KINDS) == 12
       and {"plan_not_draft", "decisions_settled", "dependencies_resolved"} <= set(CC21.ENTRY_PREDICATES["review"])
       and all(CC21.eligibility(e, _v21_snap, _v21_current, _v21_all_facts)["eligible"] for e in CC21.ELIGIBILITY_ENTRIES))
_v21_stale_failures = []
for _v21_k in CC21.READ_SET_KINDS:
    _v21_cur2 = dict(_v21_current, **{_v21_k: {"version": 2, "digest": "sha256:new"}})
    if not any("stale read: %s moved" % _v21_k in r for r in CC21.eligibility("build", _v21_snap, _v21_cur2, _v21_all_facts)["refusals"]):
        _v21_stale_failures.append(_v21_k)
    if not any("read set lacks %s" % _v21_k in r for r in CC21.eligibility("build", dict(_v21_snap, read_set={x: v for x, v in _v21_snap["read_set"].items() if x != _v21_k}), _v21_current, _v21_all_facts)["refusals"]):
        _v21_stale_failures.append(_v21_k + ":missing")
expect("VELDO-0021 AC2 eligibility/read-set: mutating each read-set kind's version after the snapshot while the project version stays "
       "fixed is a named stale-read refusal, and a snapshot missing any kind is incomplete (failures: %s)" % _v21_stale_failures,
       _v21_stale_failures == []
       and all(any("snapshot lacks %s" % f in p for p in CC21.snapshot_problems({k: v for k, v in _v21_snap.items() if k != f})) for f in CC21.SNAPSHOT_IDENTITY))
_v21_pred_failures = [(e, p) for e, ps in CC21.ENTRY_PREDICATES.items() for p in ps
                      if not any("%s requires %s" % (e, p) in r for r in CC21.eligibility(e, _v21_snap, _v21_current, {q: True for q in _v21_all_facts if q != p})["refusals"])]
expect("VELDO-0021 AC2 eligibility/predicates: every predicate of every entry refuses by name when it is not literally true, "
       "including the negative no_blockers predicate (failures: %s)" % _v21_pred_failures[:3],
       _v21_pred_failures == [] and any("review requires plan_not_draft" in r for r in CC21.eligibility("review", _v21_snap, _v21_current, dict(_v21_all_facts, plan_not_draft=False))["refusals"]))
expect("VELDO-0021 AC2 eligibility/review-draft-plan: review against a draft governing plan is refused exactly as build is",
       CC21.eligibility("review", _v21_snap, _v21_current, dict(_v21_all_facts, plan_not_draft=False))["eligible"] is False
       and CC21.eligibility("build", _v21_snap, _v21_current, dict(_v21_all_facts, plan_not_draft=False))["eligible"] is False)
# THE DECLARED FALSIFIER: allow review against a draft governing plan.
_V21_M2 = _v21_mutated('''    "review": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers", "reviewer_independent"),
''', '''    "review": ("decisions_settled", "dependencies_resolved", "no_blockers", "reviewer_independent"),  # mutant: review skips the plan
''')
expect("VELDO-0021 AC2 eligibility/review-draft-plan DRIVEN (the declared falsifier): with review no longer asking plan_not_draft in a "
       "copy, review against a draft plan is eligible, so the row reds; unmutated it is refused",
       _V21_M2.eligibility("review", _v21_snap, _v21_current, dict(_v21_all_facts, plan_not_draft=False))["eligible"] is True
       and CC21.eligibility("review", _v21_snap, _v21_current, dict(_v21_all_facts, plan_not_draft=False))["eligible"] is False)
_v21_rem = {"account": 100.0, "project": 50.0, "unit": 20.0}
expect("VELDO-0021 AC2 eligibility/charge: a bounded maximum below every remainder is allocated from all three ceilings together; at "
       "a remainder it is allowed; above any one remainder it is refused naming the ceiling; an unknown or unbounded maximum and an "
       "unknown remainder are refused before the provider call; sequential requests never spend the same remainder twice",
       CC21.charge_allocation(10.0, _v21_rem) == {"allowed": True, "remaining_after": {"account": 90.0, "project": 40.0, "unit": 10.0}, "refusal": None}
       and CC21.charge_allocation(20.0, _v21_rem)["allowed"] is True
       and "unit remainder" in (CC21.charge_allocation(20.5, _v21_rem)["refusal"] or "") and CC21.charge_allocation(20.5, _v21_rem)["allowed"] is False
       and CC21.charge_allocation(None, _v21_rem)["allowed"] is False and CC21.charge_allocation(float("inf"), _v21_rem)["allowed"] is False
       and CC21.charge_allocation(1.0, {"account": 100.0, "project": 50.0})["allowed"] is False
       and [r["allowed"] for r in CC21.allocate_sequence([15.0, 15.0], _v21_rem)[0]] == [True, False]
       and CC21.allocate_sequence([15.0, 15.0], _v21_rem)[1]["unit"] == 5.0)
expect("VELDO-0021 AC2 eligibility/exposure: reconciled usage releases the unspent allocation and authoritative proof of no charge "
       "releases all of it; a timeout, a cancellation and a delayed usage report release nothing",
       CC21.exposure_after({"allocated": 10.0}, {"kind": "reconciled_usage", "charge": 4.0})["released"] == 6.0
       and CC21.exposure_after({"allocated": 10.0}, {"kind": "proof_of_no_charge", "authoritative": True})["released"] == 10.0
       and all(CC21.exposure_after({"allocated": 10.0}, {"kind": k})["released"] == 0 for k in ("timeout", "cancelled", "delayed_usage_report"))
       and CC21.exposure_after({"allocated": 10.0}, {"kind": "proof_of_no_charge", "authoritative": False})["released"] == 0)

# ---------------------------------------------------------------------------------------------
# AC3: engineering completion obligations.
# ---------------------------------------------------------------------------------------------
_v21_bundle = {"implementation_commit": "abc123", "spec": {"id": "VELDO-0021", "revision": 1, "status": "ready", "criteria": ["AC1", "AC2"]},
               "proof": {"producer": "ava", "criteria": [{"id": "AC1", "evidence": [{"digest": "sha256:e1"}]}, {"id": "AC2", "evidence": [{"digest": "sha256:e2"}]}],
                         "checks": [{"name": "gate", "command": "bash scripts/verify.sh", "exit_code": 0, "observation_ref": "obs-1"}]},
               "review": {"reviewer": "codex", "findings": [{"blocking": True, "disposition": "fixed"}]},
               "candidate": {"root": "/cand", "tree_digest": "sha256:tree", "tree_digest_after_run": "sha256:tree"},
               "verifier": {"path": "/opt/veldo/scripts/verify.sh", "digest": "sha256:ver"}, "protected_paths_touched": [], "approval": None}
_v21_exists = lambda c: c in {"abc123"}
_v21_obl_cases = {
    "implementation_commit_exists": dict(_v21_bundle, implementation_commit="nope"),
    "accepted_spec_revision": dict(_v21_bundle, spec=dict(_v21_bundle["spec"], status="draft")),
    "complete_criterion_set": dict(_v21_bundle, proof=dict(_v21_bundle["proof"], criteria=[])),
    "evidence_per_criterion": dict(_v21_bundle, proof=dict(_v21_bundle["proof"], criteria=[{"id": "AC1", "evidence": []}, {"id": "AC2", "evidence": [{"digest": "sha256:e2"}]}])),
    "producer_identity": dict(_v21_bundle, proof={k: v for k, v in _v21_bundle["proof"].items() if k != "producer"}),
    "checks_observed": dict(_v21_bundle, proof=dict(_v21_bundle["proof"], checks=[{"name": "gate", "status": "passed"}])),
    "reviewer_identity": dict(_v21_bundle, review={}),
    "reviewer_independent": dict(_v21_bundle, review=dict(_v21_bundle["review"], reviewer="Ava")),
    "objections_disposed": dict(_v21_bundle, review=dict(_v21_bundle["review"], findings=[{"blocking": True}])),
    "candidate_tree": dict(_v21_bundle, candidate={"root": "/cand"}),
    "verifier_installed_outside_candidate": dict(_v21_bundle, verifier={"path": "/cand/scripts/verify.sh", "digest": "sha256:v"}),
    "protected_path_approval": dict(_v21_bundle, protected_paths_touched=[".veldo/policy.yaml"]),
    "post_run_tree_equal": dict(_v21_bundle, candidate=dict(_v21_bundle["candidate"], tree_digest_after_run="sha256:mutated")),
}
_v21_obl_failures = [n for n, fx in _v21_obl_cases.items() if not any(p.startswith(n + ":") for p in CC21.completion_problems(fx, _v21_exists))]
expect("VELDO-0021 AC3 completion/obligations: a complete bundle is complete; each of the thirteen obligations has one fixture refused "
       "by its own name (nonexistent commit, draft spec, empty criteria, missing evidence, no producer, a fabricated check, no "
       "reviewer, builder as reviewer, undisposed objection, no candidate tree, verifier inside the candidate, unapproved protected "
       "path, mutated tree) (failures: %s)" % _v21_obl_failures,
       CC21.completion_problems(_v21_bundle, _v21_exists) == [] and set(_v21_obl_cases) == set(CC21.PROOF_OBLIGATIONS) and _v21_obl_failures == []
       and any("mapped twice" in p for p in CC21.completion_problems(dict(_v21_bundle, proof=dict(_v21_bundle["proof"], criteria=_v21_bundle["proof"]["criteria"] + [_v21_bundle["proof"]["criteria"][0]])), _v21_exists)))
expect("VELDO-0021 AC3 completion/empty-proof: an empty criterion universe, in the proof or in the specification, proves nothing and is "
       "refused by name",
       any("complete_criterion_set" in p for p in CC21.completion_problems(dict(_v21_bundle, proof=dict(_v21_bundle["proof"], criteria=[])), _v21_exists))
       and any("complete_criterion_set" in p for p in CC21.completion_problems(dict(_v21_bundle, spec=dict(_v21_bundle["spec"], criteria=[]), proof=dict(_v21_bundle["proof"], criteria=[])), _v21_exists)))
# THE DECLARED FALSIFIER: accept an empty criterion universe as valid proof.
_V21_M3 = _v21_mutated('''    if not spec_criteria or not ids or sorted(ids) != sorted(spec_criteria):
''', '''    if sorted(ids) != sorted(spec_criteria):  # mutant: empty equals empty
''')
expect("VELDO-0021 AC3 completion/empty-proof DRIVEN (the declared falsifier): with empty-equals-empty accepted in a copy, a proof over no "
       "criteria for a spec declaring none is complete, so the row reds; unmutated it is refused",
       CC21.completion_problems(dict(_v21_bundle, spec=dict(_v21_bundle["spec"], criteria=[]), proof=dict(_v21_bundle["proof"], criteria=[])), _v21_exists) != []
       and _V21_M3.completion_problems(dict(_v21_bundle, spec=dict(_v21_bundle["spec"], criteria=[]), proof=dict(_v21_bundle["proof"], criteria=[])), _v21_exists) == [])

# ---------------------------------------------------------------------------------------------
# AC4: publication transitions and recovery findings.
# ---------------------------------------------------------------------------------------------
_v21_ev = {p: True for _s, _e, ps, _n in CC21.PUBLICATION_TRANSITIONS for p in ps}
_v21_chain = [("candidate_built", "gate_green"), ("verified", "authority_recheck_ok"), ("authorized", "push_cas_ok"), ("published", "remote_confirmed"), ("confirmed", "receipt_replicated")]
_v21_walk = []
_v21_state = "candidate_built"
for _s, _e in _v21_chain:
    _v21_state, _why = CC21.publication_step(_v21_state, _e, _v21_ev)
    _v21_walk.append(_v21_state)
expect("VELDO-0021 AC4 completion/transition-table: the full chain walks candidate_built -> verified -> authorized -> published -> "
       "confirmed -> completed with every predicate; each predicate of each step refuses by name when absent; an undeclared pair "
       "and an unknown state refuse; gate red, approval rejected, dependency withdrawn, authority revoked and a moved remote tip "
       "each halt",
       _v21_walk == ["verified", "authorized", "published", "confirmed", "completed"]
       and all(CC21.publication_step(s, e, {q: True for q in _v21_ev if q != p})[0] is None and p in CC21.publication_step(s, e, {q: True for q in _v21_ev if q != p})[1]
               for s, e, ps, _n in CC21.PUBLICATION_TRANSITIONS for p in ps)
       and CC21.publication_step("verified", "push_cas_ok", _v21_ev)[0] is None and CC21.publication_step("nowhere", "gate_green", _v21_ev)[0] is None
       and CC21.publication_step("candidate_built", "gate_red", {})[0] == "halted" and CC21.publication_step("verified", "approval_rejected", {})[0] == "halted"
       and CC21.publication_step("verified", "dependency_withdrawn", {})[0] == "halted" and CC21.publication_step("verified", "authority_revoked", {})[0] == "halted"
       and CC21.publication_step("authorized", "remote_tip_moved", {})[0] == "halted")
expect("VELDO-0021 AC4 completion/recovery-findings: the five R32 findings each need their evidence; process absence, checkpoint loss, "
       "lease expiry and nonce consumption justify only outcome_unknown",
       set(CC21.RECOVERY_FINDINGS) == {"not_dispatched", "running", "effect_committed", "acknowledgement_lost", "outcome_unknown"}
       and CC21.recovery_finding({"trusted_target_evidence": True}) == "effect_committed"
       and CC21.recovery_finding({"receiver_group_identity": True, "invocation_identity": True}) == "running"
       and CC21.recovery_finding({"receiver_acceptance_evidence": True}) == "acknowledgement_lost"
       and CC21.recovery_finding({"receiver_evidence_of_no_start": True}) == "not_dispatched"
       and CC21.recovery_finding({"process_absent": True, "checkpoint_lost": True, "lease_expired": True, "nonce_consumed": True}) == "outcome_unknown")
expect("VELDO-0021 AC4 completion/unknown-publication: a lost acknowledgement after the push moves the chain to awaiting_authority, never to "
       "published, confirmed or completed; only trusted target evidence moves it on to published, and only remote confirmation and a "
       "replicated receipt complete it",
       CC21.publication_step("authorized", "acknowledgement_lost", {})[0] == "awaiting_authority"
       and CC21.publication_step("published", "acknowledgement_lost", {})[0] == "awaiting_authority"
       and CC21.publication_step("awaiting_authority", "recovery_effect_committed", {})[0] is None
       and CC21.publication_step("awaiting_authority", "recovery_effect_committed", {"trusted_target_evidence": True})[0] == "published"
       and CC21.publication_step("awaiting_authority", "receipt_replicated", _v21_ev)[0] is None)
# THE DECLARED FALSIFIER: treat a lost publication acknowledgement as successful completion without remote evidence.
_V21_M4 = _v21_mutated('''    ("authorized", "acknowledgement_lost", (), "awaiting_authority"),
''', '''    ("authorized", "acknowledgement_lost", (), "completed"),  # mutant: silence is success
''')
expect("VELDO-0021 AC4 completion/unknown-publication DRIVEN (the declared falsifier): with a lost acknowledgement read as completion in a "
       "copy, the chain completes with no remote evidence, so the row reds; unmutated it waits for authority",
       _V21_M4.publication_step("authorized", "acknowledgement_lost", {})[0] == "completed"
       and CC21.publication_step("authorized", "acknowledgement_lost", {})[0] == "awaiting_authority")
_v21_lr = {"implementation_commit": "abc123", "proof_digest": "sha256:p", "reviewed_source_digest": "sha256:s", "old_remote_tip": "old", "candidate_commit": "cand",
           "tested_tree": "sha256:tree", "gate_invocation": "bash scripts/verify.sh", "gate_output_location": "observations://gate/1", "unit_id": "u-1",
           "dispatch_id": "d-1", "remote_confirmation": "remote:cand", "replication_receipt": "repl-1"}
expect("VELDO-0021 AC4 completion/landing-receipt: a receipt joining implementation, proof, reviewed source, old tip, candidate, tested "
       "tree, gate invocation with an external output location, unit, dispatch, remote confirmation and replication certifies; each "
       "missing join, gate output inside the candidate, a receipt inside its own commit, and a shipped status string, clean attempt, "
       "passing review or process exit as basis each refuse",
       CC21.landing_receipt_problems(_v21_lr) == []
       and all(any("lacks %s" % f in p for p in CC21.landing_receipt_problems({k: v for k, v in _v21_lr.items() if k != f})) for f in _v21_lr)
       and any("inside the candidate" in p for p in CC21.landing_receipt_problems(dict(_v21_lr, gate_output_location="candidate:.veldo/last_verify")))
       and any("cannot contain itself" in p for p in CC21.landing_receipt_problems(dict(_v21_lr, receipt_inside_certified_commit=True)))
       and all(any("not a completion chain" in p for p in CC21.landing_receipt_problems(dict(_v21_lr, basis=b))) for b in ("shipped_status_string", "clean_attempt", "passing_review", "process_exit")))
