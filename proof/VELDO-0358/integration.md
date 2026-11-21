# VELDO-0358 wave 0: integration and the lead items

Branch veldo-0358, built on e3451130 (spec, design and contracts). This file records what the lead's
integration brought in, what it changed to close the items the briefs reported, and the runs that prove
it. The logs beside it are the evidence. Nothing here ran scripts/verify.sh: the lead queues the gate.

## 1. The briefs brought in

| Brief | Branch, range | Commits here | Conflicts and how they were resolved |
| - | - | - | - |
| A, suite runtime | veldo-0358-a, e3451130..76ba9045 | 0bea0901, 1eb91de9, 52e37e15 | none |
| B, census | veldo-0358-b, ..be945fcb | 15fa5ad7, c021769e | scripts/check_teeth_mutations.py (A's and B's mutant blocks, both kept, A's first), scripts/suites/manifest.json and requires.json (suites 157 and 158, both kept; manifest rewritten in its generator's form, json indent 1) |
| D, generator and leg | veldo-0358-d, ..b2f309b5 | 5d7ef203, 68ff162a | the same three files (D's block and suite 160 added after B's) |
| C, verdict, driver and timers | veldo-0358-c, e3451130..a9bc9edd | d2e3e941 .. c5738fe3 (ten) | brought in last, after the build log said cap_retry: done (contract order puts it between A and B; B and D were already on the branch, so it lands after them). scripts/check_teeth_mutations.py: C's block kept beside A's, B's and D's. By the landing order rule its 35 removed sites are lowered from B's baseline (6f125f98). C's verdict rule reads the repository's scripts/suites/wallclock_baseline.json, so the integrated tree has its authority baseline |

Landing order rule (contracts.md): B's baseline describes e3451130 plus B. A's conversions removed eight
sites it still counted (shared.py's waits, suite_labels' 1800 s bound); their entries are lowered in
9a216827. D added one site, the canary's sleep, which has its subject exception (below).

## 2. The lead items

