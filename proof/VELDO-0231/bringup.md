# VELDO-0231 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: VELDO-0231 is built and comes over first, with its
specification (it lived only on its branch). Source branch: `agent/claude/veldo-0231` at 3c8603b0. New
base: the line at c92969a0. The ticket's commits, oldest first, were brought over as one change (the
branch is 563 commits behind the line, so its diff was ported, not replayed commit by commit):

- d186ec93 VELDO-0231: spec, a running agent flags the lead at once without stopping
- bb42d4f8 flags read by the receiver, delivered by the service through flag_conversation, rate limited per run; the question window
- 06a9e634 the loopback capture can answer with one model call; the role fixture carries the shipped flag means
- d744807e suite 127 (run flags) over fake engines, registered
- 6d4e711f the four spec falsifiers registered as mutation cases (finding 231)
- 77d4306d suite 127 flood row tolerates a refused run
- 958f1b2e the VELDO-0127 delivery fixture expects a flag grant the qualified binary does not hold refused at save
- b1efc805 proof
- 62ae0d48 lead amends AC4 and adds suite 78 to the footprint
- ffca338d independent review, SOUND
- bb58cfa4 the flag probe records the bound the binary answered within, never the measured time
- c45f89df shipped files regenerated with the one qualify command
- 3c8603b0 proof, fix round 1 (qualify reproduces)

## What changed in the port

- `.veldo/control_launch.py`: the receiver's `flags` list beside the line's VELDO-0350 fields
  (`returncode`, `closed`, `receiver_log`). `.veldo/control_service.py`: the loop's clock and flag counts
  beside VELDO-0260's `trees`. `.veldo/qualify.py`: the flag probe beside VELDO-0259's `home_as_tilde`.
  Each conflict kept both sides. The engine copies are the same bytes.
- `proof/VELDO-0127/delivery_fixture.py`: the line's case-by-case form (VELDO-0261) is kept, and the
  one clause this ticket adds (a flag grant the qualified binary does not hold is refused at save) is
  put into its `tool_case`.
- `scripts/suites/manifest.json` and `requires.json`: the line's entries are kept and the row for
  `127_veldo_0231_run_flags` is added (`requires.json` by its generator). `specs/index.md` by
  `scripts/update_index.py`.
- Generated records, not merged by hand: `runtime/codex-qualification.json` (both copies) and the
  four `proof/VELDO-0127/resources-*.json` fixtures were written again by
  `python3 .veldo/qualify.py --codex <binary> --claude <binary>` on the engines record's binaries
  (Codex 0.166.0, Claude Code 2.1.317), as fe9eb598 did. The command starts both engines against a
  loopback capture; no model was called and no account was used. Suite 126 (qualify reproduces)
  passes after it.
- All 3609 registered mutants still anchor once in their modules.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone:

| Suite | Result |
| --- | --- |
| 127_veldo_0231_run_flags | 17 passed |
| 86_veldo_0127_agent_configuration | 26 passed, 2 failed: `live/claude`, `live/codex` |
| 123_veldo_0174_conversations | 38 passed |
| 87_veldo_0127_codex_delivery | 194 passed |
| 125_veldo_0230_engine_census | 8 passed |
| 126_veldo_0230_qualify_reproduces | 4 passed |
| 82_veldo_0173_tool_registry | 11 passed |
| 88_veldo_0127_feature_defaults | 25 passed |
| 90_veldo_0127_feature_profile | 2 passed |
| 78_veldo_0160_account_pool | 34 passed |
| 106_veldo_0185_dispatch_setup | 20 passed |
| 113_veldo_0117_domain_store | 3 passed |

Suite 86's two red rows are the ticket's own open item 4 (OPEN.md): the live captures are stale once
the handoff and engine modules change, and they are retaken on real accounts by the lead. They were
red on the source branch too (`suites.txt`). Nothing in the bring-up can turn them green.

Falsifiers (`bringup-2026-11-21/falsifiers.txt`, `python3 proof/VELDO-0231/falsify.py`): each of the
four applied to the checkout's module turns its named row red and the module is restored byte for
byte: delivered-at-end (AC1/at-once), question-unmapped (AC2/codex-launch and five more),
question-window-dropped (AC3/blocking), run-window-removed (AC4/flood, AC4/per-run-cap).

Mutation cases, each alone through `scripts/check_teeth_mutations.py`
(`bringup-2026-11-21/mutations.txt`): all four are killed with baseline and no-op green.
`flag231-question-unmapped` took three runs: the first was `invalid_baseline` (next section), the
second was void because the bring-up wrote into the checkout while it ran (`inputs changed during
stage`), the third, in an untouched clone of the same commit, passed.

## Needs the lead

- `AC1/at-once` is a timing assertion the specification owns: ten flags, each committed within 2
  seconds of the engine writing it. On this host at load 20 it failed in the baseline and the no-op
  of one mutation run (two suite runs side by side), which makes that run `invalid_baseline`. It
  passed in every suite run alone (latencies 0.007 to 0.023 s). The bound was not touched: under the
  load rule a 2 second bound on a loaded host is the specification's to restate, not the bring-up's.
- Suite 86 `live/claude` and `live/codex`: live captures to retake (above).
- The ticket is `risk: high`, `human_approval: required`. Its review of 2026-11-04 was of the
  source branch; the port's conflict resolutions above have had no review.
- `proof/VELDO-0231/suites.txt`, `falsifiers.txt`, `red-at-8da5d061.txt` and the
  `mutation-flag231-*.txt` files are the source branch's runs and name its commits.
