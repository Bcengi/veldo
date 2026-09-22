# VELDO-0123: mutation results in every repository gate

Implementation verified at `409ac130443f44683f6b1ef441a8026bd9057ffb`. The specification remains ready; independent review and the owner's separate approval for landing `scripts/verify.sh` are outstanding. Nothing was pushed. No other specification, adopter gate, or `.veldo/` module was changed.

The repository gate requires 33 teeth-driver cases and 5 review-driver cases. Successful local records live only under `git rev-parse --absolute-git-dir` + `/mutation-results/`. This proof directory is documentary output and cannot supply a reusable result. Workers read an isolated snapshot without gate receipts or bytecode; the stage does not write the checked tree.

## Acceptance criteria

| Criterion | Named row | Evidence |
| --- | --- | --- |
| AC1 | `gate/both-mutation-drivers-are-required` | Both complete registries; real canonical catalog fixtures for successful, failing, missing and disabled stages; cold/warm/mixed receipts. |
| AC2 | `gate/mutation-results-have-teeth` | Completed baseline, no-op and mutant observations; exact named target false; all baseline rows retained; moved anchors, crashes, absent/duplicate targets and survivors refused. |
| AC3 | `gate/mutation-stage-budget-is-enforced` | One non-resetting 600-second clock, individual 120-second limit, deterministic deadline schedule, real hung child and process-group cleanup; real full cold and warm measurements below. |
| AC4 | `gate/removed-teeth-redden-the-gate` | Every one of 25 driver/target pairs weakened independently in disposable trees after prewarming; real stage recomputed and found the named mutant survived. Unchanged and no-op controls passed. |
| AC5 | `gate/mutation-reuse-is-input-complete` | Checkout-private Git-admin records, complete observations, actual input bytes and modes, immutable worker copy and source/runtime stability checks; committed-tree receipts cannot supply results. |
| AC6 | `gate/mutation-reuse-invalidates-per-input` | 155 independent input changes, including all 133 importable .veldo Python paths, both drivers, case definition, suite, shared/support files, corpus, coordinator, history, schema, fixture version, modes, additions/deletions, and runtime/host/environment identity. Warm and README-only fixtures launch zero workers; missing/corrupt/unkeyable/unwritable records recompute; real Python 3.12 and 3.13 runs. |

The qualification fixtures execute the real coordinator with deterministic assertion workers and a controlled runtime identity provider. The shell fixtures execute the real stage through the canonical catalog, standing down unrelated checks. The 38 domain mutants and 25 assertion edits separately execute the real domain suites. The input-change matrix and old/new keys, computed/reused identities and worker counts are in [qualification.json](qualification.json). Every declared falsifier is applied to a temporary source copy, completes, and returns its named assertion as false; none is counted from a crash or missing row. [falsifiers.json](falsifiers.json) retains all 321 diffs and observations.

## Real cold and warm gates

Both commands were `bash scripts/verify.sh`, begun with `git status --porcelain` empty. The cold run began with this checkout's mutation-results directory removed. Before the warm run, the two gate byproducts were restored while retaining the private cache. The table reports full command wall time separately from the combined mutation-stage budget.

| Run | Gate wall seconds | Mutation-stage seconds | Computed / reused | Worker invocations |
| --- | ---: | ---: | --- | ---: |
| cold | 752.915 | 13.777 | 38 / 0 | 48 |
| warm | 724.498 | 2.452 | 0 / 38 | 0 |

```text
cold:
selftest: 5573 passed, 0 failed
GATE: GREEN (409ac130443f44683f6b1ef441a8026bd9057ffb)
warm:
selftest: 5573 passed, 0 failed
GATE: GREEN (409ac130443f44683f6b1ef441a8026bd9057ffb)
```

| Run / driver | Worker wall span seconds | Mutant worker seconds (overlap allowed) |
| --- | ---: | ---: |
| cold / check_review_mutations.py | 5.378 | 8.941 |
| cold / check_teeth_mutations.py | 6.318 | 35.427 |
| warm / check_review_mutations.py | 0.000 | 0.000 |
| warm / check_teeth_mutations.py | 0.000 | 0.000 |

