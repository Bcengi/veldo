---
schema: veldo.spec/v1
id: VELDO-0278
title: Tokens of Effort leaves the gate and the mutation sets until a spend source exists, and the integration stage that only guards its first use leaves with it
status: draft
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0267, VELDO-0271]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/check_first_use.py", "scripts/mutation_case_inputs.json", "scripts/gate_graph.json"]
footprint:
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "scripts/check_first_use.py"
  - "scripts/gate_graph.json"
  - "scripts/mutation_case_inputs.json"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/suites/15_warp_14*.py"
  - "scripts/suites/16_warp_1403_sizing_pass.py"
  - "scripts/parked/**"
  - "scripts/suites/*_veldo_0278_*.py"
  - "specs/VELDO-0278-tokens-of-effort-leaves-the-gate-and-mutation-sets.md"
  - "specs/index.md"
  - "proof/VELDO-0278/**"
behavior_bearing: true
observability:
  logs: >
    The gate's catalog prints integration as na with its reason ("estimation layer parked until a spend
    source exists, VELDO-0278"). The parked runner prints its own summary line, never the gate's.
  metrics: >
    The gate stamp's checks_run drops by one and checks_na rises by one.
  traces: >
    None added.
  error_taxonomy: >
    None added or removed.
acceptance_criteria:
  - id: AC1
    text: >
      The estimation suites do not run at the gate. The eight fragments 15_warp_1402, 15_warp_1404,
      15_warp_1405, 15_warp_1406, 15_warp_1407, 15_warp_1408, 15_warp_1409 and 16_warp_1403 move to
      scripts/parked/estimation/ with their manifest entries and closures, runnable by one documented
      command (python3 scripts/selftest.py --parked estimation) that can never produce a gate pass.
      No remaining fragment depends on them, which the regenerated requires.json shows.
    falsified_by: >
      A row requires the unit stage's suite list to contain none of the eight names and the parked command
      to run all eight green. Registered mutation from a green baseline: the parked run is allowed to write
      a verify stamp: the no-gate-pass row goes red.
  - id: AC2
    text: >
      No mutation case mutates an estimation module or runs a parked suite: every case in
      scripts/check_teeth_mutations.py and scripts/mutation_case_inputs.json whose module is one of
      toe_analogy, toe_budget, toe_corpus, toe_normalize, toe_reconcile, estimate, sizing_pass,
      judgment_load or cost_to_change, or whose suite is parked, is removed, and the proof lists each
      removed case by name. Cases on spend.py and on the event vocabulary stay.
    falsified_by: >
      A row requires the registered case list to name none of the nine modules or eight suites. Registered
      mutation: one removed case is restored: the row goes red naming it.
  - id: AC3
    text: >
      The integration stage leaves the gate. Its only mutation family is recorded spend through
      .veldo/spend.py, which exists for the estimation layer, and it costs a second full suite run. In
      verify.sh CHECK_integration becomes na with the reason above, its node leaves gate_graph.json, and
      check_first_use.py moves to scripts/parked/estimation/. The unit stage's measured-seconds handoff
      to it (VELDO-0214) goes with it.
    falsified_by: >
      A fixture gate run shows no integration node, an na line with the reason, and a green stamp.
      Registered mutation: the integration node is left in gate_graph.json: the graph row, which requires
      every node to be a required catalog item, goes red.
required_evidence: [unit]
rollback: >
  Revert the commit: the suites, the cases and the integration stage return to the gate.
---

## Intent

Weight audit item 10, Veldo part: stop gating a subsystem nothing feeds, until a spend source exists; then
the owner decides whether to finish it. The code stays in the tree and keeps shipping to adopters.

## Context

Verified on main at afa292f0: the nine modules the audit names total 8,045 lines (toe_analogy 817,
toe_budget 1,090, toe_corpus 239, toe_normalize 840, toe_reconcile 1,537, estimate 1,014, sizing_pass
994, judgment_load 788, cost_to_change 726), as the audit says. Its suites are the eight fragments in
AC1.

Found beyond the audit: the integration stage (CHECK_integration, scripts/check_first_use.py, 539
lines) exists for this layer. Its docstring: it copies the repository, records spend for two specs with
.veldo/spend.py ("the whole point of the estimation layer") and runs the whole suite again to prove no
suite pins today's emptiness. In the 0261 landing gate the integration legs ended at 2,819 s and 5,080 s
against 1,440 s and 2,398 s for unit, so outside mutation it is the longest stage. With nothing recording
spend, it guards a first use that cannot happen. Removing it shortens the non-mutation gate from about
5,080 s to about 2,400 s, an estimate re-measured on the first gates after landing.

Lands after VELDO-0267 and VELDO-0271 (both change verify.sh, check_first_use.py and the mutation
inputs). If VELDO-0273 lands first, its integration clause is dropped when this one lands.

## Out of scope

Deleting the estimation code; spend.py and the event vocabulary; core's installed engine (the audit's
core half).

## What the reviewer judges

- Normal use: the gate on any candidate.
- Nothing that tests a non-estimation module leaves the gate.
- Out of review scope: per the template.

## History

2026-11-07: drafted by the lead from the weight audit's item 10 (Telegram 39708, 39710). A draft.
