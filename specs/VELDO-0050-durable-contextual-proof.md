---
schema: veldo.spec/v1
id: VELDO-0050
title: Executor persists proof and performs complete contextual validation
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W35
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049]
placement: [loop, contracts, metrics]
protected_paths: []
footprint:
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate.py"
  - "packs/*/.veldo/validate.py"
  - "engine/.veldo/control_proof*.py"
  - ".veldo/control_proof*.py"
  - "packs/*/.veldo/control_proof*.py"
  - "scripts/suites/*_veldo_0050_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0050-durable-contextual-proof.md"
  - "specs/index.md"
  - "proof/VELDO-0050/*"
behavior_bearing: true
observability:
  logs: >
    Proof acceptance records name implementation object, accepted spec digest, artifact digest,
    producer invocation, and persisted location.
  metrics: >
    Count incomplete bundles, duplicate criterion mappings, missing observations, fabricated checks,
    and recoverable proof publications.
  traces: >
    Trace actual verifier output through immutable artifact storage and proof acceptance to a
    separate review process.
  error_taxonomy: >
    Distinguish nonexistent Git object, empty criterion universe, digest mismatch, incomplete
    evidence, untrusted check, and pending proof publication.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: LiveLoop.assemble_proof and Executor.run persist immutable proof and evidence before
      reporting built or offering review. Set: Actual proof/<spec-id>/manifest.json projections,
      digest-addressed artifacts, Git implementation commits, and authority proof records across
      separate builder and reviewer processes. Completeness: Enumerate artifact-write, fsync, atomic
      publication, acceptance commit, and reply barriers. SIGKILL at each barrier and restart the
      reader without the builder memory or temporary directory; it must read the exact complete
      accepted bundle or refuse review while publication is pending. Falsifier: Keep the manifest
      only in validate_proof temporary storage and kill the builder after built;
      proof/process-boundary must fail when the fresh reviewer cannot resolve its bytes.
    falsified_by: >
      Keep the manifest only in validate_proof temporary storage and kill the builder after built;
      proof/process-boundary must fail when the fresh reviewer cannot resolve its bytes.
  - id: AC2
    text: >
      Claim: LiveLoop.validate_proof invokes complete contextual validation against accepted source
      and specification, not only validate.check_json. Set: validate.check_json,
      check_criteria_coverage, check_required_evidence, and spec_criterion_ids over real Git
      objects, manifests, and evidence bytes in enrolled snapshots. Completeness: Derive the
      required criterion/evidence/check universe from the accepted spec and verifier catalog.
      Corrupt one binding at a time: empty accepted criterion set, omitted or duplicate or invented
      mapping, nonexistent commit, wrong spec revision, missing producer, missing trusted
      observation, changed artifact digest, or absent required evidence. Require a named refusal
      before review in a new process. Falsifier: Replace contextual validation with check_json alone
      and submit an empty-criteria proof naming a nonexistent commit; proof/contextual-validation
      must reject it.
    falsified_by: >
      Replace contextual validation with check_json alone and submit an empty-criteria proof naming
      a nonexistent commit; proof/contextual-validation must reject it.
  - id: AC3
    text: >
      Claim: LiveLoop.assemble_proof records only actual trusted check observations; missing build
      checks cannot create a passing unit check. Set: LiveLoop.gate and Executor.run using the real
      canonical gate subprocess, captured exit/output artifacts, and signed Evidence Service
      receipts in control.sqlite3. Completeness: Enumerate required checks from the installed gate
      catalog and compare them to captured results. Run green, red, interrupted, missing-output, and
      altered-output cases; SIGKILL the gate before its terminal record and require missing evidence
      rather than default success. Falsifier: Reinstate the default passed unit check when build
      checks are absent; proof/no-default-check must detect fabricated success after the interrupted
      gate.
    falsified_by: >
      Reinstate the default passed unit check when build checks are absent; proof/no-default-check
      must detect fabricated success after the interrupted gate.
  - id: AC4
    text: >
      Claim: Executor.run and LiveLoop.emit submit proof/review observations to their owning
      services and never directly emit projection-owned verdict.recorded or completion. Set:
      Build-only and full executor paths with real events.emit refusal, signed review artifacts from
      a separate actor, the event file, and the authoritative journal. Completeness: Drive both
      paths beyond proof with only model responses faked. Kill after review artifact acceptance
      before event projection; replay must produce its single owned observation without executor
      append, and build-only must leave landing receipts absent. Falsifier: Restore Executor.run
      direct verdict.recorded emission; proof/event-owner must fail at the real emitter refusal on
      the full review path.
    falsified_by: >
      Restore Executor.run direct verdict.recorded emission; proof/event-owner must fail at the real
      emitter refusal on the full review path.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Make executor proof survive its producer and bind review eligibility to complete observed evidence.

## Context

Package C, W35 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R15, R46-R47, R51, and R76 require durable contextual proof. Accepting incomplete or fabricated proof can authorize unsupported publication. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Candidate integration and final gate evidence are W41 and W43. This item does not qualify live engines or channel approvals.

## Notes

D1 and D2 block durable accepted proof publication through B; D3 and D4 block the contained construction profile used in the full path. control_proof is a narrow proposed integration module, to be mapped into contracts before ready and inventoried under W30 if introduced. Preserve implementation commit, proof artifact or evidence commit, and later candidate as distinct subjects. W36 owns journal event projection; this item removes executor ownership violations without weakening events.emit. Use real ssh-keygen signing and Git object lookup. Retain the applied mutation and the specific failing row for each criterion. A review assertion remains an assertion, even when signed as an observed response.
