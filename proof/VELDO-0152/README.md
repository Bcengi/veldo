# VELDO-0152 review follow-up evidence

## Further review fixes at 5d90b5b5

Both requested fixes are committed on build-veldo-0152b:

- `7d96d036`: suite 93 sets the loaded mutation catalog's ROOT to the real repository before
  calling cases(). A temporary mutant catalog therefore reads the real qualification fixtures.
  The companion check still materializes each distinct intake dependency layout and imports it;
  its existing missing-import assertion remains intact. No mutation runner was executed here,
  so rejection of v152-intake-companions-missing remains for the reviewer to execute.
- `299e0742`: suite 86 activates the factory project through the existing signed helper and
  applies an unclear route through intake before checking the question. The original delivery
  assertion is unchanged: a question must actually arrive, its literal escape must be escaped
  once, and the stored prompt must retain the original text. An additional assertion requires
  an applied route. The incoming fixture message is dated after membership enrollment because
  the stand-in's fixed date otherwise yields unauthorized:not_member_when_sent.

The fixture change follows VELDO-0152 AC2, lines 114-116: "A store with no factory project refuses
an undecided message `unsupported_configuration:factory_project` and routes it nowhere."
Its landed-suite guidance, lines 278-281, explicitly requires a factory project and an unclear
route for rows needing a question. VELDO-0168 AC1 includes the intake question send, and AC2
requires escaping the literal `<U+` prefix. Production routing therefore stays unchanged.
The earlier classification below of 0168 intake/delivery as inherited is superseded by this
review finding; reproducing it at an earlier 0152 build did not establish that the failure
predated the 0152 routing change.

Requested suites ran individually with `python3 scripts/selftest.py --suite NAME`:

| Suite | Behavior rows | Total assertions | Result |
| --- | --- | --- | --- |
| 93_veldo_0152_intake_routes | 19 | 45 | pass, zero failures |
| 86_veldo_0168_text | 26 | 52 | pass, zero failures |
| 50_git_environment | 4 | 30 | pass, zero failures |

The partial-suite success exit is 2 by design. Suite 86 initially failed intake/delivery after
factory setup; a diagnostic rerun identified the stale platform date, and the final run above
passed after that fixture correction. Validation (`python3 .veldo/validate.py all`) and engine
sync (`bash scripts/check_template_sync.sh`) pass. No .veldo implementation files changed in
these fixes. checks.json and footprint.json record this follow-up separately from prior results.
No full gate, full selftest, mutation runner, push, merge or other worktree operation was run.

## Previous review evidence

Review base: ed630cd023ac8fb20140631b6a0c7cec39c6dbdc, branch build-veldo-0152b.
The README and repository operating instructions were read before implementation. No push,
merge, other branch, other worktree, full selftest or gate run was performed.

Three review regressions were driven against unchanged production and mutation-catalog code at
ed630cd0. Only the suite assertions were added. red-at-ed630cd0.json records exactly these three
rows red by assertion, with all sixteen previous 0152 rows green:

| Finding | Proof row | Registered mutant | Fix commit |
| --- | --- | --- | --- |
| Codex telemetry treated as a final route document | route/codex-result | v152-codex-nonmessage-final | 3c7f01f3 |
| Isolated intake mutations lack their imports | proof/intake-companions | v152-intake-companions-missing | 4228fc7a |
| Scoped member context exposes unrelated project versions | intake/scoped-context | v152-context-all-projects | ff0b84bd |

The Codex row accepts a Codex PM configuration and team through the real writers, dispatches the
fake CLI through the Runner, and emits reasoning, command_execution and agent_message completions.
Only the parsed agent message reaches the routing command. The row checks the resulting state,
reason, dispatch correlation and selected adapter. Claude result-string journeys remain covered.
Route mode accepts only parsed final-message content; the legacy raw proposal-document path stays
available to non-route PM cycles.

The companion row enumerates every control_intake.py mutation case and materializes/imports each
distinct dependency layout. Companion assignment now follows all case registrations, including
0152. Every intake case names control_project.py and control_intake_routes.py, and uses the existing
full-sibling-copy option because control_project imports eligibility and further local organs.
A missing companion becomes a false named row, not a mutation-worker exception.

