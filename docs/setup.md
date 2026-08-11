# Setting Up and Running Veldo

*The operational companion to the Veldo Development Method. The method defines what Veldo is and why it works. This document defines how you stand it up and keep it running, from one person to an organization of thousands.*

*Version 2.13, 2026-08-03*

## 1. How to read this document

The [Veldo Development Method](method.md) is fixed: intent becomes a specification, an agent implements it, a gate proves it, an independent agent reviews it, policy decides it, and it merges to trunk on green. This document is the build and operations guide for that method.

There are three layers to stand up, and the document covers them in order:

- **The repository substrate** (sections 2 and 3) - the contracts and files every repository must contain to be Veldo-operable.
- **The agent setup** (section 4) - how Claude Code is configured so agents can actually run the method.
- **The control plane** (sections 5 through 7) - the stages of growth and the software you build over time to run Veldo durably at scale.
- **The edges** (section 8) - how design tools, bug reports, and human documentation plug into the loop.

Three stances govern everything that follows. They are the reason the document is organized the way it is.

**Stance 1: the architecture is identical at every scale.** One person and an organization of ten thousand run the same pipeline against the same contracts. What differs is only how each capability is implemented: a file, a script, a CI job, or a hardened service. A file is an implementation. A service is an implementation. The contract is the design. You never redesign Veldo as you grow; you re-implement individual capabilities behind interfaces that were fixed on day one.

**Stance 2: the contracts are the durable assets.** Tools churn. Models improve and are retired. Vendors come and go. CI systems get replaced. What must survive all of that is the set of contracts: the shape of a specification, of a proof, of a review verdict, of the risk and merge policy, of the lifecycle event stream, of the index, and of a human approval. Define these first, before selecting any tooling. Everything else is a swappable implementation of a stable contract. You are allowed to implement cheaply. You are never allowed to design cheaply.

**Stance 3: rules are mechanical or they are fiction.** Every rule in this document terminates in something a machine enforces: a schema validation, a blocking hook, a required check, or a policy evaluation. Prose guides humans. Enforcement governs agents. A rule an agent can talk its way around is a suggestion, and under AI-native throughput, suggestions do not survive contact with volume.

One invariant ties the three stances together, and it is testable:

> **The drop-in test.** At any scale, you must be able to delete the entire control plane and lose nothing but speed. Repositories, immutable proof records, the approval ledger, and the retained event stream must be sufficient to rebuild every index, dashboard, and service state. If deleting a component would lose truth, that component has silently become a source of truth, and that is a defect. Test this deliberately: rebuild your derived state from the primary records on a schedule.

And one counterweight with equal force:

> **The proportionality rule.** Veldo exists to make delivery fast. A control earns its place only by speeding the path to a proven merge or by preventing an unrecoverable mistake; everything else is weight, and weight is a defect. Between two correct designs, take the lighter one, and add the heavier one only when an observed need arrives. Controls built for regulated industries (cryptographic signing, hash-chained ledgers, legal hold, multi-region evidence replication) do not belong in a software delivery process unless you actually operate in such a domain. A process heavier than the work it governs has failed at its own job.

## 2. The invariant architecture

### 2.1 The pipeline

Every change, at every scale, moves through the same pipeline:

```
Intent -> Specification -> Implementation -> Proof -> Independent Review -> Policy Decision -> Merge -> Observe -> Close
```

The unit of delivery is never code alone. It is specification plus implementation plus evidence, bound to one exact commit.

### 2.2 The five planes

The pipeline runs across five architectural planes. Naming them matters because every responsibility inside every component belongs to exactly one, and confusion between planes is where architectures rot.

| Plane | Holds | Rule |
|---|---|---|
| State | Repositories: code, specs, policy, instructions, index | Authoritative for what the system is |
| Execution | Implementing agents, gate runners, CI | Produces changes and evidence, owns nothing |
| Decision | Independent review, policy evaluation, human approval | Judges evidence, never edits it |
| Record | Proof store, verdicts, approval ledger, audit | Authoritative for what happened; immutable, append-only |
| Transport | Lifecycle events on a bus or log | At-least-once delivery, idempotent consumers |

### 2.3 The seven contracts

Seven contracts sit under the pipeline; their identity and purpose never change, while their schemas version calmly (section 3.8):

1. **Specification** - the unit of work: intent, acceptance criteria, constraints, risk.
2. **Proof manifest** - the machine-readable evidence that a change satisfies its specification.
3. **Review verdict** - the independent reviewer's structured judgment.
4. **Risk and merge policy** - what gate strength, review strength, and approval each change requires.
5. **Lifecycle event** - the append-only stream of what happened; the source of every metric.
6. **Repository index** - the derived, diffable navigation layer over specifications.
7. **Human approval record** - the durable, digest-bound record of accountable human judgment on protected changes.

The first six are the everyday spine. The seventh exists the moment a change touches a protected path.

One more contract sits above the pipeline rather than under it: the **Product Plan** (section 3.9). The seven govern a single change; the plan governs an iteration of many changes. It is optional in exactly the way the planned lane is optional (method section 2.11): a bug never needs one, a product increment always does.

### 2.4 Capability by scale

The same architecture, implemented differently as you grow:

| Capability | Solo (1) | Small team (2-10) | Scaling (10-100) | Org (100s-1000s) |
|---|---|---|---|---|
| Spec storage | Files in `specs/` | Files + PR review | Spec registry service | Registry, multi-tenant |
| Index | Generator script | CI-generated per repo | Cross-repo roll-up | Portfolio view |
| Gate | `scripts/verify.sh` | Required CI check | Gate runner service | Runner fleet, risk-aware selection |
| Proof | Manifest files in repo | CI artifacts + digests | Content-addressed store | Store with retention by risk class |
| Review | Reviewer subagent | Headless reviewer in CI | Review orchestrator | Model-diverse review fleet |
| Merge policy | Branch rule + policy file | Branch protection + CODEOWNERS | Policy engine | Policy-as-code governance |
| Approvals | Committed record in repo | Recorded approvals, digest-bound | Approval + audit ledger | Ledger behind SSO, compliance export |
| Events / metrics | Appended JSONL | Events to a warehouse table | Real bus + pipeline | Streaming analytics, SLOs |
| Agent runtime | Claude Code locally | Shared plugin + CI agents | Managed runtime, budgets | Fleet with cost governance |
| Parallel workers (the fleet) | One worker: `veldo work` | `veldo fleet N` in a terminal | Fleet across accounts, capability-routed | Fleet across a workspace of repositories, per-account budgets |
| Fleet accounts and governor | Single login | A few named accounts | Per-account token governor pacing | Per-account budgets and cost allocation |
| Work CLI and run lens | `veldo` CLI, `veldo status` | Shared via the pack | `veldo watch` over many runs | Same contracts and CLI, org-wide |
| Knowledge | CLAUDE.md + repo docs | Shared conventions | Knowledge index service | Federated, access-controlled |
| Observability / rollback | Manual + a tested script | Deploy health checks | Post-merge gates | Auto-rollback with safeguards |
| Identity / secrets | Git host identity, CI OIDC | Scoped tokens | Workload identity, RBAC | SSO, JIT access, rotation |

Read a column top to bottom and you have a complete setup for that scale. Read a row left to right and you see one capability hardening over time while its contract never moves.

## 3. The contracts (define these first)

Do this before writing any script or standing up any service. These are small schemas, and they are the most valuable artifacts you will produce, because everything else plugs into them and nothing is allowed to break them.

Four properties are common to every contract object, from day one, even solo:

1. **Versioned.** Every object names its schema and version (`veldo.spec/v1`). Changes are additive within a major version; a consumer must reject a major version it cannot interpret. No silent coercion.
2. **Content-addressed.** Every finalized object carries a digest, computed over its canonical serialization with the digest field itself excluded, and references between objects are by digest, not by filename. An approval that points at "the proof" is meaningless; an approval that points at `sha256:5f73...` is evidence.
3. **Attributable.** Every produced object records exactly what produced it: the model identifier, the runtime and version, and the digest of the instructions it ran under.
4. **Immutable once produced.** Proofs, verdicts, approvals, and events are never edited. Corrections are new objects that reference the old ones.

And one operational principle: **contracts are files before they are APIs.** At solo scale, every one of these objects is a file in the repository or an artifact the repository references by digest. Services built later ingest the same objects over new transports. That is precisely why a script and a service are drop-in compatible: both read and write the same shapes.

### 3.1 Specification

A Markdown file with structured front matter. The front matter is machine-read; the body carries context for humans and implementing agents.

```yaml
# specs/VELDO-0142-payment-retry-idempotency.md
schema: veldo.spec/v1
id: VELDO-0142
title: Payment retry idempotency
status: ready            # draft | ready | in_progress | review | proven | shipped | blocked
risk: high               # declared floor; policy may raise it, nothing may lower it
owner: <the human accountable for the intent>
human_approval: required # required | not_required
protected_paths:
  - billing/
acceptance_criteria:
  - id: AC1
    text: Retrying a failed payment with the same idempotency key never creates a second order.
  - id: AC2
    text: A duplicate submission returns the original order id in the standard response shape.
required_evidence: [unit, integration, staging_run]
out_of_scope: retry UI copy and cadence
rollback: disable the payment_retry_v2 flag
reversible: true         # policy input; irreversible work routes through prepare-and-execute
```

A specification is complete only when success can be evaluated: every acceptance criterion must be phrased so that a test or check can decide it. Structural validation is mechanical (fields, statuses, criteria ids, evidence coverage); judging criteria as subjective, contradictory, untestable, or oversized is the specification agent's job in the dialogue - judgment, not enforcement, and the documents say so rather than implying a machine does it.

Editing a `ready` specification is a revision: it produces a new version of the spec, and any proof or approval bound to the old one is invalidated with it. Intent is allowed to change; it is not allowed to change silently underneath evidence.

Standing specifications (method section 2.2) live beside ordinary ones: one file per recurring change class (dependency updates, copy corrections, configuration rotations) holding the criteria, risk, and evidence that every instance of the class runs against.

### 3.2 Proof manifest

The machine-readable claim that a change satisfies its specification. Produced by the implementing agent, consumed by review and by the merge policy. Immutable.

```json
{
  "schema": "veldo.proof/v1",
  "spec_id": "VELDO-0142",
  "commit": "7f43e6159aa6",
  "produced_at": "2026-07-16T14:12:03Z",
  "producer": {
    "role": "implementation",
    "model": "<exact model identifier>",
    "runtime": "claude-code <version>",
    "instructions_digest": "sha256:52ba..."
  },
  "environment": {
    "runner_image": "sha256:98c3...",
    "lockfile_digest": "sha256:21df..."
  },
  "criteria": [
    {
      "id": "AC1",
      "status": "passed",
      "evidence": [
        {
          "type": "test",
          "ref": "tests/payments/retry_test.py::test_no_duplicate_order",
          "artifact": "proof/VELDO-0142/junit.xml",
          "digest": "sha256:7f02..."
        }
      ]
    },
    {
      "id": "AC2",
      "status": "passed",
      "evidence": [
        {
          "type": "test",
          "ref": "tests/payments/retry_test.py::test_returns_original_id",
          "artifact": "proof/VELDO-0142/junit.xml",
          "digest": "sha256:7f02..."
        }
      ]
    }
  ],
  "checks": [
    {"name": "verify", "command": "./scripts/verify.sh", "result": "pass",
     "log": "proof/VELDO-0142/verify.log", "log_digest": "sha256:81e1..."}
  ],
  "rollback": "revert the merge commit; payment_retry_v2 flag off",
  "digest": "sha256:5f73..."
}
```

