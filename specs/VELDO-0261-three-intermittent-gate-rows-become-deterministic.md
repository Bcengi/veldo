---
schema: veldo.spec/v1
id: VELDO-0261
title: Three intermittent gate rows become deterministic, each waiting on what it checks and keeping the whole failure, and a busy store is refused by its own name
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0025, VELDO-0039, VELDO-0127, VELDO-0131]
placement: [loop, contracts]
protected_paths: [".veldo/control_launch.py", "engine/.veldo/control_launch.py", ".veldo/control_membership.py", "engine/.veldo/control_membership.py", ".veldo/authority_contract.py", "engine/.veldo/authority_contract.py", ".veldo/control_credential_keystore.py", "engine/.veldo/control_credential_keystore.py", ".veldo/control_agent_config_handoff.py", "engine/.veldo/control_agent_config_handoff.py", ".veldo/control_engine_codex.py", "engine/.veldo/control_engine_codex.py", ".veldo/control_dispatch.py", "engine/.veldo/control_dispatch.py", "scripts/check_gate_mutations.py"]
footprint:
  - "proof/VELDO-0127/delivery_fixture.py"
  - "scripts/suites/87_veldo_0127_codex_delivery.py"
  - "scripts/suites/62_veldo_0039_dispatch.py"
  - "scripts/suites/38_veldo_0025_membership.py"
  - "scripts/suites/shared.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_alias.py"
  - "engine/.veldo/control_alias.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/mutation_case_inputs.json"
  - "specs/VELDO-0261-three-intermittent-gate-rows-become-deterministic.md"
  - "specs/index.md"
  - "proof/VELDO-0261/**"
behavior_bearing: true
observability:
  logs: >
    A failed row of the three suites carries its evidence after the colon of its own row name, the
    form the mutation worker already keeps as failed_details, so a mutation baseline that fails says why
    in the gate log. A wait that runs out says what it waited for: the condition in words, the bound in
    seconds and where that bound comes from, the elapsed seconds, and the last state it observed. A
    caught exception is kept whole: its type, its code when it has one, its full message, the fixture step
    it was raised in, and its formatted traceback.
  metrics: >
    None added. The delivery suite keeps printing its total seconds; it also prints the slowest step of
    each case with its seconds, so a run under load shows where the time went.
  traces: >
    The two membership racers each write the moment they reached their commit and the moment they
    answered, so the row's detail shows the order the race actually took.
  error_taxonomy: >
    New store refusal store_busy: a write transaction could not begin because another writer held the
    store's write lock for the whole busy timeout. It classifies as unavailable_service, as read_only_handle
    does today, so no caller's classification moves. read_only_handle is kept for a handle that cannot write.
    No other refusal name or taxonomy changes.
