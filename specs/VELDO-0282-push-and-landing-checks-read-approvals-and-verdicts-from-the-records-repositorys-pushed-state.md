---
schema: veldo.spec/v1
id: VELDO-0282
title: The policy check, the push guard and the landing read proof, approvals and verdicts from the records repository's latest pushed state, and refuse by name when it cannot be fetched
status: draft
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0281, VELDO-0272, VELDO-0280]
placement: [enforcement]
protected_paths: [".veldo/policy_check.py", "engine/.veldo/policy_check.py", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", ".veldo/control_verification.py", "engine/.veldo/control_verification.py"]
footprint:
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - ".veldo/control_verification.py"
  - "engine/.veldo/control_verification.py"
  - ".veldo/records.py"
  - "engine/.veldo/records.py"
  - ".veldo/lander.py"
  - "engine/.veldo/lander.py"
  - ".veldo/control_landing.py"
  - "engine/.veldo/control_landing.py"
  - ".veldo/executor.py"
  - "engine/.veldo/executor.py"
  - ".veldo/landed_summary.py"
  - "engine/.veldo/landed_summary.py"
  - "scripts/suites/*veldo_0282*.py"
  - "specs/VELDO-0282-push-and-landing-checks-read-approvals-and-verdicts-from-the-records-repositorys-pushed-state.md"
  - "proof/VELDO-0282/**"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    Each check prints the records repository remote, branch and the pushed commit it read before its
    verdict, so a refusal and an allowance can both be traced to the exact records state. A fetch
    refusal names the remote, the branch and Git's error.
  metrics: >
    None added.
  traces: >
    None; one fetch and Git object reads per check.
  error_taxonomy: >
    New refusal: records_fetch_failed (the records repository's branch could not be fetched from its
    remote, so the pushed state is unknown). Existing refusal names, including VELDO-0272's
    approval_flag_lowered and landing_without_review, are unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      The checks read the pushed state, never a work tree. Before judging, policy_check.py, the push
      guard's proof manifest check and the landing's merge-ready check fetch the configured branch of
      the records repository and read records only from refs/remotes/origin/<branch> through Git object
      reads. A record present in the clone's work tree or in a local unpushed commit counts for nothing.
    falsified_by: >
      A fixture product repository with a protected path change and a local bare records remote: (1) a
      valid approval committed in the records clone but not pushed: policy_check exits 1 naming the
      protected path; (2) the same approval pushed: exit 0 and the log names the pushed commit; (3) the
      approval only in the clone's work tree: exit 1. A registered mutation that reads the work tree reds
      row (1).
  - id: AC2
    text: >
      Fail closed. When the fetch fails (remote unreachable, authentication refused, branch absent), every
      check exits non-zero with records_fetch_failed naming the remote and branch, and no cached earlier
      fetch is used in its place. A product push that touches no protected path is refused the same way:
      the guard's proof manifest check also needs the records state.
    falsified_by: >
      Fixture rows with the bare remote renamed away: policy_check, the guard and the landing check each
      exit non-zero naming records_fetch_failed, including when an earlier successful fetch left a
      remote-tracking ref holding a valid approval. A registered mutation that falls back to the existing
      remote-tracking ref on fetch failure reds that row.
  - id: AC3
    text: >
      Binding is to the product commit, as today. An approval or verdict counts only when it names this
      product repository and a product commit in the push range (the existing range rule in
      valid_approval_for and valid_verdict_for), with the existing scope.paths, expiry and no
      self-approval rules unchanged. A rewritten product history has new commits, so the old records no
      longer bind and a new approval is needed. A verdict's proof digest is compared with the manifest at
      proof/<id>/<product commit>/ in the records repository.
    falsified_by: >
      Rows: an approval naming another product repository's commit with the same hash prefix is refused;
      an approval bound to a commit that a rebase replaced is refused at the rebased push; a verdict whose
      digest names an older manifest of the same spec is stale; the self-approval row from the existing
      suite still refuses.
  - id: AC4
    text: >
      VELDO-0272's readers move with the records. approval_flag_lowered compares the newest revision of
      a spec covered by the push with its previous revision in the records repository, and is cleared
      only by an owner approval recorded under approvals/<spec id>/ that is not self-approved.
      landing_without_review and landed_summary.py read verdicts and approvals from the pushed state.
      The rule "spec first committed after approval_scope.from_commit" reads the spec's first revision
      record: a migrated spec carries the product commit that first added it (VELDO-0284), and a spec
      first recorded in the records repository is after that commit.
    falsified_by: >
      Fixture records repository rows: a revision lowering required to not_required with no approval:
      exit 1 approval_flag_lowered naming the spec; with an owner approval under approvals/<id>/: exit 0;
      with an approval whose approver is the producer: exit 1. A migrated spec whose first product commit
      precedes from_commit is not judged by the computed flag; a new spec is.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The checks read the product checkout's records again, which still hold every record
  until VELDO-0284. No record is rewritten by this spec.
---

## Intent

The owner's design (Telegram 39774): the checks read the records repository at its latest pushed state,
so every machine sees the same approvals, and an approval binds an exact product commit. This spec moves
the authentication of approvals and verdicts: the policy check, the push guard and the landing.

## Design

Today policy_check.py reads approvals and verdicts from the product work tree through verdict_corpus.py
(disk_corpus under ROOT/proof), the push guard requires proof/<spec>/manifest.json for HEAD through the
same enumeration, and the lander refuses missing_evidence:proof/<unit> when the manifest is absent at the
candidate's evidence commit. After VELDO-0281 those reads resolve to the records repository; this spec
makes them read the fetched remote-tracking ref only, and fail closed.

Reading the pushed state rather than a local clone is what makes one machine's approval visible to every
other machine and stops an unpushed local file from authorizing a push. The fetch is done on every check,
not cached, because a revoked or superseded record must be seen.

The range rule stays. valid_approval_for binds to any commit in the push range because today an approval
lands in an evidence commit that cannot name its own hash. With records outside the product repository
that reason is gone, and binding to the exact tip would become possible; it is not changed here, so
VELDO-0272 and VELDO-3440 in core keep their meaning. Narrowing it is a separate decision for the owner.

The evidence-only parent allowance in the guard is removed by VELDO-0280; this spec adds nothing in its
place, since evidence no longer makes a product commit at all.

Not a step for a builder: creating Bcengi/veldo-records is done by the lead at landing. The suites use a
local bare repository as the remote.

## Out of scope

The writer side (VELDO-0283); migrating Veldo's records (VELDO-0284); gate run results, which VELDO-0280
moved to the per-host store and which this spec does not read from the records repository; protecting
the records repository's own branch on GitHub (no force push, no deletion), which the lead configures at
creation.

## What the reviewer judges

- No check can be satisfied by a record that was not pushed.
- A fetch failure refuses every check, and nothing stale stands in for it.
- VELDO-0272's refusals keep their meaning with spec revisions as files.

## History

2026-11-07: written as a draft from the owner's decision, Telegram 39764 to 39774, approved design 39774.
It changes how approvals are authenticated and touches protected policy paths, so it is
approval-required.

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).
