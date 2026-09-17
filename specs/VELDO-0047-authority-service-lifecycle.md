---
schema: veldo.spec/v1
id: VELDO-0047
title: Authority service installation, startup, stop, and absent-service behavior
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W32
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0029, VELDO-0030, VELDO-0040, VELDO-0041, VELDO-0046]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/status_server.py"
  - ".veldo/status_server.py"
  - "packs/*/.veldo/status_server.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_client*.py"
  - ".veldo/control_client*.py"
  - "packs/*/.veldo/control_client*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/services/veldo-authority*.service"
  - ".veldo/services/veldo-authority*.service"
  - "packs/*/.veldo/services/veldo-authority*.service"
  - "scripts/suites/*_veldo_0047_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0047-authority-service-lifecycle.md"
  - "specs/index.md"
  - "proof/VELDO-0047/*"
behavior_bearing: true
observability:
  logs: >
    Service diagnostics identify domain instance, fixed executable digest, configuration revision,
    recovery phase, and operations stop or failure reason.
  metrics: >
    Count startup failures, recovery restarts, stopped instances, absent-service refusals, and
    retired containment groups.
  traces: >
    Join authorized installation and activation receipt to systemd unit, lock generation, recovery
    result, socket permissions, and shutdown observations.
  error_taxonomy: >
    Distinguish unqualified host, unenrolled instance, unsafe socket permissions, recovery failed,
    restart limit reached, explicit stop, and AUTHORITY_UNAVAILABLE.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Authorized installation creates a versioned user systemd instance under an
      operations-controlled account with fixed executable, protected configuration, socket
      permissions, and constrained helper. Set: Real installation and startup on every supported
      qualified Linux profile, one service instance per domain and distinct common directory.
      Completeness: Install disposable service instances, inspect loaded unit and filesystem
      permissions, and corrupt each executable/configuration/socket binding. Activation must
      refuse absent enrollment or qualification; logout persistence is required only when
      separately established and tested. Falsifier: Start from a worker-writable executable path
      after replacing its bytes; service/executable-binding must refuse activation.
    falsified_by: >
      Start from a worker-writable executable path after replacing its bytes;
      service/executable-binding must refuse activation.
  - id: AC2
    text: >
      Claim: Unexpected exits restart only through verified recovery, repeated failures leave a
      durable stopped diagnostic, and explicit operations stop remains stopped. Set: Real systemd
      authority and runner groups across normal startup, SIGKILL, corrupted startup history,
      control-channel loss, and explicit stop. Completeness: Drive each failure, observe the
      stable leader lock and generation, and require retired old containment before new
      scheduling. Exhaust the configured finite restart limit and inspect diagnostic persistence;
      stop explicitly and prove no automatic restart after the observation window. Falsifier:
      Bypass recovery on automatic restart after SIGKILL with an unresolved running group;
      service/restart-recovery must detect premature scheduling.
    falsified_by: >
      Bypass recovery on automatic restart after SIGKILL with an unresolved running group;
      service/restart-recovery must detect premature scheduling.
  - id: AC3
    text: >
      Claim: Clients never silently start a competing authority and report service identity, last
      watermark, and the documented operations procedure when it is absent. Set: Real local CLI
      and SSH-relayed inspection, mutation, and claim clients against a stopped or unreachable
      enrolled service. Completeness: Stop the service, invoke every registered client class, and
      inspect process census, common-directory files, and Git state. Require AUTHORITY_UNAVAILABLE
      for writes, explicitly stale inspection only, and no local database or claim fallback.
      Falsifier: Auto-start an authority when a claim client finds no socket;
      service/absent-client must detect the unapproved new process.
    falsified_by: >
      Auto-start an authority when a claim client finds no socket; service/absent-client must
      detect the unapproved new process.
  - id: AC4
    text: >
      Claim: The optional status listener is read-only and validates loopback at the actual socket
      boundary even through direct API calls. Set: Real status_server.make_server and serve entry
      points with loopback, wildcard, non-loopback, and resolved-address inputs plus remote relay
      inspection. Completeness: Attempt each bind against real sockets, inspect bound addresses,
      and issue mutation requests to every exposed route. Non-loopback listening must refuse
      before accepting a connection; remote inspection uses authenticated relay and cannot widen
      the local listener. Falsifier: Trust the default host argument and call make_server directly
      with a wildcard address; service/direct-bind must detect the unsafe listener.
    falsified_by: >
      Trust the default host argument and call make_server directly with a wildcard address;
      service/direct-bind must detect the unsafe listener.
required_evidence: [unit, integration]
rollback: >
  Perform an authorized stop, retire or quarantine worker groups, preserve store and activation
  receipts, and restore the previous compatible unit without implicit schema downgrade.
---

## Intent

Install one explicitly activated authority service per domain with recoverable startup, bounded stop, and honest absence behavior.

## Context

Package B, W32 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R20, R24, R43-R44, R57, R75. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Incorrect service activation or restart could run competing authorities or leave workers alive without supervision. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Automatic host failover, a network application server, and live channel ingress are excluded.

## Notes

D3 directly blocks service installation and activation until Dmitry ratifies Linux systemd and cgroup v2. D1 and D2 are inherited from authority storage and notifications. Tests must use real systemd on a qualified host; unavailable host support is an explicit blocked qualification, not a mocked pass. Installed service and helper files require explicit distribution disposition. Source landing alone never enables a user service.

