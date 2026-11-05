---
schema: veldo.spec/v1
id: VELDO-0249
title: The outside gate's check can verify that the owner approved this exact write, through a signed, single-use, short-lived approval token bound to the exact request and handed only to the check for the dispatch that makes it
status: ready
risk: critical
owner: owner
human_approval: required
lane: standalone
depends_on: [VELDO-0065, VELDO-0066, VELDO-0068, VELDO-0144, VELDO-0158, VELDO-0162, VELDO-0181, VELDO-0241]
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
    arguments digest, subject digest, the presentation it was shown in), each grant (the settlement it came
    from, the approver principal, the addressed dispatch) and each token issued (token id, key id,
    issued_at, expires_at, dispatch), each with the target kind (tool or HTTP request). The verifier writes
    one line per decision to the log of the outside gate's check service (VELDO-0252): token id, target,
    digest, verdict and refusal name. No token body, signature or argument value is logged anywhere, and the
    approval service adds each token it receives to its redaction set.
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
      Claim: only the owner's settled acceptance of the exact call yields a grant, and a grant becomes at
      most one signed token. Set and completeness: a run raises a tool approval request through the
      conversation decision flow (VELDO-0181), and a workflow owner_approval node naming a step that makes
      the write (VELDO-0241 AC2, VELDO-0243, VELDO-0244) and an approved schedule raise it the same way; the
      request names the service and its declaration revision (VELDO-0251 AC4), a target, for an HTTP request
      the request id under which the approval service of VELDO-0252 stored the exact request the run
      submitted first, for a two-phase server the subject digest its prepare returned, and the addressed
      dispatch. A target is either a tool (the tool name and the call's arguments in canonical form,
      sorted-key compact JSON, UTF-8, with their sha256 digest) or an HTTP request (the method, the path
      after the route prefix, the sorted query, the content type and the canonical body digest: sorted-key
      compact JSON for application/json, form fields sorted by name and then value, multipart as the ordered
      list of part headers with each part's sha256 and the boundary ignored, the exact bytes otherwise); a
      float anywhere in canonical JSON arguments or body is refused as invalid_input:float_argument, so
      every language computes the same bytes. A prepare that calls the vendor is itself a write under
      VELDO-0251 AC3 unless the installation declares it read. The presentation (VELDO-0065) shows the
      service and the target as observed, not as the turn restates it: an HTTP request decoded from the
      stored request (fields as fields, a file as its name, size, type and a preview), or a tool call with
      its arguments and, for a two-phase server, the prepare's plan as the engine stream recorded that
      result; a plan or request whose digest differs from the subject digest or the stored request's digest
      is refused as invalid_input:unobserved_prepare. A settlement accepted by the enrolled owner
      (VELDO-0066, VELDO-0068) records one grant keyed by the settlement, so a second answer, a declined,
      stale or superseded presentation, an automation sender and a turn's own output yield none. At the
      launch of the addressed dispatch the signer (control_signer custody, never the run) issues exactly one
      token from the grant: envelope schema veldo.tool_approval/v2 with token_id, key_id, service,
      declaration revision, target, subject_digest, approver principal, settlement reference, dispatch,
      issued_at and expires_at (at most 15 minutes after issue; the owner's configuration may only lower
      it), signed with ssh-keygen -Y sign in the namespace veldo-tool-approval by a dedicated tool-approval
      signing key that lives under the existing control_keys lifecycle (register, rotate, retire, revoke)
      and appears in the factory's published verification projection. A grant left unissued or expired
      unused is never re-minted: the owner is asked again. Rows: an approved POST to a route yields one
      grant and one token whose target is that exact request; an approved multipart upload's target is the
      same when the upload is sent again with another boundary.
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
      services behind the outside gate: which calls need a token is decided by the mechanical classification
      of VELDO-0251 AC3 (every write, anything unclassified counted as one). Rows for every engine the
      engines record names (Claude Code and Codex among them): the run, its servers and every other dispatch
      receive no token; the service holds exactly the addressed dispatch's tokens; the prompt, the
      transcript and the logs contain no token body.
    falsified_by: >
      Keep writing VELDO_APPROVAL_TOKENS into the run's configuration, or hand the service every pending
      token of the conversation instead of the addressed dispatch's: the no-token-in-the-run row or the
      exactly-the-addressed-dispatch row must find a token and fail.
  - id: AC3
    text: >
      Claim: the outside gate's check service refuses any write that does not carry a valid, unused token
      bound to that exact request, before anything goes upstream, with no shared secret and no bypass. Set
      and completeness: tool_approval_verifier.py is one self-contained Python file, standard library only
      plus the OpenSSH ssh-keygen binary, shipped as a runtime asset (init_scaffold, byte-identical in
      .veldo and engine/.veldo). The outside gate's check service (VELDO-0252) calls it against the request
      the outside gate received, before anything goes upstream, and it refuses by name unless one token:
      verifies with ssh-keygen -Y verify in the veldo-tool-approval namespace against a key that is active
      now in the published projection; names this service, this target and this dispatch; has a digest equal
      to the canonical digest the check recomputes from the whole request the outside gate actually received
      (a body over the service's declared limit is refused, never checked in part); is inside issued_at and
      expires_at with at most 60 seconds of clock skew; and is recorded as consumed in the replay ledger in
      the service's own state (SQLite in its 0700 state directory, token id unique, committed before the
      allow, so the effect runs only after the consumption is durable). The verifier holds no secret, has no
      flag, environment value or argument that skips a check, and a call it cannot decide is refused. A read
      takes no token. For a two-phase server the subject check stays at the server in a lighter form: the
      server does not verify a signature; it compares the subject digest the outside gate passes on an
      allowed write (a request header set by the check, which the caller cannot set because the outside
      gate strips it) with its stored pending action, and refuses a mismatch, so a draft edited after
      approval is refused. A server may still run the full verifier as defence in depth, but is not required
      to. Rows: no token, a forged signature, a token signed by a revoked or retired key, a token for
      another service, tool or dispatch, another method, path or query, arguments or a body changed by one
      byte, an expired token, a token reused after one success, two concurrent calls with one token (exactly
      one passes), and a caller-set subject digest header that reaches the server.
    falsified_by: >
      Make the check accept a token whose digest it copies from the token instead of recomputing from the
      received request, or commit the replay ledger after the allow: the changed-body row or the
      concurrent-replay row must pass a call and fail. Or let the caller's own subject digest header
      through to the server: the caller-set header row passes an edited draft and fails.
  - id: AC4
    text: >
      Claim: the outside gate is proven to enforce the token on every write of a service before that service
      is trusted with writes. Set and completeness: proof/VELDO-0249 ships a conformance harness that drives
      every write route and every write tool of a service declaration through the outside gate, with test
      keys published through the real control_keys projection, with the AC3 rows; a fixture two-phase server
      behind the outside gate passes every row. A service's writes are allowed only after its declaration
      revision has a passing harness record. The harness reports by name a declaration that labels a write
      as a read without a read override the owner approved (VELDO-0251 AC3, VELDO-0253 AC2), and a gate
      configuration whose check is not attached to one write route. Until a declaration passes, the outside
      gate refuses that service's writes (missing_authority:owner_approval), so a service ships its reads
      first.
    falsified_by: >
      Run the harness against the declaration that labels a write as a read without an approved read
      override, or the outside gate configuration whose check is not attached to one write route: if the
      harness reports no failure by name, or the outside gate allows that revision's writes, the row fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change: no grant becomes a token and the approval service receives none, so the outside gate's
  check refuses every write (approval_missing) and services fall back to reads only. Recorded requests,
  grants, issued token records and the tool-approval signing key stay in the store; the key can be retired
  through the existing lifecycle. No automatic rollback, retry or recovery is authorized.
---

## Intent

A service that can create an ad, submit payment dispute evidence, generate a paid image or video, save a
mail draft or publish a post must refuse to do it unless the owner approved that exact action. Today Veldo
has no way to check that, so every service would ship read-only. This spec gives the outside gate's check
(VELDO-0251, VELDO-0252) a proof it can verify on its own: a token the factory signs only after the
owner's settled approval, bound to the service, the exact request or tool call, the subject, the approver
and an expiry, used once.

## Context

- Some services are two-phase: prepare computes the exact change and returns a plan and a digest, and commit
  performs exactly that change. Every other write is approved as the exact request the run submitted first
  to the approval service. Until this spec lands every write is refused by name
  (missing_authority:owner_approval). Nothing falls back to trusting the turn: under VELDO-0181 AC2 nothing
  a turn produces carries authority, so a code the model types as approved proves nothing.
- Approvals today: requests are presented with versioned receipts (VELDO-0065), answers are attributed to
  the platform-derived sender (VELDO-0066), and one request version settles once, atomically, with the
  owner's ruling (VELDO-0068). The signer (control_signer) signs with ssh-keygen in fixed namespaces, keys
  follow the control_keys lifecycle, and control_keys publishes an allowed_signers projection that keeps
  historical keys for verification only. This spec reuses all of that: a new namespace and a dedicated key,
  never the owner's own answer key and never a shared secret.
- Delivery: every outside call goes through the outside gate (VELDO-0251), whose check service
  (VELDO-0252) holds the approval tokens, keyed by dispatch. No token, server key or credential enters a
  run, so the model never handles one. This spec, VELDO-0251 and VELDO-0252 are built and landed as one
  unit; depends_on runs one way (VELDO-0251 and VELDO-0252 depend on this spec), so the graph has no
  cycle.
- The workflow approval step (VELDO-0241 AC2, VELDO-0243, VELDO-0244, drafted on the veldo-workflow-process
  branch) settles through VELDO-0068 bound to the exact subject; when the step it guards makes an outside
  write, its settlement yields a grant through this spec instead of a second mechanism, and an approved
  schedule does the same.

## Design

1. Request. For an HTTP write the run first submits the exact request to the approval service of
   VELDO-0252, which stores it with no outside effect and returns its id; for a two-phase tool the run
   calls prepare and the engine stream records the result. The run raises a tool approval request naming
   the service, its declaration revision, the target, its canonical digest, the stored request id or the
   subject digest, and the dispatch that will send it. The owner sees the stored request decoded, or the
   recorded plan, never the turn's paraphrase.
2. Grant. An accepted settlement by the enrolled owner records one grant keyed by the settlement, as a
   separate journaled command that reads the terminal settlement; settlement code is unchanged.
3. Token. At the addressed dispatch's launch the signer turns the grant into one token, signed with the
   tool-approval key in the veldo-tool-approval namespace, valid at most 15 minutes.
4. Delivery. The signer hands the token to the approval service of VELDO-0252, keyed by the dispatch, and
   to nothing else; no token reaches a run or a server.
5. Verification. When the run sends the request, the outside gate's check recomputes the canonical digest
   from the whole request it received and runs the shipped verifier, which checks signature, key status,
   binding, expiry and replay, consumes the token durably, and only then allows the call upstream. A
   two-phase server compares the subject digest the check passes with its stored pending action. A call
   whose outcome is unknown is not retried on the same token.

## Out of scope

Declaring the services themselves (installation configuration). A spend check, which stays a separate,
necessary but not sufficient check. Approval by anyone other than the owner.

## What the reviewer judges

- Normal use: the run submits the request that creates a paused ad campaign, the owner sees it decoded in
  the channel and approves, the next run of that conversation sends that same request, the outside gate's
  check verifies the token and the vendor creates exactly that campaign, and a second send with the same
  token is refused as approval_replayed.
- Threat model: a model that types "approved"; a token copied to another run or server; arguments changed
  after approval; a draft edited after approval; a replay, including two concurrent calls; a forged or
  revoked-key signature; a stale or superseded presentation; an automation sender; a write route the check
  is not attached to; a token or argument value that reaches a log.
- Out of review scope (filed, not blocking): unlikely edge cases (an owner decision); clock attacks on
  the host beyond the 60 second skew.

## Notes

ssh-keygen -Y is already how Veldo signs and verifies every receipt, so the verifier needs no third-party
crypto library and a server in any language can verify the same way as defence in depth. Floats are refused
in approved arguments because their canonical text differs between languages; money and counts travel as
integers or strings.

## History

2026-11-04: new draft. Owner Telegram 39063 and 39067 (every switch decision for the connectors yes; paid
image and video as spend-gated exceptions, each use approved). The connectors plan
(kept in the owner's installation) names this prerequisite P-A and holds every connector's
commit tools refused until it lands. Standalone.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended as approved by the owner, Telegram 39144 ("Yes", to 39143: approvals go to the gate's check instead of to each connector). Applied as written in proof/VELDO-0251/amend-0249.md (VELDO-0251 branch): AC1 target v2, AC2 replaced by delivery to the approval service, AC3 moved into the gate's check with the subject comparison kept at two-phase servers, AC4 retargeted to the gate, the remote server out of scope item removed, observability decision line moved, depends_on adds VELDO-0251 and VELDO-0252. Status stays ready.

2026-11-04: amended per the plan consistency review (research/veldo-plan-consistency-review-2026-11-04.md) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md), both in the owner's installation repository, on the owner's request Telegram 39145. AC1: an HTTP write is approved as the exact request the run submitted first to the approval service of VELDO-0252 and shown decoded; canonical digests for form and multipart bodies; a workflow approval node and an approved schedule use the same mechanism; a prepare that calls the vendor is a write unless declared read (R4, R12, C1, C2, A24, E1). AC3: the whole body is read or refused under the per-service limit (R4). AC4: a read label needs an approved read override (D3). depends_on drops VELDO-0251 and VELDO-0252, which depend on this spec, so the graph has no cycle (D4). The title, Intent, Context, Design, rollback and observability now describe delivery to the outside gate's check instead of per-server delivery, matching the amended criteria. agentgateway is named the outside gate (E6). The owner's connectors plan and its point numbers leave the spec, and the owner field is a role id (B1). Status stays ready; the owner approves the amendments in one message.

2026-11-05: the lead removed VELDO-0243 and VELDO-0244 from depends_on: they use this spec's approvals and depend on it, so listing them here made a cycle. No acceptance criterion changes.

2026-11-05: Telegram 39154 and 39155, revised rulings R5, R7 and R14 (no mandatory sandbox): AC2's subject
digest header is stripped by the outside gate alone, since VELDO-0251 no longer has a relay. Status
unchanged.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
