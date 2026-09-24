# VELDO-0135 proof

Enrolled work is offered from its authoritative floor state, not the spec status line. PLAN-0019
revision 3 W98 (Release 1 stage 1). Branch `build-veldo-0135`, built on 5ba4a02. The specification's
status is unchanged.

## What landed

**The frontier** (`.veldo/frontier.py`, mirrored in `engine/.veldo/`). In an enrolled repository every
lane decides on one status map in which each unit's entry is its place on the floor, read through
VELDO-0049's own read path (`FloorAuthority.record` and `.version`, the handoff rule `_handoff` asked of a
copy) over the eligibility Gate's read-only connection, in one read transaction. No record: the file's
word, so `ready` is the build station, and a file that says `review` with no record behind it is withheld
as `missing_authority:floor_record`. `review`: the review station while more reviews are needed, or when
the handoff would pass (only a review dispatch runs it); with the count met and a blocking finding open it
waits (`unresolved_finding`). `returned` to ready: the build station (the rebuild is how a finding gets
fixed; its disposition is bound to the rebuilt commit). `handoff`: nothing. Landed, by the one completion
reader: shipped. A row at the record's identity that is not a floor record is `invalid_input:floor_record/kind`
and a store error `unavailable_service:store`; neither becomes an offer. With VELDO-0031's authority claim
client as `claims_root` the frontier asks it about each unit (it cannot list claims); a stop about one unit
(a ready spec the store has not admitted) is withheld by name, and any other stop still stops the read.

**The review station** (`.veldo/dispatch.py`, mirrored in `engine/.veldo/`), added after the scoped review
of e5b4dad. Before it assigns a review it asks the authority's handoff rule through the read path
(`FloorAuthority.handoff_refusals`, the same `dispatch.handoff_refusals` the frontier asks). When the rule
already passes (the policy's count of passing reviews is met and the owner resolved the last open finding)
it hands the unit off and lands it without assigning or launching a reviewer; only when the rule does not
pass is a review assigned and launched. Before this, such a unit was offered as review forever: the only
reviewer whose review stood was refused as a second position (`duplicate_reviewer`), and a new reviewer's
review was one the policy does not require.

**The work loop** (`.veldo/work.py`). Claim-then-recheck reads the same floor entry
(`frontier.floor_station`), so a unit whose record moved away from the offered station in the claim window
is released, observed as `stale_version:floor_record`, and never dispatched. Unenrolled repositories keep
rechecking the status line. A failed dispatch bars the unit only at the station it failed at (the failed
set is keyed by unit and station), so a unit whose review failed and sent it back to build is rebuilt in the
same run.

**Observability.** Each frontier read observes every enrolled unit in scope through the Gate's sink
(`veldo.frontier_floor/v1`, `floor_offer`): unit, station offered, record identity and version, and when
withheld the named reason and its class (`held` for a place a unit waits at, otherwise the floor or
eligibility taxonomy). `floor_offers` counts offers per station and withheld units per reason. The loop
joins each dispatched offer by its offer id to the VELDO-0039 dispatch the authority recorded for it
(`floor_dispatch`).

## Rows (suite `67_veldo_0135_offers`, 9 rows: 5 assertions and 4 `ran/` rows)

Real SQLite store, OpenSSH signatures, an enrolled Git repository whose spec files all say ready (one says
review) and are never written, a bare trunk, the VELDO-0052 Gate, VELDO-0036 reservations, the VELDO-0031
claim transition behind the claim client (transport replaced by the same command on the store), the
VELDO-0049 authority and real builder and reviewer processes through VELDO-0039's runner. Every floor state
is reached through the real Dispatcher.

**AC1** `offers/floor-station`: no record, review 0/2 and 1/2 (critical), returned with an open finding,
review with the count met and a finding open, then the owner's disposition (back at review), handoff,
landed, a review line with no record, a non-floor row and an unadmitted spec, each offered at its floor
station or withheld by its named reason. **AC2** `offers/no-reclaim`: a WorkLoop over the same units
claims exactly the build, review and returned units; handoff, landed and the waiting unit are never
claimed; in the window before its claim another worker builds a unit to review, and the loop releases its
stale build offer (then takes it at review). **The finding path** `offers/finding-path`: VELDO-9504 fails
its first review, is rebuilt and passes, its handoff is refused on the open finding, and the owner resolves
it; a review worker's WorkLoop with the reviewer whose review stands then hands it off and lands it on the
trunk, with no reviewer launched, the same reviews and assignments as before, the handoff on that one
passing review of attempt 2, and nothing claimed again. **AC3** `offers/end-to-end`: one enrolled unit through the
builder's WorkLoop (build accepted; its own review offer refused by the review station, nothing launched)
and a separate reviewer's WorkLoop (review, handoff, landing on the trunk), then nothing is claimed again;
builder and reviewer are different processes. The same row requires an unenrolled repository to offer and
dispatch by its status line unchanged, and a unit whose review failed there to be rebuilt in the same run. **Also** `offers/observations`.

## Red at the pre-change code

`red.py e5b4dad` writes `red-e5b4dad.json`: the current suite with its three anchors pointed at e5b4dad's
own frontier.py, work.py and dispatch.py, no stand-in, every other installed module identical to that
commit. Two assertion rows fail by assertion, every `ran/` row passes, nothing raised.
`offers/finding-path`: the review worker's loop is refused `duplicate_reviewer` at review assignment, the
unit stays at review with no handoff and is not landed, and a second loop claims it as review again.
`offers/end-to-end`: the unenrolled unit whose review failed is never rebuilt in that run. The earlier
record `red-5ba4a02.json` (the first four rows against 5ba4a02's frontier and work loop, recorded on the
pre-merge tree 40ee570) stands as it was.

## Mutations

16 registered as finding 135 in `scripts/check_teeth_mutations.py`; `mutations.py` writes `mutations.json`
with each diff in `mutations/`. Each reds its named row by assertion with that row's region completing; at
least two per row. Declared falsifiers: `offers-status-line-read` (AC1), `offers-handoff-claimable` (AC2),
`offers-build-again-after-acceptance` (AC3). For the finding path: `offers-review-assigned-before-handoff-rule`
(the review is assigned before the handoff rule is asked) and `offers-reviewer-launched-before-handoff` (the
rule passes but a reviewer is still launched); for the failed set, `offers-failed-review-bars-rebuild`
(end-to-end). Unmutated control: frontier.py, work.py and dispatch.py each copied byte for byte through the
same substitution, suite green with every row.

## Costs and runs

Suite 67: 6.3 to 8.6 s. Finding 135, 4 jobs: 16 mutations in about 33 s. Under the gate's stage
environment (`env -i`, short PATH, HOME and TMPDIR under /dev/shm): suite green, 16 of 16 rejected. After
the fix, suite 63_veldo_0049_floor's `floor/finding-not-erased` row asserted the old behavior (a third
reviewer in the handoff after the owner's resolution); it now requires the handoff on the two passing
reviews that stand with no reviewer launched, and finding 49 stays 36 of 36 rejected.

## Not done here, stated

While more reviews are needed, a reviewer whose review of the current attempt is already recorded is
still offered that unit (the frontier has no reviewer identity); the authority refuses the second position
before any launch. Once the handoff rule passes, any reviewer's offer hands the unit off without a review. The
review station refuses a builder's loop that meets its own unit's review offer, so it is claimed and
released, not launched. Offers read one floor entry per spec per frontier read. The lander and the engines
are fixtures; LiveLoop and LiveReviewer wiring is separately specified. Not run here: verify.sh, the Mac.
