---
schema: veldo.spec/v1
id: VELDO-0010
title: Evidence names the version that produced it - an optional proof-bundle field, a reader that
  reports the bundles predating it as UNVERSIONED rather than inferring today's, and a gate that
  stamps the producing version under a recorded approval
status: ready
risk: standard - it adds one OPTIONAL field to the proof-bundle contract and a reader over it, and
  refuses nothing that passes today. It is NOT low because it touches the artifact that records whether
  a criterion was met, and a required field here would have reddened every one of the 143 bundles that
  existed unversioned on the day it landed. It is not high because the field is optional by
  construction, the reader gates nothing, and the one gate-output line it adds landed under Dmitry's
  recorded approval of 2026-08-12 rather than being written first and asked about afterwards
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W9
placement: [contracts]
footprint:
  # THE APPROVED GATE EDIT. Dmitry approved the version stamp on 2026-08-12; it lands in BOTH gates
  # because an adopter's gate output should name its version too, and both are protected paths.
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  # DECLARED BECAUSE THE GATE EDIT CAUSED IT: run_scope declares the stamp's key set and a shipped
  # assertion parses verify.sh's own printf to require the two match, so adding the field to the gate
  # reddened that check until the payload carried it too. The coupling worked exactly as designed.
  - "scripts/run_scope.py"
  - ".veldo/version.py"
  - "engine/.veldo/version.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  # DECLARED BECAUSE THIS ITEM PRODUCED IT: driving AC5 found that the report-until-approved posture
  # has its own vacuous shape, recorded as ledger finding 45 so VELDO-0007's identical criterion gets
  # the same treatment when its approval lands.
  - "plans/PLAN-0018-what-a-complex-project-needs.md"
  - "scripts/suites/27_veldo_0010_evidence_provenance.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0010-evidence-names-the-version-that-produced-it.md"
  - "specs/index.md"
