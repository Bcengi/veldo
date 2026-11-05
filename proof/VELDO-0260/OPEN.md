# VELDO-0260: open items

## A. Delivering the brief to the owner is outside the footprint

AC3 asks that the owner's landing brief name the working tree and say the landing waits until it is clean. This
change writes that brief (`control_landing.checkout_brief`) into the refusal's detail and the land dispatch's
recorded `observed.brief`, next to the tree and its changes. Today no owner question is opened for a trunk_moved
end (Line.after_land re-lands it), and the code that opens owner questions is `engine/.veldo/control_service.py`,
which is not in this spec's footprint, so it is NOT edited. Exact extra piece, for the reviewer to confirm as a
footprint addition or a follow-up: in `Line.after_land`, when the latest land ended trunk_moved with
`observed.classification` in `control_landing.CHECKOUT_REFUSALS`, send `observed.brief` to the project owner once
per dispatch (as `Line.grant` does with `open_question`).

## B. Re-land cadence while a tree stays dirty (fixed in round 1, finding F1)

A re-land of a land refused for a checked-out tree now waits: `LandStation.land` with `follows` first calls
`Landing.checkout_held` (git worktree list, git status, an index.lock test, a writability test of the directories the
move writes) and, while a tree is still dirty or unmovable, refuses `trunk_checkout_dirty:<tree>` /
`trunk_checkout_unmovable:<tree>` with the brief before any dispatch is opened, rebuilt or gated. Line.reland records
that refusal and does not wake the loop, so nothing spins; once nothing holds, exactly one re-land runs. In fix round 2
(footprint widened to `control_service.py`) the waiting tree is itself a wake source: a change to its git index,
HEAD or index.lock wakes one pass, whose cheap probe decides (row `dirty/wakes`). Still not watched: a tree made
movable again by a directory permission change alone (the `cannot write in` reason) touches none of those files,
so it is noticed on the next pass anything else wakes.

## C. PDF

`docs/runbook.md` changed (III.10). Rendering `pdf/` is the manual release act (`scripts/render_pdfs.py`, Chrome CDP)
and was not run.
