# landing-b gate round 4: mutation stage, suite 126 baseline over its worker deadline

Gate at 30befb53: mutations failed, mutation_budget_exceeded, 126_veldo_0230_qualify_reproduces.py:qualify.py:False:baseline: worker deadline (120s); executed 0 of 2851.

Cause. Suite 126 has one mutation case, qualify230-claude-record-unwritten. Its baseline, no-op and
mutant each run the whole suite, whose core is the real `.veldo/qualify.py` against the qualified
Codex 0.166.0 and Claude Code 2.1.317 binaries: eleven extractors run in series, each scanning or
running the binaries offline, then the Codex catalog, the Claude Code init probe and the VELDO-0127
loopback fixtures. No network, no download. That is the work the case needs: its row qualify/covers
fails only when the command, run end to end, stops writing claude-qualification.json.

Passing gates in other worktrees recorded this case (VELDO-0215 store, max of baseline, no-op, mutant):
veldo-0230 86.0 s, upgrade-0166 103.3 s, landing-a 107.0 s, veldo-0261 119.3 s. landing-b has no
sample: the store key binds the authority checkout and the case's sources, and every gate here was red,
so no stage ever recorded one. An unmeasured case gets the 120 s floor; at load 28 to 32 on 20 CPUs
the baseline crossed it.

Fix. No code change and no raised constant. The VELDO-0215 machinery sets a measured case's deadline
as min(1800, max(120, 3 x max sample)) from passing authority runs. pending_runs.sh step 2 runs the
authority mutation CLI narrowed to this case (check_gate_mutations.py --case, measure=True); on a pass
it records the sample under the same key the gate reads, so the next gate gets about 3 x 100 s. The key
does not depend on HEAD; a later change to the suite, qualify.py, shared.py or the coordinator sources
drops it again.

Executed 0 is the designed rule: controls (baselines and no-ops) all finish before any mutant is
admitted, an expired worker deadline raises mutation_budget_exceeded and ends the stage, and
`executed` counts launched mutants only (check_gate_mutations.py run_stage, VELDO-0215 error taxonomy).

Runs: the host gate lock was held by another session's load run for the 20 minutes allowed; the
measurements are in pending_runs.sh.
