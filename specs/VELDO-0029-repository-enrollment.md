---
schema: veldo.spec/v1
id: VELDO-0029
title: Explicit repository enrollment and authority routing
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W14
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_enrollment*.py"
  - ".veldo/control_enrollment*.py"
  - "packs/*/.veldo/control_enrollment*.py"
  - "engine/.veldo/control_client*.py"
  - ".veldo/control_client*.py"
  - "packs/*/.veldo/control_client*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0029_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0029-repository-enrollment.md"
  - "specs/index.md"
  - "proof/VELDO-0029/*"
behavior_bearing: true
observability:
  logs: >
    Routing records identify requested domain, repository, store, host, generation, and enrolled
    clone identity.
  metrics: >
    Count authority-unavailable refusals, identity mismatches, relay authentication failures, and
    reenrollment requirements.
  traces: >
    Join signed enrollment command to persisted binding, IPC peer, relay command, and mutation
    receipt.
  error_taxonomy: >
    Distinguish unenrolled clone, wrong store, stale host binding, cross-domain request,
    unauthenticated relay, and unavailable authority.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Explicit signed enrollment binds repository UUID, domain UUID, store UUID, host
      identity, and generation; separate clones share one writable authority. Set: A real
      authority database and two disposable git clones plus a linked worktree, including clone
      replacement at the same path. Completeness: Race enrollment and mutation clients, inspect
      the sole stored binding, replace a clone directory with another clone, and require
      reenrollment before mutations. Corrupt each binding component independently and ensure no
      local claim or command ledger is created. Falsifier: Trust a reused clone path after
      replacing its repository identity; enrollment/replaced-clone must refuse its mutation.
    falsified_by: >
      Trust a reused clone path after replacing its repository identity; enrollment/replaced-clone
      must refuse its mutation.
  - id: AC2
    text: >
      Claim: Local authenticated IPC and remote authenticated SSH relay preserve command
      authentication and explicit workspace coordinates. Set: Every public routing API with
      current directory, imported module ROOT, and ambient repository environment pointed at a
      different real fixture repository. Completeness: Enumerate command API registrations,
      execute each applicable route through real sockets and a disposable SSH relay, and compare
      store and Git observations in both repositories. Wrong identity and valid transport with
      invalid command signature must refuse. Falsifier: Resolve a mutation target from module ROOT
      while a valid explicit command names the other repository; enrollment/ambient-root must
      detect the wrong-store write.
    falsified_by: >
      Resolve a mutation target from module ROOT while a valid explicit command names the other
      repository; enrollment/ambient-root must detect the wrong-store write.
  - id: AC3
    text: >
      Claim: An unreachable authority disables mutation and execution admission and permits only
      explicitly stale inspection. Set: Enrolled claim, command, dispatch-admission, and
      inspection clients after the authority socket closes or relay dies. Completeness: SIGKILL
      the authority or relay after enrollment, drive all registered mutation clients, and compare
      local files and process census; require AUTHORITY_UNAVAILABLE with service identity and last
      watermark, no auto-start, no fallback database, and labeled stale reads. Falsifier: Fall
      back to a clone-local claim ledger after socket loss; enrollment/unavailable-claim must
      detect the unauthorized local claim.
    falsified_by: >
      Fall back to a clone-local claim ledger after socket loss; enrollment/unavailable-claim must
      detect the unauthorized local claim.
required_evidence: [unit, integration]
rollback: >
  Disable enrolled writes and retain the signed binding and stale inspection snapshot; changing
  authority requires an authorized migration or restoration.
---

## Intent

Route every enrolled clone to one explicit authority without allowing local fallback or ambient repository selection.

## Context

Package B, W14 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R20, R26, R53-R54, R57, R75. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Service installation belongs to W32 and worker clone provisioning to W27; no cross-domain transaction is introduced.

## Notes

D1 is inherited through W8; D3 blocks later service activation, and D4 blocks replacing worker provisioning but does not authorize route inference. Use distinct throwaway repositories for wrong-root attacks. SSH is a command relay to IPC, not a new network application server. Historical migration and activation receipts remain H work.

