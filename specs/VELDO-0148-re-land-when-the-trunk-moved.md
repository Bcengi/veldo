---
schema: veldo.spec/v1
id: VELDO-0148
title: A land refused because another factory moved main is re-landed on the new tip, re-merged and re-gated, and nothing ever forces
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W108
plan_revision: 4
depends_on: [VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0154]
placement: [distribution, fleet, contracts, metrics, project_runner]
protected_paths: []
footprint:
  - "engine/.veldo/control_heartbeat.py"
  - ".veldo/control_heartbeat.py"
  - "engine/.veldo/control_containment.py"
  - ".veldo/control_containment.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "scripts/suites/63_veldo_0040_containment.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_landing*.py"
  - ".veldo/control_landing*.py"
  - "packs/*/.veldo/control_landing*.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_verification.py"
  - ".veldo/control_verification.py"
  - "packs/*/.veldo/control_verification.py"
  - "engine/.veldo/control_proof.py"
  - ".veldo/control_proof.py"
  - "packs/*/.veldo/control_proof.py"
  - "scripts/suites/*_veldo_0148_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0148-re-land-when-the-trunk-moved.md"
  - "specs/index.md"
  - "proof/VELDO-0148/*"
behavior_bearing: true
observability:
  logs: >
    Record each refused publication with its watermark, the tip found and the classification, and each
    re-land dispatch with the unit, the original land dispatch it follows and the new watermark; never
    a credential.
  metrics: >
    Count publications refused as stale-subject, lease losses classified refused or unknown, and
    re-land dispatches per unit.
  traces: >
    Join each re-land dispatch to the refused publication it follows, the new candidate, its gate run
    and its compare-and-swap.
  error_taxonomy: >
    Distinguish stale subject at the listing, trunk moved after the listing, unknown publication, a
    re-merge conflict and a missing approval for the re-merged tree; none is recorded as landed.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A publication refused as `stale-subject` because the trunk moved is followed by exactly one
      new land dispatch that re-merges and re-gates on the new tip, and nothing ever forces. Set and
      completeness: Against a disposable bare remote, land a unit whose trunk another push moves before
      the listing. The effect executor refuses the publication as `stale-subject` and the original land
      dispatch ends refused, with no new attempt under it (VELDO-0057 AC3). The factory loop (VELDO-0154
      AC1) then offers the land station again as a new land dispatch: a new watermark from the new main,
      the same re-merge, the gate run again from the trusted installation on the new candidate and a new
      compare-and-swap, which lands. A clean re-merge keeps review bound to the unchanged evidence
      commit; a real conflict sends the unit back to its builder as a new build dispatch told to merge
      the new main, and that build is reviewed again. No push is ever forced. Falsifier: Leave the land
      failed after a `stale-subject` refusal, offering no new land dispatch; the stale-subject re-land
      row must fail.
    falsified_by: >
      Leave the land failed after a `stale-subject` refusal, offering no new land dispatch; the
      stale-subject re-land row must fail.
  - id: AC2
    text: >
      Claim: A lease lost to another push between the listing and the push is classified as a refused
      publication when the new tip does not contain the candidate, and only a tip that contains it stays
      unknown. Set and completeness: Against a disposable bare remote, move the trunk between the
      listing and the push. The executor fetches the after-state tip into its publication clone; a
      commit that is neither the watermark nor the candidate and does not contain the candidate is a
      refused publication (trunk moved), followed by the re-land of AC1. Separately, make the after-state
      tip contain the candidate: that result stays `unknown`, judged per push URL, and stops under its
      original dispatch with a named stop and no new attempt. Falsifier: Move the remote trunk between
      the listing and the push and record the lease loss as `unknown`; the lease-window row must fail.
    falsified_by: >
      Move the remote trunk between the listing and the push and record the lease loss as `unknown`; the
      lease-window row must fail.
  - id: AC3
    text: >
      Claim: A unit that requires an approval asks once per re-land for a fresh grant bound to the
      re-merged tree, and the old grant never publishes the new candidate. Set and completeness: Re-land
      a unit whose policy requires an approval: observe one request for the re-merged candidate tree and
      no publication until it is granted; answer it, and the new compare-and-swap lands. Present the
      approval granted for the old candidate tree to the re-land's publication and require refusal by
      name with the trunk unchanged. Ask only when every approval problem is a tree-only binding
      mismatch for a prior grant at this revision. A mixed refusal (including a missing, revoked or
      proof-mismatched approval) stays failed with its named reasons, no subject and no loop action.
      Apply a grant at most once per dispatch and never to a failed dispatch. At answer time recheck
      every prior grant before any write; a revoked or otherwise ineligible grant refuses by name.
      Falsifier: Accept the approval bound to the old candidate tree for
      the re-merged tree; the fresh-grant row must fail.
    falsified_by: >
      Accept the approval bound to the old candidate tree for the re-merged tree; the fresh-grant row must
      fail.
