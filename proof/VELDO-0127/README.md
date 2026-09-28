# VELDO-0127 role capability configuration

Item 1 repair from `0fbf6f09`, under owner Telegram 29393 and 29398: the accepted
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

## Remaining owner decision

`catalog-loopback-gpt-6-astra.json` and `catalog-loopback-gpt-5.5.json` capture the
real pinned binary using the production generated catalog, credential-free MCP
fixtures, empty temporary profiles and the loopback stand-in. Every selected grant
is present. Both captures still expose these three ungranted resource readers:

| Current case (c) | Reach |
| - | - |
| list_mcp_resource_templates | Templates of the role's configured MCP servers |
| list_mcp_resources | Resources of the role's configured MCP servers |
| read_mcp_resource | A resource URI from a configured MCP server |

These tools can expose files, schemas or other data offered as resources by those
servers. They do not add another server or another server's credentials. The suite
keeps them unexpected and the comparator returns
`configuration_stop:codex_unexpected_tool`. They are not added to role grants by
this repair. Exact qualification remains blocked on this single case (c).

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
| AC2 | wire/resources | Both real fixture bodies and fake worker output retain the three readers as ungranted extras and fail closed |
| AC2 | review/codex-capture | The live driver runs gpt-6-astra with its generated catalog and records the loopback tools beside the unchanged model |
| AC3 | dispatch/binding, dispatch/refusal | Running A survives accepted B; later dispatch binds B; unsupported settings, missing tools and extra defaults stop |
| AC4 | launch/push, launch/unlisted, launch/instructions | PushNotification, selected skills and instruction sources, absent deferred items, and retained first-turn context |
| AC2, AC4 | live/claude, live/codex | Still red pending fresh lead captures, with the resource-reader difference also unresolved |
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
still required for both engines. A fresh capture does not waive the resource readers.

## Red record and mutations

`red-at-0fbf6f09.json` replays the current suite against the unchanged pre-change Git
archive. All eight changed behavior rows are red by assertion, with no exception:
review/codex-tools, review/codex-mode, review/codex-capture, catalog/fields,
catalog/grants, catalog/integrity, wire/normalization and wire/resources.
Older red records remain historical.

Finding 127 registers mutations for each of the four catalog removals, each granted
field's retention, unchanged reasoning, digest checking, both name normalizations,
nested declarations, runner expectations and resource-reader visibility. Earlier
criterion falsifiers remain registered. `mutations.json` and individual diffs retain
exact replacements and hashes. Mutation execution is reserved for the reviewer;
zero rejections are claimed by this run. The honest-run prerequisite remains red on
the live qualification rows.

`checks.json` records the scoped normal and clean gate-environment runs, footprint,
anchor, validator and engine-copy checks. No gate or aggregate selftest was run.
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
`codex-owner-decisions.json` names only the three current readers.

The prior apply_patch and tool_search extras are also removed by their catalog
fields. The selected Jira definition now appears directly when search is disabled.
The three resource readers above are the sole remaining case (c). Earlier captures,
switch investigations and other review repairs remain in this proof directory;
none is treated as fresh live qualification of this tree.
