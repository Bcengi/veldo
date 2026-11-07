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
  by an approval valid under valid_approval_for (`scope.nightly_run` = run id, `scope.cases` giving each failing case a reason)
  refuses as `nightly_red`. Applied when `BASE` is set (the lander's installed policy run), when
  `LANDING` is set, or with `--protected-ref`.
- `.veldo/policy.yaml`: the new rule, reader and runner (and engine copies) are protected paths.

## Rows and outcomes

Suite `scripts/suites/140_veldo_0267_mutation_selection.py`, 48 rows (results below).

| AC | rows |
|----|------|
| AC1 | select/m1-selects-a-and-canaries, select/shared-selects-c, select/docs-selects-only-canaries, select/new-case-always-selected, select/recompute-agrees, select/engine-copy-and-suite-file, select/changed-definition-selected, select/declared-inputs-are-the-covered-set, changed/rename-both-sides-and-dirty, record/written-with-line, record/stamp-names-digest, landing/gate-selects-against-the-watermark |
| AC2 | canary/empty-selection-runs-canaries, canary/broken-worker-reds-stage, canary/declaration-valid, canary/emptied-names-the-bound-of-six, canary/declaration-covers-drivers-legs-fixture |
| AC3 | trigger/every-group-forces-full (28 paths), trigger/coverage-missing, trigger/coverage-unreadable, trigger/nightly-stale, trigger/toolchain-changed, trigger/unavailable-runs-full |
| AC4 | nightly/waits-for-lock-then-sweeps, nightly/green-publishes-coverage, nightly/red-record-names-case, nightly/one-notifier-call-naming-case, landing/red-blocks, landing/other-run-id-does-not-clear, landing/latest-is-red, landing/unbound-approval-does-not-clear, landing/self-approval-does-not-clear, landing/approval-clears, landing/red-again-without-approval, landing/later-green-clears |

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
| ac1-4 | the lander drops the base hand-off (`base=c["watermark"]`) | landing/gate-selects-against-the-watermark | green | red |
| ac4-4 | self-approval accepted (valid_approval_for's producer check passes) | landing/self-approval-does-not-clear | green | red |

Every falsifier above is also registered in `scripts/check_teeth_mutations.py` (finding 267, 13
cases `selection267-*`, each anchor occurring once in its module), so the mutation stage runs it:
baseline green, no-op equal, mutant red on the targeted row. The suite names each production module
by its literal anchor (`ROOT / "scripts" / "mutation_selection.py"` and so on) for the driver to
substitute; a .veldo mutant is loaded beside a scratch copy of the real .veldo siblings. ac3-1 drops
both `scripts/mutation_selection.py` and the `scripts/mutation_*` glob from the declaration and targets
trigger/every-group-forces-full; ac2-3 empties the declared canary list and targets canary/declaration-valid.

## Fix round 1 (check of 2026-11-07, NOT SOUND)

- F1 (AC1), fixed. `control_verification.gate_env(base)` drops any inherited `VELDO_GATE_BASE_COMMIT`
  and sets it to the base its caller passes; `observe_gate(..., base=)` hands it on; `GitLandOps.gate`
  passes `base=c["watermark"]`, the trunk commit it synced and the same base its installed policy run
  takes. verify.sh already prefers the caller's value. Row landing/gate-selects-against-the-watermark
  builds a landing-shaped workspace (fresh repository, trunk only as the watermark and
  refs/remotes/origin/main, HEAD detached on the candidate, no refs/heads/main), gates it through the
  real lander and control_verification with an installed verifier that runs the real verify.sh base
  block and the real `gate_selection`, and requires mode selected, base equal to the watermark and no
  selection_unavailable. Falsifier ac1-4 drops the hand-off and turns it red.
- F3 (AC4), fixed. `valid_approval_for` gains `accept`, a caller's scope test that only narrows it;
  `policy_check.approval_rule()` is valid_approval_for over the push range with the work's producer.
  `mutation_selection.explaining_approval(record, approval_rule)` explains a red sweep only through
  that rule (scope test: `explains`, the run id and every failing case with a reason), so an approval
  must be approved, unexpired, bound to a commit of the push and not approved by the producer. The
  landing check uses the policy module's own rule; the gate's nightly_stale reading loads the
  installation's policy_check pointed at the candidate (`policy_approval_rule`, lazily, only when a
  red sweep is read), and anything it cannot load explains nothing. The private approval glob
  (`read_approvals`) is gone. The landing rows now run over a subject repository with a push range,
  a verdict and a producer: an unbound approval and the producer's own bound approval do not clear;
  an owner's bound approval does. Falsifier ac4-4 accepts self-approval and turns the self row red.
- Side observation: `.veldo/mutation-selection.json` is now in `.gitignore`.
- F2 (the guard's policy_check leg needs VELDO-0268's protected-ref flag) is left to VELDO-0268 and
  nothing changed for it here: it is resolved when both land, once the guard passes the flag.
- scripts/suites/requires.json: `run_scope.py --emit-requires` reproduces it unchanged.

## Suites run

- Suite 140 at 3d886d3f, inside `flock -w 1200 /home/dmitry/.local/state/core-gates/.gate.lock`
  (lock taken after 375 s on the second attempt): `140_veldo_0267_mutation_selection 48 passed`,
  `74 passed, 0 failed` with its closure. Every in-suite falsifier row green (targeted row green on the
  real module, red on the mutated copy).
- The registered falsifiers through the mutation stage (`check_teeth_mutations.py --finding 267`):
  PENDING. The lock was not free within the 20 minute budget (420 s, then 375 s to take it for suite
  140, then 300 s, 1,095 s in all). The exact command is in `proof/VELDO-0267/pending_runs.sh`
  (`bash -n` clean; no flock inside, the lead runs it inside the lock; one line per step to
  `proof/VELDO-0267/pending-summary.txt`, logs under /tmp).

## Still open

- `check_teeth_mutations.py --finding 267` (pending_runs.sh).
- F2, with VELDO-0268.
- The gate-time estimates in the spec's Context are re-measured on the first gates after landing.
