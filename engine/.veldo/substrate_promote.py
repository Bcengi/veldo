#!/usr/bin/env python3
"""The promotion pipeline (WARP-1505, W5 of PLAN-0015).

A release is not an event, it is a proven change moving through declared environments in order.
This decides whether a given promotion may happen, what it must carry, and how far it may go in
one step.

FOUR RULES, and each fails closed.

**1. ORDER IS THE DECLARED ORDER, AND YOU MAY NOT SKIP.** Environments are ordered by
`substrate.ENVIRONMENT_ORDER` - the same list the declaration validator uses, so the pipeline and
the validator cannot disagree about which way is forward. Promotion goes one step at a time.
Straight to production from development is the move everyone regrets, and "we tested it in dev" is
what they say afterwards.

**2. NO ROLLBACK PLAN, NO PROMOTION.** Not a warning, not a note in the proof: a refusal. A
rollback plan written after something breaks is written by someone panicking, and a promotion whose
author could not say how to undo it has not finished thinking about it. It must name a method and
be non-trivial - the string "rollback" is not a plan.

**3. THE RISK CLASS DECIDES THE CEREMONY, NOT THE ENVIRONMENT.** A standard change into staging
needs a green gate. A critical change into production needs a canary, a staged rollout and a
recorded human approval. Keying on the destination alone would make every typo into production a
critical event and every database drop into staging a trivial one.

**4. A FAILED CANARY HALTS, AND HALTED IS NOT FAILED.** A canary that reports unhealthy stops the
promotion where it is, with the stages that already completed named. The distinction matters
operationally: a halted promotion has a known position to roll back from, and a promotion reported
as merely "failed" leaves somebody guessing how far it got.

WHAT THIS IS NOT. It performs no promotion and reaches no environment: it decides, and the caller
acts through the W2 adapter seam. Keeping the decision separate from the act is what lets every
rule here be proven offline against fake environments, which is the whole of this item's evidence.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STANDARD, HIGH, CRITICAL = "standard", "high", "critical"

# THE GATING TABLE (D3). What each risk class must carry to promote. Declared as data rather than
# spelled through conditionals so the requirement can be read, diffed and argued about in one place.
GATING = {
    STANDARD: {"gate_green": True, "canary": False, "staged": False, "human_approval": False},
    HIGH:     {"gate_green": True, "canary": True,  "staged": False, "human_approval": False},
    CRITICAL: {"gate_green": True, "canary": True,  "staged": True,  "human_approval": True},
}

# A rollback plan must say HOW. These are the methods the pipeline recognises; anything else is a
# sentence somebody wrote to satisfy a checker.
ROLLBACK_METHODS = frozenset({
    "redeploy_previous", "restore_snapshot", "reverse_migration", "traffic_shift_back",
    "recreate_from_declaration", "feature_flag_off",
})

REFUSALS = (
    "unknown_environment", "not_adjacent", "backwards", "no_rollback_plan",
    "rollback_plan_incomplete", "gate_not_green", "canary_required", "canary_unhealthy",
    "staged_rollout_required", "human_approval_required",
)


def _substrate():
    spec = importlib.util.spec_from_file_location("veldo_substrate_promote",
                                                  ROOT / ".veldo/substrate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rollback_problems(plan):
    """Why this rollback plan is not one, as a list. Empty means usable.

    A plan must name a recognised METHOD and say something specific. The check is deliberately
    shallow - it cannot know whether the method would work - but it does stop the two failures that
    actually happen: no plan at all, and a plan that is the word "rollback"."""
    if plan is None:
        return ["no rollback plan: a promotion whose author cannot say how to undo it has not "
                "finished being designed, and one written after the fact is written by someone "
                "panicking"]
    if not isinstance(plan, dict):
        return ["a rollback plan must be a mapping with a method and a description, got %s"
                % type(plan).__name__]
    out = []
    if plan.get("method") not in ROLLBACK_METHODS:
        out.append("rollback method %r is not one of the recognised methods %s"
                   % (plan.get("method"), sorted(ROLLBACK_METHODS)))
    d = plan.get("description")
    if not (isinstance(d, str) and len(d.strip()) >= 20):
        out.append("the rollback description must say something specific (at least 20 characters); "
                   "the word 'rollback' is not a plan")
    return out


def check(from_env, to_env, risk=STANDARD, rollback=None, gate_green=False,
          canary=None, staged=False, human_approval=None):
    """May this promotion proceed? Returns (ok, reason, detail).

    `canary` is None when none was run, True/False for its health. `detail` always carries the
    gating requirements for the class, so a refusal explains what the class demanded rather than
    only what was missing."""
    sub = _substrate()
    need = GATING.get(risk) or GATING[CRITICAL]      # an unknown class gets the strictest, not the loosest
    d = {"risk": risk, "requires": dict(need), "from": from_env, "to": to_env}

    i, j = sub.promotion_index(from_env), sub.promotion_index(to_env)
    if i < 0 or j < 0:
        return (False, "unknown_environment",
                "promotion is between DECLARED environments; %r or %r is not one of %s"
                % (from_env, to_env, list(sub.ENVIRONMENT_ORDER)), d)
    if j <= i:
        return (False, "backwards",
                "%r is not forward of %r in the declared order: a promotion moves toward "
                "production, and going back is a rollback, which is a different act with a "
                "different plan" % (to_env, from_env), d)
    if j != i + 1:
        return (False, "not_adjacent",
                "promotion is one step at a time: %r to %r skips %s. Straight to production is the "
                "move that gets regretted, and 'we tested it in dev' is what gets said afterwards"
                % (from_env, to_env, ", ".join(sub.ENVIRONMENT_ORDER[i + 1:j])), d)

    # THE ROLLBACK PLAN IS CHECKED BEFORE ANY CEREMONY, because a promotion nobody can undo should
    # be refused whether or not it would otherwise have qualified.
    rp = rollback_problems(rollback)
    if rp:
        return (False, "no_rollback_plan" if rollback is None else "rollback_plan_incomplete",
                "; ".join(rp), d)

    if need["gate_green"] and not gate_green:
        return (False, "gate_not_green",
                "only a PROVEN change promotes: the gate must be green on the exact change being "
                "promoted", d)
    if need["canary"]:
        if canary is None:
            return (False, "canary_required",
                    "a %s change requires a canary before the full rollout" % risk, d)
        if canary is False:
            return (False, "canary_unhealthy",
                    "the canary reported unhealthy: the promotion HALTS here rather than "
                    "continuing, so there is a known position to roll back from", d)
    if need["staged"] and not staged:
        return (False, "staged_rollout_required",
                "a %s change rolls out in stages, not at once" % risk, d)
    if need["human_approval"] and not human_approval:
        return (False, "human_approval_required",
                "a %s promotion needs a recorded human approval" % risk, d)
    return (True, "may_promote",
            "%s change may promote from %s to %s" % (risk, from_env, to_env), d)


def path(from_env, to_env):
    """The environments a change must pass through, in order, to get from one to the other.
    Empty when the destination is not forward of the origin - a promotion path backwards does not
    exist, and returning one would invite a caller to walk it."""
    sub = _substrate()
    i, j = sub.promotion_index(from_env), sub.promotion_index(to_env)
    if i < 0 or j < 0 or j <= i:
        return []
    return list(sub.ENVIRONMENT_ORDER[i + 1:j + 1])
