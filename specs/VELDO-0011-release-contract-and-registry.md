---
schema: veldo.spec/v1
id: VELDO-0011
title: The release contract and its registry - a release is a typed, ordered group of plans with the
  plan as its floor, no two artifacts in either registry share an id, and a member is bound by the
  bytes of its file rather than by its front matter
status: draft
risk: standard - it adds one new artifact contract, one new registry, and one refusal to the plan
  corpus check, and it changes what the gate accepts rather than what any product does. It is NOT low
  because both halves are adoption-affecting in the strongest way a contract change can be: the
  duplicate-id refusal is evaluated against every plan file in every adopting repository, so a
  repository that already carries a duplicate reddens on the day this lands, and the plan registry it
  touches is read by eight callers that must not start raising. And it is not high because nothing it
  touches runs in production, no gate stage consumes the release report, a repository that declares no
  release is unaffected, and the whole change is reversible by deleting two check registrations
owner: dmitry
human_approval: required
lane: standalone
placement: [contracts, enforcement]
footprint:
  - ".veldo/releases.py"
  - "engine/.veldo/releases.py"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/architecture.yaml"
  - "releases/TEMPLATE.md"
  - "engine/releases/TEMPLATE.md"
  - "scripts/suites/18_veldo_0011_release_contract.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0011-release-contract-and-registry.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    Every refusal names the artifact file, the member id where a member is at fault, and the cause, in
    the voice the plan validator already refuses in, so an author reads one line and knows which
    member to fix. A stand-down prints one line naming WHICH condition stood the check down (no
    releases directory at all, or a releases directory holding only the template), because a
    stand-down that looks like a pass is how an unadopted check gets mistaken for a green one. The
    legacy-kind notice names the count and the files it counted, never a bare number.
  metrics: >
    The resolved report carries its own coverage beside every figure a reader might quote: releases,
    members, members_by_kind, members_resolved, members_unelaborated (a declared member whose target
    file is absent), duplicate_ids per registry, and digest_coverage as resolved members over declared
    members. A figure with no basis is not printed: an unresolved member carries digest None rather
    than an empty string, exactly as the estimation layer prints None rather than a confident zero.
  error_taxonomy: >
    One refusal surface with named, distinguishable causes, all read from ONE problem enumeration
    (release_problems) that both the reporting form and the refusing form consume, so the two surfaces
    cannot disagree about what is wrong. The causes are distinct rather than one undifferentiated
    invalid-release line: a missing required field, a bad status, an unapproved status past draft, an
    unknown member kind, a member target whose id shape belongs to another artifact type, a member
    cycle, a member claimed by two releases, a duplicate release id, and a duplicate plan id.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Delete the required-field loop in the new check_release so only the schema string is verified,
      and the fixture assertion that a release declaring no members is refused with members named must
      go red.
    text: >
      ONE ARTIFACT, ONE PARSER, AND EVERY REQUIRED FIELD REFUSED BY NAME. A release is one markdown
      file with front matter, flat in a releases directory, schema veldo.release/v1, id matching
      REL-nnnn, carrying schema, id, title, status, revision, owner, milestone and members; each
      missing field is refused separately and by name. The front matter is read through the ONE parser
      the whole repository reads front matter with (validate.parse_yamlish, .veldo/validate.py:351-368),
      so a release's fields arrive as the same values every other reader sees and this contract adds no
      second YAML reader. status is a closed set, and a status past draft with no approved_by and no
      approved_at is refused in the same words the plan contract already refuses it in
      (.veldo/validate.py:500-503), because a release that groups approved plans cannot itself leave
      draft on nobody's signature. ANTI-VACUITY: the fixture table is driven one bad shape at a time
      and the assertion is bound to the LENGTH of its own table, so a table somebody empties reds
      instead of passing over nothing, and a POSITIVE CONTROL requires the well-formed fixture to be
      accepted with zero errors, so the refusal is discriminating rather than a blanket rejection of
      every release.
  - id: AC2
    falsified_by: >
      Restore the bare assignment at .veldo/validate.py:669 as the only write into the registry,
      dropping the duplicate accumulation, and the assertion that a tree holding two plan files
      declaring PLAN-9999 is refused with both filenames named must go red.
    text: >
      NO TWO ARTIFACTS SHARE AN ID, IN EITHER REGISTRY, THROUGH ONE SPELLING OF THE RULE. This is
      PLAN-0018 finding 24 (plans/PLAN-0018-what-a-complex-project-needs.md:357-361) and it is fixed
      here rather than after, because a release resolves its members through the plan registry and a
      registry that silently drops a member would let a release bind to whichever colliding file
      sorted last. plan_registry at .veldo/validate.py:652-670 writes reg[fm["id"]] once per file with
      no duplicate check, so two plan files declaring one id leave the validator reporting zero errors
      while one file disappears from every derived view. Both registries now detect duplicates through
      ONE function that takes the id-to-paths mapping and names every id declared more than once with
      every file that declared it; a release-side copy of that rule is a defect even while the two
      copies agree, because they will not stay agreed. THE REGISTRY'S RETURN SHAPE AND CONTRACT DO NOT
      MOVE AND IT STILL DOES NOT RAISE: eight callers read it (.veldo/plan.py:49, .veldo/budget.py:288,
      .veldo/toe_budget.py:904, .veldo/runstatus.py:136, .veldo/judgment_load.py:581,
      .veldo/intent_corpus.py:552, scripts/update_index.py:48, and the suites), and a reader that began
      raising would redden the gate far from the defect; the duplicates are exposed as a separate
      accessor and refused through validate.fail at the corpus check. ANTI-VACUITY, AND THE LIVE READ
      IS NEVER PINNED EMPTY: the refusal is proven over a temporary tree carrying a real duplicate, and
      over the live corpus the selftest asserts only that the number of distinct ids read equals the
      number of plan files read, so a repository that legitimately grows a duplicate reds on the
      duplicate and never on the assertion (PLAN-0018 finding 26,
      plans/PLAN-0018-what-a-complex-project-needs.md:367). Measured as READ on 2026-08-11: 18 plan
      files, 18 distinct ids, so landing this reddens nothing here, and that is a reading of the corpus
      rather than a requirement on it.
  - id: AC3
    falsified_by: >
      Drop the member-kind whitelist test in the new member validation so kind is accepted as any
      string, and the assertion that a member declaring kind spec with target VELDO-0011 is refused
      must go red.
    text: >
      THE FLOOR IS A TYPE, THE DEPTH IS NOT CAPPED, AND THE MEMBER GRAPH IS A FOREST. Each member
      declares a kind of release or plan and a target id whose shape matches that kind (REL-nnnn or
      PLAN-nnnn); an unknown kind is refused, and a member whose target is a spec id is refused by
      name, because a spec binds to a plan and never to a release and the plan contract already types
      that id shape (.veldo/validate.py:546-547). THE TYPE RULE IS THE LOAD-BEARING LEG and the reason
      the falsification names it: it is what terminates the recursion, so the two graph rules below
      only terminate because it gives the walk a floor. No constant caps the depth: the selftest
      validates a three-level chain (a release whose member is a release whose member is a release
      whose member is a plan) to prove the absence of a cap rather than asserting a limit, since an
      assertion of a maximum would be the size heuristic this layer exists to avoid. A member cycle is
      refused with the ring named in order, and a plan claimed as a member by two releases is refused
      with both releases named, so single parentage is a refusal rather than a convention. ANTI-VACUITY:
      each graph refusal is paired with a POSITIVE CONTROL fixture that differs from it in one member
      only and must validate, so neither check can be satisfied by refusing every release.
  - id: AC4
    falsified_by: >
      Return plan.plan_hash of the parsed front matter from the new member_digest instead of hashing
      the file bytes, and the assertion that a one-byte edit to a fixture plan's BODY changes the
      member digest while plan_hash over the same two files stays equal must go red.
    text: >
      A MEMBER IS BOUND BY THE BYTES OF ITS FILE, AT FULL WIDTH, AND IT IS NOT plan_hash. This is
      PLAN-0018 finding 25 (plans/PLAN-0018-what-a-complex-project-needs.md:362-365) and it is fixed
      at the bottom of this layer rather than in the receipt that will consume it, because a receipt
      built on a hasher that cannot see a body is a fiction whichever item writes it. VERIFIED IN THE
      CODE: plan_hash at .veldo/plan.py:216-222 hashes the parsed FRONT MATTER, drops approved_at and
      recorded_at, and truncates to 16 hex, so a member plan's entire body can be rewritten after a
      binding is written and the binding still matches, and the hole is exactly the size of a plan
      body. member_digest reads the file BYTES the way .veldo/request_reconcile.py:131-139 already
      reads them and keeps ALL 64 hex characters, the width this repository already uses where a
      digest BINDS a decision rather than labels an artifact for a human to eyeball
      (.veldo/sizing_pass.py:485-489, and its validator requires the full 64 at
      .veldo/sizing_pass.py:525-528). plan_hash is deliberately NOT changed: it serves a proof binding
      that is right to ignore when a plan was approved, and a shipped assertion pins that behaviour
      (scripts/suites/01_warp_0101_reviewer_notes.py:471), so widening it would break a working binding
      to fix a different one. The digest is REACHED rather than sitting as an unused primitive: the
      release registry records it on each resolved member beside that member's id and path, so the
      derived view and every later receipt read one value. NEGATIVE CONTROL, and it is the leg that
      matters: the selftest edits ONE BYTE BELOW THE FRONT MATTER of a fixture plan and requires the
      member digest to change while plan_hash over the same two files stays EQUAL, which asserts the
      DIFFERENCE between the two hashers rather than the mere presence of a hash, and it requires the
      digest to be 64 hex characters so a truncation to 16 reds.
  - id: AC5
    falsified_by: >
      Make the member scan refuse a member plan declaring kind mvp instead of appending a notice, and
      the assertion that a release whose member plan declares kind mvp validates with zero errors and
      exactly one notice must go red.
    text: >
      ADOPTION SAFE, AND THE WORD MVP DOES NOT REDDEN SEVENTEEN PLANS. Two conditions stand the whole
      check down and both produce the identical stood-down report in the SAME key shape a live report
      carries, each naming which condition it was: no releases directory at all, and a releases
      directory holding only the template, which is excluded from the registry exactly as
      plan_registry excludes it (.veldo/validate.py:658-659). The stand-down is keyed on AN EMPTY
      RELEASE REGISTRY rather than on an absent directory, because shipping the template creates the
      directory and a stand-down keyed on the directory would silently stop standing down the moment
      the template landed. THE MVP DISPOSITION REPLACES THE DRAFT'S D3, WHICH WOULD HAVE REFUSED A
      PLAN THAT CALLS ITSELF AN MVP WHILE BEING A MEMBER OF A RELEASE: that refusal is not shipped,
      because MEASURED on 2026-08-11 seventeen of this repository's eighteen plan files declare kind
      mvp (the exception is plans/PLAN-0002-companion-home.md), so it would fire on the first release
      ever declared and its retrofit would be seventeen files. Instead a member plan declaring kind
      mvp is REPORTED once per release, naming the count and the files, in the report-then-flip
      posture VELDO-0001 already established for a contract rule that would otherwise redden a working
      repository on arrival (.veldo/validate_checks.py:930-942). WHAT IS REFUSED IS THE COLLISION THAT
      NEEDS NO RETROFIT: two releases both declaring kind mvp, because at most one artifact may claim
      to be the MVP and the word now lives at the release level. ANTI-VACUITY ON BOTH HALVES: the
      notice assertion is driven against a fixture whose member plan declares kind mvp AND a sibling
      fixture whose member plan does not, so an always-on notice a reader would learn to ignore fails;
      and the stand-down assertions are paired with a POPULATED release corpus that must NOT stand
      down, so the stand-down cannot be what makes every case pass.
