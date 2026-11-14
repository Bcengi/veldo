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
reads it through the installed reader. That row is the proof on the owner's host that the installed form
reads what the measurement says, from the place the service reads it.

Assumptions, marked as such. Three things were not measured. The measurement of what the capability
reads was made in a container that shares the host's process table, as uid 0 holding cap_sys_ptrace and
no other capability, against a process of the owner's; the installed reader runs as the owner against
root-owned entries, which is the same permission check from the other side. The task entries were not
read with the capability. And the two unit files were not run as written: a transient unit does not take
Accept=yes, and the capability arriving in the unit needs the installed binary. The installed row of AC6
proves all three.

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
