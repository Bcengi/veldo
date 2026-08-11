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
acceptance_criteria:
  - id: AC1
    text: >
      A NORMALIZED POINT, WITH THE RAW TOKENS STILL ON THE ROW. `normalize` renders every corpus
      record as a point against the peg (`tokens / peg_tokens`), the peg's own change being exactly
      1.000, and every view ROW carries the RECORDED tokens and the RECORDED cost, unrounded and
      unrescaled, so the ground truth is always one field away from the planning number (D2: both
      units, the point primary). THE RENDERED LINE SHOWS THE TOKENS AND, ONLY WHEN A PRICE IS
      SUPPLIED, A DOLLAR COLUMN DERIVED FROM THOSE TOKENS; it deliberately does NOT print the
      recorded cost, because two different dollar figures in one column invite a reader to take a
      price projection for a recorded actual. The recorded cost is on the row for a consumer of the
      view, which is where the "same row" claim above is discharged.
      A record whose TOKEN spend was never recorded gets NO POINT and a stated reason, never a zero,
      because a confident zero and an unmeasured change are indistinguishable once a zero is printed.
      The gate is a POSITIVE RECORDED TOKEN COUNT and not the corpus's `spend_recorded` flag: that
      flag is true when ANY spend field carries a number, so a change costed only in dollars or only
      in human minutes would otherwise print 0.000 pt and be counted as a measured change. Such a
      change gets no point either, with a reason NAMING the spend field that was recorded and saying
      the token count was not, which is a third fact distinct from nothing being recorded at all. One
      named predicate (`recorded_tokens`) serves the display and the peg derivation, so the two paths
      cannot disagree about which changes were measured in tokens.
      Selftests: the five seeded changes come out at the expected points; the raw token AND recorded
      cost columns are asserted EQUAL to the corpus's own spend block for every row of two corpora,
      the second carrying deliberately non-round values (3137 and 41 tokens, 12.37 and 0.0137 usd)
      so a rounding at any granularity or a 100x rescale of the money column reds it; the no-spend
      row is required to have no point and a reason naming the confident zero it refuses to print; a
      cost-only change and a human-minutes-only change are required to have no point, distinct named
      reasons, and no `0.000 pt` anywhere in the render, with the control that adding a token count
      turns the point on and that neither can become the derived peg; the rendered dollar column is
      asserted to be the price-derived figure and NOT the recorded cost; and the summary roll-up is
      asserted as ONE whole-dict equality over three fixtures together with the printed bottom line,
      because points_total, tokens_total and eras_present are the numbers a planner sizes work with.
  - id: AC2
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
    text: >
      A CAPABILITY SHIFT IS RECORDED, AND TWO ERAS ARE NEVER BLENDED. One ledger entry per shift
      (`veldo.toe_capability_shift/v1` under `.veldo/toe_eras/`) records when it took effect, which
      model, which model it replaced, and which direction the work per token moved; the ledger
      becomes half-open era intervals and every actual is stamped with the era its spend was
      measured in. A row from an era other than the peg's gets NO POINT, with the reason naming both
      eras, and a change whose own spend events straddle a shift gets no era at all because that
      total is already a mixture of two units. Per D5 no cross-era conversion factor is invented: a
      multiplier claiming to turn one model's tokens into another's is a guess wearing a
      measurement's clothes. Selftests: a written record round trips through `validate.parse_yamlish`
      with every field intact; recording the same era id twice is refused as append-only; with two
      eras the peg lands in the latest and three rows lose their points with both eras named; the
      straddling change and a change whose spend carries no readable timestamp produce two DIFFERENT
      named reasons; and the control, an empty ledger, gives those same rows points again.
  - id: AC5
    text: >
      FAIL CLOSED BY NAME, ADOPTION SAFE, AND ADVISORY. A malformed shift record is refused with a
      message naming the field, over eight hostile shapes: no model, the wrong schema, a timestamp
      with no UTC zone (which would turn a comparison into a TypeError rather than a refusal), a
      timestamp that is not one, a `work_per_token` outside the declared vocabulary, an id that
      would escape the ledger directory, a note carrying a newline the record format cannot round
      trip, and a record that is not a map. A ledger with a bad neighbour still loads the good
      records and leaves the bad ones OUT rather than half applying them. With NO ledger directory
      the ledger is empty, the problem count is zero, and the reporter is never called even once, so
      a repository that records nothing is byte-identically unaffected and is not nagged about a
      file it never asked for. And nothing in the gate consults this module, per PLAN-0014 NG1:
      making a planning convenience able to redden a build is the ceremony this project exists to
      remove. Selftests: each hostile shape refused with its field named and the all() bound to the
      length of its own literal list, the well-formed record validating CLEAN beside it, the absent
      directory asserted as an EMPTY message list, and the gate's own text asserted not to name this
      module with the search proven to work by finding the modules it does name.
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
