# VELDO-0239: open items

## A. The renumber hook's source is VELDO-0253 (not built)

AC1 names the renumber hook as "a command named in the project's file in the installation repository
(VELDO-0253)". VELDO-0253 has no specification in this repository yet, so there is no project file to read it from.
What this spec owns is built: `control_batch.Batch(hook=[argv...])` runs the named command in the batch clone with
the watermark and the merge commit appended, commits its change as a separate renumber commit, records every rename,
and leaves the unit out as `hook_failed:renumber:<unit>` on a non-zero exit; `hook=None` merges with no renumbering.
Missing piece, for VELDO-0253: read the hook command from the project's file in the installation repository and hand
it to the batch. Nothing here reads or invents that file.

## B. The live service does not yet construct a batch starter (resolved in fix round 1, see fix-round-1.md)

The owner's command reaches the batch through one seam: `control_intake.Intake(batches=...)`. A `/batch <project>`
message (Telegram, or the same text the project view sends through messages.send) is handed to that starter as
`(project, principal, source)` and no proposal is written; with no starter wired the message stays ordinary intake.
`control_batch.run(Batch(...), units)` is the starter's body (assemble, gate once, ask). Not built here: the
service code that, for a project, reads its repository, trunk, remote and landing destination, the units whose
independent review has passed and that have not landed (with their reviewed commits and review completion times),
checks that the principal is the project's owner, and constructs that starter with the owner's approval request
(VELDO-0068 settlement), the fix-round return of each named unit and the receipt writer. The batch takes each of
these as an argument (`ask`, `fix_round`, `receipt`, `requirements`, `tell`), so the wiring adds no batch logic.

## C. Receipts are the batch record's, not yet the authority store's (resolved in fix round 1: batch receipts are
written to the store and read back as landed)

Each landed unit gets a `revision_landed` receipt naming the batch (schema `veldo.batch_receipt/v1`), in the batch
record and through the `receipt` callable. The single-unit receipt (control_landing, committed in the store with the
VELDO-0028 publication effect and projected by VELDO-0051 to spec.shipped) is not used for a batch, because its
store transition binds one unit to one dispatch's publication effect. Committing batch receipts in the store and
projecting them is part of the wiring in B.

## D. Notes for the reviewer

- The batch's compare-and-swap is its own (`git push --force-with-lease=<trunk>:<watermark>`, or
  `git update-ref <trunk> <tip> <watermark>` for land_locally), with the remote re-read afterwards. It does not go
  through the VELDO-0028 effect executor; see C.
- "No stage is skipped because another stage is red": the gate (the project's own verify.sh, serial loop or the
  VELDO-0216 graph) already runs every stage; the batch reads every declared stage from the one observation and
  inventories every red. The falsifier stops the batch's reading at the first red stage.
- A failing check is a line of its stage's output that starts FAIL, FAILED or ERROR; a red stage that names none is
  inventoried as the stage itself. A unit is named for a red when one of its paths (its merge, and the names its
  renumber commit gave) appears in the check's line.
- Runs stay unrestricted: the hook runs in the clone with the cleaned Git environment, no sandbox and no fence.