required_evidence: [unit, integration]
rollback: >
  Stop offering re-land dispatches: a publication refused because the trunk moved stops under its
  original dispatch as it did before this concern, and every recorded dispatch, receipt and approval is
  kept. No automatic rollback is authorized.
---

## Intent

Each person runs their own factory, and the factories meet at Git main on the shared remote. A land must
survive another person's factory moving main between the land's start and its publication, without ever
forcing a push.

## Context

W108 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5 (the factory loop it
extends, VELDO-0154, is stage 5). Section 7 of the approved
[operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram 29162) designs the re-land and gives its criterion and falsifier as an amendment of VELDO-0057. VELDO-0057
has landed with its proof, so this repository's convention puts that amendment in its own specification
that depends on it, and VELDO-0057 keeps its landed text.

What the code does today: the lander builds its candidate on a watermark, the trunk tip fetched once, and
merges the build onto it (`lander.py`). Publication is a compare-and-swap of that watermark: the effect
executor lists the destination and refuses with `stale-subject` if the trunk is no longer at the
watermark, and otherwise pushes with a lease on it (`control_effect_executor.py`). After a
`stale-subject` refusal the land is simply failed, and a failed or unknown publication stops under its
original dispatch with no new attempt (`control_landing.py`), so nothing re-lands on the new main; a move
between the listing and the push makes the lease reject the push, which the executor records as
`unknown`.

## Out of scope

A bound or backoff for a trunk that keeps moving under heavy contention (hardening); recovery of a lost or
ambiguous publication (Release 2); any change to VELDO-0057's criteria.

## What the reviewer judges

- Normal use: a colleague's factory lands on main while this factory's land is under way; the publication
  is refused because the trunk moved, and the loop re-lands the unit on the new main as a new land
  dispatch, re-merged and re-gated, and the second compare-and-swap lands. The owner sees each re-land as
  its own dispatch.
- Threat model: a refused land left failed or unknown instead of re-landed; a re-land that skips the
  re-merge or the gate on the new candidate; a forced push, or one that overwrites a trunk that moved; a
  lease loss recorded as unknown when the new tip does not contain the candidate, or as refused when it
  does; a new attempt under the original dispatch; an approval for the old tree used for the re-merged
  one; a conflicting re-merge landed without a new build and review. The owner's account, the store and
  the remote host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a trunk that
  keeps moving under heavy contention; recovery of a lost or ambiguous publication (Release 2); forged
  rows in our own store and files planted in the installed directory.

## Notes

The refused publication ends its own land dispatch; the re-land is a new dispatch under a new identity,
so VELDO-0057 AC3 ("an unconfirmed publication cannot establish completion or authorize another attempt")
holds unchanged for the original dispatch and for every unknown result. The factory loop offers the land
station again because the unit's last land ended refused; that offer is the loop's next-station rule in
the authority service (VELDO-0154 AC1), which this concern extends for a refused land. Approvals are bound
to the candidate tree, so the re-merged tree needs its own grant.

## History

2026-10-02, census review repair at 3caa6d1c: Group.retain binds each libsystemd
function by explicit attribute access and passes the bound function to checked.
All C signatures, call arguments, cleanup and named errors are preserved. The
engine copy is byte-identical. VELDO-0169 census/writers fails by assertion on
the baseline and passes after this production-only binding change; its suite
selector is 84_veldo_0169_project_handouts. The census is unchanged.

