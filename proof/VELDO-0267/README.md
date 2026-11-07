# VELDO-0267 proof: mutation runs on changed code at each gate and in full nightly

Branch `agent/claude/veldo-0267-0268`. Built against the ready spec (Telegram 39692), owner context
Telegram 39710. Summaries only; no raw logs.

## What was built, per AC

### AC1: a precise selection at each gate

- `scripts/mutation_selection.py` (new, engine copy byte-identical): `changed_paths` (git diff
  `--name-status -M -z`, both sides of a rename, plus every dirty and untracked path from
  `git status --porcelain -z`), `merge_base`, `reasons_for` (mutated_module at root or engine copy,
  suite_file, covered_file from the declared entry in `scripts/mutation_case_inputs.json` else the
  traced files in the coverage map, no_coverage_record for an unknown case or a changed definition
  digest, canary), `select` (the sealed `veldo.mutation-selection/v1` record: base, candidate, every
  changed path, coverage run id and digest, toolchain digests, every case with `selected` and every
  reason, counts), `recompute`, `line` (the one selection line), `plan` (never raises: any failure is
  the full sweep, named).
- `scripts/check_gate_mutations.py` (engine copy synced): `run_stage(selection=...)` runs exactly the
  selected cases plus the canaries (`stage_cases`); every reuse rule applies unchanged to the selected
  cases. `gate_selection` resolves the candidate, takes the base from `VELDO_GATE_BASE_COMMIT` (merge
  base with it), prints the selection line and writes the record to `VELDO_MUTATION_SELECTION` before
  any case runs. `.veldo/mutation-selection.json` is added to `OUTPUTS`, so it is never a candidate
  input. `--case`/`--finding` subsets and `--full` bypass the selection.
