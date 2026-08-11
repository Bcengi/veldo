---
schema: veldo.spec/v1
id: WARP-0722
title: The review loop is invisible - derive its events from the verdicts that already exist,
  in code that already runs, and delete the instruction that asked a human to remember
status: ready
risk: high - and the tier is DERIVED rather than chosen. The ready gate raised it from the
  standard I first declared, because the footprint spans two contract areas, `enforcement`
  (scripts/verify.sh, which must call the reconciler for it to be unskippable) and `metrics`
  (.veldo/events.py, which owns the emitter). That crossing is real rather than an artifact of a
  loose footprint: an emitter nobody calls is the failure this item exists to fix, so the call
  site has to live in the stage that always runs. Recorded because WARP-0711 shipped with a risk
  sentence that misdescribed its own tier, and a floor that is asserted rather than explained is
  the same defect one layer down. THE SUBSTANTIVE RISKS: an emitter that writes on every gate run
  can grow the event log without bound, and because the log is APPEND-ONLY a reconciliation that
  appends a wrong key can never be withdrawn, only superseded. Both are addressed in AC2 rather
  than hoped away. CORRECTED DURING THE BUILD: this front matter first said it touches no
  protected path, which was FALSE - `scripts/verify.sh` and its template copy carry a high floor
  in `.veldo/policy.yaml`, and the stage has to go there, so the push needs a commit-bound
  approval naming both, as WARP-1102 recorded when it added the shape-gate stage. It touches no
  frozen core module. A revert returns the method to having no review observability, which is
  where it is today
