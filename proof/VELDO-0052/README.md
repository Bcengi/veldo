# VELDO-0052 proof

Shared floor eligibility for Release 1 stage 1 of PLAN-0019 revision 3 (W37). Specification status,
policy and every other specification are unchanged. Branch `build-veldo-0052`, built on main d5ce308.

## What landed

**One service, every entry.** `.veldo/control_eligibility.py` (mirrored byte-identically in
`engine/.veldo/`, laid down by `init_scaffold.py`) is the shared eligibility service. `Gate` reads the
real control store (VELDO-0023) inside one read transaction and returns a named decision for one
station and one unit. Station predicates are VELDO-0021's `ENTRY_PREDICATES` with current admission
added to every station (R52 excludes unadmitted work from dispatch, R69 invalidates admission on a
scope change). Review asks the same draft-plan, decision, dependency and admission questions as
build, plus reviewer independence. Predicates this release cannot evaluate refuse by name
(`missing_authority:unsupported/<name>`), never pass by default.

**The registered entries** (`REGISTRATIONS`, checked against the actual call sites by AST):
frontier `claimable._add` (selection), work loop `WorkLoop._claim_next` (claim, before and after the
claim), plan `cmd_run_check` (direct execution), `Executor.run` (direct execution),
`Dispatcher._dispatch_build` (build), `Dispatcher._dispatch_review` (review), `Dispatcher._land`
(publication) and `CallHandle.invoke` (provider request, every subscription CLI call).

**Enablement.** `gate_for()` is the one resolution each entry calls. A wired Gate is used. A
repository carrying a VELDO-0029 enrollment binding with no Gate wired stops by name
(`eligibility_required`), the same shape as claim.py's `authority_required`; a Git that cannot run
is `enrollment_unanswerable`, never "not enrolled". Unenrolled trees keep pre-factory behavior, so
no existing caller changed.

**Tickets.** Each decision carries the version and digest of every input it consumed: unit, backlog
item, governing plan, admission, project, authority, claim, each dependency and its complete receipt
collection, and the decision, blocker and approval collections for the unit. The next station passes
it back and any moved input is `stale_input:<label>`, whatever the project version. The claim's own
lifecycle writes (claim record, unit and backlog `state`) are station outputs: they are compared by
definition digest and ownership is decided fresh, through `control_claim.ownership`, so a clock
disagreement is the named stop `clock_uncertain`.

**Completion.** `Gate.completion()` is the one reader of the four facts from stored
`completion_receipt` entities, each judged by `completion_contract.fact_problems` for the unit's
current accepted revision; landed also needs the exact landing receipt
(`landing_receipt_problems`). `completion_status()` feeds that answer to the frontier and plan status
maps, so "shipped" there means a landed revision; `work_state.completion_view()` reports the four
facts beside its own DONE (manifest plus passing verdict), which it names proof accepted.

**Calls.** `StationCalls` hands the build and review stations a `CallHandle`, their only path to a
subscription CLI. Every initial, retry and follow-on call is decided (`provider_request`, with the
station decision as ticket) and then passes VELDO-0036's `InvocationGuard`, which commits the
reservation before launch. A dispatcher with the floor enabled and no `StationCalls` stops with
`reservation_required`.

## Criteria, rows and driven mutations

Suite `scripts/suites/60_veldo_0052_eligibility.py`, 32 rows (17 assertions and 15 `ran/` rows, one
per region, which show a mutation reddened its row by a failed assertion and not by raising). One
temporary tree is both the repository the entries read and the installed `.veldo` they run from.
The checkout says every scenario is ready, planned and unblocked, and without a Gate the frontier
offers all six, so each refusal is attributable to the store-backed decision.

Every mutation below is registered as finding 52 in `scripts/check_teeth_mutations.py`, applied to
a temporary copy, and required to turn its named row red while the unmutated copy is green. All 22
reddened their target rows with their regions completing (`mutations.json`, each diff in
`mutations/`).

**AC1, every enabled entry.** Rows `eligibility/registrations-from-call-sites`,
`eligibility/entry-frontier`, `entry-work`, `entry-work-rechecks`, `entry-plan`, `entry-executor`,
`named-refusals`, `entry-dispatch-build`, `entry-dispatch-review`, `entry-publication`,
`enrolled-entry-stops`. Scenarios against the real store: absent admission, draft governing plan,
unresolved dependency, unresolved decision, stale scope and valid. Launch counts: only the valid unit
is offered, dispatched, cleared, built, reviewed and landed (`observations.json`, `launches`).
`named-refusals` also pins the station-specific answers: a builder that does not hold the claim, a
reviewer who is the producer, and a claim whose heartbeat is an hour ahead (`clock_uncertain`).
- Declared falsifier `eligibility-review-bypass` (direct `_dispatch_review` without its decision):
  red `entry-dispatch-review` (blocked items launched the reviewer).
- Second mutation `eligibility-review-as-provider-request` (review decided without the draft-plan,
  decision and dependency questions): red `entry-dispatch-review`.
