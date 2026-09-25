---
schema: veldo.spec/v1
id: VELDO-0162
title: The owner saves capability configuration revisions, team revisions and the default team through typed API routes the authority executes, and a team revision becomes current on his own authenticated save or on his settled answer to another member's proposal
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W122
plan_revision: 4
depends_on: [VELDO-0064, VELDO-0068, VELDO-0089, VELDO-0127, VELDO-0130, VELDO-0151, VELDO-0152]
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
    principal, the base revision or team version and the resulting revision, each default team
    revision and each project given one, each team request opened and each settled answer applied, and
    each named refusal; never a credential value.
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
      Claim: A team revision is saved only through the API's team route and the authority's VELDO-0089
      team commands, with VELDO-0151's role fields, and the team is read back through a route. Set and
      completeness: Save a project's team with the four required roles, and then one that adds the
      specialist role `builder_jira` naming the configuration of AC1, as the typed assertion operation
      `propose_team`, which the authority executes for the verified principal as AC3's owner-save path
      when that principal is the project's owner and as VELDO-0089's `propose` otherwise, either way bound
      to the team version the save was edited from; read the team through the team read route with its
      current revision, any pending proposal and each role's kind and configuration reference. A
      save bound to an older team version is refused `stale_subject:version`; a role with no
      configuration reference, or one that resolves to no accepted configuration, returns VELDO-0151's
      refusal, and an incomplete roster `incomplete_roster`, each with the owner request those
      specifications open, by name to the caller and with no team written. Falsifier: Accept a team save
      bound to an older team version; the stale-team row must fail.
    falsified_by: >
      Accept a team save bound to an older team version; the stale-team row must fail.
  - id: AC3
    text: >
      Claim: A team revision the project owner saves himself through the authenticated API becomes
      current on that save, recorded as his decision, and a revision anyone else proposes becomes
      current only by his settled answer to one request that shows exactly that proposal. Set and
      completeness: Save a team revision as the owner through the API; the team read route shows it
      current, the journal records the owner's authenticated principal as its decider, and no decision
      request is opened, as VELDO-0150 treats his own message. Then have another principal (a second
      person member in a passkey session) submit `propose_team`; the authority opens one VELDO-0064
      decision request to the project's current owner on VELDO-0089's amendment touchpoint, whose brief
      and target are exactly VELDO-0089's amendment brief and target of the pending proposal, and a
      repeat submission returns that request. Answer it through the API's decision route (VELDO-0130)
      and, for a second proposal, from Telegram; the authority applies the settlement (VELDO-0068) as
      VELDO-0089's `amend`, and the read route shows the new revision current. A decline leaves the
      earlier revision current. Falsifier: Make another principal's proposed team revision current
      without the owner's settled answer, and separately open a decision request for the owner's own
      save; the owner-answer row and the owner-save row must each fail. Record a principal other than
      the verified one as the owner save's decider, and the decider row must fail; skip the edge
      signature check on the owner-save path, and the unverified-assertion row, which submits an owner
      save whose edge signature does not verify and requires it refused as the edge check's named
      refusal with no team written, must fail.
    falsified_by: >
      Make another principal's proposed team revision current without the owner's settled answer, and
      separately open a decision request for the owner's own save; the owner-answer row and the owner-save
      row must each fail. Record a principal other than the verified one as the owner save's decider, and
      the decider row must fail; skip the edge signature check on the owner-save path, and the
      unverified-assertion row must fail.
  - id: AC4
    text: >
      Claim: The factory keeps one default team, a versioned team the owner saves through the team route,
      and a new project's first team revision is the default team revision named in the proposal he
      answered. Set and completeness: Save the default team (the four required roles and a specialist
      role, each with VELDO-0089's role fields and VELDO-0151's configuration reference and kind) as the
      typed assertion operation `save_default_team`, which the authority checks with VELDO-0089's and
      VELDO-0151's schema and keeps as a new immutable revision, read back through the team read route; a
      save from an older revision is refused `stale_version` and a schema refusal is named, each storing
      nothing, and only the factory project's owner may save it. For an active project with no team, feed
      the authority an owner's settled answer to a proposal that named a default team revision (VELDO-0143
      AC1 makes such a proposal): that revision's roles become the project's first team revision, after
      VELDO-0089's and VELDO-0151's staffing checks for that project, with no further question; a staffing
      problem opens VELDO-0089's owner request and gives the project no team. Save a newer default team
      revision before the answer is applied and require the named one. Falsifier: Overwrite a saved
      default team revision in place, and the default-team history row must fail; give the project the
      default team's current revision when the answered proposal named an older one, and the
      named-revision row must fail.
    falsified_by: >
      Overwrite a saved default team revision in place, and the default-team history row must fail; give
      the project the default team's current revision when the answered proposal named an older one, and
      the named-revision row must fail.
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
(VELDO-0131); any change to VELDO-0127's or VELDO-0151's own checks, or to VELDO-0089's beyond the
owner-save path AC3 adds and `Teams.apply` accepting the edge-verified assertion; a PM that edits its
own team (design section 4(f)); amendment races (Release 2).

