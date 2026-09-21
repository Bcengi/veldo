---
schema: veldo.spec/v1
id: VELDO-0106
title: The owner's two settings are read exactly as written - the policy reader, and a start line that must be a commit id
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0020
work: W6
plan_revision: 5
depends_on: [VELDO-0105]
placement: [engine]
protected_paths: []
footprint:
  - "engine/.veldo/fix_validation_record.py"
  - ".veldo/fix_validation_record.py"
  - "scripts/suites/*_veldo_0106_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0106-policy-read-exactly-as-written.md"
  - "specs/index.md"
  - "proof/VELDO-0106/*"
behavior_bearing: true
observability:
  logs: >
    Every proof check result already names the flag state and the start line; a start line that is
    not a commit id is named as refused with the value it was given.
  metrics: >
    Count runs where the recorded start line was refused for its shape.
  error_taxonomy: >
    Distinguish start-line-not-a-commit-id from the existing start-line-unresolvable-here, because
    a value the owner mistyped and a value this repository simply does not have are different
    problems with different repairs.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner's two settings are read from .veldo/policy.yaml by the reader that handles
      the whole of its syntax, so a trailing comment on either line, on the block form or the
      inline form, changes neither the flag nor the start line, and a hash inside a quoted string
      is text rather than a comment. Set: The six shapes the file can take, each written to a real
      file and read through the real call site rather than a hand-built dictionary. Completeness:
      The general parser's answer is computed beside the reader's for every shape, so the row fails
      if the call site is ever pointed back at the general parser. Falsifier: Read the policy with
      the general parser at the call site; policyread/a-comment-does-not-disarm-the-rule must fail.
    falsified_by: >
      Read the policy with the general parser at the call site;
      policyread/a-comment-does-not-disarm-the-rule must fail.
  - id: AC2
    text: >
      Claim: A recorded start line must be a full forty-character commit id. Anything else, a
      branch or tag name, an abbreviated id, a value with a leading zero that a general parser
      would coerce to a number, is REFUSED for its shape, every bundle stays in scope, and the
      reason names the value. Set: A 40-hex id, an abbreviated id, a branch name that really
      resolves in the fixture repository, a tag, a leading-zero numeric value, and an empty value.
      Completeness: The branch and the tag genuinely resolve, so the row fails if resolvability is
      what is being tested rather than shape. Falsifier: Accept any value git can resolve;
      policyread/a-branch-is-not-a-start-line must fail.
    falsified_by: >
      Accept any value git can resolve; policyread/a-branch-is-not-a-start-line must fail.
  - id: AC3
    text: >
      Claim: The shared parser is NOT changed by this item, and the measurement that says why is
      kept: stripping trailing comments inside it alters the parse of documents this repository
      has already shipped. Set: Every document the shared parser reads in this repository. 
      Completeness: The comparison runs over the real corpus rather than a fixture, and reports
      the count and the affected field names. Falsifier: Make the shared parser strip trailing
      comments; policyread/the-shared-parser-is-left-alone must fail.
    falsified_by: >
      Make the shared parser strip trailing comments; policyread/the-shared-parser-is-left-alone
      must fail.
required_evidence: [unit]
rollback: >
  Point the call site back at the general parser and drop the shape check. The rule returns to the
  behaviour VELDO-0105 shipped, and no evidence is invalidated.
---

## Intent

The two settings that decide whether the gate refuses are read exactly as the owner wrote them.

## Context

PLAN-0020, W6. An adversarial read of the W5 landing found that they are not. Measured on the live file's own reader:

A trailing comment on `required: true` makes the flag read **false**. The rule the owner has just armed silently returns to advisory, with no error anywhere, and every problem it would have refused prints as a warning instead. On the inline form the same comment loses the start line too. And `from_commit: 0123456` is coerced to an integer, so the leading zero is dropped and the value comes back as `123456`, a different commit id.

All three come from the general parser: it strips whole-line comments but not trailing ones, and it turns digit-only values into integers. The repository has three readers of this file and they give two different answers, which is the same shape as the defect W5 already fixed.

**Why the obvious repair is not the repair.** The general parser could learn to strip trailing comments, which is what YAML does and what the fix-validation module's own reader already does, and the repository has a `reuse_one_parser` pattern that argues for it. That change was measured against the corpus before being attempted: **55 of its 328 specifications and plans parse differently under it**, 49 of them in `acceptance_criteria` text and the rest in `risk`, `constraints` and `status` fields containing a hash. AC3's row recomputes that count on every run and prints it, rather than pinning a number the corpus will move. It would silently truncate the text of specifications that have already shipped, to fix a flag nobody had yet tripped, and the gate would go green on it because nothing compares a specification's text across a parser change. The measurement is kept as AC3 so a later reader does not try it again.

So the fix is narrow. The fix-validation module already carries `read_policy`, which handles all six shapes correctly, and the call site uses it instead of the parser the validator hands in. That parser is still handed in and still used for the spec front matter beside it; only the policy read changes.

**Why the start line must be a full commit id.** Two of the three symptoms are really one: a value that is not an object id. A branch name resolves, and resolves to something different tomorrow, and the ref namespace is not a protected path, so the owner's line could move without the owner. An abbreviated id can become ambiguous as history grows. A leading-zero value is the parser's coercion showing through. Requiring forty hex characters refuses all three by shape, before anything is resolved, and says what it was given.

## Out of scope

The shared parser is deliberately unchanged, and so is the integer coercion in it. The other readers of the policy file are not consolidated here; this item makes the two settings that gate a landing read correctly, and leaves the wider parser question to an item that can carry the corpus migration it would need.

## Notes

`read_policy` and `_strip_comment` already exist and are already tested by VELDO-0104's suite; this item does not write a second stripper. The refusal is by shape and happens before `_commit_exists`, so a mistyped line and a line this repository does not have stay distinguishable in the output.
