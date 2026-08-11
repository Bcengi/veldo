---
schema: veldo.spec/v1
id: WARP-1203
title: The intent corpus at runtime (W3 of PLAN-0012)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W3
plan_revision: 2
depends_on: []
placement: [contracts]
footprint:
  - .veldo/intent_corpus.py
  - .veldo/capabilities.yaml
  - engine/.veldo/intent_corpus.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/intent_corpus.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1203-the-intent-corpus-at-runtime.md
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The intent corpus (schema veldo.intent_corpus/v1, module .veldo/intent_corpus.py) is
      built FROM the project's OWN recorded artifacts and reuses recorded data only, adding
      no new store, no new parser, and no new instrumentation (NG5). build_corpus INDEXES
      the existing record through the repo's OWN readers, injected, never reimplemented: the
      one front-matter parser (validate.parse_yamlish) for specs and plans, json for proofs
      and verdicts, validate.proof_digest for a proof's canonical identity,
      validate.plan_registry for the plans, validate.load_repo_contract for the architecture
      contract, and .veldo/decision.py load_record for decision records. It indexes the
      specs and their acceptance criteria, the proof manifests (criteria statuses, checks,
      the bound commit, the proof digest), the review verdicts, the plans the specs bind to,
      the recorded decisions, the event stream (.veldo/events.jsonl), and the architecture
      contract when present. open_corpus is the batteries-included opener that loads
      validate.py and decision.py BY PATH (one parser, no import cycle) and wires these
      readers. FAILS CLOSED by name, at build time, on a malformed corpus artifact: a spec
      with no YAML front matter, a spec front matter outside the parser subset, and a proof
      manifest that is not valid JSON each raise IntentCorpusError naming the artifact.
      Adoption safe: a repository with no specs and no proofs builds an EMPTY corpus whose
      empty property is true and whose every query stands down (an ungoverned Trace or an
      empty change list, no error, byte-identically unaffected). A selftest asserts the
      corpus builds over this repository and indexes the real specs, proofs, and verdicts,
      asserts a malformed spec and a malformed proof each refuse at build time, and asserts
      the empty tree stands down.
  - id: AC2
    text: >
      The runtime query interface is a READ over the record (in-session, read-only) that
      traces a behavior or a spec to its governing artifacts. trace(spec_id) returns the
      governance chain: what the spec PROMISED (its acceptance criteria), what PROVED it
      (the proof with its per-criterion statuses, its checks, its bound commit, and its
      proof digest), and the VERDICT that reviewed it, with citations listing the REAL
      artifact paths the answer rests on (the spec file, the proof manifest, the verdict).
      governing_spec(behavior) resolves a behavior to its governing spec by a recorded spec
      id or by a declared footprint match (reporting every candidate). proof_for_commit
      (commit) traces a change to the proof and verdict whose recorded commit it matches.
      recent_changes(path) reads the change log from BOTH sources the method records: git
      history (a synchronous, in-session git log over the path) AND the event stream (the
      recorded events whose commit matches). area_of(module_path) resolves a module to its
      architecture-contract area. trace_incident(incident) assembles the artifact-grounded
      trace an incident record resolves to (its governing spec, criteria, proof, verdict,
      the recent changes touching the spec's footprint, and the areas when a contract
      exists). A selftest proves, over this repository, that trace of a known spec cites its
      real criteria, proof (statuses, checks, digest, commit), and verdict; that
      governing_spec resolves both by spec id and by footprint; that proof_for_commit
      traces a change to its proof and verdict; that recent_changes returns entries from git
      AND from the event stream (proven with an injected deterministic git reader); and that
      trace_incident assembles the governing trace for a seeded incident record.
  - id: AC3
    text: >
      Diagnosis from artifacts is ARTIFACT-GROUNDED, never fabricated: the load-bearing
      guarantee and, per C1, the product. A behavior that no recorded artifact governs
      returns a truthful Trace with governed false whose reason names "no governing
      artifact" and which carries NO invented spec, criterion, proof, or verdict, so an
      honest absence can never be mistaken for a grounded answer. A spec that has no
      recorded proof or no recorded verdict traces with proof None or verdicts empty (the
      absence is reported, never filled with a fabricated one). This is proven NON-VACUOUS
      by mutation, each observed RED then reverted: a resolver mutated to FABRICATE a
      governor for an ungoverned behavior (returning an arbitrary spec instead of the
      ungoverned Trace) turns the no-fabrication check RED, and a trace mutated to
      FABRICATE a proof for a spec whose proof was dropped from the corpus turns the
      proof-grounding check RED. And the query surface FAILS CLOSED by name on a malformed
      query: an empty or non-string spec id, path, behavior, or commit, and an incident that
      names neither an affected spec nor an affected behavior, each raise IntentCorpusError.
      A selftest asserts the ungoverned Trace (no fabrication), the reported absence of a
      missing proof or verdict, the two fabrication mutations turning their checks RED, and
      the malformed-query refusals.
  - id: AC4
    text: >
      Adoption safe and the cross-plan join is SOFT (C7), degrading down and never faking a
      join. When a PLAN-0011 architecture contract exists, area_of resolves a module to the
      declared areas it belongs to and trace attaches the areas a spec's footprint and
      placement fall into; when NO contract exists the corpus STANDS DOWN honestly to spec
      and git level: area_of returns contract_present false and areas None, trace attaches
      areas None, and trace_incident still resolves the governing spec, its proof, its
      verdict, and the recent changes (spec and git level) without a contract, so a party
      that never wrote the code still reaches a cited answer. The join is never faked: an
      absent contract yields None, never an invented area. A selftest proves both paths over
      a temp corpus: with a contract, area_of and trace resolve the area; with no contract,
      area_of and trace stand down to None and trace_incident still returns the governing
      spec, proof, verdict, and git-level changes.
  - id: AC5
    text: >
      The corpus has TEETH proven by mutation (the anti-vacuity rule C1), each observed RED
      then reverted byte-identical, and it is IN-SESSION with no detached process. The
      load-bearing teeth are the no-fabrication and proof-grounding mutations of AC3 and the
      C7 stand-down of AC4. Mirroring the no-detach boundary, .veldo/intent_corpus.py spawns
      no detached or background process: its only external program is a synchronous,
      in-session git log over this repository's own history, with subprocess imported LAZILY
      inside the git reader exactly as fleet.py imports it for its git worktree helper, so
      the module top imports no process or thread machinery, and a
      subprocess.Popen(..., start_new_session=True) mutation turns the no-detach check RED
      while the synchronous git read (subprocess.run over git, never Popen) is present.
      .veldo/intent_corpus.py ships in the engine and is re-synced byte-identical across
      engine and all 6 packs; .veldo/capabilities.yaml gains ONE honest mechanical
      entry (intent_corpus) in every copy and is re-synced likewise (template sync and pack
      drift pass). The capabilities entry names exactly what ships and defers honestly: the
      responder investigation loop (WARP-1204, W4) is the first consumer that reads this
      corpus and the evidence plane and produces a cited diagnosis and a proposal (this
      module is the query surface it reads, not the agent, and it emits no diagnosis or
      proposal); the evidence plane (WARP-1202, W2), the action whitelist (WARP-1205, W5),
      the execution organ (WARP-1206, W6), and the two-key rule (WARP-1207, W7) are
      referenced, never implied built; and landing a corpus check into validate.py run_all
      and lay-down via init is WARP-1211 (W11). The full gate is GREEN (selftest, contracts,
      generated, docs, lint, secret scan, template sync, pack drift, shape gate), RULE #1 is
      clean (ASCII hyphen only, no em or en dash, no prose double-hyphen), and no protected
      path is touched (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py and their
      engine twins unchanged). Dogfood: this spec's placement [contracts] resolves
      to a declared area and its footprint tier is standard (a single area, no boundary
      crossing; .veldo/intent_corpus.py is a placeless engine module outside the contract
      areas, like the sibling organ modules).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one engine module (.veldo/intent_corpus.py, re-synced
  byte-identical across engine and the 6 packs) and one capabilities entry, plus
  a selftest block and this spec. Nothing consumes the corpus for enforcement: the corpus
  is a read surface, its first consumer is the responder investigation loop WARP-1204 (W4),
  and landing a corpus check into validate.py run_all plus the init lay-down is WARP-1211
  (W11), so the module is not wired into verify.sh or validate.py run_all and removing it
  changes no gate behavior. The corpus reads only recorded artifacts and opens no live
  connection, so there is no migration and nothing to unwind. A repository with no specs
  and no proofs builds an empty corpus that stands down either way (the adoption-safe
  posture).
