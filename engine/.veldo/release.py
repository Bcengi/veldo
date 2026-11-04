#!/usr/bin/env python3
"""VELDO release and rollback automation (reference wiring).

A release is a staged rollout: an ordered list of stages (for example canary,
then partial, then full), each carrying a traffic percentage, a set of feature
flags to enable or disable, and a health gate. A stage is promoted only when its
health gate passes; the first stage whose health fails halts the rollout and
triggers an EXECUTABLE rollback to the last-good stage (the baseline when the
very first stage fails, which is a full rollback). The rollback drives the
deploy surface, is idempotent, and is observed, never merely logged.

The deploy surface is a seam: a Deployer exposes deploy(stage), set_flag(name,
value), health(stage), and rollback(to). LiveDeployer is the reference live
impl; it has no real deploy surface of its own and fails LOUD rather than
pretend a deployment happened, so an adopting repo must wire it to a real
target, flag store, and health endpoint. The control logic below (roll_out,
reconcile_flags, execute_rollback, gate_respected) is pure orchestration over
the seam and is gate-tested with a fake deployer, with no live surface.

This ships as reference wiring: the veldo home repo has no deploy target of its
own to roll out, so the honest evidence is the fake-deployer control-logic test,
never a live rollout.
"""


class Stage:
    """One rollout stage: a name, a traffic percentage, the feature flags this
    stage sets (flag name -> desired boolean), and an optional per-stage health
    callable. When no callable is given the runner asks the deployer for the
    stage's health, so health is always a real observation, never assumed."""

    def __init__(self, name, percent, flags=None, health=None):
        if not name or not isinstance(name, str):
            raise ValueError("stage name must be a non-empty string")
        if not isinstance(percent, (int, float)) or not (0 <= percent <= 100):
            raise ValueError("stage percent must be a number in 0..100")
        self.name = name
        self.percent = percent
        self.flags = dict(flags or {})
        self.health = health

    def __repr__(self):
        return f"Stage({self.name!r}, {self.percent})"


class ReleasePlan:
    """An ordered list of stages plus the baseline the rollout returns to on a
    full rollback. Stage names must be unique so promotion and rollback targets
    are unambiguous."""

    def __init__(self, stages, baseline="baseline"):
        stages = list(stages)
        if not stages:
            raise ValueError("a release plan needs at least one stage")
        names = [s.name for s in stages]
        if len(set(names)) != len(names):
            raise ValueError("stage names must be unique within a plan")
        if baseline in names:
            raise ValueError("baseline must not collide with a stage name")
        self.stages = stages
        self.baseline = baseline

    @classmethod
    def from_dict(cls, data):
        """Build a plan from a JSON-shaped dict: {baseline?, stages: [{name,
        percent, flags?}]}. Health comes from the deployer at run time, so a
        declarative plan carries no callable."""
        raw = data.get("stages")
        if not isinstance(raw, list) or not raw:
            raise ValueError("plan dict needs a non-empty 'stages' list")
        stages = [Stage(s["name"], s["percent"], s.get("flags")) for s in raw]
        return cls(stages, baseline=data.get("baseline", "baseline"))


class Deployer:
    """The deploy-surface seam. A concrete deployer drives a real target; the
    runner talks only to this interface so the control logic stays surface
    agnostic and testable with a fake."""

    def deploy(self, stage):
        raise NotImplementedError

    def set_flag(self, name, value):
        raise NotImplementedError

    def health(self, stage):
        raise NotImplementedError

    def rollback(self, to):
        raise NotImplementedError


class LiveDeployer(Deployer):
    """Reference live deployer. It ships with NO real deploy surface, so every
    operation fails loud with an explanatory error rather than pretend. An
    adopting repo subclasses this (or passes a configured surface object) to
    wire a real deploy target, feature-flag store, and health endpoint. Failing
    loud is deliberate: a rollout that silently no-ops against a missing surface
    is more dangerous than one that refuses to run."""

    def __init__(self, surface=None):
        self.surface = surface

    def _require(self, op):
        if self.surface is None:
            raise RuntimeError(
                f"release: no live deploy surface configured; cannot {op}. "
                "LiveDeployer needs a real deploy target, feature-flag store, "
                "and health endpoint wired per repository. Refusing to pretend "
                "a deployment happened."
            )
        return self.surface

    def deploy(self, stage):
        return self._require(f"deploy stage {getattr(stage, 'name', stage)!r}").deploy(stage)

    def set_flag(self, name, value):
        return self._require(f"set flag {name!r}").set_flag(name, value)

    def health(self, stage):
        return self._require(f"check health of {getattr(stage, 'name', stage)!r}").health(stage)

    def rollback(self, to):
        return self._require(f"rollback to {to!r}").rollback(to)


