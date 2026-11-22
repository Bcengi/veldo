# VELDO-0359 B0: measurements and inventory (no product change)

Date: 2026-11-22. Build commit: 8308e71b5 (Veldo main 23318512 plus the spec and design; no code
difference from 23318512, so every design line reference applies). Host: Linux 7.0.0-38-generic,
x86_64, Landlock ABI 8, LSMs lockdown,capability,landlock,yama,apparmor,ima,evm, Yama ptrace_scope 1,
kernel.apparmor_restrict_unprivileged_userns=1, Python 3.12.3. Owner approval for the live runs:
research/approvals/2026-11-22-veldo-0359-b0-test-runs.md (Telegram 42911 asked, 42914 "Approve test runs").

Paths below write the account home as `~`. Raw logs, results and the exact tools are in b0/ (all .txt,
home paths replaced by `~`).

## Verdict

| Exit condition | Result |
|-|-|
| Both engines' ordinary tools work under the ruleset | PASS: Codex 0.166.0 (danger-full-access) shell command, child and build step; Claude Code 2.1.317 (factory settings) Bash tool and build step. Store refused in every trial |
| Heartbeat setup deadline met | PASS: ruleset build plus install at most 3.3 ms (50 fresh processes per layout) against HB.SETUP_SECONDS 5.0 s |
| Socket connect works | PASS: a guarded payload connects to the running fixture authority socket in the denied directory and is refused malformed_request (no signature) and command_signature_invalid (bogus signature), the same as unguarded |
| Live layout passes the preflight | NOT APPLICABLE: this host has no live Veldo installation. No authority unit, no receiver configuration, no store anywhere (section 7). Nothing is refused and no unnamed entry exists, because there is no live directory. The lead decides whether B2 proceeds on that basis |

Also measured: the real risky launch reaches its payload, and the census equals the runner's grants
(29 = 29, no conflict).

Findings that change what B2 can claim on this host (section 8): Codex's workspace-write failure here
is caused by AppArmor's user-namespace restriction, not by the ruleset (an unguarded control fails the
same way). Claude Code's optional sandbox turns itself off here (socat missing) instead of failing.
Cross-directory link out of the store fails with EXDEV, not EACCES.

## 1. Fixture

All live runs used a fixture, never a real store (none exists). Fixture root /var/lib/veldo/b0-0359
(0700), made for B0 and removed after it; /var/lib/veldo is empty again (`ls -la /var/lib/veldo`:
only `.` and `..`).

- Store directory: /var/lib/veldo/b0-0359/state/authority holds control.sqlite3 (WAL, one sentinel
  row, held open by tool-mkstore.py so -wal and -shm exist), authority.lock, and authority.sock bound
  by tool-fauth.py. tool-fauth.py is control_client.bind, Authority.judge and serve_one, unchanged,
  with a verifier that accepts no signature because no member key is enrolled.
- Scratch folders: /var/lib/veldo/b0-0359/runs/<label>, each made empty (mkdir fails if it exists).
- Guard: tool-guard.py is the B0 prototype of D 5 step 4. It runs control_clone.abi, then
  control_clone.rules([store], [store]), then control_clone.confine, then exec. The ancestors it
  reports (write and read): /var/lib/veldo, /var/lib/veldo/b0-0359, /var/lib/veldo/b0-0359/state
  (plus the root-owned /var/lib, /var, /).
- Probe: tool-probe.py runs one trial per row and reports the errno. tool-task.sh runs the probe, a
  child `sh -c`, and an ordinary build step (`make` compiling hello.c with cc, then running it).
- Database digest before and after every run, guarded runs included:
  e3ba06536f7dbba337dee3c1c5f01b43660ce276abb54c5cee2d5defc5b970aa (unchanged).

## 2. Ruleset trials (item 5 and the trial matrix)

Guarded payload, no engine (`guard.py ... -- python3 probe.py`), result-control-guarded.json.txt. The
same values came from the Codex and Claude runs below:

