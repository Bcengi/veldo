---
schema: veldo.spec/v1
id: VELDO-0210
title: The agent profile runs a real Claude or Codex builder and keeps today's capabilities
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0208]
placement: [enforcement]
protected_paths: ["engine/scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.json", "scripts/agent_sandbox.py", "scripts/agent_sandbox.json"]
footprint:
  - "engine/scripts/agent_sandbox.py"
  - "engine/scripts/agent_sandbox.json"
  - "engine/scripts/veldo_userns.c"
  - "engine/scripts/veldo-userns.apparmor"
  - "scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
  - "scripts/veldo_userns.c"
  - "scripts/veldo-userns.apparmor"
  - "scripts/suites/101_veldo_0208_landing_reuse.py"
  - "scripts/suites/102_veldo_0210_agent_profile_runtime.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0210-agent-profile-runtime.md"
  - "specs/index.md"
  - "proof/VELDO-0210/*"
behavior_bearing: true
observability:
  logs: >
    The launcher names on stderr each credential it wrote back, each changed credential it did not
    write back and why (not a JSON object, not a private regular file, its source changed during the
    run), an unknown client, each entry it removed from the agent's state and each it could not
    check, and each stale scratch directory it could not remove.
  metrics: None beyond the run's exit status; a run stopped by a signal exits 128 plus its number.
  traces: Not applicable; the launcher keeps no state beyond the run.
  error_taxonomy: >
    An unknown client, a client place that is not an absolute directory, a client file outside the
    client's own state directory, a credential whose source lies in the store or a protected path,
    or a namespace helper that is unusable, cannot create the namespace, leaves a capability or does
    not report the tree's init ready within 60 seconds (the message names the owner's setup command)
    refuses the start (exit 2) before any command runs.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: an agent-profile process reads /proc (never writes it) and reads the DNS resolver
      configuration: /etc/resolv.conf and, when it links into /run/systemd/resolve, that directory,
      read only, so the file systemd-resolved renames over stub-resolv.conf on a network change is
      readable in a run already going. Nothing else under /run is readable. Set: read of
      /proc/self/status, write of /proc/self/comm, read of the launcher's /proc/<pid>/environ, read
      of the resolver link, its target and a sibling, a write and a create in the resolver
      directory, a read after the target is replaced by rename, a listing of its parent and of
      /run/user/<uid>. Completeness: one grant adds /proc for every profile in landlock(); one
      function (resolver_grants) derives the only /run grant from the link. Test rows runtime/* in
      suite 102.
    falsified_by: Grant only the one file the link names; runtime/resolver-replaced-by-rename-readable goes red.
  - id: AC2
    text: >
      Claim: the launcher copies the selected client's credential files into the private scratch and,
      after the run (normal exit, failure or a stop signal), writes each one back over its source
      atomically, only if the CLI changed it and it is still one JSON object, so a token refresh
      during a run never logs the account out, and only if the source still holds the bytes copied
      in at the start, so a login made during the run is never overwritten. Set: a simulated
      refresh, an unchanged file, an invalid rewrite, a rewrite planted through a link to another
      credential, a changed non-credential seed, a refresh followed by a stop signal, a refresh
      while the account logs in again outside the run, a second write-back waiting on the lock of the
      first, and a rewrite nested past the parser's
      recursion limit in a run that fails, whose exit status is kept. Completeness: the only files
      written outside the scratch are the sources recorded at copy time; the copy is read component
      by component without following links. Test rows credentials/* in suite 102.
    falsified_by: Write back without the JSON check or follow links in the scratch; a credentials row goes red.
  - id: AC3
    text: >
      Claim: the agent profile keeps today's capabilities and nothing more. Claude's account state
      (its settings, its .claude.json, its plugin list) is copied in from the directory the runner
      names (CLAUDE_CONFIG_DIR, else the default), its installed plugins, marketplaces and skills
      are read-only and linked into the scratch, and its MCP servers use the network the profile
      already allows. Projects in the reviewed project_read_roots list of agent_sandbox.json are
      readable and never writable. Codex credentials enter only Codex runs and Claude credentials
      only Claude runs. Set: reads through the links and the absolute plugin paths, writes to them,
      a project root read and write, each client's run looking for the other client's credentials,
      a run with no client, and the refusals VELDO-0208 keeps (writes outside the worktree and
      scratch, the store, the runner, the authority), a read link at, above or beneath a seed or
      credential destination or another link, and a seed whose scratch path holds a link.
      Completeness: every file a client receives is declared under that client in the configuration
      and must lie under its own state directory (.claude or .codex); every seed is written before
      any link exists, component by component without following a link. Test rows capabilities/* in
      suite 102.
    falsified_by: Copy every client's credentials into every run; capabilities/claude-run-has-no-codex-credentials goes red.
  - id: AC4
    text: >
      Claim: the launcher's scratch directory is removed when it exits, including when it is stopped
      by TERM, INT or HUP, and a stop that lands between the fork and the child's registration is
      forwarded to the child once it is registered; a launcher killed outright takes its agent with
      it; a scratch directory left behind is removed by the next start once it is more than a day
      old, unless a live launcher, its agent or a descendant that kept the agent's descriptors
      holds it. Set: each stop signal, a child that ignores TERM, a stop sent the instant the fork
      returns, a launcher killed outright with a descendant that outlives the agent (in the tree's
      own PID namespace the descendant ends with it), a live launcher's aged scratch, a stale directory with a shut subdirectory, a recent one, a stale one
      a live launcher holds, a stale link and a stale plain file. Completeness: every launch goes
      through launch(), which sweeps before creating its own scratch and holds a shared lock on it
      until removal; the confined command holds a second shared lock on its own descriptor. Test
      rows scratch/* in suite 102.
    falsified_by: >
      Skip the lock test in the sweep, the signal block across the fork or PR_SET_PDEATHSIG;
      scratch/live-scratch-kept, scratch/stop-during-fork-forwarded-to-child or
      scratch/killed-launcher-takes-its-agent goes red.
  - id: AC5
    text: >
      Claim: the selected client's transcripts, sessions, history and memories for this worktree
      outlive the scratch, and no run can reach another project's or the account-wide ones: Claude
      reads and writes only projects/<folder>, the folder Claude Code itself names for the worktree
      (claude_project, checked against two real Claude Code 2.1.290 runs), never projects/ itself
      or another project's folder (whose memory/MEMORY.md the next unconfined run loads as
      instructions); Codex reads and writes only veldo-agent-state/<folder>/ under CODEX_HOME
      (sessions/, memories/, history.jsonl), never the account-wide sessions/, memories/ or
      history.jsonl the unconfined CLI uses. Before the grant and again once the confined tree is
      gone, before any unconfined process could read it, clean_state removes and names on stderr
      every symbolic link, every regular file with another link and every special file in that
      state, at any depth and in directories the run shut. Set: a second run of each client in the
      same worktree reading what the first wrote, a run in another worktree seeing none of it,
      writes and creates in another project's memory folder, a listing of projects/, writes and
      creates elsewhere in the configuration directory and in the account-wide Codex state, a
      credential read, a write through .. from a state directory, a read through a link planted in
      one, a planted link, FIFO, hard link and link in a shut directory removed and reported, the
      sweep on its own over 1100 nested directories, and the refusals of a state entry outside the
      configuration directory, one holding a credential and one that is a link. Completeness:
      state_dirs and state_files under each client in agent_sandbox.json are the only write grants
      outside the worktree and scratch; state_grants() refuses any that overlaps the store, a
      protected or denied path, a credential source or the worktree, or that clean_state cannot
      check. Test rows state/* in suite 102.
    falsified_by: >
      Grant projects/ instead of the worktree's folder; state/claude-other-project-memory-refused goes
      red. Skip clean_state after the run; state/planted-entries-removed-and-reported goes red.
  - id: AC6
    text: >
      Claim: the agent and gate profiles run the confined tree in its own PID namespace with its own
      procfs, so /proc inside shows only the sandbox's processes and no host process's command line,
      and nothing in the tree holds or can get a capability or a user namespace. The launcher's child
      executes the fixed, root-owned, statically built helper /usr/local/lib/veldo/veldo-userns
      (scripts/veldo_userns.c) with the launcher's own path and a context descriptor; the helper
      creates a user namespace mapping only this account's uid and gid, each to itself, then the
      mount and PID namespaces, and forks the namespace's init, which mounts a fresh procfs read only
      over /proc, drops every capability (bounding, ambient, effective, permitted, inheritable;
      securebits locked) and sets no_new_privs before it executes python3 -I -S agent_sandbox.py
      namespace-init. The host's AppArmor policy (scripts/veldo-userns.apparmor) lets only the helper
      create a user namespace and runs whatever it executes under the child profile
      veldo-userns-child, which denies every capability, every user namespace, mounts and profile
      changes, and is inherited by every program executed below it. The init refuses to go on unless
      it is PID 1 of a read-only fresh procfs, only the identity map exists, every capability set is
      empty, no_new_privs is set and (with AppArmor) its label is veldo-userns-child in enforce mode;
      it then reports ready and forks the agent, which confines itself (seccomp, Landlock) and execs.
      The launcher refuses unless the init reports ready within 60 seconds and the helper's own
      process holds no capability, and kills the tree first. The helper is never taken from the
      environment, the configuration or the candidate; one that is absent, not a regular file,
      set-user-ID or with file capabilities, not owned by root, writable by anyone but root (or in a
      directory that is) refuses the start (exit 2) naming the owner's one-time setup command, as
      does a host without the setup; host /proc is never the fallback. A stop (TERM, INT, HUP)
      during the start ends it at once: the tree, a hung helper with it, is killed and the launcher
      exits 128 plus the signal number. A launcher already inside a tree the outer launcher made
      (it inherited the outer launcher's marker, a descriptor of the outer launcher's PID namespace
      that is a proper ancestor of its own; label veldo-userns-child in enforce mode; a PID
      namespace other than the host's whose procfs is /proc; no capability) creates none, and its
      init is a child subreaper that kills and reaps every remaining descendant when the agent ends;
      any other private PID namespace (a container's, a systemd PrivatePIDs one) has no marker and
      does not count. Set: the pids /proc lists inside, a host process
      started with a marker argument read by pid and found by scanning, uid, gid, every capability
      set, no_new_privs and the AppArmor label inside, a clone(CLONE_NEWUSER) by the agent, the owner
      of a file created inside, /proc's mount options, an orphan reaped by the init, a descendant
      that left the agent's process group after the agent exits, the same for the gate profile; the
      helper source dropping everything after the procfs mount and before exec, its relays, its
      reproducible static build and its refusals (arguments, entry point's name, path, owners); the
      policy compiling and its child profile's denials; a container label, complain mode and a forged
      tree (the child label, no capability, only its own namespace descriptors) not counting as
      nested; the marker created before the helper and kept by the tree; a subreaper ending a setsid
      descendant; the start and handoff waits timing out; TERM, INT and HUP ending a start whose
      helper hangs, in both profiles; a missing, user-owned, user-writable and linked helper, a root-owned program that is not
      the helper, and every start on a host without the setup. Completeness: every launch goes
      through prepared_launch, whose child executes the helper (or, nested, forks the init) and
      whose parent waits in await_start; helper_problem is its only check of the helper and
      namespace_problem the init's only check of its namespace. Test rows namespace/* in suite 102,
      skipped with the launcher's reason where the setup has not been run; signals, cleanup and
      write-back keep their AC2 and AC4 rows. The AppArmor part is proven on the host by the
      owner's one-time self-test (agent_sandbox.py namespace-selftest), which needs the setup.
    falsified_by: >
      Skip the procfs mount; namespace/proc-lists-only-sandbox-pids goes red. Map root instead of the
      current user; namespace/ids-equal-outside goes red. Keep the bounding set; namespace/no-capability-in-any-set
      goes red. Drop helper_problem; namespace/user-writable-helper-refused goes red. Let the child
      profile allow userns; namespace/policy-child-denies-capabilities-and-user-namespaces and
      namespace/no-user-namespace-for-the-agent go red. Count any private PID namespace as nested;
      namespace/only-the-helpers-tree-counts-as-nested goes red. Wait out the start despite a stop;
      namespace/stop-ends-a-hung-helper-* go red.
required_evidence: [unit]
rollback: Revert the four protected files to a9fb11d6; runners fall back to their documented unconfined switch. On the host, `sudo rm /usr/local/lib/veldo/veldo-userns && sudo apparmor_parser -R /etc/apparmor.d/veldo-userns && sudo rm /etc/apparmor.d/veldo-userns`.
---

## Intent

The agent profile landed by VELDO-0208 cannot run a real builder: Claude's runtime aborts without
/proc and neither CLI resolves a host name, because /etc/resolv.conf links into /run. The runner
wiring (myday 9375619, report research/claude-runs/20261007-113532-acct3.txt) also found that the
profile reduced what agents can do: a token refresh during a run is lost, every Claude run carries
Codex credentials, Claude runs without its plugins and skills, and agents cannot read other project
directories today's builders read.

Owner's rules: agents keep exactly the capabilities they have today; the confinement only prevents
escaping the worktree and the protected paths. Single user, no separate OS user, no system service,
no detached process.

## Amendment

This amends VELDO-0208's agent profile in four statements: /proc is no longer excluded from the
agent profile's grants (read only, as in the gate and worker profiles); /run stays excluded except
the resolver directory /run/systemd/resolve, read only; the selected client's credential files
are written back after a refresh instead of never; and the selected client's declared state
entries in its configuration directory are writable, the only writes outside the worktree and
scratch. It also amends VELDO-0208's "no root helper": the agent and gate profiles need the
owner-installed, root-owned helper veldo-userns (built from this repository, not setuid, run as
this account) and its AppArmor policy to create their namespaces, owner decision Telegram 32539.
The first design (a root-owned copy of util-linux unshare under a profile flags=(unconfined)
{userns}, installed 32542) let any program it ran keep user-namespace rights; the owner removed
that profile (Telegram 32561-32562) and this design replaces it. Every other VELDO-0208 boundary is
unchanged.

## Design

- Runtime. landlock() grants /proc read-only to every profile, as it did for gate and worker.
  Landlock's ptrace scope still refuses another domain's environ, fd, root, cwd, mem and maps.
  resolver_grants() reads where /etc/resolv.conf points; when that is beneath
  /run/systemd/resolve, the directory itself is granted read-only, never its parent and nothing
  else under /run. A grant binds the inode it was made for, and systemd-resolved replaces
  stub-resolv.conf by rename on every network change, so a grant of the one file would stop
  matching mid-run. /run stays blocked for every other read root. Name lookups that try a service
  socket (mdns, resolved's varlink sockets in that same directory) are refused by the IPC filter and
  fall through to DNS. Gate and worker profiles are unchanged apart from the shared /proc line they already had.
- PID namespace (AC6, owner decision Telegram 32539 after the review found a host process's
  command line, a live tunnel token, readable through /proc). Unprivileged user namespaces are
  blocked on the host (kernel.apparmor_restrict_unprivileged_userns=1, VELDO-0209). The helper is a
  purpose-built static C program, scripts/veldo_userns.c, installed root-owned (0755, not setuid)
  at /usr/local/lib/veldo/veldo-userns. It takes exactly two arguments: the launcher's own path
  (absolute, canonical, a regular file named agent_sandbox.py, owned by root or this account and
  writable by no other account, in directories with the same property or root-owned and sticky;
  group write is accepted only for the account's own primary group) and a descriptor number (or
  `selftest`). It: sets PR_SET_PDEATHSIG; blocks TERM, INT, HUP and CHLD, noting which stops were
  ignored when it started; creates a user namespace and writes setgroups deny and the uid and gid
  maps `<id> <id> 1`; creates the mount and PID namespaces and makes every mount private; forks the
  init. The init waits on a pipe until the parent has dropped its capabilities and closed its
  descriptors, sets PR_SET_PDEATHSIG, mounts procfs on /proc read only (nosuid, nodev, noexec),
  locks the securebits (noroot, no setuid fixup, keep caps, no ambient raise), drops the whole
  bounding set, clears the ambient set, clears the effective, permitted and inheritable sets, sets
  no_new_privs and executes `/usr/bin/python3 -I -S <launcher> namespace-init <descriptor>` with no
  environment but LC_CTYPE. The parent drops the same, closes every descriptor above stderr,
  relays TERM, INT and HUP (unless ignored at its start) to the init as SIGRTMIN, SIGRTMIN+1 and
  SIGRTMIN+2, and exits with the init's status. Static, it has no dynamic loader, so LD_PRELOAD and
  the like cannot run code with its rights.
  The AppArmor policy, scripts/veldo-userns.apparmor, installed as /etc/apparmor.d/veldo-userns,
  attaches veldo-userns to the helper's path with userns, the four capabilities it needs inside its
  own namespace, the two mounts it makes, signals, and no tracing of it (so no process injects code
  with its rights); the only program it may execute, /usr/bin/python3, transitions to the child
  profile veldo-userns-child, as Ubuntu's bwrap-userns-restrict runs what bwrap starts under
  unpriv_bwrap. The child profile allows files, network, Unix sockets, signals, tracing (the gate's
  broker reads the agent's memory and descriptors) and IPC, denies every capability, every user
  namespace, every mount and profile change, and every program executed below it inherits it
  (ix). Nothing the helper runs can therefore create or use a user namespace with capabilities,
  whatever it executes. The policy:

  # AppArmor policy for the agent sandbox's namespace helper (VELDO-0210 AC6), installed by the
  # owner's one-time setup as /etc/apparmor.d/veldo-userns.
  #
  # veldo-userns is the only program on the host this lets create a user namespace. It needs the
  # capabilities below inside that namespace only, to map the account to itself, make the mount and
  # PID namespaces and mount their procfs. Whatever it executes (only /usr/bin/python3) runs under
  # veldo-userns-child, as Ubuntu's bwrap-userns-restrict runs what bwrap starts under unpriv_bwrap:
  # no capability, no user namespace, no mount, no profile change, and every program that child
  # executes inherits the same profile. So nothing the helper runs can create or use a user
  # namespace with capabilities. No process may trace the helper, so no code runs with its rights.

  abi <abi/4.0>,
  include <tunables/global>

  profile veldo-userns /usr/local/lib/veldo/veldo-userns flags=(attach_disconnected, mediate_deleted) {
    userns,
    capability sys_admin,
    capability setuid,
    capability setgid,
    capability setpcap,
    mount options=(rw, rprivate) -> /,
    mount fstype=proc options=(ro, nosuid, nodev, noexec) proc -> /proc/,
    file rwlkm /{**,},
    signal,
    ptrace (readby),
    audit deny ptrace (tracedby),
    /usr/bin/python3* px -> veldo-userns-child,
  }

  profile veldo-userns-child flags=(attach_disconnected, mediate_deleted) {
    file rwlkm /{**,},
    /** ix,
    network,
    unix,
    signal,
    ptrace,
    mqueue,
    io_uring,
    dbus,
    audit deny capability,
    audit deny userns,
    audit deny change_profile,
    audit deny mount,
    audit deny umount,
    audit deny pivot_root,
  }

  The owner's one-time setup, one line run from the repository root (docs/veldo-userns-setup.txt
  carries the same line; every refusal prints it, as one line to paste, with `cd <checkout> && `
  first). It builds the helper, installs it root-owned, installs the policy file that holds both
  profiles (veldo-userns and veldo-userns-child) root-owned, loads both with apparmor_parser -r,
  retires the first design's unshare copy, and runs the self-test. Its last step is the self-test, which proves through the installed helper that
  the namespace is as the init requires and that a program run through it cannot sethostname here or
  in new user and UTS namespaces, cannot create a UTS or user namespace, and cannot bring up an
  interface in new user and network namespaces, directly or through executed programs (util-linux
  unshare, hostname, ip), and that the helper's own process holds no capability:

  `d=$(mktemp -d) && cc -std=c11 -O2 -Wall -Wextra -Werror -static -ffile-prefix-map="$PWD"=. -o "$d/veldo-userns" scripts/veldo_userns.c && sudo install -D -o root -g root -m 0755 "$d/veldo-userns" /usr/local/lib/veldo/veldo-userns && sudo install -o root -g root -m 0644 scripts/veldo-userns.apparmor /etc/apparmor.d/veldo-userns && sudo apparmor_parser -r /etc/apparmor.d/veldo-userns && sudo rm -f /usr/local/lib/veldo/veldo-unshare && rm -r "$d" && python3 -I -S scripts/agent_sandbox.py namespace-selftest`

  The launcher's child (C) blocks the stops, CHLD and the relay signals, sets each stop's
  disposition to default when the launcher forwards it and to ignored when the launcher inherited
  it ignored (the helper reads them across its exec), takes its own session, sets PR_SET_PDEATHSIG
  and checks the launcher is its parent, holds its shared lock on the scratch, opens the launcher's
  /proc (O_PATH) and pidfds of the launcher and of itself, opens the tree's marker (its own PID
  namespace, /proc/self/ns/pid, the parent of the one the helper makes, kept by every process of
  the tree), writes the launch's context (worktree,
  command, environment, grants, profile, protected paths, descriptors, signal mask, ids) to a memory
  file and executes the helper with that descriptor. The init (G, PID 1) reads the context, checks
  namespace_problem, checks through the pidfds that the launcher and the helper are alive, writes
  one byte to the launcher's ready pipe and forks the agent (A), which takes its own process group,
  reads the pid the launcher sees it by from the launcher's /proc (for the gate profile's broker),
  confines itself as before and execs. Landlock's /proc grant binds the fresh procfs, so the host
  procfs beneath it is unreachable even by path. The launcher waits for the ready byte at most 60
  seconds, in slices of a tenth of a second; a stop meanwhile is forwarded to the group and ends
  the wait at once, and the group, a hung helper with it, is killed (nothing has started the
  command yet). Then it reads the helper's /proc status: every capability set empty and no_new_privs set.
  Otherwise it kills the group, writes back and cleans up, and refuses (exit 2) with the setup
  command; a stop during the start still exits 128 plus its number. The gate profile's handoff read
  in fork_brokered is bounded by the same 60 seconds and ends as soon as a stop is pending (the
  launcher still blocks the stops there), so a stop ends the gate profile's start the same way.
  Signals: the launcher stops C's process group as before. The helper and G keep TERM, INT and HUP
  blocked and take them with sigwaitinfo; the helper relays each the launcher forwards to G as a
  real-time signal, and G forwards it to A's process group, so the agent gets each stop once, even
  one that came before it existed. G discards the stop signals it receives directly. G reaps every
  process of the namespace, and when A exits G exits with A's status; the kernel then kills
  whatever is left in the namespace, including processes that left A's process group. The helper
  and G set PR_SET_PDEATHSIG and G checks the pidfds, so a launcher killed outright takes the
  helper, G and with G the whole namespace. A keeps its own PR_SET_PDEATHSIG after confinement.
  Unix addresses, terminals and the bind helper are unchanged: the mount namespace is a copy, only
  /proc differs.
  A launcher already inside a tree the outer launcher made creates no namespace (nested_namespace):
  it inherited the marker (launcher_marker: an open descriptor of a PID namespace, NS_GET_NSTYPE,
  that is not its own and in which NS_GET_PID_IN_PIDNS finds its pid, so a proper ancestor of its
  own; only nsfs descriptors get the ioctls), its AppArmor label is veldo-userns-child in enforce
  mode, which only an exec through the root-owned helper gives and which no process can leave, its
  /proc/self/ns/pid is not the initial pid:[4026531836], its /proc/self is its own pid, and it holds
  no capability. The marker cannot be forged from inside: a process in a PID namespace cannot open
  an ancestor (NS_GET_PARENT refuses it, its procfs shows no process outside), so only a process
  outside hands one in. A container's or a systemd PrivatePIDs namespace has none and does not
  count, whatever its label: there the launcher uses the helper as on the host. The nested
  launcher hands on the marker it inherited. Its C forks G itself and relays as the helper does;
  G is a child subreaper (PR_SET_CHILD_SUBREAPER), so a descendant that leaves the agent's session
  is reaped by it, and when A exits G kills every remaining descendant (each child in
  /proc/self/task/<pid>/children, then the ones that become its children) before it exits. The
  nested tree sees the outer tree's processes, never the host's.
- Clients. agent_sandbox.json gains `clients`. Each client names its places (an environment variable
  the runner may set, else a default under the account's home), its `credentials`, its `seed_files`
  and its `read_links`. The launcher's client option selects one (claude or codex); without it no
  client file is copied. The top-level seed_files keep only what every agent gets (.gitconfig).
  Every client destination must lie under that client's own state directory. The gate profile
  takes no client.
- Credentials. Source bytes are read once and written to the scratch copy (mode 0600). After the
  confined group is gone, each copy is opened component by component with O_NOFOLLOW and must be a
  regular file with one link, at most 1 MiB. Changed bytes that parse as one JSON object replace
  the source through a temporary file in the source's directory, fsync and rename; just before the
  rename the source is read again and replaced only if it still holds the bytes copied in, otherwise
  the copy is dropped and the launcher says so. The re-read and the rename run under an exclusive
  flock on the sibling file <source>.veldo-lock (left in place), so two launchers writing back one
  source never interleave them. A copy that fails to parse for any reason (a
  syntax error, nesting past the recursion limit) is not written back, and nothing the write-back
  meets replaces the run's own exit status. Every credential
  source of every client is added to deny_read for the run.
- Capabilities. Read links: Claude's plugins/cache, plugins/marketplaces, plugins/synced, skills,
  agents and commands; Codex's skills, rules and plugins/cache. Each target is granted read-only
  (through the same filter as every read root) and linked into the scratch; an absent target is
  skipped. Every seed and credential is written first, each directory component of its scratch
  path opened (or created 0700) with O_NOFOLLOW and the file created O_EXCL beneath it; the links
  are made afterwards the same way. A read link at, above or beneath a seed or credential
  destination, or another read link, refuses the start. project_read_roots (absent roots skipped, '~' is the account's home) are read-only grants
  in the agent profile only. The runner accounts measured on 2026-10-07 have no stdio MCP server;
  their MCP servers are the claude.ai connectors, reached over TCP/TLS, which the profile already
  allows. A stdio server configured later runs inside the domain with the same grants.
- State. Each client may declare `state_dirs` and `state_files`, which must lie strictly beneath its
  `home` place (CLAUDE_CONFIG_DIR or CODEX_HOME, the runner's configuration directory for that
  account); '{project}' in an entry is the worktree's Claude project folder name. Claude's is
  projects/{project} (transcripts), the one folder Claude Code writes for this working directory:
  every UTF-16 code unit of the resolved worktree path that is not an ASCII letter or digit becomes
  '-', and past 200 characters the name is cut and followed by '-' and the base-36 absolute value
  of the path's 32-bit string hash, as Claude Code 2.1.290 computes it. The launcher drops
  CLAUDE_CODE_PROJECT_DIR_NAME from the agent's environment, which would name another folder, and
  sets PWD to the worktree. Claude's auto-memory of a linked worktree lives in the main checkout's
  folder, which is not granted. Codex's are veldo-agent-state/{project}/sessions, memories and
  history.jsonl under CODEX_HOME, linked where Codex looks for its own; the unconfined Codex never
  reads that subtree, and the confined one never sees the account-wide sessions/, memories/ or
  history.jsonl. An absent entry is created with every directory above it up to the configuration
  directory (directories 0700, file 0600, each component opened without following a link) unless
  the configuration directory itself is absent; an entry that is a link, of the other kind,
  resolves outside the configuration directory, or holds, is or lies beneath the store, a protected
  or denied path, a credential source or the worktree refuses the start. Each is granted read and
  write and linked into the scratch where the CLI looks for it, after every seed and through the
  same overlap check as the read links. The rest of the configuration directory is not granted at
  all. clean_state walks each entry before the grant (a run killed outright left it unchecked) and
  again in the launcher once the confined tree is gone, before the launcher exits: every symbolic
  link, regular file with more than one link and FIFO, socket or device is removed and named on
  stderr; a directory the run shut is opened up (owner rwx) first; nothing is followed; the walk
  holds one descriptor at a time and climbs back through '..', so no depth exhausts descriptors or
  path length. An entry it cannot check refuses the start, or is named on stderr after the run.
- Scratch. launch() sweeps the temporary directory for veldo-agent-* entries owned by this uid that
  are real directories, older than a day and not locked, and removes them (shut subdirectories are
  opened first, no link is followed). Its own scratch is created there and held with flock until
  removal, with a shared lock; the child opens the scratch again and holds its own shared lock,
  kept across exec, so the sweep's exclusive lock fails while the agent or any descendant holding
  that descriptor lives. TERM, INT and HUP (unless the launcher inherited them ignored) are blocked
  from before the fork until the parent has registered its child, then forwarded to the confined
  group; a group still alive ten seconds later is killed. The launcher then writes back
  credentials, removes the scratch and exits 128 plus the signal number. The child sets
  PR_SET_PDEATHSIG to SIGKILL and refuses the start if the launcher is already gone, and so do the
  namespace's init and the agent (the agent once confined, just before exec), so a launcher killed
  outright never leaves its agent running (AC6 has the chain).

## Accepted residuals

- A confined process can write any JSON object into its copy of the selected client's credential
  file, and that object replaces the account's file. The process already holds that credential;
  the write cannot reach any other file or the other client's credentials.
- A refresh inside a run rotates the account's refresh token, so until the write-back other
  sessions on that account hold a token the provider has already replaced and may have to refresh
  or log in again. When the source changed during the run, the run's refreshed token is dropped and
  the newer file kept. The re-read and the rename run under the launcher's
  lock file, which the CLIs do not take: a CLI's own write landing between them is replaced.
- The resolver directory's other entries are readable too: resolved's resolv.conf (the upstream
  servers) and the names of its varlink sockets and per-link state directory (mode 0700, owned by
  systemd-resolve, so unreadable to this account anyway).
- A confined process can write anything into its client's state for this worktree, which later
  sessions in this worktree read (a crafted transcript can be resumed by an unconfined Claude
  started in the same worktree, which reads that folder). It reaches no other project's folder and
  no account-wide Codex state. Links, extra hard links and special files it leaves are removed
  when the run ends; an unconfined session running in the same worktree at the same time can meet
  them while the run lasts. Concurrent runs in one worktree share its state, as unconfined runs
  do today. Two worktree paths that differ only in characters other than ASCII letters and digits
  have one Claude folder name, as they do for Claude itself.
- A confined Claude run in a linked worktree loses its auto-memory writes: Claude keeps that
  memory in the main checkout's folder, and granting it would let the run rewrite instructions an
  unconfined run of the main checkout loads.
- Codex's other state under CODEX_HOME (its SQLite stores, logs and caches) stays in the scratch
  and is lost at exit: a SQLite store needs its directory writable for its journal, and that
  directory holds auth.json.
- Writes Claude or Codex make to their plugin, marketplace or skill directories (marketplace
  updates, system skill installs) fail: those directories are outside the worktree.
- engine/scripts/agent_sandbox.json is byte-identical with this repository's copy (template sync),
  so the reviewed project_read_roots entry ships to adopters; an absent root grants nothing.
- A launcher nested in a tree the helper made creates no namespace, so its tree sees the outer
  tree's processes, never the host's. PR_SET_PDEATHSIG there reaches the agent and the init, whose
  end kills the agent's remaining descendants; a launcher killed outright with SIGKILL kills that
  init, and descendants of the nested agent then outlive it until the outer tree ends.
- The helper's entry check (name, path, owners) is a guard on what it executes, not the boundary:
  the account owns the launcher file and can change it. The boundary is that the helper drops every
  capability and sets no_new_privs before it executes anything, and that the child profile denies
  capabilities and user namespaces to whatever runs below it.
- Another process of this account that runs unconfined outside every tree (the owner's own shell,
  an unconfined CLI) holds every capability over the tree's user namespace, as the namespace's
  owner, and could join it; nothing inside the tree can, and none of the tree's processes reaches
  such a process.
- The marker lets a process of the tree translate its own pids into the outer launcher's PID
  namespace (NS_GET_PID_IN_PIDNS), so it learns the host pids of its own tree's processes; it
  cannot join, see or signal anything there (setns into an ancestor PID namespace is refused, and
  NS_GET_PARENT and NS_GET_USERNS from it are outside its scope).
- AppArmor part unproven here: the policy compiles (apparmor_parser -Q) and the helper builds
  reproducibly and refuses as specified, but loading the policy needs root; until the owner runs
  the setup and its self-test passes, the rows of a running tree are skipped and every start
  refuses.
- Inside the namespace, files owned by any uid or gid other than this account's show as 65534
  (nobody, nogroup), and so do the account's supplementary groups; access is still decided by the
  real ids.
- The host procfs stays mounted beneath the fresh one in the copied mount table: /proc/self/mounts
  lists it, the mount is locked to the namespace, and Landlock grants only the fresh one.
- The setup needs the owner once, with sudo, per host, and again after any change to
  scripts/veldo_userns.c or scripts/veldo-userns.apparmor; without it every agent and gate start
  refuses. The installed helper is the build the owner made, not the repository's current source.

## Out of scope

The runner scripts (myday codex_work.sh, claude_work.sh, agent_sandbox.sh), which pass the client
option and CLAUDE_CONFIG_DIR after review. The shared-alternate rule for repositories other than
this one. The gate and worker profiles' grants.

## Build and evidence limits

Only suites 99, 100, 101, 102, 64 and 69 run for this specification, sequentially in the foreground, plus
template sync, generated, lint, docs and validate.py all. The owner runs the full gate and lands
the stamp; no protected-path approval is recorded here.
