# Runs

Route `/runs`. Reads `reads.workers` (dispatches) and `reads.work` (each unit's state for the miniature
strip and the failed and blocked words; a refused work read leaves the strip unlit). The header
summarizes the rows on screen: how many runs, distinct projects and distinct hosts (`runsSummary`,
computed from the displayed rows only). Two cards: Active (prepared, accepted, running), then Stopped
(done, failed, blocked, refused). Rows are `RunList` ([../ui/run-list.md](../ui/run-list.md)): unit,
project, host, the line in miniature and the status badge with its word.

States: loading (row-shaped skeletons), empty ("No worker has run yet"), error (refusal, for example
`unauthorized:no_project`; Try again only when retryable), ready. Each row is a link to the run.

The dispatch is taken from the entity id (`dispatch:<id>`), because the read model may redact the
data's own `dispatch_id` as high entropy.
