---
schema: veldo.spec/v1
id: VELDO-0042
title: Isolated worker clones and pinned read-only shared object cache
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W27
plan_revision: 3
depends_on: [VELDO-0029, VELDO-0031, VELDO-0040]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/env_provision.py"
  - ".veldo/env_provision.py"
  - "packs/*/.veldo/env_provision.py"
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/control_clone*.py"
  - ".veldo/control_clone*.py"
  - "packs/*/.veldo/control_clone*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0042_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0042-isolated-worker-clones.md"
  - "specs/index.md"
  - "proof/VELDO-0042/*"
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
      Claim: Each run gets an isolated clone at its accepted commit with no write access to
      authority metadata or other workers. Set and completeness: Provision two real clones while
      provisioner HEAD points elsewhere; compare tree identities and attempt actual writes to the
      other clone, store, keys and authority Git metadata under worker identities. Falsifier:
      Provision from current HEAD; the accepted-source tree comparison must fail.
    falsified_by: >
      Provision from current HEAD; the accepted-source tree comparison must fail.
  - id: AC2
    text: >
      Claim: Only named repository objects are exposed read-only and pinned while a clone uses them.
      Set and completeness: Enumerate reachable objects for accepted attachments, read them from the
      worker, try cache writes and try cat-file access to an unnamed repository; ordinary garbage
      collection must retain the live pinned objects. Falsifier: Pool unnamed repository objects
      into the worker alternate; the unnamed-object access check must fail.
    falsified_by: >
      Pool unnamed repository objects into the worker alternate; the unnamed-object access check
      must fail.
  - id: AC3
    text: >
      Claim: Ordinary clone cleanup releases its object pins only after its workers and consumers
      terminate. Set and completeness: Run a real child reading the clone, attempt cleanup while it
      is alive, then terminate it and retire the clone; inspect retained and released pins and
      distinct clone paths. Falsifier: Release a pin while its child still reads objects; the live-
      object availability check must fail.
    falsified_by: >
      Release a pin while its child still reads objects; the live-object availability check must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Isolated worker clones and pinned read-only shared object cache. Deliver the normal function needed by the running factory journey.

## Context

W27 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: each run gets its own clone at its accepted commit, whatever the provisioner's HEAD
  points at. A worker cannot write to another worker's clone, the store, the keys or the authority's
  Git metadata. Other repositories appear only as contract-named, exact-commit, read-only attachments,
  whose objects stay pinned while a clone uses them and survive ordinary garbage collection. Cleanup
  releases a clone's pins only after its workers and consumers have ended.
- Threat model: provisioning from the current HEAD instead of the accepted commit; a worker writing
  directly outside its own clone (another clone, the store, keys, authority metadata); an alternate or cache that
  exposes unnamed repository objects or authority metadata; and a pin released while a child still
  reads its objects. The owner's account outside workers, Git and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); interrupted
  provisioning or retirement and recovery from concurrent garbage collection (Release 2, see History); a
  worker that deliberately escapes its group, or writes through the owner's own unconfined processes (the
  user service manager, shell startup files, ssh to this host), which only a separate worker account
  closes (Release 2: no second operating-system account for now, Telegram 28578/28580); forged rows in
  our own store, files planted in the installed directory and resource exhaustion by our own account.

## Notes

C13 remains unchanged: other repositories are accessible only as contract-named, exact-
accepted-commit, read-only attachments. Another repository write requires its own admitted
unit. A cache alternate must not expose authority metadata or unnamed repositories.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3 interrupted
provisioning/retirement and AC2 concurrent-GC recovery moved to Release 2. Named read-only
attachments, accepted-commit clones and live object pins remain. The criteria, declared
evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.

2026-09-24, implementation (branch build-veldo-0042): `.veldo/control_clone.py` provisions one
isolated clone per dispatch at the contract's accepted commit and tree, never the source
repository's HEAD, over one read-only pinned object cache per repository borrowed through Git
alternates, with only contract-named exact-commit attachments as `refs/attachments/<name>`; its
`enter` wrapper confines a worker's direct writes with Linux Landlock to its own clone and scratch
(a consumer to its scratch only), so a worker cannot write another clone, the store, the keys, the
authority's Git metadata or a cache; cleanup releases a clone's pins only after its workers and
consumers have ended, observed from the kernel through control_containment. `.veldo/env_provision.py`
`create` now passes backend arguments through so the clone backend takes the dispatch contract; the
fake and container backends are unchanged. Both are installed by `.veldo/init_scaffold.py`; engine
copies are byte-identical. Suite `scripts/suites/66_veldo_0042_clones.py` (0.45 s, 12 assertion
rows), red at 18ecd6f, and 12 mutations as finding 42; proof in `proof/VELDO-0042/`. The criteria,
status and risk are unchanged.

2026-09-24, implementation: `scripts/check_teeth_mutations.py` was added to the footprint so the
declared falsifiers can be registered as finding 42 of the existing teeth mutation driver, as
VELDO-0040, VELDO-0065, VELDO-0066 and VELDO-0067 registered theirs. `scripts/suites/manifest.json`
and `requires.json` gained the suite's enumeration and requires entry. The criteria, status and
risk are unchanged.
