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
protected_paths: ["engine/scripts/veldo_procread.c", "scripts/veldo_procread.c", "engine/.veldo/services/veldo-procread.socket", "engine/.veldo/services/veldo-procread@.service", ".veldo/services/veldo-procread.socket", ".veldo/services/veldo-procread@.service", ".veldo/policy.yaml"]
footprint:
  - "engine/scripts/veldo_procread.c"
  - "scripts/veldo_procread.c"
  - "docs/veldo-procread-setup.txt"
  - "engine/.veldo/services/veldo-procread.socket"
  - "engine/.veldo/services/veldo-procread@.service"
  - ".veldo/services/veldo-procread.socket"
  - ".veldo/services/veldo-procread@.service"
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
    that failed. A deferral for process use names each process that counted by process id, thread id,
    uid and the fact that matched (cwd, fd or maps) with the device and inode number read, or the reason
    it stayed unread. Numbers are recorded; no path of another process is.
  error_taxonomy: >
    None of its own. Rule 4 defers as space_deferred:in_use. The reader's state is one of used, absent,
    refused:not_regular, refused:owner, refused:mode, refused:folder, refused:capability, refused:no_pin,
    refused:digest, refused:no_socket, refused:writer, refused:no_capability, refused:failed and
    refused:output.
acceptance_criteria:
  - id: AC1
    text: >
      With no reader at the fixed path, or one that fails a check (not a regular file, an owner other than
      root, a group or mode other than the installed ones, a folder on the way to it that another account
      owns or may write, a capability attribute other than exactly cap_sys_ptrace permitted and effective
      in version 2 or in version 3 with root id 0, no digest in the installation's space section, a digest
      other than that one, no socket, an output the kernel does not show as written by one process of the
      owner's that holds exactly that capability, whose status shows NoNewPrivs 1 and Seccomp 2, and that
      a pidfd names as alive before and after its status was read, anything but the one header line
      received before the probe has sent its byte, or a header that says it holds no capability), the
      probe does not use it, every unread process is judged as before this ticket, and the in_use facts
      name the reader's state and the check that failed. The reader writes its header only after it has
      set no_new_privs and installed its filter, and it writes the table only after it has read one byte
      on descriptor 1; the probe sends that byte only after it has seen the header's writer locked
    falsified_by: >
      Each of these turns a row of its own red. Skip the digest check: the row puts a program that prints
      an empty table in the reader's place, the undumpable process in the item is not counted and the item
      reads free. Accept any capability set that holds cap_sys_ptrace: the row's copy with
      cap_dac_read_search added is used. Accept version 3 of the capability attribute with any root id:
      the row's copy with another root id is used. Check the file and not its folders: the row's reader in
      a folder the owner may write is used. Ignore the header's cap field: the row's reader that says
      cap=0 is used. Take the output whoever wrote it: the row's stand-in listens on the socket, answers
      with an empty table, and the item reads free. Trust the process id without the pidfd: the row's
      stand-in writes an empty table and exits, the row answers the status read for its number as a real
      reader's, and the item reads free. Take bytes written before the writer was seen locked: the row's
      wrapper writes an empty table and then executes the real reader with its output on a socket pair,
      and the item reads free
  - id: AC2
    text: >
      With the reader in use, a process of the owner's that is not dumpable counts for an item exactly
      when the working directory or an open descriptor of any of its threads, or a mapped file, is the
      item or beneath it, matched by inode number alone: the one in the item holds it, named by process
      id, thread id and fact with the device and inode number read, and the one outside it no longer
      counts
    falsified_by: >
      Each of these turns a row of its own red. Match the working directory only: the process that holds
      nothing but an open file beneath the item reads free, and so does the one that holds only a
      directory descriptor on the item. Leave out the maps: the process that only maps a file of the item
      reads free. Read the first thread's working directory only: the process whose second thread sits in
      the item with a file system state of its own reads free. Read the first thread's descriptors only:
      the process whose second thread holds a file of the item in a descriptor table of its own reads
      free. Match on device and inode: the row's descriptor that the reader printed with another device,
      or with a hyphen, reads free
  - id: AC3
    text: >
      A root-owned process a login started is judged by the same facts: in the item it holds it, and
      elsewhere it does not count. A process with any fact the reader could not read (an x line, no block,
      or a start time other than the one the probe reads) stays unread and is judged by the bound of
      VELDO-0299. A folder of the item that the probe cannot list makes the item in use
    falsified_by: >
      Each of these turns a row of its own red. Take a block with an unread fact as read: the row's
      root-owned process, whose descriptors could not be listed and which holds a file in the item, reads
      free. Skip a folder that cannot be listed: the row's item, with a process holding a file inside a
      folder of mode 000, reads free
  - id: AC4
    text: >
      The reader takes no argument and reads only the stat, mountinfo and maps entries of each process and
      the cwd and fdinfo entries of each of its tasks. It prints numbers only, in the format of design
      section 7.1. Its seccomp filter ends it on ptrace, process_vm_readv, process_vm_writev, pidfd_open,
      pidfd_getfd, kcmp, kill, tkill, tgkill, rt_sigqueueinfo and pidfd_send_signal, on an open with a
      write, create or truncate flag, on a write to any descriptor but 1, and on a call of another
      architecture. The filter does not limit which entries are opened for reading; the reviewed source
      does, and the digest ties the binary to it
    falsified_by: >
      Allow kill in the filter; the row's patched copy of the reader, which signals itself after the
      filter is in place, exits normally and the row fails. The row runs three more patched copies, for
      pidfd_getfd on a descriptor opened before the filter, for process_vm_readv and for an open for
      writing, and allowing any one of them in the filter lets that copy exit normally
  - id: AC5
    text: >
      An output with no end line, an end count other than the number of blocks, a line outside the format,
      bytes after the end line or, where the reader is run directly, an exit status other than 0 is not
      used at all: the reader's state is refused, and every unread process is judged as before this
      ticket. The reader itself ends with no end line when a write fails. After its end line it waits,
      with one read on descriptor 1, until the probe has shut down its side, so the writer of a short
      output, one that fits in the socket's buffer, is still alive when the probe looks
    falsified_by: >
      Each of these turns a row of its own red. Use the blocks read before the cut: the row cuts the
      output before the block of the process in the item, and the item reads free. Go on after a failed
      write: the row gives the built reader a standard output that takes no more bytes, and finds an end
      line after the gap. Exit straight after the end line: the row lets the built reader finish a short
      output before it reads, and finds the writer gone when it looks
  - id: AC6
    text: >
      The reader runs in a socket-started systemd user unit of its own, with no NoNewPrivileges and no
      sandboxing setting; the authority unit keeps NoNewPrivileges=yes, and every probe reads through the
      socket and executes no reader itself. The unit's entry checks the installed binary through one open
      descriptor and executes that descriptor. Where the reader is installed (requires.json), the reader
      check, run in a transient user unit with the authority unit's properties, reports the state used
      with cap=1 and reads an undumpable process it started in a folder, whose second thread sits in
      another; the row records how long the reader ran on that host
    falsified_by: >
      Each of these turns a row of its own red. Have the probe execute the reader itself, so that the
      check passes from the owner's shell only: the installed row, which runs the check under
      NoNewPrivileges=yes, reads cap=0. Check the path and then execute the path: the row swaps the file
      between the two and finds that the other program ran
  - id: AC7
    text: >
      The reader built twice from the source of the commit under test, in two temporary folders, with
      /usr/bin/cc, an empty environment and the house build line, has one SHA-256 digest, and the proof
      bundle records it with the versions of the compiler and the C library
      (proof/VELDO-0344/reader.sha256). The owner's install lines in the setup text build from the blob of
      a commit named by its full hash, read with git's cat-file under --no-replace-objects, and root's
      line compares the installed copy with a digest written into it before it sets the capability. The
      setup text says that this digest is copied from the review record the owner approved for the commit
      and is not read back from the checkout
    falsified_by: >
      Each of these turns a row of its own red. Drop the prefix map from the build line: the two folders
      give two digests. Take the compiler from the path: the row puts a stand-in cc first in the path and
      finds the stand-in's output. Put setcap before the digest comparison in the setup text: the row that
      reads the lines finds the order wrong. Read the blob with git show: the row adds a replace ref for
      the blob in a fixture repository, runs the first line there and finds the other source built
  - id: AC8
    text: >
      The probe's own reading of a process it may read covers every thread: the working directory and the
      open files of each task under /proc/<pid>/task. A process with a task it cannot read is unread. This
      widens VELDO-0299 AC1, whose text is not edited; the change is in that spec's History
    falsified_by: >
      Read the first thread's working directory only; the row whose second thread sits in the path with a
      file system state of its own reads not in use and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change and set process_reader to none in the installation's space section. The probe then
  judges unread processes by the bound alone, as before. The installed binary and the two user units are
  the owner's to remove (systemctl --user disable --now veldo-procread.socket; sudo rm
  /usr/local/lib/veldo/veldo-procread); left in place they are used by nothing.
