# VELDO-0340 proof

Implementation efacf191 (the build) and ed136897 (the suite made to keep its rows when a part raises), on
VELDO-0318 fix round 1 at d0e2461a. Builder evidence, not independent review. All four criteria
remain pending the lead gate and independent review.

## What was built

A review worktree deferred for unique work other than review scratch gets no request of its own. It
joins the review group of its scope for the calendar day of the deferral (design 4.9 and 7):
space:group:<scope>:<day>:<sequence>. One request per group. A later deferral of the day is a new
version: new terms, a revision of the one request, its framing. A group pick is one write for every
member still in the group that the settled terms list, and closes the group. Save and Discard are
then carried per member through the remover checks VELDO-0318 built, each against the entry shown
for that worktree. Keep is the owner's signed packet, naming any member.

The lead's decision (specification History, 2026-11-16): the space terms carry one or more
worktrees under a group, targeted as space_group with every member item named. Terms without a
group are what they were. engine/.veldo/control_service.py did not change, and neither did the
VELDO-0327 suite: terms without a group still name exactly one worktree (sources.json holds both
digests).

## Rows (rows.json), 13 green at ed136897

- AC1: ac1/one-request (the falsifier row), ac1/next-day.
- AC2: ac2/new-version (the falsifier row; the old presentation is refused as stale_presentation
  before and after the new one is presented), ac2/clock (the clock moved a day with no deferral:
  no request, group, version, message or journal record), ac2/unseen-member.
- AC3: ac3/save, ac3/keep, ac3/discard (the falsifier row), ac3/closed,
  ac3/answered-takes-no-join.
- AC4: ac4/builder (the falsifier row).
- terms/group (the widened terms and their refusals), worker/group (the service's disposition
  task, unchanged, publishes a group's request and carries its Discard in the worker child).

## Falsifiers (falsifiers.json, teeth-receipt.json)

Finding 340 ran last, on the clean committed tree, with nothing written in the worktree while it
ran: 10 registered, 10 executed, 10 rejected, no reuse, no invalid result, no surviving worker,
each mutant applied once (teeth-run.json). The four declared falsifiers:

- AC1 space340-one-request-per-worktree: day 1 holds two requests; ac1/one-request red.
- AC2 space340-join-without-a-new-version: the answer to the old presentation settles;
  ac2/new-version red.
- AC3 space340-discard-without-the-comparison-per-worktree: the member with the added file is
  removed from disk; ac3/discard red.
- AC4 space340-every-run-worktree-is-a-review-worktree: ac4/builder red. The specification says the
  builder's file is deleted. Under this mutant, which is in Signal, it is not: the remover and the
  keep step judge the station themselves and refuse. The row fails because the builder's worktree
  gets no request of its own.

Six more, for what the build added: the day read as one constant, a pick that reaches a member the
owner was not shown, a pick that reaches only the named member, a join into an answered group,
review scratch removal inside a Save or Discard, and a group target that names no member.

Two earlier runs are recorded in teeth-run.json and are not evidence. In the first nothing ran: the
builder had made the driver's log folder. In the second nine were rejected and the AC1 case was
invalid, not surviving: with no group at all a later part of the suite raised and lost its rows.
The suite now fails the rows of a part that raises and runs the rest (ed136897).

## Regressions (checks.json)

At efacf191: 0318 45, 0327 27, 0345 31, 0300 39, 0297 31, 0312 41, 0317 23 rows green, the settlement
suite (0068) and the inbox suite (0064) green. Inherited reds, each red on the base d0e2461a too:
VELDO-0301 ac4/no-clock (17 green), and VELDO-0336 loss/owner-keep and loss/kept-child (19 green;
run on an export of the base with the same result). Suite 153 (0336) was run once because the
brief names its rows; no other suite of 151 and up and no gate was run. Validation, docs, template
sync, lint and the two boundary checks passed at ed136897. No space supervisor survived any run.

Not caused here and left: the teeth anchors of space301-returns-after-marking-due and
space301-refused-item-not-deferred match nothing on the base either. The anchor of
space327-target-another-item still matches once.

## Not built

- Member picks and the one-message size rule: VELDO-0342. The sequence number is built, because AC3
  defers a changed member into a new group.
- A client that signs the owner's Keep packet: none exists in the repository (as VELDO-0318 found).
  A settled accept keep changes nothing until that packet arrives; a deferral in between opens the
  next group (row ac3/answered-takes-no-join).
- A group whose request was canceled or declined keeps its members with no live request until
  their next deferral. No criterion names it.