required_evidence: [unit]
rollback: >
  Delete the registration of check_release in the corpus sweep and the one call that reports plan-id
  duplicates. The releases directory and its template become inert markdown that no reader consults,
  .veldo/releases.py and its engine twin are removed with the suite fragment and its manifest entry,
  and the one includes entry added to .veldo/architecture.yaml is removed. Nothing already written
  becomes invalid, because no plan file, spec file or proof changes shape, and plan_hash is untouched,
  so no existing proof binding moves.
---

# The release contract and its registry

## Intent

The method promises a planning layer and delivers exactly one level of it. The founder named the
missing level himself: "MVP is very specific for first release but maybe Release is more appropriate.
Among them is MVP release or any other. But it is actually needed. How would you scope a release?
With a single plan? No, it needs to be group of plans (plan of plans)."

So the unit above the plan is the release, an MVP is simply the first one, and a release cannot be
scoped by one flat plan. This item builds the bottom of that layer and nothing above it: the artifact,
its registry, the type rule that makes the plan the floor, the graph rules that make the member set a
forest, and the content binding every later receipt will rest on. It does not build the ordering, the
two-way binding, the derived view, the composed cut, or the human surface; those are named in the
notes with the seams they split on.

Three defects are fixed here rather than later, and each is fixed at the bottom because that is where
it is cheap:

