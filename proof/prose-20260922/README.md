# Documentary review repairs on prose-20260922

All fourteen findings (4 through 17) have separate commits on this branch. No specification
status or production behavior changed. The only production-file edits are relay documentation,
mirrored byte for byte into engine/.veldo/control_relay.py. Nothing was pushed.

Four executable rows were added with existing fixtures. Each passes in its unmutated suite and
fails its own assertion under a temporary production mutation registered in
[scripts/check_teeth_mutations.py](../../scripts/check_teeth_mutations.py).
The driver rejects exceptions, timeouts and incomplete runs as mutation evidence.
VELDO-0027 remains approved but NOT BUILT; its two entries change only the specification.

## Findings

| Finding | Disposition and commit | Rows and evidence | Mutation / limit |
| --- | --- | --- | --- |
| 4, VELDO-0106 | narrowed-text, 0c879aa | Suite 45: policyread/a-comment-does-not-disarm-the-rule, policyread/a-real-yaml-parser-is-the-oracle, policyread/a-setting-the-owner-wrote-never-reads-as-absent. Label seventeen regression examples and selected refusals; cite the shared yamlish grammar separately. | No new row. Independent oracle agreement adds no input coverage. Exhaustive accepted/refused coverage remains INTENDED and NOT YET DEMONSTRATED. |
| 5, VELDO-0029 | added-case, 2aafedd | Suite 46: enrollment/independent-clones-share-bound-store. Independently enroll a real clone with a distinct common directory and clone UUID; matching signed domain/store bindings resolve the exact shared store. | clone-local-store appends each clone UUID to the production resolver's answer. The new row fails; all 7 unmutated rows pass. Domain-wide conflicting-binding uniqueness remains INTENDED and NOT YET DEMONSTRATED and needs authority-wide integration evidence. |
| 6, VELDO-0109 | added-case, 56478aa; remaining matrix narrowed-text in the same commit | Suite 49: unavailable/sigkill-refuses-generic-client. After a live accepted upsert, kill the fixture authority; require -9 exit, a dead socket inode, named refusal with service/last watermark, unchanged state snapshots and no binding at the expected address. Existing unavailable/no-local-authority-appears covers graceful stop. | dead-socket-success makes send report acceptance when a dead socket inode exists. The new row fails; all 5 unmutated rows pass. Registered claim/command/dispatch clients and killed-relay/live-authority cases remain INTENDED and NOT YET DEMONSTRATED pending additional lifecycle fixtures. |
| 7, VELDO-0109 | narrowed-text, 7cee2fc | Suite 49: unavailable/no-client-starts-the-authority checks the expected address in /proc/net/unix. The existing mutant binds it in the same process. | No new row. This is not a process census; process creation at other addresses or between snapshots is unobserved. The no-auto-start claim remains unchanged, INTENDED and NOT YET DEMONSTRATED across all clients. |
| 8, VELDO-0108 | narrowed-text, f688220 | Suite 48: relay/one-endpoint-one-judgement compares fixture-local pathname Unix sockets before invocation and after relay exit; source inspection for bind/listen is separate. | No assertion change. No additional fixture-local socket remains afterward. Transient listeners, abstract sockets, other paths/protocols and a host process census remain unobserved; the wider requirement is INTENDED and NOT YET DEMONSTRATED. |
| 9, VELDO-0107 | narrowed-text, 5ce91cc | Suite 47: ipc/the-coordinate-comes-from-the-request and ipc/the-socket-follows-the-binding compare per-authority callback JSONL logs. | No new row. The callback never opens SQLite, so the evidence establishes routing and dispatch. Correct real-store mutation remains INTENDED and NOT YET DEMONSTRATED pending separate store integration evidence. |
| 10, VELDO-0027 | added-case (declared set only), 9ca28ef | AC1 declares absent, stale, revoked and wrong-principal delegations with valid kind and authenticated channel, plus a valid control. Prose history records set growth for the existing claim. | No executable row or mutation: explicitly SPEC ONLY, approved but NOT BUILT. Claim text and status unchanged. |
| 11, VELDO-0027 | added-case (declared set only), 838bd53 | AC3 declares an agent-authored assertion-only control and attempted observation relabeling with otherwise complete, consistent provenance. Prose history records set growth for the existing claim. | No executable row or mutation: explicitly SPEC ONLY, approved but NOT BUILT. Claim text and status unchanged. |
| 12, VELDO-0108 | added-case, b9db2a3; exhaustive-decision prose narrowed in the same commit | Suite 48: relay/exact-limit-request-is-carried and relay/exact-limit-response-is-carried independently carry exactly 1 MiB with a short payload in the other direction. Require exact received request, exact stdout, exit 0 and empty stderr. Both boundaries added to AC1's set. | exclusive-request-limit and exclusive-response-limit independently change > to >= in production copies. Each fails its own new row; all 10 unmutated rows pass. Carrying prose states the inclusive limit and exit-4 over-limit refusal. Exhaustive transport failure coverage remains INTENDED and NOT YET DEMONSTRATED. |
| 13, VELDO-0105 | narrowed-text, bcd0b63 | Existing suite 44 rows: proofcheck/start-line-excludes-history, proofcheck/backdating-the-manifest-buys-nothing, proofcheck/unanswerable-ancestry-fails-closed. Exclusion needs conclusive answers for every considered position: manifest and last bundle-changing commit when available. | No new row: these cases already exist. An old manifest alone does not exempt a newly changed bundle; unknown ancestry stays in scope. AC1 claim text and status retained; its evidence scope is clarified. |
| 14, VELDO-0105 | narrowed-text, 46e9ff1 | Existing suite 44: proofcheck/the-corpus-this-item-exists-for calls check_bundle in-process with required=True, first an empty start line, then dynamically resolved HEAD. | No new row. Describe the actual corpus assertions and explicit arguments. Policy rewriting/restoration is labeled historical; current measurement does not load or write policy and pins no commit id. |
| 15, VELDO-0029 | narrowed-text, b6ba712 | Suite 46: enrollment/ambient-sources-decide-nothing asserts no os.environ/os.getcwd in enrollment and use of _git_process.run. Suite 50 adds hostile HOME and contaminated-history/archive coverage. | No new row. Document the shared git_process boundary and disabled system/global configuration; cite proof/fixes-20260922 finding 4 enrollment rather than claiming an os.environ count. |
| 16, VELDO-0109 | narrowed-text, c62ed98 | Existing suite 49: unavailable/no-local-authority-appears and unavailable/a-stale-read-says-so; source seen_path and send establish recording location and condition. | No new row. Record is beside enrollment in the clone's Git common directory. send records only after an accepted response and a supplied non-None seen_at; inspect supplies now. |
| 17, VELDO-0109 | narrowed-text, 4fc9f20 | Existing suite 49: unavailable/no-local-authority-appears compares recursive path, mode, nanosecond mtime, regular-file bytes and symlink-target snapshots in both state directories after shutdown. | No new row or assertion change. Existing-file overwrites are covered by the mutation recorded in proof/fixes-20260922 finding 17. Transient reverted writes and other paths remain outside this evidence, INTENDED and NOT YET DEMONSTRATED. |

