# VELDO-0152 builder evidence

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