protected_paths:
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
behavior_bearing: true
observability:
  logs: >
    The reader reports how many proof directories exist and how many carry a manifest, how many name
    their producing version, how many predate the field, and how many are malformed - and it says in
    words that nothing infers a version for the ones that predate it. A malformed field names the
    bundle and what was wrong with it. A proof directory holding no manifest at all is NAMED rather
    than counted, so the coverage figure has no silent hole.
  error_taxonomy: >
    UNVERSIONED (the bundle predates the field: not an error, and never inferred) and a malformed
    field (present but not version-shaped, or a manifest that parses as JSON without being an object,
    named with the bundle). The distinction is the item: an absent field is the state most of this
    corpus is legitimately in, and a present-but-broken one is somebody's mistake. NO INPUT MAKES THE
    READER RAISE, because it is called at a suite's module level and a raise there shortens the run
    instead of reddening a row.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Add the version field to PROOF_REQ in .veldo/validate.py so a bundle without it is refused, and
      the assertion that this repository's existing bundles all validate unchanged must go red.
    text: >
      THE FIELD IS OPTIONAL BY CONSTRUCTION, AND THE MIGRATION IS THE ITEM. MEASURED on the day it
      landed, 2026-08-12: 143 proof bundles existed in this repository and NONE carried a producing
      version. Requiring the field would have reddened a working repository that day, which is how a
      correct rule gets reverted - the lesson VELDO-0001 wrote down and this item obeys. So the field
      is absent from PROOF_REQ, every existing bundle validates unchanged, and the reader REPORTS the
      split it finds rather than a remembered one: the assertion carries a lower bound on the corpus
      and prints the live counts, because a row pinning 143 would redden the next time anybody records
      a proof.
  - id: AC2
    falsified_by: >
      Make the reader fall back to the tree's current version for a bundle with no field in
      .veldo/version.py, and BOTH the fixture assertion that a bundle without the field is UNVERSIONED
      and the real-corpus assertion that every attributed version is read back out of the bundle's own
      file must go red.
    text: >
      NOTHING IS INFERRED FOR A BUNDLE THAT DOES NOT SAY. Reporting today's version for evidence
      written by an older one would state exactly the fact this field exists to establish, and it is
      the confident zero in its most damaging form: evidence produced when the checks were weaker
      would become indistinguishable from evidence produced now. An absent field is UNVERSIONED, it
      appears under no version, and the report says in words that nothing was inferred. OVER THE REAL
      CORPUS THE ATTRIBUTION IS READ BACK FROM DISK, in both directions: every version the reader
      files a bundle under is compared with the field in that bundle's own manifest, and every bundle
      it calls UNVERSIONED is confirmed to declare nothing. The reader's own buckets are not evidence
      that the reader did not infer - review measured the first version of this row asking whether a
      bundle sat in two buckets at once, which the reader's control flow already guarantees, so it
      stayed green under the inference mutation.
  - id: AC3
    falsified_by: >
      Accept any string as a version in .veldo/version.py, and the assertion that a bundle declaring
      the field as "latest" is reported MALFORMED with the bundle named must go red.
    text: >
      A PRESENT FIELD IS CHECKED FOR SHAPE AND NEVER FOR EQUALITY. Shape, because "latest" or an empty
      string is somebody's mistake and naming it is how they fix it. NEVER equality with the tree's
      current version, because a bundle produced by an older version legitimately carries an older
      version and that is the entire purpose of recording it - a check demanding agreement would make
      the field useless the first time it was true. EVERY UNREADABLE MANIFEST IS MALFORMED AND NONE OF
      THEM RAISES, including one that parses as JSON without being an object: review drove a list-bodied
      manifest through the reader and got an AttributeError that aborted the whole selftest with a
      traceback instead of reddening a row. NEGATIVE CONTROL: a version-shaped value is accepted and
      appears under its own version.
  - id: AC4
    falsified_by: >
      Drop the unversioned count from the report in .veldo/version.py, and the assertion that the
      counts PARTITION the bundles exactly - versioned plus unversioned plus malformed equals the
      bundle total - must go red.
    text: >
      THE COUNTS PARTITION THE BUNDLES EXACTLY, so a reader can tell how much of the evidence corpus
      the answer covers. Versioned plus unversioned plus malformed equals the manifests found, and the
      manifests found plus the directories NAMED as carrying none equals the directories present, both
      asserted over this repository's real corpus. The second half is there because review measured
      the hole in the first: the reader globbed proof/*/manifest.json and called the total "bundle(s)",
      so four proof directories holding no manifest sat outside every bucket unnamed. A report that
      quoted only the versioned count, or a denominator that quietly dropped what it could not read,
      would be a coverage figure without the weakness that produced it - the shape this plan's ledger
      keeps recording.
  - id: AC5
    falsified_by: >
      Remove the version field from the record the gate stamps in scripts/verify.sh, or leave a bare
      mention of a producing version without writing the key, and the assertions that the gate stamps
      it and that mentioning equals stamping must go red. Or restore the version derivation to
      `python3 .veldo/version.py | awk '{print $1}'`, and the assertion that the value is NULL rather
      than a guessed string must go red.
    text: >
      THE GATE STAMPS THE PRODUCING VERSION, IN BOTH GATES. Dmitry approved the protected-path edit on
      2026-08-12, so .veldo/last_verify now carries the version beside the commit and the status, and
      the shipped template does too because an adopter's gate output should name its version as well.
      THE VALUE IS NULL RATHER THAN A GUESSED STRING when the version cannot be read: a gate record is
      exactly where an invented version would be believed.
      EVERY ONE OF THOSE FACTS IS MEASURED BY RUNNING THE GATE AND PARSING THE RECORD IT WROTE, never
      by scanning the gate's source. Both gates are protected paths, so this criterion cannot be met by
      editing them - it is met by executing them: each is copied into a throwaway tree beside
      .veldo/version.py and run, once with a canonical declaration present and once without, and the
      .veldo/last_verify it produced is parsed. That replaces two substring scans that review refuted
      by satisfying both with a single comment naming the key while the record carried no field at all,
      and it is what makes MENTIONING versus STAMPING two independent facts rather than two reads of
      one string. NEGATIVE CONTROL: the same gates, run in a tree that DOES declare a version, stamp
      that version, so the null is a measurement rather than the only value they can write.
      THE CRITERION IS UNCONDITIONAL AND ITS REPORTING BRANCH IS GONE, which driving forced twice -
      first because a single posture flag let a bare marker pass, then because a posture derived from
      the live gate satisfied both branches when the stamp was removed entirely. A posture cannot catch
      its own removal.
required_evidence: [unit]
rollback: >
  Delete the provenance reader from .veldo/version.py and its suite fragment. No bundle changes, no
  contract field is removed because none was required, and every existing bundle stays valid, so the
  retreat costs one function and loses nothing already recorded.
---

# Evidence names the version that produced it

## The measurement that shapes the whole item

On the day this item landed, 2026-08-12, 143 proof bundles existed in this repository and **none of
them carried the version that produced it.**

That is why the field is optional and why nothing infers a value. Requiring it would have reddened a
working repository that day, and inferring today's version for older evidence would state exactly the
fact the field exists to establish: evidence written when the checks were weaker would become
indistinguishable from evidence written now.

So the honest shape is the one VELDO-0001 established: add the field, report the migration, and let
the flip to requiring it be a separate act with its own count. The measurement above is written here
in the past tense on purpose. It is the reason for the design, not a live invariant: the reader and
its assertions report whatever split they find, and the count is printed rather than pinned, because a
row asserting 143 would redden the next time anybody records a proof.

## The gate half, and how it is proven

The gate stamps `.veldo/last_verify` from `scripts/verify.sh`, which is a protected path, so adding
the producing version there needed a recorded approval. Dmitry gave it on 2026-08-12 and the line
landed in both gates, this repository's and the shipped template's.

**A protected path cannot be proven by reading it.** The first version of AC5 tried, with two
substring scans over `verify.sh`'s text, and independent review refuted them in one move: delete the
field from the printf in both gates and from `run_scope.verify_stamp_payload`, leave behind a comment
reading `# TODO(VELDO-0010): the record still owes a "veldo_version": field`, and this item's suite
stayed at 44 passed 0 failed while the whole repository stayed at 4530 passed 0 failed, with the
record the gate writes carrying no version at all. A substring scan used to prove a presence is the
same defect as one used to prove an absence.

So the criterion runs the thing. Each gate is copied into a throwaway tree beside `.veldo/version.py`
and executed, twice: once with a canonical declaration present, once without. The record it produced
is parsed, and the assertions are about that record - the key is there, the readable version is the
one declared, the unreadable one is `null`, and the key set equals the payload `scripts/run_scope.py`
declares for the first Python-side writer. The run is red in that tree, deliberately, because no
check script is there to pass: the stamp is written on both the green and the red path and what is
under test is its content, not the verdict.

That measurement immediately earned itself. The version derivation read the first word of
`version.py`'s stdout, and `version.py` prints its refusal on stdout for every cause it models, so in
any tree that cannot read a version the record said `"veldo_version":"veldo"` - a fabricated identity
in the one record where it would be believed, shipped to adopters in the template. The gate now checks
the exit status and the shape, and the row that catches it prints the value it found.
