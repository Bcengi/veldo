---
schema: veldo.spec/v1
id: WARP-1701
title: A blanket grep for the old name would fire on every specification id and the entire proof
  corpus, so the contract enumerates SURFACES and the check is scoped per surface
status: shipped
risk: standard - the module renames nothing and reads no filesystem. It is not low because it is the
  guard the rename in W2 is judged by, and a guard that is wrong in the permissive direction
  certifies a residual name as absent on the day a stranger first clones the repository.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0017
work: W1
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/naming.py"
  - "engine/.veldo/naming.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1701-naming-contract-and-residual-check.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THE CONTRACT COVERS EVERY SURFACE CLASS OR IT REFUSES. All eight are declared - product,
      repository, command, state directory, schema identifiers, plugin, documents, site - and a
      contract missing one is refused by name. A rename that covers seven of eight surfaces is the
      one that leaves the old name somewhere a stranger reads first.
  - id: AC2
    text: >
      A SEEDED REINTRODUCTION IS CAUGHT ON EVERY SURFACE CLASS, one negative test each, with a clean
      control beside it. A check that only proves the tree is clean today proves nothing about the
      tree next month, and what reintroduces a name is a person copying an old snippet, not an
      attacker.
  - id: AC3
    text: >
      WHAT IS DELIBERATELY NOT RENAMED IS RECORDED, NOT INFERRED. Specification ids, the proof
      corpus, document histories and commit messages carry the old name correctly and permanently:
      an id is an immutable reference, evidence records what was true when it was recorded, and a
      rewritten history is a fiction. `NOT_RENAMED` names each with its reason, so a later reader
      does not have to guess whether an omission was a decision.
  - id: AC4
    text: >
      IT REFUSES NOTHING UNTIL THE RENAME HAS HAPPENED. `pre_rename` reports and does not block;
      `post_rename` blocks. The check must exist and have teeth BEFORE the rename it guards, which
      means it must run green against a tree still entirely under the old name - as this one is.
  - id: AC5
    text: >
      MATCHING IS CASE-INSENSITIVE AND A SURFACE NOBODY DECLARED IS A FINDING. `Veldo`, `VELDO` and
      `veldo` are the same name to a reader, and a rename that fixes one casing leaves the other two
      in the README's first paragraph. An item arriving from an undeclared surface is reported as a
      gap in the contract rather than quietly skipped.
  - id: AC6
    text: >
      A MALFORMED CONTRACT NEVER BLOCKS AND ALWAYS REPORTS, so a broken contract can neither arm the
      check by accident nor silently disarm a working one. The module reads no filesystem - paths
      and text are passed in - so it is pure over its inputs and testable against a fake tree.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It renames nothing, reads nothing and is not wired
  into the gate, so there is no behaviour to restore.
---

## Outcome

The rename in W2 has a guard that already has teeth, and the guard is honest about which
occurrences of the old name are supposed to stay.

## The design problem, which is not the obvious one

The obvious implementation searches the tree for the old name. That check is useless here, and
worse, it is useless in the way that gets a check deleted.

The old name appears legitimately all over this repository and must keep appearing. Every
specification id is `VELDO-####`. The proof corpus records evidence under identifiers that were true
when it was recorded. Every document history describes a decision made under the name in force at
the time. A blanket search fires on all of it, produces hundreds of findings, and the first thing
anybody does is switch it off - at which point the real residual, the one in the command name, ships.

So the contract enumerates surface classes and the check is scoped per surface. A surface is
renamed or it is not. Each carries its own rule. And a surface the contract does not name is not
checked, which is a hole with a name rather than an accident.

## Teeth before the rename

This must run green today, against a tree that is entirely under the old name, or it cannot be
built before the thing it guards. Hence the declared posture: `pre_rename` reports, `post_rename`
blocks. Same shape as the secret inventory's posture, for the same reason - a check somebody arms
by accident is as bad as one they disarm by accident.

## What is not renamed, and why that is written down

Four things keep the old name forever: specification ids, because an id is an immutable reference
that everything else cites; the proof corpus, because evidence records what was true when it was
recorded and a renamed schema identifier must not invalidate it; document histories, because
rewriting one makes the history a fiction; and commit messages, which are immutable by
construction.

Each is recorded with its reason. An omission nobody wrote down is indistinguishable from an
oversight, and the person who finds it in six months will assume the latter.
