---
schema: veldo.plan/v1
id: PLAN-0010
title: Tracker-driven autonomous fleet - Jira is the work queue, assign to Agent, a human validates the spec, the fleet builds and mirrors back
kind: mvp
status: released
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-20T21:07:27Z
risk: standard

outcomes:
  - id: O1
    becomes_true: >
      A Jira ticket tagged to a known repo, moved to the Approved-for-dev status
      and assigned to the Agent user, flows into the fleet on its own: a non-LLM
      bridge intakes it into a VELDO spec, a fleet worker for that repo claims it,
      builds it through the VELDO loop, and lands it, with no one copying anything
      out of Jira by hand.
    measure: >
      In a repo wired to a live Jira project, a ticket set to Approved-for-dev +
      Agent + a resolvable repo tag results, unattended, in a landed change on the
      trunk and a spec that reached shipped, with no manual intake step.
  - id: O2
    becomes_true: >
      A human validates the spec before any development happens. The bridge drafts
      the spec and surfaces it, and only a human action in Jira (Approved-for-dev +
      Agent) promotes it to ready; nothing the machine drafts builds itself.
    measure: >
      A drafted-but-not-approved ticket produces a draft spec that the fleet does
      NOT claim; only after the human sets Approved-for-dev + Agent does the spec
      become ready and get built.
  - id: O3
    becomes_true: >
      The ticket reflects reality without anyone hand-updating it. As the worker
      builds, VELDO transitions the ticket through the human's own statuses, posts
      the artifact links (commit, and where present the PR and the proof), and at
      the ready-to-test handoff reassigns the ticket away from Agent to the named
      reviewer or tester.
    measure: >
      Following a build end to end, the ticket shows the shipped status, a comment
      carrying the commit and proof links, and an assignee that is the configured
      reviewer, none of it set by a human.
  - id: O4
    becomes_true: >
      A requirements document referenced by a kickoff ticket starts a whole plan.
      VELDO drafts a VELDO plan from the document, and the live epic mirror creates
      the epic and its child issues in Jira, each child becoming a claimable spec
      as it is approved.
    measure: >
      A kickoff ticket pointing at a requirements page yields a VELDO plan and, in
      Jira, one epic keyed to the plan plus a child issue per work item, and the
      approved children flow through O1.
  - id: O5
    becomes_true: >
      The autonomous loop stays inside VELDO's guarantees. The repository is the
      single source of truth (the mirror is one-way; if a ticket and the repo
      disagree the repo wins), tracker content is untrusted input, the workers run
      in-session, and the two unattended services (the inbound bridge and the live
      mirror runner) are non-LLM, opt-in, off by default, and inspectable.
    measure: >
      The mirror never writes a spec or plan definition back; the bridge and mirror
      runner create no artifact and run nothing until explicitly enabled; and the
      whole mechanical path is gate-tested offline against the fake tracker.

non_goals:
  - id: NG1
    text: >
      No auto-approval past the human validation gate. The machine never promotes
      its own draft to ready or decides on its own that work is fit to build; a
      human does that in Jira.
  - id: NG2
    text: >
      No LLM in the unattended path. The bridge and the mirror runner are
      deterministic non-LLM Python authed by a token reference (the 2026-07-20
      keep-tokens decision). The only LLM work is the build and the review inside a
      worker session.
  - id: NG3
    text: >
      No hosted scheduler, queue service, database, or message bus. Coordination
      stays git plus the shared run registry plus the claim ledger plus the
      tracker; the bridge is a thin poll-reconcile (webhook if the instance offers
      one), not a standing service platform.
  - id: NG4
    text: >
      No rogue or detached worker processes. A worker is a vanilla in-session
      session (PLAN-0007 NG1, restated). The bridge and the mirror runner are the
      only unattended mechanisms, and each is opt-in, off by default, visible, and
      removable, in the same posture as the fleet supervisor (WARP-0907).
  - id: NG5
    text: >
      VELDO does not become the tracker's source of truth. The mirror is strictly
      one-way; the tracker is a projection of the repository, never the definition
      of the work.

