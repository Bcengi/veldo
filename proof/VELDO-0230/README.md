# VELDO-0230 proof: upgrading an agent CLI is one command

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0230.

## What changed (first round)

- `.veldo/qualify.py` (mirrored in engine/.veldo): the one command. It writes the engines record
  (runtime/engines.json) to every runtime copy, runs every reader of the binaries in write mode, writes the Codex
  record (control_engine_codex.qualification, model tool modes from the bundled catalog) and the Claude Code
  record (its own writer), and regenerates the VELDO-0127 fixtures.
- Engine modules, suites, fixtures, mutations and extractors read the engines record or the generated files;
  suite 125 (the census) and suite 126 (the command reproduces the shipped files) are the gate rows.

## Fix round 1 (review-2026-11-03.md, HAS DEFECTS)

1. AC2: the command also runs proof/VELDO-0156/render_offline.py and capture_mentions.py (codex-rendered.json,
   codex-mentions.json). Suite 81 baseline/qualified requires all three VELDO-0156 captures to carry the engines
   record's Codex digest, so a stale capture fails by name. capture_mentions takes an ephemeral loopback port.
2. AC1: suite 86's fake Claude Code builds its built-in plugins and skills from the record (`engine_plugins`,
   `engine_skills`) and its bundled skills from the VELDO-0155 table.
