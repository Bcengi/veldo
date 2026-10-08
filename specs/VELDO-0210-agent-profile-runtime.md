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
protected_paths: ["engine/scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.json", "scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "engine/scripts/gate_candidate.py", "scripts/gate_candidate.py", "engine/scripts/check_gate_mutations.py", "scripts/check_gate_mutations.py", "engine/scripts/gate_legs.py", "scripts/gate_legs.py", "scripts/check_first_use.py", "scripts/suites/shared.py", "engine/.veldo/control_verification.py", ".veldo/control_verification.py", "scripts/mutation_sandbox.py", "engine/scripts/mutation_sandbox.py", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/case_reuse.py", "engine/scripts/case_reuse.py"]
footprint:
  - "docs/veldo-userns-setup.txt"
  - "engine/scripts/agent_sandbox.py"
  - "engine/scripts/agent_sandbox.json"
  - "engine/scripts/veldo_userns.c"
  - "engine/scripts/veldo-userns.apparmor"
  - "engine/scripts/gate_candidate.py"
  - "engine/scripts/check_gate_mutations.py"
  - "engine/scripts/gate_legs.py"
  - "engine/scripts/mutation_sandbox.py"
  - "engine/scripts/reuse_worker.py"
  - "engine/scripts/case_inputs.py"
  - "engine/scripts/case_reuse.py"
  - "engine/.veldo/control_proof.py"
  - "engine/.veldo/control_verification.py"
  - ".veldo/control_proof.py"
  - ".veldo/control_verification.py"
  - "scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
  - "scripts/veldo_userns.c"
  - "scripts/veldo-userns.apparmor"
  - "scripts/gate_candidate.py"
  - "scripts/check_gate_mutations.py"
  - "scripts/gate_legs.py"
  - "scripts/mutation_sandbox.py"
  - "scripts/reuse_worker.py"
  - "scripts/case_inputs.py"
  - "scripts/case_reuse.py"
  - "scripts/check_first_use.py"
  - "scripts/check_install_and_run.py"
  - "scripts/migrate_to_veldo.py"
  - "scripts/suites/shared.py"
  - "scripts/suites/03_plugin_extension_loading_runner.py"
  - "scripts/suites/14_warp_0717_subset_runner.py"
  - "scripts/suites/24_veldo_0007_install_and_run.py"
  - "scripts/suites/27_veldo_0010_evidence_provenance.py"
  - "scripts/suites/53_veldo_0123_mutations.py"
  - "scripts/suites/66_veldo_0051_events.py"
  - "scripts/suites/69_veldo_0058_gate_output.py"
  - "scripts/suites/70_veldo_0057_landing.py"
  - "scripts/suites/98_veldo_0204_mutation_receipts.py"
  - "scripts/suites/101_veldo_0208_landing_reuse.py"
  - "scripts/suites/102_veldo_0210_agent_profile_runtime.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0207-declared-case-reuse.md"
  - "specs/VELDO-0208-single-user-landing-reuse.md"
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
    refuses the start (exit 2) before any command runs A fresh mutation worker that is traced refuses
    to start its tree (exit 2), and one in mode tree outside a tree refuses before any candidate code
    runs; either is a worker error in the stage receipt. A declaration of a case whose inputs start a
    gate is refused with the reason starts_a_gate, and the case runs fresh.
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
      returns, a launcher killed outright with a descendant that outlives the agent (it ends with
      the tree: in the tree's own PID namespace with its init, nested by the init the killed relay
      orphans, AC7), a live launcher's aged scratch, a stale directory with a shut subdirectory, a recent one, a stale one
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
      instructions); Codex reads and writes only veldo-agent-state/<folder>-<digest>/ under
      CODEX_HOME (sessions/, memories/, history.jsonl; <digest> the first 16 hex digits of the
      SHA-256 of the worktree's canonical path), never the account-wide sessions/, memories/ or
      history.jsonl the unconfined CLI uses. Two worktrees whose folder names coincide (every
      character but ASCII letters and digits becomes '-') never share state: Codex's keys differ by
      the digest, and Claude's folder is claimed by the first worktree that runs there
      (veldo-agent-state/claims/<folder> under CLAUDE_CONFIG_DIR, never granted, holds the SHA-256
      of its canonical path) and refused (exit 2) to any other. Before the grant and again once the confined tree is
      gone, before any unconfined process could read it, clean_state removes and names on stderr
      every symbolic link, every regular file with another link and every special file in that
      state, at any depth and in directories the run shut. Set: a second run of each client in the
      same worktree reading what the first wrote, a run in another worktree seeing none of it,
      writes and creates in another project's memory folder, a listing of projects/, writes and
      creates elsewhere in the configuration directory and in the account-wide Codex state, a
      credential read, a write through .. from a state directory, a read through a link planted in
      one, a planted link, FIFO, hard link and link in a shut directory removed and reported, the
      sweep on its own over 1100 nested directories, and the refusals of a state entry outside the
      configuration directory, one holding a credential and one that is a link, and two worktrees
      whose folder names coincide. Completeness:
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
      over /proc, locks the securebits (no root fixup, no set-user-ID fixup, keep caps off, no
      ambient raise, each locked), drops the whole bounding set, clears the ambient, inheritable,
      permitted and effective sets, reads each result back, and, without no_new_privs (the helper
      refuses one it inherited), executes python3 -I -S agent_sandbox.py namespace-init. The host's
      AppArmor policy (scripts/veldo-userns.apparmor) lets only the helper create a user namespace
      and changes the interpreter it executes (/usr/bin/python3*, matched on the resolved path) to
      the child profile veldo-userns-child with a plain transition (px), which denies every
      capability, every user namespace, mounts and profile changes, and is kept by every program
      executed below it (ix). The init's very first act sets no_new_privs and exits unless every
      capability set, the bounding set included, is empty, the securebits are the locked ones and
      (with AppArmor) its label is exactly veldo-userns-child (enforce). It then refuses to go on
      unless it is PID 1 of a read-only fresh procfs, only the identity map exists, every capability
      set is empty, no_new_privs is set and (with AppArmor) its label is exactly
      veldo-userns-child (enforce); it then reports ready and forks the agent, which confines itself
      (seccomp, Landlock) and execs.
      The launcher refuses unless the init reports ready within 60 seconds and the helper's own
      process holds no capability, and kills the tree first. The helper is never taken from the
      environment, the configuration or the candidate; one that is absent, not a regular file,
      set-user-ID or with file capabilities, not owned by root, writable by anyone but root (or in a
      directory that is) refuses the start (exit 2) naming the owner's one-time setup command, as
      does a host without the setup; host /proc is never the fallback. A stop (TERM, INT, HUP)
      during the start ends it at once: the tree, a hung helper with it, is killed and the launcher
      exits 128 plus the signal number. A launcher already inside a tree the outer launcher made
      (it inherited the outer launcher's marker, a descriptor of the outer launcher's PID namespace
      that is a proper ancestor of its own; label exactly veldo-userns-child (enforce); a PID
      namespace other than the host's whose procfs is /proc; no capability) creates none, and its
      init is a child subreaper that kills and reaps every remaining descendant when the agent ends;
      any other private PID namespace (a container's, a systemd PrivatePIDs one) has no marker and
      does not count. Python closes every descriptor it does not hand a child, so every process that
      may start a launcher hands it the marker (pass_fds, agent_sandbox.launcher_fds: the verified
      marker, nothing outside a tree): the gate's entry gate_candidate.py and each tool, product module
      and suite that starts a gate; a launcher below the child profile that holds none refuses, naming
      that, and never consults the helper. Set: the pids /proc lists inside, a host process
      started with a marker argument read by pid and found by scanning, uid, gid, every capability
      set, no_new_privs and the AppArmor label inside, a clone(CLONE_NEWUSER) by the agent, the owner
      of a file created inside, /proc's mount options, an orphan reaped by the init, a descendant
      that left the agent's process group after the agent exits, the same for the gate profile; the
      helper source dropping everything after the procfs mount and before exec, reading each step
      back and setting no no_new_privs before that exec, the init setting no_new_privs first and
      stopping while it holds a capability, other securebits or another label, its relays, its
      reproducible static build and its refusals (arguments, entry point's name, path, owners); the
      policy compiling, its one plain exec transition and its child profile's denials; a container
      label, a stack, complain mode and a forged
      tree (the child label, no capability, only its own namespace descriptors) not counting as
      nested; the nested check under the gate and the agent profile's real grants, where /sys is
      unreadable; the marker created before the helper and kept by the tree, handed on through the gate's
      entry and refused when a child closed it; a subreaper ending a setsid
      descendant; the start and handoff waits timing out; TERM, INT and HUP ending a start whose
      helper hangs, in both profiles; a missing, user-owned, user-writable and linked helper, a root-owned program that is not
      the helper, a run granted a write to the launcher's own file or above it, and every start on a
      host without the setup. Completeness: every launch goes
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
      namespace/stop-ends-a-hung-helper-* go red. Set no_new_privs in the helper's dropping;
      namespace/helper-execs-without-no-new-privs goes red. Skip the init's first check;
      namespace/init-sets-no-new-privs-first-and-holds-nothing goes red. Drop pass_fds from
      gate_candidate.py; namespace/gate-entry-hands-on-the-marker goes red.
  - id: AC7
    text: >
      Claim: every fresh confined mutation worker starts inside a tree the agent launcher makes, the
      same veldo-userns path and checks as the agent and gate profiles (run_tree: helper_problem, the
      helper, namespace_init's checks, the init PID 1, the marker every process of the tree keeps;
      nested, the outer tree's marker), and only then applies its worker Landlock and seccomp, so a
      gate one of its cases starts nests exactly like any other nested launch. The coordinator's
      bootstrap (reuse_worker.py worker) runs no candidate code: for a fresh job it starts the same
      command in mode tree through mutation_sandbox.enter_tree and agent_sandbox.worker_tree, whose
      agent takes the worker profile, the IPC filter alone, its listener served by the bootstrap
      outside the tree (inside, the child profile denies tracing, so no process there could serve
      it); inside, mutation_sandbox.confine_in_tree refuses unless the process is in such a tree and
      applies the fresh worker's grants with Landlock, keeping the marker. A declared case (reuse,
      traced under strace by the coordinator) stays as it was: mutation_sandbox.confine, outside
      every tree; a traced process never starts a worker tree (tracer_problem), and no profile allows
      tracing a process of a tree. A suite that starts a gate is never declared: a declared case
      reads only its declared inputs, so it can start a gate only if they hold a gate entry
      (verify.sh, gate_candidate.py, gate_legs.py or agent_sandbox.py, wherever a copy lies), and
      case_reuse refuses such a declaration with the reason starts_a_gate in the case's receipt, so its
      cases run fresh. A nested tree's init takes ORPHANED as its parent-death signal and, when the relay
      that forked it is killed, ends every descendant before it exits, as the namespace's end does on
      the host. The coordinator hands each worker the marker it holds (Workers.launcher_fds). Set: a
      fresh fixture worker started as the coordinator starts it (PID 1 the namespace's init, the child
      label, every capability set empty, no_new_privs, the marker held and handed to a child, a read
      outside its grants refused); a launcher killed outright whose agent left a descendant in another
      session holding a lock; a reviewed declaration of a case whose inputs hold verify.sh and one
      holding an engine copy of gate_candidate.py, beside a declaration of a suite that starts none;
      a traced and an untraced /proc status; one confined fresh case each of suites 66_0051, 67_0056,
      69_0058 and 70_0057 through the real coordinator. Completeness: reuse_worker.py is the only
      worker entry the coordinator starts, and every job without a declared runtime set enters a tree
      there; case_reuse.Session is the only place a declaration becomes a snapshot. Test rows
      workers/* in suite 102, on the host and in the gate's tree.
    falsified_by: >
      Confine a fresh worker in place (mutation_sandbox.confine) instead of entering its tree;
      workers/fresh-worker-runs-in-a-tree and workers/gate-starting-suites-pass-confined-fresh go red.
      Drop the gate entry check in case_reuse; workers/gate-starting-suite-refused-declaration goes
      red. Keep SIGKILL as a nested init's parent-death signal; workers/killed-launcher-leaves-no-descendant
      and scratch/killed-launcher-takes-its-descendants go red in the gate's tree.
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
that profile (Telegram 32561-32562) and this design replaces it. It amends VELDO-0208's worker
boundary and VELDO-0207's declarations once more (owner decision, 2026-10-07, AC7): a fresh confined
mutation worker starts inside a tree the agent launcher makes and confines itself there, and a suite
that starts a gate is never declared. Every other VELDO-0208 boundary is unchanged.

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
  locks the securebits (SECBIT_NOROOT, SECBIT_NOROOT_LOCKED, SECBIT_NO_SETUID_FIXUP,
  SECBIT_NO_SETUID_FIXUP_LOCKED, SECBIT_KEEP_CAPS_LOCKED, SECBIT_NO_CAP_AMBIENT_RAISE,
  SECBIT_NO_CAP_AMBIENT_RAISE_LOCKED), drops the whole bounding set, clears the ambient set, clears
  the effective, permitted and inheritable sets, and reads each result back (the securebits exactly
  those, every bounding and ambient bit clear, capget all zero), else exits 2. It sets no
  no_new_privs and executes `/usr/bin/python3 -I -S <launcher> namespace-init <descriptor>` with no
  environment but LC_CTYPE; the helper refuses at its start (after its argument checks) when it
  inherited no_new_privs. The parent drops the same, sets no_new_privs (it executes nothing),
  closes every descriptor above stderr,
  relays TERM, INT and HUP (unless ignored at its start) to the init as SIGRTMIN, SIGRTMIN+1 and
  SIGRTMIN+2, and exits with the init's status. Static, it has no dynamic loader, so LD_PRELOAD and
  the like cannot run code with its rights.
  Requirement: the checkout whose scripts/agent_sandbox.py runs the launcher is the authority
  checkout, and no confined agent can ever write it. The helper executes that file as the init of
  every tree, before seccomp and Landlock, so code an agent wrote there would run as the next
  tree's init. The confinement already denies every write there (the authority and the launcher
  are protected paths, and no writable root may hold or lie beneath one), and the launcher checks
  it once more after every grant is final and before the fork (launcher_write_problem): a run that
  would be granted any write access to its own agent_sandbox.py, or to a directory above it, in any
  profile, refuses to start (exit 2). Even an edited launcher gains nothing beyond today's
  unconfined account: the helper has dropped every capability, with the securebits locked, before
  that exec, the child profile denies capabilities and user namespaces below it, and the init sets
  no_new_privs before anything of the launcher's own runs.
  The AppArmor policy, scripts/veldo-userns.apparmor, installed as /etc/apparmor.d/veldo-userns,
  attaches veldo-userns to the helper's path with userns, the four capabilities it needs inside its
  own namespace, the two mounts it makes, signals, and no tracing of it (so no process injects code
  with its rights). Its one exec rule, `/usr/bin/python3* px -> veldo-userns-child,`, lets the
  helper execute only the interpreter and changes it to the child profile outright: AppArmor
  matches an exec by the path the executable resolves to, here /usr/bin/python3.12 through the
  link /usr/bin/python3, and the glob takes whichever python3 minor version the host has. The tree
  runs under the plain label veldo-userns-child. The child profile allows files, network, Unix
  sockets, signals and IPC, denies every capability, every user namespace, every mount, unmount,
  pivot_root and profile change, and keeps itself across every exec (ix), so every program
  executed below stays in it and can never leave it. Both profiles carry the same ptrace rules:
  reading the /proc entries of the helper's and the tree's processes (ptrace read, peer
  veldo-userns or veldo-userns-child), and no confined process may trace the helper or a process of
  the tree (an unconfined tracer, such as the launcher whose gate broker reads the agent's memory
  and descriptors, is not checked against a tracee's rules).
  Why the transition is plain, not a stack (owner's host, kernel 7.0, Ubuntu): the first version
  set no_new_privs in the helper before its exec, and under no_new_privs a confined process may
  change only to a label that keeps its current profile, so the rule stacked the child onto the
  helper (`/** px -> &veldo-userns-child`). On the owner's host that exec was refused, "profile
  transition not found" (Ubuntu's own unprivileged_userns only stacks onto itself). So the helper
  sets no no_new_privs before its exec, and the transition is a plain px.
  Why this is at least as strong as the stack. What the stack gave was the child profile's
  denials, which the plain transition gives unchanged: every access of the tree is checked against
  veldo-userns-child, which denies every capability, user namespace, mount, unmount, pivot_root and
  profile change, and ix keeps it across every exec, so nothing the tree runs can get a user
  namespace (and with it capabilities in a namespace of its own), whatever it executes. The
  helper profile's own rules in the stack narrowed the child's in one place only, ptrace, and the
  child now carries the helper's ptrace rules itself (read the /proc entries of veldo-userns and
  veldo-userns-child processes, be read by any, never be traced), so the tree still traces nothing
  and no confined process traces the helper; every other rule of the helper profile allowed at
  least what the child allows (files, exec, network, Unix sockets, signals, IPC), and the child
  alone denies capabilities, user namespaces, mounts, pivot_root and profile changes, as the stack
  did.
  What no_new_privs gave before the exec, that the exec gains no capability and no identity, comes
  from the capability state instead: the bounding set is empty, so no file capability can add
  one; the securebits are locked with no root fixup and no set-user-ID fixup, so neither uid 0
  nor a set-user-ID root file grants the full sets; the ambient set is empty and cannot be raised;
  and inside the user namespace only the account's own uid and gid are mapped, so a set-user-ID or
  set-group-ID file of any other owner changes no identity (the kernel ignores it), and one of the
  account's own changes nothing. The helper reads each of these back before it executes. And the
  init sets no_new_privs as its very first act, before any code of the tree runs, and exits unless
  every set is empty and the label is exactly veldo-userns-child (enforce); from there on the tree
  runs under no_new_privs as before. Nothing the helper runs can therefore create or use a user
  namespace with capabilities, whatever it executes. The policy:

  # AppArmor policy for the agent sandbox's namespace helper (VELDO-0210 AC6), installed by the
  # owner's one-time setup as /etc/apparmor.d/veldo-userns.
  #
  # veldo-userns is the only program on the host this lets create a user namespace. It needs the
  # capabilities below inside that namespace only, to map the account to itself, make the mount and
  # PID namespaces and mount their procfs. The one program it may execute is the interpreter
  # /usr/bin/python3, which AppArmor matches by the path the link resolves to (/usr/bin/python3.12
  # and the like), and that exec changes to the child profile veldo-userns-child outright (px), so
  # the label inside is exactly veldo-userns-child. Before that exec the helper drops every
  # capability with the securebits locked (no root fixup, an empty bounding set), so the exec gains
  # none, and it sets no no_new_privs, under which only a stack would be allowed; the executed init
  # sets no_new_privs as its first act. veldo-userns-child denies every capability, user namespace,
  # mount, unmount, pivot_root and profile change, and keeps itself across every later exec (ix).
  # So nothing the helper runs can create or use a user namespace with capabilities. Both profiles
  # carry the same ptrace rules: reading the /proc entries of the helper's and the tree's processes,
  # and no confined process may trace the helper or a process of the tree, so no code runs with the
  # helper's rights, as under the stack the first version used.

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
    network,
    unix,
    signal,
    mqueue,
    io_uring,
    dbus,
    ptrace (read) peer=veldo-userns{,-child},
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
    ptrace (read) peer=veldo-userns{,-child},
    ptrace (readby),
    audit deny ptrace (tracedby),
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
  in new user and UTS namespaces, cannot bring up an interface here or in new user and network
  namespaces, cannot create a UTS namespace, cannot create a user namespace (EPERM or EACCES),
  directly or through executed programs (util-linux unshare, hostname, ip), has CapBnd 0 and the
  securebits locked as above, and that the helper's own process holds no capability:

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
  own; only nsfs descriptors get the ioctls), its AppArmor label is exactly
  veldo-userns-child (enforce) (the helper's own label, any stack, complain or mixed mode do not
  count), which no profile but the helper's changes to on exec and which no process can leave, its
  /proc/self/ns/pid is not the initial pid:[4026531836], its /proc/self is its own pid, and it holds
  no capability. Every one of these is read from /proc, which the outer tree's Landlock grants in
  every profile; none from /sys, which no profile grants (the label read alone shows AppArmor is
  enabled), so the check decides the same inside a gate tree and inside an agent tree. The marker cannot be forged from inside: a process in a PID namespace cannot open
  an ancestor (NS_GET_PARENT refuses it, its procfs shows no process outside), so only a process
  outside hands one in. A container's or a systemd PrivatePIDs namespace has none and does not
  count, whatever its label: there the launcher uses the helper as on the host. The nested
  launcher hands on the marker it inherited. Python's subprocess closes every descriptor above the
  standard three that it is not handed, so each process between two launchers hands the marker on
  explicitly with pass_fds=launcher_fds(), which returns the descriptor launcher_marker verifies and
  nothing outside a tree: gate_candidate.py; gate_legs.py's confined leg; the mutation coordinator's
  inventory; check_install_and_run.py, check_first_use.py and migrate_to_veldo.py; the installed
  verifier control_verification.observe_gate runs and the head gate control_proof.capture_gate runs,
  with control_proof.launcher_fds, which loads no module (a factory installation's closure names
  every module it loads by a literal, and scripts/ is not in it) and hands on every namespace
  descriptor the process inherited, for the gate's launcher to check; and every suite row that starts a
  gate, the launcher or a nested dispatcher (shared.launcher_fds). Handing it on grants nothing the
  nested launcher does not check again. A launcher whose AppArmor label is NAMESPACE_LABEL but which
  holds no marker refuses before helper_problem, naming the closed marker: below the child profile
  no helper can run, and root shows as an unmapped uid there, which helper_problem would misreport
  as a helper not owned by root. Its C forks G itself and relays as the helper does;
  G is a child subreaper (PR_SET_CHILD_SUBREAPER), so a descendant that leaves the agent's session
  is reaped by it, and when A exits G kills every remaining descendant (each child in
  /proc/self/task/<pid>/children, then the ones that become its children) before it exits. The
  nested tree sees the outer tree's processes, never the host's.
- Mutation workers (AC7, owner decision 2026-10-07). A confined mutation worker ran with
  no_new_privs set and outside every tree, so when a case's suite started a gate the helper refused
  (it refuses an inherited no_new_privs) and there was no marker to hand on: about 96 confined cases
  of suites 70_0057, 67_0056, 66_0051 and 69_0058 failed, and one waited 120 seconds for a check
  that never started, which cancelled the stage. Now reuse_worker.py, for a job with no declared
  runtime set, loads only the launcher and mutation_sandbox, closes every descriptor but its ledger
  and the marker it was handed, and calls mutation_sandbox.enter_tree, which repeats its own command
  (interpreter options included, mode tree) through agent_sandbox.worker_tree. That is run_tree, the
  start prepared_launch uses for the agent and gate profiles, factored out of it unchanged: the
  child executes the helper (nested, forks the init), the init checks its namespace and reports
  ready, the parent checks the helper's capabilities, and the agent keeps the marker. The worker
  profile differs in one step only: its agent installs the IPC filter (Handoff) and execs without
  Landlock, because the bootstrap it executes lives in the authority, which the worker's grants do
  not include. The filter's listener goes to the bootstrap outside the tree, exactly as the gate
  launcher serves its agent's; inside, the child profile denies every trace, so no process there
  could serve it. In mode tree the bootstrap refuses unless nested_namespace holds (the child label,
  a PID namespace not the host's, no capability, the marker), installs the ownership tracker, and
  mutation_sandbox.confine_in_tree applies the fresh worker's grants (the same worker_grants as
  confine) with Landlock beneath that filter, after launcher_write_problem, keeping the ledger and the
  marker; only then does the observer load the candidate's suite. A gate the suite starts finds the
  marker and nests (strict, since a listener is already above it). A traced process starts no worker
  tree (tracer_problem reads TracerPid); a declared case is the only traced worker, and it keeps
  mutation_sandbox.confine outside every tree, so nothing traces a process of a tree and neither
  AppArmor profile changes. The unconfined list is unchanged. A declaration whose selected inputs
  hold a gate entry (case_inputs.gate_entries: verify.sh, gate_candidate.py, gate_legs.py,
  agent_sandbox.py, by file name, so engine copies and fixtures count) is refused in
  case_reuse.Session with the reason starts_a_gate, which the stage writes into that case's receipt;
  its cases run fresh. The rule is complete for declared cases: they read only their declared inputs
  and the runtime set, which holds no gate. Teardown: the coordinator kills a worker's process group,
  and the worker's tree has its own session, so its end comes from the parent-death chain. On the
  host the namespace ends with its init. Nested (a coordinator inside a tree), the init has no
  namespace of its own, so it takes ORPHANED (SIGRTMIN+3, blocked from the relay's start) as its
  parent-death signal and on it kills the agent's group and every remaining descendant
  (end_descendants) before exiting; that holds for every nested launch, not only workers. Cost: a
  fresh worker starts a second interpreter, about 0.15 seconds more per worker on the owner's host.
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
  account); '{project}' in an entry is the worktree's Claude project folder name, and
  '{project_key}' that name followed by '-' and the first 16 hex digits of the SHA-256 of the
  worktree's canonical path. Two worktrees can share a folder name ('/a/b-c' and '/a-b/c' both
  name '-a-b-c'), never a key. State named by '{project}' is claimed: the launcher keeps, in
  veldo-agent-state/claims/<folder> under that client's configuration directory (never granted),
  the SHA-256 of the canonical path of the first worktree that ran there, created once (a private
  file linked into place, so whole or absent, each component opened without following a link),
  and refuses (exit 2) a run from any other worktree whose folder name is the same. A folder
  Claude Code made before the first confined run there belongs to whichever worktree claims it
  first. Claude's is
  projects/{project} (transcripts), the one folder Claude Code writes for this working directory:
  every UTF-16 code unit of the resolved worktree path that is not an ASCII letter or digit becomes
  '-', and past 200 characters the name is cut and followed by '-' and the base-36 absolute value
  of the path's 32-bit string hash, as Claude Code 2.1.290 computes it. The launcher drops
  CLAUDE_CODE_PROJECT_DIR_NAME from the agent's environment, which would name another folder, and
  sets PWD to the worktree. Claude's auto-memory of a linked worktree lives in the main checkout's
  folder, which is not granted. Codex's are veldo-agent-state/{project_key}/sessions, memories and
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
  the account owns the launcher file and can change it, and the helper accepts any agent_sandbox.py
  the account owns, wherever it lies. The boundary is that the helper drops every capability, with
  the securebits locked, before it executes anything, and that the child profile denies
  capabilities and user namespaces to whatever runs below it, so a launcher file someone edited
  runs with nothing beyond what the unconfined account already has today.
- The helper refuses to run when it inherited no_new_privs (a caller under a sandbox that sets
  it): the exec into the child profile would be refused there. A process of this account that is
  unconfined may itself change to veldo-userns-child (AppArmor lets an unconfined process change to
  any loaded profile); that only takes rights away from it, and without the outer launcher's
  marker it does not count as nested.
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
