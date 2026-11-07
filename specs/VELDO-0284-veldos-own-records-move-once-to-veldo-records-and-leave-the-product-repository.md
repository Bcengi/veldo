---
schema: veldo.spec/v1
id: VELDO-0284
title: Veldo's own specs, plans, proof, verdicts and approvals are copied once into veldo-records at their current state and removed from the Veldo repository, Veldo is configured with veldo-records, and an unconfigured checkout is refused by name
status: ready
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0281, VELDO-0282, VELDO-0283]
placement: [enforcement, contracts]
protected_paths: [".veldo/policy.yaml"]
footprint:
  - ".veldo/policy.yaml"
  - ".veldo/records.py"
  - "engine/.veldo/records.py"
  - ".veldo/*.py"
  - "engine/.veldo/**"
  - "scripts/*.py"
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "scripts/records_migrate.py"
  - "scripts/suites/**"
  - "bin/veldo"
  - "specs/**"
  - "plans/**"
  - "proof/**"
  - "VELDO.md"
  - "CLAUDE.md"
  - "engine/VELDO.md"
  - "engine/CLAUDE.md"
  - ".gitignore"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    The migration tool prints, per kind, the number of records read from the Veldo commit it migrates
    and the number written, and names every file it could not place. Every reader logs the records
    commit it read (VELDO-0281).
  metrics: >
    None added.
  traces: >
    None.
  error_taxonomy: >
    New refusal: records_repository_unconfigured (a product checkout whose policy names no records
    repository; no reader falls back to the checkout's own specs/, plans/ or proof/). The fallback that
    VELDO-0281 left for unconfigured checkouts is removed.
acceptance_criteria:
  - id: AC1
    text: >
      One copy at a named state. scripts/records_migrate.py reads specs/, plans/ and proof/ from one named
      Veldo commit (the commit before this spec's removal commit) and writes them into the records
      repository in VELDO-0281's layout: each spec as its one file carrying the Veldo commit that first
      added it, each plan likewise, the emergency.push and emergency.closed lines of the tracked
      .veldo/events.jsonl as one governance record each (read by the guard from the records repository
      afterwards, like approvals), each proof bundle with a manifest under
      proof/<id>/<manifest commit>/ with its cited artifacts, each bundle with no manifest (119 today)
      under proof/<id>/unbound/, and each approval and verdict as its own record. Record content is
      byte-identical to the source; only the location changes. It runs once; a second run against a
      records repository that already holds a record refuses record_exists (VELDO-0283) and writes
      nothing. History is not copied: it stays in Veldo's git history.
    falsified_by: >
      An integration row runs the tool against a fixture Veldo commit with specs, a plan, a bundle with a
      manifest, a bundle without one, a verdict, an approval, an emergency.push line and the prose-scope approval shape of
      proof/WARP-0620/approval-dmitry.json: every source file appears once at its mapped path with the
      same sha256, the count per kind matches, and a second run exits record_exists with the remote
      unchanged.
  - id: AC2
    text: >
      Removed from the product repository. One commit deletes specs/ (including specs/index.md), plans/
      and proof/ from Veldo, adds records_repository naming Bcengi/veldo-records to .veldo/policy.yaml,
      removes VELDO-0281's fallback so an unconfigured checkout refuses records_repository_unconfigured,
      removes the specs/index.md freshness check, and updates VELDO.md and CLAUDE.md (repository and
      engine copies) to say where specs, proof and approvals live.
    falsified_by: >
      At the removal commit: git ls-tree shows no specs/, plans/ or proof/; a fixture checkout of it with
      records_repository deleted exits 1 naming records_repository_unconfigured from validate.py,
      policy_check.py and the guard; with the fixture records remote configured, the full gate is green.
  - id: AC3
    text: >
      Every reader is proven to use the new home. A census (scripts/records_census.py, run by the gate)
      lists every engine and script reference to specs/, plans/ or proof/ and fails on any that does not
      go through records.py; the proof bundle records the list of the about seventy modules found today
      and how each now resolves. With the product checkout given a planted specs/ and proof/ holding a
      conflicting spec and a forged approval, the validator, policy check, guard, landing, index,
      dashboard and metrics readers each report the records repository's content and none the planted
      files.
    falsified_by: >
      A registered mutation that changes one reader (dashboard.py) back to ROOT / "specs" reds the
      census; the planted-files row fails under the same mutation, naming dashboard.py.
  - id: AC4
    text: >
      Approval semantics carry over. Every approval that was valid for an unlanded Veldo branch before the
      migration is valid after it against the records repository (same product commit, paths, expiry and
      approver), and VELDO-0272's approval_scope.from_commit judges a migrated spec by the first-commit
      field AC1 writes, so no spec changes which side of that line it falls on.
    falsified_by: >
      A row takes every approval file at the migrated commit, evaluates valid_approval_for for its bound
      commit before and after the migration, and asserts identical answers; a second row asserts each
      migrated spec's in-scope answer for the computed flag equals the answer from Veldo's git history.
required_evidence: [unit, integration]
rollback: >
  Revert the removal commit: specs/, plans/ and proof/ return to Veldo at their migrated state and the
  fallback returns. Records added to veldo-records after the migration would then be missing from Veldo;
  rolling back after new work has landed therefore needs those records copied back, which the migration
  tool's reverse mode does by the same mapping.
---

## Intent

The owner's design (Telegram 39774): Veldo keeps only code, tests and product docs; its delivery records
live in veldo-records, copied once at their current state, with history left in Veldo's own git history.

## Design

Order: VELDO-0281 (readers), VELDO-0282 (checks), VELDO-0283 (writers) land first, so that when this
spec deletes the directories nothing reads or writes them. This spec is also where the refusal of an
unconfigured checkout lands, because it is the commit that configures Veldo: in any earlier spec the
refusal would turn Veldo's own gate red.

Measured on Veldo main afa292f0 (2026-11-07): specs/ holds 426 files (5.5 MB), plans/ 21 files, proof/
323 bundle directories (108 MB), of which 203 carry a manifest.json and 119 do not; 54 approval files and
188 verdict files under the corpus patterns. The copy is a deliberate one-way move of the current state,
not a history rewrite: every existing proof's digest stays valid because the bytes are unchanged.

Not steps for a builder, but for the lead at landing: create Bcengi/veldo-records (private) in the Bcengi
GitHub organization, protect its default branch against force push and deletion, grant the factory
identity push, run the migration tool against it once, and only then land the removal commit. A builder
proves the tool and the removal against a local bare repository.

## Out of scope

Gate run results (VELDO-0280). .veldo/decisions and .veldo/decision_reviews, which
are engine contract records, not delivery records. Core (VELDO-3600 in the core repository).

## What the reviewer judges

- Every record is in veldo-records with unchanged bytes, and none remains in Veldo's tree.
- No reader can be satisfied by a file in the product checkout.
- No approval or spec changes its meaning in the move.

## History

2026-11-07: written as a draft from the owner's decision, Telegram 39764 to 39774, approved design 39774.
It changes the policy file and moves every approval, so it is approval-required.

2026-11-07: lead amendment: the emergency.push and emergency.closed lines that VELDO-0280 keeps in the tracked .veldo/events.jsonl move with the other governance records into veldo-records in this migration (owner principle, Telegram 39764: "Software should not have its sdlc bits in git"); the builder adds them to the migrated set and the guard reads them from the records repository like approvals.

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).

2026-11-07: ready. Owner approved, Telegram 39787 ("Approve all five" to 39779, which named VELDO-0281 to 0284 and VELDO-3600).
