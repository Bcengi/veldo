---
schema: veldo.spec/v1
id: WARP-1406
title: Normalization, the stable planning unit - a point pegged to a reference change over raw tokens
  that stay the ground truth, with eras recorded so numbers from two models are never blended
status: ready
risk: standard - a new derivation and display module that reads the corpus, the event log and an
  optional record ledger, and whose only write is a create-only append to that ledger. It adds no
  gate stage, changes no behaviour, and enforces nothing. It is not low because it produces the
  number a planner would size and budget work with, and a display layer that quietly blended two
  models' tokens, or that rounded the recorded actual on its way to the screen, would look exactly
  like a working one while every plan built on it was wrong.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W6
depends_on: [WARP-1401]
placement: [metrics]
footprint:
  - ".veldo/toe_normalize.py"
  - "engine/.veldo/toe_normalize.py"
  - "scripts/suites/15_warp_1406_normalization.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1406-normalization-stable-planning-unit.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: Every withheld number says why, in its own row, and the reasons are four distinct strings
    rather than one silence: nothing recorded, recorded but not in tokens (naming the field that WAS
    recorded), recorded and every figure zero, and the era refusals. The peg line says which basis is
    in force and names the change it is pegged to, or says it is standing down and why. A row whose
    non-token spend sits in another era carries a NOTE saying so. A ledger record that cannot be used
    is refused by name through validate.fail, naming the file and the field. In a tree that carries
    this module without its sibling organs, the read verbs print one line naming the absent organ and
    stand down instead of raising.
  metrics: The roll-up carries both units and its own coverage: pointed, unpointed, points_total from
    the UNROUNDED ratios, raw tokens PER ERA, the tokens that sit in no readable era, a single
    tokens_total only when every raw token in the view is in one era, the eras present and the eras
    declared. A measured change below the display resolution prints `<0.001 pt` rather than a zero.
  error_taxonomy: Three named refusal surfaces, each with one cause per message: validate_shift over
    a capability-shift record, validate_peg over a declared peg, and load_ledger over a ledger
    directory (outside the parser subset, fails validation, duplicate id, two shifts at one instant).
    record_shift raises ValueError with the same messages, and an absent sibling organ raises
    OrganAbsent naming the file, which the read verbs report and the write verb refuses on.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Round the point into the row again: change `row["points"] = tokens / float(peg["tokens"])` in
      `normalize` back to `round(tokens / float(peg["tokens"]), POINT_DIGITS)`. The below-resolution
      row in scripts/suites/15_warp_1406_normalization.py must go red, because fixture R's two
      100-token changes against a 300000-token peg then render `0.000 pt` and points_total falls from
      3.001 to the 3.0 that summing rounded points gives, while the four-shape taxonomy row and its
      control stay green, which is what proves the rounding and not the point gate moved.
    text: >
      A NORMALIZED POINT, WITH THE RAW TOKENS STILL ON THE ROW. `normalize` renders every corpus
      record as a point against the peg (`tokens / peg_tokens`), the peg's own change being exactly
      1.000, and every view ROW carries the RECORDED tokens and the RECORDED cost, unrounded and
      unrescaled, so the ground truth is always one field away from the planning number (D2: both
      units, the point primary). THE RENDERED LINE SHOWS THE TOKENS AND, ONLY WHEN A PRICE IS
      SUPPLIED, A DOLLAR COLUMN DERIVED FROM THOSE TOKENS; it deliberately does NOT print the
      recorded cost, because two different dollar figures in one column invite a reader to take a
      price projection for a recorded actual. The recorded cost is on the row for a consumer of the
      view, which is where the "same row" claim above is discharged. THAT COLUMN IS WITHHELD, as
      `- usd`, ON EVERY ROW WHOSE TOKEN COUNT WAS NEVER RECORDED, decided by the same
      `recorded_tokens` predicate the point uses: it is derived from a token count that does not
      exist, so printing its derived 0.00 tells a reader that a change whose recorded cost is 7.50
      cost nothing, which is the confident zero the point column refuses with `- pt`, one column
      over.
      A record whose TOKEN spend was never recorded gets NO POINT and a stated reason, never a zero,
      because a confident zero and an unmeasured change are indistinguishable once a zero is printed.
      AND A POINT THAT IS REAL BUT BELOW THE DISPLAY RESOLUTION IS NOT A ZERO EITHER: the row carries
      the ratio UNROUNDED, the rounding happens where the number is shown and where it is totalled,
      and a ratio that would render as `0.000 pt` renders as `<0.001 pt` instead. Rounding into the
      row made a measured change contribute exactly nothing to the total a plan is sized with, which
      is the same confident zero arriving through the ruler rather than through the data.
      The gate is a POSITIVE RECORDED TOKEN COUNT and not the corpus's `spend_recorded` flag: that
      flag is true when ANY spend field carries a number, so a change costed only in dollars or only
      in human minutes would otherwise print 0.000 pt and be counted as a measured change. Such a
      change gets no point either, with a reason NAMING the spend field that was recorded and saying
      the token count was not, which is a third fact distinct from nothing being recorded at all.
      FOUR SHAPES REACH THAT BRANCH AND THE FOURTH CANNOT NAME A FIELD: `spend.validate` accepts
      `tokens=0`, so `veldo spend record --tokens 0` is a legal call and the corpus reports that
      change with `spend_recorded` true and every figure zero. A zero in the corpus spend block is
      the DEFAULT for a field nobody recorded, so which field carried the recorded zero is
      unknowable, and "no recorded spend" is FALSE about a change whose record is in the log. It gets
      a fourth reason of its own, saying spend was recorded and every recorded figure is zero. One
      named predicate (`recorded_tokens`) serves the display and the peg derivation, so the two paths
      cannot disagree about which changes were measured in tokens, and the recorded zero can no more
      become the peg than it can carry a point.
      Selftests: the five seeded changes come out at the expected points; the raw token AND recorded
      cost columns are asserted EQUAL to the corpus's own spend block for every row of two corpora,
      the second carrying deliberately non-round values (3137 and 41 tokens, 12.37 and 0.0137 usd)
      so a rounding at any granularity or a 100x rescale of the money column reds it; the no-spend
      row is required to have no point and a reason naming the confident zero it refuses to print; a
      cost-only change and a human-minutes-only change are required to have no point, distinct named
      reasons, and no `0.000 pt` anywhere in the render, with the control that adding a token count
      turns the point on and that neither can become the derived peg; the recorded-zero shape is
      driven THROUGH the shipped spend writer at its own emit injection point (a hand-written
      envelope would be a guess at a shape whose whole claim is that it is reachable), the four
      reasons are asserted as a set of FOUR DISTINCT strings, and the live event log's mtime_ns is
      asserted unchanged across building that fixture; the rendered line is asserted as the COMPLETE
      ORDERED LIST OF FIGURES it prints, at two prices, one of them chosen so the derived figure
      (12.55) lands next to the recorded one (12.37), because the decision that the line does not
      print the recorded cost cannot be guarded by the absence of one spelling of it: a line that
      appends the cost ROUNDED, or that shows the recorded cost in the money column of the row whose
      tokens were never recorded, prints it while every searched-for spelling stays absent; and the
      summary roll-up is
      asserted as ONE whole-dict equality over three fixtures together with the printed bottom line,
      because points_total, the per-era raw totals and eras_present are the numbers a planner sizes
      work with; the below-resolution shape is driven over a fixture whose spread PRODUCES it (two
      100-token changes against a 300000-token peg, where the guard fixture's smallest ratio is
      0.041), pinned to the unrounded roll-up of 3.001 rather than the 3.0 that summing rounded
      points gives, with the control that the same two changes against a peg they are not tiny
      against carry ordinary points; and the money column is asserted as ABSENT on the two rows whose
      tokens were never recorded, which is why their figure lists are one figure long.
  - id: AC2
    falsified_by: >
      Take the middle element of the INPUT order in `peg_from_corpus`, `cands[(len(cands) - 1) // 2]`
      instead of the middle of the sorted counts, which leaves the base fixture's peg unchanged, and
      the "moving ONE recorded count MOVES THE PEG" row in
      scripts/suites/15_warp_1406_normalization.py must go red ALONE: WARP-9411 bumped to 9999 tokens
      must move the peg to WARP-9414 at 4000, and an implementation that picks a position in the
      input order cannot.
    text: >
      THE PEG IS A CORPUS STATISTIC AND IT NAMES THE CHANGE IT IS PEGGED TO (D1). The derived peg is
      the median shipped standard-risk change carrying recorded token spend within one era, and the
      LOWER median is taken deliberately, so the peg is a change a reader can open rather than the
      arithmetic middle of two changes nobody made. A declared record (`veldo.toe_peg/v1`) overrides
      it and the view reports which basis is in force; a malformed declared peg is refused by name
      and does NOT fall back to the derivation, because substituting a different reference change
      for the one a human wrote down changes every number on the surface while looking normal.
      Selftests: the peg is WARP-9413 at 3000 over the five seeded changes and the high-risk change
      at 9000 is excluded; moving one recorded count MOVES the peg to WARP-9414 (so the median is
      computed, not the first or last candidate); on an even sample the peg is the lower median and
      explicitly not the mean; an unpeggable corpus reports `pegged: false` with a reason and every
      row then says it has no peg in force; and a declared peg naming an era the ledger does not
      declare is refused with the declared eras LISTED, checked where the ledger is known rather
      than in the record validator, because that typo is otherwise accepted and then turns every row
      into a null for a reason that reads like an era problem instead of a spelling one.
  - id: AC3
    falsified_by: >
      Make `normalize` cache the point it computed back onto the corpus record it was handed, by
      adding `r["spend"]["points"] = row["points"]` beside the assignment to `row["points"]`, and the
      byte-identity row in scripts/suites/15_warp_1406_normalization.py must go red on the actuals'
      json.dumps snapshot taken before the two re-pegs, while the two-views-must-DIFFER row stays
      green, which is what distinguishes a mutation of the data from a re-render of it. It must be a
      write of a DIFFERENT value: assigning the recorded token count back to itself is a no-op no
      comparator can see, and a declared falsification that cannot redden anything is the defect this
      field exists to prevent.
    text: >
      RE-PEGGING AND RE-PRICING TOUCH NO STORED ACTUAL, AND THIS IS THE AC THAT MATTERS MOST. Every
      reading function is pure over what it is handed: two pegs and two prices are rendered over one
      seeded tree, and afterwards the actuals are BYTE-IDENTICAL, the event log's bytes AND its
      mtime_ns are unchanged, and every seeded spec file's bytes are unchanged. Two legs keep that
      from being vacuous: the two views are required to DIFFER (so the identity underneath is not
      the identity of a run in which nothing happened), and the comparator itself is driven against
      a deliberately tampered copy of the actuals and required to DETECT the change. The price is a
      display column derived from raw tokens, so a price shift moves the money and cannot move a
      point: a point is a ratio of tokens to tokens and no price enters it by construction.
  - id: AC4
    falsified_by: >
      Sum the raw tokens across eras again in `summary`: return `sum(r["tokens"] for r in rows)` as
      `tokens_total` unconditionally, with no per-era split. The per-era roll-up row in
      scripts/suites/15_warp_1406_normalization.py must go red, because the two-era view then reports
      24000 raw tokens as one figure and its printed bottom line stops naming the refusal, while the
      one-era control keeps its single 24000 total, which is what proves the roll-up still totals.
    text: >
      A CAPABILITY SHIFT IS RECORDED, AND TWO ERAS ARE NEVER BLENDED, INCLUDING BY THE RAW TOTAL.
      One ledger entry per shift (`veldo.toe_capability_shift/v1` under `.veldo/toe_eras/`) records
      when it took effect, which model, which model it replaced, and which direction the work per
      token moved; the ledger becomes half-open era intervals and every actual is stamped with the era
      its TOKEN spend was measured in. A row from an era other than the peg's gets NO POINT, with the
      reason naming both eras, and a change whose own TOKEN events straddle a shift gets no era at all
      because that total is already a mixture of two units. THE ERA OF A TOKEN TOTAL IS DECIDED BY THE
      EVENTS THAT CARRIED A TOKEN COUNT, through the same one `recorded_tokens` predicate the point
      uses: a dollar cost or a human-minute record on the other side of a shift says nothing about
      which unit a token total is in, and selecting era events with the corpus's permissive
      `spend_recorded` flag made a change whose tokens were wholly inside one era lose its point to a
      reason that was FALSE about it. That fact is not deleted to make the row green: the row carries
      a NOTE saying where the non-token figures sit and that they did not decide the era.
      AND THE PRINTED ROLL-UP REFUSES THE BLEND THE POINTS REFUSE. The raw tokens are reported PER
      ERA, the tokens of rows whose era cannot be read are counted apart, and a single `tokens_total`
      exists only when every raw token in the view sits in one era; otherwise the bottom line names
      the refusal the way every refused row names its own. A blended raw total presented beside the
      list of eras present is, by this module's own doctrine, a number no model ever produced sitting
      one column from a points total that refused to be one. Per D5 no cross-era conversion factor is
      invented: a multiplier claiming to turn one model's tokens into another's is a guess wearing a
      measurement's clothes. Selftests: a written record round trips through `validate.parse_yamlish`
      with every field intact; recording the same era id twice is refused as append-only; with two
      eras the peg lands in the latest and three rows lose their points with both eras named; the
      straddling change and a change whose spend carries no readable timestamp produce two DIFFERENT
      named reasons; a change whose tokens sit inside one era keeps its point while its human minutes
      sit in another, with the note asserted and the control that the same change without them carries
      no note and that the TOKEN straddle still refuses; the two-era roll-up is asserted as per-era
      figures summing to the total it no longer presents, with the printed bottom line pinned; and the
      controls, an empty ledger, give those same rows points again and one raw total again.
  - id: AC5
    falsified_by: >
      Make `load_ledger` accept every record that fails `validate_shift` into the ledger and report
      nothing: replace the `for m in problems: errs += report(...)` / `continue` branch with `pass`
      so the record falls through to `keep.append(rec)`. The four-path fail-closed row in
      scripts/suites/15_warp_1406_normalization.py must go red on both its refusal count and the
      ledger contents, while the control that those records DO parse cleanly stays green, which is
      what proves the loader's own judgement was removed and not the parser's.
    text: >
      FAIL CLOSED BY NAME, ADOPTION SAFE, AND ADVISORY. A malformed shift record is refused with a
      message naming the field, over eight hostile shapes: no model, the wrong schema, a timestamp
      with no UTC zone (which would turn a comparison into a TypeError rather than a refusal), a
      timestamp that is not one, a `work_per_token` outside the declared vocabulary, an id that
      would escape the ledger directory, a note carrying a newline the record format cannot round
      trip, and a record that is not a map. A LEDGER DIRECTORY FAILS CLOSED ON ALL FOUR OF ITS PATHS,
      each refused by name and left OUT of the ledger while the good records still load: a record
      outside the parser subset, a record that PARSES and fails validation, a duplicate era id, and
      two shifts claiming ONE INSTANT, which is decided on the PARSED instant and not on the
      timestamp string, because one moment has many spellings and accepting two of them declares an
      era that nothing can ever be in. With NO ledger directory the ledger is empty, the problem
      count is zero, and the reporter is never called even once, so a repository that records nothing
      is byte-identically unaffected and is not nagged about a file it never asked for. A tree that
      carries this module WITHOUT the sibling organs it reads is the other adoption axis: the read
      verbs print one line NAMING the absent organ and stand down with a zero exit, and the write
      verb refuses with a non-zero one, because nothing was appended and a reader cannot act on a
      traceback. And nothing in the gate consults this module, per PLAN-0014 NG1: making a planning
      convenience able to redden a build is the ceremony this project exists to remove; the SUBJECT
      of that claim is the gate's own STAGES, derived from validate.py, validate_checks.py, the organs
      validate.py loads by path and the stage scripts verify.sh names, because a substring scan over
      verify.sh's text cannot see a stage added inside `validate.run_all` and that is exactly the
      defect the claim is about. Selftests: each hostile shape refused with its field named and the
      all() bound to the length of its own literal list, the well-formed record validating CLEAN
      beside it, the four ledger paths refused with the count bound to the fixture's own bad-file list
      and the survivor asserted byte-equal to what was written, the absent directory asserted as an
      EMPTY message list, the orphan tree driven through the real CLI in a real directory, and the
      gate-stage set asserted empty with the detector shown to FIRE on both spellings a stage could
      use and to stay silent on a mere mention, since the installer and the publisher both name this
      module in order to ship it and naming is not consulting.
