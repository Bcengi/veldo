---
schema: veldo.spec/v1
id: VELDO-0263
title: A workflow step declares its failure policy, bounded retry with backoff, a timeout and a failure path, every attempt and timeout is journaled against the unit's revision, and no outward or outside-writing step is ever retried automatically
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0068, VELDO-0132, VELDO-0141, VELDO-0154, VELDO-0160, VELDO-0240, VELDO-0241, VELDO-0244, VELDO-0245, VELDO-0247, VELDO-0251, VELDO-0262]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - ".veldo/control_graph_steps.py"
  - "engine/.veldo/control_graph_steps.py"
  - "packs/*/.veldo/control_graph_steps.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_account_limit.py"
  - "engine/.veldo/control_account_limit.py"
  - ".veldo/control_store*.py"
  - "engine/.veldo/control_store*.py"
  - ".veldo/control_schedule*.py"
  - "engine/.veldo/control_schedule*.py"
  - ".veldo/control_event_vocabulary.py"
  - "engine/.veldo/control_event_vocabulary.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0263_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0263-a-step-declares-its-failure-policy.md"
  - "specs/index.md"
  - "proof/VELDO-0263/**"
behavior_bearing: true
observability:
  logs: >
    A refused save records every named problem with the node and the policy field at fault. Every
    attempt of a step records the unit, the workflow id, version and digest, the node, the attempt
    number and the declared attempt limit, the worker run it dispatched (if any), its start and end,
    and its outcome; a failed attempt adds its failure class, its detail, and the decision taken
    (retry at a stated due time, failure path to a named node, or put to the owner) with the rule
    that decided it. A timeout records the declared bound, the elapsed seconds, how the work was
    stopped and whether the stop was confirmed. A step refused a retry records why by name
    (outward_step, outside_write_recorded, class_not_retryable, attempts_exhausted, budget_exhausted).
    No secret is logged; a private field's value is logged only as its digest, as VELDO-0247 does.
  metrics: >
    Counted from the journal, never kept as a second record: attempts per step, retries per step and
    failure class, timeouts per step, failures that took the failure path, failures put to the owner,
    and the wait time spent in backoff. VELDO-0265 reads these from the same events.
  traces: >
    Every attempt joins to its unit, its cycle, its bound revision {id, version, digest}, its node and
    its attempt number; a retry links to the attempt it repeats, and a failure path transition links
    to the failed attempt that caused it.
  error_taxonomy: >
    New step failure classes, each mapped onto the existing classes of control_service.CLASSES so no
    caller's classification moves: step_timeout (unavailable_service), worker_failed (unavailable_service),
    and the existing named failures keep theirs. New save problems, each with the node named:
    failure_policy_invalid, retry_on_outward_step, retry_on_outside_write_kind, retry_class_unknown,
    timeout_out_of_bounds, failure_path_invalid. New run refusals: outside_write_recorded (an attempt
    called a write the record shows, so it is put to the owner and never retried), attempts_exhausted,
    budget_exhausted. account_limit keeps VELDO-0160's meaning and is never counted as an attempt.
