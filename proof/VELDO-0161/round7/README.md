# VELDO-0161 round 7: round 6 broke two suite 86 rows

Branch agent/claude/agent/claude/veldo-0161, from 2dd36163. Nothing here is a gate result, a review verdict or an
approval. This sandbox refuses AF_UNIX sockets and has no systemd user manager, so suite 86 (and suite 73's
setup rows) cannot run here; those runs are the host's, listed at the end.

## The finding (host run at 2dd36163)

Suite 86_veldo_0189_engine_upgrade: 59 passed, 0 failed at b44736c0; 57 passed, 2 failed at 2dd36163:

- ownership/commit-refused, "commit refuses while previous engine is installed and keeps all records": the answer
  was `{'accepted': True, ..., 'result': {'ok': False, 'reason': 'invalid_input:packet'}}`;
- ownership/start-drops, "serve drops previous bindings with no previous engine beside it".

With suite 86's baseline red, the gate's unconfined leg could not judge upgrade161-adoption-signer-not-laid (55 of
56 killed).

## The cause

Neither row is about a packet, a record or a key the ownership commands do not expect. Both rows kill setup at a
named point of the upgrade's step log (`points.index('restart') + 1`, `points.index('removed_previous') + 1`),
taken from a whole run. Suite 86's kill driver counts points by replacing `control_factory_setup.organ`: each
call that returns `control_factory_setup_upgrade` wraps that module's `point` in one more counter, and SIGKILLs
at count N. setup loads each module once per run (`_one_setup`), so the count is one per line only while the
upgrade module is fetched through organ once in a run, by inspect_engine.

Round 6's `lay_adoption_signer` fetched it again (`UP = organ('control_factory_setup_upgrade')`, for
`UP.replace`) inside the upgrade's prepare step. From then on `point` was wrapped twice and every write point,
starting with `adoption_key`, counted twice. So:

- the kill "after restart" (count 5 in this shape) landed when the log held 3 lines, after the first
  `adoption_signers`, before the restart. The previous engine was still serving. It has no `ownership_commit`
  branch, so the packet fell through to its generic `mutate`, which answers `invalid_input:packet` for a packet
  with no command and signature. That is the reply the host saw.
- the kill "after removed_previous" landed before the removal, so when serve started the previous engine was
  still beside bin, and serve kept the previous bindings.

The other kill rows (switch/kill-points and others) kill at every point or recover forward, so they stayed green.

## The fix

`upgrade_engine`'s prepare step hands `lay_adoption_signer` the engine module it already holds (`engine['module']`,
the one inspect_engine loaded); `lay_adoption_signer(plan, laying, observe, UP)` no longer calls organ. That is
the only product change: the same writes, at the same points, in the same order. engine/.veldo and the synced
.veldo copy are byte-identical (template sync pass). Suite 86's expectations are unchanged. Finding 161's
upgrade161-adoption-signer-not-laid anchor follows the call, which is now two lines. It still matches once, and
its replacement is unchanged.

## Evidence here

- `drive_points.py` (`drive-points.json`): applies suite 86's kill-driver patch, counting instead of killing, in
  one setup's module scope over a scratch host shaped like the 8bc34e94/971186ac ones. It fetches the upgrade
  module once, as inspect_engine does, then runs `upgrade_engine` with a run that stands in for the switch and
  the restart around the real prepare step: exchange point, prepare, restart point. For every N it requires the
  Nth count to be reached when the step log holds N lines, the last being the Nth point.
  - engine/.veldo now: 8 passed, 0 failed (5 counts, 5 lines).
  - 2dd36163's engine/.veldo: 4 passed, 4 failed. The kill at 5 ("after restart") finds 3 lines, the last
    `adoption_signers`; 9 counts for 5 lines. This is the host's failure reproduced.
- `drive_signer.py` (`drive-signer.json`): round 6's driver, carried over with the four-argument call. Its
  prepare stand-in gains the upgrade module's own `replace`, which production's engine module has. Result: 25
  passed, 0 failed. Round 6's behavior is kept: one run lays the key and both signers files as a fresh setup
  does, a second run writes nothing, a run killed after each of the three points is finished by the next, and
  the bad cases are refused by name, writing nothing.
- `run_falsifier.py` (`falsifier.json`): both drivers over three module sets. `killed_here: true`.
  - Baseline: 8/0 and 25/0.
  - The fix reverted (round 6's second fetch put back, anchor matched once): drive_points 4/4, red on the
    kill-point rows; drive_signer 25/0, since the signer is still laid and only the count is wrong.
  - Finding 161's registered upgrade161-adoption-signer-not-laid, materialized from its round-7 anchor
    (replacement count 1): drive_signer 24/1, red on the prepare check; drive_points red as well.
- All 56 finding-161 cases materialize with exactly one replacement each, and every mutant compiles.
- Sandbox runs:
  - suite 109: 75 passed, 4 failed (the four AC2 rows, AF_UNIX), as in rounds 5 and 6;
  - `.veldo/validate.py all` exits 0, and the template sync check passes.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 86_veldo_0189_engine_upgrade`: every row green (59), including
   ownership/commit-refused and ownership/start-drops.
2. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: every row green (43).
3. `python3 scripts/selftest.py --suite 85_veldo_0171_setup_api`: every row green.
4. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green (81), no HermeticViolation.
5. `python3 scripts/check_gate_mutations.py --finding 161`: 56 of 56 killed, including
   upgrade161-adoption-signer-not-laid in the unconfined leg, now that suite 86's baseline is green.
6. `./scripts/verify.sh`: green.
