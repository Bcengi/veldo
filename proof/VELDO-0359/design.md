# Agent runs cannot reach the Veldo store: design (revision 6, run boundary only)

Date: 2026-11-22. Revision 6. Scope is unchanged from revisions 3 to 5: what the owner approved under
"Scope narrowed" in research/approvals/2026-11-21-veldo-store-write-lock.md (Telegram 42876 question,
42877 lead answer, 42878 "Yes"). Revision 5 answered validation-narrow2.md; revision 6 is a small
revision answering validation-narrow3.md (CHANGES, one high, three medium). The switch rule is the
decided one and is not changed: the guard is ON by default, and the PRESENCE of store-guard.off in the
store directory turns it OFF; deleting the file turns the guard back on. Revision 6 separates the risky
census's actual grants from the locations used to construct them (section 6), gives the receiver an
explicit path for an audit failure before the identity line (section 5), and corrects test rows whose
fixtures could not produce their required outcome (section 15). revision-notes.md records what changed.
Code read in the worktree space-0329b at 23318512. Spec draft: spec-draft.md beside this file
(VELDO-0359).

## 1. Decision

One new boundary: no agent run's own processes may open the contents of, or change names in, the store
directory.

- The store directory is the real directory that holds the database the launch receiver actually opens.
  The receiver opens its configured store path (control_launch.py:2263), and open_store resolves that path
  (control_store.py:374 to 413). The store directory is therefore the directory of the fully resolved
  database path, and the database's sidecars are that resolved basename plus -wal, -shm and -journal. The
  existing authority.lock and the authority's listening socket authority.sock live in that directory
  (control_service.py:1438; control_client.py:55, 82 to 85); how either is opened or bound does not
  change. On a factory installation the directory is `<state root>/authority`. The risky runner's
  `{authority}` placeholder means the Veldo checkout (agent_sandbox.py:714); this design never uses the
  word in that sense.
- Default runs get the boundary as one Landlock ruleset, installed by the trusted wrapper before the
  heartbeat and the engine start. It is one ruleset, not one kernel rule: control_clone expresses "every
  directory but this one" as several allow rules along the store directory's ancestor chain.
- Risky runs already run under the VELDO-0208 confined runner, whose own Landlock allowlist is built from
  its configuration. They get no new layer. Before acceptance the receiver checks that the runner's
  effective grants for this launch, after the runner's own exclusions, cannot reach the store directory,
  that nothing the runner copies in comes from it, and that the host meets the runner's own kernel floor.
- The commands a run uses to read store answers (plan run-check, frontier, status, the work-state
  completion view) ask the run's own launch receiver through a closed query protocol instead of opening
  the store.
- Codex runs with its own sandbox off inside a guarded run; Veldo's ruleset is the boundary around it
  (lead decision, kept).
- The guard is ON by default. The PRESENCE of a file named store-guard.off in the store directory turns
  it OFF for every later local launch; deleting that file turns it back ON. The state is shown on every
  launch record and in the status output (section 10).

Nothing else changes. Veldo's own processes (the authority service, the receiver, the effect executor,
the signer, the space worker, setup and maintenance commands, the CLI, the API process) open the store
exactly as they do today. No check is added at authority start or in setup. The authority socket is not
moved and its authentication is not changed.

## 2. What was dropped, by the owner's decision

Revision 2 also made authority.lock a write capability for Veldo's own processes (open_store refusing a
writer without the lock's flock, every writer migrated, the signer reparented, setup reordered, layout
checks at authority start and in setup, a write census). The owner asked "Locking anything is risky. Are
you sure this is needed?" (42876); the lead recommended building only the run block (42877); the owner
agreed (42878). All of that stays dropped in revision 5. The reasons: it touched about twenty write sites
and the signer's serialization, so a defect stops the authority or corrupts signing; and it guarded only
Veldo's own cooperating code, because flock is advisory and any unconfined same-account process can
bypass it.

Consequences, stated: VELDO-0113's contract-gap row stays a GAP row; a Veldo process outside a run can
still open the store for writing; the protected signer, setup ordering, backfill and the W1 constructor
are untouched.

## 3. The boundary, stated exactly

| Process | Store directory contents | Mechanism | What it can still do |
|-|-|-|-|
| A default run (engine and every descendant), every launch kind: engine run, conversation turn, workflow step | Cannot open for read or write, create, remove, truncate, rename into or out of, or link | The new ruleset, kernel enforced, irreversible inside the run | List the directory and stat its entries; chmod them (availability only); send signals it already could; connect to the existing authority socket, which is ordinary IPC that Landlock's filesystem rights do not govern, and be refused without a member signature; ask its own receiver, or another live receiver, the closed questions of section 9; ask an unconfined same-account process to act for it |
| A risky run (VELDO-0208 confined runner) | Same | The runner's existing allowlist, which the receiver checks, for this launch's effective post-exclusion grants, cannot reach the directory | Use TCP and TLS (agent_sandbox.py:166), so an authenticated TCP service on this host could act for it; no Unix sockets (agent_sandbox.py:176 to 178), so no run query |
| Every Veldo process outside a run | Unchanged | None new | Everything it does today |
| Any process of the owner's account outside a Landlock domain | Unchanged | None. The single-user rule leaves this undefended | Everything it can do today |

The guarantee: while the guard is on, no default or risky run's own processes can open the content of,
create, remove, truncate, rename into or out of, or link any entry beneath the store directory, provided
the launch preflight of section 7 passed. It is content and name confinement, not literal "no access":
listing, stat, chmod and execute are not handled (control_clone.py:134 to 147), and connecting to the
existing authority socket stays possible because it is IPC already protected by command authentication,
not a filesystem content access. A run cannot directly disable the guard (section 10). It does not stop an
unconfined process of the same account, and it does not stop a run from asking one to act for it. It does
not promise the receiver's availability or the secrecy of the store's names, sizes and times.

## 4. Premises checked against the code

