---
schema: veldo.spec/v1
id: VELDO-0001
title: Every behaviour-bearing criterion declares its own falsification - the negative control moves
  from reviewer lore into the spec contract, so a criterion that names no way to be proven wrong is
  refused at the gate instead of discovered in review
status: ready
risk: standard - it adds one validated field to the specification contract and refuses specs that omit
  it, so it changes what the gate accepts rather than what any product does. It is NOT low because it
  is adoption-affecting in the strongest way a contract change can be: every existing spec in every
  repository either satisfies it or is refused, so a rule written without a migration would redden a
  working repository on the day it lands. And it is not high because nothing it touches runs in
  production and the whole change is reversible by deleting one check
owner: dmitry
human_approval: not_required
lane: standalone
placement: [enforcement]
footprint:
  - ".veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - "engine/specs/TEMPLATE.md"
  - "specs/TEMPLATE.md"
  - "engine/specs/TEMPLATE-standing.md"
  - "docs/method.md"
  - "scripts/suites/17_veldo_0001_falsification_declared.py"
  - "specs/VELDO-0001-every-criterion-declares-its-own-falsification.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    The refusal names the criterion by id and says what is missing, in the same voice as the
    observability refusal it is modelled on, so an author reads one line and knows which criterion to
    fix rather than being told the spec is invalid.
  error_taxonomy: >
    One refusal with three distinguishable causes, each named separately: the criterion declares no
    falsification at all, it declares one that is empty or too short to be a real statement, or it
    declares one in a form the reader cannot parse. A single undifferentiated refusal would send an
    author hunting, which is the thing this item exists to stop.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Delete the per-criterion loop so the check only verifies that acceptance_criteria exists, and a fixture spec carrying three criteria and no falsified_by anywhere must stop being refused.
    text: >
      A BEHAVIOUR-BEARING CRITERION WITHOUT A DECLARED FALSIFICATION IS REFUSED, AND THE REFUSAL NAMES
      THE CRITERION. Every entry under acceptance_criteria in a spec whose behavior_bearing is true
      carries a `falsified_by` field: one statement of the single change to the implementation that
      must make this criterion's check fail. The validator refuses a spec where any such criterion
      omits it, and the message names the criterion id and the cause.
      FALSIFIED BY: delete the per-criterion loop so the check only verifies that acceptance_criteria
      exists, and a fixture spec carrying three criteria and no falsified_by anywhere must stop being
      refused. NEGATIVE CONTROL, and it is the leg that matters: the same validator must still ACCEPT
      a fixture spec whose criteria all declare one, so the refusal is discriminating rather than a
      blanket rejection of every spec.
  - id: AC2
    falsified_by: >
      Accept any non-empty string, dropping both the character and word floors, and a fixture declaring falsified_by as n/a must stop being refused.
    text: >
      A DECLARATION THAT SAYS NOTHING IS NOT A DECLARATION. An empty falsified_by, whitespace, or a
      string too short to be a statement is refused with its own named cause, distinct from the cause
      for a missing field. There is no allowlist and no exemption keyword: this item exists because a
      rule with an escape hatch is a rule authors learn to route around.
      FALSIFIED BY: accept any non-empty string, and a fixture declaring `falsified_by: n/a` must stop
      being refused. NEGATIVE CONTROL: a genuine one-sentence declaration must still be accepted, so
      the length rule cannot be satisfied only by padding.
  - id: AC3
    falsified_by: >
      Make the check ignore behavior_bearing entirely, and a fixture spec that declares no behaviour while carrying bare criteria must start being refused.
    text: >
      SPECS THAT DECLARE NO BEHAVIOUR ARE UNAFFECTED, AND SO IS A REPOSITORY THAT HAS NOT ADOPTED THIS
      YET. A spec with behavior_bearing absent or false is not asked for a falsification, exactly as
      the observability check already stands down for the same shape, and the check reports its
      stand-down rather than passing silently. THE MIGRATION IS PART OF THE ITEM AND NOT A FOLLOW-UP:
      this repository's existing specs are brought into compliance in the same change, and until every
      one of them is, the check reports rather than refuses. The flip to refusing is a separate commit
      whose message states the date and the count, because a contract change that reddens a working
      repository on arrival is how a good rule gets reverted.
      FALSIFIED BY: make the check ignore behavior_bearing entirely, and a fixture spec that declares
      no behaviour while carrying bare criteria must start being refused. NEGATIVE CONTROL: with the
      stand-down in place, a behaviour-bearing fixture missing a falsification must still be refused,
      so the stand-down cannot be what makes every case pass.
  - id: AC4
    falsified_by: >
      Remove the falsified_by key from engine/specs/TEMPLATE.md, and the assertion that reads the template for it must go red.
    text: >
      THE TEMPLATE AND THE SPINE DOCUMENT ASK FOR IT, because a rule an author is never prompted for is
      a rule that survives only where somebody remembered it. engine/specs/TEMPLATE.md carries the
      field with a one-line explanation of what belongs in it, and docs/method.md states the rule where
      it defines a specification. MEASURED, and this is the finding that produced this item: the words
      "negative control" appear ZERO times in either file today, while being the single most cited
      concept in every review that has found a real defect in this repository.
      FALSIFIED BY: remove the field from the template, and the assertion that reads the template for
      it must go red. NEGATIVE CONTROL: the assertion must fail if it is looking for a string that the
      template never contained, so it is pinned to the field name the validator actually enforces
      rather than to a spelling nobody uses.
