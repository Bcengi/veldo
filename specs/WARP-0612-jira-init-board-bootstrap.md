---
schema: veldo.spec/v1
id: WARP-0612
title: veldo jira init - a codified, generic, idempotent bootstrap that stands a company-managed Jira
  project up as the live Veldo board (statuses + workflow provisioned, every plan and spec mirrored)
status: shipped
risk: standard - this composes on the released tracker foundation (PLAN-0006 seam/mirror + PLAN-0010
  live edges) and is REPO-ONLY build machinery (a sibling of tracker_mirror_runner.py, in the tracker
  architecture area). It touches NO protected path (verify.sh, veldo-guard.sh, policy.yaml,
  policy_check.py and their template twins are untouched) and nothing in the production-support safety
  core (the executor, whitelist, two-key rule, kill switch, or ladder), so per policy.yaml the floor is
  standard. It DOES perform live external writes at run time (provisioning statuses + a workflow, then
  the mirror), but that path is REFERENCE-WIRED exactly like the shipped JiraCloudAdapter and the live
  mirror runner: it is never exercised in the gate (the FakeTracker path is), it fails closed without a
  token, and running it live against a real board is a separate, explicit, human-driven act (like veldo
  mirror), not part of landing this spec. The mechanical footprint stays inside the single tracker area,
  so it crosses no architecture boundary and the footprint tier floor does not elevate it
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W1
plan_revision: 1
placement: [tracker]
footprint:
  - .veldo/tracker_jira_init.py
  - .veldo/tracker_adapter.py
  - .veldo/architecture.yaml
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - engine/.veldo/trackers.json
  - engine/bin/veldo
  - packs/*/.veldo/capabilities.yaml
  - packs/*/bin/veldo
  - bin/veldo
  - scripts/selftest.py
  - specs/WARP-0612-jira-init-board-bootstrap.md
  - specs/index.md
  - proof/WARP-0612/**
protected_paths: []
behavior_bearing: true
observability:
  logs: The bootstrap emits a structured report of exactly what reached the board (project, detected
    type, issue types added vs reused, statuses created vs reused, workflow wirings made vs already
    present, epics/children mirrored, transitions), so a stranger can see what one pass did from the
    report alone; the CLI prints that summary as JSON.
  error_taxonomy: Every failure is a NAMED result, never a silent no-op - a malformed bootstrap config or
    a wrong project type is BootstrapError (the message names the project, its actual type, the required
    type, and the remediation), a configured issue type the instance does not hold fails loud by name
    (the fake raises TrackerItemNotFound naming the type; the reference live provisioner raises
    BootstrapError) rather than falling back to a wrong type, an unresolved live token is a fail-closed
    adapter error, and a project the fake does not hold is TrackerItemNotFound - so a failed bootstrap is
    diagnosable from the message.
acceptance_criteria:
  - id: AC1
    text: The bootstrap is GENERIC and reads every input BY REFERENCE from .veldo/trackers.json (a
      'bootstrap' block plus the existing routing/status_map/trackers): the project key, the required
      project type, the epic/child issue-type names, the status names and their categories (To Do |
      In Progress | Done), the base URL, the token as a secret reference (env:/keychain:, never a raw
      credential), the intake JQL, and the assignee. Nothing is hardcoded to any company or board -
      .veldo/tracker_jira_init.py contains no company-specific or board-specific literal (grep-clean),
      and a malformed bootstrap block fails closed by name (BootstrapError) at resolve time.
  - id: AC2
    text: It DETECTS the project type FIRST and FAILS LOUD on a mismatch, before any write. A project
      that is not the configured required type (default company-managed) - a team-managed project, whose
      status workflow is UI-only and cannot be fully provisioned via the API - is refused with a
      BootstrapError that NAMES the project, its actual type, the required type, and the remediation
      ("recreate <project> as a company-managed project and re-run"); because detection precedes the
      first provision_status call, a refused project is left with NO status provisioned (never a
      half-provisioned board).
  - id: AC3
    text: It provisions the configured lifecycle status set IDEMPOTENTLY (create a status by name if the
      project lacks it, reuse it if present - never a duplicate) AND wires each into every configured
      issue type's workflow idempotently (wire if absent, no-op if already reachable), through the
      WARP-0603 provisioning seam (project_type, existing_status_names, provision_status,
      workflow_status_names, wire_status_into_workflow) added to the TrackerAdapter base and modeled by
      the FakeTracker. Re-running over the same board creates no status and wires nothing and leaves the
      board byte-identical; a partial board has its MISSING statuses created and its PRESENT ones reused
      (an absent status is created, never silently skipped).
  - id: AC4
    text: It REUSES the shipped one-way mirror (tracker_mirror_runner.run_from_repo, feeding
      tracker_mirror.mirror_events / mirror_plan_events, WARP-0605/0606/1004..1006) to project every plan
      onto an epic and every spec onto a child with its mapped status over the SAME provisioner object -
      it reimplements no mirror logic. The mirror's idempotent upsert (keyed by a stable marker) forks no
      epic or child and records no duplicate transition on a re-run, so the whole bootstrap (provision +
      mirror) is idempotent.
  - id: AC5
    text: It is integrated into the setup flow as ONE command, veldo jira init (a bin/veldo subcommand
      routing to the repo-only .veldo/tracker_jira_init.py, guarded by the same existence check as veldo
      mirror so a pack that did not lay the module fails loud and honestly rather than import a missing
      file). veldo jira init --dry-run previews the whole bootstrap over an in-memory FakeTracker with no
      network and no token; without it the live company-managed provisioner is built from the tracker
      connection block and FAILS CLOSED when no token resolves. The live JiraCompanyManagedProvisioner is
      REFERENCE-WIRED (a JiraCloudAdapter subclass against Jira Cloud REST v3) and is NEVER run in the
      gate; it creates no timer, daemon, or auto-start and spawns nothing detached (NG1).
  - id: AC6
    text: A selftest drives the WHOLE bootstrap over the deterministic FakeTracker offline (no network) -
      a fresh company-managed board provisions all nine statuses and wires each into both issue types; a
      re-run creates and wires nothing and leaves the board byte-identical; a team-managed project fails
      loud by name and provisions nothing; a partial board creates the missing statuses and reuses the
      present ones; and the reused mirror forks no epic/child on replay - and it is NON-TAUTOLOGICAL: an
      in-memory mutation that removes the team-managed fail-loud lets a team-managed project proceed while
      the real module refuses, and an in-memory mutation that removes the create-or-reuse guard duplicates
      a status on a re-run while the real module stays idempotent (the real module byte-unchanged).
  - id: AC7
    text: It ENSURES the configured ISSUE TYPES exist and ADDS any that are missing, and NEVER falls back
      to a wrong type ("add types if they are missing, don't use wrong types"). Through a vendor-neutral
      issue-type seam added to the TrackerAdapter base (existing_issue_types read-only; provision_issue_type
      ensure-present, idempotent by name - reuse a type the project already has, else attach the instance's
      matching type to the project, e.g. for a company-managed Jira project by adding it to the project's
      issue-type SCHEME) and modeled by the FakeTracker (a per-project set of issue types plus an instance
      catalog of addable types), provision_board ensures EVERY configured type (the epic type for plans and
      the child type for specs) exists BEFORE any status is wired into a type's workflow and BEFORE the
      mirror creates epics/children, so a fresh company-managed project that lacks an Epic type has it added
      rather than the epic creation or workflow wiring failing. It is IDEMPOTENT (a re-run adds no type and
      leaves the board byte-identical) and it FAILS LOUD by name on a configured type the instance does not
      hold (the FakeTracker refuses by name; the reference live provisioner raises BootstrapError) - never a
      silent skip and never a wrong-type fallback (it will not map a plan onto a Sub-task). The live
      company-managed edge (look up the instance issue type by name, GET the project's issue-type scheme,
      POST the type id to /rest/api/3/issuetypescheme/{schemeId}/issuetype) is REFERENCE-WIRED and NEVER run
      in the gate; a selftest proves the create-if-missing, the present-is-a-no-op positive control, the
      before-statuses ordering, and the fail-loud over the FakeTracker offline, each with an in-memory
      source-mutation tooth (neutralizing the add makes the missing type stay absent; neutralizing the
      fail-loud lets a nonexistent type be invented) that turns the assertion red while the module on disk
      stays byte-unchanged.
required_evidence: [unit]
rollback: git revert; additive - a new repo-only .veldo/tracker_jira_init.py, a provisioning seam added
  to .veldo/tracker_adapter.py (repo-only) and modeled by the FakeTracker, a veldo jira init subcommand in
  bin/veldo (root + template + 6 packs, byte-identical), one capability entry (all eight capabilities.yaml
  copies), a bootstrap example + aligned status_map in the template trackers.json, the new tracker module
  added to the tracker area of the architecture contract, a selftest block, and this spec; no protected
  path; pure stdlib; the live provisioner is reference-wired and never run in the gate.
---

## Intent

Setting up the Veldo board must be driven by CODE, not by a conversation. The founder's requirement,
verbatim intent: "Bootstrap this with CODE, not via LLM - so when jira init is done, I do not have to
drive it in chat. It cannot be fluffy fluff that breaks the moment a second person tries to set up." So
this is a repeatable, deterministic, generic bootstrap that stands a tracker project up as the live
board - provisioning the full lifecycle status set and wiring it into the workflow, then mirroring every
plan and spec onto it - runnable as one command and part of the Veldo setup flow. Any adopter drops in
their own bootstrap config and runs the same command; nothing is hardcoded.

## Context

This composes on the RELEASED tracker foundation and reuses it rather than reinventing it: the
provider-agnostic adapter seam and FakeTracker (WARP-0603), the one-way event-driven mirror
(WARP-0605/0606) and its live runner (WARP-1004..1006), and the routing/config resolver (WARP-0601).
PLAN-0006 and PLAN-0010 are both released, so this lands as a STANDALONE tracker-lineage spec (WARP-0612,
after WARP-0611), the same convention as the standalone hardening/extension specs (WARP-0113, WARP-0114,
WARP-0411, WARP-1212). Like every other tracker module it is REPO-ONLY build machinery: the VELDO home
repo's own tooling for mirroring its own work onto a board; shipping the tracker integration to adopters
via the engine is a separate release concern, so only .veldo/tracker.py is engine-synced and the new
module is not.

## The missing pieces this adds

The mirror already EXISTED; the gap was everything before it. This adds: (1) status + workflow
PROVISIONING through a new vendor-neutral seam on the adapter base, modeled by the FakeTracker for the
gate and implemented by a reference live company-managed provisioner; (2) project-type DETECTION that
fails loud on a team-managed project (empirically, team-managed lets the API create a status but leaves
workflow wiring UI-only, so full automation breaks) before any write, so the board is never
half-provisioned; (3) ISSUE-TYPE provisioning (existing_issue_types / provision_issue_type on the same
seam) that ENSURES every configured type exists and ADDS any missing one - the epic type for plans, the
child type for specs - before statuses are wired into a type's workflow and before the mirror creates
epics/children, so a fresh company-managed project that lacks an Epic type has it added instead of the
epic creation or wiring failing, and NEVER falls back to a wrong type (a type the instance does not hold
fails loud, never a plan mapped onto a Sub-task); (4) generic, by-reference CONFIG (a bootstrap block in
trackers.json); (5) IDEMPOTENCY (ensure-present issue types, create-or-reuse statuses by name,
wire-if-absent) so a second person re-running changes nothing; and (6) the veldo jira init ENTRYPOINT
wired into the CLI, which provisions and then reuses the shipped mirror in one pass.

## Why standard risk

The change touches no protected path and nothing in the production-support safety core, so the policy
floor is standard. Its live writes are reference-wired exactly like the existing JiraCloudAdapter and the
live mirror runner: never run in the gate, fail closed without a token, and applied live only by an
explicit human act. The mechanical footprint stays inside the single tracker architecture area, so it
crosses no boundary and the footprint tier floor does not raise it.

## Running it live

Against a real company-managed board (once it exists), with the tracker wired in .veldo/trackers.json
(base_url + a token_ref secret reference in the jira-cloud tracker block, plus a bootstrap block naming
the project and its statuses): `veldo jira init --dry-run` previews offline, then `veldo jira init` applies
it live. The token is resolved from the environment/secrets store named by token_ref (never a raw
credential in the config); it creates nothing that runs on its own and a re-run reconciles.
