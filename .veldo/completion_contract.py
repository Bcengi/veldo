#!/usr/bin/env python3
"""Completion and executable eligibility predicates (PLAN-0019 W6, VELDO-0021).

WHAT THIS MODULE IS. Pure predicates over plain data, a contract organ beside graph_contract.py
and authority_contract.py: the four distinct completion facts and their evidence, none implying the
next (R70, R76, AC1); the authoritative snapshot every execution entry reads and the named refusals
for stale, missing or negatively-predicated prerequisites, plus the provider charge reservation
that must fit before a call (R45, R70, AC2); the proof, review and verification obligations
engineering completion needs, verified outside worker control (R46, R47, R50, AC3); and the
publication transition table with the R32 recovery findings, where uncertainty stays explicit
and no lost acknowledgement becomes success (R32, R49, R76, AC4). Standard library only; reads no
live system, runs no Git and writes nothing. The store, the lander, the eligibility service and
the effect executor that apply these predicates are Packages B and C; a Git object this module is
asked about is looked up through a callable the caller supplies.
"""
import math
import posixpath

SCHEMA = "veldo.completion_contract/v1"


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


MACHINE_ACTORS = frozenset({"veldo-executor", "veldo-responder", "executor", "responder", "machine",
                            "agent", "bot", "ava", "automation", "service", "service_account", "service-account"})

# ---------------------------------------------------------------------------------------------
# AC1: four completion facts, each with its own evidence; none implies the next.
# ---------------------------------------------------------------------------------------------

# The fact kinds R70 and R76 name, the evidence each needs, and its subject. Every fact names its
# subject revision and its evidence; NONE implies the next: a clean build-only attempt, an accepted
# artifact, a passing review, a shipped status string or a process exit is not the completion chain.
COMPLETION_FACTS = {
    "attempt_finished": {"clause": "R70", "subject": "attempt",
                         "evidence": ("trusted_exit", "accounting_observation", "containment_empty")},
    "artifact_accepted": {"clause": "R70", "subject": "artifact",
                          "evidence": ("station", "artifact_digests", "acceptor")},
    "revision_landed": {"clause": "R76", "subject": "revision",
                        "evidence": ("publication_receipt", "remote_confirmation", "replicated", "spec_shipped_event")},
    "objective_satisfied": {"clause": "R06", "subject": "objective",
                            "evidence": ("signed_assessment", "accepted_objective_revision", "assessor")},
}
FACT_ORDER = ("attempt_finished", "artifact_accepted", "revision_landed", "objective_satisfied")


def fact_problems(kind, receipt, expected_subject=None):
    """Why `receipt` does NOT establish the fact `kind`, by name: an unknown kind; a receipt that is
    not a record, names another fact kind, names no subject or another subject than expected, or
    lacks any of the fact's evidence fields (each must be present and truthy); a superseded receipt
    (superseded_by set) establishes nothing now; a receipt whose acceptor or assessor is a machine
    actor where a person or named authority is required."""
    spec = COMPLETION_FACTS.get(kind)
    if spec is None:
        return ["unknown completion fact %r (known: %s)" % (kind, ", ".join(FACT_ORDER))]
    if not isinstance(receipt, dict):
        return ["%s: a receipt is a record" % kind]
    problems = []
    if receipt.get("fact") != kind:
        problems.append("%s: the receipt establishes %r, not %s (no fact implies another)" % (kind, receipt.get("fact"), kind))
    subject = receipt.get("subject") or {}
    if not isinstance(subject, dict) or not _is_str(subject.get("id")) or not _is_pos_int(subject.get("revision")):
        problems.append("%s: the receipt names no subject %s with an id and a revision" % (kind, spec["subject"]))
    elif expected_subject is not None and (subject.get("id"), subject.get("revision")) != (expected_subject.get("id"), expected_subject.get("revision")):
        problems.append("%s: the receipt is about %s@%r, not %s@%r" % (kind, subject.get("id"), subject.get("revision"), expected_subject.get("id"), expected_subject.get("revision")))
    for f in spec["evidence"]:
        if not receipt.get(f):
            problems.append("%s: evidence %s is missing" % (kind, f))
    if receipt.get("superseded_by"):
        problems.append("%s: the receipt is superseded by %r and establishes nothing now" % (kind, receipt["superseded_by"]))
    for who in ("acceptor", "assessor"):
        if who in spec["evidence"] and _is_str(receipt.get(who)) and receipt[who].strip().lower() in MACHINE_ACTORS:
            problems.append("%s: %s %r is a machine actor; a person or named authority is required" % (kind, who, receipt[who]))
    return problems


