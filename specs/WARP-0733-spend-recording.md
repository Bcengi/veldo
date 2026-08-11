---
schema: veldo.spec/v1
id: WARP-0733
title: The emitter Tokens of Effort was waiting for - a token count is not knowable from inside a
  repository, so spend is a record the agent makes about itself at ship, with its provenance stated
status: shipped
risk: standard - a new recorder that appends one event type the vocabulary already declares, through
  the existing single writer. It adds no gate condition and blocks no work. It is not low because it
  writes to an APPEND-ONLY log, where a wrong record cannot be withdrawn, and because the number it
  writes is what every later estimator would learn from.
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-1401]
placement: [metrics]
footprint:
  - ".veldo/spend.py"
  - "engine/.veldo/spend.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-0733-spend-recording.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      SPEND IS RECORDED, THROUGH THE ONE WRITER. `record()` appends a `spec.shipped` event carrying
      tokens, cost_usd and human_minutes for a named spec, via `events.emit` rather than opening the
      log itself - a second writer is exactly the defect the event module spent nine rounds closing.
      The emit function is injectable so a selftest drives it without touching the real log. A
      selftest records through an injected emitter and checks the type, the figures and the spec.
  - id: AC2
    text: >
      PROVENANCE IS REQUIRED, because self-reported data with no stated basis is data a later
      analysis will over-trust. `basis` must be one of four declared values - harness_reported,
      agent_estimate, partial_session, reconstructed - and an unknown basis is refused at both the
      function and the CLI. The module states plainly that this is SELF-REPORTED and approximate:
      work spanning sessions, a compaction, or several agents does not sum cleanly.
  - id: AC3
    text: >
      A RECORD CARRYING NO FIGURE IS REFUSED, and this is the AC that protects the whole point of
      WARP-1401. Such a record would set `spend_recorded` true while adding nothing, inflating the
      very coverage number the corpus exists to keep honest - worse than no record at all. At least
      one of tokens, cost_usd or human_minutes is required, and negatives and non-numbers are refused.
  - id: AC4
    text: >
      RECORDING IS NOT A GATE CONDITION, DELIBERATELY. No spec fails to ship because its spend is
      unknown. Turning an estimation convenience into a blocker on real work is the ceremony this
      project exists to avoid, and a gate that blocks on a number the repository cannot derive would
      be unsatisfiable by construction. What is mechanical is the REPORT: `toe_corpus.coverage()`
      shows the gap as a number, so adoption is visible rather than assumed. A selftest asserts no
      gate stage consults this module.
  - id: AC5
    text: >
      IF THE NUMBER STAYS AT ZERO, THAT IS AN ANSWER. The module says so: a coverage that never rises
      means nobody is recording, and the honest response is to drop the estimator layers that need
      actuals rather than to build them on nothing. Stated in the module so a later reader inherits
      the reasoning rather than the machinery alone.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Any records already appended stay, because the log is
  append-only and they remain valid events of a type the vocabulary already declared.
---

## Outcome

WARP-1401 measured that the Tokens of Effort corpus has no spend inputs: 904 events, none carrying
tokens, cost or human minutes, in a system whose envelope has always allowed them and whose readers
have always aggregated them. This is the emitter that was missing.

## Why it is a record and not a derivation

**A token count is not knowable from inside a repository.** The gate cannot see what an agent spent;
that number lives in the harness running the agent. There is nothing to derive it from, so it has to
be a record the agent makes about itself at the moment it ships.

That makes it self-reported, and the module says so rather than letting a reader assume otherwise.
It is not adversarial - an agent has no incentive to misreport its own usage - but it is approximate,
because work spanning several sessions, a compaction, or more than one agent does not sum cleanly.
Hence `basis`, which is required and names how the number was arrived at.

## What is enforced, and what is not

**Recording is not a gate condition.** A spec does not fail to ship because its spend is unknown.
Making an estimation convenience into a blocker would be exactly the ceremony this project exists to
remove, and a gate condition the repository cannot derive would be unsatisfiable by construction.

**The report is mechanical.** `coverage()` shows the gap as a number, so adoption is visible rather
than assumed. **And if that number stays at zero, that is an answer:** it means nobody is recording,
and the honest response is to drop the layers that need actuals, not to pretend.

## Why this is standalone rather than a PLAN-0014 work item

**PLAN-0014's work list does not contain an emitter.** Its W2 slot is already the structural proxy,
and the plan assumed the spend data existed, which is precisely the finding WARP-1401 recorded. So
this cannot be a work item of that plan without renumbering it, and renumbering someone's plan to
make room for a prerequisite it never declared is not a change an implementer should make quietly.

It ships standalone, PLAN-0014 depends on it in fact if not in its front matter, and **the plan
needs a revision to include it** - which is the owner's call, not this item's.

## Out of scope

- Every estimator layer. W3 through W8 wait for data, which is the whole point of doing this first
  and then waiting rather than building nine specs against an empty set.
- Making agents call it. That is adoption, not code, and pretending otherwise would be the
  prose-instructions-do-not-execute failure. What this item guarantees is that the call EXISTS and
  that the gap is measurable; whether it gets used is visible in the coverage number.
