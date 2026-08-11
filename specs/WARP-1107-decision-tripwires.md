---
schema: veldo.spec/v1
id: WARP-1107
title: Decision tripwires, monitored in-session - the recorded-readings format, the pure in-session evaluator, its three surfaces (gate output, veldo status, the weekly pass), and the fired-breach re-decision draft (W7 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W7
plan_revision: 2
depends_on: [WARP-1105]
protected_paths: []
placement: [contracts, loop]
footprint:
  - .veldo/tripwire.py
  - .veldo/validate.py
  - .veldo/runstatus.py
  - .veldo/status_server.py
  - .veldo/capabilities.yaml
  - .veldo/init_scaffold.py
  - .veldo/examples/readings-example.yaml
  - engine/.veldo/tripwire.py
  - engine/.veldo/validate.py
  - engine/.veldo/runstatus.py
  - engine/.veldo/status_server.py
  - engine/.veldo/capabilities.yaml
  - engine/.veldo/examples/readings-example.yaml
  - packs/*/.veldo/tripwire.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/runstatus.py
  - packs/*/.veldo/status_server.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1107-decision-tripwires.md
acceptance_criteria:
  - id: AC1
    text: >
      A versioned recorded-readings artifact format (schema veldo.readings/v1) exists,
      homed as per-repo instance data under .veldo/readings/*.yaml, a directory the
      engine glob does not sweep, so readings stay per-repo like the decision records
      they measure and are never shipped in the engine. A readings file binds to a
      decision record (a decision id) and records, for one or more of that decision's
      assumptions, the latest IN-SESSION measurement in one of the two shapes D3 names:
      a MEASURED reading (kind: measured, a value and a machine-comparable breach_when
      condition operationalizing the assumption's prose breach, an optional
      approaching_when early-warning, and an at timestamp) or a MANUAL-REVIEW reading
      (kind: manual_review, a reviewed_at, a valid_days expiry window, a holds boolean,
      and an at timestamp). A clearly-marked illustrative example ships at
      .veldo/examples/readings-example.yaml recording healthy readings for the shipped
      decision-example (DEC-0000) and validates clean via python3 .veldo/validate.py
      tripwires .veldo/examples/readings-example.yaml; a selftest asserts the example is
      present, names DEC-0000, and fires no tripwire.
  - id: AC2
    text: >
      An evaluator (.veldo/tripwire.py, invoked by .veldo/validate.py) that, given a
      decision record and its readings, determines for EACH assumption whether its
      breach condition is met and reports the fired tripwires. For a measured reading it
      mechanically parses breach_when (a comparator from >=, <=, >, <, ==, != and a
      threshold) and compares the recorded value; for a manual-review reading it
      computes whether the review has lapsed against valid_days at the injected
      in-session date. It FAILS CLOSED by name on a malformed readings set: a wrong
      schema, a reading with no assumption id or an assumption the decision does not
      declare (referenced but absent), an out-of-vocabulary kind, a measured reading
      missing its value or its breach_when or carrying an unparseable comparator, a
      manual-review reading missing reviewed_at, valid_days, or holds, a non-positive
      valid_days, and a file outside the parser subset. It reuses validate.parse_yamlish
      (no second parser) and the validate.fail reporter (no import cycle). Each failure
      class is proven by a negative selftest that refuses, and a well-formed readings set
      evaluates clean.
  - id: AC3
    text: >
      IN-SESSION ONLY, no daemon. The evaluation is a PURE function invoked in-session
      that reads the recorded-readings source (files the session updates) and compares
      each assumption's signal against its breach; it takes the current date as an
      INJECTED parameter (deterministic and testable) and performs no background polling.
      .veldo/tripwire.py imports and contains NO process- or thread-spawning machinery: a
      selftest tooth proves the module source contains none of subprocess, Popen,
      os.fork, os.exec, os.spawn, os.system, setsid, nohup, start_new_session,
      multiprocessing, threading, asyncio, sched, or a background "claude -p" (mirroring
      WARP-1010's _no_detached_worker_spawn), and MUTATION teeth that inject a detached
      spawn into a copy of the source turn that check RED and revert byte-identical. It
      runs only where the gate (validate.py run_all), veldo status (the loop-area runstatus
      reader, over the allow-listed loop -> contracts edge), the tripwires CLI mode, and the
      weekly pass invoke it; every one of those invokers reads recorded files and starts
      nothing, so nothing outlives the session (NG1, feedback_no_rogue_processes, the
      contract invariant no_detached_processes).
  - id: AC4
    text: >
      A fired tripwire surfaces the breached assumption for human attention in ALL THREE
      surfaces PLAN-0011 W7 names, and hands to the re-decision loop. A breached measured
      reading or a lapsed manual-review is surfaced as a NAMED finding naming the decision,
      the assumption, and the breach in each of: (1) the GATE OUTPUT (check_tripwires in
      validate.py run_all FAILS CLOSED so a breached foundation refuses - the anti-vacuity
      C1 teeth); (2) VELDO STATUS (the loop-area runstatus reader projects the SAME
      evaluation through validate.tripwire_status over the allow-listed loop -> contracts
      dependency edge, so veldo status and veldo status --serve show a fired tripwire as a
      named finding, read-only and starting nothing); and (3) the WEEKLY PASS (the tripwires
      CLI run in-session, which also drafts the re-decision). An approaching-breach or an
      assumption with no reading surfaces as a warning WITHOUT failing (there is still time
      to re-decide deliberately). Only a DECIDED decision is monitored (a draft has no chosen
      foundation to watch). A fired tripwire hands to the re-decision loop: draft_redecisions
      writes exactly ONE veldo.redecision/v1 DRAFT per breached decision (naming the decision
      and its breached assumptions) that only a HUMAN promotes (NG2 - the machine drafts,
      never decides, never re-platforms), homed per-repo under .veldo/redecisions/, and it is
      IDEMPOTENT (re-running the pass never drafts a duplicate). The ENTROPY restoration-spec
      generation for the decay class (WARP-1109, W9) is honestly OUT OF SCOPE here and is
      only referenced. The fired finding in the gate output AND in the veldo-status model and
      render, and the idempotent single draft, are asserted over a temporary tree in the
      selftest (the RJ5 tripwire-conformance journey).
  - id: AC5
    text: >
      Adoption safe, teeth, byte-identical sync, honest capability, no protected path. An
      absent .veldo/decisions/ directory (or a decisions set with no decided record, or no
      .veldo/readings/ directory) stands down: a repository without decision records is
      byte-identically unaffected by the pass (verified over a temporary tree). The check
      has TEETH proven by mutation over this repository's shipped readings-example.yaml
      (the anti-vacuity rule C1): flipping a measured reading's value past its breach_when
      turns the evaluation RED, and each mutation reverts byte-identical; over a temporary
      tree a seeded breach fires and drafts exactly one re-decision unit while a second run
      drafts none, and the veldo-status model surfaces the fired tripwire as a named finding
      (removing the runstatus wiring drops it - the anti-vacuity C1 teeth). .veldo/tripwire.py
      ships in the engine and is re-synced byte-identical across engine and all 6
      packs, and .veldo/validate.py, .veldo/runstatus.py, and .veldo/status_server.py (the
      veldo-status surface's loop-area edit) are re-synced likewise, the init scaffold lays
      .veldo/tripwire.py beside .veldo/decision.py, and capabilities.yaml gains one honest
      mechanical entry (decision_tripwires) in every copy (template sync and pack drift pass). The readings and the re-decision drafts are
      per-repo (.veldo/readings/ and .veldo/redecisions/, not shipped in the engine), so a
      fresh init stays reading-free and adoption safe. The full gate is GREEN (selftest,
      contracts, generated, docs, secret scan, template sync, pack drift), RULE #1 is clean,
      and no protected path is touched.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one evaluator module (.veldo/tripwire.py), a call to
  it from .veldo/validate.py (a directory pass in run_all, a single-file readings check for
  the example, and a tripwires CLI mode), an init-scaffold substrate entry, one
  capabilities entry, one illustrative example artifact, and a selftest block, all
  re-synced byte-identical across engine and the 6 packs. The tripwire pass stands
  down entirely when no .veldo/decisions/ directory exists, so removing it returns the gate
  to its prior behavior with no migration and nothing to unwind. A repository with no
  decision records (this repository included) is unaffected either way (the adoption-safe
  posture); recorded readings and re-decision drafts are inert per-repo data and keep their
  history.
---

## Intent

This is W7 of PLAN-0011 and the fifth move of the method's "wrong foundations"
invention (Invention #2): a foundational decision's record is a LIVING TRIPWIRE, not
a memo. WARP-1105 shipped the decision RECORD whose every assumption carries a
measurable signal and a stated breach condition; WARP-1106 shipped the adversarial
review that lets a record move to `decided`. This item builds the mechanism that
MONITORS those assumptions inside normal sessions and gate runs and FIRES when an
assumption is breached, so a wrong foundational choice is discovered by ASSUMPTION
BREACH while there is still time to re-decide deliberately, not by an outage months
later (a static ADR never did this). A fired breach surfaces as a named finding and
drafts exactly one re-decision unit for a human to promote; the machine never
re-platforms anything itself.

## Context

- Depends on WARP-1105 (shipped): the decision record at .veldo/decisions/*.yaml
  (veldo.decision/v1) whose assumptions each carry a signal and a breach. This item
  reads a record through decision.py's load_record (the one place a record is parsed)
  and monitors only DECIDED records (a draft has no chosen foundation to watch).
- Resolved decision D3 (tripwire signal sourcing): a small recorded-readings file
  updated in-session at the weekly pass is the default; the manual-review-with-expiry
  shape is supported for assumptions a team prefers to declare that way. This item
  builds both reading shapes (kind: measured and kind: manual_review) under
  .veldo/readings/, homed in a subdirectory so it stays out of the .veldo/*.yaml engine
  glob, exactly as the decision records and reviews are homed.
- The evaluator is modeled on the two shipped siblings (.veldo/decision.py,
  .veldo/decision_review.py): a structural, fail-closed validator over the same
  front-matter subset (validate.parse_yamlish), no second parser, no import cycle;
  tripwire.py receives the parser, the failure reporter, and the decision loader from
  validate.py, which owns them.
- The IN-SESSION-only, no-daemon posture is the heart of W7 and a hard rule of the
  plan (NG1) and of this codebase (feedback_no_rogue_processes, the contract invariant
  no_detached_processes). The evaluator is a pure function that reads recorded files
  and takes the current date as a parameter; it spawns nothing, imports no
  process/thread machinery, and never polls in the background. This mirrors how the
  fleet's worker launch is an in-session dispatch seam that spawns nothing detached
  (WARP-1010's _no_detached_worker_spawn), and the same string-scan-with-mutation teeth
  prove it here.
- The two postures the plan binds everywhere: adoption safe (a repository without a
  .veldo/decisions/ directory is untouched, the pass stands down) and fail closed (the
  moment a decided record with readings exists it is evaluated and a malformed readings
  set or a breached assumption refuses).

## Out of scope

- No entropy restoration. Deriving cost-to-change per contract area and generating a
  restoration SPEC on a threshold crossing (the decay class) is WARP-1108 (W8) and
  WARP-1109 (W9). This item drafts a re-decision unit for a WRONG-FOUNDATION breach
  only; the entropy restoration loop is referenced, never built here.
- No machine decision and no self-promotion (NG2). A fired tripwire drafts a re-decision
  DRAFT a human promotes; it never sets a chosen option, never records a decider, never
  flips a decision, and never re-platforms anything.
- No detached monitor of any kind (NG1). The pass runs only in-session; nothing outlives
  the session, no timer, cron, or daemon is installed. If a standing mechanism is ever
  wanted it is a separate, explicitly human-approved opt-in, off by default, and is not
  part of this item.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy_check.py, .veldo/policy.yaml and their engine twins are untouched
  (protected paths). The tripwire pass and its surfaces live in the non-protected engine
  (.veldo/tripwire.py and .veldo/validate.py in contracts; the veldo-status surface in
  .veldo/runstatus.py and .veldo/status_server.py in loop, which are loop-area engine, not
  protected paths).

## Notes

- Keep the evaluator dependency free and the readings artifact readable (the C3
  proportionality constraint). Follow the byte-identical engine sync discipline:
  .veldo/tripwire.py and the edited .veldo/validate.py and .veldo/capabilities.yaml land in
  engine and every pack byte-identical, and the drift checks end empty. The
  readings and the re-decision drafts are per-repo (like the decision records and
  reviews), and homing them in .veldo/readings/ and .veldo/redecisions/ subdirectories keeps
  them out of the .veldo/*.yaml engine glob structurally, so a fresh /veldo:init repository
  starts reading-free and adoption safe. The illustrative example ships in .veldo/examples
  so an adopter sees the format; it records healthy readings for the DRAFT decision-example
  and fires no tripwire.
- The measured shape carries the machine-comparable breach_when (the operationalized form
  of the assumption's prose breach) alongside the recorded value, so the comparison is a
  genuine mechanical evaluation, not a recorder-set flag echoed back. The manual-review
  shape carries the expiry the team committed to, so a lapsed review fires and forces a
  re-attestation. The current date is injected so the pass is deterministic and testable.
- Put teeth on the check by mutating the shipped example (flip a value past its breach_when)
  and observing the pass go red before reverting, and prove the seeded-breach path over a
  temporary tree (a decided record plus a breaching reading fires and drafts exactly one
  re-decision unit; a second run drafts none). The no-daemon tooth scans the module source
  for spawn tokens and a mutation that injects one turns it red; a mechanical check that
  cannot refuse is exactly the vacuity C1 forbids.
- Honesty (NG5 and the WARP-1101 review lesson): do not mark a rule mechanizable that
  nothing enforces, and reference the entropy restoration loop (W8/W9) as later work rather
  than claim it. This repository ships the readings format, its evaluator, the gate
  surfacing, and the idempotent re-decision draft with a healthy example; it does not
  manufacture a real breached foundation and does not build the entropy side.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
</content>
</invoke>
