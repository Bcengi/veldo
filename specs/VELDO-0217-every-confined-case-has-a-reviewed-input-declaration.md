---
schema: veldo.spec/v1
id: VELDO-0217
title: Every confined mutation case gets a current, reviewed input declaration with complete keys
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0207, VELDO-0208, VELDO-0219]
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
  logs: The proposer names each case it traced, its three mode exits, its read-set size and every non-file input class its trace shows; case_reuse names the condition a declaration fails.
  metrics: Declared, current, stale, reviewed and qualified counts; proposal wall time and worker seconds; cases kept fresh per non-file input class.
  traces: Each review record binds the declaration digest, the trace digests it was judged from, the reviewer and the commit.
  error_taxonomy: No declaration, an unreviewed one, a non-file input class the trace shows and starts_a_gate run fresh with their reason; a review record that does not match its declaration grants nothing.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the proposer produces a current proposal for every case of the confined leg, in
      parallel through the coordinator's admission (VELDO-0219), outside any gate, and finds a
      stale declaration mechanically. Set: the full registry after the pending stack (2,689 cases
      at 797b28fa, 1,707 of them confined), and the seven declarations whose suite now loads
      scripts/suites/support/compiled_sources.py while their declared files omit it
      (effects-worker-scope, message-speaker-is-edge, account-codex-old-tables, limit-unreported,
      codex-baseline-user-config-loaded, worker129-build-unwired,
      receiver148-placement-wait-unbounded, by a scan of the stack). Completeness: the proposal
      report lists every confined case of the inventory, compared by identity with the
      coordinator's enumeration; each proposal records the digest of every file it read, and row
      declarations/stale-found requires each of the seven to be reported stale and re-proposed
      with the helper included.
    falsified_by: >
      Drop scripts/suites/support/ from the proposer's captured reads. Registered mutant
      declarations217-support-dropped must fail declarations/stale-found.
  - id: AC2
    text: >
      Claim: a declaration is marked reviewed only through a review record that matches it, and
      only when every mechanical condition holds: baseline, no-op and mutant traced to exit 0; two
      independent baseline traces with the same read set; the traced baseline observation equal to
      the last fresh gate observation; no non-file input class of AC4 in any trace; no gate entry
      among its inputs; and a reviewed toolchain. Set: one declaration failing each condition, one
      passing all, and a review record whose declaration digest does not match. Completeness: row
      declarations/review-conditions drives each through case_reuse; the reviewed flag lands only
      in scripts/mutation_case_inputs.json, a protected path, so each batch also carries the
      owner's commit-bound approval.
    falsified_by: >
      Accept a declaration whose two baseline traces read different files. Registered mutant
      declarations217-one-trace-enough must fail declarations/review-conditions.
  - id: AC3
    text: >
      Claim: a qualified case's key covers every file input it reads, because the worker runs in a
      snapshot that holds only its declared files and the coordinator's trace refuses any other
      repository probe; the key binds those files' names, modes and bytes, the case's projected
      registry entry, the mandatory machinery, the suite's prerequisite closure, the support helpers
      it loads, the declaration, the reviewed toolchain (the interpreter, libraries, shell, Git and
      locale files the trace shows, each by content), the fixed worker environment and the
      authority identity. Set: one edit to each class of input, and an edit to an undeclared file.
      Completeness: row declarations/key-covers-inputs requires each class of edit to miss exactly
      the cases that declare it and the undeclared edit to miss none of them.
    falsified_by: >
      Leave the support helpers out of the snapshot key while keeping them in the snapshot.
      Registered mutant declarations217-helper-not-keyed must fail declarations/key-covers-inputs.
  - id: AC4
    text: >
      Claim: a non-file input that could carry a change into an unchanged case is refused
      mechanically from the trace, never by a reviewer's judgment: a connection or datagram to any
      address but loopback, a Unix socket connection outside the case's own private roots, any
      message to a session or user bus, and any process the case causes to run outside its traced
      tree. A case whose trace shows one stays fresh with that class as its reason. Set: fixture
      cases that connect to a non-loopback address, to the user bus, to a Unix socket under the
      owner's runtime directory, and one that serves and connects on loopback only. Completeness:
      row declarations/non-file-refused requires the first three fresh with their class and the
      fourth eligible.
    falsified_by: >
      Classify a user-bus connection as loopback traffic. Registered mutant
      declarations217-bus-allowed must fail declarations/non-file-refused.