2026-10-02, report-handshake proof complete at a45269eb: all three new falsifiers
are rejected by assertion, each with only its named suite-86 row red. The manual
proof mode applies registry edits in a disposable archive and runs the suite-86
selector serially; it never executes the mutation checker. All 27 finding-148
diffs and digests are refreshed. Suites 86, 62 (dispatch), 63 (containment), 67
(heartbeat), 80, 81 and 82 (execution record) each pass alone in ordinary and
exact empty gate environments, 14 runs with zero failures and partial-run exit 2.
Requires.json is regenerated unchanged, engine/.veldo/control_launch.py matches its source,
the Git boundary passes, anchors report 0 bad, and validate.py all exits 0.
The origin/main footprint check flags 58 inherited paths already at 1ab79713;
this repair adds none outside the existing footprint. The concatenated alternate
anchor-check path is absent; the supplied scratchpad/anchor_check.py was used.
Whole selftest, gate, mutation checker and load execution remain with the reviewer
under the owner's explicit token and concurrent-gate limits.

2026-10-02, report-handshake review repair from 1ab79713: add suite-86 probes
that stop the real wrapper immediately after release, delay it past its startup
budget, and exit it before the setup report. The read-only baseline replay makes
late-wrapper and wrapper-exited red by assertion. Report-timeout is a green
baseline control because that receiver bound already exists; its falsifier is an
unbounded report poll. The repair starts the wrapper budget before its
identity report, checks it immediately before success and exec, and distinguishes
wrapper EOF from report timeout. All changes fit the existing footprint.

2026-10-02, bounded placement regression repair from 5935c652: the heartbeat
placement child now has a five-second pidfd wait and a bounded kill/reap. The
wrapper reports setup success, failure or timeout on a private pipe; the receiver
bounds that report wait and refuses containment before reporting a running engine.
The prior blocking waitpid could wait forever on a stalled move. A failed move
also used to leave the receiver reporting accepted, making containment tests wait
for engine markers that could never exist. The dedicated-group mutant exposed
that missing refusal. Placement still precedes engine exec, preserving fast exits.
Suite 86 adds production receiver probes for an absent destination and a FIFO
that never accepts the placement writer, each with its own outer timeout reported
as an assertion. Finding 148 adds falsifiers for the unbounded placement wait and
an ignored setup result. All files fit the existing footprint. Validation follows.


2026-10-02, fast-exit proof complete: implementation 58dca632 passes suites 86,
63, 67, 80, 81 and 62 serially in both ordinary and exact empty gate environments,
12 selectors with zero failures and expected partial-run exit 2. Suite 86 has
19 passing rows. Its FIFO-controlled pre-fix replay at e1009abc makes normal-exit
and fast-exit red by assertion: both zero-exit engines receive cause exit and a
terminate step while the heartbeat remains in their worker cgroup. Other rows
stay green. The saved replay predates the production edit. Registered the late
heartbeat movement falsifier; all 22 finding-148 diffs and digests are current,
with 0 bad anchors across the registry. Mutation execution, five finding-148
baselines, finding 40 and whole-gate execution remain reserved for the reviewer;
no new mutation rejection is claimed. Saved fast-exit-verification.json and
updated the proof README. Engine copies match; registration and regenerated
requires.json are unchanged. Validation and Git boundary pass. The supplied
single-spec footprint checker reports 58 inherited paths from merged concerns,
none added by this repair; checking all three merged concerns reports none
outside. The alternate scratchpadanchor_check.py is absent; the working
scratchpad/anchor_check.py reports 0 bad anchors. Gate byproducts are restored
and excluded. No protected path, other branch or worktree was changed.

2026-10-02, fast-exit review repair: extend AC1's receiver proof with a FIFO
handshake holding the heartbeat before descriptor enumeration while the real
rebuild and review engines exit. The receiver samples actual cgroup membership
before releasing the heartbeat. Add control_heartbeat.py and its engine copy to
the footprint because the wrapper must establish heartbeat cgroup membership
before exec for these clean conflict rebuild and review exits. The intermediate
child moves before forking the heartbeat; the wrapper waits for successful setup.
Containment membership, caps, descendant cleanup and stop classification remain
production decisions. No criterion changes.

