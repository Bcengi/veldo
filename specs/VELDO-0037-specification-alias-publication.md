---
schema: veldo.spec/v1
id: VELDO-0037
title: Atomic specification alias allocation and document publication
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W22
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0035]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_alias*.py"
  - ".veldo/control_alias*.py"
  - "packs/*/.veldo/control_alias*.py"
  - "engine/.veldo/control_document*.py"
  - ".veldo/control_document*.py"
  - "packs/*/.veldo/control_document*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "packs/*/.veldo/control_store.py"
  - "engine/.veldo/control_readset.py"
  - ".veldo/control_readset.py"
  - "packs/*/.veldo/control_readset.py"
  - "scripts/suites/*_veldo_0037_*.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0037-specification-alias-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0037/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Authority allocation gives unique VELDO aliases and preserves historical IDs. Set and
      completeness: Use real counter/uniqueness constraints with identical and distinct source-
      system/ID/revision/role tuples; inspect same-source reuse, distinct-source allocation and no
      reserved alias recycling. Reject invalid unit IDs through claim.unit_id_problem before
      artifacts. Falsifier: Allocate from checkout maximum instead of the store counter; independent
      requests with stale checkouts must collide and fail the check.
    falsified_by: >
      Allocate from checkout maximum instead of the store counter; independent requests with stale
      checkouts must collide and fail the check.
  - id: AC2
    text: >
      Claim: Edits compare expected version and artifact digest before replacing accepted content.
      Set and completeness: Submit current, stale and changed-content requests against real accepted
      documents; require a new version or named conflict with prior bytes preserved, and identical
      request reuse of its allocation. Falsifier: Ignore expected digest on an edit; the stale-
      overwrite check must fail.
    falsified_by: >
      Ignore expected digest on an edit; the stale-overwrite check must fail.
  - id: AC3
    text: >
      Claim: Source mapping, allocation and accepted document identity commit together and
      materialize exact bytes. Set and completeness: Publish each enabled artifact role through real
      store/filesystem operations; compare source tuple, alias, version, digest and reader-visible
      complete document against the accepted record. Falsifier: Publish altered bytes under the
      accepted digest; the document comparison must fail.
    falsified_by: >
      Publish altered bytes under the accepted digest; the document comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Atomic specification alias allocation and document publication. Deliver the normal function needed by the running factory journey.

## Context

W22 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use the authority counter, never a runtime checkout maximum. Source identity includes intended
artifact role, so one source can produce distinct specifications and other artifacts. 0035
supplies accepted snapshots and ordinary materialization; local commit is sufficient under
amended C3.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

Stated limits of store-enforced ownership, not claims. Enforcement lives in
`control_store.execute` under a same-account threat model, so raw SQL on the store file, a copy of
the store module from before the rule, and deleting the `entity_owners` table all write owned
entities; so does code that deliberately compiles a function under the declared module's file name
or patches the owning module's globals in its own process. The declarations and the repository
bindings are not in the journal, so a store rebuilt from its journal carries neither (Release 2
recovery). A declaration names one module file and its bytes, so an owning service attaches only
from that copy as it was when it first declared: an upgraded module, or the same module from
another checkout's copy, is refused `ownership_conflict`, and Release 1 has no re-declaration path.

The first-number floor does not depend on Git keeping a commit. When `accept_revision` first
accepts a commit it records, in the same transaction and keyed by the domain, repository and commit
id, the commit's root commits and every digit-bearing path named by the commits reachable from it
and from no commit already recorded for that repository, a root commit counting as the creation of
its tree (an `accepted_carriers` entity, immutable and owned by `accept_revision`). Enabling applies
the kind's carrier pattern to the union of every record of the repository, and reads a named
revision's root commits from its record, so a branch deleted, pruned or force-pushed after
acceptance lowers nothing, and storage grows with the history, not with its square. A revision
accepted before records existed is read from the bound repository while it holds the commit and
refused `accepted_revision_unavailable` at enabling once it does not, never skipped. What clears one: none
is needed, because none exists outside test stores (`accept_revision` and its record were both
introduced on this branch, and every revision `accept_revision` writes now carries its record);
one written around the commands, by raw SQL, is the stated same-account limit above, and Release 1
has no operator path to retire an accepted revision.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1/AC2
concurrency/restart matrices and AC3 interrupted materialization moved to Release 2. Unique
counter/source mapping, version checks and exact published bytes remain. The criteria,
declared evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.

2026-09-23 implementation: register the AC1-AC3 negative controls in the existing
`scripts/check_teeth_mutations.py` driver as finding 37 (the authorized footprint exception, also
listed in the machine-readable footprint), with two distinct mutations per named criterion row
and fresh unmutated controls. The allocation commands register on the existing store connection
as 0035's read sets do; the store, its schema and the snapshot modules are consumed unchanged.
No eligibility, project-manager, landing or remote publication behavior is implemented here.

2026-09-23 second independent review: entity ownership moves into the store, so the footprint
now also names `control_store.py` (VELDO-0023) and `control_readset.py` (VELDO-0035) in all three
copies. The guard that refused generic writes of alias and document entities lived on the one
connection the allocation authority attached to, so another connection, or a read set enabled after
attach, could rewind the counter and rewrite an immutable version. Each service now declares which
commands write the entity kinds and id prefixes it owns; the declaration is persisted with the store
and `control_store.execute` enforces it on every connection whatever was registered where or in what
order. Accepted revisions and snapshots (VELDO-0035) are declared owned the same way. The store's
existing behavior for undeclared entities, its domain tables and its command registry are unchanged.

2026-09-23 third independent check: ownership named only a command, so a connection registering
its own transition as `enable_artifact_kind` or `accept_revision` passed it; each declaration now
records the owning module's file and digest, and `execute` runs an owned command only when its
registered transition, and every function its closure holds, is that file's code with those bytes
(`foreign_transition` otherwise), and no declaration may name one of the store's generic commands.
An accepted revision could name a commit the allocation authority's repository lacks, after which
every enabling refused; the first service to attach now binds each repository UUID to its accepted
repository in the store (`repository_binding_conflict` for another), `accept_revision` refuses
`unenrolled_commit` for a commit the bound repository does not hold at acceptance time, and the
floor counts only accepted commits the bound repository holds. No revision recorded before this
fix exists outside test stores: `accept_revision` was introduced on this branch, and a store
holding accepted revisions written by generic commands already refuses both attaches
`ownership_conflict`, so no operator clearing path is needed.

2026-09-23 recorded numbers: the floor skipped an accepted commit the bound repository no longer
held, so a branch deleted and pruned after acceptance lowered the next first number and could issue
a held number again. `accept_revision` now records each accepted commit's carrier paths in the
store and the floor reads that record; an unrecorded revision whose commit is gone refuses
`accepted_revision_unavailable` instead of being skipped. Each record then held the whole
history; it now holds only what its commit adds over every recorded commit, and the floor reads the
union of the records.
