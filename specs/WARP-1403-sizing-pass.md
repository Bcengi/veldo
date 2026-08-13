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
behavior_bearing: true
observability:
  logs: Every refusal is one SizingPassError naming its own subject: the agent seam names that no
    agent is wired, the file agent names the path it found nothing at, a judgement names every
    problem in it, a footprint entry that leaves the tree names the entry, and a brief bound to
    another question names BOTH digests. The CLI stand-down prints which directory it found no
    judgements under and says in its own words that this is not a finding.
  metrics: The layer carries what the prediction was made from and what it cost: the brief digest,
    the model, self_cost_tokens, self_cost_bps_of_low against a declared ceiling, a plain
    within-ceiling yes or no, and the eight brief_* inputs the agent was shown. The brief's ledger
    block reports events, spend_events, specs_with_spend, token_spend_events, tokens_recorded and
    token_figures_non_integer, each gated on the field that licenses it, with anchor_available and
    token_anchor_available answering for what is missing rather than reporting a zero.
  error_taxonomy: ONE exception type (SizingPassError) for every refusal this module makes, so a
    caller can tell a refusal from a bug, and a raising agent's own exception propagates UNCHANGED
    because catching it would be a fallback and a fallback here is a fabricated estimate.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Give `LiveSizingAgent.size` a return value instead of its raise (for example
      `return {"low": 1, "high": 2}`) at .veldo/sizing_pass.py, and the fail-loud row
      "WARP-1403 AC1: THE REFERENCE AGENT RAISES AND SAYS WHY" must go red together with the
      unwired-composition half of it, while the injected-agent positive control stays GREEN - which
      is what attributes the red to the seam rather than to the composition.
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
    falsified_by: >
      Neuter the cost-provenance membership check in `validate_judgement` at
      .veldo/sizing_pass.py - `if "self_cost_basis" in rec and rec["self_cost_basis"] not in bases:`
      rewritten to `if False:` - and the row "WARP-1403 AC2: THE PASS'S OWN COST IS REQUIRED, AND
      ITS PROVENANCE COMES FROM THE SPEND RECORDER'S TABLE" must go red, because its accepted set is
      a SET EQUALITY against spend.BASES and a validator that accepts everything fails it from the
      other direction.
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
    falsified_by: >
      Drop the content hash from a measured footprint entry in `code_facts` at
      .veldo/sizing_pass.py (delete `ent["content"]` from the assignment, leaving bytes and lines),
      so the digest binds the code's INVENTORY again, and the row "WARP-1403 AC3: THE DIGEST BINDS
      THE CODE'S CONTENT, NOT AN INVENTORY OF IT" must go red - it rewrites a footprint file to
      different bytes of the same length and requires the stale judgement to be refused.
    text: >
      THE BRIEF IS MECHANICAL AND DETERMINISTIC, AND A DIGEST BINDS THE JUDGEMENT TO IT. The brief
      is derived with no clock, no network, no subprocess and no model call, from the spec's own
      features through W1's ONE feature reader, the code its footprint resolves to through the ONE
      glob compiler, the ledger, and the structural prior W2 computed; two calls give identical
      bytes and an identical digest. The digest is sensitive to all four things it claims to bind
      (spec, code, ledger, prior), with the code and ledger cases attributed EXACTLY by differing
      in that block alone, and the code case asserted over BOTH halves of its domain: a file that
      appears, and a file rewritten to different bytes of the SAME length and line count, because
      what binds is a sha256 of each matched file's bytes and not an inventory of paths and sizes. A
      judgement whose digest is stale or whose spec is another spec is REFUSED rather than reused,
      and that refusal is driven on the composition path that COMMITS a record and not only on the
      rule underneath it: the brief is a required argument of the layer builder, so no path from a
      judgement to a record can omit the binding. A footprint entry that leaves the repository is
      refused before anything is read; an existing path carries measured bytes, lines and a content
      hash while an absent one carries NO SIZE AT ALL; a glob that matches nothing is counted apart
      from a literal that does not exist.
  - id: AC4
    falsified_by: >
      Truncate the token total per event again in `ledger_state` at .veldo/sizing_pass.py
      (`sum(int(e["tokens"]) for e in with_tokens)`), and the row "WARP-1403 AC4 THE TOKEN TOTAL IS
      NOT TRUNCATED, AND A FIGURE THAT IS NOT A WHOLE TOKEN COUNT IS NAMED" must go red over the
      ledger carrying 0.4 and 0.6 tokens, because 1.0 recorded would report as 0 beside a flag
      saying there IS an anchor.
    text: >
      HONEST ABOUT THE LEDGER AND ABOUT ITSELF. Measured over this repository: the event log
      carries over a thousand events and the ledger report AGREES with an independent recount of
      it, with the arm chosen by what that recount found - while nothing carries a spend field the
      brief reports anchor_available no and OMITS the numeric anchor keys rather than reporting
      zero, and once spend IS recorded the numeric keys must EQUAL the recount. What is never
      asserted is that the live log carries no spend: that is today's emptiness and not an
      invariant, and pinning it made the first sanctioned use of spend.py red the gate (see the
      third round in the notes below) - paired
      with the seeded control where the same function reports the recorded total, which is what
      makes the standdown a measurement instead of a hardcoded answer. Each numeric anchor is
      gated on ITS OWN field and never on spend having been recorded in some other one, so a
      ledger carrying cost_usd or human_minutes and no tokens reports token_anchor_available no
      and omits the token keys, asserted as a THIRD control over the part of the domain where
      carrying spend and carrying tokens stop coinciding. The total itself is the figures AS
      RECORDED and never truncated, with the count of figures that are not whole token counts
      reported beside it, because a floor applied per event turns 1.0 recorded tokens into the zero
      this block exists to refuse to print - and the suite's independent recount sums by a
      different expression, so the two sides of that equality cannot move together. An agent's judgement never
      makes an estimate calibrated: agent_judgement is not one of W2's grounded bases, the record
      reads uncalibrated, and moving that basis into the grounded set makes this module REFUSE to
      write the layer at all (driven, not asserted). The pass's own token cost is recorded through
      spend.py's ONE writer against the spec it sized, carrying the digest and the model; the
      layer states the cost as a share of its own lower bound against a declared ceiling, and
      crossing it is REPORTED and never refused. The layer widens the committed range or leaves it
      alone, never narrows it, and the prior shown in the brief is asserted EQUAL to the prior the
      record commits rather than assumed to be the same number.
  - id: AC5
    falsified_by: >
      Make `check_dir` create the directory it reports on at .veldo/sizing_pass.py (replace the
      `if not d.is_dir(): return 0, 0` stand-down with `d.mkdir(parents=True, exist_ok=True)`), and
      the row "WARP-1403 AC5: WITH NO JUDGEMENTS PRESENT EVERY READER STANDS DOWN SILENTLY AND
      CREATES NOTHING" must go red on its closing clause, which requires the directory to be absent
      afterwards.
    text: >
      OPTIONAL, ADOPTION SAFE, AND NEVER A BLOCKER - the AC that matters most, because it is
      PLAN-0014's C3 and NG1. With no judgements present every reader stands down silently,
      creating nothing, and a record with no sizing layer is complete. A present-but-broken
      judgement is named rather than dropped, and a record filed under the wrong name is refused.
      NO GATE STAGE LOADS THIS MODULE, asserted over the gate's OWN stages - the organs validate.py
      loads plus the stage scripts scripts/verify.sh names - and over LOADS rather than mentions,
      because a gate stage loading it is a defect NG1 forbids while the set of FILES that load it is
      a population an advisory reader and /veldo:init's lay-down legitimately join; that population
      is REPORTED and never required empty. And nothing the publisher SHIPS may load something it
      withholds: no file this module executes is held back while the module itself is shipped. And
      the load-bearing measurement: a spec with NO estimate, with a
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
it since. That is a DATED OBSERVATION and the suite treats it as one: the total grows by one line
per gate run, so the assertion is bound to the log's own length rather than to this figure, and what
it pins is the AGREEMENT between the report and an independent recount of the same log. The zero is
one BRANCH of that leg and is never itself asserted, because the day somebody records real spend the
observation stops being true while the module stays correct.

