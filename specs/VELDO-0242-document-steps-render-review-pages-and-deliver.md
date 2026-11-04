---
schema: veldo.spec/v1
id: VELDO-0242
title: Document step types, render pages to PNG and PDF with the project's own command, review the rendered pages, deliver the approved files to the owner, and a default document definition
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0058, VELDO-0132, VELDO-0174, VELDO-0177, VELDO-0241]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_step_document*.py"
  - ".veldo/control_step_document*.py"
  - "engine/.veldo/workflows/document.json"
  - ".veldo/workflows/document.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0242_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0242-document-steps-render-review-pages-and-deliver.md"
  - "specs/index.md"
  - "proof/VELDO-0242/*"
behavior_bearing: true
observability:
  logs: >
    A render records the unit, the commit, the project's named render command, its exit status, and each
    page's PNG digest and the PDF digest; a page review records every page digest it read; a delivery
    records the file digests, the channel, the approval it ran under and the channel's receipt.
  metrics: >
    Count renders, page reviews and deliveries by outcome, pages per render and render duration.
  traces: >
    Join each delivery to its approval, the page review and the render of the same commit.
  error_taxonomy: >
    Keep VELDO-0132's names. A project with no render command is unsupported_configuration:render_command;
    a render that exits non-zero or produces no pages is missing_evidence:render; a review that does not
    name every page is missing_evidence:page_review; rendered pages of another commit are
    stale_version:render; a deliver node with no installed file delivery is
    unsupported_configuration:file_delivery at save; files that differ from the approved digests are stale_subject:deliver.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the render step runs the project's own named render command on the unit's exact commit and
      records a PNG per page and a PDF, by digest. Set: the command is named in the project's work
      configuration, never in the definition (definitions carry no shell); it runs in the unit's isolated
      clone under the gate's isolation (VELDO-0058); output outside the declared output directory is
      ignored; a non-zero exit or zero pages stops the unit with the named refusal. Rows on a fixture deck
      repository with a three-page render command, a failing one and an empty one.
    falsified_by: >
      Record pages rendered from the previous commit after a new build; the commit-binding row must fail.
  - id: AC2
    text: >
      Claim: the page review reads the rendered pages, not the sources. Set: the review role receives the
      PNG pages and the PDF of the recorded render as its input; its result must name every page digest
      with a verdict, and a result missing a page, naming an unknown digest or bound to another render is
      refused with no review recorded.
    falsified_by: >
      Accept a review that names two of the three page digests; the every-page row must fail.
  - id: AC3
    text: >
      Claim: deliver sends exactly the approved files to the owner through the conversation channel, only
      after his approval, and the default `document` definition (build, render, review pages, gate, owner
      approval naming land and deliver, land, deliver) saves and runs end to end. Set: deliver is an outward
      kind under VELDO-0241 AC2; it uses the conversation channel's file delivery (VELDO-0238 when that spec
      lands with this number); a definition with a deliver node is refused at save while no file delivery is
      installed; the delivered digests equal the approved ones and the channel's receipt is recorded.
    falsified_by: >
      Deliver the PDF of a render made after the approval; the approved-digest row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change; the three step kinds are unregistered, saved revisions that use them are refused at
  the next binding and the `document` definition stays in the store unused. No automatic rollback, retry or
  recovery is authorized.
---

## Intent

Decks, models, plans and documents run through the factory as their own process: built from source,
rendered to the pages a person sees, reviewed as pages, gated, approved by the owner and landed, and the
approved files handed to him in the conversation.

## Context

Parity ticket T7 (research/veldo-parity-2026-11-04.md, the owner's assistant repository), now a set of step
types under VELDO-0241 instead of a fixed document pipeline. Owner, Telegram 39067: Veldo runs non-software
projects (PLAN-0019 NG3 amended 2026-11-04); 39069 to 39071: the process is a workflow per kind of work.
File delivery to the owner is writer A's ticket T5, numbered VELDO-0238 on branch
agent/claude/veldo-parity-a; that branch did not exist when this draft was written, so the number is
checked again before ready.

## Out of scope

Files the owner sends in (T5). How a project's render command works inside (LibreOffice, a headless
browser, openpyxl: the project's own concern). Publishing a document anywhere but to the owner (VELDO-0244).

## What the reviewer judges

- Normal use: a deck repository bound to `document` gets a build, a render of the build's exact commit, a
  page review that names every page, the gate, one owner approval for land and deliver, the land and the
  delivery of the approved PDF and pages.
- Threat model: a render of a different commit passed to review or delivery; a review that skipped pages;
  a delivery of files changed after approval; a shell command smuggled into a definition.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); render
  determinism across hosts.

## Notes

Render output is evidence of the unit, kept as the gate keeps its observations. The page review is an
ordinary review station with a different input, so the independent-reviewer rule holds unchanged.

## History

2026-11-04: new draft under owner Telegram 39067 (non-software projects, NG3) and 39069 to 39071 (process
as workflow). Supersedes the fixed document-project design of parity ticket T7. Standalone.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.