constraints:
  - id: C1
    text: >
      Eligibility is a triple, configured in .veldo/trackers.json and evaluated
      fail-closed: assignee is the configured Agent user AND status is in the
      configured ready-for-dev set (Approved-for-dev) AND the repo tag resolves to a
      known repo. A ticket assigned to a human, or in any other status, or with an
      unresolvable repo tag, is never picked up. There is a SINGLE shared Agent
      account for the whole fleet (founder decision 2026-07-20); the claim ledger,
      not the tracker, selects which worker actually runs a given unit.
  - id: C7
    text: >
      The repo tag is a validated Jira custom field ("VELDO Repo") whose allowed
      values are the known repos (a dropdown), resolved via the field mechanism and
      failing closed on any value not in the config, not a freeform label (founder
      decision 2026-07-20). At the ready-to-test handoff the mirror reassigns the
      ticket away from Agent to a per-repo configurable reviewer, defaulting to the
      ticket's reporter (founder decision 2026-07-20).
  - id: C2
    text: >
      Both the inbound bridge and the outbound mirror runner are reconcilers
      (recompute the desired state each pass and apply it), idempotent under
      at-least-once or re-poll with no processed-offset ledger: re-seeing a ticket
      never redrafts a spec, re-forks an epic, or double-posts a comment or a
      transition.
  - id: C3
    text: >
      The human validation gate is mandatory and lives in Jira. A drafted spec has
      status draft and is not claimable; promotion to ready is triggered only by
      the human moving the ticket to Approved-for-dev and assigning it to Agent,
      which the bridge maps to the promote.
  - id: C4
    text: >
      The unattended services are non-LLM, token-authed by a secret reference
      (never a raw credential in a file, prompt, proof, or log), opt-in and off by
      default, and inspectable and removable. Enabling them against a real
      instance is an explicit, human-approved step, not a default.
  - id: C5
    text: >
      Outbound the mirror writes only status, comments, artifact links, and the
      assignee on the tracker, never a spec or plan definition. It reuses the
      existing WARP-0603 adapter seam; the live edge stays a reference
      implementation wired per repo, with the mechanical logic gate-tested offline
      against the fake tracker.
  - id: C6
    text: >
      Every item is built through VELDO itself with the same gate, proof, and
      independent review, and stays proportionate: this plan fills seams and adds
      two thin services on top of the shipped tracker (PLAN-0006) and fleet
      (PLAN-0007/0009), it does not rebuild them.

feature_tree:
  - id: F1
    title: Automatic pickup - the inbound bridge, the eligibility triple, and the Agent user model
    outcome_refs: [O1, O2]
  - id: F2
    title: The human validation gate - a Jira promote (Approved-for-dev + Agent) becomes a ready spec
    outcome_refs: [O2]
  - id: F3
    title: The round-trip handoff - outbound reassignment and artifact links on the ticket
    outcome_refs: [O3]
  - id: F4
    title: Live wiring - a non-LLM mirror runner against real Jira and live epic/child creation
    outcome_refs: [O3, O4]
  - id: F5
    title: Plan from a document - a requirements page kicks off a whole plan of epics and children
    outcome_refs: [O4]
  - id: F6
    title: Release - documentation made true and a version that ships the autonomous loop
    outcome_refs: [O1, O5]

