---
schema: veldo.spec/v1
id: WARP-1210
title: The support numbers - time-to-diagnosis and time-to-restore, recurrence rate, and the
  diagnosability score, derived from recorded events and AUTHENTICATED against the reconciliation
  receipts so a number can never come from an event no reconciliation produced, joined with
  cost-to-change per area where that data exists and standing down honestly where it does not
  (W10 of PLAN-0012)
status: shipped
risk: standard - this item DERIVES and RENDERS; it decides nothing and refuses nothing operationally.
  It reads the event stream and the reconciliation receipts, both already written, and adds measures to
  the existing metrics derivation and dashboard. It touches no enforcement-core organ (the executor, the
  whitelist, the two-key rule, the kill switch and the ladder are not read and not edited), opens no
  execution path, starts no process, and writes no record other than rendered output. The footprint tier
  is standard as well: a single declared area, metrics, via .veldo/metrics.py and .veldo/dashboard.py. The
  one property that makes this item worth reviewing carefully is HONESTY OF NUMBERS rather than safety of
  action: a derived measure that silently counts an unbacked event, or invents a denominator, is a lie a
  human will act on, so the anti-vacuity work here is on the exclusion and the stand-down
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W10
plan_revision: 2
depends_on: [WARP-1208]
placement: [metrics]
footprint:
  - .veldo/metrics.py
  - .veldo/metrics_event_stream.py
  - .veldo/metrics_support_contract.py
  - .veldo/metrics_support.py
  - .veldo/metrics_read_accounting.py
  - .veldo/metrics_skip_rule.py
  - .veldo/metrics_read_kind.py
  - .veldo/metrics_read_closure.py
  - .veldo/metrics_owner_reads.py
  - .veldo/metrics_shape_readers.py
  - .veldo/metrics_readers.py
  - .veldo/metrics_support_report.py
  - .veldo/dashboard.py
  - .veldo/capabilities.yaml
  - engine/.veldo/metrics.py
  - engine/.veldo/metrics_event_stream.py
  - engine/.veldo/metrics_support_contract.py
  - engine/.veldo/metrics_support.py
  - engine/.veldo/metrics_read_accounting.py
  - engine/.veldo/metrics_skip_rule.py
  - engine/.veldo/metrics_read_kind.py
  - engine/.veldo/metrics_read_closure.py
  - engine/.veldo/metrics_owner_reads.py
  - engine/.veldo/metrics_shape_readers.py
  - engine/.veldo/metrics_readers.py
  - engine/.veldo/metrics_support_report.py
  - engine/.veldo/dashboard.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/metrics.py
  - packs/*/.veldo/metrics_event_stream.py
  - packs/*/.veldo/metrics_support_contract.py
  - packs/*/.veldo/metrics_support.py
  - packs/*/.veldo/metrics_read_accounting.py
  - packs/*/.veldo/metrics_skip_rule.py
  - packs/*/.veldo/metrics_read_kind.py
  - packs/*/.veldo/metrics_read_closure.py
  - packs/*/.veldo/metrics_owner_reads.py
  - packs/*/.veldo/metrics_shape_readers.py
  - packs/*/.veldo/metrics_readers.py
  - packs/*/.veldo/metrics_support_report.py
  - packs/*/.veldo/dashboard.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1210-the-support-numbers.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: Every excluded or unresolvable input is reported by NAME in the rendered output and in the
    returned model rather than dropped silently - an incident.closed event with no backing receipt, a
    receipt whose incident cannot be resolved, a measure whose denominator is zero, and an absent
    per-area cost source each appear as a named exclusion or stand-down line, so a surprising number is
    diagnosable from the output alone without reading the source. An entry a store directory holds that is
    NOT a record is ACCOUNTED rather than dropped: the read counts it, names it with the declared reason it
    is skippable, and the model carries it as read_skipped so ALL THREE SURFACES render it - the text report
    on its own line, the dashboard on its own card and --json as a key - because a basis a human never sees
    is not observability. A RECORD IS IDENTIFIED BY ITS NAME (the suffix is asked FIRST), so what a
    declared name may dismiss is a KIND of entry rather than a content: a REGULAR FILE, or a DIRECTORY that
    proves by its own enumeration, WITHIN A DECLARED DEPTH BOUND, that it holds no record and nothing that
    could hold one, and never a SYMLINK; every other ENUMERATED entry - including a subtree deeper than that
    bound - leaves the read INCOMPLETE with the entry NAMED and the bound stated. Every name and every
    detail that reaches a surface is PRINTABLE on any output stream (a directory entry name and an area id
    are bytes read off
    disk and the stream printing them may be ASCII), and a recorded line whose bytes are not valid UTF-8 IS
    SKIPPED by the loop reader and NAMED by the support pass, as is a line that PARSES TO SOMETHING THAT IS
    NOT A RECORD, so neither a diagnosable stand-down nor the pre-existing loop measures can be turned into
    a crash by a recorded line. EVERY RECURSIVE READ THIS PASS PERFORMS IS BOUNDED OR BACKSTOPPED, which is
    the class the depth defect belongs to rather than its one instance: there are exactly TWO recursive
    paths (the dismissible-directory walk and json.loads over a nested recorded artifact), the walk stops at
    the declared depth bound, and RecursionError - a RuntimeError that no OSError/ValueError handler catches
    - is caught at BOTH, each standing its own source down BY NAME. AND THE CLASS THOSE ROUNDS WERE EACH ONE
    MEMBER OF IS NAMED FROM WHAT THIS ITEM DECLARES RATHER THAN FROM HOW ITS CODE HAPPENS TO REACH IT,
    because three successive taxonomies keyed on a MECHANISM (recursion, then the exception classes, then the
    thirteen READ PRIMITIVES) were each one name short: A DECLARED SOURCE BECOMES UNAVAILABLE AND SOME
    SURFACE PRINTS NOTHING AT ALL - HOWEVER THE SOURCE IS REACHED, AND WHETHER THE FAILURE RAISES OR BLOCKS.
    A MODULE LOAD IS A READ that none of those primitives names, and a read that BLOCKS raises nothing at
    all, so no handler and no declared exception set can reach it. THE RULE IS THEREFORE QUANTIFIED OVER THE
    DECLARED TABLE: every one of the THIRTEEN declared sources has a READ UNIT (SUPPORT_READ_UNITS), every
    unit is asked WHAT IT IS before anything opens it (a whole-file read of an entry that is neither a
    regular file nor a directory blocks until a writer appears), every hand-off of a unit to an ENGINE OWNER
    goes through ONE delegation boundary that asks that question and then names the whole Exception family,
    and NO declared source is loaded as a module by a hard-coded path anywhere in the pass. AND THE DOMAIN OF
    THAT RULE IS THE TRANSITIVE CLOSURE OF WHAT IS OPENED ON THIS PASS'S BEHALF RATHER THAN WHAT THIS PASS
    OPENS ITSELF, which is the correction the first formulation needed and the reason it was not enough: a
    DELEGATED read unit is where the read STARTS, and six of the thirteen rows are delegated, so EVERY ROOT
    ANY OWNER OPENS ON THIS PASS'S BEHALF is DECLARED (SUPPORT_DELEGATED_CLOSURE: one row per hand-off,
    every root naming WHERE its kind question is asked), the closure is PROVEN COMPLETE BY MEASUREMENT under
    an interpreter audit hook over the real owner calls rather than by reading an owner's source, and a
    MODULE LOAD's closure is TWO files rather than one, because the loader opens the BYTECODE CACHE as well
    as the source. THE ONE MEMBER OF THIS CLASS THIS ITEM DOES NOT REACH IS STATED RATHER THAN IMPLIED AWAY:
    a REGULAR FILE on a wedged filesystem blocks with nothing to see at stat time, which no kind test can
    answer and which needs a watchdog at the caller. WITHIN that rule
    every read of a recorded artifact still SITS INSIDE A HANDLER NAMING AT LEAST FOUR DECLARED CLASSES -
    OSError, ValueError, RecursionError and MemoryError - or one naming the whole Exception family, and those
    reads are ENUMERATED FROM THE AST with the handler standing over each and the unguarded list asserted
    EMPTY; KeyboardInterrupt and SystemExit are deliberately NOT in that set, because an operator's stop and
    a caller's exit are not properties of an artifact and must propagate; and the assertions DRIVE THE FOUR
    REAL SURFACES for EVERY DECLARED SOURCE crossed with four hostile entry shapes, EACH UNDER A TIMEOUT that
    counts a wedged surface as a failure, which is the coverage neither the model-only grid nor an
    exception-keyed rule could have. A STREAM THAT EXISTS AND CANNOT BE READ AT ALL IS NOT A SHORTER HISTORY EITHER: the
    loop reader returns NO event and a NAMED SHORTFALL carrying the path, the exception class and its
    message, rendered above the measures on both text surfaces, as its own card on the HTML one and as its
    own key on --json, while an ABSENT stream stays complete, empty and silent (adoption safe). EVERY READ OF
    A RECORDED ARTIFACT
    THIS PASS PERFORMS NAMES ITS CODEC rather than inheriting the locale's, so a measure is a property of
    the recorded bytes and not of the environment that read them; the four ENGINE OWNERS this pass EXECUTES
    still decode through the locale, which is outside this footprint and is declared with its measured cost
    (the source that owner reads stands down BY NAME under an ASCII locale, and no MEASURE moves).
  error_taxonomy: The exclusion and stand-down reasons are a closed, named set (UNBACKED_EVENT,
    UNRESOLVED_RECEIPT, CONFLICTING_RECEIPTS, CONFLICTING_RECORDS, UNRESOLVED_RECURRENCE,
    UNUSABLE_INTERVAL, UNREADABLE_TIMESTAMP, EMPTY_DENOMINATOR, NO_AREA_COST_DATA,
    UNREADABLE_AREA_COST_DATA, NO_ARCHITECTURE_CONTRACT, UNREADABLE_ARCHITECTURE_CONTRACT,
    NO_SPEC_CORPUS, UNREADABLE_SPEC_CORPUS, UNREADABLE_SPEC_AREA_INDEX, UNREADABLE_RECEIPT_FILE,
    UNREADABLE_INCIDENT_RECORD, UNREADABLE_INCIDENT_VOCABULARY, UNREADABLE_INPUT_SOURCE,
    INCOMPLETE_READ, UNREADABLE_EVENT_STREAM, UNREADABLE_INCIDENT_CONTRACT_OWNER,
    UNREADABLE_FRONT_MATTER_PARSER, UNREADABLE_INTENT_CORPUS_OWNER, UNREADABLE_ENTROPY_OWNER), each
    naming what was skipped and why, so an honest gap in the numbers is legible as a category rather than
    inferred from a missing row. Three of the first eight were added by the round-1 review, which found
    real input classes handled silently: two receipts resolving to one closure with nothing ordering
    them, a timestamp pair no arithmetic can subtract, and a contract file that exists but yields no
    declared area (which is its own condition and must never be reported as an empty denominator). Eleven
    more were added by the round-2 review, which found BOTH of those defect CLASSES still standing on
    sibling inputs: ABSENT is never reported as UNREADABLE for ANY source the pass reads, and a DUPLICATE
    KEY is never resolved by collection order for ANY dict the pass keys by an id it read (the receipts
    and the incident records both refuse and name every participant; the other four collections carry a
    proven reason they cannot conflict). A recurrence_of naming an incident nothing authenticated is named
    rather than counted. The last six are the round-4 review's, and they are what AC3's new rule needs
    rather than another shape: INCOMPLETE_READ is the ONE name a source carries when it cannot prove it
    read completely (so an unenumerated shape needs no name of its own), and the other five are the
    sources round 4 found DECLARED NOWHERE - the recorded event stream and the four sibling OWNER MODULES
    the readers execute, each of which now names ITSELF instead of a failure in one being charged to
    whichever data source was being read. The source table lives in .veldo/metrics_support_contract.py
    (thirteen rows), is walked by the completeness rule, and is asserted complete against the code.
  metrics: This item IS the metrics surface: it derives time-to-diagnosis, time-to-restore, recurrence
    rate and the diagnosability score from the recorded incident lifecycle events, and reports the count
    of authenticated versus excluded inputs alongside every measure so the reader can see the evidence
    base each number rests on.