## What the reviewer judges

- Normal use: the owner, in a passkey session, saves a role's capability configuration and a project's
  team through the API; the authority executes each save as its owning command, and his own team save
  becomes current on that save, while another member's proposal becomes current when he answers the
  request that shows it, in the UI or on Telegram; he keeps a default
  team, which a new project he accepts starts with.
- Threat model: a configuration or team written without the authority's command or for a principal the
  command does not authorize; a save that overwrites a newer revision; a team made current without the
  owner's own authenticated save or his settled answer, or on an answer to a request that showed
  something else; the owner-save path reached by a principal other than the project's owner, or on an
  assertion the API edge did not verify; a new project given a
  default team revision other than the one his answered proposal named; a refusal reported
  as a save; a credential value in a response or proof. The owner's account, the API, the store and the
  signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); amendment races
  and mid-cycle changes (Release 2); the form and screens VELDO-0163 and VELDO-0131 own; forged rows in
  our own store and files planted in the installed directory.

## Notes

Each save is an assertion operation of the api edge, like `save_workflow` (VELDO-0130's History), which
the authority rechecks and executes as the owning command: VELDO-0127's revision command for a
capability configuration and VELDO-0089's team commands for a team (AC2), with VELDO-0151's role fields.
A save by the project's owner takes one new owner-save path in `control_team`: it binds the API edge's
verified assertion as its evidence, the way VELDO-0150 AC2 binds the intake command, compares the
assertion's principal with the project's owner, and makes the proposal current in the same commit.
`Teams.apply` accepts the edge-signed command the authority derives from the verified assertion, for
`propose` as well as the owner save, in place of an SSH signature from the principal's own key, checking
that edge signature against the edge's keyring key itself, as `send_message` in `control_api_authority`
and the intake's `_edge_verifies` do. A repeat submission of a pending proposal is looked up before the
team version check, since `propose` raises the version and the repeat would otherwise be refused as
stale. A proposal by another member takes the existing path: the request of AC3 is the one VELDO-0089's
`amend` already checks for (its brief, its target, the project's owner as its only principal), so
`amend` is used as it is, and it settles through VELDO-0089 AC2's retained settlement path.

The default team of AC4 is what a new project starts with (design section 5, step 4). It is plain team
data with no project of its own, so the project-bound staffing checks run when a project is given it,
and the project's first team revision settles on the owner's answer to the proposal that named it.

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

2026-09-25, PLAN-0019 revision 4, fourth review: new AC4, the default team. VELDO-0143 AC3 activated a new
project with a "default team template (VELDO-0089)" that VELDO-0089 does not define, so this
specification, built in the design's second stage and so before VELDO-0143, defines it: a versioned team
the factory project's owner saves through the team route, whose revision named in the answered project
proposal becomes the new project's first team revision. A draft.

2026-09-25, lead: AC3 counts the owner's own authenticated save as his decision, as VELDO-0150 does for
his own message, so he is never asked to approve a change he made himself; a revision anyone else
proposes still needs his settled answer.
