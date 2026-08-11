---
schema: veldo.spec/v1
id: WARP-0602
title: Per-repo routing enforcement in planning and spec creation
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W2
plan_revision: 1
depends_on: [WARP-0601]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An optional front-matter field tracker_repo is accepted on BOTH a veldo.spec/v1 spec and
      a veldo.plan/v1 plan - it names the repo the work targets when it is mirrored to an external
      tracker, because one tracker project (a Jira project) spans many repos. It is OPTIONAL: a
      spec or plan that omits it (every spec and plan in this repo today) stays valid, the
      single-repo default.
  - id: AC2
    text: When tracker_repo is present it must be a non-empty string, or validate.py fails by name
      (a bare or blank tracker_repo, and a non-string value such as a list, are each rejected);
      this holds for both the spec check and the plan check, independent of whether a tracker
      config exists.
  - id: AC3
    text: When tracker_repo is present AND a tracker config exists for this repo
      (.veldo/trackers.json, loaded via .veldo/tracker.py load_tracker_config), the value MUST be a
      known repo id in that config; a value naming an unknown repo FAILS CLOSED by name, because a
      routing target nobody can resolve is a decision nobody made. The known-repo set comes from
      the resolver (.veldo/tracker.py); config parsing and resolution are NOT reimplemented here.
  - id: AC4
    text: When tracker_repo is present but NO tracker config exists (load returns an empty config
      because the integration is not wired for this repo), the field is ALLOWED but not enforced;
      and when tracker_repo is absent there is no constraint at all. Enforcement runs parallel to
      the existing lane-field checks in check_spec and check_plan.
  - id: AC5
    text: A selftest drives validate over temporary spec and plan fixtures plus a temporary
      .veldo/trackers.json and is non-tautological - a resolvable tracker_repo passes, an
      unresolvable one (an unknown repo) fails by name, a non-string or empty one fails, an absent
      one passes, and a present one passes when no config is wired; the SAME tracker_repo value
      that passes against a config declaring it fails against a config that does not, so the check
      is proven to read the config and not merely the field.
required_evidence: [unit]
rollback: git revert; additive - an optional field plus enforcement in .veldo/validate.py, a
  selftest block, one capability entry in both capabilities.yaml copies, a documented line in the
  plan and spec skills, and this spec; no protected path; pure stdlib, no network.
---

## Intent

Routing is the spine of the tracker integration (PLAN-0006): because one tracker project spans
many repos, every mirrored spec and plan must name exactly one resolvable target repo. This item
makes that mechanical. It adds an optional tracker_repo field to the spec and plan contracts and
enforces it in validate.py the same way the lane fields are enforced - present-but-unresolvable
fails closed by name, so a misrouted work item is refused at the gate rather than mirrored to a
target nobody can resolve. The routing resolver already exists (WARP-0601); this consumes it.

## Context

W2 of PLAN-0006, depending on the routing resolver (WARP-0601). The resolver (.veldo/tracker.py)
reads the per-org config (.veldo/trackers.json, veldo.tracker/v1) and knows the set of routable
repos; enforcement reuses it for both the config load and the known-repo set rather than parsing
the config a second time. The field is optional and this repo has no tracker config, so every
existing spec and plan is unaffected: enforcement only bites when a tracker_repo is declared, and
only fails closed when a config is present and the value is not one of its repos.

The /veldo:plan and /veldo:spec skills document the PROCEDURE - when creating tracker-routed work,
set tracker_repo from the resolver - while the mechanical teeth live in validate.py. This is the
same split the method uses elsewhere: the skill runs the dialogue, the validator makes the
constraint real.

## Out of scope

No live tracker code (Jira/Confluence intake and the mirror are WARP-0604 onward). No change to
the resolver or the config format (WARP-0601). No run-time enforcement in /veldo:run beyond what
the gate already does. validate.py is an ordinary validator file, not a protected path, so this
change needs no human approval.

## Notes

The enforcement helper (check_tracker_repo) is shared by check_spec and check_plan so the rule is
identical on both contracts. Presence is keyed on the field being declared: a bare tracker_repo
(no value) or a non-string value is present-but-invalid and fails by name, which is the
fail-closed posture - a malformed routing target is worse than an absent one. The known-repo set
is read through .veldo/tracker.py (_known_repo_ids), so if the resolver's notion of a routable repo
ever changes, enforcement follows it with no second source of truth.
