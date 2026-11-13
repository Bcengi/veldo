---
schema: veldo.spec/v1
id: VELDO-0326
title: "Host principals for space commands"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0297]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_factory_setup.py"
  - ".veldo/control_factory_setup.py"
  - "scripts/suites/*_veldo_0326_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0326-host-principals-for-space-commands.md"
  - "specs/index.md"
  - "proof/VELDO-0326/**"
behavior_bearing: true
observability:
  logs: >
    Each ledger command records the principal that signed it. A refused command is logged with the
    principal and the command's name.
  error_taxonomy: >
    A command a host principal may not sign is refused by the command's name. Every owner action is
    refused from both host principals. A signed packet past its age bound is space_packet_expired, one
    issued ahead of the clock space_packet_ahead, and a nonce the store has a record of
    space_packet_replayed.
acceptance_criteria:
  - id: AC1
    text: >
      Installing the service makes the keys of space-observer and space-runner and enrolls both; a hook's
      command signed as space-observer is accepted without the owner's key being readable by the hook
    falsified_by: >
      Sign hook commands with the owner's key; the row that runs the hook with the owner's key unreadable
      finds no record and fails
  - id: AC2
    text: >
      space-observer may sign declare and confirm for a worktree, a branch and session scratch, rebranch,
      event and the read behind covers, and is refused every other ledger command by name
    falsified_by: >
      Accept signal from space-observer; the row that sends it gets items marked due and fails
  - id: AC3
    text: >
      space-runner may also sign measure, hold, admit, release, signal and outcome, only for the run or
      gate the authority issued to it: the identity is made by the Ledger with a part nobody can
      predict and bound to the principal by the authority's own issue record, and who names a run first
      decides nothing
    falsified_by: >
      Let it signal for any owner; the row that signals for another run's items gets them due and fails.
      Read a run nobody issued as the runner's; the row that holds a dispatch identity before the
      authority names it, then signals run finished for the items the authority declares there, gets
      the hold accepted and the items due and fails
  - id: AC4
    text: >
      Adopt, Abandon, Confirm, Reconcile, marking a proposal wrong, the mode switch, a protect list change
      and an answer to a space disposition request are refused from both host principals
    falsified_by: >
      Accept Abandon from space-runner; the row that sends it finds the worktree due and fails
  - id: AC5
    text: >
      A signed packet carries the time it was issued and a nonce. The Ledger refuses a packet issued more
      than 300 seconds (five minutes) before its own clock, and one more than 60 seconds ahead of it; it
      keeps a record of every nonce it has seen and refuses a nonce it has a record of, so a refused
      packet is never accepted later; the same packet sent again after it was accepted is answered with
      the original answer and writes nothing, never command_content_conflict
    falsified_by: >
      Drop the age test; the row that delivers a packet 30 days after it was signed finds the hold
      admitted and fails. Keep no record of a refused packet; the row that sends it again after the hold
      was placed finds it admitted and fails. Answer no retry from the record; the row that sends an
      accepted packet twice is refused and fails
  - id: AC6
    text: >
      Factory setup enrolls both host principals or leaves neither enrolled; its cleanup never deletes a
      key the store has a record of; the next run repairs a half state an earlier run left; a keys folder
      that is already there must be a real folder of this account that nobody else can enter; setup driven
      in-process never writes the installation folder the environment names; and the refusal of a re-run
      while the service runs names the steps that fix it
    falsified_by: >
      Leave the first enrollment when the second fails; the row finds space-observer enrolled alone and
      fails. Delete every key the failed run made; the row finds the key of the principal the store holds
      gone and fails. Enroll only what the store has no record of; the row that runs setup after a half
      state finds one principal still missing and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The two keys stay in the installation folder, and commands signed with them are
  refused.
---

## Intent

A git hook and a gate helper must be able to write to the ledger without holding the owner's key. This
ticket adds two host principals, space-observer and space-runner, each with its own key made at install,
and the Ledger's rule for what each may sign.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.11 (who signs a space command).
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: Host principals, Ledger, CLI. Depends on 0297.

Build order. It is one of the first five tickets, built in the order 0296, 0338, 0297, 0326, 0331.
depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: footprint extended to control_factory_setup.py and its engine copy, by the lead's decision.
  The installer made and enrolled the two keys only when it was handed the installation folder and the
  owner's enrollment, and veldo factory setup handed it neither, so on a real factory neither principal
  was ever enrolled and every space command was refused. Setup now takes the installation folder its
  reader resolved, has the installer make both keys there, and enrolls both through the owner's signed
  enroll_principal on its own connection; a re-run over a factory laid down before enrolls the ones the
  store does not hold, only while the service is stopped. With no installation folder no key is made and
  the answer names the step deferred. Acceptance criteria and falsifiers are unchanged; suite 133 gains
  two rows that run factory setup on the fixture and sign a command as each principal. Known and left
  for the lead: the setup suites that call the command surface resolve the installation folder from the
  ambient environment, so on a host that has one they would make the two keys there.
- 2026-11-13: amended from the independent review (verdict FIX), by the lead's three decisions. The
  acceptance criteria are no longer the design's word for word: AC3 is reworded, AC5 and AC6 are new.
  (1) Run ownership. A run or gate is the runner's only when the authority issued it: the new ledger
  command space_issue, which no host principal signs, makes the identity (a label, then a part nobody
  can predict) and writes the record space:run:<identity> naming the principal. The rule reads that
  record; the journal's first-to-name test is gone. The review's take-over (the runner holds a dispatch
  identity first, then signals its run finished) is a refused row, and an item space-observer declares
  into a run makes nobody its owner. Consequence for later tickets: the gate helper and the run wrapper
  must get their identity from the authority before their first hold; how they ask is the ticket that
  routes space packets in the service.
  (2) Packets expire (AC5). The bound is PACKET_AGE, 300 seconds, with 60 seconds allowed ahead of the
  clock. Each verified packet inside the bound leaves the record space:packet:<principal>:<nonce>; an
  accepted command writes it in its own transaction and the store consumes the packet's nonce. The
  record is kept, so a nonce is refused for good, not only inside the bound. Consequence for
  VELDO-0313: a spooled packet older than five minutes is refused, so the spool signs again when it
  replays; it never sends the old bytes.
  (3) Setup (AC6). The store commits each enrollment on its own and its journal only grows, so both or
  neither is kept this way: every key is read and proven to sign before the first enrollment, and when
  one fails after another committed, the committed one is taken back by the owner's signed
  revoke_membership. Neither is then an enrolled member; the journal keeps the enrollment and its
  revocation. Cleanup takes back only a key whose principal the store has no record of. A re-run enrolls
  what the store lacks, a principal whose membership was revoked, and a principal the store holds whose
  key file is gone (revoked, a new key made, enrolled again). keys/ is refused when it is a link, a
  file, another account's, or open to group or others. Setup's command surface takes --installation;
  driven in-process (every suite) it makes keys only in a folder it is told, never the one the
  environment names, which closes the item left for the lead above. The service_running refusal names
  the three steps. Footprint unchanged.
