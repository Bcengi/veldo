# VELDO-0221 proof: a gate leg runs its suites as isolated parallel closure shards

Built on branch veldo-0221 from main at 23318512, reviewed at e48e790a (verdict FIX), and fixed in
fix round 1 on 2026-11-21. This file says what was built, what the fix round changed for each review
finding, and every place where the build decided something the specification does not spell out. The
decisions are listed where a reviewer can judge them instead of finding them.

## What was built

- `scripts/run_scope.py`: the shard machinery. `run_shards` runs one fresh interpreter per suite of
  a leg (`selftest.py --suite NAME --shard FD --shard-root DIR`), gives each its own HOME, TMPDIR,
  XDG configuration, data, cache, state and runtime directories and its own instance name, reads
  each shard's result from a pipe, admits shards by the manifest's declared resources and by the
  gate ledger, and runs the isolation check. `leg_suites` is the one place a leg's suite set is
  computed.
- `scripts/selftest.py`: in a gate leg the dispatcher runs `run_shards` and composes the aggregate
  line from the target suites' counts; a bare run and a selector keep the ordered run.
- `scripts/agent_sandbox.py` (and the engine copy): `write_layer`, the stacked Landlock layer a
  confined shard applies to itself, which also scopes signals and abstract sockets; `--inherit`;
  and the broker's hold of a shard's `bind` to the shard's roots.
- `scripts/gate_legs.py` (and the engine copy): `ShardClaims`, the leg's side of the gate ledger;
  the per-suite shard measurements; the two kinds of node record.
- `scripts/gate_schedule.py` (and the engine copy): a leg node holds only its dispatcher's claim
  once its shards claim for themselves, and a shard's claim is held to what can always be granted.
- `scripts/check_first_use.py`: hands the leg's descriptors to its nested dispatcher.
- `.veldo/control_containment.py`, `.veldo/control_client.py`, `.veldo/control_service.py`,
  `.veldo/control_factory_setup.py` (and the engine copies): the instance name.
- `scripts/mutation_ownership.py` (and the engine copy): the authority unit pattern accepts a name
  with an instance.
- `scripts/suites/157_veldo_0221_suite_shards.py` (23 rows), the manifest and the closure table.
- `scripts/suites/15_warp_1404_historical_analogy.py` and its two new parts `_audit_b` and
  `_audit_c`: the long suite's twenty audit cases cut into three suites, no row changed.
- `scripts/check_teeth_mutations.py`: 15 registered falsifiers, in their own block.
- `scripts/check_space_boundary.py`: four table entries for the dispatcher's two directories.

## Fix round 1: each review finding, what changed, its row and its falsifier

Rows are in suite 157 and are named `suite-shards/<row>`. Falsifiers are registered under finding
221 in `scripts/check_teeth_mutations.py`; `falsifiers.json` holds the run.

