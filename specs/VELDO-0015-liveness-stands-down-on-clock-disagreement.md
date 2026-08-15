---
schema: veldo.spec/v1
id: VELDO-0015
title: Liveness stands down on clock disagreement - a heartbeat from the future is answered
  "unanswerable, human needed", never "alive", so a fast-clocked worker can no longer lock a unit
  forever, and never "stale", so its live claim is never handed to a second worker
status: ready
risk: high - both freshness readers sit under every fleet decision about who owns a unit and whether
  a run is alive, and each failure direction is serious in a different way. The defect this fixes
  (PLAN-0018 ledger finding 76): both readers subtract in one direction, so a heartbeat AHEAD of the
  reader's clock can never exceed the staleness window and reads as alive forever - one worker with a
  fast clock permanently locks every unit it touches. The tempting one-line fix (a symmetric window)
  is WORSE: a fast clock then reads stale on every heartbeat and a LIVE claim is handed to a second
  worker, which is the silent double-build the ledger exists to prevent. The honest design, settled
  by Dmitry as veldo-factory kernel decision OD-9 on 2026-08-15: clocks that disagree beyond a
  declared tolerance make liveness UNANSWERABLE, and the reader says so and summons a human instead
  of guessing in either direction
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [contracts]
footprint:
  - ".veldo/claim.py"
  - "engine/.veldo/claim.py"
  - ".veldo/runlog.py"
  - "engine/.veldo/runlog.py"
  - "scripts/suites/28_veldo_0015_clock_standdown.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0015-liveness-stands-down-on-clock-disagreement.md"
  - "specs/index.md"
  # The proof record this unit writes, and the ledger entry recording its review's three
  # report-surface follow-ups (finding 81) - the dogfood footprint check rightly demands the
  # spec name EVERY path its change set touches.
  - "proof/VELDO-0015/driven-falsifications.txt"
  - "plans/PLAN-0018-what-a-complex-project-needs.md"
behavior_bearing: true
observability:
  logs: >
    An unanswerable verdict is never silent: claim() refuses with the named reason "unanswerable",
    and runlog.classify returns the named state "unanswerable", so every surface that prints a
    classification prints the word rather than a wrong confident one. The claim refusal is
    distinguishable from "claimed" because the two demand OPPOSITE operator actions: "claimed" means
    wait, "unanswerable" means a human must look at a clock.
  metrics: >
    No new counters. work_state.liveness already answers LIVENESS_UNCONFIRMED with a future-stamp
    note for this state (a protection predating this spec) and deliberately never forwards a future
    stamp to classify, so no work_state change is needed; that pre-existing behaviour is pinned by
    AC5 rather than assumed, so it cannot later be removed as "redundant".
  error_taxonomy: >
    Two named verdicts extend two existing vocabularies additively. claim(): reasons were
    granted | capability | claimed, now also "unanswerable". runlog.classify(): states were
    done | blocked | stale | active, now also "unanswerable". No existing verdict changes meaning:
    everything previously answered "alive" or "stale" for records whose clocks agree still answers
    exactly as before, which is what keeps every shipped caller correct without edits.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      In claim(), treat a future heartbeat beyond tolerance as live (drop the unanswerable branch so
      the one-sided staleness test is the whole answer), and the assertion that a second worker's
      claim() against a far-future heartbeat returns (False, "unanswerable") must go red.
    text: >
      A CLAIM WHOSE HEARTBEAT IS AHEAD OF NOW BEYOND TOLERANCE IS REFUSED BY NAME. claim() by a
      different worker against a record whose heartbeat_at is more than CLOCK_SKEW_TOLERANCE_SECONDS
      ahead of the caller's clock returns (False, "unanswerable"), not (False, "claimed") - the two
      reasons demand opposite operator actions and must not be conflated. The tolerance is one named
      module constant with its reason in a comment, never an inline number.
  - id: AC2
    falsified_by: >
      In claim(), treat the "unanswerable" verdict as stale (fall through to publish the takeover),
      and the named takeover row - a second worker's claim() must not grant and the record must
      still name the original holder - must go red. Separately, make the reader surface treat
      unanswerable as unclaimed (is_claimed False for a beyond-tolerance future heartbeat), and the
      held-surface row must go red.
    text: >
      UNANSWERABLE IS NEVER RECLAIMABLE, AND THE UNIT VISIBLY STAYS HELD. Two halves, each against
      the real API. The takeover half: claim() by a second worker against a beyond-tolerance future
      heartbeat does not grant and does not rewrite the record. The held half, on the surface the
      frontier actually reads: holder() still names the original worker, is_claimed() answers True,
      and the unit appears in claimed_units() - so the offer surface cannot start offering a unit
      the claim surface refuses, the hot loop review B2 constructed. _is_stale keeps its boolean
      contract (False for unanswerable) as its own pinned row.
  - id: AC3
    falsified_by: >
      Remove the unanswerable branch from runlog.classify (let the one-sided window answer "active"
      for a future heartbeat), and the assertion that classify returns "unanswerable" for a state
      whose heartbeat is beyond tolerance ahead must go red.
    text: >
      THE RUN READER SAYS THE SAME WORD. runlog.classify(state) returns "unanswerable" for a run
      whose heartbeat_at is more than the tolerance ahead of now, instead of "active". Terminal
      states still win: a run with status done or aborted classifies "done", and an explicit
      blocked classifies "blocked", regardless of its heartbeat, because a recorded terminal fact
      does not need a clock.
  - id: AC4
    falsified_by: >
      Set CLOCK_SKEW_TOLERANCE_SECONDS to 0 in either module (the false-alarm flood), or to one year
      (finding 76 restored), and the band row pinning both module constants to a defensible
      magnitude - at least sixty seconds, at most ten times the module's own staleness window - must
      go red; separately, compare with >= instead of > and the boundary row must go red.
    text: >
      ORDINARY SKEW IS NOT AN ALARM, AND THE TOLERANCE'S MAGNITUDE IS A CHECKED FACT. A heartbeat
      ahead of now by no more than the tolerance is normal NTP-grade disagreement plus write latency
      and is judged exactly as before: live for the claim ledger (through the real claim(), refused
      with "claimed"), "active" for classify. The stand-down fires only beyond tolerance. And the
      tolerance itself is pinned inside a defensible band in BOTH modules - at least sixty seconds,
      at most ten times that module's own staleness window - because review B1 drove it to zero and
      to one year with every row green: a magnitude nobody asserts is a comment, not a contract.
  - id: AC5
    falsified_by: >
      In work_state.liveness, treat a future-stamp note as a confirmation (return LIVENESS_ACTIVE
      when the heartbeat note is set), and the assertion that the real status reader answers
      LIVENESS_UNCONFIRMED with the future-stamp note for a future-heartbeat run must go red.
    text: >
      NO SURFACE ANSWERS "ALIVE" FOR A FUTURE STAMP. Three surfaces, each asserted against the real
      reader: claim() refuses with the named reason (AC1), runlog.classify answers "unanswerable"
      for direct readers (AC3), and work_state.liveness - which deliberately never forwards a
      future stamp to classify (it answers before consulting the window, a protection that predates
      this spec) - answers LIVENESS_UNCONFIRMED carrying the future-stamp note, never
      LIVENESS_ACTIVE. That pre-existing protection is pinned here as a regression row so this
      spec's change can never be "completed" by quietly removing it.
  - id: AC6
    falsified_by: >
      Change one existing verdict for an agreeing-clock record - make _is_stale answer False for a
      past-window heartbeat, or classify answer "unanswerable" for a fresh one - and the
      REGRESSION table row asserting every pre-change verdict for every agreeing-clock fixture is
      byte-identical to the shipped behaviour must go red.
    text: >
      EVERY SHIPPED VERDICT FOR AGREEING CLOCKS IS UNCHANGED. For records whose heartbeat is not
      ahead of now beyond tolerance - fresh, slightly past, exactly-at-window, past-window, absent,
      and malformed timestamps - the verdict functions answer byte-identically to the shipped code,
      asserted by iterating ONE table of (fixture, expected) rows whose row count is itself
      asserted, so deleting a family reds the row rather than shrinking the evidence. The additive
      contract is the whole point: no caller that never sees a future heartbeat can tell this spec
      ever landed.