Two consequences travel with every number this item produces:

- While nothing is recorded the brief reports `anchor_available: no` and OMITS its numeric anchor
  fields rather than reporting them as zero. A zero because nothing was spent and a zero because
  nothing was ever recorded are different facts, and an agent handed the second as a measurement
  calibrates against nothing while feeling informed. The seeded control beside that assertion is
  what makes the standdown a measurement rather than a hardcoded answer, and the recount beside it
  is what lets the same leg keep its teeth once the ledger is no longer empty.
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

THE TEETH AS DELIVERED, over the 37 assertions this fragment carried then. It carries 40 now; the
remediation note below records what changed and why. 30 deliberate mutations of the module were
applied one at a time, each restored before
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

## Remediation after independent review, 2026-08-11

An independent review applied 22 mutations of its own and four left all 37 assertions green. Three
of those four were LABELS rather than measurements, and one honest-omission property was asserted
only over the convenient half of its domain. What changed, and the mutation that now reds each of
them (every one applied to a scratch copy under /tmp, diffed to confirm it applied, and the suite
run after it):

- **The ledger's omission is now per FIELD, not per ledger** (`ledger_state`). `spend.validate`
  accepts a record carrying any ONE of `tokens`, `cost_usd`, `human_minutes` and its writer defaults
  `tokens` to None, so a ledger can hold real recorded cost and no token history. The old gate was
  "any spend field present", which reported `tokens_recorded: 0` beside `anchor_available: yes` -
  the zero-that-reads-like-a-measurement this AC exists to prevent, and the one shape the seeded
  control never used, since both its events carried tokens. The token keys are now omitted unless an
  event carries a numeric `tokens`, `token_spend_events` states the basis of the total, and
  `token_anchor_available` answers for the keys it licenses. A third control asserts it over a
  ledger carrying cost_usd and human_minutes only. Driven: gating the token keys on `carrying`
  again, 1 RED (the new per-field control); pinning `token_anchor_available` to yes, 2 RED (it and
  the real-log assertion).
