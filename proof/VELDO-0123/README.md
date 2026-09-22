# VELDO-0123: every mutation runs fresh in every gate

The stage executes all 38 registered cases (33 teeth, 5 review) on every invocation. It checks exact inventory equality, completed green baseline/no-op observations and the exact named assertion becoming false. Missing targets, crashes and surviving mutants fail the stage. Workers use an isolated snapshot with bytecode disabled and leave the checked tree unchanged.

The hard stage budget is 120 seconds plus 5 seconds for cleanup, about 8.7 times the original measured 13.8-second cold cost on this machine. Reuse was removed with the owner's approval (Telegram 28800 answering 28798). The spec remains ready.

| Criterion | Named qualification row |
| --- | --- |
| AC1 | `gate/both-mutation-drivers-are-required` |
| AC2 | `gate/mutation-results-have-teeth` |
| AC3 | `gate/mutation-stage-budget-is-enforced` |
| AC4 | `gate/removed-teeth-redden-the-gate` |

All four unmutated controls pass. Every declared falsifier and at least one second mutation per row completes and makes its named assertion false (nine drives total). These are assertion failures, not crashes or absent rows. The diffs and observations are in `falsifiers.json`. The fixtures also exercise real canonical-shell failure propagation and a hung process group.

The real domain qualification independently weakens all 25 registered driver/target pairs, invokes both complete inventories each time and requires a named surviving mutant. Unchanged and no-op controls execute all 38 cases; the no-op must preserve all observations. `removed-teeth.json` retains full failure receipts and applied diffs. Successful stage receipts contain counts, inventory/input/implementation digests and a SHA-256 of the full canonical result array instead of per-case dumps.

All 25 domain edits were detected. The unchanged control took 11.247s and the no-op control took 11.236s, each with 38 cases and 48 workers. The final clean-tree canonical gate will be recorded here after this proof is committed. This is implementation evidence, not an independent review or a merged-tree stamp. Nothing is pushed.

Regenerate compact evidence outside the checkout:

```sh
python3 -B proof/VELDO-0123/drive.py refutations --output /tmp/veldo-0123-refutations
python3 -B proof/VELDO-0123/drive.py removed-teeth --output /tmp/veldo-0123-assertions
python3 -B proof/VELDO-0123/drive.py stage --output /tmp/veldo-0123-stage
```

Add `--full` to any of those commands to retain full successful per-case data. For example:

```sh
python3 -B proof/VELDO-0123/drive.py removed-teeth --full --output /tmp/veldo-0123-full
bash scripts/verify.sh > /tmp/veldo-0123-gate.log 2>&1
git checkout -- .veldo/last_verify .veldo/events.jsonl
```

Result digests bind the observed run, including elapsed times; new runs naturally have different digests. `host.json` identifies the qualification machine. `history.json` preserves earlier timings, artifact digests and the full available descriptions of earlier surprises, with commands to retrieve the original artifacts from commit `12df6ba`.

During this rework, an initial domain qualification was intentionally interrupted after ten successful assertion edits to strengthen capture: retain the complete failed stage receipt and compare the final no-op observations exactly. Its full terminal output is in `interrupted-qualification.log`; it is not counted as a completed qualification. The replacement run below covers all 25 targets.

An attempted focused command used the abbreviation `--suite 53`; the dispatcher refused it without running assertions (full output: `selector-refusal.log`). Using `--suite 53_veldo_0123_mutations` ran the four qualification rows successfully. The dispatcher correctly returned exit 2 for a partial run; only the full canonical gate below is gate evidence.
