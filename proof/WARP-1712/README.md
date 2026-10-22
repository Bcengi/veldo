# WARP-1712 round 4: authority-bound contracts

Implementation: `6c24fb27`, following the round 4 spec commit `84c5623c`.
D1 from the full fix check of `4c230340` is addressed. The lander passes its recorded
watermark through `control_verification.observe_gate`, the installed verifier's `--base`,
and the installed contracts entry. That entry validates the full commit and ancestry,
loads the installed policy and ratchet, and supplies the policy BASE to candidate contracts.
Gate contracts refuse absent or invalid authority bases even for a debt-free adopter.
A checkout gate freezes its trunk merge base before any candidate command runs.
Standalone `validate.py all` retains the existing trunk fallback.

The lander materializes reachable Git objects in its own disposable workspace before the
gate because borrowed objects can lie outside the confined contracts process's read roots.
Bootstrap install checks supply the initial commit they created as their authority base.
No sandbox grants or historical required-evidence entries were changed.

The new falsifier uses the production installed verifier and launcher with a small fixture
catalog. Its candidate unit stage moves both origin/main and origin/HEAD to HEAD before
contracts. The exact historical touch and new-debt refusals remain, with a red gate.
The fixture declares that unit command's unconfined leg: the actual confined gate profile
makes the candidate read-only, despite the config file's general write_roots. The test uses
`bind_refs=False` so its red result must come from contracts, independently of ref binding.
Re-reading origin/main at contracts time makes the attack gate green and the assertion fail.

## Focused checks

`round4-focused.txt`: 263 passed, zero failed, including six D1 controls.
All earlier falsifiers remain effective: 69 baseline refusals, 16 round 2 review refusals,
and all 11 strict-rule/ratchet mutants. `round4-falsifiers.json` records every actual exit
and assertion count. The new mutable-base mutant loses exactly the attack assertion while
all five controls pass. Expected exit 1 is a falsification result, not a product pass.

The regular selected WARP-1712 dispatcher reports 289 passed, zero failed, exit 2 by design.
The authority regression dispatcher reports 42 passed, zero failed, exit 2 by design.
These partial runs are diagnostics only, not gate or full-unit evidence. The initial
pre-fix authority diagnostic is retained in `round4-authority-suite.txt`; it found the
missing bootstrap base, unreadable borrowed objects, and the command-binding assertion
that needed to include --base. Final results are in `round4-authority-suite-final.txt`.
Lint, Git subprocess boundary, generated-file freshness and template synchronization pass.

## Canonical gate

Round 4 canonical verification is pending. No round 4 green gate is claimed.
The active manifest is bound to round 4; `round3-manifest.json` preserves the previous one.

## Preserved round 3 report

# WARP-1712 round 3: independent review corrections

Implementation: `90290e15`, following the round 3 spec commit `4b80fe8f`.
All five findings from the independent review of `5b2a5a95` are addressed.

- R1: walk the base register as well as current failures. A removed row requires the
  original spec and proof paths, unchanged paired identity, every base-required kind,
  and a strict pass. Remaining failing rows still refuse when touched. Tests cover
  deleting either half, relabeling, reducing requirements, moving paths, and real payoff.
- R2: use an explicit policy BASE when provided, otherwise origin/HEAD or origin/main.
  Never use a feature upstream or HEAD~20 to authorize debt. The policy object can be
  supplied to the ratchet; the default CLI loads the sibling policy. Tests include an
  earlier feature push containing both touches and new debt, plus explicit-base controls.
- R3: obtain Git's VELDO-root prefix once, strip it from changed paths, and prepend it
  to historical object reads. Vendored adoption, unchanged debt, and payoff are tested.
- R4: use the merge base for both changed paths and the prior register. Independent
  trunk proof changes and trunk debt payoff cannot make an untouched branch fail.
- R5: a supplied exit_code must be integer zero as well as an explicit passing outcome.
  This deliberately follows the owner's stricter instruction over the review's proposed
  expected_exit allowance: expected_exit=1 cannot bless exit_code=1. Legacy result=pass
  and result=passed remain supported; a zero exit alone is insufficient.

## Checks before the canonical gate

