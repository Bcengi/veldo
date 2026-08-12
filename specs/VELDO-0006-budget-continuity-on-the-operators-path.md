---
schema: veldo.spec/v1
id: VELDO-0006
title: Budget continuity on the operator's path - where the budget stands, whether the governor is
  actually pacing or merely bootstrapping, and what survives stopping right now
status: ready
risk: standard - it adds a read model over the governor's own arithmetic and the recorded event
  stream, writes nothing and paces nothing. It is NOT low because the number it reports is the one an
  operator decides on, and this repository has ZERO recorded spend, so the obvious report would say
  "0 tokens used, plenty of budget" when the truth is "nothing was ever measured" - the exact
  confident zero this migration kept finding. It is not high because it changes no pacing decision
  and every leg stands down by name
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W5
placement: [contracts]
footprint:
  - ".veldo/budget_state.py"
  - "engine/.veldo/budget_state.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/23_veldo_0006_budget_state.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0006-budget-continuity-on-the-operators-path.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    One report, per window: the trailing horizon, the tokens recorded inside it, what remains, the
    target rate against the measured rate, and when the window rolls. It says which POSTURE the
    governor is in by name, and when it is bootstrapping it says that the pacing it would do is not
    happening rather than printing a comfortable number.
  error_taxonomy: >
    Three postures, never collapsed, because an operator acts differently in each: PACING (burn is
    measured and the worker count is derived from it), BOOTSTRAP (no burn is measured, so the governor
    permits the maximum and is NOT pacing) and SPENT (a window's budget is used up in its trailing
    horizon, so the answer is zero workers until it rolls). A window with NO RECORDED SPEND AT ALL is
    UNMEASURED, which is distinct from a window with spend totalling zero, and neither is reported as
    "budget available".
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Make the report treat an empty spend history as zero tokens spent in .veldo/budget_state.py
      instead of UNMEASURED, and the assertion that a repository with no recorded spend reports
      UNMEASURED and BOOTSTRAP rather than a remaining budget must go red.
    text: >
      NO RECORDED SPEND IS NOT ZERO SPEND, AND THIS REPOSITORY IS THE CASE. MEASURED on 2026-08-12:
      the live event stream carries ZERO events with a spend field, so the obvious report would say
      the whole budget remains. The truth is that nothing was ever recorded, and those are different
      facts with opposite consequences - the first invites an operator to spend, the second says the
      instrument is not connected. A window with no spend inside its horizon is UNMEASURED, reported
      by name. NEGATIVE CONTROL: with one recorded spend event the same window reports a real
      remaining figure, so UNMEASURED is a measurement of the stream and not the module's only answer.
  - id: AC2
    falsified_by: >
      Report the posture as PACING whenever windows are configured in .veldo/budget_state.py, and the
      assertion that an unmeasured burn rate reports BOOTSTRAP and says the governor is permitting the
      maximum rather than pacing must go red.
    text: >
      BOOTSTRAP IS SAID OUT LOUD, BECAUSE IT MEANS THE PACING IS NOT HAPPENING. The governor's own
      contract is that a per-worker rate of zero or less means burn is not measured yet and it permits
      max_workers. That is correct for the governor and dangerous as a silent state: in this
      repository burn has NEVER been measured, so the pacing this plan promises has never paced
      anything here. The report names the posture - PACING, BOOTSTRAP or SPENT - and in BOOTSTRAP it
      says the worker count is a permission rather than a pace. NEGATIVE CONTROL: with a measured rate
      the posture is PACING and the derived worker count matches the governor's own function called
      directly, so the posture is derived rather than asserted.
  - id: AC3
    falsified_by: >
      Compute the worker count and the resume time inside .veldo/budget_state.py instead of calling
      governor.desired_workers and governor.resume_at, and the assertion that every number in the
      report equals the governor's own function over the same inputs must go red.
    text: >
      EVERY NUMBER COMES FROM THE GOVERNOR, NOT FROM A SECOND IMPLEMENTATION. The worker count, the
      windowed spend and the resume time are the governor's own functions called over the same inputs,
      and the suite asserts equality against them directly. A read model that recomputed the pacing
      arithmetic would be two implementations of one rule, which is this repository's most repeated
      defect, and the one that would diverge silently because both would look right.
  - id: AC4
    falsified_by: >
      Delete the survival section from the report in .veldo/budget_state.py, and the assertion that
      the report names what survives stopping right now - concluded artifacts, and claimed units whose
      claims age out - must go red.
    text: >
      LOSING A WINDOW MUST COST PACING AND NOT WORK, AND THE REPORT SAYS WHAT SURVIVES. On 2026-08-10
      and 2026-08-11 two sessions hit limits and 85 agents died mid-flight. What makes stopping safe
      now is not this item: it is that concluded work is ARTIFACTS on disk and a claimed unit's claim
      AGES OUT of the ledger, so the unit returns to the queue. This report names both, with the
      counts it measured, so an operator deciding whether to stop reads what is at risk instead of
      guessing. IT CLAIMS NOTHING IT DID NOT MEASURE: an unreadable or absent ledger is reported as
      such rather than as nothing at risk.
  - id: AC5
    falsified_by: >
      Remove the absent-configuration stand-down from .veldo/budget_state.py, and the assertion that
      a repository configuring no window stands the report down by name while keeping ONE key shape
      must go red.
    text: >
      ADOPTION SAFE, AND IT PACES NOTHING. A repository that configures no budget window stands the
      report down by name: "nobody declared a budget here" is not "the budget is fine". This module
      makes no pacing decision, spawns nothing, sleeps never, and no gate stage loads it - it is a
      read model an operator runs. NEGATIVE CONTROL: with a window configured the same report answers,
      so the stand-down is a measurement rather than the module's only behaviour.
required_evidence: [unit]
rollback: >
  Delete .veldo/budget_state.py and its suite fragment. The governor, the fleet and the ledger are
  untouched by construction, so the retreat removes one read model and changes no decision anything
  else makes.
---

# Budget continuity on the operator's path

## The measurement that shapes this item

PLAN-0018's O4 says a budget should not be exceeded on the path an operator actually takes, and that
losing a window should cost pacing rather than work. Its own measure is dated: **on 2026-08-10 and
2026-08-11 two sessions hit limits and 85 agents died mid-flight.**

Two facts about this repository, measured on 2026-08-12:

**The event stream carries zero events with a spend field.** So `windowed_spend` returns 0.0 for
every window, and the obvious report would say the entire budget remains.

**The governor's documented bootstrap path permits `max_workers` when the per-worker rate is zero or
less**, which is exactly the state an unmeasured stream produces. That is correct behaviour for the
governor - it cannot pace what it cannot measure - but it means **the pacing this plan promises has
never paced anything in this repository**, and nothing says so.

So the report's job is not to compute a budget. It is to say which of three postures the governor is
in, and to refuse to turn "nothing was recorded" into "plenty remains".

## Why this recomputes nothing

The worker count, the windowed spend and the resume time all come from `.veldo/governor.py` by
calling it. A read model that reimplemented the pacing arithmetic would be two implementations of one
rule - the defect this repository has shipped more than once - and the failure mode is the quiet one,
because both copies look right until they disagree.

## What actually makes stopping safe

Not this item. Concluded work is artifacts on disk, and a claimed unit's claim ages out of the ledger
so the unit returns to the queue - the properties VELDO-0002 and VELDO-0003 landed. This report names
them and the counts it measured, so an operator deciding whether to stop reads what is at risk rather
than guessing, and it reports an absent ledger as unknown rather than as nothing at risk.
