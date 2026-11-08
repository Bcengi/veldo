---
schema: veldo.spec/v1
id: VELDO-0286
title: The gate host reads who holds its lock from the holding processes' own descriptors, never from /proc/locks, and a holder it cannot read exactly never counts as the gate's
status: draft
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0220]
placement: [enforcement]
protected_paths: []
footprint:
  - "engine/scripts/gate_host.py"
  - "scripts/gate_host.py"
  - "scripts/suites/113_veldo_0220_gate_host.py"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0286-the-gate-host-reads-lock-holders-from-their-descriptors-not-proc-locks.md"
  - "specs/index.md"
  - "proof/VELDO-0286/**"
behavior_bearing: true
observability:
  logs: >
    When a process the gate host must judge (an ancestor, the recorded holder, or a process it scans
    to describe the holder) has a descriptor table or a descriptor it cannot read exactly, the host
    writes one line to stderr per such process: "gate host: holders of <lock> not read exactly: pid
    <pid> (<what was unreadable>: <errno name>)". The NOT STARTED line names the same pid and says the
    holder could not be read, instead of naming a holder it did not see. A process that exited while
    being read is not logged: it holds nothing.
  metrics: >
    None added. The stamp's host record (lock, held, waited_seconds, scope) is unchanged.
  traces: >
    None; each read is a synchronous read of /proc/<pid>/fd and /proc/<pid>/fdinfo.
  error_taxonomy: >
    No new exit codes. An unreadable holder resolves to the existing outcomes: the inside query exits 1 (not
    inside), the enter mode is NOT STARTED with exit 75 (or waits under VELDO_GATE_HOST_WAIT), and a gate the
    holder started that is not judged inside it stays the existing RED "the gate does not run inside
    the lock and scope its holder pid N made". Nothing that cannot be read becomes a yes.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: holders(lock, pids) answers, for a given set of processes, which of them hold an
      exclusive flock on the lock's inode, by reading each process's own descriptors: a process
      holds the lock when one of its /proc/<pid>/fdinfo entries carries a lock line FLOCK ... WRITE
      naming the lock's major:minor:inode and not marked as a blocked waiter. The holder is the
      process that owns the descriptor, never the pid printed in the lock line (that is the process
      that took the lock, which may have exited while a child keeps the descriptor). gate_host.py
      never opens /proc/locks. Set: the three callers, inside() (the holder and the processes above
      it), take() (this process's ancestors) and describe() (the recorded holder, then the processes
      of this user). Completeness: by construction, holders() is the only reader of lock ownership
      in gate_host.py; a source row in suite 113 requires the string /proc/locks to be absent from
      both copies. New suite 113 rows: host-lock/holder-is-descriptor-owner (a caller takes the flock,
      forks a child that keeps the descriptor and exits; the gate run below the child is judged held
      for it by its caller, and the inside query below a holder whose lock is kept that way answers yes) and
      host-lock/holders-under-churn (one steady flock held by a fixture process while three processes
      take and release flocks on other files for 3 seconds; every call of holders() in that window
      returns exactly that one process, and none after it unlocks; the row records the number of
      reads, which must be at least 100).
    falsified_by: >
      Registered mutant gate286-proc-locks-reader restores the /proc/locks table reader as holders()
      body (lines 135 to 148 at 2d6ba203). host-lock/holder-is-descriptor-owner must turn red: the
      table names the exited taker, not the live child, so the caller's hold is missed and the gate is
      NOT STARTED. The source row also turns red.
  - id: AC2
    text: >
      Claim: a holder that cannot be read exactly fails closed. When a process the host must judge
      has a descriptor directory or a descriptor fdinfo that cannot be read (permission, or a lock
      line in a form the reader does not recognise), that process is treated as not holding the lock
      for the gate: the inside query answers no (exit 1), take() does not count it as the caller's hold (so the
      gate waits or is NOT STARTED with exit 75), and describe() does not name it as the holder. The
      lock is never judged free by a read: whether it is free is decided only by flock with LOCK_NB, as
      today. A process that disappears while being read (ENOENT or ESRCH on its /proc entry) holds
      nothing and is not an error. Set: the three callers above. Completeness: suite 113 row
      host-lock/unreadable-holder-fails-closed runs the gate under a fixture caller that marks itself
      non dumpable (prctl PR_SET_DUMPABLE 0, which makes its /proc/<pid>/fd unreadable to the same
      user) and then takes the flock: the gate is NOT STARTED with exit 75, writes no stamp and no
      event, and the inside query run below it exits 1. If the fixture's descriptors turn out readable on the
      host, the row is red with that reason, never skipped.
    falsified_by: >
      Registered mutant gate286-unreadable-is-holder makes holders() count a process whose
      descriptors cannot be read as holding the lock. host-lock/unreadable-holder-fails-closed must
      turn red: the gate starts as held by its caller.
  - id: AC3
    text: >
      Claim: every unreadable holder is logged as the observability section states, once per process
      per read, on stderr, and the NOT STARTED line in that case says the holder could not be read and
      names the pid, instead of "a holder not recorded". Set: the same fixture as AC2. Completeness:
      host-lock/unreadable-holder-logged requires the gate's output to carry exactly one "holders of
      <lock> not read exactly: pid <fixture pid>" line naming the errno, and the NOT STARTED line to
      name that pid as unreadable.
    falsified_by: >
      Registered mutant gate286-unreadable-silent drops the log line and the unreadable wording, so the
      unreadable process is passed over silently. host-lock/unreadable-holder-logged must turn red
      while host-lock/unreadable-holder-fails-closed stays green.
  - id: AC4
    text: >
      Claim: nothing else changes. The VELDO-0220 behaviour of suites 113 and 114 holds as before: a
      lock held by another gate or by util-linux flock outside the gate's ancestry is NOT STARTED and
      names the holder (the recorded holder with its commit and root, or "pid <taker> (no holder
      recorded)" for the core runner's flock, where the named pid is the flock process that holds the
      descriptor), a lock the caller took is used as the caller's, the wait still starts the gate, the
      nested holder guard still refuses a forged holder, and the keeper still releases the lock only
      after the scope is empty. engine/scripts/gate_host.py and scripts/gate_host.py stay byte
      identical. Completeness: rows host-lock/held-not-started (7 cases), host-lock/released-on-exit,
      host-lock/not-started-not-red and suite 114's host-scope rows, unchanged, and the gate's
      template-sync check.
    falsified_by: >
      The VELDO-0220 registered mutants host220-ignores-lock, host220-forged-holder,
      host220-lock-inherited and host220-lock-not-retained keep being rejected against the new reader;
      each reverts one line and must turn its named row red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. holders() reads /proc/locks again, the four new rows and three mutants leave
  suite 113 and the teeth registry, and the host's behaviour returns to VELDO-0220's. No stored record
  changes shape.
