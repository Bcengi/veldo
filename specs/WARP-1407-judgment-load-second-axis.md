---
schema: veldo.spec/v1
id: WARP-1407
title: The second axis of effort - human-judgment load beside tokens, and the measured finding that
  the judgment axis has a recorder and no data, so every shape it could report is honestly unknown
status: ready
risk: standard - a new derivation module that reads the corpus, the event log and the plan registry
  and writes nothing. No behaviour changes, no gate stage is added, nothing is enforced. It is not
  low because the number it produces is what a reader would use to decide whether a change was
  expensive, and a judgment axis that reported an unrecorded zero would price every approval-heavy
  change at nothing - the most expensive single mistake available to this item.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W7
depends_on: [WARP-1401, WARP-0733]
placement: [metrics]
footprint:
  - ".veldo/judgment_load.py"
  - "engine/.veldo/judgment_load.py"
  - "scripts/suites/15_warp_1407_judgment_load.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1407-judgment-load-second-axis.md"
  - "specs/index.md"
behavior_bearing: true
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Render the per-plan roll-up's two axis columns with `_num` instead of `_axis` at
      .veldo/judgment_load.py:673-675, which is what this module did until an independent review
      refuted AC2 on it, and the whole-line pin at
      scripts/suites/15_warp_1407_judgment_load.py:307 must go red because the plan line for the
      undeclared plan then reads "toe 0 tok (0 known)  judgment 0 min (0 known)" instead of the
      words, taking the log-carrying-no-figure plan line at :384 and the recorded-zero plan line at
      :468 with it. MEASURED 2026-08-13: 3 rows red, 81 passed, 0 failed.
    text: >
      THE PAIR IS ONE VALUE AND ONE RENDERER SHOWS IT. For every corpus record the derivation returns
      both axes together - tokens from the event envelope, judgment minutes from the same envelope,
      each with its own recorded flag - plus the judgment minutes split by the kind of judgment they
      paid for, the count of judgment episodes, and the approval surface the spec declared.
      `pair_line` is the ONE rendering of that value, and the report surface renders every row
      through it, so this module's report, a status line and the dashboard cannot show the same
      change three ways. The pair rolls up per plan as well as per spec, and a plan line carries its
      DENOMINATOR (the item count the plan declares, read through the one plan registry) so a
      partial roll-up cannot read as a complete one. A selftest drives all of it over seeded specs
      and events, with a spec that has no events at all as the negative control.
  - id: AC2
    falsified_by: >
      Derive `split_known` from the truthiness of the minute SUM again -
      `any(by_kind[k] for k in SPLIT_KINDS)` at .veldo/judgment_load.py:278 - so a verdict event
      carrying `human_minutes: 0` reads as a split nobody recorded, which inverts this criterion's own
      distinction inside its own second flag, and the recorded-zero row at
      scripts/suites/15_warp_1407_judgment_load.py:433 must go red, taking its rendered line and the
      row that classifies a recorded zero rather than leaving it unknown. MEASURED 2026-08-13: 3 rows
      red, 81 passed, 0 failed. The same criterion is reachable a second way (`minutes_recorded` read
      from the total rather than from the count of events carrying the field: 4 rows red).
    text: >
      AN UNRECORDED AXIS IS "NOT RECORDED", NEVER A ZERO, AND THIS IS THE AC THAT MATTERS MOST.
      `coverage()` reports minutes_known, tokens_known, pair_known, their percentages, and a blunt
      `usable_as_second_axis`; `classify()` REFUSES to label a record whose axis was never recorded
      and returns unknown naming which axis is missing; and the rendered report prints the words
      where a figure would go - on the PER-PLAN roll-up as well as the per-spec row, because the
      roll-up is a second rendering of the same pair and an axis with nothing recorded on it is not a
      plan that cost nothing. A zero that WAS recorded is a different fact and is reported as the
      figure it is: both honesty flags count the events that carried the field and neither reads the
      truthiness of a sum, so a verdict carrying `human_minutes: 0` is a split that was recorded. And
      the sentence that names the gap says only what it counted - the records in the report, never the
      whole log, since minutes can sit on an unattributable event or on a spec the corpus does not
      hold. **Measured over this repository: 174 shipped specs, 0 percent
      judgment-minutes coverage, 0 percent tokens coverage, 0 of 174 pairs known,
      usable_as_second_axis False.** Four shape labels exist and one of them -
      cheap_to_build_expensive_to_approve - is the class no single-axis unit could ever show; each is
      drawn from this repository's own medians over the both-axes population and never from an
      absolute threshold, and below a declared minimum population NOTHING is labelled. A selftest
      requires that a log carrying no figure at all still produces every row, reports zero known
      rather than zero cost, and labels nothing.
  - id: AC3
    falsified_by: >
      Delete the correlation half of the one attribution selector at .veldo/judgment_load.py:170-171,
      leaving `return event.get("spec_id") == spec_id`, so a figure attributed only by correlation_id
      is invisible to this module while toe_corpus.spend_for still joins on it, and the
      corpus-equality row at scripts/suites/15_warp_1407_judgment_load.py:566 must go red because the
      two enumerations this criterion promises to keep equal then report 0 against 25 minutes.
      MEASURED 2026-08-13: 1 row red, 83 passed, 0 failed.
    text: >
      EPISODES ARE COUNTED AND ARE NEVER CONVERTED INTO MINUTES. The occasions a human had to judge -
      review requests, recorded verdicts, recorded approvals - ARE recorded here today (measured
      2026-08-10: 167 episodes across 141 of 174 shipped specs, 81 percent coverage; the episode count
      is a LIVE figure that rises as the loop runs and no check pins it, so it is dated here rather
      than read as a claim about today - it was 170 on 2026-08-13), so they are counted from the
      same one kind map and reported beside the pair. They are never scaled into a minute figure: a
      minutes-per-review coefficient would be an invention, and this plan's NG6 forbids exactly that.
      A selftest requires that a spec with three review episodes and no recorded minutes keeps a zero
      judgment total with judgment_known False and a shape of unknown, with a spec carrying the same
      episode count AND recorded minutes as the positive control. The per-spec axis totals are
      asserted EQUAL to the corpus's own independent totals over the same events, with a non-zero
      figure among them so the equality cannot pass vacuously.
  - id: AC4
    falsified_by: >
      Disable the finite clause of the ONE judge at .veldo/judgment_load.py:206 (`if False:`), so NaN
      and infinity pass as well-formed figures the way they did before the review, and the NaN and
      infinity refusal rows at scripts/suites/15_warp_1407_judgment_load.py:627 must go red, taking
      the check_log count, the end-to-end CLI row at :947 where `report` then prints "judgment nan
      min" at 100.0 percent coverage, and the live row that requires the judge to agree with an
      independent reading of what a well-formed figure is. MEASURED 2026-08-13: 5 rows red, 79 passed, 0 failed.
    text: >
      A MALFORMED FIGURE IS REFUSED BY NAME; AN UNATTRIBUTABLE ONE IS COUNTED, NOT DROPPED. A
      human_minutes or tokens value that is not a non-negative FINITE number raises JudgmentLoadError
      naming the field, the event type and the value. FINITE is part of the property and not a detail:
      NaN and infinity both fail a sign test rather than being caught by one, `json.loads` accepts the
      bare literals so both arrive from a log file, and a NaN that reaches the derivation moves the
      median every other record is labelled against. Where the corpus's total-only reader silently skips
      it - the difference is deliberate, because a skipped figure leaves the axis marked recorded and
      smaller than it is. `check_log` reports the same problems through validate.fail (the one
      failure reporter) instead of raising, for a caller who wants the whole list, and both spellings
      consult ONE judge so they cannot disagree about what is malformed. A well-formed event naming
      neither spec nor correlation cannot be refused - the log is append-only, so that refusal would
      be unsatisfiable by construction - and is counted in `unattributed` and reported as a number. A
      selftest drives each malformed shape, the well-formed log as the negative control, and the
      unattributable event both with and without a spec id. A corpus record naming NO spec id is
      refused by name for the same reason: with no id the one selector matches every event that names
      no spec, and a phantom row would collect the unattributable figures a second time as if they
      belonged to somebody. And because the derivation only reads figures for specs the corpus HOLDS
      while `check` judges the whole log, the report states as a number how many figures it did not
      read, so a reader who runs one command is never left to assume it covered what the other does.
  - id: AC5
    falsified_by: >
      Replace the guarded organ loads in `_repo_report` at .veldo/judgment_load.py:721-722 with bare
      `_load` calls, so a tree that carries this module without the corpus organ dies on a raw
      FileNotFoundError instead of naming the absent organ, and the corpus-organ leg at
      scripts/suites/15_warp_1407_judgment_load.py:902 must go red together with the log-organ leg at
      :915, both of which build a real tree, delete one organ and run the CLI. MEASURED 2026-08-13: 2
      rows red, 82 passed, 0 failed.
    text: >
      THE ONLY RECORDER PRODUCES A MIXED SIGNAL AND THE MODULE NAMES IT, AND THE DERIVATION WRITES
      NOTHING. `spend.py` records minutes on a `spec.shipped` event: one bulk figure for a whole
      change, which cannot say whether the time went into reviewing or approving. Those minutes count
      toward the judgment total, land in the `ship_bulk` kind, and leave `split_known` False, so no
      reader is handed an approval figure that was inferred from a total; the kind map is bound to
      `spend.SCHEMA_EVENT_TYPE` in the selftest so it cannot drift from the recorder it describes.
      The module has no writer at all: a selftest digests the tree it read before and after building
      and rendering the pair and requires it byte-identical, with a deliberate single-byte change
      proving the digest notices. AND IT NAMES AN ABSENT ORGAN INSTEAD OF DYING: `/veldo:init` lays
      down neither this module nor the corpus organ it derives from, so in a tree carrying only some of
      them the report says which organ is missing and which half of the answer went with it, prints no
      figure it could not measure, and exits 0; `check` refuses rather than reporting a clean log it
      never opened. A selftest builds a tree, DELETES one organ from it and runs the CLI, because a
      guard read out of the source is a claim about the text rather than about the run.
