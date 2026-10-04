# VELDO-0162 builder evidence

Current review fixes start at 59410582 on build-veldo-0162. No push, gate, live
model, real credential or external service is used. Status remains ready;
independent review, mutation execution and merged-tree verification are pending.
Earlier implementation evidence from 08d7edd3 is retained as historical evidence.

The configuration route executes Configurations.save. Team saves execute the
edge-verified Teams command: an owner's save becomes current immediately, while
another member's proposal waits for the owner's settled answer. Default teams
are immutable revisions; inheritance reads the revision the answer named.

Team request commands now use pm, which real factory setup already enrolls with
all-project scope and possession of its command signing key. Qualification's
requester remains scoped to channel-qualification. There is no journal-principal
fallback and no setup production change or footprint extension. The fixture runs
real factory setup, keeps those enrolled memberships and keys, and supplies its
actual qualification requester to ServiceApi. It no longer injects team-service.
Amendment aliases include the team version, distinguishing successive proposals
of the same roster while preserving repeat submission of a pending proposal.

Both API answers and service publication consume settled team requests through a
registered store command. The durable team_application receipt retains the result,
including refusal or a named application exception, so later journal advances and
consumer reconstruction do not retry it. Application and scan exceptions cannot
suppress API hints. The API answer returns team_application through the existing
redactor. Team read scope checking remains VELDO-0164 work.

Suite 94_veldo_0162_configuration_routes retains all twenty original rows and
adds five rows, plus the separate 0172 fake/capture assertion: 26 checks total.

* AC1: configuration/revisions compares all fields of two stored and API-read
  revisions, including Atlassian catalog references, native tools, skills,
  instructions, settings and load modes. Unauthorized, stale and invalid saves
  store nothing and return named refusals.
* AC2: team/roundtrip saves the required roster and a specialist with a configuration
  reference. team/stale-team preserves the current team on stale input.
  team/staffing checks missing and unresolved references and incomplete staffing,
  including the actual owner requests returned with each refusal.
* AC3: owner-save, decider and unverified-assertion prove immediate owner acceptance,
  its verified decider and both signature checks. owner-answer proves the exact
  brief and target, pending repeat reuse, settled API amendment and the returned
  team_application. telegram exercises the service publication hook. decline and
  other-request preserve the accepted revision on rejection or a different target.
  setup-requester proves real setup's narrow qualification and all-project PM
  enrollments, and opening a member's request. reproposal declines then proposes
  the same roster again: a new request opens and its pending repeat reuses it.
  consumed checks stable team observations and refusal metrics across three actual
  configuration journal advances and a reconstructed consumer. application-exception
  proves a per-request fault is recorded once and consumed; a separate scan fault
  is logged. Both send the journal hint to a real local Unix socket subscriber.
* AC4: default/history checks immutable revisions and the head. default/refusals
  checks stale, unauthorized and invalid saves. default/named-revision applies the
  answered older revision after a newer save, and refuses a different displayed
  brief. default/staffing gives an underbudget project no team and returns a request.
* Shared: routes/contract compares operation, route, action and command registrations
  and checks session and actor-body refusals. routes/redaction checks generated
  credential text in both team reads and returned team applications. install/assets
  compares and lays the canonical modules. format/fake-lines checks generated CLI
  assets through the 0172 constructors and format observer at teardown.

The fixture uses generated OpenSSH and ES256 keys, real setup and signed membership,
capability, catalog, skill, project, request, settlement and passkey commands, SQLite,
and production ServiceApi construction. Its API handler uses a service-call proxy;
the existing 0130 suite supplies transport regression coverage. Telegram uses a
loopback Bot API stand-in. Setup does not start the installed service. Fake Claude
and Codex assets are built through proof/VELDO-0172/fake_formats.py, installed by
setup and read back through conform_fake at teardown. No real engine runs.

red-at-59410582.json records the final suite against unchanged archived production,
with only current test and fixture files overlaid. Eleven rows fail by assertion,
including setup-requester; no journey raises. Some downstream request rows fail
because the initial request could not open. This is not an isolated mutation run.
The earlier red-at-08d7edd3.json remains the original twenty-row red record.

mutations.json retains all nineteen existing mutations and adds six: narrow setup
requester, reused request alias, missing consumption receipt, unrecorded application
exception, publication exception suppressing hints and hidden API team application.
Every exact diff and source digest is refreshed. The anchor-only check reads registry
definitions, loads no tests and executes no mutations: zero bad anchors. No mutation
rejection is claimed; all twenty-five await reviewer execution.

checks.json and static-checks.json retain the previous build's records and add this
review-fix run separately. Only selected suites are run sequentially. Partial selftest
success returns 2 by design and is not gate evidence. The full selftest, mutation
runner, gate and landing stamp are reserved for the reviewer. No gate byproducts
belong to this change.

2026-10-04, suite 93 performance follow-up (base df603ca5): intake-performance.json
records three unprofiled before runs (92.02, 90.93, 90.16 seconds) and three after
runs (38.98, 38.98, 39.62 seconds). intake-profile-before.txt retains the cProfile
summary. These are selected-check measurements, not a gate pass or landing stamp.

The suite compiles its immutable isolated module tree once, retains the caller's
bytecode setting when reading the mutation catalog, validates the unchanged real
runtime once, and restores a signed SQLite baseline between independent refusal
rows. Restoring requires no live launches and clears cycle input caches; real
commands, graph subprocesses, Runner dispatches and emitted fake lines remain.
All 36 assertion call sites have identical syntax trees to the baseline. All 47
checks remain: 26 shared, 20 intake groups including format/fake-lines, and one
fake/capture check comparing nine lines.

Two production costs are removed too. The factory uses the existing assignment
reader loaded once instead of importing the full PM workflow on every scan; it
still reads current records each time. Graph runtime Git discovery captures its
small output so subprocess communication waits on pipe readiness instead of timed
waitpid polling. Exit-code decisions, all isolation checks and the timeout remain.
Both canonical files and their repository copies match. No worker budget changes.

The requested sequential regression checks pass: suites 93, 82, 94 and 50 have
47, 30, 52 and 30 passing checks, with no failures. Validation and the Git boundary
check exit zero. Finding 152 is running separately with one worker; its final
result will be recorded here. No full selftest or gate runs in this worktree.