---

## Intent

The in-use probe cannot read some processes: root's, other users', and the owner's own that made
themselves not dumpable. Today each of those counts as use when it could reach the item, and on the
measured host that defers every item under the home folder. The owner decided how they are read: through
a small separate program, the process reader, that holds one file capability and only reads. This ticket
builds the reader, the user unit it runs in, the reproducible build and its recorded digest, the probe's
check that the output comes from the binary the owner installed, and the matching of its facts against
an item.

## Design

This is the forty-ninth build ticket of VELDO-0295, added after the first forty-eight by the owner's
decision of 2026-11-13 (Telegram 41204 and 41205). The design is docs/design/VELDO-0295-design.md.
Design sections this ticket builds: 7.1 (the process reader, in its second revision), the process_reader
key of 6.8, and the Process reader and Reader units rows of section 3. Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Process reader, Reader units, Probes, Declarations reader. Depends on 0296, 0299 and 0330.

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
probe matches the inode numbers against those of the item's own files. One capability stays one: the
validation accepted it and the lead confirmed it.

What the validation changed (design-veldo-0344-validation-2026-11-14.md, verdict CHANGES; design 14.6).

Where the reader runs. The authority unit sets NoNewPrivileges=yes, and under it the kernel grants no
file capability, so a reader started by the service's own child would hold nothing. The lead decided:
the reader runs in a socket-started systemd user unit of its own, beside the authority unit, with no
NoNewPrivileges. The owner installs it without sudo. It is not a system service and there is no second
account. The authority unit is not touched. Every probe connects to the socket and reads the same
output; no probe executes the reader. Because any process of the owner's can listen on a socket in the
owner's runtime folder, the probe takes the output only when the kernel names its writer as one process
of the owner's that holds exactly cap_sys_ptrace (SO_PASSCRED; measured on this host on 2026-11-13).
The validation did not ask for that check; without it the digest of the installed file would say
nothing about who answers.

