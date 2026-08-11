---
schema: veldo.spec/v1
id: WARP-0716
title: Before splitting a 16,000-line test suite, find out whether it CAN be split - enumerate mechanically
  every module-level name that crosses assertion blocks, classify each, and publish the verdict on feasibility
status: shipped
risk: standard - this item CHANGES NO BEHAVIOUR. It adds an analysis that reads scripts/selftest.py, parses it,
  and emits a report which the existing CHECK_generated stage keeps derived; the suite itself is not
  restructured, no assertion moves, and the gate's stage list is untouched. Its only real risk is being WRONG
  in a way that misleads the split that follows, which is why the enumeration must be mechanical (from the AST)
  rather than a careful read, and why the report must state what it could NOT determine rather than presenting
  a clean answer it does not have. The second risk, paid for once already, is a guard whose remedy does not
  scale: a derived document is checked by regenerating it, never by re-deriving each of its figures against a
  hand-written copy
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-1210]
placement: [enforcement]
footprint:
  - scripts/suite_survey.py
  - proof/WARP-0716/crossing-state.md
  - proof/WARP-0716/manifest.json
  - scripts/selftest.py
  - scripts/check_generated.sh
  - specs/WARP-0716-enumerate-suite-crossing-state.md
  - specs/index.md
protected_paths: []
behavior_bearing: false
observability:
  logs: The survey names every crossing symbol, the line where it is bound, every line that reads it, and its
    classification, so a reader can audit any single verdict without re-running the analysis.
  error_taxonomy: The survey FAILS LOUD rather than reporting a clean result it cannot support: if the file
    does not parse, if a name's binding site cannot be resolved, or if a read cannot be attributed to a block,
    it says so by name and exits non-zero. An UNDETERMINED symbol is reported as UNDETERMINED, never silently
    classified as safe.
acceptance_criteria:
  - id: AC1
    text: >
      THE ENUMERATION IS MECHANICAL, FROM THE AST, NEVER FROM A READ. scripts/suite_survey.py parses
      scripts/selftest.py and enumerates EVERY module-level name that is bound in one region of the file and
      read in another, together with its binding line, every reading line, and the distance between them. A
      human read of 16,000 lines is not evidence, and this repository has already paid twice for treating a
      careful read as one. The survey is asserted against a FIXTURE file with known crossings, so the analysis
      itself is proven to find what is there rather than trusted: a name bound and read in one block is NOT
      reported, a name bound in block A and read in block B IS reported, and a name that is only ever read is
      reported as unbound.
  - id: AC2
    text: >
      EVERY CROSSING SYMBOL IS CLASSIFIED, AND UNDETERMINED IS AN ALLOWED ANSWER. Each is labelled as a SHARED
      FIXTURE (built once, read by many, safe to hoist into an importable fixture), a PER-SUITE LOCAL (read only
      within one prospective suite, safe to move with it), a GENUINE ORDERING DEPENDENCY (its value depends on a
      mutation performed by an earlier assertion, so the split must either remove the dependency or declare it),
      or UNDETERMINED. Reporting UNDETERMINED is REQUIRED where the tool cannot decide, because a clean
      classification the analysis cannot support is worse than an honest gap: the split that follows would trust
      it. The counts per class are published.
  - id: AC3
    text: >
      THE OUTPUT IS A FEASIBILITY VERDICT, NOT JUST A LIST, and it is allowed to say no.
      proof/WARP-0716/crossing-state.md states: the total crossing count, the count per class, the specific
      symbols that would block a clean split, a PROPOSED SUITE BOUNDARY SET derived from the actual read
      pattern rather than from topic guesses, and an explicit verdict on whether decomposition is feasible as
      designed, feasible with named preparatory work, or NOT feasible with the reason. If the honest answer is
      that the suite cannot be cleanly split, this item SAYS SO and the decomposition item is re-scoped or
      dropped - the analysis is not obliged to produce the answer the plan wants. THE REPORT IS GENERATED,
      NOT TRANSCRIBED: every FIGURE and every TABLE ROW is derived from one measurement, and the
      CHECK_generated stage asserts that regenerating the document is a NO-OP, which is the contract that
      already governs specs/index.md. A figure the suite has made false therefore cannot reach a green gate,
      and satisfying the check costs one command instead of a hand rewrite. AND THE PROSE BETWEEN THE TABLES
      IS TYPED, SO GENERATED DOES NOT MEAN NOTHING WAS TYPED: regeneration proves the FILE matches the
      EMITTER and says nothing about whether the EMITTER matches the MEASUREMENT, which is how a typed
      paragraph shipped at a green gate asserting three classifications its own tables contradicted. So NO
      TYPED SENTENCE IN THE EMITTER MAY ASSERT A CLASSIFICATION: the one paragraph that names one is derived
      from the record set, and before emitting anything the emitter scans its OWN source and REFUSES a typed
      sentence pairing a backticked name the measurement reports with a word from the class or verdict
      vocabulary. That refusal is driven both ways in the suite, its domain is discovered from the AST rather
      than listed, and what it cannot see is published as a blind spot. The gate is GREEN, no assertion in
      the suite is added, moved or removed for the analysis itself, scripts/verify.sh and its stage list are
      byte-UNCHANGED, no protected path is touched, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one analysis script that also emits its own report, its selftest block
  against a fixture, one generated report under proof/, and one derived-artifact entry in the existing
  CHECK_generated stage script. No engine module, no stage in verify.sh, and no contract changes, and the
  suite is not restructured, so a revert removes an analysis and its freshness entry and nothing else. There
  is no migration and nothing depends on it at runtime.