owner: dmitry
human_approval: required
lane: standalone
placement: [metrics]
footprint:
  # The engine canon: an engine file changed in one place and not the other seven is drift the
  # pack gate refuses, so every copy of every touched engine file is declared here. The build
  # found the first draft of this list short by the canon copies and by capabilities.yaml, and
  # the shape gate refuses a diff outside the footprint, so the omission was mechanical rather
  # than a matter of taste.
  - .veldo/events.py
  - engine/.veldo/events.py
  - packs/*/.veldo/events.py
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - packs/*/scripts/verify.sh
  - packs/claude/skills/review/SKILL.md
  - packs/*/skills/review/SKILL.md
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-0722-review-events-derived-not-appended.md
  - specs/index.md
  # Round 6 declares the wrapper root of every pack as a PATH (`wrapper_dir`) in the pack
  # manifest, because the assertions that carry AC3's guarantees were deriving it from the
  # FIRST WORD of the manifest's English `wrapper` sentence. The manifest is not an engine
  # file and has no canon copies, so this is one path, not eight.
  - .veldo/packs.json
# scripts/verify.sh and engine/scripts/verify.sh are PROTECTED PATHS (.veldo/policy.yaml,
# floor high): this item adds a stage to the gate every adopting repository trusts, so the guard
# requires a commit-bound approval that names them before the push, exactly as WARP-1102 did when
# it added the shape-gate stage. The first draft of this front matter declared no protected path
# and no required approval while its footprint named verify.sh, which was false; the ready gate
# does not cross-check the two, and the falsity would have surfaced only at the push.
protected_paths:
  - scripts/verify.sh
  - engine/scripts/verify.sh
acceptance_criteria:
  - id: AC1
    text: >
      THE EVENTS ARE DERIVED BY CODE FROM ARTIFACTS THAT ALREADY EXIST, NEVER APPENDED BY
      WHOEVER REMEMBERS. CLAIMED: after a gate run, every verdict artifact in the repository
      has a corresponding `verdict.recorded` event in `.veldo/events.jsonl`, and the emitter is
      reached by the gate itself rather than by an instruction to an operator. OVER WHAT SET:
      every path matching `proof/*/verdict*.json` that is TRACKED IN GIT. THE SIZE OF THAT SET
      IS DELIBERATELY NOT WRITTEN HERE, in any round: it grows with the repository, so a figure
      in this sentence is a figure that goes stale, and round 3 failed because an assertion had
      the same number in it. HOW COMPLETENESS IS KNOWN:
      the set is enumerated from `git ls-files 'proof/*/verdict*.json'` at run time, the same
      mechanism the lint stage uses for its corpus, so the domain is derived rather than
      remembered and grows with the repository; a selftest asserts the reconciled event set
      EQUALS that enumeration rather than merely covering a sample, and asserts that WHAT THE
      EVENT RECORDS EQUALS WHAT THE REPOSITORY HAS COMMITTED - the verdict, the round, the
      commit it reviewed, and the review's own timestamp OVER THE PARTITION THE PROJECTION
      DECLARES - for every artifact in the enumeration, read back through a different git
      command than the one the projection uses.
      AMENDED IN ROUND 3, ON A MEASURED CONTRADICTION IN THIS VERY CLAUSE: round 2 asserted
      that the event's timestamp EQUALS the artifact's `reviewed_at` for every artifact, while
      the projection deliberately dates an artifact that declares none at RECONCILIATION and
      counts it. Both could not hold, and the artifact that broke the tie is the shape of the
      SHIPPED verdict example, which declares no `reviewed_at` and which every validator
      accepts: committing one turned the gate RED on a valid artifact and made the declared
      fallback unreachable. So the claim is now quantified over the partition - an artifact
      declaring a timestamp in this envelope's format has it carried verbatim AND dating the
      event, an artifact declaring none (or one in another legal ISO form) has the field
      DROPPED and the event dated at reconciliation, counted and reported - and BOTH branches
      are exercised by fixtures rather than one of them being forbidden.
      AMENDED IN ROUND 2, because the correspondence is to a REVIEW and not to a filename: two
      byte-identical verdict artifacts of one spec are one review recorded twice on disk and
      correspond to ONE event, the absorbed artifact being COUNTED and reported rather than
      left to be noticed (measured at 9a5f0b7: every artifact tracked there yielded a DISTINCT
      review, so nothing collapsed - a count is not written because it grows; a fixture
      exercises the case that does collapse). WHAT WOULD REFUTE IT: a tracked verdict file whose review has
      no event after a gate run, an event for a review the enumeration does not contain, or an
      event whose recorded result contradicts the committed artifact it names - which is
      exactly what round 1 shipped and an independent review measured. The type emitted is
      `verdict.recorded`, which `.veldo/validate.py` EVENT_TYPES already declares; a selftest
      asserts the emitted type is a member of that set, so this cannot invent a name the
      validator would reject.
  - id: AC2
    text: >
      IDEMPOTENT, BOUNDED, AND HONEST ABOUT WHAT IT CANNOT UNDO. CLAIMED: running the gate N
      times adds each REVIEW exactly once, and the one-time backfill of the verdicts that
      predate this item happens exactly once. OVER WHAT SET: the same enumeration as AC1, run
      repeatedly, and over five clone shapes of one commit. HOW COMPLETENESS IS KNOWN: each
      event carries a key of (type, spec id, THE ARTIFACT'S OWN BLOB SHA), which is
      content-addressed, so it is independent of file mtime, of the path the artifact sits at,
      and of how much history the clone has; the reconciler reads the existing log, skips keys
      already present, and a selftest runs the gate three times over a fixture repository and
      asserts the second and third runs append ZERO lines. AMENDED IN ROUND 2, ON A MEASURED
      REFUTATION OF THE FIRST KEY: (type, spec id, path, the sha of the commit that ADDED that
      path) identified a file's first appearance rather than a review, and an independent
      review broke it twice - an artifact amended in place, which is this repository's own
      convention across review rounds, kept publishing the superseded result; and
      `git clone --depth 1` of ONE commit derived a different key for every artifact, because
      an add-commit lookup in a grafted history attributes every path to the shallow tip. WHAT
      WOULD REFUTE IT: a duplicate key APPENDED BY A RECONCILIATION, a key that changes between
      two clones of the same commit AT ANY DEPTH, an amendment that appends no event or appends
      one on every run, a rename that appends a second event for a review already recorded, or
      a second run that grows the file. AMENDED IN ROUND 3: that first clause read "a duplicate
      key in the log", and the log this item ships with HOLDS ONE, reported on every run, so
      the criterion was refuted by its own evidence while being marked passed. The duplicate is
      RESIDUE from round 1's superseded key scheme, proven by provenance: both events carry no
      `verdict_blob`, so both were written under the path key that the content key collapses
      into one, and no reconciliation of the shipped code appends a duplicate - which is what
      the clause now says and what a fixture and six concurrent runs assert. DECLARED RATHER
      THAN CLAIMED AWAY: the log is append-only, so a wrong event cannot be withdrawn, only
      superseded - which is why the key is derived from the artifact's content rather than from
      a timestamp or from history, why an artifact that cannot be keyed durably (staged but not
      committed) and an earlier event this repository can no longer resolve are both NAMED and
      skipped rather than guessed at, why the ONE pre-existing duplicate is REPORTED on every
      run rather than explained away (and why a reader that tallies the log rather than the
      artifacts over-counts by it, permanently, which is an item against the metrics split),
      and why the backfill is asserted before it is trusted.
  - id: AC3
    text: >
      THE PROSE INSTRUCTION IS DELETED, NOT CORRECTED, AND THE INVENTED NAMES SURVIVE ONLY IN
      RECORDS THAT ARE ENUMERATED WITH THEIR REASONS. CLAIMED: `packs/claude/skills/review/SKILL.md`
      no longer asks anyone to append an event, no live instruction, engine module, skill or
      engine config carries either name, and every tracked file that still does is on a list
      that says why. OVER WHAT SET: every tracked file, searched for `review.passed` and
      `review.failed`. HOW COMPLETENESS IS KNOWN: a selftest reads EVERY tracked file and
      asserts the set containing either name EQUALS that enumerated record list, binding in
      BOTH directions, so a new occurrence anywhere turns the gate red and an entry that stops
      carrying a name must be removed from the list; and it asserts the fifteen live engine
      surfaces (seven copies of the review skill, eight of the capability manifest) carry
      neither. AMENDED IN ROUND 2: this criterion first asked for an EMPTY LIST, which the
      build measured to be unreachable and an independent review confirmed - a shipped proof
      manifest cannot be edited without moving the proof_digest its verdict carries, a shipped
      spec is kept by records policy, four design documents ARE the investigation that found
      the defect, and this criterion, its assertion, this item's evidence and the review that
      failed round 1 all have to name what they rule on. The letter was amended to the equality
      that is provably achievable rather than reinterpreted after the fact in a proof manifest.
      WHAT WOULD REFUTE IT: either name in any tracked file the list does not name, a list
      entry that no longer carries one, or the instruction being reworded rather than removed.
      WHY DELETION RATHER THAN CORRECTION: those names were never declared in EVENT_TYPES, so
      the instruction told its reader to emit an event the gate's own validator rejects. It
      shipped 2026-07-16 and was never executed, which is how it stayed wrong for ten days.
      Correcting the sentence would preserve the thing that failed; the emitter in AC1
      replaces it.
required_evidence: [unit]
rollback: >
  Revert the commits. The change adds a derivation function, a gate stage that calls it, a
  block of selftest assertions, and the deletion of two lines from a skill file. Reverting
  removes the emitter and restores the deleted instruction, returning the method to having no
  review observability and to carrying a rule that names two invalid event types. The events
  already appended cannot be un-appended, and that is deliberate: they are keyed on artifact
  CONTENT, so a re-application of this item reproduces exactly the same keys and appends
  nothing new. TWO READERS ALREADY CONSUME `verdict.recorded` and a revert leaves them reading
  a log that stops growing: `.veldo/metrics.py`, which sorts by `at` and whose tallies are
  order-free, and `.veldo/runstatus.py`, which slices its `recent verdicts` list by FILE
  POSITION and is therefore already wrong on a log that was never monotonic - a pre-existing
  defect in that module with its own item, which a revert neither causes nor cures.
---

## Intent

**The method cannot see its own review loop.** At the revision this item was written against,
a8b81b9, `.veldo/events.jsonl` holds 620 events (that figure is about a8b81b9 and about nothing
else) and every one is `gate.passed` or `gate.failed`,
emitted by `scripts/verify.sh:121-122` at that revision, which is a script. Every verdict artifact
tracked at a8b81b9 - and there were many - has no event at all. EVERY FIGURE IN THIS DOCUMENT IS
ANCHORED TO A NAMED REVISION OR IS NOT WRITTEN, which is a rule this item learned the hard way:
the reproducing commands, and what each number became, are in `proof/WARP-0722/manifest.json`,
each against the revision it was measured at.

That gap is why the design-review investigation on 2026-07-26 had to reconstruct every round
count by reading filenames, and why Dmitry's VEL-13 decision 3 ("wait for more evidence" on
mechanical item-size enforcement) currently has no evidence arriving to wait for. Rounds to
green against item size is the measurement that answers it, and it is not obtainable until the
loop emits.

**This item is the first work under VEL-13 decision 1, "if it matters, it is code, not prose,"
and it is that rule applied to its own precondition.** The reason those events do not exist is
that a skill file asked whoever ran a review to append them. Nobody ever did, across every
verdict the repository had accumulated by a8b81b9. So the fix is not a better instruction. It is
an emitter in the path the work already takes.

## Context

- **The instruction was also WRONG, which is the sharper half of the lesson.**
  `packs/claude/skills/review/SKILL.md:15-16` at a8b81b9 says to append `review.passed` or
  `review.failed`. Neither is in `.veldo/validate.py`'s `EVENT_TYPES`, which declares
  `verdict.recorded` and `review.requested`. Had anyone obeyed the instruction, the gate would
  have gone RED on an unrecognised type. It shipped 2026-07-16 and stayed wrong for ten days
  because nothing ever ran it. Prose is not merely unenforced; it is unchecked, so it can be
  wrong indefinitely and invisibly.
- **CORRECTED DURING THE BUILD, because it changes what AC3 can honestly claim.** This spec first
  said the two names "appear in that one file and nowhere else in the engine". MEASURED, they are
  in 22 tracked files at a8b81b9 (`git grep -l -e 'review\.passed' -e 'review\.failed' a8b81b9`):
  the skill in all SEVEN of its canon copies, `.veldo/capabilities.yaml` in all EIGHT, the method
  document `docs/setup.md`, four internal design documents, one shipped spec, and one shipped
  proof manifest. So AC3's literal "EMPTY LIST" is not reachable: a shipped proof manifest and a
  shipped spec are the record and rewriting them falsifies it, the design documents are the
  investigation that FOUND this defect, this spec's own AC3 names both strings, and the assertion
  that enumerates them has to name them too. What is reachable, and is what the build asserts, is
  an EQUALITY over the whole tracked corpus against an ENUMERATED list of records, each with its
  reason, holding that no live instruction, engine module, skill, or engine config is among them.
  `docs/setup.md` is the one live document left on that list and it is a real defect with its own
  item, not a record: it hand-lists NINE event types the shipped validator refuses, and correcting
  it re-renders a released PDF.
- Why DERIVE rather than emit at review time: an emitter that fires when a reviewer chooses to
  call it has the same failure mode as the instruction it replaces. The verdict FILE is the
  durable artifact, it is committed, and the gate runs over the repository on every build. So
  the event becomes a projection of the artifact, reconciled by code that cannot be skipped.
- **THE PROJECTION OWNS `verdict.recorded`, AND SIX ROUNDS GUARDED A DESCRIPTION OF THE EVENT
  INSTEAD OF THE EVENT. ROUND 7 READS THE TYPE OFF THE ASSEMBLED DICT, INSIDE THE ONE FUNCTION
  THAT WRITES THE BYTES.**
  The module said do not hand-emit it and nothing stopped anyone: the type is in `EVENT_TYPES`
  and `make_event` only checked membership, so `events.py emit verdict.recorded` exited 0. Two
  independent reviewers found it, and one demonstrated the consequence, which is why it is not
  cosmetic: the withheld set was built from the unresolvable events with NO producer
  distinction, so ONE hand-written unresolvable line naming a real spec id withheld EVERY
  future genuine review of that spec, on every run, in every clone, in a log nothing may
  rewrite, while `validate.py` still exited 0. Round 4 guarded `emit()` and the CLI. Round 5
  moved the check to `make_event` and split the builder in two, which left an UNGUARDED
  constructor beneath the guarded one: MEASURED at 19c396b, a second writer built through that
  private builder appended exactly the harmful line - unresolvable, declaring this projection's
  producer - and the suite stayed at 3236 passed 0 failed. Round 6 then moved the check onto
  `emit()` AND ONTO THE TYPE ARGUMENT PASSED TO IT, which is a name a caller supplies, so it
  was defeated by naming the type somewhere else on the way to the same append: MEASURED on
  the shipped tree at 298a820, `events.py emit spec.ready --field type=verdict.recorded
  --field 'producer=events.py reconcile-verdicts' --field verdict_path=proof/<id>/... --field
  spec_id=<id>` exits 0, lands the harmful line, passes `validate.py all`, and withholds every
  genuine verdict of that spec on runs 1, 2 and 3. `--field` merges LAST, after the argument
  round 6 checked. THE PATTERN, WHICH IS THE LESSON: each round guarded one WAY OF NAMING the
  type and the next attacker named it another way, and no assertion ever read back the type of
  a line that LANDED. So the refusal is now inside the single function that puts bytes in the
  log, reading `ev["type"]` off the FINAL dict after every merge, update, extra and CLI field;
  the vocabulary check moved onto the bytes for the same reason (`--field type=` could write a
  line no validator recognises into an append-only log, reddening `validate.py all` for good);
  the projection is entitled STRUCTURALLY, by its line's own content key being one this pass
  derived from a COMMITTED artifact, never by a string; and the assertion READS THE APPENDED
  LINES BACK and checks their types. The write surface is asserted as a SHAPE with no function
  name in it - exactly one scope writes to a handle, and the refusing scopes are that same
  scope - because round 6's version pinned two function names plus which held the open, which
  an extract-a-helper refactor reddens, and because it could not see a second in-module writer
  that opened nothing and delegated. A delegating writer now needs no visibility: it can only
  reach the log through the one writer, which reads the type off its dict.
  WHAT IS NOT CLAIMED: a caller that builds an envelope and appends it
  ITSELF is a writer outside this module and no check inside it can reach one. Those writers
  are enumerated by reading and asserted separately, `.veldo/request_reconcile.py` among them.
  The refusal ignores `--producer` because a string the caller supplies is not a credential.
- **DECLARED CHANGE OF BEHAVIOUR, ROUND 7: AN EVENT LOG IS THE PROJECTION OF ONE WORK TREE, SO
  A FOREIGN REPOSITORY'S ARTIFACTS CANNOT BE IMPORTED INTO IT.** MEASURED on the shipped tree
  at 298a820 with shipped flags only: `reconcile-verdicts --repo-root <a directory an attacker
  controls> --log <this repository's log>` derived `verdict.recorded` events from THAT
  directory's artifacts and appended them here, exit 0, `validate.py all` green, in a log
  nothing may rewrite. The reconciler now refuses a mismatch between the NEAREST enclosing
  repository of the log and of the artifacts, in both directions, so a repository created
  ABOVE this one cannot claim its log either; nothing is appended and the mismatch is REPORTED
  BY NAME with both work trees. THE ALTERNATIVE WAS REJECTED FOR A REASON RATHER THAN A
  PREFERENCE: keying the ORIGIN into the derived key does not stop the bytes, it makes the
  imported line unresolvable HERE, and an unresolvable `verdict.recorded` declaring this
  projection's producer is exactly the poison described above - it would import a permanent
  WITHHOLD in place of a forged pass.