- **All three declared vocabulary refusals are driven.** `layer_vocabulary` says it fails closed by
  name on three things; only the calibrated-basis one was driven, so `if LAYER_ID not in E.LAYERS:`
  and `if LAYER_BASIS not in E.BASES:` could both be deleted with every assertion green. The suite
  now removes each name from W2's table and watches the refusal, restoring it in a finally. Driven:
  each check neutered to `if False:`, 1 RED each.
- **The unit refusal is driven instead of described.** The old assertion observed that
  `E.UNITS` names exactly one unit, which is a fact about estimate.py that is true whether this
  module checks it or not, under a label claiming the brief REFUSES on two. The suite now makes that
  vocabulary declare two units and asserts `brief()` refuses naming the count. Driven:
  `if len(units) != 1:` neutered to `if False:`, 1 RED.
- **The reach claim is a set equality over parsed imports**, not four forbidden greps. The top-level
  name of every import statement in the module (ast.walk, so function-local ones count) is asserted
  EQUAL to a declared allowlist. Driven: `from subprocess import run as _run`, 1 RED;
  `__import__("socket")`, 1 RED. Both were invisible to the old grep. THIS BULLET'S FIRST REVISION
  ALSO CLAIMED the residual was closed by naming the two dynamic spellings an import set cannot see,
  which was the same defect in other clothes and is corrected in the round below.
- **The naming sweep covers four domains**, `.veldo/*.py`, `engine/.veldo/*.py`, `scripts/*.py` and
  `scripts/*.sh`, guarded on each glob being non-empty and on the domain provably containing both
  engine homes and the gate script. The spellings are path-shaped and import-shaped rather than the
  bare stem, because the bare stem is also the LAYER ID W2 declares in both engine homes. A release
  disposition list may name the path; nothing may import or execute it. Driven with three throwaway
  probes, each 1 RED where the old sweep was green: `.veldo/zz_probe_a.py` containing
  `import sizing_pass`, `engine/.veldo/zz_probe_c.py` and `scripts/zz_probe_d.py` naming the path.
  A fourth probe adding this module to publish.py's hold-back list stays GREEN at 40, so the sweep
  is not a trap for the publish.py fix the bullet below still needs.

