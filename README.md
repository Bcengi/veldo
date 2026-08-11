# Veldo

**Veldo is Verification-Enforced Lifecycle Delivery Orchestration: an AI-native software development method.**

> Software development at full speed, enabled by AI and governed by proof.

Veldo is built for one fact: with AI coding agents, generating code is nearly free, so the bottleneck moved from writing code to verifying it. Veldo is how a small team turns intent into shipped, proven software dramatically faster, without adding process or people. It does not optimize the traditional software development lifecycle. It replaces it.

This README is the complete front door: what Veldo is, why it exists, how the loop works in practice, what the plugin ships, and how to adopt it. The deep documents in [`docs/`](docs/) carry the full detail.

## Why Veldo exists

For decades the scarce resource was engineers writing code, and the whole lifecycle (tickets, estimates, sprints, standups, release trains) was built to schedule and coordinate that scarce resource. AI coding agents remove the scarcity. Generating a correct-looking change is now cheap and fast. What is NOT cheap is knowing the change is right: that it meets the intent, breaks nothing, and is safe to ship. So Veldo moves the whole investment to the thing that is now the bottleneck. It spends less effort producing code and far more effort proving it, and it makes the proof machine-checkable so the proving itself runs at speed.

## The one rule

> State the intent, let the machine build, require proof, and merge immediately when green.

Every change follows the same path:

```
Intent -> Specification -> Implementation -> Proof -> Independent Review -> Merge
```

The unit of delivery is not code alone. It is **specification + implementation + evidence**. Code without evidence is incomplete.

## Principles

1. The repository is the operating system. State an agent cannot read, diff, or invoke is not reliable operational knowledge.
2. The specification is the unit of work, not the ticket. The spec is the contract between human intent and machine execution.
3. Humans own intent and judgment. Machines own construction and proof.
4. Verification is the bottleneck. Invest more in the proof system than in raw code generation.
5. Every change carries evidence, proportional to its risk.
6. Independent review requires fresh context, ideally a different model. The writer does not approve its own work.
7. Green means merge. Human sign-off is a risk control reserved for the irreversible (money, auth, schema, core infrastructure), not a ritual.
8. Changes flow continuously into one trunk. No sprints, points, standups, or release trains.
9. Work stays small and reversible.

## How the loop works in practice

Veldo lives in the repository. A change moves through concrete artifacts a team can read, diff, and invoke:

- **Specification** (`specs/VELDO-####-*.md`). A human states intent as a spec: the acceptance criteria, the risk class, what evidence is required, and which paths are protected. The spec is the contract. An agent does not start building until the spec is clear.
- **Implementation.** An agent builds to the spec. Mechanical control logic is written so it can be proven by construction; the risky work is delegated behind seams and exercised by tests.
- **The gate** (`scripts/verify.sh`). One canonical command every change must pass: the spec/proof contract checks, the self-test, generated-file and template checks, the secret scan, the docs hygiene sweeps, and the repo's own runners. The gate is fail-closed: an undeclared or blank check makes it red.
- **Proof** (`proof/VELDO-####/`). A manifest records how each acceptance criterion was met and which checks ran, digest-bound to the implementation commit so the evidence cannot drift from the code.
- **Independent review.** A fresh-context reviewer (ideally a different model, never the writer) tries to prove the change wrong and records a verdict bound to the commit. Green plus a passing verdict is what lets a change merge.
- **The policy guard** (`.veldo/policy_check.py`, enforced pre-push). A recorded, unresolved blocking finding stops the push, and a change touching a protected path needs a separate human approval whose approver is not the proof producer. It deliberately does NOT require a passing verdict: a verdict is an artifact the agent can write, so requiring one asked the agent to certify itself. The authority moved instead of being defended. For ordinary work a green gate is what says done, because that is the thing an agent cannot forge into existence; for protected paths the owner says it. Reviews still run and still report findings, they just no longer certify.
- **Evidence commit.** The proof and verdict land with the change; a spec is not done until its evidence is on the trunk and its status is shipped.

The board is the repository. **`specs/index.md`** is a single diffable file, generated from the specs, that serves as plan, backlog, and status. It is a navigation layer, not a second source of truth: if the index and any external tracker disagree, the repository wins. Do not recreate Jira in Markdown.

For work larger than a single spec, a **Product Plan** (`plans/PLAN-####-*.md`) declares a set of specs as a dependency graph with a release gate; progress is derived from the specs' statuses, never tracked by hand.

## What the plugin ships

The capability manifest, [`engine/.veldo/capabilities.yaml`](engine/.veldo/capabilities.yaml), is the machine-readable truth about what is enforced by code, what is a wired reference, and what is agent-instructed procedure. Documentation defers to it. The surface today:

