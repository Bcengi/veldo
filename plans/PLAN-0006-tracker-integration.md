---
schema: veldo.plan/v1
id: PLAN-0006
title: Tracker integration - Jira/Confluence intake and a one-way, event-driven mirror
kind: mvp
status: released
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-18T15:31:50Z

outcomes:
  - id: O1
    becomes_true: An organization running ONE Jira project across MANY VELDO repositories can
      route every ticket and epic to exactly the repository it targets, and VELDO planning and
      spec creation land the work in that repository automatically - no one-project-per-repo
      assumption.
    measure: a ticket carrying the configured routing signal resolves to exactly one repo via
      the resolver and an intake run creates the spec in that repo; a ticket with a missing or
      unresolvable routing signal is refused by name, never guessed.
  - id: O2
    becomes_true: A person who never opens a repository can file a report or fill a
      requirements page in their own tool, and it becomes a routing-resolved VELDO spec draft
      through the EXISTING intake pipeline, with no one hand-writing a spec file.
    measure: a Jira-ticket fixture and a Confluence requirements-page fixture each produce a
      valid veldo.spec/v1 draft bound to the resolved repo, with the report or requirement
      captured as acceptance criteria and the source linked back.
  - id: O3
    becomes_true: The tracker reflects live status with nobody updating it by hand - lifecycle
      events on the stream drive a one-way, effectively read-only mirror of spec and plan
      status back onto the ticket and epic, and the repository stays the single source of truth.
    measure: replaying spec.ready to spec.shipped over the fake tracker moves the ticket
      through its mapped statuses and posts the closing comment; replaying the same events again
      is idempotent (no duplicate transition or comment); an edit made on the tracker never
      changes a spec or plan definition.
  - id: O4
    becomes_true: The whole integration is generic and provable offline - it ships a
      deterministic fake tracker so intake and mirror are gate-tested with no live network or
      credentials, and it is configurable per organization with no vendor lock-in.
    measure: the conformance selftest passes against the fake tracker in the gate on this box; a
      deliberately broken mapping (wrong routing, or a mirror attempting to write a work
      definition) fails the selftest by name.

non_goals:
  - id: NG1
    text: This plan does not make the tracker a source of truth or a second board. The
      repository index and the Product Plan burn-down remain the board; the tracker is intake
      plus mirror only.
  - id: NG2
    text: It does not build a control-plane tracker service, a webhook bus, or any
      bidirectional sync. The mirror is one-way (repo to tracker) and event-driven; a hardened
      service is a later control-plane concern, not this increment.
  - id: NG3
    text: It does not couple VELDO to Jira or Confluence. They are the first two adapters behind
      a provider-agnostic seam; the routing and mirror contracts are vendor-neutral, and Jira
      Data Center is a later adapter behind the same seam (Cloud first this release).
  - id: NG4
    text: It does not auto-transition human-owned tracker workflow outside the mapped VELDO
      status set, and it never pulls security or personal-data reports into automation (those
      route straight to a human, per the intake exception).

