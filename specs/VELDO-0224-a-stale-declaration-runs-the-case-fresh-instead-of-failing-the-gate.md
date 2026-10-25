---
schema: veldo.spec/v1
id: VELDO-0224
title: A stale input declaration runs its case fresh instead of failing the gate
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0207, VELDO-0217]
placement: [enforcement]
protected_paths: ["scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/case_trace.py", "engine/scripts/case_trace.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/mutation_reuse.py", "engine/scripts/mutation_reuse.py"]
footprint:
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_reuse.py
  - engine/scripts/mutation_reuse.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/100_veldo_0207_case_reuse.py
  - scripts/suites/*_veldo_0224_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0207-declared-case-reuse.md
  - specs/VELDO-0224-a-stale-declaration-runs-the-case-fresh-instead-of-failing-the-gate.md
  - specs/index.md
  - proof/VELDO-0224/*
behavior_bearing: true
observability:
  logs: The stage names every case it ran fresh as declaration_stale, with the undeclared path or the missing declared file that made it stale.
  metrics: Stale counts per stage; the authority's stale list size.
  traces: Each stale entry in the authority store binds the case identity, the declaration digest and the gate run that found it.
  error_taxonomy: declaration_stale runs fresh and is never published; a failing fresh run is RED as that failure; a stale entry never changes the protected declarations file.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a qualified case is stale when its snapshot run reports an undeclared probe, when a
      declared file no longer exists, or when its reviewed declaration no longer closes (today a
      ValueError from case_reuse that stops the whole stage); a stale case is run again fresh in the
      full frozen tree in the same stage, its verdict comes from that fresh run, and the stage stays
      green when that run is valid. Set: a declared case whose suite gains an import of an
      undeclared helper, one whose declared file is deleted, and one whose declaration no longer
      closes. Completeness: row stale-declarations/runs-fresh drives all three through the real
      coordinator and requires each fresh, validated and named declaration_stale, and the stage red
      when a fresh run itself fails.
    falsified_by: >
      Keep the snapshot run's verdict when its trace reports an undeclared probe. Registered mutant
      stale224-snapshot-verdict-kept must fail stale-declarations/runs-fresh.
  - id: AC2
    text: >
      Claim: nothing a stale case produced is published, under the stale key or any other, and no
      earlier record for it is reused in the same gate. Set: the three stale cases above with a
      scratch store holding an earlier valid record for each. Completeness: row
      stale-declarations/never-published requires zero publications and zero reuse for them.
    falsified_by: >
      Publish the fresh rerun under the stale declaration's key. Registered mutant
      stale224-published must fail stale-declarations/never-published.
  - id: AC3
    text: >
      Claim: the stale mark is written to the authority's own store (a stale list beside the
      authenticated result store, outside every candidate and worker grant), never to
      scripts/mutation_case_inputs.json or any other file of the candidate tree; the proposer reads
      that list to choose what to re-trace, and VELDO-0218's audit writes its mismatches there too.
      Set: a stale finding in candidate mode against a fixture candidate. Completeness: row
      stale-declarations/authority-store requires the candidate tree's identity unchanged and the
      entry present in the authority store.
    falsified_by: >
      Write the stale mark into the candidate's declarations file. Registered mutant
      stale224-writes-candidate must fail stale-declarations/authority-store.
required_evidence: [unit, integration]
rollback: Revert to VELDO-0207's rule; a stale declaration fails the stage loudly again.
---

## Intent

VELDO-0207 made an undeclared probe in a declared case fail the stage, and case_reuse turns a
reviewed declaration that no longer closes into a ValueError that stops the stage. That was right
while declarations were few and made by hand. Once every confined case is declared (VELDO-0217), a
landing that adds one import to one suite would turn the gate red for a bookkeeping reason, while
nothing about the change is wrong. This spec changes that rule and only that rule: the stale case
loses reuse and runs fresh, so it still gets a real verdict in the same gate.

## Design

The coordinator already traces a declared worker and checks the trace before trusting its output.
On a stale finding it releases the snapshot, queues a fresh job for the same case in the frozen
input tree with its own controls, and records the reason. case_reuse catches a declaration that no
longer closes per case instead of raising for the stage. Stale marks go to the authority store, so
the protected declarations file changes only through the proposer and the owner's approval.

Expected cost: one extra fresh case per stale declaration; no time saved by itself, but without it
full declaration coverage would make the gate fragile.

## Out of scope

How declarations are proposed and reviewed (VELDO-0217); the audit (VELDO-0218); unconfined cases
(VELDO-0222).

## What the reviewer judges

Normal use: landing gates with reviewed declarations. Threat model: as in VELDO-0207 and VELDO-0208.
Out of review scope: a planted stale list in the owner's store (it can only make cases run fresh).

## Notes

VELDO-0207's design section gains a pointer to this specification when it lands.
