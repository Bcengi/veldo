# Run

Route `/runs/<dispatch>` (the dispatch id's slashes are part of the path). Reads `runs.record` from
cursor 0, then follows `runs.record_stream` from the cursor (see
[../ui/run-terminal.md](../ui/run-terminal.md)). The station strip uses the runs store's unit states.

States: loading, live, reconnecting, ended (with the committed line count and digest), empty ("No line
yet"), error (`unauthorized:out_of_scope`, `missing_evidence:unknown_run`, a session that ended).