- **DECLARED CHANGE OF BEHAVIOUR, ROUND 4, AND ITS LIMIT STATED HONESTLY IN ROUND 5: WHOSE
  unresolvable event withholds work.** An unresolvable `verdict.recorded` DECLARING this
  projection as its producer withholds that spec's appends, because it stands for a review of
  that spec the log already covers and the reconciler cannot tell which. One declaring any
  other producer is treated as covering no review, so it withholds NOTHING and is REPORTED BY
  NAME with the producer it declares. THAT FIELD IS AUTHOR-WRITTEN, so this is a classification
  of what a line SAYS about itself and not a credential check: round 4's spec text, module
  docstring and capability note all claimed a foreign line "never covered a review", which is
  asserted rather than established, and the same documents said the refusal ignores the producer
  string because the caller chooses it. Both cannot stand. What is true, and is now what they
  say: it is the only discriminator an append-only log offers for a line written before the
  content key existed, a hand-written line declaring this projection's producer does withhold
  that spec, and the refusal on the bytes above is why no route through this module can append
  one any more.
- **NO ASSERTION IN THIS ITEM MAY BE PINNED TO A MOVING REPOSITORY PROPERTY, and rounds 4 and 5
  both exist because some of them were.** A pin is not only a count. Round 3's was a substring
  test against the verdict count, which reddened the gate 40 artifacts from where it was written.
  Round 4 closed that and introduced three more spellings, each MEASURED false rather than
  argued: an assertion that the batch resolver, not its proven-equivalent fallback, is the route
  that served (stub the batch call and the suite reds while EVERY key resolves identically); a
  copy-set expectation derived from a listing of directories under `packs/` and compared against
  a glob of files that exist, which are two different repository properties on the two sides of
  one equality (one file at `packs/zzz/README.md` reddens five assertions); and an evidence rule
  admitting a record under `proof/` only if the FILE IS NAMED `verdict*.json` or `manifest.json`,
  a naming convention 114 files in the corpus already fail. Round 5 replaces all three with the
  property, the DECLARED pack roster in `.veldo/packs.json` read through its one reader, and the
  DECLARED spec roster. AND ROUND 5 THEN WROTE THE SAME DEFECT IN ITS NEXT SPELLING: it derived
  each pack's WRAPPER ROOT as `(p.get("wrapper") or "").split()[0]`, the first word of an English
  description sentence, so three assertions depended on a prose field's word order. A PROSE FIELD
  IS A MOVING PROPERTY. Round 6 declares `wrapper_dir` as a PATH in the same manifest and reads
  that, and every assertion whose coverage depends on it now also requires the field to be
  present for EVERY declared pack, so a dropped field is a red rather than a quiet narrowing.
  AND ROUND 6 THEN WROTE THE SAME DEFECT IN ITS NEXT SPELLING, WHICH IS THE FIFTH: its
  write-surface expectation was `{"emit", "reconcile_verdicts"}` plus a requirement about which
  of the two held the guard. A FUNCTION NAME IS A MOVING PROPERTY. MEASURED at 298a820, an
  ORDINARY EXTRACT-A-HELPER REFACTOR that moved the append one function down, behaviour
  identical, took the suite to 3235 passed 1 FAILED with that assertion the sole failure.
  Round 7 replaced it with a shape that still named the two REFUSALS and still counted scopes,
  AND ROUND 7 IS THEREFORE THE SIXTH SPELLING OF THE SAME DEFECT, MEASURED THREE WAYS AT
  6808e60. A PURE RENAME of the projection refusal in all eight copies, behaviour identical,
  raised `AttributeError: module 'veldo_events_0722' has no attribute
  'refuse_projection_owned'` and the suite printed NO PASS/FAIL SUMMARY AT ALL - a crash takes
  the gate's whole reporting down and is strictly worse than a red. Its write predicate counted
  ANY `.write` in the module rather than writes to THE LOG, so an unrelated `sys.stderr.write`
  added to now_iso gave exit 1 with that assertion the SOLE failure. And extract-a-helper was
  closed for one spelling only: pulling `open(LOG, "a")` into a helper is green, pulling the
  append loop into `_write_all(fh, events)` reddens it. Round 8 DISCOVERS BOTH SETS instead of
  writing either down - the write set by resolving what each byte emission TARGETS, the refusal
  set by what those functions DO - and requires a refusal on every path into every scope that
  puts bytes in the log. Twelve behaviour-preserving spellings are measured GREEN and four real
  defects RED, each in all eight copies, each listed at the assertion.