required_evidence: [unit]
rollback: >
  Delete the module, its engine twin, and its selftest fragment; drop the fragment from
  scripts/suites/manifest.json and regenerate scripts/suites/requires.json. Nothing reads it, no
  gate stage runs it, and it holds no state of its own: any era ledger a repository recorded stays
  as inert, valid records.
---

## Outcome

PLAN-0014 sizes work in the machine's own unit. Raw tokens are a good ground truth and a bad
planning number: they move when the model changes, when the price changes, and when a harness
changes how it counts, so a plan denominated in them gets re-sized by events that have nothing to do
with the work. This is the layer that turns the recorded corpus into a number a planner can hold on
to, and it is deliberately a DISPLAY layer: one point is one reference change, and the recorded
tokens sit underneath every point, untouched.

## The peg, and why the lower median

D1 resolved the peg to the median standard-risk shipped change, which is a corpus statistic rather
than a hand-picked favourite. For an even sample the arithmetic middle of two changes is a change
nobody made, so the LOWER median is taken and the peg NAMES its spec. A planner told that the
reference change is 2500 tokens can go and read nothing; one told it is WARP-9412 can go and read
the spec, the proof and the diff.

The founder may replace the statistic with a declared record, and the view always says which basis
is in force. A malformed declared record is refused rather than quietly replaced by the derivation,
because that substitution changes every number on the surface while looking completely normal.

