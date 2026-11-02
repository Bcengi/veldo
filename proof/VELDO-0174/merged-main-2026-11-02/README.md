# VELDO-0174 on main 646b2d68, 2026-11-02

Focused evidence, not a gate stamp, a review verdict or a landing decision. The full gate was not
run here (the lead runs it). Every suite below ran alone under the host gate lock
(`flock /home/dmitry/.local/state/core-gates/.gate.lock python3 scripts/selftest.py --suite NAME`,
or several in one hold of that lock, serially). Logs: logs/.

## Merge (c81eebf4)

The lead started the merge of main 646b2d68; the five conflicts were resolved here.

- engine/.veldo/control_service.py and its .veldo copy (byte-identical after, as on main).
  FactoryLoop.__init__: main's VELDO-0188 code is kept whole (work_roles, line_counts,
  refused_lines, `follow_store(0)`); main had dropped the VELDO-0143 `add_line` loop, so it is not
  restored. 0174 adds its conversation Line (built whenever the installation names the
  `conversations` receiver, work or none) and the `conversation_offered` count, before
  `follow_store(0)`. FactoryLoop.run: main's journal-woken `follow_store` runs first (it makes lines
  and offers no work), then 0174's waiting turns, then the project lines, so turns still go before
  project stations.
- proof/VELDO-0127/claude-live.json: main's version.
- scripts/suites/manifest.json: main's entries 113 to 122 kept, 0174's appended.
- scripts/suites/requires.json: `python3 scripts/run_scope.py --emit-requires`.
  scripts/check_generated.sh and `.veldo/validate.py all` pass.

## Failure found and fixed (f50f7848)

On the merged tree suite 107 failed 23 rows (logs/before-fix/s107.log): main's follow_store reads
`service.watermark()`, absent from the journey's service stand-in. With it added, two rows stayed
red (AC3/turn-before-project, AC4/unit-to-conversation): follow_store closes a line whose project
is open but whose repository the instance does not serve or whose project has no team, so the
priority fixture's hand-built project line was removed. The stand-in now serves that repository
over the fixture's receiver configuration, the project has its own team naming the line's builder
and reviewer, the line's roles come from `line_roles`, and the stand-in stops serving the
repository when the journey ends. No production module and no assertion changed.
Afterwards: 64 passed, 0 failed (logs/after-fix/s107.log).

## Renumbering and anchors (d5f72fb6)

Main's 107 is VELDO-0153's suite, so 0174's is now 123_veldo_0174_conversations (main ends at
122): file, manifest, requires (regenerated), the S174 constant in check_teeth_mutations.py and
run_falsifier.py. It is not in scripts/gate_unconfined.json, so suite 101's whole-suite list and its
count of 42 are unchanged, and its declared-list row passes.

Anchor scan (every `c` in `m.cases()`: `c['old']` once in its module, suite file present, and
every `also` anchor applies through `m.mutate`): 2775 cases, 0 bad. Before the fix 9 were bad, the
same 9 already on 3e898da2 and none on main: cases of VELDO-0069, VELDO-0039 dispatch, retirement,
VELDO-0186 and VELDO-0204 whose anchors 0174's own code duplicated (the conversation receiver,
`prepare_conversation`, ConversationLine.activate) or rewrote (`_authorize` with subject kind, the summed
caps, `open_loop` with optional work, the receiver's `receiver_kind`). Each now anchors once and
keeps its original defect.

## Suites, each alone

- 123_veldo_0174_conversations: 64 passed, 0 failed, 9.54 s alone.
- 105_veldo_0182_memory: 152 passed, 1 failed (switch/retry-rechecks), 76.39 s alone.
- 86_veldo_0127_agent_configuration: 51 passed, 2 failed (live/claude, live/codex), 37.90 s alone.
- 96_veldo_0204_reservation_policies: 46 passed, 0 failed, 15.99 s alone.
- 66_veldo_0047_authority: 56 passed, 0 failed, 11.20 s alone.
- 86_veldo_0186_setup_assets: 37 passed, 0 failed, 14.71 s alone.
- 62_veldo_0039_dispatch: 51 passed, 0 failed, 9.20 s alone.
- 67_veldo_0041_heartbeat: 49 passed, 0 failed, 11.24 s alone.
- 101_veldo_0208_landing_reuse: 214 passed, 2 failed (sandbox/unavailable-refuses-before-exec, sandbox/old-abi-refuses-before-exec), 233.69 s alone.

On main 646b2d68, in a temporary worktree, same lock: suite 101 fails the same two sandbox rows
(214 passed, 234.40 s), so they are not this branch's; suite 105 passed 153 of 153 (78.21 s).
See "Open" for 105.

0174's suite is 9.5 s alone, well under the 45 s VELDO-0215 bound, so it was not split. Suites 105
(76 s) and 101 (234 s) are over 45 s alone but are VELDO-0182's and VELDO-0208's, outside this
ticket's footprint, and equally long on main; they were not split here.

Suite set: 0174's own suite, the suites of the nine re-anchored cases (62, 66, 67, 86_0186, 96),
suite 86_0127 (live captures over 0174's launch change), 105 (prior rounds) and 101 (counts the
manifest). The wider closure of suites that load control_service.py, control_launch.py or
init_scaffold.py (about 90) was not run; the gate covers it.

## Mutants, by hand

Each applied, its suite run, a named row confirmed red, the source restored (logs/mutants):

- handmut.py, 0174's eight teeth cases on suite 123: all RED on their rows
  (AC1/project-scope, AC1/project-owner, AC1/restart-open, AC2/one-offer-per-pass,
  AC3/turn-before-project, AC4/no-work-line, proof/mutation-dependencies,
  proof/signed-command-module).
- run_falsifier.py: v174-ignore-record-version (AC1/versioned-mutations), v174-drop-skills
  (AC2/role-skills), v174-record-memory-only (AC1/restart-open and AC1/durable-store): each exit 1,
  targets red, source restored.
- handmut.py, the nine re-anchored cases on their own suites: all RED on their rows.
- Restored suite 123 afterwards: 64 passed, 0 failed (9.47 s); `git status` clean.

## Validator and policy

`python3 .veldo/validate.py ready specs/VELDO-0174-conversation-record-and-turns.md`: exit 0.
`python3 .veldo/policy_check.py`: exit 0. No protected path is touched against main (../OPEN.md).

## Open

- Suite 86 live/claude and live/codex need fresh live captures on owner accounts (../OPEN.md).
- Suite 105 switch/retry-rechecks failed once on the branch and passed on main. The row exercises
  control_factory_setup_memory, control_memory and control_memory_check, none of which this
  branch changes. A rerun on the branch could not get the gate lock within 2 h; see OPEN.md for
  its result.
