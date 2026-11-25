# VELDO-0362 bounded evidence

Implementation commit: 987b93183245b013c5a86c4bd7710e29d529aadd. The benchmark coordinator's
SHA-256 equals the committed coordinator's digest in source-digests.json. Engine copy identical.

The new guard rows were exercised through registered mutations: 25/25 rejected at their named
rows, with baseline and no-op controls. Exact applied diffs are in mutations/. Targeted suite
results are diagnostics, not a full gate or landing approval. No full gate or full leg was run.

The native comparison uses selection.json: 150 cases spanning the analysis's 12 expensive suites,
selected deterministically from cases with validated gate-13 kills. Both trials use an immutable
scratch snapshot created by the production snapshot helper, cold timing estimates, force-fresh
verdicts, the real worker meter and ledger, and the unchanged 16 GiB host scope. The host lock
excludes gates. A fixture-only load-generator slot serializes suite 160 in both trials; existing
manager, browser and new-project limits remain in force. Only the claim store differs.

To repeat after creating an immutable snapshot and an output directory containing selection.json:

```
python3 proof/VELDO-0362/benchmark.py SNAPSHOT OUTPUT
python3 proof/VELDO-0362/compare.py OUTPUT
```

Raw trial receipts and worker logs for this drive are retained at
`/tmp/veldo-admission-0362-benchmark`. The comparison records their digests. Scope memory is the
kernel total-memory peak, including file cache; it bounds scope resident memory and is not
relabeled as anonymous memory. The separate worker anonymous-memory bound includes retained unit
accounting. Socket-throttling counters are retained alongside CPU quota and memory-high counters.

Protected paths requiring owner approval at landing are exactly:

- scripts/check_gate_mutations.py
- engine/scripts/check_gate_mutations.py
