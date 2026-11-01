# Backlog

Route `/backlog`. Reads `reads.work` (backlog items, execution units) and `reads.proof` (completion receipts),
live, and `reads.contract` once.

A `TreeTable` of items in the authority's priority order (rank 1 first, unranked last), with their state and
open blockers; each item expands to the units taken from it, each with its state and specification. A unit is
"Landed" only when the proof read holds its landing's completion receipt; a unit whose record says COMPLETED
without one is "Built, landing not confirmed" (`src/features/backlog/completion.ts`, VELDO-0131 AC2).

Reorder: drag a row onto another on a desktop, or Move up / Move down on any row (Alt+Up and Alt+Down on a
focused move button), by keyboard or touch; every move is announced. The new order is the owner's draft.
"Save priority order" maps it to ranks (the prioritized items in order take ranks 1 to 5; an unchanged rank
sends nothing) and sends one rank command per changed item through `src/api/actions.ts`, to the route the
contract names, else `backlog.reprioritize`, stopping at the first refusal, which it names. While the API
publishes no such route (the command is VELDO-0078's reprioritize) nothing is sent and the result names the
route and the gap. "Back to the stored order" drops the draft. Details opens the item's facts, blockers and units beside the
table on a desktop and as a sheet on a phone.
