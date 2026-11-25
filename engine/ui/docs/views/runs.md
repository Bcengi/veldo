# Runs

Route `/runs`. Reads `reads.workers` (dispatches) and `reads.work` (each unit's state for the miniature
strip and the failed and blocked words; a refused work read leaves the strip unlit). The header
summarizes the rows on screen: how many runs, distinct projects and distinct hosts (`runsSummary`,
computed from the displayed rows only). Two cards: Active (prepared, accepted, running), then Stopped
(done, failed, blocked, refused). Rows are `RunList` ([../ui/run-list.md](../ui/run-list.md)): unit,
project, host, the line in miniature and the status badge with its word.

VELDO-0319: the store also reads `space.pools` (a refused read leaves the rows without it). A run that would
have waited for space (report mode: it was started on advice) says so on its row in one line, with need, free,
held and floor. A run that waits for space has a hold and no dispatch yet, so it is a row of its own, after the
live runs: "Not dispatched yet", its project, the same line and the word "Waiting for space"; it is not a link,
since there is no run to open, and it is not counted as running. It is listed in the Stopped card with the
blocked runs.

States: loading (row-shaped skeletons), empty ("No worker has run yet"), error (refusal, for example
`unauthorized:no_project`; Try again only when retryable), ready. Each row is a link to the run.

The dispatch is taken from the entity id (`dispatch:<id>`), because the read model may redact the
data's own `dispatch_id` as high entropy.
