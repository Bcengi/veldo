# Veldo - agent operating contract

This file is the single, tool-neutral home of the Veldo method and how to work it. Every Veldo
pack (Claude, Cursor, Codex, Copilot, Gemini, OpenCode, Aider) bundles this same AGENTS.md, and
each tool's own instruction file points here, so the method never forks across tools. The full
method is in `docs/method.md`; the machine-readable truth about what is enforced is
`.veldo/capabilities.yaml`. When prose here and the capability manifest disagree, the manifest wins.

## What Veldo is

Veldo is an AI-native software development method. Because AI agents make generating code nearly
free, the bottleneck moved from writing code to verifying it. Veldo puts the investment there: it
spends less effort producing code and far more proving it, and makes the proof machine-checkable
so proving runs at speed.

## The one rule

> State the intent, let the machine build, require proof, and merge immediately when green.

Every change follows the same path:

```
Intent -> Specification -> Implementation -> Proof -> Independent Review -> Merge
```

The unit of delivery is not code alone. It is specification + implementation + evidence. Code
without evidence is incomplete.

## Principles

1. The repository is the operating system. State an agent cannot read, diff, or invoke is not
   reliable operational knowledge.
2. The specification is the unit of work, not the ticket.
3. Humans own intent and judgment. Machines own construction and proof.
4. Verification is the bottleneck. Invest more in the proof system than in raw code generation.
5. Every change carries evidence, proportional to its risk.
6. Independent review requires fresh context, ideally a different model. The writer does not
   approve its own work.
7. Green means merge. Human sign-off is a risk control reserved for the irreversible (money,
   auth, schema, core infrastructure), not a ritual.
8. Changes flow continuously into one trunk. No sprints, points, standups, or release trains.
9. Work stays small and reversible.

## How to work a change (the operating contract)

1. Specification. A change begins as a spec at `specs/VELDO-####-*.md`: acceptance criteria, the
   risk class, the required evidence, and any protected paths. Do not start building until the
   spec is clear. For work larger than one spec, a Product Plan at `plans/PLAN-####-*.md`
   declares a set of specs as a dependency graph.
2. Implementation. Build to the spec. Write mechanical control logic so it can be proven by
   construction; delegate the risky work behind seams and exercise it with tests. Match the
   surrounding code.
3. The gate. Every change must pass one canonical command, `./scripts/verify.sh`: the
   spec/proof/plan contract checks, the self-test, generated-file and template checks, the
   secret scan, the docs hygiene sweeps, and the repo's runners. The gate is fail-closed - an
   undeclared or blank check makes it red. Fix until green.
4. Proof. Record how each acceptance criterion was met and which checks ran in
   `proof/VELDO-####/`, digest-bound to the implementation commit so evidence cannot drift from
   the code.
5. Independent review. A fresh-context reviewer (ideally a different model, never the writer)
   tries to prove the change wrong and records a verdict bound to the commit. A passing verdict
   plus a green gate is what lets a change merge.
6. Land. The proof and verdict land with the change; a spec is not done until its evidence is on
   the trunk and its status is shipped.

## The enforcement invariant (never weaker on any tool)

No change reaches the trunk without a passing commit-bound verdict and, for a change touching a
protected path, a separate human approval whose approver is not the proof producer. This is
enforced by `.veldo/policy_check.py` at push, by a local pre-commit or pre-push hook where the
tool supports one, and always by a git pre-push hook plus the CI required status check as the
universal backstop. A tool with no local hook is still fully enforced by git and CI.

## The board

`specs/index.md`, generated from the specs, is the plan, backlog, and status - a navigation
layer over the specs, not a second source of truth. If the index or any external tracker
disagrees with the repository, the repository wins. Do not recreate a ticket tracker in Markdown.

## Risk and human approval

Classify each change by risk and require human approval only for the irreversible: money, auth,
credentials, schema and data migrations, core infrastructure, and public or outbound surfaces.
Everything else merges on green plus a passing independent verdict. Protected paths are declared
per spec and enforced at push.

## Where to go deeper

- `docs/method.md` - the full Veldo Development Method.
- `docs/setup.md` - setting up and running Veldo, and scaling it.
- `.veldo/capabilities.yaml` - what is mechanically enforced, what is a wired reference, and what
  is agent-instructed procedure. This manifest is the authority; documentation defers to it.
