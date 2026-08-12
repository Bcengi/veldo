---
schema: veldo.spec/v1
id: WARP-1207
title: The two-key rule (W7 of PLAN-0012)
status: shipped
risk: critical - this spec OPENS the irreversible/data-mutating execution path that W6 deliberately fenced off, and per C2 "data-mutating execution paths carry the CRITICAL tier". W6 (the execution organ) shipped HIGH precisely because it built NO data-mutating execution path (anything irreversible or data-mutating REFUSED with requires_two_key). W7 builds the second key path through that fence: an irreversible or data-mutating action can now actually RUN, behind two keys. Because a reachable data-mutating execution path now exists in the executor, the enforcement-core risk floor is CRITICAL (C2, nothing may lower a class), which means TWO independent fresh-context reviews and a recorded founder approval as the landing key (policy risk_tiers critical -> reviews 2, human_approval true, prepare_and_execute), independent of the footprint tier (which is standard - a single contracts area, no boundary crossing; .veldo/two_key.py is a placeless engine module like the sibling organs). human_approval is required regardless
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0012
work: W7
plan_revision: 2
depends_on: [WARP-1206]
placement: [contracts]
footprint:
  - .veldo/two_key.py
  - .veldo/action_executor.py
  - .veldo/capabilities.yaml
  - engine/.veldo/two_key.py
  - engine/.veldo/action_executor.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/two_key.py
  - packs/*/.veldo/action_executor.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1207-the-two-key-rule.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The two-key gate returns a NAMED refusal per guard through a closed reason taxonomy at each
    decision point - both keys absent (the canonical requires_two_key fence), a missing human authorization,
    a missing independent confirmation, an ungranted authorization, an unconfirming confirmation, a
    machine-authored human key, a self-authored confirmation, a foreign or stale (digest-mismatched) key,
    a foreign-incident key, and an expired key - so a two-key refusal is diagnosable from the result alone
    without reading the source (the stranger question, every future responder is a stranger to the code),
    and the executed result records the two_key provenance (the authorizing and confirming identities and
    the bound digest) so a run is auditable to the exact keys that authorized it.
  error_taxonomy: The refusal reasons are a closed, named set (two_key.py constants) - requires_two_key,
    missing_human_authorization, missing_independent_confirmation, authorization_not_granted,
    confirmation_not_granted, self_authorization_refused, confirmation_not_independent, foreign_authorization,
    foreign_confirmation, authorization_expired, and confirmation_expired - each result naming its class and
    the offending key, so the failure mode is legible from the message rather than inferred; a guarded
    refusal is a named result, never a silent no-op, and a malformed call (no proposal digest) raises
    TwoKeyError by name rather than no-op.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Restore WARP-1206's dead end on the irreversible and data-mutating branch so the executor returns
      requires_two_key instead of routing to the gate, and the positive control that executes a data-mutating
      action end to end against the fake system with both keys must go red; giving .veldo/two_key.py its own
      digest instead of taking the executor's proposal_digest falsifies the one-truth leg, since the two
      computations would then be able to disagree.
    text: >
      The two-key rule (schema veldo.two_key/v1, module .veldo/two_key.py) exists as a GENERIC engine module
      and extends the execution organ's path (WARP-1206, .veldo/action_executor.py): for any action classed
      irreversible or data-mutating, or a remedy whose required_authorization is two_key, the executor no
      longer dead-ends with requires_two_key but ROUTES to the two-key gate. Execution then requires BOTH
      keys, each BOUND TO THE PROPOSAL DIGEST (never command text, C4): KEY 1 a recorded HUMAN AUTHORIZATION
      (the veldo.approval-style record extended to bind to a proposal digest rather than a commit - decision
      approved, a human approver, the bound proposal_digest, an expiry) and KEY 2 an INDEPENDENT FRESH-CONTEXT
      CONFIRMATION (the veldo.verdict-style review pattern extended to remediation - a confirming verdict plus
      the two attestations that the diagnosis supports the action and the action does only what it claims, a
      confirmer, the bound proposal_digest, an expiry). The gate REUSES W6's proposal_digest (the ONE
      canonical binding - the executor computes it and passes it in, and the two_key CLI imports it from the
      executor, so the binding has one truth and no second digest) and W5's risk/reversibility classes
      through the executor's re-validation (W1 incident.validate_remedy, W5 require_action/validate_parameters,
      no second parser, no second gate); it is a PURE function over already-parsed records, holds no
      credential, and runs nothing against any live system. A selftest proves a POSITIVE CONTROL executes a
      data-mutating action end to end against a FAKE system with both keys and drives the module standalone
      (python3 .veldo/two_key.py authorizes; --one-key refuses).
  - id: AC2
    falsified_by: >
      Return an authorization on the human-key branch of authorize (.veldo/two_key.py:186) without requiring
      the independent confirmation, and the missing_independent_confirmation refusal must go red while the
      both-keys positive control still passes; respelling REQUIRES_TWO_KEY at .veldo/two_key.py:97 falsifies
      the drift binding that pins it to action_executor.REFUSE_REQUIRES_TWO_KEY.
    text: >
      EITHER KEY ALONE REFUSES (fail closed, degrade DOWN never up, C3), and the refusals are the product
      (C1). Both keys absent returns REFUSE_REQUIRES_TWO_KEY - the EXACT value the W6 fence used, so the
      executor's pre-two-key behavior is preserved byte-for-byte and a selftest binds two_key.REQUIRES_TWO_KEY
      to action_executor.REFUSE_REQUIRES_TWO_KEY so they cannot drift; a human authorization present without
      the independent confirmation refuses (missing_independent_confirmation); an independent confirmation
      present without the human authorization refuses (missing_human_authorization); an ungranted
      authorization (decision not approved) refuses (authorization_not_granted); and a confirmation that does
      not carry a confirming verdict or does not attest BOTH that the diagnosis supports the action and that
      the action does only what it claims refuses (confirmation_not_granted). Each refusal names its class,
      and each has a green positive control (both keys, or the granting key, execute or pass). The CRITICAL
      determination: because reaching the run in this path means a data-mutating or irreversible action
      actually ran, W7 opens the data-mutating execution path and is CRITICAL per C2 (two independent reviews
      and a recorded founder approval to land), where W6 was HIGH for building no such path.
  - id: AC3
    falsified_by: >
      Delete the confirmer-is-not-the-authorizer distinctness test from the self-separation guard, and the
      confirmation_not_independent refusal for a confirmer who is the human authorizer must go red, and the
      in-memory mutation battery must stop showing that guard turning a formerly-refused input into an
      authorization; self-separation is the load-bearing one of the three, because it is what keeps two keys
      from being one party twice.
    text: >
      BINDING AND FRESHNESS AND SELF-SEPARATION each refuse by name, proven non-vacuously. DIGEST BINDING
      (C4): a key bound to a DIFFERENT proposal digest refuses (foreign_authorization / foreign_confirmation),
      a proposal EDITED after the keys were signed changes its digest and goes STALE (the keys refuse as
      foreign, the digest-binding tooth), and a key naming a FOREIGN incident refuses. FRESHNESS: an EXPIRED
      key refuses (authorization_expired / confirmation_expired) and a key that declares no expiry refuses
      (fail closed). SELF-SEPARATION (NG4, the independent-review self-separation extended to remediation):
      KEY 1 must be a HUMAN, so a MACHINE-authored authorization refuses (self_authorization_refused) and a
      human authorization by the executor's own actor refuses; KEY 2 must be INDEPENDENT, so a confirmer that
      is the remedy's PROPOSER (a self-authored confirmation), the executor's own actor, the human authorizer
      (the two keys are two parties), or a responder/executor organ identity each refuse
      (confirmation_not_independent). The proposer identity is read from the remedy's optional proposed_by;
      the always-checkable distinctness (confirmer != authorizer, confirmer != executor actor, confirmer not
      an organ identity, authorizer != executor actor) holds regardless. A selftest proves each refusal with
      a positive control and mutates each of three load-bearing guards (the self-separation, the human-key
      digest binding, and the KEY 1 machine-actor guard) in an in-memory copy so a formerly-refused input
      authorizes, with the real module byte-unchanged.
  - id: AC4
    falsified_by: >
      Make the fake system's run_action return ok without appending to its ordered op log, and the assertion
      that the log SHOWS the action ran must go red, which is what makes the success real rather than
      reported; dropping authorized_by, confirmed_by and the bound proposal_digest from the executed result
      falsifies the audit leg, and running with one key removed falsifies the non-vacuity leg.
    text: >
      BOTH KEYS EXECUTE, and the two-key success is REAL. When both keys are present, granting, unexpired,
      self-separated, and bound to the SAME proposal digest, the executor runs the (now two-key-authorized)
      irreversible/data-mutating action against the FAKE system: the fake system's ordered op log shows the
      action ran (canary-FIRST where the action declares a canary, sequence [canary, action]), and the
      executed result records the two_key provenance (two_key true, authorized_by the human approver,
      confirmed_by the independent confirmer, and the bound proposal_digest) so a run is auditable to the
      exact keys. Removing EITHER key reverts the run to a refusal (the both-keys success is not vacuous). The
      standing safeguards still stand on this path (a tripped kill switch and an exhausted budget each refuse
      before the run). And the L2 SINGLE-CONFIRMATION path is UNCHANGED (W6 preserved, zero regression): a
      strictly reversible, non-data-mutating action still executes with one human confirmation and does not
      require two keys (its run records two_key false). A selftest proves the both-keys execution, the op-log
      reality, the provenance, the revert-on-key-removal, the safeguards on the two-key path, and the
      unchanged L2 path.
  - id: AC5
    falsified_by: >
      Add a module-top subprocess import and a Popen call with start_new_session=True to .veldo/two_key.py,
      and the NG3 no-detach check must go red naming this module; touching one pack copy of .veldo/two_key.py
      so cmp against the engine copy differs falsifies the canon leg through template sync and pack drift.
    text: >
      The organ is IN-SESSION with no detached process (NG3): .veldo/two_key.py imports pathlib and json at
      module top (for the standalone demo only) and importlib LAZILY in the demo, starts no process, thread,
      or timer, and a subprocess.Popen(..., start_new_session=True) mutation turns the no-detach check RED;
      the executor edits add no process machinery. .veldo/two_key.py, .veldo/action_executor.py, and
      .veldo/capabilities.yaml are re-synced BYTE-IDENTICAL across root, engine, and all 6 packs
      (aider, antigravity, codex, copilot, cursor, opencode) by cmp; capabilities.yaml gains ONE honest
      mechanical entry (two_key_rule, home .veldo/two_key.py) and its action_executor entry is updated to be
      truthful now that the two-key path exists, both naming what ships and deferring honestly - the
      compressed loop (WARP-1208, W8), the support metrics (WARP-1210, W10), and landing a check into
      validate.py run_all plus the init lay-down (WARP-1211, W11) - referenced never implied built. The full
      gate is GREEN (selftest, contracts, generated, docs, lint, secret scan, template sync, pack drift, shape
      gate) with ZERO regressions across the whole corpus, RULE #1 is clean (ASCII hyphen only, no em or en
      dash, no prose double-hyphen), and no protected path is touched (verify.sh, veldo-guard.sh, policy.yaml,
      policy_check.py and their engine twins unchanged; validate.py unedited, so gate wiring is
      honestly deferred to W11). Dogfood: placement [contracts] resolves and the footprint tier is standard,
      yet the spec ships at risk CRITICAL and human_approval REQUIRED because it opens the data-mutating
      execution path (C2), so the landing is TWO independent reviews plus a separate recorded founder approval
      and not the builder's.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine module (.veldo/two_key.py), extends the execution organ
  (.veldo/action_executor.py) with the two-key branch and an optional lazily-loaded two-key module, and adds
  one capabilities entry (plus the truthful action_executor note update), all re-synced byte-identical across
  engine and the 6 packs, plus a selftest block and this spec. Reverting returns the executor to
  the W6 behavior exactly: an irreversible or data-mutating action REFUSES with requires_two_key (the fence
  W6 shipped), because the two-key branch and the module it routes to are the only additions and the both-keys
  determination is the only new path. Nothing consumes the two-key gate on the gate path: it is not wired into
  verify.sh or validate.py run_all (that is WARP-1211, W11), the compressed loop that would drive it is
  WARP-1208 (W8), and no live target is wired (a separate per-system human-approved enablement act, NG1), so
  reverting changes no gate behavior and there is no migration and nothing to unwind. A repository that never
  configures the responder is unaffected either way; the gate holds no store, opens no connection, and runs
  nothing against any live system.
---

## Intent

This is W7 of PLAN-0012, the two-key rule, and the sharpest edge of the plan's design center (from the
founder's framing that production access is existential risk): the dangerous rung is not one key but two,
held by two parties, and one mind - even a good one - does not touch data alone. W5 built the whitelist and
W6 built the executor that runs a whitelisted action behind a single human confirmation, but W6 deliberately
FENCED OFF anything irreversible or data-mutating (it refused with requires_two_key) so that it built no
data-mutating execution path and stayed HIGH. W7 builds the second key path through that fence: for an
irreversible or data-mutating action, execution requires BOTH a recorded human authorization AND an
independent fresh-context confirmation that the diagnosis supports the action and the action does only what
it claims, each bound to the exact proposal digest, and EITHER KEY ALONE REFUSES. This is the
independent-review pattern and the human-approval record shape the method already uses, extended from a
commit to a remediation proposal. Everything is proven OFFLINE against fake systems (NG1); wiring a real
target is a separate per-system human-approved enablement act.

## Context

- SEPARATION AND REUSE (C4/C6). The two-key mechanism is a GENERIC engine module (.veldo/two_key.py,
  veldo.two_key/v1) the executor ROUTES to, not a second gate inside the executor. It is a PURE function over
  already-parsed records: it computes no digest and parses no file. The executor computes the proposal digest
  with W6's proposal_digest (the ONE canonical binding) and passes it in, resolves the action through W5 and
  re-validates the proposal through W1 before the gate ever runs, and passes its OWN actor so the gate can
  refuse a confirmer or authorizer that is the executor itself. The standalone CLI imports proposal_digest
  from the executor (lazily) so even the demo reuses the one binding.
- THE TWO KEYS extend two shipped record shapes to bind to a proposal digest rather than a commit. KEY 1 is
  the veldo.approval-style human authorization (decision approved, a human approver, the bound proposal_digest,
  an expiry); a machine-authored key 1 refuses (NG4, no self-authorization). KEY 2 is the veldo.verdict-style
  independent confirmation (a confirming verdict plus the two attestations, a confirmer, the bound
  proposal_digest, an expiry); a self-authored key 2 refuses (the confirmer cannot be the proposer/producer,
  the executor, the human authorizer, or a responder/executor organ - the independent-review self-separation
  extended to remediation).
- EITHER KEY ALONE REFUSES (fail closed, C3). Both keys absent is the canonical requires_two_key fence (the
  W6 value, preserved and drift-guarded). Each present-but-invalid key (ungranted, machine or self-authored,
  foreign or stale by digest, foreign incident, expired) refuses by name. Both keys present, valid, unexpired,
  self-separated, and bound to the same digest execute, and only then does the executor run against the fake
  system.
- THE CRITICAL DETERMINATION (C2). W7 opens the irreversible/data-mutating execution path (behind the two
  keys), so a reachable data-mutating execution path now exists in the executor. C2 says data-mutating
  execution paths carry the CRITICAL tier and nothing may lower a class, so this spec is CRITICAL: two
  independent fresh-context reviews and a recorded founder approval as the landing key. W6 was HIGH because
  it built no such path; the moment the path exists, the tier is critical.
- THE STANDING SAFEGUARDS still stand on the two-key path (the kill switch, budget, timeout, and canary-first
  are the executor's and run on every path); the two-key rule is an additional gate on top, never a bypass of
  them. Each two-key refusal ships as a negative test that proves the refusal (anti-vacuity C1, the refusals
  are the product), with green positive controls and load-bearing guard mutations.

## Out of scope

- No compressed loop and no reconciliation. Driving an incident through the emergency lane and closing it by
  reconciliation (which would DRIVE a proposal through this gate) is WARP-1208 (W8); this item builds the gate
  and the executor branch and stops.
- No numbers. The support metrics are WARP-1210 (W10).
- No live wiring and no real systems (NG1). The gate authorizes execution against FAKE systems only; the
  executor's LiveTargetSystem still fails loud. Connecting to any real controller is a separate per-system
  human-approved enablement act, outside this plan.
- No gate wiring and no daemon. Landing a two-key check into validate.py run_all and the init lay-down is
  WARP-1211 (W11); validate.py is unedited. The gate ships runnable standalone (python3 .veldo/two_key.py) and
  exercised through the shipped fixtures in the selftest. It starts no process, thread, or timer (NG3).
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). The gate lives in
  the placeless engine module .veldo/two_key.py, outside the declared contract areas, like the sibling organs;
  the executor it extends (.veldo/action_executor.py) is a sibling engine module, not a protected path.
- No new shipped example artifacts. The data-mutating action and the two keys are proven with selftest
  fixtures (the shipped D3 trio are all reversible, so there is no data-mutating action in the shipped
  whitelist by design); adding a promoted data-mutating action or an example two-key remedy to the shipped
  engine is deliberately not done here.

## Notes

- CRITICAL RISK, and the landing is not the builder's. Per C2 W7 opens the data-mutating execution path, so
  this spec carries the critical risk floor with a recorded founder approval and TWO independent fresh-context
  reviews regardless of its footprint tier (standard). The builder stops at review; the two reviews and the
  founder's recorded approval are the landing key. What a human approving this vouches for: that an
  irreversible or data-mutating action can now RUN, but ONLY behind two keys bound to the exact proposal
  digest - a recorded human authorization AND an independent fresh-context confirmation, held by two distinct
  parties - and that EITHER key alone, a foreign or stale key, an expired key, a machine-authored human key,
  or a self-authored confirmation each refuse by name; that the both-keys run is real and reverts to refusal
  when a key is removed; that the standing safeguards still stand and the reversible L2 path is unchanged; and
  that no live target is wired. What approving this ENABLES that did not exist before: a data-mutating or
  irreversible remediation can execute (against fake systems here), which is precisely why it is critical and
  why the second review and the founder approval are the gate. Still unbuilt: the compressed loop (W8) that
  would drive an incident through this gate, the numbers (W10), the run_all/init wiring (W11), and any live
  enablement.
- Determination: CRITICAL, not high. C2 reserves the critical tier for data-mutating execution paths; W6 was
  HIGH because it had none, and W7 builds exactly one (behind the two keys), so it is CRITICAL. human_approval
  is required regardless.
- RESIDUAL TRUST (honestly scoped, the same posture the siblings disclosed and their approvals accepted): the
  gate enforces that the two keys are distinct parties, self-separated, granting, unexpired, and digest-bound;
  the proposer identity for the self-separation comes from the remedy's optional proposed_by, and the
  genuinely-fresh-context nature of the confirmation is a procedural guarantee the artifact cannot fully
  mechanize (the always-checkable distinctness against the authorizer, the executor actor, and the organ
  identities holds regardless). The gate trusts the W5-vetted reversibility on the action and the W1-declared
  reversibility on the remedy (tamper-evident by digest), exactly as W6's approval accepted.
- Keep the gate dependency free (pathlib and json for the standalone demo only) and follow the byte-identical
  engine sync discipline: .veldo/two_key.py, .veldo/action_executor.py, and .veldo/capabilities.yaml land across
  engine and every pack byte-identical. The executor, action, incident, and evidence organs are
  reused, not re-implemented; proposal_digest has one truth in the executor.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