Three rules make a proof a proof rather than a summary. First, evidence binds to criteria: every acceptance criterion maps to specific, digest-addressed evidence, and a criterion without evidence fails the manifest. Second, the manifest binds to the exact commit and final diff; evidence produced against an earlier state of the change is not evidence. Third, evidence is proportional to risk: a copy change may carry a build result and a screenshot; an authentication change carries unit, integration, security, and regression evidence plus human review.

Two conventions close the loop mechanically. First, evidence lands as an evidence-only commit, touching only `proof/`, `.veldo/`, and `specs/`; such a commit inherits its parent's proof, because the subject of proof is the implementation commit and evidence needs no evidence about itself. Guards recognize the pattern. Second, where specification drift matters, the manifest also records the specification's digest, so revising a ready specification mechanically invalidates proof bound to the old revision.

Small proof reports live in the repository under `proof/<spec-id>/`. Large artifacts (logs, recordings, coverage data) live in an immutable object store, and the manifest carries their digests. Expiring CI artifacts are a transport, never the durable evidence store.

### 3.3 Review verdict

The independent reviewer's structured output. Produced in a fresh context, ideally by a different model. Immutable, and bound to the exact commit and proof it judged.

```json
{
  "schema": "veldo.verdict/v1",
  "spec_id": "VELDO-0142",
  "commit": "7f43e6159aa6",
  "proof_digest": "sha256:5f73...",
  "reviewer": {
    "model": "<exact model identifier, different from the producer>",
    "context": "fresh",
    "independence": "L2",
    "instructions_digest": "sha256:d694..."
  },
  "verdict": "pass",   // pass | pass_with_notes | fail | escalate
  "criteria": [
    {"id": "AC1", "assessment": "satisfied"},
    {"id": "AC2", "assessment": "satisfied"}
  ],
  "findings": {
    "blocking": [],
    "non_blocking": ["Add a retry-rate metric in a follow-up specification."]
  },
  "test_assessment": "Both new tests fail before the change and pass after it; they exercise the public API, not internals.",
  "produced_at": "2026-07-16T14:31:40Z",
  "digest": "sha256:91e0..."
}
```

A human review lane (section 8.1) uses the same shape, with the reviewer field carrying the person's identity and role instead of a model id. A verdict is invalidated by any change to the commit it reviewed. A failed review returns the change to implementation, and the revised change gets a new proof and a new fresh-context review.

### 3.4 Risk and merge policy

Policy is code: versioned, reviewed, machine-evaluated. It lives in the repository (with organization-level baselines later), and its evaluation must be deterministic for identical inputs.

```yaml
schema: veldo.policy/v1
version: 3
risk_tiers:
  low:      {gate: standard, reviews: 1, min_independence: L1, human_approval: false}
  standard: {gate: full,     reviews: 1, min_independence: L2, human_approval: false}
  high:     {gate: expanded, reviews: 1, min_independence: L2, human_approval: true}
  critical: {gate: expanded, reviews: 2, min_independence: L2, human_approval: true,
             prepare_and_execute: true}
  # min_independence above L2 (cross-vendor) is an optional, recorded budget
  # decision in a policy overlay, never a default.
protected_paths:
  - {path: "auth/**",       floor: critical}
  - {path: "billing/**",    floor: high}
  - {path: "migrations/**", floor: high}
  - {path: "infra/**",      floor: high}
merge_rule: >
  Auto-merge if and only if: the specification is ready and valid; every
  acceptance criterion is passed in a valid proof manifest for this exact
  commit; all mandatory checks pass; the verdict is pass or pass_with_notes
  with zero blocking findings; the effective risk tier permits auto-merge;
  every required approval is recorded, unexpired, and digest-bound to this
  commit; and the change is classified reversible.
```

The merge_rule reads as prose for humans; the engine evaluates it as structured conditions, and this text is the specification of those conditions. Two additions complete the policy. First, proof freshness: proof is valid only for the state it ran against, so when the trunk has moved, the gate re-runs on the merged result before the merge completes; at low volume that is a rebase and re-run, at scale a merge queue. Second, the emergency lane from the method: when production is failing, policy allows a fix-forward merge with a human engaged, and opens a backfill obligation (specification, proof, review) that must close within 24 hours. An unclosed backfill blocks the next ordinary merge, which is what keeps the lane honest.

**Effective risk** is computed, not declared: the maximum of the specification's declared tier, the floor of any protected path the diff touches, and the output of any semantic classifiers (destructive migration, permission change, data deletion). An agent may raise its own risk classification; nothing may lower it below the computed value.

**The independence ladder** referenced by `min_independence` formalizes reviewer independence:

| Level | Reviewer | Minimum for |
|---|---|---|
| L0 | Same context as the implementer | Never acceptable |
| L1 | Fresh context, same model | Low risk |
| L2 | Fresh context, different model | Standard, high, and critical risk (the working default) |
| L3 | Different vendor's model | Optional escalation, by recorded policy decision |
| L4 | Panel of 2+ independent reviewers across vendors | Optional escalation for the riskiest surfaces |

L3 and L4 are deliberately optional, because a second vendor is a real cost: separate accounts, tooling, spend, and operational surface. They are warranted only where a same-vendor blind spot is a live risk the organization has consciously judged worth paying to remove. The contained default at every tier above low is L2 - a fresh context on a different model of the same vendor - and critical risk is met by two independent L2 verdicts. Escalating a tier to L3 or L4 is a recorded budget decision in the policy overlay, never an ambient requirement. L4 is recorded as multiple independent verdicts, one per reviewer; the policy engine counts them, and no aggregate verdict object exists.

**Downstream may only tighten.** An organization baseline sets minimums; a repository overlay may raise a floor or add a protected path, never relax one.

### 3.5 Lifecycle events

An append-only stream of state transitions. Emit these from the very first change, even when the only consumer is a JSONL file, because every metric the method mandates (specification-to-production time, proof latency, first-pass proof rate, escaped defects, reversion rate) is derived from these events and is unrecoverable if they were never emitted. The event you did not emit is the metric you will never have.

```json
{
  "schema": "veldo.event/v1",
  "id": "evt_01K0A9G0F4",
  "type": "gate.passed",
  "spec_id": "VELDO-0142",
  "commit": "7f43e6159aa6",
  "at": "2026-07-16T14:12:10Z",
  "producer": "gate-runner",
  "correlation": "chg_01K0A98H",
  "payload": {"duration_s": 214, "proof_digest": "sha256:5f73..."}
}
```

Core event types: `spec.ready`, `spec.blocked`, `impl.started`, `impl.completed`, `gate.passed`, `gate.failed`, `review.passed`, `review.failed`, `policy.decided`, `approval.recorded`, `change.merged`, `change.deployed`, `postmerge.failed`, `change.reverted`, `spec.shipped`.

Events that consume human attention (the intent dialogue, clarifications, judgment, approvals) carry a `human_minutes` field in their payload; that is what makes the method's human-minutes-per-shipped-change metric derivable straight from the log.

Delivery is at-least-once; every consumer is idempotent by event id. At solo and small scale the committed log's branch churn is accepted (an append-only file merges trivially); when that friction grows, the log moves off-branch, appended by CI or shipped straight to the warehouse, with the envelope unchanged. Ordering is guaranteed per correlation id where it matters. At solo scale the "bus" is a file the scripts append to; the envelope is identical when a real broker replaces the file, which is what makes that replacement a transport swap instead of a migration.

### 3.6 Repository index

Derived, never authoritative. A generator reads specification front matter and writes a diffable table: id, title, status, risk, owner, approval requirement, last update. If the index and a specification disagree, the specification wins. If the index and any external tracker disagree, the repository wins. Do not rebuild a ticket system inside Markdown; the index is a navigation layer, nothing more. It is groomed in the weekly index pass, the one recurring ritual the method keeps (method section 6): fifteen to twenty minutes to close what shipped, kill what went stale, and confirm what is ready next.

### 3.7 Human approval record

The durable record of accountable human judgment, required for protected and irreversible changes. Approvals are the one contract where identity strength matters as much as content.

```json
{
  "schema": "veldo.approval/v1",
  "id": "apr_01K0AC91",
  "decision": "approved",
  "approver": {"id": "user:47281", "role": "security-owner"},
  "scope": {
    "spec_id": "VELDO-0142",
    "commit": "7f43e6159aa6",
    "proof_digest": "sha256:5f73...",
    "policy_version": 3
  },
  "reason": "Staging simulation passed; execution window approved.",
  "recorded_at": "2026-07-16T15:04:00Z",
  "expires_at": "2026-07-16T16:04:00Z"
}
```

The rules that matter, from the first protected change onward: records are appended, never edited; approval binds to the exact commit and proof, so any change to either invalidates it (this is the whole trick, and it is nearly free); approvals expire; self-approval is denied where separation of duties applies; rejections are retained. A pull-request comment or a chat message is not an approval, because neither says precisely what was approved. That is the entire ledger. Regulated domains may extend it with signatures and hash-chaining; for everyone else that is ceremony, not safety.

### 3.8 Contract change management

Contracts evolve; keep it simple: additive changes within a major version, a new major for breaking changes with a window where consumers accept both, and validation on read that rejects unknown majors loudly rather than coercing silently. A few example objects per version checked in the gate is enough to catch a contract regression like any other defect.

### 3.9 Product Plan (the planning contract)

The planning-layer contract, above the per-change seven (section 2.3). A Product Plan is a Markdown file with structured front matter, one per product increment, that holds the holistic view (method Stage 0) so every specification pulled from it inherits the whole. Only the planned lane uses it; the direct lane never touches it.

```yaml
# plans/PLAN-0007-orders-redesign.md
schema: veldo.plan/v1
id: PLAN-0007
title: One line - the product increment this plan delivers
kind: iteration          # iteration | mvp | release
status: ready            # draft -> ready -> in_progress -> released -> closed
revision: 1              # bump on any scope change after approval
owner: who-answers-for-this
approved_by: <human>     # required the moment status leaves draft
approved_at: 2026-07-16
outcomes:
  - {id: O1, becomes_true: The observable change for users, measure: how anyone verifies it}
non_goals:
  - {id: NG1, text: Named exclusions that kill scope drift}
constraints:
  - {id: C1, text: Budgets and invariants every work item inherits}
feature_tree:
  - {id: F1, title: A capability a user can name, outcome_refs: [O1]}
work:                    # the ordered DAG; each item becomes one spec
  - {item: W1, spec: VELDO-0501, title: Small and independently provable,
     feature_refs: [F1], depends_on: [], order: 10}
regression:
  journeys:
    - {id: RJ1, title: What must stay green across the whole plan,
       activation: {when: start}, profiles: [per_spec, release], suite: where it runs}
release:
  milestone: What done is called
  mode: continuous       # continuous | coordinated
  require_all_work_shipped: true
  require_full_regression: true
open_decisions:
  - {id: D1, text: The question and who answers it, blocks: []}
```

