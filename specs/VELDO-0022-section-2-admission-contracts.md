---
schema: veldo.spec/v1
id: VELDO-0022
title: Section 2 admission semantics
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W7
plan_revision: 1
depends_on: [VELDO-0017, VELDO-0020]
placement: [contracts, engine]
protected_paths: []
footprint:
  - ".veldo/request.py"
  - "engine/.veldo/request.py"
  - ".veldo/authorization.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - "engine/.veldo/*contract*.py"
  - ".veldo/*contract*.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0022-section-2-admission-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0022/*"
behavior_bearing: true
observability:
  logs: Admission diagnostics identify work class, request revision, missing authority, reproduction or quarantine refusal, standing occurrence, emergency deadline, or scope dimension requiring readmission.
  metrics: Proof reports class/predicate and quarantine-limit coverage, emergency deadline boundaries, and seven/fourteen-day debt counts with unknown estimates retained; live intake metrics belong to F.
  traces: Admission evidence joins accepted behavior revision, reproduction/environment digests, scan and taint results, request/standing-ticket identity, emergency authority, and before/after scope envelopes.
  error_taxonomy: Distinguish unknown or multiple work classes, unauthorized admission, untrusted reproduction, scope-changing defect, unavailable scan, quarantine overrun, repeated occurrence, expired emergency authority, and exceeded signed ceiling.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every item has exactly one governed work class and the class-specific authority, lane,
      request, and priority predicates before execution. Set: PRODUCT_CHANGE, POLICY_DEFECT,
      SECURITY_EMERGENCY, INCIDENT_CONTAINMENT, STANDING_MAINTENANCE, TECHNICAL_CHANGE, and
      COMPLIANCE_EXPIRY, plus unknown and multiply classified input. Completeness: Require equality
      between the R08 enumeration and class policy registry; test every class with each required
      authority/input absent and a permitted control, including compliance with no enrolled obligation
      and production targets with no admitted adapter. Falsifier: Permit TECHNICAL_CHANGE admission by
      a preparation agent; the admission/technical-authority row must fail.
    falsified_by: >
      Permit TECHNICAL_CHANGE admission by a preparation agent; the admission/technical-authority row
      must fail.
  - id: AC2
    text: >
      Claim: Automatic defect admission requires trusted quarantined reproduction of accepted behavior
      and refuses scope-changing or unsupported restoration claims without lowering severity. Set:
      Every R66 predicate: accepted revision, failing criterion, supported version, bounded surface
      and envelope, trusted observations, duplicate/obsolete/destructive/production-data/expected-
      behavior cases, cross-repository changes, and contract/interface/model/dependency/protected-
      path/release/compatibility changes. Completeness: Maintain a R66 clause-to-predicate table and
      require positive controls and one independently failing fixture for every predicate; assert
      grooming or bounded emergency routing on reproduction failure with severity preserved.
      Falsifier: Admit a defect supported only by an agent reproduction assertion; the
      admission/untrusted-reproduction row must fail.
    falsified_by: >
      Admit a defect supported only by an agent reproduction assertion; the admission/untrusted-
      reproduction row must fail.
  - id: AC3
    text: >
      Claim: Quarantine, standing authorization, and emergency exceptions remain bounded,
      attributable, and enforceable before automatic admission. Set: All R67 external input types and
      scan/taint fields; 1 GB, 10000 files, depth 10, ratio 100:1 bounds; standing ticket fields and
      occurrence identity; R68 break-glass scope, 4-hour ratification, one-business-day review, and
      isolated unratified patch limits. Completeness: Derive required field and limit tables from the
      cited clauses; exercise each missing field, unavailable scanner, boundary and over-bound value,
      denied network/write/credential access, repeated occurrence, expired ticket, and unavailable
      independent deadline enforcer. Falsifier: Treat an unavailable malware inspection as clean; the
      quarantine/unknown-scan row must fail.
    falsified_by: >
      Treat an unavailable malware inspection as clean; the quarantine/unknown-scan row must fail.
  - id: AC4
    text: >
      Claim: Material scope changes invalidate admission and debt reporting never grants authority or
      hides unknown effort. Set: R69 path, interface, migration, dependency, target, risk, criterion,
      class, and budget changes; signed ceilings and the greater-than-20-percent threshold; RAW,
      PREPARED, and AWAITING_GROOMING ages at seven and fourteen days. Completeness: Enumerate all
      scope dimensions from the machine-comparable schema, test at/below/above thresholds and ceiling
      independently, require AWAITING_AUTHORITY plus AWAITING_GROOMING, and compare debt counts/ages
      against all qualifying fixture items with unknown estimates retained. Falsifier: Permit a
      10-percent budget increase that exceeds the signed ceiling; the readmission/signed-ceiling row
      must fail.
    falsified_by: >
      Permit a 10-percent budget increase that exceeds the signed ceiling; the readmission/signed-
      ceiling row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Define deliberate admission for every work class, with bounded exceptions that cannot turn agent preparation into authorization.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R07-R12, R56, and R66-R69. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Admission grants engineering and emergency scope; mistakes can bypass deliberate owner authorization, so this concern is critical. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** Quarantine scanner installation, live reproduction, occurrence scheduling, emergency effects, intake operations, and debt interfaces belong to F. No customer charging or production deployment is authorized.

## Notes

Class and exception fixtures must preserve severity when reproduction fails and return the required grooming or bounded emergency disposition. Scan-unavailable and unknown-effort cases stay explicit; neither supplies permission. Admission contracts specify the quarantine limits and independent deadline-enforcement requirement, while F installs and qualifies those mechanisms.
