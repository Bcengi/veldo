# B2 current-head recheck, 2026-10-15

Correction: independent review found the retained recurring-tick diff unreachable.
Its old failure summary is withdrawn. `recurring-tick.diff` and its section in
`results.txt` now contain the reachable replacement and real rerun from the
[recovery correction](../b2-recovery.md). Other sections below describe the earlier
round and are not new verification claims.

The repeated findings were checked against starting commit fdbf5c3a. All three
runtime corrections were already present there; this recheck does not replace
them or claim another implementation fix.

1. `RemoteLaunch.ends_at` includes `ACCEPT_SECONDS`. Both the factory timer and
   remote wait use it. The grace row now advances the authority's result clock
   as well as the launch clock, and checks the final invocation report and token
   charge in addition to the dispatch exit and worker usage.
2. `FactoryLoop.run` returns immediately without a wake. Remote launches have one
   deadline each; a committed signed result calls `remote_result` directly.
   Idle iterations read no dispatch records and trigger no factory passes.
3. Acceptance journals the hold in the worker reservation. Restart reads it back.
   Signed host cleanup or a signed refusal releases capacity, including delayed
   evidence after an unknown outcome. Prepared dispatches that never accepted
   retire on transport loss or expiry. The existing capacity-one regression runs
   three successive jobs and checks duplicate release and incomplete cleanup.

`results.txt` records targeted falsifier failures against 75223fdd. Each mutation
was applied separately to both engine and installed copies, then restored before
the next suite. The grace, recurring-tick, durability and release mutations repeat
the earlier falsifiers. Two additional mutations remove the result wake and hold
never-accepted dispatches; their named regression rows must fail too. The retained
diffs omit unchanged context; apply with `git apply --unidiff-zero`.

Only `python3 scripts/selftest.py --suite 105_veldo_0125_relay` and
`python3 scripts/selftest.py --suite 106_veldo_0125_routing` were used. The
dispatcher includes its required prerequisite checks and returns exit 2 on a
successful PARTIAL run. `verification.txt` records the unmutated summaries and
mirror comparison. No full selftest, general mutation runner, canonical gate,
native Mac run, deployment or independent review was performed in this recheck.
The reviewer still owns the canonical gate and real verification stamp.
