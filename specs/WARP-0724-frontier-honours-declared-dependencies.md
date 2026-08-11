---
schema: veldo.spec/v1
id: WARP-0724
title: The frontier hands out work whose prerequisites do not exist - five of ten claimable units have an
  unshipped declared dependency, including the one the owner personally ruled on, so a spec's declared
  depends_on must gate every build path and the field must be typed where it is declared
status: shipped
risk: high - the change is small, but it decides WHAT WORK THE PROGRAMME IS ALLOWED TO PICK UP, so getting it
  wrong in the permissive direction leaves the defect and getting it wrong in the strict direction starves
  the queue. The specific danger is a dependency cycle or a stale status making a legitimately-ready item
  permanently unclaimable, which would look like the queue being empty rather than like a bug. It is high and
  not critical because no protected path and no safety core is touched, the rule is asked at ONE point rather
  than spelled twice, and non-starvation is asserted on the real corpus rather than hoped for
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-07-29
approval_record: >
  GIVEN ON TELEGRAM, 2026-07-29 07:31 UTC, in answer to a question that stated the consequence rather than
  hiding it. The question was "Promote the two new defect specs so they can be built? Note the dispatcher fix
  shrinks your visible queue from ten items to five." His answer, verbatim: "2 yes". So the approval is
  informed: the one cost a reasonable person would object to was put in front of him before he answered.
  RECORDED, NOT PERFORMED. The agent writes down the decision the owner made; it never makes one on his
  behalf. Noted honestly for a later reader: this approval is a Telegram instruction rather than a ticket
  transition, which is weaker evidence than the VEL-9 precedent on WARP-0712, and it was accepted here
  because the owner was simultaneously and explicitly instructing the agent to stop seeking ceremony and
  finish ("We need to get to the end of this build, you're floating around").
lane: standalone
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/frontier.py"
  - ".veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/frontier.py"
  - "engine/.veldo/validate.py"
  - "engine/.veldo/validate_checks.py"
  - "packs/*/.veldo/frontier.py"
  - "packs/*/.veldo/validate.py"
  - "packs/*/.veldo/validate_checks.py"
  - "scripts/selftest.py"
  - "specs/WARP-0724-frontier-honours-declared-dependencies.md"
  - "proof/WARP-0724/**"
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      NO BUILD UNIT IS CLAIMABLE WHILE ANY DEPENDENCY ITS SPEC DECLARES IS UNSHIPPED, on EVERY path that
      offers build work, and the DECISION and its own REPORT are one function so they cannot disagree. A
      selftest builds a spec index in a temporary repository where a ready standalone spec declares a
      dependency at each non-shipped status in turn plus the absent case, and asserts the unit is absent from
      claimable() and named by withheld() for every one of them, then flips the dependency to shipped and
      asserts it appears and is named by neither. The statuses are enumerated from the module's own vocabulary
      rather than listed by hand, so a new status cannot silently become permissive. A second, GATE-LEGAL
      fixture asserts the same property on the PLAN path: an approved active plan whose work item's own
      dependencies are satisfied, naming a ready spec whose own front matter declares an unshipped
      prerequisite, does not offer that unit and does offer it once the prerequisite ships.
  - id: AC2
    text: >
      THE FIVE CURRENTLY MISDISPATCHED UNITS ARE NAMED AND THEIR DISAPPEARANCE IS ASSERTED, because the
      measurement is the reason this item exists. MEASURED 2026-07-28 at a03d949, ten units claimable, of
      which WARP-0712 (needs WARP-0716), WARP-0714 (needs WARP-0712), WARP-0715 (needs WARP-0713), WARP-0717
      (needs WARP-0712) and WARP-0718 (needs WARP-0620) each have an unshipped declared dependency. A
      selftest asserts that on the repository's own spec index no claimable build unit has an unshipped
      dependency, so the property is checked against the real corpus and not only against a fixture.
  - id: AC3
    text: >
      THE QUEUE DOES NOT STARVE AND THAT IS PROVEN, not hoped. A selftest asserts claimable() is non-empty on
      the repository's own index, and separately that a dependency CYCLE among ready specs does not make the
      predicate raise or hang: it yields nothing for the cycle members and still yields every unrelated unit.
      A missing dependency id, one naming a spec that does not exist, must also be treated as unshipped and
      reported rather than skipped, because a typo that silently satisfies a dependency is the same class of
      defect as this one. EVERY read of the dispatcher in the block goes through ONE CHILD INTERPRETER under a
      wall-clock ceiling, so a dispatcher that does not terminate is a legible red rather than a run that
      produces no pass/fail summary at all. That is a correction made twice, both times by a mutant, and both
      measurements are on record.
  - id: AC4
    text: >
      REVIEW UNITS ARE UNAFFECTED, asserted explicitly. A review unit is of an already-built spec, so its
      dependencies are irrelevant to whether it can be reviewed. The gate is applied to build units by an
      explicit kind test at the one point every offer passes through, so the exemption is a test that can be
      mutated and measured, not an accident of routing. A selftest asserts a spec at status review with an
      unshipped dependency, and one with a dependency naming no spec at all, are both still offered as review
      units and appear in no withheld report.
  - id: AC5
    text: >
      DEPENDS_ON IS TYPED IN THE SPEC CONTRACT.
      NOT a universal over every place the field is declared: the PLAN WORK ITEM also carries `depends_on` and is
      NOT typed here, and a list-of-mappings or nested list there makes `check_plan` itself raise TypeError
      rather than fail legibly. That is a separate item, named and not claimed closed. check_spec refuses a depends_on that is not a list of whitespace-free spec-id strings, which
      is the one fix for four gate-legal shapes measured to break the dispatcher: a list of mappings and a
      nested list raise TypeError (unhashable type) inside it, an integer member raises inside the plan
      module's join, and a bare scalar iterates its CHARACTERS and reports a spec waiting on "W", "A", "R". A
      selftest asserts the pair: every measured bad shape is refused, and every shape the contract admits is
      read without raising. It does not claim the reader cannot crash, only that it cannot crash on input the
      contract admits. A member naming a spec that does not exist stays legal, because AC3 requires the
      frontier to treat it as unshipped and report it.
  - id: AC6
    text: >
      A SPEC ID NAMES EXACTLY ONE FILE. Every reader of the corpus resolves {id: spec} last-wins by sorted
      filename, so two files declaring one id let a prerequisite sitting at draft in one read as shipped from
      the other, which releases dependent work the AC1 gate is there to hold. Refused in the corpus contract
      (validate.check_spec_ids, run from the same sweep that validates every spec), never patched into each
      reader. A selftest MEASURES the last-wins harm in a fixture, asserts the duplicate is refused, asserts
      the same check passes once the duplicate is removed, and asserts this repository's own corpus passes.
