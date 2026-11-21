# VELDO-0221: what is not proven by this bundle

1. **The canonical gate was not run.** The lead queues it. `criteria` in `manifest.json` are
   `pending` for that reason. What was run by hand is in `legs.md`.
2. **AC4's time bound is not met by the one measured confined leg, and one suite is why.** AC4 asks
   for each confined leg in at most 600 seconds. The by-hand confined leg took 678.6 seconds, of
   which `15_warp_1404_historical_analogy` alone is 651 (634 in an ordered run of that suite by
   itself). The specification assumed no suite over about 100 seconds. The suite is outside this
   ticket; every other shard ended within 193 seconds. The unconfined bound is unmeasured.
3. **The whole unconfined leg was not run as shards**, and no whole confined leg was run after the
   last fixes (`legs.md`). Seven of the 50 listed suites were run as unconfined shards.
4. **Two parts of AC2 and AC3 are narrower than their text, each for an existing suite that is
   outside this ticket** (README decisions 9 and 11): no unconfined suite of this repository gets
   an instance name yet, and suite 151 runs without a Landlock layer of its own.
5. **The leg node's own claim counts its shards twice.** `scripts/gate_schedule.py` measures a node's
   cgroup, which includes every shard, and records that as the node's own claim, while each shard
   also claims on the ledger. The second gate after this lands will therefore grant fewer shards at
   once than the host could run. It is safe (it over-reserves) and it is outside this footprint
   (`gate_schedule.py`, `gate_graph.json`). The fix belongs with the node's claim: a leg node should
   claim only its dispatcher, as the mutation node hands off to its coordinator claim.
6. **The broker holds a shard's bind by ancestry, not by the kernel.** In a confined leg a
   suite's `bind` is performed by the launcher's broker, outside the shard's Landlock layer. The
   broker finds the caller's shard by walking its ancestors and narrows to that shard's roots. A
   process that left its shard's ancestry (reparented to the tree's init) is held to the leg's
   roots only, and `connect` to another shard's socket is not narrowed.
7. **AC2's "install at once" and AC3's /dev/shm and unit cases are driven with stand-ins inside the
   gate.** Suite 157 runs in the confined leg, where there is no user manager and /dev/shm cannot be
   written. Its rows drive the real dispatcher and the real engine naming functions in two parallel
   shards, with a fixture directory and a fixture unit list in the places of /dev/shm and the
   manager. The real places are exercised only by the unconfined leg itself.
8. **The top of the system temporary directory is attributed, not strict**, and a by-hand leg
   beside another session's suites can be charged for that session's units (README decision 1,
   `legs.md`).
9. **No full ordered run of the whole suite was made.** The suites nearest the changed files were
   run one at a time in ordered mode (`regression.txt`).