- **The gate and policy plane.** The canonical fail-closed gate, the spec/proof/plan contract validation, the verdict-at-push and protected-path-approval guard, and the emergency lane with its recorded-debt blocking.
- **Runners.** Real journey drivers a repo points at its own app: a web runner (Playwright, with an accessibility scan and named UI states), mobile drivers for Android (adb) and iOS (xcrun simctl, macOS-gated), and design runners (a token lint and a baseline pixel comparator).
- **Ephemeral environments.** A provisioner seam with the four guarantees a runner leans on (clean on create, seeded and observable, teardown idempotent and leaves nothing, a leak is a named failure).
- **The Run Lens.** See and steer a running build: a per-run registry outside git history, an optional executor observer, a read-only status reader and a local status server, and a cooperative answer/steer/abort inbox.
- **The Veldo Fleet.** Elastic parallel workers that ship in the engine: installing a pack lays the whole fleet along with the rest of the engine, and the `veldo` CLI drives it. `veldo fleet N` runs up to N in-session workers that pull ready work from anywhere in the repo, build it, and land it, self-dividing purely through a shared atomic claim ledger with no central coordinator and no detached process; `veldo work` runs a single worker per terminal. Work routes to the machine that can run it by capability (an iOS build to a Mac, a GPU job to a GPU box), a serialized lander merges each build to the trunk one at a time without collisions, a heavy shared dataset is mounted once and never duplicated, and a token-paced governor sizes the pool to the budget, per account, so the budget is used without running out.
- **Tracker integration (Jira and Confluence).** A one-way, event-driven bridge to an external tracker, in two directions, with the repository always the single source of truth. The MIRROR projects a spec's and a plan's lifecycle events onto the tracker: a spec's status plus a closing comment on its child issue, and a plan's work graph onto an epic and its child issues. It is one-directional and reconciled from the event stream, never polled, so the tracker never becomes a second definition of the work and the repository wins if the two disagree. INTAKE runs the other way: a Jira ticket or a structured Confluence requirements page becomes a routing-resolved Veldo spec draft, fed into the intake skill, with the source linked and its content treated as data, never as instructions. Routing is first-class because one tracker project commonly spans many repositories. The vendor-neutral routing, adapter seam, mirror (spec and epic), intake logic, and end-to-end conformance are enforced in code and gate-tested offline against an in-memory fake tracker; the live Jira Cloud and Confluence Cloud adapters, the mirror, the intake and the bridge are repo-only machinery that does NOT ship with a pack. What a pack lays down is the routing contract and its enforcement, so an adopter gets routing today, not the round trip. On top of that bridge, the tracker-driven autonomous fleet makes Jira the front of the work queue: a ticket assigned to a single shared Agent user, tagged to a resolvable repo, and moved to a ready-for-dev status (the eligibility triple, fail-closed on every leg) is drafted into a spec by a non-LLM inbound bridge that posts the draft back on the ticket; a human validates it by that same tracker action (the promote gate is a human act in Jira, never a machine self-promotion); a fleet worker builds it; and at the ready-to-test handoff the mirror posts the artifact links (commit always, the PR and proof when present) and reassigns Veldo's OWN child issue away from Agent to the configured reviewer, defaulting to the ticket's reporter. The ticket you filed is never transitioned, commented on, or reassigned. A structured requirements page drafts a whole Veldo plan when someone in the repository runs plan intake against it by page id, projected onto a Jira epic and its child issues; a kickoff ticket that merely points at a page triggers nothing. The accurate count is one command a person runs (`veldo mirror`) and one library nothing calls yet (the inbound bridge), both non-LLM and token-authed by reference, both repo-only, so there is nothing to turn on for the bridge until a runner exists; the live Jira edge stays a reference implementation wired per repo, its logic proven offline against the fake tracker. How to turn it on is in [`docs/plugin.md`](docs/plugin.md); the day-to-day operator workflow (flag a ticket, run intake, what happens to the ticket after) is in [`docs/tracker-operator-guide.md`](docs/tracker-operator-guide.md).

- **Architecture as a contract (the shape organ).** The intended shape of a repository becomes a versioned, human-approved artifact (`.veldo/architecture.yaml`): its areas and module boundaries, allowed dependencies, patterns, invariants, and budgets, each rule marked mechanizable or review-lane. Everything mechanizable about it that the gate can enforce today fails the build with the rule named before any reviewer sees it (the module-size budget and the engine invariants); the dependency and import boundaries, the function-length, duplication, and complexity budgets, and the prose patterns ship as stdlib reference implementations surfaced as review-lane notes at this contract revision, honestly labeled. Every spec declares its placement (which area it lives in) and footprint (what it touches) before it is built, so placement is validated at the cheapest moment; the independent review grades a second dimension where correct-but-does-not-fit is a real rework verdict. Foundational choices (technology, architecture style, communication shape, tooling) become first-class decision records, elaborated against the stated problem class and attacked by a fresh-context adversarial review before a human decides; each recorded assumption is a living tripwire the system checks in-session so a wrong foundation is caught by assumption breach, not by outage. Per-area cost-to-change is derived from what the loop already records and a threshold crossing drafts a restoration spec a human promotes through the normal loop. The whole organ is ADOPTION-SAFE: a repository with no contract is byte-identically unaffected (every check stands down), and the contract file itself is per-repo, never shipped in the engine. Every monitoring pass runs in-session; nothing detached. The delegated shape-fit and adversarial-decision reviewers are fail-loud reference seams whose live reviewer prompt wiring is per-repo. `.veldo/capabilities.yaml` is the machine-readable truth; the organ is documented in [`docs/plugin.md`](docs/plugin.md) section 13 and [`docs/setup.md`](docs/setup.md) section 7.8.

