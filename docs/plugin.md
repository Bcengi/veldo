# Veldo Plugin Guide

*Install Veldo into any repository in minutes: the plugin carries the agents, skills, and enforcement; one init command lays down the repository substrate.*

*Version 2.7, 2026-07-22*

## 1. What the plugin is

The Veldo plugin packages the local core for running the [Veldo Development Method](method.md): templates, a fail-closed gate, contract and evidence validation, the guard, and the pipeline skills. It does not yet package everything the method describes; `.veldo/capabilities.yaml` inside the plugin is the machine-readable truth of what is mechanical, what is a reference implementation, what is agent procedure, and what is still absent. Where this guide or the setup describes a behavior whose capability is marked absent, that text is a specification of target behavior, not a description of the current release:

| Component | What it is | How it arrives |
|---|---|---|
| 5 agents | The Veldo roles: spec, implementer, verifier, reviewer, steward | Native plugin components; available in every project while the plugin is enabled |
| 8 skills | `/veldo:run` (the whole pipeline, end to end) and `/veldo:status`, plus the composable steps: `/veldo:init`, `/veldo:spec`, `/veldo:gate`, `/veldo:proof`, `/veldo:review`, `/veldo:index` | Native plugin components |
| Guard hook | Blocks merge and push attempts when the gate is not green for HEAD or no proof manifest exists for HEAD | Wired automatically while the plugin is enabled |
| Templates | The repository substrate: `VELDO.md`, `CLAUDE.md` rules, `specs/` templates, `.veldo/` policy and validator and contract examples, `scripts/` gate and index generator | Laid down once per repository by `/veldo:init` |

The split is deliberate. Agents, skills, and hooks are identical everywhere, so they live in the plugin and upgrade centrally. The substrate is repository-specific (your checks, your protected paths, your specs), so it lives in your repository as ordinary reviewed files.

### 1.1 One method, seven tools

This guide describes the Claude Code plugin. Veldo also ships as seven self-contained multi-tool packs, one per AI coding tool (Claude Code, Cursor, Codex CLI, GitHub Copilot, Antigravity CLI, OpenCode, and Aider), each a complete drop-in assembled byte-identical from the one canonical engine. Claude Code is a peer pack, not a privileged base, and enforcement is identical on every tool: the tool's native hook where it has one, a git pre-push hook everywhere, and the CI required status check as the server-side backstop. The manifest `.veldo/packs.json` declares all seven; the drift-check holds every pack byte-identical to the source and the cross-pack conformance harness proves every pack enforces the same gate. See [`../packs/README.md`](../packs/README.md).

## 2. Install

From the marketplace hosted in the Veldo repository:

```
/plugin marketplace add Bcengi/veldo
/plugin install veldo@veldo
```

The repository's `.claude-plugin/marketplace.json` is what makes `veldo@veldo` resolvable: the first `veldo` names the plugin, the second the marketplace.

Then, once per repository:

```
/veldo:init
```

Init copies the templates into the repository without overwriting anything that exists, prepends the Veldo rules to an existing `CLAUDE.md` rather than replacing it (behind an idempotency marker, so re-running init never duplicates the block), and then configures with you, not for you: the real format, lint, type, test, and build commands go into `scripts/verify.sh`, and the paths where being wrong is unrecoverable go into `.veldo/policy.yaml`. It finishes by running the gate once and validating the contracts. Everything lands as uncommitted files: you review and commit the initialization like any other change. In fact, initialization IS the repository's first Veldo change: give it a specification, run the gate, produce proof, exactly as the pilot repository did. The guard's evidence rules (below) are what let that first push carry its own proof.

## 3. The first change

1. `/veldo:spec <what you want>` - the spec agent interviews you and drafts the specification; you approve it to `ready`.
2. `/veldo:run VELDO-0007` drives everything that follows: implementation, the gate, the proof manifest, and the fresh-context review (dispatched to the veldo-reviewer subagent), ending with a receipt of what was proven and whether anything awaits a human. The individual steps (`/veldo:gate`, `/veldo:proof`, `/veldo:review`) remain available for inspection and debugging.
3. Merge. The guard blocks mechanically when the gate is not green for HEAD, proof is missing, no passing verdict is bound to the commit, a protected path lacks a live approval, or an emergency debt is open. Branch protection can enforce the same server-side; the plugin does NOT configure it - the repository owner must, before claiming server-side enforcement.

A small change runs end to end in minutes rather than days, and every step after the spec is agent work.

## 4. What the guard enforces

On any merge or push the agent attempts through its shell, the guard applies these rules and blocks with a clear message on failure:

1. The canonical gate is green for exactly the current commit. Proof is valid only for the state it ran against; if you changed anything since the gate ran, run it again.
2. A proof manifest exists for exactly the current commit.
3. Evidence-only commits (touching only `proof/`, `.veldo/`, and `specs/`) inherit the parent's proof; evidence needs no evidence about itself, and this is what lets the evidence commit be pushed.
4. The emergency lane: with `VELDO_EMERGENCY=1` set by a human, the guard allows the push and records an emergency event in the log; the backfill debt (method section 4) is then open until the specification, proof, and review land.

The mechanical set at the push boundary is now: gate freshness, proof existence, verdict requirement, protected-path approvals, and emergency debt, plus the two release valves (evidence commits, the emergency lane). Ready-spec status remains procedure (the run skill refuses drafts; nothing blocks outside it), and the secret scan runs at gate time, not on every write; the capability manifest is the full honest list.

With both the plugin and the repo-local wiring present the guard may run twice; it is idempotent and the duplication is harmless, so keep both when a team mixes plugin and manual setups. The hook runs on the developer machine and is the first line, not the last: the same rules belong in branch protection and CI (see setup, section 4.4), where a local edit cannot remove them.

### 4.1 Enforcing the same gate server-side

The guard is the first line; branch protection is the last, because a local hook can be edited away and a required check cannot. Veldo ships the artifact that closes that gap: a CI workflow template at `engine/.github/workflows/veldo-gate.yml`, laid into your repository by `/veldo:init` at `.github/workflows/veldo-gate.yml`. It runs the SAME gate a developer runs locally, by invoking the exact commands rather than reimplementing any check:

```
./scripts/verify.sh        # the canonical catalog; its unit slot is scripts/selftest.py
python3 .veldo/policy_check.py   # the reader the pre-push guard calls
```

That is the mirror: `verify.sh` is what the guard requires green for HEAD, and `policy_check.py` is precisely what the guard's third stage runs (verdict bound to the commit, path-scoped approvals for protected paths, no open emergency debt). Running the same two commands server-side means the check that runs where no one is watching is the check the developer already passed, with no divergence between them. The workflow checks out full history so the policy check's commit-range and parent-commit logic resolves as it does locally.

Shipping the workflow does not by itself block a bad merge; making it a **required status check** does. That step is a host setting the repository owner applies once, and the plugin cannot apply it for you:

1. Push a change so the `veldo-gate` workflow runs at least once; the check name registers with the host.
2. On the protected branch (for example `main`), add a branch-protection rule that requires the `veldo-gate` check to pass before merging, requires the branch to be up to date first (so the gate re-runs after trunk moves), and disallows direct pushes that bypass it.
3. Optionally map protected paths to human approvers with a code-owners file, so the same paths `policy.yaml` floors also require a named review on the host.

With the required check in place, a change whose `verify.sh` is red or whose `policy_check.py` exits non-zero cannot merge, for every contributor and every agent, including agents no one is watching. This is the guidance the setup calls for at stage 0 (branch protection with the gate as a required check) and stage 1 (required checks everywhere plus code owners); the server-side merge queue that re-proves a merged result is a later, deliberately deferred capability. The honest status of this wiring is in `.veldo/capabilities.yaml`: the workflow is a shipped reference artifact, and requiring it is a documented procedure a human performs, never something the repository self-enforces.

## 5. The manual path (no plugin)

Everything the plugin does can be done by hand: copy `engine/` into your repository root, copy `packs/claude/agents/` to `.claude/agents/` and `packs/claude/skills/` to `.claude/skills/`, and merge `templates/.claude/settings.json` (the guard wiring) into your repository's `.claude/settings.json`. Note the invocation difference: the manual path exposes bare names (`/spec`, `/gate`); rename the copied directories to `veldo-spec` style if those collide with local skills. The plugin path is better because upgrades are central; the manual path exists so nothing about Veldo depends on any single distribution mechanism.

## 6. Upgrading

