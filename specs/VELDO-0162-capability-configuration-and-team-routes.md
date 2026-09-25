---
schema: veldo.spec/v1
id: VELDO-0162
title: The owner saves capability configuration revisions and team revisions through typed API routes the authority executes, and a team revision becomes current on his settled answer
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W122
plan_revision: 4
depends_on: [VELDO-0064, VELDO-0068, VELDO-0089, VELDO-0127, VELDO-0130, VELDO-0151]
placement: [contracts, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "packs/*/.veldo/control_agent_config*.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "packs/*/.veldo/control_team*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0162_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0162-capability-configuration-and-team-routes.md"
  - "specs/index.md"
  - "proof/VELDO-0162/*"
behavior_bearing: true
observability:
  logs: >
    Record each capability configuration save and each team proposal with the route, the verified
    principal, the base revision or team version and the resulting revision, each team request opened
    and each settled answer applied, and each named refusal; never a credential value.
  metrics: >
    Count configuration saves and team proposals accepted and refused by reason, team requests opened,
    and answers applied or declined.
  traces: >
    Join each save to the API session, the assertion, the authority command and the revision it made,
    and each team revision to its proposal, its request and the settlement that made it current.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, invalid configuration, incomplete roster,
    a role whose configuration reference resolves to nothing, a declined answer and unavailable service;
    none is reported as a saved or current revision.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A capability configuration revision is saved only through the API's configuration route
      and the authority's VELDO-0127 revision command, and is read back through a route. Set and
      completeness: In a passkey session (VELDO-0130), save the configuration of a role `builder_jira`
      (engine, native tools, MCP selections naming catalog server revisions including the Atlassian
      server, skills, instruction files and engine settings, each item with its load mode) as the typed
      assertion operation `save_capability_configuration`, which the authority executes as VELDO-0127's
      revision command for the verified principal and the revision it was edited from; save a second
      revision; read both through the configuration read route and compare every field with what was
      sent and with the stored revisions. A save from an older revision is refused `stale_version`, one
      from a member VELDO-0127's command does not authorize `unauthorized`, and one VELDO-0127's schema
      rejects by its named refusal, each storing nothing; compare the route-to-command registrations,
      with no browser-side authority and no direct store write. Falsifier: Store a configuration save
      without the authority's command checking the principal; the unauthorized-save row must fail.
    falsified_by: >
      Store a configuration save without the authority's command checking the principal; the
      unauthorized-save row must fail.
  - id: AC2
    text: >
      Claim: A team revision is proposed only through the API's team route and the authority's VELDO-0089
      `propose` command, with VELDO-0151's role fields, and the team is read back through a route. Set and
      completeness: Save a project's team with the four required roles, and then one that adds the
      specialist role `builder_jira` naming the configuration of AC1, as the typed assertion operation
      `propose_team`, which the authority executes as VELDO-0089's `propose` for the verified principal,
      bound to the team version the save was edited from; read the team through the team read route with
      its current revision, its pending proposal and each role's kind and configuration reference. A
      save bound to an older team version is refused `stale_subject:version`; a role with no
      configuration reference, or one that resolves to no accepted configuration, returns VELDO-0151's
      refusal, and an incomplete roster `incomplete_roster`, each with the owner request those
      specifications open, by name to the caller and with no team written. Falsifier: Accept a team save
      bound to an older team version; the stale-team row must fail.
    falsified_by: >
      Accept a team save bound to an older team version; the stale-team row must fail.
  - id: AC3
    text: >
      Claim: A proposed team revision becomes current only by the project owner's settled answer to one
      request that shows exactly that proposal. Set and completeness: After an accepted `propose_team`,
      the authority opens one VELDO-0064 decision request to the project's current owner on VELDO-0089's
      amendment touchpoint, whose brief and target are exactly VELDO-0089's amendment brief and target of
      the pending proposal; a repeat save of the same proposal returns that request. Answer it through the
      API's decision route (VELDO-0130) and, for a second proposal, from Telegram; the authority applies
      the settlement (VELDO-0068) as VELDO-0089's `amend`, and the team read route shows the new revision
      current. A decline leaves the earlier revision current, and this holds when the owner made the save
      himself. Falsifier: Make a proposed team revision current without the owner's settled answer; the
      owner-answer row must fail.
    falsified_by: >
      Make a proposed team revision current without the owner's settled answer; the owner-answer row must
      fail.
required_evidence: [unit, integration]
rollback: >
  Remove the configuration and team routes and their assertion operations; capability configuration
  revisions, team revisions, pending proposals and their requests are kept. No automatic rollback is
  authorized.
---

## Intent

In the design's second stage the owner gives a role the Atlassian server and puts that role in a
project's team, from his phone or desktop, before the full UI exists. For that the API needs a way to
save a capability configuration revision and a team revision, each executed by the authority's own
command, and a team revision needs his answer to become current.

## Context

W122 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Sections 4 and 6
of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner
Telegram 29162) have the owner save a role's capability configuration as a new revision and set a
project's team as versioned data, and its section 12 promises that "please do BCG-123" works at the end
of its second stage. VELDO-0151 refuses a team whose roles have no accepted VELDO-0127 configuration, but
the API's route table (`ROUTES` in `control_api`) has only the workflow save in its configuration family,
and VELDO-0130's History names team and agent configuration edits as having no typed command and so no
route. VELDO-0089's `propose` and `amend` exist in `control_team`, and nothing opens the request its
`amend` consumes. So on the fourth review of revision 4 this new specification adds the routes and the
request, built in the second stage after VELDO-0127 and VELDO-0151, and VELDO-0163 builds the form that
uses them. This new specification is draft; authoring it supplies neither implementation proof nor
operational activation.

## Out of scope

The role and team form (VELDO-0163); the full team and configuration screens with revision history
(VELDO-0131); any change to VELDO-0089's, VELDO-0127's or VELDO-0151's own checks; a PM that edits its
own team (design section 4(f)); amendment races (Release 2).

## What the reviewer judges

- Normal use: the owner, in a passkey session, saves a role's capability configuration and a project's
  team through the API; the authority executes each save as its owning command, and the team revision
  becomes current when he answers the request that shows it, in the UI or on Telegram.
- Threat model: a configuration or team written without the authority's command or for a principal the
  command does not authorize; a save that overwrites a newer revision; a team made current without the
  owner's settled answer, or on an answer to a request that showed something else; a refusal reported
  as a save; a credential value in a response or proof. The owner's account, the API, the store and the
  signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); amendment races
  and mid-cycle changes (Release 2); the form and screens VELDO-0163 and VELDO-0131 own; forged rows in
  our own store and files planted in the installed directory.

## Notes

Each save is an assertion operation of the api edge, like `save_workflow` (VELDO-0130's History), which
the authority rechecks and executes as the owning command: VELDO-0127's revision command for a
capability configuration and VELDO-0089's `propose` for a team, with VELDO-0151's role fields. The
request of AC3 is the one VELDO-0089's `amend` already checks for (its brief, its target, the project's
owner as its only principal), so `amend` is used as it is. The owner answering a request for his own
save follows VELDO-0089 AC2, which makes a team change settle through the retained settlement path.

Use canonical engine assets and synchronize installed copies. Inventory every asset the selected
journey installs. Compare executable registrations to each criterion's declared universe, observe the
real named interfaces, and retain the driven negative-control diff and named failed row. Fixtures
cannot certify real engine or host behavior. Required evidence labels describe future implementation
proof, not tests run by this writing revision.

## History

2026-09-25: written on the fourth review of PLAN-0019 revision 4. The owner could not give a role the
Atlassian server in the design's second stage: VELDO-0151 refuses a team whose roles have no accepted
VELDO-0127 configuration, and no surface of the first or second stage could create a configuration
revision or a team revision. This specification adds the typed routes and the team request, and
VELDO-0163 the form; VELDO-0131 depends on both and no longer builds the role form. A draft: only the
owner marks a specification ready.
