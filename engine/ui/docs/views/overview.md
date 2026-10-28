# Overview

Route `/`, the landing screen after sign-in. Reads `reads.workers` and `reads.work` (the runs store) and
`reads.decisions` (the decisions store); acts on nothing itself.

From the top: the factory's name as the title and Refresh; the andon board (running, blocked, failed,
waiting on you; [../ui/andon-board.md](../ui/andon-board.md)); the decision that has waited longest
(the earliest published presentation) with how long it has waited, when it is due and "Answer it"; the
hosts with their lamps and run counts; then the two main panels, Waiting on you (the top five of the
ranked inbox) and Runs (the first six, running first), each with a link to its full screen.

States: loading (the board's cells and rows as skeletons), populated, empty panels ("Nothing is waiting
on you", "No worker has run yet") under a board of zeros, a refused work read (blocked and failed show
"Not readable"), and both reads refused (one refusal for the screen, for example
`unauthorized:no_project`).
