---
schema: veldo.spec/v1
id: VELDO-0171
title: Factory setup writes the API configuration, enrolls the API edge and installs the API behind Tailscale Serve, so the owner enrolls his first passkey on a fresh host, and a second run changes nothing
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W131
plan_revision: 4
depends_on: [VELDO-0130, VELDO-0139, VELDO-0189]
placement: [engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/services/*"
  - ".veldo/services/*"
  - "engine/.veldo/control_client_api*.py"
  - ".veldo/control_client_api*.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/.veldo/control_api_credentials.py"
  - ".veldo/control_api_credentials.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0171_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/74_veldo_0140_standing_delegation.py"
  - "scripts/suites/66_veldo_0047_authority.py"
  - "scripts/suites/support/v171_tailscale.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0171-setup-lays-down-the-api.md"
  - "specs/VELDO-0139-factory-setup-on-a-host.md"
  - "specs/index.md"
  - "proof/VELDO-0171/*"
behavior_bearing: true
observability:
  logs: >
    Record each API step setup runs (the api edge key, its enrollment, the API service and process
    configurations, the API unit, the Tailscale Serve mapping) as done, already done or refused, with
    the tailnet name and loopback port it used and whether a store write went through the running
    service; record each passkey enrollment the host command signs with its label, fingerprint and
    principal; never a key, cookie, token or challenge.
  metrics: >
    Count setup runs by outcome (set up, already set up, refused by name), store writes sent through
    the running service, and passkey enrollments signed and left pending.
  traces: >
    Join each API step to the setup run and store it belongs to, and each passkey enrollment to its
    pending registration, its signed command and the sign-in that follows it.
  error_taxonomy: >
    Distinguish a missing or logged-out Tailscale (unavailable_service:tailscale) from a Tailscale that
    does not let this account configure Serve (unavailable_service:tailscale:operator), a tailnet
    without HTTPS certificates (unavailable_service:tailscale:https), a Serve that cannot persist in the
    background (unavailable_service:tailscale:persistence), a Serve mapping that already names another
    target (invalid_input:tailscale_serve:occupied), an API unit that fails to start
    (unavailable_service:api), a re-run whose arguments differ from what is laid down
    (invalid_input:state_root:holds_<name>), an existing file the run would write differently
    (invalid_input:state_root:differs:<path>), a store write setup cannot send through the running
    service (invalid_input:state_root:service_running:<step>), and a pending registration that is
    expired, unknown or not the one named.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Factory setup enrolls the API's own edge key through the owner-signed channel edge
      enrollment VELDO-0130 uses, and never writes the store while the authority service holds its lock.
      Set and completeness: Setup generates the api edge key (control_channel_enrollment.edge_key_id for
      channel "api") in the protected key directory and its connection key beside the Telegram edge's,
      enrolls it as the api-edge principal named in the ingress configuration by the owner's signed
      enroll command with the key's possession co-signature, exactly as it enrolls the Telegram edge, and
      republishes the key projection. Setup writes the store only while it holds the store's lock
      (authority.lock) itself. When the authority service holds the lock, the enrollment goes to the
      running service as the owner's signed command over its socket, as `veldo factory passkey` sends
      its command, and a store write the service takes no command for is refused by name
      (invalid_input:state_root:service_running:<step>), writing nothing. The service then accepts an API
      call the installed API process signs through the protected signer's api purpose, and refuses one
      signed by any other key. Rows: a fresh host, and a host VELDO-0139 laid down with its service
      running, where the journal shows the service committed the enrollment and setup opened no store
      connection for writing (the running-service row). Falsifier: Leave the api edge's enrollment out of
      setup, keeping its key, and the installed-API call row must fail with the service's refusal of the
      edge's request signature.
    falsified_by: >
      Leave the api edge's enrollment out of setup, keeping its key, and the installed-API call row must
      fail with the service's refusal of the edge's request signature.
  - id: AC2
    text: >
      Claim: Setup writes the API service configuration and installs the API process as a service that
      starts with the authority service, listens on loopback only, and is reached only through Tailscale
      Serve on the host's tailnet name (owner decision, Telegram 29094). Set and completeness: Setup reads
      the host's tailnet name from the Tailscale CLI (resolved from a fixed list of system paths, never
      PATH) and writes it as the rp_id and the https origin of the API service configuration
      (veldo.api_service/v1, on the Telegram ingress's api edge) and of the 0600 API process
      configuration (veldo.api_process/v1) with a loopback listener. It installs the API service
      configuration with the authority service (VELDO-0047's api_service option) on a fresh host, and on
      a host VELDO-0139 laid down it adds it to that installation's configuration directory and names it
      in the installation's service configuration. It installs a systemd user unit from a template beside
      veldo-authority.service that starts and stops with the authority unit, and maps the tailnet name's
      HTTPS to that loopback port with `tailscale serve --bg`, never Funnel. Before writing anything it
      refuses by name a Tailscale that does not let this account configure Serve (no operator setting),
      a tailnet without HTTPS certificates, and a Serve that does not keep the mapping in the background
      (no `--bg` persistence). It starts the API unit itself when the authority service is already running
      and its installation already named the API configuration; when this run added it, setup restarts
      nothing and names the one restart command. Read back the unit, the configurations, the listening
      sockets (none beyond loopback) and the Serve status. The suite drives a stand-in CLI that prints the
      outputs from proof/VELDO-0171/tailscale-capture.json exactly. Before building the stand-in, a
      recorded proof step runs only read-only commands on the owner's host: `tailscale version`,
      `tailscale status --json`, `tailscale serve status --json`, `tailscale debug prefs` (its
      OperatorUser field is the operator setting) and `tailscale serve --help` (its listing of `--bg` is
      the background persistence evidence); their capture is scrubbed by a
      named field allowlist as in VELDO-0172 and committed at that path. The stand-in replays exactly
      those captured outputs for the captured states. Each refusal state and the status after
      `serve --bg` are field edits of the captured JSON, each edit listed in
      proof/VELDO-0171/tailscale-capture.json. The suite owns the
      stand-in's invocation log outside setup's write access and checks it after setup exits on the
      fresh-host row: the row fails unless the log shows one successful `serve --bg` naming the API port,
      even if setup reports success, and any `funnel` invocation fails the row. The three refusal rows retain their captured source
      evidence; the real Tailscale leg is run once by the lead with the owner and recorded, and fixtures
      never count as it. Falsifier: Have setup run
      `tailscale funnel` in place of `tailscale serve`, and the fresh-host row must fail on the invocation log's `funnel` invocation.
    falsified_by: >
      Have setup run `tailscale funnel` in place of `tailscale serve`, and the fresh-host row must fail
      on the invocation log's `funnel` invocation.
  - id: AC3
    text: >
      Claim: On a host setup has just laid down, the owner enrolls his first passkey and signs in with it,
      with no other preparation, and the host command signs only the registration he picked. Set and
      completeness: The API exposes VELDO-0130's registration and possession ceremonies and the key's
      fingerprint, and serves a same-origin content security policy (default-src, script-src,
      connect-src and form-action 'self', frame-ancestors and base-uri 'none', no inline script).
      The enrollment and sign-in screen is built in VELDO-0145's React shell under PLAN-0019 C16;
      this criterion proves the API ceremony and host command without depending on that screen.
      At the host, `veldo factory passkey` lists the pending registrations with each one's label, fingerprint and principal
      (control_api_credentials.describe), and signs enroll_api_credential with the owner's key for the ONE
      registration the owner names by its fingerprint after comparing it with the one his phone shows,
      never every pending one, and sends it to the running service. Set up a fresh host, start the
      service, register two software ES256 authenticators through the API calls with the tailnet name
      as Host and Origin, sign one at the host by its fingerprint, sign in with it, and read the session:
      it names the owner, and the other registration is still pending and cannot sign in. Read the headers of
      every API response, the ceremony routes among them: the policy is served. VELDO-0145 proves the phone screen
      over the tailnet after this API ceremony is built. Falsifier: Have setup write the API's origin
      as the loopback address in place of the tailnet name, and the first-enrollment row must fail on the registration's origin
      check.
    falsified_by: >
      Have setup write the API's origin as the loopback address in place of the tailnet name, and the
      first-enrollment row must fail on the registration's origin check.
  - id: AC4
    text: >
      Claim: Running setup again with the same arguments changes nothing on a host it laid down, and on a
      host VELDO-0139 laid down before this change it adds only the API steps. Set and completeness: A
      re-run is accepted only when EVERY argument (the state root, owner, owner key, workspace, chat,
      token file, host trust, install root, unit directory and profile) equals what the state root's
      store and the installation were laid down with; a re-run with any other value is refused by name,
      writing nothing, as VELDO-0139 AC1 refuses today. An accepted re-run reports each earlier step as
      already done and runs only a step that is missing. Each step checks the file it would write: one
      equal to what it would write is left alone, an absent one is written, and any existing file that
      would differ is refused by name (invalid_input:state_root:differs:<path>) and never overwritten; the
      only change to an existing file is a step adding its own keys that the file lacks or holds as null.
      The store is written only under AC1's lock rule. An update of Veldo changes only what its new steps
      add: the installed engine files under the install root are replaced only by VELDO-0189's upgrade,
      which runs first on a re-run over an older engine. After a second run over a complete host, every file under
      the state root, install root, unit directory, host trust and workspace binding is byte for byte the
      same, the journal head and the Serve status are unchanged, and no key is generated. Over a host set
      up by VELDO-0139 alone, laid down by the whole `.veldo` of commit 7fefdb9a (taken with `git archive`,
      never that commit's setup module alone over the current engine), only VELDO-0189's upgrade and the
      API steps write, and every earlier file outside the installed engine is unchanged but for the
      installation's service configuration naming the API configuration. Falsifier: Generate a new api
      edge key on every run, and the second-run row must fail on the changed key and the second
      enrollment in the journal.
    falsified_by: >
      Generate a new api edge key on every run, and the second-run row must fail on the changed key and
      the second enrollment in the journal.
required_evidence: [unit, integration]
rollback: >
  Stop and disable the API unit, run `tailscale serve reset` for the mapping setup made, remove the API
  process configuration and the API service configuration by hand, and set the installation's
  api_service back to null; revoke the api edge with the owner's signed revocation. The
  authority service, the Telegram channel and every accepted record are unchanged. No automatic rollback
  is authorized.
---

## Intent

The owner reaches his factory's UI from his phone on a host that factory setup built, with no hand-made
key, configuration, unit or tunnel, and running setup a second time is safe.

## Context

W131 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0139's setup
writes `api_edge` into the ingress configuration but never enrolls that edge ("api-edge is enrolled by
VELDO-0130's own setup when it lands", its Notes), writes no API service configuration, and nothing
installs the VELDO-0130 API process: no unit runs control_client_api, and no step puts it behind the
transport the owner chose (Tailscale Serve, Telegram 29092 asked, 29094). This specification owns writing
the API service configuration, with its rp_id and origin read from Tailscale, and VELDO-0167 then adds the
execution record's keys to it, so VELDO-0167 depends on this one. Without it, VELDO-0145's UI cannot run
on a host built by setup, so VELDO-0145 depends on this. The re-run is the one upgrade path for a host
laid down earlier: VELDO-0167 and VELDO-0170 add their steps to it and have no command of their own. No
page is built here: VELDO-0145 owns the enrollment and sign-in screen in its React shell under
PLAN-0019 C16, including the unauthenticated enrollment state, and consumes this API ceremony, host
command and content security policy. The re-run of AC4 narrows VELDO-0139
AC1's refusal of a state root that holds a store to a store laid down for other arguments, and VELDO-0139
AC1 now says so; nothing is ever overwritten. VELDO-0139 is a standalone built item, so its edge is kept
here and not in the plan graph. This new specification is draft; authoring it supplies neither
implementation proof nor operational activation.

## Out of scope

The UI shell and its screens (VELDO-0145, VELDO-0131); other transports (the owner chose Tailscale);
enrolling a second person's passkey (Release 3); sessions that survive a restart (Release 2); the execution
record keys (VELDO-0167) and the receiver host trust key (VELDO-0170), which add their own steps to this
re-run; replacing the installed engine files after an update (VELDO-0189, which this re-run runs first).

## What the reviewer judges

- Normal use: the owner runs veldo factory setup on a host joined to his tailnet, starts the service as
  setup tells him, opens the enrollment page on his phone at the host's tailnet name, gives the phone a
  label, compares the fingerprint his phone shows with the one `veldo factory passkey` lists at the host,
  signs that one registration, and signs in. Later he updates Veldo and runs setup again with the same
  arguments: only steps the new version adds and the host lacks write, and nothing else changes.
- Threat model: the API listening beyond loopback or published to the internet; an api edge key not
  enrolled by the owner's signed command, or enrolled twice; setup writing the store while the running
  service holds its lock; an origin that is not the tailnet name, which would break every enrolled passkey
  when it changes; a re-run that regenerates a key, takes a different argument, or overwrites a file that
  differs; a passkey signed at the host without the owner seeing its fingerprint, or a pending
  registration he did not pick signed with it; the enrollment page running a script from another
  origin. The owner's
  account, his devices, the host, the Tailscale daemon and his tailnet are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as a
  tailnet name renamed after enrollment (every passkey is enrolled again), a Serve mapping another tool
  changes after setup, setup interrupted between two API steps (running it again finishes it), and more
  than one factory on one host; forged rows in our own store and files planted in the installed
  directory.

## Notes

Filed, out of review scope: republishing the key projection while the service runs remains a follow-up.

Each API step checks what is there before it writes: a key already in the key directory and enrolled is
kept, a configuration equal to the one it would write is left alone, a Serve mapping that already names
the API's port is kept, and one that names anything else is refused by name. The tailnet name is read
once per run and must equal the origin already written, so a re-run never changes the relying party.
The Tailscale checks read the CLI's JSON status and its Serve status: the operator
setting decides whether this account may configure Serve without root, the tailnet's HTTPS certificate
capability decides whether an https origin can be served at all, and `--bg` keeps the mapping across the
CLI's exit and a reboot. The lock rule is the store's single-writer rule: whoever holds authority.lock is
the only writer, and a running service is reached through its socket as every other client reaches it.

## History

2026-09-27: new draft for the gap found while drafting VELDO-0164 to VELDO-0170: no specification laid
the API down on a real host. A draft: only the owner marks a specification ready.

2026-09-27: amended on the independent check of this batch and the lead's decisions. The order with
VELDO-0167 is reversed: this specification writes the API service configuration and enrolls the api
edge, drops VELDO-0167 from depends_on, and VELDO-0167 depends on it. AC1 adds the lock rule: setup never
writes the store while the authority service holds its lock, sends the enrollment through the running
service, and otherwise refuses by name, with a running-service row. AC2 names three Tailscale refusals
(no operator setting, no HTTPS certificates, no `--bg` persistence). AC3 signs only the one registration
the owner picks by its fingerprint and serves the page with a same-origin content security policy. AC4
covers every argument, refuses rather than overwrites any file that would differ, and names what an
update changes. The risk is raised to critical, VELDO-0139 AC1 is amended to match, and VELDO-0139 is in
the footprint. The re-run is the one upgrade path (VELDO-0170 and VELDO-0167 add steps to it). Still a
draft.

2026-09-27: lead follow-up: AC3 keeps the API ceremony, host command and content security policy;
VELDO-0145 AC1 owns the enrollment screen in the React shell under C16. AC2 requires a recorded
read-only Tailscale capture before the stand-in, allowlist scrubbing and exact replay, and checks
background persistence against the suite-owned invocation log after setup exits. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-09-27: implementation preflight blocked at AC2. The three authorized read-only
Tailscale captures succeeded, but neither JSON status output exposes the operator
setting or a background-persistence capability. Their required pre-write refusals
cannot be derived from those observations without inventing a CLI contract. Raw
captures remain outside the repository; the allowlist-scrubbed capture and precise
blocker are in proof/VELDO-0171/. No production change, fabricated refusal state,
or live activation was made. The owner must resolve the observation source and
capture contract; acceptance criteria and ready status are unchanged.

2026-09-27, build: the three read-only commands cannot show the operator setting or `--bg` support, so the
builder stopped before writing code. AC2 adds two read-only sources: `tailscale debug prefs` (OperatorUser) and
`tailscale serve --help` (lists `--bg`). Back to draft for the owner's re-mark.

2026-09-27: marked ready again by the owner (Telegram 29237, "Ok" after the explanation in 29235 and 29236).

2026-09-28, build: implemented. Setup's API steps and `veldo factory passkey` are in
.veldo/control_factory_setup_api.py; the re-run, which accepts only the arguments a state root was laid
down with and never overwrites a file, is in control_factory_setup.py; the service admits the api edge
enrollment setup sends while it runs (control_service.py), the API process is an entry point of the
installed executable, the API's HTTP handler sends the content security policy on every response
(control_api.py), and the API unit template is .veldo/services/veldo-api.service. The blocker record is
replaced by the implementation: the five read-only captures (with `debug prefs` and `serve --help`) are
scrubbed into proof/VELDO-0171/tailscale-capture.json, whose status after `serve --bg` names the target
that invocation gave (@TARGET@), each suite run listening on a port of its own. Setup republishes the key
projection itself, from a read-only view of the store, after the running service commits the enrollment,
so over a VELDO-0139 host the earlier files that change are the installation's service configuration and
that projection (AC1 requires it; the api purpose of the protected signer refuses a stale one). An
installation whose fixed executable predates this change has no API process and is refused
`unavailable_service:api:not_installed` before anything is written, the engine upgrade staying Release 2.
The footprint adds scripts/suites/74_veldo_0140_standing_delegation.py and
scripts/suites/support/v171_tailscale.py: suites 73 and 74 run setup too and now give it the same Tailscale
stand-in, so no suite reaches the host's real CLI; and scripts/suites/66_veldo_0047_authority.py, whose list
of the programs an installation runs by path (installed 0500) now names the API process. Proof in suite 85_veldo_0171_setup_api and
proof/VELDO-0171/. The live Serve leg remains the lead's with the owner.

2026-09-28: the owner asked for the engine upgrade in Release 1 (Telegram 29307, "For 0171, ok to add"),
alongside his memory requirement of the same day (29306), which VELDO-0182 and VELDO-0183 take. AC4 now
says the installed engine files are replaced only by VELDO-0189's upgrade, depends_on adds VELDO-0189, and
the rows over a VELDO-0139 host lay that host down from the whole `.veldo` of commit 7fefdb9a with `git
archive`, not only its setup module, so the host holds the older engine and the re-run's refusal
`unavailable_service:api:not_installed` gives way to the upgrade. The text is the one on build-veldo-0171 at
1dbf0b88, with these changes. Back to draft: the owner must re-mark it ready.

2026-09-28: marked ready by the owner (Telegram 29313, "Ok approved"), after the fresh check's text fixes.

2026-09-28, build of the amendment: the rows over a VELDO-0139 host lay it down from the whole .veldo of
7fefdb9a with git archive and its own setup module; the re-run upgrades that engine first (VELDO-0189,
restarting the running service once) and then runs the API steps, and rerun/over-0139-host,
api-edge/running-service and api/start-rules go green through the upgrade. Outside the installed engine
the files that change are service.json (its engine keys, the work key it lacked and api_service), the
receiver configuration (only the host_trust key it lacked, added by the upgrade) and the key projection.
The re-run's first step is engine_upgrade.
