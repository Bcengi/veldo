---
schema: veldo.spec/v1
id: VELDO-0105
title: The fix-validation rule has a start line - the owner records the commit it binds from, and history is not re-judged
status: shipped
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0020
work: W5
plan_revision: 4
depends_on: [VELDO-0104]
placement: [engine]
protected_paths: [".veldo/policy.yaml"]
footprint:
  - "engine/.veldo/fix_validation.py"
  - ".veldo/fix_validation.py"
  - "engine/.veldo/fix_validation_record.py"
  - ".veldo/fix_validation_record.py"
  - ".veldo/policy.yaml"
  - "scripts/suites/*_veldo_0105_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0105-fix-validation-start-line.md"
  - "specs/index.md"
  - "proof/VELDO-0105/*"
behavior_bearing: true
observability:
  logs: >
    Every proof check result names the start line's state: the commit it binds from, or that none
    is recorded, alongside the flag state it already prints.
  metrics: >
    Count bundles excluded by the start line, bundles in scope, and runs where the recorded start
    line could not be resolved in this repository.
  traces: >
    Bind the scope decision to the bundle's own commit, the recorded start line, and the ancestry
    answer that separated them.
  error_taxonomy: >
    Distinguish before-the-start-line, in-scope, no-start-line-recorded, and
    start-line-unresolvable-here.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A bundle whose commit is the recorded start line or a descendant of it is judged by the
      fix-validation rule; a bundle whose commit predates it is reported not applicable with that
      reason and is never refused for a missing validation record. Set: Real commits in a real
      repository, one before the line, one at it, one after it, each with a bundle carrying a review
      and a later fix commit and no validation record, with the flag on. Completeness: The ancestry
      is computed from the repository's own history, not from a field in the bundle, and the set
      includes a bundle on a branch that does not contain the line at all. Falsifier: Invert the
      ancestry test so a bundle predating the line is judged; proofcheck/start-line-excludes-history
      must fail.
    falsified_by: >
      Invert the ancestry test so a bundle predating the line is judged;
      proofcheck/start-line-excludes-history must fail.
  - id: AC2
    text: >
      Claim: An absent start line, and a recorded one this repository cannot resolve, both FAIL
      CLOSED: every bundle stays in scope and the reason is printed, so a missing or broken start
      line can never quietly switch the rule off. Set: The flag on with no start line recorded; the
      flag on with a start line naming a commit this repository does not have; the flag on with a
      start line naming a malformed value. Completeness: Each case is driven against a bundle that
      the rule would refuse, and the refusal is required to still happen. Falsifier: Make an
      unresolvable start line exclude every bundle;
      proofcheck/unresolvable-start-line-fails-closed must fail.
    falsified_by: >
      Make an unresolvable start line exclude every bundle;
      proofcheck/unresolvable-start-line-fails-closed must fail.
  - id: AC3
    text: >
      Claim: The start line is the owner's and is read only from .veldo/policy.yaml, a protected
      path; nothing an author writes into a manifest, a validation record or a bundle can move it.
      Set: A bundle whose manifest and whose validation record both carry a start line of their own,
      naming a later commit than the policy's. Completeness: The author-supplied values are present
      and well formed, so the test fails if they are read at all rather than merely being absent.
      Falsifier: Read the start line from the manifest when the policy does not name one;
      proofcheck/start-line-not-author-writable must fail.
    falsified_by: >
      Read the start line from the manifest when the policy does not name one;
      proofcheck/start-line-not-author-writable must fail.
required_evidence: [unit, integration]
rollback: >
  Remove the recorded start line. The rule returns to judging every bundle, which is the behaviour
  VELDO-0104 shipped, and no evidence is invalidated.
---

## Intent

A new gate binds the work that comes after it, not the work that shipped before it existed.

## Context

PLAN-0020, W5. VELDO-0104 shipped the rule and its owner flag. Turning that flag on was tried against the whole corpus before it was committed, and thirteen proof bundles that shipped months ago went red: VELDO-0001 through VELDO-0012 and one more. They carry a review and fix commits after it, which is exactly what the rule refuses, and no validation record, because the runner and the assessor that produce one did not exist when they landed. VELDO-0012 showed eight fix rounds against a cap of two and parked retroactively.

The rule was doing what its specification says. What the specification never said is where it starts. Dmitry chose the start line (Telegram 28436, answering the ask 28434) over the two alternatives: leaving the rule advisory forever, and back-filling thirteen validation records that cannot be written honestly, because those reviews happened before the runner existed and there is no true reproduction to re-run.

**Why the line is a commit and not a date.** A date has to be compared against something, and the only timestamps near a bundle are the author's. A commit is a position in a history the author cannot rewrite under the gate, and the ancestry question, is this bundle's commit a descendant of the line, is answered by the repository rather than by anything in the bundle.

**Why it lives in the policy file.** The same reason the flag does. A check that decides whether it applies from a field the author writes binds only on authors who volunteer it, and the whole point of this rule is to bind the author of a fix. `.veldo/policy.yaml` is a protected path, so the owner sets the line and the party being gated cannot move it. AC3 exists to keep that true: it plants a well-formed start line in the manifest and in the validation record, and fails if either is ever read.

**Why absence fails closed.** An owner who sets `required: true` and nothing else gets the behaviour VELDO-0104 shipped: every bundle in scope. A start line that this repository cannot resolve gets the same answer and says so. The dangerous direction is the other one, where a typo in a commit id silently exempts everything, and AC2 is what stops it.

## Out of scope

The thirteen historical bundles are not modified, re-reviewed or re-validated, and their shipped state does not change. Nothing about the rule's content changes: what a validation record must contain, and the two-round cap, are VELDO-0104's and stay as they are.

## Notes

The start line is recorded once the implementation is green, and the value is the commit that lands this item, so the first bundle the rule binds is the next one after it. That recording is an owner act on a protected path, not part of the build.
