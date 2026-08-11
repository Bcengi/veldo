---
schema: veldo.spec/v1
id: WARP-1206
title: The execution organ - separate, privileged, laddered (W6 of PLAN-0012)
status: shipped
risk: high - the executor is the enforcement core on the execution side and the single most safety-critical organ of PLAN-0012 (C2): a spec touching the executor carries a HIGH risk floor with recorded human approval, so it needs the expanded gate, the L2 independent fresh-context review, and the founder's recorded approval as the landing key, independent of the footprint tier (which is standard - a single contracts area, no boundary crossing; .veldo/action_executor.py is a placeless engine module like the sibling organs). It is HIGH and NOT critical because it builds NO data-mutating execution path - L2 executes only strictly reversible, non-data-mutating whitelisted actions, and anything irreversible or data-mutating REFUSES pending the two-key rule (WARP-1207, W7); C2 reserves the CRITICAL tier for data-mutating execution paths, and none exists here
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0012
work: W6
plan_revision: 2
depends_on: [WARP-1205]
placement: [contracts]
footprint:
  - .veldo/action_executor.py
  - .veldo/capabilities.yaml
  - engine/.veldo/action_executor.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/action_executor.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1206-the-execution-organ.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The executor returns a NAMED refusal per guard through a closed reason taxonomy at each decision
    point - a tripped kill switch, an invalid or stale proposal, a non-whitelisted action, an invalid
    parameter, a below-floor autonomy level, an insufficient level, a disabled or lowest-class-only L3, an
    irreversible or data-mutating action pending two-key, a missing or foreign or self-authorized
    confirmation, an exhausted budget, a timeout, and a failed canary - so an execution refusal is
    diagnosable from the result alone without reading the source (the stranger question, every future
    responder is a stranger to the code).
  error_taxonomy: The refusal reasons are a closed, named set (REFUSE_* constants) - kill_switch_tripped,
    invalid_proposal, action_not_whitelisted, invalid_parameters, below_execution_floor,
    autonomy_level_insufficient, l3_disabled, l3_lowest_class_only, requires_two_key,
    missing_human_confirmation, foreign_confirmation, self_authorization_refused, action_budget_exhausted,
    timeout_exceeded, and canary_failed - each result naming its class and the offending element, so the
    failure mode is legible from the message rather than inferred; a guarded refusal is a named result,
    never a silent no-op or an unnamed exception.
