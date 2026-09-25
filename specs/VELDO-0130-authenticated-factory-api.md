---
schema: veldo.spec/v1
id: VELDO-0130
title: Authenticated factory state, message and decision API
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W93
plan_revision: 4
depends_on: [VELDO-0025, VELDO-0035, VELDO-0047, VELDO-0064, VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0126]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "engine/.veldo/authority_contract.py"
  - ".veldo/authority_contract.py"
  - "packs/*/.veldo/authority_contract.py"
  - "engine/.veldo/control_channel_enrollment*.py"
  - ".veldo/control_channel_enrollment*.py"
  - "packs/*/.veldo/control_channel_enrollment*.py"
  - "engine/.veldo/control_signer_answers*.py"
  - ".veldo/control_signer_answers*.py"
  - "packs/*/.veldo/control_signer_answers*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_client*.py"
  - ".veldo/control_client*.py"
  - "packs/*/.veldo/control_client*.py"
  - "engine/.veldo/events.py"
  - ".veldo/events.py"
  - "packs/*/.veldo/events.py"
  - "engine/.veldo/control_event_projection.py"
  - ".veldo/control_event_projection.py"
  - "packs/*/.veldo/control_event_projection.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/*_veldo_0130_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0130-authenticated-factory-api.md"
  - "specs/index.md"
  - "proof/VELDO-0130/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every API operation authenticates the caller and checks current domain/repository and
      operation permissions. Set and completeness: Derive routes from the published API contract,
      including event reads and configuration/workflow operations used by the UI. Exercise
      missing/invalid/expired credentials, wrong-domain access, insufficient role and valid current
      enrollment for every route family; browser mutation sessions also reject cross-origin/forged
      requests under the chosen auth mechanism. Falsifier: Authorize a decision using the body
      actor_id; the impersonation refusal check must fail.
    falsified_by: >
      Authorize a decision using the body actor_id; the impersonation refusal check must fail.
  - id: AC2
    text: >
      Claim: Read and event APIs expose authoritative state with identities, versions and freshness.
      Set and completeness: Compare responses and live event delivery to the actual store for
      projects/objectives, nested backlog/specs/units, machines/workers, run steps/tool calls,
      decisions, gate/review/proof, spend and configuration/workflows. Enumerate supported read
      models and redact credentials; unavailable authority yields an explicit error or labeled stale
      read, never invented live state. Falsifier: Return an unstated stale snapshot as current; the
      freshness check must fail.
    falsified_by: >
      Return an unstated stale snapshot as current; the freshness check must fail.
  - id: AC3
    text: >
      Claim: Message and decision writes reuse common intake and exact settlement. Set and
      completeness: Send plain-text messages through the API and UI message box into 0126; answer a
      decision using current request/presentation versions and actual session principal. Test a
      stale answer, unauthorized owner and conflicting Telegram/UI answers to one request. Inspect
      one terminal ruling with unchanged provenance and no intake self-admission. Falsifier: Create
      a second settlement for the UI answer after Telegram settles; the one-request-one-ruling check
      must fail.
    falsified_by: >
      Create a second settlement for the UI answer after Telegram settles; the one-request-one-
      ruling check must fail.
  - id: AC4
    text: >
      Claim: UI configuration edits and operational actions use typed current-version authority
      commands. Set and completeness: Enumerate the UI action contract for owner admission/priority,
      project pause/cancel, worker stop, team/agent configuration and workflow edits; compare route-
      to-command registrations. Submit valid and stale/unauthorized changes and inspect accepted
      revisions or named refusals with no browser-side authority or direct store writes. Falsifier:
      Bypass authority checking on a workflow save endpoint; the unauthorized-write check must fail.
    falsified_by: >
      Bypass authority checking on a workflow save endpoint; the unauthorized-write check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Give the Veldo UI and other authenticated callers one API for current state, new messages and
exact decision answers, backed by the Linux authority.

## Context

