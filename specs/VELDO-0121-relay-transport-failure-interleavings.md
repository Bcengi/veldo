---
schema: veldo.spec/v1
id: VELDO-0121
title: Qualify relay behavior at every transport exchange failure boundary
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0108]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_relay.py"
  - "engine/.veldo/control_relay.py"
  - "scripts/fixtures/relay_exchange.py"
  - "scripts/suites/48_veldo_0108_relay.py"
  - "scripts/suites/*_veldo_0121_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0121-relay-transport-failure-interleavings.md"
  - "specs/index.md"
  - "proof/VELDO-0121/*"
behavior_bearing: true
observability:
  logs: >
    Record exchange phase, byte offset, injected OS outcome, observed return/exit, exact stdout and endpoint diagnostic.
  metrics: >
    Report expected/executed phase-outcome cells, completion latency and incomplete schedules.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish endpoint_error, endpoint_timeout, orderly_eof, request_too_large and response_too_large without inventing an authority decision.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Endpoint errors or timeouts at any transport operation yield exit 3, exactly zero stdout bytes and an endpoint-naming diagnostic, even after partial response receipt.
      Set: Connect, every request send, write-half shutdown and every response receive, crossed with every applicable error/timeout transition in a written exchange-state model; include endpoint close/reset before connect, during request, after request and between response chunks.
      Completeness: Generate legal phase/outcome schedules from the model and reconcile the model's operations with the production transport calls. Exhaust all byte offsets for representative 0..3-byte payloads and chunk boundaries at 65536 and 1 MiB; require each reachable model transition. Use deterministic fault injection around the real transport plus actual kernel close/reset controls, recording which outcomes the kernel delivered.
      Refutation: relay/transport-errors-have-zero-stdout is false on a success exit, any emitted response byte, missing diagnostic or unexecuted applicable schedule.
    falsified_by: >
      Flush already received response chunks to stdout before the next recv succeeds; relay/transport-errors-have-zero-stdout must turn red on a subsequent reset.
  - id: AC2
    text: >
      Claim: Orderly EOF carries exactly the bytes received, including empty bytes, while size violations refuse with exit 4 and zero stdout.
      Set: Clean EOF before any response byte and after each small-payload prefix, complete responses at limit-1/limit/limit+1, and requests at those same size boundaries with varied chunking.
      Completeness: Enumerate normal and over-limit terminal transitions from the same state model and compare raw bytes, exit and stderr. Include a zero-byte successful echo and non-UTF-8 bytes. An EOF-delimited relay cannot distinguish an intentionally short response from a cleanly closed truncated one, so it does not manufacture a protocol error.
      Refutation: relay/eof-and-size-decisions-match-model is false if clean EOF is misclassified, bytes change or an over-limit partial answer escapes.
    falsified_by: >
      Translate clean response EOF into EXIT_UNREACHABLE; relay/eof-and-size-decisions-match-model must turn red for the successful empty response.
  - id: AC3
    text: >
      Claim: A stalled exchange has a bounded total transport lifetime and leaves no relay or helper running.
      Set: All nonterminal model phases with a stalled endpoint, plus a trickle response that makes progress just inside each per-operation timeout; stdin is already supplied and stdout is drained by the fixture.
      Completeness: Use a monotonic overall connect-to-completion deadline of 30 seconds, not a fresh 30 seconds for each recv. Each schedule must terminate by deadline plus one second teardown tolerance with the endpoint refusal contract; accelerate clocks for exhaustive scheduling and include one real-time stalled/trickle qualification.
      Refutation: relay/exchange-deadline-is-total is false if progress resets the budget or any helper survives teardown.
    falsified_by: >
      Reset the overall deadline after every received chunk; relay/exchange-deadline-is-total must turn red under the trickle schedule.
  - id: AC4
    text: >
      Claim: Transport failure never triggers a second connection or automatic replay by the relay.
      Set: Every error schedule before request completion and after the endpoint has received the full request but before the response completes.
      Completeness: The fixture counts accepted connections and complete request identities independently of relay output; require at most one connection attempt and one forwarded request. A failure after possible commit remains uncertain to the caller, not proof that the command was unapplied.
      Refutation: relay/failure-does-not-replay is false if an error results in another connect or another complete request.
    falsified_by: >
      Reconnect and resend once after a response receive error; relay/failure-does-not-replay must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Track the relay's unmeasured failure interleavings as a generated state-transition qualification task.

## Context

proof/VELDO-0108/README.md:84-87 labels exhaustive transport failure coverage unproven. The current forward path connects, sends, half-closes and receives, with per-socket timeouts and EOF-delimited raw responses.

## Out of scope

Changing the opaque byte protocol to framed messages, recognizing application-level truncated responses, SSH authentication, downstream stdout failures and another process/listener census.

## Notes

The exchange fixture owns phase barriers and fault scheduling only. Native endpoint close/reset effects can vary by scheduling: assert the observed OS outcome's specified behavior instead of assuming a send must fail when buffered bytes could still be accepted. Exhaustiveness means all reachable transitions and declared byte-offset classes in the published model, not every possible network schedule. The total deadline is an intended new requirement, not a claim about today's per-operation timeout.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
