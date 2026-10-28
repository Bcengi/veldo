# Runs

Route `/runs`. Reads `reads.workers` (dispatches) and `reads.work` (each unit's state for the
miniature strip; a refused work read leaves the strip unlit). Running runs first, then ended.

States: loading, empty ("No worker has run yet"), error (refusal, for example
`unauthorized:no_project`), ready. Each row is a link to the run.

The dispatch is taken from the entity id (`dispatch:<id>`), because the read model may redact the
data's own `dispatch_id` as high entropy.