What the validator enforces mechanically (fails closed, run in the gate):

- **Structure and vocabulary.** `veldo.plan/v1`, a `kind` from the allowed set, required sections present.
- **Reference integrity.** Every `feature_refs`, `outcome_refs`, and `depends_on` resolves to a declared id; `depends_on` must be present (an empty list is a declaration, a missing one is an error).
- **Acyclic DAG.** The work dependency graph has no cycle.
- **Approval beyond draft.** A plan past `draft` must record `approved_by` and `approved_at`; a plan approves only by a recorded human decision, exactly like a specification.
- **No blocking decision at a ready item.** An open decision may not block a work item that is otherwise on the frontier; a decision that gates work keeps that work off the frontier until it is answered.
- **Two-way mirroring.** Every work item names the spec it becomes, and every planned spec (`lane: planned`) names its `plan` and `work`; the two must agree in both directions. A half-promoted spec, or a work item with no spec, fails.

The lane fields live on the specification (section 3.1): `lane: standalone` (the default; forbids `plan`/`work`) or `lane: planned` (requires `plan`, `work`, and, for stale-context refusal, the `plan_revision` it was pulled against). These are validated with the same fail-closed discipline as everything else.

The plan is derived-reportable, never hand-maintained: its burn-down and frontier are computed from the specification files, and the repository index carries a Product Plans section generated alongside the spec table. Like the index, the plan is a projection of the truth in the specification files, not a second source of it.

## 4. Claude Code setup

This is how the agents actually run the method. The setup is a folder of files in the repository. That fact is the point: on a solo machine it is edited directly; in an organization the identical folder is packaged as a plugin and executed by a managed runtime. Nothing about it is redesigned in between.

### 4.1 Instruction files

Claude Code auto-loads `CLAUDE.md`: the repository root file, nested `CLAUDE.md` files in subdirectories (closest to the work wins), and a user-level `~/.claude/CLAUDE.md`. It does not auto-load any other instruction file by convention, so `CLAUDE.md` is the entry point, always.

- **`CLAUDE.md`** carries the always-true facts: the canonical verify command, the specs directory, the protected paths, coding conventions, product terminology, and a required-reading pointer to `VELDO.md`.
- **`VELDO.md`** carries the agent operating rules from method section 8: how a change opens, what done means, the prohibited behaviors, the role definitions.

Keep both lean. Context is the scarce resource, and the division of labor is strict: always-true facts live in `CLAUDE.md`; this-task intent lives in the specification; repeatable procedures live in skills. An instruction file that grows past what an agent needs on every single task is hiding either a skill or a document.

A minimal root `CLAUDE.md` is short enough to quote whole:

```markdown
# Repository instructions

1. Read VELDO.md before changing anything.
2. The unit of work is a specification in specs/. Do not implement without a ready spec.
3. The canonical gate is ./scripts/verify.sh. Green is the only done.
4. Protected paths and merge policy: .veldo/policy.yaml.
5. Never approve your own implementation. Review runs in a fresh context.
```

And the repository shape it points into:

```
/
├── CLAUDE.md              # entry point (auto-loaded)
├── VELDO.md                # operating rules
├── .claude/
│   ├── agents/            # the five role subagents
│   └── skills/            # the pipeline skills
├── .mcp.json
├── .veldo/                 # policy.yaml, validator, contract examples
├── specs/                 # the unit of work
├── proof/                 # proof manifests and small reports
├── scripts/verify.sh      # the one gate
├── src/
└── tests/
```

### 4.2 The Veldo roles as subagents

Each role is a Markdown file in `.claude/agents/`, with YAML frontmatter naming its tools and model, and a system-prompt body. Every subagent runs in its own fresh context by construction, which is exactly the isolation the method requires.

| Subagent | Tools | Job |
|---|---|---|
| `veldo-spec` | read, search, write to `specs/` only | Interview the human, then draft the specification from the answers; surface ambiguity; never invent product decisions |
| `veldo-implementer` | full development tools | Implement the smallest complete change, write meaningful tests, run the gate, produce the proof manifest |
| `veldo-verifier` | read, run checks | Confirm the proof maps to the criteria; refuse to pass unproven claims |
| `veldo-reviewer` | read, search, run checks; no write | Judge the spec, diff, and proof from first principles; emit the verdict |
| `veldo-steward` | read, write to instructions and index | Keep the index, instructions, and specs current; delete stale context |

The reviewer definition pins a different model via the frontmatter `model` field and is given the specification, the final diff, the proof manifest, and the repository instructions, never the implementer's conversation. That yields independence level L2 with zero infrastructure. The whole file is about this small:

```markdown
---
name: veldo-reviewer
description: Independently review a Veldo change against its spec, proof, and final diff.
tools: Read, Grep, Glob, Bash
model: <pinned reviewer model>
---

You are the independent Veldo reviewer. Start from first principles; do not
trust the implementation summary. Read the specification, the final diff,
the proof manifest, and the tests. Rerun checks when in doubt. Fail the
review if any criterion is unproven, a mandatory check was skipped, the
proof does not match the final diff, or a blocking finding remains. Judge the change against the Intent
section, not only the criteria. Emit
a verdict in the veldo.verdict/v1 schema. You must not modify any file.
```

Levels L3 and L4 (different vendor, panel) cannot come from a frontmatter field, because a subagent runs inside one vendor's harness. Where an organization has opted into cross-vendor review, it is invoked from outside: a CI step calling the other vendor's API, an MCP bridge, or the Agent SDK. At solo and small-team scale, L2 locally is the working default at every tier; an organization that adopts L3 runs it as a CI step for the surfaces it named when it made that budget decision. Whatever the level, the exact reviewer model identifier is recorded in every verdict.

### 4.3 Skills

Skills are repeatable procedures in `.claude/skills/<name>/SKILL.md`, invoked as `/<name>` with arguments available as `$ARGUMENTS`. They keep procedures out of the always-on context and make the pipeline uniform:

- `/veldo:plan` - define and steward a Product Plan: create, refine, approve, pull a work item into a spec, revise with impact analysis, status, regression, release (section 4.10, contract 3.9).
- `/veldo:spec` - draft a specification by interviewing the human, then validate it.
- `/veldo:gate` - run the canonical verification command and interpret failures.
- `/veldo:proof` - assemble and validate the proof manifest for the current change.
- `/veldo:review` - run the fresh-context review and emit a schema-valid verdict.
- `/veldo:index` - regenerate the index from specification front matter.
- `/veldo:run` - the whole pipeline for one ready spec, end to end; the normal human entry point once the loop is trusted.
- `/veldo:status` - in-flight specs, gate state, open judgment calls, emergency debt.

(Plugin-qualified names; a manual, plugin-less install exposes bare `/spec`-style names instead.)

Each skill ends by emitting its lifecycle event. That one habit is what makes the metrics pipeline exist at solo scale without any service. A skill is as small as its job:

```markdown
---
description: Run the canonical gate and produce a proof manifest.
allowed-tools: Read, Grep, Glob, Bash
---

Verify the specification identified by $ARGUMENTS. Run ./scripts/verify.sh,
map each acceptance criterion to its evidence, and emit a veldo.proof/v1
manifest. A skipped mandatory check is not a pass. Append the gate.passed
or gate.failed event when done.
```

### 4.4 Hooks: mechanical enforcement

Hooks are stance 3 made real. They are configured in `settings.json`, fire on tool events, and a `PreToolUse` hook can block the call outright (a command hook blocks by exiting 2, with stderr shown to the agent, or by emitting a deny decision). The standing Veldo guards:

1. **No merge without proof.** On any tool call that pushes, opens, or merges a change: block unless a valid, schema-checked proof manifest exists for the exact HEAD commit.
2. **No done without green.** On completion claims: block unless the canonical gate has passed on the current state in this session.
3. **No secrets on disk.** On every file write: run a secret scan; block on a hit.
4. **No work without a spec.** On implementation activity: block unless an associated specification in `ready` status exists.
5. **No irreversible execution without a live approval.** On any tool that executes a prepared irreversible operation: block unless an unexpired approval exists for that exact plan (section 7.2).

All five guards route through one policy script, so there is one place where the rules live:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "./scripts/veldo-guard.sh"}]
      }
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "./scripts/veldo-guard.sh"}]}
    ]
  }
}
```

Two of the five guards (merge and completion) are enforced by this hook directly; the secret scan runs inside the gate on every verify; the spec and approval guards are enforced by policy evaluation and review, and server-side at scale. The `Stop` entry is a backstop against unsupported completion claims. Hooks run on the developer's machine and are therefore editable by the developer; treat them as the always-on first line, not the last. The same rules are enforced server-side by branch protection and later by the merge-policy engine, so they hold for every agent everywhere, including agents no one is watching.

### 4.5 Permissions and sandboxing

Settings live at three scopes (four in organizations, where managed settings outrank all): `.claude/settings.json` (project, committed), `.claude/settings.local.json` (personal), and `~/.claude/settings.json` (user). Permission modes range from prompt-by-default to fully autonomous, with allow, deny, and ask lists per tool.

The governing principle as autonomy grows: **capabilities, not credentials.** An agent that needs to deploy to staging gets a `deploy-staging` tool that performs exactly that operation server-side; it does not get cloud keys. Concretely:

- Solo, interactive: a permissive mode is acceptable, because a human sits in the loop and the human performs every merge.
- Team and CI: least privilege. Autonomous agents run with scoped tool allowlists, short-lived tokens, and no production credentials in context.
- Parallel work: each concurrent agent runs in an isolated git worktree with a file-disjoint scope, so parallel changes cannot collide.
- Sandboxing: autonomous agents run in ephemeral environments that are destroyed after evidence capture, with egress restricted to approved registries and APIs.

### 4.6 MCP servers

MCP connects agents to the systems the method needs them to read and act on: the git host, CI, the observability stack, the knowledge index, and any capability APIs. Configuration lives in `.mcp.json` at the repository root (project scope) or at user scope, over stdio or http transports. Each server is least-privilege: narrow operations, validated arguments, no pass-through shells to privileged systems. MCP is also how non-Claude models are reached when a review must cross vendors.

### 4.7 Orchestration

The spec-to-merge pipeline is deterministic, so drive it deterministically: a single command or scripted workflow that scaffolds the spec, dispatches implementation, runs the gate, invokes the fresh-context review, evaluates the merge policy, and either merges or routes to a human. Improvising the sequence per change is how steps get skipped.

Fan out only across independent specifications, each in its own worktree with disjoint file scopes. The ceiling on parallelism is not tooling; it is the human's review and judgment capacity, which is why work-in-progress stays within what the human can actually judge.

### 4.8 Headless operation and the Agent SDK

`claude -p "<prompt>"` runs non-interactively and is the bridge into CI. The reviewer as a CI step, whole:

```bash
claude -p "Review the change for spec VELDO-0142 against its proof manifest and final diff." \
  --allowedTools "Read,Grep,Glob,Bash" \
  --permission-mode default \
  --output-format json \
  --json-schema "$(cat .veldo/schemas/verdict.json)"