def completion_state(receipts, subject=None):
    """{fact: established bool} for the four facts over a list of receipts, each fact judged ONLY
    by its own receipt: no fact is inferred from another. Missing receipts leave a fact False."""
    state = {}
    for kind in FACT_ORDER:
        mine = [r for r in receipts or [] if isinstance(r, dict) and r.get("fact") == kind]
        state[kind] = any(not fact_problems(kind, r, subject) for r in mine)
    return state


def implies(fact_a, fact_b):
    """Whether establishing fact_a establishes fact_b: never, for any pair (R70). Written down so
    the rule has a name the suite can drive over every pair."""
    return False


# ---------------------------------------------------------------------------------------------
# AC2: authoritative snapshots, executable eligibility, provider charge reservation.
# ---------------------------------------------------------------------------------------

ELIGIBILITY_ENTRIES = ("selection", "direct_execution", "build", "review", "claim", "redispatch", "provider_request",
                       "result_acceptance", "publication")
READ_SET_KINDS = ("specifications", "plans", "releases", "decisions", "floors", "policy", "membership", "admission",
                  "graph", "roster", "reservations", "receipts")
SNAPSHOT_IDENTITY = ("domain_uuid", "repository_uuid", "source_commit", "journal_sequence", "published_watermark")
# Which predicates each entry asks beyond the shared ones. Review asks the same draft-plan, decision
# and dependency questions as build: review cannot bypass them (R70).
ENTRY_PREDICATES = {
    "selection": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers"),
    "direct_execution": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers", "admission_current"),
    "build": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers", "admission_current", "claim_current"),
    "review": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers", "reviewer_independent"),
    "claim": ("plan_not_draft", "dependencies_resolved", "no_blockers", "admission_current"),
    "redispatch": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers", "previous_attempt_reconciled"),
    "provider_request": ("admission_current", "claim_current", "charge_reserved"),
    "result_acceptance": ("decisions_settled", "dependencies_resolved", "no_blockers", "claim_current"),
    "publication": ("plan_not_draft", "decisions_settled", "dependencies_resolved", "no_blockers", "claim_current", "authority_current", "approvals_valid"),
}


def snapshot_problems(snapshot):
    """Why a snapshot is NOT a complete authoritative read set (R70): a missing identity field, or a
    read-set kind without a version and a digest (checking only the project version is insufficient;
    a collection or graph version is what a negative predicate such as absence of blockers reads)."""
    if not isinstance(snapshot, dict):
        return ["a snapshot is a record"]
    problems = ["snapshot lacks %s" % f for f in SNAPSHOT_IDENTITY if not (snapshot.get(f) not in (None, ""))]
    reads = snapshot.get("read_set") or {}
    for k in READ_SET_KINDS:
        r = reads.get(k) if isinstance(reads, dict) else None
        if not isinstance(r, dict) or r.get("version") is None or not _is_str(r.get("digest")):
            problems.append("read set lacks %s with a version and a digest: a declared read set is complete or the entry does not run" % k)
    return problems


