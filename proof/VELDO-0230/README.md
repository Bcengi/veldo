# VELDO-0230 proof: upgrading an agent CLI is one command

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0230.

## What changed

- `.veldo/qualify.py` (mirrored in engine/.veldo): the one command. It writes the engines record
  (runtime/engines.json: the qualified Codex and Claude Code version, binary path and digest) to every runtime
  copy, runs the nine extractors in write mode, writes the Codex record (control_engine_codex.qualification,
  model tool modes from the bundled catalog) and the Claude Code record (a new writer: the extracted tables,
  the engine's baseline, and the built-in plugins and skills read from one offline init probe), and
  regenerates the VELDO-0127 fixtures (catalog, features listing, loopback resource captures, normalized so
  the same binary writes the same bytes). It prints the unclassified default-on Codex features it turned off
  and the Claude Code tools the replaced classification did not hold.
- Engine modules: no MODEL_TOOL_MODES table (the record's catalog decides); no Claude built-in plugin or skill
  list (the record's `engine_plugins`, `engine_skills`); the Codex feature classification is module policy and
  an unknown feature is off instead of refusing the launch (`unclassified_default_on` in the record); the
  Claude window names come from the record (`limit_names`); the Codex usage-limit match accepts either
  apostrophe; factory setup takes the Claude Code copy the engines record names, never PATH.
- Suites, fixtures, mutations and extractors read the engines record or the generated files. The extractors
  read both binary pairs (identifier-agnostic anchors; real changes read as the new binary has them).
- Gate rows: suite 125 (census of agent literals, a newer Claude tool, setup and the engines record), suite 126
  (the command reproduces the shipped files), suite 88 defaults/unknown now proves AC3 for Codex.

## AC2 runs

(a) Qualified binaries (Codex 0.154.0 global, Claude Code ~/.local/share/claude/versions/2.1.281):
`python3 .veldo/qualify.py --codex <global vendor binary> --claude 2.1.281` in the worktree left `git status`
empty: every one of the files it wrote (`ac2a-qualify-output.txt`) was already byte-identical. Suite 126 repeats
this in scratch on every gate run.

(b) Codex 0.166.0 (npm install --prefix under this worktree; the global install untouched) and Claude Code
2.1.317, in a detached scratch worktree: one command qualified both (`ac2b-qualify-output.txt`,
`ac2b-engines.json`). It turned off 20 Codex features on by default that the classification does not name and
listed 7 new Claude Code tools, all outward. Suite results in `ac2b-suites.txt`; the eight adapter-pin
mutants were each killed by their row (`ac2b-pin-mutations.txt`). Not green on (b), each a real binary change
needing an owner decision, not a literal:

- Suites 88, 89 and 90: on 0.166.0 a Code Mode model is offered the three MCP resource readers with no MCP
  server selected (`ac2b-codex-0.166-resource-readers.json`); the owner rule of Telegram 29400/29401 (none
  without a selected server) stops those launches as codex_unexpected_tool.
- Suite 78_0160 format/tool-forms and decision/outward-tool-asks: the Claude Code stream reader's own tables
  (new fields that name tools, new tool-free frames, REPL leaving the in-run list, the remote-tools gate now an
  environment switch) differ from 2.1.317's. These rows compare the reader with the installed binary and are
  right to be red until the reader learns the new forms.

## Open

- Suite 86 live/claude and live/codex: the live captures bind digests of the five production modules this
  change edits; by this repository's practice the lead retakes them on real accounts after landing.
- Codex 0.166.0 no longer prints "Logged in using an API key - "; LOGIN_STATUS keeps it (it then never
  matches; an API-key login is still not a ChatGPT login).
- Extractor decision to confirm (VELDO-0062 port): the two new 0.166.0 capacity errors are classified as
  transient, not exhaustion.
