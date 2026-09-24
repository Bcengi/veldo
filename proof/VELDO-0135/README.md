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

**The work loop** (`.veldo/work.py`). Claim-then-recheck reads the same floor entry
(`frontier.floor_station`), so a unit whose record moved away from the offered station in the claim window
is released, observed as `stale_version:floor_record`, and never dispatched. Unenrolled repositories keep
rechecking the status line.

**Observability.** Each frontier read observes every enrolled unit in scope through the Gate's sink
(`veldo.frontier_floor/v1`, `floor_offer`): unit, station offered, record identity and version, and when
withheld the named reason and its class (`held` for a place a unit waits at, otherwise the floor or
eligibility taxonomy). `floor_offers` counts offers per station and withheld units per reason. The loop
joins each dispatched offer by its offer id to the VELDO-0039 dispatch the authority recorded for it
(`floor_dispatch`).

## Rows (suite `67_veldo_0135_offers`, 7 rows: 4 assertions and 3 `ran/` rows)

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
stale build offer (then takes it at review). **AC3** `offers/end-to-end`: one enrolled unit through the
builder's WorkLoop (build accepted; its own review offer refused by the review station, nothing launched)
and a separate reviewer's WorkLoop (review, handoff, landing on the trunk), then nothing is claimed again;
builder and reviewer are different processes. The same row requires an unenrolled repository to offer and
dispatch by its status line unchanged. **Also** `offers/observations`.

## Red at the pre-change code

`red.py 5ba4a02` writes `red-5ba4a02.json`: the suite with its two anchors pointed at 5ba4a02's own
frontier.py and work.py, no stand-in, every other installed module identical to that commit (recorded on
the pre-merge tree 40ee570). All 4 assertion rows fail, all 3 `ran/` rows pass, nothing raised. Observed:
units at review, handoff and returned all offered as build from their `ready` line; the review line with no
record offered as review; and the work loop with an authority claim client stops on
`explicit_unit_required`, so no enrolled loop could run at all.

## Mutations

13 registered as finding 135 in `scripts/check_teeth_mutations.py`; `mutations.py` writes `mutations.json`
with each diff in `mutations/`. Each reds its named row by assertion with that row's region completing; at
least two per row. Declared falsifiers: `offers-status-line-read` (AC1), `offers-handoff-claimable` (AC2),
`offers-build-again-after-acceptance` (AC3). Unmutated control: frontier.py and work.py each copied byte for
byte through the same substitution, suite green with every row.

## Costs and runs

Suite 67: 5.4 to 6.0 s. Finding 135, 4 jobs: 13 mutations in about 25 s. Under the gate's stage
environment (`env -i`, short PATH, HOME and TMPDIR under /dev/shm): suite green, 13 of 13 rejected.

## Not done here, stated

A reviewer whose review of the current attempt is already recorded is still offered that unit (the
frontier has no reviewer identity); the authority refuses the second position before any launch. The
review station refuses a builder's loop that meets its own unit's review offer, so it is claimed and
released, not launched. Offers read one floor entry per spec per frontier read. The lander and the engines
are fixtures; LiveLoop and LiveReviewer wiring is separately specified. Not run here: verify.sh, the Mac.
