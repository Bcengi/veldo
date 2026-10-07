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
  - "scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
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
    run), an unknown client, and each
    stale scratch directory it could not remove.
  metrics: None beyond the run's exit status; a run stopped by a signal exits 128 plus its number.
  traces: Not applicable; the launcher keeps no state beyond the run.
  error_taxonomy: >
    An unknown client, a client place that is not an absolute directory, a client file outside the
    client's own state directory, or a credential whose source lies in the store or a protected path
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
      while the account logs in again outside the run, and a rewrite nested past the parser's
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
      returns, a launcher killed outright with a descendant that outlives the agent, a live
      launcher's aged scratch, a stale directory with a shut subdirectory, a recent one, a stale one
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
      Claim: the selected client's transcripts, sessions, history and memories outlive the scratch:
      they stay in the runner's configuration directory for that client and account, which the
      agent profile reads and writes only there (Claude's projects/; Codex's sessions/, memories/
      and history.jsonl), never its credentials and never any other path of that directory. Set: a
      second run of each client reading what the first wrote, writes and creates elsewhere in the
      configuration directory, a credential read, a write through .. from a state directory, a read
      through a link planted in one, and the refusals of a state entry outside the configuration
      directory, one holding a credential and one that is a link. Completeness: state_dirs and
      state_files under each client in agent_sandbox.json are the only write grants outside the
      worktree and scratch; state_grants() refuses any that overlaps the store, a protected or
      denied path, a credential source or the worktree. Test rows state/* in suite 102.
    falsified_by: Grant the configuration directory instead of its state entries; state/claude-settings-refused goes red.
required_evidence: [unit]
rollback: Revert the four protected files to a9fb11d6; runners fall back to their documented unconfined switch.
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
scratch. Every other VELDO-0208 boundary is unchanged.

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
  the copy is dropped and the launcher says so. A copy that fails to parse for any reason (a
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
  account): Claude's projects/ (transcripts), Codex's sessions/, memories/ and history.jsonl. An
  absent entry is created (directory 0700, file 0600) unless the configuration directory itself is
  absent; an entry that is a link, of the other kind, resolves outside the configuration directory,
  or holds, is or lies beneath the store, a protected or denied path, a credential source or the
  worktree refuses the start. Each is granted read and write and linked into the scratch where the
  CLI looks for it, after every seed and through the same overlap check as the read links. The
  rest of the configuration directory is not granted at all.
- Scratch. launch() sweeps the temporary directory for veldo-agent-* entries owned by this uid that
  are real directories, older than a day and not locked, and removes them (shut subdirectories are
  opened first, no link is followed). Its own scratch is created there and held with flock until
  removal, with a shared lock; the child opens the scratch again and holds its own shared lock,
  kept across exec, so the sweep's exclusive lock fails while the agent or any descendant holding
  that descriptor lives. TERM, INT and HUP (unless the launcher inherited them ignored) are blocked
  from before the fork until the parent has registered its child, then forwarded to the confined
  group; a group still alive ten seconds later is killed. The launcher then writes back
  credentials, removes the scratch and exits 128 plus the signal number. The child sets
  PR_SET_PDEATHSIG to SIGKILL once confined, just before exec, and refuses the start if the
  launcher is already gone, so a launcher killed outright never leaves its agent running.

## Accepted residuals

- A confined process can write any JSON object into its copy of the selected client's credential
  file, and that object replaces the account's file. The process already holds that credential;
  the write cannot reach any other file or the other client's credentials.
- A refresh inside a run rotates the account's refresh token, so until the write-back other
  sessions on that account hold a token the provider has already replaced and may have to refresh
  or log in again. When the source changed during the run, the run's refreshed token is dropped and
  the newer file kept. The re-read and the rename are two steps: a write landing between them is
  replaced.
- The resolver directory's other entries are readable too: resolved's resolv.conf (the upstream
  servers) and the names of its varlink sockets and per-link state directory (mode 0700, owned by
  systemd-resolve, so unreadable to this account anyway).
- A confined process can write anything into its client's state entries, which every later session
  on that account reads (a crafted transcript can be resumed), and may plant links there; the
  links grant nothing, since a read through one is checked against the target. Concurrent runs on
  one account share those entries, as unconfined runs do today.
- Codex's other state under CODEX_HOME (its SQLite stores, logs and caches) stays in the scratch
  and is lost at exit: a SQLite store needs its directory writable for its journal, and that
  directory holds auth.json.
- Writes Claude or Codex make to their plugin, marketplace or skill directories (marketplace
  updates, system skill installs) fail: those directories are outside the worktree.
- engine/scripts/agent_sandbox.json is byte-identical with this repository's copy (template sync),
  so the reviewed project_read_roots entry ships to adopters; an absent root grants nothing.
- Processes that leave the confined process group (their own setsid) are not stopped by the
  launcher; they stay confined.
- PR_SET_PDEATHSIG reaches the agent the launcher started, not its descendants. A descendant that
  outlives a launcher killed outright runs on, confined; if it also closed the descriptors it
  inherited, nothing holds the scratch and the next start more than a day later removes it.

## Out of scope

The runner scripts (myday codex_work.sh, claude_work.sh, agent_sandbox.sh), which pass the client
option and CLAUDE_CONFIG_DIR after review. The shared-alternate rule for repositories other than
this one. The gate and worker profiles' grants.

## Build and evidence limits

Only suites 99, 100, 101 and 102 run for this specification, sequentially in the foreground, plus
template sync, generated, lint, docs and validate.py all. The owner runs the full gate and lands
the stamp; no protected-path approval is recorded here.
