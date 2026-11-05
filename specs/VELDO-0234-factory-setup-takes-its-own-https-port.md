---
schema: veldo.spec/v1
id: VELDO-0234
title: Factory setup can put the API on its own tailnet HTTPS port, so a host whose HTTPS root serves another app keeps it
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0171, VELDO-0130, VELDO-0227]
placement: [engine, distribution]
protected_paths: ["scripts/gate_unconfined.json"]
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "scripts/suites/support/v171_tailscale.py"
  - "scripts/suites/*_veldo_0171_*.py"
  - "scripts/suites/*_veldo_0234_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/gate_unconfined.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0234-factory-setup-takes-its-own-https-port.md"
  - "specs/index.md"
  - "proof/VELDO-0234/*"
behavior_bearing: true
observability:
  logs: >
    Setup's report names the tailnet HTTPS port it used, the origin it wrote (https://<name> on port 443,
    https://<name>:<port> on any other) and the Serve mapping of that port as done, already done or
    refused; it names the other Serve mappings it found and left alone; never a key or a token.
  metrics: >
    None beyond setup's existing counts of runs by outcome: a one-shot host command.
  traces: >
    The API service and process configurations themselves record the origin, relying party id and host
    setup wrote; the Serve status read back is joined to the setup run as in VELDO-0171.
  error_taxonomy: >
    Keep VELDO-0171's names. A Serve mapping of the chosen port that names another target or is funneled
    stays invalid_input:tailscale_serve:occupied, now naming the port. A port outside the ones Tailscale
    Serve offers for HTTPS is invalid_input:https_port. A re-run with a port other than the one laid down
    is invalid_input:state_root:holds_https_port, writing nothing.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: setup takes the tailnet HTTPS port as a setup option, default 443, and maps only that port.
      Set and completeness: the option accepts 443, 8443 and 10000 (the HTTPS ports Tailscale Serve
      offers) and refuses any other value as invalid_input:https_port before anything is written.
      serve_state reads the Web key <name>:<port>, the TCP key <port> and AllowFunnel for that port only;
      a mapping of another port, such as the HTTPS root that serves another app, is neither refused nor
      changed, and a background `tailscale serve` naming that HTTPS port is the only Serve write. The chosen port, when
      another target or Funnel holds it, is refused as invalid_input:tailscale_serve:occupied naming the
      port, as today. Rows, on VELDO-0171's stand-in CLI with the captured status edited to hold
      `/ proxy http://127.0.0.1:8002` on 443: port 8443 sets up and the stand-in's invocation log shows one
      serve naming 8443 and nothing touching 443; port 443 is refused as occupied; 8443 already mapped
      elsewhere is refused as occupied naming 8443.
    falsified_by: >
      Keep HTTPS_PORT fixed at 443 inside serve_state, and the 8443 row must be refused as occupied by the
      root mapping.
  - id: AC2
    text: >
      Claim: on a port other than 443 the origin is https://<name>:<port> everywhere Veldo records or
      checks it, and the WebAuthn relying party id stays the bare name. Set and completeness: the API
      service configuration (veldo.api_service/v1 origin), the API process configuration (api.origin and
      api.host, the Host header the API requires, which the browser sends as <name>:<port>), the passkey
      binding and credential record (control_api_credentials, control_api_webauthn origin checks), the
      setup report and every URL Veldo sends the owner carry that origin; rp_id is <name> with no port in
      both configurations, the binding and the record, because a relying party id is a host name. On 443
      every one of them is byte for byte what VELDO-0171 writes today (https://<name>, host <name>), since
      a browser drops the default port from an origin. Row: VELDO-0171 AC3's first enrollment run on port
      8443 with Host and Origin <name>:8443 and https://<name>:8443: two software authenticators register,
      the owner signs one by fingerprint, it signs in, and its authenticator data's rp id hash is the
      hash of <name>.
    falsified_by: >
      Write the origin without the port on 8443, and the first-enrollment row must fail on the
      registration's origin check (wrong_origin).
  - id: AC3
    text: >
      Claim: a re-run keeps the port it was laid down with, and a host set up before this change is
      unchanged. Set: a re-run with the same port changes nothing (VELDO-0171 AC4's byte-for-byte rule,
      journal head and Serve status included); a re-run naming another port is refused as
      invalid_input:state_root:holds_https_port and writes nothing; a host laid down by the commit before
      this change, re-run without the option, reads as port 443 and every file stays the same.
    falsified_by: >
      Rewrite the origin from the option on every run, and the other-port re-run row must change
      api-service.json instead of refusing.
required_evidence: [unit, integration]
rollback: >
  Revert the change. A host set up on 443 is unchanged by it. A host set up on another port is undone by
  hand as VELDO-0171's rollback says, turning Serve off for that HTTPS port only; the
  mapping on 443 was never touched. Passkeys enrolled for the port origin must be enrolled again after a
  move to another origin.
---

## Intent

The owner runs Veldo's factory on a host whose tailnet HTTPS root already serves another app (here
travelbot, proxied to port 8002), and that app stays. Veldo takes its own HTTPS port, chosen at setup (8443
on this host), and its origin is https://<name>:<port> wherever it is recorded or checked. Owner decision,
Telegram 39047 (2026-11-04); background in the cutover research, gap 1.

