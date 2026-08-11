---
schema: veldo.spec/v1
id: WARP-0312
title: Streaming/SSE runner (reference) - B12 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B12
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A streaming runner ships at
      engine/scripts/runners/streaming/veldo_streaming_runner.py. It
      reads a journey (a name, an optional sequence_field, an optional ordered
      expected_events list, a required terminal matcher, optional final graders
      with an assemble_field, and a fake list of raw frame blocks) and drives a
      stream through a SOURCE seam - a callable returning an iterable of raw
      frame strings - so the control logic runs against a fake in-memory stream
      with no live server. It parses each raw frame as a server-sent-events
      block (field: value lines, a required data field, comment lines ignored),
      asserts framing, sequencing, and the terminal, and exits 0 when every
      assertion holds and exits 1 with the first failing assertion named. An
      adopting repo passes source=its own callable (an SSE or websocket reader)
      unchanged.
  - id: AC2
    text: Chunk sequencing is asserted honestly. When sequence_field is set, the
      JSON data of each frame that carries that field must yield values that are
      contiguous and increasing from 0 in arrival order, so a dropped chunk (a
      gap), a duplicated chunk, or a reordered chunk each fails naming the
      expected and observed index. When expected_events is set, the ordered list
      of frame event types must match one to one (a wrong type, a wrong order, a
      missing frame, or an extra frame fails naming the position). A stream that
      passes a happy-path "it produced output" check but dropped a chunk in the
      middle is exactly the defect this catches.
  - id: AC3
    text: Framing and the terminal are enforced, and a malformed stream fails. A
      frame whose line is not a valid SSE field (no colon separator, or an
      unknown field) or that carries no data field is a framing error naming the
      frame index and the offending content. A terminal frame (matching the
      journey terminal by event and/or data) is required and must be the LAST
      frame - a stream with no terminal fails with a did-not-terminate error, and
      a frame arriving after the terminal fails. When final graders and an
      assemble_field are set, the data values of the non-terminal frames are
      concatenated in order and graded (contains, not_contains, equals, regex).
      A journey that declares none of sequence_field, expected_events, terminal,
      or final asserts nothing and is a journey error.
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py with a fake
      in-memory source and NO live stream, mirroring the other reference runners.
      A happy stream passes; a sequence gap, a reordered chunk, a malformed
      frame, a missing terminal, a frame after the terminal, and a failed final
      grader each fail named; an asserts-nothing journey is a journey error. Two
      shipped fixtures (a well-formed stream and a malformed stream) are driven
      end to end (pass -> exit 0, malformed -> exit 1 with the failure named).
      All prior selftest cases keep passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference wired per repo to its own stream source; the veldo home
      repo ships no streaming surface of its own), never mechanical. The
      docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit]
rollback: git revert; B12 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is
  touched, so reverting removes the reference artifact and its unit block with no
  effect on any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B12 is the streaming surface (server-sent events and websocket-style
frame streams). The outcome that should become true is that a repository can
drive a stream its service produces (token-by-token model output, a live event
feed, a progress channel) and get proof that the stream is well-framed, that its
chunks arrive in order with none dropped, duplicated, or reordered, and that it
terminates properly. A happy-path check that the stream produced some output
misses the chunk that was dropped in the middle and the stream that never sent
its terminal event. This runner asserts the sequencing, the framing, and the
final, so those defects fail loud.

## Context

B12 of PLAN-0003, feature F4 (contract and protocol surfaces), pulled against
plan revision 2, with no dependency. It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR, a
wrapper, a README, and a unit block that gate-tests the control logic with a
fake in-memory source and no live stream. The frame format is server-sent events
(the dominant text streaming format, and the shape a websocket text feed maps
onto): field-and-value lines separated into frames, with an event type and a
data field. The source is a seam so the same runner drives a real SSE response
body or a websocket recv loop in an adopting repo.

## Out of scope

Binary websocket framing and the websocket wire protocol handshake (the runner
asserts an already-decoded text frame stream, which is what an adopting repo's
recv loop yields; it does not implement the RFC 6455 framing layer). Backpressure
and flow control. Reconnection and last-event-id resumption semantics. Driving a
live stream in the home gate, because the veldo repo ships no streaming surface;
the honest evidence is the fake-source control-logic test.

## Notes

Why reference (not mechanical): the veldo home repo has no streaming surface of
its own, so the honest evidence is the fake-source unit tests, not a live-stream
run. required_evidence is [unit]. The source is a seam so an adopting repo swaps
in its real reader. capabilities.yaml states status: reference, never
mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest
and driving the fixtures: (1) a sequence gap, a duplicate, and a reorder each
fail naming the expected and observed index; (2) a malformed frame (a bad line,
an unknown field, or a data-less frame) fails naming the frame index; (3) a
missing terminal and a frame after the terminal each fail; (4) the assembled
final content is graded only over the non-terminal frames; (5) an asserts-nothing
journey is a journey error, not a vacuous pass.