---

## Intent

The gate host decides whether the gate already runs under the host lock and whether a busy lock is
its caller's. It reads that from the kernel's whole lock table, /proc/locks, which is the wrong
source for an exact answer. Make the answer exact, and make every answer that cannot be exact a
no, logged.

## Context

Fix round 6 of landing-c (commit aa384925, proof/landing-c/README.md "Fix round 6", cause T) found
suite 66 flaky for this reason: the kernel serves /proc/locks a page per read and walks the global
lock list again for each page, so a lock taken or released elsewhere on the host between pages drops
or repeats lines. Measured on the landing-c host (Linux 7.0.0-38), one steady flock with 3 lock churn
processes for 3 s: of 22089 reads the steady lock appeared 0 times in 10, twice in 361 and three
times in 5 (376 wrong). Read from the holding descriptor's fdinfo, which the kernel prints from that
file's own lock list in one short read, it was exact in 69 of 69 reads under the same churn and
absent after unlock. Suite 66 now reads it that way; the round named gate_host.py as the same class
and left it to a follow-up spec. This is that spec.

engine/scripts/gate_host.py (canon; scripts/gate_host.py is its byte-identical copy) reads the table
in holders(), lines 135 to 148 at 2d6ba203, and three callers rely on it:

- inside() answers yes for a lock-only installation (no scope) only when the table names the holder
  or a process above it. A dropped line answers no inside a running gate, and verify.sh then execs
  the enter mode under its own holder, which refuses RED ("the gate does not run inside the lock and scope
  its holder pid N made"): a green change reads as red.
- take() counts a busy lock as the caller's hold only when the table names an ancestor. A dropped
  line makes the owner's core runner (flock -x <lock> verify.sh) see its own gate NOT STARTED.
- describe() names the holder in the NOT STARTED message; a repeated or stale line can name a process
  that no longer holds it.

Whether the lock is free is decided by flock itself, not by this read, so the defect never lets two
gates hold the host at once. It decides gate-lock ownership, though, and a wrong answer turns a gate
red or not started for a reason that is not in the change. It is control-plane and is treated so:
risk high, every criterion with a registered mutant.

## Design

The question gate_host asks is never "who on the host holds this lock" but "does one of these
processes hold it": its ancestors, the holder named in its environment and the processes above it,
or the recorded holder. That set is small and known, so the host reads each candidate's own
descriptors: list /proc/<pid>/fd, read each /proc/<pid>/fdinfo/<fd>, and match a lock line that is
FLOCK, WRITE, not a blocked waiter, and names the lock's major:minor:inode (the same device string the
table reader builds today). The fdinfo approach of suite 66 fits this question exactly, with one
difference recorded in AC1: the holder is the process that owns the descriptor, because a flock
belongs to the open file description, which the keeper, a forked child or flock(1)'s command shares;
the pid in the lock line is only the process that took it.