def eligibility(entry, snapshot, current, facts):
    """{eligible, refusals} for one execution entry (R70): the snapshot must be complete; every
    read-set version in it must equal the authority's `current` version (a changed input, or a
    record inserted after the read, is a named refusal even while the project version is fixed);
    and every predicate the entry asks must be literally True in `facts`. Named, atomic, and the
    same decision for review as for build: review cannot bypass draft-plan, decision or dependency
    checks."""
    if entry not in ELIGIBILITY_ENTRIES:
        return {"eligible": False, "refusals": ["unknown entry %r" % (entry,)]}
    refusals = snapshot_problems(snapshot)
    if not refusals:
        for k in READ_SET_KINDS:
            mine, now = snapshot["read_set"][k], (current or {}).get(k) or {}
            if mine.get("version") != now.get("version") or mine.get("digest") != now.get("digest"):
                refusals.append("stale read: %s moved from version %r to %r since the snapshot (a newly inserted or changed record)"
                                % (k, mine.get("version"), now.get("version")))
    for p in ENTRY_PREDICATES[entry]:
        if (facts or {}).get(p) is not True:
            refusals.append("%s requires %s" % (entry, p))
    return {"eligible": not refusals, "refusals": refusals}


CEILINGS = ("account", "project", "unit")


def charge_allocation(max_charge, remaining):
    """{allowed, remaining_after, refusal}: before every billable provider request, retries and
    follow-on calls included, the enforceable maximum possible charge is allocated atomically from
    EVERY remaining reservation (account, project, unit) after settled charges and outstanding
    exposure (R45). An unknown or unbounded maximum refuses; a maximum exceeding any remainder
    refuses and nothing is allocated; on success every remainder is decremented together."""
    if not _is_num(max_charge) or max_charge < 0:
        return {"allowed": False, "remaining_after": dict(remaining or {}), "refusal": "the request's maximum possible charge is not bounded (%r): refused before the provider call" % (max_charge,)}
    for c in CEILINGS:
        if not _is_num((remaining or {}).get(c)):
            return {"allowed": False, "remaining_after": dict(remaining or {}), "refusal": "no %s remainder is known: an unknown remainder admits nothing" % c}
        if max_charge > remaining[c]:
            return {"allowed": False, "remaining_after": dict(remaining), "refusal": "maximum charge %r exceeds the %s remainder %r" % (max_charge, c, remaining[c])}
    return {"allowed": True, "remaining_after": {c: remaining[c] - max_charge for c in CEILINGS}, "refusal": None}


def allocate_sequence(max_charges, remaining):
    """The allocations of several requests against one remainder in order, each seeing the
    remainder the previous left: concurrent requests cannot spend the same remainder twice."""
    out, rem = [], dict(remaining)
    for m in max_charges:
        r = charge_allocation(m, rem)
        out.append(r)
        if r["allowed"]:
            rem = r["remaining_after"]
    return out, rem


def exposure_after(reservation, outcome):
    """The remaining reservation after a request's outcome (R45): reconciled usage releases the
    difference between the allocated maximum and the settled charge; authoritative proof of no
    charge releases the whole allocation; a timeout, a cancellation or a delayed usage report
    releases NOTHING (outstanding exposure stays until reconciled)."""
    allocated = reservation.get("allocated")
    if outcome.get("kind") == "reconciled_usage":
        charge = outcome.get("charge")
        if not (_is_num(charge) and charge >= 0 and _is_num(allocated) and allocated >= 0):
            return dict(reservation, released=0, note="a reconciled charge is a finite non-negative number (%r is not): nothing is released and "
                                                     "nothing is manufactured; outstanding exposure is retained" % (charge,))
        return dict(reservation, allocated=0, released=allocated - min(charge, allocated), settled=charge)
    if outcome.get("kind") == "proof_of_no_charge" and outcome.get("authoritative") is True:
        return dict(reservation, allocated=0, released=allocated, settled=0)
    return dict(reservation, released=0, note="outstanding exposure is retained until reconciled usage or authoritative proof of no charge (%r releases nothing)" % outcome.get("kind"))


# ---------------------------------------------------------------------------------------------
# AC3: engineering completion needs proof, independent review and outside verification.
# ---------------------------------------------------------------------------------------------

