---
schema: veldo.spec/v1
id: WARP-0601
title: Tracker routing contract and resolver - which repo a ticket targets, which tracker serves a repo
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W1
plan_revision: 1
depends_on: []
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A per-org tracker config (.veldo/trackers.json, veldo.tracker/v1) declares the routing
      mechanism (a label prefix, a component, or a named field), the set of known repos, and the
      tracker/project each repo maps to; load_tracker_config reads it (or returns an empty config
      if absent) and is pure - no network. A malformed config (unknown schema, bad routing
      mechanism, a repo missing its tracker/project) is rejected by name, not silently accepted.
  - id: AC2
    text: resolve_repo(ticket, config) returns the exactly-one repo id a ticket targets by
      reading the configured routing signal (a label with the configured prefix, a component,
      or a field), and it FAILS CLOSED by name (TrackerRoutingError) when the signal is missing,
      names an unknown repo, or resolves to more than one repo - it never guesses.
  - id: AC3
    text: tracker_for_repo(repo_id, config) returns the tracker id and project a repo maps to,
      and raises by name when the repo is not declared in the config, so downstream intake and
      mirror always know exactly where a repo's tracker lives.
  - id: AC4
    text: The resolver is pure stdlib and side-effect-free (config in, answer out; no network, no
      write), so it is deterministic and gate-testable offline, and a template config ships so an
      adopting org has a starting point.
  - id: AC5
    text: A selftest drives the resolver over temporary configs and tickets - a label-routed
      ticket resolves to its repo, a component-routed and a field-routed config resolve too, and
      a missing signal, an unknown repo, an ambiguous (two-repo) signal, and a malformed config
      each fail closed by name - and is non-tautological (with the routing signal present the
      ticket resolves; with it removed it is refused).
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/tracker.py, a template config, a selftest block, and
  this spec; no protected path; pure stdlib, read-only, no network.
---

## Intent

The spine of the tracker integration: given one Jira project spanning many VELDO repositories,
answer two questions deterministically and offline - which repository does this ticket target,
and which tracker and project serves this repository. Everything downstream (intake, the mirror,
the epic structure) routes off these answers, so they must fail closed rather than guess.

## Context

W1 of PLAN-0006. It is pure configuration and resolution, no network and no tracker adapter yet
(that is the seam in W3). The config is per-org and generic; the resolver is the one place that
knows how a ticket names its repo. Routing enforcement in planning and spec creation (W2) and the
Jira intake and mirror (W4, W5) consume this resolver.

## Notes

The config is .veldo/trackers.json (structured, nested, stdlib json) rather than YAML-ish front
matter, following the fleet_env.json precedent for nested structured config. The default routing
mechanism is a label convention (a configurable prefix, e.g. veldo-repo:) so it works on a stock
Jira project with no custom fields; component and a named custom field are the other configured
mechanisms. A ticket is a plain dict (labels, components, fields) so the resolver is adapter
agnostic - the Jira adapter (W4) maps a real issue into that shape. Everything fails closed: a
missing, unknown, or ambiguous routing signal raises TrackerRoutingError and never defaults to a
repo, because a misrouted spec is worse than a refused one.
