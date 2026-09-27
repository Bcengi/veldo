# VELDO-0165 implementation and checks

The trusted exec wrapper removes every name starting with CLAUDE, CLAUDECODE, AI_AGENT or CODEX,
beside the VELDO-0155 AC4 names. The receiver carries the qualified baseline and the registered
account's profile, optional subscription token and checked adapter configuration in VELDO_ENGINE_ENVIRONMENT. The wrapper applies
those values after the strip and removes the carrier itself. The receiver's own environment is kept.
Its baseline event names the dispatch, executable version and digest, strip prefixes and removed
variable names. It records no variable value.

Both engine baselines qualify the four prefixes and explicitly name CLAUDE_AGENT_SDK_MCP_NO_PREFIX.
A qualification missing that baseline or its extracted session names refuses with
missing_evidence:engine_baseline:<version> before acceptance and spawn. Existing fake Claude
qualification writers now extract their own fixture's names too; Codex's production qualification
writer records the names directly. An empty list is present evidence; a missing key, null, false or
an empty string refuses, because the names must be a list. An adapter whose configured environment
names CLAUDE_AGENT_SDK_MCP_NO_PREFIX is refused by name when the receiver loads it, before acceptance.

The worker's environment is configured, never ambient. The wrapper list also removes what Codex
0.154.0 sets on every command it runs (NO_COLOR, TERM, LANG, LC_CTYPE, LC_ALL, COLORTERM, PAGER,
GIT_PAGER and GH_PAGER; CODEX_CI goes by prefix) and the OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE
default Claude Code writes into its own environment when unset. Each engine's baseline then sets
LANG=C.UTF-8 and TERM=dumb itself, so a run is the same from a terminal, a Codex session or systemd.

## Byte evidence

extract_environment.py reads Claude Code 2.1.281 and Codex 0.154.0 without executing either. The
committed inventories record the pinned digest, uppercase identifier candidates and byte offsets,
including ELF string slices for Rust literals that abut without delimiters. This is a conservative
candidate inventory, not a claim that every uppercase identifier is an environment read. The session
family extraction is also recorded separately and compared exactly with each shipped qualification.
The extractor locates Claude Code's child-environment array, unconditional startup assignments and
its one default-when-unset assignment by content. For Codex it decodes the six-entry child-key array
from consecutive length-bound stack string slices, and the unified exec (name, value) array in the
writable data, found through the slice of its CODEX_CI entry and walked whole. Every extracted child
name must match the prefixes or AC4's names.

Session names are read as an outside scan reads them: printable runs of six or more bytes outside
the ELF executable sections, each uppercase word cut where a prefix follows anything but an
underscore, and pieces ending in an underscore (template stems) dropped. Machine code immediates such
as CODEX_HOH are therefore gone, and names that repeat a prefix, such as CLAUDE_CODE_DISABLE_CLAUDE_MDS,
or abut other literals, such as CODEX_THREAD_ID, are kept. Rust literals that abut an uppercase
literal, or 16-byte comparison chunks, stay as the bytes hold them; they are prefixed, so the strip
covers them, and the list is evidence only. The row evidence/outside-scan runs GNU strings, grep and
readelf over the same binaries, independently of the extractor, and requires equal non-empty sets
holding CLAUDE_CODE_DISABLE_CLAUDE_MDS, CODEX_THREAD_ID, CODEX_SANDBOX and CODEX_SESSION_ID
(829 Claude Code names, 85 Codex names). The suite reruns the
extractor and compares the whole inventory; substituting the old prefixed hand list fails completeness.
The Claude record also pins the SDK naming switch, its skipPrefix field, the conditional tool name
and the MCP prefix text in the binary.

## Rows

The suite is scripts/suites/82_veldo_0165_launch_hygiene.py. Real production interfaces prepare the
accounts, memberships, claims, reservations and dispatches in a signed SQLite store, and run the
Runner, receiver, qualifier and trusted wrapper. Fake engine processes report their actual birth
environment. A local stdio MCP fixture answers tools/list; the fake Claude applies the SDK-only
naming condition read from the binary and emits its init event. The reported-identity wrapper is
local, so these rows do not access the user service manager. No model or real login runs.

