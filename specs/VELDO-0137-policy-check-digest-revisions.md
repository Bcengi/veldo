---
schema: veldo.spec/v1
id: VELDO-0137
title: policy_check reads a VELDO-0050 proof's digest-form spec revision
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0050]
placement: [enforcement]
protected_paths: [".veldo/policy_check.py", "engine/.veldo/policy_check.py"]
footprint:
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - "scripts/suites/*_veldo_0137_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0137-policy-check-digest-revisions.md"
  - "specs/index.md"
  - "proof/VELDO-0137/*"
behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A VELDO-0050 proof whose spec_revision is 'sha256:' and the digest of the spec document
      committed at the proof's own implementation commit is current in policy_check's stale-proof
      check, before and after a later edit that raises nothing, beside an integer-form proof judged
      as before. Set and completeness: Drive the real policy_check over a temporary repository with
      one digest-form and one integer-form manifest, then add a History line to the spec; neither
      proof is stale. Falsifier: Read the digest-form revision with int() again; the current-proof
      row must fail.
    falsified_by: >
      Read the digest-form revision with int() again; the current-proof row must fail.
  - id: AC2
    text: >
      Claim: A digest-form proof is stale when its digest does not name the spec committed at its
      commit, when the commit is not a full id or does not exist, and when the spec's declared
      revision has been raised since that commit. Set and completeness: Drive each case over the
      same repository; each is stale, and raising the declared revision makes the integer-form proof
      stale too. Falsifier: Never compare the digest with the committed spec; the stale-proof row
      must fail.
    falsified_by: >
      Never compare the digest with the committed spec; the stale-proof row must fail.
required_evidence: [unit]
rollback: >
  Revert the policy_check change; digest-form proofs are then stale again, which refuses and never
  admits.
---

## Intent

VELDO-0050 records a proof's accepted spec revision as the digest of the exact spec bytes.
policy_check.spec_revision_stale read every revision with int(), so every such proof counted as
stale; because the check reads every manifest in the repository, one factory proof on trunk refused
every later policy_check run there (VELDO-0056's review, 2026-09-24). This change teaches the check
the digest form without weakening it.

## Context

Found by VELDO-0056's builder and widened by its review. policy_check.py is a protected path; the
owner approved this change on Telegram (29057 asked, 29058 "Approved", 2026-09-24).

## Out of scope

Any other policy_check behavior. How VELDO-0050 accepts a proof (its proof service already binds
the proof to the exact accepted spec bytes).

## What the reviewer judges

- Normal use: policy_check runs over a repository holding VELDO-0050 proofs and older integer-form
  proofs. A digest-form proof is current when its digest is the spec committed at its own
  implementation commit and the spec's declared revision has not been raised since; a History-only
  edit at landing leaves it current. Integer-form proofs are judged exactly as before.
- Threat model: a digest that names no committed spec, a short or absent commit, a raised declared
  revision, and any shape the check cannot name for certain, each of which must count as stale
  (fail closed). The owner's account, Git and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged
  manifests or rows in our own repository; performance of the check over a very large proof
  corpus.

## Notes

The accepted revision is read at the proof's own implementation commit because VELDO-0050 refuses a
build that changes its spec, so the spec there is exactly the accepted bytes, and later edits that
only append History do not make a proof stale.

## History

2026-09-24: written, implemented and proved by the lead on the owner's approval (Telegram 29058).
Suite 68_veldo_0137_policy_revision (2 rows), red at cae421a on the current-proof row, 4 mutations
as finding 137.
