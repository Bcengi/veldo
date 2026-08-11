---
schema: veldo.spec/v1
id: WARP-0317
title: Sandbox / isolation runner (reference) - B17 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B17
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A sandbox / isolation runner ships at
      engine/scripts/runners/sandbox/sandbox_isolation_runner.py. It
      reads a journey (a JSON object with an image, an allowed_mounts list where
      each mount is an absolute path with a ro or rw mode, and a checks list) and
      drives each check as a read or a write at an absolute container path with a
      required verdict of allowed or denied. It runs the flow through a
      ContainerDriver seam: the live driver shells out to docker run or podman run
      with only the declared mount scopes, a read-only root filesystem, no
      network, and all capabilities dropped, so confinement is enforced by the
      real runtime; a FakeContainerDriver simulates confinement deterministically
      in process (a path is readable within a mount, writable within a read-write
      mount, denied otherwise) so the control logic runs with no container. The
      confinement model (confine), the verdict classifier (classify), and the
      grading (grade_check) are pure functions with no I/O.
  - id: AC2
    text: The passing fixture
      (engine/scripts/runners/sandbox/fixtures/pass.sandbox.json) exits
      0. It is a correctly-confined journey that exercises confinement in both
      directions: reads inside the read-only and read-write mounts succeed, a
      write lands in the read-write mount, a write into the read-only mount is
      refused, and two escape attempts (reading a host secret and writing a host
      path outside every mount) are denied; every observed verdict matches its
      required verdict, so the runner driven with the FakeContainerDriver exits 0.
      Every path is a generic container-internal example, never a host path of any
      specific machine.
  - id: AC3
    text: The deliberately-failing fixture
      (engine/scripts/runners/sandbox/fixtures/fail.sandbox.json) exits
      1 with the failure named. It declares an over-broad root ("/") mount (a real
      misconfiguration) that leaves /etc/shadow reachable while the journey still
      requires that read denied, so the escape succeeds and the runner exits 1
      printing a CONFINEMENT BREACH line naming the escaped host path. A path the
      journey requires denied but the sandbox allows is graded a breach and a path
      it requires allowed but the sandbox denies is graded over-restricted, and a
      journey with no checks is a named journey error, so a runner that could only
      ever say PASS is impossible.
  - id: AC4
    text: The assertions reflect real observed behavior and the control logic is
      unit-tested in scripts/selftest.py with no external dependency (no container
      runtime, no host filesystem access). The confinement model is exercised in
      both directions (a read and write inside a mount, a write into a read-only
      mount denied, a read and write outside every mount denied, the /data vs
      /database prefix trap not fooled, a root mount containing everything); the
      classifier maps exit 0 and 1 to allowed and denied and any other code to a
      hard error so a failed container cannot masquerade as a clean denial; the
      grading names a CONFINEMENT BREACH, an over-restriction, and config and
      journey errors; the live driver's fail-loud contract is proven with no
      runtime installed via require_runtime; and both shipped fixtures are driven
      end to end through the fake driver (pass -> exit 0, fail -> exit 1 with the
      escaped host path named). All prior selftest cases keep passing and the gate
      stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README, and no absolute host paths - and
      .veldo/capabilities.yaml (template and repository instance, kept
      byte-identical) declares it status reference (a shipped reference an
      adopting repo on a host with a working container runtime wires to its own
      image and the sandbox or isolation gate slot; the veldo home repo has no
      container surface of its own to confine and this Linux box has no reliable
      runtime), never mechanical. The docs-hygiene, secret, lint, and
      template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B17 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is touched,
  so reverting removes the reference artifact and its unit block with no effect on
  any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B17 is the sandbox / isolation surface. The outcome that should become
true is that a repository can run a flow inside a real container and get proof
that it is confined: the flow reads and writes only within its declared mount
and path scope, and an escape attempt - reading or writing a host path outside
the allowed mounts - is denied. A sandbox is only as good as the escapes it
actually stops, so a happy-path test that only touches the intended paths is no
proof. This runner drives the escape attempts themselves at the confined flow
and fails the run naming any host path that leaks through, because a path the
sandbox should confine but does not is a confinement breach, the worst kind of
silent green: an under-restricted sandbox.

## Context

B17 of PLAN-0003, feature F5 (systems surfaces), pulled against plan revision 2,
with no dependency. It follows the shipped runners' pattern: a generic reference
under engine/scripts/runners/, a driver seam with a live driver and an
in-process fake (as the mobile and auth runners have), a fixture PAIR (a
correctly-confined passing journey and a deliberately-breached journey with an
over-broad mount), a wrapper, a README, and a unit block that gate-tests the
control logic with the fake driver and no live surface. Confinement is expressed
as mount scope (which host paths the container can see) and mode (read-only vs
read-write), plus the read-only root, dropped capabilities, and no network the
live driver applies; the config is the journey's allowed_mounts and checks, so
an adopting repo adapts and extends the scope and the escape attempts for its
own sandbox.

## Out of scope

A live container run in the home gate, because the veldo repo has no container
surface of its own and this Linux box has no reliable runtime; the honest
evidence is the fake-driver control-logic test, and the live path fails loud
when no runtime is present rather than being silently skipped. Namespace,
seccomp, cgroup, and user-remapping hardening beyond the mount-scope, read-only
root, no-network, and dropped-capabilities flags the live driver sets: a
production sandbox tunes those per threat model, and the reference documents them
as the seam an adopting repo extends. Filesystem-level race conditions (a
time-of-check to time-of-use escape) are a production concern the deterministic
reference does not model. This spec adds no enforcer and touches no protected
path.

## Notes

Why reference (not mechanical): the veldo home repo has no container surface of
its own to confine, and a live run needs a working container runtime this box
does not reliably have, so the honest evidence is the fake-driver unit tests,
not a live run against a real container. required_evidence is [unit,
operational]: unit is the selftest control-logic block, operational is the two
shipped fixtures driven end to end through the fake driver (pass -> exit 0, fail
-> exit 1 with the breach named) via test_sandbox_isolation_runner.sh.
capabilities.yaml states status: reference, never mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest
and driving the fixtures: (1) the confinement model denies a read and a write of
a host path outside every mount and denies a write into a read-only mount, while
allowing reads and writes within the correct scope, and is not fooled by the
/data vs /database prefix trap; (2) a path required denied but observed allowed
is named a CONFINEMENT BREACH with the escaped path and a path required allowed
but observed denied is named over-restricted, which is exactly what the failing
fixture demonstrates with its over-broad root mount; (3) a journey with no checks
and a malformed check or mount are named errors, never a vacuous pass; (4) the
verdict classifier treats any exit code other than 0 or 1 as a hard error so a
container that failed to start cannot masquerade as a clean denial; (5) the live
driver fails loud when no container runtime is installed.
