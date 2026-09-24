# VELDO-0042 proof

Isolated worker clones at the accepted commit, one read-only pinned object cache per repository with
only contract-named attachments, a confined worker that cannot directly write another clone, the store,
the keys, the authority's Git metadata or a cache, nor read an unnamed repository's cache or the keys,
while it keeps every other capability it has today, and pin release only after the clone's workers,
consumers and their containment groups have ended. `.veldo/control_clone.py` is the provisioner (engine
copy byte-identical), installed by `.veldo/init_scaffold.py` beside `.veldo/env_provision.py` whose
lifecycle base it builds on. Specification status and risk are unchanged; this proof is for independent
review, not a self-approval, and the canonical gate is run by the lead.

Everything is real: a real SQLite authority with OpenSSH journal signatures, four real Git repositories
(a source whose HEAD is a commit past the accepted one, an attachment the contract names, an unnamed
repository it does not, and their per-repository caches), real `git init`/`fetch`/`checkout`/`gc`, real
worker and consumer processes started through the clone adapter and confined with Linux Landlock (ABI 8
on this host; the module requires ABI 3), the installed `claude` (2.1.281) and `codex` (0.154.0) CLIs,
and real VELDO-0040 containment scopes (`control_containment.Group`) under the owner's systemd user
manager, in a slice named for the run and stopped at its end.

## What was built

- `.veldo/control_clone.py`: `Clones` (an `env_provision.EnvProvisioner`). `create` provisions one clone
  per dispatch at the contract's accepted commit and tree (never the source repository's HEAD), over a
  new repository whose object store borrows, through Git alternates, one bare cache per repository. Each
  repository the contract names (its own and each `input.payload.attachments` entry, exact commit, bound
  in the store) is fetched into its cache under this clone's own pin ref
  `refs/veldo/pins/<clone>/<repository>`. Attachments appear as `refs/attachments/<name>`, read-only. The
  clone's manifest records its protected targets and what they cost (below). `enter` is the adapter argv
  prefix: a worker finds its clone, records its entrance (process identity and cgroup) in the clone root,
  confines itself, and becomes the engine in the clone with the repository-selecting Git variables
  removed. `teardown` releases a clone's pins only once every worker and consumer has ended, else refuses
  `clone_in_use`.
- `.veldo/env_provision.py`: `EnvProvisioner.create` passes backend arguments through, so a clone backend
  takes the dispatch contract; the fake and container backends are unchanged.
- All three are in `init_scaffold._FILES`; engine copies are byte-identical.

## The confinement: denied targets, everything else granted

