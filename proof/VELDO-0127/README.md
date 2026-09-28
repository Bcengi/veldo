# VELDO-0127 role capability configuration

Item 1 catalog repair from `0fbf6f09`, under owner Telegram 29393 and 29398: the accepted
model stays unchanged and models that default to Code Mode keep Code Mode. The
handoff now uses the pinned binary's bundled model catalog to remove ungranted
capabilities. The earlier blanket refusal of restricted Code Mode roles is gone.
No real provider, account profile, login or model was used for this repair.

The qualification CLI calls `debug models` with the bundled option under empty
temporary HOME and CODEX_HOME. Both shipped qualification records contain the
complete catalog and its SHA-256 digest over canonical JSON. Its binary digest
matches the pinned Codex 0.154.0. Existing callers that qualify only the engine can
still omit catalog capture; role launches require catalog evidence and fail closed
without it. No binary catalog command runs at launch.

The handoff selects the accepted model's entry and writes `model-catalog.json`
in the run configuration directory, passing its path as `model_catalog_json`.
Only four entry fields can change:

| Field | Grant controlling retention |
| - | - |
| multi_agent_version | sub_agents, with multi_agent retained as the existing spelling |
| apply_patch_tool_type | apply_patch |
| experimental_supported_tools | clock and request_user_input_async, mapped from the catalog names |
| supports_search_tool | tool_search |

The model slug, reasoning levels and every other entry field remain unchanged.
The role schema accepts sub_agents. A missing entry or unusable catalog digest
retains `configuration_stop:codex_code_mode_model` for Code Mode models; direct
models use `configuration_stop:codex_model_catalog`.

The comparator includes the top-level exec and wait runner plus the tool headings
inside exec's description for Code Mode. Direct mode uses the top-level tool
definitions. It removes functions prefixes and normalizes both MCP spellings to
`mcp__server__tool`, expands the native grant mapping and compares both directions.
The accepted model determines whether the runner is expected. Neither runner
presence nor nested tools can silently broaden the expected grants.

## Resource-reader rule

Owner Telegram 29400 (asked), 29401 ("Ok"), 2026-09-28: reading an MCP server's
resources is part of granting that server. The Codex native mapping records an
`mcp_server` grant for exactly list_mcp_resources, list_mcp_resource_templates and
read_mcp_resource. The qualification writer retains that mapping and the explicit `mcp_resource_rule`
condition in both shipped records. The comparison adds it only when the bound role's selected server set is
nonempty. A missing reader then fails equality. With no selected server, none is
expected and the presence of any reader fails closed. No role model changes.

`resource_probe.py` regenerates production configuration and selected catalog from
the retained production role configuration, varying only the model and server
selection for qualification. It uses `loopback.py`, empty temporary HOME and
CODEX_HOME and the 127.0.0.1 stand-in. `resource-qualification.json` indexes all four
captures: gpt-6-astra Code Mode and gpt-5.5 direct mode, with and without a server.
All four reach exact equality. The real pinned 0.154.0 binary exposes none of the
three readers without a server. `codex-loopback.json` is also a fresh capture of
the current production configuration: exact equality, no missing or extra tools.
No real provider, model, account profile or login was used.

## Historical case (c)

The earlier catalog captures reported the following readers as unexpected. Owner
Telegram 29400/29401 resolves this table; it is history, not an outstanding decision.

| Historical reader | Reach under the approved grant |
| - | - |
| list_mcp_resource_templates | Templates of the role's configured MCP servers |
| list_mcp_resources | Resources of the role's configured MCP servers |
| read_mcp_resource | A resource URI from a configured MCP server |

These readers add no server and no other server's credentials.

`resource-investigation.json` records the binary string search and loopback probes.
The catalog has no resource-reader field. Strings identify the resource handlers,
`add_mcp_resource_tools`, the MCP server fields `disabled_tools` and
`omit_tools_from`, and Code Mode's `excluded_tool_namespaces`. Server disabled tool
names, resource tool enabled flags, excluded resource names and all three valid
omit modes leave the readers present. Using resource names as omit modes is
rejected by the binary, which lists code_mode, deferred and direct as valid values.
No working suppression control was established, and none of these probes became
production configuration. This is evidence about the inspected fields and tested
controls, not a proof about all possible undocumented controls.

The reproducible driver is `catalog_probe.py`, with the pinned vendor executable
as its only argument. `request-code.json` and `request-direct.json` retain the two
request bodies used by the fake-driven rows. `catalog-fixture.json` contains the
small fake binary catalog; the qualification writer, not a hand-built record,
captures that fake's bundled response. The lead's supplied `catalog_astra_code_tight.json`,
`lb55.py` and `lbdump.py` remain historical reproduction inputs.

## Rows

The registered selector is `86_veldo_0127_agent_configuration`. Rows use accepted
role and catalog writers, generated credentials, the production Runner and receiver,
both adapters, shared VELDO-0172 fake stream constructors and transient containment
scopes stopped at teardown. One assertion report is emitted per row name.

