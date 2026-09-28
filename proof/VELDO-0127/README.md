# VELDO-0127 role capability configuration

Item 1 continuation from `04795046`: the offline request is captured successfully,
but AC2 exact equality remains blocked. No switch tested against the pinned binary
removed the remaining tools. These are case (c) owner decisions, recorded individually
in `codex-owner-decisions.json`, not approved exceptions. No capability was removed
from the role or production configuration. No metadata override was introduced.
The specification stays ready; no full qualification or gate pass is claimed.

`codex-loopback-before.json` retains the original capture. `codex-loopback.json` is a
fresh capture of the current production handoff configuration. Both use Codex
0.154.0, empty temporary HOME and CODEX_HOME, a 127.0.0.1 HTTP stand-in, generated
credential-free MCP fixtures and a Landlock TCP restriction to the stand-in port.
No model, account profile, login or real credential was used. The request carries
its exact tools array in an `additional_tools` input item.

The binary's own `debug models` output identifies `gpt-6-astra` with `shell_type`
`unified_exec`, `tool_mode` `code_mode_only` and `multi_agent_version` `v2`.
The request's embedded declarations identify `exec_command` and `write_stdin` as
shell operations, and `update_plan` as plan editing. That direct-call vocabulary
now has one production mapping in `control_engine_codex.NATIVE_TOOL_MAPPING`,
written by the qualification writer, shipped in both qualification records and
consumed by the handoff comparator. This is a direct-call mapping, not a claim
that this model emits those definitions directly. The Code Mode wrappers are not
shell-only aliases: their description also exposes patching, MCP resource readers
and clock access. Mapping the wrappers to shell would conceal those capabilities.

| Case (c) tool | Capability retained for owner decision |
| - | - |
| functions.exec | JavaScript orchestration over registered tools, including ungranted nested operations. |
| functions.wait | Resume or terminate a JavaScript cell, using cell_id rather than a shell session_id. |
| functions.request_user_input_async | Ask questions and receive asynchronous user input. |
| collaboration.followup_task | Send work to an existing agent and start its turn. |
| collaboration.interrupt_agent | Interrupt an agent turn. |
| collaboration.list_agents | List live agents. |
| collaboration.send_message | Message an existing agent. |
| collaboration.spawn_agent | Create a sub-agent. |
| collaboration.wait_agent | Wait for agent updates. |

`codex-tool-investigation.json` records one-change loopback probes and their exact
names and request hashes. The binary's strings identify the tested feature keys.
Both boolean and table forms of Code Mode and multi-agent switches left these
tools present. The binary's `features list` reports Code Mode and multi-agent false
under the current configuration, yet the model request still contains them. The
`default_mode_request_user_input` switch did not remove async input. Code Mode host,
multi-agent mode, tool search, orchestrator and non_code_mode_only controls likewise
did not produce equality. No working switch is claimed, and none was added to the
production configuration. This establishes the failure of the tested switches, not
an exhaustive proof that no undocumented switch exists.

The evidence judge now reports every unexpected and missing name together. All nine
tools above remain unexpected. The direct definitions `exec_command`, `write_stdin`,
`update_plan` and `mcp__jira.jira_search` are missing. Shell and plan declarations
inside the wrapper are observations, not substitutes for tool definitions. Jira is
still selected in the generated MCP table but has no explicit definition in this
request. Consequently even accepting the nine extras would not by itself establish
that every grant is exposed. The reader preserves `configuration_stop:codex_unexpected_tool`.

The updated fake-driven `review/codex-tools` row consumes the actual fake worker's
request, generated from the production launch configuration and authenticated MCP
listing. It checks the qualification writer's mapping, exact comparison in both
directions, and the named unresolved observations from the real capture. Its green
result does not mean real Codex equality. The other review repairs are unchanged.

