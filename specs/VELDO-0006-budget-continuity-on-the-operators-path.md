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
    One report, per window: the trailing horizon, the readings recorded inside it, what remains, the
    target rate against the corroborated rate, and when the window rolls. It says which POSTURE the
    governor is in by name, and when it is bootstrapping it says that the pacing it would do is not
    happening rather than printing a comfortable number. It also names what survives stopping and,
    for each half it could not read, prints UNKNOWN and lists it as a risk it could not measure.
  error_taxonomy: >
    Three postures, never collapsed, because an operator acts differently in each: PACING (burn is
    measured and the worker count is derived from it), BOOTSTRAP (no burn is measured, so the governor
    permits the maximum and is NOT pacing) and SPENT (a window's budget is used up in its trailing
    horizon, so the answer is zero workers until it rolls). A window with NO RECORDED SPEND AT ALL is
    UNMEASURED, which is distinct from a window whose recorded spend totals zero (ZERO_RECORDED), and
    NEITHER is reported as "budget available": no remaining figure is quoted for either. What survives
    stopping has its own two-valued taxonomy per half - a measured count, or UNKNOWN with the reason
    named (an absent corpus root, an unreadable ledger, or a ledger belonging to another tree) - and
    UNKNOWN is never rendered as zero.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Make the report treat an empty spend history as zero tokens spent in .veldo/budget_state.py
      instead of UNMEASURED, OR remove the rule in spend_events that decides which events carry a
      recorded spend, OR collapse a window whose readings total zero into an ordinary measured
      window, and the assertion that a repository with no recorded spend reports UNMEASURED and
      BOOTSTRAP rather than a remaining budget must go red.
    text: >
      NO RECORDED SPEND IS NOT ZERO SPEND, AND THIS REPOSITORY IS THE CASE. MEASURED on 2026-08-12:
      the live event stream carries ZERO events with a spend field, so the obvious report would say
      the whole budget remains. The truth is that nothing was ever recorded, and those are different
      facts with opposite consequences - the first invites an operator to spend, the second says the
      instrument is not connected. A window with no spend inside its horizon is UNMEASURED, reported
      by name, and a window whose readings TOTAL ZERO is ZERO_RECORDED - also not a remaining figure,
      because a connected instrument reporting no consumption is an idle window or a miscounting one
      and an operator must know which. THE STREAM'S ONLY SHAPE IS THE HARD CASE, so it is the one
      driven: its 1173 events carry no tokens field at all, and the whole refusal rests on the single
      rule that separates a spend reading from any other event, which is the governor's own rule
      rather than a second spelling of it. An empty list alone does not exercise that rule.
      NEGATIVE CONTROL: with one recorded spend event added to those non-spend events the same window
      reports a real used and remaining figure, so UNMEASURED is a measurement of the stream and not
      the module's only answer.
  - id: AC2
    falsified_by: >
      Report the posture as PACING whenever windows are configured in .veldo/budget_state.py, or
      repeat a caller-supplied burn rate as a measurement when no window's readings inside its
      horizon TOTAL more than zero - including by COUNTING the readings instead of totalling them,
      which is the same defect through the taxonomy's other door - and the assertion that an
      unmeasured burn rate reports BOOTSTRAP and says the governor is permitting the maximum rather
      than pacing must go red.
    text: >
      BOOTSTRAP IS SAID OUT LOUD, BECAUSE IT MEANS THE PACING IS NOT HAPPENING. The governor's own
      contract is that a per-worker rate of zero or less means burn is not measured yet and it permits
      max_workers. That is correct for the governor and dangerous as a silent state: in this
      repository burn has NEVER been measured, so the pacing this plan promises has never paced
      anything here. The report names the posture - PACING, BOOTSTRAP or SPENT - and in BOOTSTRAP it
      says the worker count is a permission rather than a pace. AND THE RATE IS CORROBORATED AGAINST
      THE STREAM, because it arrives as the CALLER'S argument and this module never measured it: a
      positive rate that no reading inside any window's horizon supports is not repeated as a
      measurement, the posture stays BOOTSTRAP, and the rate handed to the governor is 0.0. So the
      report cannot print "burn is measured at 1.0 tokens per worker per second" directly above
      "UNMEASURED - no recorded spend inside the horizon", which is what it did.
      AND THE EVIDENCE IS A TOTAL, NOT A COUNT OF READINGS. Requiring only that a reading EXIST
      inside a horizon let the contradiction back in through ZERO_RECORDED: one reading of zero
      tokens printed "burn is measured at 1.0" above "1 recorded event(s) inside the horizon total
      ZERO tokens" and paced the worker count from 8 down to 1. The governor's own
      measure_per_worker_rate is the windowed spend over the horizon and the worker count, so it
      cannot return a positive rate over readings totalling zero or less; a positive rate is
      corroborated only by a window whose readings TOTAL more than zero, which is the same evidence
      the caller's own measurement rests on. AND THE BOOTSTRAP REASON IS DERIVED FROM THE WINDOWS:
      never instrumented, readings outside every horizon, a total of no more than zero, and recorded
      burn with no rate supplied are four different facts and four sentences, because one count
      standing in for all four told an operator no window held a reading while the row underneath
      reported 250 of 1000 used.
      NEGATIVE CONTROL: with a measured rate the posture is PACING and the derived worker count
      matches the governor's own function called directly, so the posture is derived rather than
      asserted; and one reading carrying real burn ADDED to that zero reading corroborates the same
      supplied rate, so the refusal is a measurement of the total.
  - id: AC3
    falsified_by: >
      Compute the worker count or the resume time inside .veldo/budget_state.py instead of calling
      governor.desired_workers and governor.resume_at - as a FAITHFUL copy of the governor's
      arithmetic and not only as a divergent one - and the assertion that those numbers ARE the values
      a call into the governor returned must go red.
    text: >
      NO SECOND IMPLEMENTATION OF THE PACING RULES, AND EQUALITY ALONE CANNOT PROVE THAT. The worker
      count, the windowed spend, the resume time, each window's target rate, the rule for what counts
      as a recorded spend and the trailing-horizon cut are the governor's own functions called over the
      same inputs. The suite asserts equality against them directly AND, because equality is satisfied
      by a faithful copy-paste inside this module - the exact duplication this criterion refuses, since
      both copies look right until they drift - it also INTERCEPTS the organ load and requires the
      report's worker count and resume time to BE values a call into the governor returned on that
      call. An independent review drove the earlier version of this falsification and nothing went red.
      WHAT THE READ MODEL DERIVES IS NAMED RATHER THAN CLAIMED AWAY: what remains against a window's
      budget, the window's state label and the posture label are computed here, they are presentation
      rather than pacing arithmetic, and the suite says so.
  - id: AC4
    falsified_by: >
      Delete the survival section from the report in .veldo/budget_state.py, or report a half it
      could not read as zero instead of UNKNOWN, and the assertion that the report names what survives
      stopping right now - concluded artifacts, and claimed units whose claims age out - must go red.
    text: >
      LOSING A WINDOW MUST COST PACING AND NOT WORK, AND THE REPORT SAYS WHAT SURVIVES. On 2026-08-10
      and 2026-08-11 two sessions hit limits and 85 agents died mid-flight. What makes stopping safe
      now is not this item: it is that concluded work is ARTIFACTS on disk and a claimed unit's claim
      AGES OUT of the ledger, so the unit returns to the queue. This report names both, with the
      counts it measured, so an operator deciding whether to stop reads what is at risk instead of
      guessing. IT CLAIMS NOTHING IT DID NOT MEASURE, FOR BOTH HALVES: an absent corpus root is
      UNKNOWN rather than a corpus of zero, an unreadable ledger is UNKNOWN rather than nothing at
      risk, each is listed as a risk it could not measure, and a survival report about ANOTHER tree
      does not quote the running process's ledger as that tree's risk. "Nothing is at risk" and "I
      could not tell what is at risk" are opposite reassurances. NEGATIVE CONTROL: build the corpus
      and the ledger and the same read answers with real counts, including a real zero.
  - id: AC5
    falsified_by: >
      Remove the absent-configuration stand-down from .veldo/budget_state.py, or make any key of the
      report exist in one posture and not another, and the assertion that a repository configuring no
      window stands the report down by name while keeping ONE key shape must go red.
    text: >
      ADOPTION SAFE, AND IT PACES NOTHING. A repository that configures no budget window stands the
      report down by name: "nobody declared a budget here" is not "the budget is fine". The report
      carries ONE key shape with NO exception for a posture-dependent key, so a consumer reading
      resume_at outside the SPENT posture meets None rather than a KeyError. This module makes no
      pacing decision, spawns nothing and sleeps never, proved by an ALLOWLIST of the calls and
      imports it may contain rather than a denylist of the spellings someone thought of - a denylist
      let subprocess.run and os.system straight through. And NO GATE STAGE LOADS IT, asserted over the
      stages scripts/verify.sh actually runs and the modules they load, never by requiring that
      nothing in the repository uses it: an operator putting this read model on their path is the
      POINT of the item and must not redden the gate. NEGATIVE CONTROL: with a window configured the
      same report answers, so the stand-down is a measurement rather than the module's only behaviour.
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

