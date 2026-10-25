---
schema: veldo.spec/v1
id: VELDO-0222
title: Unconfined mutation cases may reuse results, but only from declared snapshots
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0217, VELDO-0218]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/case_trace.py", "engine/scripts/case_trace.py", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py", "scripts/propose_case_inputs.py", "scripts/mutation_case_inputs.json"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/case_inputs.py
  - engine/scripts/case_inputs.py
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - scripts/propose_case_inputs.py
  - scripts/mutation_case_inputs.json
  - scripts/check_teeth_mutations.py
  - scripts/suites/101_veldo_0208_landing_reuse.py
  - scripts/suites/*_veldo_0222_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0208-single-user-landing-reuse.md
  - specs/VELDO-0222-unconfined-cases-reuse-results-from-declared-snapshots.md
  - specs/index.md
  - proof/VELDO-0222/*
behavior_bearing: true
observability:
  logs: The stage names each unconfined case's qualification decision and reason, and for a qualified case the units it started and where their paths resolved.
  metrics: Unconfined cases declared, reviewed, qualified, reused, audited and fresh per stage.
  traces: An unconfined case's key adds the user manager's identity and the declared host service inputs; its receipt entry carries leg unconfined.
  error_taxonomy: An undeclared probe by the worker tree is declaration_stale (fresh rerun, no publication); a unit whose paths leave the snapshot, the private home or the keyed runtime set is unit_outside_snapshot (verdict kept, never published); row-scoped suites, gate entries and nested tracers never qualify.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: an unconfined case qualifies only with a reviewed declaration (VELDO-0217) and then
      runs in a per-case snapshot holding only its declared files, with no link to the authority
      checkout, the candidate or the frozen input tree, a private home and temporary directory, and
      its worker process tree traced by the coordinator from outside; an undeclared repository probe
      or a read outside the snapshot, the private home, the keyed runtime set and the declared host
      service inputs makes it declaration_stale. It still runs unconfined: no confinement rule
      changes. Set: a qualified unconfined fixture case, one whose child reads an undeclared file,
      and one that reads a file under the owner's home. Completeness: row
      unconfined-reuse/snapshot-and-trace drives the three through the real coordinator with a
      scratch store.
    falsified_by: >
      Run the qualified unconfined case in the frozen input tree instead of its snapshot. Registered
      mutant unconfined222-full-tree must fail unconfined-reuse/snapshot-and-trace.
  - id: AC2
    text: >
      Claim: what the user manager starts for a case cannot be traced, so it is bounded instead.
      Before cleanup the coordinator reads every unit and slice in the case's ownership ledger from
      the manager and requires each executable, working directory and path-valued setting to resolve
      inside the snapshot, the private home or the keyed runtime set; otherwise the case's verdict
      stands but its result is never published (unit_outside_snapshot). Set: a fixture case whose
      unit runs from the snapshot, one whose unit runs a script from the owner's checkout, and one
      whose unit's working directory is the owner's home. Completeness: row
      unconfined-reuse/units-bounded requires the first to publish and the other two not to.
    falsified_by: >
      Skip the unit inspection for units the case stopped before it exited. Registered mutant
      unconfined222-stopped-unit-skipped must fail unconfined-reuse/units-bounded.
  - id: AC3
    text: >
      Claim: an unconfined case's key adds the systemd user manager's version and the digest of the
      declared host service inputs (for example the user's systemd configuration directory) to the
      VELDO-0217 key; reused unconfined results are audited at 10 percent under VELDO-0218; and
      these never qualify: cases of a suite listed for some rows (refused as today), cases whose
      inputs include a gate entry, and cases whose suite runs its own tracer. Set: a manager version
      change, a configuration edit, and one case of each excluded class. Completeness: row
      unconfined-reuse/key-and-exclusions requires the first two to miss every unconfined case and
      each excluded case to run fresh with its reason.
    falsified_by: >
      Leave the manager version out of the key. Registered mutant unconfined222-manager-unkeyed must
      fail unconfined-reuse/key-and-exclusions.
required_evidence: [unit, integration]
rollback: Restore the unconfined_leg reason for every unconfined case; they run fresh and are never published, as VELDO-0208 shipped.
---

## Intent

982 of the 2,689 cases run in the unconfined leg, and VELDO-0208 made each of them fresh on every
gate: "An unconfined case is neither traced nor confined, so nothing bounds what it read: it is
never reuse-qualified." On 2026-10-25 those cases and their controls were 1,320 of 3,481 workers and
38,472 of 82,740 worker seconds, 46 percent of the mutation stage. Even with every confined case
reused, a landing that changes one suite would still re-run all of them: about 25 minutes of wall
time at the admission VELDO-0219 expects, up to 40 where the manager's 16 slots bind, so the owner's 30-minute target for a typical landing cannot be
met without bounding what an unconfined case reads.

## Owner decision this needs

This amends VELDO-0208's rule for unconfined cases, so it is the owner's decision, not a review
finding. It weakens no confinement: the same suites still run unconfined, for the same reason
(the user manager starts units outside any Landlock domain). It changes only whether a result
produced there may be reused, and it bounds that with three mechanisms of which only the third is
not mechanical: the per-case snapshot makes an undeclared repository file absent, the coordinator's
trace sees every read of the worker's own process tree, and the units the manager starts are
checked to run from the snapshot. A unit's own reads are not traced; a unit that reads the owner's
checkout by an absolute path it was never given would go unseen. That residual is stated, it
belongs to the same-account threat model VELDO-0208 already accepts for this leg, and VELDO-0218's
audit at 10 percent is its detector.

## Design

The coordinator treats a qualified unconfined case like a declared confined one, minus the
Landlock layer: the case gets its snapshot at admission (case_reuse.prepare), reuse_worker.py
starts in mode unconfined with the snapshot as its root, and the coordinator's strace log covers the
worker tree. Tracing an unconfined worker is permitted because no Landlock domain stands between the
coordinator and the worker; cases of suites that trace their own children cannot be traced again
and stay fresh.

The proposer gains an unconfined probe: today it confines every probe through
mutation_sandbox.confine, which is why it cannot propose for these suites. The unconfined probe uses
the same snapshot and trace, and records the units and slices the case started, so the reviewer
sees them.

Expected effect: in a landing that changes a few suites, unconfined re-runs fall from 982 cases to
the same 3 to 7 percent VELDO-0217 measures for confined cases, about 30 to 70 cases, plus a 10
percent audit of the reused ones, about 90 to 95 cases: some 30,000 worker seconds less, about 20
minutes of wall time at measured admission. How many unconfined cases qualify at all is measured
by the first proposal pass and recorded in the proof.

## Out of scope

Which suites are unconfined (scripts/gate_unconfined.json is unchanged); the worker confinement of
confined cases; the user manager's own behavior.

## What the reviewer judges

Normal use: landing gates with authenticated reuse on the owner's host. Threat model: VELDO-0208's
same-account model for the unconfined leg. Out of review scope: deliberate escapes by suite code
running with the owner's authority, and reads by manager-started units through absolute paths
outside everything the case was given (the stated residual).

## Notes

VELDO-0208's unconfined-leg section gains a pointer to this specification when it lands; until then
its rule stands.
