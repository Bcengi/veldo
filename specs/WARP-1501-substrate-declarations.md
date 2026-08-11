---
schema: veldo.spec/v1
id: WARP-1501
title: The repository becomes the source of truth for what should be running - a versioned substrate
  declaration whose unknown kinds are refused at contract time, whose relationships must resolve, and
  in which a secret may be named but never held
status: shipped
risk: standard - a new pure validator that provisions nothing, reaches no network, holds no credential
  and runs no process. It is not low because the secret check is the thing standing between a literal
  credential and git history, where a mistake in the permissive direction is permanent.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W1
depends_on: []
placement: [contracts]
footprint:
  - ".veldo/substrate.py"
  - "engine/.veldo/substrate.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1501-substrate-declarations.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      A VERSIONED DECLARATION FORMAT, VALIDATED STRUCTURALLY. One environment, its resources with kinds
      and pinned string versions, their relationships, and per-environment parameters. Required keys
      are enforced, the version must be a positive integer because a declaration is versioned so that
      a diff is a reviewable change, and the environment must be one of the declared four. A selftest
      drives a well-formed declaration to zero problems (the control) and each structural defect to its
      own message.
  - id: AC2
    text: >
      UNKNOWN KINDS ARE REFUSED AT CONTRACT TIME. The vocabulary is declared ONCE in `RESOURCE_KINDS`
      and a kind outside it is a validation failure, not a pass-through, because a declaration that
      validates and means nothing to anything downstream is worse than one that fails. Adding a kind is
      a deliberate contract change. A selftest drives an invented kind to a refusal.
  - id: AC3
    text: >
      SECRETS ARE REFERENCES, NEVER VALUES (C5), AND THE CHECK IS DELIBERATELY OVER-EAGER. Two
      independent tests, because each catches what the other misses: a value SHAPED like a credential
      under any name (long base64, long hex, a known prefix, an inline private key), and ANY non-empty
      value under a name that announces itself as a secret. A pointer such as `ref:`, `vault:` or
      `ssm:` is admitted. The asymmetry is the point and is stated in the module: a false positive
      costs a minute of reshaping, a false negative puts a credential in git history forever, so the
      fix is always to replace the value with a reference and never to add an exemption. A selftest
      drives both detectors and the reference control.
  - id: AC4
    text: >
      RELATIONSHIPS MUST RESOLVE AND NAMES MUST BE UNIQUE. A `depends_on` naming no declared resource
      fails, and two resources sharing a name fail, because a name is how a relationship resolves.
      Catching this at contract time is the difference between a failed validation and a
      half-provisioned environment. Both driven by selftest.
  - id: AC5
    text: >
      IT VALIDATES AND DOES NOT ACT, and reports EVERY problem in one pass. No provisioning, no
      network, no credential, no process - a validator that can also act is one you cannot safely run,
      and provisioning (W7) and drift comparison (W6) are separate items for that reason. It never
      raises and never stops at the first defect, so one run fixes one round rather than N runs fixing
      N. A selftest asserts a declaration with several independent defects reports all of them.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Nothing reads it yet, no gate stage runs it, it writes
  no state and it changes no behaviour.
---

## Outcome

Infrastructure drifts because the thing that should be running lives in somebody's memory and a
console, while the thing that is running lives somewhere else. Declaring it in the repository makes
a change to infrastructure an ordinary spec through the ordinary loop: specified, proven, gated,
merged, with a diff a human can read.

This is the declaration format and the validator that admits it. Everything else in PLAN-0015 -
the infrastructure change type, cost in the proof, the destructive-action floor, promotion, drift
tripwires, ephemeral environments - reads what this defines.

## The three rules, all failing closed

**Unknown kinds are refused.** A kind outside the declared vocabulary is a typo or an invention.
Admitting it means the validator passes something nothing downstream can act on, which is a worse
outcome than a refusal because it is discovered later and further away.

**Secrets are references, never values.** Named, never held. The detector is over-eager on purpose
and the module says so: a false positive costs a minute of reshaping the artifact, a false negative
puts a credential in git history where deleting it does not remove it. The fix for a hit is always
a reference and never an exemption, which is what stops the check rotting into a tunnel.

**Relationships must resolve.** A dependency on a name nothing declares is broken, and the whole
value of finding it here is that the alternative is finding it half way through provisioning.

## Out of scope

- Provisioning anything. W7's ephemeral-environment seam.
- Comparing declared state to actual state. W6's drift tripwires.
- Deciding what may be destroyed. W4's destructive-action floor.
