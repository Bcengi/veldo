# VELDO-0207 local build report

This is targeted local evidence, not a gate pass, approval, proof manifest or landing stamp.
The specifications remain ready. No push, merge, full selftest, full mutation stage or gate
was run. All case probes were sequential, in the foreground, with temporary files removed.

## Commits and scope

- a9ec0561: Part A, fresh-only landing enforcement in stamps/events, fleet judge and guard;
  collision poisoning; worker isolation; protected paths; runtime and force-fresh admission.
- 72b675dd: Part A, fresh fixture compatibility roots and corresponding cache placement refusal.
- 5dd7063f: Part A, synchronize the Claude pack's concrete guard with the engine.
- The commit containing this report is Part B: VELDO-0207, per-case keys, declared snapshots,
  runtime enforcement, tracing proposer, production proposals and suite 99. Its exact identity
  can be obtained with `git log -1 --format=%H -- proof/VELDO-0207/README.md`.

Part B replaces production admission of the old whole-tree profiles. HEAD and unrelated
repository content no longer enter a qualified case key. The key contains declared bytes and
modes, the case's own registry entry, projected worker code, declaration, fixed worker environment
and that driver's runtime identity. A deterministic AST projection removes registry construction
and retains executable worker code. Its implementation is itself a mandatory input.

Each qualified fresh case receives its own snapshot with only declared files and projected
drivers, no Git history and no link to the original checkout. Baseline and no-op controls are
scoped to that case's snapshot. Snapshots are built at launch and removed at completion or
failure, bounding disk use by active workers; worker projection and content hashes are memoized
within the coordinator. Landlock is inherited by descendants. A coordinator-owned strace
log, outside writable worker scratch, makes an undeclared file or metadata probe fail even when the suite catches
the error or a child attempts the read. Successful startup reads are also checked against the
runtime closure; site initialization is disabled and coordinator CPU discovery is skipped in
these workers. Already mapped native libraries, including libc and the loader, must be keyed.
The authenticated store, complete-result validator, force-fresh behavior and honest receipts
are retained. Conflicting publications also appear in the receipt's reuse_integrity_errors.

## Measurement before narrowing

The initial 30-case measurement completed before per-case implementation. It immediately exposed
legacy sandbox incompatibilities: only three clean baselines, source-file fan-in min 20, median 24,
max 363, in 16.564 seconds. These console-summary values are preserved in
initial-measurement-summary.json; its detailed aggregate was overwritten by the rerun below.

`fan-in.json` records the subsequent 30 single baseline traces: 25 teeth cases plus all five review cases,
covering 28 suites and 20 modules. Python open audit plus descendant `strace -f -e trace=file -yy`
measured actual dynamic reads; no static import graph was used. `measure.py` preserves the
recipe and replays the recorded case identities. Run it from the repository root. The retained
measurement took 194.622 seconds, including tracing overhead, during development and compatibility repairs, before the final
per-case refinements. It was not a fixed-revision qualification run. It is not a timing measurement of the final gate.

| Observation | Result |
| --- | --- |
| Repository source files per case | min 21, median 240.5, max 502 |
| Distinct repository files observed | 1,074 |
| Inputs seen in all 30 cases | 19, listed in summary.json |
| Median reach of a sampled production module | 18 of 30 cases |
| Clean baselines | 9 |
| Worker errors / completed baselines with failing assertions | 9 / 12 |

The common floor includes the shared preamble, validator, policy, Git helper and their dynamically
loaded modules. Several fixtures copy entire module directories, so a small test can read hundreds
of files. Failed traces are lower bounds, never qualified closures. Errors include host-service
requirements, runtime-directory access and Git operations against the original worktree. Some
runtime-directory restrictions were subsequently repaired; those observations are not relabeled
as successful. A full production qualification remains required.

`subset-traces.json` subsequently records baseline, no-op and mutant runs for two small production
cases, check_teeth_mutations.py:command-only and check_review_mutations.py:14. Both clean controls
passed; their mutants produced failed assertions. These are actual production worker observations,
not a full-stage pass. Conservative directory expansion in the proposer produces 407 and 408
repository-file proposals for these examples. That expansion is intentionally broader than direct
open counts and will reduce the potential reuse benefit unless reviewed declarations are narrowed.

## Savings estimate and present behavior

