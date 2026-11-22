# VELDO-0358 wave 1: integration and the lead items

Branch veldo-0358-w1, built on 636aeead (wave 0 finished). This file records what the integration brought
in, what it changed to close the wave 1 items, the root cause of loop/reset-timer-wake, and the runs that
prove it. The logs beside it (integration-wave1/) are the evidence. Nothing here ran scripts/verify.sh: the
lead queues the gate.

## 1. The briefs brought in

Each brief's own commits since fb7705e1, by git cherry-pick, in the order G, H, F, E.

| Brief | Branch, head | Commits here | Conflicts and how they were resolved | Built its own brief |
| - | - | - | - | - |
| G, space run, isolation and ownership | veldo-0358-g, 110b5f77 (8) | 7 picks ending fd82cf4f, then its proof | none | yes: suites 151 and 66_veldo_0042, v171_tailscale.py, mutation_ownership.py, engine/bin/veldo (and bin/veldo, its synced copy) |
| H, browser tests | veldo-0358-h, d3e681f4 (7) | 50c501a0 .. 364e46ae | none (the baseline and the registry merged by lines) | yes: playwright.config.ts, the e2e fixtures and specifications, harness.py, suites 120, 121, 124 |
| F, service, client and loop path | veldo-0358-f, d5450c70 (13) | 2a727aff .. 3115e2dd | scripts/suites/wallclock_baseline.json and scripts/check_teeth_mutations.py | yes: suites 66_veldo_0047, 71, 83, 86_veldo_0189, 110, proof/VELDO-0152/fixture.py; control_service, control_client, control_client_api, control_store, control_factory_setup_upgrade |
| E, launch and containment path (two rounds) | veldo-0358-e, 2927f3fb (23) | 6a23d6c1 .. 0831a89f | the same two files | yes: suites 62, 63, 78, 106 and the files they open (85_veldo_0171, setup_runtime.py, v73_authority.py, compare_formats.py, by the lead's decision); control_launch, control_containment, control_heartbeat, control_engine_claude, control_engine_codex, policy_contract, and the scaffold line for timers.py |

The lead's template said "implement brief A" in every wave 1 task. No brief built brief A: each one's
changed files are the files of its own section of the revision notes (3.3), read from the diff of its
branch against fb7705e1. Brief F did not change control_workflow_cycle_pm.py: the role budget reaches it
from the VELDO-0152 fixture's role_seconds, which suite 110 sets to the wait hang bound.

Conflicts, both intents kept:

- scripts/check_teeth_mutations.py: one block per brief, kept whole and in landing order (H, G, F, E), then
  the lead's block (VELDO-0358 WAVE 1 INTEGRATION).
- scripts/suites/wallclock_baseline.json: by the landing order rule. Per key the smaller of the two counts,
  and a key either side removed is gone; no key was added by either side. After the four briefs the census
  passed against the wave 0 baseline as its authority (no site over its count, every entry at its required
  count): 2822 entries at fb7705e1, 2359 after the briefs, 2352 after the lead's conversions.

## 2. The wave 1 items of the combine list

| Item | Closed by | Proof |
| - | - | - |
| waits.cgroup_populated and CgroupEmpty treat only ENOENT as gone (brief G) | 7cc54406. Both read a cgroup's events through one opener and take ENOENT and ENODEV as the same fact: populated is None, the source is gone and is not polled, a wait for the group to be empty is done at its first reading. Any other error is still raised. Every caller gets it (suites 63, 66_veldo_0042, 157) | suite 157 row waits/cgroup-gone-is-empty: the kernel's own ENODEV, made by removing a child cgroup once its events file is open. Falsifier wait358-enodev-not-gone rejected (mutants-waits.txt) |
| bin/veldo into the footprint (brief G) | fd7900a3. The footprint now names every file waves 0 and 1 changed that it did not: bin/veldo, the synced .veldo copies of the engine modules, init_scaffold.py, claim.py, the files brief E and the lead converted, suites 36 and 86_veldo_0168 | computed from the diff against e3451130: no changed file is outside the footprint |
| THE HANG WATCHDOG MUST KILL AND REAP THE WHOLE PROCESS TREE (brief F: 38 leaked processes) | 7cc54406. scripts/selftest.py becomes the run's keeper (waits.keep_the_tree) and its child runs the suites. The keeper is the run's child subreaper, so a process whose parent ended (the orphaned worker of suite 83's receiver-death row, in a scope of its own) is the keeper's child and is reaped by it at once, as the user manager would. When the suite process ends without having said that it ran every suite to its end (a hung wait, the watchdog, its faulthandler timer, a signal), the keeper kills every descendant, reaps each one, names each (SELFTEST TREE) and only then ends with the run's own status. An orderly end kills nothing: what a suite leaves then is the residue row's. The keeper sleeps in sigwaitinfo and reads no clock | suite 157 row watchdog/hung-tree-ended: four holders nobody releases (a child, a child with a child below it, and a process in a session of its own whose parent ended at once); after a hung run each is reaped (pidfd: no such process) and named; after an orderly run each is still held and is then released by the test. Falsifiers wait358-hung-tree-left and wait358-orphans-not-kept rejected (mutants-waits.txt) |
| Suite 36 needs sys in its allowed imports (brief F) | b0dba70e. control_store loads the shared timers table through sys.modules; sys is standard library, which is what the row requires | suite 36 green alone and in the unit leg |
| AbortSignal.timeout(n) in the census (brief H) | b0dba70e. An R3 site in TypeScript, in scripts/check_wallclock.py and its canon copy; the hang constants are the allowed forms | suite 158: a site fixture and an allowed one. Falsifier wall358-abort-signal-ignored rejected (mutants-lead.txt) |
| Sites in decisions.spec.ts, factory_harness.py, team_harness.py and suite 122 (brief H) | b0dba70e. unique() for the alias, H.wall() for the record's time, H.WAIT_HANG_SECONDS for the key tool, and suite 122 as suite 121 was converted (run_heavy for the install, the build and the browser run, the stamp, no suite seconds). Seven baseline sites lowered. Suite 121's row wave1/no-sites reads the four files | census pass. Falsifier wave358-harness-bound-restored (suite 121; in the full mutation stage) |
| AC15 rechecked with E's and F's timers in | section 4 | |
| Suite 151's dynamic row names (brief G) | Decided yes, fd7900a3: waits.declared_rows reads the rows a suite declares in ROWS (66 suites state their rows at their end under names built at run time). When such a suite hangs, each declared row no stated row reached prints SELFTEST NOT RUN, so the verdict rule reads a target row as not run (hung_not_killed) and not as a removed row | suite 157 row waits/declared-rows-not-run. Falsifier wait358-declared-rows-unread rejected (mutants-lead.txt) |
| Check that E, F and H built their own brief | section 1 | |

Also closed, from the briefs' own lead items:

| Item | Closed by | Proof |
| - | - | - |
| Brief F item 2: a module read from a fresh cache file was claimed by no suite, so the opened-files record lost it | 9e3acdd1. The dispatcher's audit hook claims the source of a cache file it sees opened (the authority's watch already counted it) | suite 157 row record/cached-module-is-its-source. Falsifier opened358-cached-module-unclaimed rejected (mutants-lead.txt) |
| Brief F items 1, 6b, 9 and brief E item 9 (the scaffold line, _await_gone, the private timer readers) | landed with briefs E and F together | the unit leg and the mutation stage below |

## 3. The root cause of loop/reset-timer-wake

The red (once in 50 loaded runs for brief F, once for brief E): at the reset the pass offered nothing and
refused the waiting unit missing_authority:claim.

Cause. The row claims its unit, runs it once into an account limit, and waits for the reset, which it states
as the end of a minute 30 to 90 seconds after the claim. Nobody renews a claim while no run works for its
unit, so at the reset pass the claim's last heartbeat is the claim itself, cut to a whole second. The product
judges a claim's liveness on its own clock: older than 90 seconds is stale (engine/.veldo/claim.py,
STALE_AFTER_SECONDS), and a stale claim is not owned. So the row was red whenever the reset was stated in
the first second of its window (one run in sixty, on an idle machine too), and on a busy machine also when
the reset was stated a few seconds later and the reset pass ran that many seconds late. It is a product
contract timer on the suite's path that the timers profile did not hold, and no bound in the suite.

