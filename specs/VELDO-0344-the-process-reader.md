---
schema: veldo.spec/v1
id: VELDO-0344
title: "The process reader"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0296, VELDO-0299, VELDO-0330]
placement: [engine, loop]
protected_paths: ["engine/scripts/veldo_procread.c", "scripts/veldo_procread.c", ".veldo/policy.yaml"]
footprint:
  - "engine/scripts/veldo_procread.c"
  - "scripts/veldo_procread.c"
  - "docs/veldo-procread-setup.txt"
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "engine/.veldo/control_space_config.py"
  - ".veldo/control_space_config.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - ".veldo/policy.yaml"
  - "scripts/suites/*_veldo_0344_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0344-the-process-reader.md"
  - "specs/index.md"
  - "proof/VELDO-0344/**"
behavior_bearing: true
observability:
  logs: >
    Every in_use answer carries the reader's state: used, absent or refused, and for refused the check
    that failed. A deferral for process use names each process that counted by process id, uid and the
    fact that matched (cwd, fd or maps) or the reason it stayed unread. Numbers are recorded; no path of
    another process is.
  error_taxonomy: >
    None of its own. Rule 4 defers as space_deferred:in_use. The reader's state is one of used, absent,
    refused:not_regular, refused:owner, refused:mode, refused:capability, refused:no_pin, refused:digest,
    refused:no_capability, refused:failed and refused:output.
acceptance_criteria:
  - id: AC1
    text: >
      With no reader at the fixed path, or one that fails a check (not a regular file, an owner other than
      root, a group or mode other than the installed ones, a capability set other than exactly
      cap_sys_ptrace permitted and effective, no digest in the installation's space section, a digest
      other than that one, or a header that says it holds no capability), the probe does not use it,
      every unread process is judged as before this ticket, and the in_use facts name the reader's state
      and the check that failed
    falsified_by: >
      Skip the digest check; the row puts a program that prints an empty table in the reader's place, the
      undumpable process in the item is not counted, the item reads free and the row fails
  - id: AC2
    text: >
      With the reader in use, a process of the owner's that is not dumpable counts for an item exactly
      when its working directory, an open file or a mapped file is the item or beneath it: the one in the
      item holds it, named by process id and fact, and the one outside it no longer counts
    falsified_by: >
      Match the working directory only; the row whose undumpable process holds nothing but an open file
      beneath the item reads free and fails
  - id: AC3
    text: >
      A root-owned process a login started is judged by the same facts: in the item it holds it, and
      elsewhere it does not count. A process with any fact the reader could not read (an x line, no block,
      or a start time other than the one the probe reads) stays unread and is judged by the bound of
      VELDO-0299
    falsified_by: >
      Take a block with an unread fact as read; the row's root-owned process, whose descriptors could not
      be listed and which holds a file in the item, reads free and fails
  - id: AC4
    text: >
      The reader takes no argument and reads only the stat, cwd, fdinfo, mountinfo and maps entries of
      each process. It prints numbers only, in the format of design section 7.1, and its seccomp filter
      ends it on any call that attaches to a process, signals one, writes to one or opens a file for
      writing
    falsified_by: >
      Allow kill in the filter; the row's patched copy of the reader, which signals itself after the
      filter is in place, exits normally and the row fails
  - id: AC5
    text: >
      An output with no end line, an end count other than the number of blocks, a line outside the format
      or an exit status other than 0 is not used at all: the reader's state is refused, and every unread
      process is judged as before this ticket
    falsified_by: >
      Use the blocks read before the cut; the row cuts the output before the block of the process in the
      item, the item reads free and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change and set process_reader to none in the installation's space section. The probe then
  judges unread processes by the bound alone, as before. The installed binary is the owner's to remove
  (sudo rm /usr/local/lib/veldo/veldo-procread); left in place it is used by nothing.
---

## Intent

