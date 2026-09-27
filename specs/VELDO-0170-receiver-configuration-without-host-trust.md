---
schema: veldo.spec/v1
id: VELDO-0170
title: A launch receiver configuration that names no host trust stops by name, and factory setup upgrades it
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W130
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0069, VELDO-0139]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0170_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0170-receiver-configuration-without-host-trust.md"
  - "specs/index.md"
  - "proof/VELDO-0170/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch refused for a configuration with no host trust, with the configuration's path and
    repository, and each upgrade with the configurations rewritten and left as they were; never a key.
  metrics: >
    Count launches refused for a missing host trust, and receiver configurations upgraded and already
    current.
  traces: >
    Join each refusal to its dispatch and receiver configuration, and each upgrade to the installation
    and host trust file it read.
  error_taxonomy: >
    Distinguish a configuration that names no host trust (host_trust_required:receiver_configuration)
    from a named trust that is absent or unreadable (host_trust_unreadable) and from an unsigned
    decision; an upgrade that finds no installed trust is refused by name with nothing written.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A launch under a receiver configuration that names no host trust is refused by one name
      before anything is spawned, never as an unsigned decision. Set and completeness: The receiver
      (control_launch.Receiver) checks for the `host_trust` key when it accepts a dispatch, for every unit,
      governed or not; a configuration without it refuses host_trust_required:receiver_configuration, and
      the service's status names each installed receiver configuration without it, with the upgrade
      command to run. Take a receiver configuration as the installer wrote it before the host trust fix
      (no `host_trust` key) and launch a governed unit and an ungoverned one: both are refused by that
      name. Falsifier: Treat a configuration with no host trust as trusting no settlement, as today, and
      the governed-unit row must fail on unsigned_decision.
    falsified_by: >
      Treat a configuration with no host trust as trusting no settlement, as today, and the governed-unit
      row must fail on unsigned_decision.
  - id: AC2
    text: >
      Claim: Factory setup upgrades an installation whose receiver configurations name no host trust,
      changing nothing else. Set and completeness: `veldo factory upgrade` reads the installed service
      configuration and, for each receiver configuration it lists, adds `host_trust` naming the host's
      installed trust file: the one the installation's channel ingress configuration names, else the
      default location (control_eligibility.host_trust_path), which must load and whose host identity
      must equal the installed service's. It replaces the file whole at 0600; a configuration that
      already names a trust is left byte for byte. Nothing else in any file changes, and the upgrade is
      refused by name, writing nothing, when no installed trust loads.
      Upgrade an installation with one old and one current receiver configuration, then launch a governed
      unit under each: both are decided by the settlement signers. Falsifier: Rewrite the configuration
      without the `host_trust` key, and the launch-after-upgrade row must fail.
    falsified_by: >
      Rewrite the configuration without the `host_trust` key, and the launch-after-upgrade row must fail.
required_evidence: [unit, integration]
rollback: >
  Restore the receiver configurations from before the upgrade by hand; launches under them are refused by
  name until they are upgraded again. No automatic rollback is authorized.
---

## Intent

A factory installed before the host trust fix tells the owner exactly what is wrong and how to fix it,
instead of quietly refusing every decision-governed unit.

## Context

W130 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3. The Codex
whole-project review of 2026-09-26 found that the launch receiver built its eligibility Gate without the
settlement signers, so work the front door had cleared was refused unsigned_decision at launch; the fix
landed on main at a4769f68 and the installer now writes `host_trust` into each receiver configuration.
Its review (rvfix0926) filed that a configuration written before the fix has no `host_trust`, and the
receiver reads that as trusting no settlement: every governed unit is refused as unsigned, with no stop
that names the cause and no path to fix it but reinstalling. VELDO-0139 is a standalone built item, so its
edge is kept here and not in the plan graph. This new specification is draft; authoring it supplies
neither implementation proof nor operational activation.

## Out of scope

Checking that the host trust path lies outside places a worker can write (filed for Release 2);
upgrading any other configuration key; migrating the store.

## What the reviewer judges

- Normal use: the owner's factory was installed before the fix; after updating Veldo he starts it, sees
  the named stop in the service status, runs the upgrade once, and governed work launches again.
- Threat model: an old configuration silently refusing governed units; an upgrade that changes anything
  but the missing key, or that points a receiver at a trust file the service was not installed with. The
  owner's account, the installed service and its trust file are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as an
  upgrade interrupted between two configurations (running it again finishes it); configuration files
  planted in the installed directory; hosts with several installations.

## Notes

The upgrade reads the trust path from the installation, never from a flag, and checks its host identity
against the installed service's, so it cannot point a receiver at another host's trust. It needs no
restart: the receiver reads its configuration at each launch.

## History

2026-09-27: new draft from the review rvfix0926 of the Codex-review fixes landed at a4769f68 (item f of
its filed list). A draft: only the owner marks a specification ready.