```

The flag takes the schema value itself, hence the `$(cat ...)`. It matters more than it looks: a malformed verdict is rejected at the tool layer and retried, rather than discovered downstream as a parsing surprise. The implementing agent can run the same way for autonomous work on low-risk specifications.

The Claude Agent SDK (Python and TypeScript) embeds the same harness (tools, hooks, subagents) as a library, and it is the substrate for the control-plane services in section 6: the review orchestrator and the agent runtime are SDK services, not shell scripts around a terminal. When a managed agent runtime is available, prefer it for the sandboxing, secret handling, and concurrency control you would otherwise build yourself.

### 4.9 Distribution

At team scale, package the whole setup (agents, skills, hooks, commands, MCP configuration) as a plugin and enable it via settings. Every repository and every person then runs the identical Veldo tooling at the same version, upgraded like any dependency. Onboarding a person or a repository collapses to: install the plugin, write the repository's `CLAUDE.md`, run the first specification through the pipeline.

**The two-tier adoption model.** There are two ways Veldo lands in a repository, and they lay down deliberately different amounts. Installing a pack lays the FULL engine: the gate, the contract validators, the runners, and the fleet, everything a repository needs to specify, prove, and build work in parallel. Running `/veldo:init` lays only the MINIMAL governance substrate: the canonical gate, the contracts, the policy, and the templates, for a repository that wants the enforced spine without the rest, and it is intentionally kept minimal rather than expanded to match the pack. The distinction answers one question directly: the path that delivers the fleet is installing a pack, not `/veldo:init`. A repository that wants parallel workers installs the pack.

### 4.10 Operating the planning layer

The planning layer runs as one skill over the plan contract (3.9) and one small module of mechanical verbs. `/veldo:plan <sub-verb>` is the dialogue; `.veldo/plan.py <verb>` answers the questions that must be computed rather than narrated. Everything the module reports is derived from the specification files, so it agrees with the index by construction.

**Standing a plan up, then keeping it current** (`/veldo:plan`, one dialogue skill):

- **create.** Interview at the product level: what user outcomes must become true, the feature breakdown, what is explicitly out, what must stay green (regression), and what "done" means (release). Draft from `plans/TEMPLATE.md`, give every work item a small, independently provable scope and an honest `depends_on`, leave `status: draft`, then `python3 .veldo/validate.py plan <file>` must pass.
- **refine.** Edit a draft freely with the human (split or merge work items, correct dependencies, sharpen outcomes), then re-validate. A draft changes freely; anything past draft uses revise.
- **approve.** A plan leaves draft only by a recorded human decision: set `status: ready`, `approved_by`, `approved_at`, and re-validate. This is the gate that makes the ordering real.
- **pull.** Turn the next ready work item into a specification. Read the frontier (below), pick a work item whose dependencies are all shipped, and create its spec with `/veldo:spec`, setting `lane: planned`, `plan`, `work`, and `plan_revision` so the mirroring holds and stale-context refusal can fire later.
- **revise.** A change to an approved plan (new work, changed dependencies, dropped scope) is a revision, not an edit: bump `revision`, add a `## Revisions` note, and run impact analysis on anything already shipped. Record what the revision invalidates.

**The mechanical verbs** (`python3 .veldo/plan.py <verb> <plan>`), all derived from spec status:

| Verb | Answers |
|---|---|
| `status <plan>` | The burn-down: each work item's state (shipped, waiting on named deps, blocked by a decision, or on the frontier) and the ready frontier |
| `release-check <plan>` | Whether the plan is releasable, and if not, exactly why (unshipped work, missing regression, an open decision still blocking, no milestone) |
| `impact <plan> <SPEC>` | The transitive dependents of a spec within the plan - the blast radius of changing it, with a warning for already-shipped dependents that may need re-proof |
| `regression <plan> per_spec:<SPEC>` / `regression <plan> release` | The regression journeys active while building SPEC, or at the release gate; manual-trigger journeys are surfaced separately, never auto-run |
| `bundle <plan> <SPEC>` | The plan context bundle for building SPEC: the outcomes, this item's features and dependencies, inherited constraints, and the regression that must stay green |
| `run-check <plan> <SPEC>` | The run-time refusal: fail if a dependency is unshipped or the plan has revised since the spec was pulled (stale context) |
| `hash <plan>` | A stable content hash of the plan, so a proof can bind to the exact plan state a change was built against |

**How the run enforces the plan.** `/veldo:run` on a planned spec runs `run-check` before building and stops if it refuses, loads the `bundle` so the agent sees the whole, and records the plan `hash` into the proof. That preflight is mechanical (it lives in `.veldo/plan.py` and the run skill calls it); building out of order or against stale context is refused, not merely discouraged.

**Regression at the gate.** Journeys declare `activation` (start, after a named spec ships, or manual), an optional `owner_spec`, and `profiles` (per_spec, release). The active-suite computation is mechanical; the EXECUTION wiring is per-repo reference: a repository points its `CHECK_journeys` gate slot at `plan.py regression` so the gate runs exactly the active per-spec suite. A repository with no user interface leaves the slot `na` and its journeys resolve to whatever its unit suite is.

**Status and release.** `status` is the whole board; there is no second tracker. `release-check` is the only thing that lets a plan move to `released`: for `mode: continuous` the work already merged as it went green, so release is the milestone marker plus the observation window; for `mode: coordinated` you cut the release together once the check passes.

The honesty line for this layer, straight from the capability manifest: the plan dialogue is a procedure (skill-instructed, not a transactional orchestrator); plan validation, the lane fields, the burn-down and frontier, the run-time refusal, and the plan hash are mechanical; and the gate-slot execution of regression is reference wiring each repository completes. Nothing here is described as more automatic than it is.

### 4.11 The fleet: elastic parallel workers

A repository with several independent ready specifications does not have to build them one at a time. The fleet runs many workers in parallel, each pulling ready work from anywhere it can see, building it, and landing it, so throughput scales with the workers you run. It obeys the same architecture as everything else in this document: it changes only where the work executes, never how a change is specified, proven, reviewed, or merged.

**The `veldo` CLI.** A single `veldo` executable is the front door, a thin dispatcher over the engine modules with no logic of its own. `veldo work` runs one worker in the current terminal; `veldo fleet N` runs up to N workers paced by the token governor; `veldo status` and `veldo watch` read the live run state; `veldo account add` and `veldo account list` manage accounts. Each subcommand routes to a shipped module and reimplements nothing.

**The account model.** A worker runs under a named account, each with its own persisted login in its own `CLAUDE_CONFIG_DIR`. `veldo account add <name>` is a one-time login that persists; a worker driven under that account reuses the saved login with no re-login thereafter. Accounts are how the fleet scales past one identity's throughput without sharing credentials.

**The governor.** The token governor paces the fleet against the budget. It does not query a remaining-token count (the harness exposes none); it measures burn from the event stream over a rolling window and sizes the active worker count so measured burn tracks the target rate for the tighter of the configured windows. Per account, the same control law applies to each account's own measured burn, and the per-account allowances sum into the pool, so a spent-out account never stalls the others and a backed-off account resumes when its own window rolls off. This is the cost-per-proven-change discipline of section 7.5 made mechanical for parallel work.

**In-session, never detached.** A worker is a real in-session worker; the fleet spawns nothing detached or headless, and a backed-off pool waits in-session and re-checks its budget before resuming. The build, the fresh-context review, and the in-session start primitive are delegated seams that fail loud rather than fabricate a result. This is the same no-rogue-process boundary the whole method holds: autonomous parallel work runs inside real sessions, not as background daemons.

Read against the capability-by-scale table (section 2.4): solo is one worker with `veldo work`; a small team runs `veldo fleet N` in a terminal; scaling adds accounts and lets the governor pace the pool; an organization runs the fleet across a workspace of repositories under per-account budgets. The contract never moves; only the number of workers and accounts does. The operational runbook for driving a fleet is in the runbook document.

## 5. The scaling stages

The rule of the stages: change implementations, never contracts. Each stage below states what exists, what runs as a script versus a service, what must not be skipped even at that stage, and the observable signal that the stage is outgrown.

### 5.1 Stage 0 - Solo

One person, Git, a git host, hosted CI, and Claude Code. There are no services, and none are missing: this is the complete method, implemented in files.

What exists: the seven contracts and their validators; specifications in `specs/`; one canonical `./scripts/verify.sh`; proof manifests under `proof/`; a reviewer subagent on a second model; a policy file; branch protection with the gate as a required check; an `events.jsonl` the skills append to; approval records committed for anything touching a protected path.

What must not be skipped, even alone:

1. The contracts and their validators. Retrofitting schemas onto months of freeform artifacts is the expensive version of an afternoon's work.
2. The one canonical gate command, identical locally and in CI. Divergence between what the agent ran and what CI runs is a class of failure you simply never allow to exist.
3. Fresh-context review on a different model. Solo is where self-confirmation bias is most dangerous, because there is no colleague to catch it.
4. The event log. Metrics not emitted are gone forever.
5. The protected-path list and real approval records. You are the approver; the discipline of recording it is what makes the ledger real later.

The human wears every human hat (intent, judgment, approval), but the execution contexts stay separate: the implementer and the reviewer are never the same context, even though the same person launches both.

Stage 0 is not a starter kit; it is the complete method with the cheapest correct parts, and a team that stays here forever while shipping fast has Veldo working exactly as designed. Complete means actually wired: the plugin lays the substrate and enforces the core mechanically, and its capability manifest (`.veldo/capabilities.yaml`) is the honest statement of which pieces are mechanical, which are procedure, and which remain target behavior in the current release.

Outgrown when: a second person joins, or you can no longer hold the cross-repository picture in your head.

### 5.2 Stage 1 - Small team (2-10)

Still git-host-native. Still no bespoke services.

Add: branch protection with required checks everywhere; CODEOWNERS mapping protected paths to named human approvers; auto-merge on green for reversible changes; the reviewer running headless in CI on every change; the Veldo setup distributed as a versioned plugin; a small dedicated repository aggregating every repository's index into a cross-repo view; lifecycle events shipped to one warehouse table; per-repository token budgets; secrets held by the CI provider, never in repositories or prompts.

Must not be skipped: digest-bound approval records for protected paths (a PR approval click is not an approval record); the shared plugin (per-person divergence in tooling is contract drift in disguise); event shipping.

Outgrown when: more than one system needs to consume lifecycle events; portfolio questions exceed what generated Markdown can answer; agents need to run somewhere other than CI jobs; or review volume needs routing and retry logic rather than a static CI step.

### 5.3 Stage 2 - Scaling (10-100, many repositories)

Conventions stop holding the line; the control plane begins, built strictly behind the contracts that already exist and in the build order of section 6.2. Nothing about how work is specified, proven, reviewed, or approved changes. Only where those steps execute changes.

Add, in order as each earns its place: the gate runner as a service; the content-addressed proof store; the merge-policy engine evaluating policy-as-code server-side; the real message bus (the moment the first external consumer appears, git-host webhooks are normalized onto it); the review orchestrator with model routing and the independence ladder; the spec registry with the cross-repo index; workload identity, RBAC, and a secrets manager before autonomy broadens; then the agent runtime with enforced budgets.

A platform owner emerges whose product is the Veldo platform itself, measured on proof latency and reliability, not on features shipped.

Outgrown when: tenancy, compliance, regional, or SLO requirements exceed what one shared deployment can honor.

### 5.4 Stage 3 - Organization (100s-1000s)

