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

- Suite 78_0160 format/tool-forms and decision/outward-tool-asks stay red on 2.1.317 (green on 2.1.281): the
  Claude Code stream reader's tables are module literals equal to 2.1.281's, pinned by mutation anchors, and the
  rows require them equal to the installed binary's. The new forms are evaluated (the evaluation file); making
  the tables follow the qualified binary is its own change.
- Suite 86 live/claude and live/codex: the live captures bind digests of the production modules this change
  edits; by this repository's practice the lead retakes them on real accounts (live.py is lead-only).
- Environment names reach the module's strip and setting lists by a code edit. A new name in one of a later
  binary's strip lists is listed as unevaluated by the command, but outside the stripped families (ANTHROPIC_,
  CLAUDE, CODEX_, OPENAI_) it is not stripped until that edit is made, and suite 75 goes red until then.