required_evidence: [unit]
rollback: >
  Delete the module, its engine copy and its selftest fragment, and remove the fragment from
  scripts/suites/manifest.json (regenerating scripts/suites/requires.json). Nothing reads it, no
  gate stage runs it, it declares no capability and it writes no state.
---

## Outcome

PLAN-0014 measures effort in the machine's own unit. Its O4 says effort is a PAIR: tokens beside
human-judgment load, so that cheap-to-build but expensive-to-approve work becomes visible for the
first time. This is the second axis and the pair surface.

## Why the pair, and not a better single number

A single-axis unit cannot tell apart a change that cost the machine 400k tokens and nobody's
attention from a four-line change that took three review rounds and an owner approval. **The second
one is the expensive one, and every legacy unit scored it as trivial** - story points, ideal days and
t-shirt sizes all measured authoring effort, which is the thing that decoupled from the work when the
agent started writing the code. The pair is what makes the approval-heavy class visible, and the
ratio between its two axes is the only place that class has ever shown up as a number.

## The finding, which travels with every figure this produces

**The judgment axis has a recorder and no data.** Measured over this repository's own log at the time
of writing: every event in it, and not one carrying `human_minutes` or `tokens`. WARP-1401 measured
that gap for spend and named the architectural reason - a token count is not knowable from inside a
repository - and WARP-0733 then built the recorder, so `spend.py record --human-minutes` EXISTS. What
has not happened is anybody calling it.

