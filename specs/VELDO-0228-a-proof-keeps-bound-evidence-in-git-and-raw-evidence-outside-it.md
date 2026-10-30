---
schema: veldo.spec/v1
id: VELDO-0228
title: A proof keeps in the repository only the evidence its manifest binds, by digest; raw evidence lives in a content-addressed store outside git; and a proof over its size budget is refused before landing
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: []
placement: [enforcement]
protected_paths: []
footprint:
  - specs/VELDO-0228-a-proof-keeps-bound-evidence-in-git-and-raw-evidence-outside-it.md
  - specs/index.md
  - proof/VELDO-0228/*
behavior_bearing: true
observability:
  logs: For each proof checked, the policy check prints its in-repository size, the budget, the count of digests resolved from the store and any that could not be resolved.
  metrics: Proof bytes in the repository per item; store bytes per item; unresolved digests.
  traces: Each landing record binds the proof manifest digest, which binds every stored evidence digest.
  error_taxonomy: A proof over its size budget is refused with its size, the budget and its five largest files; a manifest digest the store cannot produce is refused as missing evidence.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the repository holds a proof's manifest, its summaries and the evidence the manifest
      binds below a per-file threshold; larger bound evidence is stored by its sha256 in a
      content-addressed store outside git, and the manifest records the digest and size. Evidence
      the manifest does not bind is not committed. Proof: a builder run whose raw logs exceed the
      threshold lands with only digests in git and the store holding the bytes.
    falsified_by: >
      Commit a bound 30 MB log directly instead of its digest. The policy check refuses it.
  - id: AC2
    text: >
      Claim: the policy check refuses a proof whose in-repository size exceeds the budget (a
      declared number per item, default chosen from today's landed proofs) before landing, naming
      the size, the budget and the largest files.
    falsified_by: >
      Raise an item's proof past its budget with unbound files. The check stays green and the
      case reds.
  - id: AC3
    text: >
      Claim: every validator that reads proof evidence (proof validation, mutation rebinding,
      policy check) resolves a stored digest from the store and verifies its hash, so moving
      evidence out of git weakens no check.
    falsified_by: >
      Alter one byte of a stored object. Validation still passes and the case reds.
  - id: AC4
    text: >
      Claim: the store is durable and backed up with the repository (same host backup as
      the daily backup), and a missing object is reported as missing evidence, never skipped.
    falsified_by: >
      Delete a stored object a landed manifest binds. Validation passes and the case reds.
required_evidence: [integration]
rollback: >
  Revert the commit. Proofs commit raw evidence into git again and nothing bounds their size.
---

## Intent and established facts

On 2026-10-30 one core item's proof (VELDO-2260) reached 453 MB in about 2,750 files, more than all
proof already landed on core-integration (293 MB); most of it was superseded load experiments and
raw database logs. Pruned to what its manifest binds, it is 11.5 MB. VELDO-2270's proof was 141 MB
and VELDO-2230's 95 MB. Git keeps every committed blob forever, so each landing grows every clone.
Nothing today bounds proof size or keeps unbound evidence out.

## Design

To be designed (an architecture: components, interfaces, data flow, data model, deployment view)
and validated before build. Candidates the design must weigh, open source first: Git LFS with a
local LFS store, and a plain content-addressed directory with digests in the manifest. The design
also decides how a squash at landing interacts with proofs already committed on an agent branch.

## History

2026-10-30: created as a draft from the VELDO-2260 independent review (finding: 387 MB of proof
committed on the branch).
