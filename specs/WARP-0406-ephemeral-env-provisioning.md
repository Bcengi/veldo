---
schema: veldo.spec/v1
id: WARP-0406
title: Ephemeral environment and fixture provisioning (X6 of PLAN-0004)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0004
work: X6
plan_revision: 3
human_approval: not_required
protected_paths: []
required_evidence: [unit, operational]
acceptance_criteria:
  - id: AC1
    text: An EnvProvisioner seam ships at .veldo/env_provision.py with the lifecycle
      a runner drives - create() returns an opaque handle, seed(handle, fixtures)
      applies data, observe(handle) reads the current state back, paths(handle)
      returns the access coordinates (a url or paths), and teardown(handle) removes
      the environment. The base class owns the lifecycle and leak accounting so
      every backend upholds the guarantees identically; a subclass implements only
      the surface primitives (_create, _seed, _observe, _paths, _teardown,
      _is_live). Stdlib only, no third-party import, no new service.
  - id: AC2
    text: The four guarantees a runner leans on are enforced and observed, not
      assumed. An environment is CLEAN on create (observe right after create shows
      no leftover state); seeding is APPLIED and OBSERVABLE (observe after seed
      shows the seeded rows); teardown is IDEMPOTENT (a second teardown does not
      error) and LEAVES NOTHING (observe after teardown fails loud with a gone
      error, never returns stale seeded data); and a create-without-teardown is
      DETECTABLE - leaked() names every environment that is still live at the
      surface, so a leaked environment is a named failure, not a silent resource
      left running. Leak and gone detection re-observe the real surface via
      _is_live, never trust a flag the base set, so a backend that pretends to
      tear down while leaving the resource is still caught.
  - id: AC3
    text: A deterministic in-memory FakeProvisioner ships for the gate. Its surface
      is a dict of per-environment buckets; create allocates a fresh empty bucket,
      seed appends fixture rows, observe reads them, teardown deletes the bucket,
      and liveness is bucket existence. A runner-facing harness,
      verify_provisioner(provisioner, fixtures), drives create -> assert clean ->
      seed -> observe seeded -> teardown -> assert gone, plus an idempotent double
      teardown and a post-teardown leak check, and returns a report naming each
      guarantee. It exists with no external dependency (no network, no container,
      no live service).
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py against the fake
      with real observations, and the test proves it is NOT a tautology. A
      provisioner that IGNORES seeding fails the seed_observable check; a
      provisioner that PRETENDS to tear down (a no-op teardown leaving the surface)
      fails the gone_after_teardown and no_leak_after_teardown checks and is named
      a leak. The happy path is driven end to end (clean, seeded, gone, idempotent
      double teardown, leak detected on a create-without-teardown then cleared on
      teardown). All prior selftest cases keep passing and the gate stays green.
  - id: AC5
    text: A live reference implementation, ContainerEnvProvisioner, backs an
      ephemeral environment with a container the adopting repo names (its own image
      and seed). It FAILS LOUD - raises EnvProvisionUnavailable - when no container
      runtime (docker or podman) is on PATH, so an absent surface is a named error,
      never a silent skip that reports clean against nothing. The runtime finder
      and the process runner are injectable seams so the fail-loud guard and the
      container lifecycle (create makes the surface live, teardown removes it, a
      dishonest teardown leaves a detected leak) are proven in the selftest with a
      fake runtime and no live daemon.
  - id: AC6
    text: capabilities.yaml (the repository instance and the plugin template, kept
      byte-identical) declares ephemeral_env_provisioning with status reference and
      an honest note - a real ephemeral environment needs a surface (a container
      runtime and an adopting repo's own image and fixtures) the veldo home repo
      lacks, so the home gate does not run the live path; the control logic is
      fake-tested and the live path fails loud. The deliverable is generic (zero
      company, product, or person names beyond the standard owner field and zero
      absolute host paths) and hygienic (ASCII only, no em or en dash, no double
      hyphen). The specs index regenerates to include this spec and the full gate
      (lint, unit, generated, docs, template sync, secret scan, contract
      validation) stays green.
rollback: git revert; X6 is additive - a new stdlib module .veldo/env_provision.py,
  a selftest block, one capabilities entry (instance and template), and this spec.
  It touches no protected path and no synced core (validate.py, policy_check.py,
  update_index.py, veldo-guard.sh) and adds no new required CHECK_ slot, so
  reverting removes the capability and its unit block with no effect on any running
  gate; prior selftest cases are unchanged.
---

## Intent

PLAN-0004 turns VELDO's events into operations. F3's runners drive a surface, and
a surface is only trustworthy if it is clean when the run starts and gone when it
ends. X6 gives the runners that surface: an EnvProvisioner seam that spins a clean
environment with seeded data to drive, then tears it down, and that guarantees the
four properties a runner leans on regardless of which backend supplies the surface
- clean on create, seeding observable, teardown idempotent and complete, and a
leaked environment named rather than left running silently. The value is the
guarantees, not any one surface, so the seam is the deliverable and the surfaces
(an in-memory fake for the gate, a container for the live reference) plug into it.

## Context

X6 of PLAN-0004, feature F3 (observability and ops), pulled against plan revision
3, with no dependency. It follows the shipped pattern: an additive stdlib module,
control logic gate-tested in the unit slot with no live surface, and an honest
capabilities entry. The seam mirrors how the runner suite is built - a base owns
the invariant behavior and a subclass supplies the surface primitives - so an
adopting repo adds a backend (a database, a filesystem sandbox, a container) by
implementing six small methods and inherits the guarantees. The fake is the
gate-hermetic backend; the container provisioner is the live reference an adopting
repo wires to its own image.

## Out of scope

Running a live container in the home gate: the veldo home repo ships no image of
its own, which is exactly why the capability is reference and the live path fails
loud when the surface is absent. Orchestrating multiple coordinated environments,
a network fixture topology, or a hosting stack (proportionate: the seam plus two
backends is the need; more waits for measured demand). Wiring the provisioner into
any specific runner's gate slot - that is per-repo reference wiring, like the rest
of the suite.

## Notes

Why the guarantees are observed and not assumed: a provisioner that quietly drops
seeding, or a teardown that reports success while leaving a container running, is
the exact silent-green failure this seam exists to prevent, so cleanliness,
seeded-ness, gone-ness, and leaks are all read back from the real surface through
_is_live and observe, never inferred from a flag the base set. The selftest proves
this is not a tautology by mutating the fake two ways - one that ignores seeding
and one that only pretends to tear down - and asserting each fails the named check;
a provisioner that could only ever report a clean run is therefore impossible.

Why reference (not mechanical): a real ephemeral environment needs a surface the
veldo home repo does not have - a container runtime and an adopting repo's own image
and fixtures - so the honest evidence is the fake control-logic test plus the
live path's fail-loud guard, not a live container run. required_evidence is [unit,
operational]: unit is the selftest control-logic block; operational is the fake
driven end to end through the guaranteed lifecycle by the module's selfcheck.
capabilities.yaml states status reference, never mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest:
(1) observe right after create is empty (clean), observe after seed shows the
seeded rows, and observe after teardown raises the gone error rather than returning
stale data; (2) a create-without-teardown is named by leaked() and clears once torn
down; (3) the ignore-seeding mutation fails seed_observable and the pretend-teardown
mutation fails gone_after_teardown and no_leak_after_teardown; (4) the container
reference raises EnvProvisionUnavailable with no runtime on PATH and, under a fake
runtime, goes live on create, gone on honest teardown, and stays a detected leak on
a dishonest teardown.
