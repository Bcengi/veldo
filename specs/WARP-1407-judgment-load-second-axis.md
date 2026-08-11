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
acceptance_criteria:
  - id: AC1
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
    text: >
      AN UNRECORDED AXIS IS "NOT RECORDED", NEVER A ZERO, AND THIS IS THE AC THAT MATTERS MOST.
      `coverage()` reports minutes_known, tokens_known, pair_known, their percentages, and a blunt
      `usable_as_second_axis`; `classify()` REFUSES to label a record whose axis was never recorded
      and returns unknown naming which axis is missing; and the rendered report prints the words
      where a figure would go. **Measured over this repository: 174 shipped specs, 0 percent
      judgment-minutes coverage, 0 percent tokens coverage, 0 of 174 pairs known,
      usable_as_second_axis False.** Four shape labels exist and one of them -
      cheap_to_build_expensive_to_approve - is the class no single-axis unit could ever show; each is
      drawn from this repository's own medians over the both-axes population and never from an
      absolute threshold, and below a declared minimum population NOTHING is labelled. A selftest
      requires that a log carrying no figure at all still produces every row, reports zero known
      rather than zero cost, and labels nothing.
  - id: AC3
    text: >
      EPISODES ARE COUNTED AND ARE NEVER CONVERTED INTO MINUTES. The occasions a human had to judge -
      review requests, recorded verdicts, recorded approvals - ARE recorded here today (measured: 167
      episodes across 141 of 174 shipped specs, 81 percent coverage), so they are counted from the
      same one kind map and reported beside the pair. They are never scaled into a minute figure: a
      minutes-per-review coefficient would be an invention, and this plan's NG6 forbids exactly that.
      A selftest requires that a spec with three review episodes and no recorded minutes keeps a zero
      judgment total with judgment_known False and a shape of unknown, with a spec carrying the same
      episode count AND recorded minutes as the positive control. The per-spec axis totals are
      asserted EQUAL to the corpus's own independent totals over the same events, with a non-zero
      figure among them so the equality cannot pass vacuously.
  - id: AC4
    text: >
      A MALFORMED FIGURE IS REFUSED BY NAME; AN UNATTRIBUTABLE ONE IS COUNTED, NOT DROPPED. A
      human_minutes or tokens value that is not a non-negative number raises JudgmentLoadError naming
      the field, the event type and the value, where the corpus's total-only reader silently skips
      it - the difference is deliberate, because a skipped figure leaves the axis marked recorded and
      smaller than it is. `check_log` reports the same problems through validate.fail (the one
      failure reporter) instead of raising, for a caller who wants the whole list, and both spellings
      consult ONE judge so they cannot disagree about what is malformed. A well-formed event naming
      neither spec nor correlation cannot be refused - the log is append-only, so that refusal would
      be unsatisfiable by construction - and is counted in `unattributed` and reported as a number. A
      selftest drives each malformed shape, the well-formed log as the negative control, and the
      unattributable event both with and without a spec id.
  - id: AC5
    text: >
      THE ONLY RECORDER PRODUCES A MIXED SIGNAL AND THE MODULE NAMES IT, AND THE DERIVATION WRITES
      NOTHING. `spend.py` records minutes on a `spec.shipped` event: one bulk figure for a whole
      change, which cannot say whether the time went into reviewing or approving. Those minutes count
      toward the judgment total, land in the `ship_bulk` kind, and leave `split_known` False, so no
      reader is handed an approval figure that was inferred from a total; the kind map is bound to
      `spend.SCHEMA_EVENT_TYPE` in the selftest so it cannot drift from the recorder it describes.
      The module has no writer at all: a selftest digests the tree it read before and after building
      and rendering the pair and requires it byte-identical, with a deliberate single-byte change
      proving the digest notices.
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
are in the log: review requests, recorded verdicts, recorded approvals. They are counted and shown
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
