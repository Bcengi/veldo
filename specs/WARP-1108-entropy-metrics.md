---
schema: veldo.spec/v1
id: WARP-1108
title: Entropy metrics - cost-to-change per area, derived from what the loop already records and joined to contract areas through placement, with the gate's static shape measures on the same map and a relative-baseline threshold whose crossing feeds restoration (W8 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W8
plan_revision: 2
depends_on: [WARP-1102, WARP-1103]
protected_paths: []
placement: [metrics]
footprint:
  - .veldo/entropy.py
  - .veldo/metrics.py
  - .veldo/dashboard.py
  - .veldo/capabilities.yaml
  - engine/.veldo/entropy.py
  - engine/.veldo/metrics.py
  - engine/.veldo/dashboard.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/entropy.py
  - packs/*/.veldo/metrics.py
  - packs/*/.veldo/dashboard.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1108-entropy-metrics.md
acceptance_criteria:
  - id: AC1
    text: >
      A per-area cost-to-change SERIES derived from what the loop ALREADY records, joined to
      contract areas through placement. A new module .veldo/entropy.py (the metrics area, beside
      metrics.py, dashboard.py, and budget.py) derives, per contract area, a time-ordered
      cost-to-change series from the recorded event stream ONLY: per-correlation tokens, cost_usd,
      human_minutes, review cycles (verdict.recorded events), and gate failures (gate.failed
      events carrying the correlation). It introduces NO new instrumentation: the per-correlation
      components are read through metrics.compute (the single aggregation, extended here with a
      cost_by_correlation map), so the entropy map, the dashboard, and the budget enforcer never
      fork a number. Each SAMPLE is one shipped change (a correlation with a spec.shipped event),
      attributed to the contract area(s) the change TOUCHED via its spec's declared placement and
      footprint (arch.footprint_areas, the W3 join key), and a cross-area change contributes its
      recorded cost to EACH area it touched. A change with no placement/footprint (pre-W3 history)
      is UNATTRIBUTED and counted honestly, the best-effort limit PLAN-0011's data-provenance
      section names (per-area attribution starts accumulating when W3 ships). Proven over seeded
      events with an injected area index: each area's per-dimension series carries the right values
      in ship-time order, and the attributed and unattributed change counts are correct.
  - id: AC2
    text: >
      The D2 threshold detection: relative degradation against a trailing baseline, advisory during
      a calibration period, and NOTHING auto-gates on the number. detect_crossings compares, per
      area and per recorded dimension, the LATEST sample against the mean of the trailing
      baseline_window PRIOR samples and flags a crossing when the latest is at least
      baseline * (1 + degradation_factor) with a positive baseline: a relative worsening against
      the area's OWN history, never an absolute threshold. A crossing is ADVISORY while the area is
      still calibrating (fewer than calibration_min samples), so a young series is measured but its
      crossings are not yet trusted; the defaults (baseline_window, degradation_factor,
      calibration_min) are the recommended D2 defaults, tunable per repo. The derivation is
      advisory-only: it is NOT wired into scripts/verify.sh or .veldo/validate.py run_all, so no
      number ever fails the build (a tooth asserts the gate path carries no entropy reference).
      Proven over seeded events: a rising series crosses and a flat series does not (the crossing is
      not vacuous); a crossing over a still-calibrating area carries advisory True while a crossing
      over a matured series carries advisory False; and a change to the recorded values changes the
      crossing (mutation teeth).
  - id: AC3
    text: >
      The gate's static shape measures on the SAME per-area map, and adoption-safe stand-down. For
      each contract area the report carries the static shape measures REUSED from the gate's own
      analyzers (.veldo/shape_gate.py: duplication, cyclomatic complexity, function length, and the
      boundary pressure count) computed over the area's current source files (enumerated from the
      contract's area includes), on the same per-area map as the cost-to-change series, so a rotting
      area is a number beside its own trend, not an opinion. The measures reuse shape_gate's
      reference analyzers (no reimplemented duplication or complexity) and the contract's own
      budgets for their limits. Adoption safe on two axes: a repository with NO architecture
      contract stands the whole derivation down (a standdown report, byte-identically unaffected),
      and a repository with a contract but no recorded events yields empty series and no crossings.
      Proven over a temporary tree: no contract stands down; a contract plus seeded source yields
      per-area static measures that reflect the source, and injecting a duplicated block or an
      over-long function into a copy of a governed source raises the measured count, reverted
      byte-identical (teeth).
  - id: AC4
    text: >
      IN-SESSION ONLY, no daemon, and a crossing is the signal W9 consumes (referenced, not built).
      The derivation is a PURE in-session function that reads recorded files (events.jsonl, spec
      front matter, source files) and takes the events and the trailing-window policy as injected
      parameters; it starts no process, no thread, installs no timer, and never polls in the
      background (NG1, feedback_no_rogue_processes, the contract invariant no_detached_processes).
      .veldo/entropy.py imports only the standard library (argparse, importlib.util, json, sys,
      pathlib) and contains NONE of subprocess, Popen, os.fork, os.exec, os.spawn, os.system,
      setsid, nohup, start_new_session, multiprocessing, threading, asyncio, or sched: a source
      string-scan tooth proves it (mirroring WARP-1107's no-detach tooth), and MUTATION teeth inject
      a detached spawn and a background thread into a COPY of the source and observe the check go RED
      before reverting byte-identical (the real module on disk unchanged). A threshold crossing is
      emitted as a machine-readable signal (the crossings list, each naming the area, the dimension,
      the baseline, the latest, the relative increase, and whether it is advisory) that the
      restoration-spec generator WARP-1109 (W9) consumes to draft a restoration spec ONLY a human
      promotes; the later incident-metrics join (PLAN-0012) is referenced. W9 and PLAN-0012 are
      honestly out of scope here and only referenced; this item builds the per-area series, the
      static-shape map, and the threshold detection, never the restoration draft.
  - id: AC5
    text: >
      Extends the existing metrics derivation and dashboard; byte-identical sync; honest capability;
      no protected path; dogfooded placement. metrics.compute is EXTENDED with a cost_by_correlation
      aggregation (the per-correlation recorded cost components) computed in the one reader, so the
      dashboard, the budget enforcer, and the entropy map read the SAME numbers (no drift, no second
      store); the dashboard (.veldo/dashboard.py) gains a per-area entropy section rendered from
      entropy_report (the single source, never a recompute), and a tooth asserts the rendered
      per-area figures equal the report's. .veldo/entropy.py ships in the engine and is re-synced
      byte-identical across engine and all 6 packs, and the edited .veldo/metrics.py,
      .veldo/dashboard.py, and .veldo/capabilities.yaml are re-synced likewise (template sync and pack
      drift pass); capabilities.yaml gains ONE honest mechanical entry (entropy_metrics) in every
      copy. No protected path is touched: entropy, metrics, and dashboard are non-protected engine
      (the metrics area). The full gate is GREEN (selftest, contracts, generated, docs, lint, secret
      scan, template sync, pack drift), and RULE #1 is clean (ASCII hyphen only, no em or en dash, no
      prose double-hyphen; the only double-hyphen tokens are genuine CLI flags). Dogfood: this spec's
      placement [metrics] resolves to a declared area and its footprint tier is standard (a single
      area, no boundary crossing; ARCH.footprint_tier_floor == "", validate.py ready rc 0).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one derivation module (.veldo/entropy.py), extends
  metrics.compute with a cost_by_correlation aggregation (additive; existing keys unchanged), adds a
  per-area entropy section to the dashboard render, and adds one capabilities entry, all re-synced
  byte-identical across engine and the 6 packs. The derivation is advisory and unwired
  from the gate, so removing it changes no gate behavior. A repository with no architecture contract
  stands the derivation down entirely (the adoption-safe posture), so removing it needs no migration;
  the entropy series is inert derived data (it owns no store) and keeps nothing to unwind.
