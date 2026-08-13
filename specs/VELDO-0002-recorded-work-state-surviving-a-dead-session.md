---
schema: veldo.spec/v1
id: VELDO-0002
title: What is done, what nobody concluded, and what is queued - one derived answer that survives a
  dead session, and that says plainly when it cannot confirm a run is alive rather than guessing
status: ready
risk: standard - it adds a READ-ONLY reader over artifacts and a run registry that both already
  exist, writes nothing, and gates nothing, so no change can be refused because of it. It is NOT low
  because the answer it gives is the one an operator acts on after losing a session, and an answer
  that quietly omits work is worse than no answer at all: the failure it exists to prevent already
  happened once and cost four built items that survived only because a human went looking. It is not
  high because it holds no state of its own, so the retreat is deleting one module
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W1
placement: [contracts]
footprint:
  - ".veldo/work_state.py"
  - "engine/.veldo/work_state.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/19_veldo_0002_work_state.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0002-recorded-work-state-surviving-a-dead-session.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    One report, whose every section names its own source: the corpus half says which artifact made
    each item done, the run half says which run folder and which commit a claim came from, and the
    uncovered half names each direction of disagreement separately. A reader who lost a session gets
    a path to look at, never a count to trust. ONE EXCEPTION, STATED BECAUSE IT IS A COUNT: the
    unclaimed bundles the registry was NOT recording for are reported as a count per reason rather
    than a line each, and their paths are kept in the report under unrecorded_out_of_reach. The
    exception exists because a line each was measured to hand an operator 142 paths that named
    nothing wrong and to bury the one run that had gone stale, and a count of items this reader
    declines to accuse is not a count anybody has to trust.
  error_taxonomy: >
    Four distinguishable states for one item, never collapsed, because the operator's next action
    differs in each: DONE (its manifest is on disk and a verdict artifact RECORDS a passing review),
    UNCONCLUDED (a run claimed it and no artifact concludes it - go look at the named folder), QUEUED
    (no complete bundle and no run claiming it, WHATEVER STATUS ITS SPEC DECLARES) and UNRECORDED
    (finished artifacts no run claimed, WHERE THE REGISTRY WAS RECORDING WHEN THEY LANDED, which is
    the shape of work a dead session left behind). The two qualifications in capitals are corrections
    an independent review measured, and both are about a number an operator acts on rather than about
    wording. QUEUED said "ready, unclaimed" and the reader filters nothing: on this repository 73
    queued was 30 ready, 34 shipped, 6 draft, 1 blocked and 2 declaring nothing, so the count read as
    a work queue that it is not. Deciding what QUEUED should MEAN is a change to this taxonomy and is
    NOT made here; the declared status travels with every item and the report prints the composition
    beside the count. UNRECORDED accused every unclaimed done item, which is a POPULATION rather than
    a defect set: a registry starts empty and this one was flattened at migration, so creating ONE
    run folder took the report to 144 lines, 142 of them UNRECORDED alarms naming work that landed
    weeks earlier and burying the one run that had actually gone stale. Its domain is now the bundles
    the registry was in a position to judge, decided from the registry's own earliest recorded run
    start and each manifest's own produced_at, and every unclaimed bundle outside that window keeps
    its paths under a count that names the reason the registry cannot speak to it. A run whose
    liveness cannot be confirmed is reported as LIVENESS_UNCONFIRMED with the age of its last
    heartbeat, never as running and never as dead, because this module cannot tell those apart and
    saying either would be a guess an operator would act on; a run that recorded a terminal status is
    reported as the status it recorded, and DONE and ABORTED are two answers rather than one word
    built from the reassuring half. The three ways there is no age - never written, unreadable, or
    stamped in the future - are named separately, because they used to share one message and that
    message was the strongest available negative. WHAT THIS TAXONOMY CANNOT EXPRESS, recorded here
    rather than papered over: there is no state for REVIEWED AND REJECTED, and none for BUILT AND
    AWAITING REVIEW. An item whose verdict artifacts all record a rejection is reported UNCONCLUDED
    when a run claimed it and QUEUED otherwise; an item whose manifest is on disk with no verdict of
    any kind - which is EVERY item between the producer's write and the reviewer's - is reported
    QUEUED, the same bucket as work nobody has started. Each gets a LINE AND A PATH saying which it
    is, because a fifth state is a change to this taxonomy and this item does not make one. The
    operator reads the path, not the bucket.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      TWO MUTATIONS, because this criterion asserts two things about where DONE comes from, and each
      must red a row that names it. ONE: delete the artifact half of the partition in
      .veldo/work_state.py so DONE is read from the run registry's status field instead of from the
      proof and verdict on disk, and the assertion that a run recording status done for a spec with NO
      proof bundle is reported UNCONCLUDED rather than DONE must go red. TWO: make DONE read the
      EXISTENCE of a verdict artifact instead of the verdict it records, and the assertion that a
      complete bundle whose verdict records a rejection is NOT done must go red.
    text: >
      DONE IS DERIVED FROM THE ARTIFACTS, NEVER FROM WHAT A RUN SAID ABOUT ITSELF, AND A VERDICT
      FILE IS NOT A CONCLUSION - WHAT IT RECORDS IS. An item is DONE when its manifest is on disk
      and a verdict artifact RECORDS a value from the passing set the loop already declares
      (executor.PASSING_VERDICTS, taken from that module rather than re-spelled), read from the
      file's bytes, and for no other reason. A run folder claiming status done for a spec with no
      such artifacts is reported UNCONCLUDED with the folder named, because a process that says it
      finished and left nothing behind is the exact shape of the 2026-08-10 loss. A bundle whose
      verdict records a rejection, or whose verdict cannot be read at all, is NOT done either:
      MEASURED, and the reason this sentence is here, reading existence reported TWELVE rejected
      items on this repository as done, the independent review that FAILED this very item among
      them, under a headline of "154 done, 0 unconcluded". An operator told done about rejected work
      stops looking at exactly the work that needs them. NEGATIVE CONTROL: a spec whose artifacts
      ARE on disk is reported DONE even when no run folder mentions it at all, so the artifact half
      is what decides and the run half cannot veto it. SECOND NEGATIVE CONTROL, ADDITIVE: the same
      rejected bundle with a later-round verdict ADDED that records a pass IS done, because every
      multi-round review here leaves the failing round on disk as the record, so this is a
      measurement of what the verdicts say and not a refusal of any bundle that carries a failure.
  - id: AC2
    falsified_by: >
      Replace the liveness branch in .veldo/work_state.py with a return of "running" whenever a run
      folder exists, and the assertion that a run with a heartbeat older than the staleness window is
      reported LIVENESS_UNCONFIRMED carrying the heartbeat age must go red.
    text: >
      A RUN WHOSE LIVENESS CANNOT BE CONFIRMED IS SAID TO BE UNCONFIRMED, WITH THE AGE, AND IS NEVER
      CALLED RUNNING OR DEAD. This module reads a heartbeat written by a process it cannot see; a
      stale heartbeat means the process may have died, may be paused, or may be about to write. It
      reports LIVENESS_UNCONFIRMED and the age of the last heartbeat, and the operator decides. THE
      AGE IS THE PRODUCT, not the classification: 31 seconds and 15 hours are the same word in
      runlog.classify and they are not the same fact to a person who just lost a session. NEGATIVE
      CONTROL: a run heartbeating now is reported as active, so the unconfirmed report is a
      measurement of the heartbeat rather than the module's only answer.
  - id: AC3
    falsified_by: >
      Drop the uncovered-artifacts direction from the report in .veldo/work_state.py, keeping only
      run folders with no artifacts, and the assertion that a proof bundle no run folder ever claimed
      is reported UNRECORDED must go red.
    text: >
      DISAGREEMENT IS REPORTED IN BOTH DIRECTIONS, BECAUSE THEY ARE DIFFERENT FAILURES. A run folder
      whose spec has no artifacts is work that may be half-finished; a proof bundle no run ever
      claimed is work that COMPLETED off the record, which is precisely what happened on 2026-08-10
      and is invisible to any reader that only walks the run registry. Both are named, separately,
      with the path. NEGATIVE CONTROL: a spec that is both claimed and concluded appears in NEITHER
      uncovered list, so the lists are a disagreement measure and not a restatement of the corpus.
  - id: AC4
    falsified_by: >
      Make the report return zeros and empty lists when the runs root does not exist, instead of
      standing down with a reason, and the assertion that an absent runs root produces a NAMED
      stand-down rather than a zero must go red.
    text: >
      NO CONFIDENT ZERO. When the run registry does not exist at all, the report STANDS DOWN and says
      so with the reason, because "no run has ever been recorded here" and "no run is in flight" are
      different facts and a zero cannot tell them apart. The corpus half still answers, since it
      reads artifacts that do not depend on the registry, and the report says which half stood down.
      This is the disease this migration kept finding, written into the one organ whose whole job is
      to be trusted after a loss.
  - id: AC5
    falsified_by: >
      Hand-list the artifact patterns the corpus half walks in .veldo/work_state.py instead of taking
      them from verdict_corpus, WITH THE VALUES UNCHANGED, and the assertion that a tree whose
      verdict_corpus declares RENAMED patterns makes this reader walk the renamed ones must go red.
    text: >
      THE CORPUS IS THE ONE ALREADY DECLARED, NOT A SECOND SPELLING OF IT. The artifact half
      enumerates through .veldo/verdict_corpus.py, the module that already owns what a corpus path is,
      and it takes EVERY corpus pattern that module declares, found by the naming rule rather than by
      copying names or values, so a rename or an addition there arrives here without an edit. A
      hand-kept copy is how this repository has already shipped two mechanisms enumerating one set in
      two spellings, with the gap invisible to both. THE CHECK IS A SUBSTITUTION, NOT AN EQUALITY,
      and the reason is measured: an independent review drove the hand-list with the values unchanged
      and the suite and the whole gate stayed GREEN, because value equality between two reads of the
      same constants can only catch a WRONG pattern and never a copy that copies correctly, which is
      the entire defect this criterion names. So the suite substitutes a verdict_corpus declaring
      renamed patterns and requires this reader to walk THOSE - a bundle named for them is done, and
      a bundle named for the values this repository happens to use today is not. Set equality against
      that module's own declarations is asserted too, derived from its declarations rather than from a
      literal written in the suite, which is where the second spelling had moved.