- A duplicate plan id vanishes silently (PLAN-0018 finding 24). A release resolves its members
  through the plan registry, so a registry that drops a colliding member would let a release bind to
  whichever file sorted last. Found by five plan drafts written declaring one id, with nothing
  objecting.
- A binding by front matter is not a binding (PLAN-0018 finding 25). `plan_hash` cannot see a plan
  body, so the receipt design that quoted it as a content hash had a hole the size of a plan body.
  The digest primitive lands here, with the member record that consumes it, so no later item is
  tempted to reach for the wrong hasher.
- A stand-down keyed on today's absence stops standing down (PLAN-0018 finding 26). The
  adoption-safe posture is keyed on an empty release registry, not on an absent directory, because
  shipping a template creates the directory.

## Context

### What exists today, verified

- Plans live flat, contract `veldo.plan/v1`, validated by `.veldo/validate.py`; there are 18 plan
  files plus a template in `plans/`.
- A plan's work item resolves only to a spec id, typed by a regular expression at
  `.veldo/validate.py:546-547`. A work item therefore cannot itself be a plan, which is why grouping
  cannot be expressed in the shipped contract.
- `kind` already allows `mvp` (`.veldo/validate.py:38`), so today an MVP is expressed as one plan.
  That is the exact thing the founder's question rejects.
