# VELDO-0221: leg runs made by hand on the qualification host, 2026-11-21

None of these is the canonical gate. The host was shared throughout: other builders' full suites
held all three heavy-run slots, and each run below either went through the heavy-run wrapper or was
a handful of suites. Every excerpt keeps each shard's line (target, closure, roots, counts, wall,
CPU, peak memory), every failure line and the leg's summary.

## The confined leg of the whole manifest, through the leg runner and the gate launcher

`python3 -I -S scripts/gate_legs.py --root <worktree> --stage unit --record <file> --leg confined --
"python3 scripts/selftest.py"`, 12 cores, at commit d84fe299 plus the then uncommitted client change.
Excerpt: `run-confined-4.txt`.

- 189 shards, parallelism 12 (no gate ledger by hand), peak 12 running, isolation check held, every
  layered shard reporting its Landlock layer in force, each shard's temporary directory a
  three-character sibling of the launcher scratch's `tmp`.
- Leg wall 678.6 s. The ordered leg on 2026-10-25 was 1,913 s.
- Critical shard: `15_warp_1404_historical_analogy`, 651.1 s wall, 638.6 s CPU. The same suite
  alone in an ordered run took 634 s (506 s CPU). The next longest shard was 192.8 s
  (`12_warp_1210_hardening_four`), so without that one suite the leg ends in about 200 s.
- 9,184 passed, 16 failed. Fifteen were rows of `151_veldo_0313_space_run`, and one was
  `101_veldo_0208_landing_reuse` ending without a verdict. Both were defects of this build against
  existing suites, both are fixed, and the fixes were then run in the launcher (next section).

## The four suites that failed above, as shards inside the launcher's domain, after the fixes

`run-mini-1.txt`: the same launcher and domain, a dispatcher over four suites, 2 at a time.

- `101_veldo_0208_landing_reuse`: 185 passed, 0 failed. Its row
  confined-stage/unit-bind-outside-scratch-refused binds beside its HOME; the broker now holds a
  shard's bind to the shard's roots.
- `151_veldo_0313_space_run`: 37 passed, 0 failed, with no Landlock layer of its own (the one
  entry of `run_scope.UNLAYERED`), while another shard ran beside it.
- `156_veldo_0315_reconcile` 35 passed and `113_veldo_0115_authority_store` 4 passed: their socket
  paths fit again under the short temporary directory.
- Isolation check held.

A whole confined leg was not run again after these fixes: two runs were queued for over an hour
behind other builders' suites and were withdrawn.

## Suites of the unconfined leg as shards against the real user manager

`run-mini-unconfined-3.txt`: a dispatcher over `66_veldo_0047_authority`, `85_veldo_0171_setup_api`,
`71_veldo_0130_api`, `86_veldo_0189_engine_upgrade` and `74_veldo_0140_standing_delegation`, 2 at a
time, with the real shared places and the real unit list.

- Every row of all five passed: 30, 18, 45, 34 and 9.
- The isolation check charged two slices, `v4077c7c7aaa.slice` and `v4077c7c7aab.slice`, to the two
  suites running when they appeared. They are named as suite 63 names its slices, were created at
  06:42:23 and were still active seven minutes later, and suite 63 was not in this run: another
  session's run of suite 63 made them on the same manager. This is the case README decision 1
  describes: a unit carries no creator, the unit rule is strict as AC3 states, and a leg run beside
  another session's suites can be charged for that session's units. The canonical gate holds the
  host lock that keeps other heavy runs out; a by-hand run does not.
- Earlier runs of the same kind found the three things now built: an instance name set in the shard
  broke suites 66, 85 and 117 (README decision 9), and without a link to the manager's runtime unit
  directory suite 66's service was never found (decision 10).

The whole unconfined leg was not run as shards. The 50 listed suites other than the seven named in
this file are unmeasured in shard mode.
