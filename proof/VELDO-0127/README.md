# VELDO-0127 role capability configuration

The lead captured Claude Code 2.1.281 and Codex 0.154.0 runs in `claude-live.json`
and `codex-live.json`. Those captures predate the review findings and do not establish
AC2's exact Codex native-tool equality. The specification remains ready.

The 2026-09-28 review repair stopped at the owner's explicit blocker condition.
The qualified Codex binary's offline `debug prompt-input` command returns input
messages, not the model request's tool definitions. `codex-offline-tools.json` retains
the binary digest, configuration arguments, generated MCP fixture source, output
structure and output hashes for two successful renders. Both used empty temporary
CODEX_HOME and HOME directories with Landlock denying every TCP connection. The
first used the captured native settings; the second disabled shell and unified exec.
Neither returned a tool list, including the fixture's selected Jira tool. VELDO-0156
used this interface to observe instruction content, not to enumerate effective tools.
No model request, login or real credential was used.

Completing AC2 needs an offline interface that exposes the pinned engine's actual
model-request tool definitions, or authorization for a different observation method.
Inferring those definitions from feature switches would preserve the review defect.
No production changes or new behavior rows were made in this stopped repair.
Findings 1 through 6 remain open, including the debug-log positive control and probe
terminal-record defect. Existing empty debug lines have no positive control and do
not prove instruction exclusion; the captured context-size comparison is the only
current marker evidence. The lead must recapture after the eventual production fixes.

`control_agent_config.Configurations.save` accepts immutable role revisions under
current owner authority, using the signed store's writer and compare-and-swap.
The schema lists native tools, catalog MCP and skill revisions, instruction sources,
load modes and engine settings. `save` with the skill kind records a catalog source
revision; skill bodies and instruction content remain files, outside this concern.
A selector `{role, revision}` or `{role}` on `Runner.prepare` resolves the accepted
revision once. A caller-created role revision is refused by the receiver.

Both adapters keep their qualified discovery-off baseline. The handoff probes each
selected MCP server using its catalog credentials, checks requested tool availability,
and constructs exactly the selected launch set. Claude Code joins the instruction
files and stages selected skills as a generated plugin. Its Guard holds the prompt
until both the subscription handshake and the complete init set match. Codex stages
only selected skills in the clone, uses explicit skill configuration, developer
instructions, native-tool feature settings, and required MCP tables; its own MCP
listing is checked before exec receives a prompt. Unsupported settings, an unavailable
tool and a changed launch set stop by name. The execution record keeps the first-turn
context size and Claude's redacted debug stream.

The Codex native names accepted here are `update_plan` (required by the pinned engine),
`shell`, `apply_patch`, `view_image`, `multi_agent`, and `web_search`. These name the
engine's configurable tool families. Unsupported sets stop rather than gaining defaults.

## Rows

The sole selector is `86_veldo_0127_agent_configuration`. It uses generated keys and
profiles, production catalog and credential writers, signed role revisions, the Runner,
receiver, local Linux containment and both adapters. The MCP fixture authenticates the
configured credential and advertises a Jira search tool like any other tool. Engines
are VELDO-0172 shared-constructor fakes; teardown calls `conform_fake`. Its transient
slice is stopped at teardown. No real credential or model is used by the suite.

| Criterion | Rows | What they observe |
| - | - | - |
| AC1 | revision/history | Accepted A survives B byte for byte, digests link revisions, stale and unauthorized edits fail, invalid load modes and embedded definitions fail, invented revisions cannot launch, and generated secret values are absent from ordinary records and the journal. |
| AC2 | handoff/claude, handoff/codex | Both real launch paths run the selected native tools and authenticated catalog MCP selection with the accepted model. Only selected credential-source identities are reported. A missing Claude MCP tool stops before its first turn. Claude's empty no-turn probe precedes the prompt, and engine plugins and skills stay off; Codex's own listing names exactly the generated table even with an extra server in the account profile's config.toml. |
| AC3 | dispatch/binding, dispatch/refusal | A prepared A still launches A after B is saved, the next dispatch binds B, unsupported settings and missing tools give named refusals, and an extra default tool stops before the prompt. |
| AC4 | launch/push, launch/unlisted, launch/instructions | PushNotification is in init and absent from the deny list; unassigned native tools, servers, skills and instruction files do not load; an extra skill stops before the prompt; both instruction sources reach each engine and first-turn context is kept in the committed execution record. |
| AC2, AC4 | live/claude, live/codex | Fail closed until digest-bound live captures qualify both role modes, exact engine surfaces, credential sources, and marker/context comparisons. |
| Fixture | format/fake-lines, VELDO-0172 fake/capture | Generated streams complete both production terminal protocols and conform to the captured formats. |

