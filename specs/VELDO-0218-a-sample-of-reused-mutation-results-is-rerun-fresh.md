---
schema: veldo.spec/v1
id: VELDO-0218
title: Every gate reruns a random sample of its reused mutation results and compares them
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0205, VELDO-0208, VELDO-0217, VELDO-0224]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/mutation_reuse.py", "engine/scripts/mutation_reuse.py", "scripts/gate_reuse.py", "engine/scripts/gate_reuse.py", "scripts/reuse_stamp.py", "engine/scripts/reuse_stamp.py", ".veldo/reuse_evidence.py", "engine/.veldo/reuse_evidence.py"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_reuse.py
  - engine/scripts/mutation_reuse.py
  - scripts/gate_reuse.py
  - engine/scripts/gate_reuse.py
  - scripts/reuse_stamp.py
  - engine/scripts/reuse_stamp.py
  - .veldo/reuse_evidence.py
  - engine/.veldo/reuse_evidence.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0218_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0218-a-sample-of-reused-mutation-results-is-rerun-fresh.md
  - specs/index.md
  - proof/VELDO-0218/*
behavior_bearing: true
observability:
  logs: The stage names each audited case, whether its fresh result matched the reused record, and every field that differed.
  metrics: Reused, audited, matched and mismatched counts per stage, the audit's worker seconds, and the detection probability the sample size gives.
  traces: Each audit entry binds the reused record's key and digest to the fresh run's observations in the receipt.
  error_taxonomy: A verdict-bearing difference is reuse_audit_mismatch (RED); a difference only in observations no verdict reads is recorded, not red; a fresh audit run that fails its own validation is RED as that failure.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: whenever a gate reuses any mutation result, it reruns fresh a sample of the reused
      cases in the same stage: at least min(reused, 8) cases and at least 5 percent of the reused
      cases (10 percent for cases admitted under VELDO-0222), drawn by the authority with fresh
      operating-system randomness after lookup and spread across suites, so neither the candidate
      nor an earlier run can predict which. Set: stages with 0, 1, 7, 8, 100 and 2,000 reused
      cases, and a fixed-seed control. Completeness: row reuse-audit/sample-size requires the
      counts, the receipt's list of audited identities and the per-suite spread; row
      reuse-audit/unpredictable requires two runs over identical inputs to choose different samples.
    falsified_by: >
      Seed the sample from the input digest. Registered mutant audit218-predictable-sample must
      fail reuse-audit/unpredictable.
  - id: AC2
    text: >
      Claim: an audited case's fresh result must equal the reused record in every field a verdict
      reads: the baseline and no-op observation arrays, the named target rows of the mutant, the
      replacement count and both mutation digests. A difference in any of them makes the stage RED
      with reuse_audit_mismatch, removes the reused record from the authenticated store and writes
      a stale mark for the case to the authority's store (VELDO-0224), never to the declarations
      file in the candidate tree. A difference only in mutant observations no
      verdict reads (four timing-sensitive cases showed this on 2026-10-25) is recorded in the
      receipt and is not red. Set: a planted record differing in each verdict-bearing field, one
      differing only in a non-target mutant row, and one identical. Completeness: row
      reuse-audit/compare drives each through the real coordinator with controlled workers and a
      scratch store.
    falsified_by: >
      Compare only the stored result's status, not its observations. Registered mutant
      audit218-status-only must fail reuse-audit/compare.
  - id: AC3
    text: >
      Claim: counts stay honest. An audited case is reported once, as fresh, with audited true and
      the reused record's key beside it; it is not counted as reused. A force-fresh gate reuses
      nothing and audits nothing. Landing (VELDO-0208) accepts the receipt only when the audit
      entries are present for a stage that reused anything. Set: cold, warm, mixed and force-fresh
      receipts, and a warm receipt with its audit entries removed. Completeness: row
      reuse-audit/receipts drives the reducer and the landing check.
    falsified_by: >
      Accept a warm receipt with no audit entries at landing. Registered mutant
      audit218-audit-optional must fail reuse-audit/receipts.
required_evidence: [unit, integration]
rollback: Revert the audit; reuse then rests on the VELDO-0207 keys alone, as before.
---

## Intent

A reused result is only as good as its key. Under the owner's decision D2 every input a reused
case reads is traced or mechanically refused (VELDO-0217, VELDO-0222), so the audit is never the only
detector of anything: it is a second, independent check that the first one holds, for example
against a tracer defect or a run-to-run variance the two-trace condition did not show. The owner's
rule is that nothing that changed may skip its checks; the audit keeps checking, on every gate,
that a reused result is still the result a fresh run would give, without paying for a full fresh
run.

## Design

After lookup, the coordinator draws the sample from os.urandom, stratified by suite so a large
suite cannot hide a small one, and adds those cases to the fresh job list with their own controls.
The reused record stays in hand. When the fresh mutant completes, collect() compares it with the
record field by field (the fields validate_result reads) before either is used.

Detection power, stated so the sample size is a decision rather than a habit: if a stale key affects
k reused cases and the sample is 5 percent, the chance that at least one is audited is
1 - 0.95^k: about 64 percent at k = 20 and 95 percent at k = 60, per gate. Because the draw is
fresh each gate, a stale key that survives one gate faces the same odds at the next.

Cost: at 5 percent, a landing that reuses 2,500 cases reruns about 125 of them. At the measured
mean of 24 worker seconds per mutant plus shared controls, that is about 3,000 to 4,500 worker
seconds, two to four minutes of wall time at the admission VELDO-0219 sets. The proof states the
measured figure.

## Out of scope

The keys themselves (VELDO-0217); which cases may be reused (VELDO-0217, VELDO-0222); suite result
reuse (VELDO-0206).

## What the reviewer judges

Normal use: a landing gate with authenticated reuse. Threat model: as in VELDO-0208. The audit
defends against honest staleness, not against the owner forging a store record. Out of review
scope: a stale key that affects so few cases that sampling misses it for several gates in a row;
the stated detection probability is the accepted residual.

## Notes

The four timing-sensitive differences are recorded in
/tmp/veldo-mutation-throughput-20261025/canonical-observation-comparison.json: additional non-target
observations in the mutant arrays, with every named rejection matching.
