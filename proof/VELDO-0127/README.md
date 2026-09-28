# VELDO-0127 role capability configuration

Implementation is committed. Live qualification is pending the lead's run of
`proof/VELDO-0127/live.py`. The specification remains ready. The suite fails closed
on the two absent capture files and does not claim actual engine qualification.

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
| AC2 | handoff/claude, handoff/codex | Both real launch paths run the selected native tools and authenticated catalog MCP selection with the accepted model. Only selected credential-source identities are reported. A missing Claude MCP tool stops before its first turn. |
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
instructions remain subject to the previously qualified named refusal. The driver
writes `claude-live.json` and `codex-live.json`, including init or generated config and
MCP listing, redacted debug evidence, execution-record commitments and first-turn usage.
`evidence.py` independently compares those facts and current production digests. Missing,
stale, incomplete, mismatched or differently sized marker captures fail their rows.
The driver was compiled, never executed in this implementation session.

## Red record and mutations

`drive.py` replays this suite against an unchanged Git archive of pre-change `abeb3e8c`.
`red-at-abeb3e8c.json` records every one of its 11 rows red by assertion, without an
exception. The old tree has no accepted role writer or handoff implementation.

Finding 127 registers seven distinct mutations in `scripts/check_teeth_mutations.py`.
`mutations.json` and the individual diffs record their exact replacements and source
hashes. Static checks require each anchor once and parse every resulting module.
Mutation execution is reserved to the reviewer; none is claimed rejected here.

The footprint adds that mutation registry for the required falsifiers and the
VELDO-0173 suite because its sole caller-built role revision must migrate to the
accepted writer. Its fake now emits init before the held prompt for bound roles.
The existing 0158 credential and 0156 profile-skill mutation anchors follow the
refactored baseline and explicit selected-skill check.

`checks.json` records the actual scoped runs and documentation checks. The older
`inspection.json` is the prior pass's read-only inspection, not current acceptance proof.
No gate, other specification's suite, model, login, remote host or push was run.
