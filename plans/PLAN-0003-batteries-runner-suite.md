---
schema: veldo.plan/v1
id: PLAN-0003
title: VELDO batteries - the reference runner suite for common product surfaces
kind: mvp
status: released
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-16
risk: standard

outcomes:
  - id: O1
    becomes_true: A team adopting VELDO for any common surface - HTTP API, data,
      auth, performance, LLM behavior, agent loops, streaming, processes,
      sandboxes, plugins, config, security, CLI, mobile - finds a ready reference
      runner in the box and does not build their own, so verification effort
      compounds into VELDO instead of scattering across projects.
    measure: capabilities.yaml lists a shipped reference runner for each surface,
      each with a passing and a deliberately-failing fixture
  - id: O2
    becomes_true: Every runner PROVES behavior by driving the real surface and
      asserting observed results, and it fails on a deliberately-broken fixture -
      no runner can rubber-stamp a vacuous pass.
    measure: each runner ships a passing fixture (exit 0) and a failing fixture
      (exit 1 with the failure named), both demonstrated in selftest or proof
  - id: O3
    becomes_true: Runners are pluggable, not forced - a repo activates a runner
      as a gate slot only for the surfaces it has, so the proportionality rule
      holds and VELDO's own gate never runs a surface runner it does not need.
    measure: runners are marked reference in capabilities.yaml and are absent from
      the veldo gate catalog unless a repo wires them

non_goals:
  - id: NG1
    text: Hyper-domain runners (the telecom/CoreConnect protocol runner) are a
      Bcengi extension pack, not core VELDO batteries.
  - id: NG2
    text: Runners are references an adopting repo wires to its own gate slot; this
      plan does not force any runner into the veldo repo's own gate.

constraints:
  - id: C1
    text: Every runner is lighter than the surface it verifies and ships with a
      fixture pair; no runner reimplements a check the gate already owns.
  - id: C2
    text: A runner that cannot be driven in this environment (needs macOS, a live
      third-party sandbox) ships reference-honest in capabilities.yaml, never
      claimed mechanical.

feature_tree:
  - id: F1
    title: Backend surfaces - HTTP API, data/migration, authorization,
      performance/load
    outcome_refs: [O1, O2]
  - id: F2
    title: Intelligence surfaces - LLM behavior evals, agent-loop/tool-execution,
      MCP server/client
    outcome_refs: [O1, O2]
  - id: F3
    title: Client surfaces - iOS mobile and terminal/TUI (web and Android shipped
      in 1.0)
    outcome_refs: [O1, O2]
  - id: F4
    title: Boundary surfaces - external integrations, payload/contract conformance,
      streaming and websockets
    outcome_refs: [O1, O2]
  - id: F5
    title: Systems surfaces - CLI/process, process/daemon lifecycle, sandbox
      isolation, packs/claude/extension loading, config-schema validation
    outcome_refs: [O1, O2]
  - id: F6
    title: Safety surfaces - security guards (SSRF, path traversal, secret leak)
      and static architecture-invariant guardrails
    outcome_refs: [O1, O2]
  - id: F7
    title: Pluggability - gate-slot wiring, honest capability status, and a runner
      catalog for the whole suite
    outcome_refs: [O3]

