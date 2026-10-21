# WARP-1712: required evidence of the right kind, with a passing outcome

Implementation: `8be1f0d8d9206c1699b67d340f831e7ded21b23a`.
Baseline: `d49581b4`. The ready spec was committed at `76ee535e`; the measured proposal
and corpus results were committed at `84c86754`, before either production validator changed.
All commits use Dmitry Grinberg <dmitry@bcengi.com>. No push, merge, core edit or core install.

## Design

`engine/.veldo/validate.py` is canonical and `.veldo/validate.py` is byte-identical.
The alias table no longer maps generic `test` evidence to integration. It retains the
legacy unit spelling and the existing equivalent-kind spellings, including journey/e2e.
Evidence uses `type`; the check schema uses `name`. Neither counts without its own explicit
passing outcome: `status: passed`, or the proof example's legacy `result: pass` (also
`result: passed`). If both fields appear, both must pass. Unknown values, prose, missing,
null, failed, pending and not-run outcomes refuse. Criterion-level status is not inherited.
Design review retains its separate file route, but requires `verdict: pass` or
`pass_with_notes`; file existence alone refuses.

The shipped proof example now has explicit evidence outcomes and an integration example.
The existing WARP-0717 assertion that documented acceptance of a failed check now requires
that check to refuse. No historical proof was relabeled or given an invented result.

## Core blast radius, measured before the behavior change

`core-blast-radius.md` lists every changed spec/proof pair under each applicable cause.
`core-blast-radius.json` also records all pairs, each lost required kind, its old qualifying
entries and recorded outcomes, input SHA-256 digests, parser errors and exclusions.

| Reading | Count |
| --- | ---: |
| Spec files read | 184 |
| Manifests in the declared corpus | 173 |
| Matched spec/proof pairs | 173 |
| Unmatched manifests | 0 |
| Old check passes | 168 |
| New check passes | 61 |
| Pass -> fail | 107 |
| Fail -> pass | 0 |
| Same existing parser error in both checks | 5 |

| Cause group, overlapping | Changed pairs |
| --- | ---: |
| Unit test presented as integration | 38 |
| Result absent | 106 |
| Result failed or pending | 12 |
| Check name only | 12 |

These groups are not additive. A generic test with no outcome belongs to two groups.
"Result failed or pending" includes every non-passing outcome, including blocked and
unrecognized prose. "Check name only" means a check whose name used to count without a
passing outcome. A successful, correctly named check remains valid evidence.

Six spec files fail the current Veldo front-matter parser on unquoted colons, and five have
proofs. Both actual checks were called on those five pairs and raised the same parser error.
None of those five declares required_evidence, as `confirm.py` asserts. These are neither
silently skipped nor reported as passes, and are not effects of this change.

The measurement uses Veldo's declared corpus membership function and joins manifests by
spec_id. It imports no code from core. It runs the actual baseline function and the proposed
replacement on the same files, then checks input digests and manifest membership again.
The proposal is frozen in `proposed_check.py`; `confirm.py` proves that both shipped copies
contain that exact implementation and reproduce every prediction on the original core bytes.
Its recorded result: 357 input digests unchanged and 173 verdicts confirmed for each copy.

Reproduce from this worktree, writing the report outside core:

```sh
python3 proof/WARP-1712/measure.py /home/dmitry/projects/core /tmp/warp1712-impact.json
python3 proof/WARP-1712/confirm.py
```

## Tests and falsifiers

`python3 proof/WARP-1712/drive.py current`: exit 0, **213 passed, 0 failed**.
This is 103 matrix cases per validator copy plus seven real CLI integration cases in a
temporary adopter repository. The CLI runs `validate.py all`, exercising the parser, corpus
enumeration, spec/proof join and required-evidence check together. Positive controls require
exit 0; refusals require exit 1 and the integration-evidence diagnostic.

`python3 proof/WARP-1712/drive.py base`: expected exit 1, **69 refusal assertions fail on
the old implementation and all 41 compatibility/positive controls pass**. The driver
asserts that exact per-case relationship, not merely a nonzero exit. See `base-red.txt`.

| Mutant | Failed assertions | Log |
| --- | ---: | --- |
| Restore test/integration alias | 2 | mutant-integration-alias.txt |
| Ignore evidence outcome | 40 | mutant-evidence-outcome.txt |
| Ignore check outcome | 16 | mutant-check-outcome.txt |
| Accept either conflicting outcome | 4 | mutant-conflicting-outcome.txt |
| Accept design file existence alone | 7 | mutant-design-existence.txt |

Each mutation log includes its applied diff and final assertion counts; every process exits 1.
Mutations run in memory against the measured proposal. Production source is never mutated by
the falsifier driver, and `confirm.py` binds that proposal to both production copies.
These are successful falsification experiments, not passing executions of the broken product.

The regular suite dispatcher also ran the new suite (213 rows) and the changed WARP-0717
suite (27 rows), with zero failing rows. Their command exits are 2 by design because selected
suites are partial runs. Those diagnostic logs are retained but are not offered as evidence
of a complete unit run or gate pass. The standalone driver is the bounded evidence above.

Template synchronization passes: 284 pairs. Generated-file checks pass, including the suite
dependency closure. The ready-spec check and `git diff --check` pass.

## Gate and limits

The standalone contract check exits 1: **111 required-kind refusals across 79 historical
Veldo proofs**, exactly the affected manifests in `veldo-blast-radius.json`. That pre-change
measurement covered 193 matched pairs, of which 114 remain accepted. No historical proof was
rewritten to make the new gate green. Missing execution outcomes require real replacement
evidence; this change cannot infer those results from prose or parent criterion status.

The first canonical gate invocation redirected output directly into this proof directory.
The gate's descriptor protection refused that path. That attempt was interrupted at exit 130
and is retained in `gate-first-attempt.txt`. The retry captures a pipe from the unmodified
`./scripts/verify.sh`, avoiding that descriptor problem without weakening the gate.

The canonical gate is **incomplete and blocked**, not green. After the failures below were
established, the remaining run was interrupted during the confined integration stage. The capture
command exited 130; no final verifier exit was recorded. That stage had started its nested suite in a temporary copy after recording spend;
it did not produce a final result. Later catalog stages were not completed. This is recorded
in `gate-command.json` and `manifest.json`; `gate.txt` is the partial transcript. No complete
gate verdict, independent review approval, trunk landing or shipped status is claimed.

The gate's confined unit leg completed with 7,933 passed and three failed assertions:
VELDO-0012 AC7 (whole-corpus validator differential), VELDO-0010 AC1 (the real corpus
validates), and VELDO-0104 AC3 (the landed corpus refuses no bundles). These retain their
original assertions. They encounter the historical proofs the new required-evidence rule
now refuses; the 213 WARP-1712 cases passed inside this run.

The unconfined unit leg exited before its summary in the existing VELDO-0208
`profiles/case-input-proposal-tcp-suite-confined` test: `case_trace.syscall_lines` raised
`ValueError: incomplete file-read trace` while tracing `effects-worker-scope`. That test
and trace parser were not edited. This is recorded as a separate gate failure; no passing
unconfined-leg result or baseline reproduction of that error is claimed.
