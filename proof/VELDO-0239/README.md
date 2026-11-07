# VELDO-0239: batch landing

Spec: `specs/VELDO-0239-batch-landing.md` (ready; owner approvals Telegram 39096 and 39157, see its History).

## What changed

- `control_batch.py` (engine and synced `.veldo/` copy), new. `Batch.assemble` takes every unit whose review has
  passed and that has not landed (`eligible`), in review-completion order, and merges each reviewed commit with
  --no-ff onto the trunk watermark in a new isolated clone (git init with no template, the project repository's
  objects through alternates, a detached checkout; the watermark fetched from the remote for land_and_push, read
  from the local trunk for land_locally). The lander's append-only unions and projections are resolved as the
  lander does; any other conflict leaves the unit out as `conflict:<unit>`. After each merge the project's renumber
  hook (an argv) runs in the clone with the watermark and the merge commit; its change is a separate renumber
  commit with every rename recorded; a non-zero exit leaves the unit out as `hook_failed:renumber:<unit>`; no hook,
  no renumbering. No reviewed unit (or every unit left out) is `empty` and runs nothing. `Batch.gate` gates the tip
  once with VELDO-0058's `observe_gate` (exit 75, the VELDO-0220 host lock held, is no run), reads every declared
  stage, inventories each red with its stage, check and units, tells the owner and returns each named unit to its
  fix round. `request_approval` / `approval_request` ask once with the units and their reviews, the renumber
  commits, the gate and the destination in words; the bound subject is the tip and the unit list (with watermark,
  project and destination). `Batch.land` refuses a red batch `missing_evidence:gate`, any other subject
  `stale_subject:batch` (and asks again), a unit lacking another approval by that approval's name; it accepts the
  gate observation again, then makes one compare-and-swap from the watermark to the tip (push leased on the
  watermark, or `update-ref` of the local trunk), re-reads the trunk and writes a `revision_landed` receipt per unit
  naming the batch. A moved trunk ends `trunk_moved`; `Batch.reland` re-merges, re-runs the hook, re-gates and asks
  again. Every step is a batch record entry and an observe event; `metrics()` counts batches by outcome, units per
  batch, left-out units by reason, reds per batch and gate seconds.
- `control_intake.py` (engine and synced copy): `Intake(batches=...)`; `batch_started` hands the owner's
  `/batch <project>` to that starter and writes no proposal. With no starter the message is ordinary intake.
- `engine/ui/src/features/projects/projects.ts` (`batchCommand`) and `engine/ui/src/views/ProjectsView.vue`: the
  selected project's detail panel has "Start batch", which sends `/batch <project>` through messages.send and shows
  the batch outcome or the refusal.
- New suite `scripts/suites/129_veldo_0239_batch_landing.py` (manifest, requires.json regenerated);
  `scripts/check_teeth_mutations.py` finding 239 (four cases).

Lander, land station and single-unit Landing are not changed.

## Per acceptance criterion

Suite 129 before the change (`before-change.txt`, the suite committed first, 14b08535, with no control_batch.py):
14 of 14 rows red. After (`after-change.txt`): 14 of 14 green, 40 checks.

| AC | Rows | Result |
| --- | --- | --- |
| AC1 | batch/renumber, batch/conflict, batch/hook-failed, batch/no-hook, batch/empty, batch/command; UI: ProjectsBatch.spec.ts | green |
| AC2 | gate/once, gate/inventory | green |
| AC3 | land/together, land/local, land/stale, land/other-approval, land/trunk-moved | green |
| AC4 | single/unchanged; suites 70 (VELDO-0057), 86_0148 (VELDO-0148), 128 (VELDO-0235) unchanged | green |

- AC1: two units each add migration 037; the hook renames the second to 038 in its own commit whose parent is the
  merge, recorded as `037_orders.sql -> 038_orders.sql`; the tip has one 037. An unreviewed and an already landed
  unit are not taken. A third unit conflicting with the first in README.md is left out as `conflict:UNIT-3` and the
  other two are in. A hook exiting 3 leaves its unit out as `hook_failed:renumber:UNIT-6`. No hook: no hook run and
  no renumber commit. No reviewed unit: `empty`, no clone, no gate, nobody asked. `/batch <project>` (and
  `/batch@bot <project>`) is the command; intake hands it to the starter and writes no proposal. UI:
  `ui-vitest-before.txt` (3 of 3 red), `ui-vitest-after.txt` (3 of 3 green, ProjectsView.spec.ts 2 of 2 and
  projects.spec.ts 5 of 5 unchanged, vue-tsc clean); run from the locked dependencies in a scratch copy. The before log escapes vitest's
  non-ASCII marks as `\uXXXX` (the docs check allows only ASCII).
- AC2: a logging `bash` first on PATH counts each start of a verifier in candidate mode: exactly one per batch. A
  batch with one unit red in the unit stage and another red in the integration stage inventories both stages, each
  check and its unit; the owner is told once, UNIT-4 and UNIT-5 return to their fix rounds, nobody is asked, and
  the land is refused `missing_evidence:gate` with the origin unchanged.
- AC3: the request names both units with their reviews, the renumber commit, the green gate and "land and push to
  origin"; the grant lands the batch: the origin's pre-receive log shows one update from the watermark to the tip,
  and each unit has a receipt naming the batch. land_locally moves the caller's main and pushes nothing. A grant for
  another unit list, or another tip, is refused `stale_subject:batch` and the owner is asked again; a unit lacking
  its protected-path approval stops the batch by that name. A trunk moved by another pusher ends `trunk_moved`; the
  re-land re-merges onto it (the payments migration becomes 040), gates once more and asks again; the old grant is
  refused and the fresh grant lands.
- AC4: lander.py, control_landing.py and control_landing_station.py carry no batch path; the landing suites pass
  unchanged (`neighbour-suites.txt`).

## Falsifiers (finding 239), each run alone through the gate's driver

`check_teeth_mutations.py --case <name>`: every case passed (baseline green, no-op green, mutant red). Receipts in
`mutations/*.txt`, summary `mutations/summary.txt`.

- batch239-hook-not-run (AC1): the hook is never run. batch/renumber red on two files numbered 037 (the run then
  stops on the missing renumber commit, so every later row is red too).
- batch239-stops-at-first-red (AC2): the inventory stops at the first red stage. gate/inventory red: the
  integration stage is missing.
- batch239-swap-per-unit (AC3): each unit is landed by its own compare-and-swap. land/together red on two trunk
  moves.
- batch239-single-through-batch-0057 (AC4): a single unit's landing is published by the batch's swap and kept as a
  batch record. VELDO-0057's exact-tip/compare-and-swap red (no publication effect of its dispatch).

## Suites run

`neighbour-suites.txt`: the landing suites and the suites that load control_intake, each run alone as
`python3 scripts/selftest.py --suite NAME`. `scripts/verify.sh` was not run.

Open items: `OPEN.md` (the hook's source is VELDO-0253; the live service's batch starter, store receipts).
