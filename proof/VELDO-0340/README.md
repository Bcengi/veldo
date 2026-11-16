# VELDO-0340 proof

Implementation efacf191 (the build), ed136897 (the suite made to keep its rows when a part raises) and
41c8d791 (fix round 1, after the independent review), on VELDO-0318 fix round 1 at d0e2461a. Builder
evidence, not independent review. All four criteria remain pending the lead gate and independent
review. The json files beside this one are of the fix round: every suite, check and teeth case was
run again at 41c8d791.

## Fix round 1 (41c8d791)

The review's verdict was FIX with three low findings, no lost work. Each has a row and a falsifier:

- Finding 1, row ac2/join-races-answer: the owner's answer settles after a deferral read which
  group it joins and before its write. The write reads again, the answered group keeps the members
  and version the owner was shown, and the deferral opens group 2. Falsifier
  space340-join-without-the-read-in-the-write: the late worktree joins the answered group.
- Finding 2, row terms/ledger-target: a settled effect whose group target names one item for terms
  that list two, written directly past the Settlement, is no settled answer for either member, and
  no pick is applied. With the effect as it was settled the same pick is applied to both. Falsifier
  space340-ledger-takes-a-target-short-of-the-listed-items.
- Finding 3: the answered read no longer reads every request in the store. The group record's
  request holds the identity of its one request, written by the Ledger's own transition
  space_review_group_request before the request is opened; a join reads that one row by its key.
  The Ledger does not hold the repository identity, so the publisher hands the identity over; that
  is one more Ledger write per group, at its first publish. Row cost/answered-by-id counts database
  steps of the read with and without 400 more requests in the store, for a request not opened yet
  and for an open one: the counts are the same. Falsifier
  space340-answered-read-scans-every-request: 487 steps become 2487.
- Lead decision (c): the VELDO-0336 rows loss/owner-keep and loss/kept-child, stale since
  VELDO-0318 made the outcome refuse the owner mark, now drive the Keep through the request, the
  owner's settled answer and the owner's signed packet, on the production inbox, presenter and
  settlement. Suite 153 (0336) is 21 of 21. What changed in what the rows show: a request is
  raised only for a worktree, so the mark is on the worktree in both rows; loss/kept-child declares
  an evidence child under the kept worktree and shows that run finished reaches the child alone and
  that the child, its file and a file built beside it stay. The registry keeps an evidence child
  by itself, so that row shows the child is not lost with a kept parent, not that the mark alone
  saved it.

Teeth, finding 340, run last on the clean committed tree with nothing written while it ran: 13
registered, 13 executed, 13 rejected, no reuse, no invalid result (teeth-run.json). Each of the
three new cases is rejected by its own row and no other.

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

## Rows (rows.json), 16 green at 41c8d791 (13 of the build, 3 of the fix round)

- AC1: ac1/one-request (the falsifier row), ac1/next-day.
- AC2: ac2/new-version (the falsifier row; the old presentation is refused as stale_presentation
  before and after the new one is presented), ac2/clock (the clock moved a day with no deferral:
  no request, group, version, message or journal record), ac2/unseen-member.
- AC3: ac3/save, ac3/keep, ac3/discard (the falsifier row), ac3/closed,
  ac3/answered-takes-no-join.
- AC4: ac4/builder (the falsifier row).
- terms/group (the widened terms and their refusals), worker/group (the service's disposition
  task, unchanged, publishes a group's request and carries its Discard in the worker child).

## Falsifiers of the build (now 13 with the fix round: falsifiers.json, teeth-receipt.json)

The paragraphs below describe the build's run of ten at ed136897; the same ten were rejected again
in the run of thirteen at 41c8d791.

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

At 41c8d791: 0340 16, 0336 21, 0318 45, 0327 27, 0345 31, 0300 39, 0312 41, 0317 23, 0297 31 rows
green, the settlement suite (0068) and the inbox suite (0064) green, VELDO-0301 17 green with
ac4/no-clock red as on the base. The six fast checks passed. No space supervisor survived any run.
The paragraph below is the build's record.

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
