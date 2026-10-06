# VELDO-0205 local qualification

Implementation commit: 07ce3299fc1cf02341a60e24cb1a2caef8ad56e3.
This is a local test report, not a full-gate proof manifest or a landing claim.
Both specifications remain ready. VELDO-0206 is intentionally unimplemented.

## Result and limitation

Mutation reuse infrastructure is implemented: content keys, authenticated external records,
atomic publication, conservative closure admission, coordinator integration for both registry
owners, fresh/reused counts and per-case keys, and a force-fresh control. Only complete validated
kills can be stored or read. Unknown closures, missing records and bad authentication run fresh.

No production closure has been qualified. All 2,494 registered production cases still execute
fresh. The empty profile registry is intentional: the working tree alone does not account for
services, tools, interpreter libraries and other host inputs. There is no claimed gate speedup.
Qualifying production closures is required before the infrastructure saves mutation execution time.

## Tests actually run

Only the new suite was run, sequentially and in the foreground:

`python3 scripts/selftest.py --suite 98_veldo_0205_reuse`

The final run reports 47 passed and 0 failed, including the shared preamble and 21 new checks,
in 0.79 seconds. Earlier iterations reported 41, 42 and 44 passed, each with 0 failed.
The 42-assertion run also set VELDO_REUSE_MEASURE=1 for the single measurement below.
The dispatcher deliberately marks every selected suite as partial and refuses a verified claim.
No whole selftest, mutation driver executable, mutation stage, full gate or fan-out was run.
Coordinator tests use controlled workers; they launch no mutation processes. A compatibility test
executes the old fixture constructor and its small Git setup, but never executes its gate.

| Criterion | Local behavioral evidence |
| --- | --- |
| AC1 | reuse/exact-closure changes every repository file's content and mode, adds and deletes files, changes case, head, config, environment, interpreter and tool identities, and tests runtime tree additions and symlink identity. Omitting content hashing is a driven negative control. |
| AC2 | reuse/authenticated-kills drives missing, edited, truncated, wrongly keyed, recomputed-checksum and signed-but-invalid records, bad baselines, survivors and timeouts. Bypassing authentication is a driven negative control. Store errors and repository-local stores cannot produce hits. |
| AC3 | reuse/receipt-counts and reuse/mixed-counts check both drivers with cold, warm and mixed receipts; reuse/stale-cannot-pass and reuse/changed-input-cannot-pass prove fresh survivors stay red. Setup failures, worker crashes, input races and counting regressions are driven. |
| AC4 | reuse/fresh-policy tests the environment switch and explicit coordinator argument, bypassing reads and writes. Ignoring force fresh is a driven negative control. Gate wiring remains required and deadline exceptions remain red. |

The tests also validate both new spec contracts and both drivers' exact registry definition checks.
Syntax compilation and git diff whitespace checks passed. Existing suite 53's fixture constructor
now copies the two helper dependencies; its full qualification is reserved for the reviewer.

## Single key-pass cost

0.546442 seconds over 5,573 files, 80,148,189 bytes and 2,494 cases, on Python 3.12.3.
See key-measurement.json for the captured input digest and interpreter string. This was one pass,
with no fan-out, during implementation before the final receipt/error refinements. It includes
repository input reads, registry enumeration, repository hashing and admission of all cases.
There were zero qualified runtime profiles, hence zero reusable keys. External runtime hashing
and a genuine warm production gate remain unmeasured; this number must not be sold as their cost.

## Use and profile review

The default store is $XDG_CACHE_HOME/veldo/gate-reuse-v1, falling back to ~/.cache/veldo/gate-reuse-v1.
VELDO_GATE_CACHE can select another private directory outside this repository. Records are
append-only and authenticated with a separate private local key. An unreadable or corrupt store
is a miss. Editing a record and its unkeyed checksum cannot authorize reuse. An attacker with both
the signing key and execution as the owner is outside this local-store boundary.

Set VELDO_GATE_FORCE_FRESH=1 for canonical landing and release gates. Development gates may reuse
qualified cases. Standalone driver commands remain fresh; the shared coordinator owns reuse.
The suite stage is still entirely fresh pending VELDO-0206.

Profiles live in scripts/mutation_reuse_profiles.json, keyed by exact driver:case identity.
Each requires tree_digest from qualification_digest, case_digest of the complete case definition,
absolute runtime_paths covering every external file tree and tool dependency, non_file_inputs set
to none, and a reviewed rationale proving that variable host state cannot affect the observations.
The profile file is excluded only from its own qualification digest to avoid self-reference; it
is included in every result key. Every other snapshot file is pinned. A changed file invalidates
the qualification. Runtime paths must include the resolved interpreter; symlinks include link text and resolved target identity; special files
are refused. The declaration must include dynamic libraries, import paths, tool configuration and
all other dependencies, not merely the interpreter executable. A profile is a reviewed contract,
not an automatically inferred read trace. Do not fill the empty registry without that review.

Executed means launched fresh mutant attempts, including a worker that fails. Reused means a
validated cache hit. Rejected counts validated killed-case records. Each case receipt records
its key, source, reason and validation state; pending cases have no execution claim. Baseline and
no-op jobs remain separately counted in worker_invocations. This preserves honest failed receipts.

## Still required before landing

- Qualify production closures if actual reuse savings are required from this first slice.
- Run the owner's fresh full gate after the other checkout finishes, using VELDO_GATE_FORCE_FRESH=1.
- Prove the real full mutation inventories, timing limits, cleanup, existing suite 53 qualifications,
  generated/template checks and all other required gate stages on the merged result.
- Obtain independent review and exact commit/proof-bound owner approval for scripts/verify.sh.
- Produce the real full-gate proof manifest and checkout stamp from that verification.

Telegram 31900 approves the design in Telegram 31622 and reverses Telegram 28800's earlier reuse
removal. It is not represented here as approval of an implementation commit. Nothing was pushed,
merged, self-approved or changed in another worktree. Gate byproducts are excluded from commits.

## Part A review repair, 2026-10-06

Suite 98: 54 passed, zero failed (1.52 seconds). This is partial local evidence,
not a gate pass. Direct tests invoke the real fleet judge, the real shell guard
(with Python optimization enabled), the stamp receipt reducer, and a Landlock
child with a descendant process. Reused stamps/events are rejected; worker and
child reads and writes of a known coordinator key path are denied. Colliding
record contents poison that key and issue an integrity warning. Runtime admission
requires stdlib, git and shell coverage; force-fresh parsing rejects unknown values.
Only worker environment values participate in the key. Bash syntax checks passed.
The protected-path amendment requires owner approval of the final commit and proof.
Linux Landlock ABI 3 is required; no unsandboxed fallback. The coordinator account
and kernel remain trusted, as specified in the amended contract.
