---
schema: veldo.spec/v1
id: WARP-0727
title: An ordinary gate run appends a forged verdict with no flags, because the entitlement domain and the
  validated set are computed by two mechanisms whose globs disagree - derive both from ONE enumeration and
  assert their equality in both directions over the real corpus
status: shipped
risk: critical - this is the guard that decides whether an agent can mark its own homework, and the route
  measured here needs no flags, no attacker directory and no second repository: a verdict-shaped file
  committed one directory deeper than the corpus shape is inside the entitlement domain and invisible to the
  contract validator, so `validate.py all` exits 0 and the very next stage of the same gate run appends a
  forged PASS for it. The danger in the permissive direction is live and unwithdrawable, because the log is
  append-only. The danger in the strict direction is WORSE than the defect: a rule drawn too tight stops the
  projection recording GENUINE verdicts, and a review log that silently stops recording is indistinguishable
  from a repository where nobody reviewed anything
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-07-30
approval_record: >
  GIVEN ON TELEGRAM, 2026-07-30 10:08 UTC, message 21851, verbatim: "Clear 0727".
  RECORDED, NOT PERFORMED. The agent writes down the decision the owner made and never makes one for him.
  THE APPROVAL IS INFORMED. Before clearing it he was told, unprompted: that this guard took THREE attempts;
  that attempt 1 CLOSED one forgery route and OPENED another, which review 1 caught; that attempt 2 shipped a
  check that was arithmetically INCAPABLE of failing, which is worse than no check because it reads as
  protection, and review 2 caught that; that attempt 3 fixed both and was refused until it proved the check
  could fail; and that a SEPARATE, PRE-EXISTING route remains open, where the validator reads working-tree
  bytes while the appender keys the index blob and nothing compares them. That last one is WARP-0728 and is
  NOT closed by this item.
  Noted for a later reader: this is a Telegram instruction rather than a ticket transition, weaker evidence
  than the VEL-9 precedent on WARP-0712, and accepted because the owner asked for a single word rather than
  ceremony. Three independent reviews are on the record at proof/WARP-0727/verdict-review1.json,
  verdict-review2.json and verdict-review3.json; the first two are FAIL and the third is pass_with_notes.
lane: standalone
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/verdict_corpus.py"
  - ".veldo/events.py"
  - ".veldo/validate.py"
  - ".veldo/validate_checks.py"
  - ".veldo/policy_check.py"
  - ".veldo/intent_corpus.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/*.py"
  - "engine/.veldo/*.py"
  - "scripts/check_template_sync.sh"
  # The push guard's proof-manifest lookup was a FOURTH implementation of the corpus, in shell.
  # Round 2 routes it through the one owner, so the guard and all of its declared copies are in
  # this item's footprint.
  - "scripts/veldo-guard.sh"
  - "packs/*/scripts/veldo-guard.sh"
  - "packs/claude/scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - "scripts/suites/13_warp_0623_codified_live.py"
  - "specs/WARP-0727-one-enumeration-for-the-domain-and-the-validated-set.md"
  # The claim correction that closes this item declares an undeclared limit of the same class one
  # axis down and writes the DRAFT spec for it. Declared here rather than left to redden the
  # footprint check, and declared on THIS spec rather than as a footprint of its own: the shape
  # gate's footprint-versus-diff rule stands down when a change set names more than one footprinted
  # spec, so giving the new draft a footprint would have disarmed the rule on this very commit.
  - "specs/WARP-0728-keyed-bytes-are-the-validated-bytes.md"
  - "specs/index.md"
  # The gate's own records, written by scripts/verify.sh on every run: the review-events
  # projection appends to the log and the run status is rewritten, so any commit taken after a
  # gate run carries them. Declared rather than left to redden the footprint check.
  - ".veldo/events.jsonl"
  - ".veldo/last_verify"
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      THE ENTITLEMENT DOMAIN AND THE VALIDATED SET COME FROM ONE ENUMERATION. There is exactly ONE rule
      deciding what a proof-corpus path is, owned by one module, and it is applied to exactly TWO path
      sources - the git index and the working tree - NEITHER OF WHICH USES A WILDCARD: the git side names a
      DIRECTORY, so no pathspec glob semantics are involved at all, and the disk side walks that directory.
      The projection derives its domain through that module and the contract validator enumerates its corpus
      through the SAME module. A selftest asserts the module's pathspec carries no `*` in either form, that
      the enumeration call appears in the corpus owner's CODE and no longer in the projection's, and that
      the projection's domain equals an INDEPENDENT recomputation written in the suite itself. Patching one
      glob to match the other is explicitly NOT this criterion: two patterns kept in step by hand is the
      defect, and the next spelling difference reopens it.
  - id: AC2
    text: >
      THE MEASURED FORGERY IS REFUSED BY THE APPENDER ITSELF, not merely reported after the fact. MEASURED
      at ffaab41 with no change: commit `{"schema": "nope", "verdict": "pass"}` at
      `proof/WARP-9999/nested/verdict.json`; `git ls-files 'proof/*/verdict*.json'` MATCHES it because a git
      pathspec `*` crosses `/`, while `Path('proof').glob('*/verdict*.json')` does NOT; `python3
      .veldo/validate.py all` exits 0; then plain `python3 .veldo/events.py reconcile-verdicts` with NO
      ARGUMENTS appends a `verdict.recorded` carrying a real 40-hex blob, log md5 4b20b0fe19ec ->
      d262da987e54, reporting `1 appended`, and `bash scripts/verify.sh` prints GATE: GREEN over it. The
      refusal must be STRUCTURAL rather than a gate check, because verify.sh runs the reconciler AFTER the
      contract stage and does not skip it when that stage is red: a red gate that still appends has not
      closed anything. A selftest requires the artifact to be absent from the domain, nothing appended, the
      log BYTE-UNCHANGED read back from disk, the path NAMED on the stage line, and the contract stage RED.
  - id: AC3
    text: >
      THE ROUTE BATTERY IS GENERATED FROM THE MECHANISM'S OWN VOCABULARY, AND ITS COVERAGE IS STATED
      HONESTLY. The routes are a CROSS PRODUCT over the dimensions on which git and pathlib are documented
      to differ - depth, leading-dot components, name case, and directory spellings including a space, a
      glob metacharacter and both unicode normal forms - not a list of cases somebody thought of. For every
      generated path the two sets must AGREE: entitled if and only if validated. The measurement must state
      plainly that it is exhaustive over that product and NOT over all paths, and name what it excludes.
      Measured at ffaab41 over 540 generated points: 144 forgery routes (entitled, never validated) and 18
      inverse routes (validated, never entitled, caused by git quoting a non-ASCII path so a genuine review
      under such a directory could never be recorded). Both must be zero.
  - id: AC4
    text: >
      THE INVERSE HARM IS A REQUIRED LEG AND IT IS WORSE THAN THE DEFECT. Over this repository's real
      corpus, EVERY genuine verdict artifact must still reconcile, a second run must append nothing and
      report them already recorded, and the gate's review-events stage must still report zero
      derivable-but-not-appended. A property of EACH member is asserted and never a cardinality, because the
      corpus grows. In the other direction the gate must be RED, per path with the reason named, on an
      artifact that is entitled and not validated, and on one that git reports as tracked yet the
      enumeration does not hold; a verdict-shaped file at a path the rule does not admit must be NAMED
      rather than silently dropped. If the rule withholds even one genuine verdict the item FAILS and the
      honest answer is to say so rather than widen it until the forgery returns.