## Lead capture

The lead runs `python3 proof/VELDO-0127/live.py` with these required options:
`claude`, `codex`, `claude-profile`, `codex-profile`, `claude-model`, `codex-model`
(each prefixed with two ASCII hyphens). Supply the pinned Claude 2.1.281 version file,
the Codex 0.154.0 vendor binary, clean logged-in file-backed subscription profiles,
and exact model identifiers. The driver links only the login files into temporary
profiles; it never edits the supplied profiles. It creates accepted revisions in a
temporary factory and runs one worker at a time through the same production interfaces.

For each engine it captures baseline and planted-marker runs for an always-only role
and a role that also lists unassigned items. Claude gets marker CLAUDE.md files in both
clone and temporary account profile. Codex gets a project AGENTS.md marker; its profile
instructions remain subject to the previously qualified named refusal. The driver writes
`claude-live.json` and `codex-live.json`, including init or generated config and MCP listing,
the engine's built-in command names from its initialize answer, redacted debug evidence,
execution-record commitments and first-turn usage. `evidence.py` independently compares those
facts and current production digests. Missing, stale, incomplete or mismatched captures, and a
planted marker that moves the first-turn context by a quarter of its 4000 repetitions or more,
fail their rows. Two real runs of one role differ by a few dozen tokens (their generated run
paths differ), so exact equality is not the test; the captured differences are 79 and 13 tokens
for Claude and 5 and 0 for Codex.

Diagnosis options: `only` with `engine:mode:control` or `engine:mode:planted` runs one worker
and prints its facts without writing a capture; `only` with an engine name captures that engine
whole and writes its file; `diagnostics` names a file under `/run/user/UID/` that receives a
failed run's receiver messages and record lines, dropping any line that looks sensitive;
`rejudge` judges a written capture again with the current `evidence.py`, running no worker.

## Live qualification, 2026-09-28

The lead's first full run failed every Claude run and the first Codex run. Diagnosis found:

- Claude Code 2.1.281 yields its init event only as its engine starts reading a user message.
  The Guard held the prompt until init, so the run waited for its deadline. A login-free run of
  the pinned binary showed that a user message with shouldQuery false and empty content draws
  init (after the selected MCP servers connect) and a zero-turn result without any model request.
- The real init also lists the built-in plugins `agents-md` and `telemetry`, 17 bundled skills,
  the built-in skills `design` and `doctor`, and about 30 built-in commands once
  the disable-slash-commands option is dropped for a role's skill; that option also withdraws the Skill
  tool. The fake invented none of them.
- Codex 0.154 `mcp list` rejects the ignore-user-config option (exec's), reads CODEX_HOME's
  config.toml, and prints no enabled tools; `mcp get` prints them.

Production now handles each (see the spec History). The fake in the suite follows both engines'
real protocols, so every defect above reds a row without a model run. The driver launched 19
real workers, 14 of which reached a model turn: the lead's first run (4 Claude workers that never
reached a turn; its Codex listing was refused before exec), one diagnostic Claude run (no turn),
one Claude and one Codex single run, one full run (8), and a Claude recapture (4) after the
evidence learned the built-in command names. The Codex capture of the full run was judged again with the bounded
context comparison (`rejudge`), without new runs; the production modules did not change after it.

## Red record and mutations

`drive.py` replays this suite against an unchanged Git archive of pre-change `abeb3e8c`.
`red-at-abeb3e8c.json` records every one of its 11 rows red by assertion, without an
exception. The old tree has no accepted role writer or handoff implementation.

Finding 127 registers 18 distinct mutations in `scripts/check_teeth_mutations.py`.
`mutations.json` and the individual diffs retain their replacements and source hashes.
The lead reports that the checker rejected the seven mutants preceding
`role127-probe-withheld`, then stopped when that mutant exceeded the 120 second
worker limit. This is incomplete mutation qualification. The later mutants were not
reached by that checker run. Earlier builder claims about manually driven mutants
are historical reports, not evidence of a completed checker run. No mutations were
executed during this stopped repair.

The footprint adds that mutation registry for the required falsifiers and the
VELDO-0173 suite because its sole caller-built role revision must migrate to the
accepted writer. Its fake now emits init before the held prompt for bound roles.
The existing 0158 credential and 0156 profile-skill mutation anchors follow the
refactored baseline and explicit selected-skill check.

`checks.json` records the actual scoped runs and documentation checks. The older
`inspection.json` is the prior pass's read-only inspection, not current acceptance proof.
No gate, other specification's suite, model, login, remote host or push was run.
