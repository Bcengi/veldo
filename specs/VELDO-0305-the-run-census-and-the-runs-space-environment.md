---
schema: veldo.spec/v1
id: VELDO-0305
title: "The run census and the run's space environment"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "scripts/suites/*_veldo_0305_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0305-the-run-census-and-the-runs-space-environment.md"
  - "specs/index.md"
  - "proof/VELDO-0305/**"
behavior_bearing: true
observability:
  logs: >
    Each census writes the items it declared and each size with the event it was measured at.
  error_taxonomy: >
    None of its own. An untracked path git does not ignore is never recorded as an item; it makes the
    worktree unique work.
acceptance_criteria:
  - id: AC1
    text: >
      At each run event every ignored folder git reports in the run's worktree that a committed ignore
      file of the project or a declared pattern covers becomes a build output item, whatever its name and
      depth; a keep entry is left out, and so is a folder only a personal ignore rule covers
    falsified_by: >
      Match the name target; the row's folder named otherwise has no item and fails
  - id: AC2
    text: >
      An untracked path git does not ignore is never recorded as build output and makes the worktree
      unique work. So does an ignored path that no committed ignore file and no declared pattern covers,
      and a loose ignored file outside every build output folder
    falsified_by: >
      Record every untracked folder; the row's new source folder becomes build output and fails
  - id: AC3
    text: >
      The run's temporary folder and build variables point at folders declared before the worker starts
    falsified_by: >
      Set the variables without declaring; the row finds the build root with no item and fails
  - id: AC4
    text: >
      In a worktree reconcile adopted, only folders matching the project's declared patterns are recorded
    falsified_by: >
      Apply the ignored-folder rule to adopted worktrees; the adopted fixture's ignored data folder
      becomes build output and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Runs leave build output with no record.
---

## Intent

An agent's own commands create build folders Veldo never sees being made. At each run event the receiver
reads what the run left: every ignored folder git reports in the run's worktree becomes a build output
item, whatever its name. The run's temporary folder and build root are declared before the worker starts.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.3 (what a run is given, and the
census) and 8.1 (steps 4 and 7). Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Receiver.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC1: an ignored folder is build output only when a committed ignore file of the project or a declared
  pattern covers it; a folder only a personal ignore rule covers is left out. AC2: an ignored path that
  nothing of the project covers, and a loose ignored file outside every build output folder, make the
  worktree unique work, because git's non-forced worktree remove deletes ignored files without refusing.
  Both falsifiers are unchanged. Rule 5's reading of such a path is VELDO-0347 AC1.
