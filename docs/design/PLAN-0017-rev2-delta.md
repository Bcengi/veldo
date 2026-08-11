# PLAN-0017 revision 2 delta - the public work surface

Reason: Dmitry, 2026-07-24, after approving revision 1 in VEL-5. "the switch plan that includes open
sourcing - I didn't realize but we probably should also switch to github's project management too, since I
will not let anybody see the jira - open source project needs to see it's own tasks/work."

An open-source project whose issues live in a private tracker nobody can read is a code drop, not a
project. Revision 1 shipped the repository, the site and the book but left the project's own work
invisible. This revision adds the public work surface.

STATUS HANDLING: revision 1 was approved in VEL-5. This is a MATERIAL change (a new outcome, a new
constraint, a new work item), so the file goes to `status: draft`, `revision: 2`, and it returns to Dmitry
for approval as its own Decision on the board. Do NOT carry revision 1's approval forward onto changed
content.

---

## EDIT 1 - front matter

Replace:
```
status: ready
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-24
```
with:
```
status: draft
revision: 2
owner: dmitry
```
(the approval fields come back when he approves revision 2; revision 1's approval does not transfer to
changed content)

## EDIT 2 - a new outcome, inserted after O4 (the public repository outcome)

```yaml
  - id: O7
    becomes_true: >
      THE PROJECT'S OWN WORK IS VISIBLE WHERE THE CODE IS. The public project's plans, specifications and
      human decisions are readable and participable on the public forge itself, not in a private tracker
      only the founder can open. A contributor who finds the repository can see what is planned, what is
      being built, what was decided and why, and can weigh in, without being granted access to anything
      private. The tracker is a SEAM the method already declares, so this is a second adapter behind the
      existing contract rather than a migration: the private tracker keeps serving private work and both
      run at once.
    measure: >
      From the public repository alone, a stranger can read the plan set, the specification index and the
      settled decisions with their rationale; a decision raised on the public surface projects a readable
      brief with its RISK section; and the repository-side reconcile derives the actor from the public
      forge's own attributed history exactly as it does from the private tracker's, proven by the same
      conformance suite run against both adapters.
```

## EDIT 3 - a new constraint, appended to constraints

```yaml
  - id: C8
    text: >
      THE FENCE DOES NOT PORT, AND THAT IS STATED RATHER THAN GLOSSED. On the private tracker the three
      terminal transitions are restricted to an approver group, so the agent structurally cannot fire them.
      The public forge has no per-transition group condition: anyone with write access can close an issue or
      set a label. The PRIMARY control survives unchanged, because the repository is authoritative and the
      reconcile validates the actor against the approver set from attributed history, refusing otherwise;
      what is lost is the per-transition granularity. THE LAYER IS RESTORED ON A FORGE-NATIVE PRIMITIVE,
      decided by the owner 2026-07-25: the agent keeps issue write so the projection and the doorbell still
      work, the agent is READ-ONLY on pull requests, the decision-record file is gated by CODEOWNERS, and a
      human's PR REVIEW APPROVAL is the terminal act on a resource the agent structurally cannot touch.
      Setting the agent to issue read-only was REJECTED because it would also stop it creating and
      commenting on the decision issue, which is the whole outbound side. This makes the plan's core
      principle literal on the public surface: the decision settles as a REVIEWED COMMIT rather than an
      issue state. No claim that the public surface has the same PER-TRANSITION fencing as the private one
      may appear in any document, and no document may present the permission split as a substitute for the
      repository-side actor verification.
```

## EDIT 4 - a new feature-tree entry

```yaml
  - id: F7
    title: The public work surface, the project's own tasks and decisions visible where the code is
    outcome_refs: [O7]
```

## EDIT 5 - a new work item, placed BEFORE the release item so the release makes it true

Insert as W9 with `order: 75`, and renumber the existing release item W9 (WARP-1709) to W10 with
`order: 80`, updating its `depends_on` to include the new spec.