| Item | Closed by | Proof |
| - | - | - |
| Suite 38, row wait/expiry-report (VELDO-0261) and mutant wait261-expiry-returns-none test the timed-out wait AC1 removes | 7ef3dd9f. The row now drives waits.wait_for's impossible outcome (a producer's pidfd): the report names what was waited for, the caller's former bound and its source, and the last observation of both conditions (what was real in 0261). A new row wait/expiry-hung drives the same wait with no terminal condition in a child whose wait hang bound is one second: it ends with the hung status and a SELFTEST HUNG line naming the wait, its line, the bound and the last observation, and never returns. No clock is read; the bound only decides when the row is called hung, which any machine reaches. The old mutant anchored shared.py's removed branch; it is retired for two replacements on waits.py: wait261-impossible-returns-none (target wait/expiry-report) and wait261-expiry-returns-false (target wait/expiry-hung) | mutants-suite38.txt: both rejected, baseline and no-op green. Three baseline entries of the old row lowered |
| Residue reds in suites 01, 93, 113, 127, 128, 141 (01 also red in 14's --upto row) | 8b057228. 01: three HTTP servers shut down, threads joined, listeners closed. 93: a factory pass that started two PM cycles left the receiver of the one run() did not wait for; leftover launches are waited for and reaped through the runner's own wait. 113_veldo_0145_ui: three API servers joined and closed; the e2e harness's fake bot server kept no handle, so Factory.close() releases it (engine/ui/docs/patterns/testing.md says so) and the suite calls it. 127, 128, 141: accept loops never woke on close(); the listener is shut down first (wakes accept with EINVAL on TCP and Unix sockets) and the threads are joined. brief A's latch holder is for processes the test must keep alive; none of these suites holds one, so what each releases is its own server, thread or child, ended by an event (shutdown, join, pidfd wait) | each suite alone: no residue row (section 3); and the full unit leg |
| Brief D finding 1: under scripts/gate_graph.json the mutation stage ran before verify.sh saw the leg | 7aab5c8c. The leg is a catalog slot, load (required:authority load-proof leg, the authority's own command like mutation), ordered before mutation. gate_graph.json: node load depends on every other node but mutation; mutation depends on load. gate_schedule.py (engine canon and copy): the load node runs gate_legs.py --load-proof (with the opened-files record when it exists); it is not_run when a node before it is red; a node that depends on it is not_started when it is red; no mutation floor is kept for a mutation node that waits for other nodes. verify.sh reads not_run and not_started and puts the load node's record into the stamp | suite 160 row leg/graph-blocks (real scheduler, fixture authority): red leg -> mutation not started; green leg -> mutation runs; red stage before -> leg not run, mutation runs as on the serial path; the real graph orders every node -> load -> mutation. Falsifier load358-graph-red-not-blocking rejected (mutants-graph.txt) |
| Canary subject exception; gate_load.py protected | 9a216827. scripts/suites/wallclock.json: subject entry for scripts/gate_load.py, function canary, R1. .veldo/policy.yaml protects scripts/gate_load.py and engine/scripts/gate_load.py. engine/.veldo/policy.yaml is the adopters' generic template (no repository path in it), so the repository keeps one policy that names paths | check_wallclock.py: pass |

Found while proving it, and fixed:

| Found by | Defect | Fix |
| - | - | - |
| full unit leg (suite 15, WARP-1402 AC5 and WARP-1409 AC6) | the gate domain reads a dedicated-branch slot's command from the line after its then; the load slot's branch was one line | the branch now has that form and names scripts/gate_legs.py --load-proof (34187cb5) |
| full unit leg (suite 155, VELDO-0304; also the extra stage's check_space_boundary.py) | brief D's gate_legs.py run_load_proof and gate_load.py canary create and remove temporary folders undeclared | declared by function in scripts/check_space_boundary.py (34187cb5) |
| loaded batch 1, real leg | gate_legs.run_load_proof read the unconfined declaration with load() and later bound the generator module to the local name load, so with a baseline, a record and scripts/gate_unconfined.json present (the real authority) the leg died with UnboundLocalError before running a suite; suite 160's fixture has no declaration and never reached that read | the reader is also named read_declaration and the leg calls it by that name (b5ad1d33) |
| loaded batch 1, mutants | suite 160's new hang-constants row loaded gate_load.py beside a gate_legs.py mutant copied alone | it loads gate_load.py from its own subject path (b5ad1d33) |
| census after brief C | C's command() waits with timeout=WAIT_HANG_SECONDS defined in its own file; the census resolved the name to its number first (D's finding 4) | the rule takes a hang constant by its name, also when the file defines it, at the contract's value only (600, 3600); a short value under the name stays a site. Suite 158 fixtures for both; falsifier wall358-hang-name-any-value rejected (mutants-census.txt) (6f125f98) |

The specification's footprint and protected paths now name every file this integration touched
(gate_schedule.py and its engine copy, gate_graph.json, the six residue suites, suite 38, 113_veldo_0220
and 114_veldo_0220 from brief B, the harness and its docs page, proof/VELDO-0219 round2 and round3
check.py, check_space_boundary.py, and the suites and VELDO-0219 proof scripts brief C restated). The two round scripts are run by suite 115 and took the mutation node alone with its
dependencies; they now drop its dependency on load.

## 3. Brief D's other findings

| Finding | Done or why not |
| - | - |
| 2. No opened-files record reaches the leg in a real gate | Not fixed. The full unit leg also showed the writer's other side: with VELDO_OPENED_FILES set, a dispatcher run inside a confinement that cannot write there ends with a traceback in _write_opened (suite 101's fixtures). The writer is brief A's dispatcher (VELDO_OPENED_FILES); the unit stage runs it inside the confinement (VELDO-0208), which grants no write outside the candidate's sandbox, and the leg must read a record the candidate cannot shape. Writing it needs a grant in scripts/agent_sandbox.json or a record taken by the authority from the unconfined side, both protected paths of VELDO-0208 and outside this specification's footprint: the lead's and the owner's decision. Until then the leg says no_record and runs nothing (green, the census's report mode). Both paths now hand the leg the record when it is there: the serial leg and the scheduler's load node read $VELDO_OUT/opened_files.json |
| 3. Canary subject exception | Done (section 2) |
| 4. A hang constant defined in its own file is read by the census as its number | Kept as brief D built it (HANG namespace). Importing waits.py from scripts/suites/support into the authority's generator would make the gate's tool load suite support code. Instead row load/hang-constants-are-the-contract (suite 160) requires gate_load.HANG to equal waits.py's two constants, so they cannot drift (00592a77) |
| 5. policy.yaml protects gate_load.py | Done (section 2) |
| 6. The canary green alone is a real-time check | Not changed, by its nature: a test synchronized by a sleep is the canary's subject and AC12 requires one. Its result is data in the load record and decides no row by itself |
| 7. engine/scripts/verify.sh has no leg | Not changed: an adopter's authority has no gate_load.py, and giving adopters the leg needs engine/.veldo/init_scaffold.py to lay it down, outside the footprint. The repository's verify.sh has the slot |
| 8. Suite 160's waits are plain reads of a child's output and pidfds | Not converted: they have no bound of their own and the census finds no site in them; the suite runtime's progress watchdog bounds them. Converting them to waits.wait is wave 2 polish, not a defect |
| 9. A suite that moves its children into another systemd unit leaves the leg's CPU set and cgroup | Not addressed here: it is a property of such suites (the unconfined leg's), for the leg's design. Recorded for the lead |