constraints:
  - id: C1
    text: The repository is the single source of truth. The tracker is an intake surface plus a
      one-way mirror; nothing in the tracker ever defines work, the mirror writes only status
      and comments (never a spec or plan definition), and if the tracker and the repository
      disagree the repository wins.
  - id: C2
    text: The mirror is driven ONLY by the lifecycle event stream (.veldo/events.jsonl
      vocabulary) and every consumer is idempotent by event id (at-least-once delivery). No
      polling the tracker to detect repo changes, and no database-as-a-bus.
  - id: C3
    text: Reuse, do not reinvent. Intake reuses skills/intake; the mirror reuses the existing
      event stream, the capability manifest, and the derived-index pattern (update_index.py
      projects repo to a view; the mirror projects repo to a tracker); binding reuses the spec
      lane fields plus a routing field. No parallel machinery.
  - id: C4
    text: Capabilities, not credentials. The tracker is reached through a narrow,
      least-privilege adapter with a scoped token from the secrets store; no raw tracker
      credentials in any agent context, prompt, proof, or log; tracker content is untrusted
      input, never instructions.
  - id: C5
    text: Every capability is honest in .veldo/capabilities.yaml (mechanical | reference |
      procedure | absent). Anything needing a live Jira/Confluence is reference-wired per org,
      never claimed mechanical; the fake-tracker path is what runs in the gate.
  - id: C6
    text: Proportionate and generic. The standard install is a generic adapter against a STOCK
      Jira project (map VELDO statuses onto the project's existing statuses via config); an
      opinionated custom-Jira overlay (custom fields, a status workflow mirroring spec status)
      is an optional config, never a fork. No company-specific content, no one-project-per-repo
      assumption; routing and tracker binding are per-org config files (contracts are files
      before APIs).

feature_tree:
  - id: F1
    title: Routing and configuration - the per-org binding that says which repo a ticket/epic
      targets and which tracker a repo maps to
    outcome_refs: [O1]
  - id: F2
    title: Intake - external reports and requirements pages become routing-resolved VELDO spec
      drafts through the existing pipeline
    outcome_refs: [O2]
  - id: F3
    title: Mirror - a one-way, event-driven, read-only status projection from the repository
      onto tracker tickets and epics
    outcome_refs: [O3]
  - id: F4
    title: Conformance - proof over a fake tracker that intake and mirror behave offline and
      that the tracker never becomes a source of truth
    outcome_refs: [O1, O2, O3, O4]

work:
  - item: W1
    spec: WARP-0601
    title: Tracker routing contract + per-org config + resolver - a veldo.tracker/v1 config
      (.veldo/trackers.yaml) mapping repo to tracker/project and declaring the routing-field
      mechanism (default a label convention veldo-repo:<repo-id>), and a pure .veldo/tracker.py
      resolver answering which repo a ticket targets and which tracker/project serves a repo;
      no network
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-0602
    title: Per-repo routing enforcement in planning and spec creation - validate.py and the
      /veldo:plan pull and /veldo:spec draft consume the resolver so a mirrored spec/plan names
      exactly one resolvable target repo; an unresolvable or ambiguous target fails closed,
      paralleling the lane-field checks
    feature_refs: [F1]
    depends_on: [WARP-0601]
    order: 20
  - item: W3
    spec: WARP-0603
    title: Provider-agnostic tracker adapter seam + deterministic FakeTracker - an abstract
      adapter (list intake items, read item, comment, set mapped status, create/update epic and
      child) with an in-memory fake for the gate, keeping the integration vendor-neutral
    feature_refs: [F2, F3]
    depends_on: [WARP-0601]
    order: 30
  - item: W4
    spec: WARP-0604
    title: Jira INTAKE adapter (Cloud REST first) - reads a Jira ticket through the seam,
      resolves its target repo via the routing config, and feeds skills/intake to draft the
      spec in that repo (reproduction as AC1), linking the ticket; a ticket with no resolvable
      repo is refused by name
    feature_refs: [F2]
    depends_on: [WARP-0602, WARP-0603]
    order: 40
  - item: W5
    spec: WARP-0605
    title: Event-driven spec MIRROR - a one-way projection consuming the lifecycle stream
      (spec.ready, spec.blocked, verdict.recorded, spec.shipped, merge.completed), mapping VELDO
      status to the project's configured statuses and posting the closing comment; idempotent by
      event id; writes status and comments only, never a definition
    feature_refs: [F3]
    depends_on: [WARP-0602, WARP-0603]
    order: 50
  - item: W6
    spec: WARP-0606
    title: plan-creates-structure epic/child mirror - plan.created, plan.approved, plan.revised,
      work.pulled events create/update the tracker EPIC (routing field set to the plan's target
      repo) and its child issues from the work DAG, one-directionally, mirroring the burn-down;
      per-repo routing enforced on epics
    feature_refs: [F3]
    depends_on: [WARP-0605]
    order: 60
  - item: W7
    spec: WARP-0607
    title: Confluence requirements-template intake - a structured requirements page (template
      shipped) carrying the repo routing signal flows into the intake pipeline and out as a
      routing-resolved VELDO spec draft (structured requirement in, spec out)
    feature_refs: [F2]
    depends_on: [WARP-0604]
    order: 70
  - item: W8
    spec: WARP-0608
    title: Tracker conformance selftest - drives intake (routing-resolved draft) and mirror
      (event-replay status + idempotency + one-way guard) end to end over the FakeTracker with
      no live network, plus honest capabilities.yaml entries; a broken mapping or a
      write-back-of-definition attempt fails named
    feature_refs: [F4]
    depends_on: [WARP-0604, WARP-0605, WARP-0606, WARP-0607]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: The conformance selftest proves routing-resolved intake and event-driven read-only
        mirror over the fake tracker and fails on a broken mapping - no rubber-stamp
      activation: {when: start}
      owner_spec: WARP-0608
      profiles: [per_spec, release]
      suite: scripts/selftest.py (tracker intake + mirror fixtures over FakeTracker)
    - id: RJ2
      title: The tracker never becomes a writer of work definition - a mutation from the tracker
        back into a spec/plan definition is rejected and the repository stays source of truth
      activation: {when: after:WARP-0605}
      owner_spec: WARP-0608
      profiles: [release]
      suite: scripts/selftest.py (one-way mirror guard fixture)

release:
  milestone: VELDO tracker integration v1 - routing, stock-Jira Cloud intake, event-driven
    mirror, Confluence intake, proven offline
  version: plugin 3.3.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: every piece is additive under .veldo/ and engine/; a repo drops the
    integration by removing its .veldo/trackers.yaml (the resolver then no-ops) and pinning the
    prior plugin version.

open_decisions: []
---

## Intent

VELDO repositories are the source of truth; the people who report bugs, request features, and
sign off on requirements live in Jira and Confluence and always will. This increment builds the
two edges the method already names - INTAKE (reporters in their own words) and MIRROR
(auto-synced, effectively read-only status) - as generic, provable machinery, with one hard
addition: because one Jira project covers many VELDO repositories, routing is first-class. Every
ticket and epic declares which repo it targets, VELDO consumes that routing to land specs in the
right place, and the mirror writes status back the same way update_index.py projects the index
today: derived, one-directional, never a second source of truth.

## Decisions baked in (founder-approved 2026-07-18)

The standard install is a GENERIC adapter against a STOCK Jira project (VELDO statuses map onto
the project's existing statuses via trackers.yaml); a custom-Jira overlay is an optional config,
not the default and not a fork. Confluence requirements-template intake IS in this release (W7).
Jira Cloud REST first; Data Center is a later adapter behind the same W3 seam. Auth is
capabilities-not-credentials: a scoped token from the secrets store, never raw creds in an agent.
The routing-field default is a label convention (veldo-repo:<repo-id>), with component and
custom-field as config options. Mirror granularity is 1 spec to 1 ticket, 1 plan to 1 epic, work
items to child issues.

## Context

The unit of reuse is deliberate. Intake is already a shipped procedure (skills/intake); this adds
routing to it, not a new pipeline. The mirror rides the existing event vocabulary in
.veldo/events.py - the events already emitted - so the mirror is a new consumer of an existing
stream, not new plumbing. The tracker is reached behind a provider-agnostic seam with a
deterministic fake, so the whole thing is gate-tested offline and Jira/Confluence are the first
two implementations, not the design.

## Ordered delivery rationale

Routing is the spine, so it ships first (W1) and is enforced in planning/spec creation (W2)
before anything writes to a tracker. The adapter seam and fake (W3) are the vendor-neutral
boundary both intake and mirror stand on. Intake (W4) and the spec mirror (W5) are independent
once routing and the seam exist, so they are parallel on the frontier. The plan/epic mirror (W6)
extends the spec mirror to the planning layer. Confluence intake (W7) reuses the Jira intake path.
The conformance selftest (W8) is last because it proves the whole surface at once over the fake
tracker.

## Revisions

Revision 1 (2026-07-18): created from the tracker-integration design and approved by the founder -
routing-first, a stock-Jira Cloud intake adapter, an event-driven one-way mirror, plan-creates-
structure epics, Confluence intake in v1, all proven offline over a deterministic fake tracker.
