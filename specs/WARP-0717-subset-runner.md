---
schema: veldo.spec/v1
id: WARP-0717
title: A one-second inner loop for a one-line fix - run a named suite alone, and make a partial run
  STRUCTURALLY incapable of being mistaken for a gate pass
status: shipped
risk: high - this item creates a fast path, and a fast path next to a slow gate is a standing invitation to
  treat the fast one as verification. The method's central law is that a green verify.sh is the ONLY definition
  of done, so the danger here is not a bug, it is EROSION: a partial run that looks authoritative, gets quoted
  as one, and quietly becomes the bar. Labelling is not sufficient protection against that, which is why the
  criteria require the partial run to be unable to write the verify stamp, unable to satisfy required-evidence,
  and unable to emit the line the gate parses. It touches no protected path and changes no assertion
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-0712]
placement: [engine]
footprint:
  # AMENDED BY THE BUILD, ON THE RECORD. Two of the paths originally declared here DO NOT
  # EXIST and could never have existed: there is no engine/scripts/selftest.py and
  # no packs/*/scripts/selftest.py. Measured: .veldo/packs.json declares engine the
  # canonical engine for every pack, and .veldo/pack.py's ENGINE_GLOBS matches scripts/*.py
  # UNDER THAT ROOT, where no selftest.py has ever lived. The unit suite is THIS repository's
  # own assertions about its own engine; shipping it to adopters would ship our tests. So the
  # selector is not engine canon, nothing needs re-syncing, and AC3's canon clause is
  # satisfied by the canon being UNTOUCHED, asserted as absence against the declared pack
  # roster. Two paths are ADDED: scripts/run_scope.py, the module that owns what a run may
  # claim, and scripts/check_generated.sh, which holds the derived closure table fresh.
  #
  # A THIRD DEFECT, ALSO MEASURED: `scripts/suites/` and `docs/` matched NOTHING. The one
  # glob compiler (.veldo/arch.py _glob_re) gives `*` and `**` their meanings and nothing to a
  # trailing slash, so a bare directory entry is an exact-path pattern for a path that is
  # never a file. The subtree form in use elsewhere in this corpus is a quoted `path/**`, and
  # that is what these two are now. The shape gate named all five uncovered paths on the
  # first run, which is the enforcement working.
  #
  # THREE PATHS ADDED BY REVIEW 1'S CORRECTIONS, declared rather than left to the rule's
  # stand-down. scripts/suite_extract.py is the migration tool whose embedded templates
  # cross-item finding X2 heads as historical. The WARP-0729 spec is the item review 1's X1
  # asks for, written in this pass because four other shipped specs carry that defect and one
  # item has to own the class; it declares no footprint of its own ON PURPOSE, since a second
  # footprinted spec in one change set makes the footprint rule stand down, which is exactly
  # the vacuous outcome that spec exists to close.
  - scripts/selftest.py
  - scripts/run_scope.py
  - scripts/check_generated.sh
  - scripts/suite_extract.py
  - "scripts/suites/**"
  - "docs/**"
  - specs/WARP-0717-subset-runner.md
  - specs/WARP-0729-footprint-globs-must-match-a-path.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: A partial run prints a banner naming itself a PARTIAL run that does not constitute verification, states
    which suites ran and which were skipped, and reports its own elapsed time. A reader of any captured output
    can tell a partial run from a gate run without knowing which command produced it.
  error_taxonomy: One new refusal, PARTIAL_RUN_CANNOT_VERIFY, raised if a partial run is ever asked to write
    the verify stamp or to satisfy the required-evidence check. It is a refusal rather than a warning because a
    warning is a thing people learn to ignore.
