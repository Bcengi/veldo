# landing-b gate fix round 8: suite 114 host-scope/own-scope flake

Round 7 gate (HEAD 22a44db0): mutation stage invalid_baseline on
check_teeth_mutations.py:host220-no-scope; the noop control failed
VELDO-0220 host-scope/own-scope with inside-a-scope false.

## Reproduction (before any change)

12 parallel runs of `selftest.py --suite 114_veldo_0220_gate_scope`, 3 rounds:
35 of 36 green, 1 red with inside-a-scope false. Its evidence: exit 75,
"GATE: NOT STARTED (host lock .../locks/.scope.lock held by pid 884820 ...)".

Cause: not the caller unit name, not the stamp, not the output line. The
outside case's lock keeper (gate_host.keep_lock) releases the scratch flock
only as it exits, after stop_scope returns; the scope's cgroup can already be
gone. The scope cases waited for the cgroup, never for the lock, so under load
inside-a-scope started while the outside keeper still held the lock.

## Fix (scripts/suites/114_veldo_0220_gate_scope.py)

- 010a3312: each scope case asserts "lock released" after "scope cgroup gone"
  (a condition added, none removed), and waits for release before the next
  case even on red; the caller unit is v220-caller-<pid>-<random>.scope; both
  waits are bounded by the suite's 180 s fixture-gate deadline, not 15 s; a red
  case records `failed`, the name of its first failing condition.
- 25843f36: alive() treats ProcessLookupError on /proc/<pid>/stat as gone, as
  state() does. Found by the host220 run below: the lock-not-retained mutant
  crashed the suite there (driver_error) instead of being judged.

No falsifier added: the 3 host220 scope mutants still reject the row.

## After

- 12 parallel x 5 rounds: 60 of 60 green.
- Under flock on the host gate lock: suite 114 x3 parallel, 3 of 3 green
  (27 passed, 0 failed); check_gate_mutations.py with the 7 host220-* cases:
  passed, registered 7, executed 7, rejected 7, 59.8 s. host220-no-scope's
  evidence names `failed: scope named veldo-gate-*`.
