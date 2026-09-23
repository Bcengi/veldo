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
claim), plan `cmd_run_check` (direct execution), `Executor._decide` (direct execution, and build
and review for every launch the executor makes; see the 2026-09-23 section), `Executor._decide_calls`
(provider request, before each executor launch; see the second check below),
`Dispatcher._dispatch_build` (build), `Dispatcher._dispatch_review` (review), `Dispatcher._land`
(publication) and `CallHandle.invoke` (provider request, every subscription CLI call).

**Enablement.** `gate_for()` is the one resolution each entry calls. A wired Gate is used. A
repository carrying a VELDO-0029 enrollment binding with no Gate wired stops by name
(`eligibility_required`), the same shape as claim.py's `authority_required`; a Git that cannot run
is `enrollment_unanswerable`, never "not enrolled" (as first built, a Git that ran and FAILED still
read as not enrolled; fixed on 2026-09-23, below). Unenrolled trees keep pre-factory behavior, so
no existing caller changed. The command-line entries resolve through `entry_gate()` instead, which
builds the Gate from the enrollment binding (2026-09-23, below).

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

Suite `scripts/suites/60_veldo_0052_eligibility.py`, first built with 32 rows (17 assertions and 15
`ran/` rows, one per region; 46 rows after the 2026-09-23 fixes, which show a mutation reddened its row by a failed assertion and not by raising). One
temporary tree is both the repository the entries read and the installed `.veldo` they run from.
The checkout says every scenario is ready, planned and unblocked, and without a Gate the frontier
offers all six, so each refusal is attributable to the store-backed decision.