The plugin versions like any dependency. Upgrading the plugin never rewrites your repository's substrate: templates are only laid down by init, and init never overwrites existing files. When a new plugin version changes a template you already have, the changelog says so and you apply it as an ordinary reviewed change in your repository. Team-wide version consistency is a convention at small scale (announce upgrades); the guard's rules are stable across versions, so drift degrades politely rather than dangerously.

## 7. Contents reference

```
packs/claude/
├── .claude-plugin/plugin.json      # manifest
├── agents/                         # veldo-spec, veldo-implementer, veldo-verifier,
│                                   # veldo-reviewer, veldo-steward
├── skills/                         # run, status, init, spec, gate, proof,
│                                   # review, index (invoked as /veldo:run, ...)
├── hooks/hooks.json                # guard wiring (PreToolUse on Bash)
├── scripts/veldo-guard.sh           # the guard, shipped with the plugin
└── templates/                      # the repository substrate laid down by init
    ├── CLAUDE.md                   # entry-point rules (merged, never overwritten)
    ├── VELDO.md                     # the operating rules
    ├── specs/                      # TEMPLATE.md, TEMPLATE-standing.md, index.md
    ├── proof/                      # proof manifests live here
    ├── .veldo/                      # policy.yaml, validate.py, examples/
    ├── .claude/settings.json       # repo-local guard wiring (manual path)
    ├── .github/workflows/          # veldo-gate.yml: the same gate as a CI check
    └── scripts/                    # verify.sh, update_index.py, veldo-guard.sh
```

## 8. Implementation status (generated truth)

The plugin ships `.veldo/capabilities.yaml`: every capability the documents mention, with its honest status - `mechanical` (fails closed), `reference` (shipped, wire per repo), `procedure` (agent-instructed), `absent` (target behavior), or `control-plane` (deferred by the build order). Read it before trusting any sentence in any Veldo document that says "the gate lints" or "the guard blocks": if the manifest says absent, the sentence is a target. Two consequences of the current statuses, in prose:

- A freshly initialized repository's gate is RED until every catalog item is declared required, not-applicable with a reason, or waived with an expiry. An unconfigured gate can no longer pretend to be green.
- UI and mobile execution (journey runners, token lint, baseline comparison, emulator driving) is per-repository wiring today, with one shipped reference tool (the visual composite builder). The setup's section 8.1 specifies the required target; parts of the runbook's UI material are target behavior until those capabilities land.

## 9. Veldo by example

Nine worked examples and a set of failure drills, from installing Veldo to an emergency. The backend feature (8.2) is told in full; the others show only what changes. Every example is the same loop wearing different clothes, which is the point: once you know one, you know Veldo. In every example the human speaks a handful of sentences and the machine does the rest; /veldo:run is the command that makes that literal.

### 9.1 Initializing a repository (your actual first experience)

The situation: an existing repository, never touched by Veldo.

**You say:**

> /veldo:init

**The dialogue.** Init detects the stack and asks instead of guessing:

> Agent: I found npm test, npm run build, and a Playwright config. Which commands are authoritative for the gate?
> You: lint, typecheck, test, build. UI tests too.
> Agent: Which paths here are unrecoverable if wrong?
> You: migrations and the payments module.
> Agent: Should user-facing visual changes require a design owner's verdict?
> You: Yes.

**What happens.** The substrate lands as uncommitted files: VELDO.md, the specs templates, the policy with YOUR protected paths, the gate wired to YOUR commands, the validator with its contract examples. Nothing existing is overwritten; an existing CLAUDE.md gets the Veldo block prepended behind an idempotency marker (re-running init changes nothing). Then the adoption becomes the repository's first Veldo change: a spec (adopt Veldo), the gate run green on your real suite, a proof manifest, an independent review, and a commit you approve.

**What this teaches:** Veldo governs its own installation. It arrives as a proven change, not as unreviewed process configuration.

### 9.2 A backend feature (the whole loop, told in full)

The situation: your API has no rate limiting on the search endpoint and a partner just hammered it.

**You say** (to the agent, in a terminal, an IDE, or through your chat assistant; your words, not a form):

> /veldo:spec add rate limiting to the search endpoint

**The dialogue.** The spec agent interviews you; you answer in plain language:

> Agent: What outcome matters? Per-user limits, per-key, or global?
> You: Per API key. 60 requests a minute, burst of 10.
> Agent: What should a limited caller receive?
> You: 429 with a Retry-After header.
> Agent: Should existing internal callers be exempt?
> You: Yes, the internal service key bypasses it.

**The spec that results** (`specs/VELDO-0007-search-rate-limit.md`, drafted for you, you approve it to `ready`):

```yaml
---
schema: veldo.spec/v1
id: VELDO-0007
title: Rate limit the search endpoint
status: ready
risk: standard
owner: you
human_approval: not_required
acceptance_criteria:
  - id: AC1
    text: A key exceeding 60 requests per minute (burst 10) receives 429 with a Retry-After header.
  - id: AC2
    text: Requests under the limit are unaffected, verified by the existing search test suite.
  - id: AC3
    text: The internal service key is exempt.
required_evidence: [unit, integration]
rollback: disable the rate_limit_search flag
reversible: true
---
```

**What happens next, none of it yours to do.** The implementer builds the limiter behind a flag, writes tests for all three criteria, runs `/veldo:gate` (the full canonical gate: tests, secret scan, contract validation) until green, then `/veldo:proof` writes `proof/VELDO-0007/manifest.json` mapping each criterion to its passing test. `/veldo:review` dispatches the fresh-context reviewer, which reads the spec, the diff, and the proof, reruns anything it doubts, and emits a verdict. Merge follows on green; the guard would have blocked it mechanically if the gate were stale or the proof missing.

**The receipt you see at the end:**

> VELDO-0007 shipped. 3/3 criteria proven (429+Retry-After, suite unaffected, internal key exempt). Gate green on 1,507 tests. Reviewer: pass, no blocking findings. Rollback: flag off.

**What this teaches:** the loop itself. You spoke twice: once to state intent, once to approve the spec. Everything between was built and proven by machines.

### 9.3 A UI change (the design lane)

The situation: the orders screen needs an empty state, and the designer has mocked it.

What changes from 8.2: the spec pulls exact values from the design tool's API into the criteria (token references, spacing, the component to use), never a screenshot. Required evidence gains two entries:

```yaml
acceptance_criteria:
  - id: AC1
    text: The empty state renders the illustration card component with spacing tokens space-6/space-4; no raw pixel values are introduced.
  - id: AC2
    text: The screen matches the approved baseline within tolerance on desktop and mobile widths.
required_evidence: [unit, baseline, design_review]
```

The gate lints that only design tokens are used (a raw hex value fails the build). A human compares the rendered screen against the mock once, side by side, and approves; that screenshot becomes the locked baseline the gate defends from then on. And the change does not merge until the design owner, acting as an independent reviewer, files the same verdict contract an agent reviewer files, with their name in the reviewer field.

**What this teaches:** fidelity is machine-checked at the token and baseline layers, and taste stays human, as a review lane, not a meeting.

### 9.4 An infrastructure change (a protected path)

The situation: Postgres needs a version bump in the deployment configuration.

What changes: the diff touches `infra/`, which the policy floors at high risk, so the computed risk is high no matter what the spec declared. Two consequences follow mechanically: the reviewer runs at higher independence, and the change cannot merge without a human approval record bound to this exact commit and proof:

```json
{
  "schema": "veldo.approval/v1",
  "decision": "approved",
  "approver": {"id": "you", "role": "owner"},
  "scope": {"spec_id": "VELDO-0011", "commit": "9c2f41e", "proof": "proof/VELDO-0011/manifest.json"},
  "expires_at": "2026-07-16T18:00:00Z"
}
```

If anything changes after you approve, a new commit, a regenerated proof, the approval is stale and the merge blocks again. You approved a thing, not a direction.

**What this teaches:** protected paths turn human judgment from a habit into a recorded, expiring, commit-bound decision, and nothing else in the flow slows down.

### 9.5 A bug arriving as a report (intake)

The situation: support forwards a ticket: "customer says exporting an empty project crashes the app."

What changes: no one writes a spec. The intake agent reads the ticket, reproduces the crash in a scratch workspace, and drafts the spec with the reproduction attached as its first criterion:

```yaml
acceptance_criteria:
  - id: AC1
    text: The attached failing test (export of a zero-item project) reproduces the reported crash before the change and passes after it.
  - id: AC2
    text: The surrounding export suite shows no regression.
```

If it cannot reproduce, it asks the reporter clarifying questions in the ticket's own comments; the reporter never leaves their tool, and the ticket's status updates automatically as the spec moves (ready, in progress, shipped, with the fix version in a closing comment).