| Trial | Guarded | Unguarded control (disposable copy) |
|-|-|-|
| open database read, write, read-only with O_TRUNC | EACCES, EACCES, EACCES | ok, ok, ok |
| -wal and -shm read and write | EACCES x4 | ok x4 |
| authority.lock read-only | EACCES | ok |
| truncate database | EACCES | ok |
| create file, directory, symlink, socket inside | EACCES x4 | ok x4 |
| unlink database | EACCES | ok |
| rename database out | EACCES | (ENOENT: already unlinked by the trial before) |
| link database out | EXDEV | (ENOENT, same reason) |
| unlink authority.sock, rename it out | EACCES, EACCES | ok, (ENOENT) |
| rename the store directory | EACCES | ok |
| create a file directly in the store's grandparent (ancestor cost) | EACCES | ok |
| open the database through a symlink in the worktree | EACCES | (ENOENT) |
| child process opens the database | EACCES | (ENOENT) |
| list the store directory | ok (not handled, as designed) | ok |
| worktree write, /tmp write | ok, ok | ok, ok |
| connect authority.sock, unsigned request | accepted false, malformed_request | accepted false, malformed_request |
| connect authority.sock, bogus signature | accepted false, command_signature_invalid | accepted false, command_signature_invalid |

The unguarded control runs its trials in sequence on a disposable copy, so once the database is
unlinked and the directory renamed, the later trials report ENOENT. Every trial that ran on an intact
target succeeded unguarded. The socket assertions were repeated unguarded on a clean disposable copy
with a running fixture authority (`unguarded unsigned False malformed_request`, `unguarded bogus False
command_signature_invalid`). For B2's rows: Landlock reports a denied cross-directory link (REFER) as
EXDEV, not EACCES.

## 3. Engines under the ruleset (items 1 and 2)

The engines are the pinned binaries from .veldo/runtime/engines.json, re-hashed before the runs:
- Claude Code 2.1.317: ~/.local/share/claude/versions/2.1.317, sha256 eb224419e344575faa4a1f39b290b649425a10cd5ee2ef1d003480cd9ae57eb0.
- Codex 0.166.0: ~/.local/share/codex-versions/0.166.0/.../x86_64-unknown-linux-musl/bin/codex, sha256 b8a11fedf24b2dfb59a70c9e52b030f9a508dcd49cd2dd0d41956f4c785156b8.

(On PATH the host has Claude Code 2.1.326 and codex-cli 0.154.0. Neither was used.)

Each run uses `env -i` with HOME, USER, PATH, LANG=C.UTF-8 and TERM=dumb, then
`guard.py <.veldo> <store> <timing> -- <binary> ...`, with cwd set to the empty scratch folder and stdin
from /dev/null. Prompt: run `sh /tmp/b0-359-tools/task.sh` once and reply with its output. tool-run_engine.sh.txt has
the exact argv. Logins: Claude acct1 (CLAUDE_CONFIG_DIR set to that login), Codex codex1 (the default
CODEX_HOME). Each run took its login's lease (account_lease.sh lease_take) and runs never overlapped.