## Context

- control_factory_setup_api.py fixes HTTPS_PORT = 443 (line 76); serve_state checks only <name>:443 and
  refuses an occupied root (lines 163 to 176); service_config, process_config and the setup report write
  'https://' + name as origin and name as host and rp_id (lines 281, 291, and control_factory_setup.py
  line 1134).
- control_api.py refuses any Host but the configured host and any write whose Origin is not the configured
  origin; control_api_webauthn checks clientData origin against the configured origin and the rp id hash
  against sha256(rp_id). WebAuthn's relying party id is a registrable domain, never a port, so the bare
  tailnet name stays valid on any port; only origin and host change.
- Tailscale Serve offers HTTPS on 443, 8443 and 10000, and keeps each port's mapping separate.

## Out of scope

Moving the other app's mapping, Funnel, ports other than the three Serve offers, and changing the origin of
an installation already set up (that is a new setup).

## What the reviewer judges

- Normal use: the owner runs `veldo factory setup` with the port option on a host whose 443 is taken.
- Threat model: as VELDO-0171; the other app on 443 is a neighbor, not an attacker, and is never written.

## History

- 2026-11-04: drafted from the owner's decision (Telegram 39047) on the factory cutover research, gap 1.
  Not implemented; the owner approves it before it is claimed.

2026-11-04: approved by the owner, Telegram 39065 ("Yes approve all four"), with VELDO-0232, VELDO-0234, VELDO-0235 and core VELDO-3340. Status ready.

2026-11-04: footprint widened by the lead after the independent review (proof/VELDO-0235/review-2026-11-04.md):
scripts/gate_unconfined.json, a protected path, for suite 127's entry (it drives the systemd user manager,
the same reason as suite 117's entry). Needs the owner's approval at landing. Acceptance criteria unchanged.

2026-11-04: plan consistency review (veldo-plan-consistency-review-2026-11-04.md) and the lead's rulings
(veldo-plan-rulings-2026-11-04.md), owner request Telegram 39145. Built, gate queued, so the criteria and the
code are unchanged here and each change goes to a follow-up ticket: VELDO-0253 makes the HTTPS port
installation configuration (finding A19, ruling R1): setup writes the port into the installation
repository's first commit, a later port change is a commit the loader handles as a widening, and the
holds_https_port refusal and the state-root option give way to it. VELDO-0250 removes the personal setup
(B2, B8): the other app's name and port and this host's port in Intent, the fixture's
occupied-root mapping and suite 127 lines 11 and 79 become a generic occupied port, the cutover
research reference and the message ids outside History go, and README line 3 follows. Dispositions: proof/VELDO-0236/review-dispositions-2026-11-04.md on the veldo-parity-a branch.
