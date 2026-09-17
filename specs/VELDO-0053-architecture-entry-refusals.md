---
schema: veldo.spec/v1
id: VELDO-0053
title: Architecture failure handling at every eligibility entry
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W38
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
placement: [distribution, contracts, fleet, loop]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/validate_checks.py"
  - "packs/*/.veldo/validate_checks.py"
  - "engine/.veldo/arch.py"
  - ".veldo/arch.py"
  - "packs/*/.veldo/arch.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "scripts/suites/*_veldo_0053_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0053-architecture-entry-refusals.md"
  - "specs/index.md"
  - "proof/VELDO-0053/*"
behavior_bearing: true
observability:
  logs: >
    Architecture refusals include artifact path, accepted digest, load state, entry, and parse or
    structural problem.
  metrics: >
    Count optional absences, required absences, unreadable contracts, invalid contracts, and stale
    architecture reads separately.
  traces: >
    Bind the installed loader and accepted architecture revision to ready, selection, direct
    execution, and review decisions.
  error_taxonomy: >
    Distinguish optional absence, required absence, unreadable file, parse failure, invalid
    structure, and changed accepted revision.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: validate_checks.load_repo_contract distinguishes absent, valid, and invalid contracts;
      present unreadable or malformed artifacts never become optional absence. Set:
      load_repo_contract, check_arch, check_placement, placement_gate_problems, placement_gate_ok,
      and check_ready over actual architecture files and accepted snapshot artifacts. Completeness:
      Derive malformed cases from arch.load_contract and structural validators; create unreadable
      files under an unprivileged reader, dangling symlinks, directories at the path, invalid
      syntax, wrong types, and invalid references. Delete an optional contract and a required
      enrolled contract separately. Run each loader/entry in a fresh process and compare named
      outcomes. Falsifier: Return (None, None) from the ArchContractError handler for a present
      malformed file; architecture/malformed-is-not-absent must detect an allowed ready transition.
    falsified_by: >
      Return (None, None) from the ArchContractError handler for a present malformed file;
      architecture/malformed-is-not-absent must detect an allowed ready transition.
  - id: AC2
    text: >
      Claim: Invalid or required-missing architecture blocks every eligibility entry, including
      direct executor and review, before claims, launches, or accepted results. Set:
      frontier.claimable, plan.cmd_run_check, Executor.run, Dispatcher._dispatch_review, and W37
      shared eligibility registrations against real control.sqlite3 and filesystem snapshots.
      Completeness: Discover consumers of load_repo_contract and the entry registry and require
      matrix equality. Replace valid accepted architecture with each AC1 invalid class between
      selection and acceptance from a second process; run real claims and contained child launch
      attempts. Require zero new accepted work and unchanged Git trunk refs. Falsifier: Skip
      architecture validation for direct review after corrupting the accepted contract;
      architecture/review-entry must detect the reviewer launch.
    falsified_by: >
      Skip architecture validation for direct review after corrupting the accepted contract;
      architecture/review-entry must detect the reviewer launch.
  - id: AC3
    text: >
      Claim: Architecture checks use installed stdlib enforcement and the accepted immutable
      revision; candidate edits cannot stand down required policy or supply a replacement validator.
      Set: validate_checks loader calls through Executor.run and plan.cmd_run_check in a real worker
      clone, trusted installed verifier process, and authority snapshot with explicit coordinates.
      Completeness: Change the clone architecture to absent or permissive and replace its
      validate_checks.py with a success stub while retaining the accepted digest. Remove the
      execution runtime from trusted imports, race a new accepted architecture revision with entry,
      and require original enforcement or named stale-read refusal; record actual executable and
      artifact digests. Falsifier: Resolve load_repo_contract from the worker checkout after it
      deletes the required contract; architecture/worker-substitution must detect unauthorized
      stand-down.
    falsified_by: >
      Resolve load_repo_contract from the worker checkout after it deletes the required contract;
      architecture/worker-substitution must detect unauthorized stand-down.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Make every eligibility consumer fail closed when required architecture cannot be read or validated.

## Context

Package C, W38 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R03, R50-R51, and R70 require failure handling beyond the top-level gate. The baseline loader conflates malformed and absent contracts, allowing direct entries to evade policy. The declared risk floor is high; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

This item does not redesign architecture areas or relax the gate; trusted final candidate observation belongs to W43.

## Notes

D1 and D2 block accepted snapshot integration; D3 blocks activation of the replacement lifecycle policy and D4 the worker-clone profile. This item enforces A policy decisions without ratifying them. Use actual permission denial from a restricted OS identity, not a mocked read exception. No architecture.yaml amendment is authorized by this footprint; if A has not registered the adapter and replacement process policy, ready is blocked. Record each mutation and the affected entry refusal. A parseable mapping is not sufficient validation, and an absent required PLAN-0019 contract cannot use the optional-adoption exception.
