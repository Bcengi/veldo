---
schema: veldo.spec/v1
id: VELDO-0185
title: Factory setup gives the installed service its engine adapters and work configuration, enrolls the authority and launch receiver as reservation services, and writes the receiver's state root, and a second run changes nothing
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W145
plan_revision: 4
depends_on: [VELDO-0139, VELDO-0154, VELDO-0160, VELDO-0167, VELDO-0170, VELDO-0171]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0185_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0185-setup-lays-down-the-dispatch-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0185/*"
behavior_bearing: true
observability:
  logs: >
    Record each dispatch step setup runs (the adapters, the work configuration, each principal's
    reservation_service enrollment, the receiver's state root) as done, already done or refused, with the
    paths it wrote and the principals it enrolled; never a key.
  metrics: >
    Count setup runs by outcome and dispatch steps by outcome.
  traces: >
    Join each dispatch step to its setup run, and the installed service's loop status to the work
    configuration it loaded.
  error_taxonomy: >
    Distinguish an existing file the run would write differently (invalid_input:state_root:differs:<path>)
    and a store write setup cannot send through the running service
    (invalid_input:state_root:service_running:<step>).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Factory setup writes the launch receiver's engine adapters and the service's work configuration
      and installs the service with both, so the installed factory loop is configured on a fresh host. Set
      and completeness: Setup writes one adapter per engine the account registry names, `claude_code` naming
      its pinned version and `codex` its vendor binary (VELDO-0186 lays both down), and passes them through
      the installer's `adapters` option; it writes the work configuration (`veldo.factory_work/v1`) naming
      the enrolled workspace's repository with the builder and reviewer roles of the default team, and passes
      it through the installer's `work` option (VELDO-0154). After setup the running service's loop status
      reads `configured` true with no refusal, and the receiver configuration names both adapters. The
      suite sets up a fresh fixture host with fake accounts of both engines. Falsifier: Install the service
      without the `work` option, and the loop-configured row must fail on `configured` false.
    falsified_by: >
      Install the service without the `work` option, and the loop-configured row must fail on `configured`
      false.
  - id: AC2
    text: >
      Claim: Setup enrolls the `authority` and `launch-receiver` principals with the `reservation_service`
      role by the owner's signed command, and writes the receiver configuration with its `state_root`. Set
      and completeness: Each enrollment is the owner's signed `enroll_principal` command with the role, sent
      under VELDO-0171 AC1's lock rule, as setup enrolls its other principals, and the account pool and
      reservation service (VELDO-0160, VELDO-0036) accept both principals' usage observations and
      reservations. The receiver configuration's `state_root` is the setup's state root, so the execution
      records, runs and pinned engines resolve under it (control_execution_record `directory`, control_launch
      `bind`). The suite reserves an account slot as each principal and launches through the installed
      receiver. Falsifier: Enroll both principals without the role, and the reservation row must fail on the
      reservation service's refusal.
    falsified_by: >
      Enroll both principals without the role, and the reservation row must fail on the reservation
      service's refusal.
  - id: AC3
    text: >
      Claim: Running setup again with the same arguments changes nothing, and on a host laid down before this
      change it adds only these steps. Set and completeness: Each step follows VELDO-0171 AC4's re-run rule: a
      file equal to what it would write is left alone, an absent one is written, the receiver configuration
      gains its `state_root` key only where it lacks it or holds it as null, any other differing file is
      refused by name (invalid_input:state_root:differs:<path>), and an enrollment already in the journal is
      not sent again. After a second run over a complete host, every file under the state root, install root
      and unit directory is byte for byte the same and the journal head is unchanged. Over a host set up by
      VELDO-0139 and VELDO-0171 alone, only these steps write. Falsifier: Send both enrollments on every run,
      and the second-run row must fail on the changed journal head.
    falsified_by: >
      Send both enrollments on every run, and the second-run row must fail on the changed journal head.
required_evidence: [unit, integration]
rollback: >
  Reinstall the service without the work configuration, so the loop stops offering work, and revoke the two
  role grants with the owner's signed commands; accepted records are unchanged. No automatic rollback is
  authorized.
---

## Intent

After setup, the factory the owner installed on a fresh host starts work on its own: the service knows
its engines and its work, and the services that reserve account slots are allowed to.

## Context

W145 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The VELDO-0154
review on 2026-09-27 found that a factory set up on a fresh host dispatches nothing, which blocks the
owner's first use on October 1: setup passes no `adapters` and no `work` configuration to the service
(VELDO-0154 added the installer's `work` option), never enrolls the `authority` and `launch-receiver`
principals with the `reservation_service` role, and writes a receiver configuration with no `state_root`.
The installed runtime assets and pinned engines are VELDO-0186. The re-run is VELDO-0171's one upgrade
path. VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan graph. A draft:
only the owner marks it ready.

## Out of scope

The runtime assets, qualification records and pinned engines (VELDO-0186); replacing installed engine
files after an update (Release 2, VELDO-0139's Notes); the Mac relay's receiver (VELDO-0125).

## What the reviewer judges

- Normal use: the owner runs setup on a fresh host with his accounts registered, starts the service as
  setup tells him, and the loop reports itself configured; later he runs setup again and nothing changes.
- Threat model: a service installed with no work configuration, so nothing runs and nothing says why; a
  principal reserving slots without the role, or given the role without the owner's signed command; a
  receiver whose records and pins resolve outside the state root; a re-run that enrolls twice or rewrites
  a file.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as setup
  interrupted between two dispatch steps (running it again finishes it); forged rows in our own store.

## Notes

The work configuration names roles, not accounts: the account pool (VELDO-0160) picks the account per run,
so an account registered later takes work with nothing reinstalled.

## History

2026-09-27: new draft for the VELDO-0154 review finding of 2026-09-27 that a factory set up on a fresh host
dispatches nothing. Only the owner marks a specification ready.