acceptance_criteria:
  - id: AC1
    text: >
      RUNNING ONE SUITE BY NAME IS USEFUL, AND HONEST ABOUT WHAT IT RAN.
      `python3 scripts/selftest.py --suite <name>` runs the named suite TOGETHER WITH ITS MEASURED TRANSITIVE
      PREREQUISITE CLOSURE and nothing else, reproducing exactly the labels that suite produces in a full run,
      with the selected suite's own assertion count and elapsed time reported. Selecting an unknown suite name is
      a REFUSAL naming the available suites, never a silent zero-assertion pass, because a run that selects
      nothing and exits 0 is the most dangerous possible output of this feature. Selecting several suites is
      supported and reported as the union. This is the whole point of the item: WARP-1210 spent about four hours
      in a red-gate loop paying the full suite for one-line fixes.


      AMENDED BY THE BUILD, ON THE RECORD, BECAUSE "EXACTLY THAT SUITE" WAS MEASURED IMPOSSIBLE AND "ABOUT A
      SECOND" WAS MEASURED FALSE FOR MOST OF THE SUITE. This criterion originally said the command "runs exactly
      that suite and completes in about a second". Neither survived measurement.


      ONE: EXACTLY THAT SUITE. WARP-0712's committed review evidence reports every one of the fragments
      PASSES_IN_AGGREGATE_FAILS_ALONE, and scripts/suites/manifest.json says why in its own note: these are
      FRAGMENTS executed into ONE namespace in manifest order, not independent modules, because the monolith
      carried cross-region dependencies through MUTATED OBJECTS and through the FILESYSTEM and not only through
      names. Run alone, a fragment dies on a NameError. So "exactly that suite" is not reachable for any fragment
      that is not first, and an implementation claiming it would be either faking it or silently redefining the
      words. THE CRITERION IS THEREFORE THE NAMED SUITE PLUS ITS MEASURED TRANSITIVE PREREQUISITE CLOSURE, read
      from the derived scripts/suites/requires.json, with the LANDING CONDITION being label identity: the named
      suite's own assertion labels and their pass/fail outcomes must be IDENTICAL to what it produces in a full
      run. Measured this round over every fragment, recorded in proof/WARP-0717/inner-loop-measurement.json:
      13 of 13 CLOSED, identical labels, identical outcomes.


      THE CLOSURE MUST BE TRANSITIVE, and that is a measurement rather than a preference. Derived from each
      fragment's DIRECT demand only, 8 of 13 were CLOSED and 5 of 13 produced ZERO of their own labels, because a
      fragment INSIDE the closure crashed before the target began: fragment 13's direct demand names fragment 06
      but not 03 or 04, which 06 itself needs, and the run died on `NameError: name '_FakeLoop' is not defined`.
      A prerequisite set that is not closed under its own relation is not a prerequisite set.


      THE TABLE IS DERIVED FOR THE FRAGMENTS THE CUT COVERED AND HAND-TYPED FOR EVERY FRAGMENT ADDED SINCE, which
      is review 1's C5 and is the half that governs everything added from now on. Calling the closure table
      derived is true for the 13 fragments that have a region range in the WARP-0712 measurement. A fragment
      written after that cut has no range, so `direct_demand` takes the `requires` list A HUMAN TYPED in
      manifest.json at face value and merely closes it transitively. FAIL-CLOSED COVERS A MISSING DECLARATION,
      NEVER A WRONG ONE, and the consequence of a wrong one was measured this round in a copy of the repository
      under /tmp: a fifteenth fragment declaring `requires: [itself]` while using `PL`, a name fragment 01 binds,
      was ACCEPTED by the generator at exit 0; the requires.json freshness entry PASSED; and
      `--suite <it>` died on `NameError: name 'PL' is not defined`, exit 1, with ZERO verdict lines of any kind,
      which is the dead-run shape this repository calls worse than a red. In the same tree the FULL run executed
      that fragment's assertion and it passed. So a post-cut fragment's declaration is worth exactly the
      label-identity check behind it, which is why every one of them is measured in
      proof/WARP-0717/inner-loop-measurement.json rather than trusted.


      TWO: ABOUT A SECOND. Measured on the build box, whole run 93.45s at 3362 passed. WHICH OF THE FIGURES IN
      THIS PARAGRAPH ARE MEASURED AND WHICH ARE MODELLED, review 1's C7: each fragment's own time and each
      CLOSURE run are measured, and every "against N.NNs" figure for the PREFIX is MODELLED, summed from
      per-fragment times measured inside one full run rather than driven as `--upto`. The artifact labels them
      prefix_modelled_s and closure_modelled_s beside the single closure_measured_s. Review 1's own independent
      runs landed within about 2 percent. The only artifact whose numbers are wall-clock timings of shipped
      commands is proof/WARP-0717/timings.txt, which says so about itself. Per fragment, the closure
      run against the modelled prefix `--upto` gave: fragment 05 is 0.04s against 21.35s, fragment 01 is 1.62s,
      fragment 03 is 3.62s, fragment 04 is 6.93s, fragments 06 through 11 are 10.21s to 12.93s against 24.80s to
      27.70s, fragment 13 is 46.85s against 93.45s, and fragment 12 is 59.42s against 74.07s. So "about a second"
      is true for 2 of 13 fragments and false for the rest. THE CRITERION IS THEREFORE THAT THE SELECTOR RUNS A
      MEASURED-MINIMAL SET AND REPORTS ITS OWN COST, not that it hits a fixed wall-clock target. THE REASON IS
      WORTH RECORDING BECAUSE IT SHAPES WHO BENEFITS: the cost is not spread evenly, it is concentrated. Fragment
      02 is 15.02s and fragment 12 is 46.37s of the 93.45s total. The closure excludes 02 for 11 of the 13
      fragments and excludes 12 for all but 12 itself, and that is where every second of the saving comes from.
      An engineer iterating on a small fragment gets an inner loop. An engineer iterating on fragment 12 still
      pays about 59s, because half the suite's cost is inside the thing being edited. Making THAT fast is a
      different item about what fragment 12 spends its time on, and is not this one.


      THREE: IS IT MERELY --upto RENAMED. Asked and answered with the measurement, because `--upto` already
      existed and already gave a fast prefix run. It is a genuine addition: for 11 of the 13 fragments the
      closure is a STRICT SUBSET of the prefix, and the measured difference ranges from 15.02s to 46.37s off the
      run. For the 2 remaining fragments the closure IS the prefix and `--suite` buys nothing over `--upto`,
      which is stated here rather than averaged away. `--upto` is unchanged in behaviour and still exits 2 on
      success; both selectors now share one emitter, and the pre-existing partial line is a strict PREFIX of the
      new one, which carries the elapsed time.


      FOUR: AN UNRECOGNISED ARGUMENT REFUSES, NOT ONLY AN UNRECOGNISED NAME. Added for review 1's C3, which
      measured the hole: `--suite=<name>` is not the string `--suite`, so the equals form of EITHER selector was
      recognised by nothing, fell through every selector test and became a FULL run at exit 0 with the aggregate
      line printed. It failed in the SAFE direction, since a real full run happened and its line was true, but the
      feature's whole point was lost: a person chasing a fast loop silently paid the entire suite and read a green
      line as their subset's. Every argument beginning with `--` is now checked against ONE declared table and one
      that is not in it exits 2 as UNRECOGNISED_FLAG, which closes both equals forms and every future flag typo
      together rather than one spelling at a time. Driven through the real dispatcher for four shapes, with the
      three recognised shapes proven unchanged: `--list` byte-identical, both space-form selectors identical with
      elapsed times masked, and the no-selector run still emitting the aggregate line at exit 0. DECLARED LIMIT: a
      bare word that is not a flag's value is still ignored, because that shape cannot be mistaken for a selector.
      Before and after in proof/WARP-0717/flag-shapes.txt.
    id_note: fast path
  - id: AC2
    text: >
      A PARTIAL RUN IS STRUCTURALLY INCAPABLE OF COUNTING AS VERIFICATION, not merely labelled as partial. It
      CANNOT write the verify stamp (.veldo/last_verify), CANNOT satisfy the required-evidence check, and CANNOT
      emit the aggregate summary line that the gate and the operator guide parse - each asserted by a selftest
      that ATTEMPTS the thing and asserts the refusal PARTIAL_RUN_CANNOT_VERIFY by name, rather than asserting
      that the code does not contain a call. The gate stage continues to run the FULL manifest, proven by
      asserting scripts/verify.sh is byte-UNCHANGED and still invokes the suite with no selector. Green
      verify.sh remains the only definition of done, and this item is written so that a future person who WANTS
      to shortcut it has to change the gate to do so, which is a visible act.


      AMENDED BY THE BUILD, ON THE RECORD, ON HOW THE verify.sh CLAUSE IS PROVEN, AND ON WHICH OF THE THREE ACTS
      HAS TEETH TODAY. The property is unchanged and is not weakened; what changed is the instrument and what is
      claimed for it.


      ONE: BYTE-UNCHANGED IS PROVEN AS EVIDENCE, THE INVARIANT IS PROVEN AS A PROPERTY. A pinned digest of
      scripts/verify.sh inside the suite would turn red on any unrelated catalog edit, with the remedy being to
      re-pin the digest, which trains people to re-pin rather than to look. That is ceremony, not a guard. So the
      GATE asserts the durable invariant instead: the file declares exactly one unit slot, its command is
      `python3 scripts/selftest.py` with nothing following it, and NO selector flag appears anywhere in the file.
      Byte-identity for this round is recorded as evidence in proof/WARP-0717/, sha256 against the item's base
      commit, rather than frozen into an assertion.


      TWO: TWO OF THE THREE ACTS ARE FORWARD GUARDS AND SAYING OTHERWISE WOULD BE A FALSE SENTENCE. Emitting the
      aggregate summary line and returning the exit code have production callers on the real path
      (shared.report() and the dispatcher's exit), and the exit code is the mechanism by which a partial run
      cannot produce a green stamp: scripts/verify.sh writes .veldo/last_verify green only when its unit slot
      SUCCEEDS, and a partial run never returns 0. Writing the stamp and producing a unit-evidence record have NO
      production caller in this repository: the stamp is written by verify.sh in SHELL, and proof artifacts are
      written by hand. Their refusals are proven by attempt, and their non-vacuity by driving the FULL scope
      through the real verify.sh printf shape and the real validate.check_required_evidence, but what they buy is
      that the FIRST Python-side stamp writer and the FIRST generated evidence record must come through the
      scope. DECLARED BLINDNESS: nothing here can stop a human typing a passed unit check into a proof file, and
      it is also measured that check_required_evidence reads the evidence KIND and not its STATUS, so the refusal
      buys the withholding of the record and not a rejection of a forged one. The guard against a hand-typed
      claim is the review, and this item does not pretend otherwise.
  - id: AC3
    text: >
      IT IS DOCUMENTED AS AN INNER LOOP AND NOTHING MORE, in the operator guide, in one short paragraph that
      says plainly what it is for (iterating on a fix) and what it is not (evidence that anything works). The
      docs state that no proof manifest, no evidence claim and no landing decision may cite a partial run, and
      the genericity sweep keeps that text adopter-safe. Engine canon holds: the selector and its banner are
      re-synced byte-identical across engine and all six packs. No protected path is touched, the
      frozen safety core is byte-UNCHANGED, no existing assertion is added, moved or removed, the full gate is
      GREEN, and RULE #1 is clean.


      AMENDED BY THE BUILD, ON THE RECORD: THERE IS NOTHING TO RE-SYNC, BECAUSE THE UNIT SUITE IS NOT ENGINE
      CANON. This criterion asked for the selector and its banner to be re-synced byte-identical across
      engine and all six packs. Measured: .veldo/packs.json declares engine the canonical
      engine for every declared pack, .veldo/pack.py's ENGINE_GLOBS matches `scripts/*.py` under THAT root, and no
      selftest.py exists there or in any pack, because the unit suite is this repository's own assertions about
      its own engine and shipping it to adopters would ship our tests. So the selector lives only in
      repository-local files and THE CANON IS BYTE-UNCHANGED, which is the stronger outcome. THE CRITERION IS
      THEREFORE THAT THE CANON IS UNTOUCHED AND THE SELECTOR IS ABSENT FROM engine AND EVERY DECLARED
      PACK, asserted as absence against the pack roster read from .veldo/packs.json rather than a hand-written
      directory list, so a newly declared pack is covered without editing the assertion. The docs paragraph does
      ship, in docs/runbook.md III.1, and the genericity sweep binds it.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds a suite selector, a partial-run banner, one refusal name and a docs
  paragraph, re-synced byte-identical across engine and the packs. Reverting removes the fast path and
  restores the full-suite-only inner loop, which is a productivity regression and nothing more: no assertion,
  contract, stamp or gate stage changes either way, so there is no migration and no risk in reverting.
---

## Intent

Once the suite is decomposed (WARP-0712), running one part of it becomes possible. This item makes it usable,
and then spends most of its effort making sure it cannot rot the method.

The need is measured rather than assumed: WARP-1210's round-6 build spent roughly four hours almost entirely in
the red-gate debug loop, because every one-line fix paid a full multi-minute suite. Nine rounds of that is
where a large part of the 26 hours went.

The danger is equally concrete. The moment a one-second run exists next to a two-minute gate, the one-second
run starts getting quoted. Not maliciously - it is simply what is at hand. And the single law this method rests
on is that a green verify.sh is the ONLY thing that means done. A fast path that could plausibly be mistaken
for verification would erode that quietly, and nobody would be able to point at the moment it happened.

So the design principle here is that PROTECTION MUST BE STRUCTURAL, NOT ADVISORY. A banner saying "this is not
verification" is a thing people stop reading in a week. A partial run that physically cannot write the verify
stamp, cannot satisfy required-evidence, and cannot produce the line the gate parses is a thing that stays true
after everyone has forgotten why it was built that way.

## Context

- Why it is a separate item from the decomposition: the decomposition is a safety-critical refactor of the
  thing that proves everything else, and this is a convenience feature with one sharp edge. Bundling them would
  put a productivity nicety inside a high-risk refactor's review, which is precisely the over-sized-ticket
  pattern that cost this project nine rounds on WARP-1210.
- Why an unknown suite name must REFUSE: a selector that matches nothing and exits 0 reports success for having
  tested nothing. That is the same absent-versus-unreadable conflation this repository has been bitten by
  repeatedly, in a new place.
- Why the assertions must ATTEMPT the forbidden thing rather than grep for its absence: asserting that the
  source does not contain a call proves something about today's source. Asserting that the attempt RAISES
  proves something about the behaviour, and only the second survives a refactor.

## Out of scope

- The decomposition itself, the manifest, the dispatcher and the fixture extraction. WARP-0712 owns all of it,
  and this item does not begin until that has landed.
- Running suites CONCURRENTLY inside one invocation. That is a further win with its own risks (shared temp
  state, interleaved output) and is a separate item.
- Any change to what the gate runs, to the stage list, or to verify.sh. No protected path.
- Any change to an assertion. This item adds a way to select existing assertions and nothing else.

## Notes

- Write AC2 before AC1. If the fast path exists before the guard does, even for an afternoon, someone will use
  it for evidence and the habit starts.
- Make the refusal a refusal. A warning is a thing people learn to ignore, and this feature's whole risk is
  gradual erosion rather than a single wrong act.
- The banner should be impossible to lose in a scrollback: a reader of pasted output must be able to tell a
  partial run from a gate run without being told which command was used.
- NO UNBACKED UNIVERSAL: "cannot write the stamp", "cannot satisfy required-evidence" and "the only definition
  of done" each need the assertion that attempts and is refused.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