The in-use probe cannot read some processes: root's, other users', and the owner's own that made
themselves not dumpable. Today each of those counts as use when it could reach the item, and on the
measured host that defers every item under the home folder. The owner decided how they are read: through
a small separate program, the process reader, that holds one file capability and only reads. This ticket
builds the reader, the probe's check that it is the binary the owner installed, and the matching of its
facts against an item.

## Design

This is the forty-ninth build ticket of VELDO-0295, added after the first forty-eight by the owner's
decision of 2026-11-13 (Telegram 41204 and 41205). The design is docs/design/VELDO-0295-design.md.
Design sections this ticket builds: 7.1 (the process reader), the process_reader key of 6.8, and the
Process reader row of section 3. Section 12 of the design holds the ticket itself; its acceptance
criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Process reader, Probes, Declarations reader. Depends on 0296, 0299 and 0330.

The decision, as the owner gave it. The in-use probe reads every process through a tiny separate reader
that holds exactly one file capability, cap_sys_ptrace (=ep), installed once by the owner with one sudo
command. It only reads entries under /proc/<pid> and prints facts. It never attaches, signals or
writes. There is no list of trusted process names. The Veldo service never holds the capability. Without
the reader installed, or if its binary was changed, unread processes keep failing closed, and the probe
says so.

One thing in the decision could not be built as worded, and the design says how it is met instead. The
decision lists /proc/<pid>/fd among what the reader reads. Measured on this host on 2026-11-13: with
cap_sys_ptrace alone the kernel gives the working directory, the maps and the fdinfo entries of a
process, and refuses to list its fd folder. That folder is mode 0500 and listing it is an ordinary
permission check, which this capability does not pass. So the reader reads fdinfo, which gives each open
descriptor's mount id and inode number, and prints device and inode numbers for all three facts. The
probe matches them against the device and inode numbers of the item's own files. One capability stays
one. Design 7.1 has the measurements, and section 15 puts the other way (a second capability) to the
owner.

The language. C11, built static, with the build line of the repository's one other compiled helper,
veldo-userns (scripts/veldo_userns.c, VELDO-0210). A file capability must sit on a binary of its own: on
an interpreter it would be held by every script that interpreter runs. The house rule for such a helper
is already set by veldo-userns: one C file, the C library and nothing else, static so no loader runs and
no library can be put in front of it, a reproducible build line, installed root-owned under
/usr/local/lib/veldo. The gate has a C compiler because of that helper and has no other compiled
toolchain.

Build order. It is built after 0301 and before 0302, so before any ticket that removes on a real host
and long before 0332, the switch to act. It can be built as soon as 0299 and 0330 have landed.

Footprint. The reader's source with its synced copy; the owner's setup text beside the namespace
helper's; Probes, which checks, runs and matches; the Declarations reader, which gains the
process_reader key; Signal, where rule 4 reads the unread list; the policy file, which gains the
reader's source as a protected path; and the ticket's suite, proof and spec.

What a row can and cannot do. Installing the reader needs root, and a suite has none. The rows for AC1,
AC2, AC3 and AC5 give the probe a reader through its seam: a program the row writes, with the check's
file facts (owner, mode, capability) supplied by the row. The row for AC4 builds the real reader from
its source and runs it without the capability, where it prints x lines for what it may not read. One
more row runs only where the reader is installed (declared in requires.json as the namespace helper's
rows are): it starts a real undumpable process in a folder and one outside it and reads both through
the installed reader. That row is the proof on the owner's host that the installed form reads what the
measurement says.

Assumption, marked as one. The measurement was made in a container that shares the host's process
table, as uid 0 holding cap_sys_ptrace and no other capability, against a process of the owner's. The
installed reader runs as the owner against root-owned entries. Both are the same permission check from
opposite sides, and the installed row above is what proves it.

## History

- 2026-11-13: written from the owner's decision (Telegram 41204 and 41205) and the re-review's
  recommendation (review2-veldo-0298-0299-0330.md, "The open point"), with design section 7.1 added in
  the same change. No spec file on any of the repository's 508 refs or in any worktree, and no commit
  message, held the number VELDO-0344. Status ready.
