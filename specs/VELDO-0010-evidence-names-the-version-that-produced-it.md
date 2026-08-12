---
schema: veldo.spec/v1
id: VELDO-0010
title: Evidence names the version that produced it - an optional proof-bundle field, a reader that
  reports the 143 bundles predating it as UNVERSIONED rather than inferring today's, and a gate line
  held for approval
status: ready
risk: standard - it adds one OPTIONAL field to the proof-bundle contract and a reader over it, and
  refuses nothing that passes today. It is NOT low because it touches the artifact that records whether
  a criterion was met, and a required field here would have reddened 143 existing bundles on the day it
  landed. It is not high because the field is optional by construction, the reader gates nothing, and
  the one gate-output line it would add is held for a recorded approval rather than written
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W9
placement: [contracts]
footprint:
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
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    The reader reports the bundle count, how many name their producing version, how many predate the
    field, and how many are malformed - and it says in words that nothing infers a version for the
    ones that predate it. A malformed field names the bundle and what was wrong with it.
  error_taxonomy: >
    UNVERSIONED (the bundle predates the field: not an error, and never inferred) and a malformed
    field (present but not version-shaped, named with the bundle). The distinction is the item: an
    absent field is the state 143 bundles are legitimately in, and a present-but-broken one is
    somebody's mistake.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Add the version field to PROOF_REQ in .veldo/validate.py so a bundle without it is refused, and
      the assertion that this repository's 143 existing bundles all validate unchanged must go red.
    text: >
      THE FIELD IS OPTIONAL BY CONSTRUCTION, AND THE MIGRATION IS THE ITEM. MEASURED on 2026-08-12:
      143 proof bundles exist in this repository and NONE carries a producing version. Requiring the
      field would redden a working repository on the day it landed, which is how a correct rule gets
      reverted - the lesson VELDO-0001 wrote down and this item obeys. So the field is absent from
      PROOF_REQ, every existing bundle validates unchanged, and the reader reports the count that
      predate it.
  - id: AC2
    falsified_by: >
      Make the reader fall back to the tree's current version for a bundle with no field in
      .veldo/version.py, and the assertion that a bundle without the field is UNVERSIONED and appears
      under no version in by_version must go red.
    text: >
      NOTHING IS INFERRED FOR A BUNDLE THAT DOES NOT SAY. Reporting today's version for evidence
      written by an older one would state exactly the fact this field exists to establish, and it is
      the confident zero in its most damaging form: evidence produced when the checks were weaker
      would become indistinguishable from evidence produced now. An absent field is UNVERSIONED, it
      appears under no version, and the report says in words that nothing was inferred.
  - id: AC3
    falsified_by: >
      Accept any string as a version in .veldo/version.py, and the assertion that a bundle declaring
      the field as "latest" is reported MALFORMED with the bundle named must go red.
    text: >
      A PRESENT FIELD IS CHECKED FOR SHAPE AND NEVER FOR EQUALITY. Shape, because "latest" or an empty
      string is somebody's mistake and naming it is how they fix it. NEVER equality with the tree's
      current version, because a bundle produced by an older version legitimately carries an older
      version and that is the entire purpose of recording it - a check demanding agreement would make
      the field useless the first time it was true. NEGATIVE CONTROL: a version-shaped value is
      accepted and appears under its own version.
  - id: AC4
    falsified_by: >
      Drop the unversioned count from the report in .veldo/version.py, and the assertion that the
      counts PARTITION the bundles exactly - versioned plus unversioned plus malformed equals the
      bundle total - must go red.
    text: >
      THE COUNTS PARTITION THE BUNDLES EXACTLY, so a reader can tell how much of the evidence corpus
      the answer covers. Versioned plus unversioned plus malformed equals the total, asserted over
      this repository's real corpus. A report that quoted only the versioned count would be a coverage
      figure without the weakness that produced it, which is the shape this plan's ledger keeps
      recording.
  - id: AC5
    falsified_by: >
      Declare a version slot in scripts/verify.sh, and the assertion that the gate-output half is NOT
      yet written and that scripts/verify.sh is unchanged by this item must go red.
    text: >
      THE GATE-OUTPUT HALF IS SPECIFIED AND NOT WRITTEN, AND THIS CRITERION SAYS SO RATHER THAN
      PRETENDING. The gate stamps .veldo/last_verify at scripts/verify.sh, a PROTECTED PATH, so adding
      the producing version there needs Dmitry's recorded commit-bound approval. This item lands the
      evidence half and asserts the true state of the other: scripts/verify.sh carries no version
      stamp and is not in this item's footprint. It flips to asserting the stamp when the approval
      lands, the same posture VELDO-0001 and VELDO-0007 use, because a criterion that quietly passed
      while unwritten is the false coverage this project keeps finding.
required_evidence: [unit]
rollback: >
  Delete the provenance reader from .veldo/version.py and its suite fragment. No bundle changes, no
  contract field is removed because none was required, and every existing bundle stays valid, so the
  retreat costs one function and loses nothing already recorded.
---

# Evidence names the version that produced it

## The measurement that shapes the whole item

143 proof bundles exist in this repository. **None of them carries the version that produced it.**

That is why the field is optional and why nothing infers a value. Requiring it would redden a
working repository the day it landed, and inferring today's version for older evidence would state
exactly the fact the field exists to establish: evidence written when the checks were weaker would
become indistinguishable from evidence written now.

So the honest shape is the one VELDO-0001 established: add the field, report the migration, and let
the flip to requiring it be a separate act with its own count.

## The half that is not written, and why

The gate stamps `.veldo/last_verify` from `scripts/verify.sh`, which is a protected path. Adding the
producing version there needs a recorded approval, so this item lands the evidence half and asserts
the true state of the other rather than writing the line first and asking afterwards.