Five byte-identical suite/module groups share ten baseline/no-op workers; the 38 mutant workers remain distinct. Driver wall spans overlap and are not summed as the stage budget. The combined stage includes hashing, lookups, snapshots, workers and cleanup. Both gate receipts report zero surviving workers. Full logs, full stage receipts and [timings.json](timings.json) retain the measurements.

Host: Linux-7.0.0-30-generic-x86_64-with-glibc2.39; Intel(R) Core(TM) Ultra 7 265K; 20 logical CPUs. Python: `3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`. The additional supported Python 3.13.12 qualification used an empty private cache in a disposable clone: 13.778s cold (38 computed), 2.294s warm (38 reused, zero workers); see [python313.json](python313.json).

The history identity is keyed because the start-line suite reads the real proof corpus and Git ancestry. README-only working-tree edits reuse all cases; changes to actual proof/history inputs recompute. Native runtime bytes and host/environment identity are keyed; worker environment and home are isolated. Both corrupt JSON and malformed observation structures are misses. Denied writes or unavailable keys retain fresh execution. Symlinking the cache into the tree cannot import records. A mid-run source change rejects acceptance and publication.

## Real registered mutations

Each entry below completed with an all-green baseline and an identical no-op observation set. Every listed target occurred exactly once and became false. The complete observations, implementation/input digests, inventory digests and per-case provenance are in [stage-cold.json](stage-cold.json) and [stage-warm.json](stage-warm.json).

| Driver | Mutation | Named rows turned red |
| --- | --- | --- |
| check_teeth_mutations.py | `command-only` | `ipc/signature-covers/schema`, `ipc/signature-covers/workspace`, `ipc/signature-covers/domain_uuid`, `ipc/signature-covers/store_uuid`, `ipc/signature-covers/repository_uuid`, `ipc/signature-covers/repository_root_commit`, `ipc/signature-covers/clone_uuid`, `ipc/signature-covers/binding_digest`, `ipc/signature-covers/authority_generation` |
| check_teeth_mutations.py | `omit-schema` | `ipc/signature-covers/schema` |
| check_teeth_mutations.py | `omit-workspace` | `ipc/signature-covers/workspace` |
| check_teeth_mutations.py | `omit-domain_uuid` | `ipc/signature-covers/domain_uuid` |
| check_teeth_mutations.py | `omit-store_uuid` | `ipc/signature-covers/store_uuid` |
| check_teeth_mutations.py | `omit-command` | `ipc/signature-covers/command` |
| check_teeth_mutations.py | `omit-repository_uuid` | `ipc/signature-covers/repository_uuid` |
| check_teeth_mutations.py | `omit-repository_root_commit` | `ipc/signature-covers/repository_root_commit` |
| check_teeth_mutations.py | `omit-clone_uuid` | `ipc/signature-covers/clone_uuid` |
| check_teeth_mutations.py | `omit-binding_digest` | `ipc/signature-covers/binding_digest` |
| check_teeth_mutations.py | `omit-authority_generation` | `ipc/signature-covers/authority_generation` |
| check_teeth_mutations.py | `unsigned-request-field` | `ipc/signature-fields-match-request` |
| check_teeth_mutations.py | `signed-nonrequest-field` | `ipc/signature-fields-match-request` |
| check_teeth_mutations.py | `unreachable-null` | `relay/an-unreachable-authority-is-reported-not-answered` |
| check_teeth_mutations.py | `unreachable-newline` | `relay/an-unreachable-authority-is-reported-not-answered` |
| check_teeth_mutations.py | `unreachable-space` | `relay/an-unreachable-authority-is-reported-not-answered` |
| check_teeth_mutations.py | `usage-null` | `relay/usage-has-zero-stdout` |
| check_teeth_mutations.py | `usage-newline` | `relay/usage-has-zero-stdout` |
| check_teeth_mutations.py | `usage-space` | `relay/usage-has-zero-stdout` |
| check_teeth_mutations.py | `oversized-request-null` | `relay/oversized-request-has-zero-stdout` |
| check_teeth_mutations.py | `oversized-request-newline` | `relay/oversized-request-has-zero-stdout` |
| check_teeth_mutations.py | `oversized-request-space` | `relay/oversized-request-has-zero-stdout` |
| check_teeth_mutations.py | `oversized-response-null` | `relay/oversized-response-has-zero-stdout` |
| check_teeth_mutations.py | `oversized-response-newline` | `relay/oversized-response-has-zero-stdout` |
| check_teeth_mutations.py | `oversized-response-space` | `relay/oversized-response-has-zero-stdout` |
| check_teeth_mutations.py | `unreachable-object` | `relay/an-unreachable-authority-is-reported-not-answered` |
| check_teeth_mutations.py | `manifest-fallback` | `proofcheck/start-line-not-author-writable` |
| check_teeth_mutations.py | `nested-manifest-fallback` | `proofcheck/start-line-not-author-writable` |
| check_teeth_mutations.py | `manifest-precedence` | `proofcheck/start-line-not-author-writable` |
| check_teeth_mutations.py | `clone-local-store` | `enrollment/independent-clones-share-bound-store` |
| check_teeth_mutations.py | `dead-socket-success` | `unavailable/sigkill-refuses-generic-client` |
| check_teeth_mutations.py | `exclusive-request-limit` | `relay/exact-limit-request-is-carried` |
| check_teeth_mutations.py | `exclusive-response-limit` | `relay/exact-limit-response-is-carried` |
| check_review_mutations.py | `13` | `proofcheck/unanswerable-ancestry-fails-closed` |
| check_review_mutations.py | `14` | `ipc/transport-and-command-are-checked-separately` |
| check_review_mutations.py | `15` | `relay/the-authority-judges-not-the-relay` |
| check_review_mutations.py | `16` | `relay/an-unreachable-authority-is-reported-not-answered` |
| check_review_mutations.py | `17` | `unavailable/no-local-authority-appears` |