---

## Intent

This is W8 of PLAN-0011 and the entropy-reconciliation half of the method's "The Shape of the
System" invention (Invention #2): entropy becomes a NUMBER. A thousand locally proven changes still
cannot vouch for the foundation they sit on, and decay - duplication, tangled dependencies, eroding
boundaries - accumulates through many changes. This item makes decay measurable: cost-to-change per
contract area, derived from what the loop ALREADY records (tokens, cost, review cycles, gate
failures, human minutes), joined to areas through the placement declarations W3 introduced, with the
gate's static shape measures (duplication, complexity, boundary pressure) on the same per-area map. A
rotting area stops being an opinion and becomes a series that trends. A relative-degradation crossing
against an area's own trailing baseline is the signal the restoration loop (WARP-1109, W9) consumes to
draft a restoration spec a human promotes; this item does not build that draft.

## Context

- Depends on WARP-1102 (shipped): the gate's static shape analyzers (.veldo/shape_gate.py -
  duplication, complexity, function length, boundary) that this item reuses to put the static shape
  measures on the per-area map. No reimplementation.
- Depends on WARP-1103 (shipped): placement and footprint on specs, and arch.footprint_areas / 
  arch.area_for_path (the one place a change resolves to the areas it touched). That declaration is
  the JOIN KEY the cost-to-change map needs; history before W3 can be back-attributed only
  best-effort, so a pre-placement change is honestly unattributed here.