The debug leg has no qualified positive control yet. Empty old debug lines prove
nothing. The retained old context-size comparison is the only present AC4 marker
observation, and is not a fresh qualification of the changed tree. `live.py` now runs
one discovery-enabled control, retains its CLAUDE.md debug lines, and explicitly marks
`context-size-only` if a successful control produces none. `evidence.py` requires
empty planted `debug_lines` and rejects a missing control or an unstated fallback.

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
only selected skills in the clone with exact local Git exclusions, uses explicit skill configuration, developer
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
| AC2 | review/codex-tools | The fake worker derives its request from production configuration and its authenticated MCP listing. The qualification mapping agrees, extra or missing tools fail, and the real Code Mode capture retains every unresolved name and missing definition. |
| AC2, AC4 | review/skill-commit | A real fake-worker commit of everything contains its delivery but no staged skill symlink. |
| AC4 | review/marker-debug | The live capture reader consumes a production execution record; planted instruction debug lines fail, and absent positive debug evidence requires an explicit context-size-only fallback. |
| AC3, AC4 | review/probe-terminal | A fake engine closes input after the zero-turn probe. The receiver names the failed prompt write, never accepts that probe as terminal, and the live driver records zero turns and zero pre-prompt assistant events. |
| AC3, AC4 | review/init-bound | After a confirmed login, an engine withholding init stops by configuration_stop:init_missing in under 15 seconds. The production init bound is five seconds. |
| AC4 | review/slash-collision | A built-in and non-built-in entry sharing a slash name remains visible to the exact comparison and stops the run. |
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

`drive.py` replays the current suite against an unchanged Git archive. The original
`red-at-abeb3e8c.json` is historical. `red-at-5a9a05d2.json` records all six new
review behavior rows red by assertion, with no raised exception. Other already
implemented rows are retained separately and are not falsely claimed red.

Finding 127 now registers 31 unique mutations. `mutations.json` and the individual
diffs contain current exact replacements and source hashes. No mutant was executed
in this run. The earlier owner report of seven rejections followed by the withheld
probe timeout is historical. The new bounded init wait and suite launch skip make
that mutant terminate by assertion, but its actual checker rejection remains for the
reviewer. A missing probe on the first Claude handoff skips all later Claude launches
and leaves their rows false by assertion. The checker's honest-run prerequisite
will remain red until the live qualification rows are closed.

The suite remains registered in manifest.json; requires.json was regenerated.
The touched canonical engine modules and installed .veldo copies are byte-identical.
The footprint adds the two shipped Codex qualification records because AC2 now records the direct-call vocabulary there. checks.json
records the final scoped results and limitations. The gate's byproducts are not
implementation changes and are not committed.

## History

The first real qualification and initial implementation are described above. At the
previous repair stop, the debug prompt-input command could not expose tool definitions;
`codex-offline-tools.json` retains that evidence. Findings 1 through 6 were then open.
This continuation uses an explicitly authorized loopback request capture for item 1
and fixes the independent items 2 through 6. The remaining blockers are stated at the
start of this README. No prior success claim substitutes for fresh live qualification.

Item 1 investigation from `04795046` additionally records the binary's model defaults,
the ineffective switch probes and each unresolved capability above. The current
red replay targets only the changed `review/codex-tools` behavior row; the other
review rows were already implemented at that baseline. Three mutations target the
shell mapping, hiding owner-decision tools and hiding missing grants. No switch
mutation is invented because no working switch was found or shipped. The reviewer
must run mutation rejection; this run executes no mutants. Live rows still require
fresh lead qualification, including the independent Claude recapture.

Final scoped checks for this continuation: both normal and clean gate-environment
runs report 16 owned behavior and format rows passing and two live rows failing.
`red-at-04795046.json` records the changed row red by assertion. The footprint check
reports nothing outside, the anchor check reports 0 bad anchors, and validate all
exits 0. The gate and mutation worker were not run. Engine modules and qualification
copies are byte-identical. `checks.json` records the scoped results without a gate
or completed qualification claim.