**What this teaches:** a bug's first acceptance criterion is its reproduction, and humans report in their own words while agents do the formalizing.

### 9.6 A dependency bump (a standing specification)

The situation: the HTTP client library releases a security patch, the third dependency update this month.

What changes: nothing is written at all. A standing specification (`specs/VELDO-STANDING-0002-dependency-updates.md`) already defines the class once: criteria (suite green, no API breakage, changelog reviewed for breaking notes), risk (standard, floored to high if the dependency is security-critical), evidence (the full gate). The bump runs the ordinary loop as an instance: its proof manifest references the standing spec's id, and the index tracks the class, not each instance.

**What this teaches:** recurring mechanical work keeps full proof and zero per-change ceremony.

### 9.7 A database change (decomposition, not heroics)

The situation: store each customer's preferred locale and use it on newly generated invoices.

What changes: the spec agent refuses to package this as one change, because a required column, a backfill, a read-path switch, and cleanup bundled together cannot be rolled back. It proposes three specifications instead:

1. Add nullable `preferred_locale`; begin dual-writing. (Additive migration; the old application version stays compatible; rollback = stop writing.)
2. Backfill existing customers in resumable batches; switch reads with a fallback. (Data-owner approval; integrity proof; rollback = read the old path.)
3. After an observation window proves full population: enforce non-null, remove the fallback.

Each runs its own loop with its own gate, proof, review, and merge, and the system is correct and shippable after every one of the three merges.

**What this teaches:** decomposition is not project management; it is the mechanism that preserves proof and reversibility where they are hardest, in the database.

### 9.8 An emergency (the lane with teeth)

The situation: production is down; a bad config value is rejecting every payment webhook.

What changes: everything, for one hour. A human declares the emergency; the fix goes out by the fastest safe means with `VELDO_EMERGENCY=1` set, and the guard allows the push while recording an `emergency.push` event in the log. The backfill debt is now open: within 24 hours the specification describing what was intended, the proof that the shipped fix satisfies it, and an independent review of what actually went out all land as normal artifacts. An unclosed backfill blocks the next ordinary merge, so the debt cannot silently rot.

**What this teaches:** the method bends its order under pressure, never its evidence, and an emergency that recurs is a missing specification.

### 9.9 A trivial change (proportionate proof)

The situation: an error message has a typo.

What changes: almost nothing, deliberately. The spec is three lines, its single criterion is the corrected string asserted by one test, the gate runs, the proof manifest has one entry, review is a fast pass, and the whole loop takes minutes. What does NOT happen: skipping Veldo because the change is small. Small changes still cause defects; the proportionality rule cuts ceremony, never evidence.

**What this teaches:** the floor of the method is low enough that there is never a reason to step outside it.

### 9.10 Failure drills (what refusing looks like)

Happy paths teach less than refusals. Each drill is worth running once in a sandbox so the team has seen the system say no. Honesty note (per the capability manifest): drills 1, 2, 6, 7, and 8 refuse mechanically in the current release; 3, 4, and 5 are target behavior whose enforcement is landing - run them anyway, because the procedure holds even where the hook does not yet:

1. **Stale proof.** Gate green, then change one file, then try to push. The guard blocks: proof is valid only for the state it ran against.
2. **Missing proof.** Gate green, no manifest, push. Blocked, with the message telling you exactly what to produce.
3. **Trunk moved.** Two branches pass alone and fail together; the merged result must re-prove before landing.
4. **Ambiguous spec.** The spec agent hits a material product question and the human is unavailable: the work goes to `blocked`, and nothing gets guessed.
5. **Two failed reviews.** The third attempt does not happen; a human looks, and it is almost always the spec.
6. **Missing design verdict.** Every machine check green, and the merge still waits, because `design_review` is in the required evidence and nobody with the role has filed it.
7. **Stale approval.** An approval bound to commit A does not authorize commit B. Change anything, approve again.
8. **Overdue emergency debt.** An unclosed backfill blocks the next ordinary merge; the debt cannot rot silently.

**What these teach:** the rules are mechanical. Nothing here depends on anyone remembering to object.

## 10. Runner catalog and gate-slot wiring

The plugin ships a reference runner for every common product surface. A runner PROVES behavior by driving the real surface and asserting the observed result, and each ships a passing fixture (exit 0) and a deliberately-failing fixture (exit 1 with the failure named) so it cannot rubber-stamp a vacuous pass. None of them run in this repository's own gate: a runner is a battery an adopting repo wires into the gate slot for a surface it actually has (the proportionality rule). This catalog says, per runner, what it asserts, where it lives, which gate slot to point it at, and what its status means.

**Status defers to the manifest.** The Status column below repeats `.veldo/capabilities.yaml`, which is the authoritative source. If a value here ever disagrees with the manifest, the manifest wins and this table is the bug. Two statuses appear:

- `mechanical` - the runner's control logic is gate-tested end to end in this repository with stdlib only (its fixtures are driven in the unit slot on this box), so the shipped artifact is proven here, not just asserted. It still needs per-repo wiring to run against a real product surface.
- `reference` - the runner needs a product surface this repository does not have (a browser, an emulator or simulator, a container runtime, a live endpoint, a model provider, a database), so the home gate cannot drive it end to end. Its control logic is still gate-tested here through a fake driver or an in-process stdlib server, and the home gate marks the matching surface slot `na` with a reason. An adopting repo that HAS the surface wires the runner in and the slot goes from `na` to `required`.

**Gate slots.** The gate slot column names a `CHECK_*` from the canonical catalog in `scripts/verify.sh` (method section 3, stage 6). Where a surface has no dedicated canonical slot (agent loops, LLM evals, terminals, guardrails, and the like), an adopting repo points `CHECK_extra` at the runner or declares its own named required slot; the manifest note for each runner states the intended slot.

