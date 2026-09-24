# VELDO-0042 proof

Isolated worker clones at the accepted commit, one read-only pinned object cache per repository with
only contract-named attachments, a worker's direct writes confined to its own clone, and pin release
only after the clone's workers and consumers end. `.veldo/control_clone.py` is the provisioner (engine
copy byte-identical), installed by `.veldo/init_scaffold.py` beside `.veldo/env_provision.py` whose
lifecycle base it builds on. Specification status and risk are unchanged; this proof is for independent
review, not a self-approval, and the canonical gate is run by the lead.

Everything is real: a real SQLite authority with OpenSSH journal signatures, four real Git
repositories (a source whose HEAD is a commit past the accepted one, an attachment the contract names,
an unnamed repository it does not, and their per-repository caches), real `git init`/`fetch`/
`checkout`/`gc`, and real worker and consumer processes started through the clone adapter and confined
with Linux Landlock (ABI 8 on this host; the module requires ABI 3). No systemd: a clone user's ending
is read from the kernel through `control_containment.retirement` over each process's own OS identity,
the same observation the VELDO-0040 receiver's group reports through, so the retained Release 1
function is exercised without the containment machinery.

## What was built

- `.veldo/control_clone.py`: `Clones` (an `env_provision.EnvProvisioner`). `create` provisions one clone
  per dispatch at the contract's accepted commit and tree (never the source repository's HEAD), over a
  new repository whose object store borrows, through Git alternates, one bare cache per repository. Each
  repository the contract names (its own and each `input.payload.attachments` entry, exact commit,
  bound in the store) is fetched into its cache under this clone's own pin ref
  `refs/veldo/pins/<clone>/<repository>`, so a clone that pins two repositories never collides on one
  ref. Attachments appear as `refs/attachments/<name>`, read-only. `enter` is the adapter argv prefix: a
  worker finds its clone, confines its writes with Landlock to its work tree and scratch (a consumer to
  its scratch only), and becomes the engine in the clone with the repository-selecting Git variables
  removed. `teardown` releases a clone's pins only once every worker and consumer has ended (its record
  conclusive AND the kernel says the process is gone), else refuses `clone_in_use`.
- `.veldo/env_provision.py`: `EnvProvisioner.create` now passes backend arguments through, so a clone
  backend takes the dispatch contract; the fake and container backends are unchanged.
- Both, and `control_clone.py`, are in `init_scaffold._FILES`; engine copies are byte-identical.

## Rows, falsifiers and red record

Suite `scripts/suites/66_veldo_0042_clones.py`, 0.45 s (12 assertion rows plus 6 region-completion
rows). `python3 -B proof/VELDO-0042/drive.py` regenerates `mutations.json` and the 12 diffs: every named
row is red by its own assertion with its region completing, the baseline and an unmutated copy of each
mutated module are green, and every row has its declared falsifier first and a second, different
mutation. Registry: `scripts/check_teeth_mutations.py --finding 42` (footprint History line added).

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `clone/accepted-commit` | AC1 | `clone-provision-from-head`, `clone-verify-wrong-accepted-field` |
| `clone/worker-writes-confined` | AC1 | `clone-confinement-not-restricted`, `clone-grants-everything` |
| `clone/named-attachment-and-unnamed` | AC2 | `clone-pooled-cache`, `clone-attachment-ref-wrong-commit` |
| `clone/pins-survive-gc` | AC2 | `clone-pin-not-held`, `clone-pin-not-created` |
| `clone/retire-after-users-end` | AC3 | `clone-release-while-child-reads`, `clone-user-ended-ignores-kernel` |
| `clone/installed-assets` | install | `clone-module-not-scaffolded`, `clone-env-provision-not-scaffolded` |

`clone-provision-from-head` provisions from the source repository's current HEAD; the accepted-source
tree comparison then refuses, so no clone stands at the accepted commit (AC1's declared falsifier).
`clone-pooled-cache` makes one cache serve every repository, so a clone's alternate exposes the objects
of an unnamed repository another clone fetched into the shared cache (AC2's declared falsifier).
`clone-pin-not-held` fetches no durable pin ref and turns off the missing-pin guard, so ordinary `git
gc --prune=now` of the cache prunes the objects a running clone still reads. `clone-release-while-child-
reads` releases a clone's pins while a real child still reads it (AC3's declared falsifier). Each
mutation's second entry is a different defect of the same row; the drive also confirms no region raised
under any mutation, so every red is by assertion.

**Red at 18ecd6f.** `python3 -B proof/VELDO-0042/drive.py --red 18ecd6f` runs the current suite once
against that tree, extracted read-only with `git archive`: `red-at-18ecd6f.json`. At 18ecd6f the
isolated-clone provisioner did not exist, so the suite's `control_clone` anchor points at
`proof/VELDO-0042/prefix/control_clone.py`, a stand-in that refuses every provision and contains
nothing else; every other module is the commit's own, byte-identical, and the commit's `init_scaffold`
installs neither asset. All six rows are red by their own assertions (the capability is absent), none
raising.

## Costs

Suite 0.45 s (measured through `scripts/selftest.py --suite`). Finding 42 with `--jobs 4`: about
1.6 s. The drive (baseline, three no-op copies, 12 mutants, serial) is about 7 s. The red run is about
1 s. Committed proof is under 1 MB, no full gate logs.

## Out of review scope (filed, not blocking)

Per the spec's threat model: a worker that deliberately leaves its containment group, or writes through
the owner's own unconfined processes (the user service manager, shell startup files, ssh to this host),
which only a separate operating-system account closes (Release 2, Telegram 28578/28580); interrupted
provisioning or retirement, and recovery from concurrent garbage collection (Release 2). The wrapper is
Linux only; the Mac's worker profile is VELDO-0124. Wiring the production adapters' argv to the clone
adapter is VELDO-0129, and the clone and cache roots' installed placement is installation.