- **AND ROUND 8 WAS THE SEVENTH SPELLING, BECAUSE A MATRIX IS NOT A CLOSED CATEGORY.** Round 8
  claimed the category closed on twelve green spellings. TWELVE SPELLINGS ARE A MATRIX, NOT A
  CLOSED CATEGORY, and that sentence is deleted rather than softened: every one of the twelve was
  a RENAME or an EXTRACTION, not one round from 6 to 8 ever tested a PURELY ADDITIVE change, and
  the moving-property class is about the repository GROWING. Measured at 489bebb, both taking the
  whole suite's reporting down with a traceback and NO pass/fail summary at all: adding one UNUSED
  module global `AUDIT_LOG = ROOT / ".veldo" / "audit.jsonl"` beside `LOG` in all eight copies,
  nothing referencing it, behaviour identical, defeated round 8's own subject - it had pinned
  `len(the module's json-lines Path globals) == 1`, a CARDINALITY THIS REPOSITORY CAN ORDINARILY
  GROW, and the module's own docstring already mentions a second json-lines file; and a PURE
  RENAME of the contract constant `PROJECTION_OWNED` in all eight copies raised `AttributeError:
  module 'veldo_events_0722' has no attribute 'PROJECTION_OWNED'` out of a line round 8 itself
  added, inside the very leg whose headline claimed every lookup was guarded. So the pin has been
  a writer name, a refusal name and a count, one per round. ROUND 9 REMOVES THE CLASS RATHER THAN
  THE SPELLING: the log is discovered by DRIVING a copy of the module in a tree of its own and
  taking the globals its appended bytes were observed to follow, the property is required OF EACH
  such global and no cardinality is asserted anywhere in the leg, the four contract names this
  block must look up are read through guarded lookups so an absent one is a named RED, and every
  driven route including the allowed-type control records the exception it got instead of raising
  it. WHAT IS CLAIMED IS THE BATTERY THAT WAS RUN, not a closed category: thirty-eight whole-suite
  runs on the round-9 tree - twenty ADDITIVE or pure-rename controls (a second and a third
  json-lines global, each of the four contract constants renamed repo-wide, an unused function, an
  unused non-path constant, an unused class, a docstring added to a function that lacked one, an
  unused import, an extra optional parameter, a directory global, a committed file outside this
  item's footprint, a committed .py module under .veldo/, a new type in the declared vocabulary, two
  function definitions reordered, an identity decorator, a comment block inside the writer, an
  `__all__` list), twelve behaviour-preserving spellings re-measured from round 8, five DEFECT
  controls that must be red, and one unmutated control. Every figure is in the manifest check
  `additive_control_battery`, with its exit code, its pass/fail counts and whether anything
  crashed. WHAT THE BATTERY DID NOT CLOSE IS NAMED THERE TOO rather than left out: renaming
  `EVENT_TYPES` repo-wide still crashes the suite, in ANOTHER item's assertion block at
  scripts/selftest.py:2904 (`EVRL.EVENT_TYPES`), a pre-existing pin outside this item's footprint,
  measured identical at 489bebb and queued.
