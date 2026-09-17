---
schema: veldo.spec/v1
id: VELDO-0096
title: Clone and enrolled-principal adoption qualification
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W81
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095]
placement: [distribution, contracts, fleet, engine]
protected_paths: []
footprint:
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/version.py"
  - ".veldo/version.py"
  - "packs/*/.veldo/version.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/control_adoption_journey*.py"
  - ".veldo/control_adoption_journey*.py"
  - "packs/*/.veldo/control_adoption_journey*.py"
  - "engine/.veldo/control_client*.py"
  - ".veldo/control_client*.py"
  - "packs/*/.veldo/control_client*.py"
  - "scripts/check_install_and_run.py"
  - "scripts/suites/*_veldo_0096_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0096-clone-principal-adoption-qualification.md"
  - "specs/index.md"
  - "proof/VELDO-0096/*"
behavior_bearing: true
observability:
  logs: >
    Adoption qualification records installed artifact digest, domain/repository UUIDs, clone
    coordinates, principal enrollment and authority generation.
  metrics: >
    Count clone/principal/profile cases, stale-generation refusals, independent claim winners and
    authority-unavailable outcomes.
  traces: >
    Trace signed fixture enrollment through explicit clone routing to authoritative
    claim/assignment and retained results after replacement.
  error_taxonomy: >
    Distinguish wrong domain, wrong repository, unenrolled principal, stale clone coordinates,
    revoked delegation and unavailable authority.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A replacement clone uses the same explicit authority and cannot create local
      operational truth. Set: scripts/check_install_and_run.py.install_and_run and installed
      control_client routing with claim.claim/tasks.claim_task, under each composed pack.
      Completeness: Derive the nonempty pack/profile matrix from publisher output and W79
      inventory. Install into disposable repositories, enroll explicit
      domain/repository/store/host IDs, replace clone paths and require explicit client-clone
      reenrollment before mutation; vary current directory/environment/module ROOT. Race claims
      from two clones; require one durable winner and correct explicit routing. An absent
      authority reports AUTHORITY_UNAVAILABLE with watermark/start procedure and grants no local
      claim. Falsifier: Fall back to a clone-local claim ledger when the authority is unavailable;
      adoption/no-local-fallback must detect a granted claim.
    falsified_by: >
      Fall back to a clone-local claim ledger when the authority is unavailable;
      adoption/no-local-fallback must detect a granted claim.
  - id: AC2
    text: >
      Claim: Another enrolled fixture principal can act only within its signed scope and cannot
      manufacture additional real authority. Set: Installed authorization.is_authorized and B
      enrollment command verification with E enrolled signed CLI decisions. Completeness: Use real
      Ed25519 fixture keys and isolated enrollment records. Change operation, target, public key
      and other parameters under retained signatures; recomputed canonical command digests must
      refuse. Exercise principal/delegation revocation, wrong domain/repository, quorum across
      multiple channels and authorized current decisions. Fixture identities remain isolated from
      real membership; Git identity or copied checkout keys grant nothing. Falsifier: Ignore an
      enrollment public-key substitution under an unchanged signature;
      adoption/enrollment-key-binding must detect the substituted enrolled principal.
    falsified_by: >
      Ignore an enrollment public-key substitution under an unchanged signature;
      adoption/enrollment-key-binding must detect the substituted enrolled principal.
  - id: AC3
    text: >
      Claim: Restart and explicit authority replacement preserve acknowledged results and fence
      the old generation. Set: Installed control_client/recovery path with pack.engine_drift,
      version.installed_version and B leadership/replica restoration. Completeness: For each
      qualified profile, restart normally and replace the authority from its verified signed
      replica with independent old/new client processes. Preserve domain identity, published
      watermark, command results, reservations and pending effects. Old generation and revoked
      principals cannot dispatch or publish; restart cannot reenroll a clone or reenable an
      explicit operations stop. Record actual installed paths and versions for both generations.
      Falsifier: Accept an old-generation dispatch after replacement has advanced the authority
      generation; adoption/stale-generation must detect renewed old authority.
    falsified_by: >
      Accept an old-generation dispatch after replacement has advanced the authority generation;
      adoption/stale-generation must detect renewed old authority.
required_evidence: [unit, integration, journeys]
rollback: >
  Withdraw adoption qualification and stop the affected authority generation; retain enrollment,
  clone mappings and verified replica for authorized repair.
---

## Intent

Prove that installed adopters can change clones and enrolled operators without duplicating authority or losing history.

## Context

Package H, W81 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R20, R36, R63 and R75 qualify cross-clone routing and scoped fixture enrollment. False adoption proof can ship unsafe authority routing, warranting high risk. Risk is high; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Enrollment of real additional authorities, automatic host failover and changes to another live worktree are excluded.

## Notes

D1/D2 block replica-backed replacement, D3 the qualified service lifecycle and D4 isolated clone adoption. Dmitry must designate the real operations authority before live adoption; fixture principals establish protocol behavior only. W80 migration must pass before testing enrolled historical clients. Put control_adoption_journey in distribution with contract/fleet/engine consumers and W30 inventory before ready. Preserve actual executed installed paths and signed command mutation evidence, with no private key bytes in proof. Unknown target effects remain stopped under the original identity.
