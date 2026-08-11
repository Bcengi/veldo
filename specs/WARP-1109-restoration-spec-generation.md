---
schema: veldo.spec/v1
id: WARP-1109
title: Restoration-spec generation - a per-area entropy crossing drafts a restoration intent that names the area, the crossed rule, and the expected post-restoration measure, a draft only a human promotes into a spec that flows through the normal loop, idempotent, and whose post-restoration measure closes the loop on the cost delta (W9 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W9
plan_revision: 2
depends_on: [WARP-1108]
protected_paths: []
placement: [metrics]
footprint:
  - .veldo/restoration.py
  - .veldo/capabilities.yaml
  - engine/.veldo/restoration.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/restoration.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1109-restoration-spec-generation.md
acceptance_criteria:
  - id: AC1
    text: >
      CONSUME a W8 entropy crossing and DRAFT a restoration intent that NAMES the area, the crossed
      rule, and the expected post-restoration measure. A new module .veldo/restoration.py (the metrics
      area, beside entropy.py) reuses the W8 crossing detection (entropy.detect_crossings /
      entropy_report, the ONE detection, adding no second detection, no second store, and no second
      front-matter parser) and, for a crossing, renders a veldo.restoration/v1 DRAFT that names the
      AREA, the CROSSED RULE (the cost-to-change dimension that degraded against the area's own
      trailing baseline), and the EXPECTED post-restoration measure (that baseline, the level the
      restoration must bring the cost-to-change back to). The draft also records the BEFORE measure
      (the degraded latest and its baseline) so the loop can close on the cost delta once a
      restoration ships. Proven over a seeded trusted crossing: exactly one draft is created, it
      names the area and the crossed dimension, its expected measure is the area's baseline, and it
      records the before measure.
  - id: AC2
    text: >
      The draft is a DRAFT only a HUMAN promotes (NG2), and the machine authors no spec and
      self-promotes nothing. The drafted intent is schema veldo.restoration/v1 with status draft,
      drafted_by the machine pass and a drafted_at date, and it carries NO decider, NO chosen option,
      and NO promoted flag. It is a restoration-INTENT artifact homed per-repo under
      .veldo/restorations/ (a directory the engine glob does not sweep, exactly as .veldo/readings/ and
      .veldo/redecisions/ are homed), which a HUMAN promotes by authoring a real veldo.spec/v1
      restoration spec placed in the named area, which then flows through the normal loop like any
      spec (spec, gate, proof, fresh-context review). The machine drafts the intent; it never authors
      the spec, never promotes its own draft, and never restores anything itself, mirroring WARP-1107
      where a fired tripwire drafts a re-decision a human promotes into a decision record. Drafting a
      real claimable spec directly would be the machine injecting its own work onto the frontier,
      exactly the self-promotion NG2 forbids. Proven over a temporary tree: the draft carries status
      draft and none of decider/chosen/promoted, drafting writes only under .veldo/restorations/, and
      the specs/ directory stays empty (the machine authors no spec).
  - id: AC3
    text: >
      IDEMPOTENT (re-deriving the same crossing never drafts a duplicate), advisory does not draft,
      and adoption safe. The idempotency key is the crossed rule in an area, the (area, dimension)
      pair, rendered .veldo/restorations/<area>__<dimension>.yaml; an existing draft is NEVER
      overwritten, so a second derivation of the same crossing drafts no duplicate and leaves the
      draft byte-identical. Only a TRUSTED crossing drafts: an ADVISORY crossing (the area is still
      calibrating) is measured and surfaced but does NOT draft, because D2's generation starts
      advisory before its drafts are trusted (the FIRED-versus-warning split WARP-1107 uses). Adoption
      safe: a repository with no architecture contract stands the whole W8 derivation down, so there
      are no crossings and nothing drafts. Proven over temporary trees: a first derivation drafts
      exactly one (created), a second drafts none (exists) and the file is byte-unchanged; an advisory
      crossing drafts nothing; and a contract-free tree stands down and drafts nothing.
  - id: AC4
    text: >
      The post-restoration measure CLOSES THE LOOP on the cost delta (after-versus-before), and the
      module is IN-SESSION only, spawning nothing, with nothing auto-gating and nothing auto-promoting.
      restoration_delta reports, for a draft, the before measure it recorded and the AFTER measure (the
      area's current cost-to-change for the crossed dimension once a restoration has shipped, read from
      the SAME W8 entropy report, never a recompute), the delta (before minus after, positive when the
      cost-to-change dropped), and a paid_off finding (the cost-to-change returned to or below the
      pre-degradation baseline); before a restoration ships it honestly reports not-measured. The
      derivation is a pure in-session read and the drafting is an explicit in-session write action;
      .veldo/restoration.py imports only the standard library (argparse, importlib.util, json, sys,
      datetime, pathlib) and contains NONE of subprocess, Popen, os.fork, os.exec, os.spawn, os.system,
      setsid, nohup, start_new_session, multiprocessing, threading, asyncio, or sched: a source
      string-scan tooth proves it, and MUTATION teeth inject a detached spawn and a background thread
      into a COPY of the source and observe the check go RED before reverting byte-identical (the real
      module on disk unchanged), mirroring WARP-1107/WARP-1108. NOTHING auto-gates on a number and
      NOTHING auto-promotes a draft: the module is never wired into scripts/verify.sh or
      .veldo/validate.py run_all (a tooth asserts the gate path carries no restoration reference and no
      auto-draft), exactly as the W8 entropy derivation is advisory and unwired. Proven over seeded
      before/after measures: a restoration that dropped the cost reports a positive delta and paid_off,
      one that did not reports delta 0 and not paid off (non-vacuous), and the pre-ship state reports
      not-measured; plus the no-detach source scan with mutation teeth and the not-wired-to-the-gate
      teeth.
  - id: AC5
    text: >
      RJ6 entropy-to-restoration conformance end to end, byte-identical engine sync, honest
      capability, no protected path, dogfooded placement. RJ6: over a temporary tree with an
      architecture contract, seeded specs placed in an area, and a seeded single-dimension entropy
      crossing, draft_restorations drafts EXACTLY ONE restoration spec that only a human can promote
      (status draft, no decider/chosen/promoted), re-running drafts no duplicate (idempotent), and once
      the restoration ships (a cheap change in the area) close_restorations reports the post-restoration
      delta (before to after, paid off). .veldo/restoration.py ships in the engine and is re-synced
      byte-identical across engine and all 6 packs, and the edited .veldo/capabilities.yaml is
      re-synced likewise (template sync and pack drift pass); capabilities.yaml gains ONE honest
      mechanical entry (restoration_generation) in every copy that names exactly what ships (the draft,
      the idempotency, the human-promote-only posture, and the close-the-loop delta) and does NOT claim
      to author the spec or promote it. No protected path is touched (restoration is non-protected
      metrics-area engine). The full gate is GREEN (selftest, contracts, generated, docs, lint, secret
      scan, template sync, pack drift, shape gate) and RULE #1 is clean (ASCII hyphen only, no em or en
      dash, no prose double-hyphen; the only double-hyphen tokens are genuine CLI flags). Dogfood: this
      spec's placement [metrics] resolves to a declared area and its footprint tier is standard (a
      single area, no boundary crossing; ARCH.footprint_tier_floor == "", validate.py ready rc 0).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one metrics-area derivation module (.veldo/restoration.py) and one
  capabilities entry, both re-synced byte-identical across engine and the 6 packs, plus a
  selftest block and this spec. The derivation is advisory and unwired from the gate (nothing
  auto-gates), and the drafting is an explicit in-session action that only a human promotes (nothing
  auto-promotes), so removing it changes no gate behavior. A repository with no architecture contract
  stands the derivation down entirely (the adoption-safe posture), so removing it needs no migration;
  the restoration drafts are inert per-repo generated data (the module owns no store) and keep nothing
  to unwind.
