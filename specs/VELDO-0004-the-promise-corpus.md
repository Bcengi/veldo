---
schema: veldo.spec/v1
id: VELDO-0004
title: The promise corpus - a claim a document makes becomes a record with a checkable predicate,
  settled mechanically against the tree, and a contradiction carries what it measured so a human can
  overturn it
status: ready
risk: standard - it adds one artifact contract and one settling read model, writes nothing, and gates
  nothing. It is NOT low because its product is an ACCUSATION against shipped prose, and the audit
  that motivated it had five of its fifteen accusations OVERTURNED on challenge, so a settlement that
  hid its own evidence would launder a wrong accusation into a fact. It is not high because it refuses
  no change and an absent corpus stands the whole read model down
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W3
placement: [contracts]
footprint:
  - ".veldo/promises.py"
  - "engine/.veldo/promises.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/21_veldo_0004_promise_corpus.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0004-the-promise-corpus.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    Every settlement names the claim, the document and locator it came from, the predicate that
    settled it, and WHAT THE PREDICATE MEASURED. Every refusal names the claim id and the file. The
    report separates supported, contradicted and unsettleable, and never sums them into a score,
    because a percentage of a corpus nobody enumerated is the number this repository refuses to print.
  error_taxonomy: >
    Corpus refusals: PROMISE_UNREADABLE, PROMISE_MISSING_FIELD, PROMISE_KEY_UNRECOGNIZED,
    PROMISE_PREDICATE_UNKNOWN, PROMISE_DECLARED_TWICE and PROMISE_TARGET_UNBOUND, named separately
    because each is a different author mistake. Settlement outcomes are SUPPORTED, CONTRADICTED and
    UNSETTLEABLE, and the third is never folded into the first: "the tree supports this" and "no
    predicate here can decide this" are opposite facts about how much a reader should trust the report.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Widen PREDICATES in .veldo/promises.py to accept any string, and the assertion that a claim
      declaring predicate `looks_fine` is refused with PROMISE_PREDICATE_UNKNOWN and the allowed
      predicates named must go red.
    text: >
      A CLAIM IS A CLOSED CONTRACT WITH A DECLARED PREDICATE. Each claim carries an id, the document
      and locator it was read from, the claim as WRITTEN, and one predicate from a closed set. The key
      set is closed, an unknown predicate is refused with the allowed set named, and one claim id in
      two files is refused with BOTH files named. THE PREDICATE VOCABULARY IS DELIBERATELY TINY - path
      presence, text presence, text absence and symbol definition - because a predicate that needed
      judgement would be a machine pretending to make a review-lane call. NEGATIVE CONTROL: a corpus
      differing only in a valid predicate is accepted.
  - id: AC2
    falsified_by: >
      Read the outcome from a claim's own `believed` field in .veldo/promises.py instead of running its
      predicate over the tree, and the assertion that a claim declaring believed supported whose
      predicate FAILS settles CONTRADICTED must go red.
    text: >
      THE SETTLEMENT IS DERIVED BY RUNNING THE PREDICATE, NEVER READ FROM WHAT THE AUTHOR BELIEVED.
      A claim may record what its author expected, in `believed`, and that field is not consulted when
      settling - it exists only so the report can name a claim whose author and whose tree disagree.
      This is the same rule VELDO-0002 applies to a run's own word and VELDO-0003 to a worker's: the
      artifact decides. NEGATIVE CONTROL: a claim declaring believed contradicted whose predicate
      HOLDS settles SUPPORTED, so the field is ignored in both directions rather than merely
      overridden in the failing one.
  - id: AC3
    falsified_by: >
      Fold UNSETTLEABLE into SUPPORTED in the report in .veldo/promises.py, and the assertion that a
      corpus of only unsettleable claims stands the report down rather than reporting zero
      contradictions must go red.
    text: >
      UNSETTLEABLE IS A FIRST-CLASS OUTCOME AND IS NEVER FOLDED INTO SUPPORTED. A claim whose truth no
      declared predicate can decide is recorded UNSETTLEABLE with the reason, counted separately, and
      named on the page. "The tree supports this" and "nothing here can decide this" are opposite facts
      about how far a reader should trust the report, and a corpus whose claims are ALL unsettleable
      stands the report down rather than announcing zero contradictions, which is the confident zero
      this migration kept finding. NO SCORE IS PRINTED: there is no ratio, no percentage and no float
      anywhere in the report, because a proportion of a corpus nobody enumerated is exactly the number
      that would get quoted.
  - id: AC4
    falsified_by: >
      Drop the measured evidence from a settlement in .veldo/promises.py so a contradiction reports
      only its outcome, and the assertion that every CONTRADICTED settlement carries the predicate, the
      target it read and what it found there must go red.
    text: >
      A CONTRADICTION CARRIES WHAT IT MEASURED, SO A HUMAN CAN OVERTURN IT. This is the finding that
      produced this item: the 2026-08-10 audit of this project's own shipped documents raised fifteen
      accusations and FIVE WERE OVERTURNED on challenge. An accusation whose evidence is not in the
      record is indistinguishable from a correct one, and the cost of getting it wrong is deleting a
      true sentence from a shipped document. So every settlement records the predicate, the target it
      read, and what it actually found - and the same evidence is recorded for SUPPORTED, because a
      settlement that only explains itself when it accuses is a settlement nobody can audit.
  - id: AC5
    falsified_by: >
      Remove the absent-corpus stand-down from the read model in .veldo/promises.py, and the assertion
      that an absent .veldo/promises/ directory stands down with its reason named while the report keeps
      ONE key shape must go red.
    text: >
      ADOPTION SAFE, AND IT GATES NOTHING. A repository with no .veldo/promises/ directory stands the
      read model down by name rather than reporting a clean corpus it never looked at. No gate stage
      loads this, no change is refused because a claim is contradicted, and nothing here blocks a
      landing: PLAN-0018 NG3 says a completeness organ that BLOCKS on a heuristic verdict would cut
      true sentences and stop real work, and this is that organ. Advisory, loud, human-resolved.
      NEGATIVE CONTROL: with a corpus present the same report answers, so the stand-down is a
      measurement rather than the module's only behaviour.
