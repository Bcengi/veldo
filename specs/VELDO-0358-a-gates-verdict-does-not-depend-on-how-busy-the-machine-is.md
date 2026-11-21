---
schema: veldo.spec/v1
id: VELDO-0358
title: A gate's verdict does not depend on how busy the machine is
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0215, VELDO-0220]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/mutation_observer.py", "engine/scripts/mutation_observer.py", "scripts/gate_host.py", "engine/scripts/gate_host.py", "scripts/check_wallclock.py", "engine/scripts/check_wallclock.py", "scripts/gate_load.py", "engine/scripts/gate_load.py", "scripts/suites/wallclock.json", "scripts/suites/wallclock_baseline.json", ".veldo/policy.yaml", "scripts/gate_graph.json", "scripts/gate_schedule.py", "engine/scripts/gate_schedule.py"]
footprint:
  - scripts/suites/support/waits.py
  - scripts/suites/support/holders.py
  - scripts/suites/support/ports.py
  - scripts/suites/support/v171_tailscale.py
  - scripts/suites/shared.py
  - scripts/selftest.py
  - scripts/suite_labels.py
  - scripts/check_wallclock.py
  - engine/scripts/check_wallclock.py
  - scripts/gate_load.py
  - engine/scripts/gate_load.py
  - scripts/suites/wallclock.json
  - scripts/suites/wallclock_baseline.json
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/gate_graph.json
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_observer.py
  - engine/scripts/mutation_observer.py
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - scripts/gate_host.py
  - engine/scripts/gate_host.py
  - scripts/check_first_use.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/62_veldo_0039_dispatch.py
  - scripts/suites/63_veldo_0040_containment.py
  - scripts/suites/66_veldo_0042_clones.py
  - scripts/suites/66_veldo_0047_authority.py
  - scripts/suites/71_veldo_0138_channel_service.py
  - scripts/suites/78_veldo_0060_claude_adapter.py
  - scripts/suites/83_veldo_0154_factory_loop.py
  - scripts/suites/86_veldo_0189_engine_upgrade.py
  - scripts/suites/106_veldo_0185_dispatch_setup.py
  - scripts/suites/110_veldo_0143_new_project.py
  - scripts/suites/112_veldo_0215_case_deadlines.py
  - scripts/suites/120_veldo_0131_factory_ui.py
  - scripts/suites/121_veldo_0131_factory_screens_narrow.py
  - scripts/suites/124_veldo_0131_factory_reads_commands.py
  - scripts/suites/151_veldo_0313_space_run.py
  - scripts/suites/*_veldo_0358_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - proof/VELDO-0152/fixture.py
  - engine/.veldo/timers.py
  - engine/.veldo/policy_contract.py
  - engine/.veldo/control_launch.py
  - engine/.veldo/control_containment.py
  - engine/.veldo/control_heartbeat.py
  - engine/.veldo/control_service.py
  - engine/.veldo/control_client.py
  - engine/.veldo/control_client_api.py
  - engine/.veldo/control_store.py
  - engine/.veldo/control_engine_claude.py
  - engine/.veldo/control_engine_codex.py
  - engine/.veldo/control_factory_setup_upgrade.py
  - engine/.veldo/control_workflow_cycle_pm.py
  - engine/bin/veldo
  - engine/ui/playwright.config.ts
  - engine/ui/e2e/harness.py
  - engine/ui/e2e/fixtures.ts
  - engine/ui/e2e/factory-fixtures.ts
  - engine/ui/e2e/team-fixtures.ts
  - engine/ui/e2e/factory.spec.ts
  - engine/ui/e2e/layout.spec.ts
  - engine/ui/e2e/screens.spec.ts
  - engine/ui/e2e/run.spec.ts
  - engine/ui/src/*
  - .veldo/policy.yaml
  - specs/VELDO-0358-a-gates-verdict-does-not-depend-on-how-busy-the-machine-is.md
  - specs/VELDO-0223-a-red-under-others-load-is-rerun-quietly-before-it-counts.md
  - specs/VELDO-0215-measured-mutation-case-deadlines.md
  - specs/index.md
  - proof/VELDO-0358/*
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/suites/01_warp_0101_reviewer_notes.py
  - scripts/suites/38_veldo_0025_membership.py
  - scripts/suites/93_veldo_0152_intake_routes.py
  - scripts/suites/113_veldo_0145_ui.py
  - scripts/suites/127_veldo_0254_secret_scan.py
  - scripts/suites/128_veldo_0254_confined_runner.py
  - scripts/suites/141_veldo_0344_process_reader.py
  - scripts/suites/113_veldo_0220_gate_host.py
  - scripts/suites/114_veldo_0220_gate_scope.py
  - engine/ui/docs/patterns/testing.md
  - proof/VELDO-0219/round2/check.py
  - proof/VELDO-0219/round3/check.py
  - proof/VELDO-0358/*/*
