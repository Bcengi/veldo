---
schema: veldo.spec/v1
id: VELDO-0368
title: Enforce a recorded read set for each confined validation item
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0367, VELDO-0217, VELDO-0210, VELDO-0208]
placement: [enforcement]
protected_paths:
  - scripts/agent_sandbox.py
  - engine/scripts/agent_sandbox.py
  - scripts/confined_inputs.py
  - engine/scripts/confined_inputs.py
  - scripts/mutation_sandbox.py
  - engine/scripts/mutation_sandbox.py
  - scripts/case_inputs.py
  - engine/scripts/case_inputs.py
  - scripts/veldo_userns.c
  - engine/scripts/veldo_userns.c
  - scripts/veldo-userns.apparmor
  - engine/scripts/veldo-userns.apparmor
  - scripts/selftest.py
  - scripts/mutation_case_inputs.json
  - proof/VELDO-0217/reviews/*
  - scripts/mutation_observer.py
  - engine/scripts/mutation_observer.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/gate_changes.py
  - engine/scripts/gate_changes.py
  - scripts/gate_execution.py
  - engine/scripts/gate_execution.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/suites/shared.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
footprint:
  - scripts/agent_sandbox.py
  - engine/scripts/agent_sandbox.py
  - scripts/confined_inputs.py
  - engine/scripts/confined_inputs.py
  - scripts/mutation_sandbox.py
  - engine/scripts/mutation_sandbox.py
  - scripts/case_inputs.py
  - engine/scripts/case_inputs.py
  - scripts/veldo_userns.c
  - engine/scripts/veldo_userns.c
  - scripts/veldo-userns.apparmor
  - engine/scripts/veldo-userns.apparmor
  - scripts/selftest.py
  - scripts/mutation_case_inputs.json
  - proof/VELDO-0217/reviews/*
  - scripts/mutation_observer.py
  - engine/scripts/mutation_observer.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/gate_changes.py
  - engine/scripts/gate_changes.py
  - scripts/gate_execution.py
  - engine/scripts/gate_execution.py
  - scripts/suites/shared.py
  - scripts/suites/*0368*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - scripts/check_teeth_mutations.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - specs/VELDO-0368-confined-read-observation.md
  - proof/VELDO-0368/*
behavior_bearing: true
observability:
  logs: Name the item, mode, read-set digest, applied ruleset, coverage reason and reported permission failure.
  metrics: Count narrowed items, declaration failures and unknown items; measure setup time and eligible worker seconds.
  traces: The authority binds the applied grants and repository view to the dependency record and completed process tree.
  error_taxonomy: Missing evidence runs fresh; denied required inputs fail; broad or unapplied grants cannot authorize carry.
acceptance_criteria:
  - id: AC1
    text: >
      A native reader launched through worker_tree reads its allowed file and receives
      EACCES for an existing undeclared file, including after starting a watchdog and
      child processes. TracerPid is zero. Existing write, IPC and traced-launch denials hold.
      Exercise both script copies with focused fixtures.
    falsified_by: Add the repository root to the narrowed grants; the undeclared-read fixture must fail.
  - id: AC2
    text: >
      The resolver combines declarations, Python imports, prerequisites and explicit fixture
      directories. It records their sources and changes the item identity when any source
      or grant changes. Unresolved imports cannot trigger a broader runtime retry.
    falsified_by: Retry a missing import with its parent directory granted; the fixed-grants fixture must fail.
  - id: AC3
    text: >
      File and directory grants cover names, contents, types, modes and symlink targets.
      Adding, deleting, renaming or changing a descendant selects a directory consumer.
      Adding a file that changes import resolution also selects its consumer.
    falsified_by: Hash directory names without descendant bytes; the edited-data fixture must fail.
  - id: AC4
    text: >
      A worker, suite and mutation case each enter their recorded domain before candidate
      code or threads run. Baseline, no-op and mutant evidence covers the same case policy.
      Shared controls require matching grants, runtime, fixture state and prerequisites.
    falsified_by: Reuse a baseline from a broader domain; the control-policy fixture must fail.
  - id: AC5
    text: >
      The trusted runner closes unaccounted descriptors and removes checkout aliases from
      the certifiable filesystem view. Metadata-only probes, inherited file reads and
      symlink escapes cannot depend on undeclared repository state.
    falsified_by: Leave the original checkout visible to stat; the hidden-metadata fixture must fail certification.
  - id: AC6
    text: >
      Only the authority certifies successful ruleset installation on the exact launch.
      A missing, failed, stale or skipped installation, an extra grant, a forged worker
      complete flag or an incomplete process cleanup withholds complete coverage.
    falsified_by: Issue the certificate without calling landlock_restrict_self; the unapplied-domain fixture must fail.
  - id: AC7
    text: >
      A surfaced EACCES names the item, mode, policy digest and available path information.
      The item fails without a wider retry or a replacement green result. A caught denial
      does not enlarge the recorded set. Fixes use a new declaration and a fresh execution.
    falsified_by: Convert a permission failure to a broad successful retry; the denied-input fixture must fail.
  - id: AC8
    text: >
      Interpreter, toolchain and system inputs belong to the runtime digest. A runtime
      directory cannot hide repository files or external mutable inputs. Nested tracing,
      whole-repository grants and unaccounted host inputs stay unknown.
    falsified_by: Label an authority checkout as a runtime directory; the repository-alias fixture must fail.
  - id: AC9
    text: >
      VELDO-0367 carries a certified item after an unrelated edit and selects it after an
      input, directory descendant, runtime or read-set change. A row-only run retains the
      prior full-suite dependencies. Missing certificates never become empty dependencies.
    falsified_by: Compare only file bytes and ignore a changed read-set digest; the changed-grant fixture must fail.
  - id: AC10
    text: >
      Measurements reconcile the historical case and control inventory, distinguish import
      proposals from successful narrowed executions, and report setup cost from fresh
      processes on pc1. Evidence includes raw samples and source digests. No full gate runs.
    falsified_by: Count generated import candidates as certified runs; the eligibility-accounting fixture must fail.
required_evidence: [unit, integration]
rollback: Disable certification and retain unknown dependency records. Preserve confinement. Fix with focused fixtures only.
---

## Intent

Give each confined validation item an explicit read set and enforce it with Landlock.
Record everything the item is allowed to read as its dependencies. This is an
over-approximation: an allowed file counts even if the item never opens it. When
those inputs and the read set are unchanged, VELDO-0367 can carry the result.
An attempted read of an existing file denied by the ruleset receives EACCES. The runner never widens
the set to make a failing item pass.

This replaces the proposed file-observation listener. Keep the existing IPC broker,
write restrictions, namespace launcher and VELDO-0210 AC7 traced-worker refusal.
The design adds neither a tracer nor file syscall notifications. Threads inherit
restrictions installed before their creation, so the mandatory watchdog is compatible.
The owner rule is unchanged: no full gates, only fixtures for the changed behavior.

Landlock alone does not prove that every dependency is inside the read set. It does
not restrict metadata queries such as stat and access, and an already-open file
can retain access after restriction. These limits are documented in the
[kernel Landlock API](https://docs.kernel.org/userspace-api/landlock.html).
Certification therefore also requires a filesystem view that exposes only the
selected repository inputs and a clean descriptor handoff. A narrowed ruleset on
the existing visible checkout is useful enforcement, but stays `complete=false`
until these requirements hold. This draft specifies that completion condition.

## Where the read set comes from

The authority builds an immutable input plan for each item before launch. It names
exact repository files, recursive directory grants, expected absent paths, runtime
roots, private output roots and the source of each grant. It also binds the item
identity, prerequisite group, generator version and normalized plan digest.
Candidate code cannot submit an authoritative plan through environment variables,
stdout or files in its scratch directory.

Use `scripts/mutation_case_inputs.json` and VELDO-0217's reviewed-declaration
machinery where available. Preserve the protected review path and exact
`review_sha256` binding. An unreviewed or stale declaration can seed a proposal;
it cannot pretend to be an approved grant. Keep the existing rules for legacy
VELDO-0217 reuse. This extension does not turn an import scan into a review or
relax that mechanism's sensitivity and non-file checks.

For other items, generate the Python import closure, meaning the set of repository
modules reachable through their imports. Seed it with the entry point, shared
preamble, suite prerequisites, case projection, mutation target and authority
bootstrap inputs. Resolve ordinary and relative imports against the fixed import
search path. Include package initializers and literal file-location loads. Repeat
until no new module appears. Recognize reviewed loader helpers with finite literal
arguments. Preserve namespace-package search locations and the paths whose absence
chose one module over another. Disable unkeyed bytecode caches and user site imports.
Repository extension modules are repository inputs; installed extensions belong to
the runtime digest.

A computed module name, plugin scan, eval or subprocess command may require an
explicit declaration. The generator reports the unresolved expression and its source
location. It does not infer completeness from one successful execution. It may emit
a proposal that will fail when an undeclared import is attempted. Review and fresh
execution decide whether that proposal is usable. A fixture directory is never an
automatic fallback for unresolved code.

Static analysis need not prove that every possible branch can import successfully.
A run can earn coverage when its fixed domain is enforced and its other certificate
conditions hold, even if some dormant imports remain unresolved. Any executed read
still stays within that domain. Qualification must establish that the narrowed run
produces the expected observations; a missing required input cannot be excused as
a successful coverage check.

Declare fixture and data directories separately. Existing `case_inputs.selected`
and `case_inputs.freeze` provide the starting point for expanding and copying
declared inputs. Preserve the case's projected driver rather than importing the
entire mutation registry into every case dependency. A directory used to build a
fixture includes every source file that can be copied, including engine templates,
configuration, shell scripts and support data. Record setup inputs even when the
worker later reads only their generated copies. Inputs produced solely by the
item in empty private scratch need no repository path of their own.

The interpreter, loader, standard library, installed tools, system configuration and
locale data belong to `runtime_digest`. Bind their actual immutable contents or a
verified image digest, fixed environment and resolver configuration. A broad `/usr`
or `/etc` grant means the digest covers that entire allowed input tree, including
membership and symlink targets. A version string or executable timestamp is not
enough. Reuse the digest across items consuming the same immutable runtime.
Repository files cannot become runtime inputs by copying them into a tool directory
or granting an authority checkout under a different name.

Keep `/proc`, devices, services and shared caches distinct from immutable runtime
files. Today's automatic `/proc` grant does not become a stable runtime digest.
The trusted runner may use process identity for cleanup, but an item's unaccounted
host-state dependency keeps it unknown. Preserve VELDO-0367's treatment of external
inputs. This spec does not claim that Landlock removes clock, randomness or service
dependencies, or change VELDO-0367's accepted limit on validating the validator.

## Apply the plan to the item that runs

Build the plan and freeze its inputs outside candidate execution. Resolve symlinks
without permitting an ancestor of a forbidden root. Pin the files used to build the
ruleset so a rename cannot replace them between hashing and grant installation.
Build the repository view from the pinned commit, with untracked checkout files
absent, and keep it immutable for the run. Hashing a live writable checkout
before launch does not certify later bytes read from it.

At the existing trusted bootstrap, install a read layer that handles `READ_FILE`,
`READ_DIR` and `EXECUTE`, with only the plan's repository and runtime grants.
Stacking this layer intersects it with the existing domain, so old write and IPC
restrictions continue to apply. An alternative implementation may replace the
existing read grants in the initial ruleset, provided it proves the same rights.
In either form, check every ruleset creation, rule addition and restriction result.
Never continue candidate execution after an installation failure.

Apply the layer while the child is single-threaded, before the Python watchdog,
shared preamble, imports or candidate code run. Future threads and descendants stay
inside it. A long-lived worker cannot narrow itself for item A and then widen for
item B. Fork a fresh trusted child for each distinct item policy. Thread count after
installation is not an exclusion. Installing only on one thread of an already
running item cannot earn a certificate.

* A worker gets its exact item plan, private scratch and recorded runtime. A
  launcher that reads candidate files before restriction must record those setup
  inputs in the plan or keep the item unknown.
* A suite gets its own plan plus the shared preamble and prerequisite closure.
  Suites that exchange state run as a group under their union. A suite dispatcher
  can retain its outer domain, but each child receives the narrowed domain before
  its setup. Do not certify individual suites from a leg-wide union that grants
  the whole repository.
* A mutation case uses the union required by its baseline, no-op and mutant. Generate imports
  for every projected mode, including code introduced by the mutation. Apply the
  same normalized grant plan to each mode in a separate process. Bind each
  mode's input contents, the projected case and mutation digest. Controls can be
  shared only when the grant plan, prerequisite group, runtime and fixture state
  match. Otherwise run focused controls for that case. The final dependency record
  contains the union of the three modes and their setup inputs.

A row-only mutation run retains the previous full-suite dependencies and adds its
current grant set. It cannot shrink the suite record. Parent stages add their own
setup dependencies to the union of their children, as VELDO-0367 requires.

## Make the filesystem view match the claim

A projected repository is a private tree containing only the selected files and
expanded data directories. Metadata queries in that tree can reveal only those
inputs and its fixed layout. Reuse the declared snapshot builder, then give the
item a namespace view in which the original checkout, authority checkout, Git
objects and host-path aliases are absent. A private tree at a different cwd is
insufficient if the original paths are still visible to stat.

The existing namespace helper must establish that view before it drops privileges.
Keep its existing capability drop, namespace checks and traced-entry refusal.
The installed helper profile currently permits only making mounts private and
mounting procfs. It cannot construct this view. A separate protected launcher
increment must define the managed view layout and authorize only its required
mount and root-switch operations inside the private namespace. Keep the child
profile's mount, capability and tracing denials. Add no host capability or
privileged observation service. Focused escape fixtures must prove that the helper
cannot expose extra host paths or leave the old root reachable. Certification
stays disabled until that increment is reviewed and implemented; AC7 stays intact.

Account for metadata that the view exposes: file type, permissions, size, link text,
normalized timestamps and the directory layout. Normalize inode and ownership
behavior where possible; otherwise treat a result that relies on unrecorded host
metadata as unknown. An omitted repository path has fixed absence in this view.
Omitted files can produce ENOENT rather than EACCES. Required imports and data
loads must report either error as a missing declaration; expected absence remains
a valid fixed input. Import search candidates and explicit absent declarations
still enter `absent_paths`
so a newly added input selects the item and regenerates its plan.

Close inherited file and directory descriptors except reviewed authority channels
and standard streams with known sources. An input on stdin must be recorded too.
Start a fresh executable after removing unaccounted mappings and handles. The
bootstrap's interpreter and loaded authority modules must already be in the plan's
repository or runtime inputs. Prevent descriptor transfer from outside the item
through the existing broker. Restrict process-root, cwd and fd aliases through
`/proc` in the certifiable view. Keep source snapshots immutable and private outputs
separate; a shared writable fixture directory cannot be certified as a stable input.

These requirements cover metadata and inherited access without observing each
syscall. Until they are implemented, narrowed Landlock runs remain useful for
finding missing declarations but cannot establish complete dependencies.

## Directory records and selection

An exact file grant becomes a VELDO-0367 `paths` entry. Record its repository name,
content and relevant metadata, plus every symlink component and resolved target.
An expected missing input becomes an `absent_paths` entry. A symlink leaving the
repository requires a recorded runtime target or an unknown reason.

Every directory grant becomes a `directories` entry with recursive scope. Its
digest covers sorted relative names, object types, file bytes, modes and symlink
text for the entire granted subtree. VELDO-0367 must compare that scope against
added, removed, renamed and modified descendants. Membership alone is insufficient:
editing an existing data file must select the item. Persist expanded `paths` too
if the current selector needs them, but retain the directory entry so new files
cannot escape selection. Never silently reinterpret recursion as one level.

Before considering carry, regenerate the plan from the current item definition and
reviewed inputs. Compare its normalized digest with the previous certificate.
Adding, removing or widening a grant selects the item even if every previously
recorded file is unchanged. A changed generator, declaration binding or import
resolution also selects its consumers. An unrelated edit outside these scopes can
carry the item only when its runtime and all other VELDO-0367 conditions match.

Evaluate the effective read permissions across all applied layers. A broad outer
layer is compatible with a certified inner layer that narrows those permissions.
Record both layers and their intersection. A whole-repository grant in that
effective set, an ancestor grant that includes the checkout, or a set of
grants that collectively covers all repository inputs receives
`unknown_reason=whole_repository_grant`. A large fixture directory may be legitimate,
but its fan-in must be reported. It cannot be hidden under a runtime label to make
eligibility look better.

## Permission failures and declaration repair

Preserve the kernel's EACCES result. The runner reports a surfaced permission
failure as `read_set_denied`, with item identity, mode, command, plan digest,
exit status, stderr and the available failing path. Python import and fixture
loaders should include the requested path and declaration source in their error.
For a native child that returns only an error code, report that the path is unknown;
do not invent it from the last successful open. Preserve the failed result and
withhold carry. An ordinary failure cannot be converted into an unknown green result.

Landlock does not force a program to terminate when it catches EACCES. It also does
not supply the unprivileged runner with a complete denial stream. The runner cannot
promise a path-specific report for every swallowed native denial without another
mechanism. This design does not add one. A caught denial grants no access, and a
successful result still has the same bounded file inputs. Focused qualification
must verify that required fixture or import failures remain failures, rather than
being hidden by a test's fallback. Compare expected observations with existing
trusted results before approving a declaration for reuse.

Declaration repair is explicit: identify the missing input, amend the protected
declaration or supported import resolver, review the resulting plan, and execute
the item again. A diagnostic run may use the existing broad profile if separately
requested, but its result is unknown and cannot replace the failed narrowed run.
The runner never retries with a parent directory, the entire checkout or a new
runtime root. Adding a grant through a repair always changes the plan digest.

## The VELDO-0367 certificate

Keep the existing dependency record fields and add a coverage method identifying
`enforced_read_set/v1`, a read-set digest and a certificate reference. The authority
certificate binds the item, source commit, mode, run nonce, actual normalized grants,
handled rights, runtime digest, repository-view digest, input-plan sources and
launcher identity. It records successful installation before candidate execution,
mode outcomes and completed descendant cleanup. Repository paths use the original
repository names, regardless of their physical locations in a private snapshot.

The trusted bootstrap acknowledges successful restriction over its existing
supervised launch channel before handing control to the candidate. Close that
channel in candidate code. The authority must match the acknowledgment to its child
and expected policy. A worker's `complete` flag, a JSON file in scratch or the mere
existence of a ruleset descriptor cannot prove enforcement. An installation error,
missing acknowledgment, policy mismatch or skipped restriction cannot issue a
certificate. An outside launcher certificate authenticates its trusted bootstrap;
it is not a claim that the kernel exposes a query for the current Landlock ruleset.

Set `complete=true` only after the runner certifies that the exact item ran under
the narrowed set it recorded, the filesystem and descriptor conditions hold, all
required modes finished, and no other unknown-input reason remains. Store the
certificate, result and dependency record atomically after cleanup. A certificate
for one mode, item, commit or runtime cannot authorize another. Carry retains its
original evidence and source commit.

Nested tracing workloads stay unknown, including the existing 51 unconfined tracing
exclusions. Unsupported launchers, unresolved metadata visibility, unkeyed runtime
or external inputs, whole-repository grants, missing controls and interrupted
cleanup also stay unknown. Preserve the specific reason. Failures remain red.

This extends VELDO-0367's coverage method for confined items. It retains its
selection, baseline and publication rules and its unconfined observation path.
Review records approve explicit grants; they do not restore VELDO-0217's old
eligibility rules as a universal VELDO-0367 selector. Existing declarations and
review tooling supply input plans, while runner enforcement supplies the coverage
certificate for this new path.

## Measured scope and setup cost

The round 3 measurement uses `f345e09b62d737cc0dcce32aad82c398042f342f` and
`proof/VELDO-0368/round3/measure-landlock.py`. It runs through the owner's
`remote_run.sh` on pc1. Its raw result and setup samples accompany this spec.

Source inspection finds that `agent_sandbox.grants_for` always includes the
worktree, authority and scratch read roots. The gate profile replaces writable
roots with scratch but retains the broad repository reads. Configured roots are
`/usr`, `/lib`, `/lib64`, `/bin`, `/sbin` and `/etc`, plus installed optional tools,
the launcher configuration and applicable Git common directories. Agent-only
project roots are not gate roots.

Fresh mutation workers use `mutation_sandbox.worker_grants`: the whole supplied
repository or snapshot, explicit extra reads, private scratch, `/usr`, `/lib`,
`/lib64`, `/etc`, installed tools and available private fixture roots. The worker
profile's launcher installs IPC confinement first; `confine_in_tree` applies these
Landlock grants in its bootstrap. `agent_sandbox.landlock` also grants
`/proc` and, with the broker, the PTMX device. Neither path currently selects reads
by item. A declared legacy worker's frozen root is narrower because of its copied
contents, not because `worker_grants` enumerates individual files.

The final pc1 run was `rr20261126125200-be46`, on Linux `7.0.0-38-generic`,
Landlock ABI 8 and `/usr/bin/python3` 3.12.3. Both scope probes entered
`worker_tree` and `confine_in_tree`; the measurement wrapper captured the grants
passed to the production Landlock function without changing them.

The applied worker roots included the entire checkout, private scratch, `/usr`,
`/usr/lib`, `/usr/lib64`, `/etc`, `/home/dmitry/.nvm/versions/node`,
`/home/dmitry/.local/share/claude`, `/home/dmitry/.local/share/codex-versions`,
`/home/dmitry/.local/share/veldo/langgraph`, `/home/dmitry/.rustup`,
`/home/dmitry/.cargo/bin`, `/dev/null` and `/dev/urandom`. The launcher added a
private fixture root under `/home/dmitry/.vg/`, named `gad61` in the broad probe
and `gff62` in the narrowed probe. The Landlock function also added `/proc` and
brokered `/dev/ptmx`. Exact paths and rights are in `round3/landlock.json`.

The current broad worker read an unrelated repository spec through Python and
native cat, and listed the repository root. With a second read layer granting
only `scripts/agent_sandbox.json` as a repository input, those new content reads
and the listing failed with EACCES. The allowed file and `/etc/os-release` stayed
readable. Both runs kept the repository write denial and `TracerPid: 0`.
Starting the native watchdog increased the thread count from one to two; the
narrowed content read still failed afterward.

The narrowed worker could still stat the unrelated file, and access reported it
readable. It also read 32 bytes through the deliberately preopened descriptor.
These measured gaps are why this spec requires the private repository view and
clean descriptor handoff before `complete=true`. Neither scope probe is certified.

Setup measurements used one generator and 250 fresh child processes: 25 samples
per shape for each of two routines. The full routine includes the existing strict
IPC filter and Landlock setup. The added read-layer routine starts timing after
that existing domain is installed. Shape order alternates by repetition. The
fixed grants in the timing run are the recorded parent worker grants; the
launcher-created fixture root is present in the scope probes only.

| Repository grants | Full routine median wall ms | Full routine median CPU ms | Added layer median wall ms | Added layer median CPU ms | Added layer p95 wall ms |
| :- | -: | -: | -: | -: | -: |
| 1 broad root | 0.705 | 0.705 | 0.117 | 0.117 | 0.126 |
| 32 files | 1.071 | 1.070 | 0.422 | 0.422 | 0.454 |
| 128 files | 2.045 | 2.044 | 1.206 | 1.206 | 1.262 |
| 512 files | 5.702 | 5.703 | 4.349 | 4.337 | 4.577 |
| 1,024 files | 10.905 | 10.906 | 8.909 | 8.902 | 9.151 |

The added layer costs milliseconds per item, reaching 8.91 ms at 1,024 file rules.
It is not zero. Directory grants reduce rule count at the cost of selecting more
items when their descendants change. These warm setup timings include path checks,
file-descriptor opens and rule installation. They exclude process creation, input
projection, import generation, runtime hashing and ongoing filesystem lookup cost.
They do not establish total execution overhead or gate savings. The raw samples,
source digest, reproduction script and pc1 log are under `proof/VELDO-0368/round3`.


## Measured inventory and expected eligibility

The inventory joins the same receipt as round 2, at line 44525 of
`myday/research/gate-stamps/cand-1122-55b511908-verify.log`, commit `55b511908`.
`proof/VELDO-0368/round3/measure-inventory.py` verifies the receipt hash and
reconciles 4,023 cases and 5,495 worker outcomes. It reads historical sources from
this repository's Git objects and uses the workers' actual legs. Each category
counts its shared baseline and no-op controls once. Categories overlap.

| Category | Cases | Controls | Worker seconds | Share of the 91,034.33 target seconds |
| :- | -: | -: | -: | -: |
| All confined cases | 2,874 | 1,000 | 79,251.29 | 87.06% |
| Existing declarations | 19 | 34 | 1,187.52 | 1.30% |
| Reviewed declarations | 0 | 0 | 0.00 | 0.00% |
| Generated import candidates | 2,874 | 1,000 | 79,251.29 | 87.06% |
| Imports proved complete by this static scan | 0 | 0 | 0.00 | 0.00% |
| Existing declaration or proved import closure | 19 | 34 | 1,187.52 | 1.30% |
| Unconfined tracing exclusions | 51 | 32 | 11,783.04 | 12.94% |

The declaration file is identical at the receipt commit and the round 3 head:
30 declarations overall, 19 attached to confined cases, all unreviewed. Declaration
presence does not establish current completeness or successful narrowed execution.

The static measurement follows ordinary imports and literal Python filenames,
includes prerequisites, and projects the mutation drivers to remove their case
registries. It does not apply each mutation to generate that mode's imports. It scans function bodies conservatively and includes every matching
repository basename. The resulting proposals contain 1,014 to 1,020 Python files,
with a median of 1,014. Every proposal encounters dynamic loaders. This simple
algorithm demonstrates that candidate generation is possible, but its unresolved
loads and omitted data inputs prevent calling it a complete import closure.
A better resolver needs the reviewed loader rules and explicit data declarations
specified above. These proposals should not be approved without narrowing review.

The measured opportunity is 79,251.29 worker-seconds, or 47.89% of all historical
worker time and 87.06% of the 55.01% target. That is the upper bound if every
confined case qualifies. The 19 declaration-backed cases are a first qualification
batch worth at most 1.30% of the target, including their controls. Their qualification
rate has not been measured. No positive expected eligible percentage can be derived
from this receipt alone: it contains no runs under narrowed grants. The supported
range is 0 to 87.06% of target worker time, with zero currently demonstrated by
historical cases. Unlike the round 2 watchdog exclusion, unresolved static imports
do not impose a zero ceiling: successful enforced runs can establish bounded inputs
without proving every dormant import branch. Do not present the upper bound as an expected saving.

Measure a positive forecast by qualifying focused batches under the final view and
read policies, then joining their successful item identities and exact controls to
these same elapsed times. Report failures, whole-repository grants, unresolved
runtime inputs and nested workloads separately. Unmeasured cases remain unknown;
do not extrapolate a convenient suite sample across all 2,874 cases. Carry eligibility
also differs from savings on a particular edit, which depends on directory fan-in
and the changed paths.

The round 2 notification results remain archived in `proof/VELDO-0368`: zero new
eligibility and median wall overhead of 51.8% to 165.4%. They are not measurements
of this enforcement design.

## Independently landable increments

1. Add the plan schema and resolver in `confined_inputs.py`, using declarations and
   import candidates. Emit plans without changing execution or eligibility. Focused
   fixtures cover relative imports, package shadowing, stale reviews and unresolved
   loaders. A missing input source must prevent a complete plan.
2. Add the read layer to the worker bootstrap and both sandbox copies. Keep all
   results unknown. Test one native reader, EACCES, thread inheritance, write denial
   and the existing AC7 refusal. Skipping restriction or adding a root grant must
   break a fixture. Measure setup separately from fixture execution, snapshot construction and runtime hashing.
3. Build the private repository view and close descriptor and process-path aliases.
   Extend the existing namespace helper, its narrowly scoped profile and the snapshot
   machinery. Keep certification
   disabled. Test stat, access, symlink escapes, inherited descriptors, stdin and
   immutable source contents. Any remaining live-checkout metadata access blocks
   the next increment.
4. Wire plans into suite groups and mutation modes. Record directory scopes and
   runtime digests, preserve permission failures and require exact shared-control
   compatibility. Use one suite and one mutation case with baseline, no-op and
   mutant fixtures. Fix a missing declaration through review and a fresh execution.
5. Add the authority certificate and VELDO-0367 selection join. Enable carry only
   for supported, certified items. A small authenticated inventory covers an
   unrelated edit, file edit, directory addition, runtime change and grant change.
   Forged or unapplied certificates must never authorize carry.
6. Qualify reviewed batches with focused cases and publish their measured eligibility
   against the historical inventory. Leave all other items unknown. Do not run a
   full gate to produce an attractive percentage or enable broad grants as a fallback.

Each increment can land with certification disabled until its prerequisites hold.
Rollback disables only the new certification path and preserves confinement and
failed results. This round changes the specification and measurement evidence only.
