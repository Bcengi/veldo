# VELDO-0260: a local landing keeps every checked-out trunk working tree in step with the trunk

Spec: `specs/VELDO-0260-a-local-landing-keeps-every-checked-out-trunk-working-tree-in-step.md` (ready, owner
approval Telegram 39157, History).

## What changed

- `engine/.veldo/control_landing.py` (and the synced `.veldo/` copy), local landings only:
  - `_checkouts` reads `git worktree list --porcelain -z` of the project's repository and takes every working tree
    whose HEAD is `branch refs/heads/<trunk>`; bare, detached and other-branch entries are not taken.
    `_checkout_state` decides clean with `git --no-optional-locks status --porcelain=v1 -z --untracked-files=no`
    plus the MERGE_HEAD, rebase-merge, rebase-apply and CHERRY_PICK_HEAD markers; changes are recorded by path
    (at most 20) and count, never content.
  - `_publish_locally` records the set (path, clean) in the accepted effect before the swap; then: trunk moved ->
    `stale-subject` as before; a tree not clean -> refused `trunk_checkout_dirty`, nothing moved; else each tree is
    moved by `git read-tree -m -u <old> <new>` (`_move_checkout`), a tree that cannot be moved puts the moved ones back
    and refuses `trunk_checkout_unmovable`; the ref swap as before; a lost swap puts every moved tree back on the old
    tip (`restored`). The finished effect and the `local_publication` event carry each tree's outcome and a
    `checkout_outcome` summary; `status()` gains `checkouts`, counts by working-tree outcome.
  - `_recorded` turns either refusal into `trunk_checkout_dirty:<working tree>` / `trunk_checkout_unmovable:<working
    tree>` (taxonomy stale_subject / unavailable_service) with `observed` naming the tree, its changes and the brief
    (`checkout_brief`): the tree, and that the landing waits until it is clean and is re-landed then.
- `engine/.veldo/control_landing_station.py` (and copy): `classify` ends a land whose observed classification is in
  `LG.RELAND` (trunk moved, or either checkout refusal) as `trunk_moved`, so VELDO-0148's re-land follows it.
- `docs/runbook.md` III.10: what the refusal means and what to do.
- New suite `scripts/suites/129_veldo_0260_checkout_in_step.py` (manifest, requires.json); finding 260 in
  `scripts/check_teeth_mutations.py` (four cases, one per declared falsifier).

A repository with no tree holding the trunk lands as VELDO-0235 did: no working tree is read or written; the effect
and event carry `checkouts: []` (the recorded empty set and the "none checked out" count).

## Per acceptance criterion (suite 129, 15 rows)

Before (`before-change.txt`, tests committed ahead of the code in b8d25e68): every AC row red (untracked-ignored, a
preservation row, passed trivially). After (`after-change.txt`, `after-falsifiers.txt`): 15 of 15 green, 41 checks.

| AC | Rows | Falsifier case (mutations/) | Mutant red rows |
|---|---|---|---|
| AC1 | unit/set, set/main, set/linked, set/detached | step260-main-tree-only | set/linked (declared), unit/set, unit/in-progress, observe/metrics |
| AC2 | move/clean, move/untracked-ignored, move/lost-swap | step260-ref-only | move/clean (declared: the candidate shown reversed as staged), set/linked, move/lost-swap, dirty/staged, dirty/unmovable, dirty/reland, observe/metrics |
| AC3 | dirty/edited, dirty/staged, dirty/reland, unit/in-progress, dirty/unmovable, unit/locked | step260-no-clean-check | dirty/edited (declared), dirty/staged, dirty/reland, observe/metrics |
| AC4 | none/other-branch; suites 70, 86, 107, 108, 128 unchanged | step260-main-tree-always | none/other-branch (declared: the other branch's files rewritten), unit/set, unit/in-progress, set/linked, set/detached, observe/metrics |

`mutations/run.json`: `python3 scripts/check_teeth_mutations.py --finding 260`, status passed, 4 registered, 4
executed, 4 rejected; each baseline and no-op green, each mutant red on its declared row. The mutants run on copies,
so the source was never edited; `after-falsifiers.txt` is the restored-green run.

## Suites run (as verify.sh runs one: `python3 scripts/selftest.py --suite <name>`)

`neighbour-suites.txt`: 70_veldo_0057_landing 31 passed, 86_veldo_0148_re_land 26, 107_veldo_0153_identity_push
120, 108_veldo_0153_executor_profile 6, 128_veldo_0235_land_locally 9; 0 failed. Also `check_docs.sh`,
`check_template_sync.sh`, `check_lint.sh`: pass. The full gate was not run (instruction); no proof manifest is
written here, as for VELDO-0235: it follows the gate and review.

## Fix round 1 (independent check 2026-11-05, findings F1 to F4; F5 left as it is)

- F1: `Landing.checkout_held` and `LandStation._checkout_wait`: a re-land following a checkout refusal reads the
  working trees first and, while one is still dirty or unmovable, refuses with the tree named before any land
  dispatch, rebuild or gate; no pass is woken. Row `dirty/waits` drives the service's own `Line.next` /
  `after_land` / `reland` with `FactoryLoop.wake`: three passes while dirty, 0 gated and no new record; once clean,
  exactly one re-land, landed. `dirty/unmovable` does the same with the index lock.
- F2: `specs/index.md` regenerated; `round1-check-generated.txt` (exit 1 before, 0 after).
- F3: a moved tree that cannot be put back after a lost swap is refused `trunk_checkout_restore_failed`
  (taxonomy unknown_outcome, land ends `unknown`, never re-landed), the tree named, outcome `restore_failed`, and a
  brief telling the owner it was not put back. Row `move/restore-failed`.
- F4: the unmovable brief names the actual reason and what clears it (for example the index.lock to remove), never
  "waits until it is clean". Checked in `dirty/unmovable`.
- Red before: `round1-before-fix.txt` (tests committed ahead of the code: 4 rows red, the spin seen as 6 gated
  passes). Green after: `round1-after-fix.txt` (17 of 17 rows, 43 checks). Falsifiers: `mutations/run.json`, six
  cases (the four earlier plus step260-reland-spins, step260-restore-failed-relands), each mutant red on its row.
  Neighbour suites (70, 86, 107, 108, 128, every suite with those prefixes): `round1-neighbour-suites.txt`, 0 failed.
  `check_template_sync`, `check_docs`, `check_lint`, `check_generated`: pass. The full gate was not run.
