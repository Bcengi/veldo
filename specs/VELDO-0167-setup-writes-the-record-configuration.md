---
schema: veldo.spec/v1
id: VELDO-0167
title: Factory setup writes the execution record's configuration, and a launch receiver hints every API that subscribed to the running service
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W127
plan_revision: 4
depends_on: [VELDO-0130, VELDO-0139, VELDO-0141]
placement: [engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service_api*.py"
  - ".veldo/control_service_api*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0167_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0167-setup-writes-the-record-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0167/*"
behavior_bearing: true
observability:
  logs: >
    Record the records directory and the subscriber registry setup names, and each hint pass with the
    number of subscribers read and hinted; never a record line.
  metrics: >
    Count hints sent and dropped per run, and subscribers read from the registry.
  traces: >
    Join each hint to its dispatch, the record sequence it names and the registry version it was read
    from.
  error_taxonomy: >
    Distinguish an unreadable subscriber registry (no hint sent, the record still kept) from a subscriber
    whose socket is gone (dropped, counted) and an API with no records directory
    (unavailable_service:records).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: On a host factory setup laid down, a run's execution record is served through the installed
      API. Set and completeness: Setup creates one records directory under the state root (0700), writes
      it as the `records` key of every launch receiver configuration and of the API service
      configuration (veldo.api_service/v1) it writes for this authority on the Telegram ingress's api
      edge, and installs that configuration with the service (VELDO-0047's api_service option), so the
      receiver and the API name the same directory. Set up a host, launch a fake-engine run through the
      installed receiver, and read its record through the installed API's record route (VELDO-0141): the
      lines are served. Falsifier: Leave `records` out of the API service configuration setup writes, and
      the installed-record row must fail with unavailable_service:records.
    falsified_by: >
      Leave `records` out of the API service configuration setup writes, and the installed-record row must
      fail with unavailable_service:records.
  - id: AC2
    text: >
      Claim: A launch receiver hints every API process that has subscribed to the running authority
      service, including one that subscribed after setup and after the receiver started. Set and
      completeness: Setup writes, in place of a fixed `record_hints` list, the path of the installed
      service's subscriber registry (VELDO-0130's api-subscribers.json in its state directory) into every
      receiver configuration; the receiver reads the registry at each hint and hints each listed
      subscriber, counting one whose socket is gone as dropped. With a run in progress, subscribe a second
      API process: its next hint names that run. Falsifier: Have setup write a fixed `record_hints` list of
      the subscribers known at setup, and the late-subscriber row must fail.
    falsified_by: >
      Have setup write a fixed `record_hints` list of the subscribers known at setup, and the
      late-subscriber row must fail.
required_evidence: [unit, integration]
rollback: >
  Remove the records keys and the registry path from the configurations setup wrote; runs keep their
  records under the state root's default directory and the UI's live view stops updating. No automatic
  rollback is authorized.
---

## Intent

The owner's live terminal view (VELDO-0145) works on a factory laid down by setup, with no hand-edited
configuration, and keeps working when the API process restarts or a second one starts.

## Context

W127 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0141 added
two configuration keys, the receivers' `record_hints` and the API service's `records`, and its build
recorded that factory setup (VELDO-0139) writes neither. VELDO-0145's live terminal reads through them, so
this lands before it. A fixed hint list in each receiver configuration goes stale the first time an API
process restarts on a new socket; the service already keeps the list of API processes that subscribed to
it, so the receivers read that list. VELDO-0139 is a standalone built item, so its edge is kept here and
not in the plan graph. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation.

## Out of scope

Enrolling the api edge's key and starting the API process on the host (filed in VELDO-0139 for the API's
own setup); upgrading a host set up before this change, which is set up again; the record's content and
redaction (VELDO-0141).

## What the reviewer judges

- Normal use: the owner runs factory setup, starts the service, opens the UI and watches a run live; the
  API process may restart during the run.
- Threat model: a receiver and the API naming different records directories; a hint list that misses a
  live subscriber; a records directory another account can read. The owner's account and the installed
  service are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as more
  subscribers than the registry's limit; a registry file planted in the installed directory; hints lost
  while the registry is being replaced (the API reconciles on its next read).

## Notes

The registry is replaced whole by the service (control_service_api), so a receiver reading it sees
either the old or the new list, never a partial one.

## History

2026-09-27: new draft from VELDO-0141's build and its review rv141, which filed that the record hints
must be wired before VELDO-0145, preferably through the subscriber registry. A draft: only the owner marks
a specification ready.