acceptance_criteria:
  - id: AC1
    text: >
      The execution organ (schema veldo.executor/v1, module .veldo/action_executor.py) exists as a SEPARATE
      organ from the VELDO build-loop executor (.veldo/executor.py, WARP-0401): it runs ONLY whitelisted
      actions with validated parameters BOUND TO A PROPOSAL DIGEST, on its OWN credential and code path,
      and SEPARATION IS STRUCTURAL (C4). The executor holds an ExecutorCredential - a DISTINCT type from the
      responder's read-only credential and ReadHandle (WARP-1202), with no query, read, or open_read method
      - so it is not an investigator and shares no credential and no code path with the responder; the
      credential is a secret REFERENCE resolved at the shared D4 seam (evidence.resolve_secret_ref reused,
      never a raw literal, redacted in every string form, C5/D4). It accepts a whitelist action reference
      plus validated parameters, NEVER command text, resolving the action through W5's store
      (action.require_action / action.validate_parameters reused, no second resolver, no second parser) and
      re-validating the proposal through W1 (incident.validate_remedy). A non-whitelisted action refuses
      (action_not_whitelisted, does not exist to the machine path, C4/NG2); a shell-looking reference is
      unresolvable, never run; an empty whitelist means nothing exists to the machine path; an invalid
      parameter refuses by name (invalid_parameters); a proposal smuggling a command field refuses
      (invalid_proposal, W1 proposal-not-execution); and constructing the executor with the responder's
      read-only credential refuses. A selftest proves a POSITIVE CONTROL executes end to end against a fake
      system and drives each structural refusal with the reason named.
  - id: AC2
    text: >
      THE AUTONOMY LADDER (O3, D2) is constructed PER SYSTEM by a human and READ by the executor, which
      NEVER raises its own level (NG4). L0 and L1 are the read-only floor and NEVER execute (below_execution_floor,
      refuse by name), and an unconfigured system defaults to the floor L0 (fail closed). L2 executes only
      provably-REVERSIBLE, non-data-mutating whitelisted actions after an explicit human confirmation, and
      the requested level may not exceed the system's (autonomy_level_insufficient; a non-execution rung
      request refuses; degrade DOWN never up, C3). L3 is DISABLED by default and, per D2, may NEVER be
      enabled - never enabling it is a legitimate permanent state (l3_disabled); and even if a deployment
      ever set it, L3 auto-executes the LOWEST risk class alone (l3_lowest_class_only), so because the
      whitelist carries a high risk floor (W5/C2) no whitelisted action is ever the lowest class and L3
      auto-executes nothing here. The executor exposes NONE of the self-escalation or control-mutation
      methods (no raise-level, enable-l3, edit-whitelist, reset-kill-switch, or set-budget); it reads the
      ladder, whitelist, kill switch, and budget as human-owned controls (NG4). A selftest proves each
      ladder refusal with a positive control, that the executor exposes none of the forbidden mutators, and
      that a subclass ADDING one is detected (the no-escalation check is non-vacuous).
  - id: AC3
    text: >
      ANYTHING IRREVERSIBLE OR DATA-MUTATING REFUSES, PENDING THE TWO-KEY RULE (WARP-1207, W7), and the L2
      human confirmation is BOUND TO THE PROPOSAL DIGEST. proposal_digest is the canonical digest of a
      veldo.remedy/v1 proposal (the validate.proof_digest / action.action_digest idiom applied to the remedy;
      it hashes an already-parsed record and is not a second parser), and W7 imports it from here so the
      binding has one truth. L2 executes ONLY the strictly reversible, non-data-mutating case (checking BOTH
      the action's vetted reversibility from W5 and the remedy's declared one from W1, so a mismatch fails
      closed); a data-mutating action, an irreversible or costly action, and a remedy requiring two_key each
      REFUSE (requires_two_key), so this organ builds NO data-mutating execution path and does not reach the
      critical tier (it is HIGH, not critical, C2). A missing confirmation, a non-confirming decision, a
      machine-authored confirmation (self_authorization_refused, NG4), and a confirmation bound to a
      different proposal digest or a foreign incident (foreign_confirmation) each refuse; a proposal EDITED
      after it was confirmed is STALE and refuses because its digest changed (C3). A selftest proves each
      refusal with a positive control and the digest-binding tooth (an edited proposal goes stale).
  - id: AC4
    text: >
      THE STANDING SAFEGUARDS stand guard on every run, each proven NON-VACUOUSLY (C1). A KILL SWITCH any
      human trips INSTANTLY with no ceremony halts EVERYTHING first (kill_switch_tripped), and resetting it
      requires a RECORDED highest-tier (critical) human approval - a reset without one, or one approved by a
      machine, refuses and the switch stays tripped (D5). An action BUDGET refuses once exhausted
      (action_budget_exhausted); a budget of one executes once then refuses the second (consumed on
      engagement). A TIMEOUT refuses an over-budget run (timeout_exceeded), for the canary and the main
      action alike. CANARY-FIRST where the action declares canary support: the canary demonstrably runs
      BEFORE the main action (the executed sequence and the fake system's ordered op log both read
      [canary, action]), a FAILED canary refuses (canary_failed) WITHOUT running the main action (the op log
      reads [canary] alone - the load-bearing tooth), and an action declaring no canary runs the main
      directly. Everything runs against a FAKE system (NG1): the reference LiveTargetSystem FAILS LOUD and
      the FakeActionSystem is the offline proof, mirroring evidence.LiveEvidencePlane and executor.LiveLoop.
      A selftest proves the kill switch, budget, timeout, and canary-first refusals with positive controls.
  - id: AC5
    text: >
      The organ is IN-SESSION with no detached process (NG3): .veldo/action_executor.py imports pathlib, json,
      and hashlib at module top (json and hashlib for the proposal's own digest) and importlib LAZILY in the
      credential seam and the CLI, starts no process, thread, or timer, and a subprocess.Popen(..., start_new_session=True)
      mutation turns the no-detach check RED. .veldo/action_executor.py and .veldo/capabilities.yaml are re-synced
      BYTE-IDENTICAL across root, engine, and all 6 packs (aider, antigravity, codex, copilot, cursor,
      opencode) by cmp; capabilities.yaml gains ONE honest mechanical entry (action_executor, home
      .veldo/action_executor.py) that names exactly what ships and defers honestly - the two-key rule (WARP-1207,
      W7), the compressed loop (WARP-1208, W8), the support metrics (WARP-1210, W10), and landing an executor
      check into validate.py run_all plus the init lay-down (WARP-1211, W11) - referenced never implied built.
      The full gate is GREEN (selftest, contracts, generated, docs, lint, secret scan, template sync, pack drift,
      shape gate) with ZERO regressions across the whole corpus, RULE #1 is clean (ASCII hyphen only, no em or en
      dash, no prose double-hyphen), and no protected path is touched (verify.sh, veldo-guard.sh, policy.yaml,
      policy_check.py and their engine twins unchanged; validate.py unedited, so gate wiring is honestly
      deferred to W11). Dogfood: placement [contracts] resolves and the footprint tier is standard, yet the spec
      ships at risk HIGH and human_approval REQUIRED because the executor is the enforcement core (C2), so the
      landing is a separate recorded human act and not the builder's.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine module (.veldo/action_executor.py), synced byte-identical across
  engine and the 6 packs, and one capabilities entry, plus a selftest block and this spec. Nothing
  consumes the executor: it is not wired into verify.sh or validate.py run_all (that is WARP-1211, W11), the
  two-key rule it fences off is WARP-1207 (W7), and the compressed loop that would drive it is WARP-1208 (W8),
  so removing it changes no gate behavior and there is no migration and nothing to unwind. A repository that
  never configures the responder is unaffected either way; the executor holds no store, opens no connection, and
  runs nothing against any live system, so reverting is inert.
