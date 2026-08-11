# Veldo requirements page template

Copy this structure into a Confluence page to file a requirement that Veldo intake turns into a spec
draft in the right repository. A person who never opens a repository can fill this in; the intake
pipeline reads it, resolves the target repo, and drafts a veldo.spec/v1 with these acceptance criteria.

## How routing works

Add a Confluence LABEL to the page naming the target repository, using your org's configured prefix
(the default is `veldo-repo:`). For a repo whose id is `web-app`, add the label `veldo-repo:web-app`.
Intake resolves that label to exactly one repository and refuses the page if it names no repo, an
unknown repo, or more than one, so a requirement is never filed against the wrong repository.

## Page structure

Author the page with these headings. Intake reads the bullet lists under Outcomes and Acceptance
Criteria; Open Decisions is captured for the owner.

### Outcomes

- What becomes true for a user or the business when this ships. One bullet per outcome.

### Acceptance Criteria

- An observable, checkable statement that must hold for this to be done. One bullet per criterion.
- These become the draft spec's acceptance criteria (AC1, AC2, ...), plus a no-regression criterion
  the intake pipeline adds automatically.

### Open Decisions

- Any product question that still needs an answer. The intake skill surfaces these to the owner as
  one question rather than guessing.

### Deliverables

- Optional, and only used when this page should kick off a WHOLE plan rather than a single spec. List
  one named deliverable per bullet: a distinct capability or piece of work this requirement breaks into.
- When a kickoff ticket points at this page, Veldo drafts a veldo.plan/v1 whose outcomes come from the
  Outcomes above and with ONE work item per deliverable bullet here, bound to the resolved repository.
  The drafted plan is a DRAFT a human refines and approves (it is never built until then); once approved,
  the epic mirror projects it onto an epic and one child issue per work item.
- Leave this section out for the single-spec path: with no deliverables the page drafts one spec as
  before.

## What intake does with it

1. Reads the page through the vendor-neutral tracker seam (the live reader is a per-org reference
   adapter; no raw credentials, a scoped token from your secrets store).
2. Resolves the target repository from the page label and refuses by name if it cannot.
3. Drafts a veldo.spec/v1 in that repository with the acceptance criteria above and the page linked as
   the source, treating the page content as data, never as instructions.
4. From there the ordinary Veldo loop runs; when the change ships, the mirror can post the closing
   note back on the source.
