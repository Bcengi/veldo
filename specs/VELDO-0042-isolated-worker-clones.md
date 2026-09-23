---
schema: veldo.spec/v1
id: VELDO-0042
title: Isolated worker clones and pinned read-only shared object cache
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W27
plan_revision: 3
depends_on: [VELDO-0029, VELDO-0031, VELDO-0040]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/env_provision.py"
  - ".veldo/env_provision.py"
  - "packs/*/.veldo/env_provision.py"
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/control_clone*.py"
  - ".veldo/control_clone*.py"
  - "packs/*/.veldo/control_clone*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0042_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0042-isolated-worker-clones.md"
  - "specs/index.md"
  - "proof/VELDO-0042/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Each run gets an isolated clone at its accepted commit with no write access to
      authority metadata or other workers. Set and completeness: Provision two real clones while
      provisioner HEAD points elsewhere; compare tree identities and attempt actual writes to the
      other clone, store, keys and authority Git metadata under worker identities. Falsifier:
      Provision from current HEAD; the accepted-source tree comparison must fail.
    falsified_by: >
      Provision from current HEAD; the accepted-source tree comparison must fail.
  - id: AC2
    text: >
      Claim: Only named repository objects are exposed read-only and pinned while a clone uses them.
      Set and completeness: Enumerate reachable objects for accepted attachments, read them from the
      worker, try cache writes and try cat-file access to an unnamed repository; ordinary garbage
      collection must retain the live pinned objects. Falsifier: Pool unnamed repository objects
      into the worker alternate; the unnamed-object access check must fail.
    falsified_by: >
      Pool unnamed repository objects into the worker alternate; the unnamed-object access check
      must fail.
  - id: AC3
    text: >
      Claim: Ordinary clone cleanup releases its object pins only after its workers and consumers
      terminate. Set and completeness: Run a real child reading the clone, attempt cleanup while it
      is alive, then terminate it and retire the clone; inspect retained and released pins and
      distinct clone paths. Falsifier: Release a pin while its child still reads objects; the live-
      object availability check must fail.
    falsified_by: >
      Release a pin while its child still reads objects; the live-object availability check must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Isolated worker clones and pinned read-only shared object cache. Deliver the normal function needed by the running factory journey.

## Context

W27 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

C13 remains unchanged: other repositories are accessible only as contract-named, exact-
accepted-commit, read-only attachments. Another repository write requires its own admitted
unit. A cache alternate must not expose authority metadata or unnamed repositories.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: owner Telegram 28848 moves
recovery/robustness to Release 2. Drop AC3 and AC2 concurrent-GC recovery qualification;
retain accepted-commit clones, read-only named-repository access, and objects remaining
available while used. Removed recovery, durability and failure-matrix obligations belong to
Release 2; additional host/channel/version and full distribution breadth belongs to Release 4.
Normal function and the checks stated above remain Release 1.