- The recorded data reused as-is (PLAN-0011 "Data provenance", no new instrumentation): per-event
  tokens and cost_usd on the veldo.event/v1 envelope, human_minutes per step, review cycles
  (verdict.recorded) and gate failures (gate.failed), and spec lifecycle events (spec.shipped marks a
  shipped unit). metrics.compute is the single aggregation; this item extends it with a
  cost_by_correlation map rather than forking a second calculation, the same discipline the dashboard
  and the budget enforcer follow.
- Resolved decision D2 (restoration thresholds): relative degradation of an area against its OWN
  trailing baseline, with generation starting ADVISORY for a calibration period before its drafts are
  trusted. This item implements the DETECTION half (the crossing, advisory during calibration);
  WARP-1109 (W9) implements the generation half (the restoration draft) that consumes the crossing.
- The in-session, no-daemon posture (NG1, feedback_no_rogue_processes, the contract invariant
  no_detached_processes) binds this item as it bound W7: the derivation is a pure function invoked
  in-session (the CLI, the dashboard, the weekly pass), reading recorded files and taking events and
  policy as injected parameters; it spawns nothing, and the same string-scan-with-mutation tooth
  proves it here.
- Nothing auto-gates on the number (D2 and the invention): entropy is advisory. It is surfaced
  through the metrics CLI and the dashboard, exactly like the other metrics derivations, and is NOT
  wired into scripts/verify.sh or validate.py run_all.

## Out of scope

- No restoration-spec generation. Drafting a restoration spec on a threshold crossing (naming the
  area, the crossed rule, and the expected post-restoration measure) is WARP-1109 (W9); this item
  emits the crossing as the signal W9 consumes and references it, never building it.
- No incident-metrics join. Joining the incident metrics onto the same per-area map is a later plan
  (PLAN-0012); referenced only.
- No auto-gating. No number here fails the build; entropy is advisory (D2). It is not wired into the
  gate or run_all.
- No new instrumentation. This item reuses the recorded event stream and metrics.compute; it adds no
  new event type and no second store.
- No detached monitor of any kind (NG1). The derivation runs only in-session; nothing outlives the
  session, no timer, cron, or daemon is installed.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy.yaml,
  .veldo/policy_check.py and their engine twins are untouched (protected paths). The
  derivation lives in the non-protected metrics area (.veldo/entropy.py, plus the metrics.py and
  dashboard.py edits).

## Notes

- Keep the derivation dependency free of a second parser and a second aggregation: entropy.py loads
  metrics.py (the one spend/cost aggregation) and validate.py (the one front-matter parser and the
  arch area resolver) the way budget.py and dashboard.py already do (metrics -> contracts, an
  allow-listed edge), and shape_gate.py for the static analyzers. No new parser, no new store.
- Attribution rule, stated honestly: a change's recorded cost is attributed to EACH contract area its
  placement and footprint touched; a cross-area change bears its cost in each area it touched (a
  cross-area change IS a cost signal for each area). A change that declares no placement (pre-W3) is
  unattributed and counted, never silently dropped.
- The threshold is RELATIVE to an area's own trailing baseline and ADVISORY during calibration, so a
  new area is not punished for having no history and no absolute number is smuggled in. Nothing
  auto-gates: the crossing is a signal, not a refusal.
- Put teeth on every mechanical claim: the per-area series over seeded events, the crossing over a
  rising vs a flat series (non-vacuous), the advisory flag over a calibrating vs a matured series, the
  static-shape count over seeded source (raised by an injected duplicate/over-long function, reverted
  byte-identical), the adoption-safe stand-down (no contract, no events), and the no-detach source
  scan with mutation teeth. Follow the byte-identical engine sync discipline: entropy.py and the
  edited metrics.py, dashboard.py, and capabilities.yaml land in engine and every pack
  byte-identical, and the drift checks end empty.
- Honesty (NG5): the capabilities entry is mechanical and names exactly what ships (the per-area
  series, the static-shape map, and the advisory threshold detection); it does NOT claim the
  restoration draft (W9) or the incident join (PLAN-0012). RULE #1 clean (ASCII hyphen only, no em or
  en dash, no prose double-hyphen; the only double-hyphen tokens are genuine CLI flags).
</content>