## Eras: the part that would otherwise rot silently

When a new model does more work per token, a token stops meaning what it meant. Two numbers measured
either side of that change are not in the same unit, and a total that mixes them is a number no model
ever produced. So the shift is RECORDED as a ledger entry, the ledger becomes era intervals, and a
row measured in an era other than the peg's gets no point at all, with the reason naming both eras.
Nothing is hidden: the raw tokens are still there, the era is still there, and the refusal to divide
is the honest output.

**No conversion factor is invented, and that is deliberate.** D5 keeps normalization a display
concern rather than a cross-model rewrite of actuals. A single multiplier claiming to convert one
model's tokens into another's would be a guess wearing a measurement's clothes, and it would rewrite
the meaning of every historical number without touching a byte of it.

## Why the ledger is a record directory and not a new envelope event type

`.veldo/events.py` EVENT_TYPES is the vocabulary of things THE LOOP DID: a plan was approved, a gate
ran, a spec shipped. A model vendor shipping a better model is not something this loop did. It has no
commit and no spec, it is effective FROM A DATE rather than emitted at an instant, and it is the same
species as a decision record or a substrate declaration, which this repository already keeps as
validated yamlish under `.veldo/`. Recording it as a ledger entry also means the whole vocabulary of
this item lives in one module instead of being spelled once in `events.py` and again in
`validate.py`, which are the two closed sets a new envelope type has to be added to.

## Measured over this repository, honestly

`python3 .veldo/toe_normalize.py report` here today prints, as its first line:

    peg: NONE, standing down. no shipped standard-risk change in the corpus carries recorded token
    spend in a readable era, so there is nothing to peg to and this view stands down rather than
    presenting a zero

followed by one row per shipped spec, each carrying its real raw tokens (zero) and the reason it has
no point. **174 shipped specs, 0 with recorded spend, 0 points, no peg.** That is WARP-1401's finding
still holding and WARP-0733's emitter not yet being called by anybody, and it is the correct output:
the alternative is a screen full of confident zeros that read as measurements. The selftest asserts
the INVARIANT over that real corpus (no row ever carries a point without recorded spend) rather than
today's figure, so the assertion stays true the day the first agent records its spend.

## Out of scope

- Any cross-era conversion of actuals (D5, and stated above).
- The dollar roll-up per plan and program, which is W8. The price argument here is a display column
  on one view, and it exists to prove that a price shift cannot move a point.
- Judgment load as the second axis of the pair, which is W7.
- Landing this in the packs and making the method document true, which is W10.
- Anything enforcing. Per NG1 no path in this plan blocks, refuses, or delays work on a number, and
  AC5 asserts the gate does not consult this module at all.
