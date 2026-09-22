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
      inline form, changes neither the flag nor the start line; a hash inside a quoted string is
      text rather than a comment; a comma inside a quoted string does not begin a new setting; the
      block is found at any indentation; and only the block's direct members are its settings.
      Set: Seventeen regression examples, each written to a real file and read through the
      real call site rather than a hand-built dictionary. Eleven of them are bypasses three separate
      reviews demonstrated against earlier versions of this reader, including one that moved the
      start line forward and silently exempted every bundle between the owner's commit and it.
      Completeness: These examples have an independent PyYAML oracle, not a coverage proof.
      The oracle receives the same inputs; it adds no cases. It stands down by name when PyYAML
      is absent and excludes YAML 1.1 octal coercion of leading-zero identifiers.
      Accepted syntax and refusal boundaries are defined separately by the strict shared reader's
      written grammar in .veldo/yamlish.py (VELDO-0110), with policy schema checks in read_policy.
      Exhaustive agreement across that grammar is INTENDED and NOT YET DEMONSTRATED.
      Falsifier: Read the policy with the general parser at the call site;
      policyread/a-comment-does-not-disarm-the-rule must fail.
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
  - id: AC4
    text: >
      Claim: The reader has exactly three answers and no fourth. A file that is absent or carries no
      fix_validation key is advisory. A block it can read EXACTLY is that block. Everything else is
      REFUSED, and the call site turns a refusal into required with every bundle in scope and says
      why. There is no answer in which the reader guesses. Set: Thirteen unreadable shapes - a
      scalar where a mapping belongs, an unclosed inline mapping, a key with nothing under it, the
      key twice at the top level, a nested flow mapping, a nested flow sequence, a quote that never
      closes, a member whose value is on the next line, a member with no value, a required value
      that is neither true nor false, a block carrying neither setting, indentation that is neither
      the block's nor a member's, and a file that is not valid UTF-8 - plus a file with no such key.
      Completeness: These are selected refusal regressions, not an exhaustive complement of the
      accepted grammar. Exhaustive refusal outside that grammar is INTENDED and NOT YET
      DEMONSTRATED. The never-adopted file is in the set, so the row fails if the reader simply
      refuses everything it does not like the look of. Falsifier: Swallow the refusal and read an
      empty policy instead;
      policyread/a-setting-the-owner-wrote-never-reads-as-absent must fail.
    falsified_by: >
      Swallow the refusal and read an empty policy instead;
      policyread/a-setting-the-owner-wrote-never-reads-as-absent must fail.
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

So the fix is narrow. The fix-validation module already carries `read_policy`, and the call site uses it instead of the parser the validator hands in. That parser is still handed in and still used for the spec front matter beside it; only the policy read changes.

**Three rounds of review, eleven bypasses, and why the reader was rebuilt rather than patched.** The first landing handled the six shapes it was written for and answered advisory for everything else. An unbriefed Codex review found two ways through it. A second review, briefed at that class, found eight more. A third, told nothing, found three, and two of those three were REGRESSIONS introduced by the fix for the first two: the quote-aware comma split written to stop `{required: true, note: "leave this, required: false"}` broke `{note: don't relax, required: true}`, which the version before it had parsed correctly.

The eleven are one defect wearing eleven hats. A byte order mark, a space before the colon, an apostrophe or an inch mark in a plain value, a backslash-escaped quote, a U+2028 inside a note, a nested `{}` or `[]`, the key written as prose inside another key's block scalar, the key nested under an unrelated mapping, the key twice, a member whose value sits on the next line. Every one parsed to something non-empty and WRONG, so the rule read as off and nothing failed anywhere. The worst did not disarm the flag at all: it moved the start line forward to a later commit, which silently exempts every bundle between the two and prints as a tidy "not applicable".

A subset reader cannot be patched into a YAML reader. Each patch closed the shape it was shown and left the next one, and twice it opened one. So the reader was rebuilt around a different contract: **return exactly what the owner wrote, or refuse.** It reads one root-level key of one small file, it knows enough structure to tell a real key from text inside someone else's block scalar, and every shape it is not certain it reads the way YAML reads it raises. The call site turns a raise into required with every bundle in scope, so an unreadable policy makes the gate harder to pass and can never switch it off.

That contract is AC4, and it is why the reader now has three answers instead of two. It used to have one way of saying "no settings" and it meant two different things: a repository that never adopted the rule, and a setting the owner wrote that could not be parsed. Every bypass came out of that shared answer.

**The oracle.** AC1's shape list is now checked against a real YAML parser rather than only against itself, because the lesson of eleven bypasses is that a list of shapes the author thought of is not a domain. PyYAML is not a dependency of the shipped reader, which is standard library only; the row stands down by name where it is absent.

**Why the start line must be a full commit id.** Two of the three symptoms are really one: a value that is not an object id. A branch name resolves, and resolves to something different tomorrow, and the ref namespace is not a protected path, so the owner's line could move without the owner. An abbreviated id can become ambiguous as history grows. A leading-zero value is the parser's coercion showing through. Requiring forty hex characters refuses all three by shape, before anything is resolved, and says what it was given.

## Out of scope

The shared parser is deliberately unchanged, and so is the integer coercion in it. The other readers of the policy file are not consolidated here; this item makes the two settings that gate a landing read correctly, and leaves the wider parser question to an item that can carry the corpus migration it would need.

## Notes

`read_policy` and `_strip_comment` already exist and are already tested by VELDO-0104's suite; this item does not write a second stripper. The refusal is by shape and happens before `_commit_exists`, so a mistyped line and a line this repository does not have stay distinguishable in the output.

2026-09-22 follow-ups: VELDO-0118 (shared written-grammar generator and optional independent oracle fixture).