---

## Intent

This is W9 of PLAN-0011 and the closing half of the method's "The Shape of the System" invention:
entropy gets a RESPONSE, not just a number. WARP-1108 (W8) made decay measurable, a per-area
cost-to-change series with a relative-degradation threshold (D2) whose crossing is an advisory
SIGNAL. This item is the CONSUMER of that signal: a threshold crossing on an area's series drafts a
restoration intent that names the area, the crossed rule, and the expected post-restoration measure,
as a draft only a human promotes into a real spec; the work then flows through the normal loop like
any spec, and the post-restoration measure closes the loop by reporting the cost delta, proving
whether the refactor paid off (outcome O6). This is the decay-class analogue of WARP-1107's
re-decision draft for the wrong-foundation class: the machine drafts, a human decides.

## Context

- Depends on WARP-1108 (shipped): the per-area cost-to-change series and the D2 relative-baseline
  crossings (entropy.detect_crossings / entropy_report). Each crossing already carries the area, the
  dimension, the baseline, the latest, the relative increase, the advisory flag, and consumed_by ==
  WARP-1109. This item consumes that signal; it adds no second detection.
- Resolved decision D2 (restoration thresholds): relative degradation of an area against its own
  trailing baseline, with generation starting ADVISORY for a calibration period before its drafts are
  trusted. This item drafts only for TRUSTED crossings; an advisory crossing is surfaced but not
  drafted, the FIRED-versus-warning split WARP-1107 established.
