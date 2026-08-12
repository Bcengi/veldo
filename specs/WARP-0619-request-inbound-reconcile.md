---
schema: veldo.spec/v1
id: WARP-0619
title: the inbound command-and-receipt reconcile (offline logic) - a human's tracker transition is only a
  SUBMITTED ASSERTION; the repo derives the true actor and intent from the ORDERED ATTRIBUTED changelog
  (never current status), validates against the shipped safety core, and writes the settlement record only
  through an append-only compare-and-swap receipt, so the repo stays the single source of truth (W5-logic
  of the human-decision surface, offline over a fake tracker; the LIVE-sandbox proof is WARP-0620)
status: shipped
risk: high - this is the SAFETY-CRITICAL crux of the human-decision surface: the path that turns a human's
  tracker decision into an authorized settlement record. It is built and gate-proven ENTIRELY OFFLINE over a
  deterministic fake tracker with a seeded changelog (no network, no live board); the real-board shape is
  proven separately in WARP-0620 with Dmitry. It composes the shipped safety core UNCHANGED (authorization.
  is_authorized with caller-supplied VERIFIED identities, two_key for irreversible/money/external,
  policy_check, decision.validate_record) and writes settlement records + events only through an append-only
  compare-and-swap receipt. It BLOCKS on any gap, conflict, or ambiguity rather than inferring. It touches no
  protected path. The changelog read is a read-only fenced seam.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W5
