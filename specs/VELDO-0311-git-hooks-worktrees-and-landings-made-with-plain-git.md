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
- 2026-11-14: fix round after the review of bf5e9505 (verdict FIX, five findings). Ten rows added to the
  suite (28 rows), eleven falsifiers registered under finding 311 (21), each applied once and seen red on
  its row. Three statements of the build entry above no longer hold and are replaced here: "The module
  runs no git command", "The trunk ... the hook takes main", and "An entry is never dropped silently"
  (it was, for an entry that came to nothing). What changed, by the lead's decisions:
  - Finding 1, the trunk is never guessed. A declaration does name a trunk: the work configuration's
    land entry (control_api_authority.landing_of). The hook has no default: without veldo.space.trunk
    (which VELDO-0329 sets from the declared land trunk) it writes no entry for any branch, and the
    repository is noted once under space-spool/undeclared/ with the reason trunk_undeclared. The
    authority judges again, so a stale or wrong git configuration cannot make a branch a trunk: at a
    replay a ref change is sent only when its ref is the trunk the land entry declares for that
    repository or a landing ref its space file declares; any other is recorded as nothing
    (ref_not_declared, or trunk_undeclared when no land entry names the repository). Local takes the land
    entry as `landing`, by execution repository or by project name; handing it the service's own
    (control_service.landing_names) is part of the wiring VELDO-0323 and 0315 do. A plain repository has
    no land entry today, so it gets no trunk events until a declaration names its trunk; that is the
    fail-closed side, and reconcile still finds its worktrees.
  - Finding 2, the spool is a hint, never a fact. (a) The spool folder is made 0700. A spool folder, a
    refused/ or undeclared/ folder, or an entry file that another account owns or that group or others
    can write, and any link, is refused and never replayed: a file is set aside in refused/ as it was,
    with why beside it; a folder is left exactly as it is (it may not be ours to touch) and noted in
    <state root>/space-spool.refused.json. (b) The hook's side asks the kernel who serves the socket
    (SO_PEERCRED) and sends nothing unless it is this account. (c) Before anything is signed the replay
    reads the facts from git itself and records only what it read: a ref change only when its new commit
    is on the named ref now; a worktree only when that repository's own worktree list holds the path,
    with the branch it is on now and, as its start, the entry's commit when the worktree is still on the
    entry's branch and has that commit in its history, else the commit it is at now (a later start can
    only keep a worktree longer). The owner is the one the branch read from git gives. What git does not
    confirm is recorded as nothing. An entry met while a rebase is in progress waits. The old commit of a
    ref change is the hook's word and is not verified.
  - The module now runs git, and only to read: rev-parse, symbolic-ref, merge-base and worktree list,
    through one function that refuses any other command. It still writes, moves and removes nothing in
    any repository.
  - No MAC and no signature on an entry. Owner rule: this is a single-user setup. A key the same account
    can read adds nothing against that account, and another account is kept out by the folder's owner
    and mode. The account is the trust boundary.
  - OBLIGATION FOR VELDO-0323. Whoever records or consumes an event after this module has the same duty:
    the consumer reads from git itself, in the declared repository, that the event's new commit is
    reachable from the ref's current value, and that the ref is the declared trunk or a declared landing
    ref, before anything is made contained. It takes neither from the event record alone.
  - Finding 3, an item is found by repository and path. about answers the live worktree item at a path
    only when the item's repository is the entry's. A live item of another repository at the path makes
    the entry refused (space_path_of_another_repository:<item>) and set aside; that item is never
    rebranched, and no branch item is made. The same holds when a declare is answered locator taken.
  - Finding 4. An entry that comes to nothing leaves one line, with the entry whole and why, in
    space-spool/observations.jsonl before its file is unlinked. Paths are compared by the Ledger's own
    function (control_space.canonical_path), not a copy of it. That form does not follow links, so a
    repository declared through a link is still another name; its entries are now noted, not silent.
  - Finding 5. A replay has an overall deadline: five seconds for a hook's call, sixty for the replay verb
    and for start. Past it no further entry is started and no answer is waited for; the rest stay in the
    spool, whole, for the next replay.
  - Design change, recorded for the lead (review note A): the hooks reach the authority on their own
    socket, <state root>/space-spool/authority.sock, where design 6.9 says the existing local socket of
    control_client.py. The reason is in the build entry above. Until VELDO-0323 and 0315 serve it every
    entry waits: nothing deletes a waiting entry, and the spool grows until then.
  - Owner rule (Telegram 41209). The hooks and the spool still remove nothing but their own delivered or
    set-aside files: the module has the same two unlinks, both of its own spool files.
