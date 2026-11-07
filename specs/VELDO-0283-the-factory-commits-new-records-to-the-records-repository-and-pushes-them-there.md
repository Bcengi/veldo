---
schema: veldo.spec/v1
id: VELDO-0283
title: The factory's own commits of new specs, plans, proof, verdicts and approvals go to the records repository and are pushed there, never to the product repository
status: ready
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0281, VELDO-0282]
placement: [enforcement, contracts]
protected_paths: ["scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh"]
footprint:
  - ".veldo/records.py"
  - "engine/.veldo/records.py"
  - ".veldo/control_proof.py"
  - "engine/.veldo/control_proof.py"
  - ".veldo/control_landing.py"
  - "engine/.veldo/control_landing.py"
  - ".veldo/lander.py"
  - "engine/.veldo/lander.py"
  - ".veldo/executor.py"
  - "engine/.veldo/executor.py"
  - ".veldo/control_document.py"
  - "engine/.veldo/control_document.py"
  - ".veldo/control_decomposition.py"
  - "engine/.veldo/control_decomposition.py"
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - "packs/claude/**"
  - "scripts/suites/*veldo_0283*.py"
  - "specs/VELDO-0283-the-factory-commits-new-records-to-the-records-repository-and-pushes-them-there.md"
  - "proof/VELDO-0283/**"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    Every record write logs the record path, the records repository commit that added it and the pushed
    commit after the push. A refusal names the record path and the reason.
  metrics: >
    None added.
  traces: >
    None.
  error_taxonomy: >
    New refusals: record_exists (a writer asked to add a record at a path that already holds one),
    records_push_failed (the commit was made but could not be pushed; the record does not count until it
    is), record_in_product_tree (a product commit adds a file under specs/, plans/ or proof/).
acceptance_criteria:
  - id: AC1
    text: >
      One writer. records.add(kind, record) is the only code that writes a record: it writes one new file
      at the AC2 path of VELDO-0281 in the records clone, commits only that file as the factory identity,
      and pushes to the configured branch. It refuses record_exists rather than overwrite. Every factory
      path that writes a spec revision, plan revision, proof manifest and artifacts, verdict or approval
      calls it; none writes under the product checkout's specs/, plans/ or proof/.
    falsified_by: >
      A fixture factory run (spec drafted, built, proven, reviewed, approved) against a fixture product
      repository and a local bare records remote: the product repository's commits touch no file under
      specs/, plans/ or proof/, and the records remote gains one commit per record, each adding exactly
      one record file (a proof record adds its manifest and the artifacts it cites in one commit). A
      second add to the same path exits record_exists and leaves the file unchanged.
  - id: AC2
    text: >
      Concurrent writers converge. When the push is rejected because the branch moved, the writer fetches,
      rebases its one-file commit onto the new tip and pushes again, a bounded number of times; since no
      two writers choose the same path (VELDO-0281 AC2), the rebase never conflicts. When the push still
      fails, it reports records_push_failed and the caller treats the record as not recorded.
    falsified_by: >
      Two fixture writers adding different records from two clones at once: both records are on the
      remote branch afterwards and the history is linear. A remote that refuses every push: the writer
      exits records_push_failed and a following policy_check does not see the record.
  - id: AC3
    text: >
      The proof service binds to the product commit, not to an evidence commit. control_proof accepts a
      bundle whose manifest and artifacts are read from the records repository's pushed state at
      proof/<id>/<product commit>/, with the spec revision read from the records repository by its
      sha256; the built commit is the implementation commit itself. The rule that a built commit may
      differ from the implementation commit only under proof/<unit>/ is removed, and the lander no longer
      looks for evidence in the candidate tree (missing_evidence:proof/<unit> now names the records path).
    falsified_by: >
      Fixture rows: a bundle pushed to the records remote is accepted for the product commit it names; the
      same bundle with one artifact's bytes changed is refused naming the artifact and digest; a product
      candidate carrying a proof/ directory of its own is refused record_in_product_tree.
  - id: AC4
    text: >
      The product guard refuses records in the product tree. The push guard refuses
      record_in_product_tree for any product commit in the push range that adds or changes a file under
      specs/, plans/ or proof/ once the product checkout is configured with a records repository.
    falsified_by: >
      Fixture configured product repository: a push adding proof/VELDO-9999/manifest.json exits 1 naming
      the path; the same push without it exits 0.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. Writers go back to the product checkout. Records already pushed to the records
  repository stay there and are still read by VELDO-0281 and VELDO-0282, so nothing is lost.
---

## Intent

The owner's design (Telegram 39774): software should not have its delivery bits in its git. After the
readers (VELDO-0281) and the checks (VELDO-0282) read the records repository, the factory's own writes
must go there too, or new records would land where nothing reads them.

## Design

Today the factory adds a spec, plan, proof bundle, verdict or approval as a file in the product
repository and commits it there, most visibly as the "evidence commit" on top of an implementation
commit, which control_proof accepts only when it changes nothing outside proof/<unit>/, and from which
the lander reads the manifest. Moving the writes removes the evidence commit: the product branch is code
only, and the proof binds to the implementation commit directly.

One file per record and per-writer unique names (VELDO-0281 AC2) make concurrent pushes from several
machines a plain rebase with no conflict. A record not yet pushed does not count (VELDO-0282 AC1), so a
failed push is a failure, never a silent local success.

The plugin pack's commands that write specs and proof (packs/claude) call the same writer, so an agent
working in a session and the factory produce the same records.

Not a step for a builder: the lead creates Bcengi/veldo-records at landing and grants the factory
identity push access to it. The suites use a local bare repository.

## Out of scope

Moving existing records (VELDO-0284); gate run results (VELDO-0280).

## What the reviewer judges

- There is one writer, and no code path writes a record into the product checkout.
- A record that did not reach the remote is never treated as recorded.
- The removal of the evidence commit does not weaken what control_proof verifies about artifacts.

## History

2026-11-07: written as a draft from the owner's decision, Telegram 39764 to 39774, approved design 39774.
It changes where approvals are written and the push guard's rule, so it is approval-required.

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).

2026-11-07: ready. Owner approved, Telegram 39787 ("Approve all five" to 39779, which named VELDO-0281 to 0284 and VELDO-3600).