3. AC1: model names come from the catalog fixture: delivery_fixture's support expectation is the catalog's
   experimental list; suites 86, 88, 89, 90, the factory, resource_probe, served_scenario, the VELDO-0174 journey
   and the mutation rows name no model. The census now names a single catalog model name and the qualified
   Claude Code's built-in settings (a plugin name; a tuple of two built-in names), and governs the suites'
   support modules (it found the VELDO-0174 journey's literal versions, now read from the engines record).
   Rows census/planted-model and census/planted-builtin, mutants census230-model-unread and
   census230-builtin-unread.
4. Suite 126 qualify/covers checks the engines record and both qualification records in both runtimes, the
   VELDO-0127 fixtures, and its own list of every reader's table; mutant qualify230-claude-record-unwritten reds it.
5. Each record lists what a qualify run found new (`new_capabilities`, with its decision); the output lists each
   item and a count per decision. The docstring names `unclassified_default_on`.
6. AC3 amended (Telegram 38878): new capabilities are evaluated and used if useful. The evaluation is
   runtime/capability-decisions.json (with the written rules it cites) and new-capabilities-0.166-2.1.317.md.
   A granted Codex feature stays on at launch (suite 88 defaults/unknown, mutant qualify230-granted-feature-off);
   the MCP resource readers a binary offers with no server are recorded by qualify from its loopback capture
   (`offered_without_server`) and accepted on the wire, never granted; a grant the binary does not deliver under
   Veldo's switches (0.166.0: request_user_input_async) is probed, recorded (`undelivered_grants`) and left out,
   and the launch proceeds; the 2.1.317 credential and environment names are decided (extractor exceptions for the
   kept and setting names, the module's strip and setting lists for the rest).

## Fix round 2: the Claude Code stream reader's tables follow the qualified binary (AC2)

The defect (round 1's first Open item, AC2's falsifier "after qualifying a newer installed binary, any gate row still
comparing against the old version"): MESSAGES, TOOL_FREE_FRAMES, TOOL_FIELDS, NESTED, IN_RUN_TOOLS (and IN_RUN) and
IN_RUN_HOST were module literals equal to 2.1.281's, so suite 78_0160 format/tool-forms and decision/outward-tool-asks
stayed red after qualifying 2.1.317.

- `.veldo/qualify.py` (`stream_forms`) writes the reader's tables into the qualified version's Claude Code record
  (`stream_forms` in runtime/claude-qualification.json, both runtime copies), from the binary's own
  (proof/VELDO-0062/cli-formats.json tool_forms). A message, tool-free frame or tool-naming field the replaced record
  gave the reader keeps its reading; a new one is read by its decision in runtime/capability-decisions.json (claude_code
  `messages`, `frames`, `tool_fields`, `routing`) and listed in `new_capabilities` and the output. With no decision
  granting it a new message or frame is left out (an unknown call, never tool-free) and a field is `ask` (any value it
  holds is an unknown call, `field:<message>:<path>`). The nested-work and in-run tables are the binary's own; a
  `_host` routing switch (2.1.317: CLAUDE_CODE_REMOTE_TOOLS_FORWARD) is listed with its decision (off, VELDO-0160 AC3;
  the module already strips it).
- `.veldo/control_engine_claude.py` reads them from the record beside it (`stream_tables`, re-read when the record's
  bytes change; the module names resolve to them); a record without them refuses the reading by name
  (missing_evidence:engine_stream_forms). The seed: the 2.1.281 tables are the module's former literals, written once
  into the record; qualify then generates them identically (fix2-ac2a-qualify-output.txt).
- Decisions added for 2.1.317's forms (the evaluation file, section "Claude Code 2.1.317 stream forms"): the 14
  messages, `system/session_metadata`, the round-1 fields and three more the extractor lists
  (`system/permission_check_status tool_use_id`, `user tool_result_meta.built_in_tool`, `user tool_states`; all free),
  and the routing switch.
- Suite 78_0160: format/tool-forms compares the reader's tables with the qualified binary's, less what the record lists
  as not granted; the `call` fields and the allowlist are the lead's, as far as the binary has them (2.1.317 has no
  REPL); the remote-tools gate is off when compiled off or behind a switch the module strips; the two REPL fixtures
  apply only where the binary's tables list the REPL forms (on 2.1.317 the REPL call asks by rule A, named beside).
- Mutation anchors moved to the reader's table loader: decision-claude-control-request-free,
  format-claude-tool-field-unlisted, remote-trigger-not-outside, outward-sendmessage-allowlisted, nested-repl-dropped
  (its `also`). Each is killed by its rows on 2.1.281 and on 2.1.317, baseline and no-op green (fix2-mutations.txt).

Results:

1. On the qualified binaries (Codex 0.154.0, Claude Code 2.1.281) `python3 .veldo/qualify.py` in the worktree at
   0a7bf55b left every file byte-identical (git status clean; fix2-ac2a-qualify-output.txt). The VELDO-0127 fixtures
   were regenerated once before that (15501e77): they bind the reader module's digest.
2. In a scratch git worktree at 0a7bf55b, `qualify --claude 2.1.317`: 71 Claude Code items (53 granted, 7 not
   applicable, 11 off), none unevaluated (fix2-ac2b-qualify-output.txt); there suites 78_0160 (34 of 34), 125 and 126
   pass, and 78_0160 passes on the shipped 2.1.281 files too (fix2-suites.txt).
3. Suites 75, 79, 81, 86 offline rows, 88, 89, 90, 125 and 126 pass in the worktree, and so do the other suites that
   load the reader module (fix2-suites.txt). 86 live/claude and live/codex are stale: the live captures bind the
   digest of control_engine_claude.py, which this round edits; the lead retakes them.
4. A form with no decision (fix2-unevaluated.txt): with three decisions removed, qualify lists each as unevaluated, the
   frame is not tool-free, the message not known and the field `ask`; the reader names each an unknown call.

Not changed: RESPONSE_BLOCKS, REQUEST_BLOCKS, STREAM_EVENTS, BUILTIN_TOOLS, BUILTIN_RENAMED, TASK_COUNTS, NESTED_TOOLS,
IN_RUN_ALIASES, IN_RUN_AGENT, IN_RUN_SKILL and IN_RUN_TASKS are still module literals, equal in 2.1.281 and 2.1.317;
a later binary that changes one of them reds format/tool-forms until it follows the same path.

## Fix round 3: incremental_tools granted, the wire comparison reads every request of a run

Owner direction (Telegram 38895-38896, 2026-11-04): Codex 0.166's `incremental_tools` is useful (later requests carry
only the tools that changed); it was off only because VELDO-0127 AC4's comparison was taken to read a run's first
request. AC3: granted, and the comparison made complete. AC4's text is unchanged.

The format, from the binary and a loopback capture (`fix3_incremental.py`, `fix3-incremental-capture.json`, Codex
0.166.0, a Code Mode model, two turns of one session): an incremental update is a developer message ("This is an
incremental tools update. Previously declared tools remain available for direct calls unless explicitly marked
unavailable. If a tool is redefined here, its latest definition replaces the earlier one.") followed by a new
`additional_tools` input item holding only what changed (here the runner `exec` redeclared with goals' tools); the
first declaration stays in the history. A removal is a redeclaration with fewer nested tools. With the feature off
the later request carries one full replacement item instead. A direct model redeclares its full top-level `tools`
either way. A tool search's `tool_search_output` (the same capture, direct model) also declares definitions mid-run.

Changed:
- control_agent_config_handoff.py (both copies): `codex_run_tools(bodies)` is the tools declared at each request of a
  run, the union of that request's declarations and every earlier one's (a later request declaring nothing keeps the
  set; an unreadable one, an empty run or a first request declaring nothing is refused by name).
  `codex_run_tool_difference(bodies, wanted)` refuses `codex_unexpected_tool` wherever an unlisted tool is first
  declared, else `codex_missing_tool`; `codex_tool_difference(body)` is a run of one request. A request's declarations
  now include `tool_search_output` (DECLARING_ITEMS). The launch check (`codex_check_launch`) compares the run of its
  observed requests; its endpoint keeps each request's tools and declaring items only (`codex_declarations`).
- proof/VELDO-0127/evidence.py: `wire_observations(bodies)` (each request with what the run declared by then;
  `wire_observation` is a run of one), used by `problems`, qualify, live.py and loopback.py. Suite 90 compares the
  run of every captured request, not its first.
- runtime/capability-decisions.json (both copies): `incremental_tools` granted with its reason; it stays on at launch
  (not written into the features table). The evaluation file's row and its rule list are updated.

What this does not change, stated plainly: the production launch check observes the worker on a loopback endpoint
that refuses the first request, so it sees one request, as before; the real run's later requests go to the provider
and are not on a wire Veldo reads, with the feature on or off (a tool set that changes mid-run reaches the model in
both modes; only the spelling differs). The comparison is complete for every request it is given: the launch
observation, the live and loopback captures, qualify's captures and the suites. Before this round each request of a
capture was compared alone with every declaring item in its history, so a full-history update adding an unlisted tool
was already refused there; what was missed was a tool search result, a request carrying only its new items, and suite
90's first-request read.

Results:

1. Red before, green after (`fix3-red-at-fafc91e4.txt`): suite 86's new row wire/later-requests, on the modules at
   fafc91e4, fails for an unlisted tool search result (both models), an unlisted update or search result in a request
   carrying only its new items, a partial within-role update carrying only its new items (refused there as missing),
   a request with nothing new, and an empty run; at this round's commits it passes, with the full-history unlisted
   update, the within-role updates, and the launch check over the same runs (`fix3-suites.txt`).
2. AC2 (a): `qualify --codex <0.154.0> --claude 2.1.281` left every file byte-identical (`fix3-ac2a-qualify-output.txt`)
   after the VELDO-0127 fixtures were regenerated once (3ff6de4f; they bind the handoff module's digest, observations
   unchanged).
3. AC2 (b), scratch worktree, `qualify --codex <0.166.0> --claude 2.1.317` (`fix3-ac2b-qualify-output.txt`): 66 Codex
   items, 7 granted (incremental_tools among them), 55 not applicable, 4 off; incremental_tools is left at its default,
   on. There suites 86 offline rows, 87_0127, 90 and 126 pass.
4. Suites 75, 79, 81, 86 offline rows, 87_0127, 88, 89, 90, 125 and 126 pass in the worktree (`fix3-suites.txt`).
5. Mutants (`fix3_mutants.py`, `fix3-mutations.txt`): five new anchors (role127-run-each-request-alone,
   -run-first-request-only, -search-result-unread, -launch-first-observation-only, -evidence-each-request-alone) and
   the five whose code moved (role127-wire-extra-ignored, -wire-missing-ignored, -owner-tools-hidden,
   -code-mode-hides-missing-grants, -delivery-comparison-skipped) are each killed by their rows, baseline and no-op
   green.

## Fix round 4: gate reds at c62fae13 (log veldo-gate-0230d)

1. Unit, confined leg: suite 123 failed 5 rows. Its fake Codex record (`scripts/suites/support/v174_journey.py`
   `engines`) took `qualification()` without a catalog (`model_tool_modes: {}`) and then added a catalog by hand,
   so `qualified_baseline` refused it (`missing_evidence:codex_model_tool_modes`) because `{}` did not match
   `catalog_modes(catalog)`. The fault was in the fixture, not in production. The fixture now derives the modes with
   `catalog_modes` (300cb48e). The same pattern of modes set apart from their catalog: the VELDO-0186 and VELDO-0162
   fake records copied the shipped modes without the catalog, a shape qualify never writes. They now carry the shipped
   catalog with its digest and derive the modes from it. `proof/VELDO-0127/loopback.py` used its own comprehension
   and now calls `catalog_modes` (4e7be56e). No other hand-written `model_tool_modes` remains.
2. Integration, confined leg (first use, 1800s floor): this is a consequence of item 1 and nothing was changed for
   it. `gate_legs.py` records a unit leg's time only when the leg passes. The leg-time store of this checkout
   (`~/.cache/veldo/gate-leg-seconds`, authority veldo-0230, declaration dbcab869) holds the unconfined leg alone,
   because the confined unit leg has not passed here, so `check_first_use.py` fell back to its floor. The nested
   confined run needs about 2300-2450s: in gate log 0174e the unit confined leg also failed, but an earlier passing
   measurement was handed (budget 4176s), and the run passed in 2454s. In 0174d and 0174f it took 2284s and 2450s.
   Once the unit confined leg passes, its time (about 2530s) is handed in the same gate run, which gives a budget of
   about 5000s.
3. Mutation, `role127-model-modes-omitted`: the case runs in the unconfined leg. Under the mutant the qualified modes
   are empty, so suite 86's call to `live.codex_model(DIRECT_MODEL, ...)` raised the lead driver's `SystemExit`
   ("A qualified codex-model is required"). That call sat outside any `try` (`attempt` catches `Exception` only), so
   the worker exited 1 after `review/codex-mode` had already failed. On main the lookup read a module table that the
   mutant did not touch. The call now catches `SystemExit` like its sibling calls (6da06727). The mutant is killed:
   baseline and no-op are green, and `review/codex-mode` is among its failed rows (`fix4-mutation.txt`, before and
   after through `check_gate_mutations.py --case`).

Results (`fix4-suites.txt`): suite 123 was red at the old fixture (the same 5 rows and the same refusal) and passes
38 of 38 after the fix. Suite 86 passes 28 of 28. The users of the changed fixtures (86_0186, 73, 85_0171, 103, 106,
95, 87_0170, 74, 86_0189, 94, 71, 119) all pass. The full gate was not run in this round.

## AC2 runs

(a) Qualified binaries (Codex 0.154.0 global, Claude Code 2.1.281 copy): `python3 .veldo/qualify.py --codex
<global vendor binary> --claude 2.1.281` in the worktree at the final commit left every generated file
byte-identical (`ac2a-qualify-output.txt`; git status showed only that output file). Suite 126 repeats this in
scratch on every gate run.

(b) Codex 0.166.0 (npm install --prefix .scratch-0230/codex-0.166.0 under this worktree; the global install
untouched) and Claude Code 2.1.317, in a scratch git worktree: one command qualified both (`ac2b-qualify-output.txt`,
`ac2b-engines.json`): 66 Codex items (6 granted, 55 not applicable, 5 off) and 31 Claude Code items (14 granted,
7 not applicable, 10 off), none unevaluated. Suites (`ac2b-suites.txt`): 75, 79, 81, 82_0165, 82_0173, 85_0158,
85_0171, 86 offline rows, 87_0127, 87_0170, 88, 89, 90, 125 and 126 pass; the eight adapter-pin mutants are each
killed by their row with a clean baseline (`ac2b-pin-mutations.txt`, run through the VELDO-0060 and VELDO-0061
drivers, since the mutation checker's confined leg is denied /run/user on this host). The feature probe is
`ac2b-feature-probe.json`.

## Open

- Suite 86 live/claude and live/codex: the live captures bind digests of the production modules this change
  edits; by this repository's practice the lead retakes them on real accounts (live.py is lead-only).
- Environment names reach the module's strip and setting lists by a code edit. A new name in one of a later
  binary's strip lists is listed as unevaluated by the command, but outside the stripped families (ANTHROPIC_,
  CLAUDE, CODEX_, OPENAI_) it is not stripped until that edit is made, and suite 75 goes red until then.