acceptance_criteria:
  - id: AC1
    text: >
      The policy is closed data in the revision and is checked at save. A node may carry an optional
      `failure` section, exactly {attempts, backoff, timeout, retry_on}, every field optional:
      attempts an integer from 1 to ATTEMPT_CEILING (declared beside STEP_CEILING and FAN_OUT_CEILING),
      default 1; backoff exactly {first, factor, most}, seconds and a factor within fixed bounds, the
      wait before attempt n being min(most, first * factor^(n-2)) plus a jitter of up to one tenth of
      that wait derived from the sha256 of the unit id, node and attempt, so it is spread across units
      yet reproducible; timeout in seconds within the bounds the step kind declares (a kind with no
      declared bound refuses a timeout); retry_on a list drawn from the closed retryable set
      (worker_failed, step_timeout, unavailable_service), never unknown_outcome, missing_authority,
      stale_subject, invalid_input or missing_evidence. A node may also have a `failed` port with one
      transition: its failure path. STEP_KINDS gains a `writes_outside` mark beside `outward`, set for
      every outward kind (land, deliver, publish, deploy) and for every kind that may call a write
      through the outside gate (VELDO-0251), including tracker and channel writes; a node of a kind
      marked outward or writes_outside with attempts above 1 or a non-empty retry_on is refused. The
      failure path is an ordinary path to VELDO-0241's approval walk and VELDO-0247's block rules:
      the walk follows every failed port, so a failure path that reaches an outward step without the
      approval naming it, or with a subject-changing step after that approval, is refused with the
      approval walk's own named problem; a failed port inside a parallel branch must stay in the
      branch or end the cycle. Rows: each field out of bounds, an unknown key, a retryable class
      outside the set, attempts 2 on land, attempts 2 on a kind marked writes_outside, a timeout on a
      kind with no bound, and a failure path from review straight to land are each refused with the
      named problem and no revision is written; the same definitions within the rules are accepted,
      and a definition with no failure sections stores the same digest as before this spec.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the save check skips the writes_outside
      mark: the retry-on-outside-write row goes red; (2) the approval walk ignores failed ports: the
      failure-path-around-approval row goes red.
  - id: AC2
    text: >
      A retry is decided by the domain side against the unit's recorded revision, is journaled, and
      holds nothing while it waits. The step runner (VELDO-0262) only reports that a node failed and
      with which class; control_workflow_cycle reads the failed node's policy from the unit's pinned
      revision, never from the head, and decides: retry when the class is in retry_on, attempts remain,
      the cycle's step budget has room (every attempt counts one step, so retries cannot run past the
      budget), and the attempt's record shows no call to an outside write (VELDO-0160's rule, read from
      the same record); otherwise the failure path when the node has one; otherwise the owner, through
      the ordinary decision flow (VELDO-0068), naming the node, the attempts and the last failure. A
      retry's due time is a one-time occurrence of kind workflow_retry in VELDO-0240's schedule store,
      targeting the unit, node and attempt, as VELDO-0245's schedule step does with workflow_step: no
      second store, timer or list. The unit holds no worker, no account and no reservation until then;
      the service loop's one timer (VELDO-0154 AC4, VELDO-0240) wakes it, the once-only start record
      makes a restart of the authority between the failure and the due time lose no retry and run none
      twice, and a due time the service was down for is started late and recorded so, never skipped. A run classified account_limit follows VELDO-0160 and VELDO-0154 AC3
      unchanged and consumes no attempt. Each attempt is its own record in the execution record
      (VELDO-0141) and the canvas run view (VELDO-0246 AC4) reads them. Rows: a worker_failed node with
      attempts 3 is dispatched three times at the computed due times and then takes its failure path;
      the same node whose second attempt's record shows a write through the gate is put to the owner
      with outside_write_recorded and not tried a third time; a node with attempts 3 whose failure is
      unknown_outcome goes to the owner at once; a revision saved mid-unit with attempts 1 does not
      change the running unit's remaining attempts; a restart between attempts resumes at the stored
      due time; the jitter of two units at the same node differs and repeats exactly for the same unit.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) the cycle reads the policy from the
      workflow head: the mid-unit revision row goes red; (2) the retry decision ignores recorded
      outside writes: the outside-write-recorded row goes red; (3) an account_limit run consumes an
      attempt: the account-limit row, whose node has attempts 2 and is limited once, goes red because
      the node is put to the owner after its real failure instead of retried.
  - id: AC3
    text: >
      A timeout is enforced by the domain side and is a failure like any other. When a node with a
      timeout is dispatched, its deadline is stored with the attempt as a one-time occurrence of kind
      workflow_timeout in VELDO-0240's schedule store, cancelled when the attempt ends first; at the
      deadline the loop stops the attempt's worker run through the existing stop path the owner's stop
      uses (workers.stop), waits for the
      stop to be confirmed, and records step_timeout with the bound and the elapsed time. A stop that
      cannot be confirmed is recorded as such and the step is put to the owner with unknown_outcome,
      never retried. A step_timeout is then retried, takes its failure path or goes to the owner by
      AC2's rule; an owner_approval or owner_wait node with a timeout takes only its failure path or
      stays waiting, and a timeout can never grant, admit or answer for the owner. A result that
      arrives after its attempt timed out is recorded as late and discarded, never applied. Rows: a
      fixture worker that runs past a 2 second bound is stopped, recorded step_timeout and retried
      once; a worker that ignores the stop leaves the step with the owner as unknown_outcome; an
      approval with a timeout and a failure path to a notify step reaches it without granting; a late
      result after a retry has started changes nothing.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) a timeout on an owner_approval node
      takes the granted port: the approval-timeout row goes red; (2) a result arriving after its
      attempt timed out is applied: the late-result row goes red.
  - id: AC4
    text: >
      An outward or outside-writing step is never retried automatically, whatever the revision says
      and whatever the runner answers. Beyond the save refusal of AC1, the cycle itself refuses to
      redispatch a node of a kind marked outward or writes_outside after a failure, and puts the
      failure to the owner naming the node, the attempt, its record of outside calls and the outcome
      known so far; a revision written before the mark existed, or a stored definition edited outside
      workflows.save, is held to the same rule at run because the rule reads STEP_KINDS, not the
      policy. A land refused by a moved trunk keeps VELDO-0148's own re-land edges, which are
      transitions of the definition, not retries, and are unchanged. Rows: a stored revision forged
      with attempts 3 on deploy fails once and is put to the owner without a second dispatch; a forged
      runner answer that names the same land node again after its failure is refused by the cycle as
      a transition the revision does not have; VELDO-0148's re-land rows pass unchanged.
    falsified_by: >
      A registered mutation in which the cycle trusts the stored policy instead of STEP_KINDS for the
      outward check, with a green baseline: the forged-deploy-retry row goes red because deploy is
      dispatched twice.
required_evidence: [unit, integration]
rollback: >
  Revert the commits. The failure section and the failed port are unregistered, so a stored revision
  that uses them no longer validates and a unit bound to it stops at its next station with
  missing_workflow and is put to the owner; a pending retry's due time is then ignored and the unit is
  put to the owner. Stored revisions, attempt records and journal entries stay as written. No automatic
  rollback, retry or recovery is authorized.