2026-10-02, receiver repair verification: dcf48b53 passes suites 62 dispatch,
63 containment, 67 heartbeat, 80 Claude baseline, 81 Codex baseline and 86 re-land
in ordinary and empty gate environments, serially. All 12 selectors report zero
failures and the expected partial-run exit 2. Suite 86 has 18 rows including its
format control and fake capture. The red driver at a90e5a85 makes both new receiver
rows red by assertion with the prior rows green, then runs the original suites
and records both heartbeat rows and both strip/user-manager rows red by assertion.
The saved bisect and verification records carry the environments, summaries,
digests and limitations. All 21 finding-148 mutation records have exact current
diffs and digests; execution and finding 40 remain for the reviewer, with no new
rejection claimed. The supplied invalid_baseline label did not reproduce as a
suite-63 failure in either environment; its failing detail was requested.

The supplied anchor checker reports 0 bad anchors and no duplicate names; Git
boundary and validation pass. Both changed engine modules match, suite 86 remains
registered exactly once, and requires.json regenerates unchanged. The supplied
single-spec footprint check sees 58 inherited VELDO-0040 and VELDO-0127 paths from
the branch's merges; the repair delta has none outside VELDO-0148, and the same
checker with all three merged concerns reports none outside. The second supplied
anchor path, scratchpadanchor_check.py, does not exist; the actual scratchpad/
anchor_check.py was used. Neither a full selftest, gate, mutation driver nor load
test ran, as the explicit token rules prohibit them. Gate byproducts are restored
and excluded from commits. No protected file, other branch or worktree was changed.

2026-10-02, receiver regression repair from a90e5a85: read-only archive bisect
between f1e1abb9 and a90e5a85 identifies 0f289ab824e7aa88ef6271cb0d8a664ca676876f
as the first bad commit for suites 67, 80 and 81 in the empty gate environment.
The parent 9572210b and main f1e1abb9 pass all three; a90e5a85 fails the two
heartbeat rows and both strip/user-manager rows by assertion. The classification
change invented an exit stop for a clean adapter; the LoadState guard correctly
rejected collected scopes but exposed the lack of a reference retaining success.
The receiver now holds a private libsystemd RefUnit connection before releasing
the engine, reads the terminal result while that scope is still loaded, and
releases it on Group.close. Receiver death also releases the bus reference. The
engine does not inherit the connection. A clean adapter adds no stop cause;
actual cleanup, explicit stops, retained OOM and runtime evidence keep their
precedence. Missing manager evidence still stays unknown.

The footprint adds control_launch.py and control_containment.py with their engine
copies because AC1's real conflict rebuild and review must finish under the
receiver without losing their scope result. Suite 86 adds real rebuild/review
assertions for both regressions and finding 148 registers their falsifiers.
The footprint also adds suite 63: its empty-ordinary-after-cap-unknown controls
incorrectly demanded cause exit with no inferred stop and no stop steps. Their
exact expectation is corrected to None and strengthened to require no inferred
stop and no steps. All after-cap unknown assertions and all other containment
rows are unchanged. Finding 40's normal-exit mutation anchor follows the new
expression; its target row is unchanged. No failing heartbeat or baseline row
was edited. Suite 63 is green before and after this repair in the gate environment;
the mutation driver's invalid_baseline label alone does not identify its failing
row. Full gate and mutation execution remain reserved for the reviewer.

2026-09-29, deterministic proof repair complete: 587af58f's suite bytes pass all
16 rows in ordinary, empty gate-environment and artificial-load runs, serially
(42 with the shared preamble, zero failures, expected subset exit 2). One owned
process ran 18 busy threads on 20 CPUs during the load run, consumed 429.6 CPU-seconds
and was terminated and reaped by its exact PID. The wake no-op applied by hand to
a temporary control_service.py copy makes only reland/end-wakes-pass red by
assertion. All four reported timing failures and the conflict row remain green.
The immediate baseline 7ee372ed is a green control: its production already works.
The current suite against original ad916989 makes all 14 behavior rows red by
assertion, with the format control green. Saved both replays and manual-wake.json.
Refreshed all 19 mutation digests and exact diffs from registry syntax; only the
wake target changed, and no execution of the other 18 mutations is claimed.
The supplied footprint check reports 55 paths, none outside; anchor_check reports
0 bad anchors and no duplicate names across findings; validation exits 0. All
eight engine copies match, the suite remains registered once, requires.json was
regenerated, and the diff has no whitespace errors. Searched production writers
and readers of wakes, pass reports, signed requests and grant events together
with their suite consumers. No criterion, footprint or production changes. No
other suite, full gate or mutation checker ran; those remain for the reviewer.
Gate byproducts are restored before the final commit and excluded from this work.