| Criterion | Rows | Observation |
| --- | --- | --- |
| AC1 | strip/claude, strip/codex | Eleven observed parent names, a Codex name and future names are absent from each engine; names-only reporting joins the dispatch to its pinned version. |
| AC1 | strip/future-names | Unlisted names for every prefix, including CLAUDE_CODE_, are removed. |
| AC1 | strip/own-values | Each account's profile, qualified baseline and own subscription token survive in place of inherited values; the wrapper carrier is absent. |
| AC1 | refuse/claude, refuse/codex | Removing prefixes or extracted names separately refuses before any engine marker exists. |
| AC1, AC2 | evidence/qualified | Shipped qualifiers match the pinned inventory and carry the strip; the MCP override is explicitly named. |
| AC2 | mcp/prefixed-tools | Both configured SDK server tools keep mcp__tracker__ prefixes in the init event. |
| AC1 | strip/configured, strip/unprefixed | Configured subagent model and CA certificate replace parent values; Git parameters, trace context and Corepack settings are absent. |
| AC1 | evidence/empty, evidence/completeness, evidence/prefixes | Empty evidence launches, missing and null evidence refuse; extracted child structures are covered; wrapper prefixes equal both baselines. |
| AC1 | report/removed, report/refused | Restored names are not reported removed; each refused baseline emits one engine_baseline_refused metric increment. |
| AC1 | strip/child-environment | Codex's exec settings and Claude Code's metrics default, planted with parent values, are absent from both engines except LANG and TERM, which carry the baseline's C.UTF-8 and dumb. |
| AC1 | evidence/not-a-list, evidence/outside-scan | False or empty-string session names refuse before spawn; extracted session names equal the independent strings scan. |
| AC2 | mcp/configured-refused | An adapter configuring the MCP naming switch is refused by name, nothing spawned. |
| Controls | fixture/extraction, fixture/mcp-control | Inventory offsets are present; the same fake without the wrapper loses the prefix when the override is inherited. |

## Red record and mutations

red-at-65125030.json runs the current suite over an unchanged archive of the original implementation
base. red-at-fd81afc0.json does the same for the reviewed commit. Failures are assertions, never
exceptions. Both fixture controls stay green. Rows whose behavior already existed at a base remain
green there; the red records retain each individual outcome.

Finding 165 registers 23 globally unique mutations. In addition to the original nine, these cover
empty evidence treated as missing for either engine, configured values dropped after the strip,
unprefixed child names left in the environment, the old hand-list extraction and the refused metric
not incremented. The second review fix adds eight: session names that are not a list accepted for
either engine, the extractor dropping names ending in _ID, Codex's child settings or Claude Code's
metrics default left off the wrapper list, either baseline not setting LANG and TERM, and an adapter
configuring the MCP naming switch accepted. Both red records were regenerated over the 21-row suite
and fail by assertion; outside-scan is red at fd81afc0, whose session names came from the old pattern. mutations.json and individual diffs record controls and named assertion failures.

The VELDO-0062 suite still checks configured login, redirect and provider-switch refusal. Its existing
non-login-setting row now requires CLAUDE_CODE_MAX_OUTPUT_TOKENS when configured and its absence when
only inherited, following approval of VELDO-0165 (Telegram 29229). Account-boundary checks retain the
credential classification contract before the wrapper's broader strip, so that the strip cannot hide
an account-layer defect from the finding-62 mutations.

## Validation

Second review fix, on 8cc010bf: the whole selftest ran once with the checkout unchanged throughout,
6,908 rows passed and zero failed. VELDO-0165 passes 21/21. The four mutation commands, each with
two jobs, reject all cases: finding 165 has 23, finding 62 has 50, finding 61 has 30 and finding 155
has 25. All 1,900 registered mutation names are unique. The Git subprocess boundary check and the
repository validator pass, and the engine copies are byte-identical.

Earlier round:
review-fix-validation.json records the checks on e381030a. The whole selftest ran once with the
checkout unchanged throughout: 6,877 rows passed, zero failed. The individual suites pass 20/20
(VELDO-0061, assertions unchanged), 22/22 (VELDO-0062), 17/17 (VELDO-0155) and 17/17 (VELDO-0165).
The four requested mutation commands, each with two jobs, reject all cases: finding 165 has 15,
finding 62 has 50, finding 61 has 30 and finding 155 has 25. The older environment and token-delivery
mutations now remove the corresponding carrier restoration, so they still model the named defect.
All 1,877 registered mutation names are unique. Both red records fail by assertion.

The byte extractor reproduces both committed inventories. Template sync compares 231 pairs with
no drift. The Git subprocess boundary check and repository validator pass. Gate byproducts are
restored before the final evidence commit and are not part of this change.
No canonical gate, real model, login or non-loopback network access is part of this review-fix task.
