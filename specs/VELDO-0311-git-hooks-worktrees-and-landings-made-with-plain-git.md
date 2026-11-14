---
schema: veldo.spec/v1
id: VELDO-0311
title: "Git hooks: worktrees and landings made with plain git"
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
  - "engine/hooks/post-checkout"
  - "engine/hooks/reference-transaction"
  - "engine/.veldo/control_space_spool.py"
  - ".veldo/control_space_spool.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "scripts/suites/*_veldo_0311_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0311-git-hooks-worktrees-and-landings-made-with-plain-git.md"
  - "specs/index.md"
  - "proof/VELDO-0311/**"
behavior_bearing: true
observability:
  logs: >
    Each hook call leaves one item record or one event record with the repository, the ref, the old and
    the new commit. A spooled record is one file, replayed in order.
  error_taxonomy: >
    None reaches git: the git command's result is the same with the hook, without it, and with the
    authority down.
acceptance_criteria:
  - id: AC1
    text: >
      A worktree added with plain git in a bound or plain repository has an item, with its branch, start
      commit and the owner its branch pattern gives, when the git command returns
    falsified_by: >
      Record only through the CLI's record verb; the row that uses plain git finds no item and fails
  - id: AC2
    text: >
      Switching a recorded worktree from branch X to branch Y with plain git updates the item's branch to
      Y and its start commit to Y's commit; a later landing that contains X leaves the worktree in place
    falsified_by: >
      Record at worktree add only; the row lands X after the switch, finds the worktree due, and fails
  - id: AC3
    text: >
      A committed change of the trunk or of a declared landing ref, made with plain git, leaves one event
      record with the repository, the ref, the old and the new commit, and the git command returns with
      nothing removed. The row holds every remover on a fixture latch and the git command still returns
    falsified_by: >
      Remove inside the hook; with the remover held on the latch the row finds the git command still
      waiting and fails
  - id: AC4
    text: >
      With the authority not reachable the git command's result is unchanged, the record or event is in
      the spool, and it is replayed in order at the next CLI call that reaches the authority and at
      service start before reconcile
    falsified_by: >
      Drop the event when the authority is down; after service start the row finds the worktree with no
      item and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The hooks record nothing, and a worktree made with plain git is found by reconcile.
---

## Intent

A worktree added with plain git, a branch switched in it, and a landing made by hand all happen outside
Veldo. Two git hooks record them: post-checkout records the worktree and a branch switch,
reference-transaction records a change of the trunk or of a declared landing ref. A hook records and
returns. It removes nothing, and it never fails or delays the git command; when the authority is down the
record goes to the spool.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.9 (the rows for git commands, what
each mechanism does when the authority is not reachable, and the four limits), 4.5 (event record), 4.6
(spooled event), 8.4 and 8.5. Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Git hooks, Event spool, CLI. The hooks record and return. What follows a landing event is
> VELDO-0323; installing the hooks is VELDO-0329.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: built. engine/hooks/post-checkout and engine/hooks/reference-transaction start the CLI's new
  verbs (veldo space record, veldo space event; veldo space replay delivers what is spooled), which call
  engine/.veldo/control_space_spool.py. Suite scripts/suites/148_veldo_0311_git_hooks.py, 18 rows; ten
  falsifiers registered under finding 311, the four declared ones among them, each applied once and seen
  red on its row. What the build decided, and what it leaves to other tickets:
  - Nothing here removes anything of anybody's. The hooks record and exit 0. The module runs no git
    command and has two unlinks, both of its own spool files: one after the Ledger answered that it wrote
    what the entry says, one after an entry the Ledger refused for good was written whole to
    space-spool/refused/ with the reason. An entry is never dropped silently.
  - Every entry is written into the spool first and delivered from there, so the record of a worktree is
    on disk before anything is sent. The commands are the Ledger's own (declare, confirm, rebranch, event),
    each a packet signed as space-observer that the Ledger's accept verifies. The module verifies no
    signature and judges no command. A packet sent again after a crash carries the same nonce, and the
    Ledger answers it with the original answer and writes nothing.
  - AC3, for the lead. The Ledger has no event command yet: it is VELDO-0323's ("Ledger (event,
    consumed)"), and control_space.py is not in this ticket's footprint. Today the Ledger answers the
    event packet space_no_command:space_event, the entry stays in the spool as one file holding what the
    event record would hold (design 4.6), and row ac3/no-event-command-waits shows that and its delivery
    once the command exists. The rows that show one event record, and the git command returning while
    every remover is held, run against a stand-in for that command which verifies the observer's
    signature and keeps the record. Nothing is lost in between: the entries wait.
  - AC4, for the lead. control_service.py is not in this ticket's footprint (it is VELDO-0323's and
    VELDO-0315's), so the service neither serves the spool's socket nor calls start yet. The module holds
    both halves: serve_one, which answers a hook and only then calls what follows (the consumer's place),
    and start, which replays the spool and then calls reconcile. The suite serves the socket itself.
    Until the service does, no authority answers and every entry waits in the spool. The "next CLI call"
    of AC4 is any record, event or replay call; the CLI's other space verbs are VELDO-0313's and replay
    nothing yet.
  - The socket is <state root>/space-spool/authority.sock, not the workspace socket of control_client.py:
    that one routes by an enrolled workspace, and a plain repository has no enrollment. The module uses
    control_client's own bind and peer check. If the lead wants the hooks on the existing socket, it is a
    change of Remote and serve_one only.
  - What the hooks need to know comes from the repository's git configuration, which VELDO-0329 sets when
    it installs them: veldo.space.stateroot (without it the hook stands down), veldo.space.cli,
    veldo.space.installation and veldo.space.trunk.
  - The trunk. No declaration names a project's trunk, so the hook takes main unless veldo.space.trunk
    says otherwise. A wrong name sends no event, and nothing is removed on an event that was not sent.
  - The owner. A branch that matches one of the project's branch patterns is owned by the project and
    the ticket the pattern names. A branch no pattern matches, a detached worktree and a worktree of a
    plain repository are owned by the scope alone. A worktree a run owns (the run's label in the hook's
    environment) is VELDO-0336's and is not built here.
  - A live item already at the path of a worktree that is added (one removed by hand and made again) is
    given the new branch and start by rebranch. Its owner stays what it was: no Ledger command changes an
    owner. An item a creator of Veldo's declared is never confirmed by the hook.
  - A checkout git makes inside a rebase is not a switch: measured on git 2.43.0, a rebase runs
    post-checkout with HEAD detached, and recording it would take the branch off the item for good.
  - An entry that waits (no event command, the observer's key missing or not enrolled) keeps later
    entries about the same worktree or ref behind it, so an add is never delivered after its own switch.
  - How long a hook can wait: five seconds for an answer and two for another call's replay, then the
    entry stays spooled and git goes on.
