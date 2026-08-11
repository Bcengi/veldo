---
schema: veldo.spec/v1
id: WARP-0728
title: The verdict projection keys the INDEX blob while the validator reads the WORKING TREE and nothing
  compares them, so a forged body committed under valid unstaged bytes is appended as a PASS at exit 0 -
  the keyed bytes and the validated bytes must be the same bytes
status: draft
risk: critical - this is the same guard WARP-0727 hardened, one axis down, and the route needs no flags, no
  attacker directory and no second repository: commit a forged verdict body over a tracked corpus path,
  leave the genuine bytes in the working tree unstaged, and the contract stage sees the genuine bytes while
  the projection keys the forged blob. Measured at 2f6cc25, `validate.py all` exits 0 printing nothing and
  plain `reconcile-verdicts` appends a `verdict.recorded` declaring `"verdict": "pass"` for a body no
  validator ever read. The log is append-only, so the permissive direction is unwithdrawable. The strict
  direction is WORSE than the defect: an author who edits an artifact after committing it, or a filesystem
  or filter that renders the working-tree bytes differently from the index, must not have a GENUINE verdict
  withheld, because a review log that silently stops recording is indistinguishable from a repository where
  nobody reviewed anything
owner: dmitry
human_approval: required
approval_record: >
  NOT YET GIVEN. This spec is DRAFT. It was written as a claim correction while closing WARP-0727, whose
  review 3 found this route and confirmed it behaves IDENTICALLY at ffaab41, bdb4055, 0ba2c4e and f6b27a4 -
  so it is PRE-EXISTING, outside WARP-0727's declared spelling-and-anchoring class, and not a regression of
  that item. It carries NO approval from WARP-0725 or WARP-0727: both of those are about WHICH PATHS are in
  the domain, and this one is about WHOSE BYTES a key names, which neither states. The owner must clear this
  spec before anything here is built or merged, and NO AGENT MAY PROMOTE IT.
lane: standalone
depends_on: []
# PLACEMENT AND FOOTPRINT DELIBERATELY NOT DECLARED YET, and this is not an oversight. The shape gate's
# footprint-versus-diff rule stands down when a change set names more than ONE footprinted spec, so
# declaring a footprint on this draft would have silently disarmed that rule on the very commit that
# introduces it - the same commit edits WARP-0727's spec, which does declare one. The contract also
# refuses a placement without a footprint, so both stand down together rather than one half being
# declared. BOTH ARE MANDATORY BEFORE THIS SPEC REACHES READY: run `python3 .veldo/validate.py ready
# <file>`, which refuses a placement that resolves to no contract area and a footprint that is not a
# non-empty list of globs, and the implementer declares them from the change actually intended. Expect
# placement [enforcement] and a footprint over the projection and the corpus owner plus their declared
# copies, but that is a prediction here and not a declaration.
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      THE KEYED BYTES ARE THE VALIDATED BYTES, ASSERTED PER ARTIFACT. For every corpus artifact the
      projection offers a key for, the bytes that key names and the bytes a validator read are the SAME
      OBJECT, and an artifact where they differ is REFUSED A KEY with the difference named, exactly as a
      staged path and a non-regular index mode are already refused one. THE SET is every path
      `committed_blobs` iterates in this repository's own corpus at the commit under test, and it is the
      WHOLE set by construction rather than by inspection, because it is the same enumeration
      `committed_blobs` already walks and the refusal lives inside that walk. WHAT WOULD REFUTE IT: a
      corpus artifact whose index blob differs from the identity of its working-tree file and which is
      still offered a key. The comparison is git's own answer about identity and never a hand-rolled read:
      it must not re-implement content hashing, line-ending or filter handling in Python.
  - id: AC2
    text: >
      THE MEASURED ROUTE IS REFUSED BY THE APPENDER, not merely reported after the fact. Driven exactly as
      measured at 2f6cc25: commit `{"schema": "nope", "verdict": "pass"}` over a tracked corpus path, then
      restore the genuine bytes in the WORKING TREE ONLY so the index equals HEAD (nothing staged) and the
      path is present on disk (nothing absent). TODAY: `validate.py all` exits 0 with ZERO output lines and
      plain `reconcile-verdicts` with no arguments appends one `verdict.recorded` declaring `"verdict":
      "pass"` and carrying verdict_blob 81fe14a7e5d150ec93346636727c0090b33c16a8, log md5 3ce08ca1f477 ->
      8937421a420a, whose bytes are the forgery while `git hash-object` of the working-tree file is
      2699a63397c6d420. AFTER: nothing is appended, the log is BYTE-UNCHANGED read back off disk, the path
      is NAMED with the reason, and the contract stage is RED. The refusal must be STRUCTURAL, in the
      projection's own key derivation, because `scripts/verify.sh` runs the reconciler AFTER the contract
      stage and does not gate the append on it: a red gate that still appends has closed nothing.
  - id: AC3
    text: >
      THE INVERSE HARM IS A REQUIRED LEG AND IT IS WORSE THAN THE DEFECT. Over this repository's real
      corpus every genuine verdict artifact must still reconcile, a second run must append nothing and
      report them already recorded, and the gate's review-events stage must still report zero
      derivable-but-not-appended. A property of EACH member is asserted and never a cardinality, because
      the corpus grows: it went 166 to 167 to 168 to 169 during WARP-0727 alone. Two ordinary states must
      be told apart from the forgery and must NOT withhold a genuine verdict without saying so per path
      with the reason: an author who edits an artifact after committing it (the working tree is ahead, the
      review on record is the committed one), and an environment where the working-tree bytes legitimately
      differ from the index (a clean or smudge filter, or CRLF renormalisation). If the mechanism cannot
      distinguish those, the item FAILS and the honest answer is to say so rather than widen it until the
      forgery returns.
