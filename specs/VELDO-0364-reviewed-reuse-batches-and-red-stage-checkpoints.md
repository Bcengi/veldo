---
schema: veldo.spec/v1
id: VELDO-0364
title: Reviewed mutation reuse batches retain valid verdicts across a later red case
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0217, VELDO-0218, VELDO-0226, VELDO-0362]
placement: [enforcement]
protected_paths: [scripts/check_gate_mutations.py, engine/scripts/check_gate_mutations.py, scripts/mutation_case_inputs.json, "proof/VELDO-0217/reviews/*"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_case_inputs.json
  - scripts/check_teeth_mutations.py
  - scripts/suites/161_veldo_0364_reuse_checkpoints.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - proof/VELDO-0217/reviews/*
  - proof/VELDO-0364/*
  - specs/VELDO-0364-reviewed-reuse-batches-and-red-stage-checkpoints.md
  - specs/index.md
behavior_bearing: true
observability:
  logs: Checkpoint refusal names cleanup, input race, runtime race or audit mismatch without hiding the first stage failure.
  metrics: Completed records checkpointed independently of registered, executed, reused and rejected counts.
  traces: The existing authority store authenticates exact case keys; a checkpoint is never a green stage receipt.
  error_taxonomy: Invalid or unqualified cases never publish; store unavailability misses; integrity conflicts remain red.
acceptance_criteria:
  - id: AC1
    text: >
      Rank confined worker costs from both historical receipts, allocating shared controls once.
      Propose a first batch covering about 10 to 25 percent of confined worker time, excluding
      nested gates and live-capture-dependent suites. Declare conservative complete file closures,
      runtime requirements and rationale, supported by the VELDO-0217 four traces and matching
      successful observation. Retain reviewed false for independent review. Missing closure or
      qualification evidence leaves this criterion incomplete, even when a proposal is written.
    falsified_by: A repeated control in the cost total, forbidden gate entry in a proposed closure,
      reviewed true entry, or omission of a transitive dependency fails the batch checks.
  - id: AC2
    text: >
      After authority cleanup and whole-stage input and runtime stability checks, publish each
      completed valid fresh case even if another case fails. Validation, trace withholding,
      review qualification and force-fresh remain enforced. Cleanup failures, active workers,
      races and audit mismatches prevent checkpoint publication. Preserve the first failure,
      every registered identity's coverage receipt, and complete-coverage requirements for green.
    falsified_by: Registered checkpoint364-green-only, checkpoint364-input-race,
      checkpoint364-runtime-race, checkpoint364-cleanup, checkpoint364-audit and
      checkpoint364-invalid mutants must fail their named unit rows.
  - id: AC3
    text: >
      Unit and single-case evidence demonstrates unrelated-edit hits, transitive-dependency misses,
      forced-fresh equivalence, corrupt-record misses and audit mismatch refusal. Sensitivity
      proof demonstrates clock/randomness insensitivity for the exact key. An unavailable
      perturbation runner or library leaves this criterion incomplete and qualification closed,
      never represented by a fabricated production proof. No full gate,
      full leg, host load, new wall-clock site, confinement-list edit or live-capture module edit.
    falsified_by: A dependency edit that reuses, a force-fresh publication, a corrupted hit, an
      accepted audit mismatch or admission without the exact sensitivity key fails the proof.
required_evidence: [unit, integration]
rollback: Revert this ticket; unreviewed declarations grant nothing and result records are disposable.
---

Owner intent: Telegram 43610, "I need to speedup veldo work". Rank 4 phase 1 of the supplied
speed analysis. September's older cache removal does not authorize bypassing the later reviewed
declaration process. Ordinary product edits can retain keys; authority edits invalidate them.

The writer cannot sign VELDO-0217 review records or set reviewed true. Gate 18 is running;
this ticket uses only unit and sequential single-case diagnostics. A future successful fresh
observation, independent review and owner approval are still required for production activation.

## Observed blockers

The phase 1 declarations are proposals, not completed qualification. The representative
presentations baseline passes, but its trace reports denied host-socket probes and shared-preamble
Git metadata reads. The proposer also captures authority bootstrap reads. These cannot be removed
from the proof by assertion. Aliases was excluded after discovering its real checkout-history
dependency. No batch case has four current successful traces, a matching successful gate receipt,
or a positive sensitivity proof. The checkout has the VELDO-0226 key-presence checker but no
perturbation producer, and the host has no libfaketime. AC1 and AC3 remain incomplete. This change
does not install host tools during another gate or weaken the refusals to claim activation.
