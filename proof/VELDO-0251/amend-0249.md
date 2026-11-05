# Proposed amendment to VELDO-0249, for the owner's approval

Status: proposal. VELDO-0249 is approved (Telegram 39096) and is not edited by this branch. If the owner
approves, the change below is made to VELDO-0249 as its own commit, with a History line citing that approval.

## Why

VELDO-0249 has each connector verify the owner's approval itself: the token is delivered into the run's
configuration for that server, and the server calls the shipped verifier. Under VELDO-0251 every outside
call goes through one gate, and VELDO-0252 checks every write there. Verification therefore moves from each
connector into the gate's check. The token never enters a run at all, one verifier covers every service
(including code that calls a vendor API directly, which 0249 could not cover), and a connector that forgets
to call the verifier can no longer let a write through.

## What stays exactly as approved

- The request, the presentation from the recorded tool result, the grant keyed by the settlement, one token
  per grant, never re-minted (AC1, apart from the target change below).
- The tool-approval signing key, its control_keys lifecycle, the veldo-tool-approval namespace, ssh-keygen
  signing and verification, the 15 minute ceiling and the 60 second skew.
- tool_approval_verifier.py as the one implementation, standard library plus ssh-keygen, with no flag or
  value that skips a check.
- Refusal names, the journal records and the rollback.

## Changes, criterion by criterion

**AC1 (grant and token).** The request and the token name a target instead of only a tool. Envelope
veldo.tool_approval/v1 becomes v2: `server` and `server revision` become `service` and its declaration
revision (VELDO-0251 AC4), and `tool` and `args_digest` become a `target` that is either a tool (tool name
and the same canonical arguments digest) or an HTTP request (method, path after the route prefix, sorted
query, content type and the body digest: canonical JSON for application/json with floats refused, the exact
bytes otherwise). The presentation shows the HTTP request as recorded, the same way it shows a tool call.
Everything else in AC1 is unchanged. New row: an approved POST to a route yields one grant and one token
whose target is that exact request.

**AC2 (delivery).** Replaced. The signer issues the token at the addressed dispatch's launch to the approval
service of VELDO-0252, keyed by dispatch, and to nothing else. Veldo no longer writes VELDO_APPROVAL_TOKENS,
VELDO_APPROVAL_KEYS or VELDO_MCP_SERVER into any run's configuration. The catalog's `approval_tools` field
is retired for services behind the gate: which calls need a token is decided by the mechanical
classification of VELDO-0251 AC3 (every write, anything unclassified counted as one). New rows, for both
engines: the run, its servers and every other dispatch receive no token; the service holds exactly the
addressed dispatch's tokens; the prompt, transcript and logs contain no token body. The old rows "the
addressed run's server receives its token" and "another server of the same run receives nothing" are
removed, since no server receives one.

**AC3 (verification).** Moved. The checks are the same, but the gate's check service makes them against the
request the gate received, before anything goes upstream; it recomputes the digest from that request, and
the replay ledger lives in the service's state, committed before the allow. Added rows: another method,
path or query, and a body changed by one byte. The two-phase subject check stays at the server, in a
lighter form: the server no longer verifies a signature; it compares the subject digest the gate passes on
an allowed write (a request header set by the check, which the caller cannot set because the relay and
gate strip it) with its stored pending action, and refuses a mismatch as before. A server may still run the
full verifier as defence in depth, but it is not required to.

**AC4 (conformance).** Retargeted from each connector to the gate. The harness drives every write route and
every write tool of a service declaration through the gate with the AC3 rows. A service's writes are
allowed only after its declaration revision has a passing harness record. The fixture "a server that omits
the verifier on one approval tool" is replaced by "a declaration that labels a write as a read without an
owner-signed exception" and "a gate configuration whose check is not attached to one write route", each
reported by name. Until a declaration passes, the gate refuses that service's writes, which keeps the
existing rule that connectors ship their reads first.

**Out of scope section.** "Remote (HTTP) catalog servers on another host" is removed from out of scope: a
remote vendor server is a gate target like any other, so the keys never need distributing.

**Observability.** The verifier's decision line moves from each server's log to the check service's log
(VELDO-0252). The journal records of requests, grants and issued tokens are unchanged, plus the target kind.

**depends_on.** Add VELDO-0251 and VELDO-0252.

## What the owner approves

One yes approves: the v2 target in AC1, AC2 replaced by delivery to the approval service, AC3 moved into
the gate's check with the subject comparison kept at two-phase servers, AC4 retargeted to the gate, and the
out of scope and depends_on edits above.
