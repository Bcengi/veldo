---
schema: veldo.spec/v1
id: WARP-1711
title: History-dependent proofs in a flattened repository - the three assertions and one reconciler
  that resolve their input from git, why a single-commit successor cannot supply it, and the stand-down
  that says so instead of passing quietly
status: ready
risk: standard - it changes only test-harness control flow and one reporting line, ships no product
  behaviour, and a repository with history is byte-identically unaffected. It is not low because the
  thing being weakened is a PROOF: three of these assertions exist specifically to avoid trusting a
  pinned digest, and a stand-down written carelessly converts "we could not check this" into a green
  check, which is the exact defect this project has shipped twice and hunts for by name
owner: dmitry
human_approval: not_required
lane: standalone
placement: [enforcement]
footprint:
  - "scripts/suites/shared.py"
  - "scripts/suites/12_warp_1210_hardening_four.py"
  - "scripts/suites/13_warp_0623_codified_live.py"
  - "scripts/suites/15_warp_1409_cost_to_change_per_area.py"
  - ".veldo/events.py"
  - "engine/.veldo/events.py"
  - "specs/WARP-1711-history-dependent-proofs-in-a-flattened-repository.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    Every stand-down prints one line naming WHICH input was unavailable, WHY it is unavailable (a
    single-commit repository), WHICH weaker leg still proves the criterion here, and WHERE the strong
    leg was proven (the frozen predecessor). Silence is not an acceptable stand-down: a reader of the
    gate output must be able to tell a criterion that was checked from one that stood down without
    reading the suite source.
  metrics: >
    The review-event reconciler already counts what it cannot resolve and how many appends it
    withheld. That count becomes the measure of the transitional gap and is expected to fall to zero
    as the successor accumulates commits, so the number is a progress signal rather than noise.
  error_taxonomy: >
    One condition, tested one way: the repository reports a commit depth of exactly 1 AND the
    pre-change revision did not resolve. Any other combination is a broken search and stays a hard
    failure, because a repository WITH history that cannot find its own past is a defect, not a
    migration artifact.
