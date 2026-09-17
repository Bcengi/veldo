---
schema: veldo.spec/v1
id: VELDO-0082
title: Standing maintenance and compliance occurrence admission
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W67
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079, VELDO-0081]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_occurrence*.py"
  - ".veldo/control_occurrence*.py"
  - "packs/*/.veldo/control_occurrence*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0082_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0082-standing-maintenance-compliance-occurrences.md"
  - "specs/index.md"
  - "proof/VELDO-0082/*"
behavior_bearing: true
observability:
  logs: >
    Occurrence receipts identify signed standing request, policy revision, cadence slot, distinct
    item/request identity and per-occurrence bounds.
  metrics: >
    Count due, deduplicated, expired, concurrency-blocked and grooming-returned occurrences, with
    unknown obligations visible.
  traces: >
    Join deliberately authored standing authorization to each occurrence request, priority,
    reservation and completion receipt.
  error_taxonomy: >
    Distinguish unsigned cadence, expired standing policy, uncovered maintenance, absent
    compliance obligation and exceeded occurrence bound.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Standing work requires deliberately authored signed authorization covering every
      occurrence limit. Set: control_occurrence validation with
      request.validate_record/authorization.is_authorized over R68 cadence, start/expiry,
      paths/dependencies, version movement, breaking-change prohibition, budget, concurrency,
      tests and release limits. Completeness: Compare accepted standing schema fields and
      maintenance categories to coverage. Remove each bound; exercise refactors, upgrades,
      renewal, SDK migration, flakes, observability, build maintenance, dead code and deprecation
      both covered and uncovered. Uncovered debt requires TECHNICAL_CHANGE grooming; prepared
      recurring text cannot self-sign. Falsifier: Permit a generated recurring request without an
      authorized personal signature; standing/deliberate-ticket must detect automatic admission.
    falsified_by: >
      Permit a generated recurring request without an authorized personal signature;
      standing/deliberate-ticket must detect automatic admission.
  - id: AC2
    text: >
      Claim: Each cadence occurrence has a distinct item and receipt chain, while retries reuse
      the same occurrence. Set: control_occurrence scheduling, B source allocation/reservation and
      frontier.claimable integration. Completeness: Race real schedulers for the same slot and
      adjacent slots, crash after allocation before publication, and replay. Require one mapping
      per standing revision/slot, distinct UUID/request/receipt for distinct occurrences, no
      recycled aliases and enforced concurrency. Exceed any signed bound or expire policy between
      selection and claim; return to grooming without dispatch. Falsifier: Key every cadence slot
      to the standing ticket ID alone; standing/distinct-occurrences must detect identity reuse
      across two due slots.
    falsified_by: >
      Key every cadence slot to the standing ticket ID alone; standing/distinct-occurrences must
      detect identity reuse across two due slots.
  - id: AC3
    text: >
      Claim: Compliance occurrences require an actual enrolled obligation and applicable named
      authority. Set: Standing and non-standing COMPLIANCE_EXPIRY intake and signed priority
      evaluation. Completeness: Enumerate enrolled obligation types with active, expired, revoked
      and absent bindings. Standing occurrences inherit only signed bounded scope and priority;
      non-standing work is shaped and prioritized by the admission authority. Race obligation
      withdrawal with admission and reject stale read sets; no obligation is presumed for this
      repository. Falsifier: Admit a compliance occurrence when its obligation binding is absent;
      standing/no-presumed-compliance must detect unauthorized work.
    falsified_by: >
      Admit a compliance occurrence when its obligation binding is absent;
      standing/no-presumed-compliance must detect unauthorized work.
required_evidence: [unit, integration]
rollback: >
  Suspend future occurrences, preserve consumed slots and reservations, and require renewed
  standing authorization for changed bounds.
---

## Intent

Execute bounded recurring authorization without letting a scheduler invent new maintenance or compliance work.

## Context

Package F, W67 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R08, R61 and R68 distinguish previously authorized occurrences from discretionary admission. Repeating an overbroad permission makes this authority concern critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

New compliance duties, deployment actions and generic time scheduling infrastructure are excluded.

## Notes

D1/D2 block occurrence uniqueness and published authorization; D3/D4 govern inherited execution. Dmitry must enroll standing-ticket signers, priority policy identities and any compliance authority, and decide the applicable obligation before compliance activation. W66 supplies quarantine for occurrence inputs. Place control_occurrence in contracts/engine/fleet under the effective architecture and inventory it before ready. Retain slot races, original signed ticket bytes and the no-obligation refusal; a clock disagreement must retain the due obligation without guessing permission.