behavior_bearing: true
observability:
  logs: >
    A hung row prints the wait's name, its source line, the last reading of its done and terminal
    conditions, and the path of the stack dump. A process ended by its progress watchdog prints the last
    progress event it saw and the stack dump. The census stage prints every site over its allowed count
    and every baseline entry whose count is not the required one. The load-proof leg prints, per suite, its
    result and run count, and at its end each generator's liveness, the spinners' consumed CPU, the writers'
    bytes, the memory.events high count and the probe readings, all as data.
  metrics: >
    Count of baseline entries by rule and by file (it only falls). Per mutation case, kill_by (assertion,
    terminal, unproven). The load record of each gate (generator counters, probe readings, the leg's wall
    time, each suite's loaded time).
  traces: The gate stamp and the gate event carry the census counts, the opened-files record and the load record.
  error_taxonomy: >
    hung (a wait reached the wait hang bound, or a process went the process hang bound with no progress),
    residue (a suite left a thread, a child or a listener), wallclock_site (more sites for a key than the
    authority allows), baseline_stale (a candidate baseline count other than the required one),
    hung_not_killed (a mutation case whose failing target rows are hung or not run), control_failed (the
    unmutated suite failed or hung in the mutation stage), load_not_applied (a generator process was not
    alive for the whole leg), timer_unset (an engine timer on a wave 1 path not at the hang bound under the
    profile). Every one is RED. There is no invalid, voided or not-judged result for a busy machine.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a suite blocks only through the wait primitive (scripts/suites/support/waits.py), which
      replaces wait_for and the pipe barrier of scripts/suites/shared.py and keeps wait_for's report shape
      (what was waited for, the bound, the last observation) with the terminal condition added. A wait has
      exactly three outcomes: done, impossible (its terminal condition became true) and hung (the wait hang
      bound of 600 seconds passed since the wait began). An expired wait is never read as false. A hung wait
      makes its row hung, ends the suite's process, and every row not reached prints as not run; hung and
      not run are red. Set: a fixture suite with a wait that completes, one whose terminal condition
      becomes true, and one that never completes, the last run with the bound supplied as two seconds
      through the primitive's own parameter for its test; and scripts/suites/shared.py, which keeps no wait
      of its own. Completeness: row waits/three-outcomes requires the three results, the hung row's name and
      source line in the output, the later rows printed as not run, exit status red, and no clock-bounded
      loop left in shared.py.
    falsified_by: >
      Return false from a wait that reached its bound. Registered mutant wait358-expiry-reads-false must
      fail waits/three-outcomes.
  - id: AC2
    text: >
      Claim: a wait wakes on the kernel's notification of its event and on nothing else: a process exit
      (pidfd), a readable descriptor, a path appearing or being replaced (inotify on its directory, or on
      the nearest existing ancestor and moved down on each creation while the directory does not exist yet),
      a change of the store (inotify on its write-ahead file, then the condition re-read), a cgroup becoming
      empty (cgroup.events). While none of them happens the waiting thread makes no system call. Set: one
      wait per source, each held across two events the test causes itself, and a path wait whose directory
      is created two levels deep after the wait began. Completeness: row waits/no-idle-wake reads the waiting
      thread's voluntary context switches before the first event and after the second and requires the
      difference to be at most the events caused, for every source, and the deep path wait done.
    falsified_by: >
      Replace the path source with a 20 millisecond poll. Registered mutant wait358-path-polled must fail
      waits/no-idle-wake.
  - id: AC3
    text: >
      Claim: a fixture process that must stay alive is a latch holder (scripts/suites/support/holders.py):
      it blocks on a pipe whose other end the test holds, ends when the test releases it, and ends when
      the test's process dies for any reason. Set: a holder released by the test, and a holder whose
      test process is killed. Completeness: row holders/ends-with-its-test waits on each holder's pidfd
      and requires both exits; no row of the suite sleeps.
    falsified_by: >
      Make the holder ignore the closed pipe. Registered mutant wait358-holder-outlives-test must fail
      holders/ends-with-its-test.
  - id: AC4
    text: >
      Claim: a suite that ends with a thread still alive, a child process not reaped, or a listening
      socket still open has a failed row of its own named residue, listing each one. Set: three fixture
      suites, each leaving one of the three, and one leaving none; and the two suites seen leaving
      threads (66_veldo_0042_clones, 86_veldo_0189_engine_upgrade), which must now leave none.
      Completeness: row residue/named requires the three reds with the leftover named and the clean
      fixture green; the two real suites pass their own residue row in the unit stage.
    falsified_by: >
      Skip threads in the residue reading. Registered mutant wait358-threads-not-counted must fail
      residue/named.
  - id: AC5
    text: >
      Claim: a process is ended for hanging only when the process hang bound of 3600 seconds has passed with
      no progress evidence: in a suite process a row starting or ending re-arms the bound, whether the
      process runs one suite or a whole leg; around a heavy child (a suite or selftest run, a gate stage, a
      browser run, a package install, qualify) a line on its output re-arms it. Before a process is ended,
      every thread's stack is written to the log. Nothing bounds the total time of a gate, a stage, a leg,
      the mutation stage or the nested first-use run; scripts/check_first_use.py keeps no measured budget
      and no ceiling. Set, each with the bound supplied as three seconds and a supplied clock through the
      watchdog's own parameter for its test: a fixture suite that blocks outside the wait primitive (a
      blocking read); a fixture leg of three suites whose rows each take one supplied second and whose total
      is nine; a fixture mutation stage driven past 21,600 supplied seconds with every worker completing
      rows; a heavy child that prints a line each supplied second for ten seconds. Completeness: row
      watchdog/progress-not-total requires the blocking suite ended, the stack dump present and naming the
      blocking read's line, and the suite reported hung; and the leg, the stage and the child each finished
      and green, with nothing ended.
    falsified_by: >
      End the process without writing the stacks: registered mutant wait358-watchdog-silent must fail
      watchdog/progress-not-total. Arm the watchdog once per process instead of per row: registered mutant
      wait358-watchdog-total-time must fail the same row on the three-suite leg.
  - id: AC6
    text: >
      Claim: the gate has a census stage (scripts/check_wallclock.py) that finds, with calls resolved
      through each file's imports and names resolved to module constants: R1, a call resolving to
      time.sleep or asyncio.sleep, a sleep command, a sleep with a number in a string run as source, and
      waitForTimeout; R2, a read resolving to a wall or monotonic clock outside the support module; R3, a
      timeout other than zero, None or a named hang constant, given as the keyword timeout or at a position
      of the closed table (Thread.join 0, Event.wait 0, Condition.wait 0 and wait_for 1, Queue.get 1 after a
      literal block flag and put 2, Popen.wait 0 and communicate 1, socket settimeout 0,
      create_connection 1, select.select 3, a selector's select 0, poll 0, signal.alarm 0, setitimer 1,
      threading.Timer 0, asyncio.wait_for 1, a Barrier's timeout, the Playwright timeout options), with the
      process constant accepted only on a heavy child; R4, an upper bound against a number on a value named
      or derived as a duration. Scope: every file under scripts/ and proof/ in the authority's last
      opened-files record, every file the candidate changed under scripts/, proof/ and engine/ui/e2e,
      engine/ui/e2e and engine/ui/playwright.config.ts, the gate tooling, and for R3 the engine files of the
      design's section 4.8. The opened-files record is written by an audit hook on open and import in every
      suite process. Set: one fixture file per rule holding one site; one fixture per positional form
      (select with 0.2, Queue.get with True and 5, Condition.wait_for with 3, Timer with 2, the list command
      sleep 2, a thread join of 5); a fixture of allowed forms (a zero timeout, None, a named constant, a
      lower bound, ", ".join(parts), os.path.join(a, b), d.get(k), d.get(k, 5)); a fixture suite that loads
      a fixture by a computed path, the fixture holding a sleep; and the repository itself. Completeness: row
      census/each-rule requires red for each site fixture with the rule, the form and the site named, green
      for the allowed forms, red for the computed-path fixture's sleep, and green for the repository
      against its baseline.
    falsified_by: >
      Registered mutants, each of which must fail census/each-rule: wall358-sleep-admitted,
      wall358-clock-admitted, wall358-timeout-admitted, wall358-duration-bound-admitted (each stops
      reporting its rule), wall358-positional-ignored (only the keyword timeout is read), and
      wall358-scope-inferred (the scope taken from import statements instead of the record).
  - id: AC7
    text: >
      Claim: the baseline and the exceptions are multisets keyed by file, rule, normalized source text and
      enclosing qualified function name, with a count per key. Exceptions are read only from the authority
      checkout; the baseline is read from both. For each key the stage is red (wallclock_site) when the
      candidate has more sites than the authority's baseline count plus its exceptions count, and red
      (baseline_stale) when the candidate's baseline count is not the smaller of the authority's baseline
      count and the candidate's sites less the authority's exceptions. So a conversion lowers its entry in
      the same change, with no approval, and the baseline cannot grow except by an owner-approved change to
      the protected file. An exception entry has one of the kinds lower_bound, timer_fires, subject and
      supplied_clock, a reason and a specification; any other shape is refused. While the authority has no
      baseline file the stage reports and judges nothing. Set: a candidate that removes a site and lowers
      its entry; a candidate that adds a site and adds its own baseline entry; a candidate that removes a
      site and leaves its entry; a candidate that duplicates a baselined line in the same function; a
      candidate that copies an excepted line; an exception entry with an unknown kind. Completeness: row
      census/lists-from-authority requires green, red, red, red, red and red.
    falsified_by: >
      Registered mutants, each of which must fail census/lists-from-authority: wall358-baseline-from-candidate
      (the candidate's baseline is trusted), wall358-stale-entry-tolerated (a count above the sites is
      accepted), wall358-count-ignored (a key matches whatever its count).
  - id: AC8
    text: >
      Claim: a mutation case is rejected only when its controls passed every row with none hung, its
      mutant's process ended by itself without its watchdog firing, and at least one declared target row
      failed on evidence (an assertion, or a wait ended by its terminal condition), with no target row hung
      or not run. A case whose failing target rows are hung, or whose target row was not run because an
      earlier row hung, is hung_not_killed and the stage is red. A control that fails or hangs is
      control_failed for its suite. The receipt records for every rejected case the row and kill_by:
      assertion, terminal, or unproven when the suite or a file it opens has a baseline entry. Set: six
      fixture cases over fixture suites: target row fails by assertion; target row fails by terminal
      condition; target row hangs; target row not run because an earlier non-target row hung; control hangs;
      target row fails by assertion in a suite with a baseline entry. Completeness: row
      verdict/kill-by-evidence requires rejected (assertion), rejected (terminal), hung_not_killed,
      hung_not_killed, control_failed and rejected (unproven), with the receipt fields present.
    falsified_by: >
      Count a hung target row as a failed one: registered mutant verdict358-hang-counts-as-kill must fail
      verdict/kill-by-evidence. Treat a not-run target row as passed: registered mutant
      verdict358-not-run-passes must fail the same row.
  - id: AC9
    text: >
      Claim: no mutation worker is ended because it was slow. Every worker runs under its progress
      watchdog; the times VELDO-0215 measures are used to order admission and are no longer a deadline; the
      stage has no combined deadline of its own. Set: a fixture case whose recorded time is two seconds
      and whose worker is made to take thirty, with a supplied clock. Completeness: row
      verdict/slow-is-not-red requires the worker to finish and be judged by its rows, and
      mutation_budget_exceeded to appear nowhere; suite 112_veldo_0215_case_deadlines is restated to the
      same effect.
    falsified_by: >
      End a worker at three times its measured time. Registered mutant verdict358-measured-time-kills must
      fail verdict/slow-is-not-red.
  - id: AC10
    text: >
      Claim: the sites behind the reds of gates 7 to 12 are converted and these files and every file they
      open have no baseline entry: suites 62_veldo_0039_dispatch (including the row of the late-deadline
      mutant), 63_veldo_0040_containment (including the 1.2 second runtime cap row and the real-clock 0.75
      second assertion, which becomes "recorded from the pidfd wake, one wake, zero poll intervals, after the
      exit", with the latency written as data), 66_veldo_0042_clones, 66_veldo_0047_authority,
      71_veldo_0138_channel_service, 78_veldo_0060_claude_adapter, 83_veldo_0154_factory_loop,
      86_veldo_0189_engine_upgrade, 106_veldo_0185_dispatch_setup, 110_veldo_0143_new_project, 120, 121 and
      124 of VELDO-0131, 151_veldo_0313_space_run (including the 1.5 second window after SIGTERM and
      SIGHUP), the browser fixtures, specifications and configuration under engine/ui,
      scripts/suites/support/v171_tailscale.py, scripts/check_first_use.py and the mutation driver. No row of
      these suites is removed and no row's condition is weakened: an upper bound on a real duration is
      replaced by the cause and order the product recorded, and a lower bound stays. Set: those files.
      Completeness: row wave1/no-sites runs the census over them and requires zero sites outside declared
      exceptions; row wave1/rows-kept compares each suite's row labels with the base and requires the same
      set or a superset; every registered case of these suites is rejected under AC8 with kill_by assertion
      or terminal; each suite runs fifty times under the generator of AC12 with no failed and no hung row.
    falsified_by: >
      Restore the ten second bound of marker_for in suite 62: registered mutant wave358-bound-restored must
      fail wave1/no-sites. Restore the 0.75 second real-clock assertion in suite 63: registered mutant
      wave358-latency-asserted must fail the same row.
  - id: AC11
    text: >
      Claim: the gate reads who holds its lock from the holder's descriptor record (fdinfo) and not from
      /proc/locks, so a table that is torn while other processes take and drop locks cannot show a held
      lock as unheld or as held twice. Set: a supplied process root in which the lock table lists the
      holder twice, and one in which it lists nobody, while the holder's descriptor record names the
      lock. Completeness: row host/holders-from-descriptor requires exactly one holder in both.
    falsified_by: >
      Read the holders from the lock table. Registered mutant host358-holders-from-table must fail
      host/holders-from-descriptor.
  - id: AC12
    text: >
      Claim: the load generator (scripts/gate_load.py) builds the load by construction inside the gate's
      own scope: the leg's suites and three spinners per CPU are bound by CPU affinity to the same set of K
      CPUs (K equal to the leg's slots); the leg's cgroup gets a memory.high of 60 percent of the peak the
      previous load-proof leg recorded for the same set at the same concurrency, and none on the first leg;
      one writer per four CPUs of the set writes, flushes and removes a 256 MiB file on the file systems of
      the scratch root and the checkout. It proves the load by liveness: every generator process alive from
      the leg's start to its end, each spinner's consumed CPU and each writer's bytes above zero. The
      slowdown probe and the memory.events high count are recorded as data and judge nothing. A leg in which
      a generator process was not alive for the whole leg is red as load_not_applied. All generator
      processes are gone when the leg ends on any path. Set: the generator run for sixty seconds beside a
      fixture leg; the same with one spinner killed midway; the same ended by a kill of the leg; and the
      canary suite (a child does a tenth of a CPU-second of work and writes a marker, the parent sleeps 0.2
      seconds and reads it), alone and in the fixture leg. Completeness: row load/level-by-construction
      requires the load record with every generator alive, then load_not_applied, then no generator process
      left, and the canary green alone and red in the leg.
    falsified_by: >
      Start the generator with no spinners and report them alive: registered mutant load358-no-spinners
      must fail load/level-by-construction. Leave the leg's suites unbound from the spinners' CPUs:
      registered mutant load358-affinity-dropped must fail the same row through the canary.
  - id: AC13
    text: >
      Claim: the gate has a load-proof leg after the unit and integration stages and before the mutation
      stage. It runs, each in its own process and under the generator of AC12, every suite of the proven set
      once and every changed suite of the proven set repeatedly. The proven set is computed: a suite with no
      baseline entry in itself or in any file of its opened-files record. A suite is changed when its file is
      in the gate's diff or a changed file is in the opened-files record of at most three suites. The
      repetition count is twenty, lowered to fit the leg's repetition allowance of thirty minutes of loaded
      time at the leg's slots (from each suite's loaded time in the previous leg's record), never below five;
      the allowance decides how many runs are made, never a verdict. Any failed or hung row is GATE: RED;
      the mutation stage is not started; no suite is run again because it failed; the stamp carries the load
      record. Set: a fixture repository whose suites are a clean suite, the canary under a baseline entry,
      the canary with its entry removed, a changed clean suite, and a clean suite whose shared support file
      changed. Completeness: row leg/proves-and-blocks drives verify.sh over them and requires: the clean
      suite run once and green; the baselined canary not run; the canary without its entry run and red, with
      the gate red, the mutation stage not started and that suite executed exactly once; the changed suite
      executed twenty times; the suite with the changed shared file executed once.
    falsified_by: >
      Run a suite that failed in the leg a second time and report the second result: registered mutant
      load358-red-is-rerun must fail leg/proves-and-blocks. Let the gate continue to the mutation stage
      after a red leg: registered mutant load358-red-not-blocking must fail the same row.
  - id: AC14
    text: >
      Claim: VELDO-0223 is superseded and cannot be claimed: its status is blocked and its History names
      this specification and the owner's rulings (Telegram 42171 of 2026-11-18 and 42829 of 2026-11-20);
      VELDO-0215's History records that its worker deadline is no longer a verdict (AC9). The gate's result
      words are a closed list: GATE: GREEN, GATE: RED, GATE: NOT JUDGED with its existing reasons, and GATE:
      NOT STARTED (scripts/verify.sh today). Set: the two specification files, specs/index.md,
      scripts/verify.sh and scripts/gate_host.py. Completeness: row supersede/0223-not-claimable reads the
      index and requires VELDO-0223 not ready; row supersede/result-words-closed collects every gate result
      word the two scripts can print and requires exactly the closed list and no NOT JUDGED reason that
      names load, pressure, contention or a quiet window.
    falsified_by: >
      Leave VELDO-0223 at status ready: registered mutant supersede358-0223-ready (applied to the index
      generator's input in the row's fixture) must fail supersede/0223-not-claimable. Add INVALID to
      verify.sh's result words: registered mutant supersede358-invalid-word must fail
      supersede/result-words-closed.
  - id: AC15
    text: >
      Claim: every giving-up deadline and contract timer of the product on the path of a wave 1 suite (the
      design's section 4.8) is either replaced by its event (the receiver's exit awaited on its pidfd; the
      orphaned worker's cgroup becoming empty) or read from the timers table (engine/.veldo/timers.py),
      which reports its effective values: from the table in process, and in the start record of the service
      and of the launch wrapper. Each wave 1 suite's profile sets every table entry to the wait hang bound
      except the one timer its row is testing. Set: the wave 1 suites; and the engine files of section 4.8
      under the census's R3 with the table's names as the allowed forms. Completeness: row
      timers/profile-applied in each wave 1 suite reads the effective values and requires the wait hang
      bound for every entry but the one under test (red timer_unset otherwise); the census finds no numeric
      timeout in those engine files outside the table; the receiver-exit and orphan rows of suite 62 show the
      wait ended by the exit and the empty cgroup events.
    falsified_by: >
      Make the launch read RECEIVER_EXIT_SECONDS as the literal 2 instead of from the table: registered
      mutant timers358-literal-kept must fail timers/profile-applied in suite 62 and the census row. Let the
      profile skip the client's 30 second send timeout: registered mutant timers358-profile-skips-client
      must fail timers/profile-applied in suite 66_veldo_0047_authority.
required_evidence: [unit, integration]
rollback: >
  Remove the census and load-proof stages from scripts/verify.sh and scripts/gate_graph.json and restore
  the previous scripts/check_gate_mutations.py. The wait primitive, the holders, the residue check, the
  progress watchdog, the timers table and the converted suites stay: they are correct without the stages.
  VELDO-0223 stays blocked.
---

## Intent

The owner, Telegram 42829 (2026-11-20): "I want to stop failing veldo gates due to performance that is
caused by machine load - this has wasted a ton of tokens and weeks!"

A gate must give the same verdict on an idle machine and on one that is several times slower. Gates 7 to
12 of space-0329b were each red for a reason that had nothing to do with the change under test: a worker
ended at a 120 second floor with 8.8 seconds of CPU used, a "nothing happens for 1.5 seconds" window that
stretched to 6.9, a lock table read while it changed, a port released and taken, a fixed ten second wait
in a browser test, and two real races in the product that only a busy machine showed. In gates 9, 10 and
11 no mutant survived; an unmutated control failed under the mutation stage's own load and 5, 51 and 45
cases were voided two hours into the gate. Each red cost a gate of 2 h 18 min to 3 h 20 min and a triage.

This specification removes the dependency at its source, in the suites and in the product timers on their
paths, and proves the result in every gate. It does not measure how busy the machine is, wait for it to be
quiet, run anything again, or bound how long a gate may take.

The design, with the inventory of every site and the evidence, is
myday/research/designs/veldo-load-independent-gates-2026-11-20/design.md (revision 2). This specification
is waves 0 and 1 of its section 11.

## Context

- The gate declares no performance threshold (scripts/verify.sh, performance: na). Every timing assertion
  inside a suite is therefore undeclared.
- A syntax-tree reading of the worktree at f5055400 with the census rules of this specification found about
  2,035 sites in 183 of 249 suite files: 231 sleeps (112 of them in fixture source text), 914 clock reads
  (201 bounded polls, 85 deadlines as product input, 628 timestamps as data) and 890 timeouts (design,
  section 4.1 and appendix A).
- The mutation driver already refuses to count a worker that passed its deadline as a kill. It cannot see
  a row that failed because a poll inside the suite ran out; that reads as a failed row. kill_by unproven
  makes that visible until the suite is converted.
- VELDO-0220's lock and scope stay as they are. The load generator runs inside that scope. The user manager
  delegates cpu, memory and pids only, so the CPU level is built with affinity, not a cpuset.
- VELDO-0221 (one process per suite in the functional legs) is not built. The load-proof leg starts each
  suite in its own process through the existing suite selector and does not wait for it. The progress
  watchdog is re-armed per row, so a shared-interpreter leg is never ended for being long.

## Design

Components, each described in the design's section 5:

1. The wait primitive and its event sources (AC1, AC2), the latch holder (AC3) and the port holder, in
   scripts/suites/support; shared.py's wait_for and barrier become calls into it. Two named constants are
   the only durations: the wait hang bound, 600 seconds from the start of a wait, and the process hang
   bound, 3600 seconds from the last progress evidence. Why these values, and the closed list of heavy
   children: design, section 6.
2. Three-valued rows, the progress watchdog, the residue check and the opened-files record in
   scripts/selftest.py (AC1, AC4, AC5, AC6's scope).
3. The census stage, its multiset baseline and its exception list (AC6, AC7). The baseline is generated
   from the stage's first report at the commit this specification is built on and reviewed as data; the
   counts of the design's section 4.1 are the check on it.
4. The verdict rule with kill_by in the mutation driver and observer, the end of the measured worker
   deadline and of the first-use run's measured budget (AC8, AC9).
5. The timers table and its effective-values report (AC15), filled with the entries of the design's
   section 4.8, and the two event replacements in control_launch.
6. The conversion of the suites behind gates 7 to 12 (AC10), site by site as the design's section 4.2
   states, and the gate's lock reading (AC11).
7. The load generator and the load-proof leg (AC12, AC13).

Order inside the build: the briefs at the end of the design's revision-notes.md. Wave 0 is four
independent briefs; wave 1 is four independent briefs that start when the wait primitive and the timers
table of wave 0 have landed; the census and the leg become required stages last.

Expected cost per gate: the census stage, seconds. The load-proof leg, about 10 to 15 minutes while the
proven set is the wave 1 suites, about 32 minutes at full coverage on the 20 CPU host, plus at most the
thirty-minute repetition allowance. These are estimates from recorded leg times (1,913 and 1,252 seconds);
the first leg records the measured values in proof/VELDO-0358.

Expected saving: a load-dependent control is found before the mutation stage, in minutes and by name,
and not as voided cases after two hours.

## Out of scope

- The remaining suites of the baseline (design, section 11, waves 2 to 4), each a later specification.
  This specification makes it impossible to add to them.
- The product timers and tool guards that no wave 1 suite crosses, and the events that later replace the
  wave 1 table entries (wave 5).
- The paired performance stage (wave 6). Suite 63 records its exit latency as data meanwhile.
- VELDO-0221. Any change to what a suite asserts beyond replacing an upper bound on a duration by the
  recorded cause and order.
- The follower's behavior on a kernel with no pidfd (its own specification is queued).
- Any quiet window, quiet rerun, load sampling, invalid result or bound on a gate's total time. These are
  not deferred; they are rejected (owner, Telegram 42171, 2026-11-18).

## What the reviewer judges

- Normal use: the owner's runner and the lander start scripts/verify.sh on the gate host while other
  builders, containers and gates use the same machine. Builders run single suites and the mutation
  driver's case selector by hand.
- Threat model: as in VELDO-0208. The candidate cannot widen what the census allows: exceptions are read
  from the authority only, and the candidate's baseline must be the required subset of the authority's.
  Code in an unconfined suite already runs with the owner's authority and is not defended against here.
- What to drive, not read: each falsifier above (apply the mutant, show by diff that it landed, see the
  named row go red, revert). The canary under the real generator: green without load, red with it. One
  suite of AC10 run fifty times under the generator with no failed and no hung row. A leg run in one
  interpreter under the generator, longer than 3600 seconds in total, not ended.
- Out of review scope, filed as later tickets: a timing assertion that evades R4 by its naming (the stamp
  object and the leg are the controls for it); a race that shows less than once in the leg's run count;
  load of a kind the generator does not make (network); tuning of the two constants.

A finding inside this section is fixed before landing. A real defect under normal use is always inside it.

## Notes

- Numbering: VELDO-0351 to VELDO-0357 exist in other worktrees and in the pending queue, so this is 0358
  although the highest number in this worktree's specs/ is 0350. The lead confirms the number at filing.
- Statuses: the specification vocabulary has no "superseded". AC14 uses status blocked with a History
  entry. If the lead adds a superseded status to .veldo/validate.py, that is its own change.
- Protected paths: the two new scripts and the two new lists are added to .veldo/policy.yaml at floor
  high, beside scripts/gate_unconfined.json. Landing needs the owner's commit-bound approval; the
  implementing agent authors none.
- Calibration: the generator's level is fixed by AC12. If the canary is not red at that level on the gate
  host, the level is raised in the specification before landing and the reason recorded in
  proof/VELDO-0358; it is not lowered to make a suite pass.
- A suite of AC10 that still fails under the generator after its sites and the timers on its path are
  converted has found a race. Fix the race: in the test when the test raced, in the product when the
  product did (precedent: the follower's pidfd, fe737440, and Launch.wait, f8c3a898). If the cause is a
  product timer not in the design's section 4.8, it is added to the timers table under AC15 in this
  specification. Do not add a bound, a retry or an exception.
- New mutants have no measured time; under AC9 they need none.
- The gate 8 red (VELDO-0143 activation/name-taken) and service/pm-settled-due have no known cause. This
  specification removes the leftover threads seen beside them and sets the client and store timers on
  their path to the hang bound; it does not claim those rows are fixed.
- engine/ui/src is in the footprint only for panels that do not yet expose their state to the page settled
  signal; a builder who needs no change there leaves it untouched.

## History

- 2026-11-20: drafted from the design of the same date. Supersedes VELDO-0223 (never built).
- 2026-11-20: revision 2 after independent validation (CHANGES): multiset baseline that shrinks without
  approval, progress-based hang bounds with no total bound, wave 1 product timers in scope (AC15), census
  rule by closed positional table and observed scope, kill_by, load by construction.