def stage_health(stage, deployer):
    """A stage's health is a real observation: its own callable when present,
    otherwise the deployer's live health check. The boolean is coerced so a
    truthy-but-nonboolean surface answer is treated honestly."""
    if stage.health is not None:
        return bool(stage.health())
    return bool(deployer.health(stage))


def cumulative_flags(stages):
    """The flag state produced by applying an ordered list of stages in turn
    (later stages win). This is the correct flag configuration for a rollout
    that reached exactly the given stages, and the target the runner reconciles
    to on a rollback."""
    state = {}
    for s in stages:
        for name, value in s.flags.items():
            state[name] = value
    return state


def reconcile_flags(deployer, failed_stage, good_flags):
    """Clear the failed stage's flags back to the last-good configuration. Any
    flag the failed stage set that is not part of good_flags is disabled;
    otherwise it is driven to its good value. This is observable (each set_flag
    is a real call on the deployer) and idempotent (reconciling twice issues the
    same corrections)."""
    for name in failed_stage.flags:
        deployer.set_flag(name, good_flags.get(name, False))


def execute_rollback(deployer, to):
    """Executable, idempotent rollback: drive the deployer to `to`. Calling it
    again with the same target re-asserts the state and does not diverge, which
    is what makes a rollback safe to retry after a partial failure."""
    deployer.rollback(to)
    return to


def gate_respected(result):
    """The rollout invariant, as a pure predicate over a result: every promoted
    stage was observed healthy. A runner that promotes a stage despite a failed
    health gate produces a stage_log entry that is promoted yet unhealthy, and
    this returns False. The real runner cannot produce such an entry, so this is
    the assertion a promote-anyway mutation would fail."""
    return all(entry["healthy"] for entry in result["stage_log"] if entry["promoted"])


def roll_out(plan, deployer):
    """Drive a staged rollout over the deploy seam.

    Promote a stage only if its health gate passes. On the first health
    failure, halt: do NOT promote the failing stage, execute a rollback to the
    last-good stage (the plan baseline if nothing was promoted, i.e. a full
    rollback), reconcile feature flags back to the last-good configuration, and
    report the failure. Returns an observable result dict; result["ok"] is False
    exactly when a stage halted the rollout."""
    baseline = plan.baseline
    result = {
        "promoted": [],
        "stage_log": [],
        "halted_at": None,
        "rolled_back_to": None,
        "final_stage": baseline,
        "ok": True,
        "flags": {},
    }
    last_good = baseline
    promoted_stages = []

    for stage in plan.stages:
        deployer.deploy(stage)
        # feature-flag hooks: enable/disable this stage's flags before the gate
        for name, value in stage.flags.items():
            deployer.set_flag(name, value)

        healthy = stage_health(stage, deployer)
        entry = {"name": stage.name, "percent": stage.percent,
                 "healthy": healthy, "promoted": False}

        if healthy:
            entry["promoted"] = True
            result["promoted"].append(stage.name)
            promoted_stages.append(stage)
            last_good = stage.name
            result["stage_log"].append(entry)
            continue

        # health failed: halt and roll back to the last-good stage
        result["stage_log"].append(entry)
        result["ok"] = False
        result["halted_at"] = stage.name
        good_flags = cumulative_flags(promoted_stages)
        execute_rollback(deployer, last_good)
        reconcile_flags(deployer, stage, good_flags)
        result["rolled_back_to"] = last_good
        result["final_stage"] = last_good
        result["flags"] = good_flags
        return result

    # every stage promoted: the rollout reached full
    result["final_stage"] = last_good
    result["flags"] = cumulative_flags(plan.stages)
    return result