| Run | Argv essentials | Outcome |
|-|-|-|
| codex-1 (Codex 1/5) | `codex exec --json -c check_for_update_on_startup=false -c model_reasoning_effort=low --sandbox danger-full-access --skip-git-repo-check -C <scratch>` | exit 0, 15.2 s. command_execution `/bin/bash -lc 'sh /tmp/b0-359-tools/task.sh'` exit 0. Every store trial matches section 2, including the child. child.txt `child-pid=2180282 ok`. make and cc built hello, which printed `built-ok`. `task-exit=0`. Worktree files written |
| codex-2 (Codex 2/5) | same, `--sandbox workspace-write` | The shell command never started. Agent message: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. No command_execution item; the scratch folder stays empty |
| codex-3-unguarded-control (Codex 3/5) | same as codex-2, without guard.py | Same failure: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`, scratch empty (section 8, F1) |
| claude-1 (Claude 1/5) | `claude -p <prompt> --setting-sources '' --strict-mcp-config --mcp-config '{"mcpServers":{}}' --disable-slash-commands --settings '{"disableAllHooks":true}' --tools=Bash --allowedTools=Bash --model claude-haiku-4-5-20251001 --output-format stream-json --verbose`; env adds CLAUDE_CODE_DISABLE_CLAUDE_MDS=1, CLAUDE_CODE_DISABLE_AUTO_MEMORY=1, DISABLE_AUTOUPDATER=1 (the VELDO-0155 baseline and qualified environment) | exit 0, 7.4 s. init: version 2.1.317, tools [Bash], apiKeySource none (subscription), permissionMode default. The Bash tool_use ran task.sh with is_error false. Every store trial matches section 2. `built-ok`, `task-exit=0`. stderr empty |
| claude-2 (Claude 2/5) | same, `--settings '{"disableAllHooks":true,"sandbox":{"enabled":true}}'` | exit 0, 6.7 s. stderr: `Sandbox disabled: sandbox is enabled but dependencies are missing: socat not installed ... Commands will run WITHOUT sandboxing.` Bash ran task.sh unsandboxed under the ruleset. Every store trial is refused, `built-ok`, `task-exit=0` |

Runs used: Claude Code 2 of 5, Codex 3 of 5. The risky launch in section 5 ran no engine.

Mount evidence without an engine (bwrap-*.txt is the guard timing, the outputs are quoted here):
- Unguarded, this account: `bwrap --ro-bind / / --dev /dev --proc /proc true` gives
  `bwrap: setting up uid map: Permission denied` (rc 1), and `bwrap ... --unshare-net true` gives
  `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` (rc 1).
- Guarded: bwrap fails the same way. `unshare -rm true` and `unshare -r true` give
  `write failed /proc/self/uid_map: Operation not permitted`.
- So on this host, Landlock's own refusal of mount (D 5 "Mounts") cannot be isolated: AppArmor refuses
  first. Recorded as NOT RUN.

## 4. Ruleset construction time (item 3)

tool-timing.py runs 50 fresh processes per layout. Each loads control_clone, then times
abi, rules and confine:

| Store directory | Rules | rules() ms median / p95 / max | confine() ms median / max | abi+rules+confine max ms |
|-|-|-|-|-|
| /var/lib/veldo/b0-0359/state/authority (fixture) | 112 | 1.413 / 1.484 / 1.748 | 0.625 / 0.773 | 2.471 |
| /var/lib/veldo/authority (factory layout; chain /var/lib/veldo, /var/lib, /var, /) | 109 | 1.272 / 1.320 / 1.327 | 0.606 / 0.687 | 2.054 |
| ~/.local/share/veldo/authority/state/authority (home chain, worst case) | 137 | 1.710 / 1.827 / 2.126 | 0.749 / 1.358 | 3.289 |

Loading control_clone takes about 12.5 ms (max 14.0) and is not part of the wrapper's setup window if
the module is loaded before release. Deadline: control_heartbeat.SETUP_SECONDS = 5.0 s (+
SETTLE_SECONDS 1.0 s report margin). The deadline is met by more than three orders of magnitude.
In-run timings from the live runs: 2.1 to 2.2 ms total (b0/*-timing.json.txt).

## 5. Real risky launch and census parity (item 4)

Namespace self-test (`python3 -I -S scripts/agent_sandbox.py namespace-selftest`): 20 passed, 0 failed,
0.25 s. The helper /usr/local/lib/veldo/veldo-userns runs under its AppArmor profile veldo-userns.

The launch argv is shaped as control_launch.runner_argv shapes it:
`python3 -I -S scripts/agent_sandbox.py --config scripts/agent_sandbox.json --client codex --worktree <scratch> -- /usr/bin/python3 <scratch>/probe.py <store> <scratch> risky`,
with CODEX_HOME at the codex1 login, CLAUDE_CONFIG_DIR at acct1, and stdin /dev/null. The runner is
the unchanged scripts/agent_sandbox.py and .json of the build commit. tool-risky.py loads it and wraps
run_tree only to record the grants it is given, then calls the runner's own main().

The census in tool-risky.py is written separately from the runner's code, from D 6 set (b):
- deny_read is extended with borrow_root and with every client's credential sources.
- Read items go through the grants_for filter: read_roots and the placeholders, optional tools,
  project roots, the resolved read_link targets of the selected client whose sources exist, and the
  configuration file.
- Write roots, the fixed /dev grants, the resolver directory, and the codex state entries are added.
- Scratch is the symbolic `{scratch}`.

| Attempt | Outcome |
|-|-|
| risky-1 | The runner refused: `borrowed login is busy: ~/.codex/.runner-lease is held by another run`. My harness held the codex1 lease, and the runner takes that lease itself (borrowed_credentials). Nothing ran. Lesson: the risky runner is its own lease holder |
| risky-2 | The runner refused inside run_tree: `standard descriptors may not be service sockets` (the harness's stdin was a socket). Grants were captured (parity true), but no payload ran |
| risky-3 | runner_exit 0. The payload ran and wrote risky-written.txt and risky-result.json in the worktree |

risky-3 census: runner grants 29, census grants 29, `runner_minus_census` [], `census_minus_runner` [],
parity true. No grant equals, lies beneath, or is an ancestor of the fixture store directory or
/var/lib/veldo/authority. The grant list is in risky-3-census.json.txt: /usr (and /usr/bin, /usr/lib,
/usr/lib64, /usr/sbin through the /bin, /lib, /lib64 and /sbin links), /etc, the checkout, the
configuration file, the worktree (READ and READ|WRITE), {scratch} (READ and READ|WRITE), the six
optional tool roots present, ~/projects/webflow-ops-worktrees, ~/.codex/skills, ~/.codex/rules,
~/.codex/plugins/cache, three codex state entries under ~/.codex/veldo-agent-state/<project key>/,
/run/systemd/resolve, /dev/null, /dev/random and /dev/urandom. The runner's landlock() also adds /proc
(read) and the pty device inside the tree. Neither is part of set (b), and neither touches the store.

What the risky payload saw (result-risky-3.json.txt): every store trial EACCES, link out EXDEV,
listing the store EACCES (the runner handles READ_DIR), AF_UNIX socket create, connect and bind EPERM
(the runner's seccomp, as D 3 says: no run query, no authority socket), /tmp write EACCES (its TMPDIR
is scratch), worktree write ok. Database digest unchanged.

Runner side effects in the codex1 login: state_grants created
~/.codex/veldo-agent-state/-var-lib-veldo-b0-0359-runs-risky-2-2b66c643fe870770 and
...-risky-3-a57fc25609f84721 (with their claims). They were left in place: they are what a real launch
leaves. Afterwards ~/.codex/auth.json is present and non-empty, ~/.local/state/veldo/borrowed-logins is
empty (no recovery pending), and both leases are free.

## 6. Code inventory at the build commit

Every local contained launch carries the setup pipe. Receiver._spawn sends every non-reported
(local) adapter to _contained (control_launch.py:3123 to 3125). _contained always makes the setup
pipe, puts it in the held description as heartbeat_setup (3180 to 3182) and passes it with
close_fds=True, pass_fds=(beat, ready) (3188 to 3190). It is the only producer of `exec --contained`
(3183). The reported (remote) path uses a plain Popen (3126) and is not a local launch. Conversation
turns and workflow steps go through the same Receiver.launch and _spawn.

The authority unit has XDG_RUNTIME_DIR. The template (.veldo/services/veldo-authority.service) sets no
Environment=, and the unit inherits the user manager's environment:
`systemctl --user show-environment` has XDG_RUNTIME_DIR=/run/user/1000, and a running user-manager
service on this host (concierge-gateway.service) has exactly XDG_RUNTIME_DIR=/run/user/1000 in its
/proc environ. control_service.worker_writable also lists /run/user/<uid> (control_service.py:828).

The Runner can observe receiver exit. control_launch.invoke spawns the receiver with subprocess.Popen
(2207) and keeps it as Launch.child. Launch polls and waits on it (2079 to 2087, child.poll,
child.wait, child.returncode). So the Runner observes receiver exit directly.

D 4 run-side gate inventory: confirmed. Gate attributes used per caller (grep of `gate.<name>`):

| Caller | Attributes |
|-|-|
| plan.py | decide (339), decision_blockers (98, 344) |
| frontier.py | decide (557), observe (298, 299), domain_uuid and repository_uuid (276), and repository_uuid plus conn inside _floor_entry (193 to 202) |
| work.py | decide (x2), observe, domain_uuid, repository_uuid |
| work_state.completion_view | completion (336) |
| control_eligibility.completion_status | landed (483) |
| runstatus.py | refusal_types (225), refusal_code (233), close |
| executor.py | decide (581 to 595, with context and ticket) |
| control_workflow_cycle_pm.coordination_decision | SCHEMA by hasattr (136), conn, _reading, domain_uuid, repository_uuid, plus _entity, _project_owner, _project_problems, _identity and _record |

The last row adds five private members to D 4's list. coordination_decision's only caller is
Gate.decide (control_eligibility.py:1095), so under D 9.3 it runs receiver-side on a real Gate, and
the remote gate needs none of the five. entry_gate callers: plan.py:383, frontier.py:612,
runstatus.py:212, executor.py:939 and 1081. entry_gate passes a wired gate through (464 to 465).

D 9.3 frozen fields, against the code:
- Decision: control_eligibility.py:1096 builds schema, decision_id, station, unit (plus domain,
  repository, follows, inputs, watermark, pending, refusals). eligible is set at 1131, architecture at
  1112.
- Station event fields (_record, 1141 to 1161): schema, operation, domain_uuid, repository_uuid, unit,
  decision_id, follows, watermark, accepted_inputs, outcome, refusals, taxonomy; architecture has
  basis, kind, artifact_digest, validator and error.
- invalid_record (850 to 860) adds entity. decision_dependency (893 to 918) adds references.
- Input identities: _identity (1063 to 1073) gives id, version, digest, definition, or members triples
  with a digest.
- Coordination decision (control_workflow_cycle_pm.py:136 to 175): the same envelope; inputs team,
  snapshot, manager, cycle (id and digest) and project; watermark is MAX(seq) of the journal.
- Completion: FACT_ORDER attempt_finished, artifact_accepted, revision_landed, objective_satisfied
  (completion_contract.py:54). All four are false with no subject (control_eligibility.py:733 to 736).
  landed is completion's revision_landed (742 to 743).
- Floor entry (frontier.py:183 to 196): unit, record, version, state, station, lane, reason, detail,
  build_dispatch, review_dispatches.
- Replication (control_replica.py:427 to 443): schema, last_durable_seq, last_acknowledged_seq,
  local_committed_seq, pending_exports, oldest_pending_age_seconds, undispatched, backfill_required,
  paused_publication, paused_reason, and pending as seq, command_id, state.

Nothing differs from D 9.3.

Design line references were spot-checked at the build commit:
- control_launch 2263 (open_store), 3168, 3188 to 3190, 3195 to 3214, 3234, 3264 to 3270, 3830,
  3842, 3847, 3857, 3859, 3907 to 3911, 1315.
- agent_sandbox 68 to 71 (x86_64 and ABI 6).
- control_clone 219 to 226 (abi).
- control_service 1438 (socket and lock) and 4477 to 4480.
- control_agent_config_handoff 68 and 412.

All match, except that the heartbeat start D 5 cites as 3863 to 3873 is HB.start at 3869 (3863 is the
release deadline assignment). Within the cited block.

## 7. Host inventory: live layout and client environment

There is no live Veldo installation on this host:
- No veldo-authority-*.service in ~/.config/systemd/user, and no such unit file or unit in
  `systemctl --user list-unit-files`/`list-units`.
- The running control_service processes are all test fixtures under /tmp/veldo-mutations-* and
  /dev/shm/v154-*. The veldo-dispatch-*.scope units are failed transient scopes of fixture dispatches
  (VELDO-9340, VELDO-9341).
- The default install root ~/.local/share/veldo/authority (control_service.default_install_root)
  does not exist. ~/.local/share/veldo holds only guest/ and langgraph/.
- /var/lib/veldo exists, 0700, owned by the account, and is empty. It passes
  control_factory_setup.state_root_problems as is.
- No `<git common dir>/veldo` in any repository under ~/projects. A search of ~, /var/lib/veldo, /srv
  and /opt (depth 6, excluding /tmp, worktrees and fixtures) finds no control.sqlite3,
  enrollment.json or authority.sock.

So, for the brief's inventory items:
- Live receiver configuration's store path: none.
- Entries of the live store directory: none, because there is no directory. No unnamed entry exists.
- Runs location and generated run paths: none.
- Placement: not applicable.
- The live layout is neither a refused legacy layout nor an accepted one.

A first factory setup with state root /var/lib/veldo would put the store at /var/lib/veldo/authority
(control_factory_setup STORE_DIR 'authority', keys in 'keys'), with runs at <state_root>/runs
(runs_root). That passes D 7's runs and placement checks by construction: /var/lib/veldo is beneath no
home, temporary or runtime directory.

Client environment (this host, logins used):
- CODEX_HOME is unset in the account environment, so codex1 is the default ~/.codex.
- CLAUDE_CONFIG_DIR is set per session to a login under ~/.claude-accounts (acct1 to acct7; this
  runner's own session uses another one). ~/.claude also exists.
- XDG_STATE_HOME and TMPDIR are unset. XDG_RUNTIME_DIR is /run/user/1000.
- read_link sources and their resolved targets: every existing source resolves to itself, with no
  link out:
  - codex: ~/.codex/skills, ~/.codex/rules, ~/.codex/plugins/cache.
  - claude acct1: plugins/cache, plugins/marketplaces, plugins/synced, skills. agents and commands are
    absent.
  - ~/.claude: plugins/cache, skills. agents and commands are absent.
- None of these places or targets is under /var/lib/veldo, so with this environment the census finds
  no conflict for a factory store.

Migration from the conventional Git-directory store: none is established. control_store keeps
DB_RELATIVE only as a recorded convention (control_store.py:330 to 332). Enrollment refuses an
implicit rebind ("a host change is a controlled migration, never an implicit rebind",
control_enrollment.py:247, and generation and clone checks force re-enrollment). No command, script or
document in .veldo, scripts or docs moves a store and rewrites its signed bindings
(scripts/migrate_to_veldo.py is the public-tree migration, unrelated). D 7's recovery for a
conventional layout therefore stays "create store-guard.off". Moving to a factory layout would need a
new procedure. This host has no conventional store to move.

## 8. Findings for the lead and for B2

- F1. Codex workspace-write. On this host, Codex 0.166.0's own sandbox fails to start a shell command
  without the guard too: codex-3, identical error. The cause is the AppArmor restriction on
  unprivileged user namespaces (sysctl 1), so it is not attributable to the ruleset. The design's
  claim "with workspace-write its shell command fails to start" holds here, but the cause is not the
  guard. Today, a workspace-write Codex role on this host cannot run shell commands at all, guard or
  not. B2's mutant store359-role-sandbox-wins still produces "fails to start" on this host, so the row
  cannot tell Landlock from AppArmor here. Its proof needs either a host without the AppArmor
  restriction or a statement that the outcome is host-caused. This does not reopen the Codex sandbox
  decision (danger-full-access inside guarded runs), which codex-1 shows works.
- F2. Claude Code optional sandbox. With sandbox.enabled, 2.1.317 turns its sandbox off ("socat not
  installed") and runs Bash unsandboxed under Veldo's ruleset. D 8 and D 12 item 2 ("fails inside a
  guarded run") are not observed on this host: it does not fail, it does not engage. Even with socat
  installed, bwrap would hit the same AppArmor refusal as in F1.
- F3. Errno classes for B2's rows: link out of the store gives EXDEV (Landlock REFER). Everything else
  guarded gives EACCES. Under the risky runner, AF_UNIX gives EPERM (seccomp) and listing gives EACCES.
- F4. Live layout: there is none, so the preflight inventory is vacuous on this host (section 7).
  Default runs on this host go through no receiver today. B2's live-layout exit therefore rests on the
  factory layout as constructed, not on a measured installation.
- F5. Lease placeholder. Releasing the acct1 placeholder with `kill $(cat /tmp/claude-1000/acct1-b0-hold.pid)`
  (pid 644484, `flock .../acct1/.runner-lease sleep 14400`) did not free the lease. Its child
  `sleep 14400` (pid 644487, parent 644484) had inherited the lock (/proc/locks showed the FLOCK still
  held). My run waited. I then killed pid 644487, the same placeholder's child and nothing else, and
  the run took the lease. Future placeholders should be killed by process group, or hold the lock in
  the process whose pid is recorded.
- F6. The risky runner takes the client's login lease itself and refuses when the caller holds it
  (risky-1). It also refuses a socket on a standard descriptor (risky-2). Test harnesses for B2's
  launch/risky-real row must hold no lease and give it /dev/null or pipes.

## 9. Not done, by the brief

No product code changed. No real store touched (none exists). No store-guard.off created or deleted
anywhere. scripts/verify.sh not run. No sub-agents.