required_evidence: [unit]
rollback: >
  Delete .veldo/work_state.py and its suite fragment. Nothing else reads it, no gate stage runs it,
  and no artifact records it, so the retreat is one file and one manifest entry and loses nothing
  that was not already on disk.
---

# What is done, what nobody concluded, and what is queued

## The failure this exists to prevent, dated

On 2026-08-10 a session died with parallel work in flight. Four items had been fully built. They
survived because a human went looking through worktrees and found them. Nothing in the method could
answer the question "what is done", and the plan that recorded this said so in one line: **nothing
tracked that four items had been built.**

The measure PLAN-0018 sets for this item is exactly that scenario: kill a session mid-flight, start a
fresh one, ask what is done, and get the right answer without anyone grepping worktrees.

## What already exists, and why this is a reader rather than a store

`.veldo/runlog.py` already keeps per-run state under the git common dir: outside git history, shared
across worktrees, carrying the spec id, the head it started from, a pid and a heartbeat. It already
refuses to call a run active when it cannot confirm liveness, in those words.

So the substrate is not missing. What is missing is that **it answers about runs and never about the
work**. Done and queued live in the tracked artifacts; in-flight lives in the registry; and nothing
joins them. An operator who lost a session has two half-answers and no partition.

This item adds no state. It writes nothing. It is a join with a hard rule about which side wins:
**the artifacts decide what is done, and the registry only says what was claimed.** A process that
announced its own success and left nothing behind is the failure mode, so its own word is exactly
what must not be trusted.

