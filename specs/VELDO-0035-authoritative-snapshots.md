---
schema: veldo.spec/v1
id: VELDO-0035
title: Complete read-set validation and authoritative snapshots
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W20
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_snapshot*.py"
  - ".veldo/control_snapshot*.py"
  - "packs/*/.veldo/control_snapshot*.py"
  - "engine/.veldo/control_readset*.py"
  - ".veldo/control_readset*.py"
  - "packs/*/.veldo/control_readset*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0035_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0035-authoritative-snapshots.md"
  - "specs/index.md"
  - "proof/VELDO-0035/*"
behavior_bearing: true
observability:
  logs: >
    Read-set refusals identify changed entity or collection, expected and observed version,
    digest, and snapshot watermark.
  metrics: >
    Count stale positive reads, conflicting insertions, unpublished snapshots, materialization
    failures, and cache refusals.
  traces: >
    Join accepted source commit and published journal watermark to input digests, transaction
    validation, and snapshot pointer switch.
  error_taxonomy: >
    Distinguish omitted read dependency, stale entity, changed collection, unpublished watermark,
    corrupt artifact, and partial materialization.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Commands validate complete entity and collection read sets inside the same
      transaction that commits their result. Set: Specifications, plans, releases, decisions,
      floors, policy, membership, admission, combined graph, roster, reservations, and receipts,
      including absence of blockers. Completeness: Compare the R70 input registry to real command
      instrumentation in control.sqlite3. A second process changes each input or inserts a blocker
      after the snapshot while holding project version fixed; all stale command commits must
      refuse with the changed subject named. Falsifier: Validate only project version while
      another process inserts a blocking dependency; snapshots/negative-read must reject the
      proposal.
    falsified_by: >
      Validate only project version while another process inserts a blocking dependency;
      snapshots/negative-read must reject the proposal.
  - id: AC2
    text: >
      Claim: Published snapshots bind domain, repository, accepted Git commit, journal sequence,
      published watermark, and every input version and digest. Set: Real stored documents and Git
      objects consumed by snapshot clients, including stale checkout bytes and missing or corrupt
      accepted artifacts. Completeness: Construct snapshots through the store, edit the working
      checkout without acceptance, corrupt artifact bytes, and request an unpublished sequence.
      Read clients must use accepted immutable content or refuse, with no silent mutable-path
      fallback. Falsifier: Read the edited checkout specification instead of its accepted artifact
      digest; snapshots/checkout-substitution must detect the wrong bytes.
    falsified_by: >
      Read the edited checkout specification instead of its accepted artifact digest;
      snapshots/checkout-substitution must detect the wrong bytes.
  - id: AC3
    text: >
      Claim: Only the materializer exposes whole immutable snapshot directories through an atomic
      current-pointer switch; interrupted publication is recoverable. Set: Document and legacy
      status/event projections at one watermark, using real filesystem readers racing a
      materializer process. Completeness: SIGKILL before directory completion, before pointer
      switch, and after switch before acknowledgment; continuously read all projected members and
      compare their watermarks and digests. Restart must expose either the old complete corpus or
      the new complete corpus and reconcile pending work. Falsifier: Switch the current pointer
      before the last projection file is durable, then kill the materializer;
      snapshots/partial-corpus must detect a mixed or incomplete view.
    falsified_by: >
      Switch the current pointer before the last projection file is durable, then kill the
      materializer; snapshots/partial-corpus must detect a mixed or incomplete view.
required_evidence: [unit, integration]
rollback: >
  Keep the last verified snapshot pointer, pause new publication, retain pending directories and
  journal obligations, and rebuild only from verified accepted history.
---

## Intent

Validate every decision input and publish coherent immutable snapshots so stale proposals cannot commit.

## Context

Package B, W20 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R14, R22, R30, R54, R57, R70-R71. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Incomplete read sets or mixed snapshots could commit proposals after their authority or prerequisites changed. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Project-manager scheduling, live decision settlement, and floor completion-reader rewiring belong to later packages.

## Notes

D1 blocks backing-store implementation through W8; D2 governs which journal watermark is published, so snapshot clients cannot consume an unacknowledged tail. This item implements reusable transactional read-set checks and materialization; C wires every floor entry to the shared eligibility service. Collection versions must cover negative predicates and reverse dependency closure, not only explicitly fetched rows.

