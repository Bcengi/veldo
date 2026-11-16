# VELDO-0319 proof

Implementation 5f3afd34 (commits 322f2a48, 30e9bab6, cde32538, b0711d3d, 5f3afd34), on VELDO-0342 at
bf962cfc. Builder evidence, not independent review. All four criteria remain pending the lead gate and
independent review. Every suite, check and teeth case in the json files beside this one was run at
5f3afd34.

## What was built

Four reads of the space ledger, space.pools, space.usage, space.pending and space.removed, each a view
made by control_api_models from the ledger's records and served by the authority's one `read`, with the
member's scope applied and each path redacted part by part. The Space screen (engine/ui, route /space,
in the navigation) shows Pools with the waiting runs and the runs that would have waited, Usage by
project, ticket and kind, Pending removal with the reason in words, the retry events and the decision
request (a review group's worktrees under their one request, by index, with the answers each may be
given), Worktrees with Abandon, Removed, and Reconcile. The runs list shows a run that would have
waited with one line on its row, and a waiting run as a row of its own. The screen follows the record
stream (useLiveRead); nothing reads on a timer.

AC3 is built as the lead amended it (specification History, 2026-11-16): Reconcile and Abandon are the
signed owner commands that exist today, an answer to a space request is given on the Decisions screen
through the settlement path the request already uses, and no route or button exists for Adopt, Confirm,
Wrong or the mode switch. Each comes with its own ticket (VELDO-0320, VELDO-0332, and for Adopt the
ticket the lead confirms; the History line is on VELDO-0315).

## Rows (rows.json), 34 green at 5f3afd34

- 150_veldo_0319_space_screen, 21 rows at the API on a real store, Ledger, authority and API edge.
  AC1: ac1/per-project-ticket-kind, ac1/totals and ac1/deferred-counts (the falsifier rows),
  ac1/plain-and-no-project, ac1/worktrees. AC2: ac2/in-use-folder (the falsifier row),
  ac2/every-pending, ac2/requests, ac2/removed. AC3: ac3/routes-signed, ac3/unsigned-refused (the
  falsifier row), ac3/not-owner-refused, ac3/owner-accepted, ac3/no-dead-route. AC4: ac4/pools-numbers,
  ac4/record-reaches-read. Also scope/member, scope/digest, redact/locator, words/deferrals,
  canon/synced.
- 150_veldo_0319_space_ui, 13 rows in system Chrome against the built UI and the real API edge and
  authority. AC1: ac1/usage-table-1280, ac1/usage-table-390. AC2: ac2/pending-removed. AC3:
  ac3/owner-commands, ac3/answer-path. AC4: ac4/live-no-clock (the falsifier row), ac4/runs-list. Also
  ui/states-360, -390, -1280 and -1440 (loading, error, empty, populated, the Abandon confirmation, a
  refused Reconcile and the runs list: no page-wide overflow, no overlapping controls, no text out of
  its box, the primary action visible and 44 px on a phone, axe, no content security policy
  violation), ui/api-only and unit/space.

## Falsifiers (falsifiers.json, teeth-receipt.json, teeth-run.json)

Finding 319 ran last, on the clean committed tree 5f3afd34, with nothing written in the worktree
while it ran. The first run took all ten registered cases: the eight API cases were rejected, and the
two browser cases were invalid_baseline, because the driver ran them in its confined leg, where every
row of the browser suite fails by name (the suite needs system Chrome and the npm cache; the
unconfined list is scripts/gate_unconfined.json, a protected path). That receipt is
teeth-receipt-first.json. The last run took the eight API cases alone: 8 registered, 8 executed, 8
rejected, no reuse, no invalid result, no surviving worker, baseline and no-op runs green for every
case (teeth-receipt.json). The two browser cases were then applied by hand, once each, in an export of
5f3afd34 (the registered edit, the whole browser suite): both red on their rows. Once the lead has
added the suite to the unconfined list, the gate's mutation stage runs them itself.

