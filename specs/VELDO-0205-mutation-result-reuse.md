---
schema: veldo.spec/v1
id: VELDO-0205
title: Exact input mutation result reuse with authenticated records and honest receipts
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0123]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", ".veldo/policy.yaml", "scripts/gate_reuse.py", "scripts/mutation_reuse.py", "scripts/mutation_reuse_profiles.json", "scripts/mutation_sandbox.py", "scripts/reuse_stamp.py", "engine/.veldo/control_verification.py", ".veldo/control_verification.py"]
footprint:
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - ".veldo/policy.yaml"
  - "scripts/mutation_sandbox.py"
  - "scripts/reuse_stamp.py"
  - "engine/.veldo/control_verification.py"
  - ".veldo/control_verification.py"
  - "scripts/verify.sh"
  - "scripts/check_gate_mutations.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/check_review_mutations.py"
  - "scripts/gate_reuse.py"
  - "scripts/mutation_reuse.py"
  - "scripts/mutation_reuse_profiles.json"
  - "scripts/suites/98_veldo_0205_reuse.py"
  - "scripts/suites/53_veldo_0123_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0123-mutation-drivers-in-every-gate.md"
  - "specs/VELDO-0205-mutation-result-reuse.md"
  - "specs/VELDO-0206-suite-result-reuse.md"
  - "specs/index.md"
  - "proof/VELDO-0205/*"
behavior_bearing: true
observability:
  logs: Every mutation has its identity, exact key or closure refusal, execution source and validated observations.
  metrics: Exact executed, reused and rejected case counts per driver and stage; worker invocations stay separate.
  traces: Bind authenticated observations to tree, case, driver, gate, interpreter, runtime and environment digests.
  error_taxonomy: Cache miss, unknown closure, invalid record and unavailable store run fresh; existing driver failures stay red.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Only an exactly matching complete input closure permits reuse. Set: all cases in both
      registries, repository files including fixtures and scripts, names, modes, case definition,
      interpreter, tools, external input trees, environment and configuration. Completeness: a
      reviewed, content-pinned closure profile enumerates external trees and states why variable
      host state cannot affect the observations; absent, changed or incomplete profiles are misses.
      The key includes the entire existing snapshot closure and runtime closure. Test each dimension,
      additions and deletions, and an unchanged hit in reuse/exact-closure. No mtime-only identity.
    falsified_by: Omit repository content from the key; reuse/exact-closure must turn false.
  - id: AC2
    text: >
      Claim: The external store can supply only intact, validated killed-mutant observations.
      Set: missing, truncated, edited, incorrectly keyed, wrong-interpreter, invalid-baseline,
      survivor, timeout and valid records. Completeness: authenticated canonical records are written
      atomically outside the repository only after full result validation and input race checks;
      hits repeat that validation. Drive every class in reuse/authenticated-kills. Store errors
      fall back to fresh execution and never manufacture a pass.
    falsified_by: Skip authentication on read; reuse/authenticated-kills must turn false.
  - id: AC3
    text: >
      Claim: The coordinator retains full inventory coverage and exact evidence counts with mixed
      fresh and reused cases. Set: both drivers, all fresh, all reusable, mixed, corrupted hits,
      force fresh, input races and worker failure. Completeness: controlled workers drive the real
      coordinator without mutation subprocesses; receipts enumerate every completed case and key,
      and counts are derived from those observations, including failed stages. No hit can conceal
      a fresh survivor. Verify reuse/receipt-counts and reuse/stale-cannot-pass.
    falsified_by: Count reused cases as executed; reuse/receipt-counts must turn false.
  - id: AC4
    text: >
      Claim: Reuse is visible and explicitly bypassable in the canonical repository gate.
      Set: the repository gate, both driver identities and the force-fresh environment control.
      Completeness: VELDO_GATE_FORCE_FRESH=1 bypasses reads and writes; canonical landing and release
      verification require that setting. The ordinary suite stage remains entirely fresh pending
      VELDO-0206. Test actual coordinator behavior and gate wiring in reuse/fresh-policy, without
      running the full gate during this build. Measure one complete repository key pass separately.
    falsified_by: Ignore the force-fresh control; reuse/fresh-policy must turn false.
required_evidence: [unit, integration]
rollback: Revert this specification's implementation and gate wiring together; external cache records then become unused.
---

## Intent

Reduce repeated mutation work without weakening the meaning of a killed mutant. The owner reports
about 69 minutes for about 2,490 mutants within a roughly 2.5 hour full gate. Mutation reuse is the
first concern. VELDO-0206 specifies suite reuse separately and is ready but unimplemented.

