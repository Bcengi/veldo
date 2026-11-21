# The conversation chain on the line: what the line's later rules asked of it, 2026-11-21

VELDO-0231, 0177, 0176, 0175, 0178, 0179, 0180, 0181, 0183, 0184 and 0187 were brought onto the line one
commit each (each ticket's `proof/VELDO-<n>/bringup.md`). The chain was built before 563 commits of the
line. This commit holds what those later rules and suites asked of the chain as a whole, found by the
checks below. Nothing here has had a review.

## Found by `scripts/check_space_boundary.py` (VELDO-0304)

- `control_clone.conversation_clone` (VELDO-0175) fetched the commit into a held ref and deleted the ref.
  On the line only the space remover deletes a ref, and the check has no entry that could allow another.
  The commit is now fetched into no ref (`git fetch <source> <commit>`), then the branch is made as before.
  The mutant `clone175-into-initial-branch` anchors on the new line; applied in place it still turns
  `AC4/attach-initial-branch` red.
- The same function removes the work folder it made when a clone fails (VELDO-0177). One `REVIEWED` entry is
  added for it, marked in the file as added by the bring-up and pending review with design 6.10: a
  conversation's workspace is held by no space ledger. Whether it should be is the owner's question.
- `control_conversation_project.snapshot` (VELDO-0180) wrote a clone's bundle into a temporary folder. It now
  reads the bundle from git's output (`git bundle create -`), so no folder is made.

With these the check passes and suite 155_veldo_0304_space_boundary passes 51 rows.

## Found by the sweep (`sweep.txt`, `reruns.txt`)

Every suite that names a module the chain changed, 167 of 254, was run alone at the head of the port.
158 passed. The nine that did not:

| Suite | Rows | Cause | Now |
| --- | --- | --- | --- |
| 131_veldo_0184_file_memory | AC1/qualified, AC2/qualified | `proof/VELDO-0184/engine-memory-forms.json` named the source's engines (Claude Code 2.1.281, Codex 0.154.0) | The extractor reads the Claude Code forms by the product's own `FILE_MEMORY_PATTERNS` (its 2.1.281 literals with the minified names left open) and the file is read again from the line's engines, 2.1.317 and 0.166.0: all seven patterns and all six Codex literals found. 16 passed |
| 146_veldo_0308_run_finished | four | Its receiver made without `__init__` lacked what the chain's `_finish` and refusal path read | The fixture carries those defaults, as VELDO-0187's batch fix did for suites 63 and 103. 38 passed |
| 127_veldo_0254_secret_scan | three | The same, in its bare receiver | The same. 22 passed |
| 129_veldo_0254_canary_launch | ac1/canary-conversation | It expected a turn to run in the conversation's directory; since VELDO-0177 it runs in the conversation's workspace | The row reads `workspace_of`. 7 passed |
| 129_veldo_0239_batch_landing | wire/constructions | VELDO-0175 adds a fourth production intake, the service's own, built without VELDO-0239's batch starter | The service's intake passes the batch starter, and the row names four constructions. 23 passed |
| 79_veldo_0061_codex_adapter | pin/qualified-record | VELDO-0231's flag probe is written by the qualify command; the row compared it with the writer's "not probed" | The row takes `flag_means` as the command's completion, as it takes the other fields the command completes. 21 passed |
| 105_veldo_0182_memory | copy/chroma-busy-refused | False once at load 25 | 127 passed on the second run, nothing changed. A load flake, not looked into further |
| 86_veldo_0127_agent_configuration | live/claude, live/codex | VELDO-0231's own open item: the live captures are stale | Still red. The lead retakes them on real accounts |
| 151_veldo_0313_space_run | eight to ten | Red on the line without the chain too (ten rows at 3465d09a, the same day): its runs' ends were still asleep after 120 s on this loaded host | Still red here. Not the chain's; not looked into further |

One item of the extractor is reported, never required: a 2.1.281 literal that no product pattern reads
(`autoMemoryEnabled` read per settings source) is not in 2.1.317, which reads that setting through another
function. The product's rule for a version (every pattern found) holds on 2.1.317, and a run that loads memory
from elsewhere is still stopped at its init event (`AC1/mismatch-stop`). A reviewer should look at this once.

## Not done

- `scripts/verify.sh` was not run, and neither was the whole selftest as one run: 87 suites that name no
  changed module were not run at all.
- The 68 registered mutants of the chain's eleven findings and the 11 mutants of other findings the ports
  re-anchored were each applied in place and
  are red on their rows (each ticket's `bringup-2026-11-21/falsifiers.txt`). Only VELDO-0231's four went
  through the mutation driver with its baseline and no-op controls.
- Two protected paths change on this line, and the owner's approval is needed at landing for both:
  `scripts/gate_unconfined.json` (six suites across VELDO-0177, 0179, 0183 and 0187) and
  `scripts/mutation_case_inputs.json` (VELDO-0175's declarations; see fix round 1 below). The first bring-up
  named only the first.

## Fix round 1 (2026-11-21), from the review of the line at 1df7ae35

Commits 97043de7 (small items), 5635eaab (VELDO-0231 AC1), 81e610e3 (the chain's waits), 3c775bda (suite 127
tells its fake engine at once when a flag was not committed in its cycle). F4 (VELDO-0231 on a
real engine, suite 86's live rows) is not attempted here: no live run on a real account; the lead asks the owner
for capture runs before the gate. F5, F6 and F10 were not in this round's brief and are left as the review
states them: F5 is for VELDO-0184's reviewer, F6 is VELDO-0231 AC2/AC3 text (the qualify probe's 5 second
"immediate" bound, `control_engine_codex.IMMEDIATE_SECONDS`, still judged by wall time) for the owner or the
lead, F10 is optional.

### Protected paths this line changes (F1)

The owner's approval is needed at landing for both:

- `scripts/gate_unconfined.json`: six suites across VELDO-0177, 0179, 0183 and 0187 need the host (above), and
  this round rewords the reasons of two of them (F8).
- `scripts/mutation_case_inputs.json` (f31c751a, VELDO-0175): seventeen mutation-case declarations that read
  `control_intake.py`, `control_workflow_cycle_pm.py` or `control_service_channel.py` also name
  `control_intake_conversation.py`, `control_conversation_channel.py` and `control_conversation.py`, the modules
  VELDO-0175 split those paths into, so each case's declared inputs cover what its suite now reads
  (`proof/VELDO-0175/OPEN.md` section 4: each case traced with `scripts/propose_case_inputs.py`, only those three
  paths added, 51 lines).

### VELDO-0231 AC1 restated (F3, lead decision)

Under the owner's rule that no gate depends on machine speed (Telegram 42829, 2026-11-20), AC1's "within 2
seconds" is now an ordering criterion: the flag is committed in the same dispatch cycle of the service loop that
reads it, with no wait, poll or pass between, proven by event order in the record. Recorded in the
specification's History as a lead decision citing 42829; its falsifier and the suite's manifest row follow.

- The suite traces the loop's dispatch cycles (each `readable` call): each flag event taken off the launch pipe
  and each commit, with its cycle. `AC1/at-once` requires each commit in the cycle that took its flag, the order
  taken, commit, taken, commit ..., and each commit while the dispatch is running and its run not ended.
- The fake engine writes nothing after a flag until it reads that flag's commit on a FIFO the suite writes as the
  commit returns, so "still running" is an event, not the 5 seconds it used to print after its last flag.
- The measured latencies are printed and kept as data, never judged; a latency requirement belongs to
  VELDO-0358's paired A/B performance stage.
- Falsifier `flag231-delivered-at-end` (deliver only in `saw_end`): through the mutation driver with its baseline
  and no-op, `AC1/at-once` red on the mutant only (`fix1-mutations.txt`). At 81e610e3 the fake engine waited for
  the missing commit until its 120 s hang detector, past the driver's 120 s worker floor; since 3c775bda the
  suite writes 'n' on the engine's FIFO when the cycle that took a flag ends without its commit, so the engine
  goes on at once and the defect is read by event order (65 s for the whole stage).

### The chain's waits (F2): each converted site

Shared fixture `scripts/suites/support/v231_fake_engines.py`: `HANG_SECONDS = 120`; `drive` and the new
`eventually` refuse a bound under it (`fix1-load-rule-guard.txt`); `quiesce` forces the loop's next pass and
drives every run it starts to its pipe's end, the event that replaces "pause, then assert nothing moved".
Positive waits below wait for their condition and keep only the 120 s hang detector.

| Site (review section 7) | Was | Now waits for |
| --- | --- | --- |
| 127 :73 `stop_all` | `drive(..., 20)` | every launch ended (pipe EOF), hang 120 |
| 127 :109 `turn` | 40 s | the turn's `ended` row, hang 120 (AC1's turn 360: the engine's own ack hang is 120) |
| 127 :139 `max(latencies) < 2` | wall-clock verdict | removed; event order (F3) |
| 127 fake `after: 5` | 5 s "still running" window | the engine waits on the commit FIFO; `after: 1` is only run length |
| 127 :245 `Q.PROBE_SECONDS = 4` | 4 s probe deadline | 120 hang; the never-answering probe binary exits without the call's output (process exit) |
| 127 :332 blocking engine, `seconds=15` | 15 s | the receiver's stop (`configuration_stop:wait_question`), hang 120; the 2 s question window is the receiver setting under test |
| 127 answered question | separate writes vs the 2 s window | the question, its answer and the next line in one write: the receiver reads "wrote on after its question" in one read |
| 127 :349 flood, `seconds=90` | 90 s; service clock = wall | hang 120; service clock frozen through the flood, so 500 flags fall in one rate window at any speed |
| 127 :408 `L.Flags(..., 2)` | 2 s window in a unit read | the receiver's default window (the read never consults it) |
| `support/v231_fake_engines.py:126` probe urlopen | 30 | 120 hang |
| 128 :63 git | 30 | process exit, hang 120 |
| 128 :109, :142 (fake engine) urlopen, MCP listing | 10 | 120 hang |
| 128 :380, :526, :684 `J.eventually` | 30 | `F.eventually`, the marker condition, hang 120 |
| 128 :391, :462, :528, :686 `F.drive` | 30, 40 | the turns' `ended` rows, hang 120 |
| 128 :744 `systemctl stop` | 30 | process exit, hang 120 |
| 129_0177 :119, :127 sqlite | busy 10 | lock released, busy hang 120 |
| 130_0176 :323 `run_turn` and callers, :349, :352, :500, :528, :558, :565, :630 | 20 to 60 | rows and markers, hang 120 |
| 130_0176 :539 `drive(lambda: False, 2)` then "nothing moves" | 2 s pause | `F.quiesce`: next pass forced, every run it starts ended; the row also requires the loop went quiet |
| 130_0176 :545 `drive(lambda: False, 1)` then "his wait leaves the turn waiting" | 1 s pause | `F.quiesce` after the pass his answer woke |
| 130_0183 :204 (fake) `proc.wait(10)`, :811 `holder.wait(10)` | 10 | process exit, hang 120 |
| 130_0183 :784 `communicate(timeout=20)` | 20 s, then "not refused" | the start's pidfd (refused: exits) or its `READY=1` on a NOTIFY_SOCKET of the suite's (serves), hang 120 |
| 130_0183 :292, :1017 sqlite | busy 30 | busy hang 120 |
| 131_0175 :275 `settle` and callers | 60 | turn `ended` row, hang 120 |
| 131_0184 :291 `turns`, :681 | 40, 20 | rows / launches ended, hang 120 |
| 132_0175 :248 `runner.wait` | 30 | the run's end, hang 120 |
| 133_0178 :207, :212 ssh-keygen | 10 | process exit, hang 120 |
| 133_0178 :440, :485 drive | 60 | rows and markers, hang 120 |
| 133_0178 :447, :454 `lines_until` | 20 s of 0.2 s pauses | re-read after each loop step until the line is served, hang 120 |
| 133_0178 :486 `drive(lambda: False, .5)` then drain hints | 0.5 s pause | the receiver's ended hint for the dispatch on the suite's hint socket; stream reads (:468, :491) wait on the stream's condition, hang 120 |
| 136_0180 :280 `settle` | 60 | turn `ended` row, hang 120 |
| 137_0181 :267 `drive` and :307, :391, :444, :460 | 60, 90 | rows, hang 120 |
| 137_0181 :356 three passes with `sleep(0.2)` then "passes run nothing" | pauses | three `F.quiesce`, each required quiet |
| 138_0187 :336 `run_turn`, :521, :525, :526, :700 | 10 to 40 | rows, markers and the capture row, hang 120 |
| `proof/VELDO-0187/fixtures.py:263` `proc.wait(10)` | 10 | exit, hang 120 |
| `proof/VELDO-0183/fixtures.py:117` sqlite | busy 60 | busy hang 120 |
| `proof/VELDO-0127/loopback.py:54` `capture(timeout=45)` | 45 | binary's exit, hang 120 (callers that pass their own bound keep it) |

Not converted, and why:
- Production bounds the review lists (`IMMEDIATE_SECONDS = 5` (F6), `qualify.PROBE_SECONDS = 45`,
  `control_launch.QUESTION_WINDOW_SECONDS = 60`, `project_runner_macos_os.Native.check_clone` `timeout=5`): they
  are behavior that specifications state, not suite waits; out of this round.
- `proof/VELDO-0124/native_checks.py` (Mac-native driver, not run on Linux), as the review says.
- Found while converting, not in the review's list, left as they are: 133_0178 `frames_of` and the drain before it
  (:646, :653) collect event-stream frames until a 0.1 or 0.5 s idle, so the colleague's "no event" rests on a
  pause; the fake engines' `keep(seconds)` and flag `interval` pace what a fake writes, never what a row judges.

### Small items

- F7: the `conversation_clone` entry of `scripts/check_space_boundary.py` now says the folder removed is the one
  this call created, and that no ref is deleted (the commit is fetched into no ref). The optional `os.mkdir`
  against the check-then-init race is not made: it is a production change the brief did not ask for.
- F8: the reasons of `129_veldo_0177_assistant_setup` and `130_veldo_0183_memory_servers` in
  `scripts/gate_unconfined.json` now say what needs the host, as the precedents do: factory setup's profile check
  reads the owner's user manager (`systemctl --user show`); VELDO-0171's fixture starts the units itself.
- F9: suite 79's comment says `flag_means` is covered only by suite 126's whole-record comparison.

### Runs and falsifiers (`fix1-suites.txt`, `fix1-mutations.txt`, `fix1-load-rule-guard.txt`)

Each touched suite was run alone through the builders' host_heavy wrapper: 127, 128_0177, 129_0177, 130_0176,
130_0183, 131_0175, 131_0184, 132_0175, 133_0178, 136_0180, 137_0181, 138_0187, 79_0061, 155_0304 (space
boundary), and 126_0230, 86_0127, 101_0208 for the loopback fixture and the unconfined list. All pass with 0
failed except 86_0127's two live rows (F4). Load at the runs' ends ranged from 6 to 60 (132 to 138 ran at 30 to
60): the event waits held.

Falsifiers of the rows whose waits changed:
- `flag231-delivered-at-end` (AC1/at-once), `flag231-run-window-removed` (AC4/flood, now on a frozen service
  clock), `ask176-moved-unasked` (AC2/ask, now after `F.quiesce`): killed by the mutation driver with clean
  baseline and no-op.
- `flag231-question-window-dropped` (AC3/blocking) and `store183-open-unchecked` (AC4/open-refused, now on pidfd
  and READY=1): applied in place to a scratch copy, red on exactly their rows. Through the driver neither
  completes, and the lead should know why:
  - AC3/blocking's defect is a receiver timer that never fires. "Never" has no event, so the suite reads it at
    its 120 s hang detector; the driver's worker floor is also 120 s, so the mutant worker is cut off
    (`worker_cancelled`). Under the load rule this mutant needs a driver deadline above the suite's hang bound,
    or a receiver event that shows its question window passed; neither is in this round.
  - store183's baseline is red on every row in the driver's confined leg (the suite needs the host, which is why
    it is in `gate_unconfined.json`): `invalid_baseline`, independent of this change.

Not run: `scripts/verify.sh` (by instruction) and the suites this round did not touch.
