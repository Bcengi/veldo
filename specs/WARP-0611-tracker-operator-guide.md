---
schema: veldo.spec/v1
id: WARP-0611
title: Working with VELDO and your tracker - a human operator guide for intake and the mirror round-trip
status: shipped
risk: standard
owner: Dmitry Grinberg
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A HUMAN-FACING operator guide exists that walks a person through the whole
      tracker workflow end to end, written for someone working with VELDO and their
      Jira/Confluence, not for the implementer. It is discoverable: linked from the
      README tracker bullet and/or opened from docs/plugin.md section 12. It reads
      as a narrative a human follows, not a capability spec.
  - id: AC2
    text: >
      INTAKE is explained from the human's side: how to flag a Jira ticket or a
      Confluence page so VELDO picks it up (the routing signal - a label such as
      veldo-repo:<repo>, a component, or a named field; for Confluence the shipped
      requirements template with its Outcomes and Acceptance Criteria sections),
      how intake is run (the /veldo:intake skill), and what VELDO produces (a
      routing-resolved VELDO spec DRAFT the human then completes - for a bug the
      report becomes the AC1 reproduction, for a requirements page the acceptance
      criteria come from the page). It states that intake FAILS CLOSED (refuses,
      by name) when the routing signal is missing, unknown, or ambiguous, so work
      is never silently misrouted or drafted to a default.
  - id: AC3
    text: >
      The ROUND-TRIP is explained plainly, answering "what happens to the ticket
      after, do I have to guess": the human does NOT hand-update the ticket. The
      one-way mirror writes progress back automatically - as the spec moves through
      its lifecycle (ready, in review, shipped) VELDO transitions the ticket's issue
      to the matching status and posts a closing comment, and a plan's work graph
      is mirrored onto an epic and its child issues. Statuses use the human's OWN
      tracker statuses via the per-org status_map; an unmapped VELDO status is
      recorded as a comment rather than an invented transition. It never polls the
      tracker, it is one-directional, and the repository is the single source of
      truth (if the ticket and the repository disagree, the repository wins).
  - id: AC4
    text: >
      SETUP is actionable and TRUE: the per-org .veldo/trackers.json config
      (routing plus the status_map; template at engine/.veldo/trackers.json),
      the optional tracker_repo front-matter field on specs and plans, and auth by
      reference (token_ref, e.g. env:JIRA_TOKEN - a secret reference, never a raw
      credential in a file/prompt/proof/log). The mechanical-versus-reference
      honesty is preserved: the routing, mapping, mirror, and intake logic are
      mechanical and gate-tested offline against the fake tracker, while the live
      JiraCloud and ConfluenceCloud connections are reference implementations a
      repository wires to its own instance (auth handled by the token_ref, driven
      by non-LLM Python, not an agent). Every module, config, field, and template
      the guide names exists in the shipped engine.
  - id: AC5
    text: >
      The full gate is GREEN (selftest, contracts, generated/docs/secret checks,
      the dash/genericity sweeps on the changed documents), RULE #1 is clean, and
      no protected path is touched. Docs-only, so no ENGINE_GLOBS file changes and
      no pack re-sync. The change lands in the canonical two-commit shape (a
      reviewed commit carrying the guide + this spec, then an evidence-only commit).
required_evidence: [operational]
rollback: >
  Revert the commit. The change is documentation plus this spec and its proof;
  it adds no behavior and can be removed with no migration.
---

## Intent

The tracker capability is now documented (WARP-0610), but from the CAPABILITY
angle: what the pieces are, how to configure them, what is mechanical versus
reference. A human still cannot read one place and understand how to actually
WORK with it day to day: I have a Jira ticket, what do I put on it, how does VELDO
pick it up, what do I get back, and crucially what happens to the ticket after -
do I track it myself or does VELDO indicate progress on it? This guide answers
those questions as a workflow a person follows.

## Context

- The workflow is the same regardless of the connection plumbing; the live edge is
  non-LLM Python authed by a token reference (decision 2026-07-20: keep tokens,
  not MCP, because the mirror must run unattended and deterministically). So the
  guide describes a real, deterministic round-trip.
- Ground truth for accuracy: .veldo/capabilities.yaml (the tracker_* entries), the
  .veldo/tracker*.py modules, specs WARP-0601..0609, the /veldo:intake skill, and
  the shipped templates (engine/.veldo/trackers.json,
  engine/confluence-requirements-template.md).
- Honesty: the ticket round-trip is real once the live adapter is wired to a real
  instance; the mechanical logic is proven offline. Say so; do not imply a
  live instance is connected out of the box.
- Match the voice and structure of the existing docs (the fleet operator sections
  in docs/runbook.md and section 12 of docs/plugin.md are the models).

## Out of scope

- No code change. No new capability. No MCP rework (tokens are kept, per the
  2026-07-20 decision). No live wiring against a real Bcengi instance.
- capabilities.yaml is already honest; leave it unless a genuine inaccuracy is
  found.

## Notes

- Choose the home that maximizes discoverability per the existing doc IA: either a
  dedicated guide (e.g. a "working with your tracker" doc) linked from the README
  and section 12, or a rich "Working with it" subsection within section 12. Keep
  it proportionate - a clear narrative, examples of a routing label and a
  status_map, and the round-trip walked through once; not a second capability dump.
- Do the commits in the canonical shape from the start (reviewed commit, then an
  evidence-only commit); do not interleave other work.
