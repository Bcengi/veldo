---
schema: veldo.spec/v1
id: VELDO-0306
title: "Docker objects: label, snapshot, events, removal"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_docker.py"
  - ".veldo/control_space_docker.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "scripts/suites/*_veldo_0306_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0306-docker-objects-label-snapshot-events-removal.md"
  - "specs/index.md"
  - "proof/VELDO-0306/**"
behavior_bearing: true
observability:
  logs: >
    Each object found is an item record or a report, with its engine context, object id and name. Each
    engine event handled is one ledger write or one report.
  error_taxonomy: >
    A volume a container of another run still uses is deferred by the engine's own refusal,
    space_deferred:remove_refused. End of file on an engine's event pipe is not an error: the adapter
    takes a new snapshot and subscribes again.
acceptance_criteria:
  - id: AC1
    text: >
      An object carrying the run's label or compose project name is an item owned by that run, on the
      context it was created on
    falsified_by: >
      Read one context only; the object on the second context has no item and fails
  - id: AC2
    text: >
      An object with no label, no compose project name of a run and no path inside a recorded worktree is
      a report, is never an item, and is never removed
    falsified_by: >
      Attribute it to the only live run; the row with two live runs gives it an owner and fails
  - id: AC3
    text: >
      At run finished the run's containers are stopped and removed, then its networks and volumes, each by
      the engine's non-forced remove; a volume a container of another run still uses is deferred
    falsified_by: >
      Remove volumes first; the engine refuses, the item is deferred, and the row that expects it gone
      fails
  - id: AC4
    text: >
      The engine's event stream is a pipe in the service loop's poll set: an engine event is handled with
      the fixture clock stopped, and end of file on the pipe causes a new snapshot before a new
      subscription
    falsified_by: >
      Read the stream on an interval; with the clock stopped the row's event is never handled and the row
      fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Docker objects are neither recorded nor removed by Veldo.
---

## Intent

A run's containers, networks and volumes are owned through the run's label or its compose project name.
This ticket adds the Docker adapter: the snapshot per engine context, the event stream read as a pipe in
the service loop's poll set, and removal at run finished in the order containers, networks, volumes. An
object nobody can attribute is reported and never removed.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.4 (Docker) and 5 (the container,
network and volume rows). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Docker adapter, Authority service (the poll set). Rows run against a stand-in engine; one
> integration row runs against a real one with objects the row itself creates.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: from the third review of VELDO-0300 (review3-veldo-0300.md, finding E), under the owner's
  rule that no work is ever lost. No acceptance criterion changed. The removers remove a Docker object
  only when its item's locator holds the identity seen when the object was made, so the adapter records
  it: the run's label is the engine label veldo.space.run (control_space_remove.RUN_LABEL), applied at
  creation to every object Veldo itself creates and passed on to a project's scripts; each item's
  locator gets run_label when the object carries it, created_at for a volume (the engine's CreatedAt,
  from the create event or the snapshot), and id (for an image tag, the image Id the tag named when it
  was built). An item recorded without them is never removed: it waits as remove_refused.
- 2026-11-14: built. No acceptance criterion changed. What the build found and decided:
  - The footprint grew by two files and their synced copies: control_space_signal.py (rule 1) and
    control_space_probe.py (located). The reason is AC3. Rule 1 as built knew a Docker object by its
    engine Id alone, and an engine gives a volume no Id, so every volume was deferred as not_in_ledger
    and none could go at run finished (the note in VELDO-0301's History says so). located now also
    returns the engine's CreatedAt, and rule 1 passes a volume whose locator holds created_at when the
    engine shows a volume made at that time; another time is a volume made again and is not_in_ledger,
    and a volume recorded with neither id nor created_at is not proven by its name, as before. No other
    kind is read differently. This is the lead's to confirm: neither file is a protected path.
  - The adapter (control_space_docker.py) removes nothing and has no way to: it gives an engine ls,
    inspect and events only. Removal at run finished is Signal's, in the kind registry's order, through
    the safety rules and the removers of VELDO-0300, so the falsifier of AC3 (volumes first) is applied
    to the registry's order, where the order is.
  - A run is known by the items it owns that are neither removed nor gone, and by what the adapter's
    caller names. Its space label is the id the ledger records it under, and its compose project name
    is derived from the label with a part of the label's digest (compose_project). Putting the two in
    a run's environment is the receiver's and is not in this ticket; `given` says what they are.
  - An object is recorded by the ledger's adopt, with the rule that proved its owner (run_label or
    compose_project). An object the engine shows without its Id, or a volume without its CreatedAt, is
    a report and never an item. A label that names no known run, and a label and a compose name of two
    different runs, are reports as well. The engine's own networks (bridge, host, none) are not
    recorded.
  - Images are not read here (VELDO-0328). The service has no space ledger of its own yet, so nothing
    in this repository sets Service.space_docker: the pipes are in the poll set from the moment the
    ticket that builds the ledger for the service sets it.
  - A broken engine is not asked without end: a context whose snapshot cannot be read after its stream
    ended, or whose stream ended twice in a row without a byte, has no subscription until start() is
    called again. No timer does that.
  - Seen and left alone, outside this ticket: control_space_probe.located reads "no such" as the
    engine's answer that an object is absent. A real engine says "network <name> not found" for a
    network, so a network removed by hand is deferred as not_in_ledger and never marked gone by
    Signal (safe, and the adapter's destroy event marks it gone); and a client that cannot reach the
    engine can say "no such file", which the adapter does not take for an answer (absent).
- 2026-11-14: fixed from the review of this build (review-veldo-0306.md, verdict FIX, findings 1 to 5),
  under the owner's rule that no work is ever lost and that the host's real data is never touched. No
  acceptance criterion changed.
  - Finding 1 (high). The suite's real-engine row could reach objects of the host: it read the whole
    event stream of the engine and gave Signal the real client, and the registered mutants ran that row
    too. Three things now hold it, each on its own. The row's event client is started with the row's own
    label as a filter (control_space_docker.events_argv), and the row takes no snapshot. Signal, the
    removers and the adapter are given the row's client, which passes ls, inspect and info and, beyond
    them, only a stop or a remove of one object with no option on the row's context, when the engine
    shows under that word the very object the row created (the Id, or a volume's name and CreatedAt,
    read when the row made it); everything else is refused and reds the row. And the row never runs
    under a mutant: the mutation driver's worker says in the environment that it is running
    (VELDO_MUTATION_DRIVER), and the row also refuses when a production module was loaded from anywhere
    but .veldo or differs from its engine canon. The same procedure runs on a second stand-in engine in
    every run (review/own-row-on-a-stand-in), with a host-like unlabelled container, volume and network
    planted on it and their events in the row's stream (review/host-object-untouched): they are
    untouched, also under the mutant that gives an unlabelled object to a live run. Because a label
    filter lets no volume event through (an engine puts a volume's labels in no event), the object the
    row makes for its event is a container.
  - Finding 2. A container that mounts what the protect list covers (a volume by its name or by its
    compose project label, or a bind source at, above or beneath a protected path) is protected: the
    adapter gives it neither an item nor a report, and rule 2 reads the mounts from the engine again
    before any removal (control_space_probe.mounts). Mounts that cannot be read refuse at both points.
    VELDO-0341 still owns the protect list of Docker objects; this closes the gap from the first commit
    that records and removes containers.
  - Finding 3. Before each snapshot, at start and at end of file, the adapter asks the engine for its
    own time (system info), and the subscription after the snapshot is made with --since that time. An
    engine whose time cannot be read is down and gets no snapshot. The adapter still imports no clock.
  - Finding 4. A context that goes down is said: in the answer of start and of readable, in unread(),
    to the adapter's listener, in the service's observation log (unavailable:engine_not_read) and in
    Service.docker_unread.
  - Finding 5. Rule 1 also compares each owner label a volume's record holds with the labels the
    engine shows now (located returns them), so a volume made again in the same second without the
    label is not_in_ledger.
  - The footprint grew by scripts/check_teeth_mutations.py (the worker's one line, the cases of the
    review). Twelve cases were added and two anchors of the build's cases moved with the code.
  - Not as it should be, and said here: the four .veldo files of this fix (control_space_docker.py,
    control_service.py, control_space_probe.py, control_space_signal.py) were taken into commit
    fe486efb (VELDO-0305, review) by the run that was fixing VELDO-0305 in the same worktree at the
    same time, before their engine copies were synced. This fix's own commit holds the synced engine
    copies, the suite, the driver and the rest; between the two commits the template-sync check is red.
- 2026-11-14: fixed from the second review of this build (review2-veldo-0306.md, N1, low). No acceptance
  criterion changed.
  - The Ledger adds the snapshot store to the protect list as a path with no engine named, and the two
    mount checks (control_space_docker.mount_protected at adoption, control_space_probe.mounts at
    removal) kept only the entries that name the container's engine, path entries too. A container with
    a run's label that binds the snapshot store was adopted and could be stopped and removed. Both
    checks now read every path entry, whatever engines it names: a protected path is protected on every
    engine, as rule 2 for a path already has it. Configured path entries name every engine, so only the
    Ledger's entry changes. Volume and compose project entries are still read by engine.
  - Row rereview/snapshot-store-mount, on the stand-in engine: a labelled container that binds the
    store on one context, and one that binds a folder beneath it on the other, get neither an item nor
    a report; one recorded before it bound the store is deferred as protected at removal and asked
    nothing. Two cases: space306-rereview-store-mount-adopted and space306-rereview-store-mount-removed.
  - The suite now loads control_space_probe.py through its PRODUCTION map, so a mutant of the probe can
    run and the real-engine row's guard compares the probe with its canon too.