- `scripts/verify.sh`: resolves `VELDO_GATE_BASE_COMMIT` (the caller's, else `refs/heads/main`)
  before any candidate command, names the record path beside the stamp (`$VELDO_OUT`), and stamps
  `"mutation":{mode, selected, canaries, run, wall_seconds, digest, trigger, nightly}`
  (`mutation_selection.py --stamp-field`, null when the record on disk differs from the one the stage
  wrote).

### AC2: the canaries

- `scripts/mutation_selection.json` (new, protected): six canaries, the fastest measured case of each
  kind: the review driver (49_veldo_0109), the teeth driver confined (61_scope_covers twice,
  113_veldo_0145_ui with its browser fixture), the unconfined leg (65_veldo_0067_edges) and the
  systemd user manager service fixture (66_veldo_0042_clones). `load_rule` enforces six to twelve;
  `check_canaries` enforces registration, both drivers, both legs and a service fixture (a failure is
  the full sweep, `selection_unavailable`).
- Canaries always run fresh (never reused), are judged by `judge_canary` (validate_result renamed
  `canary_not_killed` with the case and what it saw); a failed canary worker (baseline, no-op or
  mutant) is also renamed `canary_not_killed`. The verdict line appends
  `mode=... selected=N canaries=M`, counted apart.

### AC3: the full sweep and its trigger

- The trigger list in `scripts/mutation_selection.json` holds both drivers, check_gate_mutations,
  mutation_selection.py/.json, mutation_case_inputs.json, `scripts/mutation_*`, `scripts/case_*`,
  gate_schedule, gate_host(.py/.json), verify.sh, gate_graph.json, gate_legs, gate_unconfined.json,
  gate_candidate, suites/shared.py and suites/manifest.json, each with its engine copy, plus
  reuse_worker, reuse_stamp, gate_reuse, agent_sandbox and candidate_git.
- Full sweep, named on the selection line, for: a trigger path, a missing or unreadable coverage map
  (`coverage_missing`), changed toolchain digests (`toolchain_changed`, digest of each driver's
  `toolchains` entry), the last green or explained sweep older than 36 hours (`nightly_stale`), and
  anything unreadable (`selection_unavailable`).

### AC4: the nightly sweep and nightly_red

- `scripts/mutation_nightly.py` (new, engine copy): crontab line in its header; resolves the trunk
  tip, takes the host lock from `scripts/gate_host.json` with a blocking exclusive flock (waiting for
  a running gate), enters its own scope (`gate_host.make_scope`), checks the trunk out cleanly into
  `<state>/checkout` (detached linked worktree), runs that checkout's `check_gate_mutations.py --full`
  (every case fresh, every confined baseline traced with `case_trace`, unconfined ones too unless
  their suite traces workers itself), records `veldo.mutation-sweep/v1` under `<state>/sweeps/`
  (run id, trunk commit, start, end, verdict, failures, wall/CPU/peak memory, coverage digest),
  publishes `<state>/coverage.json` only when green, and notifies once on red and once when not
  finished by 07:00 local (notifier argv from `<state>/nightly.json`).
- `.veldo/policy_check.py` (engine copy synced): `nightly_refusal` reads the sweep records through the
  installation's own `scripts/mutation_selection.py`; the latest finished sweep red and not explained
  by an approval (`scope.nightly_run` = run id, `scope.cases` giving each failing case a reason)
  refuses as `nightly_red`. Applied when `BASE` is set (the lander's installed policy run), when
  `LANDING` is set, or with `--protected-ref`.
- `.veldo/policy.yaml`: the new rule, reader and runner (and engine copies) are protected paths.

## Rows and outcomes

Suite `scripts/suites/140_veldo_0267_mutation_selection.py`, 43 rows (RESULT below).

| AC | rows |
|----|------|
| AC1 | select/m1-selects-a-and-canaries, select/shared-selects-c, select/docs-selects-only-canaries, select/new-case-always-selected, select/recompute-agrees, select/engine-copy-and-suite-file, select/changed-definition-selected, select/declared-inputs-are-the-covered-set, changed/rename-both-sides-and-dirty, record/written-with-line, record/stamp-names-digest |
| AC2 | canary/empty-selection-runs-canaries, canary/broken-worker-reds-stage, canary/declaration-valid, canary/emptied-names-the-bound-of-six, canary/declaration-covers-drivers-legs-fixture |
| AC3 | trigger/every-group-forces-full (28 paths), trigger/coverage-missing, trigger/coverage-unreadable, trigger/nightly-stale, trigger/toolchain-changed, trigger/unavailable-runs-full |
| AC4 | nightly/waits-for-lock-then-sweeps, nightly/green-publishes-coverage, nightly/red-record-names-case, nightly/one-notifier-call-naming-case, landing/red-blocks, landing/other-run-id-does-not-clear, landing/latest-is-red, landing/approval-clears, landing/red-again-without-approval, landing/later-green-clears |

## Falsifiers: red then green

Each registered mutation is applied inside the suite to an in-memory copy of the module it names
(compiled under the real file name); its `falsifier/*` row requires the targeted row GREEN on the real
module and RED on the mutated copy. One run therefore shows both outcomes.

| falsifier | mutation | targeted row | real | mutated |
|-----------|----------|--------------|------|---------|
| ac1-1 | `covered_file` branch disabled | select/shared-selects-c | green | red |
| ac1-2 | unknown case not selected | select/new-case-always-selected | green | red |
| ac1-3 | record keeps only the first reason | select/recompute-agrees | green | red |
| ac2-1 | judge accepts a worker reporting every row killed unrun | canary/broken-worker-reds-stage | green | red |
| ac2-2 | coordinator drops canaries on an empty selection | canary/empty-selection-runs-canaries (verdict line canaries=0) | green | red |
| ac2-3 | canary list emptied in a fixture copy of the rule | canary/declaration-valid (refusal names six) | green | red |
| ac3-1 | trigger list no longer covers mutation_selection.py | self-change row | green | red |
| ac3-2 | age bound skipped | trigger/nightly-stale | green | red |
| ac4-1 | runner skips the lock | nightly/waits-for-lock-then-sweeps | green | red |
| ac4-2 | landing check reads only green records | landing/red-blocks | green | red |
| ac4-3 | red sweep publishes its coverage map | publish row | green | red |

## Suites run

RESULT

## Still open

OPEN
