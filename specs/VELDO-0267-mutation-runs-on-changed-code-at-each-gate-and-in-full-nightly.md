---
schema: veldo.spec/v1
id: VELDO-0267
title: Each gate runs the mutation cases for the code its candidate changed plus a fixed canary set, the full sweep runs nightly on the trunk, and a red nightly sweep blocks the next landing until it is green or explained
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0123, VELDO-0207, VELDO-0216, VELDO-0219, VELDO-0220]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/verify.sh", "engine/scripts/verify.sh", ".veldo/policy_check.py", "engine/.veldo/policy_check.py", ".veldo/policy.yaml", "scripts/gate_graph.json", "scripts/mutation_selection.json", "scripts/mutation_selection.py", "engine/scripts/mutation_selection.py", "scripts/mutation_nightly.py", "engine/scripts/mutation_nightly.py", ".veldo/control_verification.py", "engine/.veldo/control_verification.py"]
footprint:
  - "scripts/check_gate_mutations.py"
  - "engine/scripts/check_gate_mutations.py"
  - "scripts/mutation_selection.py"
  - "engine/scripts/mutation_selection.py"
  - "scripts/mutation_selection.json"
  - "scripts/mutation_nightly.py"
  - "engine/scripts/mutation_nightly.py"
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "scripts/gate_graph.json"
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - ".veldo/policy.yaml"
  - "scripts/suites/140_veldo_0267_mutation_selection.py"
  - "scripts/suites/manifest.json"
  - "specs/VELDO-0267-mutation-runs-on-changed-code-at-each-gate-and-in-full-nightly.md"
  - "specs/index.md"
  - "proof/VELDO-0267/**"
  - ".veldo/lander.py"
  - "engine/.veldo/lander.py"
  - ".veldo/control_verification.py"
  - "engine/.veldo/control_verification.py"
  - ".gitignore"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    The mutation stage prints, before any case runs, one selection line: the mode (selected or full),
    the base and candidate commits, the number of changed paths, the coverage map's run id and digest,
    the number of cases selected by each reason (mutated module, suite file, covered file, no coverage
    record, canary) and, in full mode, the trigger that forced it (a named path, a toolchain change, a
    missing or stale coverage map). The nightly runner prints its start, the lock wait, the trunk
    commit it swept, its end and its verdict line in the same form the gate prints today
    ("mutations: passed registered=... executed=... reused=... workers=... elapsed=...").
  metrics: >
    The gate's last_verify gains a mutation block: mode, cases selected, cases run, the stage's wall
    seconds, and the nightly sweep the landing relies on (run id, trunk commit, verdict, finished at).
    The nightly record carries its wall seconds, CPU seconds and peak memory as the gate host line
    reports them today, so the full sweep's cost stays measured after it leaves the gate.
  traces: >
    The selection record (veldo.mutation-selection/v1) is written into the gate's evidence for every
    run: the base, the candidate, every changed path, the coverage map digest, and for every registered
    case whether it was selected and every reason it was. Anyone can recompute the selection from that
    record and the coverage map and get the same set.
  error_taxonomy: >
    New stage refusals, all red: canary_not_killed (a canary's mutant survived or its baseline was not
    green), selection_unavailable (the base, the changed paths or the selection rule could not be read;
    the stage falls back to the full sweep and says so, it never runs fewer cases), nightly_red (the
    latest nightly sweep is red and unexplained; refuses landing only), nightly_stale (no green or
    explained nightly sweep finished within the last 36 hours; the gate runs the full sweep). No
    existing refusal changes its name or meaning.