- Outcome O6: cost-to-change per area is derived from what the loop records, and a threshold crossing
  generates a restoration spec that flows through the normal loop, whose post-restoration measure
  proves the refactor paid off. Regression journey RJ6 (activation after:WARP-1109): a seeded entropy
  crossing drafts exactly one restoration spec that only a human can promote, and the post-restoration
  delta is reported once the restoration ships. Shipping this item activates RJ6, so the conformance
  journey is built here and is satisfiable.
- NG2 (no self-promotion) and NG1 (nothing detached) bind this item as they bound W7 and W8: the
  machine drafts a restoration intent a human promotes, never authoring the spec or promoting its own
  draft; and the derivation and drafting run only in-session, spawning nothing. The same
  string-scan-with-mutation tooth proves the no-detach property here.
- The closest sibling is WARP-1107's draft_redecisions: an idempotent, human-promoted, in-session
  draft-a-unit pattern homed in a per-repo subdirectory the engine glob does not sweep. This item
  mirrors it: a veldo.restoration/v1 draft under .veldo/restorations/, keyed so a re-derivation never
  duplicates, that a human promotes into a full veldo.spec/v1 restoration spec.

## Out of scope

- No auto-gating and no auto-promotion. No crossing fails the build and no draft is promoted without a
  human; like the W8 entropy derivation this module is never wired into scripts/verify.sh or
  validate.py run_all.
- No machine-authored spec (NG2). The machine drafts a restoration INTENT; a human authors the
  veldo.spec/v1 restoration spec. Authoring a claimable spec directly would inject the machine's own
  work onto the frontier.
- No new instrumentation and no second detection. This item reuses the W8 entropy report (the one
  crossing detection and the one per-area cost measure) and the one front-matter parser through it; it
  adds no new event type, no second store, and no second parser.
- No detached monitor of any kind (NG1). The derivation and drafting run only in-session; nothing
  outlives the session, no timer, cron, or daemon is installed.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). The
  derivation lives in the non-protected metrics area (.veldo/restoration.py).
- No incident-metrics join (PLAN-0012); referenced only where relevant, never built here.

## Notes

- Keep the module dependency free of a second parser and a second detection: restoration.py loads
  .veldo/entropy.py (the one crossing detection and per-area cost measure) the way entropy.py loads
  metrics.py and validate.py, and reuses that module's validate handle for the one front-matter parser
  (parse_yamlish) when reading a draft back. No new parser, no new store.
- Idempotency, stated honestly: the key is the (area, dimension) pair, one draft per crossed rule in an
  area; an existing draft is never overwritten, so a re-derivation of the same crossing never drafts a
  duplicate. An advisory crossing does not draft (D2, before its drafts are trusted).
- The loop closes on the cost delta: the draft records the before measure at crossing time, and
  restoration_delta reports the after measure (the area's current cost-to-change for the crossed
  dimension, read straight from the W8 report) and whether the cost-to-change returned to or below the
  pre-degradation baseline (paid off). Before a restoration ships it reports not-measured, honestly.
- Put teeth on every mechanical claim: the draft over a seeded trusted crossing (names area, rule,
  expected measure), the human-promote-only posture (status draft, no decider/chosen/promoted, and no
  spec authored), the idempotent single draft (created then exists, byte-unchanged), the advisory
  no-draft, the adoption-safe stand-down (no contract), the close-the-loop delta (paid vs not paid,
  non-vacuous), the no-detach source scan with mutation teeth, the not-wired-to-the-gate teeth, and the
  RJ6 conformance journey end to end. Follow the byte-identical engine sync discipline: restoration.py
  and the edited capabilities.yaml land in engine and every pack byte-identical, and the
  drift checks end empty.
- Honesty (NG5): the capabilities entry is mechanical and names exactly what ships (the draft, the
  idempotency, the human-promote-only posture, and the close-the-loop delta); it does NOT claim to
  author the spec (a human does) or to promote it. RULE #1 clean (ASCII hyphen only, no em or en dash,
  no prose double-hyphen; the only double-hyphen tokens are genuine CLI flags).