- For every literal that remains, the manifest answers what ordinary future
  change breaks it, and for every check the manifest states what shape of pin it is BLIND to.
- **Why the key is the artifact's own BLOB SHA, and why the first answer was wrong.** File mtime
  changes on checkout, so an mtime-keyed log diverges between clones of one commit; that much was
  right in round 1. What was wrong was the replacement. Round 1 keyed on the path plus the sha of
  the commit that ADDED it, and the sentence here read "the adding-commit sha is a property of
  history and is identical everywhere". IT IS NOT, AND THE REFUTATION IS ONE COMMAND:
  `git clone --depth 1` of one commit derives a different key for every artifact, because in a
  grafted history the add lookup attributes every path to the shallow tip - and `fetch-depth: 1`
  is the default of `actions/checkout`. It was also the wrong THING to identify: keyed on a path's
  first appearance, an artifact AMENDED IN PLACE keeps publishing the superseded result, which is
  not a hypothetical here, because this repository overwrites a verdict across review rounds and
  copies the earlier round out under its own name. A blob sha is a property of CONTENT: identical
  at every clone depth (measured, `git ls-files -s` is byte-identical between a full clone and a
  `--depth 1` clone of one commit), different when the review is different, and unmoved when the
  file is renamed. So the key identifies a REVIEW, the path is recorded but not keyed, and the
  derivation needs no history walk at all.
