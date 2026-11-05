---
schema: veldo.spec/v1
id: VELDO-0249
title: An outside catalog server can verify that the owner approved this exact write, through a signed, single-use, short-lived approval token bound to the call and handed only to the run that makes it
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0065, VELDO-0066, VELDO-0068, VELDO-0144, VELDO-0158, VELDO-0162, VELDO-0181, VELDO-0241, VELDO-0243, VELDO-0244, VELDO-0251, VELDO-0252]
placement: [contracts, engine, distribution]
protected_paths: [".veldo/control_store.py", "engine/.veldo/control_store.py", ".veldo/control_request_settlement.py", "engine/.veldo/control_request_settlement.py", ".veldo/control_channel_attribution.py", "engine/.veldo/control_channel_attribution.py", ".veldo/control_signer_answers.py", "engine/.veldo/control_signer_answers.py", ".veldo/control_keys.py", "engine/.veldo/control_keys.py", ".veldo/authority_contract.py", "engine/.veldo/authority_contract.py", ".veldo/settlements/*"]
footprint:
  - ".veldo/control_tool_approval.py"
  - "engine/.veldo/control_tool_approval.py"
  - ".veldo/tool_approval_verifier.py"
  - "engine/.veldo/tool_approval_verifier.py"
  - ".veldo/control_signer.py"
  - "engine/.veldo/control_signer.py"
  - ".veldo/control_mcp_catalog.py"
  - "engine/.veldo/control_mcp_catalog.py"
  - ".veldo/control_credential_delivery.py"
  - "engine/.veldo/control_credential_delivery.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_engine_claude.py"
  - "engine/.veldo/control_engine_claude.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/gate_check_approval.py"
  - "engine/.veldo/gate_check_approval.py"
  - ".veldo/egress_declaration.py"
  - "engine/.veldo/egress_declaration.py"
  - "scripts/suites/*_veldo_0249_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0249-a-catalog-server-verifies-the-owner-approved-this-exact-write.md"
  - "specs/index.md"
  - "proof/VELDO-0249/**"
