---
schema: veldo.spec/v1
id: VELDO-0014
title: What a criterion may assert about the live repository - a stated rule that a check describes a
  property and never today's contents, with the mechanisable half enforced and the half a scan cannot
  see declared rather than implied
status: draft
risk: standard - it adds one advisory stage over this repository's own suite sources and one rule in
  the method document, and it refuses nothing on the day it lands. It is NOT low because a scan that
  reported a clean sweep it had not actually performed would license the exact class it exists to
  remove, so the stage's blind spots are asserted rather than described. It is not high because the
  stage reads suite text and gates nothing until its findings are cleared
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W11
placement: [enforcement]
footprint:
  - ".veldo/live_state_pins.py"
  - "engine/.veldo/live_state_pins.py"
  - ".veldo/validate.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "docs/method.md"
  - "engine/docs/method.md"
  - "scripts/suites/29_veldo_0014_live_state_pins.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0014-what-a-criterion-may-assert-about-the-live-tree.md"
  - "specs/index.md"
  - "plans/PLAN-0018-what-a-complex-project-needs.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    The stage reports each assertion it found comparing a live read against an empty literal, an exact
    count or the absence of a path, naming the file, the assertion's own text and which of the three
    shapes it matched. It ALSO reports, every run and in the same breath, the shapes it cannot see:
    a pin routed through an intermediate variable, through a helper, or through a comprehension it
    could not follow. A count of what it examined accompanies every clean answer, because "no findings"
    over an empty examined set is the confident zero.
  error_taxonomy: >
    PIN_EMPTY_LITERAL (a live read compared against [], set(), {} or ""), PIN_EXACT_COUNT (a live read
    compared with == against an integer literal), PIN_PATH_ABSENT (an assertion requiring a path not to
    exist), and UNFOLLOWABLE (an assertion the scan could not resolve to either a pin or a property,
    which is REPORTED and never counted as clean). The fourth is the load-bearing one: a scan that
    silently dropped what it could not follow would answer "no pins" over the cases most likely to
    contain one.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Delete the empty-literal comparison from .veldo/live_state_pins.py, and the assertion that a
      fixture suite asserting a live read equals [] is reported PIN_EMPTY_LITERAL with the file and the
      assertion's own text must go red.
    text: >
      THE THREE FORBIDDEN SHAPES ARE DETECTED OVER FIXTURES THAT CONTAIN THEM, one row per shape, each
      naming the file and the assertion's own text rather than a line number. The shapes are the ones
      measured in this project: a live read required to equal an empty collection, a live read compared
      with equality against an integer literal, and an assertion requiring a path not to exist. All
      three are drawn from real instances - VELDO-0003 AC5 pinned a consumer list to empty, VELDO-0009
      AC4 pinned a four-state answer, VELDO-0005 pinned the absence of a directory - so the vocabulary
      is derived from what has actually bitten us rather than imagined.
  - id: AC2
    falsified_by: >
      Make the scan drop an assertion it cannot resolve instead of reporting it in
      .veldo/live_state_pins.py, and the assertion that a fixture pin routed through an intermediate
      variable is reported UNFOLLOWABLE rather than absent must go red.
    text: >
      WHAT IT CANNOT SEE IS REPORTED, WHICH IS THE WHOLE REASON THIS IS SAFE TO BUILD. Three of the four
      measured instances assign the live read to a local before comparing it, so a syntactic rule cannot
      follow the value without dataflow analysis this deliberately does not attempt. A scan that dropped
      those would answer "no pins found" over exactly the population most likely to hold one, and a
      green scan would then read as compliance - which is the chosen option's own declared dead-end. So
      an assertion the scan cannot resolve to either a pin or a property is UNFOLLOWABLE, it is printed,
      and it is never counted as clean.
  - id: AC3
    falsified_by: >
      Have the stage report zero findings without reporting how many assertions it examined in
      .veldo/live_state_pins.py, and the assertion that every clean answer carries its examined count
      and its unfollowable count must go red.
    text: >
      A CLEAN ANSWER CARRIES WHAT IT LOOKED AT. "No findings" over an examined set of zero is this
      project's confident zero, and it has now been recorded four separate times in this plan's ledger.
      So the report states how many suite files and how many assertions were examined alongside every
      count of findings, and a run that examined nothing SAYS SO rather than reporting a clean sweep.
  - id: AC4
    falsified_by: >
      Make the stage exit non-zero on a finding in .veldo/validate.py, and the assertion that it
      reports over this repository's real suite corpus while refusing nothing must go red.
    text: >
      IT REPORTS AND REFUSES NOTHING, AND THAT IS ASSERTED UNCONDITIONALLY RATHER THAN READ OFF THE
      LIVE TREE. PLAN-0018's NG3 forbids gating on a heuristic verdict, and this is a heuristic by
      construction: it reads text and cannot follow a value. So it names what it finds and exits zero,
      in both postures, and the row asserting that does not depend on how many findings this repository
      currently has - because a posture derived from live state can be flipped by the mutation it is
      meant to catch, which VELDO-0010's review measured.
  - id: AC5
    falsified_by: >
      Remove the rule from docs/method.md, and the assertion that the method document states both what
      a criterion MAY assert and what it may NOT, in the section that defines a criterion, must go red.
    text: >
      THE RULE IS WRITTEN WHERE AN AUTHOR MEETS IT, because the enforceable half is the smaller half.
      The method document states the permitted form - a criterion asserts a PROPERTY, such as that
      nothing here refuses a change or that no accusation this organ makes is false - and the forbidden
      form, being that a live set is empty, that a live count is an exact number, or that a path does
      not exist. IT ALSO CARRIES THE WORKED EXAMPLE, because the rule is abstract without one:
      VELDO-0005's "the unresolved set is empty" became "no accusation this organ makes is false", and
      the second reds on a real stale declaration while never reddening because the project grew. Both
      copies of the document carry it, since an adopter is bound by the same rule.
  - id: AC6
    falsified_by: >
      Point the scan at a hand-listed set of suite files in .veldo/live_state_pins.py, and the assertion
      that the examined set is DERIVED by glob and equals an independent enumeration must go red.
    text: >
      THE EXAMINED SET IS DERIVED AND NEVER LISTED. A hand-kept list of what to check is stale the day
      something lands without an entry and nothing reds when that happens, which is the defect two items
      were refuted for in this same round and the reason extend-the-table lost the decision. The set is
      globbed and asserted EQUAL, in both directions, to an independent enumeration written in the suite
      itself, with no cardinality asserted so this repository can grow.