So over this repository the derivation reports: **174 shipped specs, 0 percent judgment-minutes
coverage, 0 percent tokens coverage, 0 pairs known, usable_as_second_axis False**, and every shape is
unknown with the missing axis named. That is the correct output, and it is the reason the honesty
rules are the load-bearing part of this item rather than the arithmetic:

- An unrecorded axis is never read as a low one. A change with three review rounds and no recorded
  minutes is unknown, not cheap. Getting this wrong would price every approval-heavy change at zero,
  which is worse than having no second axis at all.
- A median needs a population. Below the declared floor nothing is labelled, because a label drawn
  from two data points is noise presented as a finding.
- Minutes and episodes are different quantities and are never converted into one another. Episodes
  say how often a human was in the loop (recorded, 81 percent coverage today); only minutes say how
  long (0 percent).

## What is recorded today, and what it is good for

The judgment axis is not empty of everything. 167 judgment episodes across 141 of 174 shipped specs
were in the log at the time of writing (2026-08-10; 170 on 2026-08-13, because the count rises with
every review the loop records): review requests, recorded verdicts, recorded approvals. They are counted and shown
beside the pair, and they are enough to see which changes drew repeated human attention. They are not
enough to price it, and this module says so in the place where the price would be.

## The mixed signal in the one recorder

`spend.py` writes minutes on `spec.shipped`: one bulk figure for a whole change. That is the right
shape for a self-reported total and the wrong shape for a split - a bulk number cannot say whether
the time was review or approval. Those minutes are counted in the total and marked `ship_bulk`, and
`split_known` stays False. **A reader is never shown an approval figure that was inferred from a
total.** If the split ever matters more than the total, the fix is the recorder recording against the
event that earned the minutes, which is a change to WARP-0733's surface and not to this derivation.

## Where the pair is surfaced, and where it is not

The pair is rendered by ONE function (`pair_line`) and surfaced by this module's own report
(`judgment_load.py report`, with `--json` for a consumer), per spec and per plan. **The one renderer
is the seam, and that is deliberate:** the moment `status_server.py` or `dashboard.py` shows the pair
it is a one-line call to the same function, so the two surfaces cannot drift from this one or from
each other.

Those two call sites are NOT made here, for two reasons stated plainly rather than left implicit.
First, both modules are being edited by other items of this plan in parallel lanes, and a
cross-editing change in a parallel fleet is a merge collision, not a feature. Second, with 0 percent
coverage those surfaces would print "not recorded" on every row, which adds noise rather than
information; the call lands with the data. The exact line each surface needs is one
`judgment_load.pair_line(row)` per effort row.

## Out of scope

- The recorder. Making agents call `spend.py` is adoption, not code, and pretending otherwise would
  be the prose-instructions-do-not-execute failure. What this item guarantees is that the moment
  minutes exist the pair reports them, and that until then the gap is a number.
- Normalization. Raw tokens are shown here because raw tokens are what is recorded; the normalized
  display point is WARP-1406 and layers over this without touching a stored figure.
- Any weighting of the judgment axis. Scaling approval minutes above review minutes, or episodes into
  minutes, would be a coefficient nobody measured. The axis is minutes, split where the log says the
  split, and unknown where it does not.
- The engine capability entry. This item adds none, so nothing claims the module ships as a
  capability; recording it is the release act (W10). The line it would add is in the item's notes.
