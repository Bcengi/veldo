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

## B. Re-land cadence while a tree stays dirty

Both checkout refusals end the land as trunk_moved, so `Line.after_land` re-lands on its next pass, as for a moved
trunk. While the tree stays dirty each re-land rebuilds and gates a candidate and is refused again at publication,
nothing moved. The station already records no bound or backoff for a trunk that keeps moving (hardening); the same
applies here. Recorded, not built: the spec authorizes no retry policy.

## C. PDF

`docs/runbook.md` changed (III.10). Rendering `pdf/` is the manual release act (`scripts/render_pdfs.py`, Chrome CDP)
and was not run.