required_evidence: [unit]
rollback: >
  Delete the stage's registration in .veldo/validate.py, the organ and its twin, the suite fragment,
  and the method-document section. The stage refuses nothing, so removing it changes no gate outcome.
---

## Intent

An assertion that describes the repository as it happens to be right now, rather than describing a
rule, goes red the first time somebody uses the feature it guards. The clearest measured instance:
a suite asserted that no file in this repository loads the budget read model. That was true the day it
was written, so **the moment anybody actually used the budget read model the entire gate went red** -
nothing broken, the test had frozen "nobody uses this yet" into a law.

Five instances measured in this round alone: VELDO-0003 AC5, VELDO-0005 twice, VELDO-0006 AC5,
VELDO-0009 AC4, and WARP-0727 AC1 in a different dress. `scripts/check_first_use.py` was built for
exactly this class and saw none of them, because its mutation table drives one file and its own
documentation says so.

Dmitry decided this on 2026-08-13, recorded at `.veldo/decisions/0002-live-state-pin-class.yaml`
version 2, choosing `policy-enforced-by-shape`: change what a criterion is allowed to assert, and
enforce the mechanisable half automatically.

## Context

The option space and why the four alternatives lost are in the decision record. The one worth
repeating here is why a scan alone was not enough: three of the four measured pins assign the live
read to a local variable first, so no syntactic rule can follow them. That is precisely why AC2 exists
and why the stage must report its own blind spots every run.

## The fix shape, which is the transferable part

The wrong fix for a live-state pin is a narrower pin. The right fix is to assert the property the pin
was standing in for. VELDO-0005's remediation is the worked example this item ships:

    before   the unresolved set is empty
    after    no accusation this organ makes about this repository is false

The second still reds on a real stale declaration, and never reds because somebody added a capability.
That transformation is what the method document teaches and what this stage nudges authors toward.

## REFUTED BY REV-DEC-0002, 2026-08-13, BEFORE ANY OF IT WAS BUILT

`.veldo/decision_reviews/REV-DEC-0002.yaml`, disposition `reframe`. The problem class is real and the
strategy survives. **The discriminator this spec is built on is wrong, and as written it would forbid
this repository's own best known fix.**

**THE FORBIDDEN LIST CONDEMNS THE CORRECT REMEDY.** The rule says an assertion may not require that a
live set is empty. Three of the four instances that motivated it still require exactly that AT THEIR
CORRECT FIX. VELDO-0006 AC5's remediation kept `loaders == []` and changed only the DOMAIN, and it
landed in commit 33f10f5, the same commit that created the decision record. Tonight's own best fix,
"no accusation this organ makes is false", IS a required emptiness.

**THE RIGHT DISCRIMINATOR IS ALREADY WRITTEN IN THIS REPOSITORY**, at
`scripts/suites/22_veldo_0005_declared_vs_shipped.py:143`: "Every bucket is a DEFECT bucket, so none of
them is a fact about how much this repository declares." So it is not empty versus non-empty. It is a
DEFECT set, which growth cannot add to and may be required empty forever, versus a POPULATION set,
which using the feature adds to and may never be pinned. Equivalently: a declared closure versus a
sweep of the source tree.

**THE ENFORCEMENT SPLIT IS ALSO WRONG WAY ROUND, MEASURED.** A one-hop shape scan over this corpus
names 260 of 935 shaped conditions and catches **1 of the 4** instances. Extending the behavioural
drive in `scripts/check_first_use.py` with two further entry kinds, one that AUTHORS an artifact
through the module's own canonicalization and one that adds a legitimate consumer, catches **4 of 4**
with no false-positive class, and is finding 38's own recorded repair. So the scan is the weaker half,
not the enforcing half.

**TWO FACTUAL CORRECTIONS THE DECISION RECORD NEEDS AT VERSION 3.** The ledger records at least eleven
instances of this shape, not four. And VELDO-0003 AC5 is NOT fixed: commit a0b3c98 closed that item's
blocker and left `_ts_loaders == []` at `scripts/suites/20_veldo_0003_task_source.py:578` untouched,
so one instance is LIVE in the required unit stage right now, and the gate will redden the first time
anybody wires the task read model into `.veldo/` or `scripts/`.
