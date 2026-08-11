# Held back from the repository proper, with the reason

Both items below were authored 2026-07-25/26 alongside the specs that landed in `specs/`. They are here
rather than in `specs/` or `proof/` because each fails a real check, and the honest options were to fabricate
the missing data or to hold the artifact where it cannot be mistaken for valid. Neither is abandoned; each has
a named next action.

## `WARP-0625-live-changelog-reader-NEEDS-PLAN-RECONCILIATION.md`

It declares itself W5 of PLAN-0016. The authoritative `plans/PLAN-0016-human-decisions-through-jira.md` says
W5 is WARP-0619. The gate catches this by name:

    specs/WARP-0625-live-changelog-reader.md: plan PLAN-0016 work W5 is spec WARP-0619, not WARP-0625

The cause is that this spec was drafted against a STALE copy of PLAN-0016 that was superseded while
WARP-1210 occupied the tree. The repository's plan is newer and correct, and it already records the O2, O3
and O4 decisions the stale copy was missing.

**Next action:** reconcile the spec against the current PLAN-0016 - either it takes a work id that is actually
free, or the plan gains a work item for it, or it is dropped as already covered by WARP-0619. That is a
reading decision, not a mechanical one, so it is not guessed here.

## `WARP-0620-evidence/` - RESOLVED 2026-08-02, landed at `proof/WARP-0620/`

The two missing fields turned out to be a NAMING mismatch rather than missing data: the record
already carried `approved_at` (recorded live) and a prose `expiry` of "single-use, that session
only". `recorded_at` copies the former verbatim; `expires_at` states the latter as a timestamp,
deliberately in the past so the record grants no live authority. Nothing was invented, and the
refusal to invent was correct - it just turned out not to be necessary.

The directory below is kept as the provenance of what was held and why. The live copy is in
`proof/WARP-0620/`.

### Original entry


The live TE1 sandbox proof: a run record, the verbatim changelog payload, a manifest draft and an approval
record. `proof/WARP-0620/approval-dmitry.json` is rejected by the contract check for two missing fields:

    missing field: recorded_at
    missing field: expires_at

**Next action:** these are timestamps on a HUMAN approval record. They will not be invented to make a check
pass, which is the whole point of binding an approval to a time. They get filled from the real record when
WARP-0620 is built, and the proof directory lands with the item, as every other item's proof does.
