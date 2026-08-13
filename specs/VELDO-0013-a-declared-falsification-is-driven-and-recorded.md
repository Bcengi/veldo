---
schema: veldo.spec/v1
id: VELDO-0013
title: A declared falsification is DRIVEN once per item and recorded against the commit it was driven
  at, so a criterion that cannot fail is caught when the evidence is written rather than by the next
  reviewer who happens to try it
status: draft
risk: standard - it adds one artifact to the proof bundle and one gate stage that reads it, and it
  refuses nothing that passes today because the artifact is optional for every bundle that predates
  it, exactly as VELDO-0010's version field is. It is NOT low because the stage it adds decides
  whether a criterion's check is believed at all, and a stage that reported compliance it had not
  measured would be worse than the absence it replaces. It is not high because it gates on a RECORD
  rather than driving mutations itself, so no gate run mutates the tree
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W10
placement: [enforcement]
footprint:
  - ".veldo/falsification_record.py"
  - "engine/.veldo/falsification_record.py"
  - ".veldo/validate.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/28_veldo_0013_falsification_driven.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0013-a-declared-falsification-is-driven-and-recorded.md"
  - "specs/index.md"
  - "plans/PLAN-0018-what-a-complex-project-needs.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    The reader reports, per item that has a proof bundle: how many of its behaviour-bearing criteria
    carry a driven record, how many do not, and how many carry a record whose commit no longer matches
    the item's own footprint. It says in words that a criterion with no record is UNDRIVEN and that
    nothing is inferred for it. A record naming a row that the suite does not contain is named with
    the item and the row, because a record citing a row nobody can find is the paper promise this item
    exists to replace.
  error_taxonomy: >
    UNDRIVEN (the criterion declares a falsification and no record covers it: reported, and for a
    bundle written before this landed it is the legitimate state), RECORD_STALE (a record exists and
    the commit it was driven at is not an ancestor of the current footprint's last change, so it
    describes a tree that has moved), RECORD_INCOMPLETE (a record covers some of an item's
    behaviour-bearing criteria and not all, which is worse than none because a partial record reads as
    coverage), RECORD_UNREADABLE (present and unparseable, named with the item), and ROW_NOT_FOUND (the
    record names an assertion the suite corpus does not contain). NO INPUT MAKES THE READER RAISE.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Make the reader treat a criterion with no record as covered in .veldo/falsification_record.py,
      and the assertion that an item whose criteria carry no record is reported UNDRIVEN with every
      criterion named must go red.
    text: >
      THE RECORD IS OPTIONAL FOR WHAT ALREADY EXISTS AND THE MIGRATION IS THE ITEM, which is the lesson
      VELDO-0010 wrote down and VELDO-0001 paid for. MEASURED on the day this is authored, 2026-08-13:
      this repository holds proof bundles for well over a hundred items and NOT ONE carries a driven
      falsification record, so a stage requiring one would redden a working repository the day it
      landed, which is how a correct rule gets reverted. So an item with no record is UNDRIVEN, that is
      REPORTED and not refused, the report NAMES the criteria it could not confirm, and the assertion
      carries no count this repository can grow past.
  - id: AC2
    falsified_by: >
      Accept a record that covers only some of an item's behaviour-bearing criteria in
      .veldo/falsification_record.py, and the assertion that a partial record is RECORD_INCOMPLETE
      naming the uncovered criteria must go red.
    text: >
      A PARTIAL RECORD IS REFUSED, BECAUSE A PARTIAL RECORD READS AS COVERAGE. An item that records
      four of five driven criteria and says nothing about the fifth is more dangerous than one
      recording none, since a reader auditing it sees a driven record and stops looking. So once an
      item carries a record at all, that record must cover EVERY behaviour-bearing criterion the spec
      declares, derived from the spec rather than listed in the record, and the uncovered ones are
      named. NEGATIVE CONTROL, ADDITIVE: adding a criterion to the spec makes the existing record
      incomplete and says which criterion is missing, so the derivation follows the spec rather than a
      copy of it.
  - id: AC3
    falsified_by: >
      Remove the commit binding from the record contract in .veldo/falsification_record.py so a record
      carries no commit, and the assertion that a record whose commit predates the last change to the
      item's footprint is RECORD_STALE must go red.
    text: >
      A RECORD IS BOUND TO THE COMMIT IT WAS DRIVEN AT, AND MOVING THE CODE INVALIDATES IT. This is the
      dead-end the chosen option carried and the reason it was chosen anyway: a record with no binding
      describes a tree that has since moved and is a claim about history presented as a claim about
      now. Every record names the commit it was driven at; when the item's own footprint has changed
      since that commit the record is RECORD_STALE, reported with both commits, and the item must prove
      itself again. NEGATIVE CONTROL: a record driven at the current state of its footprint is not
      stale, so staleness is a measurement of divergence rather than the reader's only answer.
  - id: AC4
    falsified_by: >
      Stop comparing the recorded row against the suite corpus in .veldo/falsification_record.py, and
      the assertion that a record citing an assertion no suite contains is ROW_NOT_FOUND naming the
      item and the row must go red.
    text: >
      THE ROW A RECORD CITES MUST EXIST, OR THE RECORD IS THE PAPER PROMISE IT REPLACES. A record
      stating that mutation M reddened row R is worth nothing if R is not an assertion anybody can
      find; that is the same shape as a substring scan proving a presence, which this project has now
      recorded four times. So every row a record names is looked up in the suite corpus and a miss is
      named with the item and the row. THE LOOKUP IS BY THE ASSERTION'S OWN TEXT and never by a line
      number, because a line number is stale the moment anything above it changes.
  - id: AC5
    falsified_by: >
      Make the reader raise on an unparseable record instead of naming it in
      .veldo/falsification_record.py, and the assertion that an unreadable record is
      RECORD_UNREADABLE with the item named while every other item still reports must go red.
    text: >
      NO INPUT MAKES THIS READER RAISE, AND AN UNREADABLE RECORD DOES NOT TAKE THE REPORT DOWN WITH IT.
      A traceback out of a module-level read shortens a whole run and makes a run that could not look
      indistinguishable from a run that found nothing, which is this project's confident zero in its
      most expensive form. An unparseable record, a record that is not an object, and a record whose
      fields are the wrong types are each RECORD_UNREADABLE, named with the item, and every other item
      in the same report still answers.
  - id: AC6
    falsified_by: >
      Change the stage's posture in .veldo/validate.py from reporting to refusing while this
      repository's bundles carry no records, and the assertion that the stage refuses nothing today
      while still naming what it found must go red.
    text: >
      IT REPORTS AND REFUSES NOTHING UNTIL THE CORPUS CARRIES RECORDS, AND THE POSTURE IS ASSERTED
      UNCONDITIONALLY RATHER THAN DERIVED FROM THE LIVE TREE. VELDO-0010's review found that a posture
      read off live state can be flipped by the very mutation it exists to catch, so this states two
      facts that hold in either posture: the stage NAMES every undriven criterion it found, and it
      exits zero on an UNDRIVEN corpus while exiting non-zero on a STALE, INCOMPLETE, UNREADABLE or
      ROW_NOT_FOUND record. Those are the four that mean somebody wrote a record and it is wrong, which
      is a different fact from nobody having written one yet.
