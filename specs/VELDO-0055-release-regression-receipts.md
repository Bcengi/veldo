---
schema: veldo.spec/v1
id: VELDO-0055
title: Release regression receipt consumption
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W40
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
placement: [distribution, contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/release_contract.py"
  - ".veldo/release_contract.py"
  - "packs/*/.veldo/release_contract.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/validate_checks.py"
  - "packs/*/.veldo/validate_checks.py"
  - "engine/.veldo/control_regression*.py"
  - ".veldo/control_regression*.py"
  - "packs/*/.veldo/control_regression*.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "scripts/suites/*_veldo_0055_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0055-release-regression-receipts.md"
  - "specs/index.md"
  - "proof/VELDO-0055/*"
behavior_bearing: true
observability:
  logs: >
    Regression consumption reports release and plan revision, required journey ID, candidate tree,
    environment digest, and accepted receipt identity.
  metrics: >
    Show required, executed, accepted, missing, stale, and rejected journey counts without treating
    unknown coverage as zero.
  traces: >
    Join recursive release member digests and journey activation decisions to actual gate executions
    and signed result artifacts.
  error_taxonomy: >
    Distinguish declaration-only coverage, missing receipt, wrong candidate or environment,
    duplicate coverage, stale member digest, and failed journey.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: plan.cmd_release_check consumes observed regression receipts for the complete
      applicable journey set; declaration of journeys or released status cannot establish
      acceptance. Set: plan._journey_active, cmd_regression, cmd_release_check,
      release_contract.release_report and member_digest over real accepted release/plan artifacts
      and signed receipts in control.sqlite3. Completeness: Derive recursive required members and
      journeys from the accepted snapshot and A release contract, including per_spec, release,
      start, after, and manual activation dispositions. Run registered journeys as real subprocesses
      against real Git candidate trees; compare required IDs to accepted execution coverage in both
      directions. Delete one receipt while retaining its declaration and all shipped strings;
      release-check must fail by name. Falsifier: Retain cmd_release_check acceptance based only on
      a nonempty journey declaration; regression/declaration-only must detect acceptance with the
      required receipt deleted.
    falsified_by: >
      Retain cmd_release_check acceptance based only on a nonempty journey declaration;
      regression/declaration-only must detect acceptance with the required receipt deleted.
  - id: AC2
    text: >
      Claim: Regression consumption verifies actual execution, current result, signer, candidate,
      environment, and complete subject bindings before granting any release obligation. Set:
      control_regression integration called by plan.cmd_release_check and
      validate_checks.check_releases, using real gate result files, Git objects, and OpenSSH-signed
      observation receipts. Completeness: Enumerate receipt fields from A and the registered journey
      set. Remove, duplicate, or corrupt each field and artifact; substitute another real candidate
      or environment and replay an old passing receipt after a failing run. Kill the journey process
      before result persistence and restart the reader; no missing observation may become accepted
      coverage. Falsifier: Ignore candidate identity when consuming a valid signed journey receipt
      from another commit; regression/wrong-candidate must detect the false coverage.
    falsified_by: >
      Ignore candidate identity when consuming a valid signed journey receipt from another commit;
      regression/wrong-candidate must detect the false coverage.
  - id: AC3
    text: >
      Claim: Changed required members, journey definitions, or floor obligations invalidate cached
      coverage and prevent stale acceptance through floor eligibility. Set: plan.cmd_release_check,
      release_contract.release_report, and the W37 eligibility consumer reading real published
      snapshots and complete collection read sets. Completeness: Race a second signed client
      changing a recursive member digest, adding a required journey, or superseding an applicable
      floor settlement after the consumer reads. Keep project version fixed. Require named
      stale-input refusal, no accepted release transition, and preserved prior receipt history
      across SIGKILL after invalidation commit; rerun affected journeys on a new candidate as the
      positive control. Falsifier: Check only previously fetched receipt rows after another process
      inserts a required journey; regression/new-obligation-race must detect acceptance with
      incomplete coverage.
    falsified_by: >
      Check only previously fetched receipt rows after another process inserts a required journey;
      regression/new-obligation-race must detect acceptance with incomplete coverage.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Make release readiness depend on actual regression execution for the exact accepted candidate and environment.

## Context

Package C, W40 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R47, R51-R52, R65, R70, and R76 require consumption of evidence rather than declared journeys. Missing coverage can authorize a release whose promised outcomes were never exercised. The declared risk floor is high; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Release deployment, new release ownership workflows, and live baseline decisions remain outside this consumer repair.

## Notes

D1/D2 block authoritative receipt storage and published snapshots; D3/D4 remain A/B prerequisites for candidate execution. The baseline cmd_release_check tests only whether journeys exist, and release_report resolves membership without proving execution. Keep the existing typed forest and manual-trigger semantics, while requiring every applicable obligation and explicit disposition to be accounted for by the accepted contract. control_regression is a narrow proposed contracts adapter; map and inventory it before ready. W44 owns concrete registration of RJ1-RJ4, and H owns the every-pack release matrix. Preserve the falsifier diff, actual subprocess output, and named failing row for each criterion. A current accepted floor settlement constrains regression; it never expands admission scope.