---

## Intent

This is the third root of PLAN-0012 (the frontier after approval is W1, W2, W3, and W9)
and the machinery behind Invention #3's design center for diagnosis: when agents author
everything, the five-minute diagnosis that used to be a free byproduct of authorship is
gone, because whoever gets paged is a stranger to the code. But the method already
produces what the old world never had: every behavior traces to a specification and its
acceptance criteria, every change to its proof and its verdict, every module to its place
in the declared shape. So the responder does not need to have written the code. It asks
the record: what specification governs this behavior, what did it promise, what proved it,
what changed here recently, and where does the affected module sit in the declared shape.
This item ships that query surface as a READ over the project's own record, offline and
in-session, with the no-fabrication guarantee at the center: an answer is grounded in a
real artifact, or the corpus says there is no governing artifact, and it never invents one.

## Context

- The outcome this serves (O4): diagnosis comes from artifacts, not memory. The responder
  queries the intent corpus the method already produces (what specification governs this
  behavior, what changed here recently, what did its proof cover, and where the affected
  module sits in the declared shape when an architecture contract exists) so a party that
  never wrote the code reaches a cited diagnosis at machine speed. O4's measure is a seeded
  fake incident diagnosed offline from the corpus alone, citing the governing spec, the
  implicated change, and its proof, degrading gracefully to spec and git level when no
  architecture contract is present. This item ships the corpus and its query surface that
  make that read possible and grounded; the responder AGENT that reads them and composes
  the cited diagnosis and the proposal is WARP-1204 (W4), the first consumer.
