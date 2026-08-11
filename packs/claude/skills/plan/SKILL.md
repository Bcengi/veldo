---
description: Define and steward a Veldo Product Plan - the holistic layer above specs. Create, refine, approve, pull work into specs, revise with impact analysis, check status, and release.
---

Operate on a Product Plan: $ARGUMENTS

A Product Plan (`plans/PLAN-NNNN-*.md`, contract `veldo.plan/v1`) is how a
product iteration stops being a random stream of specs: outcomes first, then
a feature tree, then an ordered, dependency-declared work DAG, planned
regression, and a release definition. Specs are pulled FROM it in deliberate
order. Use the sub-verb the human asked for; if none, infer from context.

## create
Interview at the PRODUCT level, not the spec level: what user outcomes must
become true, what the feature breakdown is, what is explicitly out, what
must stay green across the whole iteration (regression), and what "done"
means (the release). Draft from `plans/TEMPLATE.md`. Give every work item a
small, independently provable scope and an honest `depends_on` (use `[]`,
never omit it). Leave `status: draft`. Then `python3 .veldo/validate.py plan
<file>` must pass.

## refine
Edit an existing draft plan with the human: split or merge work items,
correct dependencies, sharpen outcomes. Re-validate. A plan in `draft` may
change freely; once past draft, use `revise`.

## approve
A plan leaves `draft` only by a recorded human decision. Set `status:
ready`, `approved_by`, and `approved_at`. Re-validate. This is the gate that
makes the ordering real; do not set it on the human's behalf without their
word.

## pull
Turn the next ready work item into a spec. Read the frontier
(`python3 .veldo/plan.py status <plan>`), pick a work item whose
`depends_on` are all shipped, and create its spec with `/veldo:spec`,
setting `lane: planned`, `plan: <PLAN-id>`, `work: <Wn>` so the two-way
mirroring holds. Do not pull a work item whose dependencies are unshipped;
once W3 lands, the run skill will refuse it at run time as well.

When the plan is routed to an external tracker (one tracker project spanning
many repos), set the optional `tracker_repo` field on the plan (and on each
pulled spec) to the repo the resolver (.veldo/tracker.py) returns, so the work
names exactly one resolvable target repo. Omit it for the single-repo default;
validate.py fails closed if it names a repo the tracker config does not know.

## revise
A change to an approved plan (new work, changed dependencies, dropped scope)
is a revision, not an edit: bump `revision`, add a `## Revisions` note, and
run impact analysis for anything already shipped:
`python3 .veldo/plan.py impact <plan> <SPEC>` lists downstream dependents and
warns which shipped specs may need re-proof. Record what the revision
invalidates.

## status
`python3 .veldo/plan.py status <plan>` prints the burn-down: each work item's
state (shipped / waiting on named deps / blocked by a decision / frontier)
and the ready frontier. This is generated from spec files, never
hand-updated. The specs index carries the same section for all plans.

## regression
`python3 .veldo/plan.py regression <plan> per_spec:<SPEC>` lists the
regression journeys active while building SPEC; `... release` lists those
active at the release gate (manual-trigger journeys are surfaced separately,
never auto-run). Journeys declare `activation` (start | after:<spec> |
manual), an optional `owner_spec`, and `profiles` (per_spec, release). A
repo wires its gate `journeys` slot to run exactly the active per-spec
suite, so regression is designed up front in the plan, not accumulated by
accident. For a repo with no user interface, the active suite is whatever
its journeys resolve to (often the unit suite), and the slot stays na.

## release
`python3 .veldo/plan.py release-check <plan>` verifies the release
conditions the plan declares: all work shipped (if required), regression
journeys present (if required), no open decision still blocking, a milestone
named. Only when it reports releasable do you set the plan `status: released`
and record the release. For `mode: continuous` the work already merged as it
went green; release is the milestone marker plus the observation window. For
`mode: coordinated`, cut the release together once the check passes.

## The two lanes (and promotion)
Not all work needs a plan. A bug or an isolated change is a `lane: standalone`
spec with no `plan`/`work` - the direct path stays open ("if there is a bug,
sure"). Reserve plans for product iterations: several features, many specs,
shared regression. If a standalone spec turns out to belong to an iteration,
PROMOTE it: add it to the plan's `work` list (with its `depends_on`), then
set `lane: planned`, `plan:`, and `work:` on the spec. Validation enforces
that a promoted spec and its plan agree in both directions; a half-promoted
spec (claims planned but the plan has no matching work item, or vice versa)
fails the gate.
