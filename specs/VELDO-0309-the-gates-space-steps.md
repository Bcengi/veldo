---
schema: veldo.spec/v1
id: VELDO-0309
title: "The gate's space steps"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [enforcement, engine, loop]
protected_paths: ["engine/scripts/verify.sh", "scripts/verify.sh", "engine/scripts/gate_space.py", "scripts/gate_space.py", ".veldo/policy.yaml"]
footprint:
  - "engine/scripts/verify.sh"
  - "scripts/verify.sh"
  - "engine/scripts/gate_space.py"
  - "scripts/gate_space.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - ".veldo/policy.yaml"
  - "scripts/suites/*_veldo_0309_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0309-the-gates-space-steps.md"
  - "specs/index.md"
  - "proof/VELDO-0309/**"
behavior_bearing: true
observability:
  logs: >
    The gate prints the numbers when it would wait: need, free, held and floor. A no-space end prints
    GATE: NOT JUDGED with the reason. With no installation, or with space management off, the helper says
    so in one line.
  error_taxonomy: >
    GATE: NOT STARTED, exit 75, with no stamp and no event, when the gate must wait in act mode. GATE: NOT
    JUDGED, exit 75, with no stamp and no event, for environment_failure:no_space. Neither is a verdict.
acceptance_criteria:
  - id: AC1
    text: >
      In a repository with no gate_host.json, the need step runs before the first check: in act mode with
      too little space the answer is GATE: NOT STARTED with the numbers, exit 75, no stamp and no event;
      in report mode the numbers are printed and the gate runs
    falsified_by: >
      Put the need step in the gate host; the fixture repository without the host file starts its checks
      and the row fails
  - id: AC2
    text: >
      A failed gate whose output holds the no-space error on a pool under its floor writes no stamp and no
      event and answers GATE: NOT JUDGED, exit 75
    falsified_by: >
      Classify after the stamp is written; the row finds a red stamp and fails
  - id: AC3
    text: >
      Verdict recorded is sent after the stamp and never before; the gated worktree's build folder is gone
      and its evidence present before the gate script exits; a gate killed before its stamp sends nothing
    falsified_by: >
      Send it before the stamp; the row that kills the gate between the two finds the build folder gone
      with no verdict and fails
  - id: AC4
    text: >
      With no central installation, or space management off, the gate runs and stamps exactly as before
      the change
    falsified_by: >
      Require the ledger; the adopter fixture with no installation goes red and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change to both gate scripts and take the helper off the protected paths. Gates run and stamp
  as before, and a gate that fills the disk stamps red again.
---

## Intent

A gate must not start on a disk that cannot hold its build, must not stamp red because the disk filled,
and must remove its build output once its verdict is recorded. This ticket adds three calls to the gate
script template and to this repository's own gate script: the need step before the first check, the
classify step before the stamp, the verdict step after it. The helper they call is new and is added to the
protected paths in the same change.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 8.2 (a gate, with or without a host
configuration), 8.9 (a run that hits a full pool), 6.7 (admission) and 6.9 (the gate rows). Section 12 of
the design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Gate script template, Gate space helper. Both protected: the owner's recorded approval is
> required, and the helper is added to the protected paths in the same change. This ticket changes
> engine/scripts/verify.sh and this repository's own scripts/verify.sh. Other existing repositories are
> VELDO-0325.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The gate script template and this repository's gate script are protected paths (policy.yaml:83 and 86).
The helper is new and is added to the protected paths in the same change, which is a change to
.veldo/policy.yaml, itself protected. The owner's recorded approval, bound to the commit and the proof, is
required.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.

- 2026-11-15: the footprint includes init_scaffold.py and its canon so a new adopter receives the helper its gate calls. The authority socket is VELDO-0323: until it serves the ledger, the helper reports ledger_unreachable, as the existing run wrapper does. Tests inject that wiring and exercise a real ledger. Admission retries and history remain VELDO-0316 and VELDO-0317; this ticket uses the existing admission arithmetic.
