---
schema: veldo.spec/v1
id: WARP-1209
title: Diagnosability gated - observability as acceptance criteria (W9 of PLAN-0012)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W9
plan_revision: 2
depends_on: []
placement: [contracts]
footprint:
  - .veldo/observability.py
  - .veldo/validate.py
  - .veldo/validate_checks.py
  - .veldo/capabilities.yaml
  - engine/.veldo/observability.py
  - engine/.veldo/validate.py
  - engine/.veldo/validate_checks.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/observability.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/validate_checks.py
  - packs/*/.veldo/capabilities.yaml
  - packs/claude/skills/spec/SKILL.md
  - packs/*/skills/spec/SKILL.md
  - scripts/selftest.py
  - specs/WARP-1209-diagnosability-gated.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The gate emits a NAMED refusal line per problem through the injected fail(name, msg)
    reporter at each decision point - the behavior-bearing determination, a missing
    observability block, an out-of-vocabulary criterion, a non-empty-description check, and
    a missing contract-required criterion under the C7 join - so a gate failure is
    diagnosable from the gate output alone without reading the source.
  error_taxonomy: The refusal reasons are a closed, named taxonomy over the vocabulary
    (OBSERVABILITY_CRITERIA) and the three C7 join states (absent, present, malformed); each
    refusal names its class and what to declare, so the failure mode is legible from the
    message rather than inferred from a stack trace.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Accept an unrecognised key in validate_observability (.veldo/observability.py:135) instead of refusing
      it, and the assertion that an observability key outside the four-name vocabulary is REFUSED must go red
      while the well-formed positive control keeps passing; adding a fifth name to OBSERVABILITY_CRITERIA
      (.veldo/observability.py:77) falsifies the exact-vocabulary assertion.
    text: >
      An observability CRITERIA VOCABULARY exists as a versioned engine organ
      (module .veldo/observability.py, schema veldo.observability/v1): OBSERVABILITY_CRITERIA
      names exactly the four criteria outcome O6 enumerates - logs (structured logs at
      decision points), metrics, traces, and error_taxonomy (an honest error taxonomy) - and
      nothing else. A structural validator (validate_observability, PURE over a spec's parsed
      front matter, reusing validate.parse_yamlish through the caller and the validate.fail
      reporter, no second parser and no import cycle, exactly as arch.validate_placement
      receives its parser and reporter) FAILS CLOSED by name on each malformation: a
      behavior_bearing that is neither true nor false, an observability that is not a mapping,
      an observability key outside the vocabulary (refused, never silently accepted), and an
      observability value that is not a non-empty description. Adoption safe: a spec that
      declares NEITHER behavior_bearing NOR an observability block stands down (returns 0), so
      a spec that never touches diagnosability is byte-identically unaffected. A selftest
      asserts the vocabulary is exactly the four criteria, that a well-formed declaration
      validates clean (positive control), and that each malformation class refuses.
  - id: AC2
    falsified_by: >
      Remove the observability_gate call from validate.check_ready, and the assertion driven over a temporary
      tree that check_ready REFUSES a behavior-bearing spec declaring no observability must go red while the
      present-only check_observability keeps accepting a well-formed block, which is exactly the difference
      between refusing at the ready transition and merely validating a declaration that already exists.
    text: >
      ELABORATION APPLIES the vocabulary and the VALIDATOR ENFORCES it at the ready
      transition (outcome O6). observability_gate (a PURE predicate in .veldo/observability.py
      returning the list of problems, empty iff the spec passes) is wired at the SAME
      transition the placement gate uses - validate.check_ready, run by the /veldo:spec
      elaboration skill before it promotes a spec to ready - and the /veldo:spec skill asks
      for the behavior_bearing classification and the observability criteria as part of
      elaboration (synced across every skill copy), so elaboration applies the vocabulary and
      the validator refuses. A behavior-bearing spec (behavior_bearing: true) that declares NO
      observability criteria is REFUSED at check_ready with the reason named (the stranger
      question - can this be diagnosed from outside without reading the source - is now a gate
      concern). check_observability additionally validates a declared block STRUCTURALLY over
      every spec at spec-validation time (present-only, so the shipped corpus is untouched). A
      selftest proves, over a temporary tree with a contract, that check_ready REFUSES a
      behavior-bearing spec with no observability declaration and that check_observability
      accepts a well-formed one; and asserts the /veldo:spec skill copy names the observability
      elaboration step.
  - id: AC3
    falsified_by: >
      Aim the in-memory mutation at any arm of observability_gate other than the `elif not declared` floor arm
      (.veldo/observability.py:219), so the behavior-bearing fixture with no criteria stays refused, and
      assertion (b), that neutralizing the floor turns that same fixture GREEN, must go red; the exemption
      control (d) falsifies from the other side by gating specs whose behavior_bearing is absent or false.
    text: >
      THE REFUSAL IS THE PRODUCT and it is NON-VACUOUS (the anti-vacuity rule C1). Proven by
      mutation and by controls, each observed to flip the result: (a) a behavior-bearing
      fixture spec with no observability criteria is REFUSED by name; (b) an in-memory MUTATION
      of the observability module that REMOVES the mandatory-refusal enforcement (neutralizing
      the floor branch of observability_gate) turns that same fixture GREEN, and the real
      module on disk is byte-unchanged after the mutation (the enforcement is load-bearing, not
      decoration); (c) the SAME fixture with an observability block declaring a recognized
      criterion PASSES (a spec that DOES declare criteria flips the result); (d) the CONTROL: a
      NON-behavior-bearing spec (behavior_bearing absent, and behavior_bearing: false) is
      EXEMPT - the gate returns no problem, so a non-behavior-bearing change is never a false
      positive. The UNMECHANIZABLE part is honestly labeled review-lane guidance and neither
      silently passed nor falsely mechanized (NG5): the module and this spec state that WHETHER
      the declared criteria are SUFFICIENT for a stranger to diagnose the change is a reviewer's
      judgment, while the mechanical floor (at least one recognized criterion, or the
      contract-required set) is enforced. A selftest asserts (a) through (d) and that the
      review-lane labeling is present in the module source.
  - id: AC4
    falsified_by: >
      Make contract_observability (.veldo/observability.py:180) return an empty required list for a malformed
      observability section instead of the malformed status, and the assertion that a malformed contract
      section is REFUSED rather than silently ignored must go red, because the gate would then fall back to
      the floor and report an honest stand-down over a contract it could not read.
    text: >
      THE C7 SOFT JOIN, degrading down and never faking a join. contract_observability reads a
      system's observability rules from the OPTIONAL contract-level observability.required list
      when a PLAN-0011 architecture contract declares them, and observability_gate then requires
      a behavior-bearing change to declare EACH such criterion (a system's observability rules
      live in the contract). Where no such rules exist - as in this repository's own contract
      today - the gate STANDS DOWN honestly to the spec-level floor (at least one recognized
      criterion), never inventing a rule the contract did not declare; and a contract whose
      observability section is present but malformed (not a mapping, an empty or non-list
      required, or a criterion outside the vocabulary) is REFUSED rather than silently ignored.
      A selftest proves all three paths over temporary contracts: with required rules a spec
      missing one is refused and a spec declaring all passes; with no observability section the
      floor applies (a behavior-bearing spec with no criteria refuses, one with a criterion
      passes); and a malformed section refuses. It also asserts this repository's real contract
      declares no observability section, so the live gate uses the floor (an honest stand-down,
      the join not faked here).
  - id: AC5
    falsified_by: >
      Invoke observability_gate from validate.run_all as a static sweep of the corpus, and the assertion that
      run_all does NOT invoke it must go red, which is the RJ6 property: the mandatory rule binds at the ready
      transition only, so the already-shipped specs are never re-evaluated.
    text: >
      BACKWARD COMPATIBLE (regression journey RJ6), engine-synced, and honestly recorded. The
      mandatory rule binds at the ready TRANSITION only (check_ready / observability_gate),
      never as a static check_spec sweep, exactly as the placement gate is scoped, so the 121
      already-shipped specs - none of which declares behavior_bearing - are never re-evaluated:
      a selftest asserts run_all does not invoke observability_gate, that the real WARP-1103
      shipped spec still passes check_ready == 0 (a placeless-of-this-field spec is exempt), and
      the whole gate stays GREEN across the corpus. .veldo/observability.py, the edited
      .veldo/validate.py and .veldo/validate_checks.py, and .veldo/capabilities.yaml ship in the
      engine and are re-synced byte-identical across engine and all 6 packs (template
      sync and pack drift pass; a selftest asserts root-vs-engine and cross-pack
      byte-identity). capabilities.yaml gains ONE honest mechanical entry (diagnosability_gated)
      in every copy that names exactly what ships and defers honestly: the metrics half of O6
      (time-to-diagnosis, recurrence, the diagnosability score, incidents-per-area) is WARP-1210
      (W10), and the /veldo:init lay-down is WARP-1211 (W11). observability.py starts no process,
      thread, or timer (NG3). The full gate is GREEN (selftest, contracts, generated, docs,
      lint, secret scan, template sync, pack drift, shape gate), RULE #1 is clean, and no
      protected path is touched (validators are NOT protected per policy.yaml; verify.sh,
      veldo-guard.sh, policy.yaml, policy_check.py and their twins are unchanged). Dogfood: this
      spec declares behavior_bearing: true and an observability block (logs and error_taxonomy),
      so it passes its own gate (check_ready == 0); its placement [contracts] resolves and its
      footprint tier is standard (a single area, no boundary crossing).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine organ (.veldo/observability.py: the observability
  criteria vocabulary, the structural validator, the mandatory diagnosability gate, and the C7
  contract-rules reader), wires it thin from .veldo/validate_checks.py (check_observability at
  spec-validation time and observability_gate at the ready transition) and .veldo/validate.py (one
  check_observability call in check_spec plus the re-export), asks for the observability
  classification in the /veldo:spec skill, adds one capabilities entry, and adds a selftest block,
  all re-synced byte-identical across engine and the 6 packs. The mandatory gate is scoped
  to the ready transition, so it evaluates no already-shipped spec; the present-only structural
  check stands down for every spec that declares neither field, so the shipped corpus is untouched.
  A spec that declares no behavior_bearing, and a repository with no architecture contract, are
  unaffected either way (the adoption-safe posture), so there is no migration and nothing to unwind.