## Amendment of VELDO-0123

Dmitry approved gate reuse on 2026-10-06 in Telegram 31900, answering the design in Telegram 31622.
This reverses the 2026-09-22 removal approved in Telegram 28800 when 38 mutants took 13.8 seconds.
VELDO-0123 AC1 and the intent's fresh-in-every-gate requirement now mean every registered case must
have either a fresh validated rejection or an authenticated rejection with an exactly matching
complete closure key. AC2, full inventory coverage, worker deadlines, cleanup, and fail-closed
propagation remain requirements. Its AC4 qualification fixtures remain force fresh. A cache hit
is never described as fresh execution. The prior timing record remains historical evidence.

## Closure boundary

The working-tree snapshot is a conservative repository closure, including the engine, tests,
fixtures, drivers and gate. It alone does not close host services, clocks, random data, system
configuration, dynamically loaded libraries or external tools. A profile must document all external
file trees and tools, and explain why generated paths, clocks, randomness and services cannot
change the asserted observations. Profiles pin the reviewed repository input digest and exact case
identity; any code edit invalidates that qualification. There is no automatic certification from
an observed read trace, file extension, or a suite claiming to be deterministic. No profile means
fresh execution. Runtime trees are recursively content hashed with names and modes; symlinks include link text and resolved target identity;
unreadable inputs and special files refuse reuse. Only the fixed worker environment values are hashed, never printed. Profiles and the reuse implementation are also part of every result key.

The first implementation may leave unqualified production cases fresh. Qualification must be
reported explicitly, with no implied speedup for those cases. A follow-up can narrow closures only
with evidence that omitted inputs cannot affect the case. The tests exercise real store/key code
and controlled coordinator workers; they do not claim a production suite has a closed environment.

## Protected path and landing policy

The owner instruction authorizes preparing scripts/verify.sh on this branch. Policy assigns high
risk and requires separate human approval bound to the exact final implementation commit and
proof before landing. Telegram 31900 authorizes the design, not a fabricated commit-bound approval.
No self-approval, push or merge is performed here. Landing and release gates must run with
VELDO_GATE_FORCE_FRESH=1; ordinary development gates may reuse qualified results. This is a new
explicit conservative policy, not a relaxation of the merged-tree verification requirement.

## What the reviewer judges

Normal use is a repository gate under the owner account, with an external private cache directory
and reviewed closure profiles. Missing or damaged caches are routine misses. Deliberately edited
records, including a recomputed unkeyed checksum, are in scope and must miss. HMAC authentication
protects records using a separate private local key; compromise of both that key and the process
running as its owner is outside this boundary. Invalid closures and honest implementation defects
are in scope. No claim of protection against arbitrary code already executing as the owner.

## Build constraints

Only suite 98 and its targeted unit fixtures run during this build, sequentially. The owner runs
the force-fresh full gate and existing mutation qualifications after the other checkout finishes.
No gate stamp or events byproduct is committed. Required language syntax such as front-matter
delimiters and command flags retains its ordinary ASCII spelling; prose uses single ASCII hyphens.

## Review repair authorized by owner, 2026-10-06

The protected paths listed above are prepared for exact-commit owner approval before landing.
Gate stamps and events carry force_fresh and per-stage reused counts; both the fleet verifier
and push guard reject reuse-aware evidence unless forced fresh with all counts zero. Legacy
adopter stamps without reuse metadata retain their existing behavior. Unknown force-fresh values
are errors; 1/true/yes/on and 0/false/no/off are accepted case-insensitively.

Every mutation worker installs Linux Landlock ABI 3 or newer before loading driver code.
Children inherit the restriction: only the frozen tree, /usr, /lib, /lib64, /etc and device
null/random inputs are readable, and only private worker scratch is writable. /proc and caller
home are not exposed. Cache placement under allowed runtime paths is refused. Unsupported hosts
fail closed. Runtime profiles must cover Python, its stdlib, git and the shell; reviewed profiles
remain responsible for transitive tools, libc, configuration and non-file determinism until
VELDO-0207 enforces the declared runtime set. Kernel and approved coordinator code are trusted;
an arbitrary hostile process running as the coordinator uid outside this sandbox can still
steal its key or forge evidence. HMAC is not an owner-account security boundary. Mutants inside
the sandbox cannot open the store or key even if they guess the path. Conflicting publication
poisons the identity, reports an integrity failure and never silently preserves a winning record.