acceptance_criteria:
  - id: AC1
    text: >
      THE FOUR MEASURES OUTCOME O6 NAMES ARE DERIVED FROM RECORDED DATA ONLY, in the existing metrics
      derivation (.veldo/metrics.py, extended; no new store, no new instrumentation, no new event type).
      TIME-TO-DIAGNOSIS is opened_at to diagnosed_at and TIME-TO-RESTORE is opened_at to restored_at,
      both taken from the incident record's timeline. CORRECTED PREMISE (this criterion as first written
      claimed WARP-1201 already validates that timeline as non-negative; the round-1 review refuted it and
      the correction belongs here rather than only in the evidence): that validator's check is a
      LEXICOGRAPHIC STRING COMPARE, so a naive timestamp beside a timezone-aware one passes it with zero
      errors and still yields an unsubtractable or negative interval. The derivation therefore FAILS CLOSED
      on any pair it cannot subtract and on a negative result, NAMES the input it dropped, and renders the
      rest of the report,
      reported as a TREND (per-incident values in recorded order plus the median and the latest, never a
      single average that hides a regression). RECURRENCE RATE is the share of closed incidents whose
      receipt carries a non-empty recurrence_of, which is exactly the missing-specification signal
      WARP-1208 records. The DIAGNOSABILITY SCORE is the share of closed incidents resolved FROM
      ARTIFACTS ALONE, defined mechanically as those whose receipt records a diagnosis validation and
      whose incident resolves to a governing spec or area in the corpus, never inferred from prose. Every
      measure is a PURE function over the parsed events and receipts (no clock, no network, no
      filesystem beyond the injected readers), so the same inputs give the same numbers across
      processes. A selftest asserts each measure over a seeded lifecycle, asserts the trend preserves
      recorded order, and asserts purity by recomputing under two different PYTHONHASHSEED values.
  - id: AC2
    text: >
      THE NUMBERS ARE AUTHENTICATED AGAINST THE RECEIPTS, and this is the load-bearing property of this
      item (the round-2 reviewer of WARP-1208 named it: the gate now recognizes incident lifecycle
      events, so ANY writer can append incident.closed, and a measure that trusts the event stream alone
      is unauthenticated). Every measure counts ONLY an incident whose closure is backed by a
      reconciliation receipt that resolves to that incident id; an incident.closed event with NO backing
      receipt is EXCLUDED from every numerator and every denominator and REPORTED BY NAME
      (UNBACKED_EVENT) with its incident id, and a receipt whose incident cannot be resolved is likewise
      excluded and named (UNRESOLVED_RECEIPT). The receipt store is an INJECTED READER, so the
      derivation stays pure and a repository with no receipts stands down to zero authenticated
      incidents rather than falling back to the raw events. Selftests prove: a seeded lifecycle with
      matching receipts counts; the SAME lifecycle with the receipts removed counts NOTHING and names
      every exclusion; a forged incident.closed appended by hand with no receipt is excluded while the
      genuine ones around it still count; and the authenticated-versus-excluded counts are reported
      beside each measure.
  - id: AC3
    text: >
      EVERY SOURCE PROVES IT READ COMPLETELY, OR NO NUMBER IS RENDERED AT ALL. This is the governing rule of
      the item and it REPLACES the earlier approach of naming each failure shape of each source, on the
      owner's decision of 2026-07-25 (VEL-7, option A) after three consecutive independent reviews failed
      this item on the same defect class at successively deeper levels. The earlier approach cannot
      converge: it enumerated eight sources and their known failure shapes, and each review found another
      shape that Python's path predicates or a glob silently swallow, reported as an ABSENCE with no name.
      The rule is now inverted. Each reader returns what it read PLUS A POSITIVE ASSERTION THAT THE READ WAS
      COMPLETE, and anything short of that positive assertion stands the WHOLE SUPPORT SECTION down with the
      source named. A read is complete only when the reader can affirm it: a source that is absent is
      complete and empty, and ANY other outcome - a permission error, a symlink loop, a suffix or placement
      the reader does not enumerate, a partially parsed collection, a sibling owner that would not load - is
      INCOMPLETE and therefore renders nothing. There is ONE decision point rather than eight sources times
      N filesystem shapes, so a shape nobody has thought of yet fails closed by construction instead of
      producing a plausible number. Selftests prove: every declared source, made unreadable in at least
      three shapes each (a permission-denied directory, a symlink loop, and a wrong-suffix or subdirectory
      placement), stands the whole section down with that source named and renders NO measure; a genuinely
      absent source is complete and the section renders; and a sibling owner that will not load names ITSELF
      rather than being charged to whichever source was being read. NO NUMBER means NO NUMBER ON ANY SURFACE:
      the rendered text, the rendered cards AND the machine-readable output each carry the completeness
      verdict and the named sources and not one measure, which the round-5 review found the third surface
      disobeying while this item's own prose claimed otherwise. ONE DECLARED EXCEPTION TO WHAT ACCOUNTED
      MEANS, added on the round-5 review's finding that the availability cost was materially larger than the
      description this approach was approved on: a store directory may hold entries that are NOT records (a
      .gitkeep or .keep, which is the standard idiom for committing exactly the empty store
      directories an adopter needs, a .gitignore or .gitattributes, a README, an operator's archive, an
      editor lock, swapfile or backup, a merge or patch leftover, a file browser's index or cache), and
      those are declared in ONE closed table, matched POSITIVELY, and ACCOUNTED as the non-records they are
      - counted, named with their reason, carried into the model and rendered on all three surfaces, never
      silently ignored. A RECORD IS IDENTIFIED BY ITS NAME (name.endswith(suffix), asked FIRST at every
      entry), so what a declared name may dismiss is a KIND of entry and never a content: a REGULAR FILE, or
      a DIRECTORY that proves by its OWN enumeration that it holds no record and nothing that could hold one
      WITHIN A DECLARED DEPTH BOUND (SUPPORT_STORE_SKIP_MAX_DEPTH, 32 levels: the walk RECURSES, an
      unbounded one raised RecursionError - a RuntimeError no OSError/ValueError handler caught - and exited
      all four surfaces printing nothing, so a subtree deeper than the bound is UNACCOUNTED and stands the
      read down BY NAME with the bound stated), and NEVER a SYMLINK whatever it resolves to, because the
      round-6 review measured four such shapes LOSING a seeded record while the section rendered. THE
      ASYMMETRY BETWEEN THE THREE BRANCHES IS DELIBERATE AND EACH WINDOW IS NAMED: a symlink NAMED as a
      record and resolving to one IS read (reading a resolved record is safe), a link is never DISMISSED
      unread (a target can change after the check, and that shape is the measured loss), and a DIRECTORY is
      dismissed on an enumeration that can change in the same way - accepted there because the fact checked
      IS a fact about the entry (enumerated through the entry at every level, never through a link, so the
      walk cannot leave the subtree), it stays true of the store as enumerated, and the NEXT read stands the
      section down. THE TWO RESIDUALS
      OF DECIDING RECORD-NESS BY NAME ARE DECLARED: a skip-named regular file is never OPENED, so
      record-shaped bytes inside a conventionally-named non-record file are not consumed, and a HARDLINK
      bearing a skip name IS a regular file and is dismissed as one - deciding record-ness by CONTENT would
      consume files the store's own convention excludes and would mean opening entries this reader refuses
      to open. The suffix is asked FIRST, so no skip row can take a record out of a read; an entry no row
      names is still UNACCOUNTED and still stands the section down; and the residual is OPEN-ENDED BY
      DESIGN, because a closed positive-match table cannot enumerate convention. Selftests measure every
      half: TWENTY conventional entries that stood the whole section down now render at the control's own
      diagnosability with the entry accounted by name and SURFACED, TEN skip-named entries whose kind the
      rule may not be applied to stand it down (including a record one level below a skip-named directory),
      a record whose filename matches a skip pattern is still read, and the AVAILABILITY COST IS MEASURED AS
      A DIFFERENTIAL against the pre-narrowing reader resolved FROM GIT over 105 shapes (7 name classes x 15
      entry kinds): 48 shapes that rendered before now stand the section down, 19 of them because that
      reader was losing a seeded record and 29 because the entry is a symlink, a FIFO or a socket, and no
      shape this reader affirms leaves a record unread.
  - id: AC3b
    text: >
      INCIDENTS-PER-AREA IS A SOFT JOIN THAT NEVER FAKES ITSELF (constraint C7). Incidents are attributed
      to a contract area through the incident record's affected_area when it declares one, else through
      the affected_spec resolved to that spec's placement, and the result is joined with PLAN-0011's
      cost-to-change-per-area data on ONE map when that data exists. Where there is no architecture
      contract, no per-area cost data, or no attributable incident, the join STANDS DOWN by name
      (NO_ARCHITECTURE_CONTRACT, NO_AREA_COST_DATA) and the incident measures still render on their own;
      an area is never invented, an unattributable incident is never assigned to a default area, and a
      cost figure is never carried for an area the contract does not declare. Selftests prove all three
      paths over temporary trees: with a contract and seeded cost data the map joins and both columns
      appear; with a contract but no cost data the incident column renders and the cost column stands
      down by name; with no contract at all the whole join stands down and nothing else changes. A
      further selftest asserts this repository's REAL state honestly, whatever it is, rather than
      assuming a join exists here.
  - id: AC4
    text: >
      HONEST DENOMINATORS AND NO INVENTED PRECISION. A measure whose denominator is zero renders as the
      named stand-down EMPTY_DENOMINATOR and NEVER as 0 percent, 100 percent, or a dash that reads as a
      value, because a rate with no population is not a rate. A trend with a single data point is
      reported as a single observation and not as a trend direction. Every share is reported with its
      numerator and denominator beside it, so a reader can see that "100 percent diagnosability" over
      one incident is one incident. Rounding is declared and consistent, and no measure is presented to
      a precision the input does not support. Selftests prove the zero-denominator stand-down for each of
      the two rates, the single-observation case for each of the two trends, and that the numerator and
      denominator accompany every share.
  - id: AC5
    text: >
      THE EXCLUSIONS AND STAND-DOWNS ARE NON-VACUOUS, proven by the MATRIX standard this plan's last item
      established rather than by paired mutations. Every guard in this item - the unbacked-event
      exclusion, the unresolved-receipt exclusion, the zero-denominator stand-down, the no-cost-data
      stand-down, and the no-contract stand-down - is neutralized IN MEMORY one at a time and run against
      EVERY guard's fixture, and the resulting matrix is asserted EXACTLY DIAGONAL: each mutation changes
      only its own fixture's outcome (an excluded input becomes counted, or a stand-down becomes a
      fabricated number) and no other, and every module on disk is asserted sha256-unchanged after all
      runs. Each mutation target is asserted to appear EXACTLY ONCE in its module so no mutation can
      silently match nothing. The CONTROLS prove no over-firing: a fully authenticated lifecycle renders
      every measure with no exclusions reported, and a repository with no incidents at all renders the
      support section as an honest empty state rather than an error or a row of zeros. The UNMECHANIZABLE
      part is labeled review-lane in the module and here: whether an incident was TRULY resolved from
      artifacts alone is a human judgment, and the mechanical definition in AC1 is a declared proxy, not
      a measurement of understanding.
  - id: AC6
    text: >
      ADDITIVE, ENGINE-SYNCED, AND HONESTLY RECORDED. The support measures are added to the existing
      derivation and dashboard without changing any existing number: a selftest asserts every measure
      already computed by .veldo/metrics.py is byte-identical before and after this change over the same
      event stream, and that a repository with no incident events renders exactly as it did before
      (adoption safe). The pass starts no process, thread or timer (NG3), reads no live system (NG1), and
      derives from recorded artifacts only. .veldo/metrics.py, .veldo/dashboard.py and .veldo/capabilities.yaml
      ship in the canonical engine and are re-synced BYTE-IDENTICAL across engine and all packs
      (template sync and pack drift end empty; a selftest asserts root-versus-templates and cross-pack
      byte-identity). capabilities.yaml gains ONE honest mechanical entry naming exactly what ships and
      deferring honestly: the /veldo:init lay-down and the made-true documents are WARP-1211 (W11). The
      full gate is GREEN, RULE #1 is clean, no protected path is touched, and the safety core is neither
      read nor edited. Dogfood: this spec declares behavior_bearing with an observability block and passes
      its own diagnosability gate, its placement resolves to the metrics area, and its footprint tier is
      standard.