---

## Why

PLAN-0018 ledger finding 76, measured 2026-08-13: both freshness readers subtract in one direction
(`now - hb > window`), so a heartbeat ahead of the reader's clock never exceeds the window and reads
as alive forever. In a single-process world that was latent. The veldo-factory (kernel v1.0) makes
the claim ledger the sole authority for unit ownership across a fleet, so one fast-clocked worker
would permanently lock every unit it touches, and nothing on any surface would say why.

The one-line symmetric window was considered and REJECTED in the ledger entry itself: it converts a
visible stall into a silent collision, because a fast clock then reads stale on every heartbeat and
a live claim is handed to a second worker. Dmitry settled the honest design as kernel OD-9: clocks
that disagree beyond tolerance make liveness UNANSWERABLE - say so, hold the unit, summon a human.

## Design notes

One new public verdict word, "unanswerable", added to two existing string vocabularies additively.
The boolean reclaim test keeps its name and its contract (may this claim be taken over?) and simply
answers False for the unanswerable state, because "cannot judge" must never authorize a takeover.
The tolerance is one named constant per module, generous enough for NTP-grade skew plus write
latency, and the two modules deliberately do NOT share it: claim.py and runlog.py already own their
windows separately (90s and 30s), and this spec follows the shape the modules already have.

The factory's scheduler keeps its own detection of the same state as defense in depth (kernel
OD-9), which costs one check and catches the case where an old Veldo without this spec is in play.

A cost stated rather than discovered (review N6): the tolerance EXTENDS the maximum time a dead
worker's claim can read live when its clock was fast at death - up to tolerance + window instead of
window alone. That is the price of refusing to guess, it is bounded by the tolerance band AC4 now
pins, and it is deliberate.

Known follow-ups recorded, not silently shipped (review N3, N4, N5): task_report buckets an
unanswerable claim under "claimed" (the operator surface says wait for the one state waiting cannot
fix); no shipped claim() caller retains the refusal reason; status_server renders the new state
without a badge colour. All three are report-surface prominence, none loses the word itself, and
they are PLAN-0018 ledger material for a follow-up unit rather than scope growth here.