---

## Intent

This is the fourth root of PLAN-0012 (the frontier after approval is W1, W2, W3, and W9) and the
machinery behind the plan's diagnosability half of outcome O6. The method ends at the merge and says
nothing about two in the morning: the old world's five-minute diagnosis was a free byproduct of
authorship, and when agents author everything that byproduct is gone, because whoever gets paged is
a stranger to the code. The honest response is not to hope the code is legible but to make its
legibility a gate concern. Observability - structured logs at decision points, metrics, traces, and
an honest error taxonomy - enters acceptance criteria for behavior-bearing changes, because every
future responder is a stranger. This item ships the observability criteria vocabulary and the gate
that refuses a behavior-bearing spec declaring none; the refusal is the load-bearing product (C1).

The move is the same one the method has made before, and this is its next instance: intent became
the spec, the shape became a contract, placement became a checked field. Now diagnosability becomes
a checked field. A spec declares during elaboration whether it is behavior-bearing and, if so, the
observability criteria it carries; the validator refuses a behavior-bearing spec that declares none;
and the stranger question - can this be diagnosed from outside without reading the source - stops
being a hope and becomes a check that fails at the cheapest moment, the ready transition, before
anything is built.

## Context

- The outcome this serves (O6, the diagnosability half): observability enters acceptance criteria for
  behavior-bearing changes, the vocabulary is enforced, and the unmechanizable parts stay honestly in
  the review lane. O6's measure is that the elaboration and validator refuse a behavior-bearing spec
  that declares no observability criteria. This item ships exactly that: the vocabulary
  (OBSERVABILITY_CRITERIA), elaboration applying it (the /veldo:spec skill), and the validator enforcing
  it (observability_gate at check_ready). The METRICS half of O6 (time-to-diagnosis and
  time-to-restore trending, recurrence rate, the diagnosability score, and incidents-per-area joining
  PLAN-0011's cost-to-change-per-area) is a SEPARATE work item, WARP-1210 (W10); nothing here derives
  a metric.
- The right architecture (RULE #6, no shortcut): diagnosability becomes a DECLARED, CHECKED field, not
  a keyword scrape of prose. behavior_bearing records the decision the way risk and placement record
  theirs, and observability names the criteria the way placement names the areas. The gate is a PURE
  predicate that reuses the one parser and the one failure reporter, loaded by path exactly as
  check_placement loads arch.py, so there is no second parser and no import cycle.
- The load-bearing property is the REFUSAL (C1, the refusals are the product): a behavior-bearing spec
  that declares no observability criteria is refused by name. The teeth prove it is non-vacuous - a
  mutation that removes the enforcement, or a spec that DOES declare criteria, flips the result - and
  the control proves it does not over-fire: a non-behavior-bearing spec is exempt.
- The honest boundary between mechanical and review-lane (NG5, the over-attestation lesson): the gate
  enforces the FLOOR (a behavior-bearing spec declares at least one recognized criterion, or the
  criteria a system's contract requires) and the vocabulary (a criterion outside it is refused). It
  does NOT grade whether the declared criteria are SUFFICIENT - whether the logs sit at the real
  decision points, whether the error taxonomy is honest, whether a stranger would actually diagnose
  the change from outside; that is a reviewer's judgment, labeled review-lane, neither silently passed
  nor falsely mechanized.
- The two postures the plan binds everywhere: adoption safe (a repository with no architecture
  contract, and a spec that declares neither field, stand down; the shipped corpus is never
  re-evaluated because the mandatory rule binds at the ready transition, not in a check_spec sweep) and
  fail closed (a behavior-bearing spec promoted to ready against a contract with no observability
  declaration refuses by name). And the cross-plan join is soft (C7): a system's observability rules
  live in the architecture contract when it declares them, and the gate stands down honestly to the
  spec-level floor when it does not, never faking a join.

## Out of scope

- No metrics derivation. The support numbers - time-to-diagnosis, time-to-restore, recurrence rate,
  the diagnosability score (share of incidents resolved from artifacts alone), and incidents-per-area
  joined with PLAN-0011's cost-to-change-per-area - are WARP-1210 (W10), derived from the incident
  event stream WARP-1208 (W8) emits. This item derives no metric and reads no event.
- No claim-time or build-time gate. The mandatory rule is enforced at the ready TRANSITION
  (validate.check_ready), the canonical enforcement point O6's measure names ("the elaboration and
  validator refuse"), the same surface the /veldo:spec skill runs before promoting a spec. It is
  DELIBERATELY not wired into the claimable frontier or plan.py run-check: unlike PLAN-0011's placement
  (whose outcome O3 required "never claimed for build" and so touched the fleet area), O6 asks for the
  elaboration-and-validator refusal, and wiring the claim path would cross into the fleet area and
  raise the tier without serving O6. This is stated honestly, not a gap papered over.
- No edit to the architecture contract artifact. This repository's .veldo/architecture.yaml is a
  human-approved artifact and declares no observability section; adding one (a system's observability
  rules in the contract) would be a separate, human-approved shape change. The C7 contract-rules path
  is proven over temporary contracts; the live gate stands down honestly to the spec-level floor here.
- No responder, executor, evidence plane, or contracts change. The incident and remedy contracts are
  WARP-1201 (W1), the evidence plane WARP-1202 (W2), the intent corpus WARP-1203 (W3), the responder
  loop WARP-1204 (W4), the whitelist WARP-1205 (W5), the executor WARP-1206 (W6), the two-key rule
  WARP-1207 (W7), and the compressed loop WARP-1208 (W8). This item is the diagnosability vocabulary
  and gate only, and shares no code path with any of them.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). Validators
  are explicitly NOT protected per policy.yaml, so the gate lives in the non-protected engine
  (observability.py, validate_checks.py, validate.py), like the sibling elaboration and validator organs.

## Notes

- Keep the gate a PURE predicate in one place (observability_gate), reusing validate_observability for
  the declaration's structural rules so the shape is defined once, exactly as arch.placement_gate
  reuses arch.validate_placement. Follow the byte-identical engine sync discipline: observability.py,
  validate.py, validate_checks.py, and capabilities.yaml land in engine and every pack
  byte-identical, and the drift checks end empty. The /veldo:spec skill (the wrapper, not the engine) is
  kept byte-identical across its copies by the same discipline.
- Put teeth on the refusal by mutating the module in memory and observing the fixture flip green before
  reverting, plus the positive control (a spec that declares a criterion passes) and the negative
  control (a non-behavior-bearing spec is exempt); a mechanical gate that cannot refuse, or one that
  over-fires, is exactly the vacuity C1 forbids.
- Backward-compat is load-bearing (RJ6): the mandatory rule binds at the ready transition, never a
  check_spec corpus sweep, so the 121 shipped specs are never re-evaluated and the gate stays green.
  This is the same grandfathering the placement gate uses; a selftest guards it (run_all invokes no
  observability_gate; the real WARP-1103 spec still passes check_ready).
- Honesty (NG5): the metrics half is WARP-1210, the init lay-down is WARP-1211, and the sufficiency of
  the declared criteria is a review-lane judgment. This item ships the vocabulary and the gate; it does
  not imply the numbers, the responder, or the executor are built.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
