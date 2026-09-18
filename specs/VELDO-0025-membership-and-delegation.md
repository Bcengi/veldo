---
schema: veldo.spec/v1
id: VELDO-0025
title: Authenticated membership and scoped delegation
status: shipped
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W10
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
placement: [engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_membership*.py"
  - ".veldo/control_membership*.py"
  - "packs/*/.veldo/control_membership*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - ".veldo/architecture.yaml"
  - "scripts/suites/*_veldo_0025_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0025-membership-and-delegation.md"
  - "specs/index.md"
  - "proof/VELDO-0025/*"
behavior_bearing: true
observability:
  logs: >
    Authentication records identify command digest, verified principal, membership and delegation
    versions, and rejected scope.
  metrics: >
    Count signature mismatches, possession failures, stale delegations, and refused principal
    substitutions.
  traces: >
    Join OpenSSH envelope verification to the exact executed command and its journaled membership
    transition.
  error_taxonomy: >
    Distinguish digest mismatch, unknown key, failed possession, transport-only identity, expired
    delegation, and unsatisfied named-principal requirement.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: OpenSSH-envelope Ed25519 verification recomputes the canonical digest of the actual
      operation, target, and complete parameters before executing an administrative command. Set:
      Every field in the VELDO-0020 envelope, including enrollment public key, domain, repository,
      store, command ID, request revision, nonce, expiry, and membership and delegation versions.
      Completeness: Use real ssh-keygen signatures and command processes over real SQLite; mutate
      each signed field and each operation parameter while retaining the original envelope.
      Require no membership change on failure and include authenticated SSH transport with a bad
      command signature. Falsifier: Bypass command-digest recomputation and substitute an
      enrollment public key under the original valid signature; membership/key-substitution must
      refuse.
    falsified_by: >
      Bypass command-digest recomputation and substitute an enrollment public key under the
      original valid signature; membership/key-substitution must refuse.
  - id: AC2
    text: >
      Claim: Membership changes require active scoped authority and key-possession proof, and
      preserve the accepted bootstrap and separation policy. Set: People, service, policy, and
      invocation principals across enrollment, role change, and delegation grant commands in the
      store. Completeness: Derive command/principal coverage from the authority registry; race two
      role changes against one version and SIGKILL after acceptance before reply. Assert one
      transition, unchanged historical authority, and no agent or service self-enrollment; absent
      additional named authorities leave their assignments blocked. Falsifier: Allow a service
      principal to grant itself membership during the competing-role-change test;
      membership/self-grant must detect the unauthorized stored role.
    falsified_by: >
      Allow a service principal to grant itself membership during the competing-role-change test;
      membership/self-grant must detect the unauthorized stored role.
  - id: AC3
    text: >
      Claim: Delegated use respects all role, named-principal, actor-kind, quorum, independence,
      scope, and expiry predicates conjunctively. Set: Persisted delegations for administrative
      services and enrolled-channel assertions, including distinct principal identity across
      multiple channels. Completeness: Exercise each predicate with a real signed command, current
      stored delegation, and a single invalidated field; race delegation supersession against
      acceptance and query committed outcomes. Channel fixtures exercise policy consumption only.
      Falsifier: Cache delegation authority across its committed supersession and accept a stale
      signed command; membership/stale-delegation must reject it.
    falsified_by: >
      Cache delegation authority across its committed supersession and accept a stale signed
      command; membership/stale-delegation must reject it.
required_evidence: [unit, integration]
rollback: >
  Disable new membership writes while retaining accepted versions and verification keys; supersede
  mistaken grants through authorized records rather than editing history.
---

## Intent

Authenticate administrative commands and persist only membership and delegation changes authorized by the accepted policy.

## Context

Package B, W10 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R20, R36-R38, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Command or principal substitution could grant unauthorized membership and delegation. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Key custody is W12; revocation delivery is W11; no live channel or additional person is enrolled here.

## Notes

D1 transitively blocks the backing store through W8; no membership service can activate before that choice and Package A policy are accepted. Only Dmitry is a named initial authority. Test keys represent disposable fixture principals and enroll nobody in this repository. Preserve the owner bootstrap instead of inventing a two-person enrollment rule. Live platform attribution and channel enrollment remain E.