## 4. Runs

| Run | Where | Result |
| - | - | - |
| Full unit leg at 00592a77 (A, B, D and the lead items, before the fixes above) | full-unit-run.txt | 10747 passed, 27 failed. Mine, fixed since: suite 15's two gate-domain rows and suite 155's three rows. Artifacts of this run: the six VELDO-0208 rows of suite 101 failed because the run set VELDO_OPENED_FILES for every suite and the fixture dispatchers inside 101's confinement inherited it (brief A's writer then fails writing outside the sandbox: see finding 2); 101 is green without it (reruns-verify-readers.txt, and the final run). The rest as below |
| The 55 suites that read scripts/verify.sh, plus 15_warp_1402, 15_warp_1409 and 155, after 34187cb5 | reruns-verify-readers.txt | all green |
| Brief D's loaded batch at 34187cb5 | batch1/ | suite 160 green; four of five mutants rejected (load358-red-is-rerun: worker error, the row's load path); real leg: UnboundLocalError. Both fixed in b5ad1d33 |
| Brief D's loaded batch at b5ad1d33 | brief-d/suite-160.txt, mutants.txt, cgroup-scope.txt, real-leg.txt | suite 160: 5 rows green. Mutants: all five load358 cases rejected, unmutated green. The generator in a delegated scope: memory.high applied, spinners and writer alive, nothing left. Real leg (record runs from a worktree at b5ad1d33, B's baseline as lowered then): 28 of 239 suites proven, 3 waiting for a prerequisite, 25 run, none red; the canary red under the load; probe slowdown 4.5; 24 spinners and 2 writers alive throughout; 2605 s for the leg, data only. The longest suite in it was 15_warp_1404_historical_analogy (2604 s loaded). Memory level: none (no delegated scope in that leg's process) |
| Final full unit leg at 6f125f98 (all four briefs and every fix) | full-unit-run-final.txt | 10768 passed, 12 failed, all inherited or wave 1 (below) |
| Falsifiers of the lead's changes | mutants-suite38.txt, mutants-graph.txt, mutants-census.txt | wait261-impossible-returns-none, wait261-expiry-returns-false, load358-graph-red-not-blocking, wall358-hang-name-any-value: each rejected, baseline and no-op green |

The final run's reds:

| Suite | Rows | Why it does not block |
| - | - | - |
| 66_veldo_0042_clones, 86_veldo_0189_engine_upgrade | residue (serve threads) | wave 1: briefs G and F, as the brief says |
| 102_veldo_0210_agent_profile_runtime | seven scratch/* rows | inherited: red at e3451130 when it runs after another suite in one dispatcher (brief A's reruns-after-fix.txt, base section); green alone both at e3451130 and at 6f125f98 |
| 151_veldo_0313_space_run | three rows | inherited: red at e3451130 run alone (six rows there); brief G's suite |

Not run here, as instructed: scripts/verify.sh (the lead queues the gate). Brief C's full mutation stage is
its own record (brief-c/full-stage.txt, at its own HEAD 30d6fa2a); it was not repeated on the integrated
tree.
