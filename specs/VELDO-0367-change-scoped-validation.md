---
schema: veldo.spec/v1
id: VELDO-0367
title: Run validation only for changed dependencies
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0205, VELDO-0206, VELDO-0208, VELDO-0358]
placement: [enforcement]
protected_paths:
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_changes.py
  - engine/scripts/gate_changes.py
  - scripts/gate_execution.py
  - engine/scripts/gate_execution.py
  - scripts/gate_weekly.py
  - engine/scripts/gate_weekly.py
  - scripts/gate_reuse.py
  - engine/scripts/gate_reuse.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/mutation_observer.py
  - engine/scripts/mutation_observer.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/mutation_reuse.py
  - engine/scripts/mutation_reuse.py
  - scripts/check_teeth_mutations.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/gate_host.py
  - engine/scripts/gate_host.py
  - scripts/gate_host.json
  - scripts/selftest.py
  - scripts/run_scope.py
  - scripts/check_first_use.py
  - scripts/suites/shared.py
  - scripts/reuse_stamp.py
  - engine/scripts/reuse_stamp.py
  - .veldo/reuse_evidence.py
  - engine/.veldo/reuse_evidence.py
  - .veldo/control_verification.py
  - engine/.veldo/control_verification.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
footprint:
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - scripts/suites/*.py
  - scripts/*.py
  - engine/scripts/*.py
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_host.json
  - scripts/suites/*0367*.py
  - scripts/suites/99_veldo_0205_reuse.py
  - scripts/suites/100_veldo_0207_case_reuse.py
  - scripts/suites/101_veldo_0208_landing_reuse.py
  - scripts/suites/157_veldo_0206_suite_reuse.py
  - scripts/suites/159_veldo_0218_reuse_audit.py
  - scripts/suites/shared.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - .veldo/reuse_evidence.py
  - engine/.veldo/reuse_evidence.py
  - .veldo/control_verification.py
  - engine/.veldo/control_verification.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
  - specs/VELDO-0367-change-scoped-validation.md
  - specs/index.md
  - proof/VELDO-0367/*
behavior_bearing: true
observability:
  logs: Name the baseline, changed paths, each selection reason, and weekly waiting reason.
  metrics: Executed, carried, unknown and invalidated counts by stage, suite and mutation case; measured elapsed time.
  traces: Authenticated item receipts link candidate, baseline, dependency record and original green result.
  error_taxonomy: Missing or incomplete evidence runs the item; failed execution stays red; busy hosts wait.
acceptance_criteria:
  - id: AC1
    text: >
      Baseline fixtures cover unchanged trees, additions, deletions, renames, mode changes,
      intervening red commits, divergent history and absent records. Each selection uses the
      last eligible green ancestor and accounts for every current catalog, suite and case identity.
    falsified_by: Use the previous commit after a red gate; the intervening-red fixture must fail.
  - id: AC2
    text: >
      Observer fixtures cover Python and child processes, both confinement legs, imports,
      directory discovery, missing files and lost events. Every executed item records its
      dependencies or an explicit unknown reason; a later successful run refreshes the set.
    falsified_by: Treat an incomplete trace as an empty set; the lost-events fixture must fail.
  - id: AC3
    text: >
      Mixed-inventory fixtures run every affected or unknown item and carry every other green
      result. Missing, duplicate, corrupt, revoked and wrong-source receipts cannot produce green.
      An unrelated edit and an unchanged rerun launch no workers for carried items.
      Fixtures cover prior killing rows, whole-suite fallback, survivors, shared suite controls
      and control carry. Landing accepts authenticated row kills and rejects incomplete row evidence.
    falsified_by: Replace a carried source commit with the candidate; the provenance fixture must fail.
  - id: AC4
    text: >
      Editing each reuse decision module selects its own tests through recorded dependencies.
      An unrelated item remains carried. No special gate-path rule invalidates the whole inventory.
    falsified_by: Add blanket invalidation for scripts/verify.sh; the unrelated-item fixture must fail.
  - id: AC5
    text: >
      Weekly fixtures cover two competing callers, busy and unobservable hosts, interruption,
      a second request within seven days, green refresh and red invalidation. No full run starts
      without exclusive idle-host admission, and no carried result survives an affected revocation.
    falsified_by: Release the host lock before descendants stop; the lock-custody fixture must fail.
  - id: AC6
    text: >
      The ordinary and candidate gate entries use the same selector and receipt validator.
      Small recorded inventories exercise every catalog state, suite leg and both mutation drivers.
      A partial diagnostic command still cannot issue a complete green stamp.
    falsified_by: Accept a receipt missing a catalog item; the complete-inventory fixture must fail.
required_evidence: [unit, integration]
rollback: Stop admission if selection or receipt integrity fails; repair with targeted tests. Any full recovery run obeys the weekly limit and exclusive-host rule.
---

## Intent

After a change, run only validation whose recorded dependencies changed. Carry the other
green results. Build this once in scripts/verify.sh and its Veldo modules. The myday scripts
call that gate until the factory takes over; the factory then calls the same gate.

Until VELDO-0367 is in place, owner order 43733 forbids all full gates. Validate each
change by hand through existing drivers: its targeted suites, mutation cases of the
modules it changed, and quick stages.

Owner orders: Telegram 43727 through 43731, 43733 and 43736, November 26, 2026.
This spec replaces conflicting reuse selection rules in VELDO-0205/0206/0207/0208/0217/0218/0222/0224/0226.
In particular, ordinary gates do not sample unchanged items for fresh audits. Weekly full
validation replaces those audits. There are no nightly full runs.

## The change and the dependency record

The candidate is a clean, immutable commit. The baseline is the nearest commit on its
first-parent history with an authenticated, complete green gate record for this repository.
Ignore red records and other histories. Pin both commits and the record digest.
Compare trees, including additions, deletions, rename endpoints, modes and symlink targets.
Neither the previous commit nor caller-supplied paths suffice. A changing checkout stays red.

Without an eligible baseline, all items are unknown. No green record has dependency
evidence today. The first gate is a full seed run. It is the first weekly run, once right
after increment 5 is enabled, with the same idle-host admission and seven-day limit.
Wait for admission without claiming green.
Old records cannot authorize carry; an isolated missing result later runs only that item.
If ordinary selection requires the entire inventory, it also uses full-run admission.

Inventory comes from every catalog slot in scripts/verify.sh, the scheduler's expanded
legs, scripts/suites/manifest.json and requires.json, and both mutation drivers' case
registries. Identity includes stage, leg, suite or driver and case name, as applicable.
Retain not-applicable and waived reasons; neither counts as a pass. Reconcile identities
each gate. Run new or changed definitions; mark removed identities without crediting them.
Give uncataloged validation its own identity.

Each item has a dependency record with fields `item_id`, `observed_commit`, `paths`,
`directories`, `absent_paths`, `runtime_digest`, `complete`, `unknown_reason` and
`record_digest`. Paths are relative to the repository. Include the item's definition,
mutation target, imported code, fixtures, configuration and helper files it reads.
Record symlink paths and resolved targets. Directory enumeration and failed lookups
must make newly added files selectable. Expand those observations into affected paths
when comparing trees. Runtime or environment changes mark only their consumers unknown;
unrecordable external inputs also mean unknown.

Extend VELDO-0358's observations in scripts/gate_legs.py, scripts/suites/shared.py and
scripts/mutation_observer.py beyond scripts/ and proof/. Trace all repository reads,
including native children, and attribute them to the executing item. Incomplete child
coverage, dropped events or ambiguous paths mean unknown, never an empty set.
Apply this to unconfined workers too; confinement alone does not decide reuse.

Record suite setup and prerequisites. Suites sharing required state name their group
and use its combined dependencies.
A mutation case records the union of baseline, no-op and mutant reads. A row-only run
retains the prior full-suite dependency set and adds new reads; only a complete suite
observation can replace that set. A parent stage records its children's dependencies
and its own setup reads. It dispatches only selected children; setup changes affect
children using it.
Integration fixtures and load-proof suites follow this rule too.

After successful execution and cleanup, atomically store results with dependencies.
Incomplete observations remain unknown. Carry preserves dependencies and source.
Only a complete green gate advances the baseline; failures cannot erase revocations.
Keep records in the authority's existing authenticated Store outside the checkout.
Index green gate records by repository and commit; reference immutable item records by digest.

## Selection and receipts

Run an item exactly when its dependencies intersect the changed paths, or its identity,
dependency set or usable green result is unknown. Missing, corrupt or revoked evidence
counts as unknown. Carry every other item's last green result referenced by the baseline.
No full-tree or commit hash in an item key may turn an unrelated edit into a miss.
Ordinary whole-repository checks may still run because they read the changed file.

Always perform inventory, selection and receipt assembly. The stamp names
`candidate_commit`, `baseline_commit`,
`baseline_record_digest`, `changed_paths_digest` and `inventory_digest`. Every item entry
names `item_id`, `status`, `dependency_record_digest`, `result_digest`, `source_commit`
and `source_gate_digest`. Status distinguishes executed, carried, failed, removed,
not-applicable and waived. Carry always references the original execution and authenticated
green result. Verify references and revocations before green. Executed and carried entries
cover the required inventory exactly once, with no failed or pending item.

Owner order 43736 adds two rules for ordinary selected mutations:

1. First run only the rows in that case's last authenticated `kills` list, with their
   required setup. If they no longer kill it, run the whole suite. Missing or unusable
   prior rows also require the whole suite. A survivor stays red; hangs and missing
   evidence cannot count as kills. Execute row bodies selectively, not just filter output.
2. Run baseline and no-op controls once per suite per gate, shared across its cases,
   not per module or case group. Carry the controls themselves when the suite dependency
   set is unchanged and its evidence remains eligible. Suite identity includes leg,
   runtime and fixture configuration, so sharing never crosses incompatible boundaries.
   Controls cover the suite's rows and all its cases' target wiring.

Version the result contract. A row kill names `execution_scope: rows`, exact `selected_rows`,
`observed_rows`, `kills` entries with `row` and `kill_by`, the prior kill receipt digest,
mutation digests and authenticated suite control references. A fallback names
`execution_scope: suite` and records both attempts. Landing verifies identities,
dependencies, provenance, passing controls and an actual target rejection. Require every
selected row exactly once, matching passing control rows; omitted unselected rows are
intentional. Full-suite results retain full inventory checks. Preserve confinement,
mutation-diff validation and failure evidence rules.

Gate machinery is ordinary dependency input. Changes rerun dependents, including its
own tests, without global invalidation. A selector bug can omit work, even its tests;
weekly full runs check for drift. Observed reads miss paths taken under other conditions.
This policy accepts that risk instead of requiring reviewed complete input declarations.

## Weekly full validation

Add scripts/verify.sh weekly with existing candidate and sink options. Execute every
required item and each mutant's whole suite from a clean checkout, with fresh build
outputs and no cache reads. Run controls once per suite. Publish fresh dependencies
and results, refreshing every source commit on green. Replace the force-fresh behavior
that suppresses publication.

The authority keeps `last_full_started_at` outside the checkout, shared across hosts
and worktrees for this repository. At most one full attempt starts in any rolling seven
days, including seed runs and failed attempts. Concurrent requests share one reservation.
A single authority atomically grants that reservation; if it is unreachable, callers wait.
Early requests wait; cancellation before starting consumes no slot. Legacy force-fresh and recovery entry points use this admission too.
Targeted repairs remain available.

Put admission in scripts/gate_host.py and new scripts/gate_weekly.py. Reserve the host
against new work, wait for existing work to finish, take the exclusive gate lock and
recheck idle status before starting. Idle means no other build, test, agent, container
job or user workload, including remote-run slots and work outside Veldo's scopes.
Inspect all users' processes and job scopes; low CPU use alone is insufficient.
Unobservable occupancy means wait. Record the allowed system services in gate_host.json.
All launchers on the enrolled host must honor the reservation; an unenrolled host waits
for enrollment. Existing myday launchers only request this Veldo admission.

Hold the reservation and lock through descendant cleanup and durable receipts.
If unrelated work appears, stop the run and keep it red. Never fall back to shared mode.
Waiting reports its reason and is cancelable. Weekly scheduling invokes this command;
it cannot create another gate or use occupied hosts.

A red weekly run opens one durable Veldo backlog ticket keyed by run ID, with the
commit, failed items, old results and fresh observations. Revoke affected results and
their dependents before releasing custody.
If the failure cannot be localized, revoke the entire affected stage; a broken observer
or inventory invalidates all results it could have misclassified. Unexecuted weekly
items remain unrefreshed. Persist revocations even if ticket creation needs retry, and
keep a durable pending ticket request. Later gates must execute revoked items. Repair
does not start another full run before the seven-day limit.

## Existing pieces and build order

Keep VELDO-0205's Store in scripts/gate_reuse.py and result validation in
scripts/mutation_reuse.py; replace whole-tree qualification with dependency records.
Production uses scripts/case_reuse.py Session through
scripts/check_gate_mutations.py; changing mutation_reuse_profiles.json alone does nothing.
Retire profile and reviewed-declaration eligibility, blanket authority invalidation and
ordinary audit sampling from this path. Preserve old records as historical evidence.

Extend VELDO-0206 in scripts/run_scope.py and scripts/selftest.py. Replace the empty
SUITE_REUSE registry with automatic observations, and apply it inside
scripts/check_first_use.py. Keep VELDO-0208's worker separation, confinement, authenticated
store and landing verification. Update scripts/reuse_stamp.py, .veldo/reuse_evidence.py
and .veldo/control_verification.py to validate carried evidence. Unconfined items become
eligible when observation is complete. The factory consumes the same receipt contract.

Each increment lands independently with focused fixtures only, never a full gate.
Keep selection and both mutation speed rules inactive until increment 5. In this list, a
script pair means scripts/name and engine/scripts/name. A .veldo pair means .veldo/name
and engine/.veldo/name. Every named path below is protected or becomes protected in
increment 1. Suite fixtures, mutation registrations and their manifests accompany the
relevant increment; they are not protected paths under the current policy.

1. Add the dependency and receipt schema, baseline lookup and inventory fixtures.
   Protected: new gate_changes.py pair, gate_reuse.py pair and .veldo/policy.yaml pair.
   Protect both new modules, including the reserved gate_weekly.py pair.
2. Record complete reads without changing selection. Protected: gate_legs.py,
   mutation_observer.py and reuse_worker.py pairs; scripts/suites/shared.py.
3. Add selection, carried receipts, prior-killing-row execution with whole-suite fallback,
   and once-per-suite controls with dependency-based carry behind the inactive switch.
   Update landing validation and retire conflicting assertions with focused fixtures. Protected:
   gate_changes.py, case_reuse.py, mutation_reuse.py, check_gate_mutations.py,
   gate_schedule.py and reuse_stamp.py pairs; .veldo/reuse_evidence.py pair;
   scripts/selftest.py, scripts/run_scope.py, scripts/check_first_use.py and
   scripts/check_teeth_mutations.py.
4. Add weekly admission, refresh, revocation and ticket persistence. Protected:
   gate_weekly.py, gate_host.py, gate_reuse.py and verify.sh pairs; scripts/gate_host.json.
   Prove waiting and lock custody with controlled competing processes on pc2.
5. Enable the common gate path and update landing consumers. Protected: verify.sh and
   reuse_stamp.py pairs; .veldo/control_verification.py and .veldo/reuse_evidence.py pairs.
   Prove dependency edits and unrelated carries with focused fixtures. Once enabled,
   request the one seed as the first weekly run, waiting for idle-host admission.

Increment 3 replaces check_gate_mutations.py's `validate_result` assertion that every
baseline row appears in every mutant and every declared target runs. Retire its
whole-suite-only `in_leg` premise and `control_group` per-module/fixture grouping.
In case_reuse.py, retire `TRACED_RUNS` and `failed_condition` requirements for two
per-case baselines, equal baseline reads and complete gate observations as eligibility
conditions. Replace check_teeth_mutations.py's `worker` whole-suite execution and
all-target observation contract; update registrations and fixtures tied to those
assertions, including `case-deadlines/shared-controls`. Preserve checks for failed
controls, target rejection and confinement under the new scopes.

## Expected time and review scope

Gate 22 for cand-1122, now main fc3f7c3af (owner 43740), took 13,718 seconds for
mutation. Its receipt is the admissions JSON line in myday research/gate-stamps/
cand-1122-55b511908-verify.log. Mutants used 117,344 worker seconds across 4,023 cases,
29.2 seconds per case. The 736 baseline and 736 no-op runs added 48,070 worker seconds.
The 3.4 seconds from stage elapsed divided by cases is throughput, not case cost.

Measured concurrency was 7.80 busy CPU cores and 12.06 active workers, including waits.
The latter is total worker elapsed divided by stage elapsed.
For selected cases, sum their suite-specific worker seconds, add uncarried suite controls
once, and divide by expected active workers. Respect the longest case, control-before-mutant
ordering, resource limits and setup time. CPU cores and elapsed workers are different units;
small selections may not reach the measured concurrency.

A typical planning example selects 20 to 50 cases costing the measured mean and two
suites whose controls cost 30 seconds each. That is 584 to 1,460 mutant seconds plus
120 control seconds. At eight to 12 active workers, mutants need 49 to 183 seconds;
controls add about 30 to 60 seconds before mutants. Allowing 90 to 120 seconds for
suite checks and 30 to 60 for bookkeeping gives about 3 to 7 minutes without long tails.
These are planning assumptions, not measured selected runs.

A bad case touches 124_veldo_0131_factory_reads_commands: nine mutants used 5,887 seconds,
654 each, with a 671-second maximum. Whole-suite fallback cannot finish below that tail.
At eight workers, two waves take about 22 minutes, plus roughly 1 to 2 minutes for one
control pair, before other stages. Its historical controls took about 54 to 65 seconds
each. Long suites, setup and fallback dominate, even with few selected cases. Prior-row
kills and carried controls can reduce this cost, but row timings are not measured yet.
Report selected worker seconds, concurrency, fallback counts and actual wall time.

myday research/claude-runs/veldo-speed-analysis.md section 2 explains the older
3,978-case zero-reuse run: 2,813 unknown_closure, 1,146 unconfined_leg and 19
unreviewed_declaration. Gate edits invalidated every key. Its pc2 and integration notes
are bounded evidence, not a completed green timing benchmark.

Review normal clean candidates, missing evidence, host contention and accidental stale
results. Deliberate forgery by the owner's account is outside this spec's threat model;
existing worker and signing boundaries remain. This revision changes only the spec.
Implementation, host enrollment and scheduling come later. Skip tests here or use pc2
through myday/scripts/remote_run.sh; pc1 receives no test workload.