What the second validation changed (design-veldo-nowork-0344r2-validation-2026-11-14.md; design 14.7).
It found the seven points above resolved and kept the writer check. A process id can be handed out
again between a write and the probe's look, so the probe also sets SO_PASSPIDFD and holds the writer
by the pidfd the kernel attaches (measured on this host on 2026-11-13, kernel 7.0: each part carries
one, and it reads as ended for a writer that has gone). The reader's whole output can fit in the
socket's buffer, so after its end line the reader waits, with one read on descriptor 1, until the
probe has shut down its side. The install line reads the source with git's cat-file under
--no-replace-objects, because git show follows a replace ref any process of the owner's can add, and
the digest root compares with is copied from the review record the owner approved, not read back from
the checkout. The reader also checks that /proc is a process file system before it reads.

What the final check changed (design-veldo-nowork-r2-validation-2026-11-14.md; design 14.8). Executing
a program keeps the process, its pidfd and its start time. A wrapper put into the unit's start line
could write a fake table, move its output to a socket pair and execute the installed reader, and the
probe would read the reader's status for the wrapper's bytes. The writer check stays and is closed in
two ways. The probe also requires NoNewPrivs 1 and Seccomp 2 in the writer's status: a process holds
the capability and a filter together only when it executed the installed binary first, and the
reader's filter refuses another execution. And the reader writes only its header once it is locked,
reads one byte on descriptor 1, and writes the table after that; the probe sends the byte only after
it has seen the header's writer locked, and refuses anything but the header before it. This follows
from how the kernel defines execve and was not run on this host; the AC1 row shows it.