| Finding | What changed | Row | Falsifier |
|---|---|---|---|
| F1, open item 5: the leg node's claim counted its shards twice | `gate_schedule.py`: at a leg node's first shard request its own claim shrinks to `LEG_DISPATCHER` (1 core, 1 GiB), and a node that dispatched records that as its claim, never its cgroup's total. `gate_legs.record_resources` keeps the two kinds of record apart. | leg-node-claims-only-its-dispatcher, leg-record-kinds-never-mix | shards221-leg-claim-counts-shards |
| F1, second half: a claim that could never fit was re-asked for ever | `Ledger.shard_claim` holds a shard's claim to the capacity less the mutation floor and every leg's dispatcher, so a single shard always fits once the others ended. | leg-node-claims-only-its-dispatcher | shards221-oversized-claim-forwarded |
| F2: the deadline row used a 1 second deadline | The row keeps the production deadline and moves the dispatcher's clock, only after the fixture has written that it is running. The deadline itself now runs from a shard's last progress (output or CPU time), never from its start. | deadline-fails-the-suite, deadline-runs-from-the-last-progress | shards221-deadline-from-start |
| F3: "every unit started during the leg carries some shard's prefix" was not implemented | Every shard of both legs is given an instance name (six listed exceptions, below). The manager's engine-shaped units are read at every tick, and one that refers to a shard's roots without that shard's prefix is a breach even when it is gone at the leg's end. | isolation-checked | shards221-unprefixed-unit-allowed, shards221-unconfined-shard-unnamed |
| F4: other sessions' units turned the check red, after a 300 second wait | Only this instance's units are judged: by the leg's random token in the name, or by reference to a shard's roots (the unit's properties and its processes' environments). Anything else is counted and named on the summary and neither charged nor waited for. | other-sessions-units-are-not-judged | shards221-foreign-units-judged |
| F5: the instance slice nested under the production slice | `veldo-workers_<instance>.slice`: a sibling of `veldo-workers.slice`, not its child. | isolated-by-construction, production-names | (the row pins the name) |
| F6: a confined shard could signal a sibling | `write_layer` sets the Landlock signal and abstract-socket scopes. Floor: Landlock ABI 6, which the leg's own domain already requires. | no-signal-between-shards | shards221-signal-unscoped |
| F7: the claim store accepted any size | The ledger holds every shard claim to what it can grant (F1, second half); the leg runner's docstring no longer says the claim is the authority's alone. | leg-node-claims-only-its-dispatcher | shards221-oversized-claim-forwarded |
| Decision 9: no unconfined suite had an instance name | The name is carried in the shard's runtime directory in both legs; an installed service reads it from its own unit's name; the installer writes nothing extra. | isolated-by-construction, production-names | shards221-unconfined-shard-unnamed |
| Decision 11: suite 151 without a layer ran beside the others | It runs alone: first, beside nothing, and nothing starts until it ended. | isolation-checked | shards221-unlayered-beside-others |
| Decision 1: an unattributed /tmp entry was printed and not charged | One rule for files in every place: a shard's when it can be tied to one, foreign when another account or another tree's live process holds it, otherwise the leg's isolation check fails with the entry and the suspects named. | unattributed-entry-fails-the-leg | shards221-orphan-entry-allowed |
| AC4's whole-leg time bound | Restated in the specification as a paired ratio (History). The paired runs are in `legs.md`. | (a measurement) | none, as for any measurement |
| The long suite | `15_warp_1404_historical_analogy` split in three; the table and the slices are pinned. | long-suite-split | (the row pins the split) |
| Found by the whole unconfined leg: nineteen suites stand their fixtures in XDG_RUNTIME_DIR, and the engine refuses a protected target beneath a temporary directory | In an unconfined leg a shard's runtime directory stands in a directory of the leg's own inside the real runtime directory, removed when the leg ends. Before: suites 78, 79, 80, 81, both 82s, 85_0158 and 129 failed nearly every row as shards. | runtime-directory-outside-the-temporary-directory | shards221-runtime-beneath-temporary |
| Found by the whole unconfined leg: a shard named all four XDG base directories, which the ordered run leaves unset | A shard names an XDG base directory only when its leg's environment names it; otherwise its default lies beneath the shard's private HOME. Before: suite 80's row paid-api/profile-login failed. | isolated-by-construction | shards221-xdg-always-named |
| A row that failed when suite 157 itself ran as a shard | `broker-binds-within-the-shard` assumed the suite's own process was in no shard. In a gate leg it is in one. The row now judges both cases. Found by running suite 157 as a confined shard inside the launcher, which the first build never did after writing the row. | broker-binds-within-the-shard | (existing) |

The load-rule table of the review, item by item: the 1 second deadline is gone (F2); the shard
deadline is a no-progress detector (F2); the 120 second timeouts on the manager's tools are 600
second hang detectors; units are never waited for (F4); the ledger re-ask is bounded by the claim
clamp (F1); SETTLE_S (300 seconds for a file nothing can be tied to) remains and is discussed in
`open.md`.

## Decisions a reviewer should judge

The lead kept builder decisions 2 to 8, 10 and 12 as first written (the instance name extends the
fixed prefix; the name is read through containment; the ledger channel stays with the leg runner;
the manager is admitted inside the leg; an uncuttable tree keeps the ordered run; the layer lives
in `agent_sandbox.py`; a short temporary directory; the runtime directory also links `systemd/user`;
the broker narrows binds by ancestry). What follows is what fix round 1 decided beyond the lead's
words.