- Data provenance (the plan's provenance section, reused as-is, no new instrumentation):
  the intent corpus is the specs, proofs, verdicts, and the plans they bind to; the event
  stream and git history for what changed where and when; and the architecture contract for
  the module-to-area join where PLAN-0011 has shipped. This item INDEXES that record; it
  builds no store and adds no instrumentation (NG5).
- The right architecture (RULE #6, no shortcut): the corpus reuses the repo's OWN readers
  rather than reimplementing them. There is one front-matter parser (validate.parse_yamlish),
  one proof identity (validate.proof_digest), one plan registry (validate.plan_registry),
  one contract loader (validate.load_repo_contract), and one decision reader
  (.veldo/decision.py load_record); the module receives them injected, exactly as the sibling
  organs .veldo/incident.py and .veldo/evidence.py receive the parser and the reporter, so
  there is no second parser and no import cycle. Git is part of the recorded change log and
  is read IN-SESSION and synchronously through an injected reader whose default is a thin
  git log, never a detached or background process (NG3), exactly the posture fleet.py takes
  for its in-line git worktree helper.
- The no-fabrication guarantee is the load-bearing property (C1, the refusals are the
  product): diagnosis from artifacts means the answer rests on a real artifact or the corpus
  says it cannot. A query for a behavior no recorded artifact governs returns a truthful
  Trace with governed false and the reason "no governing artifact"; it never resolves to an
  arbitrary spec, and it carries no invented criterion, proof, or verdict. A responder that
  fabricated a governing spec would be worse than one that admitted it does not know, so the
  teeth prove that a resolver mutated to fabricate a governor, and a trace mutated to
  fabricate a dropped proof, each turn their check RED.
- Two postures the plan binds everywhere, shared with the sibling organs: adoption safe (a
  repository with no specs and no proofs builds an empty corpus that stands down) and fail
  closed (a malformed corpus artifact or a malformed query refuses by name). And the
  cross-plan join is soft (C7): the module-to-area answer resolves against a PLAN-0011
  architecture contract when one exists and stands down honestly to spec and git level when
  none is present, never faking an area.

## Out of scope

- No responder loop. The in-session agent that, given an incident, investigates over the
  evidence plane and the intent corpus and produces a cited diagnosis and a veldo.remedy/v1
  proposal is WARP-1204 (W4), the first consumer. This item ships the corpus the responder
  reads through; trace_incident assembles the artifact-grounded trace the responder
  diagnoses FROM, but this module composes no prose diagnosis and emits no proposal.
- No evidence plane. The read-only runtime evidence plane (logs, metrics, traces, replicas)
  the responder investigates a live incident through is WARP-1202 (W2). The intent corpus
  reads the method's OWN records (specs, proofs, verdicts, plans, decisions, git, events);
  they are separate roots and share no code path.
- No execution organ and no contracts. The incident and remedy contracts are WARP-1201
  (W1); the action whitelist is WARP-1205 (W5); the executor with the autonomy ladder, kill
  switch, budgets, and canary-first is WARP-1206 (W6); the two-key rule is WARP-1207 (W7).
  The corpus reads and only reads; it shares no credential and no code path with any of them.
- No new instrumentation and no store (NG5). The corpus reuses the recorded data only. It
  builds no database, adds no event type, and changes no artifact; it indexes what the loop
  already writes.
- No gate wiring. Landing a corpus check into validate.py run_all and the init lay-down is
  WARP-1211 (W11). W3 ships the module runnable standalone (python3 .veldo/intent_corpus.py)
  and exercised through the injected readers in the selftest; it does not wire it into the
  gate, so validate.py is unedited and stays under its module_lines budget. This deferral
  matches W1 and W2.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy.yaml, .veldo/policy_check.py and their engine twins are untouched
  (protected paths). The module lives in the placeless engine module .veldo/intent_corpus.py,
  outside the declared contract areas, like the sibling organ modules.

## Notes

- Keep the module reusing the ONE parser and follow the byte-identical engine sync
  discipline: .veldo/intent_corpus.py and .veldo/capabilities.yaml land in engine
  and every pack byte-identical, and the drift checks end empty. The corpus reads the
  repository's own record; there is no new per-repo config artifact to validate (unlike the
  evidence plane and the incident and remedy records), so there is nothing to wire into the
  gate for W3.
- Put teeth on the corpus by mutating in-memory copies and observing the check go red before
  reverting; a query surface that cannot refuse to fabricate is exactly the vacuity C1
  forbids. The load-bearing teeth are the no-fabrication ones: a resolver that fabricates a
  governor for an ungoverned behavior, and a trace that fabricates a dropped proof, each
  turn their check red.
- No detached process (NG3 and the no-detach lesson): intent_corpus.py starts no detached
  or background process; the only external program is a synchronous in-session git log, with
  subprocess imported lazily inside the git reader, and a Popen(start_new_session=True)
  mutation turns the no-detach check red. The module is runnable in-session only.
- Honesty (NG5 and the over-attestation lesson): do not imply the responder, the executor,
  the whitelist, or the two-key rule are built, and do not imply the corpus produces a
  diagnosis. This repository ships the read-only intent corpus and its query surface over
  the method's own recorded artifacts, proven offline; the responder that reads it to
  diagnose and the gate wiring are honestly named as later and separate items.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