---

## Intent

This is W6 of PLAN-0012, the execution organ, and the single most safety-critical spec in the plan: the
executor that can actually RUN an action. The design center the plan binds everywhere (from the founder's
framing that production access is existential risk): an agent with production access can destroy a company by
simply doing the wrong thing there, so its safety cannot be a policy it follows, it has to be an architecture it
cannot escape. On the execution side, W5 built the whitelist (anything not in it does not exist to the machine
path); this item builds the organ that consumes an admitted action and runs it, and it is architecture, not
policy: separate credentials and code path, a per-system autonomy ladder whose floor never executes, a human
confirmation bound to the exact proposal, standing safeguards that fail closed, and a hard fence at the two-key
rule so nothing irreversible or data-mutating runs here at all. Everything is proven OFFLINE against fake
systems (NG1); wiring a real target is a separate per-system human-approved enablement act.

## Context

- SEPARATION IS STRUCTURAL (C4), not instructed. The executor is a distinct organ from the VELDO build-loop
  executor (.veldo/executor.py, WARP-0401) - a name collision that is honestly reconciled by giving this organ
  its own module, .veldo/action_executor.py. It runs on its OWN ExecutorCredential (a distinct type from the
  responder's read-only credential and ReadHandle, with no query/read path), holds a secret REFERENCE resolved
  at the shared D4 seam (evidence.resolve_secret_ref reused, C5/D4), and accepts a whitelist reference plus
  validated parameters bound to a proposal digest, NEVER command text. It reuses W5's resolution and parameter
  validation and W1's remedy validation: no second resolver, no second parser.
- THE PROPOSAL DIGEST is the binding. proposal_digest is the canonical digest of a veldo.remedy/v1 proposal, the
  same idiom validate.proof_digest and action.action_digest use (the WARP-0109 digest binding applied to the
  remedy). The human confirmation the L2 rung requires is bound to this digest, so a confirmation of a different
  or stale proposal refuses; W7's two keys will bind to the same digest, so the binding has one truth and lives
  in this organ (the one that introduces it), leaving W1 untouched.
- THE AUTONOMY LADDER (O3, D2) is a human-owned control the executor reads and never raises (NG4). Floor L0/L1
  never executes; L2 executes only provably-reversible, non-data-mutating actions after the confirmation; L3 is
  disabled by default and, per D2, may never be enabled, and if it ever were it executes the lowest class alone,
  which the high whitelist floor makes empty. Degrade DOWN, never up (C3).
- THE TWO-KEY FENCE (pending W7). Anything irreversible or data-mutating requires two keys, which is WARP-1207
  and is NOT built here; so the executor REFUSES any such action (fail closed), which is why this build carries
  no data-mutating execution path and stays HIGH rather than reaching the critical tier (C2).
- THE STANDING SAFEGUARDS: a kill switch any human trips instantly (reset needs a recorded highest-tier
  approval, D5), action budgets, timeouts, and canary-first where the action declares it. Each ships as a
  negative test that proves the refusal (anti-vacuity C1, the refusals are the product).

## Out of scope

- No two-key rule. The recorded human authorization plus the independent fresh-context confirmation for an
  irreversible or data-mutating action is WARP-1207 (W7). This item FENCES those actions off (they refuse) and
  builds no data-mutating execution path; proposal_digest is defined here so W7 binds two keys to it.
- No compressed loop and no reconciliation. Driving an incident through the emergency lane and closing it by
  reconciliation is WARP-1208 (W8); this item runs a single proposal's action under the guards and stops.
- No numbers. The support metrics are WARP-1210 (W10).
- No live wiring and no real systems (NG1). The reference target acts against FAKE systems only; the
  LiveTargetSystem fails loud. Connecting the executor to any real controller is a separate per-system
  human-approved enablement act, outside this plan.
- No gate wiring and no daemon. Landing an executor check into validate.py run_all and the init lay-down is
  WARP-1211 (W11); validate.py is unedited and stays under its module_lines budget. The organ ships runnable
  standalone (python3 .veldo/action_executor.py) and exercised through the shipped examples and fixtures in the
  selftest. It starts no process, thread, or timer (NG3).
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). The organ lives in the
  placeless engine module .veldo/action_executor.py, outside the declared contract areas, like the sibling organs.

## Notes

- HIGH RISK, and the landing is not the builder's. Per C2 the executor is the enforcement core, so this spec
  carries a high risk floor with recorded human approval regardless of its footprint tier (standard). The
  builder stops at review; the two independent fresh-context reviews and the founder's recorded approval are the
  landing key. What a human approving this vouches for: that the executor can run ONLY a whitelisted action with
  validated parameters bound to the exact proposal a human confirmed (never command text, no free-form path),
  that the read-only floor L0/L1 can never execute, that nothing irreversible or data-mutating can run here at
  all (it fails closed pending the two keys), that the kill switch, budgets, timeouts, and canary-first each
  refuse by name, and that the executor never escalates itself - all proven offline against fake systems, with
  the two-key rule (W7) and the compressed loop (W8) still unbuilt and no live target wired.
- Determination: HIGH, not critical. C2 reserves the critical tier for data-mutating execution paths; this build
  has none (the two-key fence refuses them), so it is HIGH with recorded human approval. human_approval is
  required regardless.
- Keep the organ dependency free (pathlib, plus json and hashlib for the proposal's own digest) and follow the
  byte-identical engine sync discipline. The action, incident, and evidence organs are reused, not
  re-implemented; the D4 secret seam is reused as the platform capability it is.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