- **The event's `at` is AUTHOR-CONTROLLED and validated nowhere, which is a declared cost rather
  than an oversight.** `at` is the review's own `reviewed_at`, and nothing checks that field for
  format, for plausibility, or for agreement with the commit that added the artifact - the
  projection makes no history call at all, so it could not cross-check it cheaply even if it
  wanted to. Measured: `1970-01-01T00:00:00Z` and `2099-12-31T23:59:59Z` both pass
  `validate.py verdict` and `validate.py all` at exit 0 and land verbatim in an append-only log,
  and this repository's corpus carries a review whose reviewed_at (2026-07-28T09:30:00Z) ran AHEAD of the commit that recorded it
  (`proof/WARP-1210/verdict-9-fail.json`, `reviewed_at: 2026-07-28T09:30:00Z`). It is accepted
  because `at` is PAYLOAD and never part of the key, so no key, no count and no result can move:
  the worst a forged timestamp does is misorder a chronology. Every other substantive field (the
  verdict, the round, the reviewer, the reviewed commit) is equally author-chosen, and the guard
  for the one that matters most - the verdict vocabulary - sits on the ARTIFACT in
  `.veldo/validate.py`, which is where a `reviewed_at` rule belongs too. THE ARTIFACT-SIDE ITEM
  IS RECORDED AND NOT TAKEN HERE: requiring `reviewed_at` in this envelope's format in
  `VERDICT_REQ` would close both this and the fallback branch above, and it is a CONTRACT
  TIGHTENING that turns an adopter's gate RED on historical verdict records nobody may edit
  (measured in this repository at 528c98f: the gate goes RED on historical verdict records
  nobody may edit, in three other items' assertion blocks as well as in both shipped example
  copies; the count is not written here because it moves with every item that adds a block).
