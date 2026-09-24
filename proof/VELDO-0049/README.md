# VELDO-0049 proof

Dispatch and tracker bridge consume authoritative state transitions, PLAN-0019 revision 3 W34
(Release 1 stage 1). Branch `build-veldo-0049`, built on 0083c85. Specification status and every
other specification are unchanged.

## What landed

**The floor authority** (`.veldo/dispatch.py`, mirrored in `engine/.veldo/`). One registered store
command, `floor_transition`, committed through the signed journal on the caller's connection, as
VELDO-0039's dispatch command is. Its actions: `accept_build` (the authority reads
`proof/<unit>/manifest.json` from Git at the built commit, binds its digest, validates it, and
requires the commit it names to be the built commit or an ancestor with only that proof changed
since; it also requires a green gate, the current claim holder and generation, and the build's own
exited VELDO-0039 dispatch under that claim; the builder becomes the unit's producer),
`assign_review`, `record_review`, `dispose_finding` and `handoff`. Nothing writes a completed
state, a shipped status or a completion receipt. The **Materializer** alone publishes an enrolled
unit's status projection, through VELDO-0035's ordinary materialization, into a new directory per
record version.

**The dispatcher.** In an enrolled repository, or with a `FloorAuthority` wired, `_set_status`
refuses (`status_projection_owned`) and a dispatcher with no authority stops (`authority_required`).
A build moves to review only through `accept_build`. A unit the authority holds is not built again.
A review is assigned to one eligible reviewer, never a builder of the unit and never a second
position for one principal. The reviewer is launched with exactly its assignment, and its receipt
is recorded only if it is signed with the reviewer's active key, bound to the source, the proof and
the assignment, and is exactly what its own VELDO-0039 review dispatch printed. A failing verdict
returns the unit and leaves its blocking findings open. Only an explicit signed disposition, by the
owner or the reviewer who raised a finding, resolves it. The handoff counts distinct passing
reviewers on the current attempt against the stored review policy (policy.yaml `risk_tiers`
reviews, critical 2). `_land` lands only from the handoff, and a refused land is retried from it.

**The tracker bridge** skips enrolled repositories in both reconcilers and refuses
`write_spec`/`promote_spec` for them (`tracker_intake_disabled`). Unenrolled repositories are
unchanged.

## Rows (suite `63_veldo_0049_floor`, 18 rows: 12 assertions and 6 `ran/` rows)

Real SQLite store, OpenSSH journal and review signatures, an enrolled Git repository with a real
gate script and committed proof, a bare trunk, the VELDO-0052 Gate over that workspace, and real
receiver, builder and reviewer processes launched through VELDO-0039's runner under separate
principals.

**AC1.** `floor/status-write-sites`: the status-write sites derived from the source equal
`STATUS_WRITES`, each refuses under enrollment, an unwired dispatcher stops before any builder, and
the same write in an unenrolled tree still writes (the additive control). `floor/build-acceptance`:
build success, invalid proof, stale proof and red gate through the real executor. Only the success
produces a record and a projection. Direct authority calls with an invalid proof, a red gate,
another holder, a stale generation or a commit without proof are refused by name, and a unit in
review is not rebuilt. `floor/authority-to-projection` checks that every published status reads back
equal to the store, is backed by a committed build acceptance whose proof the suite accepts from Git
on its own, and that no spec file was written.

