---
schema: veldo.spec/v1
id: VELDO-0029
title: One signed enrollment binding decides which authority a clone writes to, and nothing ambient does
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W14
plan_revision: 2
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_enrollment.py"
  - ".veldo/control_enrollment.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "scripts/suites/*_veldo_0029_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0029-repository-enrollment.md"
  - "specs/index.md"
  - "proof/VELDO-0029/*"
behavior_bearing: true
observability:
  logs: >
    Every resolution names the workspace it was given, the binding it read, and the store it
    returned; every refusal names its reason from a closed list and the coordinates it judged.
  metrics: >
    Count refusals by reason, so a clone that is quietly failing to route is visible as a rate
    rather than as one person's confusion.
  error_taxonomy: >
    Distinguish a clone that was never enrolled, a directory holding a different repository, a
    clone replaced under the same path, a stale host binding, a generation behind the authority's,
    a cross-domain request, a store that is not the one named, and a binding that is malformed or
    unsigned. Each is a different repair.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A signed binding names the repository, the domain, the store, the host and the
      authority generation, and resolution returns the store that binding names. Two separate
      clones enrolled against the same domain resolve to one store, and a linked worktree resolves
      to the same store as the clone it belongs to. Set: Real git clones under a temporary
      directory, one with a linked worktree, each enrolled through the real call. Completeness: The
      signature is verified over the binding's own fields, and a binding whose signature does not
      verify is refused, so the row fails if the record is trusted because it is present rather
      than because it is signed. Falsifier: Return the store without verifying the signature;
      enrollment/an-unsigned-binding-is-not-a-binding must fail.
    falsified_by: >
      Return the store without verifying the signature;
      enrollment/an-unsigned-binding-is-not-a-binding must fail.
  - id: AC2
    text: >
      Claim: Resolution reads the workspace it is GIVEN and nothing ambient. The process's current
      directory, VELDO_CONTROL_DB and any other environment variable, and the importing module's
      own location are each pointed at a second real repository enrolled against a second store,
      Set: Two enrolled clones and every public routing call, run
      with each ambient source pointed at the other one in turn; and separately
      control_store.control_db_path, which is where the ambient resolution this item exists to
      remove actually lived. Completeness: The second repository is REAL and REALLY enrolled, so
      the row fails if the answer is right only because the alternative did not exist; and the
      ambient resolver is asserted CLOSED rather than merely unused, because it had no callers and
      an unused means is still a means. Falsifier: Resolve from the current directory when an
      explicit workspace was given; enrollment/ambient-sources-decide-nothing must fail. And:
      derive a store path from the environment or the current directory again;
      enrollment/the-ambient-store-resolver-is-closed must fail.
    falsified_by: >
      Resolve from the current directory when an explicit workspace was given;
      enrollment/ambient-sources-decide-nothing must fail.
  - id: AC3
    text: >
      Claim: A clone replaced under the same path refuses and must enroll again, whether the
      replacement is a different repository or a fresh clone of the same one. Set: An enrolled
      clone, then that directory replaced by a clone of a different repository, and separately by a
      fresh clone of the same repository; each binding component corrupted independently.
      Completeness: The fresh-clone-of-the-same-repository case is in the set, so the row fails if
      identity is decided by the repository alone; and the refusals are checked to create no local
      store, ledger or file, so a refusal cannot become a quiet local authority. Falsifier: Trust a
      reused path after replacing its repository identity;
      enrollment/a-replaced-clone-must-enroll-again must fail.
    falsified_by: >
      Trust a reused path after replacing its repository identity;
      enrollment/a-replaced-clone-must-enroll-again must fail.
  - id: AC4
    text: >
      Claim: Every refusal is by a name from a closed list and carries the coordinates it judged,
      and a refusal returns no path at all. Set: Every reason in the list, each produced by a real
      binding and workspace rather than a hand-built record. Completeness: The row asserts the list
      is exhausted, so a reason added later without a case fails it. Falsifier: Return the store
      alongside the problems instead of refusing;
      enrollment/a-refusal-hands-back-no-path must fail.
    falsified_by: >
      Return the store alongside the problems instead of refusing;
      enrollment/a-refusal-hands-back-no-path must fail.
required_evidence: [unit]
rollback: >
  Stop calling the resolver. Nothing else reads the binding, and a binding left on disk is inert.
---

## Intent

The authority a clone writes to is decided by one signed record that clone carries, and by nothing about where the caller happened to be standing.

## Context

PLAN-0019 W14, revision 2. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R20 and R26.

**The defect this exists to remove is in shipped code and was measured.** `control_store.control_db_path` decides which database to open by reading `VELDO_CONTROL_DB` from the environment, and otherwise by running `git rev-parse --git-common-dir` in whatever directory the process is in. Two throwaway repositories and one call demonstrate it: standing in the first it answers the first repository's database, standing in the second it answers the second's, and with the environment variable set it answers neither. A command carries the repository it means, it is signed, and the signature verifies; then this decides where to write, from the caller's position rather than from the command. A correctly signed command naming one repository can commit into another and nothing in the chain notices, because nothing in the chain ever compares the two.

Nothing today runs the authority as a service or across clones, so the two have never disagreed in practice, and `control_db_path` has NO CALLERS at all: every place that opens the store passes an explicit path. It was a loaded gun on a shelf rather than one in anyone's hand, and it is the reason this item is first. This item CLOSES it: it now requires an explicit path and derives nothing, because an unused means is still a means, sitting exactly where the next person to want a default would find it.

**What identity means here, and why a path is not one.** The binding records two things a swapped directory cannot carry over: the repository's root commits, which a different repository does not share, and a per-clone UUID written into that clone's own git common directory at enrollment, which a fresh clone of the same repository does not have. A directory replaced at the same path fails one of the two. The absolute path is recorded for diagnosis and is never an input to the decision.

## Out of scope

This item decides WHICH store. Reaching it is three separate items: the authenticated local IPC client is VELDO-0107, the authenticated SSH command relay is VELDO-0108, and what happens when the authority is unreachable is VELDO-0109. Service installation is W32 and worker clone provisioning is W27.

## Notes

**The footprint names two copies, not nine.** `scripts/publish.py` composes every pack from `engine/`
at publication, so the private repository keeps one base and no copies; a pack's own file wins where
it has one, and no pack carries a `control_` module. Listing `packs/*/.veldo/` in the footprint would
have asked for seven files in git that the release builds anyway, which is seven things to drift.


This item was W14 in revision 1 as a single specification carrying the binding, both transports and the unavailable case. Dmitry split it on 2026-09-21: four criteria that each needed their own set, their own falsifier and their own fixture do not belong in one item, and an item that cannot close is not a smaller risk than four that can.