| Runner (capability) | Home under `engine/` | Status | What it asserts | Fixture pair (under `fixtures/`) | Adopting-repo gate slot |
|---|---|---|---|---|---|
| journeys_runner | `scripts/runners/web/veldo-web-runner.mjs` | reference | Every step of a real browser flow; exits 1 on a broken flow with a failure screenshot | `pass.journey.json` / `fail.journey.json` | CHECK_journeys |
| accessibility_scan | `scripts/runners/web/veldo-web-runner.mjs` | reference | Dependency-free DOM a11y (img-alt, input-label, control-name, html-lang, duplicate-id) | `app.html` / `broken.html` (driven by the journeys) | CHECK_accessibility |
| ui_state_runner | `scripts/runners/web/veldo-web-runner.mjs` | reference | Named UI states captured as screenshots by driving the flow to them | `pass.journey.json` / `fail.journey.json` | CHECK_ui_states |
| token_lint | `scripts/runners/design/token_lint.py` | mechanical | Raw hex/rgb color and non-allowlisted px fail against a token set | `good.css` / `bad.css` (+ `tokens.json`) | CHECK_token_lint |
| baseline_comparator | `scripts/runners/design/baseline_compare.py` | mechanical | Render vs approved-baseline pixel diff with per-baseline tolerances; size mismatch auto-fails | `baselines.config.json` (good vs changed render) | CHECK_visual_baselines |
| mobile_emulator_driving, device_matrix_execution | `scripts/runners/mobile/veldo_android_runner.py` | reference | Real adb journey plus lifecycle re-drives (rotation, process death, background, network loss) and device-matrix completeness | `pass.journey.json` / `fail.journey.json` | CHECK_journeys (mobile) |
| ios_simulator_driving | `scripts/runners/mobile/veldo_ios_runner.py` | reference | Real xcrun simctl journey, lifecycle re-drives, and an accessibility bridge that fails loud when absent (macOS only) | `fixtures/ios/pass.journey.json` / `fixtures/ios/fail.journey.json` | CHECK_journeys (mobile, macOS) |
| http_api_runner | `scripts/runners/api/veldo_api_runner.py` | reference | Per-step HTTP status and JSON assertions over a JSON journey; stops at the first failure | `pass.journey.json` / `fail.journey.json` | CHECK_contract or CHECK_integration |
| authorization_runner | `scripts/runners/auth/veldo_auth_runner.py` | reference | Allow/deny per identity; a 2xx on a deny is a bypass and owner data in the body a cross-tenant leak | `pass.journey.json` / `fail.journey.json` | CHECK_security or CHECK_contract |
| db_migration_runner | `scripts/runners/db/veldo_db_runner.py` | reference | Up then down round trip against real sqlite, data invariants, latency budgets; an asymmetric down fails | `pass.journey.json` / `fail.journey.json` | CHECK_migration |
| perf_load_runner | `scripts/runners/perf/veldo_perf_runner.py` | reference | Latency percentiles (p50/p95/p99), throughput, and error-rate budgets under concurrency | `pass.journey.json` / `fail.journey.json` | CHECK_performance |
| integration_contract_runner | `scripts/runners/integration/veldo_integration_runner.py` | reference | Response contract: required fields present and typed via dotted paths, forbidden fields absent | `pass.journey.json` / `fail.journey.json` | CHECK_integration or CHECK_contract |
| cli_process_runner | `scripts/runners/cli/cli_runner.py` | reference | A command's observable contract: exit code, stdout/stderr contains or equals, timeout | `pass.cases.json` / `fail.cases.json` | CHECK_integration (cli) or CHECK_extra |
| llm_eval_runner | `scripts/runners/llm/veldo_llm_runner.py` | reference | Behavioral graders, cost/latency/pass-rate budgets, and regression on a prompt change | `pass.journey.json` / `fail.journey.json` | CHECK_extra (eval) |
| agent_loop_runner | `scripts/runners/agent/veldo_agent_runner.py` | reference | Observed tool invocations and results, forbidden tools never called, final-answer graders, a max_turns bound | `pass.journey.json` / `fail.journey.json` | CHECK_extra (agent or eval) |
| contract_schema_runner | `scripts/runners/contract/veldo_contract_runner.py` | reference | Versioned golden-schema drift: a removed field or a type change is breaking | `pass.contract.json` / `fail.contract.json` | CHECK_contract |
| streaming_sse_runner | `scripts/runners/streaming/veldo_streaming_runner.py` | reference | SSE/websocket framing, contiguous chunk sequencing, a terminal that must be last, assembled-data graders | `pass.stream.json` / `fail.stream.json` | CHECK_contract (streaming) or CHECK_extra |
| process_lifecycle_runner | `scripts/runners/process/process_runner.py` | reference | A real child through spawn, SIGTERM, respawn with a distinct pid, and kill-tree orphan detection | `pass.lifecycle.json` / `fail.lifecycle.json` | CHECK_integration (lifecycle) or CHECK_extra |
| config_schema_runner | `scripts/runners/config/config_runner.py` | reference | Valid samples accepted, invalid samples rejected for the right named reason | `pass.schema.json` / `fail.schema.json` | CHECK_contract (config) or CHECK_extra |
| security_guard_runner | `scripts/runners/security/security_guard_runner.py` | reference | A labeled corpus of hostile and benign inputs; a hostile input allowed is a named bypass | `pass.security.json` / `fail.security.json` | CHECK_security |
| sandbox_isolation_runner | `scripts/runners/sandbox/sandbox_isolation_runner.py` | reference | Container confinement; a path required denied but allowed is a named breach (container runtime required) | `pass.sandbox.json` / `fail.sandbox.json` | CHECK_security (sandbox or isolation) or CHECK_extra |
| static_guardrail_runner | `scripts/runners/guardrail/guardrail_runner.py` | reference | Line-oriented source invariants per glob; a violation is file:line with the rule name | `fixtures/pass` / `fixtures/fail` (+ `rules.json`) | CHECK_extra (guardrail) or CHECK_security |
| mcp_tool_runner | `scripts/runners/mcp/mcp_runner.py` | mechanical | JSON-RPC handshake, tools/list, tools/call including a proxied tool, and proper error framing over stdio | `pass.mcp.json` / `fail.mcp.json` | CHECK_contract or CHECK_integration |
| terminal_runner | `scripts/runners/terminal/terminal_runner.py` | mechanical | A pty-driven TUI rendered through a real VT renderer: cell chars, attributes, and scrollback | `pass.terminal.json` / `fail.terminal.json` | CHECK_extra (terminal) |
| plugin_load_runner | `scripts/runners/plugin/plugin_load_runner.py` | mechanical | A safe archive loads and a malicious one (zip-slip, absolute path, escaping symlink) is rejected with nothing escaping the target | `pass.plugin.json` / `fail.plugin.json` | CHECK_contract (plugin) or CHECK_extra |

### 10.1 The catalog cannot rot (BJ1)

A catalog that is maintained by hand drifts the moment someone adds a runner and forgets the table. So the completeness property is mechanical, not editorial: `scripts/check_runner_catalog.py` enumerates every directory under `engine/scripts/runners/` and fails closed unless each one has a passing fixture, a deliberately-failing fixture, a `capabilities.yaml` entry whose status is non-blank and in the manifest vocabulary, and a gate wiring (a Python runner must be referenced in `scripts/selftest.py`, which drives its control logic in the unit slot; a runner with no importable module, such as the browser-driven web runner, must instead ship a fixture-driving `test_*.sh` wrapper). The check runs inside the unit slot (`scripts/selftest.py`), so a runner added later without its proving fixture pair or without a capabilities entry turns the gate red. It observes real files, so it cannot be satisfied by an entry in this table alone.

### 10.2 The home gate runs no surface (BJ2)

Running the Veldo home gate needs no backend, no emulator or simulator, no container runtime, and no third party. Two facts make this true and keep it true:

- The surface-requiring slots are declared `na` with a reason in `scripts/verify.sh`: journeys, ui_states, accessibility, token_lint, visual_baselines, contract, integration, migration, performance, and security are all not-applicable here because this repository has no such surface of its own. A slot is never left blank (a blank item is red by the fail-closed rule), so each is a recorded decision.
- No required gate command shells a runner. `check_runner_catalog.py` asserts mechanically that no `CHECK_*="required:..."` command in `scripts/verify.sh` contains `runners/`. The unit slot imports runner control logic in process with stdlib only, which is not the same as driving a live surface, so the home gate stays hermetic while still proving every mechanical runner end to end.

## 11. The fleet: elastic parallel workers

The plugin builds one change at a time by default, but a repository with several independent ready specifications does not have to build them serially. The fleet is a set of workers that each pull ready work from anywhere in the repository, build it, and land it, so throughput scales with the workers you run rather than with one operator's attention.

**How the fleet arrives.** The fleet ships in the engine. Installing a pack lays the full engine into a repository, and the fleet is part of that engine, so an adopter has the fleet the moment the pack is installed. This is the two-tier adoption model the setup guide states in full: installing a pack lays the whole engine (the gate, the runners, the fleet, all of it), while `/veldo:init` lays only the minimal governance substrate (the canonical gate, the contracts, the templates) for a repository that wants the enforced spine without the rest, kept minimal by design. The path that delivers the fleet is installing a pack.

**The `veldo` CLI is the front door.** A single `veldo` executable drives the fleet and reads from it, a thin dispatcher over the engine modules already present, reimplementing nothing:

- `veldo work` runs one worker in the current terminal: it claims the next ready unit, builds it, lands it, and repeats until the frontier is drained.
- `veldo fleet N` runs up to N workers paced by the token governor, reconciling the active pool to the count the governor allows.
- `veldo account add <name>` and `veldo account list` manage the accounts a fleet runs under (below).
- `veldo status` and `veldo watch` read the live run state; `veldo answer`, `veldo steer`, and `veldo abort` speak to a running build through its inbox.

**A per-repository capability.** The fleet is scoped to the work a repository (or a workspace of repositories) can see. Workers self-divide with no central coordinator: each unit of work is a file under the git common directory that a worker claims atomically, so two workers never build the same unit, and a serialized lander merges each finished build to the trunk one at a time. Work routes to a worker by capability (a build that needs a particular machine only claims onto a worker that advertises it), and a heavy shared dependency is brought up once for the whole fleet and attached read-only rather than duplicated per worker.

**The per-account model.** A worker runs under a named account, each with its own persisted login (its own `CLAUDE_CONFIG_DIR`). `veldo account add` registers an account once; from then on a worker driven under that account reuses its saved login with no re-login. The token governor paces each account against its own measured burn and sums the per-account allowances into the pool, so one account that has spent its budget never stalls the others, and a backed-off account resumes when its own window rolls off.

**No detached process.** A worker is a real in-session worker, never a detached or headless background process: the fleet spawns nothing that outlives the session, and a backed-off pool waits in-session and re-checks its budget before resuming. That is a hard boundary, not an implementation detail. The build step, the fresh-context review, and the in-session start primitive are delegated seams that fail loud rather than fabricate a result, exactly as the executor's build and review steps do; the fleet assembles the real machinery around them and adds no silent shortcut. The honest status of every fleet capability is in `.veldo/capabilities.yaml`, the same generated truth the rest of this guide defers to; the operational runbook for driving a fleet is in [`runbook.md`](runbook.md).

## 12. Tracker integration: Jira and Confluence

