# VELDO-0358 wave 1, fix round 2

Implementation: `5c91c8e94` (event-synchronized canary control) and `9fda26203`
(canary recorded in the existing live CPU-work fixture). The spec's AC12, falsifiers,
and exact 2026-11-22 lead History entry were already amended in `5c91c8e94`.

Run 31's failure was the separate short canary leg ending without an applied-load
record. Startup acknowledges that each generator reached its body; it does not
acknowledge its first write. A short canary can finish before the live writer has
written any bytes, and the real generator correctly reports `load_not_applied`.
The old assertion conflated recording the ordinary canary with proving a separate,
very short load leg. `9fda26203` runs that canary before the established live fixture
ends and validates its result/exit pair against the same leg's applied-load record.
All generator-liveness, positive-work, affinity, teardown, and canary-control
assertions remain in place. The canary's color and the slowdown reading remain data.

The retained run-31 log lacks its inner load record, so it cannot identify which
counter was zero. The falsifier exercises an alive writer at zero bytes: its first
write waits on a pipe event sent when the CPU fixture reports its halfway point.
The original standalone canary provides no halfway event and therefore ends before
that write. This forces the original `load/level-by-construction` row red with
`the canary leg has no applied load record`. With the fix, the same event schedule
releases the writer during the existing CPU-work fixture and the row passes.
`falsifier.py.txt` runs each version's AC12 prefix with every original assertion;
it changes only the writer schedule and supplies the halfway event. It never
fabricates a load record or uses a duration to judge the result.

The finishing procedure runs through the external `host_heavy.sh` wrapper.
`drive.py.txt ROOT OUT suites` runs three whole suite-160 invocations, then the
two registered mutants once each, then the before/after falsifier, sequentially.
Suite 160's own real AC12 generators supply the load. There is no overlapping
outer generator and no pool of suite runs. Its generator legs wait for cleanup
before advancing. The driver records real load records without modifying the
suite and judges each partial run with the repository's `gate_legs.judge`.
The mutant worker executes the exact registry replacement and captures the actual
false `expect` assertion. These are direct worker proofs, not a claim that a full
mutation stage or full gate passed. The 3600-second subprocess bounds detect hangs;
no deadline supplies a passing or mutation-rejection verdict.

Earlier evidence remains valid for behavior untouched by `9fda26203`:
`load50-first.txt` cites the 49 passes and retains run 31's sole failure and the
raw batch digest. All 50 raw results remain in `/tmp/veldo-0358-round2-load50`.
The interrupted second 50-run batch is not used. `mutants-stage.txt` retains the
earlier invalid full-stage attempt and its baseline/no-op/false-row observations;
its `unproven` classification is not relabelled as an assertion-stage receipt.

Results (2026-11-22; owner 42987 permits one test three times for this fix):

- Suite 160: three of three sequential loaded runs passed; each reports 33 passed,
  zero failed. Elapsed seconds (data): 160.66, 163.66, 161.37. Each live fixture
  records all six spinners alive with positive CPU and its live writer with
  positive bytes. Every live, killed-spinner, and killed-leg fixture cleaned up.
- `load358-canary-read-inverted`: one registered mutant run, rejected by the
  `load/level-by-construction` assertion, `the event-synchronized canary control
  is not green`. It also fails `leg/proves-and-blocks` because the inverted reading
  changes the ordinary fixture canary; both failures are retained in its log.
- `load358-canary-event-wait-removed`: one registered mutant run, rejected by that
  same assertion; no other row fails. Neither mutant hangs.
- Before/after short-leg falsifier: PASS. The original row is red with exactly
  `the canary leg has no applied load record`; its writer is alive with zero bytes.
  The fixed row is green under the same event schedule, with positive writer bytes
  and an applied-load record. All generator processes are gone on every path.

See `batch.txt` for execution order, `suite-160-{1,2,3}.txt` for complete suite logs,
the two `load358-canary-*.txt` files for mutation observations and replacement
digests, and `short-leg-falsifier.txt` for the before/after result. The protected
suite 157 and unconfined declaration are byte-identical to the starting checkout.
This round retains the earlier 49 passes and reruns only the touched suite three
times, as authorized; it does not replace them with another 50-run batch.

Final validation: `check_personal_setup.py` found 0; `git diff --check` passed.
The round-2 proof is approximately 85 KB. See `checks.txt`.