| Premise | What the code says | Consequence |
|-|-|-|
| Default runs are unconfined today | control_launch.py:401 to 420 (runner_decision), 476 (runner_argv returns the argv unchanged), 3168 to 3190 (contained spawn adds limits, no filesystem rule); VELDO-0254 AC3 | New enforcement; amends VELDO-0254 AC3 |
| Every local default launch passes one trusted wrapper | The contained form of wrap (control_launch.py:3830); Receiver.launch is the one caller; the wrapper parses its held configuration and heartbeat arguments (3842 to 3846), may write a refusal to stdout when the executable is missing (3847 to 3850), writes its identity to stdout (3857 to 3858), reads release from fd 0 (3859), starts the heartbeat (3863 to 3873), writes the success byte (3907 to 3908) and execs (3911) | One installation point covers every default launch; the descriptor audit must come before 3847, the first use of any standard descriptor (section 5) |
| The authority's socket is a normal entry of the store directory | socket_path_for puts authority.sock beside the binding's store path (control_client.py:55, 82 to 85); the service configuration names it (control_service.py:1438) and the service binds and stats it before serving (4477 to 4480); bind makes its directory 0700 and the socket 0600 and unlinks a stale one first (control_client.py:461 to 474) | The entry check allows exactly this one socket entry (section 7); every other special entry still refuses |
| No Landlock layer can precede the risky runner | The runner's helper mounts (veldo_userns.c:228 to 229, 247 to 248) before its own Landlock (agent_sandbox.py:158, 2881); a Landlock-restricted task cannot mount | No layer before the risky runner |
| The risky runner's grants are post-exclusion | grants_for (agent_sandbox.py:818 to 894) skips any read item beneath a deny_read entry, and for a read item that is an ancestor of one it grants each non-symlink child recursively instead (841 to 849); write roots are added without that filter after a validation that refuses writes overlapping the runner's own protected paths (830 to 831, 865) | The census compares the runner's effective grants after its exclusions, so a broad read root with a working exclusion is accepted (section 6) |
| The risky runner's other grants come from configuration, environment and resolved links | read roots, the worktree, the runner checkout, the fresh scratch directory (made below a parent at 2198 to 2218 and granted itself, never its parent, 853 and 865), installed tools (1150 to 1166), extra reads (858 to 859: project roots and the resolved targets of client read_links whose sources exist, 2266 to 2269), the configuration file (863 to 864) and the Git common directories (866 to 890); resolver_grants adds a resolved runtime directory (896 to 907); before grants are computed the runner adds borrow_root and every client's credential sources to deny_read (2263 to 2264); client places come from CODEX_HOME or CLAUDE_CONFIG_DIR or defaults (1234 to 1283) and only expand sources, they are not granted; client state gets read and write only after state_grants creates and qualifies it against its refused set (1329 to 1374, 2290 to 2292); seeds and credentials are copied before confinement (2283 to 2287), and seed only excludes the runner's own reuse store (1496 to 1510) | The census separates construction inputs, actual grants and copy sources and models this launch's prepared configuration (section 6) |
| The risky runner has its own kernel floor | x86_64 only, and ABI 6 or higher (agent_sandbox.py:68 to 71) | With the guard on, the receiver applies the same floor before acceptance (section 7) |
| The runs directory can fall inside the store directory | runs_root falls back to the store's own directory plus /runs when neither `runs` nor `state_root` is set (control_launch.py:1315 to 1319); upgrade writes exactly that for configurations without a state root (control_factory_setup_upgrade.py:195 to 196); the engine's generated configuration and runtime live there (control_launch.py:2899 to 2913, 2932 to 2943). With no state root, Veldo's services also put the space ledger and conversation state beside the store (control_space_reconcile.py:872; control_service.py:2160) | Such a layout is refused before acceptance, never accepted and then failed (section 7) |
| The conventional enrollment layout keeps the store beside the binding | The conventional store is `<git common dir>/veldo/control/control.sqlite3`, which is what an enrollment writes into a binding (control_store.py:330 to 332; control_enrollment.py:44 to 45), beside enrollment.json and clone_uuid, which a run reads | Under the guard that layout is refused by name (section 7) |
| Run-side gate callers, inventoried | plan: decide, decision_blockers with references (plan.py:98, 344); frontier: decide, observe, domain_uuid, repository_uuid, and gate.conn inside _floor_entry (frontier.py:183 to 240, 276 to 299); work: decide, observe, coordinates (work.py:125 to 173); completion_status: landed (control_eligibility.py:475); work_state.completion_view: completion (work_state.py:336), a registered completion consumer (control_eligibility.py:172 to 186); runstatus: refusal_types, refusal_code, close (runstatus.py:225 to 233); coordination: coordination_decision reads gate.SCHEMA by hasattr, gate._reading and gate.conn and requires a pm_cycle (control_workflow_cycle_pm.py:134 to 175); executor passes context and ticket (executor.py:582 to 597) | The remote gate contract of section 9 covers each; anything else stops by name |
| This host | Kernel 7.0, Landlock ABI 8, x86_64. /var/lib/veldo exists, 0700, owned by the account, and was empty when revision 4 was written | Unaffected by either floor. B0 must locate the live receiver configuration and prove its layout passes before enforcement ships |

## 5. The ruleset for default runs

Where and in what order. In the wrapper's contained form:

1. Immediately after parsing the held configuration and the heartbeat arguments (control_launch.py:3842
   to 3846), and before the missing-executable branch (3847), the identity line (3857) and the release
   read (3859), the wrapper reads the guard decision the receiver sampled for this launch from the held
   description (section 10). With the guard off it does none of the guard steps below.
2. Still before any of those uses, it audits every open descriptor (below). This is the one audit; it
   comes before any standard descriptor or protocol channel is written or read, so a store handle on fd 0,
   1 or 2 is never used for the identity line or the release read. On a finding or an enumeration
   failure it reports only through the setup pipe, and only when the setup pipe descriptor itself passed
   the audit: it writes the guard failure byte and the step code (audit), then exits. When the setup pipe
   did not pass, or is absent, it exits without writing anything, with a dedicated exit status. It never
   reports through stdout or stderr on this path.
3. It continues as today: the missing-executable branch, the identity line, the release read.
4. After release and before the heartbeat starts (3863), it probes Landlock again, builds the ruleset
   with control_clone.rules (deny_read and deny_write on the store directory the receiver put in the held
   description) and installs it with control_clone.confine. Any probe, create, add or restrict error
   writes the failure byte with that step's code to the setup pipe and exits.
5. It starts the heartbeat, which inherits the domain, and continues as today to the success byte and
   exec.

The heartbeat child is created only after both the audit and the ruleset, so it holds no store handle and
is confined. The wrapper opens no descriptor between the audit and the ruleset that could name the store:
its own reads are of its pipes, and reading a pipe with os.read accepts no passed descriptor. The
existing close_fds spawn with only the heartbeat and setup pipes (control_launch.py:3188 to 3190) and the
existing heartbeat sanitation stay.

What it denies beneath the store directory: read file and every write right control_clone handles at ABI
3 (write file, truncate, make every kind of entry, remove file and directory, refer). Everywhere else it
grants those rights by control_clone's ancestor-chain construction. Connecting to the existing authority
socket is not a Landlock filesystem right and stays possible; binding a new socket there needs make,
which is denied.

Descriptor audit. The wrapper enumerates /proc/self/fd, excluding the descriptor it uses for the
enumeration by identity, and checks every descriptor, standard streams and protocol channels included. A
descriptor is a finding when its device and inode equal the store directory's or those of any entry
beneath it (the wrapper lists the store directory once for this, without following links), or when its
procfs link, with a deleted marker removed, names a path beneath the store directory. Identity covers
renamed handles; the path covers deleted ones. The check is by identity and path only, never by type, so
an ordinary log file or terminal on stderr outside the store passes. An unreadable or missing
/proc/self/fd, a descriptor whose identity or link cannot be read, or a store directory that cannot be
listed is an audit failure, never a clean result. Landlock does not revoke an already open file
description, so this audit, not the ruleset, covers inherited handles.

Acknowledgement and reporting. The guard failure byte is one new setup-pipe byte followed by one step
code: audit, probe, create, add or restrict. The receiver reads it on two paths, because an audit failure
happens before the identity line and the other steps happen after release.

