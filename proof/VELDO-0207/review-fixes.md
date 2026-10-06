# Review corrections to parts A, B and C

This is local targeted evidence, not a gate pass, independent review, approval or landing stamp.
No full selftest, mutation stage, gate, push or merge was run. The active host gate unit was left
alone. Tests and baseline probes ran sequentially. All commits use the configured Git identity
without trailers. The two gate byproducts are excluded from the commits.

## Commits

- 9ea9bb92: mandatory freshness declarations and explicit authenticated-reuse landing mode;
  deterministic result records; genuine publication conflicts make the stage red.
- 10acd901: metadata and listing enforcement in normal and forced snapshots; common socket
  denial; linked-worktree persistence; planted-defect tests and ready-spec amendments.
- The report/measurement commit is identified by `git log -1 --format=%H --
  proof/VELDO-0207/review-fixes.md`.

## Findings and tests

1. The lander's environment always sets VELDO_GATE_FORCE_FRESH. Its default is 0, matching
   part C's authenticated reuse policy; a requested force-fresh override survives. Suite 100
   removes the operator variable and checks the explicit default, then tests the override.
2. The common landing validator and all three concrete guards require reused and force_fresh.
   Suite 100 plants stamps/events missing either or both fields, drives the fleet judge and
   real shell guards, and retains positive authenticated reuse and forced-zero-reuse tests.
3. The independent tracer now handles successful and failed opens, stat/statx/newfstatat,
   lstat, access/faccessat/faccessat2, readlink, FD metadata and directory enumeration. It
   tracks cwd and child cwd inheritance. Directory listing requires an explicit directory
   declaration and the complete subtree enters the key and snapshot. Traversal components
   and temporary symlink creation cannot hide probes. The proposer uses this same parser.
   Expected absent runtime inputs are explicit, keyed, and rechecked before publication.
   Python bytecode lookups use private scratch instead of an implicitly omitted repo cache.
   Suite 99 plants caught Python and child reads, every metadata probe, listdir/scandir/glob,
   traversal and scratch-alias probes, under both ordinary and forced execution. The honest
   fixture still completes baseline/noop/mutant and publishes authenticated evidence.
4. Both sandboxes deny socket creation, connect, bind, message sending and io_uring through
   seccomp, including preopened socket connection attempts. Mutation-worker tests target
   the user bus, systemd private socket and Internet families, and inject unavailable
   filtering to prove refusal. Agent tests probe the actual service paths and IPv4/IPv6;
   inherited service descriptors remain closed. Landlock still provides filesystem denial.
5. Keyed production records exclude elapsed. Timing stays in the per-run receipt. Suite 99
   forces a second miss for the same key and checks deterministic records. A planted different
   payload produces reuse_integrity_conflict and a red stage. A subsequent attempt against
   the poisoned key remains red. Suite 98's former green-on-corruption expectation was corrected.
6. The equal-cost savings claim was removed, including its JSON summary field. The earlier
   open-only estimate is labeled about 10% time-weighted as an optimistic upper bound for
   single-module edits, with 21/30 unclean baselines and 19 universal core files.

The additional worktree test creates a disposable repository and linked worktrees, runs a
real git add and commit through the launcher, verifies the main branch is unchanged, and
then attempts denied writes to the store key, runner, launcher, coordinator, landing module,
common Git config/HEAD/hooks, main working files and another worktree's index.

## Targeted results

| Command | Focused suite checks | Total including prerequisite checks | Result |
| --- | ---: | ---: | --- |
| python3 scripts/selftest.py --suite 98_veldo_0205_reuse | 28 | 54 | 0 failed |
| python3 scripts/selftest.py --suite 99_veldo_0207_case_reuse | 89 | 115 | 0 failed |
| python3 scripts/selftest.py --suite 100_veldo_0208_landing_reuse | 79 | 105 | 0 failed |

Each successful partial run returns status 2 by repository design, not a green gate status.
Changed Python sources parse, Bash syntax passes, canonical copies match, and whitespace
checks pass. The suite dependency closure and spec index were regenerated. No full-gate proof
manifest or self-approval is manufactured; the reviewer must run the complete gate.

## New sequential measurement

