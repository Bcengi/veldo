---
schema: veldo.spec/v1
id: VELDO-0117
title: The authority rejects conflicting store bindings for one domain
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0029, VELDO-0115]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_enrollment.py"
  - "engine/.veldo/control_enrollment.py"
  - ".veldo/control_client.py"
  - "engine/.veldo/control_client.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/control_store.py"
  - "scripts/suites/46_veldo_0029_enrollment.py"
  - "scripts/suites/*_veldo_0117_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0117-authority-domain-store-uniqueness.md"
  - "specs/index.md"
  - "proof/VELDO-0117/*"
behavior_bearing: true
observability:
  logs: >
    Name domain, committed store identity, proposed store identity and the authority's conflict decision without exposing signing material.
  metrics: >
    Count accepted matching enrollments and domain_store_conflict refusals.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish domain_store_conflict from invalid binding signature, stale generation and cross-domain request.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: One domain has one authoritative store identity; a valid signed binding naming another store is refused by the authority before mutation.
      Set: Two independent clones with different Git common directories and clone UUIDs, valid same-domain bindings, and unequal store UUIDs and/or canonical store locations; exercise both enrollment admission and signed mutation.
      Completeness: Generate the equality product of domain/store UUID/canonical location, holding signatures and generations valid; require matching bindings to work and each same-domain conflict to return domain_store_conflict with no accepted transaction in either store. Validate at the authoritative registration/judgment boundary even when a clone-side resolver returns the conflicting target.
      Refutation: enrollment/authority-refuses-domain-store-conflict is false if any conflicting binding mutates a store or the decision exists only in clone code.
    falsified_by: >
      Remove the authority's comparison of proposed store identity against the domain's committed store identity; enrollment/authority-refuses-domain-store-conflict must turn red.
  - id: AC2
    text: >
      Claim: Concurrent competing bindings cannot establish two stores for the same domain.
      Set: Two valid conflicting proposals racing to register an initially unbound domain, both arrival orders and a barrier forcing overlapping registration attempts.
      Completeness: The authority serializes the domain-to-store decision atomically in its durable registry. For each schedule exactly one store wins, the loser receives domain_store_conflict, and readback through both clients yields the same winning identity; use a different-domain pair as a positive control.
      Refutation: enrollment/one-domain-one-winner is false if both conflicting registrations succeed or a partial identity becomes visible.
    falsified_by: >
      Make registration check and insertion separate non-atomic operations; enrollment/one-domain-one-winner must turn red under the forced overlap.
  - id: AC3
    text: >
      Claim: The chosen domain/store identity survives authority restart and is not replaced by the next clone's binding.
      Set: Every winning registration from AC2, authority stop/restart, then matching and conflicting proposals in both orders; canonical aliases to the same store remain matching.
      Completeness: Use the VELDO-0115 persistent stores and new authority process, read the committed domain record before and after each proposal, and require exact identity preservation with matching success and conflicting refusal.
      Refutation: enrollment/domain-binding-survives-restart is false if restart permits another store or rejects the same canonical store merely because its path spelling differs.
    falsified_by: >
      Initialize the domain registration map empty on authority restart instead of loading its committed record; enrollment/domain-binding-survives-restart must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Make domain-wide store uniqueness an authority-owned invariant rather than a coincidence of matching clone bindings.

## Context

VELDO-0029 AC1 and proof/VELDO-0029/README.md:106-110 demonstrate only independently signed matching bindings. Conflicting bindings need an authoritative decision that clone-local validation cannot supply.

## Out of scope

Store migration or administrative rebinding, multi-authority consensus, transport implementation and a second real-store fixture.

## Notes

The operator-configured authority registration boundary owns the durable domain-to-store map; a clone cannot create or overwrite it by presenting a signature. The first binding is established only through authorized registration, not first arbitrary mutation. A second authority instance must consult the same authoritative domain registration or refuse to serve that domain; isolated writable maps cannot satisfy this contract. Same canonical store aliases are not conflicts, but two distinct database files with one UUID are. VELDO-0115 supplies process/store setup and independent readback.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