- Pre-identity path (audit). Today the receiver reads the wrapper's identity line in _reported
  (control_launch.py:3264 to 3270), which raises on EOF; _contained turns that into
  spawn_failed:containment:unavailable (3195 to 3214) before the setup pipe is ever read, and the
  post-release reader (3234) is reached only after identity, group attachment and release. So the
  receiver gains an explicit pre-identity handshake: when reading the identity fails (EOF, no line by
  the deadline), and before classifying the failure, it inspects the setup pipe and reaps the wrapper,
  both within the existing bounded identity deadline (ACCEPT_SECONDS), without extending it. A failure
  byte with step audit on the setup pipe records store_guard enforce_failed with step audit. No byte,
  setup pipe at EOF, and the wrapper's reaped exit status equal to the dedicated audit status records
  enforce_failed with step audit, unreported. Anything else keeps today's generic containment error. The
  receiver never releases a worker without a valid identity line, never reads a child standard stream to
  obtain an audit report (the identity read on stdout is today's read and is the one that failed), and
  keeps today's containment cleanup (group.discard) on every one of these outcomes.
- Post-release path (probe, create, add, restrict). The existing setup-pipe reader (3234) gains the
  failure byte and its step code. The success acknowledgement after release is unchanged.

The receiver records store_guard pending on acceptance of a guarded launch and applied only when it reads
the success byte; a failure byte on either path, the dedicated audit exit status on the pre-identity path,
or a wrapper exit without the success byte after release records store_guard enforce_failed with the step
(or "unreported") and no engine. A guarded contained launch without a setup pipe is refused before
acceptance.

What the ruleset costs, stated:

- Ancestors. No entry can be created, removed or renamed directly in an ancestor of the store directory,
  and a file created directly in one after the run starts cannot be read; existing files keep their
  access (control_clone.py:60 to 80). With the store at /var/lib/veldo/authority the chain is
  /var/lib/veldo, /var/lib, /var and /.
- Listing, stat, chmod and execute are not covered.
- Mounts. A Landlock-restricted task cannot mount or pivot_root. Inside a default run, bubblewrap,
  rootless podman and buildah, unshare with mounts, Codex's own sandbox and Claude Code's optional sandbox
  stop working. Daemon clients (the docker client) are unaffected.
- Startup time. Building the ruleset lists the siblings of every ancestor. B0 measures it against the
  heartbeat setup deadline.

## 6. Risky runs: no new layer, one data check of the effective grants

The wrapper execs the confined runner unguarded, as today, because the runner must mount before it
confines itself. Before acceptance, the receiver computes, as data, the runner's actual grants and copy
sources for this launch and refuses with confined_runner_unavailable:store_reachable when any actual
grant reaches the store directory, or confined_runner_unavailable:store_source when a copy source does. It
reads the same configuration file and the same environment that the launch will hand the runner (the
runner argv's --config path and the engine environment it builds for this launch, including CODEX_HOME and
CLAUDE_CONFIG_DIR); it never inspects a default file while launching with another.

The census keeps three sets apart. Only set (b) is compared with the runner's grants.

(a) Placement and source-expansion inputs. These are locations used to construct grants or to place the
launch; they are not grants. They are: the selected client's places (from the environment variable or the
configured default, which may be outside the home directory), which client_files uses only to expand the
client's source entries (agent_sandbox.py:1234 to 1285); and the scratch parent, below which the runner
makes a fresh scratch directory (2198 to 2218) and which is never itself granted. These inputs are judged
only by the conservative placement checks of section 7 (AC3): a client state place overlapping the store
directory and a scratch parent that is an ancestor of it are refused there. A place contributes to the
grants only through the source entries that actually use it, and a place with no used entry contributes
nothing.

(b) Actual post-preparation grants. The census models the same prepared configuration the runner builds
before grants_for, including the implicit exclusions: deny_read extended with borrow_root and with every
client's credential sources (2263 to 2264), not only the selected client's configured exclusions. On that
configuration it computes exactly the grants that grants_for, resolver_grants and qualified state_grants
emit, each after placeholder, '~' and environment expansion and with every symlink resolved:

- read grants through grants_for's read filter: read_roots and the worktree, runner checkout and scratch
  placeholders; installed tools (optional_read_roots, toolchain roots and their PATH entries); extra reads
  of the agent profile, which are project_read_roots and the resolved targets of the selected client's
  read_links whose sources exist (2265 to 2269); the configuration file; the repository's shared Git
  common directory and the agent's private repository (from the configured git_common_dir or the
  checkout, and from VELDO_EXPECTED_GIT_COMMON). The filter is grants_for's (841 to 849): a read item
  beneath a deny_read entry contributes nothing; a read item that is an ancestor of one contributes its
  non-symlink children, recursively, instead of itself;
- the resolved DNS resolver directory that resolver_grants adds;
- read-write grants: write_roots, which the runner adds unfiltered after its own overlap validation
  (830 to 831, 865), and the Git grants of a writable worktree;
- client state grants as state_grants would emit them (1329 to 1374): none when the client's home place
  is absent or not a directory; otherwise each state_dirs and state_files entry at its resolved path,
  where an entry that does not exist yet is represented at the path state_grants would create, without
  creating it; an entry the runner's own qualification would refuse (wrong type, outside the real home,
  or overlapping its refused set, which includes the store) is not a grant, because the runner refuses
  the start instead. The census refuses that launch before acceptance as store_reachable when the
  overlap is with the store directory. The preflight is read-only: it never calls the mutating state
  preparation, never claims state and never creates a directory or file.

The fresh scratch directory is represented by one symbolic identity, the same in the census and in the
runner-side parity computation (or by its actual path when a fixture knows it); its parent is never
compared as if granted. A resulting grant conflicts when it equals, lies beneath, or is an ancestor of
the store directory, compared after resolution in both directions. So a configured read root of /var/lib
with deny_read on the store directory is accepted, because the runner never grants /var/lib itself, while
the same read root without that exclusion is refused.

(c) Copy sources: the general seed_files, the client's seed_files and its credentials. They are judged
separately and without the deny_read filter: a source resolving beneath the store directory refuses even
when no grant covers it, because the runner copies its content into scratch before confinement.

Optional semantics are the runner's: an absent optional item (an absent optional read root, project root,
read_link source, seed or credential source, an absent client home place, or a state entry the runner
would create) behaves exactly as the runner treats it; an absent source contributes nothing, and a state
entry to be created is modelled as described in (b). A malformed or unresolvable required item refuses.
This adds no outage for a missing optional tool.

Why a receiver-side census, not deny lists. agent_sandbox.py and agent_sandbox.json are protected paths
(.veldo/policy.yaml:24 to 25, 37 to 38) and stay untouched. A store entry in the runner's deny lists would
still not cover seeds, which the runner checks only against its own reuse store (agent_sandbox.py:1496 to
1510). Drift between the census and the runner is caught in the gate, not at launch: a parity row
compares, on each fixture on which the runner's grant preparation succeeds, only set (b), normalized by path and rights with scratch as its symbolic
identity, with the grants the runner actually emits from grants_for, resolver_grants and qualified
state_grants on the same prepared configuration, and fails when the runner grants anything the census
does not list or the census lists anything the runner does not grant. Places and the scratch parent are
not in either side of that comparison. Copy sources (c) are compared with the runner's seed and
credential sources separately. Parity fixtures include the shipped Claude and Codex configurations, the
credential exclusions, an absent state home and newly created state entries; accepted controls include
an unused place and a place with only disjoint selected sources. The shipped configuration
(scripts/agent_sandbox.json) names nothing under /var/lib and is expected to pass; B0 confirms that on
this host's actual client environment.

The risky floor. With the guard on, the receiver also refuses a risky launch before acceptance when the
structured probe reports a platform other than x86_64 or an ABI below 6, as confined_runner_unavailable:
platform or confined_runner_unavailable:landlock_abi_below_6. This mirrors the runner's own floor
(agent_sandbox.py:68 to 71), which stays unchanged as a second check. It only moves a failure that already
happens today, after acceptance inside the runner, to before acceptance; it adds no new outage. If the
runner's floor ever changes, a mismatch shows as a named early refusal or as today's runner failure, never
as an unguarded run.

The receiver records store_guard pending with precondition_checked on acceptance of a risky launch, and
runner_started on the success byte, never applied, because the wrapper's success byte precedes the
runner's own confinement (control_launch.py:3908 then 3911; agent_sandbox.py:2881). The evidence that a
risky run cannot reach the store is the real risky launch of the tests.

## 7. The launch preflight that keeps the boundary true

Before acceptance, with no worker spawned on a refusal, every local launch (default and risky) with the
guard on passes these checks, in this order. Every refusal names the element, the resolved path and the
recovery action, which is either fixing the layout or creating store-guard.off in the store directory
(its presence turns the guard OFF for later launches).