required_evidence: [unit, integration]
rollback: Revert the declarations to reviewed false; every case runs fresh, as at main.
---

## Intent

The canonical gate of 2026-10-25 reported reuse_qualified 0, and not only because declarations are
unreviewed. The receipt's reasons are: 1,688 cases have no declaration (unknown_closure), 982 run in
the unconfined leg (unconfined_leg, VELDO-0208), and 19 have an unreviewed declaration. Only 30
declarations exist, all reviewed false, and 11 of them belong to unconfined suites. Reviewing
today's file would make at most 19 of 2,689 cases reusable.

The file is also out of date: the pending stack makes 12 suites load
scripts/suites/support/compiled_sources.py, and seven declared cases of those suites do not list it.

## Design

Proposals at scale. scripts/propose_case_inputs.py traces one case at a time today; three traced
runs for each of 1,707 confined cases at the measured median of 19 seconds per worker is about 27
hours serially. It now admits traced workers through the coordinator's pool and the gate-wide
ledger (VELDO-0216, VELDO-0219): about two to three hours on the qualification host. It never runs
inside a gate. A later pass re-traces only cases whose recorded inputs changed.

Review at scale. The review record (proof/VELDO-0217/reviews/) is per batch, written by an
independent reviewer under the repository's L2 rule, and binds each declaration digest to its trace
digests. case_reuse checks every condition of AC2 itself; the reviewer judges the rationale only.
The reviewed flag lands through the owner's commit-bound approval because the file is protected.

Non-file inputs, under the owner's decision D2 (reuse only when every input a case reads is traced
or mechanically refused; the sample audit of VELDO-0218 is never the only detector). Inputs that
can carry a change from outside the case's files (network peers, host services, processes outside
the traced tree) are refused mechanically by AC4. Two classes remain that no unprivileged tracer
on this kernel can key: reads of the clock (Python reads it through the vDSO, which strace never
sees) and the values of random bytes (getrandom is visible, but its bytes are not an input the key
can bind unless the gate supplies them, for example through the seccomp notification broker
VELDO-0208 already runs). These two cannot carry a change into a case whose files are unchanged;
they are sources of run-to-run variance, which the two-trace condition of AC2 and VELDO-0223's
contention rules address. Treating them so is an owner ruling D2 does not yet cover. Until the
owner rules, case_reuse refuses to qualify any declaration (reason non_file_ruling_pending), so
nothing is reused; the proposal and review work proceeds.

## How many cases a landing re-runs

Using VELDO-0207's traced read sets of 30 sampled cases (proof/VELDO-0207/fan-in-full.json) and the
files changed by the last 37 landings on main grouped by specification id, the share of declared
cases a landing invalidates is bimodal:

- landings that change only suites or a few specific modules (22 of 37): 0 to 7 percent, median 3;
- one landing in between, at 20 percent;
- landings that change a shared engine module under .veldo/ (14 of 37): 70 to 100 percent, typically
  73, because about two thirds of sampled cases lay down a fixture repository that copies all 233
  engine modules (VELDO-0225 targets this).

So a landing that changes a few suites re-runs about 50 to 120 of the 1,707 confined cases, plus
every unconfined case that VELDO-0222 cannot qualify, plus VELDO-0218's audit sample; a landing that
changes a shared engine module re-runs about 1,250 confined cases. With the non-file ruling pending,
it re-runs all of them. Saving on a typical landing once qualified: about 1,600 confined cases not
re-run, some 40,000 worker seconds, about 25 minutes at the admission VELDO-0219 expects (about 26
workers).

## Out of scope

Unconfined cases (VELDO-0222); a stale declaration's handling at gate time (VELDO-0224); the audit
(VELDO-0218); suite result reuse (VELDO-0206); any change to a case, an assertion, the worker
confinement or the tracer's rules.

## What the reviewer judges

Normal use: the owner runs the proposer outside a gate, an independent reviewer reviews a batch, the
owner approves the protected file, and gates then reuse qualified cases. Threat model: as in
VELDO-0207 and VELDO-0208. Out of review scope: planted records in the owner's store.

## Notes

Numbers come from the 2026-10-25 canonical receipt (canonical-mutations.json, case_receipts) and a
scan of the pending stack at 3ab6e90d; the mechanical staleness check, not the list in AC1, is the
authority.