- `spec.ready` is the other half of the observability gap and is deliberately NOT in this item.
  It has a different trigger (a spec reaching ready, not an artifact appearing), and rounds to
  green needs only the review side. One concern per item.

## Out of scope

- No `spec.ready` emission, no `review.requested`, no new event type. This item emits exactly
  one already-declared type.
- No change to what the gate DECIDES. Reconciliation appends events; it never fails the gate on
  their absence, because a stage that reddens the build over its own bookkeeping would make the
  first run after this lands unlandable.
- No NEW consumer, and the claim that nothing reads these events is DELETED rather than
  qualified, because it was false when it was written: two readers already consume
  `verdict.recorded`, and this item's own headline benefit is measured by running one of them.
  `.veldo/metrics.py` is safe (it sorts by `at` where order matters and its tallies are
  order-free). `.veldo/runstatus.py` slices its `recent verdicts` list by FILE POSITION, which is
  wrong on a log that was never monotonic (measured at a8b81b9: 24 inverted transitions over its
  620 lines, before this
  item touched it) and is more visibly wrong now that the log carries reviews dated by their own
  timestamps - a PRE-EXISTING defect in a module this item does not touch, with its own item. The
  measurement that answers VEL-13 decision 3 is a separate item and is not smuggled in here.
- No mechanical item-size enforcement, per VEL-13 decision 3.
- `scripts/check_docs.sh`'s `DOCS_CHECK_PATHS` fail-open is a real defect in another stage and
  has its own item.