The method does not change at all. The platform hardens into a product with tenants: multi-tenant control-plane services behind SSO; versioned organization policy bundles with repository overlays that may only tighten; the approval ledger with retention appropriate to the domain; SLOs on proof latency and review turnaround; cost allocation per specification, repository, and tenant; compliance exports generated from the records that already exist rather than maintained in parallel; disaster-recovery exercises on a calendar.

Standardize contracts and interfaces, never languages or build systems; repositories keep their own toolchains behind the same `verify` entry point. Human roles at this scale: domain teams own specifications, acceptance criteria, and their stricter policy overlays; the platform team owns contracts, services, and the paved road; a small governance function owns the organization baseline policy and the protected-path taxonomy.

Outgrown when: it is not. This stage sustains; the remaining work is continuous improvement of proof latency, escaped-defect rate, and cost per proven change.

## 6. The Veldo control plane

The control plane is the software you build for the long term: the services that apply the contracts consistently across changes, repositories, and teams once scripts and git-host features stop being enough. Read it with the proportionality rule in hand: every component here is optional weight until a measured bottleneck proves otherwise, and a team that lives at stage 0 or 1 forever, shipping fast with scripts and CI, is a Veldo success story, not an immature one. The non-negotiable principles when you do build:

- **It indexes truth; it never owns it.** Every database inside the control plane is a rebuildable projection of repositories, immutable records, and retained events. The drop-in test from section 1 is the standing check.
- **Event-driven on a real bus.** The moment work crosses a process boundary, transitions travel as events on a broker with durable subscriptions. A database is a store, not a bus; polling tables to detect changes is a defect, not a pattern.
- **Immutable records.** Proofs, verdicts, approvals, and events are append-only and content-addressed. Corrections reference; they never rewrite.
- **Policy as code.** Every decision the plane makes is the deterministic evaluation of versioned policy against digest-bound inputs, and the decision itself is recorded with the policy version that produced it.
- **Every capability is an agent-usable API.** Agents operate the plane at least as much as humans do. A capability reachable only through a human UI does not exist for the system that does the work.
- **Vendor and model agnostic.** The contracts are the portability layer; an organization that opts into cross-vendor review reaches the second vendor through the same contracts, and one that does not is still never coupled to a single model.

### 6.1 The components

Each component states its purpose, the contract it implements, its interface, and its cheap-first and hardened forms. The cheap form is not a prototype to be thrown away; it is the same contract on a smaller transport.

**Spec registry.** Purpose: validation, lifecycle state, and organization-wide query over specifications without moving authority out of Git. Contract: specification, index. Interface: `veldo spec validate|get|list` and `GET /v1/specs?...`. Cheap: the in-repo validator and index generator. Hardened: a read-only service fed by git events, rebuildable from the repositories at any time; a dashboard edit that does not become a repository commit is forbidden.

**Gate runner.** Purpose: execute the canonical checks in a clean environment and produce the proof manifest. Contract: proof manifest. Interface: `./scripts/verify.sh` locally; `POST /v1/gate-runs` as a service. Cheap: CI running the same script agents run locally. Hardened: hermetic content-addressed runner images, a scheduled fleet, risk-aware and change-aware check selection with a reliable full gate preserved, flake quarantine treated as a production defect, and proof-latency SLOs.

**Review orchestrator.** Purpose: make independent review routine: spawn fresh-context reviewers at the required independence level, collect schema-valid verdicts, route failures back, and pull in a human after two failed cycles on the same specification. Contract: review verdict. Interface: `POST /v1/reviews`. Cheap: a headless reviewer invocation in CI with `--json-schema` enforcement. Hardened: an Agent SDK service that routes models by risk tier, runs panels for critical changes, retries without letting an implementer touch a verdict, and measures reviewer catch rate and false-escalation rate.

**Merge-policy engine.** Purpose: the deterministic decision. Inputs: spec, proof, verdicts, approvals, changed paths, semantic classifications, policy version. Output: merge, wait, reject, or require-human, with matched rules and missing requirements listed. Contract: risk and merge policy. Interface: `veldo policy evaluate` in CI; `POST /v1/policy-decisions` as a service. Cheap: a deterministic script plus branch protection and CODEOWNERS. Hardened: a stateless decision service with versioned policy bundles, stricter-only overlays, semantic classifiers, decision records with policy digests, and policy simulation before rollout. Missing inputs mean rejection; the engine fails closed.

**Approval and audit ledger.** Purpose: durable, accountable human judgment. Contract: human approval record. Interface: `veldo approval request|approve|reject`; `POST /v1/approvals`. Cheap: digest-bound approval objects committed to the repository from the very first protected change; this form serves most teams indefinitely. Hardened: an append-only store with strong authentication and separation of approver and operator roles. Regulated domains extend from there (signatures, hash chains, retention regimes); nobody else should.

**Proof and evidence store.** Purpose: immutable, digest-addressed storage for everything a merge decision relied on. Contract: proof manifest artifacts. Interface: `veldo proof put|get|verify`; `GET /v1/artifacts/{digest}`. Cheap: small reports in Git, large artifacts in versioned object storage with digests recorded in manifests; this is sufficient for most teams forever. Hardened: retention by risk class and survival independent of any CI vendor.

**Event bus and metrics pipeline.** Purpose: decouple producers from consumers and derive every delivery metric from one stream. Contract: lifecycle event. Interface: publish and durable subscribe, plus `GET /v1/metrics/...`. Cheap: the appended JSONL and a query script; then one warehouse table. Hardened: a managed broker with tenant namespaces, schema enforcement, dead-letter handling, deterministic replay, and dashboards with alerting on proof latency, first-pass rate, and reversion rate. The bus arrives when the first external consumer does, not before and not after.

**Agent runtime with cost governance.** Purpose: run specification, implementation, verification, review, and steward agents under explicit identity, permission, budget, and time constraints. Contract: agent job (role, model set, tool permissions, budgets, termination reason). Interface: `POST /v1/agent-jobs`. Cheap: headless CI jobs with per-run token and time limits recorded into proofs. Hardened: an SDK-based scheduler with ephemeral sandboxes, short-lived workload credentials, model routing by risk, concurrency limits, runaway-loop detection, per-level budget enforcement with hard stops, and organization kill switches.

**Knowledge and memory.** Purpose: let agents find authoritative context without creating a second source of truth. Contract: commit-pinned citations. Interface: `veldo knowledge search`; an MCP server exposing the same. Cheap: repository search plus a steward agent that prunes stale instructions. Hardened: an event-fed index over authorized repositories with exact citations (repository, commit, path), staleness marking, and access control. Durable knowledge returns to the repository as a reviewed change; a vector index is derived state, never memory of record.

**Observability, post-merge verification, rollback.** Purpose: production evidence is part of proof; detect when it contradicts pre-merge proof and recover. Contract: deployment records and post-merge checks referenced by the specification. Interface: `veldo observe status`; `POST /v1/rollbacks`. Cheap: deployment health checks in CI, the deployed commit recorded, one tested rollback script, a human paged for protected changes. Hardened: canary and progressive delivery, feature-specific baselines, automated rollback under policy safeguards, and escaped failures fed back into gates and specifications. Detection and recovery time are measured by risk class.

**Identity, RBAC, secrets.** Purpose: every human, agent, runner, and service acts under a verifiable identity with least privilege. Contract: principal, role binding, credential lease, access decision. Interface: capability APIs; agents request operations, never raw secrets. Cheap: git-host identity for humans, CI OIDC for workloads, short-lived scoped tokens, secrets in the CI provider. Hardened: SSO and provisioning, a secrets manager with rotation, just-in-time privileged access, per-tenant authorization on bus, store, and registry, and anomaly detection on agent access. Identity is required from the beginning; the dedicated service is not.

**Git-host integration.** Purpose: bind the plane to the developer workflow: ingest webhooks onto the bus, publish check results and policy decisions to changes, enforce branch protection declaratively, perform the merge. Contract: commit and change identity, check results, merge records. Cheap: hosted CI triggered by git events with required checks and auto-merge. Hardened: a git-host application spanning repositories with signed webhook verification, normalized events, a merge queue that re-proves the merged result, tenant isolation, and support for multiple hosts behind the same contracts.

### 6.2 The build order

Numbered so that each capability earns its place. The gate between steps:

> **In daily use** means: every eligible change in the pilot scope uses it; it has a named owner; its failure mode is understood; known bypasses are removed or explicitly governed; and it has survived at least ten eligible changes or two weeks of normal work, whichever is longer.

**Never build step N+1 before step N is in daily use.** The gate paces the hardening of capabilities into services; it does not pace the pilot (section 10), which lays steps 0 through 6 down as in-repo conventions in days. A convention becomes subject to the gate the day you propose replacing it with a service.

0. **Contracts and validators.** The seven schemas, golden fixtures, validation wired into the gate. Earns its place by ending ambiguity about what an artifact is.
1. **Canonical gate and proof manifest, in CI.** One command, criterion-level evidence. Earns its place by making completion objective.
2. **Lifecycle event log.** Append from the first change. Earns its place the first time you ask how long anything takes.
3. **Fresh-context review.** Headless, schema-enforced verdicts, second model. Earns its place with the first defect the implementer could not see.
4. **Merge policy as code.** Branch protection, auto-merge on green, protected paths, CODEOWNERS. Earns its place by deleting the routine approval queue.
5. **Approval ledger.** Digest-bound records for the first protected change. Earns its place the first time judgment must be accountable.
6. **Git-host integration.** Checks, statuses, auto-merge mechanics, webhooks captured. Earns its place by removing manual coordination between proof and merge.
7. **Real message bus.** When the first consumer beyond the log appears; webhooks normalized onto it. Earns its place by decoupling the first two services.
8. **Spec registry and cross-repo index.** Read-only, rebuildable. Earns its place when repository count defeats direct navigation.
9. **Identity, RBAC, secrets hardening.** Workload identity before broader autonomy. Earns its place before the first unattended agent with real permissions.
10. **Agent runtime and cost governance.** Scheduler, sandboxes, budgets. Earns its place when job volume and governance exceed plain CI.
11. **Post-merge verification and rollback automation.** Earns its place when production feedback is the dominant remaining confidence gap.
12. **Enterprise hardening.** Multi-tenancy, SLOs, retention, compliance export, DR exercises. Earns its place under sustained production traffic and real tenants.

Do not build the platform in anticipation of adoption. Prove the workflow in one repository; harden the bottlenecks that daily use demonstrates.

## 7. Governance, safety, and economics

### 7.1 Protected paths and effective risk

The protected-path list is data in policy, not judgment exercised per change: authentication and authorization, money movement and billing, destructive migrations, encryption and key management, permanent deletion, production access controls, regulatory behavior, the control plane's own policy, and the approval and identity systems. Effective risk is computed as the maximum of the declared tier, the touched-path floors, and semantic classification, and anything downstream may raise it further: a static detector, the reviewer, even a runtime observation. Nothing lowers it; lowering requires revising the specification itself, which invalidates the evidence bound to the old one.

### 7.2 Irreversible operations: prepare and execute

For changes where being wrong is unrecoverable, approving source code is not enough; the system approves the exact act:

1. Produce the precise execution plan (the migration script, the deletion list, the key rotation steps).
2. Dry-run or simulate it where possible; verify backup and recovery readiness.
3. Digest the plan. Obtain approval bound to that digest, with an expiry.
4. Execute before expiry. Any change to plan, commit, or environment invalidates the approval and returns to step 1.
5. Record execution and resulting state; observe with a human present where policy says so.