**AC2.** `floor/review-independence`: self-review refused at the station and at the authority, and a
builder's key signing as the reviewer or as itself refused. `floor/review-binding`: wrong source,
wrong proof, missing receipt, launch at another commit, extra launch input and an altered receipt
are each refused by name. A valid review is recorded from a separate process (its pid is not the
builder's) that received only its assignment. `floor/review-policy-count`: a second review by one
principal is refused, the handoff names reviewer-b and reviewer-c, required 2, and matches the
journal's assignment and review records and the independently verified signatures.
`floor/land-retry-from-handoff` and `floor/no-builder-reviews` (the first attempt's builder cannot
review a rebuild by another worker).

**AC3.** `floor/finding-not-erased`: a blocking finding, then a pass on the returned build (refused),
a rebuild, passes with the count met (refused `unresolved_finding`), a direct land (refused
`not_handed_off`), the builder's, another agent's and a wrongly signed disposition (refused), an
owner's rejected ruling (finding stays open), with the trunk unchanged throughout. Then the owner's
signed disposition, one more pass, the handoff and the trunk at the rebuilt commit.
`floor/completion-by-lander-only`: no completion receipt, the completion reader reports nothing,
records stay `handoff` and no transition targets completion.

**Also.** `floor/tracker-disabled-when-enrolled`, `floor/observations`.

## Red at the pre-change code

`red.py 0083c85` writes `red-0083c85.json`. `prefix/dispatch.py` is 0083c85's dispatch.py byte for
byte plus a marked stand-in that ignores `authority` and has an absent authority. The tracker bridge
is the commit's own copy, and every other installed module is checked identical to the commit.
All 12 assertion rows fail and all 6 `ran/` rows pass, so every red is a failed assertion. Observed:
the enrolled status write happens, a stale proof is accepted, every review stops on
`missing_evidence:producer`, a direct land pushes unreviewed work to the trunk, and the tracker
promotes into the enrolled repository.

## Mutations

33 registered as finding 49 in `scripts/check_teeth_mutations.py`. `mutations.py` drives them and
writes `mutations.json`, with each diff in `mutations/`. Each one reds its named row by assertion,
and that row's region completes. The declared falsifiers are `floor-status-written-directly` (AC1,
two edits), `floor-builder-reviews-itself` (AC2, two edits) and `floor-pass-erases-finding` (AC3).
Every row has at least one mutation.

## Costs

Suite 63: 4.1 s inside selftest; 5.35 to 5.51 s over three `drive.py` runs at host load average 17.
`observations.json` holds one run. Finding 49 with 4 jobs: 33 mutations in 50.2 s. After merging
origin/main (already contained), these regression runs had zero failures: 62_veldo_0039_dispatch,
60_veldo_0052_eligibility, 60_veldo_0053_architecture, 58_veldo_0031_claims, 50_git_environment,
58_veldo_0035_snapshots, 05_tracker_routing_resolver_veldo, 06 and 07. `validate.py all`, template
sync, lint, the generated, Git, writer and parser boundary checks, and the shape gate all pass.
The full gate is the lead's.

## Not done here, stated

The frontier and work loop still read the spec file's status: for enrolled work that never
changes, so they offer no review unit until they read the projection (frontier.py and work.py are
outside this footprint). A dispatched build of a unit already in review is refused before any
launch. LiveLoop and LiveReviewer adapter wiring is separately specified: the suite's builder and
reviewer engines are fixtures. The gate observation is the executor's (the gate is trusted). A
committed transition whose projection fails is returned as `projection.refused` and left pending
(recovery is Release 2). The scaffolder does not install dispatch.py, before or after this change
(VELDO-0059). dispatch.py is now 1240 lines, over the advisory 1000-line budget (review lane).
Not run here: the Mac and the full gate.

## Review of d46451c (scoped, 2026-09-24)

One blocking defect in this unit, fixed: a blocking security or shape-fit dimension, and a failing verdict
that listed no finding, returned the unit without opening a finding, so after a rebuild one pass handed it
off. Now each opens a finding that only a signed disposition closes. Row
`floor/blocking-verdicts-stay-open` (two new units with an insecure and a finding-less failing review): red
by assertion before the fix (both units landed), green after (both stay pending with one open finding).
Mutations `floor-dimension-block-not-kept` and `floor-bare-fail-not-kept`. `--finding 49 --jobs 4`: 35 of
35 rejected, suite 46 assertions green.

Owed by another spec (not this footprint): the frontier and the work loop read the spec file's status
line, which an enrolled unit never changes, so a live enrolled run offers no review unit after build
acceptance. `.veldo/frontier.py` and `.veldo/work.py` are in VELDO-0052's footprint; a missing-spec ticket
is filed. Filed from the same review: nothing in normal use carries a disposition yet (intake's job); a
disposer is any active person member, not specifically the unit's owner; the reviewer also receives the
capability configuration; a landed record stays in handoff.