Every mutation below is registered as finding 52 in `scripts/check_teeth_mutations.py`, applied to
a temporary copy, and required to turn its named row red while the unmutated copy is green. All 22
first registered (36 after 2026-09-23) reddened their target rows with their regions completing (`mutations.json`, each diff in
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

As first built: suite 60 ran in 0.66 s and `--finding 52` drove 22 mutations in 32.7 s. After the
2026-09-23 fixes: suite 60 runs in 1.16 s (`observations.json`, `suite_seconds`; about 0.3 s of it is
the five real command-line processes of the production-entry row, run concurrently) and
`--finding 52` drives 36 mutations in 85 s here (72 suite runs of about 1.2 s), which in the gate's
mutation stage (8 workers, 120 s combined budget) is about 11 s of wall time. Targeted checks run on
this branch: `python3 -B scripts/selftest.py --suite 60_veldo_0052_eligibility` (46 passed),
`python3 -B scripts/check_teeth_mutations.py --finding 52` (36 rejected), `python3 .veldo/validate.py
all`, `bash scripts/check_generated.sh`, `bash scripts/check_template_sync.sh`, lint, docs and
install-and-run, plus the existing suites that load the modules touched here. The full gate is run
by the lead.

`drive.py` regenerates `observations.json` from one run of the suite.

## 2026-09-23 review: six reproduced defects and the production entries

An independent reviewer reproduced six defects in the branch as built (0ea33e3) and suspected a
seventh. Each was fixed test first: a suite row that fails its assertion over 0ea33e3's production
modules, then the fix, then two registered mutations for finding 52, one reintroducing the defect and
one a different way to break the same row. One commit per defect (2c25c03, 62610e1, 0bad5f1, 428ced5,
6056b4e, 12526d0, 75066f8).

**Recorded red at 0ea33e3.** `red.py 0ea33e3` runs the current suite over 0ea33e3's copies of every
module the suite installs by name (the same production-copy anchors the mutation driver substitutes,
plus bin/veldo). One fixture line constructs an interface 0ea33e3 did not have (StationCalls with the
runner's account and clock) and is replaced by 0ea33e3's constructor; that is the only substitution,
and the record names it. Result in `red-0ea33e3.json`: all seven new rows fail by assertion with every
region completing (no `ran/` row red), and so do two existing rows whose assertions were tightened
(`entry-executor`, `entry-dispatch-build`). The recorded observations show each defect itself: the
direct executor built with no handle and launched a reviewer; a broken .git/config read as unenrolled
and the frontier offered all fourteen specs; `veldo status` could not be asked for a Gate; the loop's
unit carried no dispatch and nothing launched; the landed standalone unit was offered for build and
the landed review unit for review; every command-line entry died with `eligibility_required`. Rows
a and b could not reach their second half at 0ea33e3 because the executor took no claim-holder
context; the reviewer's own scripts show those two defects there.

**a, the direct executor's station decisions and reservation.** `Executor.run` with a Gate and no
CallHandle built with no handle and launched its reviewer with no review-station decision, where the
dispatcher stops with `reservation_required`. The executor now takes the runner's StationCalls and a
claim-holder context: with the floor enabled and no StationCalls it stops by that same name; every
build launch asks its own station (direct execution, or build when the dispatcher drives it) and
every review launch asks the review station, reviewer independence included, before any reviewer
exists; builder and reviewer each get a CallHandle reserved against their own dispatch. Row
`eligibility/executor-station-decisions`: without StationCalls, `Stopped(reservation_required)` and
nothing built or reviewed; with them, the run reaches ready and the three calls (one build, an
initial and a follow-on review call) launch with their reservations already committed; a reviewer
who is the producer is refused before review with the build already done. Mutations
`executor-launches-unreserved` (reintroduced) and `executor-review-skips-review-station`.

**b, a recheck before every launch.** The executor decided once before its loop, so cycle 2 built
after admission was withdrawn during review. Every launch now re-decides its station over the
complete current read set against the last accepted decision as its ticket. Row
`eligibility/executor-rechecks-every-launch`: admission withdrawn during review halts cycle 2 before
its build (`stale_input:admission; missing_authority:admission`), and admission re-accepted with its
predicate still true halts it too (`stale_input:admission`), one build each. Mutations
`executor-decides-once` (reintroduced) and `executor-recheck-without-ticket`.

**c, a Git error is a stop.** `enrolled()` read any git error as "not enrolled", so a malformed
.git/config removed the eligibility stop. Only a directory where Git's own discovery finds no
repository at all (no `.git` or bare git directory at it or any ancestor on the same filesystem) is
now unenrolled; a failing Git anywhere else is `enrollment_unanswerable`. Nothing is parsed from Git's
messages. Row `eligibility/enrollment-git-error-stops`: the root, a subdirectory and the frontier
stop by that name with the config broken; a plain directory is unenrolled; the restored config is
healthy. Mutations `enrolled-git-error-reads-unenrolled` (reintroduced) and
`enrolled-discovery-ignores-ancestors`.

**d, one completion reader for `veldo status`.** `runstatus._burndown` read status text and answered
in an enrolled repository where plan.py stops. It now reads plan.py's own `_status`, and the read
model reports the stop by name (`burndown_stopped`) with the rest of the model intact. runstatus.py
joined the footprint with a history line. Row `completion/status-reader-agrees`: with the Gate, every
burn-down item equals plan status's own item state and a shipped file without a landing receipt is
not shipped; enrolled with no Gate, plan status and `veldo status` both stop with
`eligibility_required`. Mutations `status-reader-reads-status-text` (reintroduced) and
`status-reader-drops-the-stop`.

**e, the real path's dispatch identity.** The unit WorkLoop hands the Dispatcher never carries a
dispatch identity, so every subscription call reserved against `dispatch=None` and was refused: the
work loop could make no model call. The runner's StationCalls now opens each dispatch
(`open_dispatch`), reserving its VELDO-0036 worker slot under the runner's account and the unit's
accepted project, and the dispatcher opens one for build and one for review; a handle with no
dispatch refuses by name. A slot is retired only by the supervisor's actual lifecycle observation
(`Reservations.retire`), so until then it counts against capacity, the conservative direction.
Row `reservations/work-loop-dispatch-identity` drives WorkLoop to Dispatcher to executor to builder
with nothing hand-built: the units the loop handed over carry no dispatch key, the build call
launches with its reservation committed, and its worker slot names this domain, repository, the
runner's account, project p1 and the unit. Mutations `dispatch-without-identity` (reintroduced) and
`dispatch-identity-not-reserved`.

**f, every lane through the completion map.** `_is_standalone_build`, and the review lane beside it,
read front matter directly, so a landed standalone unit whose file still said ready was offered for
rebuild. Both lanes now ask the status map, which with the floor enabled is the completion reader.
Row `completion/landed-units-not-reoffered`: a landed unit saying ready and a landed unit saying
review are offered for nothing, while an unlanded ready one is still offered. Mutations
`standalone-lane-reads-front-matter` (reintroduced) and `review-lane-reads-front-matter`.

**The production entries build the Gate.** Suspected by the reviewer and confirmed: nothing in
production built a Gate from the enrollment binding, so every command-line entry in an enrolled
repository stopped with `eligibility_required`. `control_eligibility.entry_gate` is now the one
production construction, called by `veldo work` and `veldo fleet`, `veldo_run`, the executor, frontier
and plan commands and `veldo status` (command and served view). In an enrolled repository it reads the
binding once and verifies that same record with VELDO-0029's `verify_binding` (signature over the
binding's own fields, repository identity, clone and host), then opens a read-only Gate over the
store, domain, repository and authority generation the binding names. The verifier is what the HOST
trusts, never the workspace: `HostTrust`, installed at `$XDG_CONFIG_HOME/veldo/host_trust.json`
(else `~/.config/veldo/host_trust.json`), names the host identity and an OpenSSH allowed-signers file
for the `veldo-enrollment` signature namespace, checked with `ssh-keygen -Y verify`. No host trust
is `host_trust_required`; a binding that does not verify is `enrollment_refused:<reason>`; an
unreadable store is `unavailable_service:store`. bin/veldo and status_server.py joined the footprint
with a history line. Row `eligibility/production-entries-build-the-gate` enrolls the fixture with a
real ed25519 key and signature and runs the real commands as processes: the executor reaches
`reservation_required` (its station decided eligible), `plan.py run-check` refuses VELDO-9101 by
`missing_authority:admission`, `veldo work` reaches VELDO-0031's `authority_required` (the claim),
`veldo status` shows a burn-down from landing receipts (a shipped file without one counts zero), a
host with no trust installed stops with `host_trust_required`, and no process says
`eligibility_required`. In process, the built Gate decides from the store, a binding re-addressed to
another domain is `enrollment_refused:signature_invalid`, and a host with another identity is
`enrollment_refused:host_binding_stale`. Mutations `entry-gate-not-built` (reintroduced) and
`entry-gate-unverified-binding`.

**Existing rows and mutations adjusted.** `entry-executor` now drives the executor with StationCalls
and ceilings for every scenario, so only the station decision can hold a unit back; the falsifier
`eligibility-executor-bypass` now bypasses the executor's station decision itself, because the
per-launch recheck (b) catches a bypass of only the first decision. `entry-dispatch-build` also
asserts that a refused unit is given no worker slot, which is the observable part of the
dispatcher's own build decision now that the executor rechecks the build station. The anchor of
`reservation-refusal-fails-open` moved with the one refusal-naming helper both reservation paths use.

**The reviewer's scripts against the final code.** None of the six prints BUG. c and f run to their
end with the fixed behavior (`Stopped(enrollment_unanswerable)`, both landed units offered nothing).
a and b end at `Stopped(reservation_required)` from `Executor.run` before any build, the dispatcher's
own stop; d prints its first comparison and then stops with `eligibility_required` where its script
calls `_burndown` in an enrolled repository with no Gate; e's harness constructs StationCalls with no
account, so the dispatcher refuses `reservation_required:account` before any build. Because a, b, d
and e therefore end before the comparison they were written to make, the same four scenarios were
also driven through the new interface (StationCalls with an account, the claim-holder context,
`_burndown` with the Gate): a reaches ready with both launches reserved first, b halts cycle 2 at
eligibility after one build, d's burn-down says `shipped_without_landing_receipt` exactly as plan
status does and the enrolled reader reports `burndown_stopped: eligibility_required` with no
burn-down, and e's builder call launches with its reservation committed. No BUG line in any run.

**Not done here, stated.** (Superseded by the second check below: a worker slot is now retired
when its launch returns.) Retirement of a dispatch's worker slot needs the supervisor's lifecycle
observation, which no production path supplies yet; slots stay counted until then. A direct run
makes subscription calls only for a claim holder, because `provider_request` requires
`claim_current`. `veldo work` in an enrolled repository now stops at VELDO-0031's
`authority_required` until an authority claim client is wired. claim.py's own `_authority` still reads
a failing `git rev-parse` as "no ledger enrollment"; it is VELDO-0031's module and outside this
footprint.

## Second independent check (r52b): the slot leak, host trust inside the workspace, named halts

A second independent check reproduced two defects in 668d104, and the lead added a third. A probe
from the same check showed a fourth. Main was merged first (2503c81: registry conflicts kept both
sides, one `--finding` list, requires.json regenerated). Each was fixed test first: a suite row that
fails its assertion over 668d104's production modules, then the fix, then registered mutations for
finding 52, one reintroducing the defect and at least one a different way to break the same row.
One commit per defect: 8130d75 (g), 1572ae5 (h), f85d5f0 (named halt), 01e1343 (probe i).

**Recorded red at 668d104.** `red.py 668d104` (`red-668d104.json`) runs the current suite over
668d104's production modules with no substitution at all, since 668d104 already has the runner's
StationCalls; red.py now substitutes its one fixture line only for a commit that predates it. The
four new rows and the tightened work-loop row fail by assertion, and no region raised (no `ran/`
row red). The observations show each defect: every dispatch of a one-slot unit after the first
refused `usage_cap:unit:capacity` with one slot held and never retired; every host trust
naming a signers file inside the workspace built a Gate; each refusal inside a launch was raised.

**g, a worker slot for every dispatch, forever.** `Dispatcher._dispatch_build` reserved the build's
worker slot before the executor's resolve, plan check and recheck, and nothing in production called
`Reservations.retire`, so every dispatch, launched or not, held capacity until the account ran out.
`StationCalls.launch` is now the one scope a build or review launch runs in. The executor enters it
only after every pre-launch decision passed (so a halted dispatch reserves nothing), one launch per
scope (a second build cycle gets a slot of its own, and the build's slot is free again before the
review opens its own); the dispatcher's review enters it after the review decision. When the
launched call returns, normally or by any exception, `close_dispatch` retains the calls' exposure
and retires the slot. Exposure stays conservative: each call with no final usage report gets one
final report carrying no usage, which leaves it UNKNOWN, with its reserved invocation and wall time
still charged and its tokens and messages still unknown (VELDO-0036 AC3, and AC4's "retained
unknown-usage reservations"). The retirement's lifecycle observation is the runner's own: the
launching call returned in this process (`observer: runner`, `basis: launch_returned` or
`no_call_launched`, and the number of calls). The VELDO-0040/0041 supervisor is not built yet; once it
exists it owns this observation and retirement, and `close_dispatch` is where it plugs in. A retirement
the service refuses leaves the slot held and is recorded, never raised. Row
`reservations/dispatch-slot-retired`: with a unit ceiling of ONE slot, halts at resolve, plan check
and recheck hold no slot; a builder that makes no call, then two that each make one, each hold one
slot and retire it (0, 1 and 1 calls); the unit's balance is capacity 0, invocations 2, wall time 20,
both calls UNKNOWN with tokens and messages unknown; two review dispatches of the same one-slot unit
both ship; a direct run of another one-slot unit reaches ready with its build's and its review's
slots both retired. `reservations/work-loop-dispatch-identity` now also requires the real path's
slot retired. Mutations `slot-opened-before-prelaunch-halts` (reintroduced),
`slot-kept-after-launch-returns` and `slot-close-zeroes-exposure` (the close settles the calls as not
executed). The anchor of `dispatch-without-identity` moved into `StationCalls.launch`, where the
identity is now opened.

**h, the workspace vouching for itself.** HostTrust's docstring said the workspace's own
.veldo/keys cannot vouch for itself, but a signers path inside the workspace, or a relative one
(resolved against the process's directory, the workspace), built a Gate. The signers path must now be
absolute (`host_trust_refused:signers_not_absolute`, at construction) and resolve, after every
symlink, outside the workspace: the path it was named by, its working tree, its git common directory
and, for a clone whose common directory is its `.git`, that clone's working tree
(`host_trust_refused:signers_inside_workspace`). The resolved file is the one read, so a symlink
retargeted after the check cannot substitute another. Row `eligibility/host-trust-outside-workspace`:
the fixture is enrolled with a real ed25519 signature and every signers file below holds the GENUINE
signer's key, so only its location decides. Inside the workspace, relative (run from the
workspace), a host symlink into the workspace, and a file in the git directory are refused by those
names; the host's own file and a host symlink to it build the Gate. Mutations
`trust-accepts-workspace-signers` (reintroduced), `trust-accepts-relative-signers` and
`trust-judges-unresolved-path`.

**A refusal inside a launch is a named halt.** A refusal at a launched call's own boundary (its
usage reservation, or the provider_request decision over an input that moved during the launch) came
out of `Executor.run`, and out of the dispatcher's review, as a raised `Refused`. The executor now
finishes halted at the eligibility step (`call refused during build: <every refusal>`), the
dispatcher's build reports that halt, and its review returns the station's named refusal without
shipping, landing or changing the spec's status. Row `eligibility/provider-refusal-halts`: a
direct build whose call exceeds a zero invocation ceiling, and one whose builder withdraws admission
before calling, halt by name; the same through the dispatcher's build; the dispatcher's review
returns refused with `usage_cap:unit:invocations` and the spec still in review; nothing launched and
every slot retired. Mutations `provider-refusal-escapes-run` (reintroduced),
`provider-refusal-escapes-review` and `provider-refusal-halt-unnamed`.

**i, a launch decided at the boundary its calls face.** The check's probe i printed BUG on the fixed
code as first rerun: after another holder took the claim during review, a direct run's cycle-2
builder was entered and only its first call was refused. Direct execution asks no claim question,
but every call it makes does. Every executor launch now also asks provider_request's predicates
(admission and the claim) before its dispatch is opened (`Executor._decide_calls`, registered). It
carries no ticket: staleness against the last decision stays the station recheck's question (b),
and each call asks it again. Row `eligibility/launch-decides-its-calls`: the claim taken during
review stops cycle 2 before its builder (`missing_authority:claim`, one build), and a unit the run
does not hold is never built. `entry-executor` now claims every scenario, so its station-bypass
falsifier is not masked by this boundary. Mutations `launch-skips-call-boundary` (reintroduced) and
`launch-call-boundary-first-cycle-only`.

**The check's scripts against the final code.** Pointed at this branch's tree, none of the four
prints BUG. g: the dispatch halted at plan check holds no slot and the second dispatch builds. h:
the inside path stops with `host_trust_refused:signers_inside_workspace` and the relative one with
`host_trust_refused:signers_not_absolute`. smoke: no refusal, no worker held. probe i: open decision,
draft plan and claim taken each stop cycle 2 before its build, and the unrelated write reaches the
second review.

**Cost.** Suite 60: 54 rows (28 assertions and 26 `ran/` rows), 1.3 s (`observations.json`,
`suite_seconds`). `--finding 52`: 47 mutations rejected in 129 s here (94 suite runs of about 1.35 s),
under the gate's mutation-stage cap, which now scales with the registered inventory. Targeted checks
on this branch: suite 60 and every suite that loads the executor, dispatcher or eligibility module
(01, 02, 03, 06, 07, 09, 11, 12, 13, 19), `--finding 52`, `validate.py all`, `check_generated.sh`,
`check_template_sync.sh`, `check_lint.sh`, `check_docs.sh`. The full gate is run by the lead.