`round3-focused.txt`: 257 passed, zero failed. This includes 23 review controls.
`round3-review-round2.txt`: expected exit 1, exactly 16 assertions fail on the actual
round 2 validators from `5b2a5a95`, with seven compatibility controls passing. The driver
asserts the per-case result and requires a failing assertion for each of R1 through R5.
`round3-base.txt` retains the original 69 old-code refusals and 41 passing controls.
All 11 existing mutations are rejected; see `round3-falsifiers.json` and their logs.
The last-commit-only mutant now fails three controls because it also loses the base
spec needed to authorize a genuine payoff. No historical evidence was rewritten.
Contracts, lint, Git subprocess boundary, template sync, and generated files pass.

## Core remeasurement, read-only

Both shipped validators reproduce all 173 original pair verdicts and the frozen proposal
plus the explicit exit-code guard. All 357 original input digests and corpus membership
are unchanged. The actual strict predicate and ratchet on a temporary byte-identical
mirror yield 61 strict passes, 107 historical failures, zero errors for untouched debt,
and 214 single-pair touch refusals. Five existing parser errors remain separate errors.
See `round3-confirmation.txt`, `round3-core-ratchet.json`, and `round3-core-debt.jsonl`.
Nothing was written or installed into core; this is not a whole-core gate claim.

## Canonical gate

`./scripts/verify.sh` completed **GREEN, exit 0**, at
`67dec0c0fdc69242a4858ba4c671f6688bafb43f`, from 2026-10-21 15:39:49 UTC to
18:33:28 UTC (10,419.82 seconds). The run was uninterrupted and used the documented
command with its configured confined and unconfined legs.

- Unit: 7,980 confined assertions and 871 unconfined assertions passed, zero failures.
- Integration: the real first-use spend mutation preserved the same 7,980 and 871
  passing assertions, zero failures (1,767 and 765 seconds for the nested runs).
- Mutation: all 2,546 registered cases executed fresh and were rejected; zero reuse
  and zero invalid results. The 3,284 worker invocations include 369 baseline and
  369 no-op controls as well as the 2,546 mutants. Stage elapsed: 5,082.551 seconds.
- Lint, security inventory, generated files, docs, all seven pack install/run gates,
  template synchronization, and the remaining built-in checks passed. Catalog: nine
  run, 15 not applicable with reasons, zero waived and zero undeclared.

`round3-gate-command.json` records the command, tested commit, times and actual exit.
`round3-gate-stamp.json` preserves the gate's own green stamp. `round3-gate.txt` is a
readable transcript with only the large mutation JSON receipt replaced by an explicit
marker and summary. `round3-gate.txt.gz` preserves the complete raw output, including
that receipt, byte-for-byte; its raw and compressed SHA-256 digests are recorded in the
command record. The final follow-up commit only records evidence and the gate's own
observations; implementation and specification bytes remain those tested at `67dec0c0`.
No fresh independent review, push, merge, or shipped status is claimed.

## Preserved round 2 report

# WARP-1712 round 2: strict touched pairs and shrinking historical debt

Owner decision: Telegram 35399, "agree". Ready-spec amendment: `92cc0d4b`.
Implementation: `9fab5024e5664bf0a89826bcd574a838f46fa291`; scaffold delivery fix: `3ef567d5`.
Final Git-boundary/adoption fixes: `414e24cc` (empty-register spec amendment: `77c50382`).
All commits use Dmitry Grinberg <dmitry@bcengi.com>, with no co-author trailer.
No push, branch switch, other-worktree edit, core edit, or core install.

## Rule and maintenance

The round 1 strict predicate is byte-for-byte unchanged (`round2-confirmation.txt`).
The validator applies it to pairs touched by the push: the spec itself or any path in
its proof directory, including supporting artifacts and design verdicts. The range
uses `policy_check._range_specs()` and its Git boundary, including upstream/origin
fallback order. No resolvable range means no debt exemption.

The repository-local `.veldo/required-evidence-debt.jsonl` records 79 historical pairs,
sorted by spec and proof path, with their actual strict failure causes. Generate it with:

```sh
python3 .veldo/validate.py evidence-debt > /tmp/required-evidence-debt.jsonl
```

Review the difference, replace the committed register with that output, and commit it.
The command does not edit evidence. The gate requires exact computed contents, rejects
stale passing entries and fabricated, duplicated, omitted or altered entries, and bounds
membership by the push-base register. Recomputing cannot authorize new debt. Initial
adoption permits only unchanged historical failures. Keep the empty register after the
last entry is removed: deleting it must not reset adoption. Pay down individual pairs by
recording real passing evidence and removing their register entries in the same push.
No historical proof was relabeled or bulk-rewritten in this round.

