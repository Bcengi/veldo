---
schema: veldo.spec/v1
id: WARP-0610
title: Tracker integration docs made true - surface the shipped Jira/Confluence integration in the README and guides
status: shipped
risk: standard
owner: Dmitry Grinberg
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      README.md documents the tracker integration as a first-class shipped
      capability (in "What the plugin ships" and/or a dedicated short section),
      describing both directions truthfully: the ONE-WAY, event-driven mirror
      (a spec's and a plan's lifecycle events project onto an external tracker's
      status + comments and a plan's epic/child structure, one-directionally,
      never polling the tracker, with the repository remaining the single source
      of truth) and INTAKE (a Jira ticket or a Confluence requirements page
      becomes a routing-resolved VELDO spec draft). No operating metric or
      credential appears.
  - id: AC2
    text: >
      An operational section in docs/plugin.md and/or docs/setup.md tells an
      adopter how to turn the tracker on: the per-org .veldo/trackers.json config
      (veldo.tracker/v1 - routing plus the VELDO-status to tracker-status
      status_map; template at engine/.veldo/trackers.json), the OPTIONAL
      tracker_repo front-matter field on specs and plans, auth by reference not
      secret (token_ref, e.g. env:JIRA_TOKEN, fails closed, a raw credential
      never in a file/prompt/proof/log), and the Confluence requirements template
      (engine/confluence-requirements-template.md).
  - id: AC3
    text: >
      The docs are TRUE, not aspirational. Every module, config file, front-matter
      field, env/secret reference, and template the docs name actually exists in
      the shipped engine, and the reference-versus-mechanical honesty is preserved
      exactly as capabilities.yaml states it: the vendor-neutral routing, seam,
      mirror, epic mirror, intake logic, and conformance are mechanical (offline,
      gate-tested via the FakeTracker), while the LIVE JiraCloud and
      ConfluenceCloud adapters are REFERENCE (must be wired per repo, need a live
      instance, are not run in the gate), and any not-yet-live edge (e.g.
      epic/child creation against live Jira) is stated as such rather than implied
      complete.
  - id: AC4
    text: >
      The governing principles are stated: the mirror is one-way and the
      repository wins if the index and the tracker disagree (consistent with the
      existing "do not recreate Jira in Markdown" principle), and tracker content
      is untrusted input, never instructions.
  - id: AC5
    text: >
      The full gate is GREEN (selftest, contracts, generated/docs/secret checks,
      the dash/genericity sweeps on the changed documents) and RULE #1 is clean.
      No protected path is touched. If any ENGINE_GLOBS file is edited it is
      re-synced byte-identical across engine and all seven packs
      (docs/*.md and README.md are NOT engine files, so a docs-only change needs
      no pack re-sync; a template edit would).
required_evidence: [operational]
rollback: >
  Revert the commit. The change is documentation plus this spec and its proof;
  it adds no behavior and can be removed with no migration.
---

## Intent

PLAN-0006 shipped a real tracker integration (Jira/Confluence intake and a
one-way, event-driven mirror), released as WARP-0601 through WARP-0609, but the
README and the operational guides never documented it. The README calls itself
"the complete front door: what VELDO is ... what the plugin ships," yet an adopter
reading it would not learn that VELDO can integrate with their Jira and Confluence
at all. This spec closes that gap the same way W6 (WARP-0906) made the fleet docs
true: surface the shipped capability, accurately, where an adopter will find it.

## Context

- The accurate ground truth is already written in .veldo/capabilities.yaml: the
  tracker_routing, tracker_adapter_seam, tracker_routing_enforcement,
  tracker_status_mirror, tracker_epic_mirror, tracker_intake,
  jira_cloud_intake_adapter, confluence_requirements_intake,
  confluence_cloud_intake_adapter, and tracker_conformance entries. Read them and
  the specs WARP-0601..0609 and the .veldo/tracker*.py modules; write nothing the
  code does not support.
- User-facing surface to document: config .veldo/trackers.json (template at
  engine/.veldo/trackers.json), the optional tracker_repo spec/plan
  field, token_ref auth, the Confluence requirements template. There is no
  dedicated veldo CLI tracker subcommand; the mirror is driven by the event
  stream and intake feeds the existing intake skill.
- Match the voice and structure of the existing README and docs (study the fleet
  sections W6 added as the model for tone and depth). This is generic
  documentation, not tied to Bcengi's own instances.

## Out of scope

- No code change to the tracker. No new capability. No live wiring against any
  real Jira/Confluence instance (that is a separate activation, not docs).
- capabilities.yaml is already honest and thorough; leave it unless a genuine
  inaccuracy is found.

## Notes

- Do the commits in the canonical VELDO release shape from the start: one reviewed
  commit carrying the docs + this spec (the verdict binds to it), then an
  evidence-only commit (proof/, .veldo/) on top. Do not interleave other work.
- Keep it proportionate: a clear README bullet or short section plus one solid
  operational section. Depth comparable to the fleet's docs, not more.
