"""the inbound command-and-receipt reconcile (veldo.request/v1 -> an authorized settlement rec

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 11_inbound_command_receipt_reconcile` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 122-126 of the pre-split monolith.
"""


# --- the inbound command-and-receipt reconcile (veldo.request/v1 -> an authorized settlement record,
# WARP-0619, W5-logic of PLAN-0016): the safety-critical crux of the human-decision surface. A human's
# tracker transition is only a SUBMITTED ASSERTION; the repo pulls the ORDERED, ATTRIBUTED changelog
# through the read-only WARP-0603 seam, derives the TRUE actor and intent FROM THE CHANGELOG (never the
# current status), validates against the shipped safety core with identities VERIFIED from the changelog
# (authorization.is_authorized, reused UNCHANGED, composing the frozen two_key), and writes the settlement
# record + event ONLY through an append-only compare-and-swap receipt keyed (request_id, changelog_id). All
# proven ENTIRELY OFFLINE over the deterministic FakeTracker with a seeded changelog (no network). Positive
# controls, the fail-closed BLOCK cases, and six in-memory source-mutation TEETH (each turns one
# load-bearing assertion RED while .veldo/request_reconcile.py stays byte-unchanged).
import hashlib as _rr_hashlib
_rrspec = importlib.util.spec_from_file_location("veldo_request_reconcile", ROOT / ".veldo/request_reconcile.py")
RR = importlib.util.module_from_spec(_rrspec); _rrspec.loader.exec_module(RR)
_rrtaspec = importlib.util.spec_from_file_location("veldo_tracker_adapter_rr", ROOT / ".veldo/tracker_adapter.py")
TA_RR = importlib.util.module_from_spec(_rrtaspec); _rrtaspec.loader.exec_module(TA_RR)
_rrrqspec = importlib.util.spec_from_file_location("veldo_request_rr", ROOT / ".veldo/request.py")
RQ_RR = importlib.util.module_from_spec(_rrrqspec); _rrrqspec.loader.exec_module(RQ_RR)

# The FIXTURE human_decisions policy block (this repository's shipped policy.yaml has none, so the
# authorization engine is INERT there); the registry; the recorded human reasoning (the attestation
# CONTENT - the reconcile supplies the IDENTITIES from the changelog, never from a request field).
_RR_POLICY = {"roles": {"spec_approval": ["approver"], "review_disposition": ["reviewer"]},
              "quorum": {"standard": {"count": 1, "min_independence": 1}}}
_RR_REG = {"alice": {"roles": ["approver", "reviewer"], "independence": "g1", "actor": "human"},
           "bob": {"roles": ["approver"], "independence": "g2", "actor": "human"},
           "veldo-executor": {"roles": ["approver"], "independence": "g9", "actor": "agent"}}
_RR_DIGEST = "sha256:goodgoodgoodgood"
_RR_ATTS_C = {"rationale": "read the whole change end to end and reasoned about the risk it carries",
              "risk_acceptance": "I accept the standard-tier risk", "finding_disposition": "accept"}


def _rr_req(status="needs_decision", digest=_RR_DIGEST, impact=None, tp="spec_approval",
            rid="REQ", issue="VEL-1", ref="proof/X/approval.json", **over):
    rec = {"schema": "veldo.request/v1", "id": rid, "version": 1, "touchpoint": tp, "tier": "standard",
           "status": status, "impact": impact if impact is not None else [],
           "bound_artifact": {"kind": "approval", "ref": ref, "digest": digest},
           "tracker": {"issue": issue, "url": "https://tracker.example/browse/%s" % issue}}
    rec.update(over)
    return rec


def _rr_log(entries):
    # entries: (id, actor, from_state, to_state) -> the ordered attributed changelog shape.
    return [{"id": i, "ts": "2026-07-24T%02d:00:00Z" % n, "actor": a, "from": f, "to": t}
            for n, (i, a, f, t) in enumerate(entries)]


_rr_valid_log = _rr_log([("c1", "builder", None, "Needs Decision"), ("c2", "alice", "Needs Decision", "Approved")])
_rr_self_log = _rr_log([("c1", "alice", None, "Needs Decision"), ("c2", "alice", "Needs Decision", "Approved")])
_rr_agent_log = _rr_log([("c1", "builder", None, "Needs Decision"), ("c2", "veldo-executor", "Needs Decision", "Approved")])
_rr_conflict_log = _rr_log([("c1", "builder", None, "Needs Decision"), ("c2", "alice", "Needs Decision", "Approved"),
                            ("c3", "bob", "Approved", "Rejected")])
_rr_reject_log = _rr_log([("c1", "builder", None, "Needs Decision"), ("c2", "alice", "Needs Decision", "Rejected")])
_rr_pending_log = _rr_log([("c1", "builder", None, "Needs Decision")])


def _rr_run(record, log, store=None, digest_map=None, two_key=None, policy=_RR_POLICY):
    t = TA_RR.FakeTracker(intake_items=[{"id": record["tracker"]["issue"], "title": "decision"}])
    t.seed_changelog(record["tracker"]["issue"], log)
    store = store if store is not None else RR.FakeSettlementStore()
    dmap = digest_map if digest_map is not None else {record["bound_artifact"]["ref"]: record["bound_artifact"]["digest"]}
    res = RR.reconcile_requests([record], t, store, digest_reader=dmap.get, approver_registry=_RR_REG,
                                policy=policy, attestations={record["id"]: _RR_ATTS_C},
                                two_key_material=two_key or {}, config={"agent": "veldo-executor"})
    return res, store, t


# AC1: the read-only read_changelog seam - base raises NotImplementedError; FakeTracker seeds and returns
# an ORDERED, ATTRIBUTED log; it is read-only (a returned copy cannot mutate the source, no write audit).
class _RRBareAdapter(TA_RR.TrackerAdapter):
    def _has_object(self, obj_id):
        return True


_rr_ni = False
try:
    _RRBareAdapter().read_changelog("X")
except NotImplementedError:
    _rr_ni = True
expect("WARP-0619 AC1: read_changelog on the TrackerAdapter base raises NotImplementedError (reference-wired, never gate-run)", _rr_ni)
_rr_ft = TA_RR.FakeTracker(intake_items=[{"id": "VEL-1", "title": "d"}])
_rr_ft.seed_changelog("VEL-1", _rr_valid_log)
_rr_cl = _rr_ft.read_changelog("VEL-1")
expect("WARP-0619 AC1: FakeTracker.read_changelog returns the ORDERED, ATTRIBUTED changelog (id, ts, actor, from, to)",
       [e["id"] for e in _rr_cl] == ["c1", "c2"] and all({"id", "ts", "actor", "from", "to"} <= set(e) for e in _rr_cl)
       and _rr_cl[1]["actor"] == "alice" and _rr_cl[1]["from"] == "Needs Decision" and _rr_cl[1]["to"] == "Approved")
_rr_audit0 = len(_rr_ft.writes())
_rr_cl_copy = _rr_ft.read_changelog("VEL-1")
_rr_cl_copy.append({"id": "x"}); _rr_cl_copy[0]["actor"] = "tamper"
expect("WARP-0619 AC1: read_changelog is READ-ONLY (no write-audit growth; the returned copy cannot mutate the seeded source)",
       len(_rr_ft.writes()) == _rr_audit0 and _rr_ft.read_changelog("VEL-1")[0]["actor"] == "builder"
       and len(_rr_ft.read_changelog("VEL-1")) == 2)
_rr_fl = False
try:
    _rr_ft.read_changelog("NOPE")
except TA_RR.TrackerItemNotFound:
    _rr_fl = True
expect("WARP-0619 AC1: read_changelog on an unknown object fails loud (TrackerItemNotFound), never a silent empty", _rr_fl)

# AC2/AC4 POSITIVE: a valid authorized-approver terminal transition settles ONCE (record + event + receipt),
# the actor and intent are derived FROM THE CHANGELOG (not the current status), and a re-run is idempotent.
_rr_res1, _rr_st1, _rr_tk1 = _rr_run(_rr_req(), _rr_valid_log)
expect("WARP-0619 AC4: a valid authorized-approver terminal transition SETTLES once (record + event + receipt keyed (request_id, changelog_id))",
       _rr_res1["settled"] == ["REQ"] and _rr_st1.count() == 1 and _rr_st1.receipts() == [("REQ", "c2")]
       and [e["type"] for e in _rr_st1.events()] == ["request.accepted"])
_rr_r0 = _rr_res1["results"][0]
expect("WARP-0619 AC2: the TRUE actor and intent are derived FROM THE CHANGELOG (proposer=opening actor, approver=terminal actor, changelog_id=terminal entry), never the current status",
       _rr_r0["proposer"] == "builder" and _rr_r0["actors"] == ["alice"] and _rr_r0["intent"] == "accept" and _rr_r0["changelog_id"] == "c2")
expect("WARP-0619 AC4: the reconcile writes NO tracker state (read-only changelog seam; the write audit is empty)", _rr_tk1.writes() == [])
_rr_before = _rr_st1.digest()
_rr_res1b, _, _ = _rr_run(_rr_req(), _rr_valid_log, store=_rr_st1)
expect("WARP-0619 AC4: a re-run is a byte-identical NO-OP (idempotent per (request_id, changelog_id))",
       _rr_res1b["already_applied"] == ["REQ"] and _rr_st1.digest() == _rr_before and _rr_st1.count() == 1)

# AC2 finding: OPEN requests by the repo index + issue link + status query, NEVER by assignee==agent.
_rr_nl = _rr_req(); _rr_nl.pop("tracker")
_rr_res_nl = RR.reconcile_requests([_rr_nl], TA_RR.FakeTracker(), RR.FakeSettlementStore(),
                                   digest_reader=lambda r: _RR_DIGEST, approver_registry=_RR_REG,
                                   policy=_RR_POLICY, attestations={"REQ": _RR_ATTS_C}, config={"agent": "veldo-executor"})
expect("WARP-0619 AC2: a request with no tracker issue link is SKIPPED (nothing to reconcile), never selected by assignee", "REQ" in _rr_res_nl["skipped"])
_rr_res_t, _rr_st_t, _ = _rr_run(_rr_req(status="accepted"), _rr_valid_log)
expect("WARP-0619 AC2: an already-settled (terminal status) request is SKIPPED - the repo is the source of truth, never re-settled",
       "REQ" in _rr_res_t["skipped"] and _rr_st_t.count() == 0)
_rr_res_p, _rr_st_p, _ = _rr_run(_rr_req(), _rr_pending_log)
expect("WARP-0619 AC2: a request whose changelog has no terminal transition yet is SKIPPED (the human has not decided)",
       "REQ" in _rr_res_p["skipped"] and _rr_st_p.count() == 0)

# AC3 INERT: with NO human_decisions block (the shipped policy.yaml, read via policy=None) the safety core
# authorizes NOTHING, so a valid transition is HELD - the composition is real, not a fixture-only pass.
_rr_ti = TA_RR.FakeTracker(intake_items=[{"id": "VEL-1", "title": "d"}]); _rr_ti.seed_changelog("VEL-1", _rr_valid_log)
_rr_res_inert = RR.reconcile_requests([_rr_req()], _rr_ti, RR.FakeSettlementStore(), digest_reader=lambda r: _RR_DIGEST,
                                      approver_registry=_RR_REG, policy=None, attestations={"REQ": _RR_ATTS_C}, config={"agent": "veldo-executor"})
expect("WARP-0619 AC3: with the shipped INERT policy (no human_decisions block) a valid transition is HELD, never settled (the safety core authorizes nothing)",
       "REQ" in _rr_res_inert["held"])

# AC4: an accepted decision_choice writes a veldo.decision/v1 record and emits request.accepted AND
# decision.decided; the event vocabulary is REUSED from request.py so it cannot drift.
_rr_res_dc, _rr_st_dc, _ = _rr_run(_rr_req(tp="decision_choice"), _rr_valid_log)
expect("WARP-0619 AC4: an accepted decision_choice writes a veldo.decision/v1 settlement record and emits request.accepted + decision.decided",
       "REQ" in _rr_res_dc["settled"] and sorted(e["type"] for e in _rr_st_dc.events()) == ["decision.decided", "request.accepted"]
       and _rr_st_dc.records()[0]["schema"] == "veldo.decision/v1")
expect("WARP-0619 AC4: every emitted event type is in the request event vocabulary (RR.REQUEST_EVENT_TYPES == request.py, cannot drift)",
       RR.REQUEST_EVENT_TYPES == frozenset(RQ_RR.REQUEST_EVENT_TYPES) and all(e["type"] in RR.REQUEST_EVENT_TYPES for e in _rr_st_dc.events()))
_rr_res_rj, _rr_st_rj, _ = _rr_run(_rr_req(), _rr_reject_log)
expect("WARP-0619 AC4: a terminal rejection by a human settles a rejection record + request.rejected event through the receipt",
       _rr_res_rj["settled"] == ["REQ"] and [e["type"] for e in _rr_st_rj.events()] == ["request.rejected"])
_rr_res_ra, _rr_st_ra, _ = _rr_run(_rr_req(), _rr_log([("c1", "builder", None, "Needs Decision"), ("c2", "veldo-executor", "Needs Decision", "Rejected")]))
expect("WARP-0619 AC4: a terminal rejection by the agent/a service account is HELD (a machine actor never settles a human decision)", _rr_st_ra.count() == 0)

# AC5 BLOCK cases (each held, nothing settled) over the seeded changelog offline.
_rr_res_ag, _rr_st_ag, _ = _rr_run(_rr_req(decided_by="alice"), _rr_agent_log)
expect("WARP-0619 AC5: an AGENT-made terminal transition is BLOCKED (the safety core refuses a machine approver)",
       _rr_res_ag["settled"] == [] and "REQ" in _rr_res_ag["held"] and _rr_st_ag.count() == 0)
_rr_res_sa, _rr_st_sa, _ = _rr_run(_rr_req(proposed_by="builder"), _rr_self_log)
expect("WARP-0619 AC5: a SELF-APPROVAL (terminal actor == verified proposer, both from the changelog) is BLOCKED (separation of duties)",
       _rr_res_sa["settled"] == [] and _rr_st_sa.count() == 0)
_rr_res_dg, _rr_st_dg, _ = _rr_run(_rr_req(digest="sha256:forgedforgedfor"), _rr_valid_log, digest_map={"proof/X/approval.json": "sha256:realrealrealreal"})
expect("WARP-0619 AC5: a RECOMPUTED-DIGEST MISMATCH (the repo digest != the displayed digest) is BLOCKED (a forged or stale binding)",
       _rr_res_dg["settled"] == [] and "REQ" in _rr_res_dg["held"] and _rr_st_dg.count() == 0)
_rr_res_2k, _rr_st_2k, _ = _rr_run(_rr_req(impact=["irreversible"]), _rr_valid_log)
expect("WARP-0619 AC5: an IRREVERSIBLE action WITHOUT a satisfied two_key is BLOCKED (the frozen second key, composed through is_authorized)",
       _rr_res_2k["settled"] == [] and _rr_st_2k.count() == 0)
_rr_res_cf, _rr_st_cf, _ = _rr_run(_rr_req(), _rr_conflict_log)
expect("WARP-0619 AC5: a CONFLICTING/AMBIGUOUS changelog (both an accept and a reject terminal transition) is BLOCKED (held, never inferred)",
       _rr_res_cf["settled"] == [] and "REQ" in _rr_res_cf["held"] and _rr_st_cf.count() == 0)
_rr_st_dup = RR.FakeSettlementStore(receipts=[("REQ", "c2")])
_rr_res_dup, _, _ = _rr_run(_rr_req(), _rr_valid_log, store=_rr_st_dup)
expect("WARP-0619 AC5: a DUPLICATE (request_id, changelog_id) is a NO-OP (the append-only compare-and-swap receipt already exists)",
       _rr_res_dup["already_applied"] == ["REQ"] and _rr_st_dup.count() == 0)

# --- WARP-0619 anti-vacuity TEETH: each mutates ONE stable line of .veldo/request_reconcile.py IN MEMORY,
# runs the relevant scenario against the MUTANT (settle count flips), and asserts the on-disk module sha256
# is unchanged. Each targets a guard the reconcile OWNS (the frozen safety core is never mutated).
_rr_src = (ROOT / ".veldo/request_reconcile.py").read_text()
_rr_sha0 = _rr_hashlib.sha256((ROOT / ".veldo/request_reconcile.py").read_bytes()).hexdigest()


def _rr_mut(src):
    g = {"__file__": str(ROOT / ".veldo/request_reconcile.py")}
    exec(compile(src, "<request_reconcile_mut>", "exec"), g)
    return g


def _rr_count(fn, store, record, log, digest_map=None, two_key=None, runs=1):
    t = TA_RR.FakeTracker(intake_items=[{"id": record["tracker"]["issue"], "title": "d"}])
    t.seed_changelog(record["tracker"]["issue"], log)
    dmap = digest_map if digest_map is not None else {record["bound_artifact"]["ref"]: record["bound_artifact"]["digest"]}
    for _ in range(runs):
        fn([record], t, store, digest_reader=dmap.get, approver_registry=_RR_REG, policy=_RR_POLICY,
           attestations={record["id"]: _RR_ATTS_C}, two_key_material=two_key or {}, config={"agent": "veldo-executor"})
    return store.count()


def _rr_sha_unchanged():
    return _rr_hashlib.sha256((ROOT / ".veldo/request_reconcile.py").read_bytes()).hexdigest() == _rr_sha0


# T-agent (case: agent-made): neutralizing the actor-from-changelog derivation lets a self-declared request
# field drive the identity, so an agent-made transition settles; the real path reads the changelog and blocks.
_rr_t1 = _rr_mut(_rr_src.replace('    actors = _entry_actors(term["entries"])', '    actors = [record.get("decided_by")]'))
_rr_rec_ag = _rr_req(decided_by="alice")
expect("WARP-0619 AC5 T-agent: neutralizing actor-from-changelog SETTLES an agent-made transition (real reads the changelog and blocks)",
       _rr_count(_rr_t1["reconcile_requests"], _rr_t1["FakeSettlementStore"](), _rr_rec_ag, _rr_agent_log) == 1
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(), _rr_rec_ag, _rr_agent_log) == 0)
expect("WARP-0619 AC5 T-agent: the mutation is in-memory only (.veldo/request_reconcile.py on disk sha256 unchanged)", _rr_sha_unchanged())

# T-proposer (case: self-approval): neutralizing the proposer-from-changelog derivation lets a self-declared
# field supply a different proposer, so a self-approval slips through; the real path derives it and blocks.
_rr_t2 = _rr_mut(_rr_src.replace('    proposer = _opening_actor(changelog)', '    proposer = record.get("proposed_by")'))
_rr_rec_sa = _rr_req(proposed_by="builder")
expect("WARP-0619 AC5 T-proposer: neutralizing proposer-from-changelog SETTLES a self-approval (real derives the proposer from the changelog and blocks it)",
       _rr_count(_rr_t2["reconcile_requests"], _rr_t2["FakeSettlementStore"](), _rr_rec_sa, _rr_self_log) == 1
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(), _rr_rec_sa, _rr_self_log) == 0)
expect("WARP-0619 AC5 T-proposer: the mutation is in-memory only (.veldo/request_reconcile.py on disk sha256 unchanged)", _rr_sha_unchanged())

# T-digest (case: digest mismatch): neutralizing the repo-digest recompute accepts a forged displayed digest;
# the real path recomputes from the repo and blocks the mismatch.
_rr_t3 = _rr_mut(_rr_src.replace('    if not (_is_str(recomputed) and _is_str(displayed) and recomputed == displayed):',
                                 '    if False and not (_is_str(recomputed) and _is_str(displayed) and recomputed == displayed):'))
_rr_rec_dg = _rr_req(digest="sha256:forgedforgedfor"); _rr_dm = {"proof/X/approval.json": "sha256:realrealrealreal"}
expect("WARP-0619 AC5 T-digest: neutralizing the repo-digest recompute ACCEPTS a forged digest (real recomputes from the repo and blocks)",
       _rr_count(_rr_t3["reconcile_requests"], _rr_t3["FakeSettlementStore"](), _rr_rec_dg, _rr_valid_log, digest_map=_rr_dm) == 1
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(), _rr_rec_dg, _rr_valid_log, digest_map=_rr_dm) == 0)
expect("WARP-0619 AC5 T-digest: the mutation is in-memory only (.veldo/request_reconcile.py on disk sha256 unchanged)", _rr_sha_unchanged())

# T-cas (cases: idempotent re-run + duplicate no-op): neutralizing the compare-and-swap double-applies.
_rr_t4 = _rr_mut(_rr_src.replace('        if self._has_receipt(request_id, changelog_id):',
                                 '        if False and self._has_receipt(request_id, changelog_id):'))
expect("WARP-0619 AC5 T-cas: neutralizing the compare-and-swap DOUBLE-APPLIES on a re-run (real is idempotent, one write)",
       _rr_count(_rr_t4["reconcile_requests"], _rr_t4["FakeSettlementStore"](), _rr_req(), _rr_valid_log, runs=2) == 2
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(), _rr_req(), _rr_valid_log, runs=2) == 1)
expect("WARP-0619 AC5 T-cas: neutralizing the compare-and-swap APPLIES a duplicate (request_id, changelog_id) (real is a no-op)",
       _rr_count(_rr_t4["reconcile_requests"], _rr_t4["FakeSettlementStore"](receipts=[("REQ", "c2")]), _rr_req(), _rr_valid_log) == 1
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(receipts=[("REQ", "c2")]), _rr_req(), _rr_valid_log) == 0)
expect("WARP-0619 AC5 T-cas: the mutation is in-memory only (.veldo/request_reconcile.py on disk sha256 unchanged)", _rr_sha_unchanged())

# T-conflict (case: conflicting changelog): neutralizing the conflict guard settles ambiguous input; the real
# path holds when the changelog carries both an accept and a reject terminal transition.
_rr_t5 = _rr_mut(_rr_src.replace('    if term["outcome"] == "conflict":', '    if False and term["outcome"] == "conflict":'))
expect("WARP-0619 AC5 T-conflict: neutralizing the conflict guard SETTLES an ambiguous changelog (real holds, never inferred)",
       _rr_count(_rr_t5["reconcile_requests"], _rr_t5["FakeSettlementStore"](), _rr_req(), _rr_conflict_log) == 1
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(), _rr_req(), _rr_conflict_log) == 0)
expect("WARP-0619 AC5 T-conflict: the mutation is in-memory only (.veldo/request_reconcile.py on disk sha256 unchanged)", _rr_sha_unchanged())

# T-authorized (case: irreversible without two_key): neutralizing the authorized-only settlement gate settles
# an unauthorized decision; the real path honors is_authorized and blocks the missing second key.
_rr_t6 = _rr_mut(_rr_src.replace('    if not decision.get("authorized"):', '    if False and not decision.get("authorized"):'))
expect("WARP-0619 AC5 T-authorized: neutralizing the authorized-only gate SETTLES an irreversible action with no second key (real honors is_authorized and blocks)",
       _rr_count(_rr_t6["reconcile_requests"], _rr_t6["FakeSettlementStore"](), _rr_req(impact=["irreversible"]), _rr_valid_log) == 1
       and _rr_count(RR.reconcile_requests, RR.FakeSettlementStore(), _rr_req(impact=["irreversible"]), _rr_valid_log) == 0)
expect("WARP-0619 AC5 T-authorized: the mutation is in-memory only (.veldo/request_reconcile.py on disk sha256 unchanged)", _rr_sha_unchanged())