## Second round, same day: the two defects the fix itself introduced

A fresh review of the round above found the same defect class inside it, in the lines that round
wrote. Both are closed here in the suite; `.veldo/sizing_pass.py` and its engine twin are UNTOUCHED
by this round and remain byte-identical. Each mutation below was applied to BOTH twins in a scratch
copy under /tmp, unified-diffed to confirm it applied, and the suite run after it:

- **`token_spend_events` had no fixture that could distinguish it from the any-field count.** Its
  declared job is to be the BASIS of the token total, but every seeded record in the file carried
  tokens, so `len(with_tokens)` and `len(carrying)` were the same number in all three ledgers and a
  total could be reported over the wrong set with nothing red. MEASURED: rewriting the key as
  `out["token_spend_events"] = len(carrying)` left the suite at 40 passed, 0 failed. The fixture the
  claim needs is a MIXED ledger, one record with tokens beside two whose spend was recorded as
  `cost_usd` and as `human_minutes`, which is the only shape where the basis and the any-field count
  diverge and is what the sanctioned writer produces, since `spend.record` defaults `tokens` to None
  per record and not per ledger. Over it `token_spend_events` is 1 while `spend_events` is 3, and
  that same rewrite is 1 RED. A sum without a checkable denominator is not a measurement.
- **The reach claim named its own residual as exactly two spellings.** A universal claim over a
  hand-picked pair is the defect it was written to fix. MEASURED against that revision, each of
  these left the suite at 40 passed, 0 failed: `os.popen("true")` (neither `os.system(` nor
  `Popen(`), `eval("1 + 1")`, `getattr(os, "sys" + "tem")("true")`, and this module's OWN loader
  idiom aimed outside the tree, `_mod("../../etc/veldo_probe.py", ...)`. The domain is now CLOSED
  rather than sampled. Foreign code can enter a module four ways and each is an equality over the
  parsed source: an import statement (the allowlist above); a bare-name callee the module does not
  define (a declared list of builtins plus `Path` and `rx`, so `eval`, `exec`, `__import__` and
  `compile` are refused by the equality); a dotted callee rooted at an imported name (exactly seven,
  so `os.popen`, `os.system`, `os.execv` and `importlib.import_module` are refused the same way);
  and CALLING WHAT A CALL RETURNED, which is NOT empty here and is not claimed to be, since
  `sizing_pass.py:532` calls W2's bounds rule as `_bounds_rule()(rec, ...)`, so that shape is pinned
  to that one producer, a function this module defines. Driven: 1 RED each.
- **And the door those equalities leave open, which is the module's own loader.** An allowlisted
  `spec_from_file_location` can execute any file on the machine, so the call is pinned to what it is
  aimed at: all three module-executing calls occur exactly once and all three inside `_mod`, `_mod`
  builds its path as `ROOT / rel` asserted against that parsed shape rather than a substring, every
  caller passes a string literal, and the set of those literals is exactly `validate.py`,
  `estimate.py`, `toe_corpus.py`, `arch.py`, `spend.py` and `events.py`, each resolving to a real
  file under the repository root. Driven: the outside-`_mod` absolute-path loader, 1 RED; a `_mod`
  target reached through a variable instead of a literal, 1 RED.

The fragment reports 42 passed, 0 failed. `scripts/suites/manifest.json` still records the delivered
figure of 37 in its `requires_note`; that file is outside this item's footprint and the note is
stale by exactly the five assertions these two rounds added.

The probe from the round above was re-run against these two assertions: adding
`engine/.veldo/sizing_pass.py` and `engine/.veldo/examples/sizing-judgement-example.yaml` to
`scripts/publish.py`'s EXCLUDE in a scratch copy leaves the fragment at 42 passed, 0 failed, so
nothing added here traps the publish.py fix the bullet below still needs. That bullet is still OPEN:
the two EXCLUDE lines are edits to a file outside this item's footprint, and the invariant worth
asserting, that a SHIPPING engine module never loads a HELD-BACK one, is RED today and would turn
the gate red if it were asserted before those lines land. It is named here rather than papered over.

