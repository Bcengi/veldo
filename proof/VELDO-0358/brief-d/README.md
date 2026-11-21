# VELDO-0358 brief D: the load generator and the load-proof leg

Branch veldo-0358-d, built on e3451130. Criteria: AC12, AC13. Scope: revision-notes section 3.2, brief D.

## State, stated first

The code, the suite and the four mutants are built and committed. **No loaded run was made.** Every
loaded run was queued through host_heavy.sh as one batch (batch.sh.txt) and waited two hours behind a
gate and about a dozen other jobs on the host lock; it never got the lock and was stopped at the
session's limit for a background job. So the two AC rows, the four falsifiers, the generator inside a
delegated cgroup scope and the real leg of the Done line are **not proven here**. They are one command:

    bash host_heavy.sh bash proof/VELDO-0358/brief-d/batch.sh.txt <this worktree> <scratch folder>

with a plain export of brief A's HEAD in `<scratch>/brief-a` and brief B's baseline in
`<scratch>/brief-b-baseline.json` (real_leg.py.txt says why). It writes suite-160.txt, mutants.txt,
cgroup-scope.txt and real-leg.txt beside this file. The fifteen existing suites that read verify.sh
or gate_legs.py were queued the same way and did not start either.

## What was run (no load, outside the lock)

| Check | Result |
| - | - |
| scripts/check_lint.sh | pass (1246 python, 40 shell) |
| scripts/check_template_sync.sh | pass, 325 pairs (gate_load.py and gate_legs.py equal their engine copies) |
| scripts/check_generated.sh | pass (requires.json regenerated with suite 160) |
| scripts/check_personal_setup.py | 0 findings |
| The four mutant anchors (materialize) | each found exactly once, each changes its module |
| Brief B's census over this branch's files | one site: the canary's sleep (finding 3 below) |
| gate_load.py --canary alone | green |
| One generator run of 0.6 s, two slots, the canary inside (made before the queue was seen; not repeated) | canary red, 6 of 6 spinners and the writer alive, record applied |
| A fixture gate (real verify.sh, gate_legs.py, dispatcher) with every fixture suite baselined | GATE: GREEN, leg state empty, the load field in the stamp, the mutation stage started |

## What was built

| Piece | Where |
| - | - |
| Generator (AC12) | scripts/gate_load.py, canon copy engine/scripts/gate_load.py |
| Leg (AC13) | scripts/gate_legs.py (section THE LOAD-PROOF LEG), canon copy |
| The leg in the gate | scripts/verify.sh: veldo_load_leg, called before the mutation stage; the load field of the stamp and the event |
| Rows | scripts/suites/160_veldo_0358_load_leg.py: load/level-by-construction, leg/proves-and-blocks, leg/proven-and-changed-rules |
| Falsifiers | scripts/check_teeth_mutations.py, block "VELDO-0358 BRIEF D": load358-no-spinners, load358-affinity-dropped (gate_load.py), load358-red-is-rerun (gate_legs.py), load358-red-not-blocking (verify.sh) |

The code keeps the rule it builds. It has no sleep but the canary's, reads no wall or monotonic clock,
and waits only on events: a readiness byte from each generator, a pidfd, cgroup.events, a line of a
suite process. A suite process is ended only after the process hang bound with no line on its output.
Nothing bounds the leg.

Decisions a reader should know:

- Spinners run in the same cgroup as the suites. Between two cgroups the kernel shares a CPU by group, so
  a lone suite process beside a cgroup of spinners would get most of a CPU and the "quarter" of design
  10.1 would not hold. The design says "a cgroup beside the leg's"; that holds for the writers only.
- A writer's file has no name from the moment it exists (O_TMPFILE, or unlinked at once), so a killed
  leg leaves nothing. Generators die with the process that started them (PR_SET_PDEATHSIG).
- The probe is the kernel's own account (/proc/self/schedstat: time run and time waited to run) over
  one CPU-second of work. No clock is read.
- A suite's loaded time is the dispatcher's own figure on its summary line. The leg's wall time in the
  stamp is verify.sh's two readings of the date.
- The selector runs a suite with its prerequisite closure in one process, so a proven suite runs in the
  leg only when its whole closure is proven; otherwise it is printed as waiting.
- Changed means the file differs between candidate and authority, as in brief B's census. A checkout
  that is its own authority has no changed suite.
- The repetition count is one figure for all changed suites: the largest from twenty down that fits
  1800 s at the slots, longest run first on the first free slot. It gives the design's own example
  (960 s, eight slots: eight runs).
- The canary runs once under every real leg and its result is in the load record as data.
- With no baseline in the authority, or no opened-files record, the leg says so, runs nothing and is
  green (the census's report mode).

## Findings for the lead

1. **Under the graph scheduler the leg cannot block the mutation stage.** The real authority has
   scripts/gate_graph.json, and scripts/gate_schedule.py runs every stage, mutation first and in
   parallel, before verify.sh sees a result; it also starts a node whose dependency failed. So on the
   real host the leg runs after the mutation stage: its red is the gate's red, but "the mutation stage
   is not started" holds only on the serial path, which is what the fixture row drives. Ordering it
   needs a node in gate_graph.json (brief B's file) and a scheduler that holds a node whose dependency
   failed (gate_schedule.py, in no brief and not in the specification's footprint). Not touched.
2. **No opened-files record reaches the leg in a real gate.** Brief A's dispatcher writes it only where
   VELDO_OPENED_FILES points, nobody sets that variable, and the confined leg cannot write outside its
   sandbox (a write to /tmp and to .veldo was refused when tried; with the variable set, the write would
   fail at the dispatcher's exit). The leg reads `opened_files.json` beside the stamp when it is there,
   else the authority's `.veldo/opened_files.json` (brief B's default). Until one exists the proven set
   is empty.
3. **The canary's sleep needs a `subject` exception** in scripts/suites/wallclock.json (brief B's
   protected file, the owner's approval): scripts/gate_load.py, function canary, rule R1. It is the one
   site this branch adds. AC12 requires it.
4. **Brief B's census does not accept a hang constant defined in the file that uses it** (it resolves the
   name to its number first). gate_load.py therefore holds the two bounds in a namespace (HANG) and
   gate_legs.py reads them from there. Once brief A lands, pointing these at waits.py is the lead's call.
5. **.veldo/policy.yaml** (brief B's file) does not yet protect scripts/gate_load.py and its engine copy,
   which the specification lists.
6. **"The canary green alone" is a real-time check by its nature.** The row runs it on every CPU the
   process may use, so it stays green inside a real leg; on a machine with no idle CPU it can be red.
7. engine/scripts/verify.sh (the adopters' template) is unchanged: an authority without gate_load.py
   has no leg. scripts/suites/manifest.json and requires.json carry suite 160's entry.
8. Suite 160's waits are plain reads of a child's output and of pidfds, with no bound of their own
   (the suite runtime's watchdog bounds them). They can become waits.wait calls once brief A is in.
9. A suite that moves its children into another systemd unit takes them out of the leg's CPU set and
   cgroup. Not addressed.