- 2026-11-14: fix round 2 after the re-review of 90cc1fc8 (verdict FIX: one blocking finding and two
  minor). Three rows added to the suite (31 rows), four falsifiers registered under finding 311 (25),
  each applied once and seen red on its row. Two statements of the fix round entry above are replaced
  here: "through one function that refuses any other command" (it refused by the first word only, so a
  form of an allowed command that writes was run) and "The old commit of a ref change is the hook's word
  and is not verified" (it is no longer passed on). What changed, by the lead's decisions:
  - Finding 1 (blocking), git is run in five whole forms and no other. The one function that runs git
    takes exactly: rev-parse --absolute-git-dir; rev-parse --verify --quiet --end-of-options
    <name>^{commit}; symbolic-ref -q --short HEAD; the ancestry test --is-ancestor with two full commit
    ids; worktree list --porcelain. Every other form is answered (None, '') and starts no process: a
    symbolic ref given a value or deleted, update-ref, any config, any option before the command (-c,
    -C, --git-dir, --exec-path), and any other form of the four commands. Row
    r2/git-runs-whole-read-forms-only tries more than fifty such forms and reads the refs, both HEADs,
    the configuration and the worktree list before and after. Row paths/no-delete-and-canon now reads
    every place the module calls that function and finds only the five forms, the function under no
    other name, one process start in the module and that one behind the guard: the reviewer's own
    mutant (a ref write added to the read) is registered and red there.
  - Finding 2, the old commit is never passed on. Git is not asked for the old commit of a ref change,
    so the event that is signed carries old as null; the spool entry still holds what the hook saw. AC3
    names "the old and the new commit": the record has both fields, and old is null until a consumer
    reads it from git itself. The obligation for VELDO-0323 above stands, and gains this: old is never
    taken from an event record.
  - Finding 3, the deadline bounds git reads. Each read of git inside a replay is given only the time
    the replay has left (never more than five seconds); with none left, or when the read does not end
    in it, nothing is concluded: the entry stays in the spool as it is, with every later one, for the
    next replay. Row f5/replay-stops-at-its-deadline now moves its clock in the authority's accept, so
    that it still shows the stop between two entries.
  - Owner rule (Telegram 41209). Nothing in this round removes anything: the module has the same two
    unlinks, both of its own spool files, and an entry that runs out of time is kept whole.
- 2026-11-15: ROW ac3/no-event-command-waits NO LONGER ASSERTS THE HOOK'S OWN BUDGET (the review of
  VELDO-0344's run label, finding 3; the row was red once, on a host that 74 runs of another suite
  loaded, and green alone). No production file changes: the suite only.
  - What was wrong. The row read the worktree's item the moment git returned. That holds only when
    the hook's replay ends inside HOOK_SECONDS, 5 seconds; when it does not, the hook leaves the
    entry in the spool for the next call, as specified, and no record is lost. The row took the
    budget for a promise, and when it was red it printed nothing of what it saw.
  - Now. The row waits for what it is about: the end of the process that runs the hook, and then,
    when the hook left the worktree's entry spooled, the end of one space replay, which is the next
    call. Each wait is woken by the kernel, by a connection on the authority's socket or by the
    process's exit through its pidfd, and by nothing else: no sleep and no poll on a clock. Each has
    one deadline, 180 seconds, there only so that a hang ends: the hook's replay of this step was
    measured at 0.10 s on a quiet host and 0.30 s with 80 busy loops on 20 cores (the review), the
    whole git command at 0.22 s here, and the deadline is 600 times the worst of them. The check
    still requires the item present, the spool holding the ref event alone, and nothing new set
    aside, so the row's point, that the event waits while a later entry is recorded, is as it was.
  - The check's words now carry what it saw: git's status, how long it took and what ended the wait,
    what the hook left in the spool, the replay's status and time when one ran, the item's state, the
    spooled types and the set-aside list.
  - Both ways run once by hand: as it is (the hook delivers, no replay: git 0 in 0.22 s), and with the
    authority kept away during the add (the hook left ref_changed and worktree_added, the replay
    delivered the second in 0.11 s, the row green). Suite 148: 31 rows, 57 passed, 0 failed.