The four declared falsifiers:

- AC1 space319-usage-sums-only-present-items: ac1/totals and ac1/deferred-counts red.
- AC2 space319-pending-hides-deferred-items: ac2/in-use-folder red.
- AC3 space319-abandon-as-a-plain-read-route: ac3/unsigned-refused red (the request with no session
  reaches the service's abandon).
- AC4 space319-poll-on-an-interval, by hand: space319ui/ac4/live-no-clock red (with the page's clock
  stopped no timer fires and the new hold does not reach the screen); ui/api-only red as well.

Six more, for what the build added: Reconcile for any member, Removed oldest first, held counting a
waiting hold, the advised holds not listed, a path served with its credential, and, by hand, a run row
without its hold (space319ui/ac4/runs-list and unit/space red).

## Screens (screens/, screens.json)

32 PNG files, full page, at 390 and 1440 px in light and in dark: the populated screen, pending
removal, the Abandon confirmation, a refused Reconcile, empty, error, loading, and the runs list with
its space lines. Taken at 5f3afd34 by the browser suite (13 rows green in that run) and reduced to 48
colours, the largest about 0.2 MB. The fixed navigation is drawn once in the middle of a full-page
phone image; that is the capture, not the page. Each state was read by the builder at both widths:
long paths wrap inside their card, sizes are in binary units, the empty and error states say what to
do, and no record text is shown raw. A refused command shows its refusal code beside its control, as
the other screens do.

## Regressions (checks.json)

At 5f3afd34, rows green: 0342 18, 0340 16, 0318 45, 0312 41 (Abandon), 0130 45 (the API), 0164 19
(scoped reads), 0145 7, 0227 7, 0159 7, 0163 10, 0131 suite 120 14 and suite 124 8. The UI typecheck
passed and Vitest ran 155 tests in 33 files green. Validation, docs, template sync, lint and the two
boundary checks passed. No suite of 151 and up and no gate was run. No space supervisor of these runs
survived any of them.

Two things to know:

- Suites 121 and 122 (VELDO-0131, every factory screen at four widths) are load-dependent on this
  host. A row goes red with "did not open" for a different screen each time. On this tree 121 was red,
  green, red, red and 122 was red once in the earlier session and then green four times; on an export
  of the base bf962cfc 121 was green three times and 122 red, red, green. Another builder was running
  suites on the host throughout. Every row was green on this tree at least once. The lead's gate run
  is the one that counts.
- Suite 123 (VELDO-0174, conversations) has 17 rows red with "'types.SimpleNamespace' object has no
  attribute 'space'", the same 17 on the base export. Inherited, left.

## Not built

- Buttons and routes for Adopt, Confirm, Wrong and the mode switch (the lead's amendment of AC3).
- The Modes, Kept work missing, Reports and Protected sections, the run view's space panel and the
  overview's pool under its floor: design 10 lists them and no criterion of this ticket does.
- A pool's capacity and its free space now: no ledger record holds them and a read measures nothing.
- A group of its own for waiting runs on the runs screen, a link from the phone's You screen and the
  runs list component's page: RunsView.vue, YouView.vue and docs/ui/run-list.md are outside the
  footprint. On a phone the screen is reached by its address.
- A client that signs the owner's Keep packet: none exists, so an accept keep answered on the
  Decisions screen settles and is not applied (as VELDO-0318, 0340 and 0342 found).

## For the reviewer and the lead

- scripts/gate_unconfined.json (protected) needs an entry for 150_veldo_0319_space_ui, which needs
  system Chrome and the npm registry as suites 120 to 124 do. Until then the suite's rows and its two
  teeth cases fail by name in a confined run.
- The owner of the Adopt command and its console button is still to be confirmed (History of
  VELDO-0315).
- scripts/suites/71_veldo_0130_api.py, control_api_assertion.py and control_service.py are in the
  widened footprint and did not change (sources.json holds their digests, equal to the base).
