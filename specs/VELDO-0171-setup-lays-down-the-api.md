---
schema: veldo.spec/v1
id: VELDO-0171
title: Factory setup enrolls the API edge and installs the API behind Tailscale Serve, so the owner enrolls his first passkey on a fresh host, and a second run changes nothing
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W131
plan_revision: 4
depends_on: [VELDO-0130, VELDO-0139, VELDO-0167]
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
  - "engine/.veldo/control_api_pages/*"
  - ".veldo/control_api_pages/*"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0171_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0171-setup-lays-down-the-api.md"
  - "specs/index.md"
  - "proof/VELDO-0171/*"
behavior_bearing: true
observability:
  logs: >
    Record each API step setup runs (the api edge key, its enrollment, the API process configuration, the
    API unit, the Tailscale Serve mapping) as done or already done, with the tailnet name and loopback
    port it used; record each passkey enrollment the host command signs with its label, fingerprint and
    principal; never a key, cookie, token or challenge.
  metrics: >
    Count setup runs by outcome (set up, already set up, refused by name) and passkey enrollments signed
    and refused.
  traces: >
    Join each API step to the setup run and store it belongs to, and each passkey enrollment to its
    pending registration, its signed command and the sign-in that follows it.
  error_taxonomy: >
    Distinguish a missing or logged-out Tailscale (unavailable_service:tailscale) from a Serve mapping
    that already names another target (invalid_input:tailscale_serve:occupied), an API unit that fails
    to start (unavailable_service:api), a re-run whose arguments differ from what is laid down
    (invalid_input:state_root:holds_<name>), and a pending registration that is expired or unknown.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Factory setup enrolls the API's own edge key through the owner-signed channel edge
      enrollment VELDO-0130 uses. Set and completeness: Setup generates the api edge key
      (control_channel_enrollment.edge_key_id for channel "api") in the protected key directory and its
      connection key beside the Telegram edge's, enrolls it as the api-edge principal named in the ingress
      configuration by the owner's signed enroll command with the key's possession co-signature, exactly
      as it enrolls the Telegram edge, and republishes the key projection. The service then accepts an API
      call the installed API process signs through the protected signer's api purpose, and refuses one
      signed by any other key. Falsifier: Leave the api edge's enrollment out of setup, keeping its key,
      and the installed-API call row must fail with the service's refusal of the edge's request
      signature.
    falsified_by: >
      Leave the api edge's enrollment out of setup, keeping its key, and the installed-API call row must
      fail with the service's refusal of the edge's request signature.
  - id: AC2
    text: >
      Claim: Setup installs the API process as a service that starts with the authority service, listens
      on loopback only, and is reached only through Tailscale Serve on the host's tailnet name (owner
      decision, Telegram 29094). Set and completeness: Setup reads the host's tailnet name from the
      Tailscale CLI (resolved from a fixed list of system paths, never PATH), writes it as the rp_id and
      the https origin of the API service configuration and of the 0600 API process configuration
      (veldo.api_process/v1) with a loopback listener, installs a systemd user unit from a template beside
      veldo-authority.service that starts and stops with the authority unit, and maps the tailnet name's
      HTTPS to that loopback port with Tailscale Serve, never Funnel. It starts the API unit itself when
      the authority service is already running. Read back the unit, the configurations, the listening
      sockets (none beyond loopback) and the Serve status. The suite drives a stand-in CLI that prints the
      real CLI's recorded output; the real Tailscale leg is run once by the lead with the owner and
      recorded, and fixtures never count as it. Falsifier: Have setup run `tailscale funnel` in place of
      `tailscale serve`, and the tailnet-only row must fail on the Serve status naming the internet.
    falsified_by: >
      Have setup run `tailscale funnel` in place of `tailscale serve`, and the tailnet-only row must fail
      on the Serve status naming the internet.
  - id: AC3
    text: >
      Claim: On a host setup has just laid down, the owner enrolls his first passkey and signs in with it,
      with no other preparation. Set and completeness: The API serves one static enrollment and sign-in
      page (standard library, no framework) that runs VELDO-0130's registration and possession ceremonies
      and shows the key's fingerprint; at the host, `veldo factory passkey` lists the pending
      registrations, shows each one's label, fingerprint and principal (control_api_credentials.describe),
      signs enroll_api_credential with the owner's key and sends it to the running service. Set up a
      fresh host, start the service, register a software ES256 authenticator through the page's calls
      with the tailnet name as Host and Origin, sign it at the host, sign in, and read the session: it
      names the owner. The phone leg over the tailnet is run once by the lead with the owner and
      recorded. Falsifier: Have setup write the API's origin as the loopback address in place of the
      tailnet name, and the first-enrollment row must fail on the registration's origin check.
    falsified_by: >
      Have setup write the API's origin as the loopback address in place of the tailnet name, and the
      first-enrollment row must fail on the registration's origin check.
  - id: AC4
    text: >
      Claim: Running setup again with the same arguments changes nothing on a host it laid down, and on a
      host VELDO-0139 laid down before this change it adds only the API steps. Set and completeness: A
      re-run over a state root whose store this setup laid down for the same owner key, workspace and
      chat reports each earlier step as already done and runs only a step that is missing. After a second
      run over a complete host, every file under the state root, install root, unit directory, host trust
      and workspace binding is byte for byte the same, the journal head and the Serve status are
      unchanged, and no key is generated. Over a host set up by VELDO-0139 alone, only the API steps
      write, and every earlier file is unchanged. A re-run with another owner key, workspace or chat is
      refused by name, writing nothing, as VELDO-0139 AC1 refuses today. Falsifier: Generate a new api
      edge key on every run, and the second-run row must fail on the changed key and the second
      enrollment in the journal.
    falsified_by: >
      Generate a new api edge key on every run, and the second-run row must fail on the changed key and
      the second enrollment in the journal.