behavior_bearing: true
observability:
  logs: >
    Veldo records, in the journal, each tool approval request (catalog server id and revision, tool,
    arguments digest, subject digest, the presentation it was shown in), each grant (the settlement it
    came from, the approver principal, the addressed dispatch) and each token issued (token id, key id,
    issued_at, expires_at, dispatch), each with the target kind (tool or HTTP request). The verifier writes
    one line per decision to the log of the gate's check service (VELDO-0252): token id, target, digest,
    verdict and refusal name. No token body, signature or argument value
    is logged anywhere, and the receiver adds each delivered token to the run's redaction set.
  metrics: >
    Count approval requests raised, settled accepted, settled declined, grants issued as tokens, grants
    expired unused, and verifier verdicts by refusal name, per catalog server and tool.
  traces: >
    A token id joins the server's verdict line to its grant, the grant to its settlement receipt
    (VELDO-0068) and the owner's attributed answer (VELDO-0066), and the settlement to the presentation the
    owner saw (VELDO-0065) and the run that raised it.
  error_taxonomy: >
    Veldo side: a call with no settled acceptance is missing_authority:owner_approval; a settled grant
    already issued is stale_version:tool_approval; a grant whose server revision or tool is not an approval
    tool of the dispatch's selected catalog revision is unsupported_configuration:approval_tool; a
    tool-approval signing key that is not active is missing_authority:approval_key. Verifier side, each a
    named refusal the server returns as the tool's error: approval_missing, approval_malformed,
    approval_signature, approval_key_inactive, approval_server, approval_tool, approval_arguments,
    approval_dispatch, approval_expired, approval_not_yet_valid, approval_replayed, approval_ledger
    (the replay ledger cannot be written, so the call is refused, never let through).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: only the owner's settled acceptance of the exact call yields a grant, and a grant becomes at most
      one signed token. Set and completeness: a run raises a tool approval request through the conversation
      decision flow (VELDO-0181) or a workflow owner_approval node naming a catalog tool step (VELDO-0241
      AC2, VELDO-0243, VELDO-0244); the request names the service and its declaration revision (VELDO-0251
      AC4), a target, the subject digest the server's prepare returned, and the addressed dispatch. A target
      is either a tool (the tool name and the call's arguments in canonical form, sorted-key compact JSON,
      UTF-8, with their sha256 digest) or an HTTP request (the method, the path after the route prefix, the
      sorted query, the content type and the body digest: canonical JSON for application/json, the exact
      bytes otherwise); a float anywhere in canonical JSON arguments or body is refused as
      invalid_input:float_argument, so every language computes the same bytes. The presentation
      (VELDO-0065) shows the service, the target (a tool call with its arguments, or the HTTP request as
      recorded) and the prepare's plan as the engine stream recorded that result, not as the turn restates
      it; a plan whose digest differs from the subject
      digest is refused as invalid_input:unobserved_prepare. A settlement accepted by the enrolled owner
      (VELDO-0066, VELDO-0068) records one grant keyed by the settlement, so a second answer, a declined,
      stale or superseded presentation, an automation sender and a turn's own output yield none. At the
      launch of the addressed dispatch the signer (control_signer custody, never the run) issues exactly one
      token from the grant: envelope schema veldo.tool_approval/v2 with token_id, key_id, service,
      declaration revision, target, subject_digest, approver principal, settlement reference, dispatch,
      issued_at and expires_at (at most 15 minutes after issue; the owner's configuration may only lower
      it), signed with ssh-keygen -Y sign in the namespace veldo-tool-approval by a dedicated tool-approval
      signing key that lives under the existing control_keys lifecycle (register, rotate, retire, revoke) and
      appears in the factory's published verification projection. A grant left unissued or expired unused
      is never re-minted: the owner is asked again. Row: an approved POST to a route yields one grant and
      one token whose target is that exact request.
    falsified_by: >
      Key the grant by the request instead of the settlement and send two accepted answers: two grants and
      two tokens must appear and the one-grant row fails; or build the presentation from the turn's restated
      plan instead of the recorded tool result, and the altered-plan row settles and fails; or record an
      HTTP target without its query or body digest, and the approved-POST row finds a token whose target is
      not that exact request and fails.
  - id: AC2
    text: >
      Claim: a token reaches only the approval service of VELDO-0252, keyed by the dispatch it was addressed
      to, and never a run, a server or the model's context. Set and completeness: at the addressed
      dispatch's launch the signer issues the token to the approval service of VELDO-0252, keyed by
      dispatch, and to nothing else. Veldo no longer writes VELDO_APPROVAL_TOKENS, VELDO_APPROVAL_KEYS or
      VELDO_MCP_SERVER into any run's configuration. The catalog's approval_tools field is retired for
      services behind the gate: which calls need a token is decided by the mechanical classification of
      VELDO-0251 AC3 (every write, anything unclassified counted as one). Rows for both engines (Claude
      Code and Codex): the run, its servers and every other dispatch receive no token; the service holds
      exactly the addressed dispatch's tokens; the prompt, the transcript and the logs contain no token
      body.
    falsified_by: >
      Keep writing VELDO_APPROVAL_TOKENS into the run's configuration, or hand the service every pending
      token of the conversation instead of the addressed dispatch's: the no-token-in-the-run row or the
      exactly-the-addressed-dispatch row must find a token and fail.
  - id: AC3
    text: >
      Claim: the gate's check service refuses any write that does not carry a valid, unused token bound to
      that exact request, before anything goes upstream, with no shared secret and no bypass. Set and
      completeness: tool_approval_verifier.py is one self-contained Python file, standard library only plus
      the OpenSSH ssh-keygen binary, shipped as a runtime asset (init_scaffold, byte-identical in .veldo and
      engine/.veldo). The gate's check service (VELDO-0252) calls it against the request the gate received,
      before anything goes upstream, and it refuses by name unless one token: verifies with ssh-keygen -Y
      verify in the veldo-tool-approval namespace against a key that is active now in the published
      projection; names this service, this target and this dispatch; has a digest equal to the digest the
      check recomputes from the request the gate actually received; is inside issued_at and expires_at with
      at most 60 seconds of clock skew; and is recorded as consumed in the replay ledger in the service's
      own state (SQLite in its 0700 state directory, token id unique, committed before the allow, so the
      effect runs only after the consumption is durable). The verifier holds no secret, has no flag,
      environment value or argument that skips a check, and a call it cannot decide is refused. A read
      takes no token. For a two-phase server the subject check stays at the server in a lighter form: the
      server does not verify a signature; it compares the subject digest the gate passes on an allowed
      write (a request header set by the check, which the caller cannot set because the relay and gate
      strip it) with its stored pending action, and refuses a mismatch, so a draft edited after approval is
      refused. A server may still run the full verifier as defence in depth, but is not required to. Rows:
      no token, a forged signature, a token signed by a revoked or retired key, a token for another
      service, tool or dispatch, another method, path or query, arguments or a body changed by one byte, an
      expired token, a token reused after one success, two concurrent calls with one token (exactly one
      passes), and a caller-set subject digest header that reaches the server.
    falsified_by: >
      Make the check accept a token whose digest it copies from the token instead of recomputing from the
      received request, or commit the replay ledger after the allow: the changed-body row or the
      concurrent-replay row must pass a call and fail. Or let the caller's own subject digest header
      through to the server: the caller-set header row passes an edited draft and fails.
  - id: AC4
    text: >
      Claim: the gate is proven to enforce the token on every write of a service before that service is
      trusted with writes. Set and completeness: proof/VELDO-0249 ships a conformance harness that drives
      every write route and every write tool of a service declaration through the gate, with test keys
      published through the real control_keys projection, with the AC3 rows; a fixture two-phase server
      behind the gate passes every row. A service's writes are allowed only after its declaration revision
      has a passing harness record. The harness reports by name a declaration that labels a write as a read
      without an owner-signed exception, and a gate configuration whose check is not attached to one write
      route. Until a declaration passes, the gate refuses that service's writes
      (missing_authority:owner_approval), so the connectors ship their reads first, exactly as the
      connectors plan already requires.
    falsified_by: >
      Run the harness against the declaration that labels a write as a read without an owner-signed
      exception, or the gate configuration whose check is not attached to one write route: if the harness
      reports no failure by name, or the gate allows that revision's writes, the row fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change: no grant becomes a token, no run receives one, and every connector's approval tool is
  refused by its verifier (approval_missing), so connectors fall back to read tools only. Recorded requests,
  grants, issued token records and the tool-approval signing key stay in the store; the key can be retired
  through the existing lifecycle. No automatic rollback, retry or recovery is authorized.
