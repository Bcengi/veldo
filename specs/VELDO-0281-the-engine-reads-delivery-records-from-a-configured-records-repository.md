---
schema: veldo.spec/v1
id: VELDO-0281
title: The engine reads specs, plans, proof, verdicts and approvals from a configured records repository, one file per record, added and never edited, with the index generated on demand
status: draft
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0272, VELDO-0280]
placement: [enforcement, contracts]
protected_paths: [".veldo/policy.yaml"]
footprint:
  - ".veldo/policy.yaml"
  - ".veldo/records.py"
  - "engine/.veldo/records.py"
  - ".veldo/verdict_corpus.py"
  - "engine/.veldo/verdict_corpus.py"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - "scripts/update_index.py"
  - "engine/scripts/update_index.py"
  - "scripts/suites/*veldo_0281*.py"
  - "specs/VELDO-0281-the-engine-reads-delivery-records-from-a-configured-records-repository.md"
  - "proof/VELDO-0281/**"
behavior_bearing: true
observability:
  logs: >
    Every reader that resolves the records root names, once per run, the records repository remote, the
    branch and the commit it read. A refusal names the error and the configuration key or path at fault.
  metrics: >
    None added.
  traces: >
    None; resolution is one read of configuration and one Git object lookup.
  error_taxonomy: >
    New refusals: records_root_missing (configured, but no local clone at the host path),
    records_remote_mismatch (the local clone's origin is not the remote the policy names),
    record_modified (a record path whose content changed after it was first added, or was deleted).
acceptance_criteria:
  - id: AC1
    text: >
      One module, .veldo/records.py, is the only resolver of where records live. .veldo/policy.yaml
      gains records_repository: {remote, branch}; the local clone path is per host configuration, never
      committed. records.root() returns the clone's work tree after checking its origin URL equals the
      policy remote (records_remote_mismatch otherwise). When records_repository is configured, no
      reader this spec routes reads the product checkout's own specs/, plans/ or proof/, even when those
      directories exist. With it absent, records.root() returns the product root, which is the state
      until VELDO-0284; VELDO-0284 removes that branch and replaces it with the named refusal
      records_repository_unconfigured.
    falsified_by: >
      Fixture product checkouts: (1) configured, with conflicting specs/ and proof/ also present in the
      product checkout: validate.py and update_index.py read only the records repository's files;
      (2) configured, clone absent: records_root_missing naming the host path; (3) clone with another
      origin: records_remote_mismatch naming both URLs. A registered mutation that reads ROOT / "specs"
      when configured reds row (1).
  - id: AC2
    text: >
      The records repository layout is fixed and each record is one file: specs/<id>/<revision>.md (a
      spec change, including a status change or a History line, adds a new revision file and the highest
      revision is the spec), plans/<id>/<revision>.md, proof/<id>/<product commit>/manifest.json with the
      artifacts it cites beside it, proof/<id>/verdicts/<reviewer>-<product commit>-<utc stamp>.json and
      approvals/<id>/<approver>-<product commit>-<utc stamp>.json. Every proof, verdict and approval
      record names the product repository and the product commit it covers. No two writers can choose
      the same file name for different records.
    falsified_by: >
      A unit row builds a fixture records repository with two revisions of one spec, a verdict and an
      approval, and asserts the resolver returns the higher revision and binds each record to its
      product commit. A record missing the product repository or commit is refused by the validator
      naming the field.
  - id: AC3
    text: >
      Records are only ever added. The validator reads the records repository history and refuses
      record_modified for any record path whose blob changed, or which was deleted, after the commit
      that first added it, naming the path and both commits. The verdict corpus enumeration
      (verdict_corpus.py) and every corpus pattern it owns resolve under records.root(), so there stays
      one spelling of each corpus set.
    falsified_by: >
      Fixture records repository rows: an approval file edited in a later commit is refused
      record_modified; the same file deleted is refused; a new file beside it is valid. A registered
      mutation that skips the history read reds the edit row.
  - id: AC4
    text: >
      Shared lists are generated, never committed. update_index.py writes the index for the configured
      records repository to standard output or a path the caller names outside both repositories, and
      the validator refuses an index file committed in the records repository. The product repository's
      committed specs/index.md and its freshness check are removed by VELDO-0284, not here.
    falsified_by: >
      A fixture records repository with three specs: update_index.py prints the three in their status
      groups and writes nothing in either repository; a committed specs/index.md in the records
      repository is refused naming it.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. Readers go back to the product checkout's own directories, which still hold every
  record until VELDO-0284 removes them. Veldo itself is not configured with a records repository until
  VELDO-0284, so this spec changes no reading in Veldo's own gate.
---

## Intent

The owner decided on 2026-11-07 (Telegram 39764 to 39774) that a product repository keeps only code,
tests and product docs, and that delivery records (specs, plans, owner approvals, review verdicts and
proof summaries) live in a parallel private repository per product: veldo-records beside Veldo, core-veldo
beside core. This spec is the reader side only: where records are, in what shape, and the refusal when a
checkout has no records repository. VELDO-0282 makes the push and landing checks read the records
repository's pushed state; VELDO-0283 moves the factory's writes there; VELDO-0284 migrates Veldo's own
records, configures Veldo with veldo-records, deletes the records from this repository and turns an
unconfigured checkout into the named refusal.

Why the refusal is not in this spec: if it were, Veldo's own gate would refuse at this spec's commit,
because Veldo has no records repository until the migration, so this spec could never be green alone.
The refusal lands in the same commit that configures Veldo (VELDO-0284).

## Design

Today every reader resolves records relative to the product root: validate.py reads ROOT/specs and
ROOT/plans, policy_check.py and the guard reach proof/ through verdict_corpus.py (PROOF_ROOT = "proof",
APPROVAL_PATTERN = "approval*.json"), update_index.py writes ROOT/specs/index.md, and about seventy
modules under .veldo/ and scripts/ name specs/, plans/ or proof/ (found by a scan; the proof bundle lists
them). This spec adds records.root() and routes the validator, verdict_corpus.py and update_index.py
through it; the remaining readers move in VELDO-0282 and VELDO-0284, which proves the scan empty.

The remote and branch are in .veldo/policy.yaml, a protected path, because pointing the checks at another
repository would let an agent supply its own approvals. The clone's host path is per host configuration,
because checkout locations differ by machine.

Append-only is the rule that removes merge conflicts between machines and makes every approval and
verdict auditable: a spec is a sequence of revision files, not a file edited in place. The revision field
the spec contract already carries (raised on a criteria change) is the file name; a status change or a
History line adds the next file with a suffix (for example 3.1) and does not raise the contract revision,
so no proof goes stale.

Not a step for a builder: creating the GitHub repository Bcengi/veldo-records (private) is done by the
lead at landing. A builder works against a fixture records repository and a local bare remote.

## Out of scope

The refusal of an unconfigured checkout (VELDO-0284); the checks' fetch of the pushed state and fail closed behaviour (VELDO-0282); the factory's writes
(VELDO-0283); moving existing records (VELDO-0284); gate run results, which VELDO-0280 moves to the
per-host store; the Claude pack's init scaffold, which needs its own spec so that a newly installed
repository is configured with a records repository instead of being refused.

## What the reviewer judges

- No reader can reach the product checkout's own record directories when the records repository is
  unconfigured.
- The layout gives every record exactly one file, and no record is rewritten to change state.
- The remote is read from a protected file and checked against the clone.

## History

2026-11-07: written as a draft from the owner's decision, Telegram 39764 to 39774, approved design 39774.
It changes the policy file and how approvals are found, so it is approval-required.
