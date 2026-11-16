---
schema: veldo.spec/v1
id: VELDO-0323
title: "Hook events: the event record, the consumer and the space worker"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301, VELDO-0311]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_consumer.py"
  - ".veldo/control_space_consumer.py"
  - "engine/.veldo/control_space_worker.py"
  - ".veldo/control_space_worker.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0323_*.py"
  - "scripts/suites/133_veldo_0326_space_principals.py"
  - "scripts/suites/148_veldo_0311_git_hooks.py"
  - "scripts/suites/151_veldo_0313_space_run.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0323-hook-events-the-event-record-the-consumer-and-the-space-worker.md"
  - "specs/index.md"
  - "proof/VELDO-0323/**"
behavior_bearing: true
observability:
  logs: >
    Each event record goes from received to consumed once, with the items it made due, or none.
  traces: >
    A removal joins the event record, the hook that sent it and the worker that carried it out.
  error_taxonomy: >
    A record already consumed is refused by the consumed command and does nothing. A ref changed record
    whose new commit no longer exists contains nothing.
acceptance_criteria:
  - id: AC1
    text: >
      A ref changed record for the trunk or a declared landing ref is consumed on the journal advance that
      wrote it: with the fixture clock stopped, the worktree of a recorded branch that moved past its
      start commit and that the recorded new commit contains is removed, build output first, and its
      branch is kept and marked contained
    falsified_by: >
      Consume on an interval; with the clock stopped the worktree stays and the row fails
  - id: AC2
    text: >
      The containment tests and the removal both run in the space worker, a child process whose pipe is in
      the service's poll set: the service process runs no git command for an event record, and while a
      remover is held on a fixture latch the service answers another packet
    falsified_by: >
      Compute containment in the consumer; the row that counts git calls made by the service process for a
      repository with a hundred recorded branches finds a hundred and fails
  - id: AC3
    text: >
      Records are consumed oldest first, one worker at a time, each exactly once; spooled records are
      consumed at service start before reconcile
    falsified_by: >
      Consume without marking; after a restart the row counts two Signal calls for one record and fails
  - id: AC4
    text: >
      A session ended record removes that session's scratch. A session started record removes the scratch
      of every session recorded on the host whose recorded process is gone, in any project and in none,
      and leaves a session whose process is alive, however old
    falsified_by: >
      Look only at sessions of the same project; the crashed no-project session's scratch stays and the
      row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Event records stay in state received and nothing follows a hook's event; the hooks
  still record.
---

## Intent

A hook can only record. What its record ends is worked out and removed by the authority service, as soon
as the record is written and with no clock involved. The consumer hands the oldest record to the space
worker, a child process whose pipe is in the service's poll set, so the service keeps answering while a
large folder is deleted.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 4.5 (event record), 6.9 (the event
consumer), 8.4 (a landing by hand), 8.7 (a lead session) and 3 (the event consumer and the space worker).
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: Ledger (event, consumed), Event consumer, Space worker, Authority service. Depends on 0301
> and 0311.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). depends_on holds the dependencies the
design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-15: VELDO-0315 now owns the service bootstrap: synchronous replay and start reconcile, then the consumer and its received-event reconcile hook. Shutdown stops the consumer. Its standalone consumer rows use space_worker_start; the real serve order is exercised by 0315.

- 2026-11-15, fix round 2, the lead's decisions on the two points the first fix round left open.
  (1) A client that has ended and that its parent has not collected (state Z) has exited. The worker
  reads the state from the client's stat together with the recorded start time, so a reused number
  is another process, and requires that no task of it still runs. For a session ended event Signal
  and the removers read rule 4 with that one fact added: such a client is not an unread process
  that could hold a path. The scratch is removed when the kernel reports the end and does not wait
  for the parent or for the next session. Every other process is judged as before. (2) The store
  connections the service's channel and API hold are in the list the worker child closes: the child
  holds only what it needs. A descriptor handed down to the service still stays open. Rows
  ac4/exited-before-collected and ac2/channel-and-api-closed, three mutations. No acceptance
  criterion changes.

- 2026-11-15, fix round after the review (verdict FIX, no loss path found). (1) The worker child
  closes only what the service holds (its lock, listeners, pipes and store, named by the service) and
  never every inherited descriptor, so a descriptor handed down to the service stays open and the
  teeth stage can measure this ticket. (2) AC2's row counts every git process the service process
  starts, wherever it is started from. AC3 has a row for the order of three records received
  together, and rows for a second consumer on the same store while the first one's child is held: its
  child waits for the lock and reads again under it. (3) Lead decision on AC4: a session ended record
  that arrives while its client is alive is not dropped. The scratch is selected, rule 3 leaves it
  deferred as in_use, and the record's result names it as held. The consumer holds that client by a
  process descriptor in the service's poll set; when the kernel reports the client ended, one more
  session ended record is written for the same session and consumed like any other. Nothing polls. A
  scratch whose process cannot be read is still not selected, and the result says so. A service that
  starts again holds the clients of the scratch left deferred that way. Seven mutations are
  registered for these rows. No acceptance criterion changes. The startup bootstrap stays
  VELDO-0315 AC7 and is not built here.

- 2026-11-15: build footprint includes init_scaffold and its synced copy so the installed service
  carries the consumer, worker and their existing spool and kind-registry dependencies. The event
  record accepts released but this ticket removes nothing for it; VELDO-0335 supplies that behavior.
  The three earlier suites' unbuilt-event expectations now name the installed command's validation
  refusals, or explicitly simulate an older service. No acceptance criterion changes. The CLI's
  incomplete session/verb envelope is still refused; wiring that creator is outside this ticket.

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
