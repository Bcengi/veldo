---
schema: veldo.spec/v1
id: WARP-1409
title: Cost-to-change per area - the per-area aggregation of the actuals corpus, with the join that
  produced every number named in the data, and the measured finding that 61 percent of the corpus can
  be attributed at all and none of it carries cost
status: ready
risk: standard - a new derivation module that reads the actuals corpus, the architecture contract, spec
  front matter and git, and writes nothing. No behaviour changes, no gate stage is added, nothing is
  enforced, and a repository that never calls it is byte-identically unaffected. It is not low because
  the number it produces is a PER-AREA COST that a reader will quote without asking how it was derived,
  and half of this corpus can only be attributed by git path rather than by a declaration: a map that
  presented the weak join as the strong one, or defaulted an unattributable change into an area, would
  be authoritative and wrong in the direction nobody checks
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W9
depends_on: [WARP-1401]
placement: [metrics]
footprint:
  - ".veldo/cost_to_change.py"
  - "engine/.veldo/cost_to_change.py"
  # toe_corpus.py is touched for ONE behaviour-preserving reason, declared rather than slipped in:
  # its git reader threw the PATHS away and returned only counts, and this item's stand-down needs
  # the paths. Spelling a second `git log --grep` out here would have been this repository's named
  # second-spelling defect in a new place, so the reader now returns commits and files and
  # files_touched counts what it returns. Its returned keys and values are unchanged, which the
  # selftest asserts against this repository's own history.
  - ".veldo/toe_corpus.py"
  - "engine/.veldo/toe_corpus.py"
  - "scripts/suites/15_warp_1409_cost_to_change_per_area.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1409-cost-to-change-per-area.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: The report names its own weaknesses in its own output. A stand-down prints one line saying
    WHICH condition stood it down (no contract, or no records). A report carrying git-path attribution
    prints a notice counting those records, and each area line prints how many of its changes were
    attributed that way. An area with no recorded spend prints tokens=None rather than 0, and the
    report prints a cost notice saying the corpus carries no spend at all.
  metrics: Every figure a reader might quote carries its own coverage beside it: records, attributed,
    unattributed, area_memberships, per-basis counts, cycles_known with cycles_coverage per area, and
    spend_known with spend_coverage per area, plus a blunt usable_as_cost_ground_truth boolean.
  error_taxonomy: One refusal, raised as ValueError from report() and reported through validate.fail
    from check_corpus(), with a message naming the record index, the spec and the offending field.
    Both surfaces read ONE problem enumeration (corpus_problems), so the reporting form and the
    refusing form cannot disagree about what is wrong.