PROOF_OBLIGATIONS = ("implementation_commit_exists", "accepted_spec_revision", "complete_criterion_set", "evidence_per_criterion",
                     "producer_identity", "checks_observed", "checks_passed", "reviewer_identity", "reviewer_independent", "review_bound",
                     "objections_disposed", "candidate_tree", "verifier_installed_outside_candidate", "protected_path_approval", "post_run_tree_equal")


def _inside(path, root):
    """Whether `path` resolves inside `root` by lexical normalization (no filesystem): both must
    be absolute POSIX paths; `..` segments are collapsed first, so /opt/../cand/x is inside /cand."""
    if not (_is_str(path) and _is_str(root) and path.startswith("/") and root.startswith("/")):
        return None
    np, nr = posixpath.normpath(path), posixpath.normpath(root)
    return np == nr or np.startswith(nr.rstrip("/") + "/")


def completion_problems(bundle, commit_exists):
    """Why an engineering unit is NOT complete, by name (R46, R47, R50): the implementation Git object
    does not exist (asked through `commit_exists`, a callable the caller supplies); no accepted
    specification revision; an empty criterion universe or one that differs from the spec's own set
    (a proof over no criteria proves nothing); a criterion without evidence digests or a duplicate
    mapping; no producer identity; a check without a command, exit code and observation reference
    (a fabricated default check); a check that did not exit 0 (a red gate completes nothing); no
    reviewer, a reviewer who is the producer, a review not bound to the exact implementation
    commit, candidate tree and proof digest it reviewed, or an undisposed blocking objection; no
    candidate tree digest or no candidate root; a verifier that lives inside the candidate tree
    after path normalization, or whose path is not absolute; a touched protected path without a
    valid approval; no post-run tree digest, or one that differs from the candidate's."""
    problems = []
    b = bundle or {}
    if not _is_str(b.get("implementation_commit")) or not commit_exists(b.get("implementation_commit")):
        problems.append("implementation_commit_exists: %r is not a Git object this authority can resolve" % (b.get("implementation_commit"),))
    spec = b.get("spec") or {}
    if not _is_str(spec.get("id")) or not _is_pos_int(spec.get("revision")) or spec.get("status") not in ("ready", "in_progress", "review", "proven", "shipped"):
        problems.append("accepted_spec_revision: the proof binds no accepted specification revision")
    spec_criteria = list(spec.get("criteria") or [])
    proof_criteria = list((b.get("proof") or {}).get("criteria") or [])
    ids = [c.get("id") for c in proof_criteria if isinstance(c, dict)]
    if not spec_criteria or not ids or sorted(ids) != sorted(spec_criteria):
        problems.append("complete_criterion_set: the proof's criteria %s are not the specification's complete set %s (an empty universe proves nothing)" % (sorted(ids), sorted(spec_criteria)))
    if len(ids) != len(set(ids)):
        problems.append("evidence_per_criterion: a criterion is mapped twice")
    for c in proof_criteria:
        ev = c.get("evidence") if isinstance(c, dict) else None
        if not ev or not all(isinstance(e, dict) and _is_str(e.get("digest")) for e in ev):
            problems.append("evidence_per_criterion: criterion %r has no evidence digest" % ((c or {}).get("id"),))
    producer = (b.get("proof") or {}).get("producer")
    if not _is_str(producer):
        problems.append("producer_identity: the proof names no producer")
    checks = (b.get("proof") or {}).get("checks") or []
    if not checks:
        problems.append("checks_observed: the proof carries no checks")
    for ch in checks:
        if not isinstance(ch, dict) or not _is_str(ch.get("command")) or not isinstance(ch.get("exit_code"), int) or isinstance(ch.get("exit_code"), bool) \
                or not _is_str(ch.get("observation_ref")):
            problems.append("checks_observed: check %r has no command, exit code or observation reference (a fabricated default check)" % ((ch or {}).get("name"),))
        elif ch["exit_code"] != 0:
            problems.append("checks_passed: check %r exited %r; a check that did not pass completes nothing" % (ch.get("name"), ch["exit_code"]))
    cand = b.get("candidate") or {}
    review = b.get("review") or {}
    reviewer = review.get("reviewer")
    if not _is_str(reviewer):
        problems.append("reviewer_identity: no independent review is bound")
    elif _is_str(producer) and reviewer.strip().lower() == producer.strip().lower():
        problems.append("reviewer_independent: the reviewer %r is the producer" % reviewer)
    proof_digest = (b.get("proof") or {}).get("digest")
    if not _is_str(proof_digest):
        problems.append("review_bound: the proof carries no digest for a review to bind to")
    elif review.get("implementation_commit") != b.get("implementation_commit") or review.get("source_digest") != cand.get("tree_digest") \
            or review.get("proof_digest") != proof_digest:
        problems.append("review_bound: the review names commit %r, source %r and proof %r, not this bundle's %r, %r and %r; a review of other bytes reviews nothing here"
                        % (review.get("implementation_commit"), review.get("source_digest"), review.get("proof_digest"),
                           b.get("implementation_commit"), cand.get("tree_digest"), proof_digest))
    if any(isinstance(f, dict) and f.get("blocking") is True and not _is_str(f.get("disposition")) for f in review.get("findings") or []):
        problems.append("objections_disposed: a blocking finding has no explicit disposition")
    if not _is_str(cand.get("tree_digest")) or not _is_str(cand.get("root")):
        problems.append("candidate_tree: no exact candidate tree digest or no candidate root")
    verifier = b.get("verifier") or {}
    inside = _inside(verifier.get("path"), cand.get("root"))
    if not _is_str(verifier.get("digest")) or inside is None or inside:
        problems.append("verifier_installed_outside_candidate: the verifier is unnamed, not an absolute path, has no candidate root to be outside of, "
                        "or resolves inside the candidate tree (R50)")
    if b.get("protected_paths_touched") and not (isinstance(b.get("approval"), dict) and b["approval"].get("valid") is True):
        problems.append("protected_path_approval: a protected path was touched without a valid recorded approval")
    if not _is_str(cand.get("tree_digest_after_run")):
        problems.append("post_run_tree_equal: no post-run tree digest was observed; without it nothing establishes that verification left the candidate unchanged")
    elif cand["tree_digest_after_run"] != cand.get("tree_digest"):
        problems.append("post_run_tree_equal: the candidate tree changed during verification")
    return problems


