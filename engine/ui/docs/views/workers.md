# Workers

Route `/workers`. Reads `reads.workers`, live (and `reads.contract` once).

The machines the API derives from the recorded dispatches, grouped Linux then Mac, each with its host label
and how many runs it is running, and each worker run as a card: unit (opening its run), state, station,
project, account, process and record. The read's gaps (the machine registry, VELDO-0125) are named above.

Stop asks for an inline confirmation; confirming shows the result beside the card. While the API publishes no
`worker_stop` route (VELDO-0041) the result is "Not stopped" with that gap; nothing is sent.

A dispatch is linked by its entity id: inside the data the API's secret scanner may redact the dispatch id's
random suffix.
