---
schema: veldo.spec/v1
id: VELDO-0273
title: Each gate runs the test suites that cover the code its candidate changed plus a fixed canary set, and the full suite set runs nightly on the trunk through VELDO-0267's runner
status: ready
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0267, VELDO-0271]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/selftest.py", "scripts/run_scope.py", "scripts/check_first_use.py", "scripts/suites/shared.py", "scripts/gate_graph.json"]
footprint:
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "scripts/selftest.py"
  - "scripts/run_scope.py"
  - "scripts/check_first_use.py"
  - "scripts/suites/shared.py"
  - "scripts/gate_graph.json"
  - "scripts/mutation_selection.py"
  - "engine/scripts/mutation_selection.py"
  - "scripts/mutation_selection.json"
  - "scripts/mutation_nightly.py"
  - "engine/scripts/mutation_nightly.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/*_veldo_0273_*.py"
  - "specs/VELDO-0273-each-gate-runs-the-suites-its-change-touches-and-the-full-set-runs-nightly.md"
  - "specs/index.md"
  - "proof/VELDO-0273/**"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    The unit stage prints, before any suite runs, one selection line in VELDO-0267's form: mode
    (selected or full), base and candidate commits, changed path count, the suite coverage map's run
    id and digest, the number of suites selected by each reason (suite file, covered file, no coverage
    record, canary) and the closure size actually run; in full mode, the trigger that forced it.
  metrics: >
    last_verify gains a suites block beside VELDO-0267's mutation block: mode, suites selected, suites
    run with their closures, the stage's wall seconds, and the nightly run the landing relies on.
  traces: >
    The selection record (VELDO-0267's veldo.mutation-selection/v1, with a suites section) is written to
    the gate's evidence for every run, with every reason, so the set can be recomputed from it.
  error_taxonomy: >
    No new names. The suite selection uses VELDO-0267's canary_not_killed analogue for suites
    (canary_red), selection_unavailable (falls back to the full set, never fewer), nightly_red and
    nightly_stale with the same meaning, now covering the suite half of the nightly run.
acceptance_criteria:
  - id: AC1
    text: >
      At each gate the unit stage runs a selection of the suites in scripts/suites/manifest.json, not all
      of them, computed by VELDO-0267's selection module from the same inputs (candidate, base, changed
      paths with renames and dirty paths, the coverage map of the last green nightly run). A suite is
      selected when a changed path is its own file or a file in its covered set (the repository files
      its run read in the nightly run, child processes included, as recorded by scripts/case_trace.py
      with reads attributed to the fragment running when they happened). A suite the coverage map does
      not know (new, or its file digest changed) is always selected. Because the suites are fragments of
      one namespace, the stage runs the union of the selected suites' prerequisite closures
      (scripts/suites/requires.json) in manifest order, exactly as selftest.py --suite does today, and
      run_scope.py accepts that run as a gate pass only when it carries the selection record's digest;
      every other partial run still raises PARTIAL_RUN_CANNOT_VERIFY.
    falsified_by: >
      A new suite drives the selection over a fixture manifest of four fragments (B requires A; C reads
      shared.txt; D is unrelated): changing B's file runs A and B plus the canaries; changing shared.txt
      runs C; changing a docs file runs only the canaries; adding a fifth fragment selects it on the next
      run. Registered mutations from a green baseline: (1) the run drops the closure: the B row goes red
      because A's names are missing; (2) the rule ignores covered files: the shared.txt row goes red; (3)
      run_scope accepts a partial run without a selection digest: the partial-run row goes red.
  - id: AC2
    text: >
      A fixed canary set of suites runs at every gate whatever the selection is, declared in a suites
      section of scripts/mutation_selection.json (VELDO-0267's declaration, not a second file): between
      five and ten suites, including at least one that starts a systemd user unit, one that drives the
      control store and one that runs the push guard. Any canary red makes the stage red. The integration
      stage (check_first_use.py) runs its nested suite run over the same selection, not the full set.
    falsified_by: >
      Registered mutations from a green baseline: (1) the canaries are skipped when the selection is empty:
      the empty-selection row goes red because the verdict line counts zero canaries; (2) the suites
      section is emptied in a fixture copy of mutation_selection.json: the declaration row goes red naming
      the bound of five; (3) check_first_use.py runs the full set under a selection: the nested-run row,
      which counts the nested run's suites, goes red.
  - id: AC3
    text: >
      The gate runs the full suite set instead of a selection when the candidate changes what decides or
      runs the suites, or when the selection cannot be trusted: a suites trigger list in
      mutation_selection.json holding at least selftest.py, run_scope.py, suites/shared.py,
      suites/manifest.json, suites/requires.json, check_first_use.py, case_trace.py, verify.sh,
      gate_graph.json, mutation_selection.py and mutation_selection.json, with engine copies; a toolchain
      change; a missing or unreadable suite coverage map; or no green or explained nightly run in the last
      36 hours. The selection line names the trigger. A full-set gate is today's unit stage.
    falsified_by: >
      The suite changes one path from each trigger group in a fixture copy and requires mode full naming
      it; it removes and ages the coverage map and requires mode full with each reason. Registered
      mutations: (1) the trigger list drops selftest.py: the self-change row goes red; (2) the 36 hour
      bound is skipped: the stale row goes red.
  - id: AC4
    text: >
      VELDO-0267's nightly runner (scripts/mutation_nightly.py) also runs the full suite set on the trunk
      tip, under the same lock, scope and record, with the tracer on, and publishes the suite coverage map
      only when every suite is green. A red suite run is reported in the same Telegram message and blocks
      landing as nightly_red until a later run is green or the owner's approval names the run id and each
      red suite. No second runner, lock, record schema or crontab line is added.
    falsified_by: >
      The runner over a fixture trunk with one red suite yields a red record naming it, one notifier call,
      a landing refusal nightly_red and no new suite coverage map; a later green run clears the refusal
      and publishes the map. Registered mutations: (1) a red suite run publishes its map: the publish row
      goes red; (2) the landing check ignores the suite half: the red-blocks row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The unit stage runs every suite at every gate again, and the nightly runner returns
  to mutation only. The suite coverage maps sit in the state directory and are read by nothing after the
  revert.
---

## Intent

The owner agreed (Telegram 39690 to 39692) that each gate runs the suites that cover the code its
candidate changed plus a fixed canary set, and the full suite set runs nightly. VELDO-0267 does this
for mutation; this spec does it for the suites with the same selection model, module, declaration,
nightly runner and refusals, so there is one selection mechanism, not two.

## Context

Verified in the code on main at afa292f0:

- The unit stage runs all 192 fragments of scripts/suites/manifest.json in one shared namespace
  (selftest.py). The fragments are order dependent: the manifest note records suite_equiv's verdict
  that every fragment passes in aggregate and fails alone. So a selection cannot run a suite on its own;
  it runs the suite's prerequisite closure from scripts/suites/requires.json, which selftest.py
  --suite already uses (WARP-0717). That selector is refused as a gate pass today by run_scope.py
  (PARTIAL_RUN_CANNOT_VERIFY); AC1 admits exactly one partial run, the recorded selection.
- The integration stage (check_first_use.py) is a second, nested full suite run. In the 0261 landing
  gate the unit legs ended at 1,440 s and 2,398 s and the integration legs at 2,819 s and 5,080 s, so
  selection shortens both. VELDO-0278 may take the integration stage off the gate entirely; whichever
  lands first, the other drops or keeps its integration clause.
- Landing order: VELDO-0267 (selection module, nightly runner), VELDO-0271 (one leg per stage, which
  rewrites selftest.py and run_scope.py), then this spec.

Expected effect, an estimate from one green run to be re-measured on the first gates after landing: an
ordinary candidate's unit stage runs its closures plus the canaries in minutes rather than about 40.

## Out of scope

The mutation selection itself (VELDO-0267); splitting fragments into independent modules; the reuse
machinery (VELDO-0279 deletes it); core's gate.

## What the reviewer judges

- Normal use: the gate on a candidate commit on this host; the nightly runner on the trunk.
- A suite can be missed only through a changed path that neither its file nor its traced reads contain;
  every failure to compute the selection runs the full set.
- Threat model: the same account; a candidate that rewrites the selection rule triggers the full set.
- Out of review scope: per the template.

## History

2026-11-07: drafted by the lead under the owner's narrowed approval scope (Telegram 39708, 39710) from
the agreed item (Telegram 39690 to 39692). A draft.

2026-11-07: ready by the lead under the owner's narrowed approval scope (Telegram 39708): test machinery and cleanup, no money, security, schema or infrastructure decision.

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).