## Third round, same day: the real-log leg was a landmine, not a measurement

The AC4 leg labelled MEASURED OVER THE REAL LOG ran `ledger_state` over the live event log and
asserted `spend_events == 0` with every numeric anchor key absent. That is not a property of this
module. It is the observation that nobody had called `spend.py` yet, promoted to a required
invariant, so the gate was green exactly as long as the estimation layer went unused and would
redden the moment somebody used it - and the first person to use it is the one who asked for the
feature. A gate that breaks on first legitimate use is worse than a missing check, because it
teaches its owner that the gate is noise.

MEASURED, in a `cp -a` scratch copy under /tmp, with the sanctioned writer doing exactly the thing
the estimation layer exists to do:

    python3 .veldo/spend.py record --spec WARP-0100 --basis harness_reported --tokens 750000

Before: `16_warp_1403_sizing_pass 42 passed`, 0 failed. After that one record: **41 passed, 1
FAILED**, and the assertion that fired was that leg.

WHAT IT ASSERTS NOW, and the shape is the point: the live log is RECOUNTED in the suite, by a second
spelling of "numeric" over W1's own declared `SPEND_FIELDS`, so the two sides of every equality
cannot move together under a mutation. Unconditional over ANY log: `events` is one enumeration of
the list, `spend_events` equals the recount, the spend events are a subset of the events, the token
events are a subset of the spend events, each flag equals what the recount says it should, and each
numeric key is present EXACTLY when the flag licensing it reads yes. Then ONE arm, chosen by what the
recount just found: nothing recorded gives the honest stand-down with the numeric keys ABSENT rather
than zero; spend recorded requires `specs_with_spend`, `token_spend_events` and `tokens_recorded` to
EQUAL the recount, with the token keys still gated on tokens alone so a cost-only ledger omits them.
The brief's own ledger block is asserted equal to that report over the same real events. The teeth
are unchanged in the empty state and stronger in the recorded one, where the keys must match a number
instead of merely being missing.

Driven, each mutation applied to BOTH twins in the scratch copy WITH that spend record present,
unified-diffed to confirm it applied, and the suite run after it (the modules in this tree are
UNTOUCHED by this round and stay byte-identical):

- `"anchor_available": E.NO` hardcoded, the module claiming the stand-down while data exists: **4
  RED**, the real-log leg plus the three seeded controls.
- `out["tokens_recorded"] = 0` with the key still present, the zero that reads like a measurement:
  **4 RED**, the real-log leg, two seeded controls and the AC3 reach equality, which sees the
  vanished `sum(...)` call.
- and the attribution probe, `if len(evs) > 900: return {... "spend_events": 0, "anchor_available":
  E.NO ...}`, which is the old finding hardcoded for this repository's own log and nothing else:
  **exactly 1 RED, the real-log leg alone**. That is the isolated proof, since a mutation of a
  function three fixtures also call cannot attribute itself to this leg.

With the module restored and the spend record still in the log: **42 passed, 0 failed**. The feature
can be used and the leg still bites.

AC4's own text sanctioned the defect - it read "the event log carries over a thousand events and NOT
ONE with a spend field" as a thing the suite proves - so the criterion is part of this fix and was
narrowed to the truth: the report agrees with a recount, the arm follows the recount, and the
emptiness is never asserted. The dated observation itself is kept, as an observation, in the measured
finding above.

## Fourth round, 2026-08-13: the independent review's two blockers, and what they were really about

The independent review this item had never had returned FAIL on two blockers and five majors, and its
verdict is at `proof/WARP-1403/verdict-l2.json`. **Both blockers were in the mechanism this spec calls
the item's integrity, and both reproduced exactly as reported before anything was changed.** The
module is CHANGED by this round, so the twins were re-synced and every mutation below was applied to
both.

