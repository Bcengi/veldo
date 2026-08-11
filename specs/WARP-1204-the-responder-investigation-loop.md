---
schema: veldo.spec/v1
id: WARP-1204
title: The responder investigation loop, L0 investigate and L1 propose (W4 of PLAN-0012)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W4
plan_revision: 2
depends_on: [WARP-1201, WARP-1202, WARP-1203]
placement: [contracts]
footprint:
  - .veldo/responder.py
  - .veldo/capabilities.yaml
  - engine/.veldo/responder.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/responder.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1204-the-responder-investigation-loop.md
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The responder investigation loop (schema veldo.responder/v1, module .veldo/responder.py) is
      the in-session L0/L1 agent brief and harness, and the FIRST CONSUMER of the three roots of
      PLAN-0012: given an incident record (W1's veldo.incident/v1) it composes the intent corpus
      (W3, read-only) and a read-only evidence handle (W2, query only) into an investigation
      context and, through a DELEGATED fresh-context reasoning seam, reaches a CITED diagnosis.
      investigate(incident) is the L0 read: it returns a cited Diagnosis (governed, the governing
      spec, the real artifact citations that ground it) and no proposal. The intelligent diagnosis
      is a delegated step: the harness builds the mechanical control logic (assemble the corpus
      governance trace and the read-only evidence context, hold the loop at L0/L1, ground every
      citation, structurally exclude execution, and validate the emitted proposal) and the
      reference LiveResponder FAILS LOUD, raising ResponderError rather than fabricate a diagnosis,
      exactly as executor.LiveLoop.build/review and the dispatch, shape, and decision reviewers
      refuse to fabricate their judgment. The harness is dependency free (pathlib at module top,
      importlib lazily inside the opener), receives the W1 contract module and the built corpus
      INJECTED so there is no second YAML parser and no import cycle, and reads the evidence plane
      ONLY through a read-only ReadHandle: it opens no live connection (NG1) and starts no process,
      thread, or timer (NG3). OFFLINE conformance is the proof: over a seeded fake incident
      affecting a governed spec, with a read-only handle over a FAKE evidence plane, investigate
      returns a governed diagnosis citing the real corpus artifacts, and with no responder agent
      wired the LiveResponder raises rather than invent a diagnosis. A selftest asserts the offline
      investigate path and the fail-loud default over the seeded incident.
  - id: AC2
    text: >
      THE HARNESS CONTAINS NO EXECUTION CAPABILITY AT ALL - the load-bearing safety property
      (Invention #3, O2/C4), structural and not a policy the responder must remember. Diagnosis
      and execution are separate organs: the responder investigates and proposes and it CANNOT
      execute anything, because the write/execute path does not exist on its type. ResponderHarness
      carries NONE of the execution methods (no execute, apply, run, remediate, mutate, write,
      deploy, perform, act, rollback, restart, scale, commit_change, submit_write, or open_write
      method), the only production-touching capability it holds is a read-only ReadHandle from the
      evidence plane (query only, W2's physics), and it holds no write-capable credential; execution
      is a SEPARATE privileged organ on its own credentials and code path, WARP-1206 (W6), NOT built
      here. The property is proven NON-VACUOUS by mutation (C1, the refusals are the product): a
      subclass that ADDS an execute method turns the no-execution check RED, so the check cannot pass
      vacuously. A selftest asserts hasattr is false for every method name in the enumerated
      FORBIDDEN_EXECUTION_METHODS shape on ResponderHarness (and on a constructed harness), that the
      module source defines none of them, that the harness holds only a query-only read handle, and
      that the ADD-an-execute-method mutation turns the check RED then reverts.
  - id: AC3
    text: >
      THE LADDER FLOOR IS READ-ONLY, and the loop degrades down, never up (O3/C3, D2). The harness
      operates ONLY at L0 (investigate) or L1 (propose): it is constructed at one of those two levels
      and REFUSES by name to be constructed at L2 or L3 (the execution rungs), which are a separate
      organ (WARP-1206, W6; D2: start and stay at L0/L1, L3 disabled by default and may never be
      enabled, a legitimate permanent state). propose requires L1: at L0 (the investigate-only floor)
      propose REFUSES by name and degrades down, never up (C3); investigate is available at both L0
      and L1. The refusals are proven with positive controls so the check cannot pass vacuously:
      construction at L0 and L1 succeeds, investigate returns a governed diagnosis at L0, and propose
      emits a validated proposal at L1. A selftest asserts the L2 and L3 construction refusals (named),
      the propose-at-L0 refusal (named, degrade down), the investigate-at-L0 positive control, and the
      construct-at-L0/L1 positive controls.
  - id: AC4
    text: >
      DIAGNOSIS FROM ARTIFACTS, NEVER FABRICATED (O4/C1, the refusals are the product), and the
      proposal is validated structurally. Every citation in a diagnosis must resolve to a REAL
      artifact in the assembled investigation context - a corpus artifact path the governance trace
      cites (the governing spec, its proof, its verdict), a recorded change commit (git or the event
      stream) touching the governing spec's footprint, or an evidence query the reasoner ACTUALLY
      issued and the broker ALLOWED during this investigation (an audit entry) - or the harness
      REFUSES by name (FABRICATED DIAGNOSIS REFUSED); a responder that fabricated a citation would be
      worse than one that admitted it cannot diagnose. A diagnosis of a GOVERNED incident must cite at
      least one corpus artifact, so it rests on the record and not on evidence alone. Graceful
      degradation with no PLAN-0011 architecture contract (C7, the O4 measure): the corpus stands down
      to spec and git level (areas None, contract_present False) and the harness still reaches a cited
      diagnosis of the governing spec. At L1 the harness EMITS a veldo.remedy/v1 proposal, VALIDATED
      structurally through the W1 contract (INC.validate_remedy plus INC.bind_remedy, reusing the one
      parser, no second validator) so a proposal missing any element is refused (fail closed), with the
      required human authorization DERIVED mechanically by the harness (not the reasoner): an
      irreversible or data-mutating action forces required_authorization two_key so the two-key path
      W7 has an exact binding, otherwise human_confirmation. Proven NON-VACUOUS: a fabricated citation
      is refused while a diagnosis citing only real artifacts succeeds (positive control), and a
      governed-incident diagnosis citing only an evidence query (no corpus artifact) is refused. A
      selftest asserts the fabricated-citation refusal and the positive control, the corpus-citation
      requirement for a governed incident, the evidence-query grounding when a query was issued, the
      no-contract spec-and-git-level degradation, the derived authorization (human_confirmation for a
      reversible non-data-mutating action, two_key for an irreversible one and for a data-mutating
      one), and the emitted proposal validating clean through the W1 contract.
  - id: AC5
    text: >
      The harness has TEETH proven by mutation (the anti-vacuity rule C1), each observed RED then
      reverted byte-identical, and it is IN-SESSION with no detached process. The load-bearing teeth
      are the AC2 no-execution mutation (adding an execute method turns the structural check RED), the
      AC3 floor (construction at L2 refuses while L0/L1 do not), and the AC4 grounding mutation (a
      fabricated citation turns the no-fabrication check RED). Mirroring the no-detach boundary (NG3
      and the WARP-1107/WARP-1010 lesson), .veldo/responder.py spawns no detached or background process:
      it imports pathlib at module top and importlib LAZILY inside the batteries-included opener, uses
      no subprocess, thread, or timer, and a subprocess.Popen(..., start_new_session=True) mutation
      turns the no-detach check RED. .veldo/responder.py ships in the engine and is re-synced
      byte-identical across engine and all 6 packs; .veldo/capabilities.yaml gains ONE honest
      mechanical entry (responder_loop) in every copy and is re-synced likewise (template sync and pack
      drift pass). The capabilities entry names exactly what ships and defers honestly: it is the first
      consumer of the incident and remedy contracts (WARP-1201, W1), the evidence plane (WARP-1202, W2),
      and the intent corpus (WARP-1203, W3), and the action whitelist (WARP-1205, W5), the execution
      organ (WARP-1206, W6), the two-key rule (WARP-1207, W7), the compressed loop and reconciliation
      (WARP-1208, W8), and the support metrics (WARP-1210, W10) are referenced, never implied built; the
      live connection to any real system is a separate per-system act (NG1); and landing a responder
      check into validate.py run_all and lay-down via init is WARP-1211 (W11). The full gate is GREEN
      (selftest, contracts, generated, docs, lint, secret scan, template sync, pack drift, shape gate),
      RULE #1 is clean (ASCII hyphen only, no em or en dash, no prose double-hyphen), and no protected
      path is touched (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py and their engine
      twins unchanged). Dogfood: this spec's placement [contracts] resolves to a declared area and its
      footprint tier is standard (a single area, no boundary crossing; .veldo/responder.py is a placeless
      engine module outside the contract areas, like the sibling organ modules).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine module (.veldo/responder.py, re-synced byte-identical
  across engine and the 6 packs) and one capabilities entry, plus a selftest block and this
  spec. Nothing consumes the responder for enforcement: the harness is an in-session organ, its first
  downstream is the compressed loop WARP-1208 (W8) once an executor exists, and landing a responder
  check into validate.py run_all plus the init lay-down is WARP-1211 (W11), so the module is not wired
  into verify.sh or validate.py run_all and removing it changes no gate behavior. The harness reads
  only the recorded corpus and a read-only evidence handle and opens no live connection, so there is
  no migration and nothing to unwind. A repository that never configures the responder is
  byte-identically unaffected either way (the harness is inert until an incident and a wired responder
  are supplied, and the reference reasoner fails loud).
---

## Intent

This is the fourth work item of PLAN-0012 and the first CONSUMER of its three roots: the incident
and remedy contracts (W1), the read-only evidence plane (W2), and the intent corpus at runtime (W3).
It is Invention #3's design center made operational. When agents author everything, the five-minute
diagnosis that used to be a free byproduct of authorship is gone, because whoever gets paged is a
stranger to the code. But the method already produces what the old world never had, so the responder
that replaces the hero does not need to have written the code: it reads the record (the corpus) and
queries the read-only evidence, reaches a diagnosis every claim of which cites a real artifact, and
at L1 proposes a remedy. This item ships that harness, proven OFFLINE against a fake evidence plane
and a seeded incident (NG1), with two structural properties at the center: the harness contains no
execution capability at all (diagnosis and execution are separate organs, and the responder
structurally cannot execute), and the loop holds the read-only floor (L0 investigate, L1 propose,
and never higher).

## Context

- The outcome this serves (O4): diagnosis comes from artifacts, not memory. The responder queries
  the intent corpus the method already produces (what specification governs this behavior, what
  changed here recently, what did its proof cover, and where the affected module sits in the declared
  shape when an architecture contract exists) so a party that never wrote the code reaches a cited
  diagnosis at machine speed. O4's measure is a seeded fake incident diagnosed offline from the corpus
  alone, citing the governing spec, the implicated change, and its proof, degrading gracefully to spec
  and git level when no architecture contract is present. This item ships the harness that reads the
  corpus (W3) and the read-only evidence (W2) and, through a delegated fresh-context reasoner, composes
  and grounds that cited diagnosis and, at L1, the veldo.remedy/v1 proposal (W1).
- The design center the plan binds everywhere (O2/C4, from the founder's framing that production
  access is existential risk): diagnosis and execution are separate organs, and the responder's
  harness contains NO execution capability at all. This item encodes that structurally: the harness
  type carries no execute, apply, run, remediate, mutate, write, deploy, restart, or scale method, so
  a write cannot even be expressed, mirroring how the evidence plane's ReadHandle carries no write
  method. The only production-touching capability the harness holds is a read-only ReadHandle (query
  only, W2's physics); it holds no write-capable credential. The execution organ is WARP-1206 (W6), on
  its own credentials and code path, not built here.
- The ladder floor is read-only (O3, D2): the harness operates ONLY at L0 (investigate) or L1
  (propose) and refuses to be constructed at the execution rungs L2 or L3; propose requires L1 and, at
  the L0 investigate-only floor, degrades down, never up (C3). D2 resolves the plan to start and stay
  at L0/L1, with L3 disabled by default and a legitimate permanent off state.
- The intelligent diagnosis is a DELEGATED fail-loud seam (RULE #6, the right architecture). The
  mechanical control logic is built here; the judgment a stranger reaches by reading the record is a
  fresh-context step delegated through the Responder seam, exactly like executor.LiveLoop.build/review,
  the dispatch LiveReviewer, and the shape and decision reviewers. The reference LiveResponder is wired
  to nothing and RAISES rather than fabricate a diagnosis; an adopting runtime injects a responder that
  dispatches a genuinely fresh context. And the harness GROUNDS the answer: every citation must resolve
  to a real artifact in the assembled context (a corpus artifact path, a recorded change commit, or an
  evidence query actually issued and allowed) or it is refused by name. Diagnosis from artifacts means
  the answer rests on a real artifact or the harness refuses.
- Two postures the plan binds everywhere, shared with the sibling organs: adoption safe (the harness is
  inert until an incident and a wired responder are supplied, and the reference reasoner fails loud) and
  fail closed (a malformed incident, an unwired reasoner, a fabricated citation, an above-floor
  construction, a propose below its level, or a proposal missing any element each refuse by name). C1
  anti-vacuity: in this plan the refusals are the product, so every safety property ships as a negative
  test that proves the refusal, non-vacuous by a mutation that turns the check red.

## Out of scope

- No execution organ. The responder proposes and stops; it structurally cannot execute. The action
  whitelist is WARP-1205 (W5), the separate privileged executor with the autonomy ladder, kill switch,
  budgets, and canary-first is WARP-1206 (W6), and the two-key rule is WARP-1207 (W7). This harness
  shares no credential and no code path with any of them and carries no execution capability at all.
- No compressed loop and no reconciliation. Flowing the incident through the emergency lane,
  reconciling a closed incident into regression criteria, and self-maintaining runbook actions from
  real incidents are WARP-1208 (W8). This item produces the cited diagnosis and the proposal; it does
  not close an incident or emit lifecycle events.
- No live wiring (NG1). The harness reads a read-only evidence handle over a FAKE plane; connecting to
  any real logs, metrics, trace store, or read replica is a separate per-system human-approved
  enablement act, and the reference LiveResponder and the plane's live edge fail loud. All proof is
  offline over a seeded incident.
- No new instrumentation and no store (NG5). The harness reads the recorded corpus (W3) and a
  read-only evidence handle (W2); it builds no database, adds no event type, and changes no artifact.
- No gate wiring. Landing a responder check into validate.py run_all and the init lay-down is
  WARP-1211 (W11). W4 ships the module runnable standalone (python3 .veldo/responder.py) and exercised
  through the injected contract module and corpus in the selftest; it does not wire it into the gate,
  so validate.py is unedited and stays under its module_lines budget. This deferral matches W1, W2, W3.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). The module
  lives in the placeless engine module .veldo/responder.py, outside the declared contract areas, like
  the sibling organ modules.

## Notes

- Keep the module dependency free (pathlib at module top, importlib lazily inside the opener) and
  follow the byte-identical engine sync discipline: .veldo/responder.py and .veldo/capabilities.yaml land
  in engine and every pack byte-identical, and the drift checks end empty. The responder
  reuses the W1 contract module (INC.validate_remedy and INC.bind_remedy, no second parser) and the
  built corpus (W3, injected), so there is one truth for the artifacts it validates and reads.
- Put teeth on the harness by mutating in-memory copies and observing the check go red before
  reverting; a harness whose safety cannot refuse is exactly the vacuity C1 forbids. The load-bearing
  teeth are the STRUCTURAL ones: a subclass adding an execute method turns the no-execution check red,
  construction at L2 refuses while L0/L1 do not, a fabricated citation turns the no-fabrication check
  red, and a detached-spawn injection turns the no-detach check red.
- No detached process (NG3 and the no-detach lesson): responder.py starts no detached or background
  process, thread, or timer; it uses no subprocess at all, and a Popen(start_new_session=True) mutation
  turns the no-detach check red. The module is runnable in-session only.
- Honesty (NG5 and the over-attestation lesson): do not imply the executor, the whitelist, the two-key
  rule, or the compressed loop are built, and do not imply the harness connects to anything live. This
  repository ships the in-session L0/L1 responder harness that reads the corpus and a read-only evidence
  handle and emits a cited diagnosis and a validated proposal, proven offline against a fake plane and a
  seeded incident; the organs that consume the proposal and the live connection are honestly named as
  later and separate items, and the intelligent diagnosis itself is a delegated fresh-context seam that
  fails loud rather than fabricate.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
