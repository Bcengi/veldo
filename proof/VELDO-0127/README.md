# VELDO-0127 role capability configuration

## Recorded feature repair, 2026-09-29

This repair starts at `2234d205`. Every recorded feature outside the known
non-tool set now has an explicit value, independent of its default. Mapped
features follow the role grant; other features are false. Unknown default-on
features retain their named stop. Literal dotted names use an inline TOML table
because the pinned CLI treats dots in override paths as table separators.
The loopback proof serializer retains the same literal names in its generated
file and CLI arguments, including when replaying suite 86.
No new native capability or footprint path is introduced.

Suite 89 uses the signed role writer, the real qualification writer, binding and
Receiver._baseline. Its wrapper forwards the actual generated arguments to the
pinned binary only on guarded loopback, with an empty generated profile and no
login or model. The rows cover:

- AC2 and AC4: six `explicit/*` source rows observe false values for memories,
  recommended plugins, permission requests, standalone web search, MCP apps and
  the literal dotted feature name in the arguments received by the binary.
- AC2 and AC4: `explicit/mapped-default-off` changes sleep's recorded default to
  false, then observes both absent and present clock grants in the arguments and
  wire definitions. `explicit/unknown-default-off` explicitly disables a new
  default-off feature. Suite 88 retains the unknown default-on refusal.
- AC3 and AC4: `listing/missing`, `listing/empty` and `listing/malformed` require
  `configuration_stop:codex_feature_listing` with no preflight arguments or tool
  event. Records originate at the qualification writer; the missing-field case
  deletes only that field, and the other cases change the binary-output fixture.
  Each row also requires a successful valid-listing launch with standalone web
  search explicitly false. That positive control is the changed behavior; the
  invalid-listing refusal itself already existed at the baseline.

`red-at-2234d205.json` records all eleven paired behavior rows red by assertion
against the unchanged baseline archive. There is exactly one report per row.
The red driver does not alter the archived production code. AC1 is unchanged.

Three new mutations return an empty configuration for invalid listings, skip
default-off features, or withdraw the mapped clock grant when its recorded
default is off. `mutations.json` and the exact diffs record all 72 registered
finding-127 mutations against the current sources. They have not been executed
here; execution and rejection are reserved for the reviewer.

`listing-checks.json` records the final scoped runs: suites 89, 88 and 87 pass
11, 25 and 176 rows respectively in both normal and clean gate environments.
Suite 86 passes its 25 offline rows in both environments and retains only the
two stale live-capture failures. The validator passes, anchors report zero bad
anchors, the footprint reports nothing outside, requirements are regenerated,
and the production engine copies are byte-identical.

Live captures remain unchanged. The production digest changed, so the reviewer
recaptures live proofs after this lands. Scoped checks do not claim a gate pass.

## Default feature repair, 2026-09-29

This repair starts at `d72da222`. `features-fixture.json` retains the complete
140-row output of the pinned 0.154 binary's feature listing, including its 48
enabled defaults and binary digest. Capture used an empty temporary profile,
a loopback provider and the existing TCP guard; no login or model was used.
The qualification writer records that listing beside the binary digest. Binding
passes it to the role handoff, which explicitly controls each default-on tool
source and rejects an unclassified enabled feature with
`configuration_stop:codex_unknown_default_feature:<name>`.

The six mapped feature names preserve shell, image viewing, collaboration and
clock sleep grants. The other 17 tool sources stay explicitly off, including
image generation, all three browser switches, computer use, skill search and
tool suggestion. The remaining 25 defaults have a finite classification for
protocol, UI, transport or execution behavior that does not register another
tool. An absent or malformed listing also stops configuration. No new native
grant is introduced.

AC2 and AC4: suite 88's 19 `defaults/*` feature rows observe the added explicit
false values in the actual arguments forwarded to the pinned binary. The five
`mapped/*` rows check exact feature values for a granted capability and all
ungranted sources, and require its real definitions from the wire. Existing
shell, image, collaboration and goals switches are included in these comparisons.
AC3 and AC4: `defaults/unknown` changes the installed fixture binary's listing,
uses the real qualification writer and binding, and requires the named stop
before any worker preflight arguments or tool report exist. All roles are saved
through the production signed writer and launched through Receiver._baseline.
AC1 is unchanged.

`red-at-d72da222.json` records all 25 rows red by assertion against the unchanged
baseline archive. Suite 88 passes all 25 rows in ordinary and clean gate
environments. Suite 87 preserves all 176 delivery rows in both environments.
The partial runner intentionally exits nonzero even with no failures; these
scoped results are not a gate claim. Suite 86 retains 25 passing offline rows
and only the two stale live-capture failures. `feature-checks.json` records final
checks, including the exact clean environment. The validator passes, mutation
anchors report zero bad anchors, the footprint reports nothing outside, and the
production engine copies are byte-identical.

Seven new mutations omit an image, browser, computer, suggestion or skill-search
override, withdraw granted sleep, or silently accept an unknown enabled feature.
Their exact named rows and current source diffs are in `mutations.json`.
Mutation execution and rejection remain reserved for the reviewer. Live proofs
are retained unchanged; the reviewer recaptures them after this lands on the
branch because the production digests changed. No footprint expansion is needed.

## Exact Codex grant delivery repair, 2026-09-29

This repair starts at `13cc4898`. Production now runs the pinned binary with the
generated role overrides and configured MCP servers against a loopback endpoint
before releasing the task. The endpoint retains only tool definitions and rejects
the request; it cannot supply a model turn. A fresh temporary HOME and CODEX_HOME
exclude the provider login. Both missing and extra built-in or MCP tools produce
named configuration stops. Only tool names enter the receiver event.

