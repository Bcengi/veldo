# Overview

Route `/`, the landing screen after sign-in. Reads `reads.workers` and `reads.work` (the runs store) and
`reads.decisions` (the decisions store); acts on nothing itself.

From the top: the factory's name as the title and Refresh; the summary panel (running, blocked, failed,
waiting on you; [../ui/andon-board.md](../ui/andon-board.md)); beneath it the decision that has waited
longest (the earliest published presentation) with its question, how long it has waited and when it is
due as badges, and a prominent "Answer it", beside the host roster (each host's lamp, its run count and a
running or idle badge); then the two main cards, Waiting on you (the top five of the ranked inbox) and
Worker runs (the first six, running first, with how many are running), each with a link to its full
screen. Every count is computed from the API's answers.

States: loading (the board's cells and rows as skeletons), populated, empty panels ("Nothing is waiting
on you", "No worker has run yet") under a board of zeros, a refused work read (blocked and failed show
"Not readable"), and both reads refused (one refusal for the screen, for example
`unauthorized:no_project`).