| Check | Required | Refusal |
|-|-|-|
| Switch | The switch sample of section 10 is a clean absence (guard on) or a valid marker (guard off, preflight skipped) | invalid_input:layout:switch |
| Kernel | A structured probe beside control_clone.abi, which itself stays unchanged and still collapses failures to 0 (control_clone.py:219 to 226), reports the version or one reason: unsupported_platform (not Linux x86_64 or aarch64), landlock_disabled (EOPNOTSUPP), syscall_missing (ENOSYS), syscall_blocked (EPERM), abi_below_3. Both local kinds need ABI 3. A risky launch additionally needs x86_64 and ABI 6 (section 6) | unavailable_service:confinement:store_guard:<reason>; for the risky floor confined_runner_unavailable:platform or confined_runner_unavailable:landlock_abi_below_6 |
| Store directory | The configured store path resolves fully to a regular database file; its real parent directory is owned by the account. That real directory is the one the ruleset names and the marker is read in. Symlinks on the configured path are followed, not refused: Landlock attaches rules to the resolved directory, so any name reaching it is covered | invalid_input:layout:directory |
| Store entries | Every entry beneath the store directory, listed recursively without following links, is a directory or a regular file with link count 1, with exactly one named exception: the entry authority.sock directly in the store directory may be a socket, when it is owned by the account and has link count 1. That is the authority's own listening socket at the path socket_path_for derives (control_client.py:82 to 85); it is accepted whether or not the authority is serving, since the service unlinks a stale one before binding (control_client.py:468 to 469). The database's actual sidecars (resolved basename plus -wal, -shm, -journal) and authority.lock are regular files and are checked like every other. Any other socket, any socket elsewhere beneath, a FIFO, a device, a symlink or a multiply linked file refuses: a symlinked sidecar would send store content outside, and a hard link would give it an outside name. The exception adds no filesystem grant; the ruleset still denies every content and name right on the socket entry | invalid_input:layout:entry |
| Mounts | /proc/self/mountinfo of the receiver's own mount namespace, which is the one the wrapper enforces in, parsed with each mount's filesystem root translated per device, shows no second mount exposing the store directory, an ancestor of it, or any file or subtree in it (directory and single-file binds). Raw mountinfo roots are never compared with host path strings. Unreadable or unparsable mountinfo refuses | invalid_input:layout:mount |
| Runs location | The runs root (control_launch.py:1315 to 1319) and the run's generated configuration and runtime directories are outside the store directory. The fallback that puts runs inside it is refused, not relocated | invalid_input:layout:runs |
| Placement | No required launch location equals or lies beneath the store directory, and the store directory lies beneath no location the run must create entries in. Required locations: the worktree, its gitdir and Git common directory, the home directory, the temporary directory, the user runtime directory, the runs root and the run's directories, the engine's client state and, for risky launches, the scratch parent. Read-only locations (installed tools) need only to be outside the store directory | invalid_input:layout:placement |

Normal entries of a factory store directory, inventoried from code: the database, its sidecars,
authority.lock and authority.sock. B0 lists the live directory; if it finds any other service-owned entry
that the entry check would refuse, B2 does not start until the specification names it as a further exact
exception with its reason. The policy is never widened to "any socket" or "any special file".

Previously supported layouts newly refused while the guard is on, stated:

- A receiver configuration with neither `runs` nor `state_root`, including configurations upgraded that
  way (control_factory_setup_upgrade.py:195 to 196). Refusing is correct: accepting it would break engine
  startup, because the engine's generated configuration is written beneath the store directory. Recovery:
  set `runs` to a directory outside the store directory, or create store-guard.off (guard OFF). No automatic
  relocation.
- The conventional layout with the store in `<git common dir>/veldo/control`, beside enrollment.json and
  clone_uuid. It fails placement twice (the store is beneath the Git common directory, and runs must read
  files in that directory). The immediate recovery is creating store-guard.off (its presence turns the guard OFF). Moving to a factory layout is an
  operational migration, not a configuration edit: the configured store and the signed bindings must
  agree. This design does not claim an established migration procedure; B0 must name one, or report that
  none exists, before the owner is told moving is available.
- A store directory beneath home, the temporary directory or the runtime directory, as in revision 3.

The switch-off path uses the old locations and the old launch path for all of these.

Only local launches are checked; remote launches are unaffected because the store is not on that host.
Aliases created later by an unconfined owner process are a residual (section 13); a guarded run cannot
create one, because cross-directory link and rename need REFER, which is denied, and it cannot mount.

## 8. Engines under the ruleset

Codex (lead decision, kept). Codex 0.166's own sandbox mounts through bubblewrap, which a Landlock domain
forbids. Inside a guarded run, the receiver's Codex configuration step sets sandbox_mode to
danger-full-access after the role's settings are applied (control_agent_config_handoff.py:68, applied at
412), so it wins over any role or account setting. Approval policy is not changed. The same applies to
risky launches. Sandbox off is selected only for launches whose sampled guard decision is on, and the
wrapper never execs when the audit or the ruleset fails, so Codex never runs with its sandbox off and
without the ruleset. With the switch off, the role's setting stands. Codex's sandbox is never switched off
as a fallback for an enforcement failure.

Tradeoff, stated: roles that used workspace-write (VELDO-0177, VELDO-0184) lose Codex's per-command
confinement everywhere except the store directory, and model commands can write anywhere else the account
can, as under full access before. Mounting fails. The measured claim is only that the store directory
stays unreachable.

The receiver's trusted Codex preflight invocations (codex_listing and codex_check_launch,
control_launch.py:2941 to 2943) run in the receiver, before the wrapper, unguarded, and execute no model
tool. They are not evidence for the guarded run; the proof uses the model exec under the wrapper.

Claude Code. Factory adapters do not enable its sandbox (control_factory_setup_dispatch.py:113 to 123).
Its ordinary Bash tool must work under the ruleset with a writable worktree, home and temporary directory
and readable generated configuration; B0 proves that with the pinned 2.1.317, and B2 does not start
unless it holds. If an account enables Claude Code's optional sandbox, it fails inside a guarded default
run; that is stated, not fixed.

## 9. Run-side store readers move to the launch receiver

### 9.1 Decision

Runs do not open the store at all, not even read-only: with read allowed, a run can open authority.lock
and take its flock, and read every repository's records. The run-side readers ask the receiver that
already serves the run and already reads the store (control_launch.py:2467, 2480, 2535).

### 9.2 Endpoint and lifecycle

Before acceptance, the receiver with the guard on creates, exclusively, a 0700 directory under the user
runtime directory named by a digest of the dispatch id long enough to make collisions negligible, binds
and listens on query.sock in it, and starts the serving thread. The serving thread opens its own
read-only store connection, in that thread, and then signals ready. The receiver waits for ready, within
a bounded deadline, before acceptance. Any failure (existing directory, bind, listen, connection, ready
deadline) refuses the launch before acceptance as unavailable_service:run_query, removes what this
receiver made, and spawns nothing; a later refusal of the preflight also removes it. The socket is named
to the engine in VELDO_RUN_QUERY, registered as Veldo's own beside VELDO_DISPATCH_ACCEPTANCE so the
VELDO-0254 launch scan does not flag it.

A socket path holds 107 bytes, so the directory is named vq- plus 32 hexadecimal digits of the digest,
which fits a runtime directory of up to 60 characters. When the runtime directory is longer, the same
directory is made, by a fixed rule, under the first of these that is a real directory (not a link) owned
by the account with no group or other access: /run/user/<uid>, the account's system runtime directory;
then /tmp/veldo-<uid>, made 0700 if absent. The first is the runtime directory itself. The second has the
same owner and mode, is checked on every use, and sits in a sticky directory, so another account can
neither enter nor replace it; if another account made that name first, it is not used. The Runner
derives the same path by the same rule. Only when neither exists is the launch refused, as
unavailable_service:run_query:no_short_private_directory. The abstract socket namespace is not used.

Each request is one bounded read transaction with a deadline on the serving thread's connection; no
transaction stays open between requests. Heartbeat and stop processing never wait on it.

