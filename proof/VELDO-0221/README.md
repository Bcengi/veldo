# VELDO-0221 proof: a gate leg runs its suites as isolated parallel closure shards

Built on branch veldo-0221 from main at 23318512. This file says what was built, what each
criterion's evidence is, and every place where the build had to decide something the specification
does not spell out. The decisions are listed first because a reviewer should judge them, not find
them.

## What was built

- `scripts/run_scope.py`: the shard machinery. `run_shards` runs one fresh interpreter per suite of
  a leg (`selftest.py --suite NAME --shard FD --shard-root DIR`), gives each its own HOME, TMPDIR,
  XDG configuration, data, cache, state and runtime directories, reads each shard's result from a
  pipe, admits shards by the manifest's declared resources and by the gate ledger, and runs the
  isolation check. `leg_suites` is the one place a leg's suite set is computed.
- `scripts/selftest.py`: in a gate leg the dispatcher runs `run_shards` and composes the aggregate
  line from the target suites' counts; a bare run and a selector keep the ordered run. The shard
  side reports a Landlock layer record (confined leg), a target mark and a verdict.
- `scripts/agent_sandbox.py` (and the engine copy): `write_layer`, the stacked Landlock layer a
  confined shard applies to itself, and `--inherit`, by which the gate profile's command keeps the
  leg runner's two descriptors.
- `scripts/gate_legs.py` (and the engine copy): `ShardClaims`, the leg's side of the gate ledger;
  the per-suite shard measurements in the leg-time store; the three variables a leg is handed.
- `scripts/check_first_use.py`: hands the leg's descriptors to its nested dispatcher.
- `.veldo/control_containment.py`, `.veldo/control_client.py`, `.veldo/control_service.py`,
  `.veldo/control_factory_setup.py` (and the engine copies): the instance name.
- `scripts/mutation_ownership.py` (and the engine copy): the authority unit pattern accepts a name
  with an instance.
- `scripts/suites/157_veldo_0221_suite_shards.py`, the manifest and the closure table.
- `scripts/check_teeth_mutations.py`: the four registered falsifiers, in their own block.

## Decisions a reviewer should judge

1. **The isolation check attributes; it does not treat every new item as the leg's.** The
   specification says the unconfined leg records the shared locations before and after and requires
   nothing to be left behind. Measured on the qualification host on 2026-11-21 over 260 seconds,
   with this branch idle: other sessions made 20 entries at the top of /tmp, one /dev/shm entry and
   two units (a slice and a dispatch scope). The gate's own launchers and mutation workers also make
   entries at the top of /tmp while a leg runs. A literal before-and-after would turn nearly every
   gate red for something no suite of the leg did. The kernel records no creator for a file, so the
   rule built is: a new item is the leg's when its name carries a suite's instance name, when it
   refers to a shard's roots (a link's target, a small file's text, a unit's properties), or when a
   live process carrying a shard's roots in its environment holds it; an item another account owns
   or a live process of another tree holds is foreign. For what is left, the systemd configuration
   directory, the real runtime directory, /dev/shm, the two owner directories and the manager's
   units are `strict`: the dispatcher waits for the item to go (300 seconds, a hang detector) and
   what stays is a breach charged to the suites that were running when it first appeared. The top
   of the system temporary directory is `attributed`: an entry nothing ties to a shard is printed
   by name on the leg's summary and not charged. That last rule is weaker than the specification's
   sentence, and it is the one deviation from AC3's text. The three cases AC3's Set names are all
   red under it.
2. **The instance name extends the engine's fixed prefix; it does not precede it.** The names are
   `veldo-authority-<instance>-<service id>.service`, `veldo-api-<instance>-<service id>.service`,
   `veldo-dispatch-<instance>-<hash>.scope` and `veldo-workers-<instance>.slice`. Suites 85 and 117
   compute the API unit as `'veldo-api-' + unit[len('veldo-authority-'):]`, and the suites are out
   of scope, so a name placed before the fixed prefix would have made their arithmetic cut the
   wrong characters. Every name still carries its shard's name, which is what the isolation check
   reads. With no instance configured every name is today's, byte for byte.
3. **Where the instance name is read.** `control_client.py` must read no environment variable
   (VELDO-0107, row ipc/the-socket-follows-the-binding), so the rule lives once in
   `control_containment.instance_name` and the client asks it. An installed engine reads
   `config/instance.json` beside its `bin`, which `install()` writes when the installer has an
   instance (the service runs under the user manager's environment, which names no shard). An
   engine that is not installed reads `veldo/instance.json` in the user's configuration directory,
   which the dispatcher writes into each shard's private XDG_CONFIG_HOME. The two unit templates and
   `control_factory_setup_api.py` needed no change: the API unit's name is composed in
   `control_factory_setup.py` from what follows the fixed prefix.
4. **The gate ledger's channel stays with the leg runner.** VELDO-0216's row
   concurrent-stages/ordered-logs requires that no stage command sees VELDO_GATE_LEDGER_FD. So
   `gate_legs.py` asks the ledger on the dispatcher's behalf over a channel of the leg's own
   (VELDO_GATE_SHARD_LEDGER_FD), and the claim it forwards is the authority's own measurement for
   the suite, never a size the candidate names.
5. **The manager is admitted inside the leg, not claimed per shard on the ledger.** The unconfined
   legs' nodes hold the manager exclusively in `scripts/gate_graph.json`, which is outside this
   footprint, so a shard's manager claim on the ledger could never be granted. The dispatcher
   applies the manifest's declarations itself (exclusive runs beside no other user, a waiting
   exclusive suite bars later users), and that is what row suite-shards/manager-exclusive drives.
6. **A tree that cannot be cut into shards keeps the ordered run and says so.** A leg of a tree
   with no closure table, and the confined leg of a tree with no launcher module to take the
   Landlock layer from, run the ordered single-namespace run. Existing suites drive fixture
   candidates of exactly those two shapes through the real leg runner (101, 111, 14).
7. **The Landlock layer lives in `agent_sandbox.py`.** VELDO-0208's row
   profiles/one-network-rule-everywhere allows a Landlock or seccomp rule in that module only.
8. **Shard roots are short sibling directories.** A suite binds local sockets beneath its temporary
   directory and a socket path holds under 108 bytes. A directory level per shard and one per root
   put suite 24's path 3 bytes over; the layout built adds 13 bytes to the leg's own temporary
   directory and leaves that path 2 bytes to spare.

## Two edits outside the declared footprint

Both were forced by a gate check, and both are named here so that nobody finds them in the diff:

- `scripts/check_space_boundary.py`: two entries for `('scripts/run_scope.py', 'run_shards')`, in
  the existing class "Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that
  tree". Without them the gate's `extra` check is red, because the leg's shard roots are a
  temporary directory the dispatcher creates.
- `proof/WARP-0716/crossing-state.md`: regenerated with `scripts/suite_survey.py --emit-report`.
  It carries the digest of `scripts/selftest.py`, and `scripts/check_generated.sh` is red when it
  is stale. Earlier dispatcher changes regenerated it the same way.

## What is not proven here

See `open.md`.