W93 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: the owner enrolls a passkey on his phone and on his desktop browser, each approved by a
  steward-signed enrollment at the host, then signs in with one passkey tap and gets a server-side
  session. From the UI he reads live state, sends a message, answers a decision and edits configuration;
  every write carries the session's anti-forgery token and a same-origin Origin. For each write the API
  edge signs one typed assertion naming the session's member, and the authority judges that member's
  current roles and versions and executes the existing domain command. Logout, idle or absolute expiry,
  a revoked credential or membership, and an API or host restart each end the session.
- Threat model: a caller with no session, an expired one, or one whose credential or membership was
  revoked (its open event stream included); a cross-site page in the owner's own browser forging a write;
  a request body naming another actor or a principal field of any kind; a replayed, other-origin or
  other-relying-party passkey assertion, or one without user verification; a pending registration nobody
  approved used to sign in; an edge assertion naming a principal who holds no current credential, or one
  replayed after its expiry; a listener reachable beyond loopback, or plain HTTP. The owner's devices and
  authenticators, the host account, the store, the protected signer and the TLS terminator on the host
  are trusted, and so is the transport provider the owner chooses to the extent that choice makes it one.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); sessions
  surviving a restart, more than one API instance, rate-limit tuning, signature-counter clone detection
  and authenticator attestation (Release 2); step-up confirmation for dangerous actions and credential
  rotation policy (Release 3); members other than the owner, other browsers' quirks beyond current
  Safari, Chrome and Firefox, and the hosting and reachability choice itself (the owner's decision);
  forged rows in our own store and files planted in the installed directory.

## Notes

Owner Telegram 28857 requires authenticated API intake and the UI. The API is an ingress/read
service over existing domain commands, never a second store or scheduler. Document the chosen
authenticated session/token mechanism, enrollment mapping and secure transport deployment
before ready. The API may not trust actor IDs in request bodies. No additional authentication
provider or framework is selected by this draft.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

### Session, enrollment and transport design

**The mechanism.** The owner signs in with a passkey (WebAuthn Level 2, discoverable credential,
user verification required, attestation "none"), implemented in the engine with no authentication
provider or framework. A verified assertion yields a short server-side session carried by an HttpOnly,
Secure, SameSite=Strict cookie, and every write also carries a per-session anti-forgery token. Passkeys
work the same way in phone and desktop browsers, resist phishing because the browser binds each
assertion to the site's name, and leave no shared secret on the host. Passwords with one-time codes
were rejected as phishable and as a secret the host must keep; client TLS certificates as poorly
supported on phones; a login link sent by the Telegram bot as tying the API to the bot channel and not
phishing resistant. Callers that are not browsers keep the existing paths with their own enrolled
member keys, the signed local IPC of VELDO-0107 and the SSH relay of VELDO-0108, so no function is
lost by this API authenticating browser sessions only.

**How an assertion is verified, with the standard library and OpenSSL.** The API keeps, per credential,
its credential id, its public key as DER SubjectPublicKeyInfo, its COSE algorithm (ES256, -7, or
Ed25519, -8; nothing else is offered or accepted) and a random 16-byte user handle. The public key comes
from the browser's getPublicKey() and getPublicKeyAlgorithm() at registration, so no CBOR is parsed, and
the possession proof below binds that key. At sign-in the API issues a single-use challenge and receives
the credential id, clientDataJSON, authenticatorData, signature and userHandle. It checks, with json and
struct: clientDataJSON's type is "webauthn.get", its challenge is the one issued and still unused, its
origin equals the configured origin exactly and crossOrigin is absent or false; the first 32 bytes of
authenticatorData equal SHA-256 of the configured relying-party id, and the flags byte has user present
(bit 0) and user verified (bit 2) set; the userHandle is the credential's. The signature is then checked
over authenticatorData followed by SHA-256 of clientDataJSON by the openssl command line as a subprocess:
"openssl dgst -sha256 -verify" with the DER key for ES256 (a WebAuthn ES256 signature is already DER
ECDSA), and "openssl pkeyutl -verify -pubin -rawin" for Ed25519. The argument vector is fixed, there is
no shell, the key and signature go in files in a 0700 directory under the API's state directory, the
signed bytes go on standard input, the environment is stripped, the timeout is 10 seconds, and only the
exit status is read. Both forms were run on this host (OpenSSL 3.0.13) for a valid and a tampered
message on 2026-09-24. OpenSSL is Apache-2.0; its current release is 4.0.2 (project releases, 2026-09-24)
and 3.0 or later is required. ssh-keygen -Y stays the verifier for every signature the edge makes,
exactly as VELDO-0126 verifies today; it verifies OpenSSH signature envelopes, and a browser assertion is
not one, which is why OpenSSL is the tool here. The signature counter is not relied on, because synced
passkeys report zero.

**Enrollment mapping.** A passkey belongs to exactly one current person member of the same membership
authority, recorded as a new store kind, api_credential, owned by a new module control_api_credentials.py
with two OpenSSH-envelope signed commands, enroll_api_credential and revoke_api_credential (the
authority contract's envelope, never a second spelling, as VELDO-0067 enrolls an edge key). Enrollment
has two halves. On the new device the owner opens the enrollment page and gives the device a label; the
API runs a registration ceremony (checking type "webauthn.create", the challenge and the origin) and at
once a sign-in ceremony with the new credential whose challenge is SHA-256 of the canonical registration
binding (relying-party id, origin, credential id, public key, algorithm, label, a fresh nonce). That
assertion, verified as above, is the possession proof. The API keeps the pending registration in a 0600
file in its state directory for 15 minutes, at most three at a time, and shows the key's fingerprint.
It grants nothing: a pending credential cannot sign in. On the host, a current person member holding
membership_steward whose scope covers the principal runs the enrollment tool, which shows the label,
the fingerprint and the principal, and signs enroll_api_credential with the steward's personal key.
Before commit the command's verification rechecks the possession proof with OpenSSL, so the record
verifies on its own, and refuses by name a principal who is not a current person member, a credential
id or key another principal holds, a stale version, an expired pending registration or an envelope for
another authority. The committed record holds the principal, credential id, key, algorithm, user handle,
relying-party id, origin, label, effective time, proof and envelope. The owner enrolls his own passkeys
this way; it grants no role, so it is not a self-grant. Revocation is revoke_api_credential, signed by a
steward at the host or sent by a steward's own UI session as an ordinary edge assertion, and
revoke_membership revokes every credential of the member with it. An API session can never enroll a
credential.

**The API edge and domain commands.** The API is its own principal, enrolled through the VELDO-0067
channel edge enrollment as a new channel "api" (a CHANNELS entry with its own edge key id and the
attribution request id, credential id and assertion time), a service member with no roles. Its private
key stays in the protected key directory, and the API process never reads it: it asks the protected
signer, which gains an "api" purpose that signs only the typed API assertion shapes and the API's
VELDO-0107 requests and independently checks that the edge key and membership are current and that the
principal named is the principal of a current api_credential and a current person member. Every route
has an exact-field body schema with no actor field; a body carrying principal, actor, actor_id, decider
or any unknown field is refused invalid_input, never ignored. For each accepted request the API builds
one assertion from the session alone (schema veldo.api_assertion/v1, domain, repository, edge, a
single-use request id, the session's principal and credential id, a session handle that is not the
cookie, the operation, target, parameters, expected versions, issue time, and expiry 60 seconds later),
has the signer sign its canonical bytes in the contract's command namespace, and sends it over VELDO-0107.
The authority verifies the edge signature with ssh-keygen -Y, the credential and member again, and the
member's roles and scope at the operation's boundary (decision_settlement admits only a person), then
executes the existing typed command with provenance naming the channel, edge, request id, credential and
assertion digest; the journal's actor is the member, carried by the edge. Messages use VELDO-0126's API
request shape unchanged, with the session's principal. Decision answers are VELDO-0068 answer assertions
on channel api under the same delegation and VELDO-0065 presentation-receipt rules the Telegram answer
meets, so one request still gets one ruling. Reads and the event stream go through the authority's
inspection and the VELDO-0051 publication, never a direct store read. The changes to authority_contract.py,
control_channel_enrollment.py and control_signer_answers.py are outside this footprint and are added to
it before they are made, as VELDO-0126 did.

**Secure transport.** The browser must reach the API over HTTPS under a DNS name it trusts: WebAuthn
needs a secure context and a relying-party id that is a domain, never an IP address, and changing the
name later invalidates every enrolled passkey. The API serves plain HTTP with the standard library's
ThreadingHTTPServer on a loopback address and configured port only, never on a LAN, tailnet or public
interface, because Python's http.server is not meant to face a network. A TLS terminator on the same
host (TLS 1.2 or later, 1.3 preferred) forwards to it with the Host header preserved, and holds a
certificate from a public ACME authority or the network option's own issuer. The API refuses any Host
other than the configured name, uses forwarded client addresses for logs only, caps request bodies at
64 KiB and sends Strict-Transport-Security. Where the network option terminates TLS itself on the host
(Tailscale Serve) nothing more is installed; otherwise the terminator is Caddy (Apache-2.0, current
release 2.11.4 on its GitHub releases, 2026-09-24; our travelbot tunnel gateway already uses it).
**How the phone reaches the host is the owner's decision.** The options, neutrally: a Tailscale tailnet
name with its issued certificate, reachable only from the owner's enrolled devices (free personal tier;
already installed on this host); a Cloudflare Tunnel to a public name on a domain the owner holds, where
Cloudflare terminates TLS and can see the traffic (free tier, plus the domain); a self-run WireGuard
tunnel with a DNS name and a Let's Encrypt certificate through Caddy (no subscription, a domain and an
open UDP port at the host's network); or a public name on the host itself with port 443 open and Caddy
(no subscription, a domain, and the sign-in page exposed to the internet).
**The owner chose the Tailscale tailnet** (Telegram 29092 asked, 29094 "Tailscale is ok"): the host's
existing tailnet on his personal account, with Tailscale Serve terminating TLS for the host's tailnet
name and the phone joining with the Tailscale app. No other terminator is installed.

**Sessions.** The API keeps sessions behind one interface (create, find, touch, end, end by credential,
end by principal), held in the API process's memory in Release 1; sessions that survive a restart are
Release 2 durability. The parameters are these:

| Item | Rule |
|---|---|
| Sign-in challenge | 32 random bytes from secrets, single use, expires after 120 seconds |
| Session cookie | __Host-veldo-session: 32 random bytes, Secure, HttpOnly, SameSite=Strict, Path=/, no Domain; the API keeps only its SHA-256, and each sign-in makes a new one |
| Anti-forgery token | 32 random bytes per session, returned by sign-in and by the session read, kept in page memory only, sent as a request header on every write, compared with hmac.compare_digest |
| Write checks | token matches, Origin equals the configured origin, Sec-Fetch-Site is same-origin when present, Content-Type is application/json; reads never change state |
| Idle expiry | 30 minutes after the last authenticated request |
| Absolute lifetime | 12 hours after sign-in, then a new passkey sign-in |
| Logout | a write that ends the session and clears the cookie; "sign out everywhere" ends every session of the member |

Every request, the event stream included, checks the session first and then reads from the authority
that its credential is current and its principal a current person member, so a revocation or role change
applies on the next request with nothing polled. The API also follows the journal through the VELDO-0051
publication, and a revoke_api_credential or revoke_membership event ends the affected sessions and
closes their open event streams at once; an assertion already in flight is refused by the authority's
own recheck. An API or host restart ends every session, pending registration and challenge, and the
owner signs in again. The refusals are named in the error taxonomy: unauthenticated (no session, expired,
revoked, a failed assertion) and unauthorized (forgery checks, role or scope). Logs name the operation,
principal, credential id, session handle and refusal, never a cookie, token, challenge, key or signature.

The refusal of the API's judge outside the authority process (control_api_authority.authority_problem:
the descriptor must be the stable lock file beside the store and this process must hold its exclusive
flock) holds while the authority service runs, because the service holds that store lock for as long as
it serves. While no service runs the lock is free, so a process that constructs the judge itself can
take it; this is the VELDO-0047 one-instance lock doing its job, not an API boundary, and the API process
never constructs the judge: it reaches the authority only through the service socket.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 5, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-09-24, design: the Notes now choose the mechanism the draft left open. The owner signs in with a
passkey verified in the engine (json and struct, OpenSSL as a subprocess for ES256 and Ed25519) into a
server-side session with an HttpOnly, Secure, SameSite=Strict cookie and a per-session anti-forgery
token; a passkey is enrolled to a current person member by a steward-signed command with a possession
proof; the API is the enrolled "api" channel edge that signs an assertion naming the session's member
and never reads an actor from a body; it listens on loopback behind a TLS terminator on the host, and how
the phone reaches the host is left to the owner. A "What the reviewer judges" section is added. The
criteria, status, risk, dependencies and footprint are unchanged.

