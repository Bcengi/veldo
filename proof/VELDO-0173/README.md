# VELDO-0173 implementation and checks

A Claude Code run is launched with the `tools` option naming exactly its launch tool set and the
`disallowedTools` option naming every other tool of the binary's full registry. The launch tool set is
the bound role revision's native tools when a revision is bound (the contract's capability configuration
`role_revision`, VELDO-0127's to write), else the in-run tools of the version's classification. Both
options come from the qualification record and the revision alone; no tool list is in the code. Each is
passed as one `--option=value` argument: the binary's option parser reads that form once and does not
enter its variadic mode, so an argument after it is never taken as a tool name (the parser's
`/^--[^=]+=/` branch, read from the 2.1.281 bytes).

The Claude Code record's 2.1.281 entry carries `tool_registry` (86 names) and `tool_classification`
(87 rows) beside the session names VELDO-0165 added. `qualified_tools` refuses every launch of a version
whose entry lacks either, whose registry is not a non-empty list of tool names, or whose classification
leaves a registry tool unclassified, with `missing_evidence:engine_baseline:<version>`, before acceptance
and spawn; the refusal is counted by the existing `engine_baseline_refused` metric. A bound revision
without a native tool list is refused by name (`invalid_input:role_revision`) before acceptance. The
receiver's `baseline` event names the launch tool set, the registry tools switched off, the source
(`in_run` or `role_revision`) and the revision's role and number, beside the dispatch and the pinned
version and digest. Names only.

## Byte evidence and the classification

`extract_tools.py` reads the pinned binary without executing it. It parses the Bun standalone module
graph in the ELF `.bun` section (each module's path and source from the graph's own 52-byte table),
finds the one module whose registry object names `getAllBaseTools`, and resolves each of the 68 items of
the array that function returns: local bindings, imports, lazy `import.meta.require` exports, arrays,
getters, immediately called arrows, object copies and factory calls down to the object that names the
tool. An unread form raises by name, so a changed binary fails the extraction instead of shortening it.
`claude-tools.json` records, per tool, its name, module, the file offset of its quoted name literal, the
offset of its definition, its registry slot and the hint its definition carries (searchHint, else a
literal description, subject or label, kept as raw source text). Seven slots are compiled out of this
build (bound to `null`, or a getter returning `null`); they register nothing and are listed.

The classification reads `claude_code.tool_forms.in_run.tools` of proof/VELDO-0062/cli-formats.json,
18 names, identical at 14ce04f8. A registry tool on that list is `in_run`; every other registry tool is
`outward`; each reason quotes the tool's own definition. One discrepancy with the specification's
premise: 2.1.281 registers no REPL tool. Its registry slot is `...r?[r]:[]` with `r=mr()` and
`function mr(){return null}`, the getter `getTools` tests before its REPL mode. The classification keeps
REPL as an `in_run` row marked `registered: false` with that reason, so its in-run tools equal the
18-name list as AC1 requires, and the `tools` option names REPL. The binary cannot offer a tool it does
not register, so the init row expects the in-run list less REPL and checks that REPL is the only
in-run name missing. The live init's seven named tools, RemoteTrigger, SendMessage, PushNotification,
the Artifact family and the nine self_hosted_runner tools are all in the registry and all outward.

## Rows

The suite is scripts/suites/82_veldo_0173_tool_registry.py. Real production interfaces prepare the
account, membership, claims, reservations and dispatches in a signed SQLite store and run the Runner,
receiver, qualification checks and trusted wrapper. The fake Claude Code holds the extracted registry,
reads both options as the binary's parser does (either form), narrows the registry to the `tools` names,
removes the `disallowedTools` names, and prints the rest in its init event. No model, login, service
manager or network is used.

| Criterion | Row | Observation |
| --- | --- | --- |
| AC1 | launch/no-revision | With no revision bound, the `tools` option is exactly the 18-name in-run list; the init event offers the in-run list less the unregistered REPL; RemoteTrigger, SendMessage, PushNotification, the claude.ai-writing tools and every self_hosted_runner tool are absent. |
| AC1 | launch/registry | The actual `disallowedTools` option equals the extracted registry less the launch tool set; ReportFindings and every other live-init tool beyond the in-run list are in it; every registry tool is launched or switched off, never both. |
| AC1 | launch/revision | A revision granting Bash, Edit, EnterWorktree, Read and ReportFindings launches exactly those; none is switched off, every other registry tool is, Agent and WebSearch included; a revision without a tool list is refused before spawn. |
| AC1 | evidence/registry | The shipped registry equals a fresh extraction of the pinned bytes; each name is its quoted literal at its recorded offset; the registry holds the live tools the 22-name table lacks; REPL's compiled-out slot is at its recorded offset. |
| AC1 | evidence/classification | The shipped classification covers every registry tool; its in-run tools equal the 18-name list; outward is the rest; each reason quotes the definition's hint. |
| AC2 | baseline/required | No registry, no classification, a null registry and ReportFindings left unclassified each refuse `missing_evidence:engine_baseline:2.1.281` before spawn, counted once. |
| Observability | report/tools | Each launch's baseline event names its source, launch set, switched-off tools, revision and pinned version. |
| Controls | fixture/extraction, fixture/fake-default, format/fake-lines | The committed inventory equals a fresh extraction; the fake offers the whole registry with neither option and narrows with both; every printed line conforms to the binary's table. |

`VELDO-0172 fake/capture:0173_tool_registry` drives the fake through the production Guard and Terminal
at teardown. The VELDO-0062, 0060, 0160, 0155, 0129, 0141 and 0165 suites' fake qualification writers
now copy the registry and classification from `claude-tools.json`. Suite 0155's baseline row expects the
two options after the stream options, derived from the extraction, not from production code; suite
0060's option check reads the `--option=value` form as the binary's parser does. The five suites outside
the original footprint (0062, 0160, 0129, 0141, 0165) are added to it, because AC2 refuses their
records otherwise.

## Red record and mutations

`red-at-7851ae9b.json` runs the current suite over an archive of the base commit. All seven behavior
rows fail by assertion; the three fixture controls stay green.

Finding 173 registers nine mutations, each red on its named row by assertion (`mutations.json`, one
diff each):

| Mutation | Named row |
| --- | --- |
| `tools173-options-omitted` (AC1 falsifier: neither option) | launch/no-revision |
| `tools173-disallowed-from-table` (AC1 falsifier: the 22-name table) | launch/registry |
| `tools173-unclassified-accepted` (AC2 falsifier) | baseline/required |
| `tools173-registry-unchecked` | baseline/required |
| `tools173-classification-unchecked` | baseline/required |
| `tools173-revision-ignored` | launch/revision |
| `tools173-receiver-revision-unread` | launch/revision |
| `tools173-tools-unreported` | report/tools |
| `tools173-extractor-drops-lazy` | evidence/registry |

## Validation

The new suite and the suites of every touched module pass on their own selectors and again in the
empty gate environment. Findings 173 (9), 155 (25), 165 (23), 60 (35), 129 (15) and 172 (9) reject
every mutation with two jobs; every registered mutation's text is still present in its module. No
canonical gate, real engine run, login or push was performed.
