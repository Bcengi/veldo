# Veldo Operating Rules

This repository runs Veldo. The method: [Veldo Development Method](https://github.com/Bcengi/veldo). This file is the distilled operating contract for any agent or human working here.

## The one rule

> State the intent, let the machine build, require proof, and merge immediately when green.

Every change: `Intent -> Specification -> Implementation -> Proof -> Independent Review -> Merge`. The unit of delivery is specification + implementation + evidence. Code without evidence is incomplete.

## Before making changes

1. Read the repository `CLAUDE.md` and this file.
2. Locate the specification for this work in `specs/`. Do not implement without a specification in `ready` status. Do not implement a `draft`.
3. Read the affected code, tests, and any architecture decisions.
4. Restate the acceptance criteria in operational terms; surface ambiguity before writing code.

## During implementation

- Keep the change limited to the specification. The smallest coherent implementation wins.
- Add tests that demonstrate behavior, not tests that merely execute lines.
- Never weaken existing checks, delete failing tests, or modify acceptance criteria to make a change pass.
- Update documentation in the same change when behavior, interfaces, or operations change.
- If the specification cannot be satisfied safely, stop and record the blocker in the spec.

## Before claiming done

- Run the canonical gate: `./scripts/verify.sh`. Green is the only done.
- Produce a proof manifest in `proof/<spec-id>/manifest.json`: every acceptance criterion mapped to evidence.
- Never claim a check passed without running it. Mark anything not directly proven as an assumption.
- Prepare for independent review: a fresh-context reviewer receives the spec, the final diff, and the proof, never your reasoning narrative.

## Prohibited

- Treating generated code as inherently correct.
- Hiding failed checks or bypassing the gate.
- Expanding scope for convenience.
- Approving your own implementation as the sole reviewer.
- Merging when the trunk has moved without re-running the gate on the merged result.
- Storing durable knowledge only in a conversation. If it matters, it goes in the repository.

## Risk

Risk tiers and protected paths live in `.veldo/policy.yaml`. One law: anything may raise a change's risk; nothing may lower it. Changes touching protected paths require a recorded human approval bound to the exact commit and proof.

**Emergency lane:** when production is failing, fix forward immediately with a human engaged, then backfill the specification, proof, and review within 24 hours. An emergency that recurs is a missing specification.

## Rhythm

One ritual only: a weekly 15-20 minute pass over `specs/index.md`. Close what shipped, kill what went stale, confirm what is ready next.