| Criterion | Rows | Proof |
| - | - | - |
| AC1 | revision/history | Immutable accepted revisions, linked digests, authority, stale edits, explicit load modes and no secret values in ordinary records |
| AC2 | handoff/claude, handoff/codex | Accepted model, native tools, authenticated selected MCP tools, credential-source identities and generated configuration |
| AC2 | catalog/fields | All four Code Mode models change exactly the four permitted catalog fields |
| AC1, AC2 | catalog/grants | Each catalog capability and their combined grant survive accepted role save and production launch |
| AC2, AC3 | catalog/integrity, review/codex-mode | Qualification captures the bundled catalog and digest; restricted Code Mode roles launch without substitution; absent or mismatched catalog evidence stops by name |
| AC2 | review/codex-tools, wire/normalization | Runner and nested declarations, direct definitions, namespace and MCP aliases, and both missing and extra tool detection |
| AC2 | wire/resources | Selected server implies exact equality including all three readers; removing any reader fails |
| AC2 | wire/no-server | Accepted roles with no server expose no readers in direct and Code Mode; every injected reader fails; qualification mapping and real loopback absence are checked |
| AC2 | review/codex-capture | The live driver runs gpt-6-astra with its generated catalog and records the loopback tools beside the unchanged model |
| AC3 | dispatch/binding, dispatch/refusal | Running A survives accepted B; later dispatch binds B; unsupported settings, missing tools and extra defaults stop |
| AC4 | launch/push, launch/unlisted, launch/instructions | PushNotification, selected skills and instruction sources, absent deferred items, and retained first-turn context |
| AC2, AC4 | live/claude, live/codex | Still red pending fresh lead subscription captures |
| AC2, AC4 | review/skill-commit, review/marker-debug | Staged skill links stay out of commits; planted debug loads fail; absent debug control needs explicit context-size-only evidence |
| AC3, AC4 | review/probe-terminal, review/init-bound, review/slash-collision | No-turn probes cannot complete workers, init is bounded and duplicate slash entries remain visible |
| Fixture | format/fake-lines, VELDO-0172 fake/capture | Fake streams conform to the retained binary formats |

## Lead capture

Run `live.py` with options claude, codex, claude-profile, codex-profile,
claude-model and codex-model, each prefixed by two ASCII hyphens. Use the pinned
Claude 2.1.281 file and Codex 0.154.0 vendor binary. For this qualification supply
gpt-6-astra as codex-model. The driver checks the model before opening profiles and
never substitutes another model. Qualification captures the bundled catalog before
launch; the driver regenerates the same selected catalog after teardown for its
loopback capture and retains it in the resulting evidence.

Only the lead runs subscription captures. The driver links only login files into
temporary profiles and runs workers serially. Baseline and planted-marker runs cover
always-only and deferred roles. The evidence judge checks production digests,
configuration, exact effective tools, generated catalog, model, credential sources,
execution record, debug controls and context-size comparisons. Fresh captures are
still required for both engines. The resource-reader loopback qualification is complete.

## Red record and mutations

`red-at-44a1b857.json` replays the current suite against the unchanged pre-change Git
archive. All four changed behavior rows are red by assertion, with no exception:
wire/resources, wire/no-server, review/codex-tools and wire/normalization. The
no-server row also checks that the real qualification writer records the conditional
server grant. Older red records remain historical.

Finding 127 adds role127-resource-grant-omitted (wire/resources) and
role127-resource-grant-without-server (wire/no-server). The existing mutation that
hides readers still fails the selected-server row. Earlier criterion falsifiers
remain registered. `mutations.json` and individual diffs retain exact replacements
and hashes. Mutation execution is reserved for the reviewer; zero rejections are
claimed by this run. The honest-run prerequisite remains red on the pre-existing
live qualification rows, which need authorized lead subscription captures.

`checks.json` records the scoped normal and clean gate-environment runs, footprint,
anchor, validator and engine-copy checks. Both scoped runs report 24 passing suite
rows and the same two stale live-capture failures; neither is claimed green. The
validator passes, anchors report zero bad entries, and the footprint has no outside
paths. No gate or aggregate selftest was run.
The suite remains registered and requires.json was regenerated. The existing spec
footprint covers every changed file. Gate byproducts are excluded from commits.

## History

Earlier item 1 investigations used feature switches that did not remove the Code
Mode tools and then refused restricted Code Mode models. Owner Telegram 29393 and
29398 supersede that approach: never downgrade implicitly, and keep default Code
Mode. The earlier case (c) table is historical:

| Historical case (c) | Current disposition |
| - | - |
| functions.exec, functions.wait | Expected Code Mode runner, with nested declarations compared |
| functions.request_user_input_async | Removed by catalog unless explicitly granted |
| Six collaboration tools | Removed with multi_agent_version unless sub-agents are granted |

`codex-owner-decisions-before-catalog.json` retains the old table verbatim;
`codex-owner-decisions.json` records the approved conditional grant for all three readers.

The prior apply_patch and tool_search extras are also removed by their catalog
fields. The selected Jira definition now appears directly when search is disabled.
No resource-reader case (c) remains after Telegram 29400/29401. Earlier captures,
switch investigations and other review repairs remain in this proof directory;
none is treated as fresh live qualification of this tree.
