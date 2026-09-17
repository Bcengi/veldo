---
schema: veldo.spec/v1
id: VELDO-0095
title: Historical migration and atomic reader-writer cutover
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W80
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/version.py"
  - ".veldo/version.py"
  - "packs/*/.veldo/version.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/decision.py"
  - ".veldo/decision.py"
  - "packs/*/.veldo/decision.py"
  - "engine/.veldo/release_contract.py"
  - ".veldo/release_contract.py"
  - "packs/*/.veldo/release_contract.py"
  - "engine/.veldo/control_migration*.py"
  - ".veldo/control_migration*.py"
  - "packs/*/.veldo/control_migration*.py"
  - "engine/.veldo/control_client*.py"
  - ".veldo/control_client*.py"
  - "packs/*/.veldo/control_client*.py"
  - "scripts/check_install_and_run.py"
  - "scripts/suites/24_veldo_0007_install_and_run.py"
  - "scripts/suites/*_veldo_0095_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0095-historical-migration-atomic-cutover.md"
  - "specs/index.md"
  - "proof/VELDO-0095/*"
behavior_bearing: true
observability:
  logs: >
    Migration receipts list source record digests, accepted imports, unresolved identities, absent
    authority evidence, cutover watermark and writer fences.
  metrics: >
    Report inventory counts by historical record kind, authority gaps, legacy writer refusals and
    incomplete cutover attempts.
  traces: >
    Join original WARP/VELDO bytes through signed import disposition to one accepted snapshot and
    all routed reader/writer versions.
  error_taxonomy: >
    Distinguish missing historical approval, duplicate identity, live legacy writer, mixed reader
    generation and unaccepted worktree proposal.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Historical import inventories every record and fabricates no authority, identity or
      provenance. Set: Installed control_migration using release_contract.release_registry,
      plan.load_plan, tasks.read_sets, request.load_record, decision.load_record and
      version.provenance_report/installed_version. Completeness: Inventory specifications, plans,
      releases, behavior floors, tasks, common-dir claims/runs, requests, decisions and proof
      against actual files/registries in both directions. Include WARP/VELDO records, missing
      signatures, unversioned proof and unstamped installs. A signed migration receipt records
      accepted imports, unresolved records and missing historical authority; acceptance of bytes
      never fabricates signatures, admissions, reviewers, shipped events or new operational
      eligibility. Unmigrated tasks remain visible intake candidates excluded from autonomous
      dispatch. Falsifier: Assign the current install version to legacy unversioned proof during
      import; migration/no-invented-provenance must detect fabricated history.
    falsified_by: >
      Assign the current install version to legacy unversioned proof during import;
      migration/no-invented-provenance must detect fabricated history.
  - id: AC2
    text: >
      Claim: Cutover drains or fences legacy work and switches all enrolled readers and writers
      together. Set: control_migration cutover and control_client routing, including installed
      tasks.claim_task, claim.claim and plan.cmd_run_check consumers. Completeness: Derive
      reader/writer and active-worker inventory from installed registrations. Run old clients and
      real workers while cutting over, kill at each drain/fence/routing/pointer barrier and
      restart. Require either a coherent pre-cutover state with no new authority enabled or a
      coherent authoritative state; old enrolled writes refuse and never fall back to common-dir
      ledgers. All acknowledged commands meet D2. Falsifier: Allow an old tasks.claim_task client
      to write its local ledger after enrollment; migration/legacy-writer-fenced must detect a
      second authority.
    falsified_by: >
      Allow an old tasks.claim_task client to write its local ledger after enrollment;
      migration/legacy-writer-fenced must detect a second authority.
  - id: AC3
    text: >
      Claim: Only the materializer projects accepted documents and lifecycle at a declared
      watermark; installation cannot bypass cutover. Set: control_migration accepted-snapshot
      path, init_scaffold.scaffold/_lay/_write_stamp and version.drift over migrated installed
      artifacts. Completeness: Propose worktree edits to accepted specs, plans, requests and
      lifecycle while readers race a snapshot switch. Require immutable accepted bytes in
      store/replica, atomic complete projections and workers starting from the explicit accepted
      commit. Re-run scaffold from a newer pack; existing authored files/stamp remain and no
      migration or authority activation is inferred. Missing routing/materializer coverage blocks
      completion. Falsifier: Start a migrated worker from the provisioner current HEAD instead of
      the accepted commit; migration/accepted-source must detect execution of unaccepted bytes.
    falsified_by: >
      Start a migrated worker from the provisioner current HEAD instead of the accepted commit;
      migration/accepted-source must detect execution of unaccepted bytes.
required_evidence: [unit, integration, journeys]
rollback: >
  Stop cutover on unresolved state, retain original corpus and verified replica, and restore only
  a compatible fully fenced reader/writer generation.
---

## Intent

Adopt historical repositories through a signed, complete migration and one coherent authority cutover.

## Context

Package H, W80 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R54/R63 preserve historical evidence and retire legacy writers. A split authority or manufactured approval makes migration critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Renaming historical IDs, reconstructing nonexistent signatures, overwriting protected floor settlements and automatic live activation are excluded.

## Notes

D1 must ratify store authority and D2 acknowledgment before cutover; D3/D4 block worker fencing and accepted-source clone qualification. Dmitry must designate the operations/migration authority and explicitly dispose of unresolved authority gaps through an enrolled surface. These are R37/R64 rulings, not facts inferred from Git authorship. Original floor/settlement files are read as evidence, not edited; a required protected write needs a revised spec. Map control_migration and legacy routing before ready and inventory them via W30. Retain original corpus hashes and crash-state inventories so an import cannot silently lose an inconvenient record.