Reproduced (reset-timer-wake-repro.txt): a scratch copy of the tree before the fix, with the reset stated in
the first fifth of a second of its window, is red at loop/reset-timer-wake with exactly the recorded
refusal, alone on an idle machine. The same aid over the fixed tree is green.

Fix (f9662c65), by the specification's rule for a product timer outside the design's section 4.8:

- engine/.veldo/claim.py (and its synced copy): the liveness window is an entry of the timers table
  (claim.STALE_AFTER_SECONDS, kind contract), read at each judgment. Its production value is unchanged, and
  the module's constant keeps that value for its other readers.
- Suite 83: its launch receivers and their wrappers now run under the profile too. They take it from the
  receiver configuration, which the suite had not set, so beside a profiled service they armed the launch
  path's timers and judged the claim at production values.
- Suite 83's reset row now states a claim renewed twice the production window before now. The row no longer
  depends on the phase of the minute or on how late a pass ran, and it fails by assertion when any of the
  three processes that judge the claim (the suite, the service, a receiver) is outside the profile.
  timers/profile-applied requires the claim's entry in this process and in both services' start records.
- Falsifier timers358-claim-window-literal (the judgment reads the production value whatever the profile):
  rejected, target row red by assertion (mutants-claim.txt).

No bound was raised and nothing is run again.

