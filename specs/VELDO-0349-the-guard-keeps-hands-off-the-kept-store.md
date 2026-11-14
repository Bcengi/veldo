---
schema: veldo.spec/v1
id: VELDO-0349
title: "The guard keeps hands off the kept store"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0346]
placement: [engine, loop]
protected_paths: ["scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh"]
footprint:
  - "engine/scripts/veldo-guard.sh"
  - "scripts/veldo-guard.sh"
  - "packs/claude/scripts/veldo-guard.sh"
  - "scripts/suites/*_veldo_0349_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0349-the-guard-keeps-hands-off-the-kept-store.md"
  - "specs/index.md"
  - "proof/VELDO-0349/**"
behavior_bearing: true
observability:
  logs: >
    A refusal is written to the hook's standard error, which the agent sees: that the command names kept
    work, which of the two it named (the snapshot store or the kept refs), and the three veldo space
    commands to use in its place. The guard writes no record of its own for it.
  error_taxonomy: >
    Exit status 2 from the guard hook, which blocks the command. Two reasons: the command names the
    snapshot store, or it names refs/veldo/kept. A state root the guard cannot read is not an error of
    its own: the guard then refuses on the word space-saved.
acceptance_criteria:
  - id: AC1
    text: >
      The guard hook refuses, with exit status 2 and before the command runs, a shell command whose text
      names the snapshot store: its path under the state root, written in full or with the home folder
      written as ~ or $HOME. The refusal says that the store is kept work and names veldo space kept,
      veldo space restore and veldo space kept drop. When the guard cannot read the state root, it refuses
      a command that holds the word space-saved
    falsified_by: >
      Each of these turns a row of its own red. Leave the rule out: the row's planted command, a recursive
      delete of the store's path, is allowed. Stand down when the state root cannot be read: the row hides
      the state root from the guard, plants the same command, and it is allowed
  - id: AC2
    text: >
      The guard hook refuses the same way a shell command whose text holds refs/veldo/kept, whatever the
      command does with it
    falsified_by: >
      Refuse only a ref delete: the row's planted command that points a kept ref at another commit is
      allowed
  - id: AC3
    text: >
      veldo space kept drop is allowed when it is the whole command, also when it names the store or a
      kept ref. A command that joins anything to it, by a separator, a pipe, a new line or a substitution,
      is judged like any other
    falsified_by: >
      Each of these turns a row of its own red. Refuse every command that names them: the row's drop
      command, with its item given by its kept ref, is refused. Allow any command that holds the words
      veldo space kept drop: the row's command that follows them with a delete of the store is allowed
  - id: AC4
    text: >
      A command that names neither the store nor the kept refs is untouched: for a command the guard has
      never judged and for one it judges today, the exit status and the output are those of the guard
      before this ticket. veldo space kept and veldo space restore with an item are allowed. The three
      copies of the guard are byte for byte the same
    falsified_by: >
      Refuse on the word kept alone: the row's veldo space kept command, and its git command on a branch
      named kept-notes, are refused
required_evidence: [unit, integration]
rollback: >
  Revert the change to the three copies of the guard. Commands that name the store or the kept refs run
  again as before this ticket. Nothing in the store or under the kept refs is changed by the revert, and
  reconcile and veldo space kept still report kept work that is missing.
---

## Intent

An agent's own shell command cannot touch the snapshot store or the kept refs. The guard hook refuses a
command that names either one before it runs, and lets through the one command that is meant to remove
kept work, the owner's veldo space kept drop.

## Design

This ticket was added to VELDO-0295 by the lead's decision of 2026-11-13, under the owner's rule that no
work is ever lost (Telegram 41209: "It's very important no work is ever lost. Space management needs to
ensure this very clearly"). The design is docs/design/VELDO-0295-design.md. Design sections this ticket
builds: the guard's rule in 0.3, and the part of 0.9 that says what the guard does not reach. Section 13
records the decision. Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Guard hook. Depends on 0346. It builds the guard's rule of section 0.3, by the lead's
> decision of 2026-11-13 (section 13). scripts/veldo-guard.sh and engine/scripts/veldo-guard.sh are
> protected paths, so the change lands with the owner's recorded approval.

Where it comes from. The validation of design section 0 found that a process of the owner's account can
delete the snapshot store, or delete a kept ref and let git collect its commits, and that nothing in
Veldo's own code stands in the way. The design answered with detection: reconcile, veldo space kept and
restore check every keep record and report what is missing (VELDO-0346 AC5). The validation recommended
one more step and did not require it, and the lead took it: stop the command an agent types.

What the rule is. The guard hook already reads every shell command an agent is about to run. It gains
one check, made before its existing ones: when the command's text names the snapshot store or holds
refs/veldo/kept, the guard exits with status 2 and says why. The store is named by its path under the
state root, in full or with the home folder written as ~ or $HOME. The guard takes the state root from
where the keeper takes it, and when it cannot read it, it refuses on the word space-saved. veldo space
kept drop passes when it is the whole command, because the Ledger refuses a drop the owner did not sign
(VELDO-0346 AC3). A command with anything joined to it is judged like any other.

What it does not do. It reads the text of a command. It does not see a program the agent writes and
runs, a path put together from a variable, or a link that points at the store, and it does not run where
the hook is not wired. Detection stays for all of those. It refuses reading as well as deleting, and it
refuses a mention: a commit message that quotes the ref name has to come from a file. A restore's option
ref takes the short name the listing shows, so veldo space restore never needs the full ref name.

The three cases the lead named, and the row that holds each: a planted command that names the store is
refused (AC1, and AC2 for the kept refs); veldo space kept drop is allowed (AC3); a command that names
neither is untouched (AC4).

Build order. It is built straight after 0346, whose drop command is the one it lets through.
depends_on holds that dependency.

Protected paths. scripts/veldo-guard.sh and engine/scripts/veldo-guard.sh are on the protected list of
.veldo/policy.yaml today, so this ticket adds no entry to that file. It names both in protected_paths,
and the owner's recorded approval is needed at landing.

Footprint. The guard's canon under engine/scripts, its two copies, and the ticket's suite, proof and
spec.

## History

- 2026-11-13: written from the lead's decision of that day on the question design section 15 held, after
  the final check of design section 0 (design-veldo-nowork-r2-validation-2026-11-14.md; design 14.8). The
  number follows VELDO-0348; nothing on any ref, in any worktree or in any commit message held 0349. Four
  criteria. Status ready.
