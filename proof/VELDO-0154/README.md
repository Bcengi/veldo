# VELDO-0154 proof: the factory loop runs inside the authority service

Built on branch build-veldo-0154 from main at a684f73b.

## The design as built

**Where the loop lives.** `control_service.FactoryLoop`, built by `serve` from the work configuration the
installation copied (`install(..., work=...)`, CLI `--work`; `veldo.factory_work/v1`: for each served repository
one builder and its reviewers, each an identity, an engine adapter of the installation, a configuration, a payload
and seconds; anything else refuses installation by name, `invalid_input:work:*`, with nothing left behind). With
no work configuration nothing in the service dispatches, as before. Each served repository gets one `Line`: the
VELDO-0039 `Runner` whose receiver is the repository's INSTALLED launch receiver (a separate process the Runner
starts, as always), VELDO-0052's Gate over the enrolled workspace, the dispatch records and the VELDO-0036
reservation service on the service's own connection and principal, and the VELDO-0160 account pool over the
receiver's engine adapters on the host the receiver runs on.

**The three wake sources, and nothing else.** A pass runs only when the service loop collected a wake in that
iteration: `journal` from `hint_after` (a packet or channel pass that advanced the journal, exactly where the
service already hinted the API), `run_end` from a launch pipe, and `account_reset` from the timer. The service
loop now waits in `select` on its socket and the launch pipe of every run a Runner watches (`Launch.fileno`), for
the accept timeout (`ACCEPT_SECONDS`, 0.25 s, unchanged) at most, or until the reset timer when that is sooner;
the channel pass is unchanged. `Launch.pump` takes what a readable pipe holds; the run's end is the receiver's
`exited` or `unknown` report, or the pipe's end of file when the receiver died (`lost`). The loop's own writes
wake nothing, and the service's start runs no pass.

**One pass.** It settles each run whose end it saw through `Runner.wait(launch, timeout=0)`; for a lost receiver,
`Runner.orphaned` frees the account slot (below). Then every assigned unit (one the line's builder holds a
VELDO-0031 claim on) is offered its next station: build when it has none; review, from the build's commit and
following it, to a reviewer independent of the builder, once the build completed (`control_dispatch.completed`);
nothing while a run holds it; and for a run that ended otherwise, nothing, unless its invocation ended
`account_limit`. Each offer asks the Gate first (a paused project's unit is refused `project_not_active:PAUSED`
and never offered) and then `Runner.submit`, whose preparation takes the account the pool selects on the adapter's
host. A unit no account can take waits, with the earliest reset (`no_account_until:<t>`); the pass sets the timer
to the earliest such reset. Each pass is one line in the service's observation log (kind `loop`): its sources and
wakes, what it ended, released, offered (dispatch, attempt, account, host, commit), refused, left waiting, decided,
asked, left awaiting the owner and stopped, and the timer.

**A receiver that dies (AC2).** Its run is recorded `outcome_unknown` under its dispatch (`Launch.wait`, as
before), its worker slot stays held with its outcome open and its invocation stays reserved (VELDO-0041: an
unknown outcome is never retired), and `Runner.orphaned` makes the stop the dead receiver owed (its reported
containment group killed, or the recorded worker process sent SIGKILL through a pidfd while its identity still
names it), reads from the kernel that nothing of the run is left and commits the reservation service's new
`release_account` transition, which marks the slot's account released; `control_account_pool` no longer counts
such a slot among the account's runs. A release that cannot be made yet stays pending and is tried again each pass.

**A run stopped by its account's limit (AC3).** The pass reads the run's committed execution record (VELDO-0141,
`control_execution_record.read` against the exit's commitment), converts it to the form VELDO-0160's Notes give,
and asks `control_account_limit.decide`, with the configuration's catalog servers and read-only marks
(`catalog_marks`: none until VELDO-0127, so every MCP call asks). `rerun` offers the same station again under a new
dispatch identity from the run's own accepted commit with its adapter, payload and configuration; the pool takes
another account, since the exhausted one is inside its reported window. `ask` opens one ordinary decision request
(VELDO-0064, kind `decision`, choices `rerun` and `stop`, subject `account_limit_rerun` naming the dispatch, the
brief naming each call) to the unit's project owner, signed as the service's principal; nothing is dispatched until
his answer admits (`Inbox.admit`), then `rerun` dispatches as a re-run would and `stop` leaves the unit stopped. The
service now routes VELDO-0064 inbox command packets to the inbox, which authenticates them itself, so his answer
arrives as a packet and wakes a pass.

## Footprint

The drafted footprint named `control_service*` and `control_launch*`. AC2's freed account slot needed the
reservation service (`control_reservations.py`, the `release_account` transition) and the pool's count
(`control_account_pool.py`), and the finding's mutations needed `scripts/check_teeth_mutations.py`; the spec's
footprint and History say so.

## Evidence

- Suite `scripts/suites/83_veldo_0154_factory_loop.py`, eleven rows, registered in the manifest; requires.json
  regenerated. It installs the instance with `control_service.install` and runs the INSTALLED service (its
  ExecStart) on its installed configuration, with a fake Codex vendor binary and four Codex accounts.
- `red-at-a684f73b.json`: the current suite against the whole tree of main at a684f73b; every row red by
  assertion.
- `mutations.json` and one `.diff` per mutation: finding 154 in `scripts/check_teeth_mutations.py`, driven by
  `drive.py` (baseline and no-op controls green, each mutant red on its named row by assertion).