---

## Intent

A factory runs unattended for hours, and today each kind of failure is handled by a special case its
own spec wrote. The author of a workflow cannot say, per step, "a render that fails may be tried twice
more, five minutes apart; a review that takes longer than an hour is a failure; a publish that fails
goes to me". This gives every step an optional, closed failure policy in its revision: bounded retry
with backoff, a timeout and a failure path. Two rules keep it inside Veldo's authority model: nothing
outward and nothing that writes outside the factory is ever retried automatically, and every attempt is
journaled against the revision the unit runs.

## Context

Owner, Telegram 39631 to 39633 (2026-11-07): on the comparison of Veldo with n8n, asked for tickets for
step failure policy, sub-workflows and fan-out, and run insights first. This is the first; it is gap 1
of research/veldo-n8n-gaps-2026-11-07.md in the owner's research folder.

What is there today. Failure handling is scattered: a land refused by a moved trunk is re-landed
(VELDO-0148), a run stopped by an account limit is re-run or put to the owner (VELDO-0160, carried out
by VELDO-0154 AC3), a gate red under someone else's load is rerun quietly (VELDO-0223), and a declined
assignment asks the owner what becomes of the work (VELDO-0133). VELDO-0246's canvas already draws "a
failed attempt that was retried" (its AC4), but no spec lets a definition declare one. VELDO-0132
stores revisions as closed data with registered step kinds and STEP_CEILING; VELDO-0241 makes a unit's
process such a revision, pins it per unit and walks every path for the approval; VELDO-0247 adds checks,
branches, joins and FAN_OUT_CEILING. VELDO-0262 replaces LangGraph with Veldo's own deterministic step
runner, which reads no clock; this spec is written against that runner and keeps it deterministic: the
runner reports a failure, and the domain side, which owns time, decides what follows.

Design decisions.
- The retry decision lives in control_workflow_cycle, not in the runner, so the runner stays free of
  clocks and the decision is re-judged against the unit's pinned revision like every transition.
- Waiting for a retry holds nothing. The due time is an occurrence in VELDO-0240's schedule store,
  woken by the service loop's one timer, as VELDO-0245 does for a schedule step, so a long backoff costs
  no worker, account or reservation, adds no timer or poll, and a restart neither loses nor doubles a
  retry.
- Jitter is derived from a digest of the unit, node and attempt, not from randomness. Many units
  failing together on one outside outage spread their retries, and each unit's schedule can be
  replayed exactly.
- The outward rule reads STEP_KINDS at run time as well as at save, so a forged or older revision
  cannot buy a retry of a deploy. The record of outside calls is VELDO-0160's, so one rule decides
  both an account-limit re-run and a policy retry.
- A timeout stops work through the same stop path the owner uses, and a stop that cannot be confirmed
  is an unknown outcome for the owner, never a retry, because the first attempt may still be running.

Dependency on landing-b and VELDO-0262. VELDO-0241 and VELDO-0247 as built are in the landing-b batch,
not on main at afa292f0; VELDO-0262 is ready and is built after landing-b lands. This spec is built after
VELDO-0262, on the main that carries all three, and after VELDO-0240's schedule store and VELDO-0245's
workflow_step occurrence, whose store, timer and once-only start record it reuses. The writes_outside mark covers the kinds VELDO-0242 to
VELDO-0245 register; a kind registered later declares its mark when it is registered.

## Out of scope

A factory-level default failure workflow that every project inherits (n8n's error workflow); it is a
later spec on this shape and on VELDO-0264's call step. Retrying a step from a different account than
VELDO-0160 chooses. Retrying the gate itself (VELDO-0223 keeps its own rule). Any change to the save
rules of VELDO-0241 and VELDO-0247 other than following failed ports. Canvas palette and inspector
entries for the policy, which belong to VELDO-0246 and read this spec's named problems. Persistent
checkpoints of a cycle beyond what the unit record already holds (Release 2).

## What the reviewer judges

- Normal use: the owner sets "render: 3 attempts, 5 minutes apart, doubling, at most 30 minutes;
  review: time out after 1 hour; publish: on failure, ask me", sees each attempt and its reason in the
  run view, and is asked about a publish failure with what is known about it.
- Threat model: a revision that retries a deploy or a tracker write; a forged stored revision or
  runner answer that tries the same; a failure path that skips the approval; a timeout that grants an
  approval; a late result applied after a retry began; a retry storm from many units at once; a
  restart that doubles or loses a retry; an account-limit run that eats the attempts the author gave.
- The policy stays plain closed data, readable as one sentence per step, with every bound declared
  beside STEP_CEILING and nothing evaluated.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-07: drafted under owner Telegram 39631 to 39633 (the n8n comparison and its recommendation:
tickets for step failure policy, sub-workflows and fan-out, and run insights first), from main at
afa292f0, VELDO-0241 and VELDO-0247 as written in the landing-b batch, and VELDO-0262 as ready. Built
after landing-b lands and after VELDO-0262. Standalone; no plan work item.
