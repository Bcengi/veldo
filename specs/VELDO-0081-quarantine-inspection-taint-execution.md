---
schema: veldo.spec/v1
id: VELDO-0081
title: Quarantine inspection, taint propagation, and bounded execution
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W66
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/env_provision.py"
  - ".veldo/env_provision.py"
  - "packs/*/.veldo/env_provision.py"
  - "engine/.veldo/control_quarantine*.py"
  - ".veldo/control_quarantine*.py"
  - "packs/*/.veldo/control_quarantine*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/runtime/quarantine*"
  - ".veldo/runtime/quarantine*"
  - "packs/*/runtime/quarantine*"
  - "scripts/suites/*_veldo_0081_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0081-quarantine-inspection-taint-execution.md"
  - "specs/index.md"
  - "proof/VELDO-0081/*"
behavior_bearing: true
observability:
  logs: >
    Inspection records carry input digest/type/source, size, expansion count/depth/ratio,
    executable flag, scanner identity/version and secret/malware/taint results.
  metrics: >
    Count unknown inspections, tainted derivatives, denied network requests and resource-limit
    terminations.
  traces: >
    Trace external material through extraction/derivation to bounded mounts, observed execution
    and admission refusal or qualified evidence.
  error_taxonomy: >
    Distinguish unavailable scanner, unknown trust, archive overrun, taint loss, forbidden mount,
    network refusal and host resource exhaustion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every external input is inspected before model or execution consumption and retains
      taint through derivation. Set: control_quarantine ingress for reproductions, attachments,
      design files, dependency manifests, archives, scripts, production alerts and generated
      fixtures. Completeness: Compare all registered consumers and input types to the R67
      field/inspection matrix. Drive real local inspection adapters, extraction, copying and
      generated derivatives; require scanner identity/version and explicit failed automatic
      admission for unknown or unavailable results. Clean scans cannot authorize embedded
      instructions. Falsifier: Treat an unavailable malware scanner as clean;
      quarantine/unavailable-scanner must detect permission to consume unqualified material.
    falsified_by: >
      Treat an unavailable malware scanner as clean; quarantine/unavailable-scanner must detect
      permission to consume unqualified material.
  - id: AC2
    text: >
      Claim: Archive processing enforces every expansion bound before excess material becomes
      consumable. Set: control_quarantine extraction at 1 GB, 10000 files, depth 10 and ratio
      100:1, including signed exceptions. Completeness: Derive exact units and counting semantics
      from the accepted A contract before ready, then exercise below/at/above each limit with real
      nested archives and path escapes. Require named refusal; an exception must bind an enrolled
      authority decision and demonstrably narrower execution environment, never an unchecked
      override. Falsifier: Disable the archive nesting-depth check; quarantine/depth-limit must
      detect consumable output from depth 11.
    falsified_by: >
      Disable the archive nesting-depth check; quarantine/depth-limit must detect consumable
      output from depth 11.
  - id: AC3
    text: >
      Claim: Quarantine execution exposes only bounded input/scratch mounts and independently
      enforced resource limits. Set: control_quarantine runner integration with env_provision and
      supervisor on every qualified host profile. Completeness: Use real descendants to attempt
      repository/host writes, credentials, production data, deployment and denied network access.
      Verify allowlisted destination/method/content digest/bytes/policy receipts. Exhaust
      aggregate memory, cumulative descendant CPU time and writable bytes/inodes including logs;
      require effect closure, group stop and slot quarantine while authority and another project
      survive. Missing limits refuse launch. Falsifier: Leave scratch inode consumption unlimited;
      quarantine/inode-exhaustion must detect escape beyond the signed storage limit.
    falsified_by: >
      Leave scratch inode consumption unlimited; quarantine/inode-exhaustion must detect escape
      beyond the signed storage limit.
required_evidence: [unit, integration]
rollback: >
  Disable affected input consumption, retain quarantined bytes and scan history, and requalify
  inspection and containment before release.
---

## Intent

Inspect and contain untrusted material before it can influence a model, reproduction or automatic admission.

## Context

Package F, W66 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R43 as reviewed, R61 and R67 require actual isolation and resource proof. Scanner success alone is insufficient authority, and a containment escape threatens the authority host. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

A hosted scanning service, unrestricted network scanning and automatic exception approval are excluded.

## Notes

D1/D2 block durable inspection and exception receipts; D3 blocks Linux containment activation, and D4 blocks isolated reproduction clones. Dmitry must designate quarantine exception authority and ratify any scanner policy that grants exemptions. Scanner identities, exact expansion units and narrower exception profiles are readiness blockers, not values chosen by a preparation agent. Map control_quarantine to contracts/fleet; W30 must inventory local scanner locks/licenses and assets using narrow runtime paths before ready. Preserve real exhaustion observations and secret-safe taint lineage.
