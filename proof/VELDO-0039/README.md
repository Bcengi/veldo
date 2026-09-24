# VELDO-0039 proof

Durable dispatch acceptance and launch records, PLAN-0019 revision 3 W24 (Release 1 stage 1). Branch
`build-veldo-0039`, built on d95a809. Specification status and every other specification are
unchanged.

## What landed

**The dispatch authority** (`.veldo/control_dispatch.py`, mirrored in `engine/.veldo/`, laid down by
`init_scaffold.py`). One registered store command commits every transition of a dispatch record
keyed by the dispatch identity VELDO-0036's worker slot and VELDO-0028's effect contracts already
use. Preparation records the complete contract: source commit and tree, input (the VELDO-0052
station decision's consumed inputs, its context and the payload), capability (adapter and the exact
configuration), reservation (the worker slot of the same identity, by version and digest), claim
(holder and generation), deadline and authority generation. An index entity holds one active
dispatch per unit and station; only `exited` or `refused` frees it, never `unknown`. Every later
observation must carry its dispatch's contract digest, and an exit the process identity `run`
recorded. Only an active `service` member whose scope covers the repository writes a record.

**The runner and the receiver** (`.veldo/control_launch.py`). The runner decides the station,
reserves the slot, resolves the source from real Git and commits the contract; only then does it
invoke the trusted receiver process. The receiver rechecks the station decision with the
preparation's decision as ticket, records its acceptance, spawns the worker with the recorded
configuration in the owner's environment plus the adapter's configured one, records the worker's
OS identity, reaps it by the deadline and records the termination (exit status and output digest,
nothing the worker printed). The worker's birth environment carries the journal digest of that
acceptance, which exists only once the acceptance has committed. A launch on another host runs over
the configured transport through `control_launch.py exec`, which reports its own identity on its
first line and then execs the engine.

## Rows (suite `62_veldo_0039_dispatch`, 18 rows: 10 assertions and 8 `ran/` rows)

**AC1.** `dispatch/contract-before-launch`: a real admitted unit (VELDO-0031 claim transition,
VELDO-0052 admission) submitted twice; the stored source, input, capability, reservation, claim and
deadline bindings equal what was supplied and what the store and Git hold; exactly one worker
launched; its birth environment names the acceptance's journal digest; the journal orders prepare,
accept, run. `dispatch/one-active-per-unit-station`: the second submission and a second complete
contract at the authority itself are refused `active_dispatch`, two runners racing on their own
connections launch one worker, and after the first exits the next attempt is attempt 2.

**AC2.** `dispatch/launch-results`: accepted (stored pid, start and boot id equal the worker's own
report and an independent `/proc` read), refused (`spawn_failed:ENOENT`, and a withdrawn admission
refused at the receiver's recheck), unknown (the receiver ends right after its acceptance commits;
recorded `unknown` with a stop owed), and a launch through the wrapper whose worker forges an
identity line. Each result is recorded under the one original identity.
`dispatch/unknown-never-relaunched`: after `unknown`, a new submission and a direct preparation are
refused `dispatch_outcome_unknown`, and the receiver refuses to launch the unknown or an exited
attempt again (`not_prepared`), recording nothing.

**AC3.** `dispatch/transitions-from-schema`: the matrix is derived from `STATES` and `TRANSITIONS`;
every allowed transition was walked by a real record (including a running dispatch whose receiver is
killed), every disallowed one is refused `transition_refused` with the record unchanged.
`dispatch/result-binding`: one worker's result applied to another running dispatch is refused
`binding_mismatch` and neither record moves. `dispatch/terminal-not-completion`: a worker that exits
0 claiming it landed, naming another dispatch, leaves no completion receipt, a completion reader
that says nothing is satisfied, and no text of its output in the record.

**Also.** `dispatch/service-principals-only`, `dispatch/observations` (events, taxonomy, pending and
stopped), `dispatch/installed-assets`.

## Red at the pre-fix code

`red.py d95a809` writes `red-d95a809.json`. At d95a809 the only launch path is VELDO-0052's
`StationCalls.launch` with VELDO-0036's `InvocationGuard`, and there is no dispatch authority.
`prefix/` puts exactly that path behind the runner's names; every other installed module is checked
byte-identical to d95a809's. All 10 assertion rows fail and all 8 `ran/` rows pass, so each red is a
failed assertion. The observations show the defects: the second submission and both racers launch,
no contract or acceptance exists when a worker starts, the unknown case simply launches, and every
observation is accepted and changes nothing.

## Mutations

23 registered as finding 39 in `scripts/check_teeth_mutations.py`; `mutations.py` drives them and
writes `mutations.json`, with each diff in `mutations/`. Every one turns its named row red with that
row's region completing. The declared falsifiers: `dispatch-spawn-before-contract` (AC1, two edits,
because the fixed code guards the order in the runner and in the receiver),
`dispatch-new-dispatch-for-unknown` (AC2) and `dispatch-result-unbound` (AC3). Every row has at
least one further mutation.

## Costs

Suite 62: about 2.2 s (three runs, 2.16 to 2.30 s, host load average 15 on 20 cores);
`observations.json` has one run's `suite_seconds`. Finding 39 with 4 jobs: 23 mutations in 16.2 s
(46 suite runs). Regression runs on this branch, all zero failures: 58_veldo_0028_effects (77),
58_veldo_0036_reservations (36), 60_veldo_0052_eligibility (80), 53_veldo_0123_mutations,
26_veldo_0009_install_stamp, 58_veldo_0046_notifications, 60_veldo_0064_inbox and
14_warp_0717_subset_runner; `validate.py all`, template sync, lint and generated checks pass. The full
gate is run by the lead.

## Not done here, stated

The existing station launches (`StationCalls.launch`, used by `executor.py` and `dispatch.py`) are
not moved onto this runner: those modules are outside this footprint. The macOS identity branch and
the SSH transport were not run (no Mac here); the wrapper path ran locally. The unit's own lifecycle
state is not rewritten (the dispatch record carries the dispatch lifecycle). Stopping the worker of
an unknown dispatch, descendant containment and retirement policy are VELDO-0040 and VELDO-0041;
recovery of an unknown dispatch is Release 2. The branch where the receiver process cannot be
started at all is not driven by the suite. `scripts/check_docs.sh` fails on a non-ASCII byte in
`proof/VELDO-0028/r8-probes-at-4b29b11.txt`, which predates this work.