---

## Intent

A connector that can create an ad, submit payment dispute evidence, generate a paid image or video, save a mail
draft or publish a post must refuse to do it unless the owner approved that exact action. Today Veldo gives
an outside server no way to check that, so every connector would ship read-only. This spec gives the server
a proof it can check on its own: a token the factory signs only after the owner's settled approval, bound to
the server, the tool, the exact arguments, the subject, the approver and an expiry, used once.

## Context

- The owner's connectors plan (kept in the owner's installation, shared design point 3) makes
  every owner-word write two-phase: prepare computes the exact change and returns a plan and a digest with no
  outside effect; commit performs exactly that change after the server has verified the owner's approval. It
  names this missing piece P-A and requires that until P-A exists every commit tool refuses by name
  (missing_authority:owner_approval). Nothing falls back to trusting the turn: under VELDO-0181 AC2 nothing a
  turn produces carries authority, so a code the model types as approved proves nothing.
- Approvals today: requests are presented with versioned receipts (VELDO-0065), answers are attributed to
  the platform-derived sender (VELDO-0066), and one request version settles once, atomically, with the
  owner's ruling (VELDO-0068). The signer (control_signer) signs with ssh-keygen in fixed namespaces, keys
  follow the control_keys lifecycle, and control_keys publishes an allowed_signers projection that keeps
  historical keys for verification only. This spec reuses all of that: a new namespace and a dedicated key,
  never the owner's own answer key and never a shared secret.
