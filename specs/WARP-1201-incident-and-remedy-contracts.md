---
schema: veldo.spec/v1
id: WARP-1201
title: The incident and remediation contracts and their validator (W1 of PLAN-0012)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W1
plan_revision: 2
depends_on: []
placement: [contracts]
footprint:
  - .veldo/incident.py
  - .veldo/events.py
  - .veldo/capabilities.yaml
  - .veldo/examples/incident-example.yaml
  - .veldo/examples/remedy-example.yaml
  - engine/.veldo/incident.py
  - engine/.veldo/events.py
  - engine/.veldo/capabilities.yaml
  - engine/.veldo/examples/incident-example.yaml
  - engine/.veldo/examples/remedy-example.yaml
  - packs/*/.veldo/incident.py
  - packs/*/.veldo/events.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1201-incident-and-remedy-contracts.md
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A versioned incident-record format (schema veldo.incident/v1) exists, homed as
      per-repo instance data under .veldo/incidents/*.yaml, a directory the engine glob
      does not sweep, so records stay per-repo like the architecture contract and the
      decision records and are never shipped in the engine. A record declares what
      broke (signal), the affected behavior (and, softly for the later cross-plan join,
      the spec or architecture area it traces to), a severity drawn from the method's
      one tier ladder (low, standard, high, critical), a timeline that carries the
      time-to-diagnosis (opened_at always, diagnosed_at once diagnosed), and a
      lifecycle status (open, diagnosed, closed). A clearly-marked illustrative example
      ships at .veldo/examples/incident-example.yaml and validates clean via
      python3 .veldo/incident.py .veldo/examples/incident-example.yaml; a selftest asserts
      the example validates and that a diagnosed record with no diagnosed_at, or a
      diagnosed_at before the opened_at (a negative time-to-diagnosis), is refused.
  - id: AC2
    text: >
      A versioned remediation-proposal format (schema veldo.remedy/v1) exists, homed
      per-repo under .veldo/remedies/*.yaml, carrying EVERY element the plan mandates: a
      diagnosis, the evidence with query citations that supports it (a non-empty list,
      each entry citing the query or artifact it rests on), the proposed whitelist
      action and its parameters (an action reference, never command text, plus a
      parameters mapping), the risk class, the autonomy level the action needs (L0, L1,
      L2, L3), a reversibility analysis (class, analysis, data_mutating), a rollback
      plan, a canary shape (whether a canary runs first and its shape), and the human
      authorization its execution will require. A record missing any element is invalid
      at contract time, so the two-key path downstream (WARP-1207) has something exact
      to bind to. A clearly-marked illustrative example ships at
      .veldo/examples/remedy-example.yaml (a reversible deploy-rollback proposal), binds
      to the example incident, and validates clean; a selftest asserts it validates and
      that dropping any mandated element (evidence citation, proposed action or its
      parameters, risk class, autonomy level, reversibility, canary) is refused.
  - id: AC3
    text: >
      The safety architecture is STRUCTURAL, not a policy the responder must remember,
      and it fails closed. A remedy is a PROPOSAL and the artifact carries NO execution
      capability: a remedy that carries a self-execution or auto-apply field (even set
      to false) or whose status claims it executed, applied, or auto-applied is REFUSED
      (the proposal-not-execution invariant; diagnosis and execution are separate
      organs and execution is WARP-1206, W6). A proposal that omits its rollback plan is
      REFUSED, and a proposal that omits its required authorization is REFUSED (the two
      safety omissions). Anything classed irreversible, or that declares
      data_mutating true, must set required_authorization two_key, or it is REFUSED (the
      two-key rule itself is WARP-1207, W7; this contract records that the strongest
      authorization is required so W7 has an exact binding). Each refusal is proven by a
      negative selftest, and a reversible non-data-mutating proposal authorized by a
      single human confirmation, and an irreversible one requiring two keys, each
      validate clean (positive controls, so the check cannot pass vacuously).
  - id: AC4
    text: >
      The validator (.veldo/incident.py) reuses validate.parse_yamlish (no second
      parser) and the validate.fail reporter (no import cycle), the way .veldo/decision.py
      and .veldo/arch.py receive theirs, and FAILS CLOSED by name on each malformation
      class: a wrong schema id, a missing or empty required field, an out-of-vocabulary
      status, severity, risk class, autonomy level, reversibility class, or
      authorization, a timeline with no opened_at, evidence with no citation, a proposed
      action with no action reference or parameters, and a file outside the parser
      subset (malformed). A remedy binds to the incident it remediates (bind_remedy) and
      a remedy whose incident does not resolve is refused (referenced but absent), so a
      proposal never floats free of its incident. Adoption safe: with no .veldo/incidents/
      and no .veldo/remedies/ directory the check stands down and returns clean (a
      repository that never configures the responder is byte-identically unaffected);
      a required-but-absent single record fails closed, a present malformed record fails
      closed, and a duplicate incident or remedy id within its set is refused. Each is
      proven by a selftest over a temporary tree.
  - id: AC5
    text: >
      The check has TEETH proven by mutation over this repository's shipped
      incident-example.yaml and remedy-example.yaml (the anti-vacuity rule C1): stripping
      the diagnosed incident's diagnosed_at, and on the remedy injecting a self_executing
      field, stripping the rollback plan, stripping the required authorization, and
      flipping the status to executed, each turn the check RED, and every mutation reverts
      byte-identical. .veldo/incident.py ships in the engine and is re-synced byte-identical
      across engine and all 6 packs; the edited .veldo/events.py (which gains the
      incident lifecycle event vocabulary, bound to .veldo/incident.py's INCIDENT_EVENT_TYPES
      by a selftest so the two cannot drift) and .veldo/capabilities.yaml are re-synced
      likewise (template sync and pack drift pass). capabilities.yaml gains ONE honest
      mechanical entry (incident_remedy_contracts) in every copy that names exactly what
      ships and defers honestly: landing the check into validate.py run_all and lay-down
      via init is WARP-1211 (W11), and the evidence plane (W2), intent corpus (W3),
      responder loop (W4), action whitelist (W5), execution organ (W6), and two-key rule
      (W7) are referenced, never implied built - this contract carries no execution
      capability. The full gate is GREEN (selftest, contracts, generated, docs, lint,
      secret scan, template sync, pack drift, shape gate), RULE #1 is clean (ASCII hyphen
      only, no em or en dash, no prose double-hyphen), and no protected path is touched
      (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py and their engine
      twins unchanged). Dogfood: this spec's placement [contracts] resolves to a declared
      area and its footprint tier is standard (a single area, no boundary crossing;
      .veldo/incident.py is a placeless engine module outside the contract areas, like the
      PLAN-0011 organ modules).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one contract-validator module (.veldo/incident.py),
  two illustrative example artifacts, four incident lifecycle event types in
  .veldo/events.py, and one capabilities entry, all re-synced byte-identical across
  engine and the 6 packs, plus a selftest block and this spec. Nothing consumes
  incident or remedy records for enforcement yet (the first consumers are the responder
  loop WARP-1204 and the executor WARP-1206, and gate wiring into validate.py run_all is
  WARP-1211), and the validator is not yet wired into verify.sh or validate.py run_all, so
  removing it changes no gate behavior. A repository with no .veldo/incidents/ and no
  .veldo/remedies/ directory is unaffected either way (the adoption-safe posture), so there
  is no migration and nothing to unwind; incident and remedy records are inert per-repo
  data the module owns no store for.
---

## Intent

This is the first root of PLAN-0012 and the foundation of the method's "The Incident"
invention: when agents author everything, the five-minute diagnosis that used to be a
free byproduct of authorship is gone, so the responder that replaces the hero has to be
built on systems. The first system is a pair of readable contracts that make the safety
architecture structural rather than a policy anyone has to remember. veldo.incident/v1 is
how an incident enters the loop as intent arriving from production (the signal, the
affected behavior, the severity, the timeline that carries the time-to-diagnosis, and a
lifecycle status). veldo.remedy/v1 is the responder's only output: a remediation PROPOSAL
(a diagnosis derived from artifacts, cited evidence, the proposed whitelist action and
its parameters, the risk class and autonomy level, a reversibility analysis, a rollback
plan, a canary shape, and the human authorization its execution will require). This item
builds the two artifacts and their structural validator; nothing here investigates,
proposes, or executes anything, and the artifact carries no execution capability.

## Context

- The design center the plan binds everywhere (from the founder's framing that production
  access is existential risk): a remedy is a PROPOSAL, never an execution. Diagnosis and
  execution are separate organs. This contract is the diagnosis and proposal side; the
  execution organ is WARP-1206 (W6), on its own credentials and code path. The validator
  encodes this structurally: the artifact may carry no execution-capability field and no
  status that claims it executed, or it is refused. The responder proposes and stops.
- The two-key rule (a recorded human authorization plus an independent fresh-context
  confirmation for anything irreversible or data-mutating) is WARP-1207 (W7). This
  contract mechanizes the binding it needs: a remedy classed irreversible or declaring
  data_mutating true must set required_authorization two_key, the same way the decision
  record maps an irreversible choice to the critical tier (D5). The two-key scrutiny
  itself is applied by W7.
- The validator is modeled on .veldo/decision.py: structural, required-field and
  closed-vocabulary checks over the one front-matter subset (validate.parse_yamlish),
  no second parser, no import cycle. incident.py receives the parser and the failure
  reporter from its caller, which owns them.
- The two postures the plan binds everywhere: adoption safe (a repository with no
  .veldo/incidents/ and no .veldo/remedies/ directory is untouched, the scan stands down)
  and fail closed (the moment a record exists it is validated and refuses anything
  malformed). C1 anti-vacuity: in this plan the refusals are the product, so every safety
  property ships as a negative test that proves the refusal.

## Out of scope

- No evidence plane, no intent corpus, no responder loop. Reading declared read-only
  sources behind adapters with redaction and a query audit log is WARP-1202 (W2); the
  mechanical query surface over the intent corpus is WARP-1203 (W3); the in-session
  responder that produces a cited diagnosis and a proposal is WARP-1204 (W4). This item is
  the contracts and their validator only.
- No action whitelist and no executor. The pre-vetted parameterized runbook actions are
  WARP-1205 (W5); the separate privileged execution organ with the autonomy ladder, kill
  switch, budgets, and canary-first is WARP-1206 (W6). This contract names a whitelist
  action and its parameters; it neither defines the whitelist nor runs anything.
- No two-key mechanism. The recorded human authorization plus the independent
  fresh-context confirmation is WARP-1207 (W7). This item only records that an
  irreversible or data-mutating remedy requires two keys.
- No emission and no gate wiring. Emitting the incident lifecycle events, recognizing them
  in the gate's event validator (validate.py check_events), and reconciling a closed
  incident into regression criteria are the compressed loop WARP-1208 (W8); landing the
  contract check into validate.py run_all and the init lay-down is the release WARP-1211
  (W11). W1 introduces the incident lifecycle vocabulary in the emitter and ships the
  validator runnable standalone and exercised through validate.py's parser and reporter in
  the selftest; it does not wire it into the gate. This deferral is why editing the
  over-budget .veldo/validate.py (which the shape gate would refuse) is not required here.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy.yaml, .veldo/policy_check.py and their engine twins are untouched
  (protected paths). The validator lives in the placeless engine module .veldo/incident.py,
  outside the declared contract areas, like the PLAN-0011 organ modules.

## Notes

- Keep the validator dependency free and the artifacts readable (the C3 proportionality
  constraint) and follow the byte-identical engine sync discipline: .veldo/incident.py, the
  edited .veldo/events.py, and .veldo/capabilities.yaml land in engine and every
  pack byte-identical, and the drift checks end empty. The incident and remedy RECORDS are
  per-repo (like architecture.yaml and the decision records), and homing them in
  .veldo/incidents/ and .veldo/remedies/ keeps them out of the .veldo/*.yaml single-level
  engine glob structurally, so a fresh repository starts record-free and adoption safe.
  The illustrative examples ship in .veldo/examples so an adopter sees the format; they are
  clearly marked illustrative and describe no real incident.
- Put teeth on the check by mutating the shipped examples and observing the check go red
  before reverting; a mechanical check that cannot refuse is exactly the vacuity C1
  forbids. The load-bearing teeth are the safety ones: a remedy that claims self-execution,
  omits its rollback, or omits its required authorization must be refused, and an
  irreversible or data-mutating remedy that does not require two keys must be refused.
- Honesty (NG5 and the WARP-1101 over-attestation lesson): do not mark a rule mechanizable
  that nothing enforces, and do not imply the responder, the executor, or the two-key rule
  are built. This repository ships the two contract formats and their validator with
  illustrative examples; the organs that consume them are honestly named as later items,
  and the contract carries no execution capability.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
