# VELDO-0261 evidence

Three intermittent gate rows become deterministic, and a busy store is refused by its own name. The diagnosis is
`diagnosis.md`. The full gate is not run here; the lead runs it under the gate lock. Each result below is a
single-suite run of `scripts/selftest.py --suite NAME`, PARTIAL by construction and not a green gate, or a run of
the gate's mutation driver for named cases. Every suite run was made under `flock` on the gate lock
(`~/.local/state/core-gates/.gate.lock`). Home paths are written "~".

## What was built

- `proof/VELDO-0127/delivery_fixture.py` and `scripts/suites/87_veldo_0127_codex_delivery.py` (AC1): every row a
  worker will judge is registered before its first case (`plan`: the qualified models, the capabilities read
  from the production module's own `CODEX_CAPABILITIES` literal, the three stop cases and the save case). Each
  case runs inside its own capture (`case`), the configuration bind and the MCP credential resolve included. A
  caught exception is kept whole (`Failure`: the fixture step, type, code, full message and formatted traceback,
  carried after the row name's colon). Setup is its own row, `delivery/setup`, naming the step that failed. A
  registered row no judgment reached is red with "not reached" and the step and exception that stopped it.
  `delivery/completed` means every registered row was judged. The suite prints each case's slowest step.
  No timeout, bound or sleep changed in the fixture or in production.
- `scripts/suites/shared.py` (AC2): `wait_for(condition, bound, what)`. It polls an observable condition, returns
  None as soon as it holds, and on expiry returns a report naming what it waited for, the bound and its source,
  the elapsed seconds and the last observation. It only reads; it never sleeps a fixed time or repeats an action.
- `scripts/suites/62_veldo_0039_dispatch.py` (AC2): `settle_stopped` waits with `wait_for` for the stopped
  dispatch's record to leave the stoppable states, bounded by the product's own end obligation (the later of the
  contract deadline and the receiver's announced end, plus `control_launch.ACCEPT_SECONDS`), and only then
  settles it with `runner.wait`. The rows judge the cause (`stop_cause`: exited, stop result asked, no deadline
  stop, supervision cause `requested`); the elapsed time below 40 s is no longer asserted. The observations row
  states its expected unknown set as the three dispatches made unknown on purpose and names each extra or
  missing one with its state and the region that made it (`born`). A false row of the suite carries its
  evidence after its colon.
- `scripts/suites/38_veldo_0025_membership.py` (AC3, AC4): the race row is three rows over the same real
  processes, store and signatures: `one-transition/overlapped` (each racer's admission gets a store adapter that
  delegates every call to the real store module and, at its commit, records its arrival and waits for the
  parent's release on standard input; the parent waits for both arrivals with `wait_for`, bound the racer's own
  180 s process timeout, then releases both), `one-transition/sequential` (the second racer starts after the
  first answered) and `one-transition/kill-replay` (the kill after commit and the replay, as before). Each racer
  prints its code, its full detail and its arrival and answer moments. The unit row `VELDO-0261 AC4
  store/busy-store-named`.
- `.veldo/control_store.py` (AC4, engine copy byte-identical): `write_refusal` names a refused write by the
  database's own primary error code: SQLITE_BUSY is `store_busy`, SQLITE_READONLY is `read_only_handle`. Every
  write transaction begin (`_begin`: execute and the five ownership and binding commands) and the two write
  handlers that matched message text (execute's and `_write`'s) use it. `store_busy` is in `REFUSALS`.
- `.veldo/control_alias.py`, `.veldo/control_service.py` (engine copies byte-identical): their taxonomy maps name
  `store_busy` as `unavailable_service` beside `read_only_handle`.
- `scripts/check_teeth_mutations.py`: the falsifiers (finding 261), and `launch131-stop-recorded-unasked` now
  names both stop rows.

## Results

All runs below are at HEAD 93e13646, 2026-11-06, each under `flock` on the gate lock. A suite run exits 2 by
construction (PARTIAL); its outcome is its own row count.

### Suites, one run each

- 87_veldo_0127_codex_delivery (AC1): 194 rows, 194 passed, 0 failed, 85.78 s.
- 62_veldo_0039_dispatch (AC2): 25 rows, 25 passed, 0 failed, 9.51 s.
- 38_veldo_0025_membership (AC3, AC4): 20 rows, 20 passed, 0 failed, 1.90 s.

The AC4 unit row `VELDO-0261 AC4 store/busy-store-named` is a row of suite 38 and passed in that run (busy:
store_busy; read-only: read_only_handle).

Per AC:

- AC1: every registered row of suite 87 passed, `delivery/setup` and `delivery/completed` included; the
  suite printed the slowest step of each case (for every launched case the slowest step is the receiver
  baseline, 0.745 s to 1.338 s).
- AC2: `dispatch/owner-stop`, `dispatch/owner-stop-other-runner`, `dispatch/observations` and
  `dispatch/deadline-after-closed-output` passed with the rest of suite 62.
- AC3: `membership/one-transition/overlapped`, `membership/one-transition/sequential` and
  `membership/one-transition/kill-replay` passed.
- AC4: `store/busy-store-named` passed.

### Falsifiers, through the gate's mutation driver

`python3 scripts/check_gate_mutations.py --case NAME ...` for the ten cases at once: status passed, registered
10, executed 10, rejected 10, invalid 0, 193.0 s; the three suite 62 cases ran in the unconfined leg
(`scripts/gate_unconfined.json`). For every case the driver ran the unmutated suite first (green: no failed
row) and then the mutant (red: every named row false). The mutants are temporary copies, so the source stays
as committed and the suites above are the restored green.

- AC1 (1), `delivery261-keystore-exits-for-one-model`: baseline green; mutant: `delivery/gpt-6-astra/jira`,
  `stop/gpt-6-astra/missing`, `extra`, `mcp` red, "not reached ... step credential resolve: Undeliverable code
  credential_unavailable:jira" with the traceback; nothing else red, `delivery/completed` green.
- AC1 (2), `delivery261-setup-raises`: baseline green; mutant: `delivery/setup` and every registered row red (193
  of the suite's 194), each naming "step factory: RuntimeError ... defect: factory setup raises" with the
  traceback; `delivery/completed` green (every row was judged).
- AC1 (3), `delivery261-bind-raises-after-first-case`: baseline green; mutant: the rows after the first case red as
  "not reached: case ... stopped at step configuration bind: RuntimeError ..." with the traceback, none absent.
- AC2 (1), `launch131-stop-recorded-unasked`: baseline green; mutant: both stop rows red by cause: exited, deadline
  stop, cause deadline, signal 15; `dispatch/service-principals-only` also red.
- AC2 (2), `dispatch261-stop-message-ignored`: baseline green; mutant: both stop rows red by cause: exited,
  deadline stop, cause deadline, signal 15; `dispatch/service-principals-only` also red.
- AC2 (3), `dispatch261-stop-leaves-record-running`: baseline green; mutant: both stop rows red with the wait
  report: "the receiver of dispatch/... ended (exit 0) with the record still running: nothing is left to record its
  end" (state unknown); `dispatch/observations` also red, naming the stray unknown dispatches.
- AC3 (1), `membership261-store-version-unchecked`: baseline green; mutant: `membership/one-transition/overlapped`
  red, only it.
- AC3 (2), `membership261-envelope-version-unchecked`: baseline green; mutant:
  `membership/one-transition/sequential` red, only it.
- AC4, `store261-busy-named-read-only`: baseline green; mutant: `store/busy-store-named` red (busy:
  read_only_handle).
- AC4, `store261-every-error-busy`: baseline green; mutant: `store/busy-store-named` red (read-only: store_busy).

### Still open

- The full gate is not run here; the lead runs it.
- A first attempt ran the falsifiers through `scripts/check_teeth_mutations.py` directly. That entry does not
  apply the unconfined leg, so the three suite 62 cases ran confined, where no dispatch can launch its
  transient unit: every launch was refused and their baselines were invalid. That was the wrong entry, not a
  product or suite failure; the run above through the gate's entry is the result. The seven other cases
  passed in that attempt as well.
- The ten consecutive runs of each suite named in the build brief are not recorded in this bundle.