- **THE BINDING WAS ASSERTED OFF THE PATH THAT COMMITS A RECORD** (blocker). `size()` is the only
  path that produces a committed estimate, and every row that exercised the digest binding called
  `validate_judgement` or `_binding_problems` DIRECTLY. Reproduced: `layer_from(judgement, b)` ->
  `layer_from(judgement)` inside `size()` left the fragment at **42 passed, 0 failed**, and with it a
  judgement carrying the digest of a DIFFERENT brief composed into a valid committed record - range
  (50000, 1200000), `validate_record` clean - while the layer silently lost all eight `brief_*`
  inputs. The rule had teeth; its one call site had none. FIXED in the module rather than only in the
  suite: `layer_from`'s brief is a REQUIRED argument, the binding rule runs unconditionally there by
  delegation to `_binding_problems` (one spelling, never a second copy), and the eight `brief_*`
  inputs are recorded unconditionally. Three rows pin it: the commit path refuses a judgement bound
  to another brief and commits nothing, the committed layer's `brief_*` inputs EQUAL the brief's own
  values, and a layer cannot be built with no brief, with a non-brief mapping, or with a brief-shaped
  mapping whose blocks are missing. Driven: the same mutation spelled `layer_from(judgement, None)`
  is 11 RED including both new rows; the reviewer's exact spelling is now a TypeError that reds the
  composition row rather than passing.
- **THE DIGEST BOUND THE CODE'S INVENTORY, NOT THE CODE** (blocker). `code_facts` recorded paths, a
  byte count and a line count; `_file_facts` already read the bytes and threw them away. Reproduced:
  rewriting a footprint file from `return cents >= 0` to `return cents <= 0` - 41 bytes and 2 lines
  both ways - left the brief dict and its digest BYTE-IDENTICAL, the stale judgement validated clean
  and `layer_from` built a layer from it. The suite could not see it because its attribution fixture
  only ever moved a file from ABSENT to EXISTING, which is the half of the domain where a size change
  is guaranteed. FIXED with a sha256 of each matched file's PATH and BYTES per entry, hashed in
  resolved order, so a same-length edit and a rename both move the digest; an entry that matched
  nothing still carries no `content` at all, exactly as it carries no size. Driven: dropping the key
  is 2 RED, and hashing the SIZE instead of the bytes - the fix wearing its own clothes - is 1 RED on
  the new row.
- **THE AC5 SWEEP REQUIRED A LIVE POPULATION TO BE EMPTY** (major, seventh appearance of the family
  here). Reproduced both of the reviewer's probes: adding `.veldo/sizing_pass.py` to
  `init_scaffold.py`'s lay-down list, which PLAN-0014 W10 requires verbatim, and a twelve-line
  advisory reader, each took the fragment to 41 passed, 1 failed. FIXED per PLAN-0018 finding 63 and
  VELDO-DEC-0002 by changing the DOMAIN and not the comparison: the subject is the GATE'S OWN STAGES,
  derived from `validate.py`'s organ loads plus the stage scripts `verify.sh` names, asserted over
  LOADS via the AST rather than over mentions, with the population reported in the row's own text.
  Driven: both legitimate uses are GREEN now, and a load of this module added to `validate.py` - in
  the `ROOT / ".veldo" / "x.py"` spelling a direct-Constant detector was measured blind to in
  VELDO-0003 - is 1 RED on the named row. The detector's reach is driven additively: it fires on both
  spellings, stays silent on a load of another organ AND on W2 declaring the layer id `sizing_pass`
  in its vocabulary, and NAMES a source it cannot read or parse.
- **THE HOLD-BACK** (major) was ALREADY CLOSED at 770bd46 by ledger finding 73, three days after this
  item shipped, and the out-of-scope bullet above now records what the tree says. Re-measured by
  producing the tree: no composed pack carries this module or names it. What this round adds is the
  invariant the old bullet said was worth asserting: no file this module executes may be withheld
  while the module itself is shipped, evaluated against publish.py's own selection and against this
  module's own proven-complete `_mod` target set. Driven both ways, because a row that reddened on
  the owner's own disposition change would be a trap rather than a check: removing the module's
  EXCLUDE line is 1 RED and `sizing_pass.py vocab` in the produced pack exits 1 on
  FileNotFoundError; removing BOTH its line and `estimate.py`'s is GREEN and that same command exits
  0.
