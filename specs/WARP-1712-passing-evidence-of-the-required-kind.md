---
schema: veldo.spec/v1
id: WARP-1712
title: Required evidence must have the required kind and a recorded passing result
status: ready
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
placement: [contracts]
footprint:
  - engine/.veldo/validate.py
  - .veldo/validate.py
  - engine/.veldo/examples/proof-example.json
  - .veldo/examples/proof-example.json
  - scripts/suites/14_warp_0717_subset_runner.py
  - scripts/suites/106_warp_1712_required_evidence.py
  - scripts/suites/manifest.json
  - specs/WARP-1712-passing-evidence-of-the-required-kind.md
  - specs/index.md
  - proof/WARP-1712/**
protected_paths: []
behavior_bearing: true
observability:
  logs: Required-evidence refusals name the missing passing evidence kind and proof path.
  metrics: Corpus comparison records old/new verdict totals and every changed pair by cause.
  error_taxonomy: Wrong kind, absent result, non-passing result, and a check name without a passing record.
acceptance_criteria:
  - id: AC1
    text: Integration requires integration evidence; generic test remains a legacy unit alias only. Existing equivalent-kind aliases remain explicit. A passed check can supply its named kind, but a bare check name cannot.
    falsified_by: Restore test as an integration alias or count a bare check name and the corresponding refusal case fails.
  - id: AC2
    text: An evidence entry or check must itself record a passing outcome. Parent criterion status does not supply a missing outcome. Missing, failed, pending, not-run, unknown and contradictory outcomes cannot satisfy a required kind. A design-review file must record a passing verdict, not merely exist.
    falsified_by: Remove the outcome guard and each absent-result and non-passing-result refusal case fails; accept file existence alone and the failed design review case fails.
  - id: AC3
    text: Before modifying either validator, run the current and proposed required-evidence checks on every matched spec/manifest pair in core's declared proof corpus. Record input digests, totals, skipped inputs, and every changed pair grouped by cause in this proof directory. Core remains read-only and its engine is not reinstalled.
    falsified_by: Omit a matched manifest or alter an input during the measurement and the corpus reconciliation or before/after digest check fails.
  - id: AC4
    text: Veldo's own suite exercises positive controls and refusals in both validator copies. Each new refusal has an assertion that fails against the old implementation. Record focused tests, falsifiers and the canonical gate honestly without rewriting historical proofs to invent passing results.
    falsified_by: Run the refusal matrix against the base validator and it must fail by assertion while the positive controls still pass.
required_evidence: [unit, integration]
rollback: Revert the implementation commits; retain the measurement as historical evidence.
---

## Intent and design

The 2026-10-20 core review found that required integration evidence accepts generic unit tests,
bare check names, and failed or unexecuted entries. The collector must filter on both kind and
outcome. The proof contract is the field-based PROOF_REQ/check_json implementation, not a JSON
Schema file. Existing examples use criterion status=passed and checks result=pass; current
writers also emit checks status=passed. Evidence needs its own recorded outcome: it never
inherits a criterion's status. Accept status=passed and result=pass or passed, and reject a
record if any supplied outcome field disagrees. No text matching, case folding or prose inference.

The check schema names its kind with name; it counts only with a recorded passing outcome.
Evidence names its kind with type. The deliberate alias table preserves equivalent spellings,
including journeys/journey/e2e, and removes test from integration. Design reviews retain their
separate artifact route but must contain verdict=pass or pass_with_notes.

The impact report uses a proposed validator held under this proof directory before changing the
production validator. It calls the actual old and proposed check on the same files, using the
validator's corpus membership rule and spec_id join. Cause groups can overlap; totals distinguish
unique changed pairs from group memberships. A result is absent at the entry level even when a
parent criterion says passed. Existing proof records are immutable, not migration targets.

## Scope and review

Normal use is required-evidence validation of checked-in proof manifests. Review covers exact-kind
and outcome matching, positive controls, corpus completeness, and fidelity of the impact report.
Artifact execution, cryptographic authenticity, and the separate control_proof observation protocol
are outside this change. Core is read-only. No install, push, merge, branch switch or other worktree
change is authorized. WARP-1712 follows the user's explicit numbering instruction over the repository's
general VELDO naming convention. This spec is ready on the user's build instruction.