## Verification

Ran `bash scripts/verify.sh` from a clean tree at
`4fc9f20553d369c1e19c3679a4fe04eed3ed6ed4`, containing all fourteen finding commits.
The command exited 0. Its full gate line, unit result and catalog result were:

```text
GATE: GREEN (4fc9f20553d369c1e19c3679a4fe04eed3ed6ed4)
selftest: 5567 passed, 0 failed
catalog: 8 run, 15 not-applicable (reasons on record), 0 waived, 0 undeclared
```

First-use integration also passed after sanctioned writes in its throwaway copy.
Restored this checkout's gate byproducts with
`git checkout -- .veldo/last_verify .veldo/events.jsonl` before running
`python3 scripts/check_teeth_mutations.py`. That command exited 0. Its last line was:

```json
{"mutations_rejected": 33, "green_suites": {"47_veldo_0107_ipc.py": 23, "48_veldo_0108_relay.py": 10, "44_veldo_0105_startline.py": 8, "46_veldo_0029_enrollment.py": 7, "49_veldo_0109_unavailable.py": 5}}
```

The complete per-mutation results are retained in
[mutation-results.jsonl](mutation-results.jsonl). In particular, the new rows were observed red
under clone-local-store, dead-socket-success, exclusive-request-limit, and exclusive-response-limit.
All mutations were applied only to temporary production copies.

The final evidence commit adds only this report and the mutation results. Gate byproducts are
restored and excluded. The gate above verifies the fourteen finding commits, not a claim of
independent review, merge approval, or a gate stamp for a subsequently merged tree.