acceptance_criteria:
  - id: AC1
    text: >
      THE STAND-DOWN IS GATED ON HISTORY GENUINELY BEING ABSENT, AND THE NEGATIVE CONTROL IS THE
      EVIDENCE. Each stand-down fires only when `git rev-list --count HEAD` is exactly 1 and the
      pre-change revision did not resolve. A repository with history whose revision lookup fails still
      fails loudly. Proven both ways: the suite runs green in a repository WITH history and the
      from-git assertions genuinely execute there (asserted by the pre-change source differing from
      today's), and runs green in a single-commit clone where each stand-down line appears in the
      output. A stand-down that cannot be shown to NOT fire is not accepted.
  - id: AC2
    text: >
      THE COMPOUND ASSERTIONS ARE SPLIT RATHER THAN SKIPPED, which is the substance of this item. Two
      of the three assertions mix legs about the CURRENT module with legs about the pre-change module
      in a single boolean. Skipping the whole assertion would silently drop the current-module legs,
      which need no history and must keep running everywhere. Each is split so that every leg not
      requiring a pre-change revision still executes in a flattened repository, and only the
      historical leg stands down. Proven by counting executed assertions in both repositories: the
      flattened run loses exactly the historical legs and no others, enumerated by name in the spec's
      proof rather than asserted as a total.
  - id: AC3
    text: >
      THE REVIEW-EVENT RECONCILER REPORTS THE TRANSITIONAL GAP AS A GAP AND NOT AS A FAILURE OR A
      SUCCESS. Verdict artifacts whose recorded events reference commits absent from this repository
      are reported with their count and named cause (the history was flattened at migration), the
      appends stay WITHHELD rather than being fabricated against the new commit, and the stage does
      not turn the gate red for this cause alone. Fabricating the missing events by re-pointing them
      at the flattening commit is explicitly refused: it would assert that a review happened at a
      commit where it did not.
  - id: AC4
    text: >
      A FLATTENED CLONE OF THIS REPOSITORY PASSES ITS OWN GATE END TO END. The proof is a real run:
      produce the tree with `scripts/migrate_to_veldo.py`, initialise it as a single-commit
      repository, run `bash scripts/verify.sh` inside it, and record GREEN with the stand-down lines
      quoted verbatim in the proof bundle. This is the criterion the whole item exists for, because
      the successor cannot land its first change through the normal path while its own gate is red.
---

# History-dependent proofs in a flattened repository

Three assertions in `scripts/suites/12_warp_1210_hardening_four.py` resolve the PRE-CHANGE revision
of a module from git and compare its output byte for byte against today's. They were written that way
on purpose. The assertion text says so: proven against history rather than by a pinned digest inside a
branch that does not fire. A digest pinned in the same branch it defends is not evidence, because
whoever changes the behaviour changes the pin in the same commit.

The successor repository holds one commit. There is no pre-change revision to resolve, so the input
these assertions need does not exist. One of the three has already been handled and is the model for
the other two: it stands down with a line naming what stood down, states that the pinned-bytes leg
still proves the same criterion over the same stream, and points at the frozen predecessor where the
historical leg was proven. Its negative control is recorded: the same suite still passes all 252
assertions in this repository, so the stand-down does not swallow the check where history exists.

The two that remain are harder for one specific reason, and it is the reason this is a spec rather
than an edit. Both mix legs about the current module with legs about the pre-change module inside a
single boolean. One asserts that the pre-change dashboard's render is a byte-exact prefix of the new
one AND that the support section lands before the footer AND that a repository with no incident events
reads honestly. Only the first leg needs history. Guarding the whole assertion would quietly stop
checking the other two in every flattened repository, which trades a known gap for an unknown one.

The fourth instance is not an assertion at all. The review-event reconciler resolves verdicts through
events keyed to commits, and in the flattened tree it reports 154 events it cannot resolve and 153
appends withheld, against 170 already recorded in this repository. Every verdict file is present; the
commits they were recorded against are not. The honest report is the one it already gives, and what
this item adds is the named cause and the guarantee that the stage does not redden the gate for this
cause alone.

## What the measurement added to this list

The four instances above are the ones this spec was written from, and they are not the whole set. A
flattened clone was produced and its gate was RUN, which is the only way to know: with the four
closed, `bash scripts/verify.sh` in the successor was still RED on FIFTEEN more legs of the same
class, in two suites this spec had not named.

  - `scripts/suites/13_warp_0623_codified_live.py`, WARP-0711: twelve legs resolve the PER-FILE LINT
    LOOP, or the revision that read the fail-open switch, from this repository's own history and run
    it beside the shipped stage. Ten of the twelve mix legs about the SHIPPED stage with legs about
    the older text, so each is split the same way: what the stage on disk does keeps running
    everywhere, and only the comparison against the older revision stands down. One split is a
    strengthening rather than a substitution: the file-set equality that mattered ("a lint stage that
    quietly checks fewer files is the cheapest possible fake speedup") is now also asserted against
    the two `git ls-files` patterns run live, in both directions, which needs no history at all.
  - the same suite, WARP-0722: two legs assert the projection is COMPLETE over earlier reviews and
    that nothing in the log is unresolvable. Neither can hold where the commits those events name are
    absent, and the projection's answer is the WITHHOLD this item's AC3 is about, so those two stand
    down with that cause named while the domain, the derivable count, the dry run's inertness and
    the blob-existence check keep running.
  - `scripts/suites/15_warp_1409_cost_to_change_per_area.py`, WARP-1409 AC8: the git reader's control
    is a PAIR, and only its NON-EMPTY half needs a commit that names a real spec id. The absent half
    keeps running.

One more change is not a stand-down at all and is recorded because it is a consequence of the
reconciler edit: `.veldo/events.py` gained `is_flattened`, and the literal-scope guard over that
module's own code required its new integer scope to be DECLARED in the suite's table, with the reason
travelling beside it. That guard doing its job is the mechanism working as intended.

The stand-down itself lives in ONE place, `scripts/suites/shared.py`, because three suites need it
and a second copy of this decision is a second thing to get wrong. Every from-git leg registers
itself there whether it stands down or not, which is what makes the negative control mechanical
rather than a claim: suite 12 asserts that with history NOTHING stood down, every leg resolved a
revision and every resolved revision's source DIFFERS from the file on disk today, and that in a
single-commit repository the set that stood down EQUALS the set that exists.

None of this is a product defect. The shipped code in the successor is byte-identical to the code
proven here. What cannot travel is the ability to re-derive a past state from a history that was
deliberately dropped, and the cost of dropping it is exactly this: four places where the strongest
available form of a proof degrades to the second strongest, each one saying so out loud.
