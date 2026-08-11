---
schema: veldo.spec/v1
id: WARP-1202
title: The evidence plane and its read-only access physics (W2 of PLAN-0012)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W2
plan_revision: 2
depends_on: []
placement: [contracts]
footprint:
  - .veldo/evidence.py
  - .veldo/capabilities.yaml
  - .veldo/examples/evidence-sources-example.yaml
  - engine/.veldo/evidence.py
  - engine/.veldo/capabilities.yaml
  - engine/.veldo/examples/evidence-sources-example.yaml
  - packs/*/.veldo/evidence.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1202-the-evidence-plane-access-physics.md
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A versioned evidence-plane source declaration (schema veldo.evidence/v1) exists,
      homed per-repo under .veldo/evidence/*.yaml (a subdirectory the single-level
      .veldo/*.yaml engine glob does not sweep, so it stays per-repo like the
      architecture contract and the incident and remedy records and is never shipped
      in the engine). It declares one or more read-only sources, each naming an id, a
      kind drawn from the read-only source vocabulary (logs, metrics, traces,
      read_replica, and NEVER a primary), an access that MUST be read_only, a
      secret_ref that is a reference (env: or keychain:) and never a raw literal (D4),
      the templated query shapes it permits (a non-empty list), a row-limit and a
      timeout quota, and the sensitive fields it redacts before context. A
      clearly-marked illustrative example ships at
      .veldo/examples/evidence-sources-example.yaml and validates clean via
      python3 .veldo/evidence.py .veldo/examples/evidence-sources-example.yaml. The
      validator FAILS CLOSED by name on a source declared as a primary (or any kind
      outside the read-only vocabulary), an access that is not read_only, a secret
      given as a raw literal instead of a reference, a missing or non-positive
      row-limit or timeout, and a source that declares no templated query shapes; a
      selftest asserts the example validates and that each of these refuses. Adoption
      safe: with no .veldo/evidence/ directory the check stands down and returns clean
      (a repository that never configures the responder is byte-identically
      unaffected); the moment a config exists it is validated and fails closed, and a
      duplicate source id within a plane is refused.
  - id: AC2
    text: >
      The credential seam is read-only PHYSICS, not a policy the responder must
      remember: a write is structurally impossible, not merely disallowed by a flag
      that could be flipped. A resolved read-only credential (ReadOnlyCredential)
      exposes only a read handle (open_read returns a ReadHandle), and the read handle
      exposes only a query operation: neither the credential nor the handle carries
      any write, insert, update, delete, execute, or mutate method, so the write path
      does not exist on the responder's types. The NEGATIVE TEST AT THE CREDENTIAL
      SEAM is proven against a fake evidence plane: a write submitted with the
      responder's read-only credential is refused AT THE CREDENTIAL SEAM (the plane
      authorizes a write by the credential's granted role, and a read-only credential
      grants only read), the refusal names the credential as the reason and not a
      policy prompt, and the fake store is unchanged afterward. The refusal is proven
      NON-VACUOUS: the SAME write submitted with a write-granted credential (which the
      responder never holds) does apply, so it is the read-only credential that makes
      the write impossible, not a globally disabled store. A selftest asserts the
      type-level absence (no write method on either type), the seam-level refusal (a
      read-only write refused at the seam with the store unchanged and the reason
      named), and the non-vacuity (a write-granted credential applies the same write).
  - id: AC3
    text: >
      Read-only is not harmless, so the read path is a BROKER, not a raw connection:
      reads can exfiltrate, overload, or cross tenant lines. Every query passes
      templated-shape enforcement (only a query template the source declares, with its
      declared parameters; a free-form or undeclared-template query is refused by
      name), a row-limit quota (a query whose result would exceed the source's row cap
      is refused), a rate quota (queries beyond the source's rate cap within the window
      are refused), a per-query timeout (a query whose estimated duration exceeds the
      source's timeout is refused), and PII REDACTION that strips the source's declared
      sensitive fields from every returned row BEFORE the rows enter the caller's
      context. Every query, allowed or refused, lands in a FULL AUDIT LOG carrying the
      source, the template, the parameters, the decision, and the row count. A selftest
      proves each refusal by name with a positive control (a declared, in-quota,
      in-timeout query succeeds and returns redacted rows), proves seeded PII never
      appears in the returned rows, and proves the audit log carries one entry per
      query issued during a seeded investigation.
  - id: AC4
    text: >
      The live edge is a fail-loud reference seam: wiring the evidence plane to a real
      logs, metrics, or trace store or a read replica is a separate, per-system,
      human-approved enablement act (NG1) and never happens inside the gate. The live
      edge (LiveEvidencePlane) is a reference seam that FAILS LOUD: every method raises
      EvidencePlaneError naming the deferral, so a runtime that wants live evidence must
      inject a real adapter, exactly as executor.LiveLoop refuses to fabricate a build
      (a gate that silently connected to production would be worse than one that
      refuses). All proof is offline against the fake plane. The secret reference the
      credential authenticates with is resolved at the seam (an env variable or an OS
      keychain reference, per D4) and the raw secret NEVER enters the credential's
      context view, its repr, the audit log, a proof, or any returned row (C5). A
      selftest asserts the live edge raises on connect and on read, that the fake plane
      serves the read path offline, that a raw-literal secret reference is refused, and
      that a resolved credential's context view and repr redact the secret.
  - id: AC5
    text: >
      The check has TEETH proven by mutation (the anti-vacuity rule C1), each observed
      RED then reverted byte-identical: the CREDENTIAL-SEAM negative test turns RED when
      the responder's credential is granted write (the write then applies, proving the
      physics is the read-only grant and not a disabled store); a
      read-handle-gains-a-write-method mutation turns the read-only-handle source check
      RED; dropping a source's redact fields leaks the seeded PII (the redaction check
      turns RED); and a free-form query, an over-row-cap query, an over-rate query, and
      an over-timeout query each turn the broker check RED. Mirroring the no-detach
      boundary, evidence.py spawns no detached or background process (a
      subprocess.Popen(..., start_new_session=True) mutation turns the no-detach check
      RED) and the module imports only pathlib. .veldo/evidence.py ships in the engine
      and is re-synced byte-identical across engine and all 6 packs;
      .veldo/capabilities.yaml gains ONE honest mechanical entry (evidence_plane) in
      every copy and is re-synced likewise; the illustrative example is synced root and
      engine for init lay-down (template sync and pack drift pass). The
      capabilities entry names exactly what ships and defers honestly: the responder
      investigation loop (WARP-1204, W4), the action whitelist (WARP-1205, W5), the
      execution organ (WARP-1206, W6), and the two-key rule (WARP-1207, W7) are
      referenced, never implied built; the live connection to any real system is a
      separate per-system act; and landing the check into validate.py run_all and
      lay-down via init is WARP-1211 (W11). The full gate is GREEN (selftest, contracts,
      generated, docs, lint, secret scan, template sync, pack drift, shape gate), RULE
      #1 is clean (ASCII hyphen only, no em or en dash, no prose double-hyphen), and no
      protected path is touched (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py
      and their engine twins unchanged). Dogfood: this spec's placement
      [contracts] resolves to a declared area and its footprint tier is standard (a
      single area, no boundary crossing; .veldo/evidence.py is a placeless engine module
      outside the contract areas, like the sibling organ modules).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine module (.veldo/evidence.py, re-synced
  byte-identical across engine and the 6 packs), one illustrative example
  artifact, and one capabilities entry, plus a selftest block and this spec. Nothing
  consumes the evidence plane for enforcement yet: the first consumer is the responder
  investigation loop WARP-1204 (W4), and gate wiring into validate.py run_all plus the
  init lay-down is WARP-1211 (W11), so the validator is not wired into verify.sh or
  validate.py run_all and removing it changes no gate behavior. A repository with no
  .veldo/evidence/ directory is unaffected either way (the adoption-safe posture), so
  there is no migration and nothing to unwind; evidence-plane source declarations are
  inert per-repo data and the module opens no live connection to any real system.
---

## Intent

This is the second root of PLAN-0012 (the frontier after approval is W1, W2, W3, and
W9) and the machinery behind Invention #3's design center: an agent with production
access can destroy a company by simply doing the wrong thing there, so its safety
cannot be a policy it follows, it has to be an architecture it cannot escape. The
evidence plane is where the responder investigates, built as read-only PHYSICS: the
credential the responder runs on cannot write, not because it agrees not to but because
the write path structurally does not exist. This item ships that seam against a FAKE
evidence plane, with the negative test at the center: a write attempted through the
responder's access fails at the credential seam, not at a policy prompt.

## Context

- The design center the plan binds everywhere (O1): privilege separation is physics,
  not promise. The investigating responder runs on credentials that cannot write:
  read-only roles against read replicas and log, metric, and trace stores, never a
  primary; query rate and row limits apply; PII is redacted before anything enters the
  agent's context; and every query it runs lands in a full audit log. The credential
  makes the wrong write impossible; nothing depends on the agent agreeing to behave.
- Read-only is NOT harmless (the WARP-1107 tripwire lesson and the incident lessons):
  reads can exfiltrate data, overload a source, or cross a tenant line. So the read path
  is a BROKER, not a raw connection: templated query shapes only (no free-form text), a
  row cap and a rate cap, a per-query timeout, redaction before context, and an audit
  entry per query. The broker is where a read that would exfiltrate or overload is
  refused by name.
- The credential seam is TWO layers of physics. Structurally, the responder's types
  carry no write capability: a ReadOnlyCredential yields only a ReadHandle, and the read
  handle has only a query operation, so a write cannot even be expressed. And at the
  seam, even a raw crafted write submitted with the responder's credential is refused
  because the plane authorizes a write by the credential's granted role and a read-only
  credential grants only read. The refusal is proven non-vacuous: a write-granted
  credential (which the responder never holds) applies the same write, so it is the
  read-only grant that makes the write impossible.
- The live edge is a fail-loud reference seam, mirroring executor.LiveLoop: the
  mechanical, hermetic path (the fake plane, the broker, the redaction, the audit) is
  real, and the live connection to a real source fails LOUD so an adopting runtime must
  inject a real adapter. A gate that silently connected to production would be worse
  than one that refuses (NG1: live wiring is a separate per-system human-approved act).
- Credentials per D4/C5: all credentials are secret references resolved at the seam (an
  env variable or an OS keychain reference), never a raw literal in a file, prompt,
  proof, or log; an external secrets manager stays an optional per-repo extension, never
  a required dependency. The raw secret never enters the responder's context.
- The module is modeled on the sibling organs .veldo/incident.py and .veldo/decision.py:
  structural, closed-vocabulary checks over the one front-matter subset
  (validate.parse_yamlish), no second parser, no import cycle; the caller injects the
  parser and the failure reporter. Two postures the plan binds everywhere: adoption safe
  (no .veldo/evidence/ directory stands the check down) and fail closed (the moment a
  config exists it is validated and refuses anything malformed). C1 anti-vacuity: in
  this plan the refusals are the product, so every safety property ships as a negative
  test that proves the refusal.

## Out of scope

- No responder loop. The in-session agent that, given an incident, investigates over the
  evidence plane and the intent corpus and produces a cited diagnosis and a proposal, is
  WARP-1204 (W4). This item ships the plane the responder will read through; it does not
  investigate or propose anything, and its harness carries no execution capability.
- No intent corpus. The mechanical query surface over specs, proofs, verdicts, and git
  is WARP-1203 (W3). The evidence plane reads declared runtime sources (logs, metrics,
  traces, replicas); the corpus reads the method's own records. They are separate roots.
- No execution organ. The action whitelist is WARP-1205 (W5), the separate privileged
  executor with the autonomy ladder, kill switch, budgets, and canary-first is WARP-1206
  (W6), and the two-key rule is WARP-1207 (W7). The evidence plane reads and only reads;
  it shares no credential and no code path with any of them.
- No observability platform (NG5). This item builds no log, metric, or trace store; the
  evidence plane reads DECLARED existing sources through thin adapters, and improving a
  system's instrumentation is that system's work.
- No live wiring (NG1). Connecting the plane to any real source is a separate per-system
  human-approved enablement act with its own risk review; the live edge fails loud and
  no live connection is opened inside the gate. All proof is offline against a fake plane.
- No gate wiring and no emission. Landing the check into validate.py run_all and the init
  lay-down is WARP-1211 (W11). W2 ships the module runnable standalone (python3
  .veldo/evidence.py) and exercised through validate.parse_yamlish and validate.fail in
  the selftest; it does not wire it into the gate. This deferral matches W1.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy.yaml, .veldo/policy_check.py and their engine twins are untouched
  (protected paths). The module lives in the placeless engine module .veldo/evidence.py,
  outside the declared contract areas, like the sibling organ modules.

## Notes

- Keep the module dependency free (pathlib only) and follow the byte-identical engine
  sync discipline: .veldo/evidence.py and .veldo/capabilities.yaml land in engine
  and every pack byte-identical, and the drift checks end empty. The evidence-plane source
  declarations are per-repo (like architecture.yaml and the incident and remedy records),
  and homing them in .veldo/evidence/ keeps them out of the .veldo/*.yaml single-level
  engine glob structurally, so a fresh repository starts config-free and adoption safe.
  The illustrative example ships in .veldo/examples so an adopter sees the format; it is
  clearly marked illustrative and describes no real system.
- Put teeth on the check by mutating in-memory copies of the module source and the shipped
  example and observing the check go red before reverting; a mechanical check that cannot
  refuse is exactly the vacuity C1 forbids. The load-bearing teeth are the physics ones:
  the credential-seam negative test goes red when the responder's credential is granted
  write (proving the read-only grant is what blocks the write, not a disabled store), and
  a read handle that gains a write method turns the read-only-handle source check red.
- No detached process (NG3 and the no-detach lesson from WARP-1107 and WARP-1010):
  evidence.py starts no process, thread, or timer; a mutation that introduces one turns
  the no-detach check red. The module is runnable in-session only.
- Honesty (NG5 and the WARP-1101 over-attestation lesson): do not imply the responder,
  the executor, the whitelist, or the two-key rule are built, and do not imply the plane
  connects to anything live. This repository ships the read-only evidence-plane seam and
  its structural validator with an illustrative example, proven offline against a fake
  plane; the organs that consume it and the live connection are honestly named as later
  and separate acts.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