required_evidence: [unit, baseline]
rollback: revert the commit. Nothing persists and no data migrates, but a forged line already appended to a
  log cannot be rolled back by anything, which is why this item exists.
---

## Intent

**WARP-0727 made the entitlement domain and the validated set one enumeration of PATHS. This item is the
same law about CONTENT.** After WARP-0727 the two sides cannot disagree about *which paths* are corpus
members, by spelling or by anchoring. They can still disagree about *whose bytes* those paths hold, because
they read different sources and nothing compares them:

- `validate.py` enumerates and reads the **working tree**, through `verdict_corpus.disk_corpus`.
- `events.verdict_blob_map` keys the **index** blob, through `verdict_corpus.committed_blobs`, and
  `events.verdict_event` reads every substantive field with `git cat-file blob <that blob>`.

So the `"verdict"` field an event records comes from bytes **no validator opened**, whenever the two
sources differ at a path that is neither staged nor absent.

## The measured route

Driven at `2f6cc25` in a scratch clone, and identically at `ffaab41`:

1. Commit `{"schema": "nope", "verdict": "pass"}` over a tracked corpus path. The index now equals HEAD, so
   the existing `staged, not committed` exclusion does not fire.
2. Restore the genuine bytes in the **working tree only**, unstaged. The path is on disk, so the existing
   `tracked but absent from the working tree` exclusion does not fire either.
3. `python3 .veldo/validate.py all` exits **0** with **zero output lines**: it read the genuine bytes.
4. `python3 .veldo/events.py reconcile-verdicts` appends **1** event, `"verdict": "pass"`, verdict_blob
   `81fe14a7e5d150ec93346636727c0090b33c16a8`, log md5 `3ce08ca1f477 -> 8937421a420a`. That blob holds the
   forgery. `git hash-object` of the working-tree file is `2699a63397c6d420`.

At `ffaab41` the same route gives exit 0, zero lines, 1 appended, log md5 `4b20b0fe19ec -> 01efc9b1adb9`.
The blob is the same in both columns because a blob sha is a property of content. **Pre-existing, not a
regression of WARP-0727, and outside its declared class.**

`committed_blobs`' own argument for its third exclusion, that **the bytes must be there to be keyed**,
proves only that the **path** is on disk. It never proved that the bytes keyed are the bytes read, and it
was corrected to say so while WARP-0727 closed.

## Candidate mechanisms, named and not chosen

Each was checked this round only to the extent of confirming it SEES the route; none is implemented and the
choice is the implementer's, subject to AC1's requirement that git decides identity.

- **Ask git which corpus paths differ between the working tree and the index.** `git diff --name-only -z --
  ':(top,literal)<prefix>proof'` (or `diff-files`) answers exactly that set, filter- and CRLF-aware because
  git applies its own rules. Measured on the fixture: it names the forged path, is EMPTY over an unmodified
  path, and costs 1 to 2 ms over the whole corpus. This is the same shape as the existing `_staged`
  exclusion, one axis over: that one compares the index with HEAD, this one compares the working tree with
  the index.
- **Compare `git hash-object --path <rel> -- <file>` against the index blob, per path.** Measured to return
  the working-tree object (`2699a63397c6d420`) against the index's `81fe14a7e5d150ec`. Filter-aware via
  `--path`, but it is one process per artifact, which the 500 ms standing budget makes worth measuring
  before choosing.
- **Key the bytes the validator actually read**, so a key cannot name bytes nobody validated. This changes
  what a key MEANS, from committed content to validated content, and the trade has to be stated rather than
  slipped in: a blob sha is reproducible in any clone of the commit, while a working-tree read is a property
  of one checkout, and the existing idempotence key and every already-recorded event depend on the former.

**Not acceptable:** timestamps, `git status` porcelain parsing, or re-implementing content hashing,
line-ending translation or filter application in Python. Those are new spellings of an identity rule git
already owns, which is the defect class WARP-0727 exists to close.

## Out of scope

- **The membership rule and the anchoring.** WARP-0727 owns those and nothing here widens or narrows them.
- **Entitlement keyed on the log's PATH SPELLING** rather than the identity of the file actually opened
  (`open(log, "a+")` follows the final component). Still known open, still a separate item.
- **A writer that never imports the module** (a shell append, a hand-edited log) and arbitrary in-process
  Python. That is the signed-log question.
- **Gating the reconciler's append on a green contract stage.** `verify.sh` runs the reconciler after the
  contract stage and does not condition it, which is why AC2 requires a STRUCTURAL refusal; changing the
  gate's staging is its own item.
- **What a verdict SAYS.** Schema and content validation of a verdict body is `validate.py`'s job. This item
  is only about the bytes a key names being the bytes something validated.

## Notes

- **One concern, three criteria.** The keyed bytes and the validated bytes are the same bytes. AC1 is the
  property, AC2 is the measured route it must refuse, AC3 is the inverse harm it must not cause.
- **What a human approving this vouches for:** that a corpus artifact whose committed bytes differ from the
  bytes on disk is refused a key with the difference named rather than keyed silently; that the refusal is
  in the projection and not only in a gate check; and that no genuine verdict is withheld without being
  named per path with its reason.
- **What the reviewer should scrutinise:** that the leg can FAIL, driven from a constructed witness rather
  than argued (the route above is the witness and it must red); that a mutation removing the comparison
  turns exactly that assertion red and not everything; that the two legitimate divergences in AC3 are
  driven and not reasoned about; and that the whole real corpus still reconciles with nothing withheld.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double hyphen).
