---
schema: veldo.spec/v1
id: VELDO-0217
title: Every confined mutation case has a reviewed input declaration, and a stale one runs fresh
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0207, VELDO-0208]
placement: [enforcement]
protected_paths: ["scripts/propose_case_inputs.py", "scripts/mutation_case_inputs.json", "scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/case_trace.py", "engine/scripts/case_trace.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py"]
footprint:
  - scripts/propose_case_inputs.py
  - scripts/mutation_case_inputs.json
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/case_inputs.py
  - engine/scripts/case_inputs.py
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/100_veldo_0207_case_reuse.py
  - scripts/suites/*_veldo_0217_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0217-every-confined-case-has-a-reviewed-input-declaration.md
  - specs/index.md
  - proof/VELDO-0217/*
behavior_bearing: true
observability:
  logs: The proposer names each case it traced, its three mode exits and its read-set size; the stage names every case run fresh with its reason, declaration_stale included.
  metrics: Declared, reviewed, qualified, stale and fresh counts per stage; proposal wall time and worker seconds.
  traces: Each review record binds the declaration digest, the trace digests it was judged from, the reviewer and the commit.
  error_taxonomy: No declaration, an unreviewed one, unqualified non-file inputs and starts_a_gate run fresh as today; declaration_stale runs fresh and is never published; a review record that does not match its declaration is invalid and grants nothing.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the proposer produces a current proposal for every case of the confined leg, in
      parallel, and finds a stale declaration mechanically. Set: the full registry after the
      pending stack (2,689 cases at 797b28fa, 1,707 of them confined), proposed with bounded
      parallel workers outside any gate; and the declarations whose suite now loads
      scripts/suites/support/compiled_sources.py while their declared files omit it
      (effects-worker-scope, message-speaker-is-edge, account-codex-old-tables, limit-unreported,
      codex-baseline-user-config-loaded, worker129-build-unwired,
      receiver148-placement-wait-unbounded by a scan of the stack). Completeness: the proposal
      report lists every confined case of the inventory, compared by identity with the
      coordinator's enumeration; row declarations/stale-found requires each of those
      declarations to be reported stale and re-proposed with the helper included.
    falsified_by: >
      Drop scripts/suites/support/ from the proposer's captured reads. Registered mutant
      declarations217-support-dropped must fail declarations/stale-found.
  - id: AC2
    text: >
      Claim: a declaration is marked reviewed only through a review record that matches it, and
      only when every mechanical condition holds: baseline, no-op and mutant traced to exit 0;
      two independent baseline traces with the same read set; the traced baseline observation
      equal to the last fresh gate observation; non_file_inputs stated as none with a rationale;
      no gate entry among its inputs; and a reviewed toolchain. Set: one declaration failing each
      condition, one passing all, and a review record whose declaration digest does not match.
      Completeness: row declarations/review-conditions drives each through case_reuse; the
      reviewed flag lands only in scripts/mutation_case_inputs.json, a protected path, so each
      batch also carries the owner's commit-bound approval.
    falsified_by: >
      Accept a declaration whose two baseline traces read different files. Registered mutant
      declarations217-one-trace-enough must fail declarations/review-conditions.
  - id: AC3
    text: >
      Claim: a qualified case's key covers every input it reads, because the worker runs in a
      snapshot that holds only its declared files and the coordinator's trace refuses any other
      repository probe; the key binds those files' names, modes and bytes, the case's projected
      registry entry, the mandatory machinery, the suite's prerequisite closure, the support
      helpers it loads, the declaration, the reviewed toolchain, the fixed worker environment and
      the authority identity. Set: one edit to each class of input, and an edit to an undeclared
      file. Completeness: row declarations/key-covers-inputs requires each class of edit to miss
      exactly the cases that declare it and the undeclared edit to miss none of them.
    falsified_by: >
      Leave the support helpers out of the snapshot key while keeping them in the snapshot.
      Registered mutant declarations217-helper-not-keyed must fail declarations/key-covers-inputs.
  - id: AC4
    text: >
      Claim: an unknown input never yields reuse and never a false red. A qualified case whose
      snapshot run reports an undeclared probe, or whose declared file no longer exists, is run
      again fresh in the full frozen tree in the same stage; its verdict comes from that fresh run,
      nothing is published under the stale key, and the receipt and the stage line name it
      declaration_stale. Set: a declared case whose suite gains an import of an undeclared helper,
      and one whose declared file is deleted. Completeness: row declarations/stale-runs-fresh
      requires a green stage with both cases fresh and validated, zero publications for them, and a
      red stage when the fresh run itself fails.
    falsified_by: >
      Publish the snapshot run's result when its trace reports an undeclared probe. Registered
      mutant declarations217-stale-published must fail declarations/stale-runs-fresh.
required_evidence: [unit, integration]
rollback: Revert the declarations to reviewed false; every case runs fresh, as at main.
---

## Intent

The canonical gate of 2026-10-25 reported reuse_qualified 0. That is not only because the
declarations are unreviewed. The receipt's reasons are: 1,688 cases have no declaration at all
(unknown_closure), 982 run in the unconfined leg and can never qualify under VELDO-0208
(unconfined_leg), and 19 have a declaration that is not reviewed. Only 30 declarations exist, all
reviewed false, and 11 of the 30 belong to unconfined suites. So reviewing today's file would make
at most 19 of 2,689 cases reusable. Reuse becomes real only when every confined case has a current
declaration and a way to review declarations at that scale.

The current file is also out of date. The pending stack makes 12 suites load
scripts/suites/support/compiled_sources.py, and seven declared cases of those suites do not list
it. Under today's rule such a declaration, once reviewed, would fail the stage loudly at its first
snapshot run (an undeclared probe, or a module that does not import) even though nothing about the
change under test is wrong.

## Design

Proposals at scale. scripts/propose_case_inputs.py traces one case at a time today; three traced
runs per case for 1,707 confined cases at the measured median of 19 seconds per worker is about 27
hours of serial work. It now admits its traced workers through the coordinator's own worker pool
and admission (VELDO-0219), so a full proposal pass takes about two to three hours on the
qualification host. It never runs inside a gate. Each proposal records the digest of every file it
read, so a later pass re-traces only cases whose recorded inputs changed, plus every case whose
suite, closure or support helpers changed.

Review at scale. The review record (proof/VELDO-0217/reviews/) is per batch, written by an
independent reviewer under the repository's L2 rule, and binds each declaration digest to the trace
digests it was judged from. The mechanical conditions of AC2 are checked by case_reuse itself, so a
reviewer judges only what a trace cannot show: whether a case depends on the clock, randomness,
network or a host service, which the declaration records in non_file_inputs and rationale. A case
that does stays unreviewed and runs fresh. The reviewed flag lands through the owner's commit-bound
approval because scripts/mutation_case_inputs.json is protected.

Keys. VELDO-0207 already binds declared names, modes and bytes, the projected registry entry, the
mandatory machinery, the toolchain, the worker environment and the authority identity. This spec
makes the closure and the support helpers explicit inputs of every proposal (the trace reads them,
and the proposer now records them even when a fixture loads them through a cached code object), so
the key is complete by construction: anything not declared is absent from the snapshot.

Fail closed, not red. VELDO-0207 made an undeclared probe in a declared case fail the stage. That
was right while declarations were few and hand made. At full coverage a landing that adds one
import to one suite would turn the gate red for a bookkeeping reason. The stale case now runs
fresh in the full frozen tree in the same stage: no result is reused, its verdict is a real fresh
verdict, and the receipt names it so the proposer picks it up. A real failure of the fresh run is
still red.

## How many cases a landing re-runs

A measurement, not a promise. Using VELDO-0207's traced read sets of 30 sampled cases
(proof/VELDO-0207/fan-in-full.json) and the files changed by the last 37 landings on main grouped
by specification id, the share of declared cases a landing invalidates is bimodal:

- landings that change only suites or a few specific modules (22 of 37): 0 to 7 percent, median
  3 percent;
- one landing in between, at 20 percent;
- landings that change a shared engine module under .veldo/ (14 of 37): 70 to 100 percent,
  typically 73, because about two thirds of sampled cases lay down a fixture repository that
  copies all 233 engine modules, so every module is a byte-level input of those cases.

So for a change touching a few suites, a landing would re-run about 50 to 120 of the 1,707
confined cases, plus every unconfined case (982) until VELDO-0222, plus the audit sample of
VELDO-0218. A landing that changes a shared engine module re-runs about 1,250 confined cases. The
proof records the same measurement over the full proposal set once it exists.

## Out of scope

Unconfined cases (VELDO-0222); the audit of reused results (VELDO-0218); suite result reuse
(VELDO-0206); any change to a case, an assertion, the worker confinement or the tracer's rules.

## What the reviewer judges

Normal use: the owner runs the proposer outside a gate, an independent reviewer reviews a batch,
the owner approves the protected file, and gates then reuse qualified cases. Threat model: as in
VELDO-0207 and VELDO-0208; a review record is a claim about a declaration and grants nothing unless
its digest matches and the mechanical conditions hold. Out of review scope: a case whose result
depends on a non-file input the reviewer missed (VELDO-0218's audit is the detector), and planted
records in the owner's store.

## Notes

The numbers come from the 2026-10-25 canonical receipt (canonical-mutations.json, case_receipts)
and a scan of the pending stack at 3ab6e90d. The seven names in AC1 are from that scan; the
mechanical staleness check, not this list, is the authority.
