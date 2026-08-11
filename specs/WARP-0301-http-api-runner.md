---
schema: veldo.spec/v1
id: WARP-0301
title: HTTP/API journey runner (reference) - B1 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B1
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A generic HTTP/API journey runner ships at
      engine/scripts/runners/api/veldo_api_runner.py. It reads a
      journey fixture (JSON base_url plus a list of steps, each with method,
      path, headers, body, and an expect block covering status, json_keys
      present, json_equals, json_path_present, json_path_equals, and a
      max_seconds latency budget), drives the endpoint with only the Python
      standard library (urllib), asserts each step, and stops at the first
      failing step. It exits 0 when every step passes and exits 1 with the
      failing step and every failed assertion named.
  - id: AC2
    text: A passing fixture and a deliberately-failing fixture ship under
      engine/scripts/runners/api/fixtures/. Driven against the
      bundled stdlib mock server, the passing fixture passes and the runner
      exits 0; the failing fixture (which asserts a wrong status) fails and the
      runner exits 1 with the status mismatch named. Assertions reflect the
      real observed HTTP response, not a stub - a 4xx or 5xx is a real
      assertable response and a transport error is a named step failure.
  - id: AC3
    text: The runner's control logic is unit-tested in scripts/selftest.py with
      no external dependency - an in-process stdlib http.server (ephemeral port,
      in a thread) returns known JSON, the runner is driven over its own
      passing and failing fixtures (pass to exit 0, fail to exit 1 with the
      failure named), and every expect kind plus the JSON-path resolver is
      exercised directly for both its true and false outcomes. All prior
      selftest cases keep passing and the gate stays green.
  - id: AC4
    text: The runner is generic - zero company or product names in the runner,
      fixtures, mock server, wrapper, or README - and .veldo/capabilities.yaml
      (template and repository instance, kept byte-identical) declares it
      status reference (a shipped reference artifact an adopting repo wires to
      its gate slot; the veldo repo does not run it), never mechanical. The
      docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B1 adds a new runner directory under engine,
  a selftest block, and an honest capabilities entry (template and instance) -
  no protected gate script or enforcer is touched, so reverting removes the
  reference artifact and its unit block with no effect on any running gate; the
  prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface so an adopting repository has a working, self-tested starting point to
wire into its gate. B1 is the first and most common surface: an HTTP/API
endpoint. The outcome that should become true is that a repository with an API
can drop in a generic runner, point it at its own endpoint with a JSON journey
fixture, and get flow-first proof - the journey is driven end to end and the
response is asserted at every step, so a passing run is evidence the API
behaves, not merely that a port answered. A step that fails stops the journey
and names the failure, because a runner that presses on past a broken step and
still reports green is worse than none.

## Context

B1 of PLAN-0003, feature F1 (surface runners), pulled against plan revision 2.
The runner mirrors the shipped web (W5) and mobile (W7) runners: a generic
reference artifact under engine/scripts/runners/, a fixture PAIR
(passing and deliberately-failing), and a fixture/fake-driver style unit test
so the control logic is gate-tested with no live surface. Here the "fake
driver" is a tiny stdlib mock server (fixtures/mock_server.py) that returns
known JSON; the runner is driven against it in-process, so the every-commit
gate proves the request building, the JSON-path resolver, and every assertion
kind with no external service. Standard library only (urllib) keeps the
artifact zero-install, so a reviewer reruns it with no setup.

## Out of scope

Authentication flows (token acquisition, refresh) - a later battery. Response
schema validation beyond key presence and exact value/path equality. Load or
throughput testing - max_seconds is a per-request budget, not a performance
suite. Wiring the veldo home repository's gate to this runner: the home repo has
no HTTP surface of its own, so the runner ships as a reference marked status
reference and is not run in the home gate.

## Notes

The runner exits 0 only when every asserted step passes; it stops at the first
failing step because later steps in a journey usually depend on earlier state
and are unproven once one breaks. The optional [base_url] CLI argument (or the
BASE_URL environment variable) overrides the journey's base_url so the same
fixture aims at local, staging, or the test server unchanged - which is how the
selftest points the shipped fixtures at the ephemeral-port in-process server.
capabilities.yaml states the honest status: reference (the artifact ships and
is self-tested) - never mechanical, because the veldo repo does not itself run
it against a live endpoint.