- Further driven rows: `eligibility-frontier-bypass` (entry-frontier), `eligibility-executor-bypass`
  (entry-executor), `eligibility-plan-bypass` (entry-plan), `eligibility-build-bypass`
  (entry-dispatch-build), `eligibility-publication-bypass` (entry-publication),
  `eligibility-work-no-preclaim-decision` and `eligibility-work-no-postclaim-recheck`
  (entry-work-rechecks), `eligibility-enrolled-default-runs` (enrolled-entry-stops),
  `eligibility-unregistered-work-entry` (registrations-from-call-sites), `eligibility-ignores-scope`
  (named-refusals).

**AC2, current inputs after selection.** Row `eligibility/stale-input`. After selection a
dependency's landing receipt is superseded, and a separate unit's admission is re-accepted with its
predicate still true; the project version stays fixed. Build, review, publication and claim each
refuse by name (`stale_input:receipts/VELDO-9110`, `stale_input:admission`) with zero launches,
while a fresh decision for the re-accepted unit is eligible.
- Declared falsifier `eligibility-status-only-recheck` (check only the unit's own record after the
  prerequisite is withdrawn): red `stale-input`.
- Second mutation `eligibility-recheck-ignores-collections`: red `stale-input`.

**AC3, completion readers.** Rows `completion/readers-agree` and
`completion/consumers-from-call-sites`. Real receipts for build-only (with a manifest, a passing
verdict and shipped status text), proof accepted, landed, landed for another revision, landed with
objective, and a landed fact lacking the exact landing receipt. A fresh process reads each fact
through the reader, the frontier, plan, work_state and the eligibility dependency predicate; only
the two exact landings satisfy a dependency, and work_state reports proof accepted without landing.
- Declared falsifier `completion-manifest-verdict-landed` (conclude landed from a manifest plus
  passing verdict): red `readers-agree`.
- Second mutations `completion-frontier-reads-status-text` and `completion-any-revision-lands`: red
  `readers-agree`; `completion-unregistered-consumer`: red `consumers-from-call-sites`.

**AC4, pre-call usage caps.** Rows `reservations/forbidden-call-observation` and
`reservations/unknown-usage-retained`. All 12 paths (build and review, Claude Code and Codex,
initial, retry and follow-on) under an account, a project and a unit allowance of 12 invocations:
the first 12 launch with their reservation already committed, the next 12 refuse
`usage_cap:<scope>:invocations` and the observed receiver sees nothing more. An unreported call
keeps follow-on and retry from launching (`unknown_allowance:tokens`) until its final report.
- Declared falsifier `reservation-review-follow-on-bypass`: red `forbidden-call-observation`.
- Second mutation `reservation-refusal-fails-open`: red `forbidden-call-observation`;
  `reservation-retry-bypass`: red `unknown-usage-retained`.

**Observability.** Row `eligibility/observations`, driven by `eligibility-refusals-not-pending`.
Each decision records operation, domain, repository, unit, decision id and the one it follows,
watermark, accepted input versions, outcome, named refusals and taxonomy (invalid input, missing
authority, stale subject, unavailable service, missing evidence, unknown outcome); `status()` counts
accepted and refused and lists units whose latest decision refused. In-memory diagnostics are
bounded; the durable sink is the `observe` callback.

## Narrowest seams, stated

These are consumed, not implemented here. The store records their plain entities; the services that
write them are other items.
- Admission (`admission:<unit>`, scope digest) stands in for VELDO-0022's Admission Service.
- Governing plan (`plan:<id>`) and decisions (`decision` entities with `blocks` and `state`); exact
  decision-record consumption is VELDO-0054, architecture refusals at these same registrations are
  VELDO-0053.
- Authority (`authority:<domain>`, state and generation) and approvals (`approval` entities) for
  publication.
- Completion receipts (`completion_receipt` entities); VELDO-0057 will write landing receipts.
- Usage caps are VELDO-0036 as landed. VELDO-0062 (credentials and live usage) is absent on main.
- The build and review launches are counters behind the dispatcher's existing seams; this qualifies
  no live engine.

## Cost and verification

Suite 60 runs in 0.66 s (`observations.json`, `suite_seconds`). `--finding 52` drives 22 mutations
in 32.7 s here (44 suite runs of about 0.74 s); in the gate's mutation stage that is about 36 worker
runs across 8 workers, a few seconds. Well under the 60 s limit. Targeted checks run on this
branch: `python3 -B scripts/selftest.py --suite 60_veldo_0052_eligibility` (32 passed),
`python3 -B scripts/check_teeth_mutations.py --finding 52` (22 rejected), `python3 .veldo/validate.py
all`, `bash scripts/check_generated.sh`, `bash scripts/check_template_sync.sh`, lint, docs and
install-and-run, plus the existing suites that load the modules touched here. The full gate is run
by the lead.

`drive.py` regenerates `observations.json` from one run of the suite.