required_evidence: [unit]
rollback: revert the commit; the change is one gate, one report and two contract checks, and nothing persists.
---

## Intent

`depends_on` is a declared field. A dispatcher that hands out work while ignoring it makes the declaration
decorative, and the harm is not theoretical: **WARP-0712's own AC1 says it "does not begin until" WARP-0716
has produced its crossing-state verdict, and the frontier offers WARP-0712 right now while WARP-0716 sits at
ready.** A builder that trusts the queue would start the highest-consequence refactor in the repository
before the enumeration it depends on exists.

The second instance is worse because it erases a human decision. The owner ruled on VEL-16 that the suite
split decides the shape before the speed work lands, and that ruling was implemented as a declared
dependency: WARP-0714 depends on WARP-0712. The frontier offers WARP-0714 anyway. **So the decision was
recorded and is unenforced, which is the failure mode this repository exists to prevent: a rule that lives
in a document instead of in the code that acts on it.**

## Context

`.veldo/frontier.py` `claimable()` had two build paths and each had its own idea of a dependency. The PLAN
path computes a shipped set and calls `PL.item_state(...)`, which reads the PLAN WORK ITEM's `depends_on` -
so a plan's work item surfaces at its plan's frontier, and the spec's OWN front matter is never consulted.
The STANDALONE path immediately below it filtered on `lane == "standalone" and status == "ready"` and read no
dependencies at all.

Both are the same mistake: a per-path rule. Three routes follow from it and all three were driven:

- **The standalone path**, which is the original measurement: five of ten claimable units had an unshipped
  declared prerequisite.
- **The plan path.** Setting `specs/WARP-0620` to ready with `depends_on` including WARP-0712 (at ready)
  leaves `check_spec` and `check_ready` both at 0 and the frontier still prints `build WARP-0620 PLAN-0016`,
  while `unmet_dependencies` on that same spec in that same process returns `[('WARP-0712', 'ready')]`. A
  predicate contradicting its own report is the defect whichever answer is right.
- **Both paths reaching one spec.** Whichever loop ran first put the id into `seen`, and the standalone loop -
  the only one that asked about dependencies - returned early without asking.

So the rule is now asked ONCE, in `_add()`, which every offer passes through however the unit was found. The
plan's work graph keeps its own separate job: it decides ORDER WITHIN a plan. A planned spec must satisfy
both, and that is the conservative direction on the axis that matters here.

## Where the report lives

AC3 requires a dependency naming a spec that does not exist to be REPORTED rather than skipped, and the risk
section names the danger that an ordering rule looks like an empty queue instead of a waiting one. Both are
answered by one addition: `withheld()`, a pure read that returns the build work a declared prerequisite is
holding back, each entry naming the prerequisite and its state, with `DEP_ABSENT` for a prerequisite no spec
declares. It reports EVERY ready spec, planned or standalone, because the gate withholds every ready spec and
a report narrower than the rule it explains is this same defect one layer up. `veldo frontier` writes it to
STDERR in both output modes, so the diagnostic is always visible next to a short queue while STDOUT stays
exactly the claimable set that existing callers parse.

## Why the field is typed rather than guarded