- Delivery: a run's catalog servers (VELDO-0144) are written by the receiver into the run's generated
  configuration with their credentials just before spawn (VELDO-0158), selected through the role's
  capability configuration (VELDO-0162). Tokens travel the same path, so the model never handles them.
- The workflow approval step (VELDO-0241 AC2, VELDO-0243, VELDO-0244, drafted on the veldo-workflow-process
  branch) settles through VELDO-0068 bound to the exact subject; when the step it guards is a catalog tool
  call, its settlement yields a grant through this spec instead of a second mechanism.

## Design

1. Request. The run calls prepare, the engine stream records the result, and the run raises a tool approval
   request naming server, revision, tool, canonical arguments, their digest, the subject digest and the
   dispatch that will commit. The owner sees the recorded plan, not the turn's paraphrase.
2. Grant. An accepted settlement by the enrolled owner records one grant keyed by the settlement, as a
   separate journaled command that reads the terminal settlement; settlement code is unchanged.
3. Token. At the addressed dispatch's launch the signer turns the grant into one token, signed with the
   tool-approval key in the veldo-tool-approval namespace, valid at most 15 minutes.
4. Delivery. The receiver writes the token, the server id, the dispatch id and the published keys path into
   that server's generated configuration only.
5. Verification. The server calls require(tool, arguments) from the shipped verifier, which checks
   signature, key status, binding, expiry and replay, consumes the token durably, and only then lets the
   effect run. A call whose outcome is unknown is not retried on the same token.

## Out of scope

Writing the connectors themselves (the plan's tickets). The spend gate inside a server (plan point 4), which
stays a separate, necessary but not sufficient check. Approval by anyone other than the owner.

## What the reviewer judges

- Normal use: the run prepares a paused ad campaign, the owner sees the plan in Telegram and
  approves, the next run of that conversation commits, the server verifies the token and creates exactly
  that campaign, and a second commit with the same token is refused as approval_replayed.
- Threat model: a model that types "approved"; a token copied to another run or server; arguments changed
  after approval; a draft edited after approval; a replay, including two concurrent calls; a forged or
  revoked-key signature; a stale or superseded presentation; an automation sender; a server that skips the
  verifier; a token or argument value that reaches a log.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); clock attacks on
  the server's host beyond the 60 second skew.

## Notes

ssh-keygen -Y is already how Veldo signs and verifies every receipt, so the verifier needs no third-party
crypto library and connectors in any language can verify the same way. Floats are refused in approved
arguments because their canonical text differs between languages; money and counts travel as integers or
strings.

## History

2026-11-04: new draft. Owner Telegram 39063 and 39067 (every switch decision for the connectors yes; paid
image and video as spend-gated exceptions, each use approved). The connectors plan
(kept in the owner's installation) names this prerequisite P-A and holds every connector's
commit tools refused until it lands. Standalone.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended as approved by the owner, Telegram 39144 ("Yes", to 39143: approvals go to the gate's check instead of to each connector). Applied as written in proof/VELDO-0251/amend-0249.md (VELDO-0251 branch): AC1 target v2, AC2 replaced by delivery to the approval service, AC3 moved into the gate's check with the subject comparison kept at two-phase servers, AC4 retargeted to the gate, the remote server out of scope item removed, observability decision line moved, depends_on adds VELDO-0251 and VELDO-0252. Status stays ready.
