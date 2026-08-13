---
schema: veldo.spec/v1
id: WARP-1402
title: The estimate record and the structural proxy - a range committed before build, with every
  layer's contribution on record
status: ready
risk: standard - a new module that reads specs and the declared policy and writes nothing unless
  asked. No gate stage is added, nothing is enforced, and a repository committing no records is
  byte-identically unaffected. It is not low because this record is the shape three later items
  write into (W3, W4, W5) and one reads for budgets (W8), so a schema that admitted a point
  estimate, or a committed range its own layers do not support, would propagate a false number
  into every surface above it and no later item would be able to tell.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W2
depends_on: [WARP-1401]
placement: [metrics]
footprint:
  - ".veldo/estimate.py"
  - "engine/.veldo/estimate.py"
  # The ONE footprint reader this item's feature read goes through. It belongs to WARP-1401 and is
  # declared here because this item's 2026-08-13 remediation repairs it: the reader stopped at the
  # first non-item line, so a comment truncated a spec's declared surface and THIS item published
  # the short count as a measurement.
  - ".veldo/toe_corpus.py"
  - "engine/.veldo/toe_corpus.py"
  - ".veldo/examples/estimate-example.yaml"
  - "engine/.veldo/examples/estimate-example.yaml"
  - "scripts/suites/15_warp_1402_estimate_record.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1402-estimate-record-and-structural-proxy.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      A RANGE, NEVER A POINT, AND THE UNIT IS PART OF IT. veldo.estimate/v1 refuses low equal to
      high by name, refuses an inverted range, refuses a non-integer or non-positive bound, and
      refuses a missing or unknown unit naming the declared set. The unit is declared ONCE at the
      top level and a layer that spells a unit of its own is refused, because two spellings of one
      unit is this repository's named second-spelling defect. A selftest drives each refusal and
      pairs it with the positive control that the same record validates clean once corrected.
      AND THE KEY IS A KEY. The schema's premise is that the filename IS the key, so a `spec` that
      is not its own filename is REFUSED - in `validate_record`, the ONE gate every reader and every
      writer here asks, by delegation to the claim ledger's ONE definition of an id that cannot be
      stored faithfully rather than a second character rule. Independently of that rule, both the
      writer and the reader resolve a record's path through ONE place that requires the resolved
      file to lie inside the records directory. Measured 2026-08-13 before either existed: a spec
      whose `id:` was `../policy` was accepted by the contract validator with zero errors, the
      record was VALID, and the writer replaced `.veldo/policy.yaml` - the file that declares which
      paths are protected - with an estimate record.
  - id: AC2
    text: >
      THE COMMITTED RANGE IS DERIVED FROM THE LAYERS PRESENT AND THE RECORD CANNOT LIE ABOUT IT.
      The record declares a combination rule from a declared table (v1 declares `envelope`, the
      union), and the validator RECOMPUTES the committed range from the layers through that rule:
      a range hand-widened or hand-narrowed by even one token is refused by name. The envelope
      never narrows, which is NG6 in arithmetic - two layers that disagree are evidence of
      uncertainty, and averaging them would manufacture confidence out of disagreement. A selftest
      mutates a committed bound and requires the refusal, and separately requires that adding a
      wider layer widens and adding an enclosed layer does not narrow.
  - id: AC3
    text: >
      EVERY LAYER SAYS WHAT IT CONTRIBUTED AND ON WHAT BASIS, AND CALIBRATION IS DERIVED RATHER
      THAN ASSERTED. Each layer carries a layer id from the declared vocabulary (unique within a
      record), its own low and high, a basis from the declared vocabulary, and the inputs it
      actually used; the record's `calibration` must equal what those bases support, so a declared
      prior can never be presented as a measurement. Measured over this repository: the actuals
      corpus has 0 percent spend coverage (WARP-1401), so every record this module can produce
      today reads `calibration: uncalibrated`. A selftest requires the refusal of a claimed
      calibration, and its control: a record carrying a corpus-grounded layer is ACCEPTED as
      calibrated, so the check is the bases' doing and not a rule that always refuses.
      AND OVER EVERY STATE A LAYER'S `inputs` KEY CAN BE IN, VALID MEANS WRITABLE: that map is
      checked against exactly what the ONE writer writes and the ONE parser reads back, so a record
      the validator calls valid with any of those states survives its own write and reads back as
      itself. An EMPTY map, a key the parser cannot read back as a key, a value the writer cannot
      render, a non-mapping, and the key PRESENT WITH A NULL VALUE are each refused BY NAME rather
      than silently dropped on the way to disk or left to crash the writer. That last state is
      reachable from a file and not only from a fixture, because the ONE parser reads a bare
      `inputs:` line as null, and it is refused by ONE rule over EVERY declared key in both scopes:
      optional in this schema means present or absent, null is neither, and no reader may reach an
      optional key through a lookup that reads a present null as an absence. The claim is bounded
      deliberately and is not that every accepted record is writable: a single-line string value the
      subset would read back as something else (padded, all digits, opening with a bracket) is still
      refused AT WRITE TIME by the ONE renderer, by name and never as a crash, which is where this
      record has always drawn that line. A selftest drives every state of the `inputs` key through
      the real writer and the real reader, requires each refusal to be a refusal rather than a
      crash, and pairs them with the controls that the key ABSENT and a non-empty map both validate
      clean.
  - id: AC4
    text: >
      THE STRUCTURAL PROXY IS DETERMINISTIC, MECHANICAL, MONOTONE AND SCALE-HONEST. It reads the
      spec's features through toe_corpus's ONE feature reader and ONE footprint reader, reads no
      clock, spawns nothing, and takes its review count and gate depth from the declared
      `.veldo/policy.yaml` while stating in the record which numbers came from the policy and
      which from the declared default. The same spec on the same date renders byte-identical
      bytes; more acceptance criteria, a larger regression surface, a higher risk tier and a
      protected-path touch each strictly widen the range; rounding never collapses a range into a
      point; and the token scale it multiplied by, the coefficients its structural weight was built
      from and the NAME of that coefficient set are all recorded IN the layer, so a later
      reconciliation can separate a wrong structure from a wrong scale and can still decompose a
      record written before the coefficients changed. A selftest drives each property, including the
      anti-vacuity control that the proxy is not a constant, and it reproduces the layer's bounds
      FROM THE RECORD ALONE rather than from this module's constants.
      A FEATURE THIS LAYER CANNOT READ IS A REFUSAL AND NEVER A ZERO. A spec that declares no
      footprint block has a regression surface of 0 and estimates fine; a footprint block that is
      PRESENT and reads as empty is refused by name, because a surface of 0 and a protected touch of
      `no` would then be stated as measurements nobody made. Measured 2026-08-13: the ONE footprint
      reader stopped at the first line that was not a list item, so a comment inside a block
      truncated it and a comment on its first line emptied it - 8 of this repository's 215 specs got
      a materially wrong record and 3 of them said `protected_touch: no` about a spec that does touch
      a declared protected path. The reader is repaired here and the refusal covers the next
      unreadable shape.
      THE SOURCE PROPERTY IS ASSERTED AS A PROPERTY, NOT AS TODAY'S ANSWER: for every declared tier,
      a tier the policy really offers through the ONE parser reads `policy` with the file's own
      numbers and a tier it does not offer reads `default` with the default table's numbers. Nothing
      requires any particular tier to be readable, so repairing `.veldo/policy.yaml` reds nothing;
      the folding this item measured is driven against hermetic policy fixtures instead.
  - id: AC5
    text: >
      ADOPTION SAFE, AND NEVER A BLOCKER - the AC that matters most, because it is PLAN-0014's C3
      and NG1. With no records present every reader stands down silently, creating nothing and
      reporting nothing as a finding. No stage the gate runs names this module or its records
      directory, asserted over a DERIVED domain: the required stage set is parsed out of
      scripts/verify.sh's catalog and its always-run body and then closed over what each member
      executes or loads, so a slot repointed at a new stage script enters the domain by itself. That
      claim is bounded to what a text property can support and says so - a stage that COMPUTED the
      path would pass it, which is why the load-bearing evidence below is behavioural. What stood
      here, "nothing in scripts/verify.sh calls this module", was proven by scanning two files for a
      literal, and a required stage reached by a computed path walked past all of it. And the
      load-bearing pair: a spec with NO estimate, a spec with a VALID estimate beside it, and a
      spec with a MALFORMED estimate beside it all return the identical result from the real
      validate.check_spec, while the malformed record is named by validate_record - so absence or
      breakage of an estimate provably cannot invalidate a spec, and the pass is a measurement
      rather than an absence.