### 7.3 Audit

The audit trail is a byproduct, not a parallel system: intent, specification commit, implementation commit, proof manifest, evidence artifacts, verdicts, policy decision, approvals, merge, deployment, observation, closure, all digest-linked. The reconstruction test is periodic and real: pick a shipped change and walk the chain end to end from primary records. Compliance mappings are generated from these records; a spreadsheet maintained beside the system is an anti-pattern by definition. Retention follows risk class, and destruction at end of retention is itself an authorized, logged operation.

### 7.4 Security of the agent runtime

Treat every input as potentially hostile: repository content, pull-request text, tool output, external documents. All of it can carry instructions aimed at your agents. The posture:

- Ephemeral, isolated execution per job; destroyed after evidence capture.
- Least privilege everywhere: implementers write only to their branch and workspace; reviewers read and run checks; production credentials appear in no agent context.
- Short-lived workload identity; no static keys; egress denied by default for sensitive jobs.
- Capabilities, not credentials: privileged operations are narrow server-side tools with validated arguments.
- Secrets never in instructions, prompts, transcripts, proofs, or logs; scan on write and before storage.
- Untrusted code (forks, external contributions) never executes with privileged secrets; verification of untrusted changes is segregated from privileged operations.
- Hooks are defense in depth, not the isolation boundary; the sandbox is the boundary.
- Emergency controls exist at every level: cancel a job, a repository, a tenant, a model, or everything; revoke credentials immediately; preserve forensics.

### 7.5 Cost governance

The economic unit is **cost per proven, shipped change**, not tokens. Token counts alone reward the wrong thing; a cheaper agent that fails proof twice is more expensive than the stronger one that passes once.

Budgets exist per job, specification, repository, team, and organization, and every agent job declares its role, permitted models, and maximums (tokens, money, time, retries, concurrency) before it starts. Enforcement is preflight validation plus hard stop at the ceiling, with warning thresholds and bounded retries; budget terminations are recorded and visible. Model routing follows risk: economical models for mechanical work, the strongest models for review of high-risk changes, and reviewer strength is never lowered to save money. Track cost per proven change, rework cost after failed proof, cost of escaped defects, and the verification-investment share of platform work.

### 7.6 Reproducibility and model pinning

AI output is not deterministic, so reproducibility means reproducing inputs and conditions, never identical text. The practical rule: every proof and verdict records the exact model identifier and the digest of the instructions it ran under, and the gate runs in a pinned environment. That is enough to answer "what produced this and under what rules" for any shipped change. When a model is retired, the original record stands; nothing is backfilled. Upgrade models deliberately rather than silently: run the candidate on a handful of representative changes, compare review quality and cost, keep a rollback path.

### 7.7 Disaster recovery

Keep this simple, because the architecture already did the hard part. The recoverable core is small: repositories, the proof store, the approval records, and the retained events. Back that core up like you back up anything that matters. Everything else (registries, indexes, dashboards, scheduler state) is derived and gets rebuilt from the core, never restored as if it were truth. Restore in the obvious order: access first, then the core, then rebuild the derived state. Exercise a restore occasionally so the runbook is fact rather than hope. Organizations with real continuity obligations can add replication and formal recovery objectives; that is their extension to make, not the default.

### 7.8 Architecture as a contract (the shape organ)

Protected paths (7.1) govern the RISK of a change; this governs its SHAPE. Veldo proves every change locally, but a thousand locally proven changes cannot on their own vouch for the foundation they sit on. The organ makes the intended shape governable the same way intent became the spec.

