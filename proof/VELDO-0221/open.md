# VELDO-0221: what is not proven by this bundle, as of fix round 1

1. **The canonical gate was not run.** The lead queues it. `criteria` in `manifest.json` are
   `pending` for that reason. What was run by hand is in `legs.md`. The integration stage's nested
   legs, which shard through the same dispatcher, were not run at all.
2. **AC4's ratios are the build's, not the lead's, and each was measured once.** The lead restated
   AC4 as a paired ratio and gave no number. The specification now says one third (confined) and
   one half (unconfined), which are the first text's own bounds as ratios. One paired run measured
   0.148 and 0.448 (`legs.md`). The unconfined figure is 0.225 to the end of the last shard; the
   rest is the isolation check's 300 second wait for files other sessions left in /tmp, so on a
   host where that wait happens the ratio sits close to the bound, and with a slower ordered run
   or a faster one it would move. The load on the host changed between the four runs.
3. **Six unconfined suites run without an instance name** (`run_scope.UNNAMED`: 85_veldo_0171,
   86_veldo_0189, 91_veldo_0167, 106_veldo_0185, 117_veldo_0227 and 127_veldo_0234, each of which
   runs the current engine over a host an older engine laid down), and
   **suite 151 runs without a Landlock layer of its own, alone** (`run_scope.UNLAYERED`). AC2 and
   AC3 say every shard. Both tables need the owner's decision (README decision 1; the lead already
   narrowed 151).
4. **What the unit check cannot see or tell apart.** It reads the manager every 2 seconds and at
   every shard's end, so a unit that starts and ends between two readings is not seen. A unit a
   shard leaves that is neither engine-shaped nor refers to that shard's roots (an empty slice a
   suite named itself, for example suite 63's) cannot be told from another session's and is not
   charged: the lead's rule is that only this instance's units are judged. In the fixture rows the
   manager is a list in a file; the real manager is exercised only by the unconfined leg itself.
5. **The unconfined leg is red on a shared host, by the lead's rule.** A new entry at the top of
   /tmp, in /dev/shm, in the runtime directory or in the owner's cache and state directories that
   nothing ties to a shard or to a foreign holder is waited on for 300 seconds (`SETTLE_S`, a hang
   detector) and then fails the leg with its name recorded. In the paired run every one of the 50
   shards passed and the leg still ended red, for three files another builder's session left in
   /tmp (`legs.md`). The gate's own lock keeps other heavy runs out; it does not keep out sessions
   that write to /tmp. Whether a canonical gate on this host can be green under this rule while
   other builders work is for the lead and the owner to weigh: the choices are the rule as it is,
   a list of name patterns that are known to be others', or a place of the gate's own for /tmp.
6. **Isolation is isolation of writes, signals and abstract sockets in the confined leg, and of
   nothing in the unconfined leg.** Measured by hand with the reviewer's cross-shard probe
   (`legs.md`): in a confined fixture leg a shard is refused a write into a sibling's home, a signal
   to a sibling and a connection to a sibling's abstract socket; it can read a sibling's files, and
   it can connect to a sibling's path socket. In an unconfined leg all five succeed: such a leg is
   only checked afterwards, as the specification says.
7. **The broker holds a shard's bind by ancestry, not by the kernel.** In the gate's confined leg a
   suite's `bind` and `connect` are performed by the launcher's broker, outside the shard's layer.
   The broker narrows a bind to the caller's shard's roots; a process that left its shard's ancestry
   is held to the leg's roots only, and `connect` to another shard's socket is not narrowed.
8. **A shard's result and the leg's metrics pipe are reachable by a process of the same account
   that is in no domain of its own**: any unconfined shard, and suite 151 in the confined leg
   (through `/proc/<pid>/fd`). Suite 151 now runs alone, so it has no sibling to reach, but it can
   still reach the dispatcher's descriptors. The stored per-suite claims are therefore evidence of
   what ran, not values the authority computed alone; the ledger clamps them.
9. **The leg dispatcher's claim is a constant** (1 core, 1 GiB). A shard that uses more than its
   stored claim is not covered by the node's claim any more, as it was, by accident, when the node
   held its whole cgroup's. The per-suite claims are the largest ever measured for each suite.
10. **A shard that spins without ending is not ended by the dispatcher**: its deadline is 1800
    seconds without progress, and CPU time is progress. The stage's budget ends it.
11. **The split of 15_warp_1404 duplicates about 250 lines of that suite's preparation in each of
    two new suites.** A row pins the three tables and loops equal. A change to the preparation
    itself has to be made three times, and nothing checks that.
12. **Suite 102_veldo_0210_agent_profile_runtime fails 7 rows in an ordered run under load.** It is
    an existing suite about the launcher's signal handling whose rows name grace periods. It failed
    the same 7 rows in the ordered confined leg of the paired run and once by hand beside other
    runs; it passed as a shard in the paired run and alone by hand (`legs.md`, `regression.txt`).
    This build changed `agent_sandbox.py` only in `write_layer`, which an ordered run never calls.
    It is recorded, not explained, and it is the kind of row VELDO-0358 is about.
13. **`mutation_ownership.py` accepts an instance in the authority unit's name only.** Its slice
    pattern matches neither `veldo-workers.slice` nor `veldo-workers_<instance>.slice`; it tracks
    the slices a worker's own profiles name. The specification's sentence that its patterns accept
    the prefixed names holds for the service.
14. **A dispatcher that is killed outright leaves its two directories behind**: its temporary one,
    as before, and now the leg's directory in the real runtime directory (`veldo-leg-<token>-...`),
    which lasts until the session ends. A later leg sees it as there before it started.
15. **Suite 151 by hand, outside the launcher, fails rows that read this host's real space ledger**
    (`regression.txt`). As the confined leg's first shard, alone, it passed all 37 rows.