1. **Six unconfined suites get no instance name** (`run_scope.UNNAMED`: 85_veldo_0171_setup_api,
   86_veldo_0189_engine_upgrade, 91_veldo_0167_setup_records, 106_veldo_0185_dispatch_setup,
   117_veldo_0227_ui_location, 127_veldo_0234_https_port). The lead decided the name is carried in
   the runtime directory, as the review recommended, and the review expected that to make 66, 85
   and 117 pass. Measured against the real user manager with every shard named: 66 passes, and
   these six fail between 1 and 20 rows each, all for one cause that no carrier can remove. Each
   lays a host down with an OLDER ENGINE taken from this repository's history (`git archive` of an
   earlier commit) and runs the current engine over it. The older engine installs its unit without
   an instance, and the current one, given a name, looks for a unit that was never installed
   (`invalid_input:state_root:holds_unit_dir`). The suites are outside this ticket. So the table
   names the six, each with its measured reason, in the protected dispatcher; every leg prints
   them; a row pins the table. Their units keep today's names and are tied to their shard by
   reference to its roots; one left behind is still its breach. The other 44 suites of the
   unconfined leg are named. This is short of AC2's "every" and needs the owner's decision, like
   suite 151. The other way out, an engine that adopts the unit name an existing installation
   has, changes how the engine upgrades a host and was not attempted here.
2. **The engine parses an authority unit's name instead of rebuilding it** (`control_service.py`
   `UNIT_NAME`, `uninstall`). Suites 85 and 117 first failed with "not an authority unit name": a
   tool was asked about a unit that another process, with another runtime directory, had named.
   With no instance configured the accepted names are exactly today's.
3. **AC4's ratios.** The lead restated AC4 as a paired ratio and named no number. The build wrote the
   first text's own bounds as ratios: at most one third for a confined leg, one half for an
   unconfined leg. The lead confirms or changes them.
4. **The leg dispatcher's claim is a constant** (1 core, 1 GiB), not a measurement, because the node's
   cgroup cannot separate the dispatcher from its shards. What the dispatcher really used is printed
   on every leg's summary (`the dispatcher itself: ...`); the paired runs show it in `legs.md`.
5. **A shard's deadline is "no progress for 1800 seconds"**, where progress is a byte of output or CPU
   time of its process group. A shard that spins without ending is not caught by it; the stage's own
   budget is what ends it, as it ended the ordered run.
6. **Who ran when a file appeared is not attribution.** The fix round first charged a file to the one
   shard that ran alone when it appeared. The whole unconfined leg showed that wrong on a shared
   host: two files another session made in /tmp appeared while only suite 101 was still running,
   and it was charged with them (`legs.md`). Such a file now fails the leg's own check and is
   charged to no suite; the suites that ran when it appeared are named beside it.
7. **The unit check's floor.** A unit that starts and ends between two readings (2 seconds apart) is
   not seen. A unit a shard leaves that is neither engine-shaped nor refers to its roots (an empty
   slice a suite named itself) cannot be told from another session's and is not charged.
8. **Signal scoping has one branch.** The lead asked for Landlock signal scoping where the kernel has
   it and a separate scope otherwise. The confined leg's own domain already refuses to start below
   Landlock ABI 6, the version that brought the scopes, so there is no kernel on which a confined
   shard runs without them; below it `write_layer` raises and the shard is reported unconfined
   (isolation_breach). No second mechanism was built.
9. **Two more entries in the space boundary tables** (`scripts/check_space_boundary.py`), beside the
   builder's two: the leg's directory in the real runtime directory is made with `mkdtemp` and
   removed with `rmtree` by `run_scope.RuntimeStand`, which removes only the one directory it made,
   named with the leg's token. The existing class for such an entry is "lead decision"; this one
   is written as waiting for the lead's approval. A dispatcher that is killed outright leaves that
   directory behind, as it leaves its temporary one.
10. **The split of 15_warp_1404 copies its preparation** into the two new suites (about 250 lines
   each), because a suite that read another suite's names would have that suite in its closure and
   run it again in its own shard. The three tables and loops are pinned equal by a row.

## The paths the build added to the footprint

- `scripts/check_space_boundary.py` and `proof/WARP-0716/crossing-state.md`: each forced by an
  existing gate check, kept by the lead. Fix round 1 added two more entries to the first (decision 9).
- `scripts/gate_schedule.py`, `engine/scripts/gate_schedule.py`: the leg node's claim (lead
  decision). Both are protected paths.
- `scripts/suites/15_warp_1404_historical_analogy*.py`: the split (lead decision).

## The falsifiers

`falsifiers.json` and `mutations.txt`: `python3 scripts/check_teeth_mutations.py --finding 221`.

## The legs that were run

`legs.md`.

## What is not proven here

`open.md`.