Cleanup has exactly two owners, and both act only on an endpoint whose owner is known to be finished:

- the receiver removes its own directory when its run ends;
- the supervising Runner that spawned the receiver removes that receiver's directory after observing the
  receiver's exit.

There is no opportunistic cleanup at receiver start. A connection-refused probe cannot tell a dead
endpoint from one still starting (a bound socket refuses until listen), so a sweep could remove a live
launch's endpoint; it is omitted rather than made clever. An endpoint survives only when both the receiver
and its Runner die; it is then an empty directory and a socket nobody listens on, named by a dispatch id
that is never reused, so it affects no later launch, and it goes away with the user runtime directory
(logout or reboot). That leftover is listed as a residual. No new service is added.

### 9.3 The remote gate contract

control_eligibility.entry_gate, in an enrolled workspace with VELDO_RUN_QUERY set and no wired gate,
returns a remote gate instead of opening the store. A gate an unconfined orchestrator wired in is passed
through unchanged, as today (control_eligibility.py:464 to 465); moving answers does not move any
orchestrator's write behavior. The remote gate holds only these members:

| Member | Contract |
|-|-|
| domain_uuid, repository_uuid, authority_generation | Immutable, from the receiver's verified launch binding, returned once by a hello exchange. The client reads its workspace's binding locally (a file in the Git common directory, readable) and stops with run_query:other_repository when its repository differs, so a command run against another checkout never gets the launch repository's answers |
| SCHEMA | The eligibility decision schema constant, local, so coordination_decision's hasattr probe (control_workflow_cycle_pm.py:136) keeps its answer |
| decide(station, unit, *, context=None, ticket=None) | Station is a known station or coordination; unit a non-empty string. Context is forwarded as a bounded JSON object, as callers construct it today; ticket is forwarded as the JSON decision it is (control_eligibility.py:1064 to 1073 already shapes identities for JSON). The receiver applies Gate.decide unchanged, which routes coordination to coordination_decision (1094 to 1095), including the ticket's unit and domain check and staleness by consumed-input identity (1091 to 1133) |
| decision_blockers(unit, references=()) | References forwarded; the receiver applies Gate.decision_blockers unchanged (893 to 918) and returns its codes |
| completion(unit) | The four facts attempt_finished, artifact_accepted, revision_landed and objective_satisfied (completion_contract.py:54), exactly as Gate.completion computes them, with all four false for a unit with no subject, as today (control_eligibility.py:730 to 740). No receipt, record or landing id is returned |
| landed(unit) | Local: completion(unit)'s revision_landed, as Gate.landed is (742 to 743) |
| floor_entry(unit, word, landed) | The projected floor entry frontier._floor_entry computes today (frontier.py:183 to 240), in one read transaction |
| replication_status() | The replication projection of the receiver's own store, with the fields below |
| observe(event) | The local callback, as today. Callers' own events (frontier and work floor events, frontier.py:276 to 299; work.py:139 to 160) go to it directly |
| close() | Closes the socket |
| refusal_types, refusal_code(error) | A local tuple holding the named run-query exception, and its code, so runstatus's handling (runstatus.py:225 to 233) keeps working |

Any other attribute raises the named stop run_query:unsupported:<name>, which is also an AttributeError so
existing hasattr probes keep their meaning. There is no conn, no _reading, no SQL, no raw record reader, no
unit_record, no receipts and no file descriptor passing. Methods that open dispatches or record launches
(open_dispatch, launch, handle, close_dispatch) are unsupported inside runs, and the query server's
connection is read-only, so forwarding references, context and tickets is a read query only; it never
authorizes a dispatch or a launch.

Supported inside runs: plan run-check, bundle and hash; frontier claimable, withheld and floor offers and
observations; work's floor joins; status, including the authority override; work_state.completion_view
when its caller builds its gate through entry_gate; coordination decisions. Library callers wired by an
unconfined orchestrator (executor, dispatch, work_state) keep their local Gate; when one of them builds
its gate through entry_gate inside a guarded run, it gets the remote gate and this contract.

Observations travel with answers. Every decide and decision_blockers response is an envelope of the
answer and the events the receiver's Gate emitted for that request, in order: the station decision event
of Gate._record (control_eligibility.py:1141 to 1161), the decision_dependency event (895 to 916) and the
invalid_record event (850 to 860). Each event is forwarded with only these fields: schema, operation,
domain_uuid, repository_uuid, unit, entity (invalid_record only), decision_id, follows, watermark,
accepted_inputs, references (decision_dependency only), outcome, refusals, taxonomy, and for station
decisions architecture with basis, kind, artifact_digest, validator and error. The client delivers them,
in order, to its local observe, so local callback events equal a direct Gate's. No other event attribute
crosses.

Receiver-side binding and scope. The receiver builds its Gate from its own verified binding of the launch
worktree, with that workspace, the host trust and settlement trust; the workspace, trust and authority
inputs are receiver-bound and never come from the client. Scope is checked per operation, before any
read:

- decide at a work station, decision_blockers, completion, landed and floor_entry: when the unit exists
  as an entity, it must be an execution unit of the launch repository; otherwise coordinate_not_served.
  Each reference must be one the Gate would accept for that unit. A unit that does not exist gets the
  same answer a direct Gate gives (a held decision, a blocker code, four false facts, the absent floor
  entry), never a crash of the whole frontier.
- decide at coordination: when the unit exists, it must be a pm_cycle whose recorded domain and
  repository are the launch's; otherwise coordinate_not_served. A cycle that does not exist gets the
  direct Gate's own answer, missing_authority:pm_cycle (control_workflow_cycle_pm.py:141 to 142).

Response schemas, frozen. Identity metadata only: record ids, versions and digests, never a record body,
membership body, key or journal row.

- Decision: schema, decision_id, station, unit, domain_uuid, repository_uuid, follows, inputs, watermark,
  pending, refusals, eligible, and architecture when the station asks it. inputs, per label, is one of:
  id, version, digest and definition (a digest, control_eligibility.py:490 to 495, 1071 to 1072); members
  as id, version and digest triples with their digest (1069 to 1070); or, for a coordination decision's
  cycle, id and digest only (control_workflow_cycle_pm.py:167 to 168). architecture is exactly basis,
  kind, state, required, accepted (id, version, digest or null), artifact (path, type, digest), validator
  (per module: module, role, path, digest; control_eligibility.py:604 to 606), refusals, and problems or
  error when present (1171 to 1206).
- Coordination decision: the same envelope with station coordination, inputs labeled team, snapshot,
  manager, cycle and project, and watermark the journal's maximum sequence (control_workflow_cycle_pm.py:
  136 to 175).
- Blockers: the list of codes.
- Completion: the four named booleans.
- Floor entry: unit, record, version, state, station, lane, reason, detail (codes), build_dispatch,
  review_dispatches (frontier.py:195 to 196).
- Replication: schema, last_durable_seq, last_acknowledged_seq, local_committed_seq, pending_exports,
  oldest_pending_age_seconds, undispatched, backfill_required, paused_publication, paused_reason, and
  pending as seq, command_id and state triples (control_replica.py:427 to 443). This projection is
  store-wide, not limited to the run's repository: it includes store-wide sequence numbers and the
  identities of pending commands of every repository the store serves. That is stated and accepted,
  because it is what status shows today and contains identities, not bodies.
- Errors: run_query:other_repository, run_query:unsupported:<name>, coordinate_not_served,
  unavailable_service:run_query (endpoint missing, refused, timed out or malformed answer), and the
  Gate's own named refusals inside answers, unchanged.

