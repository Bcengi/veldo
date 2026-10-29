# VELDO-0220 proof index

Round 3 splits the scope checks into suite 114 and keeps the lock and not-started
checks confined in suite 113. The owner approved the unconfined entry; its single
line now names suite 114 whole. See [OPEN.md](OPEN.md) for current status and
[round3](round3/) for coordinator evidence. This is implementation evidence,
not an independent verdict or a claim that the canonical gate passed.

The following records describe round 2's lifecycle and test coverage fixes from
[the independent review](review-2026-10-28.md).

A keeper forks before scope creation and retains the lock outside that scope.
It creates the scope for the holder, detects holder death through a socket and
pidfd, kills through cgroup.kill, and waits for cgroup.events to report no live
processes before releasing custody. This covers normal exit, red exit, SIGTERM,
SIGINT, SIGHUP and SIGKILL of the holder. The keeper has a separate process group
and exits after cleanup. Cleanup errors retain custody and retry. Lock-only
configurations use the command's private process group instead of a scope.

The changed tests require stages to be dead when the scratch lock becomes free.
The scope row includes a worker in a different session and a delegated child
cgroup. It exercises termination and normal completion with leftover work. It freezes the keeper across holder death to check that custody survives. It
also verifies that the lock descriptor is absent from stage processes.

The nested-holder test runs below a real flock owner. A non-holder ancestor,
the flock process itself, and a nonexistent pid cannot authenticate the holder
environment variable. Existing successful fixture gates exercise the real
holder path. Removing the guard must fail the held-not-started row.

The [final summary](round2/summary.json) binds all seven mutant and baseline
records to implementation commit a30a74f6. All seven mutants are red on
their target rows and all seven baselines are green. No fixture gate or keeper
remained after validation.

Evidence in [round2](round2/):

* 01-lifecycle-red.log: the original code fails both lifecycle rows after the
  new assertions, including normal exit with a leftover scoped worker.
* 02-lifecycle-green.log: all four ticket rows pass with scope custody fixed.
* 03-lock-mutant-survived records show the initial descriptor check was too
  narrow. It was expanded to inspect the shell ancestors as well as the probe.
* 05-all-falsifiers.log and the corresponding JSON records: removing scope
  kill, dropping keeper custody, leaking the descriptor, skipping the scope,
  ignoring the lock or charging NOT STARTED as red must fail. Baselines pass.
* 04-holder-guard.log and host220-forged-holder JSON records: guard removed is
  red and the restored baseline is green.
* 08-suite-green.log and 09-custody-green.log: the suite with the new guard
  checks, then the deterministic keeper custody check.
* 06-documents-red.log and 07-documents-green.log: missing proof documents turn
  green after creation; the spec and protected unconfined list stay unchanged.

Each falsifier JSON records the exact source digests, base commit, observed rows
and failure details. check.py runs only this ticket's registered falsifiers,
mutant before restored baseline. The initial descriptor falsifier ran under
the owner's blocking host flock. Later checks execute only the single ticket
suite, within the owner's single-file allowance; every fixture gate uses its
own temporary lock path. Single-file suite runs
select only suite 113. Partial suite exit 2 means the targeted rows passed and
is deliberately not a canonical gate success.

No canonical verify command, push or merge was performed. Earlier records in
PROOF.md and local_checks.json describe round 1 and are retained as history.

manifest.json and PROOF.md are the round 1 record at commit 8030ef4d and are superseded by
round3/README.md (suite 113 lock rows, suite 114 scope rows) and the independent fix-check of
round 3 (SOUND, 2026-10-28).
