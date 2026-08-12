---
schema: veldo.spec/v1
id: WARP-0615
title: the human-touchpoint request record (veldo.request/v1) - a thin envelope that REFERENCES the
  shipped settlement records (approval/decision/verdict) and never extends them, so the frozen
  safety-core readers stay byte-compatible while W3/W5/W6 get one schema to build on (W2 of PLAN-0016)
status: shipped
risk: standard - a schema module (.veldo/request.py, sibling of .veldo/decision.py, engine-synced across the
  eight copies exactly as decision.py is) plus its
  wiring into validate.py, additive event-vocabulary entries, and a selftest block. It touches NO
  protected path (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py and their template twins are
  untouched) and it does NOT modify the frozen settlement readers (policy_check.py, two_key.py,
  decision.py) - it only adds a new record type they never read. No live writes, pure stdlib, gate-
  proven offline. Its IMPORTANCE is critical (it is the schema the entire human-decision surface keys
  on, and getting it wrong would couple or break the safety-core readers), so it must carry a rigorous
  independent adversarial review even though the mechanical footprint is standard-tier
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W2
plan_revision: 1
placement: [contracts]
footprint:
  - .veldo/request.py
  - .veldo/validate.py
  - .veldo/events.py
  - .veldo/init_scaffold.py
  - .veldo/capabilities.yaml
  - .veldo/architecture.yaml
  - engine/.veldo/request.py
  - engine/.veldo/validate.py
  - engine/.veldo/events.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/request.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/events.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-0615-human-touchpoint-request-record.md
  - specs/index.md
  - proof/WARP-0615/**
protected_paths: []
behavior_bearing: true
observability:
  logs: check_requests_dir reports each request it validated and any refusal by name (id, the failing
    field, the reason), so a malformed request surface is diagnosable from the gate output alone.
  error_taxonomy: every refusal is NAMED and fail-closed - a bad schema string, an out-of-vocabulary
    touchpoint/tier/status/impact, a missing required field, a non-positive version, a duplicate request
    id, a decided/accepted request whose bound_artifact digest does not resolve, or a request whose
    settlement record path does not exist each refuse by name; an absent .veldo/requests/ directory is a
    clean no-op (adoption safe), never an error.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Delete the closed-vocabulary refusal at .veldo/request.py:216 so validate_record accepts any
      touchpoint string it is given, and the AC1 assertion that an out-of-vocabulary touchpoint refuses
      (scripts/suites/10_warp_0613_anti_vacuity.py:472) must go red.
    text: A new record type veldo.request/v1 is defined in .veldo/request.py (a sibling of .veldo/decision.py)
      as a THIN ENVELOPE with the fields id, request_hash, touchpoint, tier, impact, required_roles,
      quorum, expires_at, supersedes/superseded_by, bound_artifact, settlement, tracker, and status.
      Closed vocabularies are validated fail-closed by name - touchpoint in {spec_approval, plan_approval,
      decision_choice, review_disposition, risky_action_authorization, escalation}; tier in {low, standard,
      high, critical}; status in the request lifecycle set; impact entries in {data_mutating, money,
      external, irreversible} (FLAGS, never a fifth tier). The record REFERENCES a settlement record
      (approval/decision/verdict) by path; it does NOT contain or duplicate the settlement data, and this
      spec makes NO change to policy_check.py, two_key.py, or decision.py.
  - id: AC2
    falsified_by: >
      Make request_digest at .veldo/request.py:126 return bound_artifact.digest instead of hashing
      DIGEST_FIELDS, which unifies the two hashes this spec forbids unifying (the load-bearing leg of the
      three), and the AC2 separateness assertion at scripts/suites/10_warp_0613_anti_vacuity.py:441 must
      go red.
    text: request_digest(record) is the ONE canonical integrity hash over the request's substance
      (parallel to policy_check.proof_digest and action_executor.proposal_digest), and it is SEPARATE
      from bound_artifact.digest. bound_artifact.digest is POLYMORPHIC per touchpoint - it is the binding
      the eventual settlement reader will use (the commit(s)+paths for an approval that policy_check binds
      on; the action_executor.proposal_digest verbatim for a risky action that two_key binds on; the
      veldo.decision/v1 record digest for a decision-choice) - and it is NEVER fed to the frozen readers.
      The tier of a decision_choice request is DERIVED from the bound decision's risk (single derivation),
      not set independently; an irreversible impact maps to the critical tier (consistent with decision.py).
  - id: AC3
    falsified_by: >
      Delete the duplicate-id refusal loop at .veldo/request.py:383-385, the one guard that exists ONLY in
      the directory scan and so is the load-bearing leg here, and the AC3 assertion that a duplicate request
      id across records is refused (scripts/suites/10_warp_0613_anti_vacuity.py:539) must go red.
    text: check_requests_dir(root, parse, fail) validates every .veldo/requests/*.yaml record STRUCTURALLY
      and is wired into validate.py run_all, in the EXACT adoption-safe, fail-closed, dependency-free style
      of decision.check_decisions_dir - the front-matter parser and the failure reporter are passed in
      (no second YAML parser, no import cycle), an absent .veldo/requests/ directory stands the check down
      and returns clean (byte-identically unaffecting a repo that never uses the surface), a present
      malformed record fails closed by name, and a duplicate request id is refused by name.
  - id: AC4
    falsified_by: >
      Remove decision.decided from EVENT_TYPES at .veldo/events.py:132 while leaving
      request.REQUEST_EVENT_TYPES at .veldo/request.py:104 intact, and the AC4 drift-guard assertion that
      events.py EVENT_TYPES carries the request lifecycle
      (scripts/suites/10_warp_0613_anti_vacuity.py:571) must go red.
    text: The event vocabulary in .veldo/events.py gains request.opened, request.accepted,
      request.rejected, request.superseded, and decision.decided (the settled decision-choice has no event
      today), added to EVENT_TYPES as a conscious contract change with the events drift-guard selftest
      updated to match. No existing event is removed or renamed.
  - id: AC5
    falsified_by: >
      Add a strict unknown-key refusal to decision.validate_record in .veldo/decision.py so a
      veldo.decision/v1 record carrying request_id and request_hash is rejected rather than ignored, and the
      AC5 tolerance assertion at scripts/suites/10_warp_0613_anti_vacuity.py:582 must go red.
    text: The optional back-reference fields request_id and request_hash may be carried on a
      veldo.approval/v1, veldo.decision/v1, or veldo.verdict/v1 record, and the shipped readers TOLERATE them
      - a selftest asserts that policy_check.valid_approval_for, two_key.authorize, and
      decision.validate_record still accept a record that carries the back-reference (they ignore unknown
      fields), so linking a settlement record to its request never breaks the frozen readers. This spec
      adds the fields' MEANING and the tolerance proof; it does not modify the reader modules.
  - id: AC6
    falsified_by: >
      Make the T1 tooth vacuous by leaving the touchpoint-vocabulary line unpatched in the in-memory copy of
      .veldo/request.py, so the mutant still refuses a bad touchpoint, and the T1 assertion that neutralizing
      the closed-vocabulary check lets a bad touchpoint PASS
      (scripts/suites/10_warp_0613_anti_vacuity.py:623) must go red.
    text: A selftest drives the request validator over deterministic fixtures offline (no network) and is
      NON-TAUTOLOGICAL - a well-formed request of each touchpoint validates; a bad schema, an
      out-of-vocabulary touchpoint/tier/status/impact, a missing required field, a duplicate id, and a
      decided/accepted request whose bound_artifact digest does not resolve each fail closed by name; the
      frozen readers accept a back-ref'd record (AC5); and each load-bearing guard carries an in-memory
      source-mutation TOOTH that turns its assertion red while .veldo/request.py stays byte-unchanged
      (neutralizing the closed-vocabulary check lets a bad touchpoint pass; neutralizing the duplicate-id
      guard lets two records share an id; neutralizing the digest-resolves check lets an unbound accepted
      request pass). None of the teeth is vacuous.
required_evidence: [unit]
rollback: git revert; purely additive - a new schema module (engine-synced across the eight copies like
  decision.py) and its validate.py wiring, additive event-vocabulary entries, one capability entry (all
  eight capabilities.yaml copies byte-identical), the new module declared in the contracts area of
  architecture.yaml and added to the init scaffold lay-down (so veldo init stands it up beside its sibling
  decision.py), a selftest block, and this spec; no protected path; no change to the frozen settlement
  readers; pure stdlib.
---

## Intent

Every other item of the human-decision surface (the outbound projection W3, the command-and-receipt
inbound edge W5, the authorization and quorum logic W6) reads and writes the same thing: a human
touchpoint. If that thing is modeled by EXTENDING the shipped settlement records (veldo.approval/v1,
veldo.decision/v1, veldo.verdict/v1), it couples the safety-critical readers those records feed
(policy_check, two_key, decision) to the new surface, and a mistake there breaks the merge gate or the
two-key rule. So the touchpoint is a NEW, THIN ENVELOPE (veldo.request/v1) that REFERENCES a settlement
record and carries all the coupling and projection metadata the frozen readers must never see. Because
those readers ignore unknown fields, the settlement records stay byte-compatible; the envelope is the one
schema W3/W5/W6 build on. This spec builds the envelope, its canonical digest, its fail-closed validator,
and the event vocabulary - and nothing else.

## Context

This is W2 of PLAN-0016 (the approved "Human decisions through Jira" plan, VEL-1). It composes on the
shipped decision organ (veldo.decision/v1 + check_decisions_dir, whose adoption-safe/fail-closed/dependency-
free shape this mirrors), the shipped approval/two-key readers (which it must not break), and the released
event stream. It is the foundation of the phase: W6 (authz) reads the request's tier/roles/quorum, W3
(projection) reads its brief/RISK/bound-digest, and W5 (inbound) writes its settlement + status. Getting
the schema right for all three consumers at once is the whole point of building it first.

## The binding rule (flag 2 from the phase design)

policy_check binds an approval on the COMMIT(s)+paths; two_key binds on a proposal DIGEST. So
bound_artifact.digest cannot be one uniform hash - it is polymorphic, holding whatever the settlement
reader for that touchpoint will actually check. request_hash is a separate integrity hash over the request
substance (for tamper-detection and the material-change rule) and is never handed to a frozen reader. Do
not unify the two or a reader breaks.