The scoped-context row sends both unresolved and ticket-key messages through Telegram and API as
the scoped member. Both proposal context and decision must contain the exact versions of only
project:bcengi and project:factory; project:other must be absent. Intake reads the same restricted
set for transaction version checks.

All nineteen 0152 rows pass after the fixes (45 total assertions including the shared preamble).
Current scoped suite results, validation, engine sync and footprint are recorded in checks.json,
static-checks.json and footprint.json. Partial selftests intentionally return exit 2 when green;
assertion summaries, not a zero process exit, determine their result.

The requested suite list contains twelve neighboring suites. Eleven pass; 0169 census/writers
remains red, as already recorded and reproduced at the earlier base below. No unrelated assertion
was suppressed. The 0088 timeout case and all timeout values are unchanged.

Mutation anchors and Python syntax were checked for all 130 cases in findings 136, 168, 126, 133,
128 and 152; all passed. Fourteen finding-152 mutants are registered. Mutation execution is NOT
claimed: the task's TOKEN RULES explicitly prohibit check_teeth_mutations.py, conflicting with its
later request for those six findings. Clarification was requested. No mutation runner or gate
runner was executed, and no mutant is described as rejected without execution.

Earlier build evidence follows; its counts and base describe the previous implementation run.

## Earlier builder evidence

Base: 16a91069, on build-veldo-0152b. No push or other worktree changes.

The suite drives signed activation, actual common intake for Telegram and API, the factory
pass, LangGraph and Runner with a local fake claude process returning the CLI result shape.
It tests the routing decision, all three routes, clarifications and named refusals. The
read model and real journal report writer preserve route reasons and dispatch correlation;
report delivery uses the loopback channel with its activation boundary trusted by the fixture.

The new route owner is installed by the scaffold and engine copies are synchronized.
The production PM integration changes the 0088 cycle module, which is inside this footprint.
The 0151 suite changes only its intake request to carry an explicit project field. Existing routing suites are amended as the specification directs.
Additional footprint entries cover the report registry and the 0085, 0151 and 0169 intake consumers.

Mutation execution and the full gate remain reviewer-owned. mutations.json lists the registered
finding-152 cases; it does not claim they have been executed or rejected.

The supplied footprint checker compares with origin/main and therefore also reports inherited
0088 and 0151 paths. footprint.json compares with the specified 0152 base instead.

Final scoped results are in checks.json. All 16 VELDO-0152 behavior rows pass normally and in the
specified clean gate environment. red-at-16a91069.json records all 16 red by assertion on the
unchanged starting tree. No row reports more than once.

- AC1: ticket-key, name-is-a-hint, request-field and prefixes cover both sources, unique/shared/unknown
  prefixes, explicit project precedence and project names retained only as hints.
- AC2: factory-inbox and factory-refusals cover zero, one and two ordinary projects, the scoped member,
  arbitrary wording, factory-field refusal, the member with no project and a store with no factory record.
- AC3: new-project, existing-project, asked-only-when-unclear, answers, runner-input and read-and-report
  drive the factory pass and dispatched PM, all route states, channel questions, offered names and keys,
  other answers kept for the next run, current-member API authority reads and actual loopback reports.
- AC4: scope-refusal, malformed, stale and factory-refusal cover named rejection with unchanged proposals,
  including a proposal routed while the fake PM was running.

Suites run one at a time, normally and in the clean environment: 0152, 0126, 0136, 0133, 0130,
0077, 0078, 0150, 0079, 0076, 0149, 0128, 0088, 0186, 0085, 0151, 0169 and 0168.
Sixteen pass in both environments. The remaining rows are inherited: 0169 census/writers and
0168 intake/delivery. Both were reproduced with their unchanged suites in a git archive of
16a91069. The 0169 paused-disposition control now passes. No inherited failure was suppressed.

static-checks.json records passing validation, Git boundary, zero bad mutation anchors, whitespace,
engine-copy equality and the base-relative footprint. The supplied origin/main footprint checker
passes with 0152 plus the inherited 0088 and 0151 footprints; 0152 alone reports inherited changes.

Eleven finding-152 mutants are registered with unique exact anchors and parseable Python. Their
execution and rejection results are intentionally not claimed. The full selftest, mutation runners
and verify.sh were not run. The install-and-run suite, which invokes verify.sh, was not run; the
0186 asset census and the scaffold registration cover the new installed route module here.
