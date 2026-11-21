# VELDO-0221: the legs that were run, fix round 1, 2026-11-21

None of these is the canonical gate. The whole-leg runs went through the lead's heavy-run wrapper,
from a second, detached worktree of this repository frozen at the commit named, at 12 cores
(`taskset`), with no gate ledger (so 12 shards at once). Each excerpt keeps every shard's line
(target, roots, instance, counts, wall, CPU, peak memory), every failure line and the leg's summary.
The runs of the first build (`run-confined-4.txt`, `run-mini-1.txt`, `run-mini-unconfined-3.txt`)
are kept for the record; the review judged them and they are superseded.

## The paired measurement (AC4)

One job, one host, commit c9c21e81: `run-fix1-job.txt` has the four steps with their start and end
times and the host's load at each. The sharded legs ran through the authority's leg runner
(`gate_legs.py --stage unit --leg <leg> -- "python3 scripts/selftest.py"`), the confined one through
the gate launcher. The ordered legs ran the same leg with the same environment and launcher and a
selector that covers the whole leg (`selftest.py --upto <last suite>`: a selector inside a leg keeps
the ordered single-namespace run).

| Leg | As shards | Ordered | Ratio | AC4 asks | Rows |
|---|---|---|---|---|---|
| confined | 469.6 s | 3,169.9 s | 0.148 | at most 0.333 | 9,393 of the leg's own in both runs |
| unconfined, whole leg | 603.8 s | 1,348.4 s | 0.448 | at most 0.5 | 1,107 of the leg's own in both runs |
| unconfined, to the end of its last shard | 303.6 s | 1,348.4 s | 0.225 | | |

The two legs did not run under the same load. The host's load average was about 4 while the
unconfined leg ran as shards, 4 rising to 30 while the confined leg ran as shards, about 21 to 30
during the ordered unconfined leg and 21 falling to 2 during the ordered confined leg: other
builders' work came and went. A ratio from one pair on a shared host is one measurement, not a
bound. The ordered times are also far above the 1,913 and 892 seconds of 2026-10-25, on a host
that was then quiet.

**Confined, as shards** (`run-fix1-sharded-confined.txt`): green. 191 shards, peak 12 running, 9,393
passed, 0 failed, isolation check held, 190 shards reporting their Landlock layer in force and
suite 151 running first and alone without one (45.2 s). Critical shard
`15_warp_1404_historical_analogy_audit_b`, 225.1 s; the three parts of the split suite took 215.7,
225.1 and 224.6 s, and `12_warp_1210_hardening_four` 225.0 s. Before the split the one suite was
651 s of a 678.6 s leg. The shards' wall times add up to 4,687 s and their CPU to 3,148 s. The
dispatcher itself used 0.5 s of CPU and 19 MiB.

**Confined, ordered** (`run-fix1-ordered-confined.txt`): 9,411 passed (the 26 rows of the shared
preamble are counted once here), 8 failed. Seven are rows of the existing suite
`102_veldo_0210_agent_profile_runtime` about the launcher's handling of signals; the same suite
passed as a shard in the paired run, passed alone by hand, and failed the same rows by hand beside
other runs (`regression.txt`, `open.md`). The eighth was a row of this ticket's suite 157 that was
wrong inside the ordered confined leg; it is fixed (commit 15068058) and the suite was then run in
that position, through the launcher, 49 passed and 0 failed.

**Unconfined, as shards** (`run-fix1-sharded-unconfined.txt`): every shard green, the leg RED on
the isolation check. 50 shards against the real user manager, peak 12 running, 1,107 passed, 0
suite rows failed; 44 shards with their instance names and six without (`run_scope.UNNAMED`).
Critical shard `101_veldo_0208_landing_reuse`, 290.4 s (its traced rows); the next longest 98.8 s.
The dispatcher used 14.5 s of CPU and 60 MiB. The isolation check then waited its full 300 seconds
and failed the leg for three files at the top of /tmp that another builder's session made and
left: `veldo-0218-mutations-v2.txt`, `veldo-0218-suite-v2.txt` and `rr217-local100.log`. That is
the lead's rule working as written on a shared host: an entry nothing can attribute fails the leg
with its name recorded. Eight more new entries were told apart and only noted (held by a live
process of another tree, or gone again within 75 s), and 41 units of other sessions and the
desktop were named and not judged. At this commit the first two files were charged to suite 101,
the one shard still running when they appeared. That attribution was wrong and is removed (commit
692b3d3d): such a file is now the leg's own failure and names no suite.

**Unconfined, ordered** (`run-fix1-ordered-unconfined.txt`): 1,133 passed, 0 failed, 1,348.4 s.

**The confirming run at the final commit**: see the last section.

## What running the whole unconfined leg found, before the paired run

The first build ran 7 of the 50 unconfined suites as shards. The whole leg as shards, through the
wrapper, was run twice before the paired run, and each run found a defect of the shard machinery
that no fixture row could have:

- `run-fix1-discovery-1-unconfined.txt` (commit e8505cc7, stopped after its shards ended): 201 failed
  rows. Suites 78, 79, 80, 81, both 82s, 85_0158 and 129 failed nearly every row, because a
  shard's runtime directory stood beneath the system temporary directory, where the engine refuses
  a protected target; suites 91, 106 and 127 failed the rows that upgrade a host an older engine
  laid down. Fixed in commit 3eb090e8.
- `run-fix1-discovery-2-unconfined.txt` (commit 3eb090e8, stopped the same way): one failed row,
  suite 80's paid-api/profile-login, because a shard named XDG_CONFIG_HOME where the ordered run
  leaves it unset. Fixed in commit c9c21e81.

## By hand, a handful of suites at a time

`run-fix1-by-hand-unconfined.txt`: five dispatchers over 4 to 8 unconfined suites each, against the
real user manager, made while the fixes above were being worked out. In order: the first with
every shard named (85, 86 and 117 fail); after the engine parses unit names (85, 86 and 117 still
fail their older-engine rows); six more suites (91, 106, 127 and 78 fail); after the runtime
directory fix and the six-suite table (169 passed, 0 failed); after the XDG rule (109 passed, 0
failed).

`run-fix1-by-hand-confined.txt`: a dispatcher over ten suites inside the gate launcher, at an
early state of the fix round. Suite 151 alone and green; suite 157 died without a verdict, which
is how the broker row's assumption was found; suite 104 failed one row because files of the
worktree were being edited while it ran, which is why every later run used a frozen worktree.

## The reviewer's cross-shard probe

`run-fix1-probe.txt`: the reviewer's own probe (two shards, B tries to reach A), run by hand outside
the launcher with one correction (its second shard used `json` without importing it and died). In
the confined fixture leg B reads A's file, is refused a write into A's home, a signal to A and a
connection to A's abstract socket, and connects to A's path socket. In the unconfined fixture leg
all five succeed.

## The confirming run at the final commit

`run-fix1-confirm-unconfined.txt`: the unconfined leg as shards once more, through the wrapper, at the
final code commit 15068058, with the host's load average about 19. Every shard green again: 50
shards, 1,107 passed, 0 suite rows failed, shards ended at 303.2 s. The leg ended red again, for
one file another session left at the top of /tmp (`v111_t5.py`), after the full 300 second wait
(603.5 s in all). It is charged to the leg and to no suite, with the twelve suites that ran when
it appeared named beside it. Thirteen other new entries, in /tmp, /dev/shm and the runtime
directory, were told apart and only noted, and 106 units of other sessions were named and not
judged. So in three whole runs of this leg on this host the shards were green three times (after
the fixes) and the isolation check was red each time it ran to its end, each time for another
session's file in /tmp.