# AC dogfood: WARP-0619 is a STANDALONE tracker-lineage spec (no plan/work), HIGH risk (the safety-critical
# crux; touches no protected path), placement [tracker] with a footprint, behavior_bearing with observability,
# and the module declared in the tracker area of the architecture contract.
_p0619_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0619-request-inbound-reconcile.md").read_text(), re.S).group(1))
expect("WARP-0619 dogfood: PLANNED lane bound to PLAN-0016 W5 (the plan file now exists; the validator enforces this binding bidirectionally, refusing a plan whose spec does not declare it back)",
       _p0619_fm.get("lane") == "planned" and _p0619_fm.get("plan") == "PLAN-0016"
       and _p0619_fm.get("work") == "W5" and str(_p0619_fm.get("plan_revision")) == "1")
expect("WARP-0619 dogfood: HIGH risk (safety-critical) with human_approval not required, and no protected path touched",
       _p0619_fm.get("risk", "").split()[0] == "high" and _p0619_fm.get("human_approval") == "not_required"
       and (_p0619_fm.get("protected_paths") or []) == [])
expect("WARP-0619 dogfood: placement [tracker] with a footprint, behavior_bearing with observability",
       _p0619_fm.get("placement") == ["tracker"] and _p0619_fm.get("footprint")
       and _p0619_fm.get("behavior_bearing") == "true" and isinstance(_p0619_fm.get("observability"), dict))
_p0619_arch, _p0619_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-0619 dogfood: .veldo/request_reconcile.py is declared in the TRACKER area of the architecture contract",
       _p0619_contract is not None and _p0619_arch.area_for_path(".veldo/request_reconcile.py", _p0619_contract) == {"tracker"})
expect("WARP-0619 dogfood: the spec placement resolves and passes the mandatory placement gate; the footprint touches only the tracker area (tier floor not elevated)",
       _p0619_contract is not None and _p0619_arch.placement_gate(_p0619_fm, _p0619_contract) == []
       and _p0619_arch.footprint_tier_floor(_p0619_fm, _p0619_contract) == "")