required_evidence: [unit]
rollback: >
  Revert the commit. The change extends the existing metrics derivation and dashboard with the support
  measures, adds one capabilities entry, and adds a selftest block, all re-synced byte-identical across
  engine and the packs. It adds no store, no event type, no record and no check, and it changes
  no existing number (a selftest asserts byte-identity of the pre-existing measures over the same
  stream), so reverting removes the support section and nothing else. A repository with no incident
  events is unaffected either way.
---

## Intent

This is W10 of PLAN-0012 and the second half of outcome O6: support has numbers. WARP-1209 made
diagnosability a gate concern; WARP-1208 made the incident lifecycle produce records. This item turns
those records into the four measures the plan names, so that "are we getting better at this" stops being
a feeling and becomes a derivation from artifacts the loop already wrote.

The reason it needs care is not safety, it is honesty. A derived number is acted on by a human who cannot
see how it was computed, so every way this item could quietly lie is a defect: counting an event nobody
authenticated, inventing a rate over an empty population, assigning an unattributable incident to a
convenient area, or presenting one incident as a percentage. The load-bearing property is therefore the
one the round-2 reviewer of WARP-1208 identified: the gate now recognizes incident lifecycle events, so
anything can append incident.closed, and a measure that trusts the event stream alone is unauthenticated.
Every number here is backed by a reconciliation receipt or it is excluded and named.

