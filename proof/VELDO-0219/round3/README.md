# VELDO-0219 round three, 2026-10-28

Starting revision: 822b69e2. The requested repairs and documentation are complete.
Owner approval of the protected scope expansion and disposition of the AC1 memory
difference remain pending. Canonical qualification remains deferred by rule 37191.

## Red and green evidence

| Item | Red | Green |
| --- | --- | --- |
| Graph present without a ledger channel | suite115-red.log: 51 passed, 1 failed; the new CLI row fails. suite104-red.log: 32 passed, 1 failed, zero cases executed. | suite115-green.log: 52 passed, 0 failed. suite104-green.log: 33 passed, 0 failed, including the real confined four-case driver call. |
| Channel selection in both directions | falsifiers.json: graph-without-channel and channel-ignored mutants fail their respective CLI rows. | Both baseline and no-op controls pass. The existing aggregate-handoff row also exercises the real inherited channel. |
| Protected scope declaration | scope-red.json: all six documentation checks fail. | scope-green.json: all six pass. The spec amendment was later approved by the owner (Telegram 37454, 37455); this audit itself is not approval. |
| Acquisition before handoff | falsifiers.json: admission219-worker-before-handoff fails admission/worker-before-handoff-refused. | Baseline and no-op pass. The row uses a real scheduler channel and verifies refusal without a worker grant. |
| Unowned lifecycle registration | falsifiers.json: admission219-unowned-lifecycle-register fails admission/lifecycle-registration-owned. | Baseline and no-op pass. Slice and service registrations cover an absent entry, an owned entry and a ledger containing a rejected entry. No real manager effects occur in these fixtures. |
| AC1 memory wording | scope-red.json lacks an explicit explanation of the difference. | scope-green.json verifies the explanation in OPEN.md. The conservative bound is retained; acceptance or revision remains an owner decision. |

All eight VELDO-0219 registered mutants fail their intended rows. All sixteen
baseline and no-op controls pass. falsifiers.json binds these results to 410cbe88
and SHA-256 hashes of the tested implementation, suites and fixture helpers.
The final suite 115 run uses the same sources. The stable suite 104 run used
beafa146; its driver and suite bytes are unchanged in the final result.

The admission fix is 80786b28, with red evidence committed in b5a41803. The
pending scope amendment is beafa146. The exact protected changes inherited from
round two are in protected-paths.diff and are enumerated with reasons in OPEN.md.
The ownership module is scripts/mutation_ownership.py, line 398; there is no
.veldo/mutation_ownership.py at this revision.

## Run boundaries and retained unsuccessful attempts

Only suites 115 and 104 and this ticket's falsifiers were run. Each invocation
executed one suite file. falsifiers.py asserts that all selected cases execute
suite 115 and runs them sequentially under the single-file allowance. No run
combined suite files. No canonical gate, native lifecycle qualification, push
or merge was performed. All processes remained attached and were awaited.
Partial selftest success exits 2 by design; failures exit 1.

suite104-input-race.log is an unsuccessful intermediate run: all four cases
executed and rejected their mutants, but editing and committing during the run
correctly triggered the input-stability check. The stable rerun is the green
evidence above. falsifiers-fixture-error.json and its log retain an incomplete
attempt in which the isolated scheduler copy could not load gate_legs.py. That
setup exception is not counted as a killed mutant. Commit 410cbe88 points the
fixture's unchanged sibling dependencies at the authority directory while still
running the copied scheduler; the full final falsifier run then passed.

The memory claim and the three inherited protected implementation files are
unchanged in round three. Their approvals remain open in the dated amendment.


Later, 2026-10-28: the owner approved the protected scope (Telegram 37454, 37455) and the AC1 memory wording (37458, 37459); the spec records both.