## Why the age of a heartbeat is the product

`runlog.classify` returns `stale` for a heartbeat 31 seconds old and for one 15 hours old. That is
correct for its purpose, which is liveness. It is useless for this one. A person who just lost a
session needs to know whether the thing that stopped writing stopped a moment ago or last night,
because that is what tells them whether to wait or to go look.

So this reports the age and refuses to convert it into a verdict about the process. It cannot see the
process. Saying "dead" would be a guess, and saying "running" would be the same guess wearing a more
reassuring word.

## What an independent review found, and what changed

An L2 review at dda45bf confirmed AC1 to AC4 by driving their declared falsifications, and REFUTED
AC5: it applied that criterion's own declared mutation, hand-listing the corpus patterns with the
values unchanged in both mirrors, and the suite stayed at 43 passed 0 failed with the whole gate
GREEN. The row only reddened when the hand-list also changed a VALUE, which is a different defect
that AC1 and AC3 already catch. **Value equality between two reads of the same constants cannot
detect a copy that copies correctly**, which is the entire defect AC5 names, so AC5's check is now a
SUBSTITUTION: the suite builds a tree whose `verdict_corpus` declares renamed patterns and requires
this reader to walk those. Two sentences of AC5 were also false about the code, and both are
corrected above: that module declares FOUR corpus patterns rather than the two the old row compared
against, and the "declared" set the old row measured was a two-element literal written inside the
suite, so the second spelling had moved into the test rather than disappearing.

