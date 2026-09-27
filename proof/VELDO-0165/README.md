# VELDO-0165 implementation and checks

The trusted exec wrapper removes every name starting with CLAUDE, CLAUDECODE, AI_AGENT or CODEX,
beside the VELDO-0155 AC4 names. The receiver carries the qualified baseline and the registered
account's profile and optional subscription token in VELDO_ENGINE_ENVIRONMENT. The wrapper applies
those values after the strip and removes the carrier itself. The receiver's own environment is kept.
Its baseline event names the dispatch, executable version and digest, strip prefixes and removed
variable names. It records no variable value.

Both engine baselines qualify the four prefixes and explicitly name CLAUDE_AGENT_SDK_MCP_NO_PREFIX.
A qualification missing that baseline or its extracted session names refuses with
missing_evidence:engine_baseline:<version> before acceptance and spawn. Existing fake Claude
qualification writers now extract their own fixture's names too; Codex's production qualification
writer records the names directly.

## Byte evidence

extract_environment.py reads Claude Code 2.1.281 and Codex 0.154.0 without executing either. The
committed inventories record the pinned digest, uppercase identifier candidates and byte offsets,
including ELF string slices for Rust literals that abut without delimiters. This is a conservative
candidate inventory, not a claim that every uppercase identifier is an environment read. The session
family extraction is also recorded separately and compared exactly with each shipped qualification.
The independently listed parent session names are checked against the prefixes and AC4's names.
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
| Controls | fixture/extraction, fixture/mcp-control | Inventory offsets are present; the same fake without the wrapper loses the prefix when the override is inherited. |

## Red record and mutations

red-at-65125030.json runs the current suite over an unchanged git archive of the starting commit.
All eight behavior rows fail by assertion. Both fixture controls stay green. The suite reports each
row once and the driver rejects raised exceptions as proof of a behavior failure.

Finding 165 registers nine unique mutations. The declared falsifiers are hygiene-listed-names-only
(using the complete extracted session-name sets), hygiene-codex-strip-unqualified and
hygiene-mcp-override-kept. The others drop Claude qualification, either extracted-name check, the
restored own values, the exec strip, or the names-only removal report. mutations.json and the
individual diffs retain the controls and each named assertion failure. All nine are rejected.

## Validation and remaining restriction

The new suite passes 10 rows, and the VELDO-0160 account pool suite passes 33 rows, each both normally
and in the requested empty gate environment. Each selector also runs the 26 shared preamble rows.
These are partial selftests and do not constitute a gate pass or landing evidence.

The engine and installed copies are byte-identical. The mutation anchor check, footprint check,
Git subprocess boundary check and repository validator pass. The byte extractor's check reproduces
the committed inventories.

The whole selftest and the existing contained-launch, heartbeat, accounts, adapter and baseline suites
have not been run: they use the real user service manager, which this task expressly forbids touching.
Clarification was requested; no exception to that restriction has been received. No gate was run.
The implementation remains ready for those checks and independent review; this is not a completion
or activation claim.

The footprint adds scripts/drive.py because the requested red command had no repository entry point,
and the VELDO-0062 and VELDO-0160 suites because their fake Claude qualifications must carry the new
required evidence. No protected path was changed.