# AC engine-sync / honesty: the capability entry is byte-identical across all eight capabilities.yaml copies,
# the AC1 seam is on the tracker adapter, the module is REPO-ONLY (a tracker-family sibling), and the frozen
# safety core is UNCHANGED (no reconcile reference added to any frozen reader).
expect("WARP-0619 engine-sync: capabilities.yaml byte-identical root vs engine (the new entry lands in both)",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-0619 engine-sync: capabilities.yaml byte-identical across all 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-0619 AC: the tracker_request_reconcile capability is declared mechanical, repo-only, home .veldo/request_reconcile.py",
       bool(re.search(r"(?m)^\s{2}tracker_request_reconcile:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/request_reconcile\.py,\s*scope:\s*repo-only\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-0619 AC1: the read_changelog seam (base + FakeTracker seed_changelog) is on .veldo/tracker_adapter.py",
       "def read_changelog" in (ROOT / ".veldo/tracker_adapter.py").read_text() and "def seed_changelog" in (ROOT / ".veldo/tracker_adapter.py").read_text())
expect("WARP-0619 AC: request_reconcile.py is REPO-ONLY like the tracker family (not synced to engine or packs)",
       not (ROOT / "engine/.veldo/request_reconcile.py").exists()
       and not (ROOT / "engine/.veldo/request_reconcile.py").exists())
expect("WARP-0619 AC3: the frozen safety core is UNCHANGED (no request_reconcile reference added to authorization/two_key/policy_check/decision)",
       all("request_reconcile" not in (ROOT / (".veldo/" + _f)).read_text()
           for _f in ("authorization.py", "two_key.py", "policy_check.py", "decision.py")))

# --- incident as intent: the compressed loop and reconciliation (WARP-1208, W8 of PLAN-0012): the
# ENDING of an incident, shipped as machinery. A closed incident is not a restored service, it is a SETTLED
# PIECE OF INTENT. This organ runs AFTER the diagnosis and after any remediation already executed: it detects
# a recurring failure SIGNATURE and reports it as a MISSING SPECIFICATION, REFUSES to settle without a
# human-validated diagnosis (five fail-closed conditions, each named), leaves TWO DRAFTS only a human can
# promote (the machine structurally cannot: the runbook draft is unreviewed, so the SHIPPED whitelist physics
# excludes it, and the writer refuses any target inside the whitelist store or the spec corpus), reconciles
# the execution against its RECEIPT rather than the remedy's claim, and is idempotent under replay through an
# append-only compare-and-swap receipt. The ONE IMPURE EDGE is the sibling organ .veldo/reconciliation_store.py
# (the receipt store, the draft writes, the compare-and-swap and the draft PATH GUARD in one home). Proven
# ENTIRELY OFFLINE over seeded records on temporary trees (no live system, NG1) with positive controls, every
# named refusal, and TWELVE in-memory source-mutation TEETH in a full matrix - one per guard, each turning its
# OWN refusing fixture GREEN and no other, plus two sub-mechanism teeth on the path guard's resolution and its
# case folding - while both modules stay byte-unchanged on disk.
import ast as _ir_ast
_irspec = importlib.util.spec_from_file_location("veldo_incident_reconcile", ROOT / ".veldo/incident_reconcile.py")
IR = importlib.util.module_from_spec(_irspec); _irspec.loader.exec_module(IR)
_irstspec = importlib.util.spec_from_file_location("veldo_reconciliation_store", ROOT / ".veldo/reconciliation_store.py")
IRS = importlib.util.module_from_spec(_irstspec); _irstspec.loader.exec_module(IRS)
_irevspec = importlib.util.spec_from_file_location("veldo_events_1208", ROOT / ".veldo/events.py")
EV1208 = importlib.util.module_from_spec(_irevspec); _irevspec.loader.exec_module(EV1208)
_ir_src = (ROOT / ".veldo/incident_reconcile.py").read_text()
_ir_st_src = (ROOT / ".veldo/reconciliation_store.py").read_text()
_IR_FILES = (".veldo/incident_reconcile.py", ".veldo/reconciliation_store.py")
_ir_sha0 = {f: _rr_hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in _IR_FILES}


def _ir_sha_unchanged():
    """BOTH organs on disk, byte-unchanged. Every teeth mutation is compiled in memory, so this holds after
    each one; it covers the sibling store too, since three of the twelve guards live there."""
    return all(_rr_hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == _ir_sha0[f] for f in _IR_FILES)


# The seeded lifecycle: the W1 fixture records (a real veldo.incident/v1 diagnosed incident and a real
# veldo.remedy/v1 proposal, both parsed through the ONE parser), the execution RECEIPT the executor (W6)
# would have written, and the HUMAN diagnosis validation bound to the digest the module recomputes over the
# incident AND its remedy (the remedy is where the diagnosis and its cited evidence actually live).
_IR_INC = V.parse_yamlish(GOOD_INCIDENT)
_IR_REM = V.parse_yamlish(GOOD_REMEDY)
_IR_RECEIPT = {"executed": True, "action": "rollback_deploy", "system": "fake-deploy-controller",
               "parameters": {"service": "payment-confirmation", "to_release": "prior-known-good"},
               "proposal_digest": AE.proposal_digest(_IR_REM)}
_IR_UNSET = object()


def _ir_inc(**over):
    rec = dict(_IR_INC)
    rec.update(over)
    return rec


def _ir_val(incident=None, who="dmitry", digest=None, remedy=_IR_UNSET, bind=True):
    """The HUMAN diagnosis validation for a fixture: it NAMES the remedy it validated (bound_remedy) and BINDS
    the digest this module RECOMPUTES over the incident AND that remedy. bind=False drops the bound_remedy
    field, which is the fixture for the unbound-remedy refusal."""
    inc = incident if incident is not None else _IR_INC
    rem = _IR_REM if remedy is _IR_UNSET else remedy
    val = {"validated_by": who, "validated_at": "2026-07-23T03:00:00Z",
           "bound_digest": IR.diagnosis_digest(inc, rem) if digest is None else digest}
    if bind and isinstance(rem, dict):
        val["bound_remedy"] = rem.get("id")
    return val


def _ir_go(fn=None, store=None, incident=None, **over):
    """Drive ONE reconciliation over the seeded fixture. fn/store accept a MUTANT module's entry point and
    store, so a teeth mutation runs the SAME fixture through the neutralized copy. The default validation is
    bound to whichever remedy the call puts in play, so a fixture that swaps the remedy has to say so."""
    inc = incident if incident is not None else _IR_INC
    rem = over["remedy"] if "remedy" in over else _IR_REM
    kw = {"remedy": _IR_REM, "validation": _ir_val(inc, remedy=rem), "execution_receipt": _IR_RECEIPT}
    kw.update(over)
    st = store if store is not None else IR.FakeReconciliationStore()
    return (fn or IR.reconcile_incident)(inc, st, **kw), st


# AC1 the FAILURE SIGNATURE: deterministic and pure over exactly the identity-of-failure fields.
expect("WARP-1208 AC1: the organ declares schema veldo.reconciliation/v1 and BOTH organs stay under the 1000-line module budget",
       IR.SCHEMA == "veldo.reconciliation/v1" and len(_ir_src.splitlines()) < 1000
       and len(_ir_st_src.splitlines()) < 1000)
expect("WARP-1208 AC1: the ONE IMPURE EDGE is the sibling store organ: the pass RE-EXPORTS it and declares no second store, path guard, or compare-and-swap of its own",
       "class ReconciliationStore" in _ir_st_src and "def forbidden_draft_target" in _ir_st_src
       and "def _same_receipt" in _ir_st_src
       and all(t not in _ir_src for t in ("class ReconciliationStore", "def forbidden_draft_target",
                                          "def _same_receipt", "def put_draft", "def settle"))
       and all(("%s = _ST.%s" % (_n, _n)) in _ir_src for _n in
               ("ReconciliationStore", "FakeReconciliationStore", "FilesystemReconciliationStore",
                "forbidden_draft_target", "UNREADABLE", "ReconcileError")))
_ir_st_loads = sorted(n.args[1].value for n in _ir_ast.walk(_ir_ast.parse(_ir_st_src))
                      if isinstance(n, _ir_ast.Call) and getattr(n.func, "id", "") == "_load"
                      and len(n.args) == 2 and isinstance(n.args[1], _ir_ast.Constant))
expect("WARP-1208 AC1: the store organ is stdlib only, loads ONLY the shipped whitelist store (for its LOCATION) and no enforcement module, and starts no process, thread or timer (NG3)",
       _ir_st_loads == ["action.py"] and not any(t in _ir_st_src for t in _TRIP_DETACH_TOKENS)
       and sorted(re.findall(r"(?m)^import (\w+)", _ir_st_src)) == ["hashlib", "importlib", "json"]
       and "policy_check" not in _ir_st_src)
expect("WARP-1208 AC1: failure_signature is DETERMINISTIC over the same record (a re-hash of a copy matches)",
       IR.failure_signature(_IR_INC) == IR.failure_signature(dict(_IR_INC)) and IR.failure_signature(_IR_INC).startswith("sha256:"))
_ir_ws = _ir_inc(signal="  p99 LATENCY   rose at the deploy   boundary with no error-rate change.  ",
                 affected_behavior="THE ENDPOINT returns within its latency budget after a charge.")
expect("WARP-1208 AC1: the identity fields are whitespace-normalized and case-folded (the same failure differently written shares a signature)",
       IR.failure_signature(_ir_ws) == IR.failure_signature(_IR_INC))
for _irf, _irv in (("affected_behavior", "a different behavior entirely"), ("signal", "a different signal entirely"),
                   ("affected_spec", "WARP-9001"), ("affected_area", "contracts")):
    expect("WARP-1208 AC1: the identity field %s CHANGES the signature" % _irf,
           IR.failure_signature(_ir_inc(**{_irf: _irv})) != IR.failure_signature(_IR_INC))
for _irf, _irv in (("title", "a totally different title"), ("severity", "low"), ("id", "INC-OTHER"),
                   ("timeline", {"opened_at": "2026-01-01T00:00:00Z", "diagnosed_at": "2026-01-02T00:00:00Z"})):
    expect("WARP-1208 AC1: %s does NOT change the signature (it describes the incident, not the failure)" % _irf,
           IR.failure_signature(_ir_inc(**{_irf: _irv})) == IR.failure_signature(_IR_INC))
expect("WARP-1208 AC1: a malformed record (no signal, empty behavior, or not a mapping) has NO computable signature",
       IR.failure_signature(_ir_inc(signal="")) is None and IR.failure_signature({"affected_behavior": "x"}) is None
       and IR.failure_signature("not a record") is None
       and IR.failure_signature(_ir_inc(affected_spec="")) is None)
_ir_sig_code = ("import importlib.util,json,sys\n"
                "s=importlib.util.spec_from_file_location('ir', sys.argv[1])\n"
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                "print(m.failure_signature(json.loads(sys.argv[2])))\n")
_ir_sig_out = []
for _seed in ("0", "12345"):
    _ir_env = dict(os.environ, PYTHONHASHSEED=_seed)
    _ir_sig_out.append(subprocess.run([sys.executable, "-c", _ir_sig_code, str(ROOT / ".veldo/incident_reconcile.py"),
                                       json.dumps(_IR_INC)], capture_output=True, text=True,
                                      env=_ir_env).stdout.strip())
expect("WARP-1208 AC1: the signature is identical ACROSS PROCESSES under two different PYTHONHASHSEEDs (sha256 over canonical JSON, never Python's salted hash)",
       _ir_sig_out == [IR.failure_signature(_IR_INC), IR.failure_signature(_IR_INC)])

# AC1 RECURRENCE: the ordered prior ids sharing the signature, self-excluded, malformed skipped.
_IR_PRIOR = _ir_inc(id="INC-EARLIER", title="an earlier record of the same failure", severity="standard",
                    status="closed")
_IR_PRIOR2 = _ir_inc(id="INC-EARLIEST", title="the first time it happened")
_IR_OTHER = _ir_inc(id="INC-UNRELATED", signal="disk filled on the log volume",
                    affected_behavior="the queue drains within its budget")
expect("WARP-1208 AC1: a second seeded incident with the SAME identity fields is detected against the first (recurrence is REPORTED)",
       IR.recurrence(_IR_INC, [_IR_PRIOR]) == ["INC-EARLIER"])
expect("WARP-1208 AC1: the recurrence set is ORDERED as recorded and de-duplicated",
       IR.recurrence(_IR_INC, [_IR_PRIOR2, _IR_PRIOR, _IR_PRIOR2]) == ["INC-EARLIEST", "INC-EARLIER"])
expect("WARP-1208 AC1: the incident EXCLUDES ITSELF from its own recurrence",
       IR.recurrence(_IR_INC, [_IR_INC, dict(_IR_INC)]) == [])
expect("WARP-1208 AC1: a MALFORMED prior record is SKIPPED, never silently matched",
       IR.recurrence(_IR_INC, [_ir_inc(id="INC-BAD", signal=""), "not a record", {"id": "INC-EMPTY"}, _IR_PRIOR])
       == ["INC-EARLIER"])
expect("WARP-1208 AC1: an unrelated failure is NOT a recurrence (control, so the detection is non-vacuous)",
       IR.recurrence(_IR_INC, [_IR_OTHER]) == [])
expect("WARP-1208 AC1: a recurrence is named a MISSING SPECIFICATION and a first occurrence is not",
       IR.missing_specification(["INC-EARLIER"]) is True and IR.missing_specification([]) is False)
_ir_rec_res, _ir_rec_st = _ir_go(prior_incidents=[_IR_PRIOR])
expect("WARP-1208 AC1: a settled reconciliation of a RECURRING failure records recurrence_of and missing_specification true",
       _ir_rec_res["recurrence_of"] == ["INC-EARLIER"] and _ir_rec_res["missing_specification"] is True
       and _ir_rec_st.records()[0]["missing_specification"] is True)

# AC2/AC5 POSITIVE CONTROL: a diagnosed incident with a valid non-machine validation whose bound digest
# matches, and no open debt, SETTLES cleanly and writes both drafts.
_ir_ok, _ir_ok_st = _ir_go()
expect("WARP-1208 AC2 CONTROL: a diagnosed incident with a valid human validation and a matching digest SETTLES (the pass does not over-fire)",
       _ir_ok["outcome"] == IR.OUTCOME_SETTLED and _ir_ok["refused"] is None and _ir_ok_st.count() == 1)
expect("WARP-1208 AC5 CONTROL: the settlement writes BOTH drafts and reports a first occurrence honestly (recurrence_of empty, missing_specification false)",
       sorted(d["kind"] for d in _ir_ok["drafts"]) == [IR.DRAFT_CRITERIA, IR.DRAFT_RUNBOOK]
       and _ir_ok["recurrence_of"] == [] and _ir_ok["missing_specification"] is False)
expect("WARP-1208 AC2: the settlement appends exactly ONE incident.closed event, its type SELECTED from the contract's vocabulary",
       [e["type"] for e in _ir_ok_st.events()] == [IR.INCIDENT_CLOSED] and IR.INCIDENT_CLOSED == "incident.closed")

# AC2 the FIVE fail-closed conditions, each REFUSED BY NAME over seeded fixtures.
_ir_open, _ir_open_st = _ir_go(incident=_ir_inc(status="open"))
expect("WARP-1208 AC2(a): an OPEN incident REFUSES by name (incident_not_diagnosed) and nothing is written",
       _ir_open["refused"] == IR.REFUSE_NOT_DIAGNOSED and _ir_open_st.count() == 0)
_ir_nov, _ir_nov_st = _ir_go(validation=None)
expect("WARP-1208 AC2(b): NO human diagnosis validation REFUSES by name (missing_diagnosis_validation), never a default allow",
       _ir_nov["refused"] == IR.REFUSE_MISSING_VALIDATION and _ir_nov_st.count() == 0)
expect("WARP-1208 AC2(b): a validation that is not a mapping, or names no validator, refuses the same way",
       _ir_go(validation="dmitry said so")[0]["refused"] == IR.REFUSE_MISSING_VALIDATION
       and _ir_go(validation={"bound_digest": IR.diagnosis_digest(_IR_INC)})[0]["refused"] == IR.REFUSE_MISSING_VALIDATION)
for _irm in ("veldo-responder", "veldo-executor", "agent", "Service_Account"):
    expect("WARP-1208 AC2(c): a MACHINE actor (%s) validating the diagnosis REFUSES by name (NG4, no self-authorization)" % _irm,
           _ir_go(validation=_ir_val(who=_irm))[0]["refused"] == IR.REFUSE_MACHINE_VALIDATOR)
expect("WARP-1208 AC2(c): the machine-actor set is REUSED from the shipped authorization.py (no second copy of the list)",
       IR.MACHINE_ACTORS == frozenset(AUTHZ.MACHINE_ACTORS) and "MACHINE_ACTORS = frozenset(_AUTHZ.MACHINE_ACTORS)" in _ir_src)
_ir_dg, _ir_dg_st = _ir_go(validation=_ir_val(digest="sha256:forgedforgedfor"))
expect("WARP-1208 AC2(d): a validation whose bound digest is not the RECOMPUTED one REFUSES by name (diagnosis_digest_mismatch)",
       _ir_dg["refused"] == IR.REFUSE_VALIDATION_DIGEST_MISMATCH and _ir_dg_st.count() == 0)
expect("WARP-1208 AC2(d): the recomputed digest is over the RECORD's diagnosis material, so a validation bound to a STALE record's digest refuses",
       _ir_go(validation=_ir_val(digest=IR.diagnosis_digest(_ir_inc(signal="a different signal"))))[0]["refused"]
       == IR.REFUSE_VALIDATION_DIGEST_MISMATCH
       and IR.diagnosis_digest(_ir_inc(title="only the title changed")) == IR.diagnosis_digest(_IR_INC))

# AC2 THE BOUND DIGEST BINDS THE DIAGNOSIS A HUMAN ACTUALLY VALIDATED (the WARP-1208 review's F2). veldo.incident/v1
# carries NO diagnosis field: the diagnosis and its cited evidence live on veldo.remedy/v1, so the recomputed material
# binds the remedy's identity and its CANONICAL proposal digest (action_executor.proposal_digest, the same digest the
# executor's confirmation and the two-key rule bind) whenever a remedy exists. Changing the proposed action, the
# diagnosis, or the cited evidence therefore INVALIDATES the validation, and a validation naming no remedy REFUSES.
expect("WARP-1208 AC2(d): the recomputed material BINDS the remedy: its id and its canonical proposal digest are in it, and the digest reuses the SHIPPED action_executor.proposal_digest",
       IR.diagnosis_material(_IR_INC, _IR_REM)["remedy"] == _IR_REM["id"]
       and IR.diagnosis_material(_IR_INC, _IR_REM)["remedy_proposal_digest"] == AE.proposal_digest(_IR_REM)
       and "remedy" not in IR.diagnosis_material(_IR_INC)
       and IR.diagnosis_digest(_IR_INC, _IR_REM) != IR.diagnosis_digest(_IR_INC))
for _irf, _irv in (("diagnosis", "an entirely different diagnosis of the same failure"),
                   ("evidence", [{"citation": "a different artifact entirely"}]),
                   ("proposed_action", {"action": "drop_customer_table", "parameters": {"table": "customers"}}),
                   ("rollback", "a different rollback plan"), ("risk_class", "critical"),
                   ("autonomy_level", "L3"), ("required_authorization", "two_key")):
    expect("WARP-1208 AC2(d): changing the remedy's %s CHANGES the recomputed digest, so a validation taken before that change no longer binds" % _irf,
           IR.diagnosis_digest(_IR_INC, dict(_IR_REM, **{_irf: _irv})) != IR.diagnosis_digest(_IR_INC, _IR_REM))
# THE REVIEWER'S EXACT ATTACK: the validation untouched, the whole remedy swapped (the proposed rollback_deploy
# replaced by drop_customer_table). It settled before this hardening and rendered the runbook draft for the
# destructive action; it now REFUSES by name and writes no runbook draft at all.
_IR_SWAPPED = dict(_IR_REM, proposed_action={"action": "drop_customer_table", "parameters": {"table": "customers"}},
                   diagnosis="a different diagnosis nobody validated",
                   reversibility={"class": "irreversible", "data_mutating": "true",
                                  "analysis": "dropping a table destroys data and cannot be undone"},
                   required_authorization="two_key")
_ir_swap, _ir_swap_st = _ir_go(remedy=_IR_SWAPPED, validation=_ir_val(), execution_receipt=None)
expect("WARP-1208 AC2(d) F2 ATTACK: the SAME validation with the ENTIRE REMEDY SWAPPED (rollback_deploy replaced by drop_customer_table) REFUSES by name, writes NO draft at all, and settles nothing",
       _ir_swap["refused"] == IR.REFUSE_VALIDATION_DIGEST_MISMATCH and _ir_swap_st.count() == 0
       and _ir_swap_st.drafts() == {} and _ir_swap["drafts"] == []
       and "drop_customer_table" not in json.dumps(_ir_swap_st.drafts()))
expect("WARP-1208 AC2(d) F2 ATTACK: the swapped remedy is itself CONTRACT-VALID (validate_remedy reports zero problems), so the refusal comes from the binding and not from a malformed record",
       INC.validate_remedy(dict(_IR_SWAPPED), str(ROOT), "selftest.swapped-remedy", V.fail) == 0)
_ir_unbound, _ir_unbound_st = _ir_go(validation=_ir_val(bind=False))
expect("WARP-1208 AC2(d): a validation that BINDS NO REMEDY while a remedy exists REFUSES by name (validation_binds_no_remedy), never settles on a diagnosis nobody named",
       _ir_unbound["refused"] == IR.REFUSE_VALIDATION_UNBOUND_REMEDY and _ir_unbound_st.count() == 0)
expect("WARP-1208 AC2(d): a validation naming a DIFFERENT remedy id refuses the same way, and with NO remedy in play the binding stands down (an incident with no remedy still settles)",
       _ir_go(validation=dict(_ir_val(), bound_remedy="REM-SOMETHING-ELSE"))[0]["refused"]
       == IR.REFUSE_VALIDATION_UNBOUND_REMEDY
       and IR.validation_binds_remedy(None, {}) is True
       and _ir_go(remedy=None, execution_receipt=None)[0]["outcome"] == IR.OUTCOME_SETTLED)
expect("WARP-1208 AC2(d): the RECEIPT records what the human bound (bound_remedy) and spells out WHAT the digest covers, so a stranger reads the binding rather than inferring it",
       _ir_go()[1].records()[0]["diagnosis_validation"]["bound_remedy"] == _IR_REM["id"]
       and AE.proposal_digest(_IR_REM) in _ir_go()[1].records()[0]["diagnosis_validation"]["binds"]
       and "cited evidence" in _ir_go()[1].records()[0]["diagnosis_validation"]["binds"]
       and "no remedy" in _ir_go(remedy=None, execution_receipt=None)[1].records()[0]["diagnosis_validation"]["binds"])
_ir_debt, _ir_debt_st = _ir_go(debt_reader=lambda inc: "WARP-1208 backfill still open")
expect("WARP-1208 AC2(e): an OPEN emergency backfill debt REFUSES by name (the fix flows the emergency lane first)",
       _ir_debt["refused"] == IR.REFUSE_OPEN_EMERGENCY_DEBT and _ir_debt_st.count() == 0)
expect("WARP-1208 AC2(e): a debt reader that reports NO debt settles, and a reader that RAISES fails closed (an unreadable surface never assumes there is no debt)",
       _ir_go(debt_reader=lambda inc: None)[0]["outcome"] == IR.OUTCOME_SETTLED
       and _ir_go(debt_reader=lambda inc: (_ for _ in ()).throw(RuntimeError("no debt surface")))[0]["refused"]
       == IR.REFUSE_OPEN_EMERGENCY_DEBT)
expect("WARP-1208 AC2(e): with NO debt_reader the condition STANDS DOWN honestly (adoption safe: no debt surface is declared here)",
       _ir_ok["outcome"] == IR.OUTCOME_SETTLED and "debt_reader=None" in _ir_src)
_ir_loads = sorted(n.args[1].value for n in _ir_ast.walk(_ir_ast.parse(_ir_src))
                   if isinstance(n, _ir_ast.Call) and getattr(n.func, "id", "") == "_load"
                   and len(n.args) == 2 and isinstance(n.args[1], _ir_ast.Constant))
expect("WARP-1208 AC2: the organ loads ONLY shipped owners by path - the five contract owners, the ONE parser, and its own store sibling - and NO enforcement module (policy_check.py absent: a contracts organ never depends on enforcement)",
       _ir_loads == ["action.py", "action_executor.py", "authorization.py", "events.py", "incident.py",
                     "reconciliation_store.py", "validate.py"])
_ir_pc_lines = [ln.strip() for ln in (_ir_src + _ir_st_src).splitlines() if "policy_check" in ln]
expect("WARP-1208 AC2: the ENFORCEMENT AREA appears in BOTH organs only as PROSE explaining why it is not depended on - never an import, never a _load",
       _ir_pc_lines and all(not any(t in ln for t in ("import ", "_load(")) for ln in _ir_pc_lines))
expect("WARP-1208 AC2: the organ imports no third-party module (stdlib only) and starts NO process, thread, or timer (NG3)",
       not any(t in _ir_src for t in _TRIP_DETACH_TOKENS)
       and sorted(re.findall(r"(?m)^import (\w+)", _ir_src)) == ["argparse", "hashlib", "importlib", "json", "sys"])

# AC3 THE TWO DRAFTS, over a real temporary tree (the filesystem store), and the SHIPPED whitelist physics.
with tempfile.TemporaryDirectory() as _ird:
    _ir_fs = IR.FilesystemReconciliationStore(_ird)
    _ir_fres, _ = _ir_go(store=_ir_fs)
    _ir_paths = {d["kind"]: Path(_ir_fs.drafts_dir) / d["path"] for d in _ir_fres["drafts"]}
    expect("WARP-1208 AC3: a settled reconciliation WRITES both drafts into the declared drafts directory",
           _ir_fres["outcome"] == IR.OUTCOME_SETTLED and all(p.is_file() for p in _ir_paths.values())
           and all(d["outcome"] == "created" for d in _ir_fres["drafts"]))
    _ir_bytes0 = {k: p.read_bytes() for k, p in _ir_paths.items()}
    _ir_fres2, _ = _ir_go(store=_ir_fs)
    expect("WARP-1208 AC3: a second pass RE-RENDERS both drafts BYTE-IDENTICALLY (pure renderers, no clock) and never overwrites",
           all(_ir_paths[k].read_bytes() == v for k, v in _ir_bytes0.items())
           and all(d["outcome"] == "exists" for d in _ir_fres2["drafts"])
           and [d["digest"] for d in _ir_fres2["drafts"]] == [d["digest"] for d in _ir_fres["drafts"]])
    _ir_rb = V.parse_yamlish(_ir_paths[IR.DRAFT_RUNBOOK].read_text())
    expect("WARP-1208 AC3: the RUNBOOK draft is STRUCTURALLY VALID against the shipped veldo.action/v1 contract (action.validate_action reports zero problems)",
           _ir_rb.get("schema") == ACT.SCHEMA_ACTION
           and ACT.validate_action(_ir_rb, _ird, "selftest.runbook-draft", V.fail) == 0)
    expect("WARP-1208 AC3: the runbook draft carries review status proposed, so the SHIPPED physics says it is NOT reviewed",
           _ir_rb["review"]["status"] == IR.DRAFT_REVIEW_STATUS and _ir_rb["review"]["status"] in ACT.REVIEW_STATUSES
           and ACT.action_reviewed(_ir_rb) is False and "verdict" not in _ir_rb["review"])
    _ir_wl, _ir_wle = ACT.build_whitelist(_ir_paths[IR.DRAFT_RUNBOOK].parent, V.parse_yamlish, V.fail)
    expect("WARP-1208 AC3: build_whitelist over the draft's OWN directory does NOT contain it and reports no error (a valid but unreviewed draft does not exist to the machine execution path, NG2)",
           _ir_wl == {} and _ir_wle == 0)
    _ir_cd = V.parse_yamlish(_ir_paths[IR.DRAFT_CRITERIA].read_text())
    expect("WARP-1208 AC3: the REGRESSION CRITERIA draft is rendered from the failure mode and carries the incident id, the failure signature, and the recurrence set",
           _ir_cd["status"] == "draft" and _ir_cd["incident"] == _IR_INC["id"]
           and _ir_cd["failure_signature"] == IR.failure_signature(_IR_INC) and _ir_cd["recurrence_of"] == []
           and _IR_INC["affected_behavior"] in _ir_cd["acceptance_criterion"]
           and _IR_INC["signal"] in _ir_cd["regression_criterion"]
           and "decider" not in _ir_cd and "promoted" not in _ir_cd and "review" not in _ir_cd)
    # the PATH GUARD: a target inside the action whitelist store or inside the spec corpus refuses BY NAME.
    _ir_store_dir = ACT.default_actions_dir(_ird)
    _ir_pg1, _ir_pg1_st = _ir_go(store=IR.FakeReconciliationStore(drafts_dir=_ir_store_dir))
    _ir_pg2, _ir_pg2_st = _ir_go(store=IR.FakeReconciliationStore(drafts_dir=Path(_ird) / "specs" / "drafts"))
    expect("WARP-1208 AC3: a draft target inside the ACTION WHITELIST STORE is REFUSED by name (forbidden_draft_path) and nothing is written",
           _ir_pg1["refused"] == IR.REFUSE_DRAFT_PATH_FORBIDDEN and _ir_pg1_st.count() == 0
           and _ir_pg1_st.drafts() == {})
    expect("WARP-1208 AC3: a draft target inside the SPEC CORPUS is REFUSED by name (the machine never authors a spec into the corpus)",
           _ir_pg2["refused"] == IR.REFUSE_DRAFT_PATH_FORBIDDEN and _ir_pg2_st.count() == 0)
    expect("WARP-1208 AC3: the ACTION WHITELIST STORE root is read from the SHIPPED store location (the spec corpus root is an honest literal, no engine module owns it), and an ordinary drafts directory is allowed (control)",
           IR.forbidden_draft_target(_ir_store_dir / "x.yaml") == ".veldo/actions/"
           and IR.forbidden_draft_target(Path("specs") / "WARP-9999.md") == "specs/"
           and IR.forbidden_draft_target(Path(_ird) / ".veldo" / "incident_drafts" / "criteria" / "x.yaml") is None
           and IRS._STORE_SEGMENTS == tuple(ACT.default_actions_dir("").parts)
           and '_STORE_SEGMENTS = tuple(_ACT.default_actions_dir("").parts)' in _ir_st_src
           and "no engine module owns the corpus root" in _ir_st_src)
    # THE PATH GUARD IS DECIDED ON THE RESOLVED PATH (the WARP-1208 review's F1). A '..' traversal, a drafts
    # directory that IS a symlink into the whitelist store, an absolute target, and a case variant on the
    # case-INSENSITIVE filesystems this engine ships to all landed INSIDE the store before this hardening.
    _ir_trav = Path(_ird) / ".veldo" / "incident_drafts" / ".." / "actions"
    (Path(_ird) / ".veldo" / "actions").mkdir(parents=True, exist_ok=True)
    _ir_link = Path(_ird) / "drafts-symlink"
    if not _ir_link.exists():
        os.symlink(Path(_ird) / ".veldo" / "actions", _ir_link)
    _ir_loop = Path(_ird) / "loop-a"
    if not _ir_loop.is_symlink():
        os.symlink(Path(_ird) / "loop-b", _ir_loop)
        os.symlink(Path(_ird) / "loop-a", Path(_ird) / "loop-b")
    for _irlabel, _irdir in (("a '..' TRAVERSAL out of the drafts directory", _ir_trav),
                             ("a drafts directory that is a SYMLINK into the store", _ir_link),
                             ("a CASE VARIANT of the store path", Path(_ird) / ".VELDO" / "Actions"),
                             ("a CASE VARIANT of the spec corpus", Path(_ird) / "Specs" / "drafts"),
                             ("a target that cannot be RESOLVED at all (a symlink loop)", _ir_loop / "drafts")):
        _ir_pgx, _ir_pgx_st = _ir_go(store=IR.FakeReconciliationStore(drafts_dir=_irdir))
        expect("WARP-1208 AC3 F1: %s is REFUSED by name (the guard decides on the RESOLVED, case-folded path) and nothing is written" % _irlabel,
               _ir_pgx["refused"] == IR.REFUSE_DRAFT_PATH_FORBIDDEN and _ir_pgx_st.count() == 0
               and _ir_pgx_st.drafts() == {})
    expect("WARP-1208 AC3 F1: the guard NAMES the real forbidden root behind each disguise, and an unresolvable target is named as such (fail closed)",
           IR.forbidden_draft_target(_ir_trav / "x.yaml") == ".veldo/actions/"
           and IR.forbidden_draft_target(_ir_link / "x.yaml") == ".veldo/actions/"
           and IR.forbidden_draft_target(Path(_ird) / ".VELDO" / "Actions" / "x.yaml") == ".veldo/actions/"
           and IR.forbidden_draft_target(Path("Specs") / "x.md") == "specs/"
           and IR.forbidden_draft_target(_ir_loop / "x.yaml") == IRS.UNRESOLVABLE_TARGET)
for _irr in ({"status": "reviewed"}, {"status": "proposed", "verdict": "approved"},
             {"status": "proposed", "reviewer": "dmitry"}, {"status": "retired"}):
    _ir_rv, _ir_rv_st = _ir_go(draft_review=_irr)
    expect("WARP-1208 AC3: a draft asked to carry the review block %r is REFUSED by name (a machine-recorded review is the rubber stamp the method forbids)" % (_irr,),
           _ir_rv["refused"] == IR.REFUSE_DRAFT_REVIEWED and _ir_rv_st.count() == 0)
expect("WARP-1208 AC3: the renderer returns a draft for review status proposed and NOTHING for any other review block (control)",
       IR.render_runbook_draft(_IR_INC, _IR_REM, "sha256:x", [], review={"status": "proposed"}) is not None
       and IR.render_runbook_draft(_IR_INC, _IR_REM, "sha256:x", [], review={"status": "reviewed"}) is None)

# AC3 STRUCTURAL VALIDITY IS ENFORCED, NOT EXHIBITED (the WARP-1208 review's F4). A CONTRACT-VALID remedy whose
# proposed_action.parameters carries an empty or whitespace-only key renders a draft the SHIPPED validator refuses
# ("parameter 0 has no name"); the write path now validates the RENDERED draft through that same shipped validator
# and REFUSES by name, so an unpromotable artifact is never written and never recorded as a regression criterion.
for _irlabel, _irkey in (("an EMPTY parameter key", ""), ("a WHITESPACE-ONLY parameter key", "   "),
                         ("a NEWLINE-ONLY parameter key", "\n")):
    _ir_badrem = dict(_IR_REM, proposed_action={"action": "rollback_deploy",
                                                "parameters": {_irkey: "x", "service": "payment-confirmation"}})
    _ir_bad, _ir_bad_st = _ir_go(remedy=_ir_badrem, execution_receipt=None)
    expect("WARP-1208 AC3 F4: a contract-valid remedy with %s renders a draft the SHIPPED validator refuses, so the write path REFUSES by name (structurally_invalid_draft) and writes no runbook draft" % _irlabel,
           _ir_bad["refused"] == IR.REFUSE_DRAFT_INVALID and _ir_bad_st.count() == 0
           and list(_ir_bad_st.drafts()) == [IR.criteria_draft_path(_IR_INC)]
           and INC.validate_remedy(dict(_ir_badrem), str(ROOT), "selftest.empty-key-remedy", V.fail) == 0)
expect("WARP-1208 AC3 F4: the guard runs the RENDERED text through the ONE parser and the SHIPPED action.validate_action (nothing reimplemented), and reports the contract's own message",
       "parameter 0 has no name" in " ".join(IR.draft_action_problems(
           IR.render_runbook_draft(_IR_INC, dict(_IR_REM, proposed_action={"action": "a", "parameters": {"": 1}}),
                                   "sha256:x", [])))
       and IR.draft_action_problems(IR.render_runbook_draft(_IR_INC, _IR_REM, "sha256:x", [])) == []
       and IR.draft_action_problems("this is not a record: [") != []
       and "_ACT.validate_action(parsed" in _ir_src and "_V.parse_yamlish(text)" in _ir_src)
expect("WARP-1208 AC3 F4: the ONE parser is LOADED by path (validate.py, the parser's owner) rather than reimplemented, and the store organ needs no parser at all",
       '_V = _load("veldo_validate_for_incident_reconcile", "validate.py")' in _ir_src
       and "parse_yamlish" not in _ir_st_src and "def parse_yamlish" not in _ir_src)

# AC4 THE HONEST RECEIPT: what was done comes from the RECEIPT, never from the remedy's own claim.
_ir_rcpt = _ir_ok_st.records()[0]
expect("WARP-1208 AC4: the receipt is veldo.reconciliation/v1 with a content-addressed REC- id and the settlement identity",
       _ir_rcpt["schema"] == IR.SCHEMA and _ir_rcpt["id"] == _ir_ok["receipt_id"]
       and _ir_rcpt["id"].startswith("REC-") and _ir_rcpt["incident"] == _IR_INC["id"]
       and _ir_rcpt["remedy"] == _IR_REM["id"] and _ir_rcpt["failure_signature"] == IR.failure_signature(_IR_INC))
expect("WARP-1208 AC4: WHAT WAS DONE takes the executed action and parameters from the EXECUTION RECEIPT",
       _ir_rcpt["what_was_done"]["action"] == "rollback_deploy"
       and _ir_rcpt["what_was_done"]["parameters"] == _IR_RECEIPT["parameters"]
       and _ir_rcpt["what_was_done"]["system"] == "fake-deploy-controller")
_ir_exec_diff = dict(_IR_RECEIPT, parameters={"service": "as-actually-executed", "to_release": "r-99"})
expect("WARP-1208 AC4: when the receipt's parameters DIFFER from the remedy's proposal, the receipt's are recorded (never the remedy's claim)",
       _ir_go(execution_receipt=_ir_exec_diff)[1].records()[0]["what_was_done"]["parameters"]
       == {"service": "as-actually-executed", "to_release": "r-99"}
       != _IR_REM["proposed_action"]["parameters"])
_ir_noparams = {k: v for k, v in _IR_RECEIPT.items() if k != "parameters"}
_ir_np_rec = _ir_go(execution_receipt=_ir_noparams)[1].records()[0]["what_was_done"]
expect("WARP-1208 AC4: a receipt that recorded NO parameters yields the honest value none, never the remedy's parameters",
       _ir_np_rec["parameters"] == IR.NONE_VALUE and "never substituted" in _ir_np_rec["detail"])
expect("WARP-1208 AC4: WHAT IT PROVED carries the receipt's RECORDED outcome and its proposal digest, RECOMPUTED through the shipped executor digest (reused by path, never reimplemented)",
       _ir_rcpt["what_it_proved"]["outcome"] == "executed"
       and _ir_rcpt["what_it_proved"]["proposal_digest"] == AE.proposal_digest(_IR_REM)
       and _ir_rcpt["what_it_proved"]["recomputed_proposal_digest"] == AE.proposal_digest(_IR_REM)
       and IR.proposal_digest(_IR_REM) == AE.proposal_digest(_IR_REM)
       and "proposal_digest = _AE.proposal_digest" in _ir_src and "def proposal_digest" not in _ir_src)
expect("WARP-1208 AC4: a receipt recording a REFUSAL is reconciled as refused with the reason named, never as executed",
       IR.what_it_proved(_IR_REM, dict(_IR_RECEIPT, executed=False, refused="kill_switch_tripped"))["outcome"] == "refused"
       and IR.what_it_proved(_IR_REM, dict(_IR_RECEIPT, executed=False))["outcome"] == "unrecorded")
expect("WARP-1208 AC4: WHAT REGRESSION CRITERIA IT LEAVES records the paths and digests of the two drafts",
       [d["kind"] for d in _ir_rcpt["what_regression_criteria_it_leaves"]] == [IR.DRAFT_CRITERIA, IR.DRAFT_RUNBOOK]
       and all(d["digest"].startswith("sha256:") for d in _ir_rcpt["what_regression_criteria_it_leaves"])
       and all("outcome" not in d for d in _ir_rcpt["what_regression_criteria_it_leaves"]))
# the NONE-execution path: an incident with no remedy at all settles with an honest none block.
_ir_none, _ir_none_st = _ir_go(remedy=None, execution_receipt=None)
_ir_none_rec = _ir_none_st.records()[0]
expect("WARP-1208 AC4/AC5 CONTROL: an incident with NO remedy at all SETTLES with an honest none execution block rather than refusing",
       _ir_none["outcome"] == IR.OUTCOME_SETTLED and _ir_none_rec["remedy"] == IR.NONE_VALUE
       and _ir_none_rec["what_was_done"]["action"] == IR.NONE_VALUE
       and _ir_none_rec["what_it_proved"]["outcome"] == IR.NONE_VALUE
       and _ir_none_rec["what_it_proved"]["proposal_digest"] == IR.NONE_VALUE)
expect("WARP-1208 AC4: with no remedy the runbook draft is honestly recorded as none (never an invented draft) and only the criteria draft is written",
       [d["path"] for d in _ir_none_rec["what_regression_criteria_it_leaves"]][1] == IR.NONE_VALUE
       and len(_ir_none_st.drafts()) == 1)
# the EXECUTION CLAIM is refused without its receipt (both paths, one named refusal).
_ir_claim, _ir_claim_st = _ir_go(execution_receipt=None, execution_claim=True)
expect("WARP-1208 AC4: an execution asked to be recorded with NO receipt REFUSES by name (unsupported_execution_claim)",
       _ir_claim["refused"] == IR.REFUSE_UNSUPPORTED_EXECUTION_CLAIM and _ir_claim_st.count() == 0)
_ir_fake_dg, _ir_fake_dg_st = _ir_go(execution_receipt=dict(_IR_RECEIPT, proposal_digest="sha256:notthedigest"))
expect("WARP-1208 AC4: a receipt whose proposal digest does not match the RECOMPUTED one REFUSES by name (never claim a check passed)",
       _ir_fake_dg["refused"] == IR.REFUSE_UNSUPPORTED_EXECUTION_CLAIM and _ir_fake_dg_st.count() == 0)
expect("WARP-1208 AC4: a receipt supplied for an EDITED remedy (the digest no longer matches) also refuses, and the honest none path does not",
       _ir_go(remedy=dict(_IR_REM, diagnosis="edited after the confirmation"))[0]["refused"]
       == IR.REFUSE_UNSUPPORTED_EXECUTION_CLAIM
       and IR.execution_claim_refusal(_IR_REM, None, None) is None)
# REPLAY: no second record, no second event, the SAME receipt id; and a CONFLICT refuses.
_ir_rp_st = IR.FakeReconciliationStore()
_ir_rp1, _ = _ir_go(store=_ir_rp_st)
_ir_rp_before = _ir_rp_st.digest()
_ir_rp2, _ = _ir_go(store=_ir_rp_st)
expect("WARP-1208 AC4: a full REPLAY of the same settlement is a byte-identical NO-OP (zero new records, zero new events, the SAME receipt id)",
       _ir_rp2["outcome"] == IR.OUTCOME_ALREADY and _ir_rp2["receipt_id"] == _ir_rp1["receipt_id"]
       and _ir_rp_st.count() == 1 and len(_ir_rp_st.events()) == 1 and _ir_rp_st.digest() == _ir_rp_before)
_ir_closed_res, _ = _ir_go(store=_ir_rp_st, incident=_ir_inc(status="closed"))
expect("WARP-1208 AC4: an ALREADY-CLOSED incident takes the idempotent replay path and returns the EXISTING receipt, never a second settlement",
       _ir_closed_res["outcome"] == IR.OUTCOME_ALREADY and _ir_rp_st.count() == 1
       and _ir_closed_res["receipt"]["id"] == _ir_rp1["receipt_id"])
expect("WARP-1208 AC4: a CLOSED incident with NO recorded reconciliation is not settled a second time (the status gate refuses)",
       _ir_go(incident=_ir_inc(status="closed"))[0]["refused"] == IR.REFUSE_NOT_DIAGNOSED)
_ir_cf_st = IR.FakeReconciliationStore(receipts={_ir_ok["receipt_id"]: dict(_ir_rcpt, incident="INC-TAMPERED")})
_ir_cf, _ = _ir_go(store=_ir_cf_st)
expect("WARP-1208 AC4: a CONFLICTING write under an existing receipt id REFUSES by name and does NOT overwrite recorded history",
       _ir_cf["refused"] == IR.REFUSE_RECEIPT_CONFLICT and _ir_cf_st.count() == 0
       and _ir_cf_st.get(_ir_ok["receipt_id"])["incident"] == "INC-TAMPERED")
# AC4 AN EXISTING-BUT-UNREADABLE RECEIPT IS A CONFLICT, NEVER AN ABSENCE (the WARP-1208 review's F3). The attack,
# run over a REAL tree: settle, TRUNCATE the receipt, re-run. Before this hardening the truncated file read as
# ABSENT, was overwritten, and a SECOND incident.closed landed in the stream that every W10 measure reads.
with tempfile.TemporaryDirectory() as _irud:
    _ir_u_fs = IR.FilesystemReconciliationStore(_irud)
    _ir_u1, _ = _ir_go(store=_ir_u_fs)
    _ir_u_path = next((Path(_irud) / ".veldo" / "reconciliations").glob("*.json"))
    _ir_u_events = Path(_irud) / ".veldo" / "events.jsonl"
    for _irlabel, _irpayload in (("a CRASH-TRUNCATED receipt", '{"schema": "veldo.reconcil'),
                                 ("a receipt that is not JSON at all", "\x00 not json \x00"),
                                 ("a receipt whose payload is not a MAPPING", "null\n"),
                                 ("a receipt whose payload is a LIST", "[]\n")):
        _ir_u_path.write_text(_irpayload)
        _ir_u2, _ = _ir_go(store=_ir_u_fs)
        expect("WARP-1208 AC4 F3: %s REFUSES by name (reconciliation_receipt_unreadable), is NOT overwritten, and appends NO second incident.closed" % _irlabel,
               _ir_u2["refused"] == IR.REFUSE_RECEIPT_UNREADABLE and _ir_u_path.read_text() == _irpayload
               and sum(1 for ln in _ir_u_events.read_text().splitlines() if IR.INCIDENT_CLOSED in ln) == 1)
    expect("WARP-1208 AC4 F3: the store tells ABSENCE from CORRUPTION (None versus the UNREADABLE sentinel, which is neither None nor a mapping), and settle() names the third outcome",
           _ir_u_fs.get("REC-nothing-here-at-all") is None and _ir_u_fs.get(_ir_u1["receipt_id"]) is IR.UNREADABLE
           and IR.UNREADABLE is not None and not isinstance(IR.UNREADABLE, dict)
           and _ir_u_fs.settle(_ir_u1["receipt_id"], dict(_ir_rcpt), []) == ("unreadable", None))
    expect("WARP-1208 AC4 F3: an ALREADY-CLOSED incident whose receipt is unreadable REFUSES too, rather than returning a corrupt record as the proof that it is settled",
           _ir_go(store=_ir_u_fs, incident=_ir_inc(status="closed"))[0]["refused"] == IR.REFUSE_RECEIPT_UNREADABLE)
    _ir_u_path.write_text(json.dumps(_ir_u1["receipt"], indent=2, sort_keys=True, default=str) + "\n")
    expect("WARP-1208 AC4 F3 CONTROL: with the receipt RESTORED the very same re-run is an idempotent replay again (the refusal is about corruption, not about replay)",
           _ir_go(store=_ir_u_fs)[0]["outcome"] == IR.OUTCOME_ALREADY
           and sum(1 for ln in _ir_u_events.read_text().splitlines() if IR.INCIDENT_CLOSED in ln) == 1)
expect("WARP-1208 AC4: the receipt id is CONTENT-ADDRESSED over the settlement identity (a different remedy or execution receipt is a different id)",
       IR.reconciliation_id("INC-FIX", "sha256:a", "REM-FIX", "none") == IR.reconciliation_id("INC-FIX", "sha256:a", "REM-FIX", "none")
       and len({IR.reconciliation_id("INC-FIX", "sha256:a", "REM-FIX", "none"),
                IR.reconciliation_id("INC-FIX", "sha256:a", "REM-OTHER", "none"),
                IR.reconciliation_id("INC-FIX", "sha256:b", "REM-FIX", "none"),
                IR.reconciliation_id("INC-OTHER", "sha256:a", "REM-FIX", "none"),
                IR.reconciliation_id("INC-FIX", "sha256:a", "REM-FIX", "sha256:z")}) == 5)
# THE VOCABULARY BINDING: the emitter, the metric source, and the GATE cannot drift.
expect("WARP-1208 AC4: incident.INCIDENT_EVENT_TYPES is a subset of BOTH events.EVENT_TYPES and validate.EVENT_TYPES (emitter, metric source, and gate bound)",
       set(INC.INCIDENT_EVENT_TYPES) <= set(EV1208.EVENT_TYPES) and set(INC.INCIDENT_EVENT_TYPES) <= set(V.EVENT_TYPES)
       and IR.INCIDENT_EVENT_TYPES == frozenset(INC.INCIDENT_EVENT_TYPES) and IR.INCIDENT_CLOSED in INC.INCIDENT_EVENT_TYPES)
expect("WARP-1208 AC4: the event type is SELECTED from the contract's vocabulary, never written as a literal string in the organ",
       '"incident.closed"' not in _ir_src and "_lifecycle_event(STATUS_CLOSED)" in _ir_src)
with tempfile.TemporaryDirectory() as _ired:
    _ir_ev_log = Path(_ired) / "events.jsonl"
    _ir_ev_log.write_text("\n".join(json.dumps(e) for e in _ir_ok_st.events()) + "\n")
    expect("WARP-1208 AC4: the GATE now RECOGNIZES the emitted incident.closed event (validate.check_events reports zero problems)",
           V.check_events(str(_ir_ev_log)) == 0)
    # THE TEETH ARE DRIVEN ON A PRIVATE COPY OF THE VALIDATOR, NOT ON THE SHARED ONE. This block used to
    # strip the incident types out of the shared V.EVENT_TYPES, call check_events, and put them back. Two
    # problems with that, one latent and one structural. LATENT: the restore was not exception-safe, so if
    # check_events raised, V.EVENT_TYPES stayed mutated for every assertion in the remaining ten thousand
    # lines. STRUCTURAL: mutating the module object that 58 other regions read is an ORDERING DEPENDENCY,
    # and it is the single obstruction WARP-0716's survey measured as making the suite unsplittable - drop
    # it and the same rule reports FEASIBLE at 109 components. A private module instance proves exactly the
    # same property with neither problem, using the same importlib pattern this file already uses for V.
    _ir_v_spec = importlib.util.spec_from_file_location("validate_ir_teeth", ROOT / ".veldo" / "validate.py")
    _ir_V = importlib.util.module_from_spec(_ir_v_spec)
    _ir_v_spec.loader.exec_module(_ir_V)
    _ir_ev_saved = set(V.EVENT_TYPES)
    _ir_V.EVENT_TYPES.difference_update(INC.INCIDENT_EVENT_TYPES)
    _ir_ev_unrecognized = _ir_V.check_events(str(_ir_ev_log))
    expect("WARP-1208 AC4 TEETH: without the four incident types in validate.EVENT_TYPES the SAME event is REJECTED as unknown (the recognition is load-bearing)",
           _ir_ev_unrecognized > 0 and V.EVENT_TYPES == _ir_ev_saved and V.check_events(str(_ir_ev_log)) == 0)
    expect("WARP-1208 AC4 TEETH is driven WITHOUT mutating the shared validator: the private instance really lost the four incident types, the shared one never did, and they are therefore different objects",
           not (set(_ir_V.EVENT_TYPES) & set(INC.INCIDENT_EVENT_TYPES))
           and set(INC.INCIDENT_EVENT_TYPES) <= set(V.EVENT_TYPES)
           and _ir_V.EVENT_TYPES is not V.EVENT_TYPES)
expect("WARP-1208 AC6: the validate.py EVENT_TYPES change is PURELY ADDITIVE (the previously recognized set is untouched; only the four incident types are new)",
       set(V.EVENT_TYPES) - set(INC.INCIDENT_EVENT_TYPES) == {
           "plan.created", "plan.approved", "plan.revised", "work.pulled", "spec.ready", "spec.shipped",
           "spec.blocked", "gate.passed", "gate.failed", "proof.recorded", "review.requested",
           "verdict.recorded", "approval.recorded", "emergency.push", "emergency.closed",
           "merge.completed", "index.updated"})

# --- WARP-1208 AC5 anti-vacuity TEETH: TWELVE guards, TWELVE mutations, run as a FULL MATRIX. Each mutation
# neutralizes exactly ONE guard in an in-memory copy of the organ that OWNS it (nine in .veldo/incident_reconcile.py,
# three in the sibling .veldo/reconciliation_store.py), runs that guard's OWN refusing fixture through the mutant (it
# turns GREEN: it stops refusing), and asserts BOTH modules on disk are byte-unchanged. The matrix then runs every
# mutation against every OTHER guard's fixture and asserts it stays RED, so no mutation can flip a fixture it does
# not own. A safety property with no negative test is a claim, and this plan does not ship claims.
_IR_TEETH = {  # guard -> (the organ that owns it, the guard's line, that ONE guard neutralized)
    "status gate": ("pass", "    if status != STATUS_DIAGNOSED:", "    if False and status != STATUS_DIAGNOSED:"),
    "missing validation": ("pass", '    if not isinstance(validation, dict) or not _is_str(validation.get("validated_by")):',
                           '    if False and (not isinstance(validation, dict) or not _is_str(validation.get("validated_by"))):'),
    "machine actor": ("pass", "    if _norm(who) in MACHINE_ACTORS:", "    if False and _norm(who) in MACHINE_ACTORS:"),
    "unbound remedy": ("pass", "    if not validation_binds_remedy(remedy, validation):",
                       "    if False and not validation_binds_remedy(remedy, validation):"),
    "recomputed digest": ("pass", '    if validation.get("bound_digest") != recomputed:',
                          '    if False and validation.get("bound_digest") != recomputed:'),
    "open emergency debt": ("pass", "    if open_debt:", "    if False and open_debt:"),
    "reviewed draft": ("pass", "    if status != DRAFT_REVIEW_STATUS or any(f in requested for f in FORBIDDEN_DRAFT_REVIEW_FIELDS):",
                       "    if False and (status != DRAFT_REVIEW_STATUS or any(f in requested for f in FORBIDDEN_DRAFT_REVIEW_FIELDS)):"),
    "invalid rendered draft": ("pass", "    if problems:", "    if False and problems:"),
    "unsupported execution claim": ("pass", "    if not supported:", "    if False and not supported:"),
    "draft path": ("store", "        if forbidden is not None:", "        if False and forbidden is not None:"),
    "compare-and-swap conflict": ("store", "            if not _same_receipt(existing, record):",
                                  "            if False and not _same_receipt(existing, record):"),
    "unreadable receipt": ("store", "            return UNREADABLE  # PRESENT and unreadable (truncated, corrupt, unopenable): a CONFLICT",
                           "            return None  # neutralized: a corrupt receipt reads as an absence"),
}
# The path guard's two SUB-MECHANISMS, each with its own tooth and its own fixture. They are deliberately NOT matrix
# rows: they feed the SAME refusal decision as the "draft path" guard, so neutralizing that outer check dominates
# them by construction (it flips their fixtures too). That is a nesting, not a leak, and it is asserted below.
_IR_SUBTEETH = {
    "draft path resolution": ("store", "        resolved = Path(path).resolve()", "        resolved = Path(path)"),
    "draft path case fold": ("store", "    return tuple(part.casefold() for part in resolved.parts)",
                             "    return tuple(part for part in resolved.parts)"),
}
_IR_MUT_SRC = {"pass": _ir_src, "store": _ir_st_src}
expect("WARP-1208 AC5: every teeth mutation target appears EXACTLY ONCE in the organ that owns it (a mutation that matched nothing, or matched two guards, would prove nothing)",
       all(_IR_MUT_SRC[where].count(old) == 1 for where, old, _new in
           list(_IR_TEETH.values()) + list(_IR_SUBTEETH.values()))
       and len(_IR_TEETH) == 12 and len(_IR_SUBTEETH) == 2)
_IR_REAL_NS = {"reconcile_incident": IR.reconcile_incident,
               "FakeReconciliationStore": IR.FakeReconciliationStore,
               "FilesystemReconciliationStore": IR.FilesystemReconciliationStore}


def _ir_mut(guard):
    """(pass namespace, store namespace) with exactly ONE guard neutralized in exactly ONE organ, compiled IN
    MEMORY. A store mutation is driven through the REAL pass (the store is an injected seam, so a mutant store
    instance is simply passed in). Neither file on disk is ever written; _ir_sha_unchanged() proves it."""
    where, old, new = (_IR_TEETH.get(guard) or _IR_SUBTEETH[guard])
    rel = ".veldo/reconciliation_store.py" if where == "store" else ".veldo/incident_reconcile.py"
    g = {"__file__": str(ROOT / rel), "__name__": "veldo_%s_mut" % where}
    exec(compile(_IR_MUT_SRC[where].replace(old, new), "<%s_mut>" % where, "exec"), g)
    return (_IR_REAL_NS, g) if where == "store" else (g, g)


def _ir_fake_fixture(seed=None, drafts_dir=None, **over):
    """A refusing fixture over the IN-MEMORY store. run(pass_ns, store_ns) returns (the named refusal or None,
    the records written), so the same fixture runs against the real organs and against any mutant."""
    def run(pass_ns, store_ns):
        kw = {}
        if seed is not None:
            kw["receipts"] = dict(seed)
        if drafts_dir is not None:
            kw["drafts_dir"] = drafts_dir
        res, st = _ir_go(fn=pass_ns["reconcile_incident"], store=store_ns["FakeReconciliationStore"](**kw), **over)
        return res["refused"], st.count()
    return run


def _ir_unreadable_run(pass_ns, store_ns):
    """The F3 fixture over a REAL tree: settle, TRUNCATE the receipt, re-run. Returns (the named refusal or None,
    the number of EXTRA incident.closed events the re-run appended), so a neutralized sentinel shows up as both a
    green outcome and the duplicated event that corrupts every W10 measure."""
    with tempfile.TemporaryDirectory() as d:
        st = store_ns["FilesystemReconciliationStore"](d)
        _ir_go(fn=pass_ns["reconcile_incident"], store=st)
        next((Path(d) / ".veldo" / "reconciliations").glob("*.json")).write_text('{"schema": "veldo.reconcil')
        res, _ = _ir_go(fn=pass_ns["reconcile_incident"], store=st)
        lines = (Path(d) / ".veldo" / "events.jsonl").read_text().splitlines()
        return res["refused"], sum(1 for ln in lines if IR.INCIDENT_CLOSED in ln) - 1


_ir_cas_seed = {_ir_ok["receipt_id"]: dict(_ir_rcpt, incident="INC-TAMPERED")}
_IR_NOVALIDATOR = {k: v for k, v in _ir_val().items() if k != "validated_by"}
_IR_BADREM = dict(_IR_REM, proposed_action={"action": "rollback_deploy",
                                            "parameters": {"": "x", "service": "payment-confirmation"}})
_IR_FIXTURES = {  # guard -> (the refusal its fixture must draw from the REAL organs, the fixture runner)
    "status gate": (IR.REFUSE_NOT_DIAGNOSED, _ir_fake_fixture(incident=_ir_inc(status="open"))),
    "missing validation": (IR.REFUSE_MISSING_VALIDATION, _ir_fake_fixture(validation=_IR_NOVALIDATOR)),
    "machine actor": (IR.REFUSE_MACHINE_VALIDATOR, _ir_fake_fixture(validation=_ir_val(who="veldo-responder"))),
    "unbound remedy": (IR.REFUSE_VALIDATION_UNBOUND_REMEDY, _ir_fake_fixture(validation=_ir_val(bind=False))),
    "recomputed digest": (IR.REFUSE_VALIDATION_DIGEST_MISMATCH,
                          _ir_fake_fixture(validation=_ir_val(digest="sha256:forgedforgedfor"))),
    "open emergency debt": (IR.REFUSE_OPEN_EMERGENCY_DEBT,
                            _ir_fake_fixture(debt_reader=lambda inc: "WARP-1208 backfill still open")),
    "reviewed draft": (IR.REFUSE_DRAFT_REVIEWED, _ir_fake_fixture(
        draft_review={"status": "reviewed", "verdict": "approved", "reviewer": "the machine"})),
    "invalid rendered draft": (IR.REFUSE_DRAFT_INVALID,
                               _ir_fake_fixture(remedy=_IR_BADREM, execution_receipt=None)),
    "unsupported execution claim": (IR.REFUSE_UNSUPPORTED_EXECUTION_CLAIM, _ir_fake_fixture(
        execution_receipt=dict(_IR_RECEIPT, proposal_digest="sha256:notthedigest"))),
    "draft path": (IR.REFUSE_DRAFT_PATH_FORBIDDEN, _ir_fake_fixture(drafts_dir=Path("specs") / "drafts")),
    "compare-and-swap conflict": (IR.REFUSE_RECEIPT_CONFLICT, _ir_fake_fixture(seed=_ir_cas_seed)),
    "unreadable receipt": (IR.REFUSE_RECEIPT_UNREADABLE, _ir_unreadable_run),
}


def _ir_tooth(guard):
    """Run the guard's OWN refusing fixture through the real organs and then through its mutant. Returns
    (the real path refused BY NAME writing nothing, the mutant's refusal, what the mutant wrote): the real path
    must refuse and the mutant must stop refusing (None), which is the fixture turning green."""
    refusal, run = _IR_FIXTURES[guard]
    real = run(_IR_REAL_NS, _IR_REAL_NS)
    mut = run(*_ir_mut(guard))
    return (real == (refusal, 0), mut[0], mut[1])


expect("WARP-1208 AC5 T-status: neutralizing the STATUS GATE settles an OPEN incident (the real path refuses incident_not_diagnosed)",
       _ir_tooth("status gate") == (True, None, 1))
expect("WARP-1208 AC5 T-status: the mutation is in-memory only (.veldo/incident_reconcile.py and .veldo/reconciliation_store.py on disk sha256 unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-validation: neutralizing the MISSING-VALIDATION refusal settles an incident whose diagnosis NAMES no human validator",
       _ir_tooth("missing validation") == (True, None, 1))
expect("WARP-1208 AC5 T-validation: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-machine: neutralizing the MACHINE-ACTOR refusal lets the responder validate its own diagnosis (NG4 defeated)",
       _ir_tooth("machine actor") == (True, None, 1))
expect("WARP-1208 AC5 T-machine: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-remedybinding: neutralizing the UNBOUND-REMEDY refusal settles on a validation that names no remedy, so the human attests to a failure identity and not to the diagnosis",
       _ir_tooth("unbound remedy") == (True, None, 1))
expect("WARP-1208 AC5 T-remedybinding: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-digest: neutralizing the RECOMPUTED-DIGEST comparison accepts a forged binding (the real path recomputes from the record and its remedy)",
       _ir_tooth("recomputed digest") == (True, None, 1))
expect("WARP-1208 AC5 T-digest: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-debt: neutralizing the OPEN-DEBT refusal settles an incident whose fix never flowed the emergency lane",
       _ir_tooth("open emergency debt") == (True, None, 1))
expect("WARP-1208 AC5 T-debt: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-reviewed: neutralizing the REVIEWED-DRAFT refusal accepts a machine-recorded review on the draft",
       _ir_tooth("reviewed draft") == (True, None, 1))
expect("WARP-1208 AC5 T-reviewed: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-draftvalid: neutralizing the STRUCTURAL-VALIDITY refusal writes a draft the SHIPPED validator refuses and settles, recording it as a regression criterion",
       _ir_tooth("invalid rendered draft") == (True, None, 1))
expect("WARP-1208 AC5 T-draftvalid: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-claim: neutralizing the UNSUPPORTED-EXECUTION-CLAIM refusal records an execution its receipt does not support",
       _ir_tooth("unsupported execution claim") == (True, None, 1))
expect("WARP-1208 AC5 T-claim: the same mutation also settles an execution CLAIMED with no receipt at all",
       _ir_go(fn=_ir_mut("unsupported execution claim")[0]["reconcile_incident"],
              store=_ir_mut("unsupported execution claim")[1]["FakeReconciliationStore"](),
              execution_receipt=None, execution_claim=True)[0]["outcome"] == IR.OUTCOME_SETTLED)
expect("WARP-1208 AC5 T-claim: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-draftpath: neutralizing the DRAFT PATH GUARD in the store writes a draft into the forbidden root and settles",
       _ir_tooth("draft path") == (True, None, 1))
expect("WARP-1208 AC5 T-draftpath: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-cas: neutralizing the COMPARE-AND-SWAP conflict check accepts a conflicting write as a benign replay (the real path refuses and never overwrites)",
       _ir_tooth("compare-and-swap conflict") == (True, None, 0)
       and _ir_go(store=IR.FakeReconciliationStore(receipts=dict(_ir_cas_seed)))[1].get(_ir_ok["receipt_id"])["incident"] == "INC-TAMPERED")
expect("WARP-1208 AC5 T-cas: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())
expect("WARP-1208 AC5 T-unreadable: neutralizing the UNREADABLE-RECEIPT sentinel reads a truncated receipt as an ABSENCE, overwrites it, and appends a SECOND incident.closed for one incident",
       _ir_tooth("unreadable receipt") == (True, None, 1))
expect("WARP-1208 AC5 T-unreadable: the mutation is in-memory only (both organs on disk byte-unchanged)", _ir_sha_unchanged())

# THE FULL MATRIX: every mutation against every guard's fixture. A cell is GREEN when that fixture stopped
# refusing under that mutation. The matrix must be exactly the DIAGONAL: each mutation flips its own fixture and
# nothing else, so no guard is propped up by another and no mutation is quietly turning off two.
_ir_matrix = {}
for _irm in _IR_TEETH:
    _ir_m_ns = _ir_mut(_irm)
    for _irg, (_irref, _irrun) in _IR_FIXTURES.items():
        _ir_matrix[(_irm, _irg)] = _irrun(*_ir_m_ns)[0] is None
expect("WARP-1208 AC5 MATRIX: all 144 cells of the 12x12 teeth matrix are exactly the DIAGONAL - every mutation flips ONLY its own fixture, and every other fixture still refuses by its own name",
       all(_ir_matrix[(_irm, _irg)] == (_irm == _irg) for _irm in _IR_TEETH for _irg in _IR_FIXTURES)
       and len(_ir_matrix) == 144 and sum(1 for _v in _ir_matrix.values() if _v) == 12)
expect("WARP-1208 AC5 MATRIX: the matrix ran over BOTH organs (nine guards in the pass, three in the store) and neither file on disk changed",
       sorted({w for w, _o, _n in _IR_TEETH.values()}) == ["pass", "store"]
       and sum(1 for w, _o, _n in _IR_TEETH.values() if w == "store") == 3 and _ir_sha_unchanged())

# THE PATH GUARD'S SUB-MECHANISMS (F1): the RESOLUTION and the CASE FOLD each get their own tooth over their own
# crafted fixture. Neutralizing the resolution makes a '..' traversal reachable again; neutralizing the case fold
# makes a case variant reachable on the case-insensitive filesystems this engine ships to. The outer "draft path"
# check dominates both (it flips their fixtures too), which is why they are proven here rather than in the matrix.
with tempfile.TemporaryDirectory() as _irsd:
    (Path(_irsd) / ".veldo" / "actions").mkdir(parents=True)
    _IR_SUBFIX = {
        "draft path resolution": _ir_fake_fixture(
            drafts_dir=Path(_irsd) / ".veldo" / "incident_drafts" / ".." / "actions"),
        "draft path case fold": _ir_fake_fixture(drafts_dir=Path(_irsd) / ".VELDO" / "Actions"),
    }
    for _irsub, _irfix in _IR_SUBFIX.items():
        expect("WARP-1208 AC5 T-%s: the real path REFUSES its fixture by name and neutralizing THAT sub-mechanism alone makes the forbidden root reachable again" % _irsub.replace(" ", ""),
               _irfix(_IR_REAL_NS, _IR_REAL_NS) == (IR.REFUSE_DRAFT_PATH_FORBIDDEN, 0)
               and _irfix(*_ir_mut(_irsub))[0] is None and _ir_sha_unchanged())
    expect("WARP-1208 AC5 T-pathsub: each sub-mechanism mutation flips ONLY its own fixture (the resolution does not make a case variant reachable, and the case fold does not make a traversal reachable), while the outer path-guard check dominates both",
           _IR_SUBFIX["draft path case fold"](*_ir_mut("draft path resolution"))[0] == IR.REFUSE_DRAFT_PATH_FORBIDDEN
           and _IR_SUBFIX["draft path resolution"](*_ir_mut("draft path case fold"))[0] == IR.REFUSE_DRAFT_PATH_FORBIDDEN
           and all(_irfix(*_ir_mut("draft path"))[0] is None for _irfix in _IR_SUBFIX.values())
           and _IR_FIXTURES["draft path"][1](*_ir_mut("draft path resolution"))[0] == IR.REFUSE_DRAFT_PATH_FORBIDDEN
           and _IR_FIXTURES["draft path"][1](*_ir_mut("draft path case fold"))[0] == IR.REFUSE_DRAFT_PATH_FORBIDDEN)
expect("WARP-1208 AC5: the REVIEW-LANE guidance (the unmechanizable part) is labeled in the module source and rendered into both drafts",
       "REVIEW LANE (unmechanizable, NG5)" in _ir_src and "REVIEW LANE" in IR.REVIEW_LANE_GUIDANCE
       and IR.REVIEW_LANE_GUIDANCE in IR.render_criteria_draft(_IR_INC, "sha256:x", [])
       and IR.REVIEW_LANE_GUIDANCE in IR.render_runbook_draft(_IR_INC, _IR_REM, "sha256:x", []))
expect("WARP-1208 AC5: the refusal taxonomy is CLOSED, every refusal this suite exercised is in it, and the three the STORE decides are FOLDED IN from the store rather than restated",
       len(IR.REFUSALS) == 12 and {IR.REFUSE_NOT_DIAGNOSED, IR.REFUSE_MISSING_VALIDATION, IR.REFUSE_MACHINE_VALIDATOR,
                                   IR.REFUSE_VALIDATION_UNBOUND_REMEDY, IR.REFUSE_VALIDATION_DIGEST_MISMATCH,
                                   IR.REFUSE_OPEN_EMERGENCY_DEBT, IR.REFUSE_DRAFT_PATH_FORBIDDEN,
                                   IR.REFUSE_DRAFT_REVIEWED, IR.REFUSE_DRAFT_INVALID,
                                   IR.REFUSE_UNSUPPORTED_EXECUTION_CLAIM, IR.REFUSE_RECEIPT_CONFLICT,
                                   IR.REFUSE_RECEIPT_UNREADABLE} == set(IR.REFUSALS)
       and {IR.REFUSE_DRAFT_PATH_FORBIDDEN, IR.REFUSE_RECEIPT_CONFLICT, IR.REFUSE_RECEIPT_UNREADABLE}
       == {IRS.REFUSE_DRAFT_PATH_FORBIDDEN, IRS.REFUSE_RECEIPT_CONFLICT, IRS.REFUSE_RECEIPT_UNREADABLE}
       and all(('REFUSE_%s = _ST.REFUSE_%s' % (_n, _n)) in _ir_src for _n in
               ("DRAFT_PATH_FORBIDDEN", "RECEIPT_CONFLICT", "RECEIPT_UNREADABLE"))
       and set(IR.REFUSALS) == {v for k, v in vars(IR).items() if k.startswith("REFUSE_")})
_ir_reported = []
_ir_go(fail=lambda name, msg: _ir_reported.append((name, msg)))
_ir_go(validation=None, fail=lambda name, msg: _ir_reported.append((name, msg)))
expect("WARP-1208 observability: every settlement and every refusal emits ONE NAMED line through the injected fail reporter (diagnosable from the output alone)",
       len(_ir_reported) == 2 and _ir_reported[0][0] == _IR_INC["id"] and "settled: receipt REC-" in _ir_reported[0][1]
       and _ir_reported[1][1].startswith(IR.REFUSE_MISSING_VALIDATION + ":"))
_ir_out, sys.stdout = sys.stdout, open(os.devnull, "w")
try:
    _ir_cli = (IR.selfcheck(), IR.main(["selfcheck"]))
finally:
    sys.stdout.close(); sys.stdout = _ir_out
expect("WARP-1208 AC6: the in-session CLI selfcheck drives the fixture lifecycle green (the only entry point; nothing calls the pass automatically)",
       _ir_cli == (0, 0))

# AC6 ENGINE SYNC, honest capability, dogfood, and the untouched safety core.
for _irf in ("incident_reconcile.py", "reconciliation_store.py", "validate.py", "capabilities.yaml"):
    expect("WARP-1208 AC6: .veldo/%s is byte-identical root vs engine" % _irf,
           (ROOT / (".veldo/" + _irf)).read_bytes() == (ROOT / ("engine/.veldo/" + _irf)).read_bytes())
    expect("WARP-1208 AC6: .veldo/%s is byte-identical across all 6 packs" % _irf,
           (ROOT / (".veldo/" + _irf)).read_bytes() == (ROOT / ("engine/.veldo/" + _irf)).read_bytes())
expect("WARP-1208 AC6: the incident_reconciliation capability is declared mechanical with home .veldo/incident_reconcile.py",
       bool(re.search(r"(?m)^\s{2}incident_reconciliation:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/incident_reconcile\.py\b",
                      (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1208 AC6: the capability entry defers the NUMBERS to WARP-1210 and the init lay-down plus docs to WARP-1211 (honest deferral, nothing claimed)",
       all(t in (ROOT / ".veldo/capabilities.yaml").read_text() for t in
           ("WARP-1210 (W10)", "WARP-1211 (W11)", "incident_reconciliation:")))
expect("WARP-1208 AC6: the SAFETY CORE is byte-UNCHANGED and only READ (no incident_reconcile or reconciliation_store reference in the executor, the whitelist, the two-key gate, the contracts, or the authorization matrix)",
       all(_t not in (ROOT / (".veldo/" + _f)).read_text()
           for _f in ("action_executor.py", "action.py", "two_key.py", "incident.py", "authorization.py",
                      "policy_check.py")
           for _t in ("incident_reconcile", "reconciliation_store")))
expect("WARP-1208 AC6: nothing calls the pass or its store (no check, gate stage, validator, or run path references either; the CLI is the only entry point)",
       all(_t not in (ROOT / _f).read_text()
           for _f in ("scripts/verify.sh", ".veldo/validate.py", "scripts/veldo-guard.sh")
           for _t in ("incident_reconcile", "reconciliation_store")))
_p1208_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1208-incident-as-intent-and-reconciliation.md").read_text(), re.S).group(1))
expect("WARP-1208 AC6 dogfood: the spec is PLAN-0012 W8, standard risk, human_approval not required, and touches no protected path",
       _p1208_fm.get("plan") == "PLAN-0012" and _p1208_fm.get("work") == "W8"
       and _p1208_fm.get("risk", "").split()[0] == "standard" and _p1208_fm.get("human_approval") == "not_required"
       and (_p1208_fm.get("protected_paths") or []) == [])
expect("WARP-1208 AC6 dogfood: placement [contracts] with a footprint, behavior_bearing with an observability block, and check_ready clean",
       _p1208_fm.get("placement") == ["contracts"] and _p1208_fm.get("footprint")
       and _p1208_fm.get("behavior_bearing") == "true" and isinstance(_p1208_fm.get("observability"), dict)
       and V.check_ready(ROOT / "specs/WARP-1208-incident-as-intent-and-reconciliation.md", repo_root=str(ROOT)) == 0)
_p1208_arch, _p1208_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1208 AC6 dogfood: the spec placement resolves and passes the mandatory placement gate (footprint tier standard, no boundary crossing)",
       _p1208_contract is not None and _p1208_arch.placement_gate(_p1208_fm, _p1208_contract) == []
       and _p1208_arch.footprint_tier_floor(_p1208_fm, _p1208_contract) == "")


# --- the support numbers (WARP-1210, W10 of PLAN-0012): the second half of outcome O6, where "are we
# getting better at this" stops being a feeling and becomes a DERIVATION from artifacts the loop already
# wrote. .veldo/metrics.py gains a SECOND derivation beside compute(): time-to-diagnosis and
# time-to-restore as TRENDS (per-incident values in recorded order plus the median and the latest, never
# a single average that hides a regression), the RECURRENCE RATE (the share of authenticated closed
# incidents whose receipt carries a non-empty recurrence_of, the missing-specification signal WARP-1208
# records), and the DIAGNOSABILITY SCORE (the share resolved FROM ARTIFACTS ALONE under a declared
# mechanical proxy), plus the incidents-per-area SOFT JOIN with PLAN-0011's cost-to-change data.
# THE LOAD-BEARING PROPERTY IS AUTHENTICATION, and it answers the round-2 reviewer of WARP-1208 rather
# than an invention: the gate now RECOGNIZES the incident lifecycle events, so ANY writer can append an
# incident.closed, and recognition is not authentication. Every measure counts ONLY an incident whose
# closure is BACKED by a reconciliation receipt that resolves to it; an unbacked event and an
# unresolvable receipt are each EXCLUDED and REPORTED BY NAME. Proven ENTIRELY OFFLINE over seeded
# lifecycles and temporary trees (no live system, NG1), with positive controls, the honest empty state,
# the zero-denominator stand-downs, the three soft-join paths, and FIVE in-memory source-mutation TEETH
# run as a FULL 5x5 MATRIX asserted exactly diagonal while both modules stay byte-unchanged on disk.
_m10spec = importlib.util.spec_from_file_location("veldo_metrics_1210", ROOT / ".veldo/metrics.py")
M10 = importlib.util.module_from_spec(_m10spec); _m10spec.loader.exec_module(M10)
_m10esspec = importlib.util.spec_from_file_location("veldo_metrics_event_stream_1210",
                                                   ROOT / ".veldo/metrics_event_stream.py")
ES10 = importlib.util.module_from_spec(_m10esspec); _m10esspec.loader.exec_module(ES10)
_m10ctspec = importlib.util.spec_from_file_location("veldo_metrics_support_contract_1210",
                                                   ROOT / ".veldo/metrics_support_contract.py")
C10 = importlib.util.module_from_spec(_m10ctspec); _m10ctspec.loader.exec_module(C10)
_m10sspec = importlib.util.spec_from_file_location("veldo_metrics_support_1210",
                                                  ROOT / ".veldo/metrics_support.py")
S10 = importlib.util.module_from_spec(_m10sspec); _m10sspec.loader.exec_module(S10)
_m10aspec = importlib.util.spec_from_file_location("veldo_metrics_read_accounting_1210",
                                                  ROOT / ".veldo/metrics_read_accounting.py")
A10 = importlib.util.module_from_spec(_m10aspec); _m10aspec.loader.exec_module(A10)
_m10skspec = importlib.util.spec_from_file_location("veldo_metrics_skip_rule_1210",
                                                   ROOT / ".veldo/metrics_skip_rule.py")
SK10 = importlib.util.module_from_spec(_m10skspec); _m10skspec.loader.exec_module(SK10)
_m10kspec = importlib.util.spec_from_file_location("veldo_metrics_read_kind_1210",
                                                  ROOT / ".veldo/metrics_read_kind.py")
K10 = importlib.util.module_from_spec(_m10kspec); _m10kspec.loader.exec_module(K10)
_m10clspec = importlib.util.spec_from_file_location("veldo_metrics_read_closure_1210",
                                                   ROOT / ".veldo/metrics_read_closure.py")
CL10 = importlib.util.module_from_spec(_m10clspec); _m10clspec.loader.exec_module(CL10)
_m10ospec = importlib.util.spec_from_file_location("veldo_metrics_owner_reads_1210",
                                                  ROOT / ".veldo/metrics_owner_reads.py")
O10 = importlib.util.module_from_spec(_m10ospec); _m10ospec.loader.exec_module(O10)
_m10shspec = importlib.util.spec_from_file_location("veldo_metrics_shape_readers_1210",
                                                   ROOT / ".veldo/metrics_shape_readers.py")
SH10 = importlib.util.module_from_spec(_m10shspec); _m10shspec.loader.exec_module(SH10)
_m10rspec = importlib.util.spec_from_file_location("veldo_metrics_readers_1210",
                                                  ROOT / ".veldo/metrics_readers.py")
R10 = importlib.util.module_from_spec(_m10rspec); _m10rspec.loader.exec_module(R10)
_m10rptspec = importlib.util.spec_from_file_location("veldo_metrics_support_report_1210",
                                                    ROOT / ".veldo/metrics_support_report.py")
RPT10 = importlib.util.module_from_spec(_m10rptspec); _m10rptspec.loader.exec_module(RPT10)
_m10dbspec = importlib.util.spec_from_file_location("veldo_dashboard_1210", ROOT / ".veldo/dashboard.py")
DB10 = importlib.util.module_from_spec(_m10dbspec); _m10dbspec.loader.exec_module(DB10)
_m10_src = (ROOT / ".veldo/metrics.py").read_text()
_m10_es_src = (ROOT / ".veldo/metrics_event_stream.py").read_text()
_m10_ct_src = (ROOT / ".veldo/metrics_support_contract.py").read_text()
_m10_sup_src = (ROOT / ".veldo/metrics_support.py").read_text()
_m10_acc_src = (ROOT / ".veldo/metrics_read_accounting.py").read_text()
_m10_sk_src = (ROOT / ".veldo/metrics_skip_rule.py").read_text()
import socket as _m10_socket   # one skip-named UNIX SOCKET fixture, bound and never connected to (NG1)
_m10_kind_src = (ROOT / ".veldo/metrics_read_kind.py").read_text()
_m10_cl_src = (ROOT / ".veldo/metrics_read_closure.py").read_text()
_m10_own_src = (ROOT / ".veldo/metrics_owner_reads.py").read_text()
_m10_shp_src = (ROOT / ".veldo/metrics_shape_readers.py").read_text()
_m10_rdr_src = (ROOT / ".veldo/metrics_readers.py").read_text()
_m10_rpt_src = (ROOT / ".veldo/metrics_support_report.py").read_text()
_m10_db_src = (ROOT / ".veldo/dashboard.py").read_text()
_M10_SRCS = (_m10_src, _m10_es_src, _m10_ct_src, _m10_sup_src, _m10_acc_src, _m10_sk_src, _m10_kind_src,
             _m10_cl_src, _m10_own_src, _m10_shp_src, _m10_rdr_src, _m10_rpt_src, _m10_db_src)
_M10_FILES = (".veldo/metrics.py", ".veldo/metrics_event_stream.py",
              ".veldo/metrics_support_contract.py", ".veldo/metrics_support.py",
              ".veldo/metrics_read_accounting.py", ".veldo/metrics_skip_rule.py",
              ".veldo/metrics_read_kind.py", ".veldo/metrics_read_closure.py",
              ".veldo/metrics_owner_reads.py",
              ".veldo/metrics_shape_readers.py", ".veldo/metrics_readers.py",
              ".veldo/metrics_support_report.py", ".veldo/dashboard.py")
_m10_sha0 = {_f: _rr_hashlib.sha256((ROOT / _f).read_bytes()).hexdigest() for _f in _M10_FILES}
# THE TWO SWEEP REGISTERS, filled BY the assertions below and checked for COMPLETENESS against the
# module's own declared tables at the end of this block. Round 2 failed this item because round 1's two
# defects were fixed on the inputs they were REPORTED on and not on their siblings, so the suite now
# proves the sweep was systematic rather than incidental: an unreadable state that no assertion reaches
# leaves its source missing from this register and the completeness assertion names it.
_M10_SWEPT_SOURCES = {}   # source id -> the reason name an assertion actually OBSERVED for it
_M10_SWEPT_KEYED = {}     # id-keyed collection -> the conflict name observed, or the immunity proven


def _m10_sha_unchanged():
    """BOTH modules on disk, byte-unchanged. Every teeth mutation is compiled IN MEMORY, so this holds
    after each one and after the whole matrix."""
    return all(_rr_hashlib.sha256((ROOT / _f).read_bytes()).hexdigest() == _m10_sha0[_f]
               for _f in _M10_FILES)


# The SEEDED LIFECYCLE: the recorded close events, the reconciliation RECEIPTS that back them (the
# authority), and the veldo.incident/v1 RECORDS whose validated timelines carry the two intervals. The
# records are parsed through the ONE parser and asserted contract-valid below, so the timelines are the
# real validated shape rather than a hand-made dict.
_M10_CLOSED = "incident.closed"


def _m10_event(iid, at="2026-07-24T04:00:00Z", etype=_M10_CLOSED, **over):
    ev = {"schema": "veldo.event/v1", "type": etype, "at": at, "producer": IR.SETTLED_BY,
          "correlation_id": iid, "incident": iid}
    ev.update(over)
    return ev


def _m10_receipt(iid, recurrence=(), validated_by="dmitry", **over):
    rec = {"schema": IR.SCHEMA, "id": "REC-" + iid, "incident": iid,
           "recurrence_of": list(recurrence), "missing_specification": bool(recurrence),
           "diagnosis_validation": {"validated_by": validated_by, "bound_digest": "sha256:seeded"}}
    rec.update(over)
    return rec


def _m10_record_text(iid, diagnosed, restored=None, spec="WARP-1210", area=None):
    lines = ["schema: veldo.incident/v1", "id: %s" % iid, "title: a seeded incident",
             "signal: p99 latency rose at the deploy boundary with no error-rate change.",
             "affected_behavior: the endpoint returns within its latency budget after a charge.",
             "severity: high", "status: diagnosed"]
    if spec:
        lines.append("affected_spec: %s" % spec)
    if area:
        lines.append("affected_area: %s" % area)
    lines += ["timeline:", "  opened_at: 2026-07-24T00:00:00Z", "  diagnosed_at: %s" % diagnosed]
    if restored:
        lines.append("  restored_at: %s" % restored)
    return "\n".join(lines) + "\n"


def _m10_record(iid, diagnosed="2026-07-24T03:00:00Z", restored=None, spec="WARP-1210", area=None):
    return V.parse_yamlish(_m10_record_text(iid, diagnosed, restored, spec, area))


# INC-A resolves through its affected_spec's PLACEMENT, INC-B through its declared affected_area, and
# the recorded order (A then B) carries DESCENDING values, so a trend that sorted its observations
# would be caught.
_M10_EVENTS = [_m10_event("INC-A"), _m10_event("INC-B", at="2026-07-24T05:00:00Z")]
# INC-B's receipt names a recurrence of INC-A, an incident the stream reports CLOSED and a record the
# readers carry, so the recurrence CROSS-REFERENCE (round-2 note 2) resolves rather than counting a
# phantom string. A recurrence_of nothing carries is named UNRESOLVED_RECURRENCE and not counted.
_M10_RECEIPTS = [_m10_receipt("INC-A"), _m10_receipt("INC-B", recurrence=["INC-A"])]
_M10_RECORDS = [_m10_record("INC-A", diagnosed="2026-07-24T03:00:00Z", restored="2026-07-24T05:00:00Z"),
                _m10_record("INC-B", diagnosed="2026-07-24T01:00:00Z", restored="2026-07-24T02:00:00Z",
                            spec=None, area="metrics")]
_M10_NO_RESTORE = [_m10_record("INC-A", diagnosed="2026-07-24T03:00:00Z"),
                   _m10_record("INC-B", diagnosed="2026-07-24T01:00:00Z", spec=None, area="metrics")]
_M10_SPEC_AREAS = {"WARP-1210": ["metrics"], "WARP-9210": []}
_M10_AREAS = ["contracts", "metrics"]
_M10_COST = {"metrics": {"samples": 8, "latest": {"human_minutes": 30, "tokens": 300,
                                                 "review_cycles": 3, "cost_usd": 0.5,
                                                 "gate_failures": 1}}}


def _m10_reads(contract=C10, **over):
    """A COMPLETE READ for every DECLARED source, as a fixture injects them. The suite builds these FROM
    the declared table rather than listing sources by hand, so a source added to SUPPORT_SOURCES later
    cannot leave the seeded fixtures half-affirmed and quietly stood down; the FAIL-CLOSED half (a source
    with NO read, or a read that does not prove complete) is asserted directly and separately, which is
    where it belongs. `over` replaces one source's read, which is how a fixture makes exactly one source
    unproven with no filesystem at all."""
    reads = [contract.read_complete(_r["source"], "injected by the suite",
                                    "the suite injected this source's values directly, so there is no "
                                    "partial read of it to hide")
             for _r in contract.SUPPORT_SOURCES if _r["source"] not in over]
    return reads + [_v for _v in over.values() if _v is not None]


def _m10_go(fn=None, **over):
    """Derive the support numbers over the seeded lifecycle. The vocabulary and every reader are
    INJECTED, so the pure path runs with NO filesystem read at all; fn accepts a MUTANT module's entry
    point, so a teeth mutation runs the SAME fixture through the neutralized copy. The COMPLETENESS
    ASSERTIONS are injected too (AC3): a fixture that supplies its inputs by hand still has to say that
    each declared source was read completely, or the model renders no number at all."""
    events = over.pop("events", _M10_EVENTS)
    kw = {"receipts": list(_M10_RECEIPTS), "incidents": list(_M10_RECORDS),
          "spec_areas": dict(_M10_SPEC_AREAS), "contract_areas": list(_M10_AREAS),
          "area_cost": dict(_M10_COST), "closed_event_type": _M10_CLOSED,
          "source_reads": _m10_reads()}
    kw.update(over)
    return (fn or S10.support_numbers)(events, **kw)


# AC1 THE FOUR MEASURES, derived from recorded data only over the seeded lifecycle.
expect("WARP-1210 AC1: the seeded incident RECORDS are contract-valid veldo.incident/v1 records, so the timelines the trends read are REAL validated records rather than hand-made dicts - and 'validated' means only what that validator checks, which is a LEXICOGRAPHIC string compare rather than calendar math (the premise round 1 refuted, corrected here in the suite's own words too)",
       all(INC.validate_incident(_r, ROOT, "selftest.1210", V.fail) == 0 for _r in _M10_RECORDS)
       and all(INC.validate_incident(_r, ROOT, "selftest.1210", V.fail) == 0 for _r in _M10_NO_RESTORE))
_m10_ok = _m10_go()
expect("WARP-1210 AC1: TIME-TO-DIAGNOSIS is opened_at to diagnosed_at per incident, at the declared hours precision",
       [(_o["incident"], _o["hours"]) for _o in _m10_ok["time_to_diagnosis"]["observations"]]
       == [("INC-A", 3.0), ("INC-B", 1.0)] and _m10_ok["time_to_diagnosis"]["field"] == "diagnosed_at")
expect("WARP-1210 AC1: TIME-TO-RESTORE is opened_at to restored_at per incident",
       [(_o["incident"], _o["hours"]) for _o in _m10_ok["time_to_restore"]["observations"]]
       == [("INC-A", 5.0), ("INC-B", 2.0)] and _m10_ok["time_to_restore"]["field"] == "restored_at")
expect("WARP-1210 AC1: each interval is reported as a TREND - the per-incident values plus the MEDIAN and the LATEST, and NEVER a single average (no mean or average key exists on the measure)",
       _m10_ok["time_to_diagnosis"]["median"] == 2.0 and _m10_ok["time_to_diagnosis"]["latest"] == 1.0
       and _m10_ok["time_to_restore"]["median"] == 3.5 and _m10_ok["time_to_restore"]["latest"] == 2.0
       and not any(_k in _m10_ok["time_to_diagnosis"] for _k in ("average", "avg", "mean")))
expect("WARP-1210 AC1: the trend preserves RECORDED ORDER, never a sorted one (the seeded values descend, so the latest is the SMALLEST and a sort would move it)",
       [_o["hours"] for _o in _m10_ok["time_to_diagnosis"]["observations"]] == [3.0, 1.0]
       and _m10_ok["time_to_diagnosis"]["latest"]
       != max(_o["hours"] for _o in _m10_ok["time_to_diagnosis"]["observations"])
       and _m10_ok["authenticated"] == ["INC-A", "INC-B"])
expect("WARP-1210 AC1: the MEDIAN of an even count is the declared mean of the two middle values, of an odd count the middle value, and of nothing is None",
       S10._median([1.0, 4.0]) == 2.5 and S10._median([1.0, 2.0, 9.0]) == 2.0
       and S10._median([]) is None)
expect("WARP-1210 AC1: RECURRENCE RATE is the share of authenticated closed incidents whose RECEIPT carries a non-empty recurrence_of (the missing-specification signal WARP-1208 records)",
       _m10_ok["recurrence_rate"]["numerator"] == 1 and _m10_ok["recurrence_rate"]["denominator"] == 2
       and _m10_ok["recurrence_rate"]["rate"] == 0.5 and _m10_ok["recurrence_rate"]["percent"] == 50.0
       and _m10_ok["recurrence_rate"]["incidents"] == ["INC-B"])
expect("WARP-1210 AC1: the recurrence signal is read from the RECEIPT and never from the event (an event carrying recurrence_of while its receipt carries none does NOT count)",
       S10.recurring_incidents(["INC-A"], {"INC-A": _m10_receipt("INC-A")}, ["INC-A"]) == ([], [])
       and S10.recurring_incidents(["INC-A"], {"INC-A": _m10_receipt("INC-A", recurrence=["INC-0"])},
                                   ["INC-0"])[0] == ["INC-A"]
       and _m10_go(events=[_m10_event("INC-A", recurrence_of=["INC-0"])],
                   receipts=[_m10_receipt("INC-A")])["recurrence_rate"]["numerator"] == 0)
expect("WARP-1210 AC1: an EMPTY recurrence_of, a non-list, and a list of blanks are all first occurrences, never a recurrence",
       S10.recurring_incidents(["A", "B", "C"], {"A": {"recurrence_of": []},
                                                 "B": {"recurrence_of": "INC-0"},
                                                 "C": {"recurrence_of": ["", "   "]}},
                               ["A", "B", "C"]) == ([], []))
expect("WARP-1210 AC1: DIAGNOSABILITY SCORE is the share resolved FROM ARTIFACTS ALONE under the declared mechanical definition (a recorded diagnosis validation AND a resolving spec or declared area)",
       _m10_ok["diagnosability_score"]["numerator"] == 2
       and _m10_ok["diagnosability_score"]["denominator"] == 2
       and _m10_ok["diagnosability_score"]["percent"] == 100.0)
expect("WARP-1210 AC1: an incident whose receipt records NO diagnosis validation is NOT diagnosable (the definition's first half is load-bearing)",
       _m10_go(receipts=[_m10_receipt("INC-A", validated_by=""),
                         _m10_receipt("INC-B")])["diagnosability_score"]["numerator"] == 1
       and S10._records_diagnosis_validation({"diagnosis_validation": {"validated_by": "dmitry"}}) is True
       and S10._records_diagnosis_validation({"diagnosis_validation": "a human, honest"}) is False
       and S10._records_diagnosis_validation({}) is False)
expect("WARP-1210 AC1: an incident that resolves to NEITHER a corpus spec NOR a declared area is NOT diagnosable (the second half is load-bearing), and it is never inferred from prose",
       _m10_go(incidents=[_m10_record("INC-A", spec="VELDO-NOT-IN-CORPUS"),
                          _m10_record("INC-B", spec=None, area="an-undeclared-area")]
               )["diagnosability_score"]["numerator"] == 0)
expect("WARP-1210 AC1: a governing spec the corpus carries resolves EVEN WITH NO CONTRACT, so the diagnosability score never silently depends on the architecture join",
       _m10_go(contract_areas=None)["diagnosability_score"]["numerator"] == 1
       and S10.incident_corpus_resolution(_M10_RECORDS[0], _M10_SPEC_AREAS, None)["spec"] == "WARP-1210")
# AC1 PURITY: the same inputs give the same numbers across processes, and the derivation names no
# filesystem, clock or network primitive at all.
_m10_pure_code = ("import importlib.util,json,sys\n"
                  "s=importlib.util.spec_from_file_location('m', sys.argv[1])\n"
                  "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                  "a=json.loads(sys.argv[2])\n"
                  "print(json.dumps(m.support_numbers(a['events'], **a['kw']), sort_keys=True))\n")
_m10_pure_arg = json.dumps({"events": _M10_EVENTS,
                            "kw": {"receipts": _M10_RECEIPTS, "incidents": _M10_RECORDS,
                                   "spec_areas": _M10_SPEC_AREAS, "contract_areas": _M10_AREAS,
                                   "area_cost": _M10_COST, "closed_event_type": _M10_CLOSED,
                                   "source_reads": _m10_reads()}})
_m10_pure_out = []
for _seed in ("0", "12345"):
    _m10_pure_out.append(subprocess.run(
        [sys.executable, "-c", _m10_pure_code, str(ROOT / ".veldo/metrics_support.py"), _m10_pure_arg],
        capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=_seed)).stdout.strip())
expect("WARP-1210 AC1: the measures are IDENTICAL across processes under two different PYTHONHASHSEEDs (a pure derivation over the injected readers: no clock, no salted hash, no ambient state)",
       len(set(_m10_pure_out)) == 1 and _m10_pure_out[0] == json.dumps(_m10_ok, sort_keys=True))
_M10_PURE_FNS = ("closed_incident_ids", "_receipt_problem", "authenticate_incidents", "_incident_hours",
                 "_median", "_population", "support_trend", "support_share", "recurring_incidents",
                 "_records_diagnosis_validation", "incident_corpus_resolution",
                 "diagnosable_incidents", "_area_cost_cell", "incidents_per_area", "support_numbers",
                 # the round-3 additions, held to the same purity: the record index, the timeline
                 # problem, the substance fingerprint, the dependence report, and the whole REPORT layer
                 # (the named set and the text presentation).
                 "_timeline_problem",
                 "_interval_hours", "_incident_interval", "index_incident_records", "_record_substance",
                 "contract_dependence", "_receipt_schema_problem",
                 "support_empty", "_support_subject", "support_named_inputs", "_support_named_line",
                 "_support_trend_lines", "_support_share_lines", "_support_dependence_lines",
                 "_support_area_lines", "support_lines",
                 # the round-5 additions: the DECLARED CONTRACT (the closed names, the source table and
                 # the ONE completeness decision, now its own module) and the two render decisions the
                 # governing rule adds. The completeness rule is a PURE decision over injected read
                 # records: the READING is impure and lives in the readers, the JUDGING is not.
                 "read_complete", "read_incomplete", "read_proves_complete", "read_problems",
                 "_read_shortfall", "support_completeness", "source_problem_detail", "_problem_fields",
                 "_named_problem", "support_source_problems",
                 "support_renderable", "support_standdown_lines",
                 # the round-6 additions: the ONE string primitive that makes a rendered value printable
                 # on any output stream (a PURE function of a string, which is why it belongs to the
                 # declared contract rather than to a renderer), and the two halves of the text and
                 # machine presentations the third surface needed.
                 "printable", "support_json", "_support_section_lines",
                 # the round-7 additions, both pure: the read record's list of DECLARED NON-RECORDS it
                 # accounted for and did not read, and the text presentation of that list.
                 "_skipped_entries", "support_skipped_lines")
_M10_IMPURE_NAMES = {"Path", "open", "glob", "read_text", "read_bytes", "write_text", "now",
                     "socket", "environ", "load", "_sibling", "compute", "listdir", "lstat"}
_m10_trees = [_ir_ast.parse(_s) for _s in (_m10_src, _m10_es_src, _m10_ct_src, _m10_sup_src,
                                          _m10_acc_src, _m10_sk_src, _m10_kind_src, _m10_cl_src,
                                          _m10_own_src, _m10_shp_src, _m10_rdr_src, _m10_rpt_src)]
(_m10_tree, _m10_es_tree, _m10_ct_tree, _m10_sup_tree, _m10_acc_tree, _m10_sk_tree, _m10_kind_tree,
 _m10_cl_tree, _m10_own_tree, _m10_shp_tree, _m10_rdr_tree, _m10_rpt_tree) = _m10_trees
_m10_fn_nodes = {_n.name: _n for _t in _m10_trees for _n in _t.body
                 if isinstance(_n, _ir_ast.FunctionDef)}


def _m10_names(fn_name):
    """Every Name and Attribute identifier one function references, so a filesystem, clock or network
    primitive inside the pure derivation is caught by the source rather than by trust."""
    out = set()
    for _n in _ir_ast.walk(_m10_fn_nodes[fn_name]):
        if isinstance(_n, _ir_ast.Name):
            out.add(_n.id)
        elif isinstance(_n, _ir_ast.Attribute):
            out.add(_n.attr)
    return out


expect("WARP-1210 AC1: NO function of the DECLARED CONTRACT, the PURE derivation OR the REPORT layer names a filesystem, clock, network or reader primitive (Path/open/glob/read_text/write_text/now/socket/environ/load/_sibling/compute/listdir/lstat absent from all 48, which is EVERY function of all three pure modules, asserted by comparing the list to the modules' own definitions rather than by keeping a hand list in step) - and the two enumeration primitives the readers now need (os.listdir, os.lstat) are in that forbidden set, so the ACCOUNTING can only live at the impure edge",
       len(_M10_PURE_FNS) == 48 and len(set(_M10_PURE_FNS)) == 48
       and all(_f in _m10_fn_nodes for _f in _M10_PURE_FNS)
       and not any(_m10_names(_f) & _M10_IMPURE_NAMES for _f in _M10_PURE_FNS)
       and sorted(_M10_PURE_FNS) == sorted(_n.name for _t in (_m10_ct_tree, _m10_sup_tree, _m10_rpt_tree)
                                           for _n in _t.body
                                           if isinstance(_n, _ir_ast.FunctionDef)))
expect("WARP-1210 AC1: the ONLY function that loads a sibling OWNER module is the ONE declared owner edge, plus the CLI edge - NO FUNCTION of any of the three pure modules loads anything, so the impure edge is exactly where it is declared to be. Stated exactly: the DERIVATION performs TWO loads at IMPORT (the core's timestamp reader and the declared contract), the CONTRACT and the REPORT layer ONE each (the core's string predicate; the contract's closed set of names), the READERS TWO (the core's loader and the contract), and none of them reads a file, a clock or a network in any function. The four owner modules are loaded through _owner(), which is why they are a DECLARED SOURCE FAMILY that can name itself rather than four exec calls scattered across four readers",
       sorted(_f for _f in _m10_fn_nodes if "_sibling" in _m10_names(_f)) == ["_owner", "main"]
       and not any("_sibling" in _m10_names(_n.name)
                   for _t in (_m10_ct_tree, _m10_sup_tree, _m10_rpt_tree)
                   for _n in _t.body if isinstance(_n, _ir_ast.FunctionDef))
       and _m10_ct_src.count("spec_from_file_location") == 1
       and _m10_sup_src.count("spec_from_file_location") == 2
       and _m10_rdr_src.count("spec_from_file_location") == 2
       and _m10_rpt_src.count("spec_from_file_location") == 1
       and '"veldo_metrics_core_for_support",\n' in _m10_sup_src
       and '"veldo_metrics_support_contract_for_support",\n' in _m10_sup_src
       and '"veldo_metrics_support_contract_for_report",\n' in _m10_rpt_src
       # the REPORT layer no longer loads the DERIVATION at all: a layer that renders a MODEL needs the
       # vocabulary, not the arithmetic, and one fewer dependency edge is one fewer way to drift.
       and "metrics_support.py" not in _m10_rpt_src.split('"""', 2)[2]
       and not any(isinstance(_n, (_ir_ast.FunctionDef, _ir_ast.ClassDef))
                   and "spec_from_file_location" in _m10_names(_n.name)
                   for _n in _m10_rpt_tree.body if isinstance(_n, _ir_ast.FunctionDef)))
expect("WARP-1210 AC1: NO NEW EVENT TYPE, NO NEW STORE, NO NEW RECORD - none of the TWELVE modules of the pass writes a file or declares a schema of its OWN (the count is the file list minus the dashboard surface, measured rather than carried; round 10 added the LOOP DERIVATION'S OWN READ as the tenth, round 11 the DECLARED READ UNIT AND ITS KIND as the eleventh, and round 12 the TRANSITIVE CLOSURE OF A DELEGATED READ as the twelfth); the ONE schema literal in the pass is the RECEIPT schema the contract declares and the derivation CHECKS (bound to incident_reconcile.SCHEMA below), and the close event type is SELECTED from the vocabulary the incident contract owns rather than written as a literal",
       all("write_text" not in _s and '"schema":' not in _s
           and '"incident.closed"' not in _s
           for _s in (_m10_src, _m10_es_src, _m10_ct_src, _m10_sup_src, _m10_acc_src, _m10_sk_src,
                      _m10_kind_src, _m10_cl_src, _m10_own_src, _m10_shp_src, _m10_rdr_src,
                      _m10_rpt_src))
       and len((_m10_src, _m10_es_src, _m10_ct_src, _m10_sup_src, _m10_acc_src, _m10_sk_src,
                _m10_kind_src, _m10_cl_src, _m10_own_src, _m10_shp_src, _m10_rdr_src, _m10_rpt_src))
       == len(_M10_FILES) - 1
       and _m10_ct_src.count('"veldo.reconciliation/v1"') == 1
       and "veldo.reconciliation/v1" not in _m10_src and "veldo.reconciliation/v1" not in _m10_rdr_src
       and "veldo.reconciliation/v1" not in _m10_rpt_src
       and "veldo.reconciliation/v1" not in _m10_sup_src
       and "SUPPORT_CLOSED_STEP" in _m10_rdr_src
       and R10.support_vocabulary()["closed_event_type"] == IR.INCIDENT_CLOSED
       and IR.INCIDENT_CLOSED in INC.INCIDENT_EVENT_TYPES
       and R10.support_vocabulary()["closed_event_type"] in EV1208.EVENT_TYPES
       and R10.support_vocabulary()["closed_event_type"] in V.EVENT_TYPES)
_m10_saved_vocab = R10._SUPPORT_VOCAB
R10._SUPPORT_VOCAB = {"closed_event_type": None}
_m10_novocab_type = R10.support_vocabulary()["closed_event_type"]
_m10_novocab = S10.support_numbers(_M10_EVENTS, receipts=_M10_RECEIPTS,
                                   closed_event_type=_m10_novocab_type,
                                   source_reads=_m10_reads())
R10._SUPPORT_VOCAB = _m10_saved_vocab
expect("WARP-1210 AC1: an engine whose vocabulary owner cannot be resolved supplies NO close event type, so the derivation recognizes nothing and stands down honestly (adoption safe) instead of raising in the metrics CLI - and the SAME stream WITH the resolved type counts, so the stand-down is not vacuous",
       _m10_novocab_type is None and _m10_novocab["closed_events"] == 0
       and _m10_novocab["authenticated_count"] == 0
       and "vocabulary owner is absent" in "\n".join(RPT10.support_lines(_m10_novocab))
       and R10.support_vocabulary()["closed_event_type"] == IR.INCIDENT_CLOSED
       and S10.support_numbers(_M10_EVENTS, receipts=_M10_RECEIPTS,
                               closed_event_type=R10.support_vocabulary()["closed_event_type"],
                               source_reads=_m10_reads())["authenticated_count"] == 2)

# AC2 THE NUMBERS ARE AUTHENTICATED AGAINST THE RECEIPTS (the load-bearing property of this item).
expect("WARP-1210 AC2 CONTROL: the seeded lifecycle WITH matching receipts COUNTS - both incidents authenticated, nothing excluded, every measure reporting a number",
       _m10_ok["authenticated"] == ["INC-A", "INC-B"] and _m10_ok["excluded"] == []
       and _m10_ok["closed_events"] == 2 and _m10_ok["receipts_read"] == 2
       and all(_m10_ok[_k]["standdown"] is None for _k in
               ("time_to_diagnosis", "time_to_restore", "recurrence_rate", "diagnosability_score")))
_m10_noreceipts = _m10_go(receipts=[])
expect("WARP-1210 AC2: the SAME lifecycle with the RECEIPTS REMOVED counts NOTHING - zero authenticated, every measure standing down by name, and never a fallback to the raw events",
       _m10_noreceipts["closed_events"] == 2 and _m10_noreceipts["authenticated"] == []
       and _m10_noreceipts["authenticated_count"] == 0
       and all(_m10_noreceipts[_k]["standdown"] == C10.SUPPORT_EMPTY_DENOMINATOR for _k in
               ("time_to_diagnosis", "time_to_restore", "recurrence_rate", "diagnosability_score")))
expect("WARP-1210 AC2: with the receipts removed EVERY exclusion is NAMED with its incident id (UNBACKED_EVENT for each), so the gap is diagnosable from the output alone",
       [(_x["reason"], _x["incident"]) for _x in _m10_noreceipts["excluded"]]
       == [(C10.SUPPORT_UNBACKED_EVENT, "INC-A"), (C10.SUPPORT_UNBACKED_EVENT, "INC-B")]
       and all("recognition is not authentication" in _x["detail"]
               for _x in _m10_noreceipts["excluded"]))
expect("WARP-1210 AC2: a repository with NO receipt reader at all (receipts=None) stands down identically - the injected reader's absence is zero authenticated, byte for byte",
       json.dumps(_m10_go(receipts=None), sort_keys=True) == json.dumps(_m10_noreceipts, sort_keys=True))
_m10_forged = _m10_go(events=_M10_EVENTS + [_m10_event("INC-FORGED", at="2026-07-24T06:00:00Z")])
expect("WARP-1210 AC2: a FORGED incident.closed appended by hand with no receipt is EXCLUDED and NAMED while the genuine incidents around it still count",
       _m10_forged["authenticated"] == ["INC-A", "INC-B"] and _m10_forged["closed_events"] == 3
       and [(_x["reason"], _x["incident"]) for _x in _m10_forged["excluded"]]
       == [(C10.SUPPORT_UNBACKED_EVENT, "INC-FORGED")]
       and _m10_forged["recurrence_rate"]["denominator"] == 2
       and _m10_forged["time_to_diagnosis"]["observations"]
       == _m10_ok["time_to_diagnosis"]["observations"])
_m10_ghost = _m10_go(receipts=_M10_RECEIPTS + [_m10_receipt("INC-GHOST")])
expect("WARP-1210 AC2: a receipt whose incident the stream never reports closed is EXCLUDED and NAMED (UNRESOLVED_RECEIPT) with its receipt id - a settlement with no close event is not evidence of a closure",
       [(_x["reason"], _x["receipt"], _x["incident"]) for _x in _m10_ghost["excluded"]]
       == [(C10.SUPPORT_UNRESOLVED_RECEIPT, "REC-INC-GHOST", "INC-GHOST")]
       and _m10_ghost["authenticated"] == ["INC-A", "INC-B"])
expect("WARP-1210 AC2: a receipt that is not a record, and one that names no incident, are each EXCLUDED and NAMED rather than counted",
       [_x["detail"] for _x in _m10_go(receipts=["not a receipt at all"])["excluded"]][0]
       == "the receipt is not a record (mapping)"
       and "names no incident" in [_x["detail"] for _x in _m10_go(
           receipts=[{"schema": IR.SCHEMA, "id": "REC-X"}])["excluded"]][0]
       and _m10_go(receipts=[{"incident": "   "}])["authenticated"] == [])
expect("WARP-1210 AC2: a DUPLICATED close event for one incident names it ONCE, so a double-emitted event cannot double-count a measure",
       _m10_go(events=_M10_EVENTS + [_m10_event("INC-A", at="2026-07-24T07:00:00Z")])["closed_events"] == 2
       and S10.closed_incident_ids([_m10_event("INC-A"), _m10_event("INC-A")], _M10_CLOSED) == ["INC-A"])
expect("WARP-1210 AC2: an event of another type, one that is not a record, and one naming no incident contribute nothing (the index is the close event type alone)",
       S10.closed_incident_ids([_m10_event("INC-A", etype="gate.passed"),
                                {"type": _M10_CLOSED, "at": "x"}, "not an event"], _M10_CLOSED) == [])
expect("WARP-1210 AC2: the close event's own incident field is preferred and its correlation_id is the fallback (the reconciliation stamps both)",
       S10.closed_incident_ids([{"type": _M10_CLOSED, "incident": "INC-FIELD",
                                 "correlation_id": "INC-CORR"},
                                {"type": _M10_CLOSED, "correlation_id": "INC-ONLY-CORR"}], _M10_CLOSED)
       == ["INC-FIELD", "INC-ONLY-CORR"])
_m10_ok_text = "\n".join(RPT10.support_lines(_m10_ok))
_m10_forged_text = "\n".join(RPT10.support_lines(_m10_forged))
_m10_measure_lines = [_l.strip() for _l in _m10_forged_text.splitlines()
                      if _l.strip().startswith(("time-to-diagnosis:", "time-to-restore:",
                                                "recurrence rate:", "diagnosability score:"))]
expect("WARP-1210 AC2: the AUTHENTICATED-VERSUS-EXCLUDED counts are reported BESIDE the numbers rather than in a footnote, and every excluded input is named in the rendered output",
       "authenticated: 2 of 3 closed incident(s) backed by a receipt" in _m10_forged_text
       and "2 receipt(s) read" in _m10_forged_text and "1 input(s) excluded" in _m10_forged_text
       and "EXCLUDED UNBACKED_EVENT incident INC-FORGED" in _m10_forged_text)
expect("WARP-1210 AC2: EVERY measure line carries the authenticated population beside it, so no number can be read without its evidence base",
       len(_m10_measure_lines) == 4 and all("of 2 authenticated" in _l for _l in _m10_measure_lines)
       and "of 2 authenticated" in [_l for _l in _m10_forged_text.splitlines()
                                    if "incident(s) of" in _l and "metrics:" in _l][0])
# AC2 THE WIRED PATH over a REAL tree: the receipt is settled by the SHIPPED store and read back by the
# reader, which BINDS the reader's path literal to FilesystemReconciliationStore's own location.
_M10_WIRED_INCIDENT = GOOD_INCIDENT.replace(
    "  diagnosed_at: 2026-07-23T02:31:00Z\n",
    "  diagnosed_at: 2026-07-23T02:31:00Z\n  restored_at: 2026-07-23T03:14:00Z\n")
with tempfile.TemporaryDirectory() as _m10d:
    _m10r = Path(_m10d)
    (_m10r / ".veldo" / "incidents").mkdir(parents=True)
    (_m10r / ".veldo" / "incidents" / "INC-FIX.yaml").write_text(_M10_WIRED_INCIDENT)
    _m10_wired_res, _m10_wired_store = _ir_go(store=IR.FilesystemReconciliationStore(_m10r))
    _m10_wired_events = [json.loads(_l) for _l in
                         (_m10r / ".veldo" / "events.jsonl").read_text().splitlines() if _l.strip()]
    _m10_wired = S10.support_numbers(
        _m10_wired_events, **R10.load_support_inputs(root=_m10r, events=_m10_wired_events))
    expect("WARP-1210 AC2 WIRED: an incident SETTLED through the shipped reconciliation (its receipt and its incident.closed both written by the store) is AUTHENTICATED end to end by the wired readers",
           _m10_wired_res["outcome"] == IR.OUTCOME_SETTLED and _m10_wired["closed_events"] == 1
           and _m10_wired["authenticated"] == ["INC-FIX"] and _m10_wired["excluded"] == []
           and _m10_wired["records_read"] == 1 and _m10_wired["receipts_read"] == 1)
    expect("WARP-1210 AC2 WIRED: load_receipts reads the receipt the SHIPPED store settled, which BINDS the reader's path literal to FilesystemReconciliationStore's own location (the store exposes no constant to read)",
           [_r["id"] for _r in R10.load_receipts(_m10r)[0]] == [_m10_wired_res["receipt_id"]]
           and [_r["id"] for _r in R10.load_incidents(_m10r)[0]] == ["INC-FIX"]
           and R10.load_receipts(_m10r)[1] == [] and R10.load_incidents(_m10r)[1] == [])
    expect("WARP-1210 AC2 WIRED: the measures are the RECORDED timeline's (17 minutes to diagnosis, 60 to restore) and the diagnosability score is an HONEST ZERO over a real population, because this record resolves to no spec and no area",
           _m10_wired["time_to_diagnosis"]["observations"] == [{"incident": "INC-FIX", "hours": 0.28}]
           and _m10_wired["time_to_restore"]["observations"] == [{"incident": "INC-FIX", "hours": 1.0}]
           and _m10_wired["diagnosability_score"]["percent"] == 0.0
           and _m10_wired["diagnosability_score"]["denominator"] == 1
           and _m10_wired["recurrence_rate"]["percent"] == 0.0)
    for _m10_p in sorted((_m10r / ".veldo" / "reconciliations").glob("*.json")):
        _m10_p.unlink()
    _m10_stripped = S10.support_numbers(
        _m10_wired_events, **R10.load_support_inputs(root=_m10r, events=_m10_wired_events))
    expect("WARP-1210 AC2 WIRED: with the RECEIPT STORE EMPTIED the very same stream counts NOTHING and names the exclusion, so the numbers rest on the receipts and not on the events",
           _m10_stripped["authenticated"] == [] and _m10_stripped["closed_events"] == 1
           and [(_x["reason"], _x["incident"]) for _x in _m10_stripped["excluded"]]
           == [(C10.SUPPORT_UNBACKED_EVENT, "INC-FIX")]
           and _m10_stripped["time_to_diagnosis"]["standdown"] == C10.SUPPORT_EMPTY_DENOMINATOR)
    (_m10r / ".veldo" / "reconciliations" / "REC-corrupt.json").write_text('{"schema": "veldo.reconcil')
    _m10_corrupt = S10.support_numbers(
        _m10_wired_events, **R10.load_support_inputs(root=_m10r, events=_m10_wired_events))
    expect("WARP-1210 AC2 WIRED: a receipt file that cannot be READ is not passed to the derivation, so its incident is reported as UNBACKED_EVENT rather than counted on a record nobody can read (fail closed) - and the UNREADABLE FILE is now NAMED beside it (UNREADABLE_RECEIPT_FILE), because an unbacked event alone says no receipt was ever written, which is a different fact",
           R10.load_receipts(_m10r)[0] == []
           and [(_x["reason"], _x["incident"]) for _x in _m10_corrupt["excluded"]]
           == [(C10.SUPPORT_UNBACKED_EVENT, "INC-FIX")]
           and [(_x["reason"], _x["source"], _x["subject"]) for _x in _m10_corrupt["source_problems"]]
           == [(C10.SUPPORT_UNREADABLE_RECEIPT_FILE, "receipt_store", "REC-corrupt.json")]
           and "UNREADABLE SOURCE UNREADABLE_RECEIPT_FILE source receipt_store (REC-corrupt.json)"
           in "\n".join(RPT10.support_lines(_m10_corrupt))
           and _m10_stripped["source_problems"] == []
           and _M10_SWEPT_SOURCES.setdefault("receipt_store", C10.SUPPORT_UNREADABLE_RECEIPT_FILE))

# AC3 INCIDENTS-PER-AREA IS A SOFT JOIN THAT NEVER FAKES ITSELF (C7), proven over temporary trees.
_M10_ARCH = """schema: veldo.arch/v1
id: t
title: the seeded shape
version: 1
status: approved
approved_by: dmitry
approved_at: 2026-07-22
areas:
  - id: core
    title: core
    includes: [".veldo/core.py"]
"""
_M10_SPEC_FILE = """---
schema: veldo.spec/v1
id: VELDO-T210
title: a seeded spec that declares a placement
status: shipped
risk: standard
owner: selftest
placement: [core]
footprint:
  - .veldo/core.py
acceptance_criteria:
  - id: AC1
    text: something observable happens.
required_evidence: [unit]
rollback: git revert
---
body
"""


def _m10_tree_seed(root, contract=True, shipped=True):
    """A temporary repository: the incident record, the reconciliation receipt on disk, a spec that
    declares a placement, and optionally the architecture contract and a shipped change carrying the
    recorded cost. Returns the recorded events."""
    (root / ".veldo" / "incidents").mkdir(parents=True)
    (root / ".veldo" / "reconciliations").mkdir(parents=True)
    (root / "specs").mkdir()
    if contract:
        (root / ".veldo" / "architecture.yaml").write_text(_M10_ARCH)
    (root / "specs" / "VELDO-T210-seed.md").write_text(_M10_SPEC_FILE)
    (root / ".veldo" / "incidents" / "INC-T.yaml").write_text(
        _m10_record_text("INC-T", "2026-07-24T02:00:00Z", restored="2026-07-24T03:30:00Z",
                         spec="VELDO-T210"))
    # The PRIOR incident INC-T's receipt names a recurrence of: a RECORD on disk with no close event and
    # no receipt of its own, which is exactly what an earlier incident looks like AND exactly what any
    # writer inside .veldo/ can drop in. Rounds 3 to 5 resolved the reference against it and rendered a 100
    # percent recurrence rate; round 6 does not, because nothing AUTHENTICATES it - the reference is NAMED
    # with what it landed on and the record-only population is reported beside the rate.
    (root / ".veldo" / "incidents" / "INC-PRIOR.yaml").write_text(
        _m10_record_text("INC-PRIOR", "2026-07-20T02:00:00Z", spec="VELDO-T210"))
    (root / ".veldo" / "reconciliations" / "REC-T.json").write_text(
        json.dumps(_m10_receipt("INC-T", recurrence=["INC-PRIOR"])))
    events = [_m10_event("INC-T")]
    if shipped:
        events.insert(0, {"schema": "veldo.event/v1", "type": "spec.shipped", "producer": "selftest",
                          "at": "2026-07-23T00:00:00Z", "correlation_id": "VELDO-T210",
                          "human_minutes": 25, "tokens": 400})
    return events


_m10_paths = {}
for _m10_label, _m10_contract, _m10_shipped in (("join", True, True), ("no cost data", True, False),
                                               ("no contract", False, True)):
    with tempfile.TemporaryDirectory() as _m10d:
        _m10r = Path(_m10d)
        _m10_ev = _m10_tree_seed(_m10r, contract=_m10_contract, shipped=_m10_shipped)
        _m10_in = R10.load_support_inputs(root=_m10r, events=_m10_ev)
        _m10_model = S10.support_numbers(_m10_ev, **_m10_in)
        _m10_paths[_m10_label] = (_m10_model, _m10_in, "\n".join(RPT10.support_lines(_m10_model)))
_m10_join, _m10_join_in, _m10_join_text = _m10_paths["join"]
_m10_nocost, _m10_nocost_in, _m10_nocost_text = _m10_paths["no cost data"]
_m10_nocontract, _m10_nocontract_in, _m10_nocontract_text = _m10_paths["no contract"]
expect("WARP-1210 AC3: with a CONTRACT and SEEDED COST DATA the map JOINS and BOTH columns appear - the incident count per declared area and PLAN-0011's recorded cost-to-change beside it",
       _m10_join["incidents_per_area"]["standdown"] is None
       and _m10_join["incidents_per_area"]["areas"] == [
           {"area": "core", "incidents": 1, "incident_ids": ["INC-T"], "cost_standdown": None,
            "cost": {"samples": 1, "latest": {"human_minutes": 25, "tokens": 400, "cost_usd": 0.0,
                                              "review_cycles": 0, "gate_failures": 0}}}]
       and "core: 1 incident(s) of 1 authenticated; cost-to-change 1 sample(s), latest human_minutes=25"
       in _m10_join_text)
expect("WARP-1210 AC3: the attribution is the record's affected_spec resolved to that SPEC'S PLACEMENT (the PLAN-0011 join key), read through the shipped index rather than restated",
       _m10_join_in["spec_areas"] == {"VELDO-T210": ["core"]}
       and _m10_join_in["contract_areas"] == ["core"]
       and _m10_join_in["area_cost"]["core"]["samples"] == 1)
expect("WARP-1210 AC3: with a CONTRACT but NO COST DATA the incident column renders and the COST column STANDS DOWN BY NAME (NO_AREA_COST_DATA), never as a zero cost",
       _m10_nocost_in["area_cost"] == {} and _m10_nocost["incidents_per_area"]["standdown"] is None
       and _m10_nocost["incidents_per_area"]["areas"][0]["incidents"] == 1
       and _m10_nocost["incidents_per_area"]["areas"][0]["cost"] is None
       and _m10_nocost["incidents_per_area"]["areas"][0]["cost_standdown"]
       == C10.SUPPORT_NO_AREA_COST_DATA
       and "core: 1 incident(s) of 1 authenticated; cost-to-change STANDING DOWN (NO_AREA_COST_DATA)"
       in _m10_nocost_text)
expect("WARP-1210 AC3: with NO CONTRACT AT ALL the whole join STANDS DOWN BY NAME (NO_ARCHITECTURE_CONTRACT) and NOTHING ELSE CHANGES - the four measures are byte-identical to the with-contract run",
       _m10_nocontract_in["contract_areas"] is None
       and _m10_nocontract["incidents_per_area"]["standdown"] == C10.SUPPORT_NO_ARCHITECTURE_CONTRACT
       and "STANDING DOWN (NO_ARCHITECTURE_CONTRACT)" in _m10_nocontract_text
       and all(json.dumps(_m10_nocontract[_k], sort_keys=True)
               == json.dumps(_m10_nocost[_k], sort_keys=True)
               for _k in ("time_to_diagnosis", "time_to_restore", "recurrence_rate",
                          "diagnosability_score", "authenticated", "excluded")))
expect("WARP-1210 AC3: an area the contract does NOT declare is never INVENTED, and a record that declares one is never silently reassigned to a different area (it is unattributable instead)",
       S10.incident_corpus_resolution(_m10_record("INC-X", spec="WARP-1210", area="an-undeclared-area"),
                                      _M10_SPEC_AREAS, _M10_AREAS)["areas"] == []
       and S10.incident_corpus_resolution(_m10_record("INC-X", spec="WARP-1210"),
                                          _M10_SPEC_AREAS, _M10_AREAS)["areas"] == ["metrics"]
       and S10.incident_corpus_resolution(_m10_record("INC-X", spec=None, area="contracts"),
                                          _M10_SPEC_AREAS, _M10_AREAS)["areas"] == ["contracts"])
_m10_unattr = _m10_go(incidents=[_M10_RECORDS[0], _m10_record("INC-B", spec=None, area="nowhere")])
expect("WARP-1210 AC3: an UNATTRIBUTABLE incident is listed BY ID and never assigned to a default area, and the attributed count is honest",
       _m10_unattr["incidents_per_area"]["unattributed"] == ["INC-B"]
       and _m10_unattr["incidents_per_area"]["attributed"] == 1
       and [_r["incident_ids"] for _r in _m10_unattr["incidents_per_area"]["areas"]] == [["INC-A"]]
       and "unattributed (never assigned to a default area): INC-B"
       in "\n".join(RPT10.support_lines(_m10_unattr)))
expect("WARP-1210 AC3: with a contract but NO ATTRIBUTABLE INCIDENT the map stands down (EMPTY_DENOMINATOR) rather than inventing a row",
       _m10_go(incidents=[_m10_record("INC-A", spec=None), _m10_record("INC-B", spec=None)]
               )["incidents_per_area"]["standdown"] == C10.SUPPORT_EMPTY_DENOMINATOR)
expect("WARP-1210 AC3: a cross-cutting incident attributed to two declared areas appears on BOTH rows and is counted once in the population",
       [(_r["area"], _r["incidents"]) for _r in _m10_go(
           spec_areas={"WARP-1210": ["contracts", "metrics"]},
           incidents=[_M10_RECORDS[0]])["incidents_per_area"]["areas"]]
       == [("contracts", 1), ("metrics", 1)])
# AC3 THIS REPOSITORY'S REAL STATE, asserted honestly rather than assumed.
_m10_real_events = ME.load()
_m10_real_in = R10.load_support_inputs(root=ROOT, events=_m10_real_events)
_m10_real = S10.support_numbers(_m10_real_events, **_m10_real_in)
expect("WARP-1210 AC3 REAL STATE: this repository declares an architecture contract and its corpus resolves, so the CONTRACT half of the join is live here (the areas are read, not assumed)",
       _m10_real_in["contract_areas"] == sorted(ARCH.area_ids(_SG_REAL))
       and "metrics" in _m10_real_in["contract_areas"]
       and _m10_real_in["spec_areas"].get("WARP-1210") == ["metrics"])
expect("WARP-1210 AC3 REAL STATE: this repository's committed stream carries NO recorded per-area cost sample and NO incident lifecycle event, so the cost column stands down by name and the section is the honest EMPTY STATE - asserted, not assumed",
       # BRANCHED ON WHAT IT MEASURED, NEVER PINNED TO TODAY'S EMPTINESS (VELDO-0001 class, and the
       # first-use gate check found this instance after four sibling suites had been defused). The
       # earlier form asserted area_cost == {} as a REQUIRED invariant, so recording one spend through
       # the sanctioned writer, which is the whole point of the estimation layer, reddened the required
       # gate. The teeth are kept and are now the harder claim: whichever branch this tree is in, the
       # cost column and the stand-down code must AGREE with each other, so a stand-down printed
       # alongside real data is still caught, and so is data reported with no stand-down cleared.
       (_m10_real["closed_events"] == 0 and _m10_real["receipts_read"] == 0
        and RPT10.support_empty(_m10_real) is True)
       and ((_m10_real_in["area_cost"] == {}
             and _m10_real["incidents_per_area"]["cost_standdown"] == C10.SUPPORT_NO_AREA_COST_DATA)
            or (_m10_real_in["area_cost"] != {}
                and _m10_real["incidents_per_area"]["cost_standdown"] is None)))
expect("WARP-1210 AC3 REAL STATE: the rendered section here is ONE honest empty-state line, not a row of zeros and not an error - and NOTHING was skipped on this tree (every entry of every store this repository has is a record), so read_skipped is empty and the section is byte-identical to what it rendered before the skipped entries were surfaced",
       [_l.strip() for _l in RPT10.support_lines(_m10_real)][1:]
       == ["no incident lifecycle event and no reconciliation receipt recorded: standing down as an "
           "honest empty state, not a row of zeros (adoption safe)"]
       and _m10_real["read_skipped"] == []
       and all(_r.get("skipped") == [] for _r in _m10_real_in["source_reads"]))

# AC4 HONEST DENOMINATORS AND NO INVENTED PRECISION.
_m10_empty = _m10_go(receipts=[])
_m10_empty_text = "\n".join(RPT10.support_lines(_m10_empty))
for _m10_k, _m10_label in (("recurrence_rate", "recurrence rate"),
                           ("diagnosability_score", "diagnosability score")):
    expect("WARP-1210 AC4: the %s over an EMPTY population stands down as EMPTY_DENOMINATOR and renders NEITHER 0 percent, NOR 100 percent, NOR a dash that reads as a value" % _m10_label,
           _m10_empty[_m10_k]["standdown"] == C10.SUPPORT_EMPTY_DENOMINATOR
           and _m10_empty[_m10_k]["rate"] is None and _m10_empty[_m10_k]["percent"] is None
           and _m10_empty[_m10_k]["denominator"] == 0
           and "%s: STANDING DOWN (EMPTY_DENOMINATOR)" % _m10_label in _m10_empty_text)
expect("WARP-1210 AC4: the rendered stand-downs carry NO percentage at all - no 0%, no 100%, no bare dash, no n/a - so nothing on those lines can be misread as a measurement",
       not any(_t in _m10_empty_text for _t in ("0%", "100%", "0.0", ": -", "n/a"))
       and "a rate with no population is not a rate" in _m10_empty_text)
_m10_single = _m10_go(events=[_m10_event("INC-A")], receipts=[_m10_receipt("INC-A")])
_m10_single_text = "\n".join(RPT10.support_lines(_m10_single))
_m10_norecords = _m10_go(incidents=[])
for _m10_k, _m10_label in (("time_to_diagnosis", "time-to-diagnosis"),
                           ("time_to_restore", "time-to-restore")):
    expect("WARP-1210 AC4: a %s with ONE data point is reported as a SINGLE OBSERVATION and not as a trend direction" % _m10_label,
           _m10_single[_m10_k]["samples"] == 1
           and _m10_single[_m10_k]["reading"] == "single observation"
           and _m10_ok[_m10_k]["reading"] == "trend over 2 observations"
           and "[single observation]" in _m10_single_text)
    expect("WARP-1210 AC4: a %s with NO data point stands down by name rather than reporting a median of nothing" % _m10_label,
           _m10_norecords[_m10_k]["standdown"] == C10.SUPPORT_EMPTY_DENOMINATOR
           and _m10_norecords[_m10_k]["median"] is None and _m10_norecords[_m10_k]["latest"] is None)
_m10_onerecord = _m10_go(incidents=[_M10_RECORDS[0]])
expect("WARP-1210 AC4: an authenticated incident whose RECORD is absent contributes NO observation, and the samples-versus-population count makes the gap visible rather than hiding it",
       _m10_onerecord["time_to_diagnosis"]["samples"] == 1
       and _m10_onerecord["time_to_diagnosis"]["population"] == 2
       and "over 1 observation(s) of 2 authenticated incident(s)"
       in "\n".join(RPT10.support_lines(_m10_onerecord)))
expect("WARP-1210 AC4: EVERY share carries its numerator and its denominator beside it, so 100 percent over one incident reads as ONE INCIDENT",
       all({"numerator", "denominator", "of"} <= set(_m10_single[_k])
           for _k in ("recurrence_rate", "diagnosability_score"))
       and "diagnosability score: 100.0% (1 of 1 authenticated closed incident(s)" in _m10_single_text)
expect("WARP-1210 AC4: ROUNDING is DECLARED once and applied consistently (hours to 2 decimals, a rate to 3, a percent to 1), and no measure is presented to a precision its input does not support",
       C10.SUPPORT_ROUNDING == {"hours": 2, "rate": 3, "percent": 1}
       and S10.support_share(["a"], ["a", "b", "c"], "x")["rate"] == 0.333
       and S10.support_share(["a"], ["a", "b", "c"], "x")["percent"] == 33.3
       and S10.support_trend(["A"], {"A": _m10_record("A", diagnosed="2026-07-24T00:00:37Z")},
                             "diagnosed_at")["observations"][0]["hours"] == 0.01)
expect("WARP-1210 AC4: an absent or unreadable timestamp yields NO observation rather than a zero, and a NEGATIVE interval is dropped rather than counted (a negative time-to-diagnosis is a corrupt measure)",
       S10._incident_hours({"timeline": {"opened_at": "2026-07-24T00:00:00Z"}}, "restored_at") is None
       and S10._incident_hours({"timeline": {"opened_at": "not a date",
                                             "diagnosed_at": "2026-07-24T01:00:00Z"}},
                               "diagnosed_at") is None
       and S10._incident_hours({"timeline": {"opened_at": "2026-07-24T05:00:00Z",
                                             "diagnosed_at": "2026-07-24T01:00:00Z"}},
                               "diagnosed_at") is None
       and S10._incident_hours("not a record", "diagnosed_at") is None)
expect("WARP-1210 AC4: the exclusion and stand-down reasons are a CLOSED named set - TWENTY-FIVE names after the round-5 change of approach (eight after round 1, ELEVEN more after round 2 because each was a real input class being handled SILENTLY, and SIX more now: the ONE name a source carries when it cannot PROVE it read completely, plus the five sources round 4 found declared NOWHERE - the recorded event stream and the four sibling OWNER MODULES the readers execute) - the exact tuple is pinned, no name can be added without declaring it, every reason this suite exercised is in it, and the closure holds across BOTH the contract that OWNS the names and the derivation that re-exports the ones it uses, so neither module can introduce a name of its own",
       C10.SUPPORT_REASONS == ("UNBACKED_EVENT", "UNRESOLVED_RECEIPT", "CONFLICTING_RECEIPTS",
                              "CONFLICTING_RECORDS", "UNRESOLVED_RECURRENCE", "UNUSABLE_INTERVAL",
                              "UNREADABLE_TIMESTAMP", "EMPTY_DENOMINATOR", "NO_AREA_COST_DATA",
                              "UNREADABLE_AREA_COST_DATA", "NO_ARCHITECTURE_CONTRACT",
                              "UNREADABLE_ARCHITECTURE_CONTRACT", "NO_SPEC_CORPUS",
                              "UNREADABLE_SPEC_CORPUS", "UNREADABLE_SPEC_AREA_INDEX",
                              "UNREADABLE_RECEIPT_FILE", "UNREADABLE_INCIDENT_RECORD",
                              "UNREADABLE_INCIDENT_VOCABULARY", "UNREADABLE_INPUT_SOURCE",
                              "INCOMPLETE_READ", "UNREADABLE_EVENT_STREAM",
                              "UNREADABLE_INCIDENT_CONTRACT_OWNER", "UNREADABLE_FRONT_MATTER_PARSER",
                              "UNREADABLE_INTENT_CORPUS_OWNER", "UNREADABLE_ENTROPY_OWNER")
       and len(C10.SUPPORT_REASONS) == 25 and len(set(C10.SUPPORT_REASONS)) == 25
       # the derivation RE-EXPORTS the owner's names rather than restating them: equal by value, and
       # bound in the source to the contract module, so a name cannot be forked by editing one module.
       and S10.SUPPORT_REASONS == C10.SUPPORT_REASONS
       and "SUPPORT_REASONS = _contract.SUPPORT_REASONS" in _m10_sup_src
       and set(C10.SUPPORT_REASONS) == {_v for _m in (C10, S10) for _k, _v in vars(_m).items()
                                        if _k.startswith("SUPPORT_") and isinstance(_v, str)
                                        and _v.isupper()}
       # the completeness TOKEN is deliberately NOT an uppercase reason word: a truthy flag or a bare word
       # is what an incomplete read carries by accident, and a versioned token only appears on purpose.
       and C10.SUPPORT_READ_COMPLETE == "support.read.complete/v1"
       and not C10.SUPPORT_READ_COMPLETE.isupper()
       and C10.SUPPORT_READ_COMPLETE not in C10.SUPPORT_REASONS)

# --- WARP-0625 (W10 of PLAN-0016): the live changelog normalization -----------------------------
_ta625spec = importlib.util.spec_from_file_location("veldo_tracker_adapter_625",
                                                    ROOT / ".veldo/tracker_adapter.py")
TA625 = importlib.util.module_from_spec(_ta625spec); _ta625spec.loader.exec_module(TA625)

# THE FIXTURE IS THE REAL RUN'S IDENTITIES AND TIMESTAMPS, nested back into Jira's payload shape as
# the WARP-0620 run record describes it (values[].author.displayName, items[].fromString). HONEST
# LIMIT: the run captured the NORMALIZED output, not the raw payload, so this reconstructs the
# nesting rather than replaying a recorded body. What it therefore proves is the flattening,
# filtering and ordering logic - not that Jira's wire format is exactly this.
_W625_RAW = {"values": [
    {"id": "31205", "created": "2026-07-24T20:30:34.329-0400",
     "author": {"displayName": "Dmitry Grinberg", "accountType": "atlassian",
                "accountId": "712020:fbf897f7"},
     "items": [{"field": "status", "fromString": "Needs Decision", "toString": "Approved"},
               {"field": "assignee", "fromString": None, "toString": "someone"}]},
    {"id": "31204", "created": "2026-07-24T20:28:12.074-0400",
     "author": {"displayName": "Veldo Agent", "accountType": "app",
                "accountId": "712020:591c1515"},
     "items": [{"field": "status", "fromString": "To Do", "toString": "Needs Decision"}]},
]}
_w625 = TA625.normalize_changelog(_W625_RAW)

expect("WARP-0625: the nested payload flattens to the shape every shipped accessor reads",
       [r["from"] for r in _w625] == ["To Do", "Needs Decision"]
       and [r["to"] for r in _w625] == ["Needs Decision", "Approved"]
       and all(set(TA625.FLAT_FIELDS) <= set(r) for r in _w625))
# ORDER IS THE PROPERTY THE RECONCILE RESTS ON: the terminal decision is the LAST accepting
# transition, so an endpoint returning newest-first must not invert the derivation.
expect("WARP-0625: entries are ordered by WHEN THEY HAPPENED even though the payload arrived newest-first",
       [r["id"] for r in _w625] == ["31204", "31205"])
# ONE ENTRY, SEVERAL ITEMS: the assignee change in the same entry is not a transition and must not
# become one, and dropping it must not drop the status item beside it.
expect("WARP-0625: a non-status item in the same entry is EXCLUDED, and the status item beside it survives",
       len(_w625) == 2 and all(r["to"] in ("Needs Decision", "Approved") for r in _w625))
# THE ACTOR KIND COMES FROM THE TRACKER (WARP-0624), on the real identities the live run captured.
expect("WARP-0625: the actor kind is the tracker's own accountType, so the real 'Veldo Agent' reads machine and the human reads human",
       [r["actor_kind"] for r in _w625] == ["machine", "human"]
       and [r["actor"] for r in _w625] == ["Veldo Agent", "Dmitry Grinberg"])
# IT MATCHES THE EVIDENCE THE LIVE RUN ACTUALLY RECORDED, field by field on what both carry.
_w625_captured = json.loads((ROOT / "proof/WARP-0620/te1-changelog-raw.json").read_text())["entries"]
expect("WARP-0625: the normalization reproduces the live run's recorded records on every field both carry",
       [{k: r[k] for k in ("id", "at", "actor", "from", "to")} for r in _w625]
       == [{k: e[k] for k in ("id", "at", "actor", "from", "to")} for e in _w625_captured])
# MALFORMED HISTORY IS SKIPPED, NOT FATAL: one unreadable entry must not make a history unreadable.
expect("WARP-0625: junk entries are skipped rather than raising, and a good entry beside them still lands",
       len(TA625.normalize_changelog({"values": [None, 7, {"items": "nope"},
                                                 _W625_RAW["values"][1]]})) == 1)
expect("WARP-0625: an empty or absent payload is an empty history, not an error",
       TA625.normalize_changelog({}) == [] and TA625.normalize_changelog(None) == [])

# --- WARP-0625 part two: the live FETCH, driven through an injected transport ------------------
_jl625spec = importlib.util.spec_from_file_location("veldo_jira_live_625",
                                                    ROOT / ".veldo/tracker_jira_live.py")
JL625 = importlib.util.module_from_spec(_jl625spec); _jl625spec.loader.exec_module(JL625)


def _w625_pages(pages):
    """A fake `request` returning canned pages in order, recording the paths it was asked for."""
    seen = []

    def request(method, path):
        seen.append(path)
        return pages[min(len(seen) - 1, len(pages) - 1)]
    return request, seen


def _w625_entry(i, actor, kind, frm, to, day):
    return {"id": str(i), "created": "2026-01-%02dT00:00:00-0400" % day,
            "author": {"displayName": actor, "accountType": kind},
            "items": [{"field": "status", "fromString": frm, "toString": to}]}


# PAGING IS THE POINT: Jira returns 100 at a time and a truncated changelog does not error, it
# quietly loses the EARLIEST transitions - exactly the ones the opening-actor derivation reads.
_w625_req, _w625_seen = _w625_pages([
    {"values": [_w625_entry(1, "Veldo Agent", "app", "A", "B", 1)], "isLast": False},
    {"values": [_w625_entry(2, "Dmitry Grinberg", "atlassian", "B", "C", 2)], "isLast": True},
])
_w625_fetched = JL625.fetch_changelog(_w625_req, "TE1-1")
expect("WARP-0625: the fetch PAGES and accumulates - a two-page history returns both entries, not just the last page",
       len(_w625_fetched) == 2 and [r["id"] for r in _w625_fetched] == ["1", "2"])
expect("WARP-0625: paging advances startAt by what was actually received rather than assuming a full page",
       len(_w625_seen) == 2 and "startAt=0" in _w625_seen[0] and "startAt=1" in _w625_seen[1])
expect("WARP-0625: the fetch feeds the ONE normalizer, so the records come back flat with the tracker-reported kind",
       [r["actor_kind"] for r in _w625_fetched] == ["machine", "human"])
# It must stop. A malformed isLast that never arrives is a hang, so emptiness is the backstop.
_w625_req2, _w625_seen2 = _w625_pages([{"values": []}])
expect("WARP-0625: an empty page stops the loop even when the server never says isLast (no hang on a malformed response)",
       JL625.fetch_changelog(_w625_req2, "TE1-1") == [] and len(_w625_seen2) == 1)
_w625_req3, _w625_seen3 = _w625_pages([{"values": [_w625_entry(9, "x", "app", "A", "B", 1)]}])
expect("WARP-0625: a server that never sets isLast is bounded by a page cap rather than spinning forever",
       len(JL625.fetch_changelog(_w625_req3, "TE1-1")) <= JL625.CHANGELOG_MAX_PAGES
       and len(_w625_seen3) == JL625.CHANGELOG_MAX_PAGES)
# The fetch does not own a transport, which is what makes all of the above testable at all.
expect("WARP-0625: the fetch takes the caller's request callable and opens no socket of its own",
       not any(t in (ROOT / ".veldo/tracker_jira_live.py").read_text()
               for t in ("urllib.request.urlopen(", "socket.create_connection", "requests.get(")))

# --- WARP-0622 AC1-AC3: the structural no-bypass check ----------------------------------------
_nbspec = importlib.util.spec_from_file_location("veldo_no_bypass", ROOT / ".veldo/no_bypass.py")
NB = importlib.util.module_from_spec(_nbspec); _nbspec.loader.exec_module(NB)

# AC1: the real surface is clean TODAY, which is the property the check exists to keep true.
expect("WARP-0622 AC1: no module in the decision surface reads a human decision from a terminal",
       NB.check() == [] and len(NB.DECISION_SURFACE) == 11)
# ... and a surface naming a module that does not exist reports itself, so deleting one cannot
# silently shrink what is checked - the roster-empties defect in another costume.
expect("WARP-0622 AC1: a surface entry with no module behind it is REPORTED, so the roster cannot silently shrink",
       [p[0] for p in NB.check(surface=("definitely_not_here.py",))] == ["definitely_not_here.py"])

# AC2: IT PARSES. Every spelling that must be caught, and every lookalike that must stay clean, so
# the check can be neither blind nor hysterical. A grep would fail at least three of these.
_NB_CAUGHT = {
    "bare input": 'x = input("approve? ")',
    "raw_input": "x = raw_input()",
    "getpass": "import getpass\ny = getpass.getpass()",
    "stdin.readline": "import sys\nz = sys.stdin.readline()",
    "stdin.read": "import sys\nz = sys.stdin.read()",
    "builtins.input": "import builtins\nw = builtins.input()",
}
_NB_CLEAN = {
    "the word in a comment": "# input() is forbidden here\nx = 1",
    "the word in a string": 's = "call input() to fail"',
    "a lookalike function name": "def n_inputs(a):\n    return a",
    "an attribute that merely ends in read": "class C:\n    def read(self):\n        return 1\nC().read()",
}
expect("WARP-0622 AC2: EVERY spelling of a terminal read is caught, including the ones a grep for 'input(' misses",
       all(NB.terminal_reads(src) != [] for src in _NB_CAUGHT.values())
       and len(_NB_CAUGHT) == 6)
expect("WARP-0622 AC2 control: prose, strings and lookalike names stay CLEAN, so the check is not hysterical",
       all(NB.terminal_reads(src) == [] for src in _NB_CLEAN.values())
       and len(_NB_CLEAN) == 4)
expect("WARP-0622 AC2: a module that will not parse is reported as UNVERIFIABLE rather than passed",
       any("unparseable" in w for _l, w in NB.terminal_reads("def f(:")))
expect("WARP-0622 AC2: the report names the module, the line and what it found, so an operator does not go reading code",
       "terminal read" in NB.report([("m.py", 4, "input()")])[0]
       and "m.py:4" in NB.report([("m.py", 4, "input()")])[0])

# AC3: the limit is in the module, so nobody upgrades the claim later.
_nb_doc = " ".join((NB.__doc__ or "").lower().split())
expect("WARP-0622 AC3: the module states what it CANNOT prove, so the claim cannot be quietly widened",
       "cannot prove a human decision did not reach the system some other way" in _nb_doc
       and "environment variable" in _nb_doc)

# --- WARP-0622 AC4: END-TO-END CONFORMANCE over the fake tracker --------------------------------
# Nine scenarios the plan names, each driven through the REAL reconcile with the REAL harness above,
# each with a CONTROL beside it so a refusal is attributable to the scenario and not to a checker
# that refuses everything. Nothing here is a parallel mock: same reconcile_requests, same
# FakeTracker, same FakeSettlementStore, same policy and registry as every assertion before it.
#
# WHAT THESE PROVE AND WHAT THEY DO NOT. Every path is offline over a deterministic fake. They prove
# the DECISION LOGIC holds under each hostile condition; they cannot prove a live tracker behaves
# the way the fake does. That is what the human-run live proof is for, and it is why WARP-0622 stays
# `ready` until WARP-0620's board run happens.

def _e2e_outcome(res, rid="REQ"):
    """The per-request outcome. Keyed on `request`, which is what the reconcile actually returns."""
    return next((r["outcome"] for r in res["results"] if r.get("request") == rid), None)


def _e2e_receipts(store):
    return store.count() if callable(getattr(store, "count", None)) else len(store.receipts())


# S1 REPLAY. The same decided request reconciled twice settles ONCE; the second pass is
# already_applied, not a second receipt. A replayed approval must not buy a second settlement.
_e2e_store = RR.FakeSettlementStore()
_e2e_first, _, _ = _rr_run(_rr_req(), _rr_valid_log, store=_e2e_store)
_e2e_second, _, _ = _rr_run(_rr_req(), _rr_valid_log, store=_e2e_store)
expect("WARP-0622 S1 REPLAY: the first pass settles and the SECOND is already_applied - a replayed approval buys no second receipt",
       _e2e_outcome(_e2e_first) == "settled" and _e2e_outcome(_e2e_second) == "already_applied"
       and _e2e_receipts(_e2e_store) == 1)
expect("WARP-0622 S1 control: a DIFFERENT request against the same store settles on its own receipt, so the store is not simply refusing everything after the first",
       _e2e_outcome(_rr_run(_rr_req(rid="REQ2", issue="VEL-2"), _rr_valid_log,
                            store=_e2e_store)[0], "REQ2") == "settled"
       and _e2e_receipts(_e2e_store) == 2)

# S2 SPOOFED ACTOR. The identity comes from the CHANGELOG, never from a field on the request. A
# record naming a decider it was not decided by changes nothing.
_e2e_spoof = _rr_req()
_e2e_spoof["decided_by"] = "alice"                      # the lie, on the record itself
_e2e_spoof_res, _, _ = _rr_run(_e2e_spoof, _rr_log([("c1", "builder", None, "Needs Decision"),
                                                    ("c2", "mallory", "Needs Decision", "Approved")]))
expect("WARP-0622 S2 SPOOFED ACTOR: a request CLAIMING alice decided it is held when the changelog says mallory - identity is read from the tracker's history, never from a field the requester wrote",
       _e2e_outcome(_e2e_spoof_res) == "held")
expect("WARP-0622 S2 control: the same record with alice ACTUALLY in the changelog settles, so the refusal is the spoof and not the extra field",
       _e2e_outcome(_rr_run(_e2e_spoof, _rr_valid_log)[0]) == "settled")

# S3 AUTOMATION TRANSITIONS. A transition made by the agent itself is not a human decision.
_e2e_auto, _, _ = _rr_run(_rr_req(), _rr_agent_log)
expect("WARP-0622 S3 AUTOMATION: a terminal transition made by the AGENT is held - the machine moving a ticket to Approved is not a human deciding",
       _e2e_outcome(_e2e_auto) == "held")
expect("WARP-0622 S3 control: the same transition made by a human settles",
       _e2e_outcome(_rr_run(_rr_req(), _rr_valid_log)[0]) == "settled")
expect("WARP-0622 S3: SELF-APPROVAL is held too - the actor who opened the request cannot be the actor who decided it",
       _e2e_outcome(_rr_run(_rr_req(), _rr_self_log)[0]) == "held")

# S4 WORKFLOW EDITS. Someone renames a board state so the terminal transition lands somewhere the
# repository does not recognise. That must HOLD, never settle on a guess.
_e2e_renamed = _rr_log([("c1", "builder", None, "Needs Decision"),
                        ("c2", "alice", "Needs Decision", "Signed Off")])
_e2e_renamed_res, _, _ = _rr_run(_rr_req(), _e2e_renamed)
expect("WARP-0622 S4 WORKFLOW EDIT: a board state the repository does not recognise SETTLES NOTHING rather than being guessed into acceptance - the safety property holds",
       _e2e_outcome(_e2e_renamed_res) == "skipped" and _e2e_renamed_res["settled"] == [])
# WHAT THIS SCENARIO FOUND, and the fix it produced. The outcome was always SAFE, but the REASON was
# identical to a genuinely pending request's, so an operator would wait for a decision that had
# already happened instead of fixing the state vocabulary. The pending branch now NAMES the states
# the ticket actually moved to. The two cases must stay distinguishable, which is what this pins.
_e2e_renamed_reason = _e2e_renamed_res["skipped"].get("REQ") or ""
_e2e_pending_reason = _rr_run(_rr_req(), _rr_pending_log)[0]["skipped"].get("REQ") or ""
expect("WARP-0622 S4 FIX: a renamed state is DISTINGUISHABLE from a pending one and names the state the ticket moved to, so the operator is told to fix the config rather than to keep waiting",
       _e2e_renamed_reason != _e2e_pending_reason
       and "Signed Off" in _e2e_renamed_reason
       and "no longer matches the board" in _e2e_renamed_reason)
expect("WARP-0622 S4 control: a GENUINELY pending request still reads as undecided and does NOT accuse the config, because that would be the same defect pointing the other way",
       "has not decided" in _e2e_pending_reason
       and "no longer matches the board" not in _e2e_pending_reason)
expect("WARP-0622 S4 control: teaching the reconcile the new state through CONFIG settles it - the state vocabulary is configuration, not a guess",
       _e2e_outcome(RR.reconcile_requests(
           [_rr_req()], _rr_run(_rr_req(), _e2e_renamed)[2], RR.FakeSettlementStore(),
           digest_reader=lambda r: _RR_DIGEST, approver_registry=_RR_REG, policy=_RR_POLICY,
           attestations={"REQ": _RR_ATTS_C},
           config={"agent": "veldo-executor", "accept_states": ("Signed Off",)})) == "settled")

# S5 DOWNTIME. The tracker is unreachable. A reconcile that cannot READ must not conclude anything.
class _E2EDownTracker(TA_RR.FakeTracker):
    # The adapter's REAL error class. An earlier draft of this raised a name that does not exist,
    # so the fake threw AttributeError and the assertion passed while testing nothing about an
    # outage - a green test of the wrong thing, which is worse than a red one.
    def read_changelog(self, obj_id):
        raise TA_RR.TrackerAdapterError("tracker unreachable: connection refused")


_e2e_down = RR.reconcile_requests([_rr_req()], _E2EDownTracker(), RR.FakeSettlementStore(),
                                  digest_reader=lambda r: _RR_DIGEST, approver_registry=_RR_REG,
                                  policy=_RR_POLICY, attestations={"REQ": _RR_ATTS_C},
                                  config={"agent": "veldo-executor"})
expect("WARP-0622 S5 DOWNTIME: an unreachable tracker HOLDS and settles nothing, and the reason names the outage rather than reporting an empty history",
       _e2e_outcome(_e2e_down) == "held" and _e2e_down["settled"] == []
       and "not readable" in (_e2e_down["held"].get("REQ") or "")
       and "connection refused" in (_e2e_down["held"].get("REQ") or ""))
expect("WARP-0622 S5: the same request against a reachable tracker settles, so downtime is the reason and not the request",
       _e2e_outcome(_rr_run(_rr_req(), _rr_valid_log)[0]) == "settled")

# S6 SECRET ROTATION. Credentials change under the reconcile mid-flight. The observable is the same
# as downtime for the read that fails, and CRUCIALLY the run must not half-settle.
class _E2ERotatingTracker(TA_RR.FakeTracker):
    """Reads once, then the credential is rotated out from under it."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.reads = 0

    def read_changelog(self, obj_id):
        self.reads += 1
        if self.reads > 1:
            raise TA_RR.TrackerAdapterError("401 unauthorized: credential rotated")
        return super().read_changelog(obj_id)


_e2e_rot = _E2ERotatingTracker(intake_items=[{"id": "VEL-1", "title": "d"},
                                             {"id": "VEL-2", "title": "d"}])
_e2e_rot.seed_changelog("VEL-1", _rr_valid_log)
_e2e_rot.seed_changelog("VEL-2", _rr_valid_log)
_e2e_rot_store = RR.FakeSettlementStore()
_e2e_rot_res = RR.reconcile_requests(
    [_rr_req(), _rr_req(rid="REQ2", issue="VEL-2")], _e2e_rot, _e2e_rot_store,
    digest_reader=lambda r: _RR_DIGEST, approver_registry=_RR_REG, policy=_RR_POLICY,
    attestations={"REQ": _RR_ATTS_C, "REQ2": _RR_ATTS_C}, config={"agent": "veldo-executor"})
expect("WARP-0622 S6 SECRET ROTATION: a credential rotated mid-run settles what it could READ and HOLDS the rest, naming the rotation - it never guesses past the failure and never half-writes a receipt",
       _e2e_outcome(_e2e_rot_res) == "settled"
       and _e2e_outcome(_e2e_rot_res, "REQ2") == "held"
       and "credential rotated" in (_e2e_rot_res["held"].get("REQ2") or "")
       and _e2e_receipts(_e2e_rot_store) == 1)

# S7 CONCURRENT ARTIFACT CHANGES. The bound artifact changes between the decision and the reconcile.
# The approval was for what the human READ, not for whatever the file says now.
_e2e_moved = _rr_run(_rr_req(), _rr_valid_log,
                     digest_map={"proof/X/approval.json": "sha256:somethingelse00"})[0]
expect("WARP-0622 S7 CONCURRENT CHANGE: the bound artifact changing after the decision HOLDS - the approval was for what the human read, not for whatever the file says now",
       _e2e_outcome(_e2e_moved) == "held")
expect("WARP-0622 S7: an artifact the repository cannot read at all HOLDS rather than settling on an absent digest",
       _e2e_outcome(_rr_run(_rr_req(), _rr_valid_log, digest_map={})[0]) == "held")
expect("WARP-0622 S7 control: the unchanged artifact settles, so the refusal is the digest and nothing else",
       _e2e_outcome(_rr_run(_rr_req(), _rr_valid_log)[0]) == "settled")

# S8 REPOSITORY CONFLICTS. Two humans move the same ticket in opposite directions. An ambiguous
# history is an ambiguity to BLOCK on, never a race to resolve by picking the last writer.
_e2e_conflict, _, _ = _rr_run(_rr_req(), _rr_conflict_log)
expect("WARP-0622 S8 CONFLICT: approve-then-reject by two different humans HOLDS - an ambiguous history is blocked on, never resolved by taking the last writer",
       _e2e_outcome(_e2e_conflict) == "held")
expect("WARP-0622 S8 control: a clean single decision in either direction resolves - approve settles, reject settles as a decision",
       _e2e_outcome(_rr_run(_rr_req(), _rr_valid_log)[0]) == "settled"
       and _e2e_outcome(_rr_run(_rr_req(), _rr_reject_log)[0]) == "settled")
expect("WARP-0622 S8: a request with NO terminal transition yet is SKIPPED and never settled - pending is not consent",
       _e2e_outcome(_rr_run(_rr_req(), _rr_pending_log)[0]) == "skipped")

# S9 REVOCATION. An approver is removed from the registry after deciding. The decision does not
# survive the authority behind it.
_e2e_revoked_reg = {k: v for k, v in _RR_REG.items() if k != "alice"}
_e2e_revoked = RR.reconcile_requests(
    [_rr_req()], _rr_run(_rr_req(), _rr_valid_log)[2], RR.FakeSettlementStore(),
    digest_reader=lambda r: _RR_DIGEST, approver_registry=_e2e_revoked_reg, policy=_RR_POLICY,
    attestations={"REQ": _RR_ATTS_C}, config={"agent": "veldo-executor"})
expect("WARP-0622 S9 REVOCATION: an approver removed from the registry no longer authorizes - the decision does not outlive the authority behind it",
       _e2e_outcome(_e2e_revoked) == "held")
_e2e_norole_reg = dict(_RR_REG, alice={"roles": [], "independence": "g1", "actor": "human"})
expect("WARP-0622 S9: stripping the ROLE has the same effect as removing the approver, so authority is checked per touchpoint rather than per name",
       _e2e_outcome(RR.reconcile_requests(
           [_rr_req()], _rr_run(_rr_req(), _rr_valid_log)[2], RR.FakeSettlementStore(),
           digest_reader=lambda r: _RR_DIGEST, approver_registry=_e2e_norole_reg,
           policy=_RR_POLICY, attestations={"REQ": _RR_ATTS_C},
           config={"agent": "veldo-executor"})) == "held")
expect("WARP-0622 S9 control: with the registry intact the same request settles, so revocation is the reason",
       _e2e_outcome(_rr_run(_rr_req(), _rr_valid_log)[0]) == "settled")

# THE SET IS COMPLETE AND ENUMERATED ONCE. Nine scenarios, named by the plan; asserting the count
# here means dropping one from the file is a failure rather than a silently smaller suite.
_E2E_SCENARIOS = ("replay", "spoofed_actor", "automation_transitions", "workflow_edits", "downtime",
                  "secret_rotation", "concurrent_artifact_changes", "repository_conflicts",
                  "revocation")
expect("WARP-0622 AC4: all NINE scenarios the plan names are covered, enumerated once so dropping one is a failure rather than a quietly smaller suite",
       len(_E2E_SCENARIOS) == 9
       and len({s for s in _E2E_SCENARIOS}) == 9)