describe() has no candidate set when no holder is recorded; it scans this user's processes in pid
order and names the process that took the lock if it still holds the descriptor, else the lowest pid
that does. That scan runs only on the NOT STARTED path.

A candidate that cannot be read is not a holder for the gate's purposes (AC2) and is logged (AC3).
Failing closed here costs a NOT STARTED or a red, both visible and both retried by the caller; failing
open would let a gate run outside the lock it claims.

## Out of scope

Suite 66 and its reader (already fixed in fix round 6); the lock path, the keeper, the scope and the
stamp; any other reader of /proc/locks in the repository; a shared helper module between the suite
and the host (the two readers answer different questions and stay separate).

## What the reviewer judges

- Normal use: verify.sh calls gate_host.py's two command line modes (the inside query
  and the enter mode, VELDO-0220) on the owner's host, inside or below
  the core runner's flock, while other processes on the host take and release flocks freely.
- Threat model: none beyond VELDO-0220's. A process of the same account that forges a holder record
  or an environment variable is already handled by is_holder and the ancestry check; this change does
  not widen it. Processes of other users are unreadable and are treated as AC2 states.
- Out of review scope: kernels without fdinfo lock lines (Linux before 3.8), descriptors passed over
  sockets to unrelated processes, and pid reuse within a single read.

A finding inside this section is fixed before landing. A finding outside it is filed as a ticket
and does not block landing. A real defect under normal use is always inside it.

## Notes

The proof bundle carries, per the proof rule, a summary of the churn row: reads, wrong reads (must
be 0), the command, commit, host, kernel and host load during the run, and the same measurement with
mutant gate286-proc-locks-reader applied, for comparison. Raw read logs are discarded.

## History

2026-11-08: drafted from landing-c fix round 6 (aa384925, proof/landing-c/README.md, cause T and its
"Same class, not changed here" line). human_approval not_required as VELDO-0272's rule computes it:
no footprint entry matches a protected path in .veldo/policy.yaml, protected_paths is empty and no
risk area applies.
