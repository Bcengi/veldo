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

- 2026-11-15, fix round after the independent review (verdict FIX, five findings):
  - The hold belongs to the gate process that took it. Its identity names the run, the gate's process id,
    that process's start time and the boot. The gate script releases it on every exit path (a trap on
    EXIT, INT and TERM calls the helper's release step). A gate killed outright runs no trap: the next
    gate's need step reads the holds, finds the process gone (no such process, or the same process id with
    another start time) and releases the hold before it judges its own. Nothing waits for a time and
    nothing sweeps. A hold that is not a gate's is never touched there. The trap of INT and TERM runs when
    the check that is running returns, which is how bash delivers a trapped signal; the hold stands until
    then, and the check does use the space until then.
  - The suite's row names are fixed. What a failed row saw is printed on the error stream. A suite that
    stopped on a missing file lost its later rows, which the teeth tool also refuses; those reads no
    longer stop it.
  - The template runs the review events inside the refused-graph guard again, as this repository's copy
    does.
  - The gate's copy of its output is one folder per run, gate-space.<run>, in the gate's output folder
    (design 8.2). The need step declares it with the ledger before it is made. Decision: it is declared
    as build output of the gated worktree's owner, because it is the run's working copy for the classify
    step and not the evidence gate log of design 0.4; the cell of build output at verdict recorded is
    remove, so the verdict step names it in the same Signal as the worktree's build output and the
    folder remover removes it. The folder of a gate that never reached its verdict stays the ledger's
    item and goes with the next verdict in that output folder. A folder the ledger refuses (an output
    folder outside every known root) is not made and the gate answers NOT STARTED: a sink that is to be
    used with space management on must be inside a declared root (design 11 names the gate lock's log
    folder as a scratch root). Known effect: while an active gate runs, its folder is one untracked
    path, and the stamp's tree field counts it.
  - The copy ends at a line only the gate writes, as its last, and not at end of file, so the gate waits
    for its own child and for no process a check left running with the output open. At its exit the
    gate ends what is left of the process group it leads (the helper's group step). It leads one when
    the host holder started it, which makes it a session leader, or when a shell with job control did.
    A gate that is a member of its caller's group leads none and ends nobody, because ending that group
    would end the caller. The other children of the gate's parent (the commands of a pipeline the gate
    was started in) are not ended. With no installation, or space management off, none of this runs.
  - Found in this round by running the other suites that start a gate script, and not in the review:
    the first build made every gate whose installation has no helper file answer exit 75, which the
    host lock and scope suites (113, 114) showed, and it put the classify step and the review events
    between the stamp fields that suites 101 and 114 run on their own. An installation with no helper
    file now says so in one line and its gate runs as before; the classify step and the review events
    stand before the stamp fields; the stamp writer is the first line of its branch again.
  - Not built here, as the reviewer noted: a no-space error on a pool at or above its floor keeps the
    ordinary verdict; the one repeat of design 8.9 step 4 belongs to the admission tickets.
