---
schema: veldo.spec/v1
id: WARP-0705
title: Fleet environment provisioning - shared read-only deps attached once, isolated write layers, never a wholesale copy
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y5
plan_revision: 2
depends_on: [WARP-0703]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A repo declares each dependency's sharing mode in a fleet env definition
      (.veldo/fleet_env.json - ephemeral, or shared_ro with an optional capability tag and a
      write_layer strategy), and a resolver turns a build's declared needs into a provisioning
      plan honoring the modes - an ephemeral dep to a fresh per-build env, a read use of a
      shared_ro dep to a read-only attach, and a MUTATING use of a shared_ro dep to an isolated
      write layer (schema, copy-on-write clone, or fixture). There is deliberately NO
      wholesale-copy action, so a heavy dataset is never duplicated.
  - id: AC2
    text: A shared_ro dependency is REF-COUNTED across the whole fleet - the first worker to
      need it brings it up exactly once, every other worker attaches to the same instance, and
      it is torn down only when the LAST worker releases it - so two concurrent workers never
      bring up two copies of a 75-million-row dataset. The ref count is mutated atomically
      (reusing the claim ledger's hardened per-unit lock), and a selftest with many
      barrier-synchronized concurrent workers asserts exactly-once bring-up and last-out teardown.
  - id: AC3
    text: A dependency may declare a capability tag; the resolver refuses to plan a build that
      needs a capability-gated dep on a worker that does not advertise the tag (reusing the
      claim ledger's capability match), so the heavy dataset's dep only provisions where it is
      mounted and never elsewhere; with the capability the same dep resolves (non-tautological).
  - id: AC4
    text: The actual bring-up, attach, write-layer, ephemeral provision, and teardown are
      delegated to an injected FleetEnvBackend seam (a real backend runs docker or a database
      or a copy-on-write clone; a fake drives the gate with no external dependency), and a
      provision() front door resolves the plan (validating before any side effect) and returns
      a lease whose teardown() reverses exactly what was provisioned - dropping the fleet ref
      count for shared deps and tearing down the per-build write layers and ephemeral envs. A
      backend failure PARTWAY through provisioning tears down the partial lease and re-raises,
      so it never leaks a fleet ref count (which has no TTL to reclaim it) or a per-build env.
  - id: AC5
    text: A selftest over the fake backend proves the control logic and its non-tautology - the
      mode resolution (ephemeral / shared read / mutating write-layer), a mid-provision backend
      failure that re-raises and leaks no shared ref, the capability
      refuse-vs-grant, the refusal of a mutating shared use with no write_layer and of an
      undeclared dep, the barrier-synchronized exactly-once bring-up, and a full provision +
      teardown lease - and the full gate is GREEN.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/fleet_env.py, a selftest block, one capability
  entry (both copies), and the WARP-0705 spec; no protected path; the control logic is a seam
  with the real infra ops in FleetEnvBackend, and the selftest runs over a fake backend.
---

## Intent

Make the fleet safe to run against heavy shared data. A dozen workers building the places
service must not each deploy their own copy of a 47.9-million-POI database; the shared
read-only dataset is brought up once and attached by all, while a build that must MUTATE gets
a cheap isolated write layer, not a wholesale copy. Which machine can run a build against the
heavy dep is decided by capability, so the dataset is provisioned only where it is mounted.

## Context

Y5 of PLAN-0007, on the worker loop (WARP-0703) and the WARP-0406 single-env EnvProvisioner
seam that it extends. It reuses the claim ledger (WARP-0701, hardened by WARP-0710) twice: the
capability match to gate a heavy dep, and the per-unit lock to mutate the shared-dep ref count
atomically so two workers never bring up two copies. The isolated-write-layer strategies
(schema, copy-on-write clone, fixture) and the ephemeral path are the backend's to implement;
this item is the definition, the resolver, the ref count, and the seam.

## Notes

The env definition is .veldo/fleet_env.json (structured config, stdlib json, nested per-dep
objects) rather than the YAML-ish front matter used for prose specs. The resolver validates
before any side effect (unknown dep, bad mode, missing capability, mutate-without-write-layer
all raise before provisioning), so a bad plan never half-provisions. The shared-dep ref count
holds the per-unit lock across the backend bring-up/teardown so those run exactly once even
under contention; that means a slow bring-up serializes other acquirers of the SAME dep, which
is correct (they must wait for it to be up before attaching) and never blocks acquirers of a
different dep (distinct deps use distinct lock files). Provisioning across separate hosts (a
dep mounted on one machine only) is expressed by the capability tag; cross-host attach
transport is the backend's and the launcher's concern (Y7).
