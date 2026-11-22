---
schema: veldo.spec/v1
id: VELDO-0221
title: A gate leg runs its suites as isolated parallel closure shards, with an isolation check in every gate
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0214, VELDO-0216]
placement: [enforcement]
protected_paths: ["scripts/selftest.py", "scripts/run_scope.py", "scripts/suites/shared.py", "scripts/check_first_use.py", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.py", "scripts/gate_schedule.py", "engine/scripts/gate_schedule.py"]
footprint:
  - scripts/selftest.py
  - scripts/run_scope.py
  - scripts/suites/shared.py
  - scripts/check_first_use.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/agent_sandbox.py
  - engine/scripts/agent_sandbox.py
  - .veldo/control_client.py
  - engine/.veldo/control_client.py
  - .veldo/control_service.py
  - engine/.veldo/control_service.py
  - .veldo/control_factory_setup.py
  - engine/.veldo/control_factory_setup.py
  - .veldo/control_factory_setup_api.py
  - engine/.veldo/control_factory_setup_api.py
  - .veldo/control_containment.py
  - engine/.veldo/control_containment.py
  - .veldo/services/*
  - engine/.veldo/services/*
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0221_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0221-a-gate-leg-runs-its-suites-as-parallel-closure-shards.md
  - specs/index.md
  - proof/VELDO-0221/*
  - scripts/check_space_boundary.py
  - proof/WARP-0716/crossing-state.md
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/suites/15_warp_1404_historical_analogy*.py
behavior_bearing: true
observability:
  logs: Each shard prints its target suite, its closure, its private roots, its pass and fail counts and its wall time; each leg prints its shard count, its parallelism and its isolation check result with every leaked or foreign item named.
  metrics: Per suite shard seconds, CPU seconds and peak anonymous memory (the claims VELDO-0216's ledger reads); leg wall time, which VELDO-0214 records as before.
  traces: Each shard's result names the suite, the closure from scripts/suites/requires.json and the leg; the aggregate line is composed from target-suite counts only.
  error_taxonomy: A shard that exits without a verdict, asserts nothing for its target or exceeds its deadline is a failure of its suite; a closure that leaves a name undefined fails its shard (never a skip); a write outside a shard's roots, a leaked item or a unit without its shard's name is isolation_breach, RED, naming the suite.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: in a gate leg, selftest.py runs every suite of the leg as one shard, a fresh
      interpreter that executes the suite's prerequisite closure from scripts/suites/requires.json
      in manifest order in one namespace and then the suite, with the leg's row ownership applied
      exactly as today, in parallel as VELDO-0216's ledger grants each shard's claim. Set: the full
      manifest in both legs, a leg with one failing suite, a shard that dies without a verdict, a
      shard whose target asserts nothing, and a fixture suite whose undeclared prerequisite is
      missing from requires.json. Completeness: every suite of the leg is a target exactly once, by
      construction from the manifest; row suite-shards/coverage requires the target set equal to
      the leg's suite set, each failure to fail the leg, and the missing prerequisite to fail its
      shard rather than pass.
    falsified_by: >
      Skip a shard whose process exits without a verdict. Registered mutant shards221-lost-shard
      must fail suite-shards/coverage.
  - id: AC2
    text: >
      Claim: shards are isolated by construction. Each shard has its own HOME, TMPDIR, XDG config,
      data, cache and state directories and result channel; it reports to the dispatcher over a pipe
      it inherits, never through a shared file; in a confined leg each shard adds its own Landlock
      layer (stacked on the leg's domain) that grants writes only beneath its own roots; each shard
      has a private runtime directory in place of /run/user/<uid>, holding only links to the user
      manager's own sockets (its bus and systemd/private) so units still reach the one manager; and
      the engine names every unit, slice, service and runtime directory it creates with a
      per-instance prefix read from the installation's configuration, which each shard's fixtures
      set to the shard's name. Today those names are fixed (veldo-workers.slice in
      control_containment.py:76, the veldo-authority- prefix in control_client.py:90 that
      control_service.py and control_factory_setup_api.py build the authority and veldo-api- units
      from, and the two templates in .veldo/services/), and suites 66, 71, 73, 74, 85 and 86 install
      them, so parallel shards would collide. With no prefix configured, which is every production
      installation, every name is exactly today's. Set: two fixture shards that each write the same
      relative path under their home, temporary and runtime directories, one that tries to write
      another shard's root, and two unconfined fixture shards that each install the authority
      service, its API unit and the workers slice at once. Completeness: row
      suite-shards/isolated-by-construction requires distinct roots and results, the cross-shard
      write refused, every unit, slice and runtime directory name carrying its shard's prefix, and
      row suite-shards/production-names requires an unprefixed installation to produce today's names
      byte for byte.
    falsified_by: >
      Give every shard the leg's TMPDIR. Registered mutant shards221-shared-tmpdir must fail
      suite-shards/isolated-by-construction.
  - id: AC3
    text: >
      Claim: every gate, not only force-fresh gates, checks that isolation held (the owner's decision
      D1). In a confined leg the dispatcher verifies that each shard's Landlock layer was in force
      before its suite ran (the restriction's success is reported over the shard's pipe) and that
      nothing exists after the shard outside its roots that it created. In an unconfined leg the
      dispatcher records the shared locations before the leg and after it (the user manager's units
      and slices, the user's systemd configuration directory, the real runtime directory
      /run/user/<uid>, /dev/shm, the top of the system temporary directory, and the owner's
      ~/.cache/veldo and ~/.local/state/veldo), and requires
      every unit started during the leg to carry some shard's prefix and nothing to be left behind.
      Any breach is isolation_breach, RED, naming the suite. At the top of the system temporary
      directory alone (lead decision 2026-11-21, see History), a new entry fails a shard only when
      it is attributable to that shard, by its instance name, its private roots or its process
      tree; an entry that is attributable to none is recorded in the leg's result and shown on its
      output, and does not fail the leg. Set: a confined shard whose Landlock
      layer is skipped, an unconfined shard that leaves a file in /dev/shm, one that starts a unit
      without its prefix, three that each leave an entry at the top of the temporary directory
      (one by each tie), and an entry there that nothing ties to a shard. Completeness: row
      suite-shards/isolation-checked drives the first three in an ordinary landing gate, not a
      force-fresh one; rows suite-shards/own-temporary-entry-fails-its-shard and
      suite-shards/unattributed-temporary-entry-is-recorded-not-charged drive the rest.
    falsified_by: >
      Run the unconfined after-check only in force-fresh gates. Registered mutant
      shards221-check-force-fresh-only must fail suite-shards/isolation-checked. Only record a
      shard's own entry at the top of the temporary directory: registered mutant
      shards221-own-temporary-entry-allowed must fail
      suite-shards/own-temporary-entry-fails-its-shard.
  - id: AC4
    text: >
      Claim: shards claim their measured CPU and anonymous memory from the gate-wide ledger; a leg's
      node holds only its dispatcher's claim once its shards claim for themselves, so a leg's shards
      run in parallel beneath the mutation stage's reserved cores; and a suite that declares the
      systemd user manager exclusive (63_veldo_0040_containment, 66_veldo_0047_authority) holds an
      exclusive manager claim while it runs. The time claim is a PAIRED measurement (lead decision
      2026-11-21 under the owner's rule that no verdict may depend on machine speed, Telegram 42829;
      see History): each leg is run as shards and then as the ordered single-namespace run, back to
      back in one job on one host at one commit, and is judged on the ratio of the two wall times,
      sharded over ordered, never on either time alone. The ratio is at most one third for a confined
      leg and at most one half for an unconfined leg (the lead's thresholds, decided 2026-11-21
      under Telegram 42829), which are the bounds this criterion first
      stated in seconds (600 against 1,913 and 420 against 892) as ratios. Set: a fixture leg with
      two exclusive and three shared manager suites; a fixture gate of the real scheduler with a
      mutation floor of 11 of 20 cores and a leg node whose earlier claim was its whole cgroup's;
      and one paired run of each leg at the fix-round candidate. Completeness: row
      suite-shards/manager-exclusive requires no overlap of an exclusive shard with any manager
      user; row suite-shards/leg-node-claims-only-its-dispatcher requires three shards held at once
      while the mutation node holds its floor; the proof records every shard's wall and CPU time,
      each leg's critical shard and both times of each pair.
    falsified_by: >
      Ignore the manifest's manager declarations in the shard dispatcher. Registered mutant
      shards221-resources-ignored must fail suite-shards/manager-exclusive. Keep a leg node's
      whole-cgroup claim while its shards claim: registered mutant shards221-leg-claim-counts-shards
      must fail suite-shards/leg-node-claims-only-its-dispatcher.
required_evidence: [unit, integration]
rollback: Revert the shard mode; every leg runs the ordered single namespace run, as before.
---

## Intent

The unit and integration stages are the largest cost before mutation: their four legs took 5,434 of
the 5,502 pre-mutation seconds on 2026-10-25, each on about one core (0.75 to 1.00), because
selftest.py executes every suite in one interpreter, one after another. Running the legs beside each
other (VELDO-0216) still leaves the confined unit leg at 1,913 seconds, more than the 30 minutes the
owner wants for a typical landing. The suites are mostly independent: of the 167 suites in the
pending stack's scripts/suites/requires.json, 156 need no other suite, and the other 11 (fragments 01
to 13 of the original monolith) need between 2 and 12 earlier fragments. The mutation stage already
runs each suite on its own in a fresh worker; the isolated baseline times there are at most about
100 seconds per suite.

## Design

selftest.py keeps its ordered mode for a bare run and a selector. In a gate leg it runs the shard
mode: one job per suite of the leg from the manifest and requires.json, each started as a child
interpreter of the same dispatcher with the suite selector (which already runs exactly the closure
in manifest order and refuses to print an aggregate line), each reporting its per-suite counts and
row labels over its inherited pipe. The parent composes the leg's aggregate line from target-suite
counts. Green for a leg now means every shard passed and the isolation check held.

Isolation, under the owner's decision D1, is built in rather than inferred: separate interpreters
share no Python state; separate roots share no files; the stacked Landlock layer (the same unprivileged
mechanism agent_sandbox.py uses for the leg) makes a write to another shard's roots impossible in a
confined leg; prefixed instance names keep two shards' units, slices and runtime directories apart
on the one user manager (scripts/mutation_ownership.py's patterns accept the prefixed names, so
mutation workers clean them up as today); and the unconfined leg, which cannot be confined, is checked before and after against
the shared places a suite can reach. The cross-suite pollution the ordered run used to reveal can
then arise only through those shared places, and they are checked in every gate. A suite that
silently depended on an undeclared earlier suite now fails its shard, where the ordered run hid it.

Expected time. CPU per confined leg rises by the replayed closures (61 extra suite executions, all
among fragments 01 to 13) and one interpreter start per suite, from about 1,900 to about 2,500 CPU
seconds; at 8 to 12 granted cores that is about 210 to 320 seconds, with the longest shard (about
100 seconds confined, about 240 seconds for suite 101's traced rows in the unconfined leg) as the
floor. The isolation checks add seconds per leg. Saving on every gate's critical path: from 1,913
seconds to about 300 to 600.

## Out of scope

Suite result reuse (VELDO-0206), which isolated shards make possible; the suites and their
assertions; the unconfined list; the mutation stage.

## What the reviewer judges

Normal use: the canonical and landing gates. Threat model: as in VELDO-0208; the dispatcher,
run_scope.py, shared.py and agent_sandbox.py stay protected, so a candidate cannot change how shards
are rooted, counted or checked. Out of review scope: deliberate escapes by unconfined suite code
running with the owner's authority, beyond the shared locations AC3 names.

## Notes

The integration stage's nested run uses the same dispatcher, so its legs shard the same way; its
budget input from VELDO-0214 becomes the 1800-second floor because the measured unit leg time falls
far below 900 seconds.

## Build notes (2026-11-21, as of fix round 1)

Recorded by the build, for the owner and the reviewer. The evidence and the reasons are in
proof/VELDO-0221/README.md and proof/VELDO-0221/open.md.

- The instance name extends the engine's fixed unit prefix instead of preceding it. It is read from
  the shard's runtime directory, and by an installed service from its own unit's name, not from the
  installation's configuration as AC2's text says (lead decision 9 below).
- Six unconfined suites are given no instance name (run_scope.UNNAMED: 85_veldo_0171_setup_api,
  86_veldo_0189_engine_upgrade, 91_veldo_0167_setup_records, 106_veldo_0185_dispatch_setup,
  117_veldo_0227_ui_location, 127_veldo_0234_https_port): each lays a host down with an older
  engine from this repository's history, which cannot carry a name. This needs the owner's decision.
- In an unconfined leg a shard's private runtime directory stands inside the real runtime
  directory, in a directory of the leg's own, because the engine refuses a protected target beneath
  a temporary directory and nineteen suites stand their fixtures in XDG_RUNTIME_DIR.
- A shard names an XDG base directory in its environment only when the leg's environment names it;
  one the leg leaves unset has its default beneath the shard's private HOME, as in the ordered run.
- Suite 151_veldo_0313_space_run runs without a Landlock layer of its own (run_scope.UNLAYERED), and
  alone: no other shard runs beside it.
- AC3's unit check judges only this instance's units, by the leg's prefix or by reference to a
  shard's roots; a file nothing can be tied to fails the leg's isolation check by name, except at
  the top of the system temporary directory, where it is recorded and shown (History, fix round 2).
- The build added five paths to this footprint, its last five entries. Two because a gate check
  requires each edit: scripts/check_space_boundary.py (two table entries for the dispatcher's
  temporary directory) and proof/WARP-0716/crossing-state.md (regenerated for the dispatcher's
  digest). Three by the lead's decisions of 2026-11-21: scripts/gate_schedule.py and its engine
  copy (the leg node's claim) and scripts/suites/15_warp_1404_historical_analogy*.py (the split).

## History

2026-11-21, fix round 1, lead decisions after the independent review (verdict FIX):

- AC4 restated. Its first text bound each confined leg to 600 seconds and each unconfined leg to
  420 on the qualification host. A whole-leg wall-time bound depends on machine speed and on what
  else the host runs, which the owner's rule forbids (Telegram 42829). AC4 is now a paired
  measurement: sharded against ordered, same job, same host, same commit, judged on the ratio. The
  lead named no number; the build wrote the first text's own bounds as ratios (one third, one
  half), and the lead confirms or changes them at landing. The criterion also gained the leg
  node's claim (review finding F1) with its row and falsifier.
- Builder decisions 2 to 8, 10 and 12 and the two footprint additions are kept.
- Decision 9: the instance name is carried in the shard's runtime directory, in both legs.
- Suite 151's Landlock exception is narrowed to running it alone. It stays the one entry of the
  protected table, and the owner approves it at landing.
- The rule for the top of the system temporary directory: a new entry made during a leg is charged
  to its shard when it can be attributed; one that cannot fails the leg's isolation check with its
  name recorded. It is never silently allowed.
- Suite 15_warp_1404_historical_analogy is split so no one shard dominates a leg, its rows unchanged.
- The footprint gains scripts/gate_schedule.py, its engine copy and the split suite's files.

2026-11-21, fix round 2, lead decisions after fix round 1's evidence:

- The rule for the top of the system temporary directory, revised on a new fact. On a shared host
  other sessions leave files in /tmp: in three whole unconfined legs every shard was green and the
  leg was red each time for another session's file. A new top-level /tmp entry now fails a shard
  only when it is attributable to that shard, by its instance prefix, its private roots or its
  process tree. An entry that is attributable to none is recorded in the leg's evidence and shown
  in its output, and does not fail the leg. Shards keep temporary directories of their own, so a
  leak by a shard stays attributable. This replaces the fix round 1 rule above ("one that cannot
  fails the leg's isolation check"). Every other shared place keeps that rule.
- AC4's thresholds are the lead's decision under the owner's rule that no verdict may depend on
  machine speed (Telegram 42829): the ratio of the sharded wall time to the ordered wall time, same
  run, same host, is at most 1/3 for the confined leg and at most 1/2 for the unconfined leg. The
  paired run of fix round 1 measured 0.15 and 0.45, which meet them.
- The 7 rows of suite 102_veldo_0210_agent_profile_runtime that fail only in the ordered confined
  leg are inherited: an order dependence that is also seen at the base commit and is recorded in
  VELDO-0358's notes. They are recorded in the proof and do not block this specification.
- For the owner at landing: the six suites of run_scope.UNNAMED, suite 151 running alone without a
  Landlock layer of its own, and the two further space-boundary entries. They are listed in
  proof/VELDO-0221/README.md under "For the owner at landing".

2026-11-22, landing candidate cand-1122, lead decision with VELDO-0206: suite result reuse operates
per shard. A shard's verdict also carries the counts of every suite of its closure, and the leg's
result carries each shard's charged failures, so the dispatcher can settle a qualified suite's shard
as VELDO-0206's isolated run. A suite the reuse plan leaves out is not started as a shard; every
other suite of the leg is a target exactly once, as before. AC1 to AC4, the isolation check and the
paired ratios of AC4 are unchanged. The rows and falsifiers are VELDO-0206's (its spec, same date).