2026-09-29, deterministic proof repair from 7ee372ed: suite 86 now steps the
installed Service and FactoryLoop through signed Authority requests and real
receiver pipe events. Removed the shared 100-second budget, 20-second polling
waits, shared stalled flag and teardown sleep. Completed passes precede every
state snapshot. Independent journal-driven passes prepare the behavior rows;
reland/end-wakes-pass separately asserts that real land ends start the immediate
next pass with their dispatch wakes, without a timer or another command. Retargeted
only reland148-end-wakes-nothing to that row. Production, criteria and footprint
are unchanged. Initial ordinary run: 16 suite rows, 42 including the preamble,
zero failures. Proof refresh and further checks follow in the completion entry.

2026-09-29, proof repair at 41340bc1: the once-per-dispatch row now persists a
new failed land through the station's signed open/end writer, retaining G's real
replacement subject and eligible prior grant. It asserts refusal without an approval
write or accepted event, isolating the state guard previously masked by X's missing
subject. Registered grant148-failed-dispatch-accepted against that row. Regenerated
all 19 mutation records from current production bytes using the registry's exact
replacements and zero-context diffs, including the seven stale control_service.py
records. The prior refresh claim was incorrect. No production, criterion or footprint
change. Ordinary suite 86 passes all 15 rows (41 with shared preamble, zero failures;
expected subset exit 2). Remaining proof checks follow in the completion entry.

2026-09-29, proof repair complete: ef9bbd13 also passes suite 86 in the requested
empty gate environment (15 suite rows, 41 with preamble, zero failures, subset exit 2).
The old state guard applied by hand to a temporary copy makes only
grant/once-per-dispatch red by assertion; the real module remains unchanged. Saved
manual-failed-state-guard.json with source, mutant and suite digests. The current
suite replayed against ad916989 makes all 13 behavior rows red by assertion, with
the format control green. The requested immediate baseline 41340bc1 stays green,
as expected for a proof-only repair of already correct production; its replay is
saved separately without claiming a red result. All 19 exact diffs apply and match
current source and mutant digests, including the service offset now at line 1740.
Names are unique and the supplied anchor check reports 0 bad anchors. The footprint
check reports nothing outside, validation exits 0, all eight engine copies match,
and requires.json regenerates unchanged with the suite registered once. Searched
production readers and writers of land transitions, subjects and grants. No other
suite, full gate or mutation checker ran. All 19 registry cases await reviewer
execution; only the separate manual guard experiment is newly demonstrated here.
No acceptance criterion or footprint change. Gate byproducts are excluded.

2026-09-29, adaptation after main 82b185f2: copy the runtime assets into suite 86's
temporary module tree, matching VELDO-0186's factory-loop fixture update. The existing
fake Codex already supplies its production-generated qualification record and explicit
executable binding. All 15 rows pass in the ordinary environment (41 with the shared
preamble, zero failures; expected subset exit 2). No assertion, acceptance criterion,
production module or footprint changes are needed. Empty-environment verification and
proof audits follow in the completion record.

2026-09-29, adaptation proof complete: b3e40a45 passes all 15 suite rows in the
requested empty gate environment as well (41 with shared preamble, zero failures,
expected subset exit 2). The current suite replayed against the original pre-implementation
ad916989 makes all 13 behavior rows red by assertion, with the format control green.
All 18 finding-148 mutations retain their named rows and have valid anchors and syntax;
seven control_service.py source and mutant digests and diff offsets were refreshed for
main. No mutation execution or new rejection is claimed. Searched runtime-asset writers
and readers, including scaffold, installer, setup, engine qualification and receiver
binding. All eight production modules match their engine copies. Suite registration
is unchanged and requires.json regenerated unchanged. The supplied footprint check
reports 46 paths, none outside; anchor_check reports 0 bad anchors; validation passes.
No other suite, full gate or mutation runner ran. Gate byproducts are restored before
the final commit. No criterion or footprint changes.