The same review measured something worse than any single criterion, on the live tree: **the reader
gave the wrong answer about this repository**. It called an item DONE because a file named
`verdict.json` existed, never reading what the verdict SAID, so twelve items whose only verdict on
disk recorded `fail` were reported done under a headline of "154 done, 0 unconcluded" - including
this item's own failing review. AC1's second half is that fix, and the honest limit is written into the taxonomy
above: the four states cannot say REVIEWED AND REJECTED, a fifth state is a change to this item's
declared taxonomy, and it is NOT invented here. A rejected item falls back to UNCONCLUDED or QUEUED
and the report names it with the path of the verdict that rejected it.

## What the SECOND independent review found, and what changed

A second L2 review at 93c1c8d drove the same criteria and reported six defects in the ANSWER rather
than in any criterion, every one of them measured over the live tree. They are closed in
`.veldo/work_state.py` and in the taxonomy above, and they share one shape: a number that reads like
a measurement and is not.

- **The reader answered its own scenario wrongly.** A bundle is written in two stages, so every item
  that is BUILT and awaiting review is a manifest with no verdict, and that was reported QUEUED with
  no line and no path - the bucket for work nobody has started. PLAN-0018's measure for this item is
  "kill a session mid-flight, start a fresh one, ask what is done, and get the right answer"; a fresh
  session asking was told the built items were queued. It now gets a line and a path, and no fifth
  state, for the reason the taxonomy already gives about reviewed-and-rejected.
- **Using the run registry once turned the report into 142 false alarms.** UNRECORDED accused every
  unclaimed done item, so the first run folder to appear made every historically landed spec qualify
  and buried the one run that had gone stale. Fixed by changing the DOMAIN rather than the
  comparison, per ledger findings 51 and 63: the accusation now needs the registry to have been
  recording when the bundle landed, decided from the registry's own earliest run start and the
  manifest's own produced_at, and everything outside that window keeps its paths under a count that
  names why the registry cannot speak to it.
- **A confident zero survived inside the criterion that forbids confident zeros.** The headline
  printed "0 unconcluded" beside the stand-down, although UNCONCLUDED is defined entirely by a
  registry claim and QUEUED rests on the same predicate. The two are now reported as one NOT
  CONCLUDED number with the reason, and the report dict names which counts are consequences of the
  stand-down rather than measurements.
- **QUEUED was not what this taxonomy said it was.** The reader's own docstring had already been
  corrected to say it filters nothing while the count an operator acts on had not; the report now
  prints the composition by declared status.
- **An ABORTED run was reported with the word done**, and the run's own recorded status never reached
  the printed line. Two answers now, and the line carries what the run recorded.
- **The heartbeat, which this item calls its product, had two spellings that printed the wrong
  fact.** A stamp two seconds old in an offset-bearing ISO spelling printed "no heartbeat ever
  recorded", the strongest negative available, and a future-dated stamp printed "active, last
  heartbeat 0s ago", the most reassuring, from a clock this reader cannot verify. The parser accepts
  the ISO spellings, the staleness window still has one owner, and never-written, unreadable and
  future are three named answers.

The same review reported two defects that are NOT this item's, both live at that commit, recorded
rather than fixed here: the gate reddened for any reviewer who wrote a verdict artifact without
committing it, which ledger finding 46 has since closed, and the L2 verdict shape the reviewers were
handed declares a findings vocabulary `.veldo/validate.py` refuses.
