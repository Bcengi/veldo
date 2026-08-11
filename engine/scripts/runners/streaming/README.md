# Veldo streaming / server-sent-events runner (reference)

A generic runner for the streaming surface (server-sent events and
websocket-style text frame streams): it drives a stream and proves it is
well-framed, that its chunks arrive in order with none dropped, duplicated, or
reordered, and that it terminates properly. A happy-path check that the stream
produced some output misses the chunk that was dropped in the middle and the
stream that never sent its terminal event. It uses only the Python standard
library.

## Use

```
veldo_streaming_runner.py <journey.json>   # exit 0 = framing, sequencing, terminal hold
test_streaming_runner.sh                   # self-contained regression
```

The stream is a SOURCE seam: a callable returning an iterable of raw frame
strings. This reference defaults to the journey's `fake` list of frames, so the
control logic runs against a fake in-memory stream with no live server. An
adopting repo imports `run()` and passes `source=` its own callable (an SSE
response reader or a websocket recv loop yielding decoded text frames) unchanged.

## Frame format

Each raw frame is a server-sent-events block of `field: value` lines (a single
leading space after the colon is stripped, per the SSE rule); comment lines
beginning with a colon are ignored; a `data` field is required; the event type
defaults to `message`. Framing is strict: a non-comment line with no colon
separator, or an unknown field, is a framing error. A websocket text feed maps
onto the same shape once the recv loop yields decoded frames.

## Journey format

```json
{
  "name": "token stream",
  "sequence_field": "i",
  "expected_events": ["token", "token", "done"],
  "terminal": {"event": "done"},
  "assemble_field": "text",
  "final": [{"type": "contains", "value": "Hello"}],
  "fake": ["event: token\ndata: {\"i\": 0, \"text\": \"He\"}", "..."]
}
```

Assertions (the journey must declare at least one of `sequence_field`,
`expected_events`, `terminal`, or `final`, or it is a journey error - a check
that asserts nothing is not proof; framing is always checked):

- `sequence_field` - over the frames whose JSON data carries this field, the
  values must be contiguous and increasing from 0 in arrival order. A dropped
  chunk (a gap), a duplicate, or a reorder fails naming the expected and observed
  index. This is the distinctive streaming check.
- `expected_events` - the ordered list of frame event types, matched one to one
  (a wrong type, order, missing, or extra fails naming the position).
- `terminal` - a matcher (event and/or data) for the terminal frame; it is
  required and must be the LAST frame. A stream with no terminal fails with a
  did-not-terminate error, and a frame arriving after the terminal fails.
- `final` - behavioral graders (`contains`, `not_contains`, `equals`, `regex`)
  over the concatenation of the non-terminal frames' data (or their
  `assemble_field` value when set).

The `fixtures/` pair demonstrates both outcomes: `pass.stream.json` (a well-formed
token stream) exits 0, and `fail.stream.json` (a stream that dropped a chunk)
exits 1 with the sequence gap named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS stream source,
then points the gate's streaming or contract slot at it. The runner's control
logic - the SSE framing parser, the contiguous-sequence check, the ordered event
match, the terminal enforcement, and the assembled-content graders - is
unit-tested in `scripts/selftest.py` with a fake in-memory source, so the
every-commit gate proves the logic with no live stream. The veldo home repository
ships no streaming surface of its own, so it does not run the runner in its own
gate; it ships it for repos that do.
