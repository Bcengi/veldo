#!/usr/bin/env python3
"""VELDO streaming / server-sent-events runner (reference).

Drives a stream a service produces (token-by-token model output, a live event
feed, a progress channel) and proves it is well-framed, that its chunks arrive in
order with none dropped, duplicated, or reordered, and that it terminates
properly. A happy-path check that the stream produced some output misses the
chunk that was dropped in the middle and the stream that never sent its terminal
event. This runner asserts the sequencing, the framing, and the final.

  veldo_streaming_runner.py <journey.json>

The stream is a SOURCE seam: a callable returning an iterable of raw frame
strings. This reference defaults to the journey's fake list of frames, so the
control logic runs against a fake in-memory stream with no live server. An
adopting repo passes source=its own callable (an SSE response reader or a
websocket recv loop yielding decoded text frames) unchanged.

Frame format is server-sent events: each raw frame is a block of `field: value`
lines (an optional leading space after the colon is stripped, per the SSE rule),
comment lines beginning with a colon are ignored, and a data field is required.
The event type defaults to "message". Framing is strict: a non-comment line with
no colon separator, or an unknown field, is a framing error.

Journey format (JSON):
  {
    "name": "token stream",
    "sequence_field": "i",
    "expected_events": ["token", "token", "done"],
    "terminal": {"event": "done"},
    "assemble_field": "text",
    "final": [{"type": "contains", "value": "Hello"}],
    "fake": [
      "event: token\\ndata: {\"i\": 0, \"text\": \"He\"}",
      "event: token\\ndata: {\"i\": 1, \"text\": \"llo\"}",
      "event: done\\ndata: [DONE]"
    ]
  }

Assertions (the journey must declare at least one of sequence_field,
expected_events, terminal, or final, or it is a journey error - a check that
asserts nothing is not proof; framing is always checked):
  sequence_field   over the frames whose JSON data carries this field, the values
                   must be contiguous and increasing from 0 in arrival order (a
                   gap, a duplicate, or a reorder fails naming expected vs got)
  expected_events  the ordered list of frame event types matched one to one (a
                   wrong type, order, missing, or extra fails naming the position)
  terminal         a matcher (event and/or data) for the terminal frame; it is
                   required and must be the LAST frame (no terminal fails; a frame
                   after the terminal fails)
  final            behavioral graders (contains, not_contains, equals, regex) over
                   the concatenation of the non-terminal frames' data (or their
                   assemble_field value when set)

Exit 0 = every assertion holds. Exit 1 = the first failing assertion, a framing
error, a source error, or an asserts-nothing journey is named.
"""
import json
import re
import sys
from pathlib import Path


