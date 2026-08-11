---
schema: veldo.spec/v1
id: WARP-0604
title: Jira intake - a ticket becomes a routing-resolved VELDO spec draft through the existing pipeline
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W4
plan_revision: 1
depends_on: [WARP-0602, WARP-0603]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: Intake reads a ticket THROUGH the WARP-0603 seam (vendor-neutral read_item) and produces a
      veldo.spec/v1 DRAFT bound to the repository the ticket targets, capturing the report as the AC1
      reproduction observable (a bug's first acceptance criterion is its reproduction, attached as a
      failing test by the intake skill) and a no-regression ACn, with the source ticket linked in an
      intake_source field. It feeds the existing intake procedure (packs/claude/skills/intake), not a new
      pipeline, and treats ticket content as untrusted input, never as instructions.
  - id: AC2
    text: The ticket's target repo is resolved with the REUSED WARP-0601 resolver (resolve_repo, no
      second config parser), and a ticket with no routing signal, an unknown repo, or an ambiguous
      one is REFUSED by name (IntakeError) - never guessed and never drafted to a default repo. A
      misrouted spec is worse than a refused one.
  - id: AC3
    text: The risky Jira field mapping is PURE and gate-tested - _jira_issue_to_item maps a Jira Cloud
      REST issue onto the vendor-neutral item shape (key to id, summary to title, an Atlassian
      Document Format or plain description flattened to text, labels and component names and custom
      fields preserved so the resolver can route in any configured mechanism), proven over a fixture
      issue with no live Jira.
  - id: AC4
    text: The live Jira Cloud REST adapter is REFERENCE-WIRED, not mechanical - JiraCloudAdapter
      implements the WARP-0603 seam against Jira Cloud REST v3 via stdlib urllib, resolving its token
      from a secrets reference (token_ref) and never embedding a raw credential in a file, prompt,
      proof, or log (C4); it needs a live Jira so it is NOT run in the gate, and the capability
      manifest is honest about this (the intake logic and mapping are mechanical and gate-tested; the
      live adapter is reference). The fake-tracker path is what runs in the gate (C5).
  - id: AC5
    text: A selftest drives intake over the deterministic FakeTracker and a fixture Jira issue offline
      (no network) - a routing-resolved ticket produces a draft bound to the right repo with the
      reproduction as AC1 and the ticket linked, a ticket with no routing signal is refused by name,
      the pure Jira mapping reads key/summary/labels/components and flattens the ADF description, and a
      rendered draft carries the resolved repo - and it is non-tautological (an unroutable ticket is
      refused, a routed one drafts; removing the routing signal flips a draft into a refusal).
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/tracker_intake.py, two capability entries (one mechanical
  for the intake logic, one reference for the Jira adapter; both capabilities.yaml copies), a selftest
  block, and this spec; no protected path; pure stdlib, the live adapter reference-wired (not gate-run).
---

## Intent

O2 wants a person who never opens a repository to file a report in their own tool and have it become
a routing-resolved VELDO spec draft, with nobody hand-writing a spec file. This is the inbound edge:
read a Jira ticket, resolve which repo it targets, and draft the spec there with the report captured
as its reproduction and the ticket linked. Routing is first-class because one Jira project spans many
VELDO repos - a ticket that cannot be routed to exactly one repo is refused, not guessed.

## Context

W4 of PLAN-0006, on the frontier once routing (W2) and the seam (W3) exist. It reuses the WARP-0601
resolver (which repo) and the WARP-0603 seam (how a tracker is read), and it feeds the existing
intake skill (the procedure that reproduces the report as a failing test and asks the owner one
question) rather than adding a new pipeline (C3). Jira Cloud REST is the first adapter behind the
seam; Data Center is a later adapter behind the same seam (C6, Cloud first).

## Notes

The network is kept at arm's length so the substance is gate-tested offline. The intake LOGIC
(resolve + draft + refuse) and the risky Jira field MAPPING (_jira_issue_to_item, including the
Atlassian Document Format description flattening) are pure and unit-tested over the FakeTracker and a
fixture issue. Only the actual HTTP - JiraCloudAdapter's urllib calls to Jira Cloud REST v3 - is
reference-wired: it needs a live Jira and a scoped token (resolved from a secrets reference, never a
raw credential per C4), so it is not run in the gate. This is the same honesty as the reference
mobile and web runners: the live driver is reference, the control logic and mapping are tested.

The draft is a veldo.spec/v1 DRAFT (status draft): the intake skill completes it (reproduce as a
failing test, ask the owner one product question, mark ready). The reproduction is AC1 and a
no-regression criterion is ACn, per the intake procedure. The source ticket is linked in an
intake_source field so the closing comment can be posted back on ship (the mirror, WARP-0605). A
ticket touching security or personal data routes straight to a human (the intake exception, NG4);
that judgment lives in the skill, not in this mechanical spine.