Clock keeps its sleep operation. Code Mode's `web__run` normalizes to web search;
the observation provider advertises standalone search support, as the production
provider does. The pinned catalog only supplies clock and async input on
gpt-6-astra, so other models refuse those grants at save. Tool search is refused
on all pinned models: it is absent without MCP, Code Mode omits search itself,
and with MCP the selected definitions are deferred. No accepted grant is reduced.

Suite 87 drives the signed configuration writer, binding, materialization,
credential resolver, generated baseline and Receiver._baseline. Its 176 rows cover
all ten native grant names on all eleven qualified models, empty native controls,
selected Jira definitions, unsupported saves, and production stops for a missing
native tool, an extra native tool and a missing MCP tool. The fault adapter changes
the real binary's arguments; it never invents tool definitions. Suite 86 also uses
real wire observations where its old fake assembled tools from catalog fields.
The catalog fixture now retains the complete shipped catalog so the real binary
can parse it. The binary only runs against 127.0.0.1 with empty generated profiles;
the fixture additionally restricts TCP to the stand-in port.

The new falsifiers restore the unconditional sleep disable, drop web search, skip
the production comparison, accept unsupported grants, drop a selected MCP tool,
and add an ungranted default tool. The former granted-search catalog mutation is
replaced by an unsupported-search acceptance mutation because no pinned model can
deliver that grant exactly. `mutations.json` records current anchors and diffs.
No mutation execution or rejection is claimed; those runs belong to the reviewer.

Production digests changed. The live capture must be redone by the reviewer after
this lands on the branch. The prior live evidence is retained unchanged, and its
digest checks remain enabled. No gate or aggregate selftest is run or claimed.
Existing footprint patterns cover the changes; no expansion is needed.

`delivery-checks.json` records the scoped runs. Suite 87 passes all 176 rows in
both normal and clean gate environments. Suite 86 passes 25 offline rows in both
environments and fails only `live/claude` and `live/codex`, the retained stale
captures. The partial-suite runner deliberately returns a nonzero status even
when every scoped row passes; these observations do not certify the gate.
`red-at-13cc4898.json` records all 176 delivery rows red by assertion against the
unchanged baseline archive, with no raised-row failures. The footprint check
reports nothing outside, the anchor check reports zero bad anchors, and the
repository validator passes. All 211 shared Python engine files match byte for
byte, and the probed binary matches the shipped qualification digest.

## Usage-window integration repair, 2026-09-29

The baseline is `ef1cd2fb`. The receiver constructor always defines `binding`;
the engine launch path calls `_login`, then `_bind`, and refuses failures before
`_invoke` constructs Metering. A successful engine binding is a dictionary.
The window-only stand-in in suite 83 omitted this field. It now supplies an empty
binding dictionary, with no role expectation. Production behavior is unchanged.
An AST comparison confirms that adding this keyword is the only executable change
in the suite; all window, receipt, ordering, rejection and profile assertions remain.
The spec footprint adds this suite to preserve AC2/AC4's receiver contract.

Suite 83 now passes all 19 rows. Suite 86 passes all 27 rows, including both live
evidence checks, in the normal and clean gate environments. This supersedes the
older stale-capture notes below: this fixture repair changes no production digest
and requires no recapture. All 211 shared Python engine copies match byte for byte.
The constructor and production invoke searches also identify the receiver regression
suites listed with their results in `integration-checks.json`: 24 scoped suites,
528 target rows and zero failures. Suite 83 also passes in the clean environment.

The baseline suite 83 failed with the reported AttributeError before its first row.
That is a reproduced crash, not an assertion-based red record. Replaying suite 86
against this baseline cannot make a fixture-only repair into a production behavior
change; `red-at-ef1cd2fb.json` retains 26 passing VELDO-0127 rows and no red rows,
without claiming a new assertion-based red result.
Earlier assertion-based behavior red records remain historical.

The existing 56 finding-127 and 32 finding-166 mutations remain registered. The
global static audit finds unique names and zero bad anchors. No mutation was run,
and no rejection is claimed; the reviewer runs those checks. No new criterion or
production mutant is introduced by this fixture correction. requires.json was
regenerated without a content change. The gate and aggregate selftest were not run.

## Lead check repairs, 2026-09-29

The repair baseline is `c6f6b357`. Skill exclusion now uses the shared isolated
Git boundary. The new AC4 row `review/skill-git-boundary` saves and binds a real
role revision, materializes its skills, then stages them while GIT_DIR names a
second fixture repository. Only the intended project's exclude file may change.
The existing skill-commit row still proves staged links stay out of delivery commits.

The VELDO-0061 installed-record comparison now asks the production writer to
capture the bundled catalog offline, preserving every qualification field. Its
suite is the sole footprint addition, required for AC2's complete qualification.
The VELDO-0173 fake now answers the empty no-turn probe with init and a zero-turn
result, then waits for the real prompt. Its bound-revision row still requires one
engine to complete the dispatch with exactly the accepted tools.

`red-at-c6f6b357.json` records the new skill-boundary row red by assertion on the
unchanged baseline archive. That replay also reports the two stale live rows;
only the changed skill-boundary behavior is claimed red. The earlier red records
below retain their original behavior scope. Finding 127 adds `role127-skill-private-git`, which restores the
private subprocess and must fail that row. Mutation execution remains reserved
for the reviewer; this run claims no mutation rejections.

`lead-check-repairs.json` records the requested scoped checks. Both normal and
clean-environment VELDO-0127 runs pass 25 rows and fail only live/claude and
live/codex. The handoff edit changed a production digest bound by both captures;
the lead must recapture them. The captured observations and their checks remain
unchanged. The four other requested suites pass. Engine copies match; footprint,
anchor and validator checks pass. No aggregate selftest or gate was run.

## Earlier qualification work

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
