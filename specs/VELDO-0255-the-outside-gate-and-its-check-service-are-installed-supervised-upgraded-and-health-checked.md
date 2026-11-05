---
schema: veldo.spec/v1
id: VELDO-0255
title: Setup installs the outside gate and its check service as supervised user services started with the authority, on ports from the installation, the service reports their health, and a gate upgrade goes live only after the new binary loads the configuration in force
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0251, VELDO-0252, VELDO-0253, VELDO-0254]
placement: [engine, distribution]
protected_paths: [".veldo/pins/gate.json", "engine/.veldo/pins/gate.json"]
footprint:
  - ".veldo/gate_binary.py"
  - "engine/.veldo/gate_binary.py"
  - ".veldo/gate_supervision.py"
  - "engine/.veldo/gate_supervision.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_launch*.py"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0255_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0255-the-outside-gate-and-its-check-service-are-installed-supervised-upgraded-and-health-checked.md"
  - "specs/index.md"
  - "proof/VELDO-0255/**"
behavior_bearing: true
observability:
  logs: >
    Setup writes one line per unit it installs or leaves unchanged (unit name, binary path, version,
    listen address) and one line per host prerequisite it checked. The service writes one line per health
    change of the gate or the check service (healthy, unhealthy with the probe that failed, restarted with
    its restart count) and one line per upgrade step (asset verified, check instance load result, switch,
    previous binary kept), never a credential value.
  metrics: >
    Gate and check service up or down; restarts per unit; health probe latency; launches refused because
    the gate was unhealthy; upgrades by outcome.
  traces: >
    Each health change and each upgrade carries the gate version, the pin file digest and the accepted
    installation commit whose ports and configuration were in force; a refused launch carries its dispatch
    id.
  error_taxonomy: >
    prerequisite_missing:<name> (a host prerequisite of the gate is absent; the message names the command
    the owner runs), unit_install_failed:<unit>, port_not_declared:<unit>, gate_unavailable (a launch that
    selects an outside service while the gate or its check service is unhealthy, refused before the engine
    starts), upgrade_rejected:<reason> (the new binary failed verification or its check instance refused
    the configuration in force; the previous binary keeps serving). The pin refusals of VELDO-0252 keep
    their names.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the gate and its check service run as supervised user services that start and stop with the
      authority, restart on failure and listen only where the installation says. Set: setup installs one
      user unit for the gate and one for the check service beside the authority's unit (the way
      control_service installs the API), each started with the authority, stopped with it, restarted on
      failure with a bounded backoff, and started only after VELDO-0252's pin and version checks pass; each
      listen address and port is read from the installation's ports kind (VELDO-0253) and an absent one
      refuses setup as port_not_declared:<unit>. The relay stays per dispatch in the launcher (VELDO-0251,
      VELDO-0254). A second setup run with the same values changes nothing. Rows: setup creates both units
      with the declared ports; stopping the authority stops both; killing the gate's process restarts it;
      a second setup run leaves the unit files byte for byte unchanged.
    falsified_by: >
      Start the gate as a detached child of setup instead of a unit; the killed-gate row finds no gate
      listening and fails.
  - id: AC2
    text: >
      Claim: the service knows whether the gate and the check service are healthy, tells the owner once per
      change, and does not start a run that would fail on an unhealthy gate. Set: the service probes the
      gate's readiness and reported version and the check service's readiness on each start and on each
      unit state change notification (no timed polling); while either is unhealthy, a launch whose dispatch
      selects an outside service is refused as gate_unavailable before the engine starts, a launch that
      selects none starts, and the owner gets one notice per health change through Veldo's own channel with
      the failing probe named. Rows: with the gate stopped, a launch that selects a fixture service is
      refused by name and one that selects none starts; stopping and restarting the gate sends exactly two
      notices; a gate reporting another version is unhealthy.
    falsified_by: >
      Launch without the health state; the stopped-gate row starts the engine and the run fails mid-turn
      on check_unavailable instead of being refused at launch.
  - id: AC3
    text: >
      Claim: a gate upgrade is a reviewed pin change that goes live only after the new binary accepts the
      configuration in force, and a failed upgrade leaves the old binary serving. Set: when the pin file
      names a new version, setup downloads and verifies the new asset as VELDO-0252 AC4 requires into its own
      versioned directory beside the old one, loads the generated configuration in force in a check instance
      of the new binary, and only when that load passes switches the gate unit to the new binary and
      restarts it; the previous binary stays installed for the rollback. A failed verification or load is
      upgrade_rejected:<reason> and the unit keeps the old binary. Rows: an upgrade to a fixture version that
      loads the configuration switches and restarts once; one whose check instance refuses the configuration
      leaves the old version serving and reports the reason; the rollback of a switched upgrade restarts the
      previous binary.
    falsified_by: >
      Replace the binary in place before the check instance load; the refused-configuration row finds no
      gate serving and fails.
  - id: AC4
    text: >
      Claim: a host missing what the gate needs is refused at setup by name, and the installation guide
      lists the prerequisites. Set: setup checks the keystore's command-line tool and a reachable keystore
      service (the gate's credentials and grants live there, VELDO-0252), and the sandbox setup of
      VELDO-0254, and refuses each missing one as prerequisite_missing:<name> with the command the owner
      runs; docs/outside-services.md lists each prerequisite and its check. Rows: setup on a fixture host
      without the keystore tool, and on one without the sandbox setup, is refused by name and installs no
      unit; the guide names each prerequisite setup checks.
    falsified_by: >
      Skip the keystore tool check; the missing-tool row installs the units and the first grant fails at use
      instead of at setup.
required_evidence: [unit, integration]
rollback: >
  Revert the change and remove the two units: the gate and the check service are no longer started, so the
  gate's fail-closed rule refuses every outside call as VELDO-0251 and VELDO-0252 describe. Installed
  binaries stay in the versioned tools directory, unused. No automatic rollback, retry or recovery is
  authorized.
---

## Intent

VELDO-0252 downloads and verifies the gate binary and checks its version at start, but nothing says how the
gate and the check service are started, kept running, told apart from a dead process, or upgraded. This
ticket makes them ordinary supervised services of an installation, so an outside call fails because a rule
refused it, never because a process quietly died.

## Context

- control_service already installs the authority and the API as user units and manages them.
- VELDO-0252 AC4 pins the gate binary, verifies its checksum and refuses a wrong version at start; its
  rollback says the service stops being started, but no criterion starts it.
- VELDO-0253 declares a ports kind in the installation repository.
- The keystore tool the check service needs may be absent on a fresh host.

## Design

Units beside the authority's, ports from the installation, health from probes triggered by start and
unit state change, one notice per change, upgrades through a check-instance load before a switch, and
prerequisite checks with the owner's command named.

## Out of scope

- The gate's routes, the classification and the check itself (VELDO-0251, VELDO-0252).
- The pin's contents and checksum verification, which stay in VELDO-0252 AC4.
- Hosting the gate on another machine.

## What the reviewer judges

- Normal use: setup on a fresh host with its prerequisites installs two units that start with the
  authority; the owner raises the pin, setup verifies and switches; the gate crashes once and is back
  within its backoff with one notice each way.
- Threat model: a gate that died unnoticed, an upgrade that would refuse the live configuration, a port
  chosen outside the installation, a missing keystore found only at the first call.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-04: new draft, Telegram 39145, from research/veldo-plan-consistency-review-2026-11-04.md (C11,
C12) and the lead's rulings research/veldo-plan-rulings-2026-11-04.md (R1 for ports in the installation,
R6 for notices through Veldo's own channel). Not absorbed by VELDO-0252, whose four criteria cover
verification and grants, not supervision. Standalone; no plan work item.
