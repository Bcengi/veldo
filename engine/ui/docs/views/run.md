# Run

Route `/runs/<dispatch>` (the dispatch id's slashes are part of the path). Reads `runs.record` from
cursor 0, then follows `runs.record_stream` from the cursor (see
[../ui/run-terminal.md](../ui/run-terminal.md)). The view holds the record follower and passes it to the
terminal, so the header and the terminal read one record.

The header is the run's headline: the unit as the title; its state (Running, Done, Reconnecting) with a
lamp and the elapsed time (first line to now while running, first to last line once done); the engine
and model (from the record's own start lines, `runFacts`), the host, the station and the project. The
dispatch id is a copyable detail behind "Dispatch id". On a phone the headline wraps onto a second line
rather than clipping (the project is left out there); no fact is cut off. Then the station strip, the control bar and the
record, which takes the rest of the height.

States: loading, live, reconnecting, ended (with the committed line count and digest), empty ("No line
yet"), error (`unauthorized:out_of_scope`, `missing_evidence:unknown_run`, a session that ended): the
refusal alone, no record controls, Try again only when retryable.
