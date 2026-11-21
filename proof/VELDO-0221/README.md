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
  confined shard applies to itself; `--inherit`, by which the gate profile's command keeps the
  leg runner's two descriptors; and the broker's hold of a shard's `bind` to the shard's roots.
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
8. **A confined shard's temporary directory is no longer than the leg's.** A suite binds local
   sockets beneath its temporary directory and a socket path holds under 108 bytes. Measured in the
   confined leg: with 18 bytes added suite 24's path was 3 over, and with 13 added suites 156 and
   113 failed too. So in the gate's confined leg, whose temporary directory is `tmp` in the
   launcher's scratch, a shard's temporary directory is a three-character sibling of it. Those
   directories are not removed by the dispatcher; the launcher removes its scratch at the leg's end.
9. **No unconfined suite of this repository gets an instance name yet.** AC2 says each shard's
   fixtures set the engine's prefix to the shard's name. Measured against the real user manager,
   suites 66, 85 and 117 fail when an instance is configured in their shard: their own fixtures
   hand their subprocesses a configuration root of their own, so the installer and the tool it
   starts disagree on the unit's name, and suite 66 pins the installation's exact file set. The
   suites are outside this ticket. So the dispatcher sets the name in every shard of a confined
   leg, and in an unconfined leg only for a suite whose manifest entry declares `"instance": true`;
   none does. The unconfined leg's units keep today's names and stay apart on the one manager as
   they do in the mutation stage: by each installation's own service id and by the manifest's
   manager declarations. The engine capability, the dispatcher's side and the mutation ownership
   pattern are built and driven by rows; turning it on for a suite is one manifest key once that
   suite's fixtures carry the name.
10. **A shard's runtime directory links three things, not two.** The manager's two sockets, as the
   specification says, and the manager's runtime unit directory (`systemd/user`): suite 66 writes
   its unit files there through XDG_RUNTIME_DIR, and with no link the one manager never found its
   service. That directory is read strictly by the isolation check.
11. **One shard runs without a Landlock layer of its own.** `run_scope.UNLAYERED` names
   `151_veldo_0313_space_run`: its rows judge what every process of the leg's tree holds, and a
   process in a Landlock domain of its own is refused the dispatcher's and every other shard's, so
   the run it tests never ends (15 rows failed). In the leg's own domain it reads them, as in the
   ordered run. The table is in the protected dispatcher module, every leg prints what it exempted
   and why, and a row pins the table to this one entry. AC2 and AC3 say every shard; this is one
   short of that and needs the owner's decision.
12. **The broker holds a shard's bind to the shard's roots.** Suite 101's row
   confined-stage/unit-bind-outside-scratch-refused binds beside its HOME and requires a refusal;
   in a shard that path is inside the leg's scratch, which the broker serves. The broker now finds
   the caller's shard by ancestry and narrows the bind to that shard's roots (`open.md` item 6 says
   what this does not cover).

## Two edits outside the declared footprint

Both were forced by a gate check, and both are named here so that nobody finds them in the diff:

- `scripts/check_space_boundary.py`: two entries for `('scripts/run_scope.py', 'run_shards')`, in
  the existing class "Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that
  tree". Without them the gate's `extra` check is red, because the leg's shard roots are a
  temporary directory the dispatcher creates.
- `proof/WARP-0716/crossing-state.md`: regenerated with `scripts/suite_survey.py --emit-report`.
  It carries the digest of `scripts/selftest.py`, and `scripts/check_generated.sh` is red when it
  is stale. Earlier dispatcher changes regenerated it the same way.

## The falsifiers

`falsifiers.json` and `mutations.txt`: `python3 scripts/check_teeth_mutations.py --finding 221`,
4 registered, 4 executed, 4 rejected, baseline and no-op green. Three defects turn only their own
row red. `shards221-shared-tmpdir` turns its row red and five more: with every shard given the
leg's temporary directory, each confined shard's layer grants the directory the probe stands in,
so every confined fixture leg of the suite is a breach, which is the same defect seen again.

## What is not proven here

See `open.md`.
