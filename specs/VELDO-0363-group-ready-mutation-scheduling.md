---
schema: veldo.spec/v1
id: VELDO-0363
title: Release each mutant after its own controls and stop on the first invalid verdict
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0362]
placement: [enforcement]
protected_paths: [scripts/check_gate_mutations.py, engine/scripts/check_gate_mutations.py]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/115_veldo_0219_measured_admission.py
  - scripts/suites/98_veldo_0204_mutation_receipts.py
  - scripts/suites/99_veldo_0205_reuse.py
  - scripts/suites/100_veldo_0207_case_reuse.py
  - scripts/suites/support/v363_early.py
  - scripts/suites/158_veldo_0224_stale_declarations.py
  - scripts/suites/157_veldo_0217_declarations.py
  - specs/VELDO-0363-group-ready-mutation-scheduling.md
  - specs/index.md
  - proof/VELDO-0363/*
behavior_bearing: true
observability:
  logs: First invalid result remains the stage failure; completed and cancelled workers retain receipts.
  metrics: Registered, executed, rejected and pending cases retain full inventory accounting.
  traces: Group readiness follows validated baseline and no-op observations; history only orders work.
  error_taxonomy: Invalid controls, survivors, missing results and cleanup errors cannot produce green.
acceptance_criteria:
  - id: AC1
    text: >
      Mutants become eligible after their own group's baseline and no-op pass unchanged validation,
      without waiting for unrelated controls. Stale declarations rerun all three modes on full inputs.
      A deterministic replay of gate 15's 734 control groups and 3978 cases proves early release,
      pair agreement, failed-group isolation and complete coverage.
    falsified_by: Removing either dependency, accepting a failed or mismatched control, or restoring the global barrier makes its named replay row fail.
  - id: AC2
    text: >
      Default execution stops on the first invalid control or mutant result, preserves the first
      error and partial receipts, and drains all active workers through the existing cleanup path.
      VELDO_GATE_COLLECT_ALL=1 continues independent work for diagnostics; invalid groups never
      launch mutants. Green still requires every registered identity to validate.
    falsified_by: Continuing after an invalid verdict, dropping a receipt or bypassing the drain fails the abort rows; treating partial coverage as green fails the coverage row.
  - id: AC3
    text: >
      Eligible work orders last-failed cases first and then measured long tails. Shared controls
      inherit their members' priority. Authority-owned scheduling hints survive red stages and
      input-key changes but cannot change admission, correctness timeouts or verdicts. Missing or
      corrupt history falls back safely. Every new guard has a registered named-row falsifier.
    falsified_by: Reversing failure or measured-tail priority, allowing fixture writes to owner history, or discarding red-stage history fails the corresponding named row.
required_evidence: [unit, integration]
rollback: Revert this ticket; scheduling history is disposable and authorizes no verdict.
---

Owner: Telegram 43610, "I need to speedup veldo work"; rank 6 of the fully read speed analysis.
Gate 13's 5149-second control barrier is evidence of delayed first launch, not a promised saving.
Gate 18 is running. Only unit fixtures, coordinator suites and single-case controls are authorized;
no full gate, full leg, benchmark or loaded run. No live-capture modules, new clock sites, timeout
reductions or unconfined-list edits. Engine copies stay identical. Independent review and a full
gate remain outstanding; this ticket makes no landing or full-gate-green claim.

The inherited branch contains the existing Workers.cleanup drain but no VELDO-0360 spec or
collect-all switch. This ticket reuses that drain and implements the requested environment switch
at the mutation-stage boundary, without modifying the outer stage scheduler.

## Bounded evidence

The fake gate-15 replay validates all 3978 cases in 734 groups and starts the first mutant at its
own second control's completion. Thirty-six registered guard falsifiers have passing baseline
and no-op controls and are killed at their named rows. The targeted suites and static constraints
are recorded in `proof/VELDO-0363/`; this is not a full-gate acceptance. The proof README records
the interrupted suite-104 native selection, which exceeded the intended unit-only scope and is
excluded from passing evidence. Independent review and landing approval remain outstanding.