required_evidence: [unit, baseline]
rollback: revert the commit. Nothing persists and no data migrates, but note that any forged line already
  appended to a log cannot be rolled back by anything, which is why this item exists.
---

## Intent

**When two mechanisms compute what is claimed to be the same set, the gap between them is an attack surface
and neither mechanism can see it.** Each side is individually correct and individually tested; the defect
lives only in the difference, so no test of either side can find it.

`.veldo/events.py` derived the projection's entitlement domain with the git pathspec
`proof/*/verdict*.json`. `.veldo/validate.py` enumerated the corpus it validates with the pathlib glob
`Path('proof').glob('*/verdict*.json')`. **A git pathspec `*` crosses `/`. A pathlib `*` does not.** So an
artifact one directory deeper was simultaneously INSIDE the entitlement domain and INVISIBLE to the contract
validator, and the gate itself appended the forgery.

## Why not just fix the glob

Making the pathlib glob recursive closes ONE spelling of the difference. `*`, `**`, case folding, symlink
following, unicode normalisation, path quoting and dotfile handling all differ between git, pathlib, shell
and regex, and each is a new spelling of the same defect. Six of nineteen hand-enumerated candidate paths
were forgery routes at `ffaab41`, and a generated cross product found 144. **Two patterns kept in step by
hand is the defect.** One rule, two sources, no wildcard.

## What this item does NOT close

- **The one enumeration is an enumeration of PATHS, not of CONTENT.** Both sides now agree about which
  paths are corpus members. **Nothing compares their bytes:** `validate.py` reads the WORKING TREE,
  `committed_blobs` keys the INDEX blob, and no check asks whether they are the same object. Driven at
  `2f6cc25`: commit a forged `{"schema": "nope", "verdict": "pass"}` over a tracked corpus path and leave
  the genuine bytes unstaged in the working tree, so the index equals HEAD and the path is on disk and
  neither exclusion fires; `validate.py all` exits 0 with zero output and plain `reconcile-verdicts`
  appends `"verdict": "pass"` carrying a blob whose bytes are the forgery. Identical at `ffaab41`, so
  **pre-existing and outside this item's declared spelling-and-anchoring class. KNOWN OPEN, specified as
  WARP-0728 (draft).**
- **Entitlement is keyed on the log's PATH SPELLING, not on the identity of the file actually opened.**
  `log_entitlement` resolves a repository from `Path(log).parent` while the bytes are written by
  `open(log, "a+")`, which follows the final component, so symlinking or hardlinking an attacker's log at
  the victim's name transfers entitlement. **KNOWN OPEN. A separate item.** Nothing here touches it, and
  nobody should read this item as closing the whole forgery.
- A writer that never imports the module (a shell append, a hand-edited log) and arbitrary in-process
  Python. Both can already append directly; that is the signed-log question.
- A process environment that redirects what git ANSWERS: `GIT_DIR` and `GIT_WORK_TREE` pointed at an
  attacker's repository make that repository's enumeration the domain. Declared, not defended against.

## Relationship to WARP-0725

WARP-0725 is `ready`, `critical`, owner-approved, and its AC1 states entitlement as membership in the domain
of the repository **fixed by the LOG's path**. That is a different question from **which enumeration computes
that domain**, and its AC1's phrasing is the stand-in this item replaces. This spec carries a subset of
WARP-0725's approved intent, narrowed to one concern, and **it is DRAFT: the owner must clear it before
merge.** WARP-0725's approval fields are untouched.
