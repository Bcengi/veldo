---
schema: veldo.spec/v1
id: VELDO-0299
title: "The probes: in use and unique work"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0326, VELDO-0331]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "scripts/suites/*_veldo_0299_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0299-the-probes-in-use-and-unique-work.md"
  - "specs/index.md"
  - "proof/VELDO-0299/**"
behavior_bearing: true
observability:
  logs: >
    A probe's facts are written on the deferral they caused: the process or container that used the path,
    or the case of rule 5 that found unique work. File names are recorded; contents never are.
  error_taxonomy: >
    None of its own. The rules that read these facts defer as space_deferred:in_use and
    space_deferred:unique_work.
acceptance_criteria:
  - id: AC1
    text: >
      A path is in use when a live process has its working directory, an open file or a mapped file at or
      beneath it, or a running or stopped container has a bind mount there; a command line naming it is
      not use
    falsified_by: >
      Check the working directory only; the row with an open file beneath the path reads not in use and
      fails
  - id: AC2
    text: >
      A worktree has unique work in each of the five cases of rule 5. A branch with a commit that only its
      own ref holds is unique work; the same branch after a squash landing whose receipt names its tip is
      not
    falsified_by: >
      Count the worktree's own branch among the refs that contain the commit; the row with an unlanded
      commit reads no unique work and fails
  - id: AC3
    text: >
      For an agent's worktree and an agent repository the comparison is against the shared repository's
      refs: a branch the runner has not brought across is unique work, and after it is brought across it
      is not
    falsified_by: >
      Compare inside the agent repository only; the row with a branch not yet brought across reads no
      unique work and fails
  - id: AC4
    text: >
      A sandbox launcher's scratch is in use while its scratch lock is held or its borrowed login is not
      settled, and not in use once both are clear
    falsified_by: >
      Read the lock only; the row with a free lock and an unsettled login reads not in use and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Nothing is removed by this ticket, so nothing on disk changes.
---

## Intent

The safety rules decide from facts. This ticket adds the observers that return those facts: which
processes use a path, which containers mount it, whether a worktree or an agent repository holds unique
work, and whether a sandbox launcher's scratch is still in use. A probe returns facts and decides nothing.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (rules 3, 4 and 5, and the notes
on the probes). Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers
are copied here word for word.

What section 12 says about this ticket:

> Components: Probes. The rule order, the ledger rule and the protect rule are VELDO-0330.

Build order. It is built together with 0298, 0299, 0330 and 0300, after the first five tickets. The design
states no dependency for this ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: review (verdict FIX). The lead's rule: every probe fails closed, and what it cannot read
  or decide is in use or unique work, never free. The five paths that failed open, each now a row with
  its falsifier: (1) a stash no longer counts among the refs that hold a commit (only a branch, a tag
  and a remote-tracking ref do), so a stash that reaches an unlanded commit leaves it unique work;
  (2) agent_repository given no shared repository is unread with unique work unknown, where it compared
  the repository with itself; its stash entries and its other refs the shared repository does not hold
  are unique work, and stashes is a fact of both probes; (3) git_lock reports locked, with read False
  and what git said, when git cannot read the worktree, and in_use carries it; (4) a scratch folder the
  probe cannot open reads as locked, and a journal it cannot look into as not settled; (5) a process
  whose name cannot be read is listed and counted, and only an entry that is gone when it is read is
  taken as ended. unread.processes is a list of {pid, uid, command, reach}, not a count. A process
  table mounted with hidepid is reported and makes the path in use. in_use is now true when a user was
  seen (found) or when something unread could hold the path (unknown).
- 2026-11-13: the lead's decision, bounded fail closed: an unread process counts as use of a path only
  when it could reach it. reach(path, uid, gids) reads the owner, group and mode of every directory
  from / to the path with os.stat; a process of another uid that a directory shuts out is excluded
  (reach None). It counts when it runs as the probing uid, when its status cannot be read, when the
  directories let it through, when a directory cannot be judged by owner, group and mode, when a parent
  could reach, and (added by in_use) when a container has a bind mount at, beneath or above the path or
  an engine cannot be read. A root-owned process is judged by the mode like any other uid, so it is
  excluded only where the mode shuts uid 0 out and no container mounts the path. containers returns the
  mounts above a path in above. The reasoning is design section 7, "What a probe cannot read". Measured
  on this host for an item under the home folder: 536 unread, 527 excluded, 9 counted (six of the
  user's own that are not dumpable, three let through by the home folder's group), so every such item
  is still in use here; the design records it as the lead's open point. Not changed: the review's low
  findings 8a to 8d (the helper matched by name, the exclusive lock test against a starting launcher,
  the calling process not excluded, volumes with a bind option). No acceptance criterion changed.
