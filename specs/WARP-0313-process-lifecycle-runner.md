---
schema: veldo.spec/v1
id: WARP-0313
title: Process/daemon lifecycle runner (reference) - B13 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B13
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A process lifecycle runner ships at
      engine/scripts/runners/process/process_runner.py. It reads a
      fixture (a name, a spawn argv array run without a shell, an optional env
      map, a list of lifecycle assertions, and optional grace/settle/readiness/
      kill windows) and drives a REAL child process via stdlib subprocess, os,
      and signal. It spawns the target in a new session so the target leads its
      own process group and the runner signals the whole group with os.killpg.
      The passing fixture (a well-behaved sleeper that spawns a child and dies on
      SIGTERM) exits 0 and the deliberately-failing fixture (a target that
      ignores SIGTERM and leaks a setsid-escaped child) exits 1 with the failing
      assertions named on stdout.
  - id: AC2
    text: The assertions reflect real observed behavior, never a narration. spawn
      confirms a live pid and fails named if the command cannot be spawned or
      exits immediately. graceful_signal sends SIGTERM to the group and requires
      the target to exit within the grace window; a target that ignores SIGTERM
      is force-killed with SIGKILL and that force-kill is reported as the failure,
      so the runner never hangs on a stuck daemon. respawn spawns, terminates, and
      spawns again and requires a DIFFERENT live pid so a stale process cannot
      masquerade as a restart. kill_tree waits for the target to report a
      child-of-child (via the VELDO_PIDFILE seam), kills the parent group, and
      fails naming any descendant left alive; a grandchild that called setsid to
      escape the group survives a group kill and is caught as an orphan.
  - id: AC3
    text: A fixture that declares no assertions asserts nothing and is a fixture
      error (a check that asserts nothing is not proof), an unknown assertion name
      is a named error, a fixture with no spawn argv is a named error, and a
      kill_tree assertion whose target reports no child-of-child fails named
      rather than passing vacuously. Exit code is 0 only when every declared
      assertion held; otherwise exit 1 with the failing assertion and what was
      observed named.
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py with no external
      dependency, driving real short-lived python -c sleepers with generous
      windows so the suite is self-contained and leaks no processes. A
      well-behaved target passes all four assertions; a SIGTERM-ignoring target
      fails graceful_signal with the force-kill reported; a setsid-escaped child
      fails kill_tree naming the orphan; a missing command is a named spawn
      failure not a crash; asserts-nothing, unknown-assertion, and no-spawn-argv
      fixtures are named errors; and the two shipped fixtures are driven end to
      end (passing -> exit 0, failing -> exit 1 naming graceful_signal and
      kill_tree). All prior selftest cases keep passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference an adopting repo wires to its lifecycle or integration
      gate slot; the veldo home repo ships no long-running process of its own),
      never mechanical. The docs-hygiene, secret, lint, and template-sync gates
      stay green.
required_evidence: [unit, operational]
rollback: git revert; B13 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is touched,
  so reverting removes the reference artifact and its unit block with no effect on
  any running gate, and the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B13 is the process and daemon lifecycle surface. The outcome that should
become true is that a repository can drive a real long-running process (a daemon,
a worker, a supervised service) and get proof that it does the four things such a
process must actually do: it spawns to a live pid, it honors a termination signal
by exiting within a grace window (or is force-killed and that is reported), a
respawn yields a fresh process rather than reusing a stale one, and a kill of the
parent process group leaves no orphaned descendant. A happy-path check that the
process came up misses the daemon that ignores SIGTERM and hangs forever on
shutdown, and the worker that leaks a detached child on every restart. This runner
sends real signals to a real process group and asserts what happened.

## Context

B13 of PLAN-0003, feature F5 (process and configuration surfaces), pulled against
plan revision 2, with no dependency. It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR (a
passing and a deliberately-failing fixture), a wrapper, a README, and a unit block
that gate-tests the control logic with no live dependency. Here "no live
dependency" means the selftest drives real short-lived python -c sleepers rather
than a mock, because the surface under test IS the OS process lifecycle; the
sleepers are fully self-contained and need nothing installed. The target is
spawned in a new session so it is a process-group leader, which is the correct way
to reach a whole tree with a single os.killpg. Descendant discovery is a seam: the
target reports its child-of-child pids to the file named in VELDO_PIDFILE, so an
adopting repo either has its daemon record its worker pids there or wires the
assertions to its own supervisor.

## Out of scope

Service-manager integration (systemd, launchd, Windows services) and their
readiness or socket-activation protocols. Windows process semantics (the runner
uses POSIX sessions, process groups, and signals). Restart backoff policy,
crash-loop detection, and health-check probing beyond the four lifecycle
assertions. Resource-limit enforcement (cgroups, rlimits). Driving a live daemon
in the home gate, because the veldo repo ships no long-running process of its own;
the honest evidence is the real-subprocess control-logic test.

## Notes

Why reference (not mechanical): the veldo home repo has no long-running process of
its own, so the honest evidence is the real-subprocess unit tests, not a live
daemon run. required_evidence is [unit, operational] - unit is the selftest
control-logic block, operational is the shipped fixtures driven end to end and the
test_process_runner.sh wrapper. capabilities.yaml states status: reference, never
mechanical.

Liveness is probed with signal 0 for portability; where /proc is available a
zombie (an exited descendant not yet reaped by its reparented init) is reported
dead, so a briefly-unreaped child is never mistaken for a leaked orphan. Windows
are generous and are upper bounds only: a well-behaved process exits in
milliseconds, far under any grace, and the only full-window waits are the
deterministic-failure paths (a target that genuinely ignores the signal, a
descendant that genuinely escaped the group).

The adversarial properties a reviewer should confirm by rerunning the selftest and
driving the fixtures: (1) a target that installs SIG_IGN for SIGTERM fails
graceful_signal and is force-killed with the force-kill reported, never hanging;
(2) a grandchild that calls setsid to escape the parent group survives a group
kill and is named as an orphan, and the runner then cleans it up so nothing leaks;
(3) respawn requires a different live pid; (4) a kill_tree with no reported
child-of-child fails named rather than passing vacuously; (5) a missing command is
a named spawn failure, not an uncaught exception.