The original open-only traces support about 10% time-weighted savings as an optimistic
upper bound for single-module edits, before keying and lookup costs. They have 21 of 30
unclean baselines and 19 core files read by every case (including validate.py and policy.yaml).
They are not a measured gate speedup: failed observations, tracer overhead, different mutant
costs, metadata probes and conservative directory declarations all limit extrapolation.
Churn in shared inputs dominates reuse economics. Part C permits authenticated landing reuse;
an explicit force-fresh run still saves zero. Specs/docs/proof edits can reuse only qualified
cases whose declarations exclude those changed files. Changes to a universal shared file
invalidate every case.

Enabled production savings in this branch are ZERO. All 30 committed declarations are proposals
with reviewed false, not fabricated qualifications. Twenty-eight carry baseline-only proposals;
the two named examples carry all-three-mode proposals. The generator is ready for sequential
full-registry tracing. Cases with services, clocks, entropy or repository-history dependencies
remain fresh until an enforceable closure and non-file rationale exist. An observed trace alone
cannot establish that rationale, and no implementation approval is inferred from these files.

## Tests and boundaries

Only the specifications' own suites ran, one at a time:

- `python3 scripts/selftest.py --suite 98_veldo_0205_reuse`
- `python3 scripts/selftest.py --suite 99_veldo_0207_case_reuse`

Final counts and input hashes are in local-tests.json. Suite 98 covers real landing policy and
shell-guard invocation, stamp fields, truthy parsing, runtime admission, symlinks, collisions and
worker/child denial of the store key. Suite 99 covers selective invalidation, another driver's
unchanged toolchain, unrelated HEAD/content, signed stale and tampered records, force fresh,
controlled cold/warm/mixed coordinator receipts and real traced single-worker execution. Its real
baseline/no-op/mutant fixture is validated, authenticated, published and read back. Caught Python
and descendant undeclared reads fail; an actual read before sandbox installation is also refused.

Python compilation, Bash syntax, whitespace and canonical-copy comparisons are targeted checks,
not substitutions for the gate. Existing suite 53's fixture dependencies and exact catalog text
were updated for the new helpers/receipt; its qualification was not run here. The derived suite
closure and spec index were regenerated; the static crossing-state report was unchanged.

Linux Landlock ABI 3 and strace are required for reusable workers, with no unsandboxed fallback.
The kernel, tracer and coordinator account remain trusted. An arbitrary hostile same-uid process
outside confinement can still read the HMAC key. Fresh legacy workers need broader system roots
for existing fixtures; declared reusable workers receive only their runtime profile and private
scratch. Complete host-service compatibility still needs the owner's fresh gate.

## Remaining owner/reviewer work after veldo-gate-0204h finishes

1. Generate full proposals sequentially, with no fan-out:

   `python3 scripts/propose_case_inputs.py --all --output scripts/mutation_case_inputs.json --report proof/VELDO-0207/full-proposals.json > /tmp/veldo-case-proposals.log 2>&1`

   A smaller follow-up can use repeated `--case DRIVER:NAME` instead. The generator writes proposals
   only and resets their review flags. Review all-mode observations, actual runtime/tool paths,
   repository-history and non-file dependencies. Narrow conservative directory expansions only
   with a defensible closure. Set reviewed true on a case and its toolchain only after qualification,
   with non_file_inputs none and an explicit rationale. Unqualified cases should stay fresh.
2. Run the fresh full gate on the candidate/merged tree in the reviewer's checkout:

   `VELDO_GATE_FORCE_FRESH=1 ./scripts/verify.sh > /tmp/veldo-fresh-gate.log 2>&1`

   This must include full registry coverage, timing/cleanup, existing mutation qualifications,
   generated/template/pack checks and all other gate stages. Resolve any failing lines there.
3. Obtain independent review and exact commit/proof-bound owner approval for the protected policy,
   landing, coordinator, key, declaration and sandbox paths. Produce the real proof manifest and
   landing stamp from the checkout that verified the merged tree. No stamp/event byproducts from
   this development checkout belong in its implementation commits. Remove the owner's temporary
   logs after retaining the required proof.

## Independent-review correction follow-up

See [the review correction report](../VELDO-0207/review-fixes.md) for the fixes, planted-defect
tests, full-call-family measurement, savings assessment and deployment limits.
