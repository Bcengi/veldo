# B2 stalled receiver corrections, 2026-10-15

This is a bounded regression record, not a proof manifest, gate stamp, native
qualification or independent review. The owner reserves the canonical gate and
merged-tree verification for the reviewer. Only suites 105 and 106 were selected.
Their prerequisite closure is the selftest dispatcher's own choice. Exit 2 with
zero failed rows is the dispatcher's required PARTIAL result, not a gate pass.

## Deadline and wake behavior

`Line.offer` registers exactly one remote deadline at the contract deadline plus
`control_launch.ACCEPT_SECONDS`, matching the local wait grace. The serve loop
waits for that deadline alongside the socket, launch pipes and actual account
resets. Idle serve iterations neither read dispatch state nor start factory passes.
The signed worker-result handler notifies the matching launch after its transaction
commits. A terminal result removes that launch's deadline. Expiration consumes the
one deadline, stops the transport and settles only that launch; it does not provision
accounts, scan scheduling work or visit another launch's authority record.

Regression rows in `106_veldo_0125_routing`:

- `AC2/remote-no-polling`: zero factory passes and zero dispatch reads while a
  remote launch remains pending across six simulated serve iterations.
- `AC2/remote-factory-deadline`: prepared, accepted and running stalled receivers;
  only the expiring launch is settled, another pending launch is untouched, and
  repeated expiration produces no second pass.
- `AC3/remote-deadline-grace`: a signed exit and final usage remain acceptable
  after the execution deadline and before the end of acceptance grace.
- `AC3/remote-authority-end`: the signed result wakes its launch without EOF.
- `AC2/factory-remote-delivery`: the production offer registers its deadline and
  contacts the configured receiver through a subprocess.

## Durable holds and release protocol

Remote acceptance journals a `remote_hold` on the worker reservation in the same
transaction as acceptance, the invocation reservation and worker observation. It
binds host and contract digest and records open termination, group and clone
obligations. `Runner.remote_retirements` reads these records; factory status exposes
`remote_holds` and `remote_deadlines`. A restart cannot erase a held obligation.

The trusted Mac receiver collects output/proof and usage, observes the supervisor's
termination and empty group, removes clone and scratch, and releases the host slot.
It then includes `cleanup: {terminated: true, cleaned: true, clone_removed: true}`
in its signed `worker_result` observation. `collect` must retain output/proof outside
the removed clone and scratch. Cleanup failure still permits a signed exit and
spend report but supplies no cleanup evidence, so the authority slot stays held.
Missing usage in an otherwise final cleanup result retains unknown charge in the
invocation; it never becomes zero spend.

The authority saves the signed worker observation and retires the reservation in
one transaction. The reservation transition checks the durable observation's host,
contract, worker principal, command and cleanup before release. A Linux kernel
observation cannot substitute for that evidence. Duplicate cleanup does not retire
the slot again. A result after a timeout can record actual exit/spend and discharge
cleanup while retaining the dispatch's unknown outcome; it does not automatically
recover or retry the unit.

For a previously reported exit whose cleanup was delayed, the assigned Mac receiver
can send another `Client.result(binding, observation, usage=usage,
references=references)` with the same original observation, usage and references
plus the cleanup object after actually completing those obligations. It uses the
same enrolled coordinates and signing key; another worker's signature is refused.
For an accepted launch that conclusively never spawned, the receiver can send a
signed result with `state: refused`, a named `refusal`, and that cleanup object;
the invocation is finalized as not executed and the slot released. Before acceptance,
a signed refusal needs no process cleanup evidence. A transport that started but
never obtained acceptance also releases its prepared reservation on loss/deadline.

Additional regression rows:

- `AC3/remote-hold-restart`: close SQLite, recreate the authority and Runner,
  preserve the hold, refuse another worker's release, then accept a late signed
  result or refusal and free capacity, including a lost running notification.
- `AC3/remote-signed-cleanup`: retain the slot without cleanup; reject incomplete
  cleanup; release once; reuse a capacity-one account for three successive jobs.
- `AC3/remote-signed-refusal`: a claimed but never accepted dispatch releases and
  cannot subsequently accept.
- `AC3/remote-cleanup-held`: Linux retirement cannot bypass signed cleanup even
  when accounting settles.
- `AC3/remote-result-transport-failure`: losing the signed-result transport after
  host cleanup keeps the authority hold and does not reopen or signal the retired
  host run.
- `AC2/actual-worker-launch`: the trusted Mac orchestration path removes clone and
  scratch and releases both host and authority slots. Apple OS observations here
  are synthetic; this is not a fresh native Mac run.

## Falsifiers

The adjacent `b2-falsifiers/` directory retains each exact temporary mutation and
selected failing rows. Diffs omit unchanged context (apply with `--unidiff-zero`). Each mutation was applied alone to the installed `.veldo`
copy, tested with `python3 scripts/selftest.py --suite 106_veldo_0125_routing`, then
restored. Canonical and installed source copies are identical in the final tree.

- `recurring-tick.diff`: an account-reset wake while a remote deadline exists makes
  `AC2/remote-no-polling` and the deadline isolation row fail.
- `grace.diff`: removing acceptance grace makes `AC3/remote-deadline-grace` fail.
- `durability.diff`: omitting the durable hold makes `AC3/remote-hold-restart` fail.
- `release.diff`: disabling signed release makes cleanup, restart and actual-worker
  release rows fail.

- `result-transport.diff`: restoring stop/wait after failed delivery of an already
  retired run makes `AC3/remote-result-transport-failure` fail.

The selected final-run summaries and falsifier failures are in `results.txt` there.
No full selftest, gate, general mutation checker, native SSH run or deployment was
performed during this correction.