```yaml
  - item: W9
    spec: WARP-1710
    title: >
      The public work surface. A second tracker adapter behind the existing seam, for the public forge's
      issues and projects, plus the projection that publishes the plan set, the specification index and the
      settled decisions with their rationale so a stranger can read what is planned, what is being built and
      what was decided. The inbound reconcile derives the actor from the forge's own attributed history and
      validates against the approver set exactly as it does for the private tracker, and the SAME conformance
      suite runs against both adapters so neither can drift into a weaker guarantee. Builds the C8 control
      model as decided: agent write on issues, agent READ-ONLY on pull requests, the decision-record file
      CODEOWNERS-gated, and a human PR review approval as the terminal act, with a negative test proving the
      agent's own credential CANNOT settle a decision (the forge equivalent of the live fence proof). No
      private artifact and no private decision is ever projected to the public surface, proven by the
      publication pipeline's own leak scan extended to cover the projection. HARD DEPENDENCY: WARP-0624 must
      ship first, because on this surface the repository-side actor verification is the primary control and
      the live proof showed it inert against the real agent identity.
    feature_refs: [F7]
    depends_on: [WARP-1706, WARP-0624]
    order: 75
```

## EDIT 6 - the release milestone

Add to the `release.milestone` text, after the repository clause: "and the project's own plans,
specifications and decisions are readable and participable on the public forge, with the same conformance
suite passing against both tracker adapters".

## EDIT 7 - a regression journey

```yaml
    - id: RJ6
      title: >
        The tracker conformance suite passes against BOTH adapters, and the public projection carries no
        private artifact: a seeded private plan, specification and decision are provably absent from the
        public surface.
      activation: {when: after:WARP-1710}
      suite: dual-adapter tracker conformance plus projection leak scan
```

---

## C8 - DECIDED 2026-07-25 (the routes are kept below for the record)

Three routes for the lost fence layer, my recommendation first:

1. REPO-SIDE ONLY, documented honestly. The reconcile already refuses an actor outside the approver set,
   and that is the control that matters. Cheapest, and the honesty has value in an open-source project
   whose subject is exactly this kind of rigour.
2. FORGE ENVIRONMENTS WITH REQUIRED REVIEWERS. The one forge primitive that genuinely enforces an approver
   set, and the one CI already trusts. Built for deployments, so using it for decisions is a stretch.
3. A REQUIRED STATUS CHECK PLUS CODEOWNERS ON THE DECISION RECORD. Most forge-native, and it makes the
   repository-authoritative principle literal: a decision settles through a reviewed commit rather than an
   issue transition.

DECIDED BY DMITRY 2026-07-25: ROUTE 3, the PR review approval with CODEOWNERS. His words: "I agree with
recommendation." So C8 is no longer an open decision; it is a recorded choice and W9's spec must build it.

WHAT THAT MEANS CONCRETELY, and why the naive version was rejected: GitHub permissions ARE the right
mechanism and are enforced per resource server-side, which is stronger than a policy. But GitHub has NO
per-transition granularity, unlike the Jira fence which restricts exactly three terminal transitions while
the agent keeps write on everything else (proven live: the agent moved a ticket to Needs Decision and was
refused only on Approved, Decided and Rejected). Setting the agent to Issues read-only would therefore also
stop it creating the decision issue and commenting on it, which is the entire outbound projection and
doorbell. So the terminal signal MOVES OFF the resource the agent must write:

- the agent keeps Issues: Write, so the projection and the doorbell still work
- the agent is READ-ONLY on Pull requests
- the decision-record file is gated by CODEOWNERS
- a human's PR REVIEW APPROVAL is the terminal act, on a resource the agent structurally cannot touch

This also makes the plan's core principle literal rather than metaphorical: the decision settles as a
REVIEWED COMMIT in the repository, not as an issue state, so "the repository is authoritative and the
tracker action is only a submitted assertion" stops needing a translation layer on the public surface.

STILL REQUIRED, and this is not softened by the above: WARP-0624 must land first. The permission split is
the FENCE; the repository-side actor verification is the control the design calls PRIMARY, and the live
proof showed that control is inert against the real agent identity. On GitHub the timeline carries
actor.type (Bot versus User) and performed_via_github_app, which is exactly the structural machine-ness
signal 0624 teaches the guard to consume instead of guessing from a display name. It is also the layer that
catches a token misconfiguration, which is the failure mode a permission-only design cannot see.

SUPERSEDED RECOMMENDATION (kept for the record): dual surface, not a switch (the seam supports both at once, so this costs one adapter), and
route 1 now with route 3 declared as the target. Route 2 only if he wants the enforcement layer before the
project has contributors.
