---
schema: veldo.spec/v1
id: WARP-0726
title: A ready spec the placement gate refuses is offered by nothing and reported by nothing - withheld() is
  dependency-only, so the frontier's diagnostic half must cover EVERY reason claimable() drops a unit
status: draft
risk: high - this changes what the queue TELLS a reader, and the failure modes are asymmetric. Reporting too
  little is the defect being fixed: an item drops out of both halves of the frontier and the queue looks
  empty rather than broken. Reporting too much is worse than noise, because a report that lists every spec
  every worker cannot claim for capability or scope reasons stops being read at all, and an unread report is
  the same silence with more output. It is high and not critical because no protected path and no safety core
  is touched and the change is to a diagnostic, not to the claim decision; the claim decision itself must be
  byte-unchanged, which is the property the item most needs asserted
owner: dmitry
human_approval: required
lane: standalone
depends_on: [WARP-0724]
placement: [enforcement]
footprint:
  - ".veldo/frontier.py"
  - "engine/.veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "scripts/selftest.py"
  - "specs/WARP-0726-withheld-reports-every-refusal.md"
  - "specs/index.md"
  - "proof/WARP-0726/**"
protected_paths: []
behavior_bearing: false
observability:
  logs: The frontier CLI names every ready build-shaped spec that is not claimable together with the REASON
    it is not, so a queue that is short can be told apart from a queue that is broken without reading code.
  error_taxonomy: A spec withheld for an unmet dependency, a spec refused by the placement gate, and a spec
    with no offer for any reason the tool cannot name are three DIFFERENT lines. The third is required: a
    reason nobody enumerated must print as an unexplained withholding rather than vanish, which is the same
    fail-closed rule the survey's UNDETERMINED default is.
acceptance_criteria:
  - id: AC1
    text: >
      EVERY READY BUILD-SHAPED SPEC IS EITHER OFFERED OR EXPLAINED, and that is asserted as a PARTITION over
      the real corpus rather than as a count. For every ready build-shaped spec, the spec appears in
      claimable() for a worker with every capability, or it appears in the withheld report with a named
      reason. A spec in NEITHER is the defect and the assertion states it as set arithmetic, so the property
      survives the corpus growing.
  - id: AC2
    text: >
      THE PLACEMENT REFUSAL IS ONE OF THE NAMED REASONS, and it is DRIVEN over a fixture spec tree, not read
      off the repository. A fixture ready spec whose footprint crosses an unmodeled area pair with a declared
      risk below the computed floor is refused by claimable() and appears in the withheld report carrying
      arch.placement_gate's own problem text. The reason is not re-derived in the reporter: it comes from the
      same predicate the claim decision asks, so the report cannot drift from the refusal.
  - id: AC3
    text: >
      THE CLAIM DECISION IS BYTE-UNCHANGED. claimable() returns exactly the same units over the repository
      corpus before and after this change, asserted by driving both, because a diagnostic that alters what
      may be claimed is a different item and a far riskier one.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds reasons to a diagnostic report and adds no rule to the claim decision,
  so a revert restores the dependency-only report and nothing that consumes the frontier changes behaviour.
  There is no migration and no state to unwind.
---

## Intent

WARP-0724 shipped the dependency gate and its diagnostic half, `withheld()`, whose docstring states the
principle exactly: "An ordering rule that hides its own effect looks like an empty queue rather than like a
queue that is waiting." Its own risk section then predicted the failure this item exists for: "a legitimately
-ready item permanently unclaimable, which would look like the queue being empty rather than like a bug."

That prediction came true within a day, and not through a dependency cycle. `claimable()` drops a build unit
for FOUR reasons: an unmet declared dependency, a capability mismatch, a scope filter, and a refusal from
`arch.placement_gate`. Only the first is reported. WARP-0716, a landed and legitimately ready item, declared
`placement: [engine]` while its footprint touched `scripts/check_generated.sh` in the ENFORCEMENT area; the
tier floor computed high, the declared risk was standard, and the gate refused the unit. `check_placement` and
`check_spec` both reported ZERO errors, so the gate stayed green. Of thirteen ready specs, seven were
claimable, five were in the withheld report, and exactly one was in neither. Nothing anywhere said so.

The instance was fixed by correcting the false placement. The CLASS is not fixed: the next mis-declared
placement, or any future refusal reason added to `claimable()`, disappears the same way.

## Context

- `withheld()` is dependency-only BY DESIGN and says so. That is not the bug; the bug is that nothing else
  covers the other refusals, so "not in claimable and not in withheld" is a state the tool can reach silently.
- The capability and scope drops are WORKER-RELATIVE and legitimately not the same thing as a withholding: a
  unit no worker can claim is a different report from a unit THIS worker cannot claim. The report must not
  become a list of everything everyone cannot do, or nobody will read it.
- The placement refusal is NOT worker-relative. It is a property of the spec and the contract, exactly like an
  unmet dependency, which is why it belongs in the same report.
- FAIL CLOSED ON THE UNENUMERATED REASON. The point is not to enumerate today's four; it is that a ready
  build-shaped spec with no offer and no named reason must print as an unexplained withholding. Otherwise the
  fifth reason, whenever it is added, reproduces this defect exactly.

## Out of scope

- Any change to what may be CLAIMED. This is the diagnostic half only, and AC3 pins the other half.
- Reporting capability or scope drops, which are worker-relative and would drown the report.
- The plan burn-down's own report, which answers a different question.

## Notes

- Source: an independent review of WARP-0716, 2026-07-29, which found the item invisible and asked whether
  this blindness was itself worth reporting. It is, and this is the report.
- MEASURE FIRST. The partition claim in AC1 must be measured over the real corpus before the sentence is
  written, and it must be stated as set arithmetic and never as a count of claimable or withheld items.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