work:
  - item: B1
    spec: WARP-0301
    title: HTTP/API journey runner (reference) - request, assert status + JSON +
      latency budget; passing and deliberately-failing fixtures
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: B2
    spec: WARP-0303
    title: DB/migration runner (reference) - apply up and down, assert data
      invariants and a query-latency budget; failing fixture
    feature_refs: [F1]
    depends_on: []
    order: 20
  - item: B3
    spec: WARP-0305
    title: LLM/eval runner (reference) - graded eval set, behavioral assertions,
      cost/latency budget, regression on prompt change; failing fixture
    feature_refs: [F2]
    depends_on: []
    order: 30
  - item: B4
    spec: WARP-0306
    title: CLI/process runner (reference) - drive a command, assert stdout,
      stderr, exit code and a time budget; failing fixture
    feature_refs: [F5]
    depends_on: []
    order: 40
  - item: B5
    spec: WARP-0302
    title: Auth/authorization runner (reference) - drive an endpoint as another
      user and assert no cross-tenant access (owner-scoping); failing fixture
    feature_refs: [F1]
    depends_on: [WARP-0301]
    order: 50
  - item: B6
    spec: WARP-0304
    title: Performance/load runner (reference) - drive a target under concurrency
      and assert latency and throughput budgets; failing fixture
    feature_refs: [F1]
    depends_on: [WARP-0301]
    order: 60
  - item: B7
    spec: WARP-0307
    title: Integration/external-service runner (reference) - drive an integration
      in sandbox/contract mode and assert the contract; failing fixture
    feature_refs: [F4]
    depends_on: [WARP-0301]
    order: 70
  - item: B8
    spec: WARP-0308
    title: iOS mobile runner (reference, macOS-gated) - simulator journey driving
      and state capture, shipped reference-honest where no macOS is present
    feature_refs: [F3]
    depends_on: []
    order: 80
  - item: B10
    spec: WARP-0310
    title: Agent-loop/tool-execution runner (reference) - drive an agent turn
      (prompt, tool calls, tool results, final) and assert the observed tool
      invocations and outputs; failing fixture
    feature_refs: [F2]
    depends_on: []
    order: 90
  - item: B11
    spec: WARP-0311
    title: Contract/schema runner (reference) - capture a real payload and assert
      it against a versioned golden contract; drift fails
    feature_refs: [F4]
    depends_on: []
    order: 100
  - item: B12
    spec: WARP-0312
    title: Streaming/SSE/websocket runner (reference) - drive a stream and assert
      chunk sequencing, framing, and final; a malformed stream fails
    feature_refs: [F4]
    depends_on: []
    order: 110
  - item: B13
    spec: WARP-0313
    title: Process/daemon lifecycle runner (reference) - spawn a real child,
      assert spawn, signal, respawn, and kill-tree behavior; failing fixture
    feature_refs: [F5]
    depends_on: []
    order: 120
  - item: B14
    spec: WARP-0314
    title: Config-schema validation runner (reference) - feed valid and invalid
      config into the real validator and assert accept/reject plus error messages
    feature_refs: [F5]
    depends_on: []
    order: 130
  - item: B15
    spec: WARP-0315
    title: Security-guard runner (reference) - send SSRF, path-traversal, and
      secret-leak inputs at the real guard and assert each is blocked
    feature_refs: [F6]
    depends_on: []
    order: 140
  - item: B16
    spec: WARP-0316
    title: Plugin/extension-loading runner (reference) - install a packaged
      plugin (including a malicious archive) and assert safe load or rejection
    feature_refs: [F5]
    depends_on: []
    order: 150
  - item: B17
    spec: WARP-0317
    title: Sandbox/isolation runner (reference) - run a flow in a real container
      and assert confinement (mount scope, path scope); an escape attempt fails
    feature_refs: [F5]
    depends_on: []
    order: 160
  - item: B18
    spec: WARP-0318
    title: MCP server/client runner (reference) - drive an MCP transport and
      assert tool listing, invocation, and proxying; a bad tool call fails
    feature_refs: [F2]
    depends_on: []
    order: 170
  - item: B19
    spec: WARP-0319
    title: Terminal/TUI runner (reference) - feed keystrokes and output into the
      real terminal renderer and assert ANSI, layout, and history
    feature_refs: [F3]
    depends_on: []
    order: 180
  - item: B20
    spec: WARP-0320
    title: Static-invariant/guardrail runner (reference) - assert architecture
      invariants over the source (forbidden imports, boundary rules) with a
      failing fixture that violates one
    feature_refs: [F6]
    depends_on: []
    order: 190
  - item: B9
    spec: WARP-0309
    title: Suite pluggability - gate-slot wiring guidance, honest capabilities
      status for every runner, and a runner catalog in the docs
    feature_refs: [F7]
    depends_on: [WARP-0301, WARP-0302, WARP-0303, WARP-0304, WARP-0305, WARP-0306, WARP-0307, WARP-0308, WARP-0310, WARP-0311, WARP-0312, WARP-0313, WARP-0314, WARP-0315, WARP-0316, WARP-0317, WARP-0318, WARP-0319, WARP-0320]
    order: 200

regression:
  journeys:
    - id: BJ1
      title: Every shipped runner's passing fixture passes and its failing fixture
        fails - no runner rubber-stamps
      activation: {when: start}
      owner_spec: WARP-0309
      profiles: [per_spec, release]
      suite: scripts/selftest.py (runner fixture pairs) plus each runner's proof
    - id: BJ2
      title: The veldo repo's own gate never invokes a surface runner it lacks (no
        backend, emulator, or third-party needed to run the veldo gate)
      activation: {when: start}
      owner_spec: WARP-0309
      profiles: [release]
      suite: scripts/verify.sh catalog (surface runners marked not-applicable)

release:
  milestone: VELDO batteries v1 - the common runner suite
  version: plugin minor bumps per runner; suite complete at B9
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: each runner is additive under engine/scripts/runners/; a
    repo pins the prior plugin version to drop one
  observation:
    duration: the suite is complete when all runners plus B9 are shipped and
      BJ1/BJ2 pass

open_decisions: []
---

## Intent

VELDO is a platform used across many projects. If it does not ship the common
runners, every project rebuilds its own and never contributes back - pure waste.
This plan ships the batteries: a reference runner for each common product
surface, so verification effort compounds into VELDO. Each runner drives the real
surface and fails on a broken fixture, and each is pluggable so a repo runs only
the runners its surfaces need.

## Context

Grounded in a survey of ~/projects and a deep survey of openclaw (our largest
codebase, ~8500 files, an agent/coding harness) used as INPUT for which surfaces
are worth a battery. openclaw's own test lanes made several surfaces obvious:
agent-loop/tool-execution (its single largest test surface), contract/schema
testkits, streaming, process lifecycle, config-schema, plugin loading, sandbox
isolation, security guards, and static architecture guardrails - alongside the
backend, LLM, auth, integration, CLI, and mobile surfaces already evident across
our projects. Web (W5), Android (W7), and design/visual (W6) shipped in VELDO 1.0.

## Out of scope

The telecom/CoreConnect protocol runner (a Bcengi extension, not core VELDO), and
forcing any runner into the veldo repo's own gate.

## Revisions

Revision 2 (2026-07-16): expanded the suite after the openclaw survey - added
agent-loop/tool-execution, contract/schema, streaming/websocket, process/daemon
lifecycle, config-schema validation, security-guard, packs/claude/extension loading,
sandbox/isolation, MCP, terminal/TUI, and static-invariant guardrail runners;
regrouped the feature tree into backend, intelligence, client, boundary, systems,
and safety surfaces. No items were shipped under revision 1, so nothing is
invalidated.