Current plugin version: 3.10.1 (the manifests are the source of truth: `.claude-plugin/marketplace.json` and each pack's own manifest).

## Install and adopt

Install the plugin:

```
/plugin marketplace add Bcengi/veldo
/plugin install veldo@veldo
```

Then, once per repository:

```
/veldo:init
```

It lays down the Veldo substrate (specs, policy, the canonical gate, templates) and configures it with you. Details: [`docs/plugin.md`](docs/plugin.md).

Your first change, end to end:

1. Write a spec for a small change with `/veldo:spec` (or copy `specs/TEMPLATE.md`): the acceptance criteria, the risk class, the required evidence.
2. Build it with `/veldo:run`, or by hand against the spec.
3. Run the gate: `./scripts/verify.sh`. Fix until green.
4. Get an independent review; record the verdict.
5. Commit the proof and verdict, and push. The guard refuses a push that is not proven.

Running at scale: once a repo is initialized and its runners and environment are declared, add workers for throughput with `veldo fleet N` (or run `veldo work` per terminal). One workspace-scoped terminal covers all the Veldo repos it can see; add terminals (or accounts) for more parallelism, and the governor paces them. Terminals are the unit of parallelism, not of project count.

Adoption is incremental. Start by putting the gate in front of one repository and requiring a spec and a green gate for one kind of change, then widen. The full path, including a two-week pilot, is in [`docs/setup.md`](docs/setup.md).

## Repository contents

- [`docs/method.md`](docs/method.md) - the full Veldo Development Method (core model, principles, the 10-stage lifecycle, risk classification and the emergency lane, repository structure, agent roles and human review lanes, agent operating instructions, definitions of proven and done, failure modes, adoption path, metrics, and the manifesto).
- [`docs/setup.md`](docs/setup.md) - Setting Up and Running Veldo: the operational companion. The durable contracts, the exact Claude Code setup, scaling from one person to thousands, the control plane with its build order, governance and economics, the edges (design, intake, documentation), and the two-week pilot.
- [`docs/plugin.md`](docs/plugin.md) - the Veldo Plugin Guide: install, init, the first change, the guard, the manual path.
- [`docs/runbook.md`](docs/runbook.md) - operational runbook.
- [`docs/tracker-operator-guide.md`](docs/tracker-operator-guide.md) - working with Veldo and your tracker: the human workflow for filing work from Jira or Confluence (intake) and what happens to the ticket after (the one-way mirror round-trip). The operator companion to the Plugin Guide section 12.
- [`docs/change-management.md`](docs/change-management.md) - how Veldo itself is changed.
- [`docs/public-distribution.md`](docs/public-distribution.md) - what is in the public repository and what is not: what a pack gives an adopter, what did not travel out of the private repository it was built in, and why.
- [`packs/claude/`](packs/claude/) - the Veldo plugin itself (agents, skills, guard hook, the capability manifest, and the repository templates that `/veldo:init` lays down). This repository is also the plugin marketplace.
- [`packs/`](packs/) - the seven self-contained multi-tool packs (Claude Code, Cursor, Codex CLI, GitHub Copilot, Antigravity CLI, OpenCode, Aider), each a complete drop-in assembled byte-identical from the one canonical engine, with identical enforcement on every tool. See [`packs/README.md`](packs/README.md).
- [`engine/`](engine/) - the one canonical base every pack extends: the gate, the guard, the validators, the `.veldo` substrate, the runners and the CI workflow.

## What is not here, and why

Veldo is built with Veldo, so the method has been run on itself from the first change, and this repository is open sourced out of the private one that work happened in. Two things did not travel. Our own paperwork: the specifications, plans and proof corpus name unreleased products, a supplier and colleagues, so they stay internal, and the publication is derived by default-deny globs rather than curated by hand. And machinery that only makes sense in the repository that develops Veldo: 31 entries in the capability manifest carry `scope: repo-only`, most of them the live tracker round trip and the harness that builds our seven packs, marked in the manifest rather than described in prose. Nothing that enforces anything was held back. The gate, the specs, the proof bundles, the independent review, the plan layer and the fleet all ship and all run in a fresh repository: an init from a composed pack lays 49 files and that repository's own gate is green. Full detail, in that order, in [`docs/public-distribution.md`](docs/public-distribution.md).

The Markdown in `docs/` is the source of truth. Each document versions itself (version line under the title, Document History at the end). Method authored 2026-07-16. Supporting research and design produced from a 20-agent research and design pass.