## Notes

- Write AC2's double-run assertion before the emitter works. The temptation is to build the
  happy path and add idempotence after, and idempotence is the item.
- The event log is APPEND-ONLY. A wrong key cannot be withdrawn, and round 1 proved that the
  hard way: it backfilled the whole corpus as it stood at 9b7a58a, and one of those lines
  asserts a result its own artifact contradicts, permanently. Assert the key against a fixture repository AND against FOUR CLONE
  SHAPES of one commit (full, `--depth 1`, `--filter=blob:none`, `--single-branch`) before
  appending anything to the real log, and prove what the projection records equals what the
  repository has committed rather than only that the key is stable.
- NO UNBACKED UNIVERSAL: "every verdict has an event", "appears nowhere" and "exactly once" each
  need the assertion that enumerates them. Measure first, then write the sentence.
- DO NOT PIN ANY ASSERTION TO A MOVING REPOSITORY PROPERTY, AND A PIN IS NOT ONLY A COUNT: a
  filename convention, a directory listing, a set of pack names, a FUNCTION NAME, and WHICH of
  two supported code
  routes ran are all pins. Not the verdict count, not the event count, not the number of packs,
  not the number of files carrying a string. All of them move. Derive the expectation from the
  owner's own constants or from a roster the repository DECLARES, and for every literal you do
  write, answer in the manifest what ordinary future change breaks it. THIS RULE WAS IN THIS FILE
  FROM ROUND 1 AND THE ITEM BROKE IT IN ROUNDS 2, 3, 4, 5 AND 6, because a rule in prose does not
  execute. Each round closed one spelling and introduced the next: a count, then a stringified
  count, then a filename convention and a directory listing and an environment property, then
  THE FIRST WORD OF A PROSE SENTENCE in the pack manifest, which round 6 replaced with a PATH the
  manifest declares, and then TWO FUNCTION NAMES in round 6's own write-surface expectation,
  which an ordinary extract-a-helper refactor reddens and which round 7 replaced with a shape
  that names nothing. Round 5
  re-ran round 4's own control (1000 verdict artifacts added inside existing proof directories)
  to prove the corpus-growth win was kept, and MEASURED each of the three new spellings failing
  before replacing it; round 7 re-ran that control and round 5's other two as well. A sweep whose
  lenses are the shapes it already knows will miss the next
  one, so every lens must also state what shape of pin it is BLIND to.
- AND A REFUSAL MUST BE ASSERTED ON THE THING REFUSED, NOT ON A DESCRIPTION OF IT. Six rounds of
  this item asserted the projection-type refusal over a type PASSED POSITIONALLY, a return code,
  or a raised message, and NO LEG EVER READ BACK THE TYPE OF A LINE THAT LANDED - which is why a
  guard on an argument satisfied every assertion while `--field type=` put the forbidden name on
  the bytes. Read the log, parse it, and check the field.
- RULE #1: ASCII hyphen only, no em dash, no en dash, no prose double hyphen.
