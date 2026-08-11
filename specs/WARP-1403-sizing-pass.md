---
schema: veldo.spec/v1
id: WARP-1403
title: The sizing pass - an in-session agent reads the spec and the code it will touch, and its
  prediction is one optional layer that can never pretend to be a measurement
status: ready
risk: standard - a new module beside the estimate record that reads specs, code and the event log
  and writes nothing unless asked. No gate stage is added, nothing is enforced, and a repository
  committing no judgements is byte-identically unaffected. It is not low because this is the ONE
  place in PLAN-0014 where an LLM enters the estimating path (NG2), so a seam that fabricated a
  judgement, or a layer that let a guess read as calibrated, would put an invented number into a
  committed range that W5 later reconciles and W8 converts to dollars, and no later item could
  tell it apart from a real prediction.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W3
depends_on: [WARP-1402]
placement: [metrics]
footprint:
  - ".veldo/sizing_pass.py"
  - "engine/.veldo/sizing_pass.py"
  - ".veldo/examples/sizing-judgement-example.yaml"
  - "engine/.veldo/examples/sizing-judgement-example.yaml"
  - "scripts/suites/16_warp_1403_sizing_pass.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1403-sizing-pass.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THE SEAM FAILS LOUD AND NOTHING HERE MANUFACTURES A RANGE. The sizing agent is a seam. The
      reference implementation RAISES, naming the refusal, exactly as the executor's LiveLoop
      refuses to fabricate a build and dispatch's LiveReviewer refuses to fabricate a verdict; the
      composition refuses the same way with no agent wired; the file-backed agent is TRANSPORT and
      refuses on an absent file rather than producing anything; and an agent that raises has its
      exception propagate UNCHANGED, because a handler around that call is a fallback and a
      fallback here is a fabricated estimate. Paired with the positive control that an injected
      agent and a judgement file each DO produce a record carrying the layer, and with the
      anti-vacuity control that two judgements over ONE brief give two different layers carrying
      exactly the bounds the agent gave - so the range is provably the agent's and not derived
      from the brief behind its back.
  - id: AC2
    text: >
      THE JUDGEMENT IS VALIDATED FAIL CLOSED, ON THE RULES AND VOCABULARIES THAT ALREADY EXIST.
      veldo.sizing_judgement/v1 refuses an unknown key by name rather than ignoring it, names
      every missing required key, and refuses a bad schema, a malformed brief digest, an empty
      model identity, a reasoning below the stated floor or spanning more than one line, a
      non-positive self cost, and a cost provenance outside spend.py's declared table (asserted as
      a SET EQUALITY against that table, so a provenance added there works here with no edit).
      The bounds rule is FETCHED from veldo.estimate/v1 rather than respelled: the point refusal is
      W2's own message, this module's source carries no copy of it, and with that rule deleted the
      fetch refuses instead of falling back. Every refusal is paired with the positive control
      that the same judgement validates clean once corrected.
  - id: AC3
    text: >
      THE BRIEF IS MECHANICAL AND DETERMINISTIC, AND A DIGEST BINDS THE JUDGEMENT TO IT. The brief
      is derived with no clock, no network, no subprocess and no model call, from the spec's own
      features through W1's ONE feature reader, the code its footprint resolves to through the ONE
      glob compiler, the ledger, and the structural prior W2 computed; two calls give identical
      bytes and an identical digest. The digest is sensitive to all four things it claims to bind
      (spec, code, ledger, prior), with the code and ledger cases attributed EXACTLY by differing
      in that block alone, and a judgement whose digest is stale or whose spec is another spec is
      REFUSED rather than reused. A footprint entry that leaves the repository is refused before
      anything is read; an existing path carries measured bytes and lines while an absent one
      carries NO SIZE AT ALL; a glob that matches nothing is counted apart from a literal that
      does not exist.
  - id: AC4
    text: >
      HONEST ABOUT THE LEDGER AND ABOUT ITSELF. Measured over this repository: the event log
      carries over a thousand events and NOT ONE with a spend field, so the brief reports
      anchor_available no and OMITS the numeric anchor keys rather than reporting zero - paired
      with the seeded control where the same function reports the recorded total, which is what
      makes the standdown a measurement instead of a hardcoded answer. An agent's judgement never
      makes an estimate calibrated: agent_judgement is not one of W2's grounded bases, the record
      reads uncalibrated, and moving that basis into the grounded set makes this module REFUSE to
      write the layer at all (driven, not asserted). The pass's own token cost is recorded through
      spend.py's ONE writer against the spec it sized, carrying the digest and the model; the
      layer states the cost as a share of its own lower bound against a declared ceiling, and
      crossing it is REPORTED and never refused. The layer widens the committed range or leaves it
      alone, never narrows it, and the prior shown in the brief is asserted EQUAL to the prior the
      record commits rather than assumed to be the same number.
  - id: AC5
    text: >
      OPTIONAL, ADOPTION SAFE, AND NEVER A BLOCKER - the AC that matters most, because it is
      PLAN-0014's C3 and NG1. With no judgements present every reader stands down silently,
      creating nothing, and a record with no sizing layer is complete. A present-but-broken
      judgement is named rather than dropped, and a record filed under the wrong name is refused.
      Nothing in scripts/verify.sh, in the contract validator, or in any other engine module names
      this module. And the load-bearing measurement: a spec with NO estimate, with a
      structural-only estimate, with an estimate carrying a real sizing layer, and with a
      MALFORMED judgement committed beside it all return the identical result from the real
      validate.check_spec, with the negative control that the same validator DOES refuse a
      genuinely broken spec under the same root.