required_evidence: [unit]
rollback: >
  Delete the stage's registration in .veldo/validate.py, the organ and its twin, and the suite
  fragment. Nothing else consumes the record, no existing bundle carries one, and the artifact is
  absent from PROOF_REQ, so removing it returns the repository byte-identically to its prior gate
  behaviour.
---

## Intent

Every behaviour-bearing criterion in this project already declares the single edit that should make
its check fail. **Nothing has ever applied that edit.** The clause is a promise on paper, and the
twelve independent reviews of PLAN-0018 measured what that is worth: reviewers who actually applied
the declared mutations found criteria whose checks stayed fully green, meaning the check could not
fail for the defect its own text names. Ledger findings 40, 48, 55 and 60 are four instances, and two
of them are mine, written within an hour of each other while documenting the same mistake.

Dmitry decided this on 2026-08-13, recorded at `.veldo/decisions/0001-driving-declared-falsifications.yaml`
version 2, choosing `proof-time-record`: drive once per item when its evidence is written, record the
result, and stamp it with the commit it was driven at.

## Context

The three alternatives and why they lost are in the decision record rather than repeated here. The
short version: driving everything on every gate run costs hours, and a gate people stop running
protects nothing; driving only the changed footprint trusts the author's own declaration of what they
touched, which is the same declaration under verification.

**What this item is NOT.** It does not drive mutations during a gate run. No gate run mutates the
tree, which is why the risk is standard rather than high. The driving happens once, when an item's
evidence is produced, by whoever produces it; this item is the CONTRACT for what that produces and the
stage that refuses a record that is wrong.

## The distinction that decides the posture

An item with no record and an item with a broken record are different facts and this item never
collapses them. Nobody having driven a criterion yet is the state the entire existing corpus is
legitimately in. Somebody having driven it and recorded something stale, partial, unreadable, or
citing a row that does not exist is a mistake that reads as coverage, and that is the one this
refuses.

## REFUTED IN PART BY REV-DEC-0001, 2026-08-13, BEFORE ANY OF IT WAS BUILT

`.veldo/decision_reviews/REV-DEC-0001.yaml`, disposition `reframe`. This spec is NOT ready and two of
its criteria cannot be built as written. Recorded here rather than in a chat message, because a spec
that reads cleanly while a bound review has already refuted it is the worst artifact in the tree.

**AC4 IS UNBUILDABLE AND THE MEASUREMENT IS THE PROOF.** It requires that the row a record cites must
exist, resolved by the assertion's own text. That assumes a criterion maps to one row. Measured
independently over this repository at 292367d: of 227 behaviour-bearing criteria, **6 resolve to
exactly one labelled assertion, 80 resolve to NONE, and 141 resolve to more than one** (median 6,
maximum 33). The mechanism is therefore unworkable for 221 of 227 cases. It reads perfectly and it
cannot be built.

**THE WHOLE GATE-READS-A-RECORD HALF IS THE SHAPE THIS REPOSITORY ALREADY EJECTED.** `.veldo/policy.yaml`
records why the merge rule stopped requiring a passing verdict: "A verdict is an artifact the agent
can write, so that clause asked an agent to certify itself and cost nine build rounds of forgery
guards" (WARP-0730). This spec proposed reintroducing that shape under a new name, and made it worse
by never requiring the record to carry the mutation, the baseline or the paired control, so it was an
attestation to an event no other party could reproduce.

**THE COST MODEL THAT JUSTIFIED THE CHOICE WAS WRONG BY TWO ORDERS OF MAGNITUDE.** The decision refused
driving on every gate run on cost. That assumed each drive re-runs all 34 suites. A criterion needs
only its OWN suite and the subset runner already ships: measured, all 61 criteria of VELDO-0001 to
VELDO-0012 cost about 60 seconds of suite wall clock, against a unit stage of 105.8 seconds.

**WHERE THIS GOES INSTEAD**, from the review's missing options: make falsifiability an in-suite paired
control on an injected seam, applying the mutation to an in-process copy of the module, so no artifact
exists to be trusted, nothing is written to the tree, nothing needs reverting, and the question of
when to drive dissolves. A version 3 of the decision record carries this before anything is built.