2026-09-28, re-check at f59b3136: the owner resolved the contradictory mixed-case brief.
A replacement question is allowed only when every approval problem is a tree-only binding
mismatch for a prior grant at this revision. Missing, revoked and proof-mismatched approvals
keep the land failed with its named reasons, no subject and no loop action. The station refuses
failed dispatches, applies a grant at most once per dispatch, and rechecks all prior grants
before writing any replacement. Added mixed-proof, repeated-pass and revoke-before-answer rows;
flipped mixed-approvals to require no question or grant. All changes fit the existing footprint.
The lead reports 14 of 14 mutations rejected at f59b3136. Added mutations are registered and
not yet run; mutation execution remains reserved for the reviewer.

2026-09-25: written for PLAN-0019 revision 4 from the approved operating-model design (Telegram 29162),
section 7(e), whose VELDO-0057 amendment is carried here whole because VELDO-0057 has landed. The
criterion text, its falsifier (move the remote trunk between the listing and the push; the re-land row
must fail if the unit is left unknown) and the approval rule are the design's, split into one criterion
each for the stale-subject re-land, the lease window and the fresh grant. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4 review: the factory loop this concern extends is VELDO-0154, split
from VELDO-0129 (its former AC4 is VELDO-0154 AC1), so depends_on names VELDO-0154 in place of
VELDO-0129 and the loop references follow. Criterion meaning unchanged.

2026-09-28: built on branch build-veldo-0148 from main ad916989. Each land of a unit is its own land dispatch,
recorded by the land station, class LandStation in the new `control_landing_station.py` (records of kind
`land_dispatch`, one transition, `open` and `end`, by an active service member; one land of a unit at a time, and
a land that follows another must follow the unit's latest one, only after it ended trunk_moved or
awaiting_approval). A land runs the factory land unchanged (GitLandOps with the CandidatePolicy and the
VELDO-0057 Landing) and ends landed, trunk_moved (the publication refused `stale-subject` at the listing or
`trunk-moved` after it, with the watermark, the tip found and the classification), conflict, awaiting_approval
(only a grant for the re-merged tree is missing, with its exact subject), unknown or failed. The factory loop's
next-station rule (`control_service.py` Line.after_land) re-lands a trunk_moved unit as one new land dispatch,
sends a conflicted one back to its builder as a new build dispatch whose payload names the new trunk to merge and
offers its review once it completed, and asks the project's owner once per re-land for a fresh grant, recording
his grant as an approval bound to exactly the re-merged tree before the next land dispatch; each land runs to its
end inside the pass, and one whose end owes a next station wakes the next pass as a run's end. The work
configuration names a repository's `land` station (installation refuses a malformed one by name), and the loop's
status reports each station's dispatches. The effect executor (`control_effect_executor.py`) fetches each
destination's moved tip into its publication clone and records a lost lease as a refused publication,
`trunk-moved`, when every destination's trunk holds a commit that does not contain the candidate; a tip that
contains it stays unknown. The lander loads its siblings by its own path (`lander.py`), so the land station runs
from the service's installed executable. Two files outside the drafted footprint were needed for that, added
here: the installation's closure reads a module's declared EXTERNAL_LOADERS, and `control_verification.py`
declares its `_policy_main`, which loads the trusted installation's policy_check.py in a process of its own; and
`control_proof.py` loads validate.py through control_eligibility's ValidatorSnapshot of its own directory, since
validate.py loads its organs from a repository tree and the CandidatePolicy asks the proof reader about the
candidate. Suite 86, the red record against ad916989, finding 148 and proof/VELDO-0148/ carry the evidence. No
criterion or status changes.

