---
schema: veldo.spec/v1
id: VELDO-0209
title: Control-plane suites proven in a KVM guest the candidate cannot leave
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0208]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/gate_candidate.py", "engine/scripts/gate_candidate.py", "engine/scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.json", "scripts/agent_sandbox.py", "scripts/agent_sandbox.json", ".veldo/policy.yaml"]
footprint:
  - "engine/scripts/gate_guest.py"
  - "scripts/gate_guest.py"
  - "engine/scripts/gate_guest_init.sh"
  - "scripts/gate_guest_init.sh"
  - "engine/scripts/agent_sandbox.json"
  - "scripts/agent_sandbox.json"
  - "engine/scripts/verify.sh"
  - "scripts/verify.sh"
  - "scripts/check_template_sync.sh"
  - "scripts/suites/102_veldo_0209_guest_gate.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0209-confined-control-plane.md"
  - "specs/VELDO-0208-single-user-landing-reuse.md"
  - "specs/index.md"
  - "proof/VELDO-0209/*"
behavior_bearing: true
observability:
  logs: >
    The guest stage names its kit digest, boot time, shares and exit status; a stage that cannot run
    in the guest names its stand-down reason (guest_unavailable:<reason>) on the gate's own line.
  metrics: >
    Guest boot seconds, stage seconds and the host-domain duration of the same stage, per run.
  traces: >
    The stamp and gate event carry each guest-placed stage's kit digest, status source and any
    stand-down reason.
  error_taxonomy: >
    guest_unavailable (kvm, qemu, kit, kit_digest, busybox, modules) stands the stage down and the
    gate is red; guest_boot_failed, guest_timeout and guest_status_missing are red with the serial
    log tail; a failing stage is red exactly as in the host domain.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a gate stage placed in the guest cannot write any host path, reach the host's systemd
      user manager or session bus, or read the reuse store, its key, ~/.ssh or any deny_read path,
      even through units its own user manager starts. Set: a planted suite that starts a transient
      service and a scope through systemd-run --user, a unit that writes the host home and the
      store path, writes to every shared path, a connect to the host's /run/user/<uid>/bus and
      systemd/private, a network socket to a routable address, and qemu itself writing outside its
      scratch under the same grants. Completeness: every share is read-only at the qemu device and
      at the guest mount; the store, key and deny_read paths are never shared; the guest has no
      network device; qemu runs inside the launcher's Landlock domain with qemu's own seccomp
      sandbox. Test rows guest-escape/* in suite 102.
    falsified_by: Share one path writable, or start qemu outside its Landlock domain; a guest-escape row goes red.
  - id: AC2
    text: >
      Claim: the legs VELDO-0208 left unprovable in the host domain are proven in the landing gate.
      Set: the unit and integration stages run in the guest; every control-plane suite listed in
      VELDO-0208 (systemd user manager), suites 100 and 101 (workers under strace), 65_0067 (the
      product's nested custody confinement) and 82_0085 pass there. Completeness: the same
      `python3 scripts/selftest.py` and `python3 scripts/check_first_use.py` commands, unchanged,
      produce the stage verdict; guest and host-domain durations are recorded. Test row
      guest-legs/* plus one full guest unit stage run recorded in proof.
    falsified_by: Remove the guest's user manager (mask user@.service); the control-plane rows go red.
  - id: AC3
    text: >
      Claim: a guest-placed stage that cannot run stands down by name and the gate is red; it never
      passes silently and never falls back to the host domain or to no confinement. Set: no
      /dev/kvm, no qemu, no kit, a kit whose digest differs from the pinned one, a missing module.
      Completeness: one function decides availability before anything boots and returns one named
      reason; verify.sh prints it on the stage line and records it in the stamp and gate event.
      Test rows guest-standdown/* in suite 102.
    falsified_by: Let a missing kit fall back to the host domain; a guest-standdown row goes red.
  - id: AC4
    text: >
      Claim: the stage verdict comes only from the guest's status port, written by the authority
      bootstrap after the stage's session is gone. Set: a planted suite that prints a forged
      status line on stdout, one that exits 0 after killing its parent, a guest that powers off
      before writing status, and a guest that never finishes. Completeness: the kernel, initramfs,
      init and bootstrap come from the kit and the authority, never from the candidate; the status
      port's device node is root-only in the guest and the stage runs as the host's uid.
      Test rows guest-status/* in suite 102.
    falsified_by: Read the verdict from the stage's stdout; a guest-status row goes red.
required_evidence: [unit, integration]
rollback: Return CHECK_unit and CHECK_integration to the host domain (required:) and record the VELDO-0208 open classes as red, as before this specification.
---

## Problem

VELDO-0208 runs every gate stage in a Landlock domain on the host. With its gate stage corrections,
the unit stage reaches every suite, and three classes stay red by design, not by defect:

- The systemd user manager. About 29 control-plane suites drive `systemctl --user` and
  `systemd-run --user` and use /run/user/<uid>. A unit the host's user manager starts is forked by
  that manager, outside every Landlock domain. That is exactly the same-user service escape
  VELDO-0208 denies, so the domain refuses the connection, and those suites fail. Several of them
  fail at module level, which stops the unit run and with it the integration stage's nested run.
- Workers under strace. Suites 100 and 101 trace authority workers. The launcher's seccomp list
  refuses ptrace, so those rows cannot run when the unit stage itself is confined.
- Three unclassified suites: 62_0045, 65_0067 and 82_0085 (classified below).

The owner's constraints: one OS user, no separate users, no system services, no root step. No
"run them unconfined" and no "skip them". A check that cannot run stands down by name with a
recorded reason and never passes silently. The landing gate must still prove these legs, somewhere a
candidate cannot use to escape.

## What this host is (measured 2026-10-06)

| Fact | Value | How measured |
|---|---|---|
| Kernel | 7.0.0-30-generic, x86_64, Ubuntu 24.04.4 | uname -a |
| LSM stack | lockdown,capability,landlock,yama,apparmor,ima,evm (no bpf) | /sys/kernel/security/lsm |
| Landlock ABI | 8 (no control of connect to a pathname socket) | landlock_create_ruleset(NULL,0,VERSION) |
| systemd | 255.4-1ubuntu8.17, user manager running | systemctl --version, is-system-running |
| cgroup2 | unified, mounted nsdelegate,memory_recursiveprot | mount |
| Unprivileged user namespaces | blocked: kernel.apparmor_restrict_unprivileged_userns=1 | unshare -Ur: "write failed /proc/self/uid_map: Operation not permitted"; bwrap: "setting up uid map: Permission denied" |
| Yama ptrace_scope | 1 | sysctl |
| Tools present | bwrap, xdg-dbus-proxy, busctl, dbus-daemon, strace, runc, qemu-system-x86_64, qemu-img, busybox (static) | command -v |
| Tools absent | podman, crun, systemd-nspawn, virtiofsd, dbus-broker, firecracker | command -v |
| KVM | /dev/kvm crw-rw----+ root:kvm, account is in group kvm | ls -la, id |
| Kernel images | /boot/vmlinuz-* are 0600 root (unreadable); initrds 0644; modules readable | ls -la /boot |
| docker | Docker Desktop client; group docker (a root-equivalent daemon) | docker info |

## Options and the evidence for each

### O1. The host's user manager behind a D-Bus filter (xdg-dbus-proxy). Rejected.

xdg-dbus-proxy filters by bus name, object path and interface. It does not look at method
arguments. So it can admit or refuse StartTransientUnit, but it cannot tell a confined unit from an
escaping one. It also only sits on the bus. `systemctl --user` reaches the manager on
$XDG_RUNTIME_DIR/systemd/private, not on the bus: the sd-bus debug trace shows "starting bus by
connecting to .../systemd/private" first. Any admitted StartTransientUnit or StartUnit makes the
host manager fork the unit outside every Landlock domain. A filter by unit name prefix bounds
names, not what the unit runs.

### O2. An argument-checking proxy that rewrites every unit's ExecStart through the launcher. Rejected.

This needs trusted D-Bus marshalling and policy for the manager's whole API: StartTransientUnit
properties of every type, StartUnit, Exec*, sockets, timers, paths, SetEnvironment and
SetProperties. That is a large new trusted parser. The relaunched unit would get a new sibling
Landlock domain, not the suite's own. Landlock's scopes for signals, abstract sockets and ptrace
separate sibling domains, and the suites signal and inspect their units. The units and their
cgroups would also live in the owner's real manager (/run/user/<uid>/systemd/transient), so
leftovers and cleanup would reach the owner's session.

### O3. The host manager's own unit sandboxing through transient properties. Rejected.

Measured: `systemd-run --user --wait -p ProtectHome=read-only -p PrivateTmp=yes -- sh -c 'touch
$HOME/...'` wrote the file (journal: WROTE-HOME). `-p ProtectSystem=strict -p ReadWritePaths=/tmp`
also wrote $HOME (WROTE-HOME2). In a user manager these properties need a mount namespace inside a
user namespace. This host refuses that, and systemd degrades **silently**. systemd 255 has no
Landlock property. RestrictFileSystems needs the BPF LSM, which is not in the LSM stack. A
sandbox that silently does not apply is worse than none.

### O4. User namespaces: bwrap, rootless podman, systemd --user in a user namespace, unshare. Rejected under the constraints.

Measured: `unshare -Ur` and `bwrap --unshare-user` cannot write uid_map
(kernel.apparmor_restrict_unprivileged_userns=1 moves an unconfined creator into the
`unprivileged_userns` profile, which denies every capability). podman and systemd-nspawn are not
installed. Enabling any of these needs a root step: the sysctl, or an AppArmor profile that grants
`userns` to a VELDO helper. VELDO-0208 excludes root steps. If the owner ever accepts that one
root step, a user, mount and cgroup namespace sandbox becomes viable (see O5's trigger).

### O5. A private `systemd --user` inside the gate's Landlock domain, on a delegated cgroup subtree. Measured, then rejected.

Built as a prototype: the trusted parent runs in a `systemd-run --user --scope -p Delegate=yes`
scope, splits it into supervisor/ and domain/, and grants the domain Landlock read and write on
domain/ only. The manager then runs with XDG_RUNTIME_DIR in scratch and SYSTEMD_UNIT_PATH set
to a private unit directory.

- Without the cgroup grant the manager exits at once: mkdir of .../init.scope returns EACCES.
- With the grant it starts, and its units inherit the domain (they are its children). But the
  first `systemctl --user` failed. sd-bus in systemd 255 binds every client socket to an abstract
  name (bind(3, {sun_path=@"3d3b11b609a64765/bus/systemctl/"}) = -1 EPERM in the trace), and the
  broker refuses abstract binds. With an autobind substitution, `systemctl --user show` worked
  (Version=255.4-1ubuntu8.17, ControlGroup=.../domain/manager).

Two defects remain, and no unprivileged mechanism closes either one on this kernel:

1. **Cgroup pull-in.** Moving a process into a cgroup checks write permission on the common
   ancestor's cgroup.procs through DAC only (inode_permission; Landlock has no hook there). Every
   ancestor under user@<uid>.service belongs to the user. Measured: a process in the domain wrote
   the pid of an outside, same-user process into its delegated subtree's cgroup.procs (PULLED),
   and the subtree's cgroup.kill then killed it. That is a cross-domain kill and freeze path,
   which Landlock's signal scope exists to deny. cgroup2 is mounted nsdelegate, so a cgroup
   namespace would bound migration, but creating one needs a user namespace (O4).
2. **Peer identity through the broker.** VELDO-0208's broker performs connect itself, because
   Landlock ABI 8 cannot mediate a pathname connect. So SO_PEERCRED and the peer pidfd name the
   broker, not the caller. systemd resolves "the caller" from them. Measured: `systemd-run --user
   --scope` failed with "Unknown object '/org/freedesktop/systemd1/unit/self'". Anything that
   resolves the caller's pid would act on the trusted broker; a scope created for "the caller"
   would migrate the broker into a candidate-controlled cgroup. Closing this needs Landlock control
   of pathname connects (a later ABI), so that connect no longer needs brokering.

**Trigger to revisit:** a kernel with Landlock control of pathname Unix connects, plus a
user-namespace allowance for one VELDO helper. Together those remove both defects.

### O6. A delegated cgroup subtree by itself. A component, not a boundary.

It is part of O5 and carries O5's pull-in defect. Cgroup membership does not confine files,
sockets or the manager.

### O7. Keep the legs out of the landing gate, or skip them. Excluded by the owner.

### O8. Docker (the account is in group docker). Excluded.

The docker daemon is a root-equivalent system service. A candidate that can talk to it owns the
host.

### O9. A KVM guest: the recommended option.

The account can open /dev/kvm, qemu-system-x86_64 is installed, and the guest needs no root step:

- **Kernel.** /boot/vmlinuz-* is root-only. `apt-get download
  linux-image-unsigned-7.0.0-30-generic` as the user fetched the matching unsigned kernel (17.1
  MB), and `dpkg-deb -x` extracted it. The 9p modules (netfs, 9pnet, 9pnet_virtio, 9p, overlay)
  are readable under /lib/modules and were decompressed with zstd. busybox is static.
- **Boot.** A 1.6 MB initramfs (busybox, five modules, a 20-line init) mounts the host's /usr and
  /etc read-only over virtio-9p (qemu readonly=on). It puts a tmpfs root and a tmpfs overlay over
  /etc, writes a guest-private shadow and gshadow, an empty fstab, crypttab and machine-id, and no
  host *.wants. It then switch_roots into the host's own /usr/lib/systemd/systemd as guest PID 1.
  Measured: PID 1 up in 1.1 to 2.9 s; boot, probe and power-off in 3.4 to 4.3 s wall.
- **Real user manager.** `runuser -l <user>` goes through PAM and logind: session cgroup
  /user.slice/user-1000.slice/session-c1.scope, then `systemctl --user show` gives
  Version=255.4-1ubuntu8.17 and ControlGroup=/user.slice/user-1000.slice/user@1000.service.
  `systemd-run --user --scope` lands in .../user@<uid>.service/app.slice/veldo-dispatch-probe.scope.
  The first attempt failed only because the host's /etc/shadow is unreadable to qemu; the
  guest-private shadow fixed it.
- **The suites, in the guest, as the host uid, with the worktree and the git common directory
  shared read-only at the same paths and no network device:**

  | Suite | Host gate domain (VELDO-0208) | Guest | Host unconfined |
  |---|---|---|---|
  | 62_0039 dispatch (user manager) | 37 passed, 10 failed, 66 s | 47 passed, 0 failed, 12 s | 47/0, 8.5 s |
  | 63_0040 containment (scopes, caps, cgroup.kill) | 72 passed, 11 failed | 83 passed, 0 failed, 9 s | |
  | 100_0207 case reuse (strace) | 85 passed, 30 failed | 115 passed, 0 failed, 9 s | |
  | 65_0067 edges (nested custody Landlock) | 34 passed, 1 failed | 35 passed, 0 failed, 8 s | |
  | 82_0085 decomposition | 40 passed, 1 failed (fixed below: 41/0) | 41 passed, 0 failed, 5 s | |

- **Planted escapes, from inside the guest:** a `systemd-run --user` unit wrote /home/<user>/...
  and the file existed only in the guest's home, never on the host. Writes to the worktree and
  to /usr returned "Read-only file system". ~/.ssh did not exist. /run/user/<uid>/bus was the
  guest's own session bus.
- **Defence in depth:** qemu itself ran inside a Landlock domain (read /usr, /etc, /proc,
  /sys/devices/system/cpu, the worktree and the common dir; write only its own directory;
  /dev/kvm with ioctl), with `-sandbox on,obsolete=deny,elevateprivileges=deny,spawn=deny,
  resourcecontrol=deny`. It booted and ran the escape probe in 4 s. A guest-to-qemu escape
  therefore lands in a domain no stronger than today's gate stage.
- **ptrace is a domain question, not a boundary need.** Under Landlock alone, without the
  launcher's seccomp list, strace of a same-domain child worked. Attaching to an outside process,
  even an unconfined descendant that Yama scope 1 would allow, was refused (PTRACE_SEIZE EPERM),
  and so was signalling it. In the guest, strace simply works.

## Recommendation

Run the unit and integration stages of this repository's gate in a KVM guest that the gate's
authority launcher boots for each stage. Keep every other stage, every agent and every mutation
worker in the VELDO-0208 Landlock domain.

In plain words: the control-plane suites need a whole Linux machine with its own systemd, and on
this host the only machine a single unprivileged user can safely give them is a virtual one. The
guest gets a real systemd, user manager, cgroups, ptrace and /dev/shm. Nothing it starts can
reach the host's user manager, because that manager is not in the guest. Every host path it sees
is read-only at the qemu device. qemu itself stays inside the Landlock domain, so the candidate
needs two independent escapes, guest-to-qemu and then out of Landlock, to get further than
today's gate already allows it.

Why the whole stage and not just the 29 suites: selftest runs every fragment in one namespace in
manifest order (scripts/selftest.py), and a selected subset is a partial run that can never count
as a gate pass. Moving the whole stage keeps the unchanged command, the unchanged summary line
and the unchanged evidence contract, needs no per-row bookkeeping, and gives every row the
stronger boundary.

## Design

### Components

1. **Guest kit** (owner-installed, read-only to every candidate). A kernel image and the
   matching module package, pinned by sha256 in the reviewed sandbox configuration
   (agent_sandbox.json, new `guest` block: kit directory, kernel digest, modules digest, memory,
   cpus, stage timeout). It is installed with `gate_guest.py kit install --kernel <deb>
   --modules <deb>` into ~/.local/share/veldo/guest/<kit-digest>/. The command extracts only
   vmlinuz and the five named modules, records their digests, and refuses any package whose digest
   is not the pinned one. Fetching the packages (`apt-get download`) is an owner act. The kit
   decouples the guest from host kernel upgrades, since /lib/modules/<running> disappears after one.
2. **gate_guest.py** (authority, engine canon plus synced copy). It has the same interface and
   exit contract as gate_candidate.py: `gate_guest.py --root <worktree> -- <command...>`. It:
   - decides availability first (one function, one named reason, nothing booted on refusal);
   - builds the initramfs in its scratch from the kit modules, /usr/bin/busybox and
     gate_guest_init.sh;
   - creates a sparse scratch disk image in its scratch;
   - starts qemu inside a Landlock domain built by agent_sandbox.grants_for with the gate profile,
     plus the kit (read), /dev/kvm (read, write, ioctl) and its scratch (write). Its flags are
     `-sandbox on,...`, -nodefaults, -nic none, -no-reboot, accel=kvm, the pinned memory and
     cpus, and a host-side wall-clock limit;
   - streams the stage's output port to its stdout as it arrives, reads the status port, kills
     and reaps qemu, and removes scratch.
3. **gate_guest_init.sh** (authority). The initramfs init: it loads the five modules, mounts every
   share read-only (qemu readonly=on is the first barrier, the ro mount the second), builds the
   tmpfs root, the /etc overlay (guest-private shadow and gshadow, empty fstab, crypttab and
   machine-id, no host *.wants), the home directory and the scratch disk (mkfs.ext4 from the
   shared /usr, mounted at /var/tmp and the stage's TMPDIR). It installs the veldo-gate target and
   service and switch_roots to systemd.
4. **Guest bootstrap** (veldo-gate.service, authority code). After dbus.socket and logind, it runs
   the stage as the host's uid through `runuser -l` (PAM, a logind session, the user's manager and
   session bus, /run/user/<uid>), in the worktree path, with the gate profile's environment (HOME
   in the guest, TMPDIR on the scratch disk, no host credentials). The stage writes stdout and
   stderr to the `veldo.out` port. When the stage exits, the bootstrap terminates the user's
   session and slice (`loginctl terminate-user`, then `systemctl kill` the slice). Only then does
   it write `status <exit>` to the root-only `veldo.status` port and power off.
5. **verify.sh placement.** A new declaration form, `required:guest:<command>`, routes the stage
   through `veldo_guest` (gate_guest.py) instead of `veldo_candidate`. This repository declares
   `CHECK_unit="required:guest:python3 scripts/selftest.py"` and
   `CHECK_integration="required:guest:python3 scripts/check_first_use.py"`. The engine template
   accepts the form, and adopters opt in per check. A stand-down prints
   `== unit: STOOD DOWN guest_unavailable:<reason> (not proven)` and sets FAIL=1. The stamp and gate
   event record `guest: {stage: {kit, boot_s, stage_s, status_source}}` or
   `stood_down: {stage: reason}`.

### Shares (all read-only, at the same absolute paths as on the host)

/usr and /etc (as in the gate profile's read roots), the worktree, its Git common directory (from
the authority's validated marker, VELDO-0208 Git boundary), the authority checkout, and the gate
profile's optional read roots (CLI directories, the locked graph runtime). Never shared: the reuse
store and its key, deny_read paths, ~/.ssh, the rest of $HOME, /run, /dev and /tmp of the host.
The share list is computed from the same `grants_for` the host domain uses, so the two placements
cannot drift. A grant with write access becomes a guest-local writable location, never a shared one.

### Data flow

verify.sh -> gate_guest.py (host, authority) -> availability -> initramfs and disk in scratch
-> qemu (in Landlock) -> guest kernel -> init (authority) -> systemd -> veldo-gate.service
(authority) -> runuser stage (candidate, guest uid = host uid) -> `veldo.out` -> gate_guest.py
stdout -> verify.sh. The exit is `veldo.status` (written by the authority bootstrap) ->
gate_guest.py exit code.

### Failure modes

| Condition | Result |
|---|---|
| no /dev/kvm or no access, no qemu, kit absent, kit digest mismatch, module or busybox missing | STOOD DOWN guest_unavailable:<reason>, red, nothing booted |
| kernel or init fails to boot, no status within the boot limit | red guest_boot_failed, with the serial tail |
| stage exceeds the stage limit | qemu killed, red guest_timeout |
| guest powers off or crashes without status | red guest_status_missing |
| guest out of memory | stage fails inside the guest, or no status: red either way |
| candidate prints a fake status line | ignored: the verdict comes from veldo.status only |
| guest-to-qemu escape | lands in the gate's Landlock domain (write scratch only, no store, no services) |

The guest's verdict is the candidate's own test verdict, exactly as in the host domain today. The
boundary protects the host, the store, the key and the authority. It does not make a candidate's
tests honest; review does that (VELDO-0208, Trust boundary).

### Out of scope, recorded

- Mutation workers stay in the worker profile. A mutation case whose suite needs the user manager
  will fail there in the same way. Proving those cases needs a guest-placed worker, where the
  authority's trace runs as guest root over a non-root worker. That is a follow-on
  specification, not this one.
- The host domain's seccomp list keeps refusing ptrace. With the unit stage in the guest, no gate
  stage needs ptrace on the host.
- Measured but not changed here: the broker's abstract-bind refusal breaks every sd-bus client in
  the host domain. Only O5 needed that.

## The three unclassified suites

- **62_0045 (pip wheel refusal rows): a simple confinement mismatch, fixed.** The suite's fixed
  pip environment dropped TMPDIR, so pip's uninstall stash fell back to /tmp, which the domain does
  not grant ("No usable temporary directory found in ['/tmp', ...]"). Every wheel row then failed.
  The pip environment now names the fixture's own temporary directory. Confined: 47 passed, 0
  failed. Alone: 47 passed, 0 failed.
- **82_0085 (concurrent publication): a simple confinement mismatch, fixed.** multiprocessing's
  Barrier, Lock and Queue are POSIX semaphores in /dev/shm, which the domain does not grant
  (PermissionError 13 at creation). Same class as fcb9d906. shared.py gains ForkLock and
  ForkBarrier on pipes, and the region answers on one Pipe per racer. The semantics were checked
  across forks: the barrier held the early party 1.00 s for a late one, an abort and a timeout
  both break it for the other party, and the lock serialised two holders. Confined: 41 passed, 0
  failed. Alone: 41 passed, 0 failed.
- **65_0067 (custody: worker cannot read the key): not a simple mismatch; it needs the guest.**
  The product's custody wrapper (control_keys_custody.grants) builds its Landlock allowlist by
  listing every ancestor of the protected directory up to /. In the gate domain, / and /tmp
  cannot be listed (no READ_DIR there), so the wrapper granted 4 paths instead of 109,517, and
  the confined worker could not even exec python (EACCES). Fixing that in place would mean
  granting directory listing over all of / to every candidate. In the guest it passes (35/0).

## Acceptance tests (suite 102_veldo_0209_guest_gate)

- guest-escape/* (AC1): each planted act and its expected refusal, observed both from inside the
  guest and on the host afterwards:
  - a transient service and a scope started with systemd-run --user write the host home path and
    the store path, and nothing appears on the host;
  - writes to the worktree, the common directory, the authority checkout, /usr and /etc return
    EROFS;
  - the host's /run/user/<uid>/bus and systemd/private are absent in the guest, and the guest's
    own are the guest's;
  - the store, key, ~/.ssh and every deny_read path are absent;
  - `ip -o link` shows lo only, and a TCP connect to a routable address fails;
  - qemu started with the same grants and a planted `-chardev file` outside scratch is refused
    by Landlock.
- guest-legs/* (AC2): suites 62_0039, 63_0040, 65_0067, 82_0085 and 100_0207, plus one full guest
  unit stage. Its counts, its duration and the host-domain duration are recorded in
  proof/VELDO-0209.
- guest-standdown/* (AC3): a configured /dev/kvm path that does not exist, a qemu name that
  resolves to nothing, an absent kit, a kit with one changed byte, and a kit missing 9p.ko. Each
  produces its named reason, a red gate line and no boot.
- guest-status/* (AC4): a stage that prints `status 0` and exits 1 is red; a stage that kills its
  parent and exits 0 is judged only by the bootstrap's status; a bootstrap that powers off before
  writing status gives guest_status_missing; a stage that sleeps past the limit gives
  guest_timeout, with qemu reaped and scratch removed.

## Open decisions for the owner

1. The kit source: Ubuntu's unsigned kernel and modules packages for the running series, fetched
   by the owner with `apt-get download` and pinned by sha256 (the experiment used
   linux-image-unsigned-7.0.0-30-generic), or another source.
2. Guest memory, cpus and stage limit. The experiment used 4 GiB and 4 cpus. The proof will
   record what the full unit stage needs.
3. Whether integration's nested unit run boots its own guest or runs in place inside the
   integration stage's guest. The design is "in place": it is already inside the guest.

## Reproduction of the measurements

Every experiment ran under /tmp/v209-* and was removed afterwards; nothing was left running.

- Guest kit: `apt-get download linux-image-unsigned-7.0.0-30-generic; dpkg-deb -x <deb> k`, then
  `zstd -d $(modinfo -n M)` for M in netfs 9pnet 9pnet_virtio 9p overlay.
- Initramfs init: busybox --install; mount proc, sys, devtmpfs; insmod the five modules; tmpfs at
  /newroot; `mount -t 9p -o trans=virtio,version=9p2000.L,ro,msize=524288,cache=loose` for usr,
  etc (as the overlay's lower layer) and each read-only share at its host path; symlink
  bin, sbin, lib and lib64 to usr; empty machine-id, fstab and crypttab; shadow and gshadow
  generated from passwd and group with locked entries; remove /etc/systemd/system/*.wants and
  default.target; install the gate target and service; `exec switch_root /newroot
  /usr/lib/systemd/systemd`.
- qemu: `-machine q35,accel=kvm -cpu host -m 4096 -smp 4 -nodefaults -display none -no-reboot
  -nic none -serial file:<log> -kernel vmlinuz -initrd initrd.gz -append "console=ttyS0
  rdinit=/init systemd.show_status=0 systemd.unit=<gate target>" -virtfs
  local,path=<p>,mount_tag=<t>,security_model=none,readonly=on` per share. For the defence-in-depth
  run, add `-sandbox on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny` and
  start it after landlock_restrict_self with the grants listed under O9.
- Guest service: Type=oneshot, After and Requires dbus.socket and systemd-logind.service,
  ExecStart is the probe and ExecStartPost is `systemctl poweroff --force`. The probe runs
  `runuser -l <user> -c 'cd <worktree>; python3 scripts/selftest.py --suite <name>'`.
- O5 prototype: a Python parent in `systemd-run --user --scope -p Delegate=yes` makes supervisor/,
  domain/gate and domain/manager, enables +memory +pids +cpu, forks with agent_sandbox.fork_brokered,
  and confines the child with agent_sandbox.landlock(gate profile, plus domain/ read and write). The
  child moves a subshell into domain/manager and execs `/usr/lib/systemd/systemd --user` with
  XDG_RUNTIME_DIR and SYSTEMD_UNIT_PATH in scratch. The pull-in probe writes the pid of an
  outside `sleep` into domain/pull/cgroup.procs.