plan_revision: 1
placement: [tracker]
footprint:
  - .veldo/request_reconcile.py
  - .veldo/tracker_adapter.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - .veldo/architecture.yaml
  - scripts/selftest.py
  - specs/WARP-0619-request-inbound-reconcile.md
  - specs/index.md
  - proof/WARP-0619/**
protected_paths: []
behavior_bearing: true
observability:
  logs: the reconcile reports, per request it examines, the changelog id it read, the derived actor and
    intent, every validation it ran and the single reason it accepted or BLOCKED, and whether a settlement
    record + event were written or suppressed as an already-applied receipt - so a stranger sees exactly why
    each decision settled or was held, from the report alone.
  error_taxonomy: a gap/conflict/ambiguity in the changelog BLOCKS (held, never inferred), never errors; an
    unauthorized/agent-made/self-approving/digest-mismatched/quorum-short/two-key-missing transition is
    REFUSED via the safety core (held), not applied; a duplicate (request_id, changelog_id) is a no-op
    (idempotent), not a double-apply; a request with no tracker link yet is skipped (nothing to reconcile).
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Drop the per-entry deep copy in FakeTracker._read_changelog at .veldo/tracker_adapter.py:747 so
      it hands back the seeded list itself. The load-bearing leg is READ-ONLY, and the assertion that
      a caller appending to and tampering with the returned changelog leaves the seeded source at
      actor "builder" with two entries must go red.
    text: A read-only read_changelog seam is added to the TrackerAdapter base (NotImplementedError) and to
      the deterministic FakeTracker (seed_changelog + read_changelog), returning an ORDERED, ATTRIBUTED
      changelog (each entry = id, ts, actor identity, from-state, to-state). It is READ-ONLY - the reconcile
      never writes back through it - and the live adapter is reference-wired but NEVER exercised in the gate
      (the fake is what runs). No always-on listener: the reconcile is in-session demand-driven by default,
      with an opt-in off-by-default supervised timer, never a background poller/daemon.
  - id: AC2
    falsified_by: >
      Replace `actors = _entry_actors(term["entries"])` with `actors = [record.get("decided_by")]` at
      .veldo/request_reconcile.py:446 so a self-declared request field supplies the identity instead
      of the attributed changelog, and the assertion that an agent-made terminal transition is
      BLOCKED must go red by settling it.
    text: reconcile_requests (a sibling of the shipped reconcile_promotions) finds OPEN requests by the repo
      index (.veldo/requests/) plus the issue link plus a status query - NEVER by assignee==agent (the service
      account cannot be an assignee) - and for each pulls the ordered attributed changelog and derives the
      TRUE actor and intent FROM THE CHANGELOG (the terminal transition entry and who made it), NEVER from
      the current status. A tracker transition is only a SUBMITTED ASSERTION; the repo decides whether it
      settles.
  - id: AC3
    falsified_by: >
      Guard the authorized-only settlement gate as `if False and not decision.get("authorized")` at
      .veldo/request_reconcile.py:482. That is the leg every other one funnels through (separated
      approver, never the agent, quorum, two_key), and the assertion that an irreversible request
      with no satisfied second key is held must go red by writing a settlement record.
    text: Before a decision settles, the reconcile VALIDATES it against the shipped safety core with
      identities derived and VERIFIED from the changelog/lineage (never self-declared request fields) - the
      terminal actor must be an authorized approver for the request tier and separated from the verified
      proposer and never the agent (authorization.is_authorized, given the verified proposer and approver
      identities), the bound artifact digest RECOMPUTED FROM THE REPO must equal the displayed digest, two_key
      (KEY1+KEY2) must hold for irreversible/money/external, and quorum must be met. Any gap, conflict, or
      ambiguity (missing entry, two conflicting terminal transitions, an actor not resolvable) BLOCKS - the
      request is held, never inferred or defaulted-open.
  - id: AC4
    falsified_by: >
      Guard the compare-and-swap inside SettlementStore.settle as `if False and
      self._has_receipt(request_id, changelog_id)` at .veldo/request_reconcile.py:307, and both
      receipt assertions must go red: a second pass over the same request writes a second record
      instead of being a byte-identical no-op, and a pre-seeded (REQ, c2) receipt applies instead of
      being skipped.
    text: On a validated acceptance the reconcile writes the touchpoint's settlement record (veldo.approval /
      veldo.decision / veldo.verdict) and emits the event ONLY through an APPEND-ONLY COMPARE-AND-SWAP receipt
      keyed (request_id, changelog_id) - so a re-run, a re-projection, or a duplicated changelog entry is a
      no-op and never double-applies. The repo is the single source of truth: the settlement record lands in
      the repo FIRST; setting the terminal tracker state is a downstream projection (W3), so the tracker is
      never a second source of truth. The reconcile writes no tracker state itself.
  - id: AC5
    falsified_by: >
      Pass `_rr_src` unmutated into `_rr_mut` at
      scripts/suites/11_inbound_command_receipt_reconcile.py:218 so the T-agent mutant derives its
      actor from the changelog exactly as the shipped module does, and T-agent's assertion that the
      mutant settles one record while the real path settles none must go red, which is the
      tautology this criterion refuses.
    text: A selftest drives reconcile_requests over the FakeTracker with a seeded changelog OFFLINE (no
      network) and is NON-TAUTOLOGICAL - a valid authorized-approver terminal transition settles once
      (settlement record + event + receipt written) and a re-run is idempotent (no second write); an
      agent-made transition is BLOCKED; a self-approval (terminal actor == verified proposer) is BLOCKED; a
      recomputed-digest mismatch is BLOCKED; an irreversible action without a satisfied two_key is BLOCKED; a
      conflicting/ambiguous changelog is BLOCKED; a duplicate (request_id, changelog_id) is a no-op - each
      with an in-memory source-mutation TOOTH that turns its assertion red while the on-disk module stays
      byte-unchanged (neutralizing the actor-from-changelog derivation lets current-status drive it;
      neutralizing the compare-and-swap double-applies; neutralizing the repo-digest recompute accepts a
      forged digest). None vacuous.
required_evidence: [unit]
rollback: git revert; additive - a new repo-only reconcile module + a read-only changelog seam on the
  adapter, one capability entry per copy, an architecture.yaml declaration, a selftest block, and this spec;
  it reuses the shipped safety core (authorization/two_key/policy_check/decision) UNCHANGED and the shipped
  reconcile_promotions pattern; no protected path; the live changelog read is a reference seam never run in
  the gate; pure stdlib. The LIVE-board shape proof is the separate WARP-0620.
---

## Intent

This is the inbound half of the human-decision surface, and the most safety-critical piece: the path by
which a human's decision on the tracker becomes an authorized settlement record in the repo. The rule is
command-and-receipt: a tracker transition is only a SUBMITTED ASSERTION. The repo pulls the ordered,
attributed changelog, works out who actually did what from the changelog itself (never from the current
status, which can be set by anyone or drift), validates it against the shipped safety core using identities
verified from the changelog, and only then writes the settlement record - once, through an append-only
compare-and-swap receipt. If anything is missing, conflicting, or ambiguous, it BLOCKS. The repo is the
single source of truth; the tracker's terminal state is set afterwards by the outbound projection (W3), so
the two can never disagree in a way that changes an outcome.

## Context

W5-logic of the approved human-decision surface (VEL-1), built and gate-proven ENTIRELY OFFLINE over a
deterministic fake tracker; the real-board changelog shape, actor attribution, and the agent's withheld
scopes are proven separately, with Dmitry, in WARP-0620 (Sol's live-sandbox requirement). It composes:
W2 (veldo.request/v1) as the thing being reconciled; W6 (authorization.is_authorized), which now REQUIRES
caller-supplied verified proposer and approver identities, so this module derives them from the attributed
changelog and lineage and passes them in (never trusting a self-declared request field); the frozen
two_key/policy_check/decision safety core, reused unchanged; and the shipped reconcile_promotions pattern
(tracker_bridge) it is a sibling of. The service account cannot be an assignee, so the trigger is inverted:
find work by the repo index + issue link + status query, never by assignee. There is no always-on listener.
