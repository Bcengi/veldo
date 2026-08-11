---
schema: veldo.spec/v1
id: WARP-1001
title: The eligibility model and the Agent user - the Agent plus ready-status plus resolvable-repo triple
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W1
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The .veldo/trackers.json config schema (veldo.tracker/v1) is extended, and its
      shipped template documents it with example values, to carry: the Agent user
      identity (a single account the fleet acts as, e.g. an "agent" field naming the
      account id or name), the ready-for-dev status set (the Jira statuses that mean
      "take it", e.g. a "ready_statuses" list defaulting to include Approved-for-dev),
      and the repo routing field (the existing routing config expressing a validated
      custom field). The loader validates the new fields (fails closed by name on a
      malformed shape), reusing the existing config validation rather than a second
      parser.
  - id: AC2
    text: >
      A pure, side-effect-free function is_eligible(ticket, config) returns True only
      when ALL THREE hold: the ticket's assignee equals the configured single Agent
      user, the ticket's status is in the configured ready-for-dev set, and the
      ticket's repo tag resolves to a known repo via the reused WARP-0601 resolver
      (resolve_repo). It fails CLOSED - a missing/unknown/ambiguous repo signal, a
      non-Agent (or unassigned) ticket, or a non-ready status yields False; it never
      raises into the caller and never guesses a repo. When eligible it also reports
      the resolved repo id (so the caller need not resolve twice).
  - id: AC3
    text: >
      A selftest enforces the triple with teeth (non-tautology): a fully eligible
      fake ticket is eligible, and THREE separate negative cases each flip exactly
      one leg and assert ineligible - wrong/absent assignee, a status not in the
      ready set, and an unresolvable repo tag - so the check cannot pass vacuously.
      It also asserts is_eligible is pure (the config and ticket are unchanged after
      the call).
  - id: AC4
    text: >
      capabilities.yaml gains an honest entry for the eligibility resolver
      (mechanical, its shipped home), in both byte-identical copies. Every edited
      file matched by ENGINE_GLOBS (.veldo/*.py, .veldo/*.yaml) is re-synced
      byte-identical into engine/.veldo and all seven packs; the trackers.json
      template (a scaffolded template, per the repo's own convention) is updated in
      its shipped location. check_template_sync.sh and check_pack_drift.py pass.
  - id: AC5
    text: >
      The full gate is GREEN (selftest, contracts, generated/docs/secret checks, the
      dash/genericity sweeps), RULE #1 is clean, and no protected path is touched.
      The change lands in the canonical two-commit shape (a reviewed commit carrying
      the code + this spec, then an evidence-only commit).
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds config fields, one pure function, and a
  selftest; nothing consumes is_eligible yet (its first caller is WARP-1002), so
  removing it has no downstream effect.
---

## Intent

This is the foundation of the tracker-driven fleet (PLAN-0010): the single, pure
rule that decides whether a Jira ticket is the fleet's to take. Every later item
reads it. Getting it exactly right - a fail-closed AND of three independent legs -
is what keeps the autonomous loop from ever grabbing a ticket that was assigned to
a human, sitting in the wrong state, or tagged to a repo nobody can resolve.

## Context

- Eligibility (PLAN-0010 C1) is the triple: assignee == the single shared Agent user
  AND status in the ready-for-dev set (Approved-for-dev) AND the repo tag resolves to
  a known repo. There is ONE Agent account for the whole fleet; the claim ledger, not
  the tracker, decides which worker runs a unit.
- Reuse, do not reinvent: repo resolution is the shipped WARP-0601 resolver in
  .veldo/tracker.py (resolve_repo, _known_repo_ids); config loading/validation is
  load_tracker_config in the same module. Read them and extend, adding no second
  parser.
- The repo tag is a validated custom field ("VELDO Repo") per C7, modeled as the
  existing routing field mechanism; the known-repo set already fails closed on an
  unknown value.
- The ticket shape is the vendor-neutral item the WARP-0603 adapter seam yields
  (id, fields incl. status/assignee, labels, components); is_eligible reads that
  shape, not a Jira-specific one.

## Out of scope

- No poller, no intake call, no promotion, no mirror - this is only the eligibility
  decision and the config it reads. The first consumer is WARP-1002.
- No live Jira. Everything is gate-tested offline over fake tickets + a temp config.

## Notes

- Keep is_eligible a pure function so the selftest drives it directly with fakes.
  Fail closed everywhere: any doubt about a leg resolves to ineligible.
- Match the existing tracker config + selftest conventions (study .veldo/tracker.py
  and its selftest cases). Follow the byte-identical sync discipline for any engine
  file (the W5/W6 lesson) and re-run the drift checks before proof.