work:
  - item: W1
    spec: WARP-1001
    title: >
      The eligibility model and the Agent user. Extend .veldo/trackers.json with the
      Agent user identity, the ready-for-dev status set, and the repo routing field,
      and add a pure fail-closed is_eligible(ticket, config) resolving the triple
      (Agent + ready status + resolvable repo). Gate-tested with fake tickets, with
      a non-tautology (drop any leg and it refuses).
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-1002
    title: >
      The inbound bridge, draft stage. A non-LLM reconciler that queries the tracker
      for repo-tagged tickets in the pre-approval stage, runs the existing intake to
      produce a spec DRAFT bound to the resolved repo, idempotently, and surfaces the
      drafted spec back onto the ticket for the human to validate (the 2-stage shape,
      gated on D1). Reference live query plus offline fake gate-test.
    feature_refs: [F1]
    depends_on: [WARP-1001]
    order: 20
  - item: W3
    spec: WARP-1003
    title: >
      The promotion gate. When a ticket enters Approved-for-dev and is assigned to
      Agent, the bridge promotes that ticket's spec draft to ready (making it a
      claimable frontier unit); no other transition promotes. Idempotent, and it
      never promotes a draft whose ticket a human reassigned away.
    feature_refs: [F2]
    depends_on: [WARP-1002]
    order: 30
  - item: W4
    spec: WARP-1004
    title: >
      Outbound reassignment and artifact links. Add a set_assignee (assign) write to
      the WARP-0603 adapter seam and structured artifact-link writes (commit, PR,
      proof), and extend the mirror to reassign the ticket away from Agent to the
      configured reviewer and post the links at the ready-to-test transition. Fake
      first with a non-tautology.
    feature_refs: [F3]
    depends_on: [WARP-1001]
    order: 25
  - item: W5
    spec: WARP-1005
    title: >
      The live mirror runner. A non-LLM production runner wiring the events.jsonl
      stream to the live JiraCloud adapter so status, comments, artifact links, and
      the assignee actually apply to a real tracker, idempotently. Opt-in, off by
      default, inspectable and removable (supervisor-style boundary).
    feature_refs: [F4]
    depends_on: [WARP-1004]
    order: 40
  - item: W6
    spec: WARP-1006
    title: >
      Live epic and child creation. Fill JiraCloudAdapter._create_or_update_epic and
      _create_or_update_child (today they raise "wired in a later increment") so the
      epic mirror projects a plan onto a real Jira epic and child issues, with the
      transitions and assignment reused from W4.
    feature_refs: [F4]
    depends_on: [WARP-1004]
    order: 35
  - item: W7
    spec: WARP-1007
    title: >
      Plan from a requirements document. Add draft_plan_from_requirements so a
      Confluence requirements page referenced by a kickoff ticket produces a VELDO
      PLAN (not just a spec); the live epic mirror (W6) then creates the epic and
      one child per work item, each an approvable spec. Fail closed on an
      unresolvable routing signal.
    feature_refs: [F5]
    depends_on: [WARP-1006]
    order: 50
  - item: W8
    spec: WARP-1008
    title: >
      Release. Make the docs true for the autonomous loop (the tracker operator
      guide and the capability manifest gain the Agent model, the eligibility
      triple, the promote gate, the reassignment/links round-trip, and the two
      opt-in services), bump the plugin version, and mark the plan released once the
      regression is green.
    feature_refs: [F6]
    depends_on: [WARP-1002, WARP-1003, WARP-1004, WARP-1005, WARP-1006, WARP-1007]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: >
        An Agent-assigned, Approved-for-dev, repo-tagged ticket flows to a ready
        spec (after the human promote), a worker builds and lands it, and the ticket
        ends shipped with artifact links and reassigned to the reviewer.
      activation: {when: after:WARP-1005}
      suite: end-to-end tracker-fleet conformance (fake tracker offline)
    - id: RJ2
      title: >
        A ticket assigned to a human, or in a non-ready status, or with an
        unresolvable repo tag, is NEVER picked up or promoted.
      activation: {when: after:WARP-1001}
      suite: eligibility selftest
    - id: RJ3
      title: >
        A kickoff ticket referencing a requirements page produces a plan and, on the
        tracker, one epic keyed to the plan plus one child per work item.
      activation: {when: after:WARP-1007}
      suite: doc-to-plan-to-epic conformance (fake tracker)
    - id: RJ4
      title: >
        Idempotency end to end: re-polling the same tickets and replaying the event
        stream creates no duplicate draft, epic, child, comment, or transition and
        leaves state byte-identical.
      activation: {when: after:WARP-1002}
      suite: reconciler idempotency selftest
    - id: RJ5
      title: >
        The existing VELDO gate stays green across every item (selftest, contracts,
        drift, docs), and the repository stays the source of truth (the mirror never
        writes a spec or plan definition).
      activation: {when: start}
      suite: scripts/verify.sh

release:
  milestone: >
    VELDO tracker-driven autonomous fleet v1 - Jira is the queue, work is assigned to
    the Agent user, a human validates each spec in Jira, and the fleet builds and
    mirrors status, links, and the handoff back, with the inbound bridge and the
    live mirror runner as opt-in non-LLM services.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    Disable the two services (they are off by default) and git revert the version
    bump; the seams return to their prior fail-loud reference state and the fleet
    keeps running from the in-repo frontier as before.
  observation:
    duration: >
      Run one repo against a real Jira project with the Agent user for a working
      period, confirming eligible tickets flow in, the human gate holds, and the
      round-trip lands on the ticket, before the services are recommended on.

