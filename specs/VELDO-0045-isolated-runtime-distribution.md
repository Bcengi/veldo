---
schema: veldo.spec/v1
id: VELDO-0045
title: Pinned isolated runtime, dependency licenses, and distribution inventory
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W30
plan_revision: 3
depends_on: [VELDO-0043]
placement: [distribution, enforcement, loop]
protected_paths: [scripts/verify.sh, engine/scripts/verify.sh]
footprint:
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "engine/.veldo/pack_conformance.py"
  - ".veldo/pack_conformance.py"
  - "packs/*/.veldo/pack_conformance.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_runtime*.py"
  - ".veldo/control_runtime*.py"
  - "packs/*/.veldo/control_runtime*.py"
  - "engine/runtime/*"
  - ".veldo/runtime/*"
  - "packs/*/runtime/*"
  - ".veldo/packs.json"
  - "scripts/check_install_and_run.py"
  - "scripts/check_pack_drift.py"
  - "scripts/check_template_sync.sh"
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "packs/*/scripts/verify.sh"
  - "scripts/suites/*_veldo_0045_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0045-isolated-runtime-distribution.md"
  - "specs/index.md"
  - "proof/VELDO-0045/*"
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
      Claim: The journey installs a compatible pinned, hashed and licensed LangGraph runtime in
      isolation. Set and completeness: Use real package tooling for the chosen runtime/Python
      configuration; compare installed transitive metadata to the lock and license/provenance
      records and run the actual nonpersistent adapter workload. Alter one artifact hash and omit
      one dependency; both must refuse activation. Falsifier: Bypass hash enforcement for an altered
      wheel; the runtime-integrity check must fail.
    falsified_by: >
      Bypass hash enforcement for an altered wheel; the runtime-integrity check must fail.
  - id: AC2
    text: >
      Claim: The chosen installed journey contains every code and non-code asset it needs. Set and
      completeness: Enumerate actual runtime imports, service/helper/config assets and lock files
      reached by the reference pack installation and journey; compare to installed files and
      digests. Omit one required non-code asset and require named failure without source-tree
      fallback. Falsifier: Omit the runtime lock from the reference installation; the journey-asset
      check must fail.
    falsified_by: >
      Omit the runtime lock from the reference installation; the journey-asset check must fail.
  - id: AC3
    text: >
      Claim: Validators, authorization and gate imports remain stdlib-only when the execution
      environment is absent. Set and completeness: Enumerate enabled installed enforcement entries,
      hide the runtime and run their real commands against accepted data; graph invocation alone
      reports unavailable. Falsifier: Add a runtime import to installed authorization; the no-
      runtime enforcement check must fail.
    falsified_by: >
      Add a runtime import to installed authorization; the no-runtime enforcement check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Pinned isolated runtime, dependency licenses, and distribution inventory. Deliver the normal function needed by the running factory journey.

## Context

W30 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Exact Python/LangGraph versions and licenses must come from compatibility qualification.
Install the chosen reference distribution and all its journey assets; full inventory/every-
pack coverage is Release 4. No persistent checkpoint dependency is required in Release 1.
Apply C16 provenance and no-free/paid-tier restrictions to direct and transitive dependencies.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: owner Telegram 28848 moves
recovery/robustness to Release 2. Drop AC1 installation-crash/profile matrix, AC2 every-
pack/full inventory qualification, AC3 replay/recovery matrix; retain a compatible isolated
pinned runtime and every asset needed by the chosen installed journey. Removed recovery,
durability and failure-matrix obligations belong to Release 2; additional host/channel/version
and full distribution breadth belongs to Release 4. Normal function and the checks stated
above remain Release 1.