2026-09-25: the owner chose the Tailscale tailnet for transport (29092/29094). The footprint gains the
modules the authentication design changes (the authority contract, channel enrollment, the answer signer,
the scaffold) and the teeth-mutation registry.

2026-09-24, implementation phase 1 (branch build-veldo-0130): the API skeleton and AC1 and AC3 for the
auth, messages and decisions route families. New engine modules: control_api (the loopback
ThreadingHTTPServer service, the one published route table ROUTES with handlers registered by route
name, server-side sessions, the anti-forgery, Origin, fetch-metadata, Host and body-size checks, the
registration and possession ceremonies with 0600 pending files, and `follow`, which ends sessions from
committed journal records), control_api_webauthn (the passkey checks with json, struct and the openssl
subprocess), control_api_credentials (the api_credential store kind and its two steward-signed commands),
control_api_assertion (the veldo.api_assertion/v1 shape and the one domain request each operation derives),
control_api_signer (the protected signer's "api" purpose and the API's client of it) and
control_api_authority (the authority's recheck and execution into VELDO-0126 intake, VELDO-0068 settlement
and credential revocation). authority_contract gains EDGE_CHANNELS with the "api" edge and edge_channel();
control_channel_enrollment enrolls it; control_signer_answers hands the api edge to its own purpose.
Suite 71_veldo_0130_api; proof in proof/VELDO-0130; teeth are finding 130. Decisions the build made,
each for the reviewer: the "api" entry lives in EDGE_CHANNELS, not CHANNELS, because CHANNELS is the
VELDO-0020 answer-channel registry whose order settle() ranks answers by and whose set suite 33 pins;
for Ed25519 the signed bytes go to openssl in a file in the same 0700 directory, because OpenSSL 3.0.13's
pkeyutl cannot size a pipe for a one-shot verification (measured), while ES256 keeps standard input; a
revoked membership ends its credentials by derivation (a credential is current only while its principal
is a current person member), with no second write; the committed intake and settlement records keep
their own provenance unchanged (channel api, edge, request id, request digest), and the credential id,
session handle and assertion digest are in the authority's observation of that request id; a failed
registration ceremony ends its registration, and an enrolled one stops being pending. Left for phase 2:
AC2's read models and live events (and wiring `follow` to the VELDO-0051 publication so open streams
close), AC4's configuration and operational actions, extending ROUTES with those families, and routing
the assertion packets through the VELDO-0047 service socket over VELDO-0107 with the signer signing the
API's own requests, which changes control_service.py and control_client.py and adds them to the
footprint first.