def _json_or_none(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def grade(output, graders):
    """Behavioral graders over the assembled stream content. Mirrors the other
    runners' graders. Returns a list of failure strings."""
    failures = []
    for g in graders or []:
        kind = g.get("type")
        value = g.get("value")
        if kind == "contains":
            if value not in (output or ""):
                failures.append(f"final contains: assembled stream does not contain {value!r}")
        elif kind == "not_contains":
            if value in (output or ""):
                failures.append(f"final not_contains: assembled stream unexpectedly contains {value!r}")
        elif kind == "equals":
            if output != value:
                failures.append(f"final equals: expected {value!r}, got {output!r}")
        elif kind == "regex":
            if re.search(value, output or "") is None:
                failures.append(f"final regex: {value!r} did not match the assembled stream")
        else:
            failures.append(f"final: unknown grader type {kind!r}")
    return failures


def parse_sse_frame(raw):
    """Parse one raw server-sent-events frame block. Returns (frame, None) on
    success or (None, error) on a framing error. A frame is {event, data,
    fields}; the event defaults to 'message'; comment lines (a leading colon) are
    ignored; a data field is required; framing is strict (a non-comment line with
    no colon, or an unknown field, is an error)."""
    event = "message"
    data_lines = []
    fields = {}
    for line in raw.split("\n"):
        if line == "":
            continue
        if line.startswith(":"):
            continue
        if ":" not in line:
            return None, f"line has no field separator: {line!r}"
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event = value
        elif field == "data":
            data_lines.append(value)
        elif field in ("id", "retry"):
            fields[field] = value
        else:
            return None, f"unknown SSE field {field!r}"
    if not data_lines:
        return None, "frame has no data field"
    return {"event": event, "data": "\n".join(data_lines), "fields": fields}, None


def frame_matches(frame, matcher):
    """A frame matches a terminal matcher when every key the matcher declares
    (event and/or data) equals the frame's value."""
    if "event" in matcher and frame["event"] != matcher["event"]:
        return False
    if "data" in matcher and frame["data"] != matcher["data"]:
        return False
    return bool(matcher)


def run(journey, source=None):
    """Drive the stream and return a machine-readable result. source() is the
    stream seam; it defaults to the journey's fake frames so the runner is
    replayable with no live stream. passed is False on a framing error, a
    sequencing or terminal violation, a failed final grader, a source error, or
    an asserts-nothing journey."""
    result = {"stream": journey.get("name"), "passed": True, "frames": 0,
              "failures": [], "error": None}

    if not any(journey.get(k) for k in ("sequence_field", "expected_events", "terminal", "final")):
        result["passed"] = False
        result["error"] = "journey asserts nothing: declares no sequence_field, expected_events, terminal, or final"
        result["failures"].append(result["error"])
        return result

    try:
        raws = list(source() if source else journey.get("fake", []))
    except Exception as e:
        result["passed"] = False
        result["error"] = f"stream source error: {e}"
        result["failures"].append(result["error"])
        return result

    frames = []
    for i, raw in enumerate(raws):
        frame, err = parse_sse_frame(raw)
        if err:
            result["passed"] = False
            result["error"] = f"frame {i}: framing error: {err}"
            result["failures"].append(result["error"])
            return result
        frames.append(frame)
    result["frames"] = len(frames)

    terminal = journey.get("terminal")
    is_terminal = [bool(terminal) and frame_matches(f, terminal) for f in frames]
    if terminal:
        term_idx = [i for i, t in enumerate(is_terminal) if t]
        if not term_idx:
            result["passed"] = False
            result["failures"].append("stream did not terminate: no frame matched the terminal")
        elif term_idx[-1] != len(frames) - 1:
            result["passed"] = False
            trailing = len(frames) - 1 - term_idx[-1]
            result["failures"].append(
                f"frame arrived after the terminal (terminal at frame {term_idx[-1]}, {trailing} frame(s) followed)")

    seqf = journey.get("sequence_field")
    if seqf:
        expected = 0
        for i, f in enumerate(frames):
            if is_terminal[i]:
                continue
            d = _json_or_none(f["data"])
            if isinstance(d, dict) and seqf in d:
                if d[seqf] != expected:
                    result["passed"] = False
                    result["failures"].append(
                        f"sequence {seqf!r}: frame {i} expected index {expected}, got {d[seqf]!r}")
                    break
                expected += 1

    exp = journey.get("expected_events")
    if exp is not None:
        got = [f["event"] for f in frames]
        if len(exp) != len(got):
            result["passed"] = False
            result["failures"].append(f"expected {len(exp)} event(s), observed {len(got)} ({got})")
        for j in range(min(len(exp), len(got))):
            if exp[j] != got[j]:
                result["passed"] = False
                result["failures"].append(f"event {j}: expected {exp[j]!r}, observed {got[j]!r}")
                break

    graders = journey.get("final")
    if graders:
        af = journey.get("assemble_field")
        parts = []
        for i, f in enumerate(frames):
            if is_terminal[i]:
                continue
            if af:
                d = _json_or_none(f["data"])
                if isinstance(d, dict) and af in d:
                    parts.append(str(d[af]))
            else:
                parts.append(f["data"])
        assembled = "".join(parts)
        for fail in grade(assembled, graders):
            result["passed"] = False
            result["failures"].append(fail)

    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    result = run(journey)
    print(f"stream {result['stream']!r}: {result['frames']} frame(s)")
    if result["passed"]:
        print("stream PASSED: framing, sequencing, and terminal all hold")
        return 0
    for f in result["failures"]:
        print(f"FAIL - {f}")
    print("stream FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