required_evidence: [unit]
rollback: >
  Delete the module, its engine copy, the example record and the suite fragment, and remove the
  suite from the manifest (regenerating scripts/suites/requires.json and specs/index.md). Nothing
  reads it, no gate stage runs it, and it writes no state unless explicitly asked to; a repository
  that committed no records is unaffected either way.
---

## Outcome

PLAN-0014 sizes work in the machine's own unit. W1 built the corpus of what changes actually cost.
This is the other half of the measurement: the record that says what a change was EXPECTED to
cost, committed before the work starts so that a later reconciliation has something to reconcile
against.

It is the keystone of the plan. Three later items write into this record and one reads it, so the
shape is defined here in full, in the module docstring, rather than left to be discovered: W3
adds a sizing-pass layer, W4 adds a historical-analogy layer, W5 reconciles the record against the
actual and writes a recalibrated layer, and W8 sums records into a plan budget and a dollar range.

## What the record has to make possible

A single pair of numbers beside a spec is almost worthless. At reconciliation the actual is one
number, and a record holding only a combined range can say nothing better than "in" or "out". So
the record carries each layer's OWN range and the inputs that layer used, which buys the one
distinction that separates an estimator that improves from one that only keeps score: whether a
right answer came from right reasoning.

That is concrete here. The structural proxy multiplies a structural WEIGHT it derives from the
spec by a token SCALE it derives from nothing. Both are in the layer's inputs. A reconciliation
can therefore tell a good estimate (weight right, scale right) from a lucky one (weight wrong,
scale wrong in the other direction), and it can refit the scale without touching the structure.

