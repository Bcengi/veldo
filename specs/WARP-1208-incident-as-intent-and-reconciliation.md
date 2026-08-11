---
schema: veldo.spec/v1
id: WARP-1208
title: Incident as intent - the compressed loop and reconciliation. A closed incident is not a
  restored service, it is a settled piece of intent: the close refuses without a human-validated
  diagnosis, the failure mode leaves behind drafted regression criteria and a drafted runbook action
  that ONLY a human promotes, the executed remediation is reconciled against its receipt (never a
  claim), a recurring failure signature is reported as a missing specification, and the whole pass
  is idempotent under replay (W8 of PLAN-0012)
status: shipped
risk: standard - this item builds NO execution path and touches NO enforcement-core organ. It is the
  reconciliation pass that RUNS AFTER an incident is already diagnosed and any remediation already
  executed: it reads the incident and remedy records, reads an execution receipt the executor
  (WARP-1206) already wrote, writes a reconciliation receipt plus two DRAFT artifacts, and appends
  the incident.closed event. C2's high floor covers specs touching the executor, the whitelist, the
  two-key rule, the kill switch, or the ladder configuration; this spec edits none of them
  (.veldo/action_executor.py, .veldo/action.py, .veldo/two_key.py are READ for their shipped physics and
  are NOT in the footprint), and it opens no data-mutating path, so the critical tier does not apply
  either. The footprint tier is standard as well (a single declared area, contracts, via
  .veldo/validate.py; the new module is a placeless engine organ like every sibling of this plan).
  Nothing here lowers a class: the drafts it writes are structurally OUTSIDE the whitelist store, so
  the machine gains no ability to promote anything
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W8
plan_revision: 2
depends_on: [WARP-1204, WARP-1206]
placement: [contracts]
footprint:
  - .veldo/incident_reconcile.py
  - .veldo/reconciliation_store.py
  - .veldo/validate.py
  - .veldo/capabilities.yaml
  - engine/.veldo/incident_reconcile.py
  - engine/.veldo/reconciliation_store.py
  - engine/.veldo/validate.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/incident_reconcile.py
  - packs/*/.veldo/reconciliation_store.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/index.md
  - specs/WARP-1208-incident-as-intent-and-reconciliation.md
protected_paths: []
behavior_bearing: true
observability:
  logs: Every refusal and every settlement decision is a NAMED line through the injected
    fail(name, msg) reporter at each decision point of reconcile_incident - the status gate, the
    missing or unverified diagnosis validation, the self-validation refusal, the recomputed-digest
    mismatch, the open emergency backfill debt, the unsupported execution claim, the draft-store
    path guard, and the compare-and-swap conflict - so a refused reconciliation is diagnosable from
    the output alone without reading the source.
  error_taxonomy: The refusal reasons are a closed, named taxonomy (REFUSALS) with one constant per
    refusal path, each naming its class and what to correct; the receipt records the refusal name
    verbatim, so the failure mode is legible from the record rather than inferred from a stack trace.
  metrics: The pass appends the incident lifecycle events (incident.closed on a settled
    reconciliation) to the event stream that is the sole source for the support numbers of WARP-1210
    (time-to-diagnosis, time-to-restore, recurrence rate, the diagnosability score), and records the
    failure signature and the recurrence set on the receipt so recurrence rate is derived from
    recorded data rather than recomputed prose.
acceptance_criteria:
  - id: AC1
    text: >
      THE FAILURE SIGNATURE AND RECURRENCE DETECTION exist as pure functions in one new engine organ
      (module .veldo/incident_reconcile.py, record schema veldo.reconciliation/v1, standard library
      only, under the 1000-line module budget). failure_signature(incident) is a DETERMINISTIC
      normalized digest over exactly the incident's identity-of-failure fields (affected_behavior and
      signal, each whitespace-normalized and case-folded, plus affected_spec and affected_area when
      the record carries them), so two records describing the same failure produce the same signature
      and a record differing in title, severity, timeline, or id does NOT change it; the function is
      PURE (no clock, no filesystem, no randomness) and the same input yields the same digest across
      processes. recurrence(incident, prior_incidents) returns the ORDERED ids of prior incidents
      sharing the signature, excluding the incident itself and excluding records whose signature
      cannot be computed (a malformed record is skipped, never silently matched). A recurrence is
      REPORTED, and the report names it what the method already says it is (VELDO.md: an emergency that
      recurs is a missing specification): the receipt carries recurrence_of (the prior ids) and
      missing_specification: true whenever that list is non-empty, and false only when it is empty.
      Selftests assert the determinism, the field sensitivity (the four identity fields change the
      signature; title, severity, timeline, and id do not), the self-exclusion, the malformed skip,
      and that a second seeded incident with the same identity fields is detected against the first.
  - id: AC2
    text: >
      THE CLOSE GATE FAILS CLOSED on four independent conditions, each REFUSED BY NAME, and a
      diagnosis validation is never a self-declared field. reconcile_incident REFUSES to settle
      when: (a) the incident's status is not diagnosed (an open incident is not reconcilable, and an
      already-closed incident takes the idempotent replay path of AC4, not a second settlement);
      (b) NO human diagnosis validation is supplied for the incident (the diagnosis is validated by
      a human, outcome O5, and its ABSENCE is a refusal, never a default-allow); (c) the supplied
      validation's actor is a MACHINE actor (the actor set is REUSED from the shipped
      .veldo/authorization.py MACHINE_ACTORS, loaded by path exactly as .veldo/request_reconcile.py
      loads it, so there is no second copy of the machine-actor list and the responder can never
      validate its own diagnosis: NG4, no self-authorization); (d) the validation's bound digest does
      not equal the digest this module INDEPENDENTLY RECOMPUTES from the incident record's diagnosis
      material (the module's own guard, the 0619 lesson: an attestation that binds itself to a
      displayed value proves nothing, so the value is recomputed from the record rather than trusted).
      The emergency-lane condition is DEPENDENCY-INVERTED and enforced: reconcile_incident takes an
      injected debt_reader (default None, meaning no debt surface is declared and the condition
      stands down honestly) and, when a reader IS supplied and reports an OPEN emergency backfill
      debt for the incident, the settlement REFUSES with the reason named, so the fix flows the
      emergency lane before the incident is settled; the module IMPORTS no enforcement module (a
      contracts-area organ never depends on .veldo/policy_check.py, which would invert the declared
      layering) and starts no process, thread, or timer (NG3). Selftests prove each of the five
      refusals by name over seeded fixtures, and prove the positive control: a diagnosed incident with
      a valid non-machine validation whose bound digest matches, and no open debt, settles.
  - id: AC3
    text: >
      THE TWO DRAFTS A HUMAN PROMOTES, and the machine STRUCTURALLY CANNOT promote either. A settled
      reconciliation writes (i) a REGRESSION CRITERIA DRAFT rendered from the failure mode (the
      incident's affected behavior and signal become acceptance and regression criteria text, carrying
      the incident id, the failure signature, and the recurrence set) and (ii) a RUNBOOK ACTION DRAFT
      rendered from the remedy's proposed action, structurally VALID against the shipped
      veldo.action/v1 contract (it passes .veldo/action.py validate_action) and carrying
      review_status: proposed, so the shipped whitelist physics excludes it: action_reviewed() is
      False for it and build_whitelist() does not contain it, hence it does not exist to the machine
      execution path (NG2). Both are written ONLY into declared DRAFT directories, and the writer
      REFUSES BY NAME any target inside the action whitelist store or inside specs/ (the path guard:
      the machine never writes into the whitelist store the executor reads, and never authors a spec
      into the corpus), so promotion is a HUMAN act of moving and reviewing the draft, not a flag the
      machine can flip. The renderer also REFUSES to emit a runbook draft carrying any review status
      other than proposed, and REFUSES a review verdict field entirely (a machine-recorded review is
      exactly the rubber stamp the method forbids). Selftests prove: both drafts are written and
      re-render byte-identically; the runbook draft validates against veldo.action/v1, is NOT reviewed,
      and is ABSENT from build_whitelist over its own directory; a draft target inside the actions
      directory or inside specs/ is refused by name; a reviewed or verdict-bearing draft is refused by
      name.
  - id: AC4
    text: >
      THE RECONCILIATION RECEIPT IS HONEST AND IDEMPOTENT UNDER REPLAY. The receipt
      (veldo.reconciliation/v1) records exactly what the plan's W8 requires of a reconciled change:
      WHAT WAS DONE (the incident id, the remedy id when one exists, and the executed action
      reference and parameters taken from the execution RECEIPT, never from the remedy's own claim),
      WHAT IT PROVED (the execution receipt's recorded outcome and its proposal digest, and for a
      remedy that was never executed the honest value none rather than an invented one), and WHAT
      REGRESSION CRITERIA IT LEAVES (the paths and digests of the two AC3 drafts), plus the failure
      signature, recurrence_of, and missing_specification of AC1. The EXECUTION CLAIM IS REFUSED
      WITHOUT ITS RECEIPT: a reconciliation asked to record an execution with no supplied receipt, or
      with a receipt whose proposal digest does not match the remedy's recomputed proposal digest
      (recomputed here via the shipped .veldo/action_executor.py proposal_digest, loaded by path, not
      reimplemented), REFUSES by name (never claim a check passed; a reconciliation that overstates
      what happened is worse than none). The receipt id is CONTENT-ADDRESSED ("REC-" plus a digest over
      the incident id, the failure signature, the remedy id, and the execution receipt digest), and the
      store is APPEND-ONLY WITH COMPARE-AND-SWAP: a replay of the same settlement is a NO-OP that
      returns the EXISTING receipt and appends NO second record and NO second event, while a
      conflicting write under an existing id (the same settlement identity with different content)
      REFUSES by name rather than overwriting. Settlement appends the incident.closed event
      (vocabulary REUSED from .veldo/incident.py INCIDENT_EVENT_TYPES, never a literal string) and the
      GATE now RECOGNIZES it: .veldo/validate.py EVENT_TYPES gains the four incident lifecycle types
      (the recognition WARP-1201 deliberately deferred to this item), and a selftest BINDS the two
      vocabularies (incident.INCIDENT_EVENT_TYPES is a subset of both events.EVENT_TYPES and
      validate.EVENT_TYPES) so the emitter, the metric source, and the gate cannot drift. Selftests
      prove: the honest receipt over a seeded executed lifecycle; the none-execution path; both
      execution-claim refusals; a full replay producing zero new records and zero new events with the
      SAME receipt id; and the compare-and-swap conflict refusal.
  - id: AC5
    text: >
      THE REFUSALS ARE THE PRODUCT AND THEY ARE NON-VACUOUS (the anti-vacuity rule C1). Every refusal
      of AC2, AC3, and AC4 gets TEETH: for each guard, an IN-MEMORY MUTATION of the loaded module that
      neutralizes THAT guard alone is observed to turn its refusing fixture GREEN, and after the
      mutation the module ON DISK is byte-unchanged, proving the guard is load-bearing rather than
      decoration. The guards under teeth are exactly: the status gate, the missing-validation refusal,
      the machine-actor refusal, the recomputed-digest mismatch refusal, the open-emergency-debt
      refusal, the draft path guard, the reviewed-draft refusal, the unsupported-execution-claim
      refusal, and the compare-and-swap conflict refusal. The CONTROLS prove the pass does not
      over-fire: a well-formed diagnosed incident with a valid human validation settles cleanly and
      writes both drafts; an incident with no remedy at all settles with an honest none execution
      block rather than refusing; and a first-occurrence incident reports recurrence_of empty and
      missing_specification false. The UNMECHANIZABLE part is honestly labeled review-lane guidance in
      the module and in this spec, neither silently passed nor falsely mechanized (NG5): whether the
      drafted regression criteria are SUFFICIENT to catch the failure again, and whether the drafted
      runbook action is the RIGHT action, are a human reviewer's judgment at promotion time; the
      mechanical floor is that the drafts exist, are structurally valid, are unreviewed, and cannot be
      promoted by the machine. A selftest asserts the review-lane labeling is present in the module
      source.
  - id: AC6
    text: >
      BACKWARD COMPATIBLE, ENGINE-SYNCED, AND HONESTLY RECORDED. The pass is PURELY ADDITIVE and runs
      only when invoked in-session (a main() CLI entry point in the module, the sibling posture of
      .veldo/request_reconcile.py): no existing check, gate stage, validator, or run path calls it, so a
      repository that never opens an incident is byte-identically unaffected, and the only edit to a
      shipped file is the EVENT_TYPES addition in .veldo/validate.py (recognition only, which refuses
      nothing that passed before). The whole gate is GREEN (selftest, contracts, generated, docs, lint,
      secret scan, template sync, pack drift, shape gate), the shipped selftest count only grows, and
      no protected path is touched (scripts/verify.sh, scripts/veldo-guard.sh, .veldo/policy.yaml,
      .veldo/policy_check.py and their engine twins are byte-unchanged; the safety core
      .veldo/authorization.py, .veldo/two_key.py, .veldo/action.py, .veldo/action_executor.py and
      .veldo/incident.py are byte-UNCHANGED and only READ). .veldo/incident_reconcile.py, the edited
      .veldo/validate.py, and .veldo/capabilities.yaml ship in the canonical engine and are re-synced
      BYTE-IDENTICAL across engine and all packs (template sync and pack drift end empty; a
      selftest asserts root-versus-engine and cross-pack byte-identity). capabilities.yaml
      gains ONE honest mechanical entry (incident_reconciliation) in every copy naming exactly what
      ships and deferring honestly: the support NUMBERS derived from these events are WARP-1210 (W10)
      and the /veldo:init lay-down plus the made-true docs are WARP-1211 (W11); no live production
      system is touched (NG1) and no standing service is created (NG3). RULE #1 is clean (ASCII
      hyphens only, no em dash, no en dash, no prose double-hyphen) and this spec passes its own
      diagnosability gate (behavior_bearing with a declared observability block, check_ready == 0).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine organ (.veldo/incident_reconcile.py: the failure
  signature and recurrence detection, the fail-closed close gate, the two draft renderers with their
  path guard, the content-addressed compare-and-swap receipt store, and the in-session CLI), adds four
  event types to the .veldo/validate.py recognition set, adds one capabilities entry, and adds a
  selftest block, all re-synced byte-identical across engine and the packs. Nothing calls the
  pass automatically, so reverting removes a capability and changes no existing behavior; the only
  edit to a shipped file is a recognition-set addition that refused nothing before and refuses nothing
  after. Any receipts, events, or drafts a run already wrote are ordinary repository artifacts: the
  drafts are unreviewed and outside the whitelist store, so no execution path ever depended on them,
  and an incident.closed event already in the stream stays valid under events.py (which has carried the
  vocabulary since WARP-1201). There is no migration and nothing to unwind.
---

## Intent

This is W8 of PLAN-0012 and the item that closes the plan's loop back onto the method. The plan's first
seven items built the diagnosis side (the evidence plane, the intent corpus, the responder) and the
execution side (the whitelist, the executor, the two keys). What is still missing is the ending: what
happens to an incident AFTER the service is restored. In the old world the answer was a postmortem
document nobody read, and the failure came back. Outcome O5 states the honest version: an incident is
INTENT ARRIVING FROM PRODUCTION, so it belongs in the same compressed loop as every other piece of
intent, and it is not finished when the service is up. It is finished when the diagnosis has been
validated by a human, the fix has flowed the lane, and the reconciliation has left artifacts behind
that make the same failure harder next time.

This item ships that ending as machinery rather than as a ritual. Reconciliation refuses to settle an
incident whose diagnosis no human validated. It turns the failure mode into a drafted regression
criteria artifact and the remediation into a drafted runbook action, both of which a human, and only a
human, promotes. It reconciles the executed remediation against the executor's own RECEIPT rather than
against the remedy's claim about itself. It detects a recurring failure signature and names the
recurrence what the method already calls it: a missing specification. And it is idempotent under
replay, because a loop that double-counts its own history cannot be trusted to measure it.

## Context

- The outcome this serves (O5): "An incident is intent arriving from production, handled by the
  compressed loop and closed by reconciliation." O5's measure is exactly the conformance this item
  proves over a seeded lifecycle: the closed incident leaves behind regression criteria and a
  runbook-action draft in draft status, re-running the reconciliation creates no duplicates, and the
  recurrence of the same failure signature is detected and reported. Regression journey RJ5 activates
  after this item and asserts the same three properties.
- The dependencies are shipped and are READ, not edited. WARP-1201 (W1) owns the incident and remedy
  contracts and the incident event vocabulary, and states plainly that emission and gate recognition
  land here in W8; this item does exactly that and no more of W1's surface. WARP-1204 (W4) produces the
  diagnosis and the proposal this pass reconciles. WARP-1206 (W6) produces the execution receipt and the
  proposal digest this pass verifies against, and WARP-1207 (W7) the two-key path; both are enforcement
  core under C2 and both stay byte-unchanged here. Reading a shipped organ's physics is how this item
  stays standard risk while still being safe: the whitelist exclusion of an unreviewed action is not
  reimplemented as a flag, it IS the shipped .veldo/action.py behavior.
- The right architecture, no shortcut (RULE #6). Three shortcuts were available and are rejected. First,
  writing the runbook draft into the action store with a draft flag: rejected, because it puts the
  machine inside the whitelist store and makes promotion a flag flip; the draft goes to a separate
  drafts directory and the writer refuses any path inside the store, so promotion is a human move plus a
  human review. Second, trusting the incident record's own "validated_by" field: rejected as the exact
  self-declared-field failure the 0619 design established; the validation is a supplied attestation whose
  actor is checked against the shipped machine-actor set and whose bound digest is INDEPENDENTLY
  RECOMPUTED from the record. Third, importing .veldo/policy_check.py to read emergency debt: rejected
  because a contracts-area organ must not depend on the enforcement area (the declared dependency graph
  has no contracts-to-enforcement edge); the debt surface is an injected reader, which also keeps the
  module pure and testable and lets a repository with no debt surface stand down honestly.
- The two postures this plan binds everywhere hold here. FAIL CLOSED (C3): a missing validation, a
  machine validator, a digest mismatch, an open backfill debt, an unsupported execution claim, a
  forbidden draft path, and a compare-and-swap conflict all refuse; nothing degrades upward. ADOPTION
  SAFE: nothing calls this pass, so a repository that never opens an incident is unaffected, and the
  emergency-debt condition stands down when no reader is declared.
- The refusals are the product (C1) and every one of them carries teeth. This plan's items have all
  shipped with the mutation discipline: neutralize the guard in memory, observe the refusing fixture turn
  green, confirm the module on disk is byte-unchanged. A safety property with no negative test is a
  claim, and this plan does not ship claims.

## Out of scope

- No metrics derivation and no dashboard. Time-to-diagnosis, time-to-restore, recurrence rate, the
  diagnosability score, and incidents-per-area joined with PLAN-0011's cost-to-change data are WARP-1210
  (W10). This item EMITS and RECORDS the data those measures read (the incident.closed event, the failure
  signature, the recurrence set) and derives no measure itself.
- No release, no /veldo:init lay-down, no docs made true. That is WARP-1211 (W11). This item lands the
  organ in the canonical engine and syncs it byte-identically, and it adds exactly one honest
  capabilities entry; it changes no document in docs/ and claims nothing about the plan being released.
- No promotion of either draft, ever, by any machine path. Promoting a regression criteria draft into a
  spec and promoting a runbook draft into a reviewed whitelist action are human acts. This item writes
  drafts and refuses to write anywhere that would make them live.
- No change to the executor, the whitelist, the two-key rule, the kill switch, the autonomy ladder, or
  the ladder configuration (C2, NG4). No new execution path of any kind, at any autonomy level; this pass
  runs after execution and cannot cause one.
- No live production access (NG1) and no standing service (NG3). Every fixture is a seeded record on a
  temporary tree; the pass is invoked in-session and starts no process, thread, or timer.
- No new front-matter parser and no second machine-actor list, event vocabulary, or proposal-digest
  implementation (the contract's reuse_one_parser pattern and the plan's C4 separation): each is loaded
  by path from the module that already owns it.

## Notes

- Keep the module a set of PURE functions over injected seams, with exactly one impure edge (the
  append-only receipt store), the shape .veldo/request_reconcile.py established: a store base class, a
  fake for the tests, and a filesystem implementation. The store is the only place that writes, so
  idempotency has one home and the compare-and-swap has one implementation.
- Content-address the receipt id from the settlement identity, not from a clock or a counter. Replay
  safety follows from the id: the same settlement recomputes the same id, finds the existing receipt, and
  returns it without a second write or a second event. Assert BOTH invariants in the replay selftest (no
  new record AND no new event), because the event stream is the metric source and a duplicated
  incident.closed silently corrupts every W10 measure.
- Put the teeth on every guard individually rather than on the pass as a whole. A single mutation that
  turns off "all validation" proves much less than nine mutations each turning off exactly one guard and
  each observed to flip exactly its own fixture.
- Honesty (NG5): the module and this spec both state that the SUFFICIENCY of a drafted criterion and the
  RIGHTNESS of a drafted action are review-lane judgments at promotion time. The mechanical floor is
  existence, structural validity, unreviewed status, and the impossibility of machine promotion.
- Follow the byte-identical engine sync discipline: .veldo/incident_reconcile.py, .veldo/validate.py, and
  .veldo/capabilities.yaml land in engine and every pack byte-identical, and the drift checks end
  empty.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
