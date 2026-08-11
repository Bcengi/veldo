---
schema: veldo.spec/v1
id: WARP-1105
title: The foundational decision record artifact and its validator (W5 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W5
plan_revision: 2
depends_on: []
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A versioned decision-record artifact format (schema veldo.decision/v1) exists,
      homed as per-repo instance data under .veldo/decisions/*.yaml, a directory the
      engine glob does not sweep, so records stay per-repo like the architecture
      contract and are never shipped in the engine. Each record declares the
      decision to make (id, title, problem_class, owner), the option space (a
      non-empty options list, each option with a summary and its dead_end
      condition), the reversal_cost class and the risk tier it maps to, and the
      assumptions that become living tripwires (a non-empty assumptions list, each
      with a measurable signal and a breach condition); a record with no
      assumptions is refused (a memo is not a tripwire). A clearly-marked
      illustrative example ships at .veldo/examples/decision-example.yaml in the
      un-decided (draft) state with no attributed decider, and validates clean via
      python3 .veldo/validate.py decisions .veldo/examples/decision-example.yaml; a
      selftest asserts the example is present and in draft state with no recorded
      decider.
  - id: AC2
    text: >
      A validator (.veldo/decision.py, invoked by .veldo/validate.py) structurally
      checks a decision record the way .veldo/arch.py checks the contract and FAILS
      CLOSED by name on each of: a wrong schema id, a missing or empty required
      field, a non-integer version, an out-of-vocabulary status or reversal_cost
      class or risk tier, an option lacking its dead_end condition, a duplicate
      option id or assumption id within a record, and a file outside the parser
      subset (malformed). It reuses validate.parse_yamlish (no second parser) and
      the validate.fail reporter (no import cycle). Each failure class is proven by
      a negative selftest that refuses, and a well-formed record validates clean.
  - id: AC3
    text: >
      The foundational choice is decided by a HUMAN, on the record, never by the
      machine (O4, NG2). A record whose status is decided but which carries no
      decision block, no decided_by, no decided_at, or no chosen option is refused;
      the chosen option must resolve to a declared option (referenced but absent
      otherwise); a draft needs no decider (draft is the un-decided state, the
      option space before a human commits); and a non-decided record may not smuggle
      a decision block carrying a decider or a chosen option. Scrutiny scales with
      reversal cost through the existing risk tiers (D5): a record whose
      reversal_cost is irreversible but whose risk tier is not critical is refused.
      Both the negatives (decided-without-decider, chosen-does-not-resolve,
      draft-smuggling-a-decider, irreversible-not-critical) and the positives (a
      draft with no decider validates; a fully decided record with a recorded human
      decider validates; an irreversible-and-critical record validates) are asserted
      in the selftest.
  - id: AC4
    text: >
      Adoption safe and fail closed at the directory and the file boundary. An
      absent .veldo/decisions/ directory stands down: a repository without decision
      records is byte-identically unaffected by the scan (verified over a temporary
      tree). A required-but-absent single record fails closed by name, a malformed
      present record fails closed, and a decision id declared by more than one
      record is refused (an ambiguous reference across the set). Each assumption
      carries a measurable signal and a stated breach condition, so the later
      in-session tripwire pass has something to monitor; an assumption missing its
      signal or its breach is refused. Each is proven by a selftest.
  - id: AC5
    text: >
      The check has TEETH proven by mutation over this repository's shipped
      decision-example.yaml (the anti-vacuity rule C1): stripping an option's
      dead_end condition, and flipping the example to status decided without a
      recorded human decider, each turn the check RED. .veldo/decision.py ships in
      the engine and is re-synced byte-identical across engine and all
      packs, .veldo/validate.py's edit is re-synced likewise, the init scaffold lays
      .veldo/decision.py beside .veldo/validate.py, and capabilities.yaml gains one
      honest mechanical entry in every copy (template sync and pack drift pass). The
      decision RECORDS themselves are per-repo (.veldo/decisions/, not shipped in the
      engine), so a fresh init stays record-free and adoption safe; the adversarial
      decision REVIEW is WARP-1106 (W6) and the in-session tripwire MONITORING is
      WARP-1107 (W7), honestly out of scope here. The full gate is GREEN (selftest,
      contracts, generated, docs, secret scan, drift), RULE #1 is clean, and no
      protected path is touched.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one validator module (.veldo/decision.py), a
  call to it from .veldo/validate.py (a directory scan in run_all plus a single-file
  examples check and a decisions CLI mode), an init-scaffold substrate entry, one
  capabilities entry, one illustrative example artifact, and a selftest block;
  nothing consumes decision records for enforcement yet (the first consumers are
  WARP-1106 and WARP-1107), so removing it returns the gate to its prior behavior
  with no migration and nothing to unwind. A repository with no .veldo/decisions/
  directory is unaffected either way (the adoption-safe posture).
---

## Intent

This is the second root of PLAN-0011 and the mechanism behind the method's "wrong
foundations" invention: a foundational choice (technology, architecture style,
communication shape, tooling) becomes a first-class, versioned, human-decided unit
of work, never a side effect discovered inside a feature's implementation. The
record states the decision to make, the OPTION SPACE the machine elaborates with
each option's dead-end condition (where and when it stops working), the
reversal-cost class and the risk tier it maps to, and the assumptions that become
living tripwires. This item builds the RECORD ARTIFACT and its structural
validator; nothing here decides anything, and no machine-decided state is
representable.

## Context

- Resolved decision D5: reversal cost is expressed through the existing risk tiers,
  with irreversible mapping to critical (two independent verdicts plus recorded
  human approval). This item mechanizes the mapping: an irreversible record not at
  the critical tier is refused. The two-verdict scrutiny itself is applied by the
  adversarial review (WARP-1106).
- The validator is modeled on .veldo/arch.py: structural, required-field and
  closed-vocabulary checks over the same front-matter subset (validate.parse_yamlish),
  no second parser, no import cycle. decision.py receives the parser and the failure
  reporter from validate.py, which owns them.
- The two postures the plan binds everywhere: adoption safe (a repository without a
  .veldo/decisions/ directory is untouched, the scan stands down) and fail closed
  (the moment a record exists it is validated and refuses anything malformed).
- Constraint C6 (judged against the problem class): the record carries an explicit
  problem_class field, and "it is only one process today" is never a rationale a
  record may carry. The structural check requires the field's presence; arguing the
  choice against the class rather than the current deployment is the adversarial
  review's job (WARP-1106).

## Out of scope

- No adversarial decision review. Attacking a proposed decision before a human
  decides (what breaks first at ten times the problem class, which future
  requirement the choice precludes, whether the tool is right or merely near) is
  WARP-1106 (W6). This item is the record and its structural validator only.
- No in-session tripwire monitoring. Comparing each assumption's declared signal
  against its current recorded value and surfacing an approaching or reached breach
  as a named finding is WARP-1107 (W7). This item only requires each assumption to
  carry a signal and a breach condition so W7 has something to monitor.
- No elaboration blocking. Making an elaboration that hits an undecided foundational
  choice block and surface the decision is downstream of the review lane and is not
  built here.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy_check.py, .veldo/policy.yaml and their engine twins are
  untouched (protected paths).

## Notes

- Keep the validator dependency free and the artifact readable (the C3
  proportionality constraint). Follow the byte-identical engine sync discipline:
  .veldo/decision.py and the edited .veldo/validate.py and .veldo/capabilities.yaml
  land in engine and every pack byte-identical, and the drift checks end
  empty. The decision RECORDS are per-repo (like architecture.yaml), and homing them
  in a .veldo/decisions/ subdirectory keeps them out of the .veldo/*.yaml engine glob
  structurally, so a fresh /veldo:init repository starts record-free and adoption
  safe. The illustrative example is shipped in .veldo/examples so an adopter sees the
  format; it is a draft with no decider and attributes no decision to any human.
- Put teeth on the check by mutating the shipped example and observing the gate go
  red before reverting; a mechanical check that cannot refuse is exactly the vacuity
  C1 forbids.
- Honesty (NG5 and the WARP-1101 review lesson): do not mark a rule mechanizable
  that nothing enforces, and do NOT record any human as having decided a decision
  they did not make. This repository ships the artifact format and its validator
  with a draft example; it does not manufacture a decided foundational record,
  because a genuinely decided record depends on the adversarial review (WARP-1106)
  that does not exist yet.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