required_evidence: [unit]
rollback: >
  Delete .veldo/promises.py and its suite fragment. Nothing imports it, no gate stage runs it, and the
  corpus it reads is authored data that stays valid and inert, so the retreat costs one file.
---

# The promise corpus

## The hole this closes, and why every automated check missed it

On 2026-08-10 an audit of this project's own shipped documents found **64 false claims across 8
documents**: sentences asserting a capability the tree did not have. The gate was green throughout.
Every one of those claims was checkable - "the guard refuses X", "the loop covers Y" - and nothing
checked them, because they lived in prose and the gate reads code.

That is the class: **a document makes a claim about the tree, and nothing joins the two.**

## Why the extraction is not in this item, stated plainly

Reading a document and deciding which sentences make checkable claims is a judgement call, and a
machine that pretended to make it would produce exactly the confident wrongness this method keeps
finding. So extraction is an authoring job - a task in VELDO-0003's queue, done by an agent or a
human - and its product is a claim record with a **declared predicate**.

This item is the mechanical half: validate those records, run each predicate over the tree, and
report. The split is the same one the behaviour floor makes, and for the same reason: the machine
drafts, and the part that needs judgement is somebody's job by name.

## Why a contradiction must carry its evidence

The audit that motivated this item raised fifteen accusations against three documents and **five were
overturned** when challenged. That is a third of them wrong, in the direction that costs the most:
deleting a true sentence from a shipped document because a check misread the tree.

So a settlement is not a verdict, it is a **measurement with the reading attached**: the predicate,
the target it read, and what it found there. A human who disagrees can see immediately whether the
predicate was pointed at the wrong file. And the evidence is recorded for supported claims too,
because a settlement that only explains itself when it accuses is one nobody can audit.