Four `depends_on` shapes passed `check_spec` and broke the reader, measured: a list of mappings in either
form and a nested list raise `TypeError: unhashable type` inside the dispatcher, an integer member raises
inside the plan module's join, and a bare scalar iterates its characters and reports a spec waiting on "W",
"A", "R". Guarding the reader would have meant the same guard in `unmet_dependencies`, `item_state` and every
future reader, and each guard would have had to invent a meaning for a value the contract never defined. The
field is declared in TWO contracts - the spec and the plan work item - and this item decides its shape in ONE
of them (`validate.check_depends_on`), so the readers of a SPEC's depends_on keep reading. The plan work
item's copy is untyped and still crashes; that is the separate item above. The same reasoning puts the duplicate-id refusal in the corpus contract rather than in
`_spec_index`.

## Footprint

The declared footprint was widened twice, and both times because a rule this repository already enforces made
the narrower footprint FALSE rather than merely incomplete. First from `.veldo/frontier.py` alone to every copy
of it: the engine is held byte-identical across the canonical source and every declared pack
(`check_template_sync.sh`, `check_pack_drift.py`), so a change to the dispatcher is a change to every copy.
Then to `.veldo/validate.py` and `.veldo/validate_checks.py` and their copies, because typing the field at the
declaring layer is a change to the validator. The two new checks live in `validate_checks.py`, the sibling
module that exists precisely so `validate.py` stays under the `module_lines` budget the architecture contract
ENFORCES: putting them in `validate.py` was measured to take it to 1055 lines against a 1000-line budget and
turned the shape gate red. No new architecture area is reached, so the derived tier is unchanged.

## Out of scope

The `requires`/capability gate, the placement gate and the claim ledger are all correct and untouched. This
item does not change any spec's declared dependencies, does not promote or demote anything, and does not
decide whether the five named units SHOULD be reordered - only that the tool must stop offering work whose
prerequisites are unshipped.

Three things are DECLARED OUT OF SCOPE with their reasons rather than left undescribed:

- **Duplicate PLAN ids.** `plan_registry` resolves a plan id the same last-wins way `_spec_index` did, and
  nothing refuses two plan files declaring one id. It is the same class as AC6 and it is not fixed here
  because the plan registry's readers are a different surface with their own gate passes, and folding them in
  would make this item's blast radius larger than its own measurement. It is named so the next reader finds
  it, not left for them to rediscover.
- **A spec with NO declared lane** (five in the corpus today) is invisible to the standalone loop, which asks
  for `lane == "standalone"` literally. That is the conservative direction - such a spec is never offered as
  standalone build work at all - and inferring the lane in the dispatcher would be a policy change this item
  was not asked to make.
- **The readers stay last-wins.** `_spec_index`, `plan.spec_status_by_id` and `run_all`'s own `spec_by_id`
  still resolve a duplicate id by taking the last file. The gate refuses the input, which is the layer that
  declares the contract; a repository whose gate has never run can still be misread, and that is the honest
  residual of fixing it there rather than in six readers.
- **`specs/TEMPLATE.md` still does not mention `depends_on`,** so an author learns the field's type from the
  validator's refusal rather than from the template. Documenting it is an edit to the template and to the copy
  of it in every declared pack, which would widen this item's footprint again for a docs improvement the
  measurement did not ask for.

## Two things a reviewer should attack

This spec carries SIX acceptance criteria, above the three-or-four this programme holds itself to. The
alternative was three items, and the review that found the plan-lane route, the untyped field and the
duplicate-id hole required them closed together because they are one defect class - a rule that lives in one
reader instead of at the layer that declares the contract. Recorded rather than hidden: if this were being
sized from scratch, AC5 and AC6 would be their own items.

And the one design choice worth arguing with: a planned spec is now DOUBLE-GATED, by its plan's work graph
and by its own front matter. The previous build declared the opposite (that front matter must not override an
owner-approved plan) and the review confirmed that as the defect, because the module contradicted itself in
one process. The reason double-gating is right rather than merely stricter: the two questions are different.
The plan says when the plan is ready for an item; the spec says what the item cannot start without, which is
frequently a fact about work OUTSIDE the plan (WARP-0718 depends on WARP-0620 across exactly that boundary
today). Neither answer subsumes the other, so both must hold. MEASURED on the real corpus the strict direction
withholds nothing that was being offered - but that measurement is VACUOUS for the plan lane, because every
ready spec in this corpus is lane standalone, so there is no planned ready unit for it to withhold. The
plan-lane half is proven only in a gate-legal fixture.

## Approval

The cost a reasonable owner would object to is that fixing this shrinks his visible queue. That cost was
stated to him before he approved, as "from ten items to five", and he approved anyway. See `approval_record`.
The numbers he was given were the 2026-07-28 measurement at a03d949; MEASURED AGAIN at 18e6ca8 the queue was
twelve and the fix leaves seven, because WARP-0723 and WARP-0724 were promoted to ready in between. Recorded
rather than quietly corrected: he approved a shrinking queue with the same five units named, and the shape of
the cost he agreed to is unchanged.