The worker count, the windowed spend, the resume time, each window's target rate, the rule for what
counts as a recorded spend and the trailing-horizon cut all come from `.veldo/governor.py` by calling
it. The horizon cut is `windowed_spend` asked a different question - the same events with each
reading's value replaced by 1, so the governor counts the readings inside the horizon instead of
totalling them - because a local `t >= now - seconds` here would be a second spelling of the
governor's own line. A read model that reimplemented the pacing arithmetic would be two
implementations of one rule - the defect this repository has shipped more than once - and the failure
mode is the quiet one, because both copies look right until they disagree.

Which is exactly why the suite does not stop at equality. Equality against the governor's functions
is satisfied by a faithful copy-paste, so it can only ever catch a copy that has ALREADY diverged;
the duplication itself stays invisible. An independent review proved that by driving this item's own
declared falsification - a verbatim copy of `desired_workers` and `resume_at` inside the read model -
and watching the whole suite stay green. So the suite now intercepts the organ load and requires the
report's worker count and resume time to BE the values a call into the governor returned. What this
module genuinely derives - what remains against a window's budget, the window's state label, the
posture label - is named as derived instead of being covered by a blanket claim that was not true.

## What actually makes stopping safe

Not this item. Concluded work is artifacts on disk, and a claimed unit's claim ages out of the ledger
so the unit returns to the queue - the properties VELDO-0002 and VELDO-0003 landed. This report names
them and the counts it measured, so an operator deciding whether to stop reads what is at risk rather
than guessing, and it reports an absent ledger as unknown rather than as nothing at risk.