required_evidence: [unit, integration]
rollback: >
  Stop and disable the API unit, run `tailscale serve reset` for the mapping setup made, and remove the
  API process configuration by hand; revoke the api edge with the owner's signed revocation. The
  authority service, the Telegram channel and every accepted record are unchanged. No automatic rollback
  is authorized.
---

## Intent

The owner reaches his factory's UI from his phone on a host that factory setup built, with no hand-made
key, configuration, unit or tunnel, and running setup a second time is safe.

## Context

W131 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0139's setup
writes `api_edge` into the ingress configuration but never enrolls that edge ("api-edge is enrolled by
VELDO-0130's own setup when it lands", its Notes), and nothing installs the VELDO-0130 API process: no unit
runs control_client_api, and no step puts it behind the transport the owner chose (Tailscale Serve,
Telegram 29092 asked, 29094). VELDO-0167 writes the API service configuration's `records` key and filed
this as out of its scope. Without it, VELDO-0145's UI cannot run on a host built by setup, so VELDO-0145
depends on this. No specification owns the page the first passkey is enrolled from, since VELDO-0145's
shell needs a signed-in session to show anything; this one serves the minimal page for it. The re-run of
AC4 narrows VELDO-0139 AC1's refusal of a state root that holds a store to a store laid down for other
arguments; nothing is ever overwritten. VELDO-0139 is a standalone built item, so its edge is kept here
and not in the plan graph. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation.

## Out of scope

The UI shell and its screens (VELDO-0145, VELDO-0131); other transports (the owner chose Tailscale);
enrolling a second person's passkey (Release 3); sessions that survive a restart (Release 2); the execution
record keys (VELDO-0167) and receiver host trust upgrade (VELDO-0170).

## What the reviewer judges

- Normal use: the owner runs veldo factory setup on a host joined to his tailnet, starts the service as
  setup tells him, opens the enrollment page on his phone at the host's tailnet name, gives the phone a
  label, confirms the fingerprint at the host with `veldo factory passkey`, and signs in. Later he runs
  setup again after an update and nothing changes.
- Threat model: the API listening beyond loopback or published to the internet; an api edge key not
  enrolled by the owner's signed command, or enrolled twice; an origin that is not the tailnet name, which
  would break every enrolled passkey when it changes; a re-run that regenerates a key or rewrites a
  configuration; a passkey signed at the host without the steward seeing its fingerprint. The owner's
  account, his devices, the host, the Tailscale daemon and his tailnet are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as a
  tailnet name renamed after enrollment (every passkey is enrolled again), a Serve mapping another tool
  changes after setup, setup interrupted between two API steps (running it again finishes it), and more
  than one factory on one host; forged rows in our own store and files planted in the installed
  directory.

## Notes

Each API step checks what is there before it writes: a key already in the key directory and enrolled is
kept, a configuration equal to the one it would write is left alone, a Serve mapping that already names
the API's port is kept, and one that names anything else is refused by name. The tailnet name is read
once per run and must equal the origin already written, so a re-run never changes the relying party.

## History

2026-09-27: new draft for the gap found while drafting VELDO-0164 to VELDO-0170: no specification laid
the API down on a real host. A draft: only the owner marks a specification ready.
