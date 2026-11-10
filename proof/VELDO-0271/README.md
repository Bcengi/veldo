# VELDO-0271 proof

The gate runs every stage as one leg, with no namespace sandbox and no root helper. This bundle is
not complete: the whole unit suite, the registered mutations and the red run on the old code have not
been run on this tree. They are in `heavy_runs.sh`, for the lead's lock queue. Every criterion in
`manifest.json` is pending until that script has run and the gate is green.

## What is here

- `removed.json`: the table AC4 asks for. 437 lines: 4 suites, 1 mutation case, 430 suite rows and 2
  rows that stay and lost a clause. Each line names what the row checked and either the row that
  still checks it (94 lines) or "confinement only" (343 lines).
- `rows.json`: the row names of every suite whose rows differ between 24c9f5b4 and this tree, and the
  mutation case names only one of them has. The suite row `removed/table-lists-every-removed-row`
  compares it with the table. `rows.summary.json` is its summary.
- `record_rows.py`: records the row names of a checkout and builds `rows.json`.
- `heavy_runs.sh`: the runs still owed.

## How rows.json was made, and what replaces it

The record at 24c9f5b4 is a whole unit suite of a clean checkout (9056 passed, 2 failed; the two
failures are launcher rows of suite 101, which this spec removes).

The record of this tree is not a whole run yet. The 31 suites whose files changed, the new suite 141
among them, were each run alone with `selftest.py --suite` in a scope limited to 10 GB, and their row names
recorded; every other suite is taken as recorded at 24c9f5b4. `heavy_runs.sh` records the whole suite,
builds `rows.json` again from it, says whether the names are the same, and copies the result here.

## Run alone on this tree

Each of these suites was run alone and was green: 03, 14, 24, 27, 53, 64, 66, 69, 70, 73, 98, 99, 100,
101 (90 rows), 103, 112, 113_veldo_0220, 114_veldo_0216, 114_veldo_0220, 115, 127_veldo_0254,
127_veldo_0259, 128_veldo_0235, 129_veldo_0239, 129_veldo_0260, 129_veldo_0272, 129_veldo_0274,
129_veldo_0278, 140 and 141 (16 rows, with the table in place). A run of one suite is not
verification, and nothing here cites it as a pass.

## Open: one row is red, and the fix is outside this footprint

`VELDO-0230 qualify/reproduces` in suite 126 is red on this tree. Four files in proof/VELDO-0127
(`resources-gpt-6-astra-selected.json`, `resources-gpt-6-astra-none.json`,
`resources-gpt-5.5-selected.json`, `resources-gpt-5.5-none.json`) record the sha256 of
`.veldo/control_launch.py`, and AC4 changes two comments in that file. The row passes again once those
four files are written again by qualify. proof/VELDO-0127 is not in this spec's footprint, so the
build did not touch them. The two live captures in the same bundle bind the same digest. The gate
cannot be green until the lead decides this.

`proof/WARP-0716/crossing-state.md` is derived from `selftest.py` and is stale after this change. It is
also outside the footprint.

## Where the tree differs from the spec's wording

- Suite 100's traced worker rows are removed, not rewritten. They ran a declared case in a confined
  worker and checked its trace, and that check needs the confinement boundary in the trace. Restored
  without it, every one fails with "missing authority worker confinement boundary". With reuse off no
  case is declared, so the gate never takes that path. The suite's other strace row
  (`case/startup-runtime-boundary`) and suite 101's traced workers run in the unit stage. The
  snapshot assertion those rows carried is kept as two rows of its own.
- Rows of suites 99 and 100 that needed a reused result (warm counts, a conflicting stored record) are
  removed, because the stage now looks nothing up and publishes nothing. The table names the row that
  checks the new behavior for each.
- The tree registers two suite 62 cases of VELDO-0261, not three. `heavy_runs.sh` runs both.
- The unit node's estimate in `scripts/gate_graph.json` still carries the sum of the two old legs and
  is marked pending. `unit.summary.json`, written by `heavy_runs.sh`, has the measured wall seconds,
  CPU seconds and peak memory to put there.

## heavy_runs.sh

    bash <host lock wrapper> bash proof/VELDO-0271/heavy_runs.sh <scratch dir> <clean checkout of 24c9f5b4>

One pass, on a clean tree: the whole unit suite with row names recorded, the table inventory from it,
the eleven registered mutations of this spec, the five cases whose anchors moved, the two suite 62
cases, and suite 141 over a copy of 24c9f5b4, where it must be red. It writes nothing into the
repository until the last step, which copies seven small files here: `unit.summary.json`, `rows.json`,
`rows.summary.json`, `teeth-271.summary.json`, `teeth-moved.summary.json`, `teeth-261.summary.json`
and `red.summary.json`. Logs and raw records stay in the scratch directory.