# ---------------------------------------------------------------------------------------------
# AC4: publication transitions and recovery findings; uncertainty stays explicit.
# ---------------------------------------------------------------------------------------------

PUBLICATION_STATES = ("candidate_built", "verified", "authorized", "published", "confirmed", "completed", "halted", "awaiting_authority")
RECOVERY_FINDINGS = {
    "not_dispatched": ("receiver_evidence_of_no_start",),
    "running": ("receiver_group_identity", "invocation_identity"),
    "effect_committed": ("trusted_target_evidence",),
    "acknowledgement_lost": ("receiver_acceptance_evidence",),
    "outcome_unknown": (),
}
# (state, event, predicates) -> next state. Every step of the chain has its own evidence; a lost
# acknowledgement never advances the chain.
PUBLICATION_TRANSITIONS = (
    ("candidate_built", "gate_green", ("candidate_identity", "verifier_receipt"), "verified"),
    ("candidate_built", "gate_red", (), "halted"),
    ("verified", "authority_recheck_ok", ("claim_generation_current", "authority_generation_current", "admission_current", "scope_current",
                                          "decisions_settled", "dependencies_resolved", "approvals_valid", "expected_tip_current"), "authorized"),
    ("verified", "approval_rejected", (), "halted"),
    ("verified", "dependency_withdrawn", (), "halted"),
    ("verified", "authority_revoked", (), "halted"),
    ("authorized", "push_cas_ok", ("remote_tip_was_expected_old_tip",), "published"),
    ("authorized", "remote_tip_moved", (), "halted"),
    ("authorized", "acknowledgement_lost", (), "awaiting_authority"),
    ("published", "remote_confirmed", ("remote_commit_matches_candidate", "ancestry_confirmed"), "confirmed"),
    ("published", "acknowledgement_lost", (), "awaiting_authority"),
    ("confirmed", "receipt_replicated", ("landing_receipt_committed", "receipt_replicated_off_host", "spec_shipped_event"), "completed"),
    ("awaiting_authority", "recovery_effect_committed", ("trusted_target_evidence",), "published"),
    ("awaiting_authority", "recovery_not_dispatched", ("receiver_evidence_of_no_start",), "verified"),
)
TERMINAL_PUBLICATION = ("completed", "halted")