Veldo lives in the repository, but the people who report work and the people who watch its status often live in a tracker. Veldo bridges to one without ever moving the source of truth out of the repository. The bridge runs in two directions, both one-way, and neither ever polls the tracker: the MIRROR projects the repository's truth outward, and INTAKE pulls a report inward as a spec draft. This section is how an adopter turns it on and what actually ships. For the day-to-day human workflow (what to put on a ticket, how to run intake, and what happens to the ticket after), see the operator companion, [`tracker-operator-guide.md`](tracker-operator-guide.md).

### 12.1 What the two directions do

**The mirror (repository to tracker).** A spec's lifecycle events (`spec.ready`, `spec.blocked`, `verdict.recorded`, `spec.shipped`, `merge.completed`) project onto the spec's child issue as a status change and, when it ships, a closing comment. A plan's planning-layer events (`plan.created`, `plan.approved`, `plan.revised`, `work.pulled`) project the plan's work graph onto an EPIC and its CHILD issues: the epic is keyed to the plan (one plan, one epic, never forked) and every work item becomes a child, so the whole structure exists on the tracker even for items not yet started. The mirror writes ONLY status and comments, never a spec or plan definition, so the repository stays the single source of truth. It is a reconciler, like the index generator: it recomputes the desired tracker state from the current repository state each run and applies it, so it is idempotent under at-least-once event delivery with no processed-offset ledger. Replaying the whole event stream, or a doubled event, records no duplicate transition and no duplicate comment. It is driven by the existing event stream, never by polling the tracker.

**Intake (tracker to repository).** A Jira ticket or a structured Confluence requirements page becomes a routing-resolved `veldo.spec/v1` DRAFT. For a bug ticket, the first acceptance criterion is its reproduction and the report is captured as the observable; for a Confluence requirements page, the acceptance criteria come from the page. The source is linked in the draft's `intake_source` field, the draft is bound to the resolved repository, and it feeds the existing `/veldo:intake` skill rather than a new pipeline. Tracker content is untrusted input: it is sanitized against front-matter injection and treated as data, never as instructions.

### 12.2 Turning it on

The integration is off until a repository (or the organization that owns several repositories) wires it. Four pieces:

1. **The per-org config, `.veldo/trackers.json`** (`veldo.tracker/v1`). It declares two things. First, ROUTING: because one tracker project commonly spans many repositories, every ticket declares which repository it targets. The default mechanism is a label convention (`"mechanism": "label"`, `"label_prefix": "veldo-repo:"`), so a stock tracker project with no custom fields works; a `component` or a named `field` are the other mechanisms. Second, the `status_map`: it maps each Veldo spec status onto your tracker project's OWN status names (for example `ready` to `To Do`, `shipped` to `Done`). The mirror only transitions a child within this mapped set; a Veldo status with no mapping is recorded as a comment, never invented as a transition, and omitting the `status_map` entirely makes the mirror comment-only. A ready-to-edit template ships at [`engine/.veldo/trackers.json`](../engine/.veldo/trackers.json); a `status_map` can be global with an optional per-repo override.

2. **The optional `tracker_repo` front-matter field** on a spec or a plan names the repository the work targets when it is mirrored, since one tracker project spans many repositories. It is validated parallel to the lane fields: present, it must be a non-empty string, and when a tracker config is wired it must name a KNOWN repository or the contract check fails closed (a routing target nobody can resolve is a decision nobody made); absent, it is the single-repository default. A spec with no `tracker_repo`, no config, or an unroutable repository is simply skipped by the mirror, not errored.

3. **Auth by reference, never a secret in a file.** A tracker adapter resolves its token from a reference, `token_ref` (for example `env:JIRA_TOKEN`), and FAILS CLOSED if nothing resolves. The default resolver reads the named environment variable; a repository can inject its own resolver to read another secrets store. A raw credential never appears in a config file, a prompt, a proof, or a log. This is the capabilities-not-credentials rule the setup guide states, applied to the tracker edge.

4. **The Confluence requirements template**, at [`engine/confluence-requirements-template.md`](../engine/confluence-requirements-template.md). A person who never opens a repository copies its structure into a Confluence page, adds a `veldo-repo:<repo>` label to route it, and fills in the Outcomes and Acceptance Criteria sections. Intake reads the page through the vendor-neutral seam, resolves the target repository from the label (refusing by name if it names no repository, an unknown one, or more than one), and drafts the spec with those criteria.

### 12.3 What is mechanical and what is reference

The honest split, straight from `.veldo/capabilities.yaml`, which this section defers to:

- **Mechanical (enforced in code, gate-tested offline).** The routing resolver (`.veldo/tracker.py`), the routing enforcement on specs and plans (`.veldo/validate.py`), the vendor-neutral adapter seam (`.veldo/tracker_adapter.py`), the spec mirror and the epic mirror (`.veldo/tracker_mirror.py`), the intake logic for both Jira tickets and Confluence pages (`.veldo/tracker_intake.py`), and the end-to-end conformance harness (`.veldo/tracker_conformance.py`). These run in the gate against a deterministic in-memory FakeTracker with no network and no credentials, so their control logic is proven here.
- **Reference (shipped, wired per repository, needs a live instance, NOT run in the gate).** The live `JiraCloudAdapter` and `ConfluenceCloudAdapter` in `.veldo/tracker_intake.py`, the VELDO-0603 seam implemented against the Jira Cloud and Confluence Cloud REST APIs. They need a live instance and a resolved token, so the home gate does not drive them; the fake-tracker path is what runs there, the same honesty shape as the reference UI and mobile runners.
- **Not yet live, stated as such.** Epic and child creation against a live Jira instance is wired in a later increment; the mechanical epic mirror already builds and reconciles that structure against the FakeTracker, and the Jira reference adapter today reads issues, posts keyed comments, and transitions status. A Confluence wiki page has no status workflow, so the Confluence adapter reads pages and posts comments only; status and structure live on the tracker the mirror drives.

### 12.4 The governing principles

- **The mirror is one-way and the repository wins.** If the index and the tracker disagree, the repository is right, consistent with the standing rule that the index is a navigation layer and you do not recreate a tracker in Markdown. Nothing anyone types in the tracker becomes engineering truth; an answer that changes a requirement or a durable decision is committed to the spec, not left in a ticket comment.
- **Tracker content is untrusted input, never instructions.** A ticket or a page is data. Intake sanitizes it against front-matter injection, links it as a source, and never executes anything it contains.

### 12.5 The tracker-driven autonomous fleet

Sections 12.1 through 12.4 are the bridge as a set of capabilities: routing, a mirror, intake, an adapter seam. The autonomous fleet closes them into a loop so that Jira, not a person running a skill, is the front of the work queue. A ticket that a human tags, approves, and assigns flows into the fleet on its own, gets built, and comes back updated, with the human validating the actual spec in Jira and the repository staying the single source of truth. Everything named here is shipped; the live Jira edge is the same reference implementation section 12.3 describes, wired per repo.

**The single Agent user and the eligibility triple.** There is ONE shared Agent account for the whole fleet (`agent` in `.veldo/trackers.json`); the claim ledger, not the tracker, decides which worker actually runs a unit. `is_eligible(ticket, config)` in `.veldo/tracker.py` is one pure, fail-closed rule with three legs ANDed together: the ticket is assigned to that Agent user, its status is in the configured ready-for-dev set (`ready_statuses`, defaulting to include "Approved for dev"), and its repo tag resolves to a known repo through the reused routing resolver (the validated "Veldo Repo" field, or the label convention). Drop any leg - a ticket assigned to a human, in any other status, or with an unresolvable repo - and it is never picked up. It never raises and never guesses a repo.

**The inbound bridge (auto-draft), then the human promote gate.** `.veldo/tracker_bridge.py` is a non-LLM reconciler with two stages. `reconcile_drafts` acts on the two-leg pre-approval subset (assigned to the Agent user AND a resolvable repo, independent of status): it runs the existing intake to produce a `status: draft` spec bound to that repo and posts the drafted spec back onto the ticket as a keyed comment, so the human validates the ACTUAL spec. It is idempotent by the durable `intake_source` link with no processed-offset ledger - re-seeing a ticket redrafts nothing and re-posts no comment - and it does NOT promote, so a draft stays unclaimable and nothing builds. `reconcile_promotions` is the human validation gate wired: it flips an already-drafted spec from draft to ready ONLY when the ticket satisfies the FULL eligibility triple - that is, only after the human moves it to the ready-for-dev status while keeping it assigned to the Agent user. The machine never promotes its own draft (NG1); a human who reassigns the ticket off the Agent, or moves it out of the ready set, pulls it back before it builds. The promote writes nothing back to the tracker.

