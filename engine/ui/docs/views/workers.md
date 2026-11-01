# Workers

Route `/workers`. Reads `reads.workers`, live (and `reads.contract` once).

The machines the API derives from the recorded dispatches, grouped Linux then Mac, each with its host label
and how many runs it is running, and each worker run as a card: unit (opening its run), state, station,
project, capability (the dispatch contract's adapter, configuration role and revision, servers and tools),
account, process and record. The read's gaps (the machine registry, VELDO-0125) are named above, and so is the
cap: no engine command sets a worker or machine cap yet, and an account's run concurrency is fixed when it is
registered (VELDO-0062).

Stop asks for an inline confirmation; confirming sends the stop through `src/api/actions.ts` to the route the
contract names, else `workers.stop`, and shows the result beside the card. While the API publishes no such
route (the stop command is VELDO-0041's) nothing is sent and the result is "Not stopped" naming the route and
the gap.

A dispatch is linked by its entity id: inside the data the API's secret scanner may redact the dispatch id's
random suffix.