def publication_step(state, event, evidence):
    """(next_state, reason): one step of the publication chain (R49, R76). An undeclared (state,
    event) pair refuses; a declared step advances only when every predicate is literally True in
    `evidence`. A lost acknowledgement moves to awaiting_authority, never to a success state, and
    only trusted target evidence or receiver evidence moves it on from there: evidence that the
    effect committed moves to published (confirmation still needs the remote), evidence of no
    start returns to VERIFIED, so every authority, claim, admission, scope, decision, dependency,
    approval and tip recheck runs again before another publish (revocation during the recovery
    interval is seen, never assumed away)."""
    if state not in PUBLICATION_STATES:
        return None, "unknown publication state %r" % (state,)
    for s, e, preds, nxt in PUBLICATION_TRANSITIONS:
        if s == state and e == event:
            missing = [p for p in preds if (evidence or {}).get(p) is not True]
            if missing:
                return None, "%s + %s needs %s; missing %s" % (state, event, ", ".join(preds), ", ".join(missing))
            return nxt, "%s -> %s on %s" % (state, nxt, event)
    return None, "%s + %s is not a declared publication transition" % (state, event)


def recovery_finding(evidence):
    """The one R32 finding the evidence justifies, or outcome_unknown: not_dispatched needs durable
    receiver evidence of no start; running needs the receiver's containment group and invocation
    identity; effect_committed needs trusted target evidence; acknowledgement_lost needs receiver
    acceptance evidence. Process absence, checkpoint loss, lease expiry and nonce consumption
    justify nothing."""
    ev = evidence or {}
    for finding in ("effect_committed", "running", "acknowledgement_lost", "not_dispatched"):
        if all(ev.get(p) is True for p in RECOVERY_FINDINGS[finding]):
            return finding
    return "outcome_unknown"


def landing_receipt_problems(receipt):
    """Why a landing receipt does NOT certify completion (R76): it must join the implementation
    commit, the proof artifact, the reviewed source and proof digests, the old remote tip, the
    candidate commit, the exact tested tree, the gate invocation with its EXTERNAL output location,
    the unit and dispatch identities, the remote confirmation and the replication receipt; it may
    not live inside the commit it certifies (self-certification); a shipped status string, a clean
    attempt or a passing review assertion in place of any of these certifies nothing."""
    fields = ("implementation_commit", "proof_digest", "reviewed_source_digest", "old_remote_tip", "candidate_commit", "tested_tree",
              "gate_invocation", "gate_output_location", "unit_id", "dispatch_id", "remote_confirmation", "replication_receipt")
    r = receipt or {}
    problems = ["landing receipt lacks %s" % f for f in fields if not r.get(f)]
    if _is_str(r.get("gate_output_location")) and _is_str(r.get("candidate_commit")) and r["gate_output_location"].startswith("candidate:"):
        problems.append("the gate output lives inside the candidate: stamps and events are external observations, never uncommitted evidence")
    if r.get("receipt_inside_certified_commit") is True:
        problems.append("the receipt is inside the commit it certifies: a receipt cannot contain itself")
    if r.get("basis") in ("shipped_status_string", "clean_attempt", "passing_review", "process_exit"):
        problems.append("%r is not a completion chain" % r["basis"])
    return problems
