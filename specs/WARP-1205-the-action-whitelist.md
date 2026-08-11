---
schema: veldo.spec/v1
id: WARP-1205
title: The action whitelist - runbook actions as code (W5 of PLAN-0012)
status: shipped
risk: high - the whitelist is the enforcement core on the execution side (PLAN-0012 C2): a spec touching the whitelist carries a high risk floor with recorded human approval, so it needs the expanded gate and the L2 independent review and the founder's recorded approval as the landing key, independent of the footprint tier (which is standard - a single contracts area, no boundary crossing; .veldo/action.py is a placeless engine module like the sibling organs)
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0012
work: W5
plan_revision: 2
depends_on: [WARP-1201]
placement: [contracts]
footprint:
  - .veldo/action.py
  - .veldo/capabilities.yaml
  - .veldo/examples/action-rollback-deploy-example.yaml
  - .veldo/examples/action-restart-service-example.yaml
  - .veldo/examples/action-scale-pool-example.yaml
  - engine/.veldo/action.py
  - engine/.veldo/capabilities.yaml
  - engine/.veldo/examples/action-rollback-deploy-example.yaml
  - engine/.veldo/examples/action-restart-service-example.yaml
  - engine/.veldo/examples/action-scale-pool-example.yaml
  - packs/*/.veldo/action.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1205-the-action-whitelist.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The store emits a NAMED refusal line per problem through the injected fail(name, msg)
    reporter at each decision point - a malformed action, a risk class below the floor, a stale
    review, a duplicate id, an unknown or unreviewed action reference, and an out-of-range
    parameter - so a whitelist rejection is diagnosable from the gate output alone without
    reading the source (the stranger question, every future responder is a stranger to the code).
  error_taxonomy: The refusal reasons are a closed, named taxonomy - contract malformation, risk
    floor, stale review, unresolvable reference (does not exist to the machine path), and parameter
    validation (unknown, missing required, wrong type, out of range, out of enum, pattern mismatch) -
    each refusal naming its class and the offending element, so the failure mode is legible from the
    message rather than inferred.
acceptance_criteria:
  - id: AC1
    text: >
      The veldo.action/v1 contract (schema veldo.action/v1, module .veldo/action.py) exists and its
      structural validator (validate_action) FAILS CLOSED by name on every malformation class. A
      pre-vetted, parameterized runbook action declares the system it acts against (a FAKE system,
      NG1), a set of typed parameter specs (each a name, a type from {string, integer, number,
      boolean, enum}, a required flag, and its validation constraint), a risk class, a reversibility
      analysis (class, analysis, data_mutating), a rollback plan, and a canary declaration (supported
      and, when supported, a shape), plus a recorded review. validate_action refuses a wrong schema, a
      missing id/title/system, an out-of-vocabulary risk_class/reversibility class/parameter
      type/review status/review verdict, a malformed parameter spec (no name, an enum with no values,
      an inverted min/max range, an uncompilable pattern, a duplicate parameter name), a missing
      rollback plan, a missing canary declaration or a supported canary with no shape, and a missing
      or malformed review block, and a file outside the parser subset (malformed). It reuses
      validate.parse_yamlish and validate.fail (no second parser, no import cycle), the way
      .veldo/incident.py and .veldo/decision.py receive theirs. The reference TRIO per D3 ships as
      clearly-illustrative fake-system example actions (.veldo/examples/action-rollback-deploy-example.yaml
      against fake-deploy-controller, action-restart-service-example.yaml against fake-service-controller,
      action-scale-pool-example.yaml against fake-pool-controller); each validates clean via
      python3 .veldo/action.py .veldo/examples/action-*-example.yaml. A selftest asserts each shipped
      example validates and drives every refusal class over a GOOD_ACTION fixture with a positive
      control, so no check passes vacuously.
  - id: AC2
    text: >
      A RUNBOOK ACTION CARRIES A HIGH RISK FLOOR AND NOTHING LOWERS A CLASS (C2). Being pre-vetted for
      execution is itself a high-risk fact, so an action may not declare a risk class below high; a
      data-mutating or irreversible action carries the critical tier. risk_floor(data) returns high for
      a reversible non-data-mutating action and critical when data_mutating is true or the reversibility
      class is irreversible, and validate_action REFUSES an action whose declared risk_class is below its
      floor with the reason named, while a declaration AT or ABOVE the floor is accepted (anything may
      raise a class, nothing may lower it - the same D5 posture the decision record and the remedy
      two-key binding use). Proven non-vacuous: a data-mutating action declaring high is refused, an
      irreversible action declaring high is refused, an action declaring standard is refused, and the
      positive controls (a data-mutating action declaring critical, and any action raising to critical)
      validate. A selftest asserts each refusal and each positive control and that risk_floor computes
      high and critical over the two cases.
  - id: AC3
    text: >
      THE STORE REJECTS AN ACTION WITHOUT A RECORDED, DIGEST-CURRENT REVIEW. An action is code: it is
      proposed, reviewed through the normal VELDO loop, and only a human promotes it; the review is
      recorded on the artifact and BOUND BY A DIGEST to the exact content it vetted (the WARP-0109
      verdict-proof digest binding applied to a runbook action). action_digest is the action artifact's
      own canonical digest over its reviewable substance (everything except the review block itself);
      action_reviewed admits ONLY an action whose review status is reviewed, whose verdict is approved,
      and whose recorded reviewed_digest STILL matches action_digest of the current content; review_stale
      detects a reviewed action whose content changed afterward and check_actions FAILS CLOSED on it (a
      vetted action cannot be silently edited). A PROPOSED action is a valid draft but is NOT admitted (it
      does not exist to the machine path until reviewed). Proven non-vacuous: an action whose digest
      matches is admitted (positive control), the placeholder-digest and edited-content actions are not
      admitted and the edited one is stale, a proposed action is not admitted, and the shipped trio are
      each reviewed and digest-current (a drift guard). A selftest asserts each.
  - id: AC4
    text: >
      ANYTHING NOT IN THE WHITELIST DOES NOT EXIST TO THE MACHINE PATH (O2/C4, NG2), and parameters are
      validated with the refusal NAMED. An action reference is a whitelist KEY, never command text:
      resolve_action of an unknown reference returns None with NO free-form fallback, and require_action
      REFUSES by name, so the machine can point only at a pre-vetted action and never at a crafted
      command (a shell-looking reference is unresolvable, not run); a present-but-unreviewed (proposed)
      action is likewise unresolvable. build_whitelist admits exactly the reviewed, approved,
      digest-current actions; check_actions is ADOPTION SAFE (no .veldo/actions/ directory stands down and
      the effective whitelist is empty) and FAILS CLOSED on a malformed action, a stale review, a
      duplicate id, and a required-but-absent action. validate_parameters refuses an unknown parameter, a
      missing required parameter, a wrong type, and a value outside the declared range, enum, or pattern,
      each NAMING the parameter. veldo.action/v1 BINDS INTO veldo.remedy/v1 (W1): bind_remedy_action
      resolves a remedy's proposed_action reference against the whitelist (unknown or unreviewed refuses)
      and validates its parameters (out of range refuses by name), reusing the remedy dict W1 already
      parsed and validated (no second parser), and it RESOLVES and VALIDATES only - it runs NOTHING. A
      selftest proves the shipped remedy example binds to rollback_deploy end to end, an unknown-action
      remedy and a bad-parameter remedy each refuse, every parameter-validation class refuses by name
      with positive controls, and the adoption-safe and fail-closed directory postures.
  - id: AC5
    text: >
      The check has TEETH proven by mutation over this repository's shipped action-scale-pool-example.yaml
      (the anti-vacuity rule C1, the refusals are the product): stripping the review block, declaring the
      risk below the floor, making the action data-mutating while it declares high, stripping the rollback
      plan, and editing a reviewed field (a stale digest) each turn a check RED, and every mutation reverts
      byte-identical. .veldo/action.py is IN-SESSION with no detached process (NG3): it imports pathlib,
      json, hashlib, and re at module top and starts no process, thread, or timer, and a
      subprocess.Popen(..., start_new_session=True) mutation turns the no-detach check RED. .veldo/action.py
      and .veldo/capabilities.yaml are re-synced byte-identical across engine and all 6 packs, and
      the three example actions byte-identical across engine (packs carry no examples); template
      sync and pack drift pass. capabilities.yaml gains ONE honest mechanical entry (action_whitelist, home
      .veldo/action.py) that names exactly what ships and defers honestly: landing the check into
      validate.py run_all and lay-down via init is WARP-1211 (W11), the EXECUTOR that would run an action
      (on its own credentials and code path, bound to a proposal digest, with the autonomy ladder, kill
      switch, budgets, and canary-first) is WARP-1206 (W6), and the two-key rule is WARP-1207 (W7), all
      referenced never implied built - this store carries NO execution capability and runs nothing. The full
      gate is GREEN (selftest, contracts, generated, docs, lint, secret scan, template sync, pack drift,
      shape gate), RULE #1 is clean (ASCII hyphen only, no em or en dash, no prose double-hyphen), and no
      protected path is touched (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py and their
      engine twins unchanged). Dogfood: placement [contracts] resolves and the footprint tier is
      standard (a single area, no boundary crossing), yet the spec ships at risk HIGH and human_approval
      REQUIRED because the whitelist is the enforcement core (C2), so the landing is a separate recorded
      human act and not the builder's.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one contract-validator and store module (.veldo/action.py), three
  illustrative example actions, and one capabilities entry, all re-synced byte-identical across
  engine and the 6 packs (the examples across engine only), plus a selftest block and
  this spec. Nothing consumes action records for execution: the executor is WARP-1206 (W6) and the two-key
  rule WARP-1207 (W7), and gate wiring into validate.py run_all is WARP-1211 (W11), so the module is not
  wired into verify.sh or validate.py run_all and removing it changes no gate behavior. A repository with no
  .veldo/actions/ directory is unaffected either way (the adoption-safe posture), so there is no migration
  and nothing to unwind; action records are inert per-repo data the module owns no store for, and this
  module runs nothing.
---

## Intent

This is W5 of PLAN-0012, the execution-side pillar of the method's "The Incident" invention. The design
center the plan binds everywhere (from the founder's framing that production access is existential risk):
an agent with production access can destroy a company by simply doing the wrong thing there, so its safety
cannot be a policy it follows, it has to be an architecture it cannot escape. On the execution side that
architecture is a WHITELIST of pre-vetted, parameterized runbook actions reviewed like the code they are.
There is no general shell, no free-form command, no "just run this" path anywhere in the machine: the only
thing the machine can point at is a pre-vetted action reference with validated parameters, and anything
else is unresolvable, which makes it a human's job by definition (NG2). This item builds the CONTRACT
(veldo.action/v1), the STORE (the whitelist that admits an action only after a recorded, digest-bound
review), and the reference trio against FAKE systems (D3). It does not build the executor that would run an
action (WARP-1206, W6) or the two-key rule (WARP-1207, W7); this module runs nothing and carries no
execution capability.

## Context

- The design center this item encodes, fail closed (O2/C4, the refusals are the product C1): anything NOT
  in the whitelist does not exist to the machine path. A reference is a whitelist KEY, never command text;
  an unknown or unreviewed reference is unresolvable, with no free-form fallback. This is the structural
  guarantee that "free-form production commands do not exist in the machine path" (O2 measure).
- An action is code (the plan's framing): it is proposed, reviewed through the normal VELDO loop, and only a
  human promotes it. The store enforces that a recorded review exists and is CURRENT: the review is bound
  by a digest to the exact content it vetted, so an action edited after review is refused as stale. This is
  the verdict-proof digest binding of WARP-0109 (a high-risk sibling) applied to a runbook action, so
  "reviewed" means reviewed EXACTLY THIS, not "was reviewed once, in some earlier shape."
- The whitelist carries a HIGH risk floor and a data-mutating or irreversible action carries critical (C2);
  nothing lowers a class, anything may raise one. This is the same one-tier-ladder posture the decision
  record's D5 mapping and the remedy's two-key binding use, so the tiers mean the same thing across the
  method.
- The validator is modeled on .veldo/incident.py and .veldo/decision.py: structural, required-field and
  closed-vocabulary checks over the one front-matter subset (validate.parse_yamlish), no second parser, no
  import cycle. action.py receives the parser and the failure reporter from its caller, which owns them, and
  owns the action artifact's own canonical digest (action_digest, the way validate.proof_digest is the proof
  manifest's own digest).
- veldo.action/v1 binds into veldo.remedy/v1 (W1): a remedy's proposed_action is an action reference plus a
  parameters mapping (W1 validated its shape and refused command text). bind_remedy_action resolves that
  reference against the whitelist and validates the parameters, reusing the remedy dict W1 already parsed, so
  there is one truth for the artifacts. The executor (W6) will bind the resolved action to a proposal digest
  on its own credentials; this item resolves and validates only.
- The two postures the plan binds everywhere: adoption safe (a repository with no .veldo/actions/ directory
  is untouched, the effective whitelist empty) and fail closed (the moment a record exists it is validated
  and refuses anything malformed, stale, below floor, or unresolvable). C1 anti-vacuity: every safety
  property ships as a negative test that proves the refusal, non-vacuous by a mutation that turns the check
  red.

## Out of scope

- No executor. The separate privileged execution organ on its own credentials and code path, with the
  autonomy ladder, kill switch, action budgets, timeouts, and canary-first execution, is WARP-1206 (W6). This
  module resolves and validates a whitelist reference and its parameters; it runs NOTHING and holds no
  credential. The proposal-digest binding an executor performs before running an action is W6's, not built
  here.
- No two-key rule. The recorded human authorization plus the independent fresh-context confirmation for an
  irreversible or data-mutating action is WARP-1207 (W7). This item records that an action carries a risk
  class and a reversibility analysis (so W6/W7 have an exact binding); it does not implement the two keys.
- No action review engine. Vetting an action (does it do only what it claims, are its parameters
  constrained, is its risk class honest, is it reversible as declared) is performed through the normal VELDO
  loop by a fresh context and promoted by a human; this module ENFORCES the recorded, digest-bound outcome,
  it does not perform the review. There is no reviewer seam to fabricate, so unlike the responder or the
  adversarial decision reviewer this module ships no delegated reasoner.
- No live wiring and no real systems (NG1). The reference trio acts against FAKE systems only; connecting an
  action to any real deploy controller, service controller, or pool controller is a separate per-system
  human-approved enablement act, outside this plan.
- No gate wiring and no self-maintenance. Landing the action check into validate.py run_all and the init
  lay-down is WARP-1211 (W11); runbook actions self-maintaining from real incidents as drafts a human
  promotes is the compressed loop WARP-1208 (W8). W5 ships the module runnable standalone
  (python3 .veldo/action.py) and exercised through the injected parser and the shipped examples in the
  selftest; it does not wire it into the gate, so validate.py is unedited and stays under its module_lines
  budget. This deferral matches W1 through W4.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). The validator lives
  in the placeless engine module .veldo/action.py, outside the declared contract areas, like the sibling organ
  modules.

## Notes

- HIGH RISK, and the landing is not the builder's. Per C2 the whitelist is the enforcement core, so this spec
  carries a high risk floor with recorded human approval regardless of its footprint tier (which is standard:
  a single contracts area, no boundary crossing). The builder stops at review; the L2 independent
  fresh-context review and the founder's recorded approval are the landing key. What a human approving this
  vouches for: that a whitelist reference can NEVER become command text (no free-form path exists), that
  "reviewed" is bound by a digest to exactly the reviewed content (no silent edit), that the risk floor cannot
  be talked down, and that a bad parameter is refused before it could reach any executor - all proven offline
  against fake systems, with the executor itself still unbuilt (W6).
- Keep the validator dependency free (pathlib, plus json and hashlib for the action's own digest and re for a
  declared pattern) and follow the byte-identical engine sync discipline: .veldo/action.py and
  .veldo/capabilities.yaml land in engine and every pack byte-identical, and the three example
  actions land in engine (packs carry no examples), and the drift checks end empty. The action
  RECORDS are per-repo (.veldo/actions/, a directory the single-level .veldo/*.yaml engine glob does not sweep),
  so a fresh repository starts record-free and adoption safe. The illustrative examples ship in .veldo/examples
  so an adopter sees the format; they are clearly marked illustrative and describe no real system.
- Put teeth on the check by mutating the shipped example and observing the check go red before reverting; a
  mechanical check that cannot refuse is exactly the vacuity C1 forbids. The load-bearing teeth are the safety
  ones: an action with no recorded review, an unresolvable reference (never command text), a risk class below
  the floor, an edited reviewed action (stale digest), and an out-of-range parameter must each be refused.
- Honesty (NG5 and the WARP-1101 over-attestation lesson): do not imply the executor, the two-key rule, or the
  compressed loop are built. This repository ships the action contract, the whitelist store, and the reference
  trio against fake systems with their validator; the organs that would RUN an action are honestly named as
  later items, and this module carries no execution capability.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