The review refused the first confinement because it was an allow list: a worker could write only its
work tree and scratch, so Codex exited at start ("failed to initialize in-process app-server client:
Permission denied", reproduced in `red-at-2f643d0.json`'s run), `/dev/shm`, `/tmp`, `/var/tmp`, `~/.cache`
and the home directory were refused, and Claude Code could not save its state. It is now a deny list, the
way `control_keys_custody.py` (VELDO-0067) denies reads.

**Denied writes** (create, write, truncate, remove, rename, link) beneath exactly: the clone root (every
clone, including this clone's own manifest and entrance records), the cache root (every cache), the
store's directory, the configured protected directories (the keys), and the Git metadata of every
repository the store binds (git directory, common directory and `.git` entry). A worker's own work tree
and scratch directory are granted back beneath the clone root; a consumer's scratch directory only, so a
consumer writes none of the clone.

**Denied reads** of file content beneath the cache root and the keys, with the caches of the repositories
this clone names granted back. An unnamed repository's cache stays unreadable even when a worker appends
it to its own alternates (the filed finding), because the kernel refuses the object files themselves.

**Everything else is granted as before**: the home directory's existing entries (`~/.claude`,
`~/.claude.json`, `~/.codex`, `~/.cache`, `~/.config`, `~/.local`), `/tmp`, `/var/tmp`, `/dev/shm`, the
worker's TMPDIR, the devices, and every other repository's work tree. Listing and executing are never
handled.

**How, and what the method still denies.** Landlock grants by hierarchy and cannot deny one path, so each
denial is built from its targets' ancestor chains: every entry beside a chain, at every level, is granted
as a whole hierarchy (an existing file beside it is granted its content rights), and nothing on a chain
is. That leaves these everyday operations denied, stated plainly:

1. Creating, removing, renaming or linking an entry directly in a directory on the write chain, that is,
   an ancestor of a protected target that this account can write. Each manifest names them
   (`ancestors.write`). In production's layout they are the home directory, the directory holding the
   bound repositories (`~/projects`), each bound repository's top-level directory, and Veldo's own state
   directory; an existing file in any of them stays writable in place. The home directory is on the chain
   because the authority's Git metadata lives in the owner's checkouts under it; nothing else puts it
   there.
2. A file created directly in one of those directories after the worker started is not writable by it,
   and moving a file into or out of one directly needs a copy.
3. On the read chain (`ancestors.read`, in production only Veldo's state directory), a file created
   directly there after the worker started is not readable by it.
4. Gaining privilege through a setuid program (`sudo`, `su`): Landlock requires no_new_privs.

**Measured with the real engines** (`engine-denials.json`, `drive.py --engines`: each CLI confined through
the clone adapter in production's layout under `strace`): Claude Code 2.1.281 saves `~/.claude.json` by
creating `~/.claude.json.tmp.<pid>.<hex>` and renaming it over the file, under a `~/.claude.json.lock`
directory, and both are refused (9 creates and 10 lock attempts in one run). It then rewrites
`~/.claude.json` in place, so its settings are saved, but without its lock and not atomically: two Claude
workers saving at the same moment can lose one update. Codex 0.154.0 is refused nothing: all of its state
is under `~/.codex`. A write-and-rename of a file directly in the home directory (a Python probe standing
for any tool that saves there that way) is refused. On a first run an engine could not create
`~/.claude.json` or `~/.codex` if absent; a logged-in owner's home holds them, as the suite's temporary
HOME does.

**Layout.** No protected target may be beneath a temporary directory (`/tmp`, `/var/tmp`, `/dev/shm`, the
provisioner's TMPDIR): the constructor and each provision refuse `invalid_input:layout`, because that
chain would deny every engine the files it creates there. The clone root, cache root, store and keys
belong in one directory of Veldo's own whose ancestors the owner's account cannot write anyway (for
example `/var/lib/veldo`, made once by the installation), so that chain costs nothing beyond Veldo's own
directory. Under the home directory instead (for example `~/.local/state/veldo`), `~/.local` and
`~/.local/state` join the write chain. Choosing the installed location is installation.

## Rows, falsifiers and red records

Suite `scripts/suites/66_veldo_0042_clones.py`: 10 assertion rows and 10 region-completion rows (20 in
all), about 1.5 s. `python3 -B proof/VELDO-0042/drive.py` regenerates `mutations.json` and the 21 diffs:
every named row is red by its own assertion with every region completing, the baseline and an unmutated
copy of each mutated module are green, and every row has two or more mutations, the declared falsifier
first where the criterion declares one. Registry: `scripts/check_teeth_mutations.py --finding 42`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `clone/accepted-commit` | AC1 | `clone-provision-from-head`, `clone-verify-wrong-accepted-field` |
| `clone/worker-writes-confined` | AC1 | `clone-confinement-not-restricted`, `clone-grants-everything` |
| `clone/protected-targets-denied` | AC1, AC2 | `clone-reads-not-denied`, `clone-cache-root-readable`, `clone-own-root-writable` |
| `clone/real-engines-run-confined` | AC1 | `clone-confinement-allow-list`, `clone-chain-walked-one-level` |
| `clone/consumer-confined` | AC1 | `clone-consumer-granted-work-tree`, `clone-consumer-allow-list` |
| `clone/named-attachment-and-unnamed` | AC2 | `clone-pooled-cache`, `clone-attachment-ref-wrong-commit` |
| `clone/pins-survive-gc` | AC2 | `clone-pin-not-held`, `clone-pin-not-created` |
| `clone/retire-after-users-end` | AC3 | `clone-release-while-child-reads`, `clone-user-ended-ignores-kernel` |
| `clone/retire-waits-for-group` | AC3 | `clone-group-emptiness-ignored`, `clone-unknown-group-ended` |
| `clone/installed-assets` | install | `clone-module-not-scaffolded`, `clone-env-provision-not-scaffolded` |

What each row runs. `worker-writes-confined`: clone A's worker writes clone B's work tree, the store file
and directory, the key directory, its own repository's real cache, the source repository's real
`.git/HEAD`, and runs `git update-ref` into the source `.git`; every one is refused and nothing lands.
`protected-targets-denied`: the complete protected set, enumerated by the suite and not read back from
the provisioner (clone B's manifest, its own manifest, entrance records and clone root, the clone and
cache roots, the store, the key file and directory, every bound repository's `.git`, a named and an
unnamed cache), is refused for writing; an unnamed cache's object file and the key file are refused for
reading, directly and through the worker's own alternates, while the named attachment still reads.
`real-engines-run-confined`: `claude -p` and `codex exec`, each confined through `Clones.adapter` in its
own containment scope with the temporary HOME (its state layout present, and on the write chain as in
production), every proxy variable pointed at a local listener that records each request line and answers
nothing, must reach their network step (a CONNECT to the listener, never a provider) and write their
state directory (`~/.claude/...`, `~/.codex/sessions/...`) with no Permission denied at initialization;
a probe then takes a `multiprocessing` lock on `/dev/shm` and makes new files in TMPDIR, `/tmp`,
`/var/tmp` and `~/.cache`. A CLI that is not installed fails the row by name with its install hint.
`consumer-confined`: a consumer whose directory is the work tree is refused every write to the clone
(a new file, a tracked file, `.git`) and to the store and keys, and reading the keys, while its scratch,
`/dev/shm`, `/tmp` and `~/.cache` stay writable and it reads the clone. `named-attachment-and-unnamed`:
the attachment's real cache is refused for writing (objects and refs), asserted. `retire-after-users-end`:
a worker and a consumer alive in their own scopes, each recorded with `record_group`, keep the clone
(`clone_in_use`, pins held, objects readable); once both end and their groups report empty it retires
and releases every pin. `retire-waits-for-group`: the real VELDO-0040 group path, where the worker's own
process exits and is recorded exited while a child it started keeps reading the clone inside its group;
teardown refuses while the group is populated and retires once the kernel reports it empty (about 0.1 s
after the child's release on this host); and a worker entered on this host whose group was never
recorded is refused `clone_in_use` after it exits, because nothing can say its descendants are gone.

**Red at 2f643d0** (`red-at-2f643d0.json`, `drive.py --red 2f643d0`): the current suite against that
tree, every module the commit's own. Exactly the four new rows are red, by assertion:
`protected-targets-denied` (the unnamed cache and the key file read), `real-engines-run-confined` (Codex
exits at start with the Permission denied the review saw, Claude writes no state, `/dev/shm`, `/tmp`,
`/var/tmp` and `~/.cache` are refused), `consumer-confined` (the keys read, the everyday locations
refused) and `retire-waits-for-group` (the clone whose group was never recorded is retired).
**Red at 18ecd6f** (`red-at-18ecd6f.json`): before the provisioner existed, with
`proof/VELDO-0042/prefix/control_clone.py` standing in (it refuses every provision); all ten rows red by
assertion, none raising.

`observations.json` (`drive.py --observe`) keeps one full run's observations: what the kernel allowed
each probe, each engine's requests and state files, the groups, and the chain cost each manifest records.

## Costs

Suite about 1.5 s (1.49 to 1.56 s over three runs through `scripts/selftest.py --suite`). Finding 42 with
`--jobs 4`: about 8 s. The drive (baseline, three no-op copies, 21 mutants, serial) is about 32 s. Each
red run is about 2 s, the engine measurement about 3 s. Committed proof is under 1 MB, no full gate logs.

## Out of review scope (filed, not blocking)

Per the spec's threat model: a worker that deliberately leaves its containment group, or writes through
the owner's own unconfined processes (the user service manager, shell startup files, ssh to this host),
which only a separate operating-system account closes (Release 2, Telegram 28578/28580); interrupted
provisioning or retirement, and recovery from concurrent garbage collection (Release 2). A worker still
reads the owner's other repositories' checkouts directly, as it does today: only Veldo's own caches are
denied, which closes the exposure Veldo creates. The wrapper is Linux only; the Mac's worker profile is
VELDO-0124. Wiring the production adapters' argv to the clone adapter is VELDO-0129, and the clone and
cache roots' installed placement is installation.