open_decisions:
  - id: D2
    text: >
      Trigger mechanism for the two services: poll-reconcile on an interval (the
      default, works everywhere) versus a webhook when the instance offers one (lower
      latency, more setup). Poll-reconcile is assumed unless chosen otherwise; does
      not block the logic, only the deployment shape.
    blocks: []

resolved_decisions:
  - id: D1
    text: >
      Spec validation depth: 2-stage versus 1-stage.
    resolution: >
      2-STAGE. The bridge drafts the spec and posts it onto the ticket, and the human
      approves the ACTUAL spec by moving the ticket to Approved-for-dev and assigning
      it to Agent. Founder-confirmed 2026-07-20.
    resolved_at: 2026-07-20
---

## Intent

VELDO today is repository-driven: fleet workers pull ready specs from the in-repo
frontier, and the tracker integration (PLAN-0006) is a side channel - intake is a
manual, agent-run conversion of a ticket into a draft spec, and the mirror is a
one-way status echo proven only offline. This plan makes JIRA the front of the
work queue for teams that live there, without giving up any VELDO guarantee.

The loop a human sees: tag a ticket to a repo, and when it is genuinely ready move
it to Approved-for-dev and assign it to the Agent user. VELDO drafts the spec, the
human validates it (in Jira), and from there it is autonomous - a fleet worker for
that repo claims it, builds it through the full VELDO loop, and mirrors the ticket
forward: status, artifact links, and a reassignment to the reviewer at the
ready-to-test handoff. A requirements document referenced by a kickoff ticket
starts an entire plan, projected onto a Jira epic and its children.

The shift is where the queue lives, not how the work is done. The fleet, the claim
ledger, the executor, the review, the proof, and the one-way mirror all stay as
they are. What is new is the connective tissue: an inbound bridge that turns
eligible, human-validated tickets into claimable specs; the outbound writes the
handoff needs (reassign and links); the live wiring that makes the mirror and the
epic/child creation act on a real tracker; and a document-to-plan generator. Two
new pieces run unattended - the inbound bridge and the live mirror runner - and
both are non-LLM, token-authed, and opt-in, exactly why keeping tokens (not MCP)
was the right call for the tracker edge.

## Ordered delivery rationale

W1 is the root: the eligibility triple and the Agent user model that every later
item reads. W2 (the inbound draft) and W4 (the outbound reassign and links) are the
two independent edges and can proceed in parallel once W1 exists. W3 (the promote
gate) depends on W2 because it promotes what W2 drafted. W5 (the live mirror runner)
depends on W4 because it runs the reassign and links live. W6 (live epic/child)
also depends on W4 for the shared transition and assignment primitives, and W7 (the
document-to-plan generator) depends on W6 because a plan is only useful once its
structure can reach a real tracker. W8 releases once the work is shipped and the
regression is green. D1 shapes W2 and W3 and is the one decision the founder still
owes; everything else proceeds around it.

## Out of scope

Auto-approval or any machine self-promotion (NG1); an LLM in the unattended path
(NG2); a hosted scheduler, queue, database, or bus (NG3); detached or headless
workers (NG4); VELDO as the tracker's source of truth (NG5). Live enablement against
the real Bcengi Jira is an operational, human-approved step, not part of the build.

## Revisions

Revision 1 (2026-07-20): drafted from the founder's stated target workflow (workers
per login develop any repo; auto-pickup of repo-tagged tickets that are
Approved-for-dev and assigned to the Agent user; a human validates the spec in Jira;
the worker updates the ticket and reassigns at ready-to-test; a requirements
document kicks off a whole plan) and the settled design decisions (the Agent user
model, the Jira-native promote gate, keep-tokens non-LLM unattended services, and
the repository as the single source of truth). Open decision D1 (2-stage versus
1-stage spec validation) is recorded, blocking only W2 and W3, so the rest is
reviewable now. Awaiting founder approval to leave draft.
