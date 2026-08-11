---
schema: veldo.spec/v1
id: WARP-0608
title: Tracker conformance - prove intake and the mirror end to end over the fake tracker
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W8
plan_revision: 1
depends_on: [WARP-0604, WARP-0605, WARP-0606, WARP-0607]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An end-to-end conformance (conformance_findings) drives the whole tracker surface over the
      deterministic FakeTracker with no live network - a ticket becomes a routing-resolved spec draft
      (intake), the spec's lifecycle mirrors onto its tracker child (spec mirror), and the plan builds
      its epic and children (epic mirror) - by COMPOSING the shipped pieces (routing, seam, intake,
      mirror), adding no new machinery. It returns a list of named findings; an empty list is
      conformance, and the good config conforms.
  - id: AC2
    text: RJ1, no rubber-stamp - a deliberately broken mapping FAILS the conformance BY NAME. A
      routing config whose prefix does not match the ticket, or a status_map missing the shipped
      mapping, each produces a named finding (non-empty), while the good config produces none, so the
      conformance has teeth rather than asserting success unconditionally.
  - id: AC3
    text: RJ2, the tracker never writes a definition - the whole journey mutates ONLY the tracker
      (every write op is a seam write, comment/set_status/create_or_update_epic/create_or_update_child)
      and NEVER the repository (the spec index and plan index it reads are byte-unchanged afterward),
      so the repository stays the single source of truth; a projection that wrote back into a spec or
      plan definition is surfaced as a named finding.
  - id: AC4
    text: Idempotency holds end to end - replaying the spec lifecycle stream records no new transition
      or comment and leaves the tracker state byte-identical, and the conformance reports a named
      finding if replay is not idempotent.
  - id: AC5
    text: The conformance is honest and non-tautological - the tracker capability entries are declared
      with valid statuses (mechanical for the gate-tested logic, reference for the live adapters), and
      a selftest drives conformance_findings so that the good config conforms (empty) and each broken
      config fails by name, and neutering a load-bearing piece turns the conformance red (mutation
      teeth), so a green result is earned, not assumed.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/tracker_conformance.py that composes the shipped tracker
  pieces, a selftest block owning RJ1 and RJ2, one capability entry (both capabilities.yaml copies),
  and this spec; no protected path; pure stdlib, no network.
---

## Intent

O4 wants the whole integration provable offline: the per-item selftests prove each piece, but the
plan is only done when the SURFACE is proven - a ticket flows in and becomes a spec, the spec's status
flows back onto the tracker, the plan builds the epic, and none of it lets the tracker become a second
source of truth. This is that proof, and it owns the two regression journeys the plan names (RJ1 the
conformance is real and fails on a broken mapping; RJ2 the tracker never writes a definition).

## Context

W8 of PLAN-0006, the last item, depends on both intake edges (W4, W7) and both mirror edges (W5, W6).
It is the release gate for the plan (require_all_work_shipped, require_full_regression). It adds no
new capability behavior; it COMPOSES the shipped pieces into one journey and asserts the invariants,
so it is a conformance harness, not new machinery (C3).

## Notes

conformance_findings(config) runs the journey over the FakeTracker and returns named findings; empty
is conformance. Every invariant fails by name - a broken routing or status mapping, a non-idempotent
replay, a write op outside the seam's set, or a mutated spec/plan index - so the selftest can assert
the good config conforms and a broken config fails named (the RJ1 non-rubber-stamp teeth), and the
one-way guard (RJ2) is the byte-unchanged spec and plan indices plus the seam-only write audit. The
journey deep-copies the indices it reads so the mutation guard is real. Pure stdlib, no network: the
live Jira and Confluence adapters are reference-wired and never run here; the FakeTracker is the whole
surface under test, which is the point of a vendor-neutral seam.

Boundary of the offline conformance: because the FakeTracker has no status vocabulary of its own, the
shipped-status check is self-referential (the child reaches whatever the config's status_map maps
shipped to), so a status_map that maps shipped to a name the real tracker would reject still conforms
here. That is correct by design (C5): validating that a mapped status name actually exists in a live
project is the reference-wired adapter's job, not the offline conformance. What the offline conformance
proves is the behavior the seam owns - routing, the mirror transitions and closing comment, idempotent
replay, and the one-way guarantee. The capability-honesty check binds each capability name to its
declared status on its own line, so a live adapter mislabeled mechanical fails the check.