required_evidence: [unit]
rollback: >
  Delete the check's registration in check_spec. The field becomes inert data that no reader consults,
  and every spec carrying it stays valid, so the retreat costs one line and loses nothing already
  written.
---

# Every behaviour-bearing criterion declares its own falsification

## Why this item exists, in one measurement

On 2026-08-11 an independent review of this repository's estimation layer produced 34 confirmed
findings across nine items, fourteen of them blockers. They are almost all one sentence: **a property
the module claims that nothing asserts.** The module could be inverted and the suite stayed green.

The obvious diagnosis is that the acceptance criteria were too thin, and it is wrong. The criteria in
this repository are long. WARP-1405's AC3 is a fifteen line paragraph. Length was never the property
that separated the criteria that produced working code from the criteria that produced checks which
could not fail.

The property that separated them is whether the criterion **said what would make it false**. WARP-1402's
AC5 was singled out by its reviewer as the strongest work in that plan, and what makes it strong is that
it demands a negative control in the criterion itself: drive the real validator, and prove it still
refuses a genuinely broken spec. An implementer reading that has to build the mutation. An implementer
reading a property described in prose has to invent the falsification, and the cheapest invention is one
that passes.

## Why the method did not already do this

It knows the rule. It applies it in every review. A previous plan recorded it as a lesson, in these
words: a sentence that makes a checkable claim must be backed by an assertion.

And the words "negative control" appear **zero times** in `engine/specs/TEMPLATE.md` and **zero times**
in `docs/method.md`. The validator checks that a spec HAS acceptance criteria and nothing about what
they contain.

So the discipline lives in reviewer lore and in verdict prose, and never in the artifact an author fills
in. That is this project's own rule turned on itself: prose instructions do not execute. The lesson was
written down in the place that does not run.

## What this changes, and what it deliberately does not

It adds one field and one refusal. It does not attempt to judge whether a declared falsification is a
GOOD one, because that is a review-lane judgement and a machine that pretended to make it would produce
exactly the confident wrongness this item is about. The check verifies that the author was asked the
question and answered it in a sentence. Whether the answer is any good is what a reviewer is for.

The migration is inside the item rather than after it. A contract change that reddens a working
repository the day it arrives is how a correct rule gets reverted, so this reports until this
repository's own specs comply, and the flip to refusing is its own commit that states the count.