Status. runstatus._replication honors an override (runstatus.py:296 to 308). Inside a guarded run, when
the override resolves to the receiver's own database, status asks replication_status; when it resolves
anywhere else beneath the store directory, status reports the section not present by name before
attempting any open; elsewhere (the default per-repository replica under the Git common directory) it
opens locally as today. No arbitrary path crosses the protocol.

Risky runs have no Unix sockets; their enrolled gate stops by name, as today.

### 9.4 What a run can observe

| Channel | What it yields |
|-|-|
| Its receiver's socket | The answers above, for its own repository, plus the store-wide replication projection, as of the request's read transaction |
| Another live receiver's socket | The same answers for that receiver's repository. A 0700 directory of the same account is not caller isolation; accepted and stated, because the answers are status projections and identity metadata. No caller-isolation mechanism is added in this narrowed scope |
| The authority socket | A connection, then a refusal without a member signature |
| Filesystem | Entry names, sizes, times, owner and mode in the store directory. No content |
| Receiver memory and descriptors | Denied by Landlock's process-domain restriction on ptrace-class access to a process outside the domain; tested (section 15) |

## 10. The switch

Polarity (decided rule, unchanged in revision 6): the guard is ON by default. The PRESENCE of a valid file
named store-guard.off in the store directory turns it OFF. Deleting the file turns the guard back ON. To
turn the guard off, create the file; to turn it on, delete it. There is no activation step and no file to
create at install; launch code never creates or deletes the marker. Any wording elsewhere that reads
deletion as turning the guard off is wrong; validation-narrow3's finding 1 came from a brief that still
carried such an old wording.

Sampling. The receiver samples the marker once per local launch, by no-follow metadata, in the store
directory resolved for enforcement (section 7), before anything else in the preflight, and records the
decision in the held launch description. The preflight, the query endpoint, the Codex setting and the
wrapper all use that one sample.

| Sample | Meaning |
|-|-|
| No entry at that name (ENOENT) | Guard on |
| A regular file, not a symlink, owned by the account | Guard off for this launch: no ruleset, no preflight of this design, no ABI floor, no risky census or risky floor, no VELDO_RUN_QUERY (entry_gate reads the store directly, as today), the role's Codex sandbox setting |
| Anything else: a symlink, a directory, another owner, a failed stat other than ENOENT, an unreadable store directory | Refused as invalid_input:layout:switch with the path and the fix (delete it to keep the guard on, or replace it with a regular file to turn the guard off). Never read as off, never silently read as on |

The marker's contents and mode carry no meaning; changing them changes nothing.

Owner visibility, with honest timing. Each local launch's lines and record carry store_guard:

- on the accepted line of a guarded default launch: pending (guard on, enforcement not yet confirmed);
  later on the record: applied when the success byte arrives, or enforce_failed with the step when it
  does not;
- on the accepted line of a guarded risky launch: pending with precondition_checked; later runner_started;
- on a launch with the marker: off (marker at <path>), immediately;
- on a preflight refusal: refused (<reason>, <path>, <fix>), immediately, with no worker spawned.

Two guard failures happen after acceptance, both before any model code runs: a descriptor-audit failure
and a probe, create, add or restrict failure in the wrapper. The record says enforce_failed with the step
and that no engine was started.

