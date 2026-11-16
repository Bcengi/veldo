# VELDO-0342 proof

Implementation df1d2c6a, on VELDO-0340 fix round 1 at 73c7b832 (the blocker record e5dbc0df is between
them and holds no code). Builder evidence, not independent review. All three criteria remain pending
the lead gate and independent review. Every suite, check and teeth case in the json files beside this
one was run at df1d2c6a.

## What was built

A review group's request offers the three group picks and, for each member, the same three with the
letter w and the member's index: accept discard w2. The index is the member's place in the order it
joined. It is on the group record, in the signed terms (`indexes`) and in the member's own
disposition, and the text names each worktree by it, so the text and the picks name a worktree
alike after another member left.

A member pick is one write. The member it names gets the answer and is recorded with it on the group
record. Every other member still in the group stays deferred and gets a new request on the same
record: its own alias, version 1, the indexes unchanged. The settled request is kept on the record
with its answer, and an answer to it is refused as request_closed. The members left are written in
that same write, deferred with a requested disposition, which is what the service's disposition
task wakes on: the new request is published with no polling. The group closes when its last member
leaves.

The picks offered are those of the lowest indexes that fit one message part, measured by the Ledger
with the presenter's own limit, room for the part line and counting. The terms name them (`picks`)
and the text names the members without one. The Settlement does not judge the size.

A group stays the one group of its scope and day that takes a join after a member pick, and also
between a settled member pick and its application.

The lead's decision (specification History, 2026-11-16) widened the footprint by the settlement, the
remover and the VELDO-0340 row terms/group. engine/.veldo/control_service.py did not change, and
neither did the presenter or the VELDO-0327 and VELDO-0318 suites (sources.json holds the digests,
equal to those at 73c7b832).

## Rows (rows.json), 18 green at df1d2c6a

- AC1: ac1/offer (twelve choices for three members, each worktree named beside its index),
  ac1/member-discard (the falsifier row: accept discard w2 in a group of three; member 2 alone is
  discarded, saved in the snapshot store first; members 1 and 3 are on disk with their edits under
  a new request on the same record, in one write), ac1/request-closed, ac1/member-keep (the
  authority alone is refused, the owner's packet naming another member keeps nothing, the packet
  naming member 1 keeps it alone), ac1/last-member (accept save w3 saves the last member on its
  kept branch and the group closes), ac1/changed-member (a file added to member 2 after the request
  was shown: accept discard w2 removes nothing, and the member joins the open group again as
  member 3 with its new file list).
- AC2: ac2/fit (the falsifier row: 74 real review worktrees in one group; the request offers the
  group picks and the member picks of members 1 to 69, its text names 70 to 74, the presentation is
  rendered and sent with the choices in its last part, the presenter refuses to render the picks of
  member 70 added to the same receipt, and an answer for member 74 names no offered choice),
  ac2/next (accept discard w10 discards member 10 alone and the next request offers a pick to
  member 70).
- AC3: ac3/one-open (a deferral joins the open group, also after a member pick, under the next
  index and a new version of the current request), ac3/next-sequence (the falsifier row: after the
  day's group is closed by an answer, a deferral the same day has a request, in group 2),
  ac3/pending-join (a deferral between a settled member pick and its application joins the same
  group, is on no request, and is listed by the request raised when the pick is applied).
- A member pick is an answer for no other member: pick/ledger, pick/signal (member 1 written as
  authorized past the Ledger, and a Ledger that lets the effect through: Signal carries nothing),
  pick/remover (Signal let through as well: the remover refuses and member 1 is on disk),
  pick/single (a request for one worktree offers exactly three picks; a member pick written past
  the Settlement is no settled answer for it).
- terms/indexes (the terms and their refusals), next/gone (the member a settled pick names is gone:
  the next publish raises the request for the members left), worker/member-pick (the service's
  disposition task, unchanged, in the worker child: one pass carries the Discard of member 2 alone,
  and the task raises the request for members 1 and 3).

## Falsifiers (falsifiers.json, teeth-receipt.json, teeth-run.json)

Finding 342 ran last, once, on the clean committed tree df1d2c6a, with nothing written in the
worktree while it ran: 15 registered, 15 executed, 15 rejected, no reuse, no invalid result, no
surviving worker, each mutant applied once, baseline and no-op runs green for every case.

The three declared falsifiers:

- AC1 space342-member-pick-reaches-the-whole-group: ac1/member-discard red. Members 1 and 3 are made
  due for Discard and the group closes. The specification says the row finds member 1 discarded.
  Under this one change it is not removed from disk: Signal reads the settled choice itself and
  refuses a pick that names another member, and so does the remover. The row fails on member 1
  being given the Discard. Applied by hand in an export of df1d2c6a as well, with the same result.
- AC2 space342-every-member-pick-whatever-the-size: ac2/fit red. All 74 members are offered picks,
  the presenter refuses to render (presentation_too_long) and there is no presentation.
- AC3 space342-reuse-the-day-key: ac3/next-sequence red. The join is refused and the worktree
  deferred after the answer has no request.

Twelve more, for what the build added: the Ledger, Signal and the remover each taking a pick for
another member (three cases, each rejected by its own row alone), a request for one worktree taking
a member pick, the authority keeping by a member pick, the next request raised while the pick can
still be applied, no next request when the named member is gone, a member that left being unable
to join again, a join in the window opening a second group, worktrees numbered by their place in
the list, the members without a pick not named, and picks for any indexes.

## Regressions (checks.json)

At df1d2c6a: 0342 18, 0340 16 (only terms/group changed), 0336 21, 0318 45, 0327 27, 0345 31,
0300 39, 0312 41, 0317 23, 0297 31 rows green, the settlement suite (0068) 8 and the inbox suite
(0064) 18 green. VELDO-0301 17 green with ac4/no-clock red, as on the base. Validation, docs,
template sync, lint and the two boundary checks passed. Suite 153 (0336) is the one suite of 151
and up that was run; no gate was run. No space supervisor survived any run.

## Not built

- A group whose request was canceled or declined (the lead's decision): no criterion and no section
  of the design names it. Its members stay deferred on disk with no live request; nothing is lost.
- A client that signs the owner's Keep packet: none exists in the repository (as VELDO-0318 and
  VELDO-0340 found). After a settled accept keep w2 the other members wait for that packet before
  their new request is raised.
- The console's listing of a group's members with their picks: VELDO-0319.

## For the reviewer

- The two lines of the last message part are written once more in the Ledger (_picks_that_fit),
  because the presenter is outside the footprint. ac2/fit binds them at the boundary; a change of
  the presenter's last part that is not mirrored would turn that row red.
- A settled member pick whose member cannot take it (accept keep w2 with no packet, or a member
  that changed state in a way the next publish does not see as gone) leaves the other members
  waiting. They stay deferred on disk.
- VELDO-0340 lists every member of a group at a join, whether or not it is still deferred. That is
  unchanged here except that a member answered by a pick, or found gone when a request was raised,
  is no longer listed.