required_evidence: [unit]
rollback: >
  Delete the module, its engine copy, the example judgement and its engine copy, and the suite
  fragment, then remove the suite from the manifest (regenerating scripts/suites/requires.json and
  specs/index.md). Nothing reads it, no gate stage runs it, and it writes no state unless
  explicitly asked to; the estimate records already committed stay valid, because a record with
  only a structural proxy layer is a complete record.
---

## Outcome

W2 committed the estimate record and its first layer, a structural proxy that reads only the
spec's mechanics. This is the second layer and the only place in PLAN-0014 where a model is asked
anything (NG2): a small in-session agent reads the spec AND the code the spec says it will touch,
and predicts a range with stated reasoning.

Its value is the information the mechanical layer cannot have. The proxy counts acceptance criteria
and footprint entries; it cannot tell a new 40-line module from a 900-line one it has to change
without breaking, or notice that four of five declared paths do not exist yet. An agent that reads
the code can. Its cost is noise: a prediction is not a measurement, and this item's whole design
is about making sure nobody downstream can mistake one for the other.

## What could go wrong here, and what stops it

A sizing pass has exactly one catastrophic failure mode: a plausible number that nobody produced.
An invented range is indistinguishable from a real prediction, it widens a committed range on
nothing, and at reconciliation (W5) a real actual gets scored against a fabrication - which
poisons the calibration curve the whole plan exists to build.

So the agent is a SEAM and the reference implementation raises. That is not caution, it is the
posture this repository already takes at its two other agent boundaries: `LiveLoop.build` refuses
to fabricate a build and `LiveReviewer.review` refuses to fabricate a verdict. There is no
default range, no heuristic and no fallback anywhere in the module; the only two ways a judgement
exists are an injected agent and a file an agent wrote, and both refuse rather than invent. The
suite proves it by driving it: with the seam unwired the pass refuses, and with an agent that
raises, the exception comes out unchanged, because a handler there IS a fallback.

## The brief, and why it has a digest

The agent is not asked to go and look at whatever it likes. It is handed a BRIEF derived
mechanically: the spec's features through W1's one feature reader, the code its footprint resolves
to (bytes, lines, what exists and what will be created), the state of the actuals ledger, the
structural prior W2 already computed, and the ask itself. No clock, no network, no subprocess.

The brief's sha256 is echoed in the judgement, and that single field carries most of this item's
integrity. A judgement is only ever about the brief it was made from: if the spec gained a
criterion, if the code moved, if the ledger gained history, or if the prior was refitted, the
digest no longer matches and the judgement is REFUSED rather than quietly applied to a different
question. It also makes a judgement untransplantable between specs. The suite measures the
sensitivity to all four inputs rather than asserting it, because a digest that ignored one of them
would pass a mere equality check and bind nothing.

## The measured finding of this item

**This repository's ledger is empty, and the emitter W1b shipped has never once been called.**
Measured over `.veldo/events.jsonl` at the commit this item was built from (a06fc17): 1094
events, of which 785 `gate.passed`, 171 `verdict.recorded` and 138 `gate.failed`; **zero carry
`tokens`, `cost_usd` or `human_minutes`, and there is not one `spec.shipped` spend record.** W1
measured the same gap at 904 events and built `spend.py` to close it; nothing has emitted through
it since. The total grows by one line per gate run, which is why the suite binds its assertion to
the log's own length rather than to this figure; what it pins is the ZERO.

Two consequences travel with every number this item produces:

- The brief reports `anchor_available: no` and OMITS its numeric anchor fields rather than
  reporting them as zero. A zero because nothing was spent and a zero because nothing was ever
  recorded are different facts, and an agent handed the second as a measurement calibrates against
  nothing while feeling informed. The seeded control beside that assertion is what makes the
  standdown a measurement rather than a hardcoded answer.
- Recording this pass's own cost would be the FIRST spend record this repository has ever written.
  It goes through `spend.py`'s one writer, against the spec being sized, so the estimating
  apparatus's cost lands INSIDE the measured cost of the change it sized - which is the only way
  PLAN-0014 C4's proportionality claim can ever be checked instead of asserted.

## A prediction is never a measurement

`agent_judgement` is deliberately not one of W2's calibrated bases, so a record carrying this
layer still reads `calibration: uncalibrated`. This module checks that at the moment it writes a
layer and REFUSES if it ever stops being true, and the suite drives that refusal by moving the
basis into the grounded set and watching the module decline to write anything.

The arithmetic agrees: the committed range is the ENVELOPE of the layers, so this layer can only
widen it. A sizing pass sharpens by disagreeing visibly, never by tightening a band nothing
supports (NG6).

## Delivery notes, including the reds

THE TEETH. 30 deliberate mutations of the module were applied one at a time, each restored before
the next, plus two targeted probes; **35 of the 37 assertions were watched failing from a module
mutation, and the remaining two from the probes: the AC5 negative control (planting a spec that is
not actually broken) and the gate-naming sweep (a throwaway module naming this one, since
verify.sh is outside this item's footprint and was never edited).** The most instructive:

- LiveSizingAgent returning a range instead of raising: the fail-loud assertion RED, and the
  injected-agent control GREEN, which is what makes it attributable to the seam.
- A handler around the agent call: 2 RED, including the propagation assertion.
- Dropping the digest comparison: 2 RED, the stale-judgement refusal and the example-judgement
  binding, while the clean-judgement control stayed green.
- Reporting `tokens_recorded: 0` on an empty ledger: 1 RED, the honest-omission half, while the
  seeded half stayed green.
- Re-spelling the bounds rule locally with W2's exact wording: 2 RED. The local copy kept the
  point refusal and silently lost the inverted, non-integer and non-positive refusals, which is
  the second-spelling defect in miniature.
- Taking the layer's bounds from the prior instead of the judgement: 4 RED, including the
  anti-vacuity assertion.

A MEASUREMENT ABOUT THE SUITE ITSELF, found while proving the teeth: three of those mutations
originally killed the fragment with a traceback at its first composition call and produced ZERO
verdict lines, so the assertions they were meant to red were never seen failing. A crash is
strictly worse than a red, because it makes a run that found nothing look like a run that could
not look. Every call in the fragment whose refusal is a raise now turns that exception into DATA,
the composition's own success is an assertion like any other, and no mutation crashes it now.

AND ONE ABOUT THE HARNESS, worth recording because it produced a false attribution: two
same-length mutations written in the same second reused a stale `__pycache__` entry, so a red was
attributed to the wrong mutation until the batch was re-run with bytecode writing off. The brief's
own walk excludes `__pycache__` and `.pyc` for the same species of reason, and the suite asserts
it: a brief's digest must not depend on what was imported recently.

## Out of scope

- Any enforcement. Nothing here gates, blocks, deprioritizes or delays work on an estimate (NG1,
  D4). There is no new gate stage and verify.sh is untouched.
- Historical analogy (W4). Matching this spec to similar shipped specs and predicting from their
  recorded actuals is a different layer on a different basis; the brief reports whether measured
  history EXISTS and never derives a prediction from it.
- Reconciliation, recalibration and the estimator's accuracy curve (W5), which is where this
  layer's noise finally gets scored; normalization (W6); the judgement-load pair (W7); the plan
  roll-up and dollar conversion (W8).
- Writing a judgement. A module that could write one could also invent one, so the judgement is
  the agent's own artifact and this module only reads, validates and refuses. The shape ships as a
  validated example whose digest is honestly of no brief in this repository.
- Committing an estimate for this spec itself, which would have to be dated before a build that
  had already happened.
- The capability manifest entry and the release hold list. `.veldo/capabilities.yaml` is
  integrated separately, and `engine/.veldo/sizing_pass.py` belongs in scripts/publish.py's
  deliberate hold-back list beside the other PLAN-0014 modules until this item has had its own
  independent review; both lines are recorded with this item's delivery notes rather than edited
  here.