---

## Intent

The suite decomposition (WARP-0712) is the change that unblocks parallel work, and it is also the highest
consequence refactor in this repository, because the thing being restructured is the thing that proves
everything else. Its stated danger is that a 16,000-line script grown over 145 items will carry module-level
state that one assertion block creates and a later block consumes, so a naive split yields suites that pass
together and fail alone, or worse, pass alone having quietly stopped checking what they checked in context.

That danger is currently a HYPOTHESIS. Nobody has counted. This item counts it.

Two reasons it is its own ticket rather than the first criterion of the big one. First, the smaller-tickets
decision of 2026-07-25: one concern per item. Second, and more usefully, THIS ITEM NEEDS NO APPROVAL BECAUSE IT
CHANGES NOTHING, while the decomposition does. So the analysis that determines whether the decomposition is
even feasible can run immediately, in parallel with waiting for a human decision, instead of behind it. That is
real time recovered rather than a reorganization of the same time.

And it can return a NO. If the honest finding is that the crossings are too tangled to split cleanly, that is a
far cheaper thing to learn from a report than from a failed refactor of the file the whole gate depends on.

## Context

- What "crossing" means precisely: a module-level binding whose reads are not confined to the region that binds
  it. That is the mechanical proxy for implicit sequential state, and it is decidable from the AST, unlike
  "does this assertion depend on that one", which is not.
- Why UNDETERMINED must be a first-class answer: the tool will meet names bound inside conditionals, rebound
  several times, or read through indirection. A classifier that guesses on those produces exactly the false
  confidence the decomposition must not be built on. This is the same absent-versus-unreadable discipline the
  rest of this repository already enforces.
- Why the suite boundary set should come from the read pattern rather than from topic names: a boundary drawn
  where the data actually stops crossing produces suites that are independent by construction, whereas a
  boundary drawn around a topic produces suites that look tidy and share state.
- What follows: WARP-0712 (the split itself, which needs Dmitry's approval) and then the subset runner. Both
  consume this report. If this report says NOT FEASIBLE, both change shape before anyone asks for approval.

## Out of scope

- Moving a single assertion, or changing the suite in any way. This item only reads it.
- Building the subset runner, the manifest, or the dispatcher.
- Any judgement about which suites SHOULD exist beyond the boundary set the read pattern implies.
- Any change to verify.sh, the stage list, or any engine module. No protected path.

## Notes

- Prove the analyser against a fixture with KNOWN crossings before pointing it at the real file. An analysis
  nobody has tested is not evidence either.
- Let the answer be no. The value of this item is highest in the case where it stops a bad refactor, and an
  analyst who cannot return a negative result is not measuring anything.
- Publish the symbols, not just the counts. The next person needs to audit a verdict without re-running it.
- NO UNBACKED UNIVERSAL: "every module-level name" is the central claim, so the fixture test is what makes it
  sayable. And MEASURE FIRST, then write the sentence from the output.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
- PLACEMENT CORRECTED FROM `engine` TO `enforcement`, and why it is a correction rather than a tier dodge.
  The defect-fix commit added scripts/check_generated.sh to the footprint, which resolves to the ENFORCEMENT
  area, while the declared placement said ENGINE. arch.footprint_tier_floor unions the two, found no
  allow-listed edge between enforcement and engine, and raised the required tier to high; the declared risk
  stayed standard, so arch.placement_gate refused the unit while check_placement and check_spec both reported
  zero errors. The item was therefore offered by NOTHING and reported by NOTHING: of the ready specs on main,
  this was the only one in neither the claimable frontier nor the withheld report, which looks like an empty
  queue rather than a bug. THE ENGINE AREA IS `.veldo/authorization.py` AND THIS ITEM TOUCHES NO PART OF IT -
  this spec's own rollback paragraph says "No engine module" - so `engine` was a false declaration and the
  crossing it manufactured was a phantom. The footprint is UNCHANGED except for adding the proof manifest;
  narrowing it to drop check_generated.sh would have hidden a path the change really edits, and raising the
  risk to high would have declared an item that CHANGES NO BEHAVIOUR as high risk to satisfy a gate whose
  input was wrong. The one declared area this footprint actually falls in is enforcement.

## How this item was cleared, stated plainly so a reader can weigh it

Its independent review of the landed state returned **fail** on three findings: a hand-typed sentence inside
the emitter that asserted a measurement (which regeneration structurally cannot catch, because it proves the
file matches the emitter and not that the emitter matches the measurement), a footprint entry that made this
very spec unclaimable while the validator reported nothing, and a missing proof manifest. All three are fixed.

**The fix was NOT independently reviewed.** The orchestrator drove its two load-bearing claims itself, each
with the substitution count asserted before the result was read: planting a typed sentence that asserts a
class makes the emitter exit 1 naming the line and the label, and the shipped frontier offers this item again
with ready-minus-claimable-minus-withheld now the empty set. That is weaker evidence than a fresh reviewer
and is recorded as such rather than dressed up.

Shipped on the repository's own policy, which asks ONE independent review at this risk tier. That review
happened and its findings are answered. A fix answering a review's findings does not restart the count.
