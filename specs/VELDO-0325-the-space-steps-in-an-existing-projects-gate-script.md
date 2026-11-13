---
schema: veldo.spec/v1
id: VELDO-0325
title: "The space steps in an existing project's gate script"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0332]
placement: [engine, loop, docs]
protected_paths: []
footprint:
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "docs/setup.md"
  - "scripts/suites/*_veldo_0325_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0325-the-space-steps-in-an-existing-projects-gate-script.md"
  - "specs/index.md"
  - "proof/VELDO-0325/**"
behavior_bearing: true
observability:
  logs: >
    space gate-check prints each of the three calls as present, missing or misplaced. Reconcile lists each
    bound project whose gate script fails the check under space.reports.
  error_taxonomy: >
    A failing check names the missing or misplaced call. It is a report, not a refusal: the project's
    gates still run, through the run wrapper.
acceptance_criteria:
  - id: AC1
    text: >
      space gate-check says, for a project's gate script, whether the need call is before the first check,
      the classify call before the stamp and the verdict call after it; a fixture script laid before the
      change fails the check by naming the missing calls
    falsified_by: >
      Look for the helper's name anywhere in the file; the fixture with the verdict call placed before the
      stamp passes and the row fails
  - id: AC2
    text: >
      Reconcile lists every bound project whose gate script fails the check under space.reports, and a
      project leaves the list when its script passes
    falsified_by: >
      Check the engine's template only; the adopter fixture whose gate script predates the change is not
      listed and the row fails
  - id: AC3
    text: >
      A gate script that predates the change, run through the run wrapper, is admitted before it starts
      and has its build output removed at run finished
    falsified_by: >
      Skip the census for a wrapped gate; the row finds the build folder present after the gate and fails
  - id: AC4
    text: >
      docs/setup.md holds the recipe for adding the three calls to an existing gate script, names no
      project, and passes the docs check
    falsified_by: >
      Name the measured host's project in the recipe; the docs check row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Projects whose gate lacks the space steps are no longer listed.
---

## Intent

A change to the gate script template reaches only repositories initialized after it; an existing project's
gate script is its own file. This ticket adds the check that says whether a gate script has the three
calls in the right places, lists the projects that lack them, covers their gates through the run wrapper
until then, and writes the recipe for adding the calls.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 8.2 (which gates the change
reaches), 6.9 (the gate whose script does not have the steps yet) and 3 (the gate script is each
repository's own file). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: CLI (space gate-check), Reconciler, documents. The change to each project's own gate script is
> that project's spec, made from the recipe this ticket writes, and is approved by the owner there.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

This ticket touches no protected path in this repository. The change it leads to in each bound project's
scripts/verify.sh is that project's own spec, made from the recipe this ticket writes, on a path protected
in that project, and it is approved by the owner there.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