## Assertion removal controls

[removed-teeth.json](removed-teeth.json) retains each applied assertion diff, prewarm reuse count, recomputation count, baseline observations and surviving mutant. [assertion-control.json](assertion-control.json) and [assertion-noop.json](assertion-noop.json) retain the unchanged and no-op controls.

| Driver | Assertion replaced with true | Mutations that survived |
| --- | --- | --- |
| check_review_mutations.py | `proofcheck/unanswerable-ancestry-fails-closed` | `13` |
| check_review_mutations.py | `ipc/transport-and-command-are-checked-separately` | `14` |
| check_review_mutations.py | `relay/an-unreachable-authority-is-reported-not-answered` | `16` |
| check_review_mutations.py | `relay/the-authority-judges-not-the-relay` | `15` |
| check_review_mutations.py | `unavailable/no-local-authority-appears` | `17` |
| check_teeth_mutations.py | `proofcheck/start-line-not-author-writable` | `manifest-fallback`, `nested-manifest-fallback`, `manifest-precedence` |
| check_teeth_mutations.py | `enrollment/independent-clones-share-bound-store` | `clone-local-store` |
| check_teeth_mutations.py | `ipc/signature-covers/authority_generation` | `command-only`, `omit-authority_generation` |
| check_teeth_mutations.py | `ipc/signature-covers/binding_digest` | `command-only`, `omit-binding_digest` |
| check_teeth_mutations.py | `ipc/signature-covers/clone_uuid` | `command-only`, `omit-clone_uuid` |
| check_teeth_mutations.py | `ipc/signature-covers/command` | `omit-command` |
| check_teeth_mutations.py | `ipc/signature-covers/domain_uuid` | `command-only`, `omit-domain_uuid` |
| check_teeth_mutations.py | `ipc/signature-covers/repository_root_commit` | `command-only`, `omit-repository_root_commit` |
| check_teeth_mutations.py | `ipc/signature-covers/repository_uuid` | `command-only`, `omit-repository_uuid` |
| check_teeth_mutations.py | `ipc/signature-covers/schema` | `command-only`, `omit-schema` |
| check_teeth_mutations.py | `ipc/signature-covers/store_uuid` | `command-only`, `omit-store_uuid` |
| check_teeth_mutations.py | `ipc/signature-covers/workspace` | `command-only`, `omit-workspace` |
| check_teeth_mutations.py | `ipc/signature-fields-match-request` | `unsigned-request-field`, `signed-nonrequest-field` |
| check_teeth_mutations.py | `relay/an-unreachable-authority-is-reported-not-answered` | `unreachable-null`, `unreachable-newline`, `unreachable-space`, `unreachable-object` |
| check_teeth_mutations.py | `relay/exact-limit-request-is-carried` | `exclusive-request-limit` |
| check_teeth_mutations.py | `relay/exact-limit-response-is-carried` | `exclusive-response-limit` |
| check_teeth_mutations.py | `relay/oversized-request-has-zero-stdout` | `oversized-request-null`, `oversized-request-newline`, `oversized-request-space` |
| check_teeth_mutations.py | `relay/oversized-response-has-zero-stdout` | `oversized-response-null`, `oversized-response-newline`, `oversized-response-space` |
| check_teeth_mutations.py | `relay/usage-has-zero-stdout` | `usage-null`, `usage-newline`, `usage-space` |
| check_teeth_mutations.py | `unavailable/sigkill-refuses-generic-client` | `dead-socket-success` |

