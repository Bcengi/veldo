---
schema: veldo.spec/v1
id: VELDO-0330
title: "The rule order, the ledger rule and the protect rule"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0299]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "scripts/suites/*_veldo_0330_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0330-the-rule-order-the-ledger-rule-and-the-protect-rule.md"
  - "specs/index.md"
  - "proof/VELDO-0330/**"
behavior_bearing: true
observability:
  logs: >
    A deferral records the first rule that refused, by name, the event it was refused at and the event
    that retries it.
  error_taxonomy: >
    space_deferred:not_in_ledger, space_deferred:protected, space_deferred:in_use,
    space_deferred:unique_work and space_deferred:remove_refused. One per refusal, named by the first rule
    that refused.
acceptance_criteria:
  - id: AC1
    text: >
      The rules run in the order of section 7 and the first refusal names the deferral
    falsified_by: >
      Run unique work before protect; the protected worktree with an edit is deferred as unique_work and
      the row fails
  - id: AC2
    text: >
      Rule 1 refuses a thing that is not the item recorded: a path that now resolves elsewhere through a
      link, a folder replaced by another repository's worktree, a Docker name now held by another object
      id
    falsified_by: >
      Compare the locator's text only; the row replaces the folder with a link, finds the link's target
      removed, and fails
  - id: AC3
    text: >
      A locator at or above a protect entry, or with one beneath it, is protected, and no event, no
      Confirm and no Discard removes it
    falsified_by: >
      Skip the protect rule in the discard remover; the row's protected worktree is removed on a discard
      answer and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change together with the removers. Without the rule order nothing may be removed.
---

## Intent

Every removal passes seven rules in one order, and the first that refuses names the deferral. This ticket
fixes that order and adds the two rules that are not probes of use: the ledger rule, which refuses a thing
that is no longer the item recorded, and the protect rule.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (the safety rules: their order,
rule 1 and rule 2). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: the rule order of section 7. Depends on 0299.

Build order. It is built together with 0298, 0299, 0330 and 0300, after the first five tickets. depends_on
holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The design's component table names no module for the rule order. The footprint takes Signal, which runs
the rules, and Probes, which holds the protect list.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: after the review of VELDO-0298 and VELDO-0299 (verdict FIX for both), on which this
  ticket is built. What the rules read changed, and no acceptance criterion did.
  (1) Unread or None is in use or unique work. Rule 4 refuses when the probe says in use, and also on
  its own reading of what could not be read: an unread process that could reach the item, an unread
  engine, a process table that hides processes, a worktree whose locks git cannot read, a scratch
  folder that cannot be opened or a journal that cannot be looked into. Rule 5 refuses unless the
  probe read the worktree or the repository and says unique work is False: read False and unique_work
  None are unique work, and so is an agent repository with no shared repository to compare with.
  (2) What the probe needs. It needs read access to /proc of the processes it judges. Without root it
  has the status file of every process (uid, groups, parent), which the kernel gives every user, and
  os.stat on the item's directories; it does not have the working directory, descriptors or maps of
  another user's process, of a root-owned one, or of one of its own that is not dumpable. So removal is
  refused while any process it could not read could hold the item, and the refusal names each by
  process id, uid and reason. Under hidepid it cannot list what it must judge, and every removal is
  refused until the table shows every process or the service has CAP_SYS_PTRACE.
  (3) Bounded fail closed (the lead's decision; this ticket's first report: 617 unread processes on
  this host, so every item deferred as in_use). An unread process counts for an item only if it could
  reach that item. A process of another uid that cannot traverse the item's path by the path's own
  permissions (owner, group and mode of every directory from / to the item, read with os.stat) cannot
  hold it and is excluded. A root-owned process is judged by the mode and not by its privilege, and is
  excluded only where the mode shuts uid 0 out and no container has a bind mount at, beneath or above
  the path (the engine probe's mount list, which covers dockerd and containerd binds); with such a
  mount, or an unread engine, every unread process counts. A process of the same uid always counts when
  it cannot be read. A process whose parent could reach counts (a command run through sudo keeps the
  folder it was started in). The reasoning, and what the bound does not see, is design section 7.
  Measured here for an item under the home folder: 9 of 536 unread processes count, six of them the
  user's own undumpable ones, so rule 4 still defers such an item on this host; open for the lead.
  (4) Rule 6 follows the amended design: a child holds its parent in every state but removed and gone
  (declared, present, due, deferred, removing, kept). It reads the children itself at the attempt
  (inside): the ledger's items inside this one by parent and by path, and for an agent repository the
  worktrees its git folder registers that are on disk; one that no live item records holds it. inside
  is also the look VELDO-0298's due is given. Rows ac1/children, ac1/kept-child-holds-parent,
  ac1/unread-process-reach, ac1/unread-is-in-use.
- 2026-11-13: re-review (verdict FIX). Finding 0330-1, a deletion the reviewer reproduced: rule 6's look
  read the disk only for an agent repository's registered worktrees, so a git repository in a folder
  of a worktree that git ignores, with a commit that exists nowhere else, passed every rule and went
  with git's non-forced worktree remove. inside now also asks the probe's nested for every git
  repository on disk beneath a worktree or an agent repository (a .git folder or file, or a bare git
  folder; ignored or not; no link followed; a recorded live item's folder not walked into). Each one
  no live item records holds the item as path:<its path> unrecorded, and a folder that cannot be
  listed holds it as unread. Row ac1/nested-repository-holds-worktree is the reproduction, refused
  in_use by children with the commit still there; its falsifier skips the look, and the row's remover
  then deletes the repository. Rule 4 reads the re-review's reach of VELDO-0299 (a root-owned process a
  login started refuses as privileged_login; row ac1/unread-process-reach). Design section 7 is amended
  for both, and its measurement paragraph is corrected: of the six unread processes with the user's uid
  number, five are the user's own and one is a container's. VELDO-0301's History now says it must pass
  look=signal.inside to the kind registry's due, with a falsifier. No acceptance criterion changed.
- 2026-11-13: the owner's decision (Telegram 41204 and 41205) adds the process reader, VELDO-0344,
  design section 7.1. Rule 4 keeps its reading: it refuses on a process that uses the item and on an
  unread process that could reach it. What changes with VELDO-0344 is which processes are still
  unread: one the reader read in full is a user of the item or is not counted, and one it could not
  read is judged as now. The deferral then also names the reader's state. No acceptance criterion
  changed.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. This
  ticket is built and its criteria are not edited. The seven rules keep their order and their numbers. The
  keep step runs after rule 6 has passed and before the tool of rule 7 is called, inside the removers,
  with the deferral keep_failed (VELDO-0345). Rule 6's look beneath a scratch item and a build output
  item, with the clean clone exception, is VELDO-0347 AC2. No acceptance criterion changed.