2026-09-25, implementation phase 2 (branch build-veldo-0130): AC2 and AC4. New engine module
control_api_models: the published read models (objectives, work, workers, runs, decisions, proof, spend
and configuration, each naming the store kinds it reads with the module and specification that own
them), the UI action contract and the named gaps, the redaction and the authority-side reader. ROUTES
gains the reads family (the published contract and one GET per read model), the configuration family (a
workflow revision's read through VELDO-0132's load, and its save) and the events family (the event read
and the live stream); a GET's query parameters are its exact fields. Every read goes through the
authority on its own connection, and each answer carries identities, versions and entity digests, the
journal watermark it was read at and freshness "live"; the event feed is read through the VELDO-0051
publication's journal reader and labels the published events "stale", with the count of records not
yet published, whenever the publication is behind the head; an unreadable store or publication is
unavailable_service, never an answer. Credentials are redacted by field name, by environment and header
mappings and by the secret scanner's known shapes. The live stream (text/event-stream) is fed by
`deliver`, which takes the VELDO-0046 notification hint the authority passes after each accepted
command, follows the records after its cursor, ends the sessions a revocation ends, closes their streams
and re-reads the rest for each stream's own member. A workflow save is the assertion operation
save_workflow, which the authority executes as VELDO-0132's Workflows.save for the verified principal
and base, so a stale base is stale_version and a member without the editor role is unauthorized.
Decisions the build made, each for the reviewer: the phase 1 in-process authority stays the stand-in for
the VELDO-0047 socket, so a command committed at the host (a steward's revocation) reaches `deliver`
from the authority service once that phase is wired, and the suite passes the hint as that service
would; the event read calls the publication's own journal reader in place, leaving
control_event_projection unchanged. Named gaps, each with the specification that owns it: projects
(VELDO-0076); accepted objectives (VELDO-0077; objectives are served as the VELDO-0126 intake proposals
and questions); backlog items and the nesting of specs and units under them (VELDO-0078); a machine
registry with host capabilities (VELDO-0125; machines are derived from the host and platform each
dispatch recorded); tool call records (no specification writes them yet, VELDO-0131 AC2 consumes them;
run steps are the workflow cycles' traces); team configuration (VELDO-0089). For AC4: owner admission
(VELDO-0079), owner priority (VELDO-0078), project pause and cancel (VELDO-0076), worker stop (VELDO-0041:
the stop mechanism exists and no authority command requests it) and team and agent configuration edits
(VELDO-0089, VELDO-0127) have no typed command in the engine yet, so they have no route. Still left:
routing assertions and reads through the VELDO-0047 service socket.

2026-09-25, footprint for phase 3: the footprint gains the VELDO-0047 authority service and the
VELDO-0107 client (control_service*.py and control_client*.py, engine, root and pack copies), because
phase 3 routes the API's assertions and reads through the service socket, which changes
control_service.py and adds the service's API side and the API process's client beside them; and
events.py, because the service's fixed executable loads VELDO-0051's publication, whose events.py
loaded its proof-corpus sibling from the repository layout rather than beside itself, which a copy laid
outside a .veldo directory cannot satisfy.

2026-09-25, implementation phase 3 (branch build-veldo-0130): the API reaches the authority only through
the VELDO-0047 authority service socket over VELDO-0107. New engine modules: control_service_api (the
service's side: the veldo.api_service/v1 configuration copied at installation (the installer's api_service option), which
must be this authority's and name the api edge its Telegram ingress names; the ApiAuthority constructed
at `serve` on the ingress's store connection, sharing its acquirer and settlement, with the lock the
service holds; each API call run there; a steward's enroll_api_credential and revoke_api_credential
admitted there; the post-commit hint sent to each subscribed API) and control_client_api (the API
process's side: ServiceAuthority, whose every call is one control_client.send with an API call command
signed by the protected signer; the API's hint socket, 0600 in its 0700 state directory, taking only a
peer of this account; and open_api, the production construction of the API process). The protected
signer's api purpose gains sign_api_request, which signs a VELDO-0107 request for this authority whose
command is exactly one API call, in its own namespace veldo-api-request, and nothing else; the service
verifies an API call's request against the enrolled api edge key alone in that namespace, so no member
key speaks as the API. After every packet or channel pass that advanced the journal, whoever sent it, the
service sends the head record's VELDO-0046 hint to each subscribed API, so a revocation committed at the
host ends the API's sessions and closes their open streams with nothing passed by hand; an API that sees
a new service instance subscribes again and reconciles from its cursor. The judge
(control_api_authority) refuses every command and read, missing_authority:not_the_authority, unless its
process holds the service's exclusive lock on the stable lock file beside the store through the
descriptor it was given, so the API process cannot run a command in-process while the service runs. The
service's closure derivation now follows a loader helper called through another function of its module
(control_workflow's _organ), which the API's modules load. Decisions the build made, each for the
reviewer: the API rides on the Telegram ingress (an installation naming an API service configuration without a
channel ingress refuses by name), because the VELDO-0126 intake needs the ingress's acquirer and one settlement service
must rule for both channels; the hint is a one-shot push to the API's own socket, never a poll, and the
API always re-reads through the feed, so a forged or stale hint changes nothing; subscriptions live in the
service's memory and an API re-subscribes when an answer names another instance (durable subscriptions
are Release 2). Phases 1 and 2 behave as before; their fixture holds its own store's lock as the service
would.

2026-09-25, review fixes (branch build-veldo-0130, two reviews of phase 3): the API's deliver no longer
reads a single feed page and requires the hinted record on it. It pages the feed from its cursor until
it reaches the hinted record, applying each page in order (a revocation ends its sessions and closes
their streams as it is met), and every stream, including the first frame of a new one, is filled page by
page to the head; so an API any number of records behind (a restart, lost hints) reconciles on the next
hint. The service now remembers its subscribers across a restart (a 0600 file in its state directory,
superseding the in-memory subscriptions and the Release 2 note above), numbers each hint per subscriber
and names its instance in it, and a new instance sends each remembered API the head's hint once it
serves; the API's hint channel then sees the new instance, or a gap in the numbers, and subscribes again
and reconciles by itself, without waiting for a request of its own. A new instance noticed by a call made
inside a delivery defers its reconcile to the end of that delivery (no re-entry, no deadlock) and applies
it once. The event feed reads only VELDO-0051's new public bounded readers (control_event_projection
journal(after, limit) with the head, and published(after, upto), the projection's own log never past its
stored watermark), never its private full-journal reader or events it derives itself; the footprint gains
control_event_projection.py (engine, root and pack copies) for them, and VELDO-0051's behavior is
unchanged. A stream resumes from the Last-Event-ID an EventSource sends on reconnect; a stream whose
session expired closes as session_expired, not revoked. Redaction uses the secret scanner's own full
detection (scan_text: patterns and entropy). A down service during registration answers 503
unavailable_service, and two possession requests racing on one registration id refuse the second by name
(stale_version:registration_completed). openssl is resolved once to an absolute path from a fixed list
of system locations, never PATH, and its absence refuses unavailable_service:openssl. The Notes state
that the in-process refusal holds while the authority service runs. New rows events/reconcile-past-page,
events/resume-last-event-id, events/expiry-named, events/published-watermark, events/reconcile-deferred,
enrollment/possession-race, webauthn/openssl-fixed-path, service/restart-reconciles and
service/down-at-registration, and an entropy check in reads/authoritative, each red by assertion at
c3c0c6a; fifteen new finding 130 mutations, each reddening its row. Acceptance criteria, status, risk and
dependencies are unchanged.

2026-09-25, fresh-check fixes (branch build-veldo-0130): a stream whose credential the stream's own
recheck finds revoked, or whose membership it finds ended, closes as revoked, as follow closes it, so the
close reason no longer depends on which path saw the revocation first; service/restart-reconciles waits
for the reconcile after the new subscription to reach the head with no delivery in hand before it
revokes. A delivery the service fails (the feed refused unavailable_service, or a call raising, such as a
reconcile's subscription) keeps its catch-up owed, and the hint socket's thread, which wakes every 0.25
s, runs it again with backoff (0.25 s doubling to 8 s) until it reaches the head; this is a retry of a
delivery known to have failed, and with nothing owed it calls nothing. A stream whose session a
revocation ended while the stream was filling is closed as revoked once registered. open_api delivers the
head the subscription answers, so the API's cursor is set from the start. New rows
events/revoked-either-path, events/fill-window-revocation, events/retry-after-failure and
service/connect-sets-cursor, each red by assertion at c0b27cc; seven new finding 130 mutations, each
reddening its row. Acceptance criteria, status, risk and dependencies are unchanged.