- `plan_registry` (`.veldo/validate.py:652-670`) is a bare `reg[fm["id"]] = ...` with no duplicate
  check, and it skips files whose name starts with TEMPLATE (`.veldo/validate.py:658-659`).
- `plan_hash` (`.veldo/plan.py:216-222`) hashes front matter with `approved_at` and `recorded_at`
  dropped, truncated to 16 hex. A shipped assertion pins the volatile-key exclusion
  (`scripts/suites/01_warp_0101_reviewer_notes.py:471`), so it is a working binding for the thing it
  binds and must not be widened for a different purpose.
- A file-bytes digest already exists at `.veldo/request_reconcile.py:131-139`, at the 16-hex short
  width, and a full 64-hex binding digest already exists at `.veldo/sizing_pass.py:485-489` with its
  validator requiring the full width at `.veldo/sizing_pass.py:525-528`. The house therefore already
  spells both, and the rule this item follows is the one those two imply: a short digest labels, a
  full digest binds.
- Absent, and searched for before being called absent: `check_release`, `release_registry`,
  `veldo.release/v1`, `RELEASE_STATUSES`, a `REL-nnnn` id, and a `releases/` directory all return
  nothing anywhere in the tree. One near-collision is real: `.veldo/release.py` exists and owns
  staged rollout and rollback execution (`.veldo/release.py:1-22`), a different concern, which is why
  the new module takes the plural name matching the new directory and the shipped module is not
  renamed.