For the owner, outside this specification: in production nothing renews the claim of a unit that waits with
no run for longer than 90 seconds (for an account's reset hours away, for a free slot). The loop's pass at
the reset would refuse such a unit as this row was refused. Whether the line's builder renews its claims
elsewhere was not traced; if nothing does, it is a product defect of its own.

## 4. AC15 rechecked with brief E's and brief F's timers in

The timers table now has entries from twelve engine modules: control_launch, control_containment,
control_heartbeat, control_engine_claude, control_engine_codex and policy_contract (brief E),
control_service, control_client, control_client_api, control_store and control_factory_setup_upgrade
(brief F), and claim (this integration).

| Question | Answer |
| - | - |
| Do the profile rows of briefs G and H, which saw an empty table, have teeth now? | Yes. Suite 66_veldo_0042 requires control_containment's two entries and the unit leg ran its row green; suites 120, 121 and 124 read every entry the browser harness reports (the store's, the client's and the launch's beside the harness's sentinel) and hold each to the bound. The timers358 falsifiers of briefs E and F are in the full mutation stage (section 5) |
| Is every process of a wave 1 suite under its profile? | Suite 83 was not: its launch receivers and wrappers ran at production values. Fixed (section 3), and the reset row is red when one is not. Suite 106 still is not, as brief E reported (its item 4): the service setup installs and starts runs at production values while its receivers run under the profile. Brief F's service profile exists now; handing it to that service is a change to brief E's suite that was not made here |
| Does the census find a numeric timeout in the engine files of section 4.8 outside the table? | Two, both baseline entries and both cadences that the design's section 4.8 leaves unchanged in wave 1: listener.settimeout(ACCEPT_SECONDS) in control_service.serve and self.server.settimeout(0.25) in control_client_api.Hints. A lap at the hang bound would stop the laps, so neither is a table entry. AC15's sentence holds for every giving-up deadline and not for these two cadences: the owner decides between an exception kind for a cadence and the cadence's own event (wave 5) |
| Is a product timer outside section 4.8 on a wave 1 suite's path? | One was found: the claim's liveness window (section 3), now a table entry |

## 5. Runs

Every heavy run went through the external host-heavy wrapper (outside the repository), each from its own
detached worktree of the named commit, so later edits could not disturb it. The tree was frozen at 9e3acdd1
for them. Two things changed after it: a path in suite 151's census row (1f0120c6), found by the unit leg and
covered by its own runs below; and terminal conditions in suite 83 (5342fa22) that were withdrawn again
(4486b1bf), so suite 83 is byte for byte the file of 9e3acdd1.

| Run | Where | Result |
| - | - | - |
| Full unit leg at 9e3acdd1, one dispatcher over every suite | full-unit-run-9e3acdd1.txt (driver unit_with_ledger.py.txt) | 10804 passed, 18 failed, no hung row, no residue row red (the two residue reds of wave 0, suites 66_veldo_0042 and 86_veldo_0189, are gone). The 18 are below |
| Fifty loaded runs each of suites 62, 83 and 151 at 9e3acdd1 | loaded-62-83-151.txt (driver loaded50.py.txt, the leg's own runner under scripts/gate_load.py: 62 and 83 unconfined as the gate lists them, 151 through the confined launcher) | 150 of 150 with no failed and no hung row. 24 spinners and the writers alive to the end, probe slowdown 4.55 (data) |
| Fifty loaded runs of suite 151 at 1f0120c6, after the fix the unit leg found | loaded-151-1f0120c6.txt | 50 of 50 with no failed and no hung row, probe slowdown 4.2 (data) |
| The load-proof leg at 9e3acdd1 | load-proof-leg-9e3acdd1.txt (driver leg.py.txt; the wave 0 checkout as the authority, so wave 1's suites are the changed ones) | pass. 44 of 239 suites proven, 41 run, 326 suite runs, none red. The fifteen changed suites ran twenty times each (62, 63, 66_veldo_0042, 66_veldo_0047, 71, 78, 83, 85_veldo_0171, 86_veldo_0189, 106, 120, 121, 122, 124, 151). The canary is red under this load (calibration, revision notes 3.4). 24 of 24 spinners and both writers alive to the end, probe slowdown 4.1, 6186 s for the leg (data). Longest: 15_warp_1404 at 3091 s loaded, once |
| The proven set | the same log | every wave 1 suite is in it but 110_veldo_0143_new_project: a baseline entry remains in scripts/suites/support/identity_wire.py, which it opens and no brief owned (brief F's item 3) |
| Suite 83 with the reset stated in the fatal second, before and after the fix | reset-timer-wake-repro.txt | red before, green after (section 3) |
| The lead's falsifiers through the registered cases' own worker | mutants-waits.txt, mutants-claim.txt, mutants-lead.txt, mutants-151.txt | wait358-enodev-not-gone, wait358-hung-tree-left, wait358-orphans-not-kept, timers358-claim-window-literal, wait358-declared-rows-unread, opened358-cached-module-unclaimed, wall358-abort-signal-ignored: each rejected on its target row, baseline and no-op green. Brief G's wave358-clones-socket-timeout-restored still rejected after 1f0120c6 |
| Suite 101 alone at 1f0120c6 | (this file) | 190 rows green, unconfined-leg/fixture-sharers-are-listed among them |

### The mutation stage

| Run | Where | Result |
| - | - | - |
| The full stage at 9e3acdd1, ten workers | full-stage-9e3acdd1.txt | status failed: stopped after 16686 s with 723 of 3665 cases executed, 650 rejected (76 by assertion, 574 unproven: a suite or a file it opens still has a baseline entry). It stopped on a worker cleanup error: the mutant of loop154-pipe-not-polled made suite 83 hang, the hung process left its directory under /dev/shm, and an unmetered worker's directory outside its home cannot be shown to be its own (the gate's metered workers can). Of the 73 invalid results: 58 are the cases of suite 86_veldo_0127, whose controls are red until the live recapture; 3 are cases of suite 160 whose no-op control was red because the canary ALONE was red under the stage's own load (below); 1 control and 1 survivor are of suite 86_veldo_0148 (below); 5 are suite 83's (1 hung, 4 cancelled when the stage stopped); 5 cancelled |
| Suite 83's twelve cases, each driven alone | mutants-suite83.txt | eight rejected on evidence; FOUR HANG and are not rejected: loop154-pipe-not-polled, loop154-ask-reruns, loop154-account-slot-kept, loop154-orphan-not-stopped. In the gate each is hung_not_killed, and the stage is red. Brief F drove its five falsifiers and not the inherited cases of its suites (section 7, item 1) |
| The cases the first stage did not judge, in groups through the same driver at 5342fa22 (one stage per wave 1 suite, then the other suites 400 at a time) | stage-groups.txt (driver stage_groups.py.txt) | GROUPS |
| The survivor and the red control of suite 86_veldo_0148, driven alone | mutants-0148.txt | reland148-landed-rebuilt is rejected alone (target row red, controls green): it survived only under the stage's load. receiver148-release-deadline-not-finite: its no-op control is red alone too (receiver/pre-release-budget). Suite 86_veldo_0148 is not a wave 1 suite and has baseline entries: its verdicts are unproven by the specification's own word, and both are wave 2's |

The three red controls of suite 160: row load/level-by-construction requires the canary green ALONE, and the
canary is by construction a test synchronized by a sleep (AC12). Inside the mutation stage, beside ten workers
and two other heavy runs of this integration, alone was not quiet and the canary was red in the no-op control.
Wave 0 recorded this as its finding 6 and left it, by its nature. It is a row of this specification that
depends on how busy the machine is, and it needs the owner's ruling (section 7, item 2).

The unit leg's 18 reds:

| Suite | Rows | Why |
| - | - | - |
| 86_veldo_0127 | live/claude, live/codex | expected. The live captures are bound to the digests of the engine modules waves 0 and 1 changed (brief E's item 8). The owner-approved recapture is done once on the combined line (the combine list) |
| 126_veldo_0230 | qualify/reproduces | expected, the same binding: qualify is run again on the combined line |
| 101_veldo_0208 | unconfined-leg/fixture-sharers-are-listed | new, found here and fixed (1f0120c6): suite 151's census row wrote suite 66_veldo_0042's path whole, which this row reads as loading a listed suite |
| 102_veldo_0210 | seven scratch/* rows | inherited: red when it runs after other suites in one dispatcher, green alone (wave 0, section 4) |
| 151_veldo_0313 | seven rows | inherited, and of the host: in one unconfined dispatcher on a shared host, processes nobody here can read hold its runs (the suite's own docstring). Through the gate's confined launcher it is green: 50 of 50 loaded here, 20 of 20 in the leg |

## 6. Protected paths changed by wave 1, for the owner's approval at landing

Beyond the paths of wave 0 (integration.md, section 5), which are unchanged since 636aeead except as listed:

| Path | Change | By |
| - | - | - |
| scripts/selftest.py | the keeper (waits.keep_the_tree before the watchdog is armed, waits.run_ended after the last suite); a module read from its cache file is claimed as its source | this integration |
| scripts/check_wallclock.py, engine/scripts/check_wallclock.py | AbortSignal.timeout(n) is an R3 site in TypeScript | this integration |
| scripts/suites/wallclock_baseline.json | lowered only: 2822 entries at fb7705e1, 2352 now (briefs E, F, G, H and the lead's seven sites). No entry added, no count raised; the census passes with the wave 0 baseline as its authority | the four briefs, this integration |
| specs/VELDO-0358 (the specification) | footprint, protected_paths (scripts/check_first_use.py and scripts/suites/shared.py, which wave 0 changed and the list did not name) and History | this integration |

Not protected by .veldo/policy.yaml, and named because they are product or runtime behavior the owner should
see: engine/.veldo/claim.py (the claim's liveness window read from the timers table; production value
unchanged), scripts/suites/support/waits.py (the keeper, the cgroup readers, declared rows), engine/bin/veldo
and bin/veldo (brief G: the supervisor acknowledges each stop on its report), the engine modules of the
design's section 4.8 (briefs E and F: timers from the table; the receiver awaited on its pidfd; the orphan
release on cgroup.events; the service's timers_profile, its start record, its STATUS line per channel pass and
pending_wakes), and engine/.veldo/init_scaffold.py (lays down timers.py). scripts/suites/wallclock.json (the
exceptions) is not changed by wave 1.

## 7. Open, for the lead and the owner

BLOCKERS FOR THE GATE:

1. Four inherited mutants of suite 83 hang it (mutants-suite83.txt): loop154-pipe-not-polled (the pass after a
   run's end never comes: the service holds the run and is neither idle nor ended), loop154-ask-reruns and
   loop154-account-slot-kept (the service is quiet for good but lists an orphan whose release is pending, which
   the suite's idle answer does not accept), loop154-orphan-not-stopped (under the profile the service itself
   waits the hang bound for an orphan nobody stopped, and answers nothing meanwhile). AC10 requires every
   registered case of a wave 1 suite rejected by assertion or terminal condition; brief F proved only its five
   new falsifiers. Tried here and withdrawn: a terminal condition on the receiver's exit (the service asked
   twice after it, still holding the run) and an idle answer that accepts a pending orphan and a timer further
   away than any wait. On an idle machine they ended three of the four on evidence; under load they made the
   unmutated suite red (7 of 32 loaded runs; loop/receiver-death five times, the waiting unit not offered in the
   pass of the receiver's death), so suite 83 is as the loaded runs proved it. The fourth needs the product to
   record that it made the orphan's stop before it waits. This goes back to brief F.
2. Suite 160's row load/level-by-construction is red when the canary alone is run on a busy machine (three
   controls in the stage). AC12 asks for the canary green alone; the owner rules whether that fact is asserted,
   or recorded as data like the canary's red in the leg.
3. Release acts on the combined line before the gate: qualify again (suite 126) and the owner-approved live
   recapture (suite 86_veldo_0127), because their records are bound to the engine modules' digests.
4. Suite 110 is not in the proven set: scripts/suites/support/identity_wire.py has baseline entries and is in
   no brief's files and outside the footprint (brief F's item 3).
5. AC15: the two cadences of section 4 need the owner's decision; suite 106's service runs outside the
   profile (brief E's item 4).
6. The keeper ends the process tree: what the suite process started, and what was started below it. A unit
   the user manager itself starts for a suite (systemctl start of an installed unit) is no descendant and is
   not ended by it. A descendant another account owns is named as not ended. A heavy child that run_heavy ends
   after its second bound is killed alone unless it is a dispatcher (then its keeper ends its tree on the first
   signal). A mutation worker runs a suite with no dispatcher and so with no keeper: its coordinator reaps the
   worker's unit, and a hung suite's directory under /dev/shm stops an unmetered stage (section 5).
7. A browser expectation that never holds takes the wait hang bound to fail (brief H's item 3): it makes
   the mutation stage long, as the stage's time below shows. A design follow-up for wave 2.
8. In production nobody was found to renew the claim of a unit that waits with no run (section 3).
9. Brief E's item 11: control_api_authority's stop_worker has the stale_version order brief E fixed in
   Runner.honor_stops; no row reaches it.
