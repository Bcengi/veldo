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
- AC2 (3), `dispatch261-stop-leaves-record-running`, as registered at 66f23c71 (the receiver exits on a stop):
  baseline green; mutant: both stop rows red with the dead-receiver message "the receiver of dispatch/... ended
  (exit 0) with the record still running: nothing is left to record its end" (state unknown), which is not the
  wait report: the wait ended on its first poll and its expiry branch never ran. `dispatch/observations` also red,
  naming the stray unknown dispatches. Superseded by fix round 1 below.
- AC3 (1), `membership261-store-version-unchecked`: baseline green; mutant: `membership/one-transition/overlapped`
  red, only it.
- AC3 (2), `membership261-envelope-version-unchecked`: baseline green; mutant:
  `membership/one-transition/sequential` red, only it.
- AC4, `store261-busy-named-read-only`: baseline green; mutant: `store/busy-store-named` red (busy:
  read_only_handle).
- AC4, `store261-every-error-busy`: baseline green; mutant: `store/busy-store-named` red (read-only: store_busy).

### Fix round 1 (independent check, AC2 finding)

The check found that falsifier (3) never ran `wait_for`'s expiry branch, and that nothing else did either. Changed
at 349e227d:

- `dispatch261-stop-leaves-record-running` now leaves the receiver alive and the record running on a stop (the
  receiver sleeps where it would begin the requested stop). The product's bound is shortened on the mutant copy
  only, by two further replacements: the receiver announces its contract deadline as its end (no graces or
  settle), and the module the suite loads allows 2 s to accept (`ACCEPT_SECONDS = 2` outside `__main__`, so the
  launch's own acceptance keeps its 30 s). Row names unchanged.
- `scripts/suites/38_veldo_0025_membership.py`: unit row `VELDO-0261 AC2 wait/expiry-report` drives the expiry
  branch directly: the shared module's own `wait_for`, read from the file the anchor `ROOT / "scripts/suites" /
  "shared.py"` names, with a condition that never holds and a 0.3 s bound; it asserts what, the bound, its
  source, the elapsed seconds (at least the bound, at most the time measured), the last observation (the last
  poll's) and that it polled more than once.
- New falsifier `wait261-expiry-returns-none` (`shared.py`, dir `scripts/suites`): the expiry branch returns
  None; declared row `wait/expiry-report`.

Runs at 349e227d, 2026-11-06, each once under `flock` on the gate lock:

- 62_veldo_0039_dispatch: 25 rows, 25 passed, 0 failed, 9.47 s.
- 38_veldo_0025_membership: 21 rows, 21 passed, 0 failed, 1.87 s (the 20 before plus `wait/expiry-report`).
- `python3 scripts/check_gate_mutations.py --case dispatch261-stop-leaves-record-running --case
  wait261-expiry-returns-none`: status passed, registered 2, executed 2, rejected 2, invalid 0, 96.7 s; the
  suite 62 case in the unconfined leg.
  - `dispatch261-stop-leaves-record-running` (77.2 s): baseline green (51 rows, 0 failed), noop copy green (51, 0
    failed); mutant: `dispatch/owner-stop` and `dispatch/owner-stop-other-runner` red with the wait report:
    "waited 31.5 s for dispatch dispatch/VELDO-9340/... to reach a terminal state, bound 31.5 s (the dispatch's
    end obligation: the later of its contract deadline and the end its receiver announced, plus
    control_launch.ACCEPT_SECONDS); last observed: {'state': 'running', 'receiver_exit': None}" (the other row
    the same for VELDO-9341), cause state unknown, asked True; `dispatch/service-principals-only` and
    `dispatch/observations` (naming the two stray unknown dispatches by region) also red.
  - `wait261-expiry-returns-none` (2.5 s): baseline green (47 rows, 0 failed), noop copy green (47, 0 failed);
    mutant: only `wait/expiry-report` red ("report: None; polls: 16; took 0.30 s").

The mutants are temporary copies; the source stays as committed, and the two suite runs above are the restored
green.

### Still open

- The full gate is not run here; the lead runs it.
- A first attempt ran the falsifiers through `scripts/check_teeth_mutations.py` directly. That entry does not
  apply the unconfined leg, so the three suite 62 cases ran confined, where no dispatch can launch its
  transient unit: every launch was refused and their baselines were invalid. That was the wrong entry, not a
  product or suite failure; the run above through the gate's entry is the result. The seven other cases
  passed in that attempt as well.
- The ten consecutive runs of each suite named in the build brief are not recorded in this bundle.