Every thread. The entries under /proc/<pid> are the first thread's. The reader reads the working
directory and the fdinfo entries of every task, and so does the probe's own reading of the processes it
may read, which had the same gap (AC8, recorded on VELDO-0299's spec).

The build. The reader is built from the blob of the approved commit, with /usr/bin/cc and an empty
environment, reproducibly. The gate builds it twice and records the digest in the proof bundle, and
root's install line compares the installed copy with that digest before it sets the capability. The
owner's shell, which is also the agent's, no longer vouches for the binary.

Matching. By inode number alone in every case, because a file held through an overlay shows another
device. The device stays in the deferral record.

The filter. It ends the reader on every call that attaches, signals, writes to a process, takes a
descriptor from one or opens a file for writing. It cannot limit which entries are opened for reading;
the reviewed source does that, and the spec says so.

The language. C11, built static, with the build line of the repository's one other compiled helper,
veldo-userns (scripts/veldo_userns.c, VELDO-0210). A file capability must sit on a binary of its own: on
an interpreter it would be held by every script that interpreter runs. The house rule for such a helper
is already set by veldo-userns: one C file, the C library and nothing else, static so no loader runs and
no library can be put in front of it, a reproducible build line, installed root-owned under
/usr/local/lib/veldo. The gate has a C compiler because of that helper and has no other compiled
toolchain.

Build order. It is built after 0301 and before 0302, so before any ticket that removes on a real host
and long before 0332, the switch to act. It can be built as soon as 0299 and 0330 have landed.

Footprint. The reader's source with its synced copy; the two unit templates with their synced copies;
the owner's setup text beside the namespace helper's; Probes, which checks, connects, matches and holds
the unit's entry; the Declarations reader, which gains the process_reader key; Signal, where rule 4 reads
the unread list; the policy file, which gains the reader's source and the two unit templates as protected
paths; and the ticket's suite, proof and spec. The proof bundle holds reader.sha256.

What a row can and cannot do. Installing the reader needs root, and a suite has none. The rows for AC1,
AC2, AC3 and AC5 give the probe a reader through its seam: a program the row writes, served on a socket
the row makes, with the check's file facts (owner, mode, capability) and the writer's capability supplied
by the row. One AC1 row leaves the writer check real and answers from a stand-in, which must be refused.
Another has the stand-in write and exit while the row answers the status read as a real reader's; the
pidfd must refuse it. A third has a wrapper write an empty table and then execute the built reader with
its output on a socket pair; the lock check and the order of the bytes must refuse it. One AC5 row serves the built reader on a socket, lets it finish a short output
before it reads, and checks that the writer is still alive.
The rows for AC4 and AC7 build the real reader from its source and run it without the capability, where
it prints x lines for what it may not read. The row for AC8 needs no reader. One row of AC6 runs only
where the reader is installed (declared in requires.json as the namespace helper's rows are): it runs the
reader check in a transient user unit with the authority unit's properties, NoNewPrivileges=yes among
them, and that check starts a real undumpable process in a folder, with a second thread in another, and
reads it through the installed reader. The check's fifth row requires a whole block in the reader's
table (no x line, the start time the probe reads) for process 1, which is root's and which the probe
cannot read itself. The installed row requires all five PASS lines. That row is the proof on the owner's
host that the installed form reads what the measurement says, from the place the service reads it.

Assumptions, marked as such. Three things were not measured. The measurement of what the capability
reads was made in a container that shares the host's process table, as uid 0 holding cap_sys_ptrace and
no other capability, against a process of the owner's; the installed reader runs as the owner against
root-owned entries, which the kernel permits on another branch of its check (the uids differ, and its
capability-subset check applies), so the measurement does not cover it. The task entries were not read with the capability. And the two unit files were not run
as written: a transient unit does not take Accept=yes, and the capability arriving in the unit needs
the installed binary. What the installed row of AC6 proves of each, by the line of the reader check that
carries it: root-owned entries, by the fifth line alone (process 1), since the other four read a process
of the owner's own uid and say nothing about another uid; the task entries, by the second and third
lines on the owner's process and by the fifth, whose block is whole only when every task of process 1
was read; the unit files, by the state used with cap=1, reached through the socket from a unit with
NoNewPrivileges=yes. Until the owner's host runs that row, all three stay assumptions.

## History

- 2026-11-13: written from the owner's decision (Telegram 41204 and 41205) and the re-review's
  recommendation (review2-veldo-0298-0299-0330.md, "The open point"), with design section 7.1 added in
  the same change. No spec file on any of the repository's 508 refs or in any worktree, and no commit
  message, held the number VELDO-0344. Status ready.
- 2026-11-13: design revision 2 of section 7.1, after its validation
  (design-veldo-0344-validation-2026-11-14.md, verdict CHANGES; one capability accepted). Every required
  change is taken, by the lead's decisions. B1: the reader runs in its own socket-started systemd user
  unit with no NoNewPrivileges, installed without sudo; the authority unit keeps NoNewPrivileges=yes and
  never holds the capability; every probe reads through the socket; new AC6 with the installed-only row
  that runs the reader check under the authority unit's properties. B2: the reader reads cwd and fdinfo of
  every task, prints a t line per task and each equal line once; AC2 names the thread and gains the two
  thread falsifiers; new AC8 gives the probe's own reading the same fix. B3: built from the blob of the
  approved commit with /usr/bin/cc and an empty environment, reproducibly, and compared by root with the
  digest the gate recorded in proof/VELDO-0344/reader.sha256; new AC7. R1: matched by inode number alone,
  the device kept in the deferral record, the xino overlay named as unseen. R2: AC4 lists the calls the
  filter ends the reader on and says the filter does not limit which entries are read; its row also runs
  pidfd_getfd and process_vm_readv. R3: AC1, AC2 and AC3 carry a falsifier for each check they name, and
  the capability attribute's version is stated. R4: the unit's entry checks one open descriptor and
  executes it (AC6). Added beyond the validation: the probe takes the output only from the writer the
  kernel names (AC1), because a socket in the owner's runtime folder can be answered by any process of the
  owner's; and the reader ends with no end line when a write fails (AC5). The footprint and the protected
  paths gain the two unit templates. Five criteria became eight. Status ready.
- 2026-11-13: design 7.1 amended after its second validation
  (design-veldo-nowork-0344r2-validation-2026-11-14.md; design 14.7), which found B1 to B3 and R1 to R4
  resolved and kept the writer check. N-R4: AC1 holds the writer by a pidfd (SO_PASSPIDFD, measured on
  this host), with a falsifier for a process id trusted without it; AC5 has the reader wait after its end
  line until the probe has shut down its side, with a row for a short output and a falsifier for a reader
  that exits at once. The reader checks that /proc is a process file system, and the design names what it
  takes on trust about /proc. N-R5: AC7 reads the blob with git's cat-file under --no-replace-objects,
  from a commit named by its full hash, and the setup text says the digest is copied from the approved
  review record; one more falsifier, a replace ref. From the same validation's table: AC1 gains a
  falsifier for version 3 of the capability attribute with any root id, and AC6's installed row records
  the reader's run time. Still eight criteria. VELDO-0299's AC1 is not edited, as that validation
  confirmed. Status ready.
- 2026-11-13: design 7.1 amended after the final check (design-veldo-nowork-r2-validation-2026-11-14.md,
  verdict CHANGES; design 14.8), which found every earlier point resolved and one new hole in the writer
  check: a process that writes a fake table and then executes the reader in its own place keeps its
  process id and its pidfd. AC1: the writer's status must also show NoNewPrivs 1 and Seccomp 2, the reader
  writes its header only after it has locked itself and the table only after it has read one byte, and the
  probe sends that byte only after it has seen the header's writer locked; anything but the header before
  the byte is refused. AC1 gains one falsifier, bytes taken from before the writer was seen locked. Still
  eight criteria. VELDO-0299's AC1 is not edited, as this check confirmed again. Status ready.
- 2026-11-14: built. The reader's source with its synced copy, the two unit templates, the setup text,
  the probe's checks, socket conversation, table reading and matching with the three owner commands
  (reader, reader-units, reader-exec), the process_reader key, Signal's deferral facts, suite
  141_veldo_0344_process_reader and proof/VELDO-0344. No acceptance criterion was edited. What the build
  found, each recorded in the proof bundle's assumptions:
  - NOT DONE, the policy file. This spec's footprint and protected_paths name .veldo/policy.yaml, which is
    itself a protected path, and the builder was told to touch none and to report. The three entries
    (the reader's source, with its engine copy, and the two unit templates, with theirs) are written out
    in proof/VELDO-0344/owner-install.txt for the owner or the lead to add. Until then those files are
    not protected paths.
  - NOT RUN, the installed rows. Nothing here could install the file capability. Row ac6/installed runs
    only where the reader is at /usr/local/lib/veldo/veldo-procread and prints a skip line elsewhere.
    Its falsifier (the probe executes the reader itself, and reads cap=0 under NoNewPrivileges) is shown
    here by another row, ac6/reads-through-the-socket, and is not shown by the installed row. The three
    assumptions of the Design section (the capability read from the owner's side, the task entries read
    with it, the two unit files as written) stay assumptions until the owner's host runs that row.
  - requires.json is derived by scripts/run_scope.py and holds suite closures only, so it cannot name a
    row. The installed-only row is declared the way the namespace helper's are in fact declared: by its
    skip line in the suite, and in the suite's requires_note in scripts/suites/manifest.json.
  - AC7, the prefix map. Dropping -ffile-prefix-map from the build line does not change the digest on
    this compiler: the line compiles a relative file name with no debug information, so no folder name
    reaches the binary (measured: one digest in two folders, with the map and without). The falsifier as
    worded ("the two folders give two digests") does not turn red. The row instead requires the map in
    the line, and the registered case turns it red on that. The map stays, for a build line that later
    gains debug information.
  - "An empty table" (falsifiers of AC1 and AC5). A process with no block stays unread and is counted by
    the bound, so a table with no blocks cannot make an item read free. The rows' stand-ins print a table
    that shows the process elsewhere, a whole block with facts outside the item, which is the table that
    would. For AC5's cut, the row reads the process whose block came before the cut: it must still be
    judged by the bound.
  - process_reader may be left out of the space section, and then reads as none. Design 6.8 says every key
    is required. Nine reviewed suites outside this ticket's footprint write sections without it, and one
    of them holds the required keys to the nine it names. Left out, no reader is used, which is the answer
    that removes less.
  - Every thread, at a cost the build measured: reading each task's descriptors separately took the probe
    from 0.1 to 1.7 seconds per call on this host (2,454 tasks, 766,000 descriptor reads). The probe now
    asks the kernel, with kcmp, whether a task shares its descriptor table or its file system state with
    the first thread and reads it separately only when the kernel does not say they are the same one. Any
    error has it read. Rows ac8/second-thread-cwd and ac8/second-thread-descriptor cover both, with a
    falsifier of their own.
  - The reader keeps everything in static storage, so its filter allows no call for memory, which design
    7.1 lists among the allowed ones. That is narrower than the design, not wider.
- 2026-11-14: fixed after the independent review (review-veldo-0344.md, verdict FIX; the C reader, the
  filter, the writer check and the fail-closed paths were found sound). No acceptance criterion was
  edited, and the reader's source is unchanged, so C and H stay as recorded.
  - Finding 1, the sudo line. The line made root read a path in the owner's temporary folder, which any
    process of the owner's account can turn into a link to a root-only file, and it left the copy in
    place, readable by the owner's group, when the comparison failed. Now the owner's shell opens the
    build and root reads it as standard input, into a temporary file of root's own under umask 077; root
    compares that copy with H before chown, chmod and setcap, and moves the file into place only after
    setcap; a failed comparison, or a failed step after it, removes the copy. The folder gets mode 0755
    only when the line makes it. Row ac7/setcap-after-digest reads the new order, that no path of the
    owner's is inside the root command, and the two removals; its registered case
    (space344-setcap-before-the-comparison) is re-anchored on the new line and still turns it red. The
    setup text and proof/VELDO-0344/owner-install.txt carry the line and the review's full uninstall.
    The design's copy of the old line (docs/design, section 7.1) is outside this footprint and is not
    edited here: the setup text is the line the owner runs.
  - Finding 2, the installed row. The reader check had four rows, all on a process of the owner's own
    uid, and the spec said the installed row proved root-owned reading. The check gains a fifth row: a
    whole block for process 1, root's and closed to the probe itself, with the start time the probe
    reads. Row ac6/installed and the setup text require five PASS lines. The Design section's claim is
    corrected to say which line proves which assumption, and that the earlier measurement does not cover
    another uid. When the reader is present and systemd-run is not, the skip line says that. Still not
    run here: nothing in this build can install the capability.
  - Finding 3, the policy entries. Three more are written out beside the six in owner-install.txt:
    .veldo/control_space_probe.py, engine/.veldo/control_space_probe.py and
    docs/veldo-procread-setup.txt. The policy file is still not edited by the builder; until the owner
    adds the nine entries none of those files is a protected path.
- 2026-11-14: toolchain record. No acceptance criterion, no code, no suite and no setup text changed. An
  unattended update of the C library on the build host that day (glibc 2.39-0ubuntu8.9 to
  2.39-0ubuntu8.12) changed the digest of the reader's build: the link is static, so the library's code
  is in the program. The reviewed source is unchanged (scripts/veldo_procread.c, SHA-256
  233df2c7174357a0d1481b279f60e679f52135bfaf1e5c7edc940866fdfb865c). Line 1 of
  proof/VELDO-0344/owner-install.txt, run twice against commit
  705d64311de90f1945d7d0c0a5b9b3e6d125e78e with cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 and glibc
  2.39-0ubuntu8.12 on x86_64, printed 861d22a18e477344b637dae2d3443cb78a9233b3b0ee90620679f599fa47f199
  both times. proof/VELDO-0344/reader.sha256 records it with its toolchain and keeps the earlier record
  (bb9bd262a12793669e19a1cf3c77f2539ad48cb26093ba4377d5cf520d70d035, glibc 2.39-0ubuntu8.9) with its
  own. owner-install.txt carries the new H and says that H follows the toolchain: it is read from the
  record reviewed for the toolchain of the host the reader is installed on, and a digest that line 1
  prints and no reviewed record has is not installed. The new record awaits review. No sudo command was
  run, and the reader is not installed on this host.
- 2026-11-14: THE READER READS THE RUN LABEL TOO (the lead's decision after the re-review of VELDO-0313,
  whose finding 1 is that a block of this reader held files and no environment, so it could not say
  whether a process is a run's). For every task it reads, the reader now opens the task's environ entry
  and prints the value of one variable, VELDO_SPACE_LABEL, the name the run wrapper gives a run
  (bin/veldo SPACE_LABEL_VARIABLE, control_space_docker.py LABEL_VARIABLE): l =HEX for each entry that
  is the variable, the value in hexadecimal; l - when the environment was read to its end and holds
  none; x env ERRNO when it could not be read, and x env 7 for a value longer than 64 bytes, which is
  not printed in part or whole. Nothing else of an environment is printed, copied or kept: other
  entries are passed over byte by byte, the source names no other variable, the read buffer is cleared
  after each environment, and nothing is logged. Everything else of the reviewed design is as it was:
  static, read only, the same seccomp filter with no call added (an environ entry is one more open for
  reading beneath /proc), matching by inode number alone, the same sudo line.
  - The probe (reader_table) gives each block label: the values its tasks carry, an empty list when
    the environment was read and holds none, and None when it was not read (an x env line, no l line,
    a g line, a process id that opens two blocks). Not read is never no label. An x env line leaves
    whole as it is, so rule 4 reads the files of such a block exactly as before. The reader check has
    a sixth row: the label of its undumpable process, whose environ entry the probe is refused, is
    read and is the one the check started it with, and the label of process 1 is read. Row
    ac6/installed, the setup text and owner-install.txt require six PASS lines.
  - VELDO-0313's rule uses it (bin/veldo, _space_holders): of a block only a label that was read
    decides. This run's label makes the process a holder by its label; a label that is not this run's
    takes it out; a block with no label read takes nothing out.
  - AC4's TEXT IS NOW NARROWER THAN THE READER, and the builder did not edit it: it says the reader
    reads only stat, mountinfo, maps, cwd and fdinfo and prints numbers only. By this decision it also
    reads environ of each task and prints the label's value in hexadecimal. The criterion's wording,
    the Design section and design section 7.1 are the lead's and the owner's to amend. What an agent
    of the owner's account can learn through the socket grows by one fact for each process: which run
    it says it belongs to. The setup text says so.
  - Rows. reader/label (the built reader on processes it may read: the label's value for each task,
    l - for none, an empty value, 64 bytes read and 65 not printed; a secret the row plants, its
    name, the label's name and two variables whose names only begin or end like the label's are
    nowhere in the output, as they are or in hexadecimal; the one name in the source is the
    adapter's and the CLI's). label/table (the probe's reading). ac4/format, ac4/entries and
    ac4/unread-without-capability read the new line and the new entry. Five falsifiers, each seen red:
    space344-label-every-entry-printed, space344-label-name-without-its-equals-sign,
    space344-long-label-cut-short, space344-unread-environment-taken-as-no-label,
    space344-no-label-line-taken-as-no-label.
  - THE SOURCE CHANGED, SO ITS DIGEST DID, AND BOTH AWAIT REVIEW. scripts/veldo_procread.c has SHA-256
    f5373c0a5b2ba29ba425a5305e97d16fa578a632bfb5afed69962a1abae39821 (before:
    233df2c7174357a0d1481b279f60e679f52135bfaf1e5c7edc940866fdfb865c). Built with line 1 of
    proof/VELDO-0344/owner-install.txt on cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 and glibc
    2.39-0ubuntu8.12 on x86_64 it has the digest
    f890b5a253447011bd3570700275579119ff89170e61ea8e3f8903717bf8b647. reader.sha256 records it first
    and keeps the two earlier records, which are digests of the earlier source and of nothing else.
    owner-install.txt carries the new C and H and says that the source it names is not the one that
    was reviewed. No sudo command was run, the reader is not installed on this host, and row
    ac6/installed, with its sixth line, has not run anywhere.
- 2026-11-15: FIX AFTER THE REVIEW OF THE RUN LABEL (review-veldo-0344-label.md, verdict FIX, four
  findings). Owner rule (Telegram 41209): no work is ever lost.
  - Finding 1 (high, reproduced by the review: 33 of 150 reads). The reader wrote l -, "read to its
    end, no label", for a task that executed a program between the open of its environ entry and the
    read. The kernel reads environ from the memory the task had at the open; after the execution that
    memory is gone and the read returns nothing. With the reader wired in, VELDO-0313's rule then took
    a live process that carries the run's label out of the run. NOW: an l line is written only for a
    whole read of one program. Before the read and after it the reader takes what the task is: the
    start time and the two ends of the environment (fields 22, 50 and 51 of the task's own stat) and
    the device and inode of its exe, by stat. The read is whole when the two agree, the kernel
    returned at least one byte, and it returned exactly as many as the ends are apart. A read that is
    not whole is made once more, the same way; when that one is not whole either the fact is unread,
    x env 11, and no l line of either read is written (l lines are kept back until their read is
    known to be whole). The probe already reads x env as a label that was not read, so the process
    holds the run. Not read is never no label.
  - AN ENVIRONMENT OF NO BYTES IS NEVER A WHOLE READ. It is what the kernel returns for a task that
    is executing, and during an execution the two ends can both be zero before and after. The cost:
    a process that really has an empty environment is unread for as long as it lives, and so holds
    every run it could belong to. That is the fail-closed side.
  - What the reader opens grows by two entries of a task, both beneath /proc and for reading: its
    stat, and its exe by stat (the one newfstatat call of the source, now in one function). Nothing
    of either is printed. The filter is as it was: no call added. AC4's text was already narrower
    than the reader (the entry of 2026-11-14) and is narrower by these two as well; it is still the
    lead's and the owner's to amend, and was not edited.
  - Finding 2 (medium, the lead's): a process that overwrites its own environment area reads as no
    label. Recorded as an accepted limit in VELDO-0313's History of this day; nothing in /proc says
    whether the area is as the execution left it.
  - Finding 3 (low, suite 148): fixed under VELDO-0311, in its own commit.
  - Finding 4 (low): the buffers an environment passed through (the read buffer, the value, the kept
    lines) are cleared with explicit_bzero, which the compiler may not drop.
  - The CLI's own scan had the same defect (bin/veldo, _space_holders read environ once and took an
    empty read as no label; a plain read of a process that executes itself without end was wrong in
    355 of 3000 reads here). It now reads through _space_environment, by the same rule, and a read
    that is not whole leaves the process unread.
  - Rows. reader/whole-read, suite 141: a small static program the row builds, three ways. One
    carries the label and executes itself again without end, and is read 150 times: never l -, never
    a label of none, its own label whenever its environment was read whole (on this host the reader
    of 2df0c67c gave l - in 21 of 150 such reads, and this one 0 of 150, the label in all 150). One
    unmaps the end of its environment, the label in that part, behind 100000 bytes of another entry:
    x env 11, no l line. One has an environment of no bytes: x env 11. Row ac4/entries reads the two
    new entries. Suite 141 has 62 rows. Three falsifiers, each seen red on reader/whole-read:
    space344-environment-not-whole-taken-as-read (the three conditions gone: the reader as it was),
    space344-empty-environment-taken-as-read, space344-short-environment-taken-as-read. Finding 344
    has 40 cases.
  - NOT FALSIFIED BY A ROW: the comparison of the two takings alone (start time, exe, the two ends).
    A read that is complete, of the right length, and of a program the task no longer is cannot be
    made on purpose from outside the kernel; the comparison is there for that case and no mutant of
    it alone turns a row red. The second read has no falsifier either: without it the reader is
    still right, and only says unread more often.
  - SEEN AND NOT CHANGED (outside the review, about files and not the label): a process whose first
    thread has ended and whose other thread then executes a program takes the first thread's id; a
    table read across that moment has a whole block with no task line for it. Its label is then not
    read, so it holds; but rule 4 finds no file of it in that one table.
  - THE SOURCE CHANGED, SO ITS DIGEST DID, AND BOTH AWAIT REVIEW. scripts/veldo_procread.c has SHA-256
    44936632a48945a9380319b91b32deef1e9ffac11bac477401db1691b14b3561 (before:
    f5373c0a5b2ba29ba425a5305e97d16fa578a632bfb5afed69962a1abae39821). Built with line 1 of
    proof/VELDO-0344/owner-install.txt on cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 and glibc
    2.39-0ubuntu8.12 on x86_64 it has the digest
    bf1e1256ad3edb8fb83c695ef7e01380146a7048a3c465bfe463d9fee8835f26. reader.sha256 records it first
    and keeps the three earlier records. No sudo command was run and the reader is not installed.
- 2026-11-15: THE PROOF OF THE FIX, AND THE OWNER'S FILE. proof/VELDO-0344/owner-install.txt names
  C = 8bdfd98769830deb0a4ccfa78b3573ab5bcf589d and H =
  bf1e1256ad3edb8fb83c695ef7e01380146a7048a3c465bfe463d9fee8835f26 in line 1, line 2 and step 4, says
  that the source of 2026-11-14 (commit 2df0c67c, digest f890b5a2...) is not to be installed, and has
  a History section. Line 1 was run twice against C and printed H both times. Suite 141 on that
  tree: 62 rows, 88 passed, 0 failed, ac6/installed skipped. The 40 cases of finding 344, each
  through the driver's materialize() and worker(), outside its confinement: every no-op green, every
  mutant red on its target rows; the registered driver itself refuses the stage at its baseline, as
  before. Everything here awaits review. Nothing is installed; no sudo command was run.
- 2026-11-15: THE REVIEW OF THE FIX (review-veldo-0344-fix.md, verdict FIX, tests only). The reader's
  source and its digest are as they were: scripts/veldo_procread.c is not changed.
  - Finding 1 (medium): no row failed when the comparison of what the task is, before the read and
    after it, was removed alone. The entry above says such a read cannot be made on purpose from
    outside the kernel. It can: a task that shares its parent's memory (clone with CLONE_VM, which
    vfork and posix_spawn use) keeps that memory until it executes, and the parent keeps it alive
    after. Row reader/same-program: the suite's helper starts such a task, which waits on a fifo and
    then executes the helper with the run label as its whole environment; the built reader runs
    under strace, which holds its read of that one environ entry back for 2 seconds, and the row
    lets the task execute when strace shows the open. The read returns the parent's environment (12
    bytes, no label), as long as the ends taken before are apart. The reader reads once more and
    writes the task's own label. Case space344-identity-not-compared (the comparison alone gone):
    the row is red, l - and a label of none for a task that carries one; the no-op copy is green.
    The row is added only where strace is on /usr/bin:/bin and prints a SELFTEST SKIP line
    elsewhere; the case then has no row and is an error, never a pass.
  - Finding 2 (low), A KNOWN EFFECT: a process with an environment of no bytes that started after a
    run holds the run while it lives (a program started with env -i, for one). Kernel threads,
    zombies and processes older than the run's supervisor are taken out by what stat says, not by
    the label.
  - Row reader/rewritten-environment (the limit recorded in VELDO-0313, put to the proof): a process
    started with the run label that writes over its environment area, with its working directory
    in the item and a file of the item open. The reader writes l - for it (the label is lost for
    every reader) and its block is whole and names the working directory and the open file by
    inode: what holds an item is read with no label.
  - Suite 141 has 64 rows where strace is there. Finding 344 has 41 cases. Only the new case was
    applied in this round, through the driver's materialize() and worker(), outside its
    confinement, as before; the other 40 were not applied again.
  - THE SUDO LINE, DRY: lines 1 and 2 of proof/VELDO-0344/owner-install.txt, run without sudo
    against a scratch prefix in place of /usr/local/lib/veldo, with programs on the path that log
    their call in place of chown and setcap and before sha256sum. Line 1 printed H. A build with one
    byte added: exit 1, digest differs: nothing installed, sha256sum the only call, the folder
    empty. The right build with setcap failing, and with chown failing: exit 1, the install failed:
    nothing installed, the folder empty. The right build: sha256sum, then chown, then setcap, and
    the file in place with digest H. No sudo command was run and nothing is installed.

- 2026-11-17: suite 141 in the gate's confinement (gate 99zz3 on the VELDO-0329 integration, 39 rows red;
  lead ruling: the confinement stays and the suite is not listed in scripts/gate_unconfined.json).
  Cause: the fixture gave a thread its own file system state or descriptor table with unshare(CLONE_FS /
  CLONE_FILES), and the gate domain refuses the unshare call. A forked process cannot carry the property:
  it is its own first thread, so the falsifiers "read the first thread's working directory only" and "read
  the first thread's descriptors only" would still find it. The fixture's processes with threads are now a
  C program the suite builds; each thread is a task started with clone(2) in the same address space and
  thread group that leaves out CLONE_FS or CLONE_FILES, so the kernel gives it its own copy at its start
  and nothing calls unshare. The rows and their conditions are unchanged. Off the gate the suite passes
  every row but ac6/installed, which reads refused:no_pin on this host (the separate no_pin ruling).
  The proof manifest's words "by unshare" describe the fixture before this entry. The production reader
  check (control_space_probe.py) still makes its own thread with unshare; it runs under the authority
  unit, not in the gate domain, and is not changed here.
- 2026-11-17: gate fix 3 (gate 99zzD on the VELDO-0329 integration; lead rulings: the confinement
  stays, no gate_unconfined.json entry). Three suite changes, no change to the reader or the probe.
  - The stub build of ac6/executes-the-checked-descriptor ran cc without TMPDIR, so cc wrote /tmp, which
    the gate domain refuses, and aborted; the 11 rows after it were unreached. It now has TMPDIR, its own
    folder, as the other builds do. Behind it, ac7/reproducible ran the setup text's first line, whose
    env -i drops TMPDIR: the suite now adds TMPDIR="$d" (the line's own folder) after that env -i when it
    runs the line, and fails the row if the line does not have exactly one. The setup text is unchanged.
  - ac5/failed-write closed its 900 descriptors before it sent the byte after which the reader reads the
    table, so the table was large only by the host's other processes; in the gate domain they are not
    readable, the write succeeded and the reader ended 0. The descriptors now stay open until the reader
    has ended, and a check says all 900 were held. Falsifier: case space344-goes-on-after-a-failed-write
    applied, the row reads exit 0 and is red, off the gate and inside the gate domain.
  - reader/same-program held the reader's read back with strace, which the gate domain's seccomp filter
    refuses (ptrace). The row now uses no ptrace: the sharing parent's environment is about 960 KB, so
    the reader reads that entry in 64 KiB reads; the row watches /proc/<reader>/fd, stops the reader with
    SIGSTOP when it holds the entry open, reads the entry's position from its fdinfo while it is stopped,
    and only when the position is short of the end lets the task execute, waits until it has, and sends
    SIGCONT; a run where the stop came too late is not counted (60 runs at most). The row now always
    runs; the SELFTEST SKIP for a missing strace is gone. Falsifier: case space344-identity-not-compared
    applied, the row reads l - and a label of none (held at 65536 of 960068 bytes off the gate, 786432
    inside the gate domain, caught in the first run) and is red; unchanged, it is green in both.
  Measured: off the gate and inside the gate domain (gate_candidate.py) 64 of 65 rows, the one red
  ac6/installed with refused:no_pin (the owner's pin, already ruled).
