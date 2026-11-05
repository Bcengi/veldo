---
schema: veldo.spec/v1
id: VELDO-0252
title: One small service behind the outside gate verifies the owner's approval token on every write and keeps the owner's service logins, refreshing them before expiry and telling the owner when one fails, and hands the outside gate only the current credential for each call
status: ready
risk: critical
owner: owner
human_approval: required
lane: standalone
depends_on: [VELDO-0065, VELDO-0066, VELDO-0068, VELDO-0144, VELDO-0159, VELDO-0203, VELDO-0234, VELDO-0249, VELDO-0251, VELDO-0253, VELDO-0259]
placement: [contracts, engine, enforcement, distribution]
protected_paths: [".veldo/tool_approval_verifier.py", "engine/.veldo/tool_approval_verifier.py", ".veldo/control_keys.py", "engine/.veldo/control_keys.py", ".veldo/control_signer.py", "engine/.veldo/control_signer.py", ".veldo/control_credential_keystore.py", "engine/.veldo/control_credential_keystore.py", ".veldo/pins/gate.json", "engine/.veldo/pins/gate.json", ".veldo/settlements/*"]
footprint:
  - ".veldo/gate_check_service.py"
  - "engine/.veldo/gate_check_service.py"
  - ".veldo/gate_check_approval.py"
  - "engine/.veldo/gate_check_approval.py"
  - ".veldo/gate_check_grants.py"
  - "engine/.veldo/gate_check_grants.py"
  - ".veldo/gate_check_store.py"
  - "engine/.veldo/gate_check_store.py"
  - ".veldo/gate_binary.py"
  - "engine/.veldo/gate_binary.py"
  - ".veldo/pins/gate.json"
  - "engine/.veldo/pins/gate.json"
  - ".veldo/tool_approval_verifier.py"
  - "engine/.veldo/tool_approval_verifier.py"
  - ".veldo/control_tool_approval.py"
  - "engine/.veldo/control_tool_approval.py"
  - ".veldo/control_signer.py"
  - "engine/.veldo/control_signer.py"
  - ".veldo/control_credential_keystore.py"
  - "engine/.veldo/control_credential_keystore.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_api*.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "engine/ui/**"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0252_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0252-the-token-and-approval-service-behind-the-gate.md"
  - "specs/index.md"
  - "proof/VELDO-0252/**"
behavior_bearing: true
observability:
  logs: >
    One decision line per check: dispatch, service, route template or tool, method, classification, verdict,
    refusal name, token id for a write, grant id and grant version for a credential lookup, and latency. One
    line per submitted request: request id, dispatch, service, route template or tool, method, content type,
    canonical digest and body size, never a body or argument value. One line per grant event: consent
    started (by which principal, through the UI or the channel), consent completed (provider account id,
    scopes granted), refresh succeeded (old and new version, new expiry, whether the refresh token rotated),
    refresh failed (attempt, error class, next attempt), state change (active, refresh_failing,
    reconnect_needed, revoked), revocation at the provider and its result, and each owner notice sent. One
    line per gate binary install or start: version, platform, expected and measured sha256, and one line per
    unit start, stop and restart. No token, refresh token, client secret, authorization code, PKCE verifier,
    state value, body or argument value is ever logged; each value the service handles joins its redaction
    set.
  metrics: >
    Count checks by verdict and refusal name per service; writes allowed; tokens received, consumed and
    expired unused; refreshes by outcome; grants by state; owner notices sent; check latency; gate installs
    refused for a checksum mismatch.
  traces: >
    A token id joins the decision line to its grant and settlement in VELDO-0249 (settlement receipt,
    attributed answer, presentation) and to the outside gate access line of VELDO-0251 for the same call. A
    grant id joins each backend credential lookup to the consent that created the grant, every refresh
    since, and the owner notices about it.
  error_taxonomy: >
    Approval refusals, returned to the outside gate and passed to the caller by name: approval_missing,
    approval_malformed, approval_signature, approval_key_inactive, approval_service, approval_target,
    approval_digest, approval_dispatch, approval_expired, approval_not_yet_valid, approval_replayed,
    approval_ledger (the consumption could not be made durable, so the call is refused),
    approval_body_too_large, approval_request_unknown (an approval naming no request the service stored),
    caller_assertion (the relay's assertion is missing, forged or expired),
    gate_key (the request did not come from the outside gate). Grant refusals: grant_missing:<service>,
    grant_reconnect_needed:<service>, grant_revoked:<service>, grant_refresh_failing:<service> (only once
    the access token has expired). Consent refusals: consent_state (missing, unknown, reused or expired
    state), consent_principal (not the enrolled owner), consent_provider_error:<error>. Install refusals:
    pin_mismatch:gate:<platform>, pin_missing:gate:<platform>, gate_version_mismatch,
    host_prerequisite_missing:<tool> (for example secret-tool, named by setup before anything is installed).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the owner approves the exact request a run will send, and no write passes the outside gate
      unless the service verified a valid, unused approval token bound to that exact request for that
      dispatch, and the token never enters the run. Set and completeness: a run that needs a write first
      submits the exact request to this service through the outside gate's approval route, with no outside
      effect: the service computes its target and canonical digest (as below), stores the request in its
      0700 state under a request id it returns to the caller, and the run raises the approval of VELDO-0249
      naming that id; the owner's presentation is built from the stored request, decoded (fields as fields,
      a file as its name, size, type and a preview), never from the turn's restatement. A workflow
      owner_approval node and an approved schedule raise their approval by the same submission. The signer
      of VELDO-0249 issues each token at the addressed dispatch's launch to this service (as amended by
      proof/VELDO-0251/amend-0249.md), not to the run or a server; the service stores it 0600 in its own
      0700 state directory, keyed by dispatch. The service answers the outside gate's extAuthz call only
      when it carries the outside gate's own key and a valid relay assertion (VELDO-0251 AC1). For a call
      the shared classification table of VELDO-0251 marks as a write it recomputes the target from the
      request it actually received, by the same rule it used at submission: for an HTTP route the service,
      the method, the path after the route prefix (percent-decoded once, dot segments refused), the query
      with keys and values sorted, the content type, and the sha256 of the canonical body (sorted-key
      compact JSON for application/json with floats refused; for application/x-www-form-urlencoded the
      fields sorted by name and then value; for multipart/form-data the ordered list of each part's headers
      with the sha256 of its content, the boundary ignored; the exact bytes otherwise); for a tool the
      service, its declaration revision, the tool name and the canonical arguments digest of VELDO-0249. The
      body limit is the one the service declares in the installation (VELDO-0251 AC4; default 1 MiB, larger
      for media uploads); the check reads the whole body or refuses it as approval_body_too_large, at
      submission and at the send, never checking part of it. It then calls the one verifier,
      tool_approval_verifier.py (standard library plus ssh-keygen), which requires a token that verifies
      with ssh-keygen -Y verify in the veldo-tool-approval namespace against a key active now in the
      published projection, names this dispatch and this exact target, is inside its validity window with at
      most 60 seconds of skew, and is recorded as consumed in the service's SQLite replay ledger (token id
      unique, committed before the allow is returned). Only then does it allow, passing the token id and the
      token's subject digest to the outside gate as request headers for the upstream. Rows: no token, a
      forged signature, a revoked or retired key, a token for another dispatch, service, method, path, query
      or tool, a body or argument changed by one byte, an expired token, a token reused after one success,
      two concurrent calls with one token (exactly one passes), a missing or forged relay assertion, a
      request without the outside gate key, a body over the service's declared limit, and the ledger made
      unwritable: each is refused by its name and the stub vendor records nothing; a submission reaches
      nothing upstream; an approved multipart upload sent again with a new boundary, and an approved form
      body sent with its fields in another order, each pass once; a read passes with no token; the run's
      filesystem, environment and transcript never contain a token body.
    falsified_by: >
      Take the digest from the token instead of recomputing it from the received request, or commit the
      ledger after returning allow: the changed-body row or the concurrent-replay row reaches the stub and
      fails. Or allow when the ledger cannot be written: the unwritable-ledger row passes a call and fails.
      Or digest a multipart body as its exact bytes: the new-boundary row is refused and fails.
  - id: AC2
    text: >
      Claim: the owner grants a service login once, through a consent only the owner can start and finish,
      and the login is stored only in the keystore. Set and completeness: a grant is declared by the
      installation (VELDO-0251 AC4): authorization, token and optional revocation endpoints (https only),
      client id, client secret as a keystore reference, scopes, and the redirect path under the
      installation's configured UI origin (VELDO-0234). The enrolled owner starts consent from the UI (an
      authenticated owner session) or from the channel (an answer attributed to the owner under VELDO-0066;
      an automation sender or anyone else is refused as consent_principal). The service creates the
      authorization URL with PKCE S256 (RFC 7636), a 256-bit random state bound to the grant and the owner
      principal, single use, valid 10 minutes, and an exact registered redirect URI; the channel only
      carries the link, and the service never accepts an authorization code pasted into a message. The
      callback refuses a missing, unknown, reused or expired state as consent_state, exchanges the code with
      the verifier, and stores the access token, the refresh token and the client secret only in the OS
      keystore (VELDO-0144, encrypted at rest by the keyring, written through standard input, never a
      command line) under versioned item names; the service's SQLite record keeps only the grant id,
      service, provider account id, scopes granted, expiry, version and state. Rows: a full consent against
      a stub provider stores a grant whose secrets are found only in the keystore; a replayed state, an
      expired state, a state from another grant and a callback without the verifier are refused; a consent
      started by a non-owner sender is refused; a scan of the SQLite file, the service's logs, the journal
      and the channel transcript finds none of the stub's secret values.
    falsified_by: >
      Accept a callback whose state was already used, or keep the refresh token in the SQLite record: the
      replayed-state row stores a second grant or the scan row finds the refresh token, and the row fails.
  - id: AC3
    text: >
      Claim: a grant is kept fresh before it expires, a rotated refresh token is never lost, and a grant
      that is revoked or keeps failing is told to the owner and is never retried silently forever. Set and
      completeness: the service refreshes a grant when its remaining lifetime falls below the larger of 5
      minutes and 20 percent of its lifetime, with one refresh in flight per grant (a lease row in SQLite).
      On a provider response it first writes the new tokens to the keystore under the next version, then
      commits the version in SQLite, then deletes the old items; on start it reconciles, adopting a newer
      version found in the keystore. A definitive refusal (invalid_grant, invalid_client,
      unauthorized_client, or the provider's documented revocation answer) moves the grant to
      reconnect_needed at once with no further provider call. A transient failure (network error, 5xx, 429
      honouring Retry-After) is retried with capped exponential backoff and jitter while the access token is
      still valid; once it has expired the grant is refresh_failing, retries continue at most hourly, and
      after 24 hours of failure it becomes reconnect_needed. Each state change sends the owner one notice
      through the UI and Veldo's own channel with a reconnect link (a message from the control plane, not a
      call through the outside gate), never a repeat for the same state. Calls for a grant not active are
      refused by name (grant_reconnect_needed, grant_refresh_failing, grant_revoked) with no provider call.
      Revocation by the owner calls the provider's revocation endpoint when declared (RFC 7009), deletes the
      keystore items and marks the grant revoked. Rows against a stub provider and a fake clock: a refresh
      happens before expiry and exactly once under ten concurrent calls; a rotated refresh token survives a
      crash between the keystore write and the SQLite commit; invalid_grant yields reconnect_needed, one
      notice and no further provider request over a simulated week; 503 for 24 hours yields refresh_failing
      then reconnect_needed, two notices in total and at most hourly attempts after expiry; a revoked grant
      sends nothing upstream.
    falsified_by: >
      Retry invalid_grant on the backoff schedule, or notify on every failed attempt: the no-further-request
      row or the two-notices row counts more and fails. Or commit the new version before the keystore
      write: the crash row loses the rotated refresh token and fails.
  - id: AC4
    text: >
      Claim: the credential for a call reaches only the outside gate, only for that call's selected service,
      and the service and the outside gate binary are built only from what is pinned. Set and completeness:
      for every call the outside gate sends, the service returns the current credentials for the call's
      service, the first as extauthz.backend_token and any further ones as headers the check returns for the
      upstream request, each formatted for its declared location (bearer, a named header, a named query
      parameter, or basic), read from the keystore for a static credential or from the active grant, and
      only when the request carries the outside gate key and a relay assertion that selects that service; a
      service declared with no credential (the forward route, a public registry) gets an allow with none.
      Its listener is on host loopback, which no run or project process can reach (VELDO-0251 AC1). The
      service is Python standard library only (http.server, urllib with the default TLS context, sqlite3,
      hmac, hashlib, secrets, json) plus the ssh-keygen and secret-tool binaries Veldo already uses; a suite
      row fails on any other import. The outside gate binary is pinned in .veldo/pins/gate.json: name,
      version 1.7.0, license Apache-2.0, source repository, and per platform the release asset URL and its
      sha256. Setup downloads only that URL, verifies the sha256 before the file is made executable,
      installs it into Veldo's versioned tools directory, and refuses a mismatch as
      pin_mismatch:gate:<platform> or an unpinned platform as pin_missing:gate:<platform>; it never fetches
      a latest release, never uses a package manager, and never updates by itself, and when the project
      publishes a signature or provenance for the asset setup verifies it as well. At every start the
      service checks that the outside gate's reported version equals the pin and refuses to serve otherwise
      (gate_version_mismatch). An upgrade is a reviewed change to the pin file. Setup installs user units
      for the outside gate and this service, started with the authority as the API service is, restarted on
      failure, and refused if the pinned version is wrong; the relay is started per dispatch by the
      launcher; listen ports come from the installation's ports (VELDO-0253). Setup refuses by name a host
      without the tools the service needs (host_prerequisite_missing:secret-tool) before it installs
      anything. Rows: a request without the outside gate key, with an assertion for another service, or with
      no assertion gets no credential; the credential never appears in a run; a tampered asset and an
      unpinned platform are refused before execution; a gate reporting another version is refused; a service
      declaring two credentials gets both upstream; a killed service unit is restarted; setup on a host
      without secret-tool is refused by name; the import row passes.
    falsified_by: >
      Return the credential to any loopback caller, or install the outside gate asset before checking its
      sha256: the no-gate-key row receives the credential or the tampered-asset row executes, and the row
      fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change and stop the service: the outside gate's fail-closed check then refuses every call, so
  no outside service is reachable and nothing is written without approval. Grants stay in the keystore and
  their records in the service's state directory, inert; the owner can revoke them at each provider. The
  pinned gate binary stays installed, unused. No automatic rollback, retry or recovery is authorized.
---

## Intent

The outside gate of VELDO-0251 needs two answers for every call: is this write approved by the owner,
exactly as sent, and which credential goes upstream. This spec builds the one small service that answers
both, so approvals are verified in one place for every service, the owner's service logins live behind the
outside gate and stay fresh on their own, and a login that breaks is told to the owner instead of failing
quietly.

## Context

- VELDO-0249 (approved, amended per proof/VELDO-0251/amend-0249.md) defines the approval: a
  settlement-keyed grant, a signed single-use token bound to the exact request, the tool-approval key under
  the control_keys lifecycle, and one standard library verifier. This spec reuses that verifier and that
  key, verifies the token here, and stores the submitted request the owner approves. It is built and
  landed as one unit with VELDO-0251 and the VELDO-0249 amendment; depends_on runs one way, so the graph
  has no cycle.
- VELDO-0251 makes the outside gate the only way out and sends every call of a selected service to this
  service's check in fail-closed mode. The outside gate adds the credential from extauthz.backend_token and
  removes the caller's own.
- VELDO-0144 and VELDO-0159 already put credentials in the OS keystore through standard input, set by the
  owner in a write-only field. Static credentials keep that path; OAuth grants add the consent flow.
- Ready-made grant holders were weighed: one is a source-available product whose free self-hosted tier is
  described by its vendor as for hobby use, one never hands a token out through its API, one self-hosts
  only on an enterprise plan, and the one open-source vault plugin is archived. A small service of our own
  on the standards is the smaller and safer piece.

## Design

1. One process, two jobs, one check endpoint. The outside gate's extAuthz (HTTP mode) posts each call with
   its body up to the service's declared limit. The service checks the outside gate key and the relay
   assertion, looks up the classification, verifies the approval for a write, and returns allow with the
   backend token, or deny with a refusal name.
2. Approvals. A run submits the exact request first; the owner approves it as stored and decoded. Tokens
   arrive from the signer at the dispatch's launch, are verified by the shared verifier against the
   canonical digest of the request as received, and are consumed durably before allow. A prepare or
   validate-only call that reaches the vendor is a write by the shared classification unless the
   installation declares it read (VELDO-0251 AC3). The token id and subject digest
   go upstream as headers so a two-phase server can still compare its stored pending action.
3. Grants. Consent with PKCE and state, owner only; secrets only in the keystore; refresh ahead of expiry
   with one refresh in flight and rotation written before it is committed; definitive failures stop at
   once; transient failures are bounded and visible; one notice per state change.
4. Dependencies. Standard library only, like the existing Veldo assets. The outside gate binary is the one
   outside artifact, pinned by version and checksum, verified before it runs.

## Out of scope

- The outside gate, the network rule, the declarations and the classifier (VELDO-0251).
- Device authorization and other grant types; request-signing credential schemes.
- Standing approvals for recurring writes.
- Releases, deploys, publishing, pipelines, chunked uploads and batches of many writes, which the owner
  approves as one release and an executor of the control plane performs outside every run.
- Approval by anyone other than the owner.

## What the reviewer judges

- Normal use: the owner connects a calendar API once from the UI; a week later a run reads it with no login
  in the run; the access token was refreshed twice in between; the owner revokes the grant at the provider,
  the next refresh gets invalid_grant, the owner gets one notice with a reconnect link, and calls are
  refused by name until reconnect.
- Threat model: a write with no token, a copied token, a changed body, a replay including two concurrent
  calls, a forged relay assertion, a host process asking for a credential, a replayed consent state, a
  code pasted into the channel, a rotated refresh token lost in a crash, a tampered gate download, a secret
  in a log.
- Out of review scope (filed, not blocking): unlikely edge cases (an owner decision); clock attacks on
  the host beyond the 60 second skew.

## Notes

A token is spent when the check allows, even if the vendor then fails; the owner is asked again, as
VELDO-0249 already requires, because a write whose outcome is unknown must not run twice on one approval.

docs/outside-services.md notes that a provider's OAuth app left in a testing status may issue refresh tokens
that expire within days, so the owner would be asked to reconnect often until the app is published.

## History

2026-11-04: new draft. Owner Telegram 39131 to 39140 approved the plan ("You asked for yes - yes"), item 4:
one small service of our own verifies the approval token on every write as the gate's extAuthz, holds the
OAuth logins (authorization code with PKCE, encrypted at rest in the keystore, refresh before expiry,
revocation) and hands the gate the current backend token per call. Companion of VELDO-0251. Standalone.

2026-11-04: approved by the owner, Telegram 39144 ("Yes", to 39143). Status ready.

2026-11-04: amended per the plan consistency review (research/veldo-plan-consistency-review-2026-11-04.md) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md), both in the owner's installation repository, on the owner's request Telegram 39145. AC1: the run submits the exact request first and the owner approves it decoded; canonical digests for form and multipart bodies; the body limit is declared per service and read whole or refused; workflow approval nodes and approved schedules use the same submission (R4, C1, C2, A24). AC2 and AC3: the redirect origin cites VELDO-0234 (C14), owner notices go through Veldo's own channel (R6). AC4: several credentials per service, no credential for public read services, user units, ports from the installation, the secret-tool prerequisite refused by name (R5, C11, C12, C16). Prepare and validate-only calls follow the shared classification (R12, E1). Many-write releases are out of scope (R3, C3). depends_on adds VELDO-0234 and VELDO-0253 (C14, R1). agentgateway is named the outside gate (E6). Owner field is a role id (B1). Status stays ready; the owner approves the amendments in one message.

2026-11-04: depends on VELDO-0259 instead of VELDO-0250: the installation reader this spec builds on was
split out of VELDO-0250 into VELDO-0259, which lands first, on the owner's request Telegram 39145 (plan
consistency review research/veldo-plan-consistency-review-2026-11-04.md, finding D5). Criteria unchanged;
status stays ready.