acceptance_criteria:
  - id: AC1
    text: >
      THE DECLARATION IS THE JOIN, AND IT GOES THROUGH THE ONE RESOLVER. The corpus is aggregated per
      contract area on the spec's DECLARED placement and footprint, resolved by
      `arch.footprint_areas` - the same join key PLAN-0011's entropy map uses - so the two maps can
      never disagree about where a change landed, and a spec's front matter is read through the ONE
      parser (`validate.parse_yamlish`, injected) so placement arrives as a real list rather than a
      string. A placement naming an area the contract does not declare RESOLVES TO NOTHING and invents
      no home for the change. A selftest drives a declaring fixture spec and requires the declaration
      to WIN over the paths handed in beside it, and requires an unresolving placement to fall through
      rather than land.
  - id: AC2
    text: >
      THE STAND-DOWN IS BY GIT PATH AND THE REPORT SAYS SO IN THE DATA, WHICH IS THE WHOLE POINT OF
      THIS AC. A spec that declares no resolving placement is attributed through
      `arch.area_for_path` over the paths git says its change touched, and every record so attributed
      carries `basis: git_path` plus a label naming the weakness (derived from what happened rather
      than declared, blind to paths no area's includes glob enumerates, blind to commits that never
      named the spec); every area carries a per-basis count and an `attribution_basis` that reads
      `mixed` when both joins are present; and the report carries `git_path_attributed`, a `bases`
      entry and a notice counting the records. Asserted INSIDE the serialized report, because a
      comment and a docstring are invisible to the organ that consumes the JSON. NEGATIVE CONTROL:
      a placement-only report carries the git_path count at 0, no notice key, and the label's text
      nowhere, so the warning is not always-on decoration a reader learns to ignore.
  - id: AC3
    text: >
      NEVER A FABRICATED JOIN. A record with no resolving placement and no touched path inside a
      declared area is UNATTRIBUTED: counted in `unattributed.records`, named in
      `unattributed.specs`, and assigned to nothing. Nothing is spread, split, defaulted or
      rounded into an area. A cross-area change contributes its recorded cost to EACH area it
      touched and is never divided between them, because a split would be an invented weighting.
      A selftest asserts the partition as SET EQUALITY and DISJOINTNESS over one enumeration
      (every corpus spec is in at least one area or in the unattributed list, never both and never
      neither) rather than as two counts that could be wrong in the same direction, and requires
      `area_memberships` to equal the total of the per-area record counts.
  - id: AC4
    text: >
      A COST NOTHING RECORDED IS None, NEVER A CONFIDENT ZERO, and this is WARP-1401's finding
      carried forward rather than restated. An area whose records carry no recorded spend reports
      tokens, cost_usd and human_minutes as None with `cost_known` false, `cost_basis` unrecorded
      and `spend_coverage` 0.0, and the report carries a cost notice. Partial coverage is reported
      as partial: the sum covers the records that carried spend and `spend_known` of `records` says
      how many that was. POSITIVE CONTROL: a record carrying real spend produces the real numbers
      and flips `usable_as_cost_ground_truth`, so the None is the absence of data and not a
      hardcoded value. MEASURED OVER THIS REPOSITORY: 0 of 174 records carry any spend, so every
      cost field in the live map is None and the map is a CYCLES map today.
  - id: AC5
    text: >
      FAIL CLOSED AND BY NAME, THROUGH ONE ENUMERATION. A malformed actuals record is REFUSED with a
      message naming the record index, the spec and the offending field; a duplicate spec is refused
      because one record counted twice inflates every area it touches. `report()` raises ValueError
      and `check_corpus()` reports through the injected `validate.fail`, and both read the single
      `corpus_problems` enumeration, so the two surfaces cannot diverge. A selftest drives EIGHT
      planted-bad shapes (not a mapping, a foreign schema, no spec id, a negative gate-failure count,
      a non-numeric one, a spend block that is not a mapping, a non-boolean spend_recorded, cycles
      with no events_seen) and requires each message to name its field, with the assertion bound to
      the length of its own table so an emptied table reds instead of passing over nothing. POSITIVE
      CONTROL: the well-formed corpus raises nothing and reports zero problems.
  - id: AC6
    text: >
      ADOPTION SAFE, DETERMINISTIC, AND OUTSIDE THE GATE. No architecture contract stands the whole
      derivation down; no actuals records stands it down too; each returns a report in the SAME key
      shape a live report carries so a consumer never guesses whether a key is missing or genuinely
      empty, and neither raises. The report is byte-identical across repeated runs AND across a
      REVERSED corpus, so it is a function of the record set and not of harvest order; nothing reads
      a clock, mints an id or writes a file. NEGATIVE CONTROL: a populated corpus with a contract
      does NOT stand down, so the stand-downs are the missing inputs' doing. And no gate stage
      invokes this module: a selftest scans the nine files the gate actually runs and requires the
      module's name to be absent from all of them, with a positive control requiring the same scan
      to find `shape_gate.py` inside `scripts/verify.sh`.
  - id: AC7
    text: >
      THE CROSS-PLAN SEAM IS PROSE AND A SHARED RESOLVER, NEVER A DEPENDENCY EDGE (PLAN-0014 C6).
      The module's whole dependency surface is enumerated from its own source (every sibling arrives
      through one `_load` call with a literal path) and is exactly validate, toe_corpus, metrics and
      policy_check: `.veldo/entropy.py` is absent from it, and entropy.py names cost_to_change
      nowhere either, so PLAN-0011's organ may consume this report without either module importing
      the other. The ONE dependency taken (metrics reaching contracts, for arch) was already
      allow-listed in the architecture contract before this item existed, so nothing here adds an
      edge. The module also contains no spawn primitive at all, asserted with a scanner proven on a
      planted text, so the derivation runs in-session and outlives nothing.
  - id: AC8
    text: >
      ONE GIT READER, NOT TWO. `toe_corpus.git_touched` returns the commits git attributes to a spec
      and the paths they touched; `toe_corpus.files_touched` COUNTS exactly that and its returned
      keys and values are unchanged, so the WARP-1401 corpus record is byte-identical to before and
      this item spells out no second `git log --grep`. A selftest drives both over a real spec id in
      this repository's history and requires each count to equal the length of the matching list,
      with a NEGATIVE CONTROL requiring a spec id no commit names to yield empty lists and zero
      counts rather than an exception, and requiring the real id to yield a NON-EMPTY read (without
      which a reader that always returned nothing would satisfy the absent case and quietly make
      every git-path attribution in the repository unattributed).
