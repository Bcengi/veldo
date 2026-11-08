# VELDO-0239 fix round 1 (review 2026-11-05, NOT SOUND)

Fixes exactly F1, F2 and F3 of `review-2026-11-05.md`. No other requirement is added.

## Tests first

`fix1-before.txt`: suite 129 rewritten for the three findings, run against the production modules at 0964756d:
23 of 23 rows red (the batch has no store authority and no starter exists). `fix1-after.txt`: 23 of 23 green.

## F1 (AC1): the command is wired

- `control_batch_service.Starter` is passed as `batches=` by every production construction of Intake:
  control_service_api.py (the project view's Start batch, through messages.send), control_service_projects.py and
  control_workflow_cycle_pm.py (Telegram). It refuses anyone but the project's owner
  (`missing_authority:batch/owner`), takes the eligible units from the store and records one `batch_request` per
  source; nothing is proposed.
- `control_batch_service.BatchLine` runs on the project's line pass (control_service Line, with its land
  configuration and the repository's identity record): assemble, gate once, ask the owner through the inbox; red
  returns each named unit to its fix round, recorded in the store; the owner's settled grant lands it and the
  receipts are written to the store. A landed unit is not batched again.
- init_scaffold installs control_batch.py and control_batch_service.py.
- Rows: wire/constructions (every Intake construction in the installed copy passes the starter), wire/telegram
  (loopback Bot API, production Acquirer, production Intake), wire/api (signed API intake request, as the project
  view sends), wire/line (request to landed with store receipts).

## F2 (AC3, security): the batch enforces its own authority

- `control_batch.Authority` reads a unit's review from its floor record handed off on exactly the reviewed commit,
  its landing from the store's receipts, and the batch approval only as the owner's own signed answer the inbox
  admits (VELDO-0064, VELDO-0068) to the question for exactly the batch subject (tip plus unit list). `Batch.land`
  takes no authority from its caller; a Batch cannot be built without the store's Authority.
- Rows: authority/unsettled-grant (a grant built from b.subject() is refused `missing_authority:approval/batch`;
  a colleague's answer is no settlement), authority/review-commit (a review for another commit makes the unit
  ineligible; a caller's review state is ignored).

## F3 (AC3): the push is classified by the trunk found

- After the swap the trunk is read with ok=None (twice at most): at the tip is landed with the receipts; at the
  watermark is the swap's failure by name (`unavailable_service:git/push` or `git/update-ref`), the batch stays
  green; unreadable is `unknown_outcome:batch/trunk`; anywhere else is trunk_moved.
- Rows: push/at-tip, push/at-watermark, push/elsewhere.

## Falsifiers

`mutations/summary.txt`: the four earlier cases and one per finding (batch239-api-intake-unwired,
batch239-caller-grant-accepted, batch239-review-unbound, batch239-push-status-judged); every case passed
(baseline green, no-op green, mutant red).

## Suites run (each `python3 scripts/selftest.py --suite NAME`; the full gate was not run)

`neighbour-suites-fix1.txt`.