## Recorded checks

- `round2-focused.txt`: 234 passed, zero failed. The original 213 assertions remain;
  21 ratchet controls use a temporary Git repository and the shipped CLI, with real
  commits and the real range resolver.
- `round2-base.txt`: expected exit 1, all 69 original refusal assertions fail on the
  old validator, while all 41 compatibility controls pass.
- The five original mutations still fail by exactly 2, 40, 16, 4, and 7 assertions.
  Their reruns are `round2-integration-alias.txt`, `round2-evidence-outcome.txt`,
  `round2-check-outcome.txt`, `round2-conflicting-outcome.txt`, and
  `round2-design-existence.txt`.
- Six new mutations fail: disabling touch refusal (5 assertions), reapplying strict
  enforcement globally (3), skipping computed-register equality (6), and permitting
  register growth (2), narrowing the push to its last commit (2), and allowing an empty
  adopted register to be deleted (1). See `round2-ratchet-*.txt` and `round2-falsifiers.json`. These expected process failures are
  successful falsification experiments, not passing broken-product executions.
- Standalone contracts, lint, template synchronization, generated-file freshness, and
  the spec contract check pass. Their `round2-*.txt` captures are retained.

## Core read-only measurement

`python3 proof/WARP-1712/measure_ratchet.py` reads core's declared corpus, reconciles
membership and all round 1 input digests, and applies the shipped strict predicate and
ratchet to a temporary byte-identical corpus mirror. It never writes into core or
imports code from core. The hypothetical ranges are explicit changed-path sets, not a
claim to have run core's entire canonical gate.

Of 173 matched pairs, 61 pass strictly and the same 107 fail strictly. With all 107
registered, a push touching none has zero ratchet errors. Touching each historical
pair's spec and manifest separately produces 214 single-pair refusals. Five existing
pair parser errors are separately reported and remain errors, not passes. Input bytes
and corpus membership are unchanged. See `round2-core-ratchet.json` and the generated
`round2-core-debt.jsonl`; neither was installed into core.

## Canonical gate

The first round 2 gate exposed two fresh-scaffold assertions: the new module had not
been added to the scaffolder's explicit install list. That attempt was stopped to fix
the defect. `round2-gate-first-command.json` and `round2-gate-first.txt` preserve it.
Both scaffold copies now include the module in the install list and required substrate.
`round2-scaffold.json` records fresh install and reinstall gates passing, and a mutant omitting the module refusing. Both install checks were repeated after the final corrections.

The canonical attempt at `3ef567d5` completed confined unit with **7,953 passed and one
failed**, then unconfined unit with **871 passed and zero failed**. All three round 1
historical-corpus assertions now pass, and the round 1 incomplete-trace exception did
not recur. The one confined failure was `git-boundary/no-private-git-invocations`: the
shared boundary was called through `policy._git_process`, while the source contract
recognizes the local `_git_process` binding. The call now uses that supported binding;
`round2-git-boundary-final.txt` records the complete source-boundary scan passing.

The final review also reproduced an empty-register reset defect: deleting a fully paid
register could permit later adoption to start over. `round2-empty-reset-red.txt` records
the defect, and the final CLI matrix plus `round2-ratchet-reset.txt` prove the refusal.
The same final matrix covers a spec touched earlier in a multi-commit push, with a
last-commit-only mutation as its falsifier. These fixes are in `414e24cc`.

The gate attempt was **interrupted during integration**, before applying those final
corrections. Its terminated process returned -15; there is no final verifier exit.
`round2-gate-command.json` and `round2-gate.txt` record the exact attempt and its scope.
The final tree has passing focused and standalone checks, but **no complete final-tree
canonical gate run**. Full canonical validation, including remaining integration and
later catalog stages, remains the landing blocker. No green gate or independent review
is claimed. The spec stays blocked for landing, not shipped.

The three suites containing round 1's corpus failures were also run as a diagnostic
selection: 149 assertions passed, zero failed, exit 2 because the run is partial. This
is not full-unit or gate evidence and does not appear as passing evidence in the proof
manifest. See `round2-corpus-suites-command.json` and `round2-corpus-suites.txt`.

## Preserved round 1 report

The report below describes round 1 and its historical blockers. The original manifest
is retained as `round1-manifest.json`; the active manifest records the current round.

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