## Context

- What O6's measure asks for: the metrics derivation renders all four measures from the event stream,
  joining per-area cost data when present and standing down without it. The four are time-to-diagnosis
  and time-to-restore trending, recurrence rate, and the diagnosability score.
- What is already recorded and therefore reusable: the incident record's validated timeline (WARP-1201
  refuses a negative time-to-diagnosis, so the inputs are sane), the reconciliation receipt with its
  failure signature, recurrence_of, missing_specification and diagnosis validation (WARP-1208), the
  event stream itself, and PLAN-0011's per-area cost-to-change data in .veldo/entropy.py. Nothing new is
  instrumented.
- The authentication join is the item's spine, and it is a direct consequence of a review finding rather
  than an invention: WARP-1208 added the four incident types to the gate's recognition set, which was
  correct and necessary, and the side effect is that recognition is not authentication. The receipts are
  the authority; the events are the index.
- The soft join is the same discipline PLAN-0012 uses everywhere (C7): join PLAN-0011 data where it
  exists, stand down by name where it does not, never fake it. This repository's own state is asserted
  honestly by a selftest rather than assumed.

## Out of scope

- No new event type, record, store or check. This item derives; it writes only rendered output.
- No /veldo:init lay-down and no made-true documents. That is WARP-1211 (W11).
- No change to any existing measure. The pre-existing numbers are asserted byte-identical over the same
  stream; if this item would change one, that is a defect, not an improvement.
- No live system, no dashboard service, no standing process. The dashboard stays the existing in-session
  render.
- No judgment about whether the diagnosability proxy is the RIGHT proxy. The mechanical definition is
  declared and labeled review-lane; refining it is a later intent, not a silent change here.

## Notes

- Prove the teeth as a MATRIX (every mutation against every fixture, asserted exactly diagonal), which is
  the standard WARP-1208's round-2 review established after reproducing 144 cells independently. Paired
  mutations are no longer sufficient evidence in this plan.
- Put the authenticated-versus-excluded counts next to the numbers in the rendered output, not in a
  footnote. A reader who cannot see the evidence base will assume the number is complete.
- Keep every reader injected (events, receipts, the contract, the per-area cost data) so the derivation is
  pure and the stand-downs are testable without a filesystem.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