The status command (runstatus status, text and model) gains one store guard line for the enrolled store:
on, OFF (store-guard.off present at <path>, with its modification time and "delete it to turn the guard
back on"), or invalid (<path>, <reason>). The line reports the configuration that later launches will
use; it does not describe runs already in progress, which keep whatever they started with. Status reads
the marker by stat, which needs no store access and also works inside a run. No new service or dashboard.

What a run can do to the switch. A guarded run cannot directly create the marker, link or rename a file
to that name, or replace or move the store directory or its parent: those need make, refer and remove
rights in the store directory or its ancestors, which the ruleset denies. A risky run has no grant there.
A run can recruit an unconfined same-account process to create it; that is the accepted delegation
residual, so the claim is "cannot directly disable".

Time semantics. The marker affects launches that start after it changes. It is a recovery switch, not a
revocation. Creating it does not lift the ruleset from a run already guarded; a blocked job must end and
be relaunched. Deleting it does not confine runs started while it was present, and such a run could
create it again; before treating re-enabling as effective, the owner ends those runs, then checks the
status line. The risky runner's own sandbox stays in effect whatever the switch says.

The full rollback is a revert of the change: the store format, the lock, the socket and the journal are
untouched.

## 11. Old kernels: refuse

Below Landlock ABI 3 the guard cannot be installed. Recommended: refuse every local launch by name while
the guard is on, rather than run and warn. Refusal does cost availability on affected hosts and imposes an
operator step: an automatic fallback would avoid it. It is still recommended because warn-and-run would
leave the protection absent where nobody looks and would need a second Codex path (its own sandbox back
on) tested only on old kernels. The owner's deliberate step is creating store-guard.off, whose presence
turns the guard OFF; it is visible on every launch record and in status and restores the old path and the
old Codex settings. Codex's sandbox is
never switched off as an enforcement-failure fallback.

Mainline Landlock ABI 3 arrived in Linux 6.2, so a stock 5.15 or 6.1 kernel without backports is refused,
as is any host with Landlock disabled at build or boot or its syscalls blocked; the probe decides, not the
version string. Risky launches additionally need x86_64 and ABI 6 (mainline 6.12), as they do today. This
host reports ABI 8 on x86_64. A successful probe does not guarantee the later installation succeeds; that
case is the wrapper's enforce_failed.

## 12. Behavior changes for the owner, plainly

While the guard is on (none of these with store-guard.off present):

1. Agent runs cannot read or write anything in the store directory.
2. Default runs cannot mount. Bubblewrap, rootless podman or buildah, unshare with mounts, Codex's own
   sandbox and Claude Code's optional sandbox fail inside default runs.
3. Codex runs with its own sandbox off inside guarded runs, over any role setting.
4. Default runs cannot create, remove or rename entries directly in the store directory's ancestors
   (/var/lib/veldo, /var/lib, /var, /), nor read files created directly there after the run started.
5. Local launches are refused below Landlock ABI 3, or when Landlock is disabled, blocked or unsupported
   on the platform. Risky launches below ABI 6 or off x86_64 are now refused before acceptance instead of
   failing inside the runner.
6. Local launches are refused when the store directory holds a symlink, a special file other than the
   authority's own authority.sock, or a multiply linked file, when it or a file in it is mounted a second
   time, when the runs directory falls inside it, or when it sits beneath a location runs need (home,
   temporary, runtime, worktree, Git directory). Affected previously supported layouts: no `runs` and no
   `state_root`, and the conventional store in the Git directory.
7. A risky launch is refused when its runner's effective grants or copy sources reach the store
   directory. A broad read root that the runner's deny_read already excludes the store from is fine.
8. Plan run-check, frontier, the completion view and status inside a default run answer through the
   receiver; any default run can also ask other live receivers for their status answers, and the
   replication part of status is store-wide.
9. Launch lines show pending at acceptance and the record shows applied or enforce_failed afterwards; off
   and preflight refusals show at once. The status command shows the guard configuration for later
   launches.
10. The guard is ON by default; the presence of store-guard.off in the store directory turns it OFF, and
    deleting it turns the guard back ON. A present but invalid store-guard.off refuses launches until it
    is deleted (guard ON) or made a regular file (guard OFF).

Not changed: how the authority, setup, maintenance commands, the CLI, the API process or the signer open
the store; where the authority socket is and how it authenticates; anything a Veldo process does outside
a run.

## 13. Residuals

- Any process of the owner's account outside a Landlock domain can read and write the store, take the
  lock, create aliases, chmod or delete files, and create store-guard.off.
- A default run can ask an unconfined same-account process to act for it (systemd-run, a login shell's
  startup file, ssh to this host), including creating the marker; a risky run can use an authenticated TCP
  service. A descriptor voluntarily sent to a run later by an unconfined service is part of this residual.
- A default run can edit the installation's configuration in the home directory for later launches.
- A default run can chmod store entries (availability) and see their names, sizes and times; it can
  signal processes it already could; it can connect to the authority socket and is refused without a
  member signature.
- Aliases created by an unconfined process after the last preflight.
- Runs started while the switch was off.
- A query endpoint left in the runtime directory when both its receiver and its Runner died, until the
  runtime directory is cleared.

## 14. Runtime views

A default launch, guard on.
1. The Runner spawns the receiver, which opens the store as today.
2. The receiver samples the switch (absent), runs the preflight, creates the query endpoint and waits for
   its serving thread to be ready. A refusal ends here; nothing is spawned and the endpoint is removed.
3. It accepts (store_guard pending), sets Codex's sandbox off if the engine is Codex, and spawns the
   wrapper (close_fds; heartbeat and setup pipes only).
4. The wrapper parses its configuration, audits descriptors, then reports identity, waits for release,
   installs the ruleset, starts the heartbeat, writes the success byte and execs. The receiver records
   store_guard applied.
5. plan run-check: entry_gate sees VELDO_RUN_QUERY, says hello, checks the repository, asks decide, and
   delivers the returned events to its local observe.
6. The run ends; the receiver removes the endpoint (or the Runner does, if the receiver died).

A risky launch, guard on. As above through the preflight, plus the risky floor and the effective-grant
census; no query endpoint; the wrapper audits descriptors and execs the confined runner, which mounts,
confines itself and execs the engine. The record shows pending with precondition_checked, then
runner_started.

A launch, guard off. The receiver finds a valid store-guard.off, records store_guard off with its path,
and launches exactly as today.

## 15. Tests and falsifiers

Rules for every row: a store content check compares the protected logical state and the bytes of the
database file around a quiesced attack interval, accounting separately for the receiver's authorized
launch-record writes; an unexplained change fails the row. Each mutant is checked against a row whose
unmutated control passes on the same fixture, and each mutant must reach the operation the row asserts:
a mutant is bound to the exact behavior it changes, and a registered name is not evidence by itself. A
fixture facility that cannot be built (a mount, a kernel) records NOT RUN, which never satisfies a row.

| Row | Proves | Falsifier |
|-|-|-|
| launch/guard-default | Real contained default launches of each kind (engine run, conversation turn, workflow step), fixture engine and a descendant, separate trials with errno classes: open read and write of the database and its actual sidecars; open read-only with truncate; truncate; unlink; rename out and link out; create a file, a directory, a symlink and a socket inside; open authority.lock read-only; on authority.sock only name-protection trials: unlink, rename out and link out (socket creation in the directory is the create trial above); move or replace the store directory both ways; open through an outside symlink pointing in. An ordinary open of authority.sock is not a trial: opening a pathname Unix socket fails with ENXIO even unguarded, so it is no evidence for Landlock. Compatibility assertions in both modes, guarded and skipped: connect to the running authority socket and receive its unsigned-request refusal. Allowed: worktree, home and temporary writes. The ancestor refusal | store359-guard-skipped makes each listed content and name trial succeed (none of them fails unguarded); the connect and unsigned-refusal assertions hold in both modes |
| ruleset/primitive-symlink-out | A primitive control_clone ruleset test, outside the launch preflight by design: following a symlink inside the denied directory that points out reaches the target, because target resolution governs access. Not a production launch case; production refuses that layout in layout/aliases | none needed; documents the kernel semantics the entry check relies on |
| launch/guard-read | With no competing lock holder, a write-only ruleset lets the lock open read-only and flock; the real ruleset refuses the open | store359-write-only-guard |
| launch/enforce-fail | Probe, create, add and restrict failures injected separately by seccomp filters on the wrapper that match arguments: the create filter refuses landlock_create_ruleset only with flags 0 and a ruleset attribute, so the version query passes; the probe filter refuses only the version query. Each ends with store_guard enforce_failed naming that step, no heartbeat child, no model payload marker, no Codex | store359-guard-skipped passes the payload |
| launch/descriptors-early | At the real wrapper spawn: stdout and stderr each a writable store database handle, stdin a store file, the setup pipe replaced by a store handle. Each refused before any startup output or release read: fixture bytes unchanged even with stdout and stderr writable on the store, no release read from the forbidden stdin, no write to any forbidden stream, the failure reported on the setup pipe only when that pipe passed, otherwise a silent exit with the audit status. The final receiver launch record is asserted for each case, through the pre-identity handshake of section 5: enforce_failed with step audit when the setup pipe passed, enforce_failed with step audit, unreported when the setup pipe was the forbidden one, never the generic spawn_failed:containment:unavailable, no release and containment cleaned up. An ordinary log file on stderr outside the store launches | store359-fd-check-late (the audit after the identity line and release read): stdout's identity line lands in the fixture database, so its bytes change; store359-audit-late-reader-only (the receiver reads the failure byte only in the post-release reader): the record shows the generic containment error instead of the required guard outcome |
| launch/descriptors-leaked | At the real wrapper spawn, with clean standard streams and channels: an extra inherited descriptor (a writable sidecar, a read-only lock, the directory, a deleted store file) that the fixture payload actually uses; inspection failure of one descriptor and an unreadable enumeration refuse; a clean launch applies | store359-fd-check-skipped: the payload writes or reads through the extra handle |
| launch/ack | The event sequence shows pending at acceptance and applied only after the success byte; with restrict injected to fail, no applied event ever appears, even though enforce_failed does | store359-ack-early (an applied event before the success byte is caught in the sequence) |
| launch/receiver-memory | From the guarded payload: receiver /proc/PID/fd and /proc/PID/mem, process_vm_readv and writev, pidfd_getfd where supported, all denied; an unguarded control on the same host succeeds, or the row records the other denying layer (Yama, seccomp) and is not counted as guard evidence | store359-guard-skipped succeeds |
| launch/abi | Refused before acceptance, no worker, each reason by name, for default and risky kinds: ENOSYS, EPERM and EOPNOTSUPP from real seccomp filters on the receiver, ABI 1 and 2 by probe parameter, unsupported platform by parameter. Risky only: ABI 3, 4 and 5 by probe parameter refused as landlock_abi_below_6 before acceptance, and a non-x86_64 platform parameter refused as platform; these test the receiver's own check, which is the claim. Accepted: ABI 3 and the host's ABI for default; the host's ABI for risky. The probe parameter reaches only the receiver's criterion; the wrapper probes the real kernel again, and the risky runner keeps its own floor (control_clone.confine refuses below ABI 3, control_clone.py:300 to 302; agent_sandbox.py:68 to 71), so removing the preflight check does not defeat the later kernel qualification | store359-low-abi-accepted: a default launch at parameter ABI 2 is accepted, which is the distinguishing failure of the receiver criterion (the wrapper then sees the host's real ABI); on an actual ABI-2 host the same mutant is accepted and then ends enforce_failed with no payload. store359-risky-floor-skipped: a risky ABI-5 parameter launch is accepted |
| layout/entries | Accepted: a normal running factory layout with an actually bound authority.sock, the authority serving, and an ordinary default receiver launch completing while it serves; the same with a stale authority.sock left by a stopped authority. Refused by name: an unexpected socket elsewhere beneath and one under another name in the store directory, a FIFO, a device where the fixture can make one, a symlink, a symlinked sidecar of a custom database name, a hard-linked file anywhere beneath; hard links to the database, a sidecar and the lock | store359-socket-exception-removed fails the normal running factory launch; store359-special-entries-allowed accepts the unexpected socket and the FIFO; store359-links-allowed accepts the hard links |
| layout/mounts | Refused: a bind of the directory, of an ancestor and single-file binds of the database and the lock, in the actual enforcement namespace; unreadable mountinfo. Accepted: a symlinked path to the store directory (the ruleset still denies through it) | store359-file-binds-allowed |
| layout/placement | Refused: no runs and no state_root (actual fallback); a worktree under the store directory; a store under the worktree, the Git common directory (conventional layout), home, temporary and runtime directories; equality cases; an external client state place overlapping the store; a risky worktree or scratch parent that is an ancestor of the store. Accepted: a normal factory layout; an explicit `runs` outside the store with no state_root; the same layout with an absent optional tool root. With the marker, the fallback launches today's way with its old path | store359-placement-skipped: the fallback launch is accepted and then fails reading its engine configuration |
| launch/risky-real | A real risky launch with the shipped configuration reaches its payload and completes; the payload is refused the store and the lock | store359-guard-before-runner breaks this successful launch before the payload |
| launch/risky-census | Exposure fixtures, end to end, on otherwise valid grant or copy fixtures that pass every placement check (disjoint layouts), refused before acceptance with nothing spawned: a read root containing the state root without an exclusion; a client read_link resolving into the store; a configuration file inside it; a general seed, a client seed and a credential source resolving to store files. For each, a companion run shows the unchanged runner, given the same configuration without the census, actually grants or copies that route. Early-refusal timing fixture: an unresolvable required root is refused before acceptance with nothing spawned. Accepted: an absent optional root; a broad read root with deny_read on the store directory; an unused client place; a client place whose selected sources are all disjoint from the store. Component census tests (no launch) cover the routes placement already refuses end to end: worktree and scratch-parent ancestors, Git common directory, client state place overlap. Parity of set (b) only, scratch symbolic: on every fixture on which the runner's grant preparation succeeds, including the shipped Claude and Codex configurations, the credential exclusions, an absent state home and newly created state entries, the census's normalized actual grants equal the grants the runner emits. Grant-set parity applies only to fixtures on which the runner's grant preparation succeeds. For the unresolvable required-root fixture the expected outcome is the named pre-acceptance census refusal and, with only the census skipped, acceptance followed by runner failure and no payload. For any component fixture whose unchanged runner qualification refuses, the expected refusal outcome is compared instead of a returned grant set. | store359-precondition-skipped: for each exposure fixture the payload reads a planted sentinel through that route, or the seed copy exposes it; for the unresolvable root the mutant's launch is accepted and then fails in the runner with no payload (timing, not exposure). store359-census-prefilter (configured roots compared instead of actual grants) refuses the accepted deny_read control. store359-census-places-as-grants (client places treated as grants) refuses the accepted unused-place or disjoint-place control or fails parity |
| launch/engines | Pinned Codex through the production wrapper with a workspace-write role runs a real shell command and a child: worktree write succeeds, store opens refused with errno, effective setting recorded; again through a real risky launch; enforcement failure starts no Codex; with the marker the role's setting stands. Pinned Claude Code runs its Bash tool and an ordinary build step under the ruleset. Heartbeat deadline met | store359-role-sandbox-wins: the shell command fails to start; store359-guard-skipped on a disposable store: the command writes it |
| query/journey | Under the real ruleset: run-check, bundle and hash to the build; frontier claimable and withheld with offers, observations and handoff records; plan references; executor context, tickets and a stale ticket; work_state.completion_view called explicitly with the remote gate; a valid coordination decision on the launch repository's pm_cycle, a stale coordination ticket, and a missing cycle answered missing_authority:pm_cycle; a missing dependency held, not crashed; local observe callbacks (station decision, decision_dependency, invalid_record) equal to a direct Gate's in order; status in both modes (default replica, and the override at the receiver's store). Stable semantic fields equal a direct Gate's at the same state (decision ids and clock fields normalized). Zero direct store opens attempted by the client, also on timeout and transport failure. Fresh answers after a committed store change | Unset VELDO_RUN_QUERY: the journey stops unavailable_service:store; store359-events-dropped: the callback comparison fails |
| query/scope | coordinate_not_served for another repository's execution unit, a member id as unit, a foreign reference, a pm_cycle of another repository, an execution unit passed to coordination, an unlisted request; run_query:other_repository from another checkout; schema tests: every response holds exactly its frozen fields, including all approved metadata, no planted sentinel; two concurrent runs in different repositories each get their own answers; a dead receiver gives unavailable_service:run_query | store359-query-any-unit: a foreign unit's projected identity appears in an answer; store359-query-fallback attempts a direct open, even if caught |
| query/lifecycle | Endpoint made and ready before acceptance and removed on refusal; removed at run end, after a killed engine (by the receiver) and after a killed receiver (by the Runner, within its deadline). Concurrent startup: receiver A paused between bind and listen while receiver B starts; A's endpoint survives and answers after release. A leftover endpoint of a dead receiver and Runner does not affect a later launch | store359-query-leak (no removal at run end); store359-query-startup-sweep (a connection-refused sweep at receiver start) removes A's endpoint |
| switch/off | Valid marker on a valid layout: no ruleset (fixture opens the store), no query variable, role's Codex setting, store_guard off with the path on the record, status shows OFF. Valid marker on a fixture with ABI forced to 2 and an extra hard link: launches as today. Marker removed on that defective fixture: refused by name. Marker removed on a valid fixture: guarded. Symlink, directory and foreign-owner markers: refused by name, never off. A mode or content change of a valid marker changes nothing | store359-switch-ignored |
| switch/run-cannot-flip | Inside a guarded run: create the marker, link and rename a file to its name, rename or replace the store directory and its parent: all refused; the next launch is guarded. Inside a risky run: same | store359-switch-outside: the switch is read from a run-writable location, the guarded payload changes it there, and the next launch is unguarded |
| switch/transitions | Off to on with one surviving unguarded run and one surviving guarded run: after deletion, status shows on, the next launch is guarded, the surviving unguarded run still reaches the fixture store (stated residual), the guarded one still cannot; on to off: the surviving guarded run stays guarded | none; it keeps the status and time claims honest |

## 16. Footprint and protected paths

Product code, both trees (.veldo and engine/.veldo): control_launch (switch sample, preflight, risky
floor, census, wrapper audit and ruleset, failure byte and step, query endpoint, records), control_clone
(a structured probe beside abi; abi unchanged), control_run_query (new: server and remote gate),
control_eligibility (entry_gate), frontier (floor entry behind the gate), runstatus (override handling,
store guard line), control_agent_config_handoff (Codex override), init_scaffold (module list).

Tests: a new suite, the suite manifest and requires files, check_teeth_mutations.py, and suites whose
fixtures assert the launch record's shape.

Records: the spec, specs/index.md, proof/VELDO-0359.

Protected paths: one, scripts/gate_unconfined.json, because the real-launch rows need the systemd user
manager and the installed namespace helper. Untouched: scripts/agent_sandbox.py and .json (both trees),
scripts/verify.sh, scripts/gate_graph.json, .veldo/policy.yaml, control_store, control_service,
control_client, control_signer, control_factory_setup and every module revision 2 changed for the write
capability.

## 17. Dependencies and amendments

Depends on VELDO-0039, VELDO-0040, VELDO-0041 (receiver, wrapper, setup status byte), VELDO-0042
(Landlock primitives), VELDO-0052 (entry_gate), VELDO-0208 (confined runner), VELDO-0254 (default runner
contract and launch scan) and VELDO-0127 (pinned engines).

Amends VELDO-0254 AC3: while the guard is on, default runs lose access to the store directory, direct
entries in its ancestors and the ability to mount; local launches are refused below Landlock ABI 3, on an
aliased or misplaced store layout and on a runs directory inside the store directory; a risky launch is
refused below the runner's own floor, or when its runner's effective grants or copy sources reach the
store directory; Codex's own sandbox is off inside guarded runs. Risk high, human approval required.