**And the coefficients the weight was built from are in the inputs too, with a name for the set.**
Without them the weight is one number a later reader can decompose only by importing today's
constants, so the promise above would hold exactly until one coefficient changed: from that day an
old record's structure could not be recovered and no reader could tell which model produced which
record. It is cheap while no record exists and expensive the day they do, which is the same argument
this item makes for defining the whole schema up front.

## The inherited finding, which shapes every number here

WARP-1401 measured that this repository's spend inputs are empty: 904 events, 148 shipped specs,
95.3 percent cycle coverage and **0 percent spend coverage**, because a token count is not
knowable from inside a repository and nothing has ever emitted one.

That warning travels with every number this item produces. The proxy's structure is derived from
the spec and is honest; its SCALE is a declared prior with no evidence behind it at all. So the
record says so: `calibration: uncalibrated`, `basis: uncalibrated_prior`, and the scale itself
written into the layer's inputs where W5 can find and replace it. Nothing here presents a stated
number as a measured one.

## The measured finding of this item

The proxy takes its expected review count and gate depth from `.veldo/policy.yaml` rather than
inventing them. **Measured: this repository's `critical` tier is written across two lines, and the
ONE front-matter parser folds a deeper-indented continuation into the preceding scalar, so that
tier arrives as a STRING rather than a map and its review count is not readable there.** The
`standard` tier, which almost every spec uses, reads cleanly.

Falling back to the declared default is the right behaviour, and hiding the fallback would put a
default into a record that looks like a policy reading. So every record states
`reviews_source: policy` or `reviews_source: default`.

**The selftest asserts the PROPERTY that makes those words worth anything - the source a record
states is the source the number came from, for every declared tier - and not this repository's
current answer for one tier.** The first version required `policy_tier('critical')` to come back as
`default`, which is to say it required the file above to STAY unreadable: repairing it, by writing
the same inline map on one line and changing no meaning, turned a required stage red. The folding is
now driven against three hermetic policy fixtures (the same tier on one line reads `policy`, the
same tier across two lines reads `default`, no policy at all falls back for everything), so the
finding is reproduced without anything in the gate depending on this file staying broken.

## Out of scope

- Any enforcement. Nothing here gates, blocks, deprioritizes or delays work on an estimate
  (NG1, D4). There is no new gate stage and verify.sh is untouched.
- The other two estimating layers. The sizing pass is W3 and historical analogy is W4; their
  layer ids and bases are declared in this schema so they extend a vocabulary rather than widen
  one, but neither is built here.
- Reconciliation, recalibration and the estimator's own accuracy curve (W5); normalization to a
  stable display point (W6); the judgement-load pair (W7); the plan roll-up and dollar conversion
  (W8).
- Committing an estimate for this spec itself. It would have to be dated before a build that had
  already happened, which is a fabricated commitment; the shape ships as a validated example
  record instead.
- The capability manifest entry. `.veldo/capabilities.yaml` is integrated separately; the exact
  line to add is recorded with this item's delivery notes.
