# A review that leaves no verdict artifact is off-book

Recorded 2026-07-29. Scope: the process, not any one item.

## The defect

On 2026-07-29 four independent reviews ran, were real and rigorous, and produced
NO verdict artifact. They ran inside orchestrator workflows rather than through
this repository's own review lane: the specs were never transitioned to status
`review`, `.warp/frontier.py` never offered a review unit for any of them, no
claim was taken, and nothing was written under `proof/`. Every one of the four
items then landed on main.

For a method whose whole product is the RECORD, that is the defect. The code
was fine in three of the four cases and reworked in the fourth; what was wrong
is that none of it was written down where the repository can see it.

## The four

| item | verdict that review gave | reviewed commit | reviewed at (UTC) |
|---|---|---|---|
| WARP-0722 round 9 | fail | 18e6ca8 (main's head; the item had already landed) | 07:48:54 |
| WARP-0724 round 1 | fail | 0f59d33 (branch tip) | 09:07:38 |
| WARP-0723 round 1 | pass_with_notes | 26b6c34 (branch tip) | 09:09:37 |
| WARP-0713 round 1 | fail | e1ece57 (branch tip) | 11:42:47 |

The verdict artifacts written after the fact to repair this are
`proof/WARP-0722/verdict-9-fail.json`, `proof/WARP-0724/verdict-1-fail.json`,
`proof/WARP-0723/verdict-1-pass_with_notes.json` and
`proof/WARP-0713/verdict-1-fail.json`. Each one says in its `reviewer` field
that it came from an orchestrator-dispatched agent and not from the review
lane, so a later reader can tell the difference. Each one is a TRANSCRIPTION by
the orchestrator of the reviewing agent's own structured return, not the
reviewer's own hand, and each says so.

## It had already been condemned, the same morning, on this same record

The FIRST of the four, the WARP-0722 round-9 review at 07:48:54Z, named this
exact pattern as the reason a defect had gone unfound: the entitlement hole it
was reporting arrived at round 7, and rounds 4 through 9 of that item had no
recorded independent verdict, so round 9's review was the first to reach the
code those rounds shipped. Five consecutive rounds off the record, and the cost
of it measured.

Three more reviews ran that day, after that finding was in hand, and each of
the three left no artifact either. Naming the defect did not stop it, which is
the whole lesson: a stated intention is not a mechanism.

The repository already knew this in a second place. `scripts/verify.sh` carries
the reason the event projection exists at all, in its own words: the thing it
replaced was an instruction asking whoever ran a review to append the event by
hand, and across every verdict in the corpus nobody ever did.

## What it cost, measured rather than feared

1. All four specs still say `status: ready`. Nothing in the repository records
   that they were reviewed.
2. The frontier therefore still offers all four as claimable build work, so the
   fleet can pick up an item that has already landed.
3. The metrics will not count the reviews. `.warp/events.py reconcile-verdicts`
   derives a `verdict.recorded` event from each COMMITTED verdict artifact, so a
   review with no artifact is invisible to the projection, to
   `.warp/metrics.py`, and to the dashboard. Four reviews, four verdicts, three
   of them FAIL, none of them counted.
4. A reader sees four items with no evidence of review, which is
   indistinguishable from four items nobody reviewed.
5. Worst of the five, and the one the WARP-0722 review measured directly: with
   no artifact there is nothing for a later round to be adversarial ABOUT. A
   defect introduced in a round that leaves no record is not merely unrecorded,
   it is unreachable.

## The remedy

A REVIEW IS NOT DONE UNTIL ITS VERDICT ARTIFACT EXISTS.

Not "should be written up". Not "the reviewer reports and someone records it
later". The artifact under `proof/<spec-id>/verdict*.json`, satisfying
`.warp/validate.py`'s own VERDICT_REQ, is the review's OUTPUT. A review whose
output does not exist has not produced anything, whatever was measured while it
ran, and it must not be counted as a review or relied on to land an item.

Three corollaries, each one paid for above:

- **Record the verdict THAT REVIEW GAVE.** A later, kinder verdict on a
  reworked tree is a DIFFERENT review and needs its own artifact. Rewriting the
  first one is how a `fail` disappears.
- **Record the commit the reviewer actually saw**, which is the branch commit,
  not main's head after the merge. A verdict pinned to the wrong tree cannot be
  reproduced and cannot be attacked.
- **Say who reviewed, honestly enough that a reader can tell how much weight it
  carries.** An orchestrator-dispatched agent in a workflow is weaker evidence
  than a review the repository itself dispatched, and a rework verified by the
  party that made it is not verified at all.

## What this note does NOT claim

It does not claim the four reviews were bad. They drove routes, ran the gate and
the suite themselves rather than reading the builder's numbers, and three of
them found real defects that were then fixed. The findings are in the four
artifacts.

It does not claim the record is now complete. In all four cases the rework, or
the decision not to rework, was verified BY THE ORCHESTRATOR and not by a fresh
independent reviewer, and each artifact records that as a gap rather than as
evidence. No spec is moved to `shipped` by this note or by those artifacts,
because a `fail` verdict plus an orchestrator-verified rework does not support
`shipped`.

It does not claim to be a mechanism. This is prose, and prose does not execute.
Turning "a review is not done until its verdict artifact exists" into something
with teeth means CODE: the review lane refusing to close a unit with no
artifact at its declared path, and the gate reporting an item that landed with
no verdict on record. Until that exists, this file is a record of a defect and
not a fix for it.