acceptance_criteria:
  - id: AC1
    text: >
      At each gate the mutation stage runs a precise selection of the registered cases of both drivers
      (check_teeth_mutations.py and check_review_mutations.py), not all of them. The inputs are the
      candidate commit, its base (the merge base with the trunk commit the gate is told to compare
      against; for a landing, the trunk commit the lander synced, the same BASE policy_check already
      takes), the changed paths between them (git diff with rename detection, both sides of a rename
      counted, a working tree that is not clean counted as changed in every dirty path), and the
      coverage map from the last green nightly sweep. A case is selected when any changed path is (a)
      the module the case mutates, at its root or its engine copy, (b) the case's suite file, or (c) a
      file in the case's covered set: the files its declared entry in scripts/mutation_case_inputs.json
      names when it has one, otherwise the repository files its baseline read in the nightly sweep, as
      recorded by the existing tracer (scripts/case_trace.py). A case the coverage map does not know
      (new, or its definition digest changed) is always selected. Every reuse rule of VELDO-0205 to
      VELDO-0218 applies to the selected cases unchanged. The selection record with every input and
      every reason is written to the gate's evidence before the first case runs, and last_verify names
      its digest.
    falsified_by: >
      The new suite drives the selection over a fixture repository with three registered cases (A
      mutates m1.py, B's suite is s2.py, C's traced inputs include shared.py): changing only m1.py selects
      exactly A plus the canaries; changing shared.py selects C; changing an unrelated docs file selects
      only the canaries; adding a fourth case selects it on the next run whatever changed. Registered
      mutations, each from a green baseline: (1) the rule ignores covered files: the shared.py row goes
      red; (2) the rule ignores a case missing from the coverage map: the new-case row goes red; (3) the
      record omits a reason: the recompute row, which rebuilds the set from the record and compares,
      goes red.
  - id: AC2
    text: >
      A fixed canary set runs at every gate whatever the selection is, so a broken driver, worker or
      coordinator can never pass a gate by selecting nothing. The set is declared in
      scripts/mutation_selection.json (a protected path), holds between six and twelve cases, and covers
      both drivers, the confined and the unconfined leg, and at least one case that needs a service
      fixture. Each canary must show a green baseline, an equal no-op and a killed mutant; any other
      outcome reds the stage as canary_not_killed with the case and what it saw. A selection of zero
      cases is legal and still runs the canaries, and the stage's verdict line counts them separately
      from the selected cases.
    falsified_by: >
      Registered mutations, each from a green baseline: (1) the worker reports every mutant killed
      without running it: at least one canary's baseline row is red, so the stage is red; (2) the
      coordinator skips the canaries when the selection is empty: the empty-selection row goes red
      because the verdict line shows zero canaries; (3) the canary list is emptied in a fixture copy of
      scripts/mutation_selection.json: the declaration row goes red naming the bound of six.
  - id: AC3
    text: >
      The gate runs the full sweep instead of a selection when the candidate changes what decides or
      runs mutation testing, or when the selection cannot be trusted. The trigger list is declared in
      scripts/mutation_selection.json and holds at least: both drivers, check_gate_mutations.py,
      mutation_selection.py and mutation_selection.json themselves, mutation_case_inputs.json and every
      mutation_* and case_* script, the gate ledger and host files (gate_schedule.py, gate_host.py,
      gate_host.json), verify.sh, gate_graph.json, gate_legs.py, gate_unconfined.json, gate_candidate.py,
      scripts/suites/shared.py and scripts/suites/manifest.json, each with its engine copy where one
      exists. It also runs the full sweep when the toolchain digests recorded in
      mutation_case_inputs.json differ from those the coverage map was made with, when the coverage map
      is missing or unreadable, or when the last green or explained nightly sweep finished more than 36
      hours before the gate started (nightly_stale). The selection line names the trigger. A full-sweep
      gate is today's gate, unchanged.
    falsified_by: >
      The suite changes, in a fixture copy, one path from each group of the trigger list and requires mode
      full with that path named; it removes the coverage map, ages it past 36 hours, and alters one
      toolchain digest, and requires mode full with each reason. Registered mutations: (1) the trigger
      list drops mutation_selection.py: the self-change row goes red; (2) the age bound is skipped: the
      stale row goes red.
  - id: AC4
    text: >
      The full sweep runs every night on the trunk. scripts/mutation_nightly.py, started by the host's
      scheduler (a crontab line documented in the script's header, installed by the owner), takes a
      clean checkout of the trunk tip into its own directory, takes the same host lock the gate takes
      (VELDO-0220) and its own scope, waiting for a running gate rather than overlapping it, runs every
      registered case fresh with the tracer on, and records veldo.mutation-sweep/v1 in the authority's
      state directory, outside every candidate tree: run id, trunk commit, start, end, verdict, every
      surviving mutant and driver error, the CPU and memory line, and the coverage map it produced with
      its digest. Only a green sweep publishes a new coverage map. A red sweep, or a sweep that did not
      finish by 07:00 local time, sends the owner one Telegram message through the notifier command named
      in the runner's configuration, naming the commit and each failing case. While the latest finished
      sweep is red, the landing check (policy_check on a protected ref, and the lander's installed
      policy run) refuses as nightly_red, until a later sweep is green or the owner's approval
      (veldo.approval/v1, which no agent can produce) names that sweep's run id and each failing case
      with a reason. A candidate's own gate is not made red by a red nightly sweep; only landing is
      blocked. Nothing loses coverage for more than a day: every case runs at least once per night on
      the trunk, and AC3's 36 hour bound forces the full sweep into the gate when a night is missed.
    falsified_by: >
      The suite runs the nightly runner over a fixture trunk with a fake lock holder: it waits for the
      lock and then sweeps; a fixture case whose mutant survives yields a red record, one notifier call
      naming the case, and a landing check that refuses nightly_red; an approval naming that run id and
      case clears the refusal; an approval naming another run id does not; a later green sweep clears it
      without approval. Registered mutations: (1) the runner skips the lock: the lock row goes red; (2)
      the landing check reads only green records: the red-blocks row goes red; (3) a red sweep publishes
      its coverage map: the publish row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The mutation stage runs every registered case at every gate again, as today, and
  the nightly runner and its crontab line are removed (the line is the owner's host configuration; the
  runner refuses to start once its script is gone). The sweep records and coverage maps sit in the state
  directory and are read by nothing after the revert; no tracked record carries them, so nothing needs
  migrating.
---

## Intent

The mutation stage is most of every Veldo gate and holds the host lock that core's gates share, so one
Veldo gate stops four or five core gates. The owner agreed (Telegram 39676, 39683, 39684) that a gate
should test the code its candidate changed and the trunk should be swept in full once a night. The
point of mutation testing does not change: a check whose teeth were pulled is still found, at the gate
when the change touched its code and by the next morning otherwise.

## Context

Measured from the gate logs in ~/projects/myday/research/gate-stamps/:

- veldo-landing-0261 at 94b85812 (green, 2026-11-06): the mutation stage ran from 0 s to 13,114 s
  (3 h 39 min). Every other stage was finished by 5,080 s (integration.confined end; lint to security
  by 73 s, unit legs at 1,440 s and 2,398 s, integration legs at 2,819 s and 5,080 s). The verdict line:
  registered=2815 executed=2815 reused=0 workers=3711 elapsed=13112.507s, over 1,032 teeth cases. The
  host line records the stage at 56,170 CPU seconds, 10.8 of 20 cores and 8.25 GiB peak memory. So
  mutation alone kept the gate open 8,034 s past everything else.
- veldo-landing-b at 00a66936 (red, 2026-11-07): the stage ended at 4,875 s with a driver_error on a
  baseline (86_veldo_0148_re_land.py), after docs had already failed at 4 s.
- Reuse (VELDO-0205, 0207, 0208, 0218) reused 0 results in both gates.

Expected gate time after this change: the selected cases run concurrently with the unit and integration
legs on the declared graph (VELDO-0216), so an ordinary candidate's gate should end when the
integration legs end, about 5,100 s (85 minutes) on the host as measured, against 13,114 s today, and
the host lock is released about 2 h 15 min sooner. The selection must stay well under 5,080 s of stage
wall time for that to hold; at today's measured average of 3.5 s of stage wall per worker, that is room
for roughly 1,400 workers, about a third of the full sweep. A candidate that hits AC3's trigger list
pays today's 13,114 s. These are estimates from one green run and are re-measured on the first gates
after landing; the proof records them.

The audit (~/projects/myday/research/veldo-core-weight-audit-2026-11-07.md, item 1) names the risk: a
surviving mutant in code the change did not touch is found the next morning instead of at landing. The
covered-set rule (AC1 c) narrows that to code no suite trace connects to the change, and AC4 bounds it
to one night. The selection uses the traced inputs the reuse work already records rather than a static
import scan, because many suites start the code they test in child processes that no import graph
shows.

This spec and VELDO-0268 both touch .veldo/policy_check.py; whichever lands second rebases onto the
first. Retiring the resource ledger (gate_schedule.py, most of gate_host.py) once the stage is small is
a separate spec, as the audit recommends.

## Out of scope

Retiring or changing the reuse machinery, the resource ledger, the worker admission or the host lock;
adding, removing or editing any mutation case; core's gate; how the owner's host schedules other
nightly jobs.

## What the reviewer judges

- The selection can only miss a case through a changed path that neither the case's module, its suite,
  nor its traced or declared inputs contain, and the record shows every reason.
- No path through the stage runs fewer cases than the rule selects plus the canaries; every failure to
  compute the selection runs the full sweep.
- A red nightly sweep cannot be cleared by anything an agent can write.
- The trigger list covers every file that decides which cases run or how they run.

## History

2026-11-07: drafted on the owner's agreement, Telegram 39676, 39683 and 39684, to the audit's item 1
recommendation (veldo-core-weight-audit-2026-11-07.md). Mutation time measured from the 0261 landing
gate log. A draft: only the owner marks it ready.

2026-11-07: ready on the owner's approval, Telegram 39692 ("Ok.") to the summary in 39689 and 39691.

2026-11-07: footprint gains .veldo/lander.py and .veldo/control_verification.py with their engine copies, .gitignore, scripts/suites/requires.json and scripts/check_teeth_mutations.py; protected_paths names the five files policy.yaml newly protects and control_verification.py with its engine copy. By the lead under Telegram 39708, ACs unchanged: AC1 says a landing compares against the trunk commit the lander synced, and the lander and the gate environment are where that base is handed to verify.sh (check of 2026-11-07, research/claude-runs/veldo-0267-check-2026-11-07.md F1).
