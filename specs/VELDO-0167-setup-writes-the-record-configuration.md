---
schema: veldo.spec/v1
id: VELDO-0167
title: Factory setup writes the execution record's configuration, and a launch receiver's record hints reach every API subscribed to the running service through that service
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W127
plan_revision: 4
depends_on: [VELDO-0130, VELDO-0139, VELDO-0141, VELDO-0171]
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
  - "scripts/suites/*_veldo_0171_*.py"
  - "specs/VELDO-0167-setup-writes-the-record-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0167/*"
behavior_bearing: true
observability:
  logs: >
    Record the records directory setup names and each key a run adds or finds already there, and each
    record hint with the dispatch, the sequence it names and the number of subscribers the service
    fanned it out to; never a record line.
  metrics: >
    Count record hints the receivers sent, hints the service fanned out and dropped, and configurations
    a re-run upgraded or found current.
  traces: >
    Join each record hint to its dispatch, the record sequence it names and the service instance that
    fanned it out.
  error_taxonomy: >
    Distinguish a service that cannot be reached for a hint (no hint sent, the record still kept, the
    API reconciling on its next read) from a subscriber whose socket is gone (dropped, counted), an API
    with no records directory (unavailable_service:records), and a re-run over a configuration that
    differs in anything but the keys this step adds (invalid_input:state_root:differs:<path>).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: On a host factory setup laid down, a run's execution record is served through the installed
      API. Set and completeness: Setup creates one records directory under the state root (0700) and
      writes it as the `records` key of every launch receiver configuration and of the API service
      configuration (veldo.api_service/v1) that VELDO-0171's setup writes and installs, so the receiver
      and the API name the same directory. Set up a host, launch a fake-engine run through the installed
      receiver, and read its record through the installed API's record route (VELDO-0141): the lines are
      served. Falsifier: Leave `records` out of the API service configuration setup writes, and the
      installed-record row must fail with unavailable_service:records.
    falsified_by: >
      Leave `records` out of the API service configuration setup writes, and the installed-record row must
      fail with unavailable_service:records.
  - id: AC2
    text: >
      Claim: A launch receiver's record hint reaches every API process subscribed to the running authority
      service when it is sent, including one that subscribed after setup and after the receiver started.
      Set and completeness: The receiver sends each record hint (the dispatch and the last sequence,
      identity only) to the running authority service over the socket its configuration names, and the
      service fans it out to every API subscribed at that moment, with the per-subscriber numbering and
      instance VELDO-0130's hint already carries (control_service_api publish); the subscriber registry
      stays the service's private state and no receiver reads it. Setup writes, in place of a fixed
      `record_hints` list, the receiver hint key naming the installed service's socket into every receiver
      configuration. With a run in progress, subscribe a second API process: its next hint names that run.
      Falsifier: Have setup write a fixed `record_hints` list of the subscribers known at setup, and the
      late-subscriber row must fail.
    falsified_by: >
      Have setup write a fixed `record_hints` list of the subscribers known at setup, and the
      late-subscriber row must fail.
  - id: AC3
    text: >
      Claim: Running setup again (VELDO-0171's re-run) over a host laid down before this change adds only
      this step's keys, and a further re-run changes nothing. Set and completeness: Over a host VELDO-0171
      laid down without them, the re-run creates the records directory and adds the `records` key and the
      receiver hint key to each receiver configuration and the `records` key to the API service
      configuration, each file otherwise byte for byte as it was, and refuses by name, overwriting nothing,
      a configuration that differs in anything else, as VELDO-0171 AC4 refuses. A second re-run leaves
      every file byte for byte the same. Falsifier: Treat an existing receiver configuration as already
      done without reading its keys, and the older-host row must fail on the missing `records` key.
    falsified_by: >
      Treat an existing receiver configuration as already done without reading its keys, and the
      older-host row must fail on the missing `records` key.
required_evidence: [unit, integration]
rollback: >
  Remove the records keys and the receiver hint key from the configurations setup wrote; runs keep their
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
this lands before it. VELDO-0171 writes the API service configuration and enrolls the api edge, and this
specification adds the execution record's keys to what it laid down, so it depends on VELDO-0171. A fixed
hint list in each receiver configuration goes stale the first time an API process restarts on a new
socket. The service already keeps the list of API processes that subscribed to it and already fans its own
hint out to them after each commit, so a receiver sends its record hint to the service and the service
fans it out; the receivers never read the service's private api-subscribers.json, which would make that
file a second interface with two writers' rules. So the configuration gains no registry path. A host laid
down before this change gets the keys through VELDO-0171's re-run, the one upgrade path. VELDO-0139 is a
standalone built item, so its edge is kept here and not in the plan graph. This new specification is
draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

Writing the API service configuration, enrolling the api edge's key and starting the API process on the
host (VELDO-0171); the re-run's own rules for arguments and differing files (VELDO-0171 AC4), which AC3
follows; the record's content and redaction (VELDO-0141).

## What the reviewer judges

- Normal use: the owner runs factory setup, starts the service, opens the UI and watches a run live; the
  API process may restart during the run.
- Threat model: a receiver and the API naming different records directories; a hint that misses a live
  subscriber; a receiver reading the service's private state; a records directory another account can
  read; a re-run that rewrites more than this step's keys. The owner's account and the installed
  service are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as more
  subscribers than the service's limit; hints lost while the service restarts (the API reconciles on its
  next read, as VELDO-0130's hint channel does); a forged hint, which changes nothing because the API
  re-reads the record through its route.

## Notes

The hint wakes only: it names the dispatch and the last sequence, and the API reads the lines through
the record route, so a lost, stale or forged hint changes nothing but the moment the view updates. The
service is the one fan-out point for every hint it sends, its own and the receivers', which keeps one
subscriber list with one owner.

## History

2026-09-27: new draft from VELDO-0141's build and its review rv141, which filed that the record hints
must be wired before VELDO-0145, preferably through the subscriber registry. A draft: only the owner marks
a specification ready.

2026-09-27: amended on the independent check of this batch and the lead's decisions. The order with
VELDO-0171 is reversed: VELDO-0171 writes the API service configuration and enrolls the api edge, and
this specification depends on it and adds `records` and the receiver hint key. AC2 now sends each record
hint through the running service, which fans it out to its subscribers, in place of receivers reading the
service's private api-subscribers.json, so no registry path is written. New AC3: the re-run adds only
this step's keys to a host laid down before it and keeps VELDO-0171's changes-nothing behavior. The out of
scope text now names VELDO-0171. Still a draft.
