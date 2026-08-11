---
schema: veldo.spec/v1
id: WARP-0906
title: Docs made true - the fleet, the two-tier adoption model, and an honest capabilities manifest
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W6
plan_revision: 1
protected_paths: []
depends_on: [WARP-0905]
acceptance_criteria:
  - id: AC1
    text: The README is made true about the fleet. The fleet now ships in the engine and is delivered by
      installing a pack, so the README's fleet description matches what actually ships, and the stale
      "Current plugin version 3.2.0 (VELDO Fleet v1)" line is corrected to the actual current plugin
      version and does NOT claim a release that has not happened (the plugin 3.5.0 release is W8/WARP-0908,
      not this item). No operating metric appears; the fleet is described by capability, not by a version
      it did not ship in.
  - id: AC2
    text: docs/plugin.md gains an accurate fleet section - what the fleet is, that installing a pack lays
      the full engine including the fleet and the veldo CLI, veldo fleet N and veldo work as the entry
      points, the fleet as a per-repo capability, the per-account model, governor pacing, and that it
      spawns no detached process (the in-session, no-rogue-processes boundary). It claims only what W1-W5
      actually shipped.
  - id: AC3
    text: docs/setup.md's scaling coverage gains the fleet, the veldo CLI, the account model, and the
      governor, consistent with its capability-by-scale framing, AND the two-tier adoption model is
      documented explicitly - installing a pack lays the FULL engine (the fleet included) while /veldo:init
      lays the MINIMAL governance substrate (gate, contracts, templates) by design, so a reader knows
      which path delivers the fleet.
  - id: AC4
    text: docs/runbook.md gains a fleet operational runbook - the one-time veldo account add per account
      (a login into that account's own persisted CLAUDE_CONFIG_DIR profile, no relogin thereafter),
      running veldo fleet N or veldo work --account NAME, monitoring with veldo status / veldo watch, and the
      in-session resume behavior when an account hits its budget - with the no-detached-process boundary
      stated.
  - id: AC5
    text: The capabilities manifest is made honest end to end. Every non-fleet dogfood or build-machinery
      capability entry whose home does NOT ship to an adopter (neither a pack nor /veldo:init lays it -
      e.g. budget.py, lessons.py, init_scaffold.py, the tracker_* build family, pack.py,
      pack_conformance.py, check_pack_drift.py, packs.json, env_provision.py, release.py) is tagged with a
      distinct repo-only marker in BOTH byte-identical capabilities.yaml copies, and a gate check
      (selftest, not a protected file) enforces WITH TEETH that every UNMARKED capability entry's home
      resolves in the shipped engine (so an adopter who installs a pack actually has it) while every
      repo-only entry exists in the repo but is exempt from the shipped-tree requirement. Un-marking a
      dogfood entry, or pointing a shipped entry's home at a missing file, must turn the check RED.
  - id: AC6
    text: The full gate is GREEN including the new capabilities-honesty check; the docs sweeps (dash,
      non-ASCII, genericity) pass; the two capabilities.yaml copies stay byte-identical; NO protected path
      is edited (scripts/verify.sh, scripts/veldo-guard.sh, .veldo/policy.yaml, .veldo/policy_check.py or
      their engine twins); the index is regenerated; and the veldo name is unchanged. The
      "documentation is always updated" standing rule holds - every capability W1-W5 shipped is reflected
      in the adoption docs.
required_evidence: [unit]
rollback: git revert; additive - doc prose added to README/plugin.md/setup.md/runbook.md, a repo-only
  marker on the dogfood capability entries in both byte-identical capabilities.yaml copies, and a new
  selftest honesty check. Removing them returns to the pre-W6 docs and manifest. No protected path.
---

## Intent

W5 shipped the fleet into the engine; the docs still describe a world where it was not shipped (the
README claims a fleet at plugin 3.2.0 that did not ship until W5) and the shipped capabilities manifest
over-claims (it lists dogfood/build-machinery capabilities an adopter will never have). W6 makes the
shipped artifacts honest: the README, plugin.md, setup.md, and runbook.md describe the fleet, the veldo
CLI, the account model, and the two-tier adoption model as they actually are, and the capabilities
manifest is tagged and gate-checked so it names only what an adopter gets (plus honestly-marked
repo-only entries). This is the W5 review's carry-forward closed and the "documentation is always
updated" standing rule enforced.

## Context

W6 of PLAN-0009, depends on W5 (WARP-0905, the fleet in the engine). The two-tier model is the frame:
installing a pack lays the FULL engine (fleet included); /veldo:init (init_scaffold) lays the MINIMAL
governance substrate by design and is not expanded. The capabilities manifest lives in two
byte-identical copies (.veldo/capabilities.yaml and engine/.veldo/capabilities.yaml); no gate
check currently verifies a capability's home exists, so the honesty is prose-only today - AC5 adds the
teeth. The current plugin version is 3.4.0 (from PLAN-0008); the 3.5.0 release is W8, so W6 must NOT
bump the version or claim a release. Docs are swept for dashes/non-ASCII/genericity by the gate; packs/
is not swept, but the canonical docs under docs/ and README are.

## Out of scope

The external supervisor (W7 / decision D1), the plugin 3.5.0 release and the PLAN-0009 released status
(W8). No rename (veldo stays veldo; VELDO parked). No protected-path edits. No new fleet code - W6 is docs
plus the manifest-honesty marker and its gate check.

## Notes

Two commits, the standard shape: an impl commit (README/docs/capabilities/selftest, with its own
independent review and commit-bound verdict) then an evidence-only commit (proof/, .veldo/, specs/).

RULE #1: the gate's dash-sweep catches em/en dashes but NOT the ASCII double-hyphen; hand-check all new
doc prose and capability markers for `--`. Keep the two capabilities.yaml copies byte-identical (the
marker goes in both). The capabilities.yaml is read by regex tooling, not a strict YAML parser, so keep
the marker in the same single-line entry shape the file already uses; validate new entries against the
selftest's honest-check regex.