required_evidence: [unit]
rollback: >
  Delete .veldo/cost_to_change.py and its engine copy, remove the suite file and its manifest entry,
  and regenerate scripts/suites/requires.json and specs/index.md. Nothing reads the module, no gate
  stage runs it and it writes no state. The toe_corpus change is a behaviour-preserving extraction
  whose reverting is a three-line inline of git_touched back into files_touched; the corpus records
  it produces are identical either way.
---

## Outcome

PLAN-0014 O6: the per-area aggregation of reconciled actuals that PLAN-0011's entropy metrics
consume, joining placement declarations where that plan has shipped and standing down honestly to
git-path attribution where it has not.

## What is actually new here, since a per-area cost map already exists

`.veldo/entropy.py` (PLAN-0011 W8) already computes a per-area series from the EVENT STREAM joined
on placements, and drops what it cannot attribute into a single `unattributed_changes` count. This
item is the other half of that sentence, and the difference is the point:

- It aggregates the SPEC-LEVEL ACTUALS CORPUS (WARP-1401), so the unit is a shipped spec with its
  mechanical features, its cycles and its git reality, not a correlation id in a log.
- It carries a SECOND JOIN. Where a spec declares no placement the contract resolves, the areas
  come from the paths git says the change touched, and the record says so. entropy.py has no
  fallback: a pre-placement change is simply unattributed there.
- The BASIS IS IN THE DATA. Every record, every area and the report as a whole state which join
  produced them, so the weaker attribution cannot be quoted as the stronger one.

## The finding, measured over this repository

Run over this repository's own corpus and contract on 2026-08-10:

- **174 shipped-spec records, 137 (record, area) memberships, 107 attributed, 67 unattributed.**
- **66 attributed by DECLARED placement, 41 by GIT PATH.** So 38 percent of what this map can
  attribute at all rests on the weaker join, which is exactly why the basis is a field rather than
  a footnote. The git-path records land almost entirely in two areas: docs (39) and enforcement (8),
  which is what a corpus of pre-placement history looks like.
- **0 of 174 records carry any spend. cost_coverage 0.0, usable_as_cost_ground_truth false.** Every
  cost field in the live map is None. WARP-1401 measured why and it has not changed: nothing in the
  loop emits tokens, because a token count is not knowable from inside a repository.
- **AND A SECOND GAP THIS ITEM MEASURED, WHICH IS NEW: THE GATE CYCLES ARE UNATTRIBUTABLE TOO.**
  1077 events in the log: 771 `gate.passed`, 135 `gate.failed`, 171 `verdict.recorded`. **Not one
  of the 906 gate events carries a spec id or a correlation id** - `scripts/verify.sh` writes a
  COMMIT and nothing else - so `gate_passes` and `gate_failures` are 0 for every spec in the corpus
  and the cycle half of this map is REVIEW VERDICTS ONLY. WARP-1401's AC3 (failures counted
  separately from passes) is real in its seeded selftest and structurally empty in production.

What that means for the plan, stated rather than left for whoever first trusts a number: this map
is usable TODAY as a per-area REVIEW-CYCLE map with an honest attribution basis. It becomes a
cost-to-change map when something records spend (`.veldo/spend.py`), and it becomes a rework map
when the gate's own events carry the spec they ran for. Both are emitters, neither is in this item,
and neither is guessed at here.

## Out of scope

- The emitters. Making `verify.sh` name the spec its run belongs to is a change to a protected path
  and its own decision; recording spend is `.veldo/spend.py` and an adoption question. This item
  reports both gaps as numbers and closes neither.
- Any change to `.veldo/entropy.py`, to PLAN-0011's contract, or to the architecture contract. The
  seam is prose and a shared resolver by construction (C6), and adding an edge would be the exact
  thing that constraint forbids.
- Any enforcement. Nothing gates on these numbers (NG1). No gate stage calls this module, which
  AC6 asserts rather than promises.
- A capability entry. `.veldo/capabilities.yaml` is integrated by another process; the line to add
  is recorded in this item's handover notes.

## Notes

- Write the label before the fallback. If git-path attribution exists for an afternoon without the
  basis field, somebody quotes a per-area figure that no human ever declared, and the habit starts.
- Every assertion in the suite has a negative control beside it, and FOUR mutations were driven to
  see reds from a clean 30 passed, 0 failed: unknown cost summing to zero (2 red), git-path
  attribution mislabelled as a placement join (4 red), an unattributable record defaulted into the
  first declared area (5 red), and the front-matter index blinded so no placement is ever seen
  (6 red). The second is the instructive one: it left every per-area TOTAL identical and was caught
  only by the basis assertions, which is the failure mode this item exists to prevent.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
