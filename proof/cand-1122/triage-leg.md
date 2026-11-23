# Unit-leg triage, round 4

Implementation: `5b69957ebaed1654d496fcb7792dc9e3078046fc`; baseline `8656888f8`, failing tip `382c847b6`.
The supplied leg stopped in suite 116 after 580 failure rows. These counts partition its
snapshot, not a rerun of every failure: guarded-layout cascades 243; missing service
custody 184; setup keystore fixtures 81; shared team fixtures 54; timer composition 4;
closure declarations 2; scaffold assets, work IPC and send inventory 1 each; inherited
live captures 2; inherited scratch/signal interference 7.

| Representative | Baseline | Candidate | Repaired |
|---|---:|---:|---:|
| 0126 intake | 44/0 | 35/10 | 45/0 |
| 0058 gate output, host | 42/0 | 31/12 | 43/0 |
| 0039 dispatch | 51/0 | 37/21 | 58/0 |
| 0040 containment | 85/0 | 80/10 | 90/0 |
| 0138 timers | 39/0 | 41/1 | 42/0 |
| 0717 closure | 52/1 | 51/3 | 54/0 host |
| 0047 authority/assets | 56/0 | 58/3 | 61/0 |
| 0052 work IPC | 80/0 | 80/1 | 81/0 |
| 0168 send inventory | 52/0 | 52/1 | 53/0 |
| 0162 setup | 52/0 | 28/25 | 53/0 |
| 0188 shared team | 53/0 | fixture acceptance crash | 54/0 |
| 0127 configuration | 52/2 | 31/24 | 53/2 |
| 0210 scratch, exact host archives | 263/0 | 264/0 | unchanged |

Counts are passed/failed, including the shared preamble. Each selected one suite;
successful partial runs exit 2. Comparisons used pc2 immutable commits, or host_heavy
with exact commit archives when the fixture needed the host. The pc2 0717 comparison
has one environment failure on both tips. Gate-output also required the host for a
clean comparison (pc2: 10 old, 14 candidate). Additional repaired checks: Codex lifecycle
48/0, Claude adapter 65/0, Codex baseline 49/0, domain-registry behavior 30/0 on the host
(the extra pc2 domain-registry run had two routing/authority-unavailable failures).

The guards stay on. Valid fixture layouts replace misplaced stores; authority fixtures
enter explicit service custody and a fixture Secret Service. The dispatch worker proves
its store read is denied; its birth digest binds the authority-side journal observation.
Exact Codex argument checks include the outer guard's sandbox setting. No suite assertion
was dropped. No full leg or load generator was run; the unconfined list is unchanged.

Remaining: the two previously documented stale live captures, and the seven scratch
failures seen in the aggregate but green alone at both exact tips. Later suites were not
reached by the supplied leg; nothing here claims their result or a full-leg pass.

Checks: personal setup 0 findings; template sync 361 pairs; closure generation unchanged;
space boundary passes; changed Python parses; diff whitespace clean. Wall-clock census
passes after removing only the five converted baseline sites (2860 sites; 2704 baseline
entries, 2824 allowed sites). Detailed group attribution and fix-commit map are in the
requested external `triage-cand-1122-leg.md` report.