- **The shape is a versioned, human-approved contract.** `.veldo/architecture.yaml` (schema `veldo.arch/v1`) states the repository's areas and module boundaries, allowed dependencies, patterns, invariants, and size and complexity budgets, each rule marked mechanizable or review-lane. It is validated structurally like a plan, and it leaves draft only by a recorded human approval: changing the shape means changing the contract first, on the record. It is the eighth contract-shaped artifact, but unlike the seven of 2.3 it is optional and per-repo - a repository declares its own shape or declares none.
- **Mechanizable rules fail the build; unmechanizable ones stay honestly in review.** The shape gate wired into `scripts/verify.sh` refuses a mechanizable violation with the rule named before any reviewer sees it. Be honest about the split at the current contract revision: what is gate-BLOCKING is the module-size budget (change-scoped, so the shipped corpus is grandfathered and only new entropy is refused) and the engine invariants (byte-identical packs, derived-never-authoritative, adoption-safe fail-closed). The dependency and import boundaries, the function-length, duplication, and complexity budgets, and the prose patterns ship as stdlib reference implementations surfaced as review-lane NOTES, not refusals. A rule that cannot be checked mechanically never becomes a vacuous gate check; a rule marked mechanizable with no wired enforcement is itself refused (anti-vacuity).
- **Placement before build, shape-fit at review.** Every spec declares its placement (which area it lives in) and footprint (what it touches); when a contract exists a spec cannot reach ready or be claimed without a placement that resolves to a declared area, and a footprint crossing an unmodeled boundary raises the risk tier and nothing lowers it. The independent review grades a second dimension where correct-but-does-not-fit is a real, merge-blocking rework verdict; its mechanical half is enforced and fails closed, and whether a change follows the declared patterns is a fail-loud delegated reviewer seam.
- **Foundational decisions are recorded, adversarially reviewed, human-decided, and monitored.** A technology, architecture-style, communication-shape, or tooling choice becomes a `veldo.decision/v1` record: options elaborated against the stated problem class (never today's scale), each with its dead-end condition, and assumptions carrying measurable signals and breach conditions. Only a human decides; scrutiny scales with reversal cost through the existing risk tiers (irreversible maps to critical, two independent reviews plus recorded human approval), and a fresh-context adversarial review attacks the proposal first. The recorded assumptions are living tripwires the system checks IN-SESSION (never a daemon or timer) in the gate, in `veldo status`, and at the weekly pass, so a wrong foundation surfaces as an assumption breach, not an outage; a breach drafts one re-decision unit a human promotes.
- **Entropy has a number and a response.** Per-area cost-to-change is derived from what the loop already records, joined to areas through placements; a relative degradation against an area's own trailing baseline (advisory during calibration) drafts a restoration spec a human promotes through the normal loop, and the post-restoration delta closes the loop. Nothing auto-gates on the number and nothing auto-promotes the draft.
- **Adoption-safe and per-repo.** A repository with no contract is byte-identically unaffected: every check above stands down. The contract, decision records, readings, and drafts are per-repo artifacts, never shipped in the engine or laid by `/veldo:init` (init lays the validators, not a contract). `.veldo/capabilities.yaml` is the machine-readable truth for exactly what is mechanical, what is a fail-loud reference seam awaiting per-repo reviewer wiring, and what is advisory; the Plugin Guide section 13 is the component reference.

## 8. The edges: design, intake, and documentation

Veldo's loop runs from intent to production. Three edges touch worlds that are not code: design tools, the people who report problems, and the places where humans read and write. The rule at every edge is the same one: the repository is the database, not the user interface. Humans work in their own tools, in their own words; agents carry truth across the boundary in both directions.

### 8.1 Design

A design file cannot be a contract. It is not diffable, agents cannot fully read it, and a browser never renders exactly what a design tool renders, so "bug = not exactly the mock" defines a defect class that can never be closed. The design contract therefore moves into the repository, in three layers, each with its own kind of proof:

1. **Tokens.** Colors, spacing, typography, and radii are exported from the design tool into a tokens file in the repository. The gate lints against raw values: no hex codes, no magic paddings, tokens only. Exactness is now defined against data, and an entire class of fidelity bugs becomes machine-checkable.

2. **Components.** A component library in code mirrors the design tool's component library one to one. Each component's fidelity is validated once, carefully, by human and designer eyes. Product screens are then composed only from library components, which makes screens on-design by construction for everything components govern; composition, layout, and responsive behavior still get the baseline check. Nobody inspects every screen's padding, because off-design parts do not exist to build with.

3. **Baselines.** For a new or changed screen, a human compares the rendered result against the design once, side by side, and approves. The approved screenshot becomes a locked visual-regression baseline, and the gate fails on drift beyond defined tolerances (zero-tolerance pixel gates are flaky; tolerances are part of the baseline). Humans judge fidelity once; machines prevent regression forever. What is never done is machine-diffing a browser screenshot against a design-tool export: that comparison can never converge, and chasing it is where design QA goes to die.

UX splits into two halves with different proofs. Flows are specifiable: acceptance criteria written as user journeys ("a payment failure returns the user to the cart with items intact and an actionable error"), driven by agents as end-to-end tests. Feel (animation, gesture response, whether an interaction reads as right) is genuine human judgment, so it is a review lane, not a checklist: the design owner reviews as an independent reviewer and emits the same verdict contract an agent reviewer emits. A specification that touches look, feel, or flow lists `design_review` in its required evidence, and the change does not merge without that verdict.

On the intake side, design specifications pull exact values from the design tool's API (node identifiers, real dimensions, token references) into the specification. Design intent enters the repository as data, never as a screenshot.

And on the validation side, the rule that governs all testing under Veldo: **if a test can be executed by an agent, a human executing it is a defect in the setup.** Agents write the tests, run them, and interpret failures; humans judge delivered evidence. UI proof is four layers in strict order of importance: **flows first** (every named journey driven end to end by the agent, happy path and failure path, with behavior asserted at each step: navigation, state transitions, data effects, focus), then **states** (every named state reached by driving, captured, and asserted on content and accessibility), then **interaction detail** (keyboard, gestures, timing: asserted where assertable, recorded where not), and only then **visual fidelity** (the token lint, the composites, the baselines - the layer humans judge as pictures). A UI with perfect screenshots and unproven flows is unproven. For the web, the agent drives the browser across the spec's widths. For mobile, historically the weakest AI-tested surface and therefore treated as first-class: the agent drives the emulator itself - boots the spec-declared device profile, installs the build, walks the flow including the lifecycle events where mobile bugs live (backgrounding, process death mid-flow, rotation, network loss), captures every named state, and records the interaction as video, across the device matrix the spec declares. The visual pipeline closes the loop for any design-lane change: the design tool's frame exported via its API, the rendered capture, and a side-by-side composite with a pixel-diff strip, written to `proof/<spec-id>/visual/` and DELIVERED to the judging human where they live (chat); the one-line reply becomes the baseline approval or the design verdict, and the composite stays on the record as evidence. UI and mobile specs name this machinery in their evidence: `required_evidence: [unit, journeys, ui_states, interaction_recording, figma_composite]`, plus `device_matrix` for mobile; `journeys` is the load-bearing entry. Where risk genuinely demands physical devices (payments, camera, biometrics), the spec says so and a human lane covers exactly that named residue.

### 8.2 Intake

Work arrives from people who will never open a repository: bug reports, support escalations, crash alerts, feature requests. Two rules make intake work.

First, the tracker keeps exactly two roles: **intake**, where reporters report in their own words, and **mirror**, an automatically synced, effectively read-only view of status for those same people. It is never the definition of work and never the source of truth, and nobody updates it by hand for Veldo work; lifecycle events update it.

Second, nobody writes specification files by hand, engineers included. Converting a report into a specification is agent work:

1. A report lands: a tracker ticket, a support thread, a crash alert.
2. The intake agent deduplicates it against known issues and open specifications.
3. It attempts to **reproduce**. A bug's first acceptance criterion is its reproduction: the specification ships with a failing test that demonstrates the reported behavior, which must pass after the change, with no regressions around it.
4. It drafts the specification, links the ticket, and the ticket's status flows automatically from then on: ready, in progress, shipped, with a closing comment naming the fix version.
5. When it cannot reproduce, it asks the reporter clarifying questions in the ticket's comments. Triage is a conversation the agent runs in the tool where the reporter already lives.

The intake agent runs with implementation-grade tools in a scratch workspace, because building a reproduction is implementation work. And one hard exception: reports touching security or personal data skip the pipeline and route directly to a human; automation resumes after judgment.

Crash and error telemetry enters the same pipeline and is even more automatable: stack trace in, reproduction attempt, specification out. Recurring report classes get standing specifications like any other recurring change class.

### 8.3 Documentation

Documentation splits by what it governs, not by where people prefer to write.

| Class | Examples | Home | Written by |
|---|---|---|---|
| Engineering truth | Architecture, decisions, runbooks, API contracts, agent instructions | Repository | Agents, as part of every change |
| Human knowledge | Plans, meeting notes, product thinking, brainstorms | Knowledge tool (wiki) | Humans, freely |
| Published views | Doc sites, PDFs, customer documentation | Generated from the repository | The render pipeline |

Engineering truth lives in the repository without exception, because agents need it to build correctly. But humans do not hand-write it: the agent that changes behavior updates the documentation in the same change, and the steward prunes what goes stale. A human who finds a wrong document states one sentence of intent ("this document is wrong about X"), and the loop fixes it like any other change.

Human knowledge lives in the knowledge tool, and that is correct, not a compromise. One law keeps the boundary clean: **nothing an agent needs to build or operate the system may live only in the knowledge tool.** The wiki is where humans think together; the moment a durable engineering decision lands there, an agent moves it into the repository. Decisions flow in.

Published views flow out: human-readable sites, PDFs, and reference pages are generated from the repository, so they cannot drift from shipped behavior, and documentation examples can run in the gate like any other check. The steward's job includes flagging wiki pages that have quietly become load-bearing.

The rule of thumb: the knowledge tool for conversation, the repository for anything a machine or an engineer acts on, generation for anything published.

## 9. Production support: what ships, and what you must turn on yourself

The engine lays down a production support organ. **It arrives inert, and that is deliberate.** What
you get on install is the contracts, the responder loop, the action whitelist, the executor and the
checks. What you do not get is any connection to a real system. Nothing reads your logs, nothing
holds a credential, and nothing can execute anything, until a person configures it. This section is
about that person's work.

Read section 7 first if you have not: the governance and kill-switch machinery described there is
what this organ is bounded by, and none of what follows is safe without it.

### What arrives on install

| Piece | Home | State on install |
|---|---|---|
| Incident and remediation contracts | `.veldo/incident.py` | active, validated by the gate |
| Read-only evidence plane | `.veldo/evidence.py` | present, **no sources configured** |
| Responder loop | `.veldo/responder.py` | present, **structurally has no execution tool** |
| Action whitelist | `.veldo/action.py` | present, **empty** |
| Action executor | `.veldo/action_executor.py` | present, **refuses everything, nothing whitelisted** |
| Two-key rule | `.veldo/two_key.py` | active |
| Support numbers | `.veldo/metrics_support.py` | active, reports zero |

An empty whitelist is a working configuration, not an unfinished one. A repository that adopts the
method and never turns any of this on is in a supported, sensible state: it has the incident record
and the numbers, and no machine anywhere near its production systems.

### Going live is a separate, human-performed act

**Do not do this on adoption day.** Turning the organ on against real systems is a change to who and
what can touch production, and it deserves its own decision record, its own risk classification and
its own approval. Four steps, in this order, because each one is safe only if the one before it is
done:

1. **Declare the evidence sources, read-only.** Point the evidence plane at logs, metrics, traces
   and whatever else the responder should reason over. Use credentials that cannot write. Verify the
   credential seam refuses a write rather than trusting the configuration: the conformance suite
   drives exactly this and it is the check worth running first.
2. **Declare the redaction seam.** Whatever must never enter an agent's context - secrets,
   customer data, anything regulated - is redacted at the plane, not filtered later. A context that
   never held the data cannot leak it.
3. **Write the whitelist.** Each runbook action declared in advance with its parameters, its blast
   radius, its reversibility and whether it requires a canary. Start with the reversible ones. An
   action that is not written down is not available during an incident, which is the point.
4. **Grant execution last, and narrowly.** Only after the three above, and only with per-action,
   short-lived, least-privilege credentials. Anything irreversible or data-mutating requires two
   keys; do not configure a path around that because an incident felt urgent. The urgency is exactly
   when the rule earns its keep.

### What to watch after it is live

The support numbers come off the same event trail as everything else, so they are measured rather
than reported. Watch time-to-diagnosis and time-to-remediation, and watch the refusal counts: a
responder that never proposes anything and an executor that refuses everything both look like calm
and are usually a misconfiguration. A recurring incident is a signal about the system, not about the
responder, and the reconciliation trail is what makes the recurrence visible at all.

## 10. Substrate and release: what ships, and what you must wire yourself

The engine lays down the substrate machinery: declarations and their validator, the plan-then-apply
change type, the cost projection, the destructive floor, the promotion pipeline, the drift
comparator and the ephemeral environment seam. **Every one of them decides. None of them acts.**
The shipped adapters are fakes that record what they were asked to do, and nothing here holds a
credential or opens a connection.

**A repository that declares no substrate is untouched by all of it.** An empty declaration set
produces an empty plan, an empty plan is a success rather than an error, and no gate stage runs any
of this. Adopting the method does not opt you into managing your infrastructure.

### What arrives on install

| Piece | Home | State on install |
|---|---|---|
| Declarations and validator | `.veldo/substrate.py` | active; validates what you write |
| Plan and apply | `.veldo/substrate_change.py` | active, **adapter is a fake that does nothing** |
| Cost projection | `.veldo/substrate_cost.py` | active, **declared price table, no pricing API** |
| Destructive floor | `.veldo/substrate_floor.py` | active; keys judged by the shipped two-key module |
| Promotion pipeline | `.veldo/substrate_promote.py` | active; decides only |
| Drift comparator | `.veldo/substrate_drift.py` | active, **snapshot is an argument you supply** |
| Ephemeral environments | `.veldo/substrate_ephemeral.py` | active, **fake provider** |

### Going live is a separate, human-performed act

**Do not do this on adoption day**, and do not do it in the same change as anything else. Wiring a
real adapter gives a machine the ability to alter running infrastructure, which is a change to who
can touch production and deserves its own decision record, risk classification and approval.

1. **Write the declarations first and let them be wrong.** Declare an environment, run the
   validator, fix what it refuses. Do this before any adapter exists, so the first time a real
   adapter runs it is against a declaration somebody has already read.
2. **Wire the drift comparator before the applier.** Supply a real snapshot and look at what it
   reports. Drift you did not know about is the normal first result, and finding it with a
   read-only tool is considerably better than finding it with an apply.
3. **Wire the applier for one non-production environment.** Prove plan-then-apply, prove the stale
   plan refusal by deliberately changing the declaration between plan and apply, and prove teardown
   leaves no residue against your real provider rather than against the fake.
4. **Set the budgets and price the resource kinds you actually use.** An unpriced kind refuses, and
   that refusal is correct: it means the check cannot yet protect you.
5. **Only then, production, and only through the promotion pipeline.** By this point the rollback
   plan, the canary and the destructive floor are the things standing between an ordinary Tuesday
   and an outage, so do not route around them because the first real promotion feels slow.

### What to watch afterwards

Drift findings that keep reappearing mean the declaration is wrong, not that the tool is noisy.
Ephemeral environments reported as leaked mean your provider is leaving residue and the number will
grow quietly. And an unpriced-resource refusal is a prompt to price the kind, never a prompt to
remove the check.

## 11. Security by design: what ships, and what you must turn on yourself

The engine lays down the security machinery: the secret reference seam, the absolute scan, the
context redaction seam, per-task credential issuance, untrusted-input fencing, supply-chain policy,
the generated-privilege floor, commit signing and attribution policy, the security review dimension,
and the inventory tool. **Almost all of them decide. Two of them need you to wire something real.**

**A repository that adopts none of it is untouched.** No check here blocks a verdict that does not
declare the dimension, the inventory is advisory until you declare otherwise, and nothing holds a
credential or opens a connection on install.

### What arrives on install

| Piece | Home | State on install |
|---|---|---|
| Secret reference seam | `.veldo/secretref.py` | active, **resolver is yours to wire** |
| Absolute secret scan | `.veldo/secret_scan.py` | active; pattern plus entropy, **no allowlist by design** |
| Context redaction seam | `.veldo/context_redaction.py` | active; fails closed on a chunk it cannot make safe |
| Per-task credentials | `.veldo/credential_issue.py` | active, **issuer is a fake that mints nothing** |
| Untrusted-input fencing | `.veldo/untrusted_input.py` | active across seven declared seams |
| Supply-chain policy | `.veldo/supply_chain.py` | active; DEC- record where you have one, a written reason where you do not |
| Generated-privilege floor | `.veldo/generated_privilege.py` | active; **per-stack analyser slot is yours** |
| Commit signing and attribution | `.veldo/commit_attribution.py` | active, **signer registry is yours to declare** |
| Security review dimension | `.veldo/security_review.py` | active, **reviewer seam RAISES until wired** |
| Inventory and migration | `.veldo/secret_inventory.py`, `scripts/secret_inventory.py` | active; **advisory until you declare enforcing** |

**`.veldo/capabilities.yaml` is the machine-readable truth** for exactly what is mechanical, what is a fail-loud reference seam awaiting per-repo wiring, and what is advisory; this section defers to it, and the Plugin Guide section 14 is the component reference.

### The two that need real wiring

**The secret resolver.** The seam returns a reference and resolves at use. Until you point it at
your vault, environment loader or cloud secret manager, it resolves nothing. Wire this before you
wire anything else, because every other piece assumes a value has a name.

**The security reviewer.** The reference implementation raises rather than fabricate a judgment,
which is deliberate: a fabricated "looks fine" is indistinguishable in the record from a real
review, and it is what somebody points at later to show the change was checked. Wire a genuinely
fresh context over the built change, or leave the dimension off entirely. Do not wire something that
returns `secure`.

### Migrating an existing repository

**Do not flip to fail-closed on adoption day.** You do not yet know what is in your history.

1. **Run the inventory and read it.** `python3 scripts/secret_inventory.py` scans the working tree
   and every reachable blob. Expect a large number, and expect most of it to be entropy noise -
   entropy is advisory here precisely because it is noisy at repository scale.
2. **Triage the pattern findings, which are the ones that gate.** In practice these collapse to a
   handful of distinct lines; this repository's own run reduced roughly nine hundred findings to
   twenty-two lines. Read the lines, not the count.
3. **Disposition each one by digest, with a written reason.** A disposition covers one
   byte-identical line, never a path and never a pattern, so a real credential dropped in later
   inherits nothing. Put the record under `protected_paths` before it gates anything.
4. **Rotate anything real that was reachable in history, and rotate it yourself.** Deleting the line
   does not un-publish it. The tool names the work and the owner; it issues nothing.
5. **Then declare enforcing, with a date.** The flip is a decision somebody made with the inventory
   in hand. It is refused while anything is outstanding, and once declared it will not silently
   downgrade - going back to advisory needs a written reason, because a gate switched off during an
   incident is one nobody turns back on.

### What to watch afterwards

A rising count of dispositions is a smell: it means fixtures are multiplying or somebody is
dispositioning rather than fixing. An entropy finding that turns out to be real means the pattern
set needs a new detector, not that entropy should start gating. And a security review that has never
returned `insecure` is not evidence that everything was safe - it is evidence worth checking that
the reviewer is actually reading above the floor.

## 12. Anti-patterns

**Truth and state**
1. A tracker, dashboard, or control-plane database becoming the source of truth. The repository wins, always.
2. Dashboard edits that do not become repository commits or ledger records.
3. Durable knowledge living only in conversations or a vector index.
4. Restoring derived indexes as if they were truth instead of rebuilding them from primary records.

**Proof**
5. A green summary without criterion-level evidence.
6. Expiring CI artifacts as the durable evidence store.
7. Weakening or deleting tests to make a gate pass.
8. Tolerating flaky gates; flakiness converts the whole team to bypass culture.
9. Skipping the proof contract "for now"; it is the one thing that must exist on day one.

**Review**
10. The implementer approving its own work, at any scale, in any form.
11. Handing the reviewer the implementer's narrative instead of the spec, diff, proof, and instructions.
12. Lowering reviewer model strength to cut cost on high-risk changes.

**Approval**
13. Approval by chat message, email, or an unstructured PR comment.
14. Approving a moving target: any change to commit, proof, verdict, policy, or plan invalidates approval.
15. Routine human approval queues on reversible low-risk changes.
16. Policy exceptions without a durable exception record naming owner, scope, reason, and expiry.

**Architecture**
17. A database as a message bus, or polling to detect changes.
18. Building the platform before the workflow is proven in one repository.
19. A capability reachable only through a human UI.
20. Designing to today's scale; the contract is the problem-class boundary, design there.
21. Coupling the system to a single model or vendor.

**Agents and security**
22. Broad cloud credentials in an agent's hands instead of narrow capability APIs.
23. Secrets in prompts, instructions, transcripts, or proof artifacts.
24. One monolithic autonomous agent with unrestricted tools instead of separated roles with bounded jobs.
25. Untrusted code executing with privileged secrets.
26. Silently changing models, prompts, policies, or toolchains without pinning and evaluation.

**Economics and process**
27. Optimizing activity metrics (tokens, commits, PR counts) instead of cost per proven change and proof latency.
28. Oversized specifications and long-lived branches, then adding project management instead of cutting scope.
29. Batching unrelated specifications into one change.

**Weight**
30. Process heavier than the work it governs: when the ceremony around a change costs more than the change, the system is in its own way.
31. Importing regulated-industry controls (signing, hash chains, legal hold, formal recovery objectives) into an ordinary software team because they look rigorous. Rigor is proof and review; the rest is weight.
32. Building any control-plane component before its absence is a measured bottleneck.
33. And the inverse failure: skipping Veldo for "tiny" changes. Small changes still cause defects; the answer is proportionate proof, never absent proof. The proportionality rule cuts ceremony, not evidence.

## 13. Adoption path

### 10.1 Choose the pilot repository

One repository, two weeks. Pick a representative production service: active delivery, a build that can be made deterministic, mostly reversible changes, at least one protected path to exercise the approval flow, and an observable deploy. Not the easiest docs repository, and not the most critical system you run.

### 10.2 The two-week pilot

**Days 1-2: repository clarity.** Write `CLAUDE.md` and `VELDO.md`. Document build, test, verify, deploy, and rollback commands. Delete contradictory instructions. Record the baseline: current merge latency, defect rate, rollback time. Exit when a fresh Claude Code session can build, test, and describe the repository's constraints with no human explanation.

**Days 3-4: contracts and specifications.** Commit the seven schemas, validators, and golden fixtures. Convert the next three real changes into specifications with testable acceptance criteria and declared risk. Generate the index. Exit when every active change has a valid specification and the validator rejects a deliberately bad one.

**Days 5-6: the canonical gate.** Create or repair `./scripts/verify.sh` covering format, lint, types, tests, build, and secret scan. Quarantine flaky tests as defects. Produce the first proof manifests; store evidence with digests; start appending lifecycle events. Exit when the same command passes locally and in clean CI and a manifest validates.

**Days 7-8: first full Veldo changes.** Run two or three specifications end to end: implement with the subagent roles, gate, proof, and the standing hooks active. Exit when the unit of delivery is visibly spec plus implementation plus evidence, and a hook has actually blocked at least one premature completion.

**Day 9: independent review.** Add the reviewer subagent on a different model and the headless CI invocation with schema-enforced verdicts. Exit when a fresh-context review has produced a real finding or a defensible pass, and the verdict is bound to the exact commit.

**Day 10: merge policy and the protected path.** Encode the policy file; enable auto-merge on green for reversible changes; wire CODEOWNERS; run one protected-path change through a digest-bound approval record, and test that a commit change invalidates it. Exit when a green reversible change merges with no human in the loop and a protected change cannot merge without a valid approval.

Run the pilot on real, bounded changes, not synthetic demos: idempotency on a retry path in a payments service, a tightened authorization check, a new filter on a search API.

### 10.3 Pilot exit criteria

Stay in one repository until: ten or more representative changes have used the full lifecycle; every merged change has a proof manifest and an independent verdict; auto-merge works and protected changes fail closed; at least one deliberately invalid change (unproven, or with a stale approval) was mechanically blocked, because a gate you have never seen refuse anything is not yet a gate; a rollback has been exercised; specification-to-production time and proof latency are being measured from events; and the team can name the current bottleneck from data. Expand because the workflow is reliable, not because it is popular.

### 10.4 Roll out in waves

One repository, then two to five in the same domain, then a product area, then the organization. Each wave gets a named owner, the versioned plugin and contracts, real changes through the full lifecycle before the next wave starts, and the removal of whatever approval queue or status ritual the wave replaces. Onboarding is a bootstrap command that opens a reviewable change adding schemas, instructions, verify adapters, and policy references. No permanent parallel sources of truth: the old tracker becomes a read-only mirror or it becomes the enemy.

The waves map onto the method's adoption phases directly: repository clarity (phase 1) is days 1-2 of each wave, specification discipline (phase 2) is days 3-4, canonical verification (phase 3) days 5-6, independent review (phase 4) day 9, automatic merge (phase 5) day 10, and continuous improvement (phase 6) is the standing state that follows.

## 14. North star

The destination is a system where the only human work is stating intent and exercising judgment; where everything between intent and production is built and proven by machines; where every merge is the deterministic consequence of evidence evaluated under versioned policy; and where the full history of what was intended, built, proven, reviewed, approved, and observed reconstructs from primary records alone.

You get there by fixing the contracts first and hardening implementations behind them for years. You never get there by shortcutting proof. Veldo is fast because it can prove what it is doing. This setup exists to make that proof cheap, mechanical, and permanent, at every scale you will ever reach.

## Document History

Minor versions add, clarify, or extend; major versions restructure or break compatibility with existing practice.

| Version | Date | Changes |
|---|---|---|
| 1.0-1.1 | 2026-07-16 | Original version, superseded by the 2.0 rewrite |
| 2.0 | 2026-07-16 | Full rewrite: the proportionality rule, seven contracts, the independence ladder, rebalanced control plane, day-blocked pilot |
| 2.1 | 2026-07-16 | Sync with method v1.1: the emergency lane in policy, proof freshness and the merge queue, standing specifications, the weekly index pass, human-minutes events |
| 2.2 | 2026-07-16 | New section 8, The edges: design, intake, and documentation; document versioning and the PDF map |
| 2.3 | 2026-07-16 | Revalidation fixes from an independent hostile review: evidence-commit convention and spec-digest binding documented, digest construction defined, human verdicts representable, panel recording, hook-coverage honesty and matcher fix, json-schema usage corrected, events-log churn policy, pilot versus build-order reconciliation, design tolerances, intake security exception |
| 2.4 | 2026-07-16 | /veldo:run and /veldo:status join the skill set |
| 2.5 | 2026-07-16 | Agent-driven testing made first-class in the design edge: the agents-test-humans-judge-pictures rule, agent-driven mobile emulator testing, the visual pipeline with delivered composites, the UI/mobile evidence contract |
| 2.6 | 2026-07-16 | UI proof restructured as four flow-led layers; journeys added to the evidence contract |
| 2.7 | 2026-07-16 | Honesty pass from the conformance audit: mechanical versus procedural versus target behavior labeled; the capability manifest referenced as generated truth |
| 2.8 | 2026-07-16 | Cross-vendor review (L3/L4) made an explicitly optional, recorded budget decision; L2 is the working default at every tier |
| 2.9 | 2026-07-16 | The planning layer documented as it shipped: section 3.9 (the Product Plan contract, its validator rules, the lane fields), section 4.10 (operating the layer - the /veldo:plan sub-verbs and the plan.py mechanical verbs, run enforcement, regression at the gate, status and release), /veldo:plan added to the 4.3 skill list, and the Product Plan acknowledged in 2.3 as the contract above the per-change seven |
| 2.10 | 2026-07-19 | The fleet and the two-tier adoption model (W6 of PLAN-0009): the capability-by-scale table (2.4) gains parallel workers, fleet accounts and the governor, and the work CLI and run lens; section 4.9 states the two-tier adoption model (a pack lays the full engine including the fleet; /veldo:init lays the minimal governance substrate by design); new section 4.11 documents the fleet, the veldo CLI, the account model, the token governor, and the in-session, no-detached-process boundary, tied to the capability-by-scale framing |
| 2.11 | 2026-07-22 | The architecture organ (VELDO-1110 of PLAN-0011, plugin 3.7.0): new section 7.8 documents the shape as a per-repo, human-approved contract the gate enforces - the mechanizable-versus-review split (honest that only the module-size budget and the engine invariants are gate-blocking, while dependency boundaries, function-length, duplication, complexity, and prose patterns are review-lane reference implementations), placement before build and shape-fit at review, foundational decision records with adversarial fresh-context review and in-session assumption tripwires, the entropy-to-restoration loop, and the adoption-safe, per-repo, nothing-detached postures; deferring to the capability manifest for what is mechanical, what is a fail-loud reference seam awaiting per-repo reviewer wiring, and what is advisory |
| 2.12 | 2026-08-03 | Security by design (VELDO-1311 of PLAN-0013, plugin 3.10.0): new section 11 documents what ships and what an adopter must turn on - the install-state table for all ten modules, the two that need real wiring (the secret resolver and the security reviewer, with the explicit instruction not to wire a reviewer that returns secure), the five-step migration for an existing repository (inventory, triage the pattern findings, disposition by digest with a reason, rotate what was reachable in history yourself, then declare enforcing with a date), and what to watch afterwards; sections 11 through 13 renumbered to 12 through 14 |