acceptance_criteria:
  - id: AC1
    text: >
      The Codex delivery suite (suite 87, its fixture proof/VELDO-0127/delivery_fixture.py) keeps the whole
      failure and loses no row. (a) Before any case runs, the suite registers every row the run will judge,
      computed from the qualified models, the classified capabilities and the stop and save cases, never
      from what ran; a row the run never reached is red with the detail "not reached" and the step and
      exception that stopped it, so an exception can no longer remove the rows after it. (b) Every
      production call of a case runs inside the case's own capture, the configuration bind and the MCP
      credential resolve included (today both sit outside it), so a refusal or exception in one case reds
      that case's rows and the next case still runs. (c) Factory setup is its own row,
      delivery/setup, whose detail names the setup step that failed. (d) Every capture records the type,
      the code when present, the full message and the formatted traceback, and the row's detail carries
      them after the row name's colon; the 180 character cut and the stdout only report go. (e)
      delivery/completed means only that every registered row was judged. No timeout, bound or sleep in
      the fixture or in production changes.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) the fixture's keystore double exits
      nonzero for one model's MCP credential lookup: that model's jira and stop rows go red with detail
      naming credential_unavailable and the traceback, every other model's rows pass and delivery/completed
      stays green; (2) an exception raised in factory setup: delivery/setup and every registered row go red,
      each naming the setup step; (3) an exception raised in the configuration bind after the first case:
      the following rows are red as not reached with the exception in their detail, never absent. The
      existing role127 delivery mutations still red the rows they name.
  - id: AC2
    text: >
      The dispatch suite's two owner stop rows (suite 62, dispatch/owner-stop and
      dispatch/owner-stop-other-runner) wait on the observable end of the stopped dispatch instead of a
      fixed 25 second bound that, when it runs out, makes the suite itself end the receiver and record the
      dispatch unknown. A shared helper in scripts/suites/shared.py, wait_for(condition, bound, what),
      polls an observable condition, returns as soon as it holds, and on expiry returns a report naming
      what, the bound and its source, the elapsed seconds and the last observation; it never sleeps a fixed
      time and never retries the action under test. The rows wait, with that helper, for the dispatch's
      record to reach a terminal state, bounded by the product's own end obligation for that dispatch
      (the later of its contract deadline and the end its receiver announced, plus the accept allowance,
      the bound the launch already uses when no timeout is given), and only then settle it with the
      runner's wait. The rows judge the cause, not the speed: the record is exited, the stop request's
      result says asked, the termination says no deadline stop and the supervision's cause is the requested
      stop. The elapsed time below 40 seconds is no longer asserted. dispatch/observations states its
      expected set of unknown dispatches as the three the suite made unknown on purpose and, when the set
      differs, names in its detail each extra or missing dispatch with its state and the region that
      created it, so one row's failure is attributed to that row.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) the holding runner records the stop as
      asked without writing it to its receiver: both stop rows go red because the worker ends only at its
      contract deadline with a deadline stop, and the detail names the cause seen; (2) the receiver ignores
      a stop message: the same rows go red by cause; (3) a stop that leaves the record running past the
      product's bound: the rows go red with the wait report. The existing dispatch-closed-output mutations
      still red dispatch/deadline-after-closed-output.
  - id: AC3
    text: >
      The membership race row (suite 38, VELDO-0025 AC2 membership/one-transition) controls the order it
      claims instead of hoping two processes overlap. It becomes two rows over the same real processes,
      store and signatures. (a) one-transition/overlapped: each racer passes the admission a store adapter
      that delegates every call to the real store module and, when the admission calls its commit, records
      its arrival and waits for the parent's release; the parent waits for both arrivals with wait_for
      (bound: the racer's own process timeout) and then releases both. Exactly one commits; the other is
      refused store_refused with a stale_version detail naming the membership entity; the membership version
      advances by one. (b) one-transition/sequential: the second racer starts only after the first has
      answered; it is refused envelope_refused with a detail naming the stale membership version, and
      nothing is written. The kill after commit and the replay checks stay as they are, in a row of their
      own. Each racer prints its refusal code and its full detail, and its standard error is kept in the
      row's detail when it fails. A racer that never arrives fails the row with the wait report and that
      racer's exit status and standard error.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the store's expected version comparison
      disabled: the overlapped row goes red on every run because both racers commit (today the same
      mutation is caught only when the processes happen to overlap); (2) the envelope's membership version
      check disabled: the sequential row goes red because the second racer commits.
  - id: AC4
    text: >
      Product defect, found on the overlapped path: a write transaction that cannot begin because another
      writer holds the store's write lock past the busy timeout is refused read_only_handle today, the name
      of a handle that cannot write. Every write transaction begin in the store (execute and each ownership
      and binding command that begins one) refuses a busy lock as store_busy and keeps read_only_handle for a
      read-only handle, telling them apart by the database's own error code, never by message text. The
      refusal list and every caller's taxonomy map that names read_only_handle also name store_busy as
      unavailable_service. The engine copies stay byte-identical.
    falsified_by: >
      A unit row opens two writable handles on one store, holds the write lock on the first, and begins a
      command on the second with a short busy timeout: it must be store_busy; a read-only handle beginning a
      command must be read_only_handle. A mutation that maps the busy code back to read_only_handle reds the
      first; one that maps every error to store_busy reds the second.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The three suites return to their fixed waits and narrow captures and the store
  returns to one name for both causes. No stored record, journal entry or contract carries store_busy, so
  nothing written while the change was in place needs migrating.
---

## Intent

A landing candidate passed its full gate once and then failed three reruns of the same commit, each
time on a different row. A gate that reds at random teaches people to rerun it until it goes green, and
then a real regression is rerun away too. Each of the three rows must give the same answer on every run
of the same code, and when it is red it must say why in the gate log.

## Context

The diagnosis with line references is proof/VELDO-0261/diagnosis.md. In short:

- Suite 87 (delivery): a test assumption. An exception escaped the per launch capture during a run that
  took 166 seconds against 70 in the green run, on a host the mutation scheduler held near its full CPU
  capacity, and the whole run catch kept only its type and 180 characters, printed to a stdout the
  mutation worker discards. The exact exception cannot be recovered from the failed run. The calls that can
  raise outside the capture are the factory setup, the configuration bind and the MCP credential resolve;
  the ones that wait on a child process with a fixed bound are the setup's key generation (20 s), the
  bundled catalog and feature listing (30 s each) and the keystore lookup of the resolve (15 s). AC1 makes
  the next occurrence name itself and confines it to the case it happened in.
- Suite 62 (dispatch): a test assumption. A fixed 25 second wait for a stopped worker's end. When it ran
  out under load, the launch did what it is specified to do for a caller's timeout: it ended the receiver
  and recorded the dispatch unknown. That failed the other runner row, and the extra unknown dispatch then
  failed the observations row.
- Suite 38 (membership): a race in the test. The loser of the two process race is refused store_refused
  when it read the membership before the winner committed and envelope_refused when it read it after;
  both are the specified refusal of a stale version and in both exactly one change commits. The row
  required the first order.
- The product defect of AC4 did not cause the observed failure; it lies on the path AC3 makes
  deterministic, where a racer's commit waits on the other's write lock while that one signs its journal
  record inside the transaction.

## Out of scope

Any timeout, bound or retry in production code; the mutation scheduler's admission and resource claims;
the gate's concurrency; any other suite's waits.

## What the reviewer judges

- Each new wait returns on its condition and reports what it waited for; none is a fixed sleep, a longer
  constant or a retry of the action under test.
- Each falsifier is registered and reds its row from a green baseline.
- AC4 changes only the name of a refusal for a busy lock, by error code, in every write begin.

## History

2026-11-05: drafted from the three failed reruns of the landing candidate at ecacfd0a (gate logs
~/projects/myday/research/veldo-gate-landing-a2.log green, a3, a4 and a5 red). The gate lock was held
throughout the diagnosis, so no suite was run; the diagnosis is from the logs and the code.