- The architecture contract's `contracts` area lists its files explicitly
  (`.veldo/architecture.yaml:19-21`), and an area was already added to the approved contract by a
  shipped spec with its reason recorded in the file (`.veldo/architecture.yaml:45-52`), so amending
  `includes` inside an ordinary item has precedent.

### Prior art, adopted and argued with

`docs/design/05-product-planning-layer-sol.md` is the design for this capability and it never became
a spec, which is PLAN-0018 finding 18 (`plans/PLAN-0018-what-a-complex-project-needs.md:319-321`). It
is read here as prior art to adopt or reject in the open, not to quietly re-derive.

Adopted:

- Specifications bind to the nearest leaf plan (`05:318`). Kept exactly: a spec binds to a plan,
  never to a release, so the layer below is untouched and the spec contract grows no second parent.
- A release grouping is for a genuinely large increment and is not the default workflow
  (`05:310-323`). Kept: the single plan stays the common case, and a repository that declares no
  release is unaffected.

Rejected, with reasons:

- "An approved plan contains either direct `work` or `child_plans`, not both" (`05:317`) and the
  `parent_plan` / `child_plans` fields on the plan schema (`05:103-104`). That makes a plan a union
  type discriminated by which key happens to be populated, so every reader must branch on
  container-or-leaf and a reader that forgets fails open. A separate artifact type makes the illegal
  state unrepresentable rather than merely refused, and keeps required-field checks unconditional,
  which is how the plan validator already works (`.veldo/validate.py:486-503`). This is the draft's
  D1 and it is the founder's call: see the notes.
- Status-as-directory (`05:79-89`). The method already forbids this for specs and explains why: every
  reader reads the corpus flat, and a file one directory down is invisible to all of them and fails
  silently. Releases go flat, like plans.

## Out of scope

- Ordering, activation and claimability. Nothing in this item changes `.veldo/frontier.py`, and no
  member's order field is consulted; the release report is a reading and no gate stage consumes it.
- The two-way binding. No plan file gains a parent field here, so no plan is edited and no retrofit
  is implied. A declared member whose plan file exists is resolved and digested; whether that plan
  binds back is the next item's refusal.
- The composed cut, the receipt, the observation window and the close. This item ships the digest
  primitive and the member record that carries it, and writes no receipt.
- Any change to `plan_hash`, to `recompute_file_digest`, or to `.veldo/release.py`. Each is named
  with its reason above rather than left as an omission a reader has to notice.
- `docs/method.md` and the packs. The documents gain the release as the unit that groups plans in the
  release item, and no skill is shipped here: a skill that documents a verb the code does not have is
  the failure that item exists to avoid.
- Judging whether a release is a GOOD grouping. The contract types the shape; whether the grouping is
  sensible is a review-lane judgement and a machine that pretended to make it would produce exactly
  the confident wrongness this layer is supposed to remove.

## Notes

### Where the draft's oversized items split, and on what seam

The draft (`myday/data/veldo-plan-drafts-2026-08-11/release-layer.md`) filed nine items, four of them
too big. The splits, with the seam named, are what follows this spec:

1. **The release's promise and its order** (the other half of the draft's W1). Member `depends_on`,
   the rule that every member serves a declared release outcome, release-level regression journeys,
   the cut definition, and the open-decisions block. SEAM: this spec answers "is this a legal release
   corpus, and what are its members"; that one answers "what does the release promise, and in what
   order". Neither changes a rule the other makes.