## Coordinator falsifiers

All six unmutated rows were true. The declared mutations and the additional different mutation for each row follow; AC5 omissions and AC6 stale-reuse mutations are expanded independently for every matrix input. The full applied diffs are retained in [falsifiers.json](falsifiers.json).

| Applied mutation | Named assertion turned false |
| --- | --- |
| `omit-review-registry` | `gate/both-mutation-drivers-are-required` |
| `omit-teeth-registry` | `gate/both-mutation-drivers-are-required` |
| `worker-exit-as-detection` | `gate/mutation-results-have-teeth` |
| `disable-required-stage` | `gate/both-mutation-drivers-are-required` |
| `accept-surviving-target` | `gate/mutation-results-have-teeth` |
| `reset-combined-deadline` | `gate/mutation-stage-budget-is-enforced` |
| `accept-at-deadline` | `gate/mutation-stage-budget-is-enforced` |
| `ignore-stage-status` | `gate/removed-teeth-redden-the-gate` |
| `accept-removed-teeth` | `gate/removed-teeth-redden-the-gate` |
| `omit-input-.veldo/accounts.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/accounts.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/action.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/action.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/action_executor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/action_executor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/admission_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/admission_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/arch.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/arch.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/authority_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/authority_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/authorization.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/authorization.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/behavior_floor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/behavior_floor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/budget.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/budget.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/budget_state.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/budget_state.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/capsule.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/capsule.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/claim.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/claim.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/commit_attribution.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/commit_attribution.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/completion_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/completion_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/context_redaction.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/context_redaction.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/contract_loader.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/contract_loader.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_client.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_client.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_enrollment.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_enrollment.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_membership.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_membership.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_relay.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_relay.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_replay.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_replay.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_replica.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_replica.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_revocation.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_revocation.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/control_store.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/control_store.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/cost_to_change.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/cost_to_change.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/credential_issue.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/credential_issue.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/dashboard.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/dashboard.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/decision.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/decision.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/decision_review.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/decision_review.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/declared.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/declared.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/dispatch.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/dispatch.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/entity_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/entity_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/entropy.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/entropy.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/env_provision.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/env_provision.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/estimate.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/estimate.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/events.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/events.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/evidence.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/evidence.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/execution_binding.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/execution_binding.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/executor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/executor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/fix_assessor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/fix_assessor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/fix_validation.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/fix_validation.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/fix_validation_record.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/fix_validation_record.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/fixture.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/fixture.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/fleet.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/fleet.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/fleet_env.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/fleet_env.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/frontier.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/frontier.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/generated_privilege.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/generated_privilege.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/git_process.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/git_process.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/governor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/governor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/graph_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/graph_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/incident.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/incident.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/incident_reconcile.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/incident_reconcile.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/init_scaffold.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/init_scaffold.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/intent_corpus.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/intent_corpus.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/judgment_load.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/judgment_load.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/lander.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/lander.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/lessons.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/lessons.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_event_stream.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_event_stream.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_owner_reads.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_owner_reads.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_read_accounting.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_read_accounting.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_read_closure.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_read_closure.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_read_kind.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_read_kind.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_readers.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_readers.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_shape_readers.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_shape_readers.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_skip_rule.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_skip_rule.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_support.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_support.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_support_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_support_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/metrics_support_report.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/metrics_support_report.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/naming.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/naming.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/no_bypass.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/no_bypass.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/observability.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/observability.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/pack.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/pack.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/pack_conformance.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/pack_conformance.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/plan.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/plan.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/policy_check.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/policy_check.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/policy_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/policy_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/promises.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/promises.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/reconciliation_store.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/reconciliation_store.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/release.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/release.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/release_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/release_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/release_floor_contract.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/release_floor_contract.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/request.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/request.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/request_doorbell.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/request_doorbell.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/request_projection.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/request_projection.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/request_reconcile.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/request_reconcile.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/responder.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/responder.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/restoration.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/restoration.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/runcmd.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/runcmd.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/runlog.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/runlog.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/runstatus.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/runstatus.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/secret_inventory.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/secret_inventory.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/secret_scan.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/secret_scan.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/secretref.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/secretref.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/security_review.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/security_review.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/shape_gate.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/shape_gate.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/shape_review.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/shape_review.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/sizing_pass.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/sizing_pass.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/spend.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/spend.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/status_server.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/status_server.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate_change.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate_change.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate_cost.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate_cost.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate_drift.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate_drift.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate_ephemeral.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate_ephemeral.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate_floor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate_floor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/substrate_promote.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/substrate_promote.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/supervisor.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/supervisor.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/supply_chain.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/supply_chain.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tasks.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tasks.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/toe_analogy.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/toe_analogy.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/toe_budget.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/toe_budget.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/toe_corpus.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/toe_corpus.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/toe_normalize.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/toe_normalize.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/toe_reconcile.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/toe_reconcile.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_adapter.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_adapter.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_bridge.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_bridge.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_conformance.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_conformance.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_intake.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_intake.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_jira_init.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_jira_init.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_jira_live.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_jira_live.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_mirror.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_mirror.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tracker_mirror_runner.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tracker_mirror_runner.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/tripwire.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/tripwire.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/two_key.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/two_key.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/untrusted_input.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/untrusted_input.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/validate.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/validate.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/validate_checks.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/validate_checks.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/verdict_corpus.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/verdict_corpus.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/version.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/version.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/work.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/work.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/work_state.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/work_state.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-.veldo/yamlish.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-.veldo/yamlish.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-proof/data.json` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-proof/data.json` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-scripts/check_gate_mutations.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-scripts/check_gate_mutations.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-scripts/check_review_mutations.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-scripts/check_review_mutations.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-scripts/check_teeth_mutations.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-scripts/check_teeth_mutations.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-scripts/suites/fixture.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-scripts/suites/fixture.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-scripts/suites/shared.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-scripts/suites/shared.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-scripts/suites/support/transitive.py` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-scripts/suites/support/transitive.py` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-case-definition` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-case-definition` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-interpreter` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-interpreter` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-history` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-history` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-schema` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-schema` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-fixture-version` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-fixture-version` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-addition` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-addition` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-deletion` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-deletion` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-mode` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-mode` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-runtime:implementation` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-runtime:implementation` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-runtime:executable` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-runtime:executable` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-runtime:cache_tag` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-runtime:cache_tag` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-runtime:runtime` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-runtime:runtime` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-runtime:host` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-runtime:host` | `gate/mutation-reuse-invalidates-per-input` |
| `omit-input-runtime:environment` | `gate/mutation-reuse-is-input-complete` |
| `reuse-stale-runtime:environment` | `gate/mutation-reuse-invalidates-per-input` |
| `ignore-file-bytes` | `gate/mutation-reuse-is-input-complete` |
| `discard-all-reusable-results` | `gate/mutation-reuse-invalidates-per-input` |

## Reproduction and landing

```sh
python3 -B proof/VELDO-0123/drive.py refutations --output /tmp/veldo-0123-refutations
python3 -B proof/VELDO-0123/drive.py removed-teeth --output /tmp/veldo-0123-assertions
bash scripts/verify.sh
git checkout -- .veldo/last_verify .veldo/events.jsonl
bash scripts/verify.sh
git checkout -- .veldo/last_verify .veldo/events.jsonl
```

Clear only this checkout's private `mutation-results/` directory before reproducing a cold gate. Do not import any file from this proof directory into it. The final evidence commit adds these observations after the tested implementation commit; it does not claim a gate stamp for the merged tree. The reviewer supplies that stamp. Gate byproducts are restored and excluded from all commits. A preliminary gate was deliberately stopped before completion to add malformed-cache and direct shell-wiring controls; it is not reported as a passing run. A second preliminary run found the Git boundary violation, which was fixed and directly checked before restarting the final clean pair.
