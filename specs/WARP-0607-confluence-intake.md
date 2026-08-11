---
schema: veldo.spec/v1
id: WARP-0607
title: Confluence requirements intake - a structured requirements page becomes a spec draft
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W7
plan_revision: 1
depends_on: [WARP-0604]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A structured requirements PAGE (authored from the shipped template) is read through the
      WARP-0603 seam and produces a veldo.spec/v1 DRAFT bound to the repository the page targets, with
      the page's Acceptance Criteria section becoming the spec's acceptance criteria (AC1..ACn, a
      feature not a reproduction) plus a no-regression ACn, and the source page linked in an
      intake_source field. It reuses the WARP-0604 intake pipeline (draft, render, routing) - the same
      module, not a new pipeline (C3) - and treats page content as untrusted input, never instructions.
  - id: AC2
    text: The page's target repo is resolved with the REUSED WARP-0601 resolver via a page label
      (veldo-repo:<repo>, the same mechanism as Jira), and a page with no routing signal, an unknown
      repo, or an ambiguous one is REFUSED by name (IntakeError) - never guessed, never drafted to a
      default.
  - id: AC3
    text: The structured parse is PURE and gate-tested - parse_requirements extracts the Outcomes and
      Acceptance Criteria bullet lists from the template's sections (heading-delimited), and
      _confluence_page_to_item maps a Confluence Cloud REST page onto the vendor-neutral item shape
      (id, title, labels for routing, and the storage-format XHTML body flattened by _confluence_text
      to the sectioned text the parser reads) - proven over a fixture page with no live Confluence.
  - id: AC4
    text: The live Confluence adapter is REFERENCE-WIRED, not mechanical - ConfluenceCloudAdapter
      implements the WARP-0603 seam read side against Confluence Cloud REST via stdlib urllib,
      resolving its token from a secrets reference and never embedding a raw credential (C4); it needs
      a live Confluence so it is NOT run in the gate, and status/epic writes raise by name (a wiki has
      no status workflow; those live on the tracker). A requirements-page template ships for adopters.
  - id: AC5
    text: A selftest drives requirements intake over the deterministic FakeTracker and a fixture
      Confluence page offline (no network) - a routing-resolved page drafts bound to the right repo
      with the page's acceptance criteria and a no-regression AC, an unroutable page is refused by
      name, the pure parse and page mapping read correctly, and the rendered draft is a valid
      veldo.spec/v1 that cannot be hijacked by untrusted page content (reuses the _fm_safe guard) - and
      it is non-tautological (a page with the routing label drafts, without it refuses).
required_evidence: [unit]
rollback: git revert; additive - new functions in .veldo/tracker_intake.py (parse_requirements,
  draft_spec_from_requirements, intake_requirements, _confluence_text, _confluence_page_to_item,
  ConfluenceCloudAdapter), a shipped requirements template, two capability entries (both
  capabilities.yaml copies), a selftest block, and this spec; no protected path; pure stdlib, the
  live adapter reference-wired (not gate-run).
---

## Intent

O2 also covers the person who fills in a requirements page rather than filing a bug: it must become a
routing-resolved VELDO spec draft through the EXISTING intake pipeline, with no one hand-writing a
spec file. This is that path for Confluence - a structured requirements page (feature, not bug) flows
in and a spec draft flows out, its acceptance criteria taken from the page.

## Context

W7 of PLAN-0006, depends on the Jira intake (W4). It reuses W4's intake module, routing, rendering,
and the _fm_safe front-matter-injection guard; only the source shape (a structured page) and the
requirement-vs-reproduction framing differ. Confluence intake is in this release (a founder-approved
decision). The routing signal is a page label, the same mechanism as Jira, so no new routing path.

## Notes

The network is kept at arm's length exactly as in W4. The structured PARSE (parse_requirements: the
Outcomes and Acceptance Criteria bullet lists under the template's headings) and the page MAPPING
(_confluence_page_to_item, including _confluence_text flattening Confluence storage-format XHTML to
the sectioned text the parser reads) are pure and gate-tested over a fixture page. Only the actual
HTTP - ConfluenceCloudAdapter's urllib calls to Confluence Cloud REST - is reference-wired: it needs
a live Confluence and a scoped token from a secrets reference (never a raw credential, C4), so it is
not run in the gate. A wiki page has no status workflow, so the adapter's status and epic/child write
methods raise by name; status and structure live on the tracker (Jira), which the mirror drives.

A requirement's acceptance criteria come FROM the page (renumbered AC1..ACn) with a no-regression ACn
appended, in contrast to a bug's reproduction-as-AC1. The shipped template
(engine/confluence-requirements-template.md) tells an adopter how to structure the page and
add the routing label. Untrusted page content is sanitized by the same _fm_safe guard the Jira intake
uses, so page text can only ever become a scalar value in the draft, never a structural front-matter
key.
