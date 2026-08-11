---
schema: veldo.spec/v1
id: WARP-0621
title: Two keys prove two humans authorised something, not that they authorised THIS execution against
  THIS system in THIS environment with THESE parameters on the world as it was and exactly once - bind
  those six facts and re-check every one of them at execution
status: shipped
risk: high - it adds a new refusal to the path that changes running production systems, and a blocking
  check that is wrong in the strict direction stops remediation during an incident, which is when
  remediation matters most. It extends `.veldo/action_executor.py`, the execution organ. It is not
  critical because the new guard is confined to the risky branch (irreversible, data-mutating, or
  two-key-declared): a reversible L2 action takes exactly the path it took before, unchanged.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W8
depends_on: [WARP-0616]
placement: [loop]
footprint:
  - ".veldo/execution_binding.py"
  - ".veldo/action_executor.py"
  - "engine/.veldo/execution_binding.py"
  - "engine/.veldo/action_executor.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/09_action_whitelist_warp_1205.py"
  - "specs/WARP-0621-risky-action-execution-binding.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      SIX FACTS ARE BOUND AND ALL SIX ARE RE-CHECKED AT EXECUTION, not at issue. An authorisation for a
      risky action binds target, system, environment, parameters, state_digest and proposal_digest, and
      `execution_binding.check` refuses with a DISTINCT NAMED reason for each one that no longer holds:
      `binding_target_mismatch`, `binding_system_mismatch`, `binding_environment_mismatch`,
      `binding_parameters_changed`, `binding_state_changed`, `binding_proposal_changed`. A selftest
      drives all six mismatches individually plus the happy path, so no single refusal can be carrying
      the others and the positive control proves the guard is not simply refusing everything.
      The bound-fact list is declared ONCE as `BOUND_FACTS`, and a selftest requires every member to
      have a check, so a seventh fact added without a check is a red rather than a silent hole.
  - id: AC2
    text: >
      EXPIRY AND REVOCATION END AN AUTHORISATION. Past `expires_at` refuses `binding_expired`; a record
      marked revoked refuses `binding_revoked` regardless of everything else. An authorisation is a
      moment, not a standing permission, and revocation forces a new one. Both driven by selftest.
  - id: AC3
    text: >
      THE NONCE IS SPENT EXACTLY ONCE, ATOMICALLY, AND BEFORE THE ACTION RUNS. `consume` uses
      `os.open` with `O_CREAT|O_EXCL`, so of two callers racing the same nonce exactly one gets True.
      Consumption happens BEFORE the run, never after, so a process dying mid-action cannot leave a
      replayable nonce: the failure mode is an action that ran at most once and may need
      re-authorising, which is the safe direction. A selftest drives the double-consume and requires
      `True` then `False`, and drives a replayed check to `binding_replayed`.
  - id: AC4
    text: >
      AN ABSENT BINDING ON A RISKY ACTION REFUSES, and this is the load-bearing choice. The executor
      fails closed on `execution_binding=None` for anything irreversible, data-mutating or
      two-key-declared. Optional would mean the entire guard is skipped by omitting an argument, which
      is the shape of every guard this repository has watched be defeated. A selftest drives the
      shipped `ActionExecutor.execute` with a risky remedy and no binding and requires the refusal.
  - id: AC5
    text: >
      THE REVERSIBLE PATH IS UNCHANGED, which is the required negative control. A strictly reversible,
      non-data-mutating action executes through the W6 single-confirmation path with no binding
      supplied and no new refusal, proving the change is confined to the risky branch and has not
      quietly raised the bar for ordinary remediation. A selftest drives a reversible action to
      `executed: True` with `execution_binding=None`.
  - id: AC6
    text: >
      IT EXTENDS THE EXECUTOR RATHER THAN REPLACING IT, and says what it is not. The W6 and W7 guards
      keep their order and their names; the binding is one additional step inside the existing risky
      branch. The module docstring states plainly that this is NOT a forgery defense - an agent that
      can write the repository can write a binding record, per WARP-0730 - and that what it buys is
      that an HONEST execution cannot drift from what was approved and that a replay requires an
      affirmative act. A selftest asserts that limit is present in the docstring, so a later reader
      cannot delete the honesty and keep the guard.
required_evidence: [unit]
rollback: >
  Revert the commit. The guard is confined to the risky branch and reads only arguments the caller
  passes, so reverting restores the W7 behaviour exactly. No persisted state beyond the consumed-nonce
  directory, which is write-only, never read by anything else, and harmless if left behind.
---

## Outcome

The two-key rule proves that two humans authorised something. It does not prove they authorised THIS
execution. A key bound only to a proposal digest still admits four moves nobody approved:

- run it against a **different system**
- run it in a **different environment**
- run it after the **world it was reasoned about changed**
- run it **again tomorrow**

Each of those is the same approved bytes doing a different thing, and each is a plausible incident
rather than a contrived one: the approver looked at a system degraded one way, and by the time the
key turns it is degraded another way.

## The design, and the one thing that makes it work

Six facts bound, all six re-checked **at execution rather than at issue**, because every one of them
can change in the gap. Checking at issue time proves what was true then; this answers "is it still
true".

Plus a nonce, consumed exactly once, which is what turns an authorisation from a standing permission
into an event. **`os.open` with `O_CREAT|O_EXCL` is the whole concurrency design**: the kernel
guarantees exactly one creator, so two executors racing the same authorisation cannot both proceed,
with no lock file, no daemon and no second store to keep consistent.

**Consumption happens before the run.** A process that dies mid-action then leaves a spent nonce and
the action needs re-authorising. That is the correct direction to fail: a risky action that runs
twice is worse than one that runs zero times and says so.

## What this is not

**Not a forgery defense.** An agent that can write the repository can write a binding record.
WARP-0730 settled that fight deliberately and WARP-0732 stated the same limit. What this buys is
that an honest execution cannot drift from what was approved, and that a replay requires an
affirmative act - deleting a consumed-nonce file - rather than merely doing nothing.

The claim is deliberately modest and the code says so, because overstating it is how the nine
rounds of forgery guards started.

## Out of scope

- Issuing bindings from the tracker side. This module mints no nonce and reads no clock; the caller
  supplies both, which keeps it a pure function and lets the selftest drive it deterministically.
- The reversible path. Untouched by construction, and AC5 is the control that proves it.
- WARP-0620 and WARP-0622, the remaining PLAN-0016 items. WARP-0620 needs a real board with the
  owner present and cannot be built by an agent at all.
