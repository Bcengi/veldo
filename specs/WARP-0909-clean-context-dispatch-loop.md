---
schema: veldo.spec/v1
id: WARP-0909
title: Clean-context dispatch loop - bound the orchestrator's memory
status: shipped
risk: standard
owner: Dmitry Grinberg
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      docs/method.md documents a CLEAN-CONTEXT DISPATCH rule for running many
      specs in one session (an autonomous or multi-spec loop): each spec's build
      and review MUST be performed in a dispatched fresh sub-context (a sub-agent),
      which returns ONLY a compact receipt; the long-lived orchestrator MUST NOT
      perform per-spec heavy work inline, and MUST NOT ingest a sub-context's full
      transcript into its own context. The rule names its rationale (the
      2026-07-19 OOM: one orchestrator session drove item after item inline and
      grew to ~17.8 GB before the kernel killed it).
  - id: AC2
    text: >
      packs/claude/skills/run/SKILL.md makes the review step an explicit fresh-context
      sub-agent dispatch with parity to the build step (both name their sub-agent),
      states that the orchestrator retains only each step's receipt (not its
      transcript), and points to the method's loop rule for chaining many specs.
  - id: AC3
    text: >
      A mechanical receipt projection exists at the dispatch boundary: a pure
      function projects a dispatch outcome to a bounded receipt carrying only an
      allowlisted set of small summary fields (at minimum spec, kind, ok, status,
      and where present verdict/commit/proof_digest/gate/halted_at/reason) and
      NEVER a build transcript, file contents, or full review reasoning. It is the
      value the loop retains per spec.
  - id: AC4
    text: >
      A selftest enforces the receipt contract with teeth: it asserts the
      projected receipt keys are within the allowlist and its serialized size is
      under a fixed small bound, and a mutant that smuggles a bulky transcript or
      the full nested result through the receipt FAILS the selftest.
  - id: AC5
    text: >
      The seam docstrings in .veldo/executor.py (LoopSteps.build and .review) and
      .veldo/dispatch.py state the clean-context/receipt contract explicitly (the
      delegated step runs in a fresh sub-context and returns a receipt, not a
      transcript the orchestrator must hold).
  - id: AC6
    text: >
      All engine copies stay byte-identical. Every edited file matched by
      ENGINE_GLOBS (scripts/selftest.py, .veldo/*.py, .veldo/*.yaml) is re-synced
      into engine/.veldo and all 7 packs; check_template_sync.sh,
      check_pack_drift.py and scripts/selftest.py all pass; no protected path is
      touched.
required_evidence: [unit]
rollback: >
  Revert the commit. The change is documentation, one additive pure function, one
  additive selftest, and docstrings; it adds no behavior to the mechanical
  dispatch and can be removed with no migration.
---

## Intent

Make VELDO's own loop procedure prevent the failure that just happened: a single
long-lived orchestrator session that drives spec after spec inline accumulates
every spec's build context plus every review sub-agent's transcript in one
process, growing without bound until the OS out-of-memory killer terminates it.
On 2026-07-19 that process (Claude Code) reached ~17.8 GB and was killed, taking
the terminal down with it.

The cure is the clean-context handoff VELDO's own research already endorses and
that its single-spec design already uses (veldo-implementer and veldo-reviewer are
sub-agents): apply it to the LOOP. The orchestrator must be a THIN DISPATCHER -
it hands each spec's heavy work to a fresh sub-context that returns a small
receipt, and keeps only the receipt. Its memory footprint then stays flat across
any number of specs instead of the sum of all of them.

## Context

- The single-spec run skill already dispatches build to the veldo-implementer
  sub-agent (step 2). Review (step 5) is a fresh-context verdict but the skill
  does not state it is a dispatched sub-agent nor that only the receipt is kept.
- There is NO documented procedure for the multi-spec / autonomous loop that
  keeps the orchestrator thin. That gap is what the fleet build exercised.
- The mechanical dispatch (.veldo/dispatch.py Dispatcher.dispatch) already returns
  a summary dict rather than a transcript, but it can currently pass the full
  nested executor `result` through, so "bounded receipt" is not yet enforced. A
  pure receipt projection plus a teeth-test codifies the boundary so a future
  change cannot silently reintroduce unbounded orchestrator retention.
- ENGINE_GLOBS makes scripts/*.py, .veldo/*.py and .veldo/*.yaml byte-identical
  across engine and all 7 packs; any edit there must be re-synced.

## Out of scope

- No change to the mechanical dispatch's routing, status flips, gate/proof/land
  behavior, or the fleet launcher/governor.
- The external-supervisor decision (D1) and PLAN-0009 W8 release are separate and
  untouched here.
- No empirical RSS/soak test is required for this spec (it may follow); the teeth
  here are the mechanical receipt-contract selftest.

## Notes

- Place the receipt projection where the loop layer can reuse it (work.py loop or
  alongside dispatch.py); keep it a pure function so the selftest drives it
  directly with fakes and no live agent.
- The receipt allowlist should be small and explicit; prefer failing closed (an
  unknown large field is a violation) so the teeth actually bite.
- Follow the byte-identical sync discipline and re-run check_template_sync.sh and
  check_pack_drift.py before proof, per the W5/W6 lesson.