2026-09-28, completion after main moved: merged local main at 9f1a0445 without conflicts and
reconciled the suite registry as main's entries plus suite 86, preserving main's order; regenerated
requires.json. Audited all 12 finding-148 registrations against the saved mutations.json: every
record names its registered assertion failures, every diff exactly applies the registered old/new
text (including the forced-push mutation's second replacement), and all source and mutant digests
match the merged production modules. No records are missing or stale; mutation names are unique
across the registry. The saved baseline and four no-op controls are green. This was a static audit
of the previous builder's evidence, not a new mutation run; the reviewer runs the mutation checker.

2026-09-28, merged-tree regression checks: suite 86 passes all 10 rows in both the ordinary
and requested gate environments. The proof (64, 14 rows), floor (63, 20), candidates (67, 11),
gate output (69, 16), effect executor (58, 51), landing (70, 31) and factory loop (83, 13) suites
all pass without failures. Candidates and gate output initially overlapped accidentally, then
were rerun serially; all final runs were separate. Subset mode intentionally exits 2 and does not
constitute a full gate verdict. No merge repair was needed. Searched production writers and
readers of the land dispatch, trunk-moved classification, approval request and installed-loader
seams; all eight changed production modules match their engine copies byte for byte.

2026-09-28, final completion checks: the supplied footprint checker reports 37 changed paths,
none outside this specification; the supplied anchor checker reports 0 bad anchors and no
mutation-name duplicates. `python3 .veldo/validate.py all` passes, and the diff has no whitespace
errors. The suite registry preserves every main entry and adds suite 86 exactly once; requires.json
is regenerated. The proof README maps each criterion's rows, the saved red record, the 12 audited
mutation rejections and replay instructions. No further footprint expansion or criterion change
was needed. The full gate and mutation checker were not run, as directed; they remain for the
independent reviewer. Gate byproducts are restored before the final commit and are not this work.

2026-09-28, review repair: local main is already an ancestor of b33e82f8. AC3 replacement
requests cover only prior grants at this revision whose tree binding mismatches. A never-granted
approval stays refused by name with no request or grant. A mixed refusal can request replacement
of its mismatched grant only; the dispatch stays failed and its missing approval still blocks
publication after the answer. Added production-interface rows for both cases, including a policy
requirement added between candidate policy and final authorization. The repeated-question mutant
now varies the command identity as well as the alias, and the row counts persisted questions on
both passes directly. No footprint expansion.

2026-09-28, follow-up tickets outside this repair: start the first land dispatch after a conflict
rebuild; offer the rebuild review at its new evidence commit; reject open with follows=None after
an end; replace the module-declared EXTERNAL_LOADERS opt-out; move synchronous re-land gates out
of loop passes; clean up refs/veldo/observed/*.

2026-09-28, review repair proof: suite 86 passes all 12 rows in ordinary and empty gate
environments, serially (38 including the shared preamble, zero failures; subset exit 2).
The current suite replayed against b33e82f8 makes both new approval rows red by assertion;
against ad916989 all ten behavior rows are red by assertion. The repeated-question row now
counts questions on both passes directly. All 14 finding-148 registrations have unique names,
valid single anchors, compiling mutant sources and current digests and diffs; their execution
is reserved for the reviewer. The prior 12 rejections are preserved separately as historical
evidence. The supplied footprint checker reports 41 changed paths, none outside; anchor_check
reports 0 bad anchors; validate.py all exits 0; the three changed engine modules match byte for
byte and the diff has no whitespace errors. Suite 86 remains registered once and requires.json
was regenerated without changes. No other suites, full gate or mutation checker ran in this
repair. Gate byproducts are restored before the final commit and are excluded from this work.

2026-09-28, re-check proof complete: repair commit bc92f46f passes suite 86 in ordinary
and empty gate environments, serially: 15 suite rows, 41 with the shared preamble, zero
failures (expected subset exit 2). The current suite is red by assertion on all four re-check
rows against f59b3136, and all 13 behavior rows against the original ad916989; format controls
stay green. Finding 148 now has 18 registered mutations with exact diffs and current digests,
0 bad anchors and no duplicate names. The lead's 14 of 14 rejections at f59b3136 are recorded
as attributed historical evidence; all current registrations, including four new ones, await
reviewer execution. The supplied footprint check reports 46 paths, none outside; the repair's
20 paths also fit. Validation exits 0. The three production modules and engine copies match,
requires.json is regenerated, and the diff has no whitespace errors. Audited production readers
and writers of approval subjects, replacement names, grant events and loop dispatch states.
No other suite, full gate or mutation runner ran. Gate byproducts are restored before the final
commit. No footprint expansion was necessary.