`fan-in-full.json` preserves all 30 baseline observations; `summary-full.json` includes every
observed file's reach. `measure.py` retains the replay recipe using the full syscall family.
Measurement occurred during repair, before final scratch-alias/private-bytecode refinements,
not at a frozen qualification revision. Raw syscall files were temporary and removed.

| Observation | Result |
| --- | ---: |
| Sampled cases | 30 (25 teeth, 5 review) |
| Clean baselines | 3 |
| Worker errors | 15 |
| Completed baselines with failed assertions | 12 |
| Trace parsing errors | 0 |
| Total elapsed, including tracing | 204.151 seconds |
| Per-case repository file reach | min 24, median 244, max 467 |
| Distinct observed repository files | 991 |
| Universal core files | 19 |

The measurement wrapper is a twentieth universal file in the raw counts. It is instrumentation,
not an additional production dependency. Socket denials now expose service-dependent cases;
other errors include unavailable effect services and Git-history operations. Failed traces are
lower bounds. Nothing here qualifies a case for reuse or demonstrates a gate speedup.

All 30 baselines reached these core paths:

- `.veldo/arch.py`
- `.veldo/architecture.yaml`
- `.veldo/contract_loader.py`
- `.veldo/control_event_vocabulary.py`
- `.veldo/fix_validation.py`
- `.veldo/fix_validation_record.py`
- `.veldo/git_process.py`
- `.veldo/observability.py`
- `.veldo/policy.yaml`
- `.veldo/policy_check.py`
- `.veldo/tracker.py`
- `.veldo/validate.py`
- `.veldo/validate_checks.py`
- `.veldo/verdict_corpus.py`
- `.veldo/yamlish.py`
- `scripts/check_gate_mutations.py`
- `scripts/check_teeth_mutations.py`
- `scripts/mutation_sandbox.py`
- `scripts/suites/shared.py`

The next most shared files are .veldo/control_enrollment.py (26/30), control_client.py
(25/30), control_relay.py and control_store.py (22/30), followed by authority_contract.py,
capsule.py, claim.py, control_alias.py, control_decomposition_binding.py, control_document.py,
control_effect_executor.py, control_effects.py, control_engine_claude.py and control_keys.py
(21/30 each). Their churn, especially the universal floor, decides the economics.

## Expected savings

Enabled production savings remain zero: every committed production declaration is unreviewed.
The following are conditional on a warm store and reviewed, complete deterministic closures:

- Specs/docs/proof-only commit: specs and docs had no observed reads in this sample, so their
  unrelated edits could preserve all qualified mutation results. Proof is mixed: 369 proof
  files appeared, including executable helpers and fixtures. Edits to those invalidate their
  readers. Ordinary unreferenced narrative proof edits could preserve all qualified results.
  The rest of the gate still runs; suite-result reuse remains unimplemented.
- One control module: the prior open-only about-10% time-weighted estimate is an optimistic
  upper bound, not an expected measured speedup. The fuller sample has only three clean
  baselines and high shared reach, so it cannot justify a replacement timing estimate.
- One universal shared core file: no per-case savings; every dependent case must run again.
  An explicitly forced run always saves zero regardless of the changed paths.

## Deployment limits requiring reviewer attention

Filesystem access remains denied to the reuse store/key, trusted working files and external
runners. Git persistence grants the own-worktree gitdir, shared objects and branch/ref-log
parent directories. Git's sibling lock files require directory grants: sibling loose refs in
those directories are writable too. A dedicated branch namespace reduces that scope. Shared
Git objects/refs must be treated as candidate-controlled data. Trusted machinery must use an
independent immutable authority, not install code from that shared mutable Git store. This
implementation does not claim integrity isolation for individual objects or sibling refs.

The network ban also prevents real Codex/Claude CLIs from directly reaching remote model APIs.
A separately reviewed narrow transport is needed for live deployment; local commit tests are
not live-CLI validation. Existing mutation fixtures that need sockets now fail, as the new
measurement shows. Restoring those fixtures requires an enforceable service dependency design,
not silently reopening access to the user bus or an unconfined service. Full-gate compatibility
and production qualification remain outstanding for the reviewer/owner.