2. **The two-way binding** (the draft's W2). The plan side's parent fields and the forward and reverse
   refusals, modelled on `.veldo/validate.py:636-649` and `.veldo/validate.py:673-695`.
3. **The release status read** (half of the draft's W3). The member tree and each member's state, as a
   command.
4. **The release section of the derived index** (the other half of W3). SEAM: a reader versus a
   generated artifact; the second must regenerate byte-identically and therefore carries no timestamp
   (`scripts/update_index.py:122-126`).
5. **Release-ordered claimability** (the draft's W4) and **elaboration as a unit of work** (W5), in
   that order, because both touch `.veldo/frontier.py`.
6. **The composed release check** (the draft's W6).
7. **The receipt writer** (half of W7): records each member by the digest AC4 defines, with the specs
   that shipped under it. SEAM: writing the receipt versus enforcing it.
8. **The close refusals** (the other half of W7): a changed member digest, an unelapsed observation
   window, an out-of-threshold observation check.
9. **The release verbs in one pack** (half of W8) and **the fan-out to every other pack plus the plan
   skill's binding lesson** (the other half). SEAM: the verbs versus the fan-out; the second is
   mechanical and the first is not.
10. **Release** (the draft's W9): the engine canon, the documents, the capability record.

Ids are not assigned to those here, because the plan they belong to does not exist yet and inventing
ids other work may already hold is the collision this item's own AC2 is about.

### Decisions left open, and what each blocks

- **The load-bearing choice, the draft's D1.** A separate recursive release contract, as specified
  here, or the prior design's plan schema with `parent_plan` and `child_plans` and the either-or rule.
  This spec assumes the separate contract and argues for it in the context above. If the founder
  chooses the prior design's shape, this spec is WITHDRAWN rather than amended, because AC1 and AC3
  describe an artifact that would not exist. BLOCKS: everything, including this item.
- **The plan this item belongs to.** The release-layer draft declares `id: PLAN-0018`, already owned
  by `plans/PLAN-0018-what-a-complex-project-needs.md:3` (status ready, approved 2026-08-11), and its
  work items already claim VELDO-0002 through VELDO-0010. The release-layer plan needs the next free
  plan id and a recorded approval. BLOCKS: this spec moving from `lane: standalone` to
  `lane: planned`, and the ids for the ten follow-on items above. It does not block building this one.
- **Whether adding one `includes` entry to the approved architecture contract should bump the
  contract's version.** The contract is `status: approved` (`.veldo/architecture.yaml:14-16`), is not
  a protected path (`.veldo/policy.yaml:16-27`), and has been amended by a shipped item before
  (`.veldo/architecture.yaml:45-52`). This item adds one entry and bumps nothing, following that
  precedent. BLOCKS: nothing here; recorded so the choice is visible rather than silent.
- **The draft's D2** (must a plan belonging to no release say so, at the cost of touching every plan
  file once). Untouched here, because this item edits no plan file. BLOCKS: the two-way binding item.
- **The draft's D8, naming.** Resolved in this item and not left open: the module is
  `.veldo/releases.py`, plural and matching the directory, with a docstring pointing at
  `.veldo/release.py` and saying what each owns. If the founder prefers renaming the shipped module,
  that is its own item with its own blast radius, never a side effect of this one.

### For the implementing agent

- Write the refusal before the happy path. The refusals are the product here: a release layer whose
  evidence is a validating fixture proves only that the parser runs.
- Every assertion gets its negative control beside it, and every live read is asserted as a READING
  of the corpus rather than as a requirement that the corpus stay as it is today. PLAN-0018 finding 26
  is that exact mistake made in four suites at once, and it was invisible to code review and found by
  using the feature.
- The suite fragment captures its own exceptions and reds the assertion that names them. A raise at
  fragment scope takes every assertion below it with it, which is how a mutation that deletes coverage
  passes.
- RULE #1 clean: ASCII hyphen only, no em dash, no en dash, no prose double hyphen.
