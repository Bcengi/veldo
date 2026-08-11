---
schema: veldo.spec/v1
id: WARP-0114
title: Approval binding must be satisfiable - bind to the push range, not HEAD
status: shipped
risk: high    # changes .veldo/policy_check.py, protected as of WARP-0113
owner: dmitry
human_approval: required
lane: standalone
protected_paths: [.veldo/policy_check.py]
acceptance_criteria:
  - id: AC1
    text: valid_approval_for accepts an approved, unexpired approval bound to
      ANY commit in the push range (upstream..HEAD with the same fallback
      changed_files uses), and rejects approvals bound outside the range,
      expired, or with a non-canonical decision (unit-tested with an isolated
      proof root).
  - id: AC2
    text: The full push-time allow path is demonstrated live for the first
      time - policy_check.py exits 0 at the batch HEAD with protected paths
      touched, because the recorded approvals bind to in-range commits; and
      it exits 1 when the approvals are hidden (negative demonstration).
required_evidence: [unit, operational]
rollback: git revert; the change widens approval matching from one commit
  (HEAD, unsatisfiable by construction) to the push range while keeping
  decision, expiry, and exact-commit binding; nothing else in policy_check
  changes.
---

## Intent

Dogfooding the first protected-path push found the enforcement's allow path
mechanically unsatisfiable: the approval record lands in an evidence commit,
and no file can name the hash of the commit that will contain it, so
requiring scope.commit to prefix HEAD can never be met. Verdicts already
acknowledge this shape with a parent fallback; approvals had none - meaning
every prior demonstration showed the BLOCK path only, and the first real
approved push would have been stuck. The guarantee that matters is kept: the
approval names an exact commit that is part of what is being pushed, on the
record, unexpired.

## Context

Standalone lane, defect found by running the machinery on itself (the
WARP-0100/0113 batch is the first push in this repository to touch protected
paths). The reviewer-noted enforcement themes of WARP-0113 made
policy_check.py protected, so this fix itself requires and demonstrates the
approval flow it repairs.

## Out of scope

Verdict-proof digest binding and approval self-separation remain W9 of
PLAN-0001.