**The round-trip: artifact links and the reassignment at ready-to-test.** The VELDO-0603 seam gained an `assign(obj_id, assignee)` write beside comment, set_status, and the epic/child creates, idempotent by target assignee and failing loud on a missing object. The spec mirror uses it at exactly one point: when a spec crosses into review after a build (`verdict.recorded`, Veldo status `in_review`, the ready-to-test transition), the mirror posts a keyed comment carrying the artifact links that actually exist - the commit always, the PR and the proof when the events carry them, never fabricated - and reassigns the child away from the Agent user to the reviewer that `resolve_reviewer` returns (a per-repo `reviewer` in the config overrides a global one, either falling back to the ticket's reporter; with none of the three known it leaves the assignee untouched, never inventing one). Earlier lifecycle points do NOT reassign, so the fleet keeps the ticket while it works. Both writes are idempotent (links by comment key, reassign by target), and the mirror stays one-way.

**The live mirror runner, opt-in and off by default.** `.veldo/tracker_mirror_runner.py` is a non-LLM reconciler that drives the shipped one-way mirror onto a real tracker; it adds no mirror logic of its own, feeding `mirror_events` and `mirror_plan_events` from an injected event-stream reader (`.veldo/events.jsonl` in production) and an injected adapter (the live `JiraCloudAdapter` in production, the fake tracker in the gate). It is invoked explicitly through a `veldo mirror` CLI subcommand: installing Veldo lays no timer, daemon, or auto-start, running it spawns nothing detached, and each invocation is ONE reconcile pass (poll-when-run), so a cadence is the operator's own poll interval, never a hidden mechanism - the same no-detached-process boundary as the fleet supervisor. `build_live_adapter` constructs the reference adapter from the tracker connection block (`base_url` plus `token_ref`, a secret reference never a raw credential) and fails closed when no token resolves; that live path needs a real Jira, so it is not run in the gate.

**A requirements page becomes a whole plan.** `draft_plan_from_requirements` in `.veldo/tracker_intake.py` is the plan-level sibling of the single-spec intake: a structured Confluence requirements page referenced by a kickoff ticket, routed by the same `veldo-repo:<repo>` label, drafts a `veldo.plan/v1` (not just one spec) whose outcomes come from the page's Outcomes and with one work item per named Deliverable, bound to the resolved repo and the page linked as the source. It fails closed by name on a missing, unknown, or ambiguous routing signal, is a deterministic non-LLM transform, and sanitizes every front-matter value so a malicious page cannot inject plan front matter. The plan is `status: draft` a human refines and approves (the machine never approves its own plan); once approved, the live epic mirror (the `_create_or_update_epic` and `_create_or_update_child` writes in the reference `JiraCloudAdapter`) projects it onto a real Jira epic keyed to the plan and one child issue per work item, each found by a stable veldo marker so a re-run never forks a second epic or a duplicate child, and each child an approvable spec that flows through the loop above.

**What is turnkey and what is not.** The routing, eligibility, draft-and-promote logic, the reassignment and artifact links, the runner's reconcile core, and the doc-to-plan transform are mechanical and gate-tested offline against the in-memory fake tracker. The live Jira Cloud connection - the queries, the transitions, the comment and assign writes, and the epic/child creation - is the reference `JiraCloudAdapter` a repository wires to its own instance with a resolved `token_ref`; it needs a live instance and is not exercised by the home gate. The two unattended services (the inbound bridge and the `veldo mirror` runner) are opt-in and off until an operator turns them on against a real instance, an explicit human-approved step. As always, `.veldo/capabilities.yaml` (the `tracker_*` entries) is the machine-readable truth this section defers to.

## 13. The architecture organ: the shape as a contract

Veldo's per-change guarantees are local: the spec binds intent, the gate proves the change, a fresh context reviews it. A thousand locally proven changes still cannot vouch for the FOUNDATION they sit on. This organ closes that gap. It ships in the engine and is ADOPTION-SAFE by construction: a repository with no architecture contract is byte-identically unaffected (every check below stands down), and the moment a contract exists the mechanizable checks fail closed. The contract artifact itself is PER-REPO and is never shipped in the engine or copied into a pack; `/veldo:init` lays down the validators, not a contract. As everywhere, `.veldo/capabilities.yaml` (the `architecture_contract`, `spec_placement_footprint`, `shape_gate_enforcement`, `shape_fit_review`, `foundational_decision_record`, `adversarial_decision_review`, `decision_tripwires`, `entropy_metrics`, and `restoration_generation` entries) is the machine-readable truth this section defers to.

### 13.1 The architecture contract

The intended shape of the repository is a versioned, human-approved artifact at `.veldo/architecture.yaml` (schema `veldo.arch/v1`): its AREAS and their module boundaries, the allowed DEPENDENCIES between them, the PATTERNS in force, the INVARIANTS, and the size and complexity BUDGETS. Each rule is marked `mechanizable` (a gate check can refuse it) or `review` (a reviewer judges it). `.veldo/arch.py` validates it structurally the way a plan is validated (required fields, closed vocabularies, unknown rule kinds rejected at contract time, dependency edges resolving to declared areas), and the contract leaves draft only by a recorded human approval - changing the shape means changing the contract first, on the record, exactly the way specs are kept true. Validation runs in the gate through `validate.py all`; it fails closed on a malformed or referenced-but-absent contract and stands down when none exists.

### 13.2 The shape gate: mechanizable rules fail the build

`scripts/verify.sh` calls the shape gate (`.veldo/shape_gate.py`) after the contract validator. For every rule the contract marks `mechanizable`, it applies the enforcement that REFUSES a violation and fails the gate with the rule named, before any reviewer sees it; a rule marked `review` is surfaced as a NON-BLOCKING note, never a gate refusal (the honest reading of "mechanizable": the gate never carries a vacuous check). Be precise about what is gate-BLOCKING today, driven by this repository's own contract labels: the module-SIZE budget (a changed module over its line budget refuses by name) and the ENGINE INVARIANTS (byte-identical packs, derived-never-authoritative, adoption-safe fail-closed, each wired to its catalog check and refused if that check is ever deleted). Honestly REVIEW-LANE at this contract revision, shipped as stdlib reference implementations and surfaced as notes rather than refusals: the dependency and import boundaries, the function-length, duplication, and complexity budgets, and the prose patterns. The size rule is CHANGE-SCOPED (it binds the files the change touches, never a corpus re-sweep), so the shipped corpus is grandfathered and only new entropy is refused; an unknown mechanizable rule, or a mechanizable budget of a kind with no reference implementation, is itself refused (the anti-vacuity rule: you cannot mark a rule mechanizable and enforce nothing). The gate also enforces the declared FOOTPRINT against the diff when the change set names exactly one footprinted spec (a changed path the spec never declared refuses).

### 13.3 Placement and footprint at elaboration

No change is built placeless. A spec declares, in its front matter, a PLACEMENT (one or more contract area ids the change lives in) and a FOOTPRINT (the path globs it is allowed to touch). When a contract exists, a spec cannot REACH ready and is never CLAIMED for build unless its placement resolves to a declared area - the validator (`validate.py check_ready`), the claimable frontier, and `plan.py run-check` all read the one predicate in `.veldo/arch.py`, so they agree. A footprint that crosses an UNMODELED area boundary (a pair of touched areas with no allow-listed dependency edge between them) raises the required risk tier to at least high, and nothing lowers it; cohesive breadth across a pair the contract already connects does not elevate. This validates placement at the cheapest moment, before anything is built, and it is adoption-safe: no contract stands the gate down and the already-shipped corpus is never re-evaluated.

### 13.4 The shape-fit review dimension

The independent reviewer grades a SECOND dimension beyond spec-conformance: does this change FIT the declared shape. Correct-but-does-not-fit is a legitimate rework verdict that BLOCKS the merge like any blocking finding from day one. The dimension is honestly split. The MECHANICAL part (`.veldo/shape_review.py`) decides from the contract, the spec's placement and footprint, and the diff's paths the rules that need no judgment (a placement that does not resolve, a diff path outside the footprint, a diff path in a declared area outside the placement, a diff coupling two areas with no allow-listed edge) and fails closed. Whether a change follows the declared PATTERNS is a judgment no mechanical rule can settle, so `ShapeReviewer.review` is a fresh-context DELEGATED seam; the reference `LiveShapeReviewer` RAISES rather than fabricate a judgment. The merge gate reads the dimension through the verdict's `shape_fit` block (a `does_not_fit` or malformed block blocks; a verdict with no shape-fit dimension does not, adoption-safe). The machine never LOWERS the verdict: any mechanical misfit forces `does_not_fit` regardless of the judgment.

### 13.5 Foundational decisions: records, adversarial review, and tripwires

A foundational choice (technology, architecture style, communication shape, tooling) is the class of decision that passes every test while being wrong. It becomes a first-class recorded unit. `.veldo/decision.py` validates a `veldo.decision/v1` record (`.veldo/decisions/*.yaml`, per-repo): the machine elaborates the option space against the STATED PROBLEM CLASS (never today's scale), every option must carry its dead-end condition, and every assumption must carry a measurable signal and a breach condition. Only a HUMAN decides, on the record; there is no machine-decided state, and an irreversible choice maps to the critical risk tier. Before the human decides, `.veldo/decision_review.py` runs an ADVERSARIAL fresh-context review (`veldo.decision_review/v1`): what breaks first at ten times the problem class, which future requirement the choice precludes, what a mature system in this domain would choose, whether the tool is right or merely near. Scrutiny scales with reversal cost through the existing risk tiers (`decided_requires_review` reads `.veldo/policy.yaml` and requires the tier's number of bound valid reviews - two for critical, one for standard); the fresh-context reviewer is a fail-loud delegated seam. The recorded assumptions are LIVING TRIPWIRES: `.veldo/tripwire.py` compares each assumption's declared signal against a small in-session recorded-readings file (`.veldo/readings/*.yaml`) and surfaces an approaching or breached assumption as a named finding in the gate output, in `veldo status`, and at the weekly pass; a breach drafts exactly one re-decision unit a human promotes. It runs IN-SESSION ONLY - a pure function that reads recorded files and spawns nothing (no timer, no daemon, no detached process); a wrong foundation is caught by assumption breach, not by outage.

### 13.6 Entropy measured and reconciled

Decay gets a number and a response. `.veldo/entropy.py` derives a per-area COST-TO-CHANGE series from what the loop already records (per-correlation tokens, cost, human minutes, review cycles, gate failures) joined to contract areas through each spec's placement and the files a change touched, with the gate's static shape measures (duplication, complexity, boundary pressure) on the same map. The threshold is a RELATIVE degradation of an area against its own trailing baseline, ADVISORY during a calibration period before its crossings are trusted. `.veldo/restoration.py` consumes a trusted crossing and drafts a `veldo.restoration/v1` intent naming the area, the crossed rule, and the expected post-restoration measure; the draft is a DRAFT only a human promotes into a real spec that flows through the normal loop, idempotent by the (area, dimension) pair, and the loop closes by reporting the cost delta once the restoration ships. NOTHING auto-gates on a number and NOTHING auto-promotes a draft: neither module is wired into `verify.sh` or `validate.py run_all` - they are surfaced through the entropy CLI and the metrics dashboard and run in-session only.

### 13.7 What ships, what is per-repo, and what is pending

Shipped in the engine and laid by a pack: all the organ's validators and derivations, the shape hook in `verify.sh`, and the reference analyzers. Laid by `/veldo:init`: the six gate-wired and validate-wired validators (`arch.py`, `decision.py`, `decision_review.py`, `shape_review.py`, `shape_gate.py`, `tripwire.py`); the two advisory CLI-only derivations (`entropy.py`, `restoration.py`) ship in the full pack engine but are not part of the minimal init substrate, by design (they never gate). PER-REPO, never shipped: the `architecture.yaml` contract, the decision records, the readings, the re-decision and restoration drafts - a fresh init repository has none of these, so the whole organ stands down until a team authors its own contract. PENDING and honestly not turnkey: the mechanical halves are gate-tested, but the two delegated reviewers (`LiveShapeReviewer` for shape-fit and `LiveAdversarialReviewer` for decisions) are fail-loud reference SEAMS - wiring a real fresh-context reviewer's prompt to them is a per-repo step after release, the same honesty shape as the executor and dispatch reviewer seams. Everything mechanizable that a rule marks `review` (dependency boundaries, function-length, duplication, complexity, prose patterns) is a reviewer note, not a gate refusal, at this contract revision.

## 14. Security by design: floors that hold, and one lane of judgment

An agent writes the most common shape of a thing, and the most common shape of an IAM policy in the training data is `Action: *`. That is not a reasoning failure and a better instruction does not fix it - the next task starts with a fresh context and the same training data. So this organ is a set of mechanical FLOORS plus one graded REVIEW DIMENSION above them. It ships in the engine and is ADOPTION-SAFE by construction: no check here blocks a verdict that does not declare the dimension, the inventory is advisory until a repository declares otherwise, and nothing holds a credential or opens a connection on install. As everywhere, `.veldo/capabilities.yaml` (the `secret_reference_seam`, `absolute_secret_scan`, `context_secret_free`, `per_task_credentials`, `untrusted_input_isolation`, `supply_chain_policy`, `generated_privilege_floor`, `signed_attributable_commits`, `security_review_dimension`, and `secret_inventory_migration` entries) is the machine-readable truth this section defers to.

### 14.1 Secrets: named in the repository, absent from the context

`.veldo/secretref.py` is the seam: the repository holds a REFERENCE, the value resolves at use, and `SecretHandle` renders the reference in both `__repr__` and `__str__` because the commonest way a credential reaches a log is an object being printed. An absent secret is distinguishable from an empty one, so a misconfiguration cannot masquerade as a blank. `.veldo/secret_scan.py` refuses anything credential-shaped in a diff, a generated file or an artifact through pattern PLUS entropy detection, and it ships NO ALLOWLIST MECHANISM - not an empty allowlist, no mechanism, because an allowlist is how a scanner dies one convenient exception at a time. `.veldo/context_redaction.py` removes secrets at the seam where data becomes agent context rather than filtering a transcript afterwards: once a value is in a context it is in the transcript, in whatever the model quotes back, in the summary and in the compaction, and there is no recall. It fails closed - a chunk it cannot make safe is refused entirely rather than returned looking scrubbed.

### 14.2 Credentials, input trust, and the dependency edge

`.veldo/credential_issue.py` issues a credential FOR one task, scoped to what that task DECLARED. Scope is derived, never requested: an agent that hits a permission error, widens its request and succeeds is how least privilege dies, and nobody involved was careless. Expiry is re-checked at USE, not only at issue, because a credential validated only when handed out works forever in practice. `.veldo/untrusted_input.py` fences external text across seven declared seams so it arrives as DATA with its provenance; the fence nonce is derived from the content, so a payload cannot contain its own terminator, and marker-like content is REFUSED rather than escaped. The module states plainly that labelling does not make a model impossible to fool and that the real defence is downstream - a labelling layer presenting itself as the protection would be worse than none. `.veldo/supply_chain.py` makes a new dependency a visible decision: a `DEC-` record where PLAN-0011 has shipped, a written reason where it has not, never nothing. A version BUMP is deliberately not flagged, because a check that fires on ordinary work gets deleted.

### 14.3 Generated infrastructure and attributable commits

`.veldo/generated_privilege.py` refuses seven named classes in infrastructure the machine writes - wildcard action, resource and principal, over-broad role, public ingress, public storage, and a credential with no expiry - each carrying the NARROWER THING TO DO, because a refusal that says only "least privilege violation" is one somebody adds an exception for. It reads PARSED STRUCTURE, never text: a regex over HCL matches a wildcard in a comment and misses one built by concatenation, which is exactly what a generator emits. `BROAD_ROLES` and `OPEN_CIDRS` are named data so widening is a decision, and `Analyzer` is the per-stack slot a real Terraform or Kubernetes analyser plugs into. `.veldo/commit_attribution.py` holds signing and attribution as policy over parsed commit records: the trailer says WHO and the signature is what makes the who TRUE. Its load-bearing property is that git's good-signature verdict is not a trust decision - git reports G for any key the LOCAL KEYRING holds, and the keyring is a file in the environment the agent runs in, so the fingerprint is pinned against a `Registry` declared in the repository. Unsigned, unattributed, and actor-does-not-own-the-key are three DIFFERENT refusals. Enforcement is configurable and on from first release, and the checks run either way, because a check switched off entirely goes stale.

### 14.4 The security review dimension

`.veldo/security_review.py` grades security ABOVE the mechanizable floor, exactly as the shape-fit lane grades architecture, and correct-but-INSECURE is a legitimate rework verdict the real `Dispatcher._verdict_passes` refuses on. The dimension is designed against a specific failure: a reviewer handed a green wall of automated checks grades the rest by vibes, so `security_review_context` states that the floors are ALREADY ENFORCED, instructs the reviewer not to re-grade them, and names the four dimensions above them (secrets handling, input trust, privilege footprint, dependency delta). THE MACHINE NEVER LOWERS - a mechanical finding forces insecure whatever the reviewer concluded, and the reviewer may overrule upward only. The floors are RE-RUN at review and PASSED IN, since a build's own report of itself is the artifact an insecure change has every reason to be wrong about. `LiveSecurityReviewer` RAISES: nothing fabricates a judgment, because in the record a fabricated one is indistinguishable from a real one. Both lanes now implement ONE dimension interface (`validate_dimension` / `dimension_blocks`) enumerated once in `validate_checks.REVIEW_DIMENSIONS`, so a third review dimension edits neither `validate.py` nor the merge gate.

### 14.5 The honest migration

`.veldo/secret_inventory.py` with the `scripts/secret_inventory.py` runner inventories the working tree AND ALL REACHABLE HISTORY, because a credential committed and then deleted is still in every clone, every fork and whatever CI cached the checkout. Findings are BY REFERENCE - path, line, detector, and a digest of the LINE - and the scanner returns no matched text, so there is nothing to leak even by accident. A DISPOSITION COVERS ONE EXACT LINE BY DIGEST, never a path and never a pattern: a path allowlist exempts a location forever and is precisely what 14.1 refuses to ship, whereas mutating a dispositioned line makes the disposition stop matching, so a real credential cannot inherit a fixture's exemption. A malformed disposition dispositions NOTHING. Which detector gates is a MEASURED call: over this repository's tree plus 3,252 reachable blobs the detectors produced roughly nine hundred pattern hits (twenty-two distinct lines, every one a conformance fixture, zero real credentials) against 17,849 entropy hits, so pattern GATES and entropy REPORTS - a gate nobody can triage is a gate that gets switched off. The flip to enforcing is DECLARED AND DATED, never inferred from a scan returning zero, and enforcing does not downgrade without a written reason.

### 14.6 What ships, what is per-repo, and what is pending

Shipped in the engine and laid by a pack: all ten modules and the inventory runner. PER-REPO, never shipped: the signer registry, the secret resolver's real backing store, the inventory record and its dispositions, and any per-stack privilege analyser. PENDING and honestly not turnkey: the secret RESOLVER (the seam resolves nothing until pointed at a vault, an environment loader or a cloud secret manager), the credential ISSUER (the shipped one is a fake that mints nothing), and the security REVIEWER (a fail-loud seam, the same honesty shape as the executor, dispatch and shape-fit reviewer seams - wire a genuinely fresh context or leave the dimension off, but do not wire something that returns `secure`). Also pending and requiring a human: wiring the inventory check into `scripts/verify.sh` and placing the inventory record under `protected_paths`, both of which touch protected files and so are approvals rather than agent work.

## Document History

Minor versions add, clarify, or extend; major versions restructure or break compatibility (the 1.1 skill renames should have been judged by this stricter wording; recorded here so the mistake is visible).

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial plugin and guide |
| 1.1 | 2026-07-16 | Skill names shortened: /veldo:spec instead of /veldo:veldo-spec (all six) |
| 1.2 | 2026-07-16 | Revalidation fixes: guard rules stated honestly (two checks, two release valves), emergency lane implemented, evidence-commit rule documented, init as the first Veldo change, idempotent CLAUDE.md marker, marketplace note, manual-path naming |
| 1.3 | 2026-07-16 | /veldo:run and /veldo:status added (plugin 1.3.0); section 8, Veldo by example: nine worked examples and failure drills |
| 2.0 | 2026-07-16 | Conformance audit applied: fail-closed gate (undeclared items are red, waivers expire), verdicts + protected-path approvals + emergency debt enforced mechanically at the push boundary, evidence and criteria coverage validation, the capability manifest as generated truth, honesty rewrites labeling target behavior |
| 2.1 | 2026-07-16 | Server-side gate wiring (W10): section 4.1 and the shipped CI workflow template (`.github/workflows/veldo-gate.yml`) that runs the same gate (verify + policy_check) as a required check, with the branch-protection recipe and how it mirrors the local guard; contents reference and capability manifest updated |
| 2.2 | 2026-07-17 | Runner catalog and gate-slot wiring (B9 of PLAN-0003): section 10 catalogs every reference runner in the suite with its surface, home, honest status (deferring to the capability manifest), fixture pair, and adopting-repo gate slot; the catalog completeness check (`scripts/check_runner_catalog.py`, BJ1) and the home-gate-runs-no-surface property (BJ2) are documented and asserted mechanically in the unit slot |
| 2.3 | 2026-07-19 | The fleet made true in the guide (W6 of PLAN-0009): section 11 documents the fleet as it ships in the engine, the two-tier adoption model (a pack lays the full engine including the fleet; `/veldo:init` lays the minimal governance substrate by design), the `veldo` CLI entry points (`veldo work`, `veldo fleet N`, `veldo account`, `veldo status`/`veldo watch`), the per-account model and token governor, and the in-session, no-detached-process boundary; deferring to the capability manifest for honest status |
| 2.4 | 2026-07-20 | Tracker integration made true (VELDO-0610 of PLAN-0006): new section 12 documents the one-way, event-driven Jira and Confluence bridge as it ships - the mirror (spec status and comments, plan epic and child structure) and intake (a ticket or a requirements page becomes a routing-resolved spec draft), how to turn it on (the `.veldo/trackers.json` routing and status_map, the optional `tracker_repo` field, `token_ref` auth, the Confluence requirements template), the mechanical-versus-reference split (vendor-neutral logic gate-tested against a fake tracker; the live Jira Cloud and Confluence Cloud adapters wired per repo), the not-yet-live edge (epic/child creation against live Jira), and the one-way, repository-wins, untrusted-input principles; deferring to the capability manifest for honest status |
| 2.5 | 2026-07-20 | Section 12 links its operator companion (VELDO-0611 of PLAN-0006): the new `docs/tracker-operator-guide.md`, which walks a human through the tracker workflow day to day (flag a ticket or requirements page, run intake, and the mirror round-trip that writes progress back). This section stays the capability reference; the guide is the workflow companion |
| 2.6 | 2026-07-21 | The tracker-driven autonomous fleet made true (VELDO-1008 of PLAN-0010, plugin 3.6.0): new section 12.5 documents the loop as it ships in the engine - the single shared Agent user and the fail-closed eligibility triple (`is_eligible`), the non-LLM inbound bridge that auto-drafts a spec and posts it on the ticket and the human validation gate that promotes only on the ready-for-dev-plus-Agent action (`reconcile_drafts`/`reconcile_promotions`), the `assign` seam write and the ready-to-test round-trip that posts artifact links and reassigns the ticket to the reviewer, the opt-in off-by-default `veldo mirror` live runner, and the requirements-page-to-plan generator feeding live epic and child creation; the live Jira edge stays reference wired per repo and the two services stay opt-in, deferring to the capability manifest for honest status |
| 2.7 | 2026-07-22 | The architecture organ made true (VELDO-1110 of PLAN-0011, plugin 3.7.0): new section 13 documents the shape organ as it ships in the engine - the per-repo architecture contract (`.veldo/architecture.yaml`, `arch.py`), the shape gate wired into `verify.sh` (honest about the module-size budget and engine invariants being gate-blocking while dependency boundaries, function-length, duplication, complexity, and prose patterns are review-lane reference implementations), placement and footprint at elaboration, the shape-fit review dimension, foundational decision records with adversarial fresh-context review and in-session assumption tripwires, and the entropy-to-restoration loop; honest that the contract is per-repo and never shipped, that `/veldo:init` lays the six validators and the two advisory derivations ship only in the full pack engine, that every pass is in-session with nothing detached, and that the delegated shape-fit and adversarial-decision reviewer seams are fail-loud references whose live prompt wiring is per-repo and pending; deferring to the capability manifest for honest status |
| 2.8 | 2026-08-03 | Security by design made true (VELDO-1311 of PLAN-0013, plugin 3.10.0): new section 14 documents the organ as it ships in the engine - the secret reference seam and the no-allowlist absolute scan, redaction at the seam where data becomes context, task-derived credential scope with expiry re-checked at use, seven-seam untrusted-input fencing with a content-derived nonce, supply-chain policy that flags a new relationship but never a version bump, the seven-class generated-privilege floor reading parsed structure rather than text, signing and attribution pinned against a repository-declared registry because git's good-signature verdict is not a trust decision, the security review dimension the merge gate refuses on with the machine never lowering, and the honest migration over reachable history with per-digest dispositions and a declared, dated flip; honest that the resolver, the issuer and the reviewer are per-repo wiring, that the inventory's gate hook and protected-path placement are human approvals, and deferring to the capability manifest for status |