- **tokens_recorded WAS TRUNCATED PER EVENT** (major). `spend.validate` accepts a fractional figure
  through the sanctioned writer's own API, and two events carrying 0.4 and 0.6 tokens reported
  `tokens_recorded: 0` beside `token_anchor_available: yes` - AC4's own named defect. The third
  round's recount was a second spelling of "numeric" and the SAME spelling of `int()`, so both sides
  moved together. FIXED: the total is the figures as recorded, `token_figures_non_integer` counts the
  figures that are not whole token counts (gated on the same field as the keys around it), and the
  suite's recount is an accumulator rather than a comprehension applying the same floor. `int` is
  deliberately absent from the allowed bare-call set now, so re-introducing the truncation reds the
  reach equality as well as the new fractional row. Driven: 2 RED for the truncation, 1 RED for
  keeping the honest total while dropping the count.
- **THE BRIEF WAS AN OPTIONAL ARGUMENT** (major) is the same fix as the first blocker: it is what made
  that one invisible.
- **THE ITEM DECLARED NO falsified_by ON ANY CRITERION** (major), so the rule written because of this
  layer stood the layer's own item down. FIXED: the spec declares `behavior_bearing: true` with an
  observability block, and every criterion carries a `falsified_by` naming ONE change and the row it
  must redden - each one DRIVEN in this round rather than asserted. Driven: with
  `behavior_bearing` removed the corpus count drops from 46 declaring specs to 45 and this spec
  stands down again; with it present and AC3's `falsified_by` deleted the validator REFUSES by name
  and `validate.py spec` exits 1.

AND ONE DEFECT THIS ROUND'S OWN DRIVING FOUND IN THIS ROUND'S OWN WORK, recorded because it is the
same class: the first version of the content row read `ent["content"]` by subscript, so AC3's declared
falsification raised KeyError out of the fragment and produced ZERO verdict lines - the row it names
was never seen failing. That is PLAN-0018 finding 67's shape and this file's own header already warned
about it. The reads are captured as data now and the mutation reds the named row with nothing lost.

The fragment reports **49 passed, 0 failed** (42 before this round), and `bash scripts/verify.sh` is
GREEN. The full driving log, including the git diff proving each mutation landed and the additive
controls, is the round's own artifact rather than a claim here.

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
- The capability manifest entry. `.veldo/capabilities.yaml` is integrated separately.
- CLOSED 2026-08-12 AT 770bd46, and recorded here because two revisions of this bullet were wrong
  about the tree. It said `engine/.veldo/sizing_pass.py` SHIPS while `engine/.veldo/estimate.py` is
  held back, so every entry point here raised FileNotFoundError on `vocab` in a public tree while
  `check` still exited 0 - measured, not reasoned about, and confirmed independently by three
  reviewers (ledger finding 73). `scripts/publish.py` now withholds `sizing_pass.py`,
  `toe_analogy.py`, `toe_budget.py` and `toe_reconcile.py` beside `estimate.py`, and the hold-back is
  complete. RE-MEASURED 2026-08-13 by producing the tree rather than by reading the manifest:
  `python3 scripts/publish.py <dest>` gives 416 files and 7 composed packs, `engine/.veldo` in the
  produced tree carries neither module, and nothing in that tree so much as names `sizing_pass`. The
  invariant the earlier bullet said was worth asserting is asserted now, in this item's own suite and
  against publish.py's own selection: no file this module executes may be withheld while the module
  itself is shipped. The disposition is REPORTED rather than pinned, because shipping or holding this
  layer is its owner's decision while shipping HALF of it is nobody's.
- STILL OPEN, AND IT IS ONE LINE IN A FILE THIS ITEM MAY NOT EDIT:
  `engine/.veldo/examples/sizing-judgement-example.yaml` still ships, while the module that validates
  that shape does not. Nothing loads it and nothing breaks, so this is a documented shape with no
  reader rather than a broken command; it is named here rather than papered over, and the fix is one
  EXCLUDE line in `scripts/publish.py` whenever that file is next opened.
