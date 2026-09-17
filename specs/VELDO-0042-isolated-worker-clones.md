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
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0029, VELDO-0031]
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
    Provisioning records identify accepted commit, clone identity, object-cache pin, worker OS
    identity, and retirement result.
  metrics: >
    Count active pins, refused mutable-cache access, missing accepted objects, failed isolation
    checks, and unreleased clone resources.
  traces: >
    Join admitted contract and claim generation to Git object resolution, clone creation, mount
    permissions, and pin release.
  error_taxonomy: >
    Distinguish unaccepted source, authority-path access, mutable alternate, missing pinned
    object, stale clone identity, and cleanup uncertainty.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Each run receives an isolated clone checked out at its explicit accepted commit, with
      no write access to authority metadata or other workers. Set: Two real git clones under
      worker identities, authority clone/common directory, claims, keys, database, and another
      worker clone. Completeness: Move the provisioner HEAD away from the accepted commit, create
      each run, and verify Git tree identity. Execute actual read/write and symlink-traversal
      attacks from workers against protected authority paths; repository object access must reveal
      no operational metadata or credentials. Falsifier: Provision from current HEAD instead of
      the accepted commit after HEAD moves; clones/accepted-source must detect the wrong tree.
    falsified_by: >
      Provision from current HEAD instead of the accepted commit after HEAD moves;
      clones/accepted-source must detect the wrong tree.
  - id: AC2
    text: >
      Claim: The shared cache exposes only read-only Git objects and pins every referenced object
      until all dependent clones retire. Set: Real Git alternates or an equivalently qualified
      sharing mechanism with concurrent clone provisioning, object reads, and git gc.
      Completeness: Enumerate accepted commit reachability with Git, race garbage collection and
      clone creation, and try worker writes to shared objects. Require all pinned object reads to
      succeed and cache bytes to remain unchanged, including during a worker build that creates
      local objects. Falsifier: Drop a live clone pin before running git gc on an otherwise
      unreachable accepted commit; clones/gc-pin must detect a missing running-checkout object.
    falsified_by: >
      Drop a live clone pin before running git gc on an otherwise unreachable accepted commit;
      clones/gc-pin must detect a missing running-checkout object.
  - id: AC3
    text: >
      Claim: Interrupted provisioning or retirement preserves pin and resource obligations and
      cannot silently reuse another clone path. Set: Clone creation, mount setup, claim
      association, cleanup, and pin-release durable boundaries. Completeness: SIGKILL the
      provisioner at each barrier, replace a fixture clone directory at the same path, then
      restart provisioning or retirement. Verify actual clone identity, conservative pin
      retention, and no pin release before containment and clone consumers are retired. Falsifier:
      Release the pin after parent exit while a real child still reads the clone;
      clones/retirement-pin must catch the premature release.
    falsified_by: >
      Release the pin after parent exit while a real child still reads the clone;
      clones/retirement-pin must catch the premature release.
required_evidence: [unit, integration]
rollback: >
  Stop provisioning, retain cache pins for live or uncertain clones, retire workers safely, and
  return to a previously qualified provisioning profile only through recorded activation.
---

## Intent

Provision workers from accepted Git commits in isolated clones with pinned, read-only shared objects.

## Context

Package B, W27 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R20, R25, R43, R45, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Writable shared objects or authority metadata could let one worker corrupt accepted source or another run. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Historical client migration and general source landing are excluded.

## Notes

D4 directly blocks replacing shared-worktree provisioning until Dmitry ratifies isolated clones and the cache. D1 is inherited from claims and routing; D3 blocks activation of the OS isolation profile. Existing fleet.WorktreeProvisioner and env_provision are the known integration sites, but only enrolled autonomous work crosses this new boundary. A read-only alternate must not expose the authority Git common directory as its mount.

