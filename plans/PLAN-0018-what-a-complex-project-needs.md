---
schema: veldo.plan/v1
id: PLAN-0018
title: What a complex project needs and Veldo lacks - the organs this migration proved missing, and
  the accumulating ledger of every finding it produced
kind: mvp
status: ready
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-08-11

# THIS PLAN IS TWO THINGS ON PURPOSE, and the second is why it exists.
# It is a set of work items closing capability gaps. It is ALSO the LEDGER: every finding this
# migration produced is recorded here, including the ones fixed elsewhere, with a pointer to where.
# Dmitry 2026-08-11: "once completed and all working, the plan should include all the findings, as I
# am sure between now and then you will find more." So the ledger is APPEND-ONLY and the plan is not
# done while a finding is unrecorded. A finding that lives only in a chat message is a finding we
# will rediscover.
#
# PROVENANCE. Every entry below is something that ACTUALLY BIT US between 2026-08-09 and 2026-08-11
# while opening this method's source as a public repository. Nothing here is speculative, and that is
# the entry requirement: a gap earns a place by having cost us something measurable.

outcomes:
  - id: O1
    becomes_true: >
      A complex project can be run through Veldo without the operator keeping the real state in
      their head or in a shell. Work that was built is known to have been built, by the system,
      across a session that died.
    measure: >
      Kill a session mid-flight with parallel work in progress, start a fresh one, and ask Veldo
      what is done. It answers correctly without anyone grepping worktrees. That is the exact
      failure of 2026-08-10, where four built items survived only because a human went looking.
  - id: O2
    becomes_true: >
      Parallel work that is NOT construction (review, audit, authoring, investigation, migration)
      has an organ. Today the fleet pulls ready specs from the frontier and builds them, and that
      is the only kind of work it knows.
    measure: >
      The nine independent reviews, eight document audits and five plan critiques of this migration
      could be dispatched and paced by Veldo rather than by the harness. Measured by running that
      same job through it.
  - id: O3
    becomes_true: >
      The method notices what nobody specified: a promise with no implementation, a design with no
      descendants, a shipped document making a claim the tree does not support.
    measure: >
      Run it against this repository's own documents and the book. It finds the class of hole that
      a book audit found in an hour on 2026-08-10 and every automated check missed.
  - id: O4
    becomes_true: >
      A budget is not exceeded on the path an operator actually takes, and losing a window costs
      pacing rather than work.
    measure: >
      Exhaust a window deliberately during parallel work and lose no completed work and no queue
      position. On 2026-08-10 and 2026-08-11 two sessions hit limits and 85 agents died mid-flight.

non_goals:
  - id: NG1
    text: >
      This plan does NOT remediate PLAN-0014's 34 review findings. Those belong to that plan and
      are recorded in the ledger below with a pointer, because mixing a capability build with
      another plan's remediation would make both unreviewable.
  - id: NG2
    text: >
      No daemons, no detached processes, no headless spawners. Every organ here runs in-session.
      This is not a constraint to design around, it is the constraint: the fleet's own refusal to
      spawn detached workers is a safety property, not a limitation to route past.
  - id: NG3
    text: >
      Nothing here gates on a number. A completeness organ that BLOCKS on a heuristic verdict would
      cut true sentences and stop real work. Advisory, loud, and human-resolved.

constraints:
  - id: C1
    text: >
      Every organ added here must be honest when it cannot answer. The disease this migration kept
      finding is the confident zero: a module reporting 0.000 as a measurement when the input was
      never recorded. An organ that cannot tell "no data" from "measured zero" is worse than none.
  - id: C2
    text: >
      Every check added here must be able to fail, and the proof is a driven mutation with the
      mutation asserted to have applied. Three checks shipped in this project could not fail, and
      one of them was found only because a reviewer edited the module and watched the suite stay
      green.
  - id: C3
    text: >
      No hand-maintained list of what to verify. A curated list is a promise somebody will remember,
      and the thing it protects is exactly what people forget: seven listed pairs guarded nine
      modules that arrived later. Derive the domain, declare the exceptions with reasons.

feature_tree:
  - id: F1
    title: Work state that survives a dead session
    outcome_refs: [O1]
  - id: F2
    title: A fleet for work that is not construction
    outcome_refs: [O2]
  - id: F3
    title: The completeness organ
    outcome_refs: [O3]
  - id: F4
    title: Budget continuity on the path people take
    outcome_refs: [O4]
  - id: F5
    title: The product actually runs, checked as a criterion
    outcome_refs: [O3]
  - id: F6
    title: A running installation can say what it is
    outcome_refs: [O3]
  - id: F7
    title: The method's own checks are provably able to fail
    outcome_refs: [O3]

work:
  - item: W1
    spec: VELDO-0002
    title: Recorded work state, derived not remembered, surviving a dead session
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: VELDO-0003
    title: A dispatch organ for review, audit and authoring work, paced by the governor
    feature_refs: [F2]
    depends_on: []
    order: 20
  - item: W3
    spec: VELDO-0004
    title: The promise corpus - extract checkable claims from a document and settle each against the tree
    feature_refs: [F3]
    depends_on: []
    order: 30
  - item: W4
    spec: VELDO-0005
    title: A design with no descendants and a capability with no home are named findings
    feature_refs: [F3]
    depends_on: [VELDO-0004]
    order: 40
  - item: W5
    spec: VELDO-0006
    title: Budget continuity - the governor covers the operator's path, and a spent window costs pacing not work
    feature_refs: [F4]
    depends_on: [VELDO-0002]
    order: 50
  - item: W6
    spec: VELDO-0007
    title: The install-and-run smoke criterion, proven from the artifact an adopter receives
    feature_refs: [F5]
    depends_on: []
    order: 60
  - item: W7
    spec: VELDO-0008
    title: veldo version - the CLI can answer what it is, from one declaration
    feature_refs: [F6]
    depends_on: []
    order: 70
  - item: W8
    spec: VELDO-0009
    title: init stamps the version into the repository it lays down, so substrate drift has a detector
    feature_refs: [F6]
    depends_on: [VELDO-0008]
    order: 80
  - item: W9
    spec: VELDO-0010
    title: The gate output and the proof bundle name the version that produced them
    feature_refs: [F6]
    depends_on: [VELDO-0008]
    order: 90
  # ADDED 2026-08-13 UNDER DMITRY'S RECORDED DECISIONS, not unilaterally. This plan is `status:
  # ready, approved_by: dmitry`, so adding a work item changes an approved scope. Both items exist
  # because the twelve independent reviews of W1 to W9 found that the dominant defect class in this
  # project is a check that cannot fail for the defect its own criterion names, and the two decisions
  # below are what he chose to do about it. Each is bound to its decision record rather than to a
  # conversation.
  - item: W10
    spec: VELDO-0013
    title: A declared falsification is DRIVEN once per item and recorded against the commit it was
      driven at, so a vacuous criterion is caught when the evidence is written
    feature_refs: [F7]
    depends_on: []
    order: 100
    decision: VELDO-DEC-0001
  - item: W11
    spec: VELDO-0014
    title: What a criterion may assert about the live repository, stated as a rule and enforced where a
      scan can see it, with its blind spots reported rather than implied
    feature_refs: [F7]
    depends_on: []
    order: 110
    decision: VELDO-DEC-0002

regression:
  journeys:
    - id: RJ1
      title: >
        A flattened clone of the published tree initialises from a composed pack and its own gate
        runs green. This is the journey whose absence shipped an uninstallable 1.0.
      activation: {when: start}
      suite: scripts/suites (the smoke criterion of W6, once it exists)
    - id: RJ2
      title: >
        A session killed mid-flight during parallel work loses no record of what was built.
      activation: {when: after:VELDO-0002}
      suite: scripts/suites

release:
  milestone: Veldo survives a complex project without a human holding its state
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    Every organ here is additive and adoption-safe. A repository that declares none of it is
    byte-identically unaffected, which is the same posture the architecture contract took.
  observation:
    duration: >
      The real observation is the next complex project. This plan is not proven by its own suite; it
      is proven by running a migration-sized job through Veldo and not reaching for the harness.

open_decisions:
  - id: D1
    text: >
      Does the work-state record live in the event stream (already append-only, already the
      corpus's ground truth) or in its own store? The event stream is my recommendation because a
      second store would be a second truth, and this project's first principle is that the
      repository is the operating truth. Who answers: Dmitry.
    blocks: [VELDO-0002]
  - id: D2
    text: >
      Is the non-construction fleet the SAME organ as the construction fleet with a pluggable work
      source, or a sibling? My recommendation is the same organ with a work-source seam, because the
      governor, the claim ledger and the retirement logic are exactly what it needs and duplicating
      them would create the second spelling this project keeps finding. Who answers: Dmitry.
    blocks: [VELDO-0003]
  - id: D3
    text: >
      What is the authoritative statement of the promise for the completeness organ: the README, the
      method document, the capability manifest, or the book? They can and do disagree with each
      other, which is itself a finding the organ should report rather than resolve silently.
    blocks: [VELDO-0004]
  - id: D4
    text: >
      Does the smoke criterion run in the gate on every change (slow, complete) or at release only
      (fast, and blind between releases)? Gate-on-every-change is my recommendation despite the cost,
      because "does it install" was green for the entire life of 1.0 while being false.
    blocks: [VELDO-0007]
---

# What a complex project needs and Veldo lacks

This plan exists because the method was pointed at itself under load for the first time, and the
load found things no single change ever would. Opening the source as a public repository is the
largest, most coupled, least reversible piece of work this project has done, and it was run with
four parallel builders, two sessions that died, and a book auditing every claim. That is what a
complex project looks like, and it is the first time Veldo has been asked to be one.

The findings are not a list of bugs. They share one shape. **Everything the method had a mechanism
for, it caught. Everything it had no mechanism for, it missed, and every miss was an absence.**
Nobody had written down that init must work from the artifact an adopter receives, so nothing
checked it, and a 1.0 shipped that could not be installed while every check was green. Nobody had
written down that the documents must describe a layout the readers can actually read, so the spine
document sent adopters to a directory no shipped reader can see, and it failed by silence rather
than by error. Nobody had written down that every engine module must be paired, so a hand-written
list of seven guarded nine modules that arrived later.

A verification system is exactly as complete as its specification set. That is the sentence this
migration bought, and the organs below are what it costs to act on it.

## The findings ledger

Append-only. Every finding, including the ones fixed elsewhere, with where it was fixed. A finding
recorded nowhere is a finding we will rediscover, which is the cheapest possible way to waste the
price we already paid for it.

### Fixed during the migration (2026-08-10 and 2026-08-11)
1. **`/veldo:init` failed from every composed pack** with "gate template drift" and laid nothing
   down, so Veldo 1.0.0 could not be initialised by anyone. The published template shipped its
   slots pre-filled with exactly the text the scaffolder intended to write, and the scaffolder
   demanded the blank form. Nothing had ever run init from a composed pack, because every test runs
   against this repository, which is the one tree nobody installs. FIXED, proven end to end: 49
   files laid into a fresh repository whose own gate then ran green.
2. **The method document told adopters to file specs where no reader can see them.** Nine shipped
   readers glob `specs/*.md` non-recursively and there is no recursive read anywhere in the
   substrate, so a spec filed one directory down is invisible to the validator, the index, the
   frontier and the push guard. Measured: the same file gives 0 index rows nested and 1 flat.
   FIXED in three places plus one example, and the text now says why it is flat.
3. **The template sync check was a hand-written list of seven pairs** and nine estimation modules
   were never added, so the copy every adopter installs was guarded by nothing. Demonstrated by a
   reviewer inverting `engine/.veldo/toe_corpus.py` so the corpus always reported itself usable as
   ground truth, with template sync printing pass and 3942 tests passing. FIXED by deriving the
   pairs: 113 compared, 7 declared per-repo exceptions with reasons, fails closed on an
   implausible count. Reproduced the mutation to prove the fix, asserting the mutation applied first.
4. **The redaction pass silently stripped every executable bit**, disarming every pack's git
   pre-push hook, `veldo-guard.sh` and `bin/veldo`. Git skips a hook it cannot execute, so the tree
   would have shipped LOOKING gated and been fail-open. No leak scan could ever see this; the gate
   running INSIDE the produced tree caught all eleven. FIXED.
5. **Withholding the private-name list broke the successor's honesty suite**, which refuses to scan
   for nothing by design. FIXED by rewriting rather than withholding the file.
6. **The publication scanner called `GET /api/v1/home/` a build path**, because a bare substring
   cannot tell an absolute path from a route. FIXED with a not-nested requirement plus a negative
   control proving real build paths still fail.
7. **The publication negative control pinned one entry of the private-name list by name**, making
   the only check proving the scanner has ever caught anything a hostage of the list's contents, and
   putting a supplier's name in a shipped test. FIXED by deriving the seed from the list.
8. **`WARP-1404`'s engine twin had drifted eleven lines**, the primary carrying a correctness fix the
   shipped copy never got. Caught by its own acceptance criterion at merge. FIXED.
9. **The tracker operator guide told an operator three untrue things** and the README repeated them:
   that the mirror transitions the ticket you filed, that the inbound bridge can be turned on and
   runs itself, and that the live adapters ship. FIXED in both.
10. **The guard's capability entry and the README both asserted a rule that was deliberately
    removed**: a passing commit-bound verdict required at push. Enforcement is real and arguably
    stronger (a green gate, the owner's approval on protected paths, and an unresolved objection
    blocking the push), but both documents described the removed rule and the capability was KEYED
    on it. FIXED, key renamed.
11. **`WARP-1401`'s acceptance criterion published stale figures**, 148 shipped specs and 95.3
    percent cycle coverage, overstating by 14 points. Measured: 174 records, 141 with cycles, 81.03
    percent, spend coverage zero, and the module's own verdict is NOT usable as ground truth. FIXED,
    and the criterion now says these are dated evidence rather than a contract.
12. **The verdict example had diverged into two formattings of the same JSON**, invisible to the old
    hand list. FIXED by syncing to the engine canon.
13. **Veldo shipped 1.0 without ever expanding its own acronym.** FIXED in the README, the method
    document, and the first content sentence of veldo.dev.

### Recorded here, fixed under another plan
14. **PLAN-0014 failed independent review on all nine items: 34 findings, 14 blockers**, with 12
    accusations refuted by the adversarial pass. Two are landmines that fire on first real use:
    `WARP-1408`'s suite asserts against the live repository that zero estimates exist, no token
    price is declared and `.veldo/estimates` does not exist, so the gate reddens the moment anyone
    uses the feature; and `WARP-1404`'s real-repository measurement goes red when that item's own
    status flips to shipped. One is a statistical error with a printed conclusion. Most of the rest
    are checks that cannot fail. Belongs to PLAN-0014 per NG1.

### Recorded here, awaiting an organ in this plan
15. **Nothing tracked that four items had been built.** They survived a dead session only because a
    human hunted through worktrees. PLAN-0014 sat ready with ten items and no record of which were
    done. -> W1.
16. **The fleet only knows how to build a ready spec.** Every parallel job of this migration was
    review, audit, authoring or investigation, so the harness did all of it and the fleet did none.
    Its own author routed around it for the largest parallel job in the project's history. -> W2.
17. **The token governor never fired**, because it governs a worker pool that was never running. The
    README promises the budget "is used without running out"; two sessions ran out and 85 agents
    died. Even inside the fleet, resuming after token-out is an opt-in human act. -> W5.
18. **A design can die with nothing noticing.** `docs/design/05-product-planning-layer-sol.md`
    defined `child_plans` and never became a spec or a plan item, which is why a release still
    cannot be scoped as a group of plans. -> W4.
19. **Nothing compares a document's claims against the tree.** 64 false claims across 8 shipped
    documents, found by an audit rather than by the gate, and the honesty suite is structurally
    blind to it: marking a capability repo-only satisfies the gate while the documents go on
    claiming it ships. -> W3.
20. **No criterion says the product installs and runs.** The most expensive finding of the whole
    migration, green for the entire life of 1.0. -> W6.

21. **Two version lineages, each correct locally and wrong together.** The repository release is
    tagged 1.0.0 while the plugin declares itself 3.10.0, consistently, in `.claude-plugin/marketplace.json`
    and in every pack that declares a version. The 3.x lineage predates the project being public. Both
    numbers are defensible alone; together a stranger installing "Veldo 1.0.0" receives something that
    announces itself as 3.10.0, and cannot tell which number belongs in a bug report. RESOLVED
    2026-08-11: keep the plugin lineage, abandon the repo release lineage, so there is one number and
    it is the one attached to the artifact people install. Plugin bumped to 3.10.1 for the init fix.
    CORRECTION to this finding as first written: I said nothing checks that the versions agree, and
    that was wrong in a way worth recording. A check DID exist and pinned the literal "3.10.0" across
    two hardcoded paths. It had two defects instead of being absent: it named 2 of the 3 sites that
    declare a version, leaving `packs/antigravity/plugin.json` unwatched, and pinning a literal meant
    every bump edited the test, so the check and the thing it checked were maintained by the same hand
    in the same commit. Rewritten to DERIVE its sites and require agreement rather than a literal, so
    a bump touches no test and a new pack is covered the moment it exists. Proven by drifting the
    previously-unguarded site and watching it fail, with the mutation asserted to have applied.

22. **Nothing reports the running version.** `bin/veldo` contains no version command and no version
    string, zero hits. A user who wants to know what they are running has nowhere to ask. The number
    exists only in the plugin manifest of the artifact they installed, which is not a place anyone
    looks. -> W7.
23. **Nothing records which version initialised a repository.** `init_scaffold.py` stamps no version
    into the tree it lays down, so an adopter's repository holds no trace of what created it. This is
    worse than a missing convenience: the plugin upgrades and the laid-down substrate does not, so a
    repository can be running old substrate under a new plugin with nothing anywhere able to say so.
    Drift with no detector, the same shape as the engine twins that were paired by nothing. -> W8.
    And a proof bundle does not name the machinery that produced it, which for a method whose claim is
    that a stranger can check the evidence is an incomplete artifact. -> W9.

24. **A duplicate plan id vanishes silently.** `plan_registry` in `.veldo/validate.py` is a plain
    `reg[fm["id"]] = ...` with no duplicate check, so two plan files declaring the same id leave the
    validator reporting zero errors while one of them disappears from every derived view. Found by five
    plan critiques at once: all five drafts had been written declaring this plan's own id, and nothing
    objected. A registry that silently drops a member is the same class as a check that cannot fail.
25. **A release close receipt binds a member by front matter only.** `.veldo/plan.py` hashes front
    matter with volatile keys dropped, so a member plan's entire body can be rewritten after the
    receipt is written and the close still passes. The hole is exactly the size of a plan body. Found
    while critiquing the release-layer draft, but it is a property of the shipped hasher.

26. **THE MOST IMPORTANT FINDING OF THE DAY. An assertion measured over the live repository pinned
    today's emptiness as a required invariant, in FOUR suites independently, so the required gate went
    red the first time anybody used the estimation layer.** Driven and measured rather than argued: a
    scratch copy of this repository was 4145 passed and 0 failed; one invocation of the sanctioned
    writer, `python3 .veldo/spend.py record --spec WARP-0100 --basis harness_reported --tokens 750000`,
    which is precisely what the layer exists to do, took it to 4141 passed and 4 FAILED, in WARP-1403
    AC4, WARP-1404 AC5, WARP-1405 AC3 and WARP-1409 AC4.
    WHY IT MATTERS MORE THAN ITS COUNT: a gate that breaks on first real use is worse than a missing
    check, because it teaches whoever hits it that the gate is noise, and the person who hits it is the
    founder on the day he first tries the feature. It was also invisible to every form of review that
    reads code, including the adversarial pass that found the other 34: it took USING the product.
    AND IT DEFEATED ITS OWN REMEDIATION ONCE. The first review found this shape in WARP-1408 and I
    fixed that instance and told Dmitry the class was closed. It was not; three more suites carried it
    and I had checked only the two instances I had been handed. The lesson is the one this ledger keeps
    relearning: a class is not closed until the class is driven, and fixing the named instances is not
    the same as removing the shape.
    THE CORRECT SHAPE: an assertion over the live repository may require the honest STAND-DOWN when
    nothing is recorded and the measured branch when something is, chosen by what it just measured.
    Structural invariants and partitions stay unconditional. Nothing may assert that the measured set
    is empty.

### Found wiring VELDO-0011 and VELDO-0012 into the gate (2026-08-12)
27. **A DERIVATION THAT READS SOURCE FOR LITERAL PATHS IS BROKEN BY MAKING THOSE PATHS DYNAMIC, AND
    THE REFACTOR LOOKS CORRECT.** Three separate mechanisms regex `.veldo/validate_checks.py` for the
    quoted form of an organ path: what `/veldo:init` must lay down, and two independent gate
    dependency closures. Collapsing eight duplicated organ loaders into one generic loader that built
    the path from a variable emptied all three at once, reddening five assertions.
    WHAT IT HID is the point: a freshly scaffolded repository raising `FileNotFoundError` the first
    time a verdict reached the organ, which is the exact defect the init check was written for after
    `security_review` was wired in without being laid down.
    THE FIX KEEPS BOTH PROPERTIES: one generic loader, and the nine literal paths declared once each
    riding on the alias lines that had to exist anyway, so the inventory costs no extra lines. The
    duplication is gone and the literals are now an explicit declaration instead of nine paths buried
    in nine functions. GENERALISED: before changing how a path, id or module name is WRITTEN, look for
    a derivation that reads that file as text. If one exists, the literal form is load-bearing.
28. **A SOURCE-PARSING DERIVATION CANNOT TELL A SPECIFICATION OF A FORM FROM AN INSTANCE OF IT.** The
    comment written to warn that these paths must stay literal contained a quoted example, and both
    closures parsed the example as a real member: `.veldo/<name>.py` entered the dependency graph as
    a file that does not exist. Any file a derivation reads must spell such forms in words.
29. **BOTH OF init_scaffold's LISTS ARE HAND-MAINTAINED AND BOTH WERE MISSING BOTH NEW ORGANS.** The
    builders wired two organs into `validate_checks` and neither added them to `_FILES` or
    `REQUIRED_SUBSTRATE`. Nothing a human reads would have caught it; the derived check did. This is
    the third recorded instance of the same shape, which is the argument for deriving the list rather
    than keeping a second copy of it.
30. **A CARDINALITY ASSERTED OVER A CACHED REGISTRY BREAKS THE MOMENT THE THING IT MEASURES IS REALLY
    WIRED.** `18_veldo_0012` asserted `len(floor_standdowns()) == 1` over a module-level registry on a
    deliberately CACHED instance. Once `run_all` carried the registration it recorded a stand-down of
    its own into the same registry and the row went red. Same class as finding 26, in a new dress:
    the assertion measured process-wide accumulation instead of one call.
31. **THE REPOSITORY CONTRADICTS ITSELF ABOUT THE module_lines BUDGET, AND THE CONTRADICTION IS NOW
    LOAD-BEARING.** `architecture.yaml` declares `module_lines` ADVISORY (`enforcement: review`) on
    Dmitry's 2026-08-01 decision, recorded there in his terms: a mechanised cap "blocked a correct
    four-line security fix" and "costs more than the sprawl it prevents". WARP-1012 AC1/AC2 then HARD
    ASSERT two named files at `<= max`. So the contract says advisory and the suite says mandatory.
    WHY IT MATTERS: `validate.py` and `validate_checks.py` both now sit at EXACTLY 1000 of 1000, so
    the next correct change to either has nowhere to go, and the two available moves are both bad -
    shredding load-bearing rationale comments, or raising the budget, which uses his advisory ruling
    as a loophole to make room for one's own code. NOT RESOLVED TONIGHT and deliberately not resolved
    unilaterally: it is a contract question. Recorded so the next person does not rediscover it at
    2am while blocked.
32. **`validate_checks.py` HAS BECOME THE THING WARP-1012 SPLIT `validate.py` TO STOP BEING.** It now
    holds nine organs' gate faces plus every spec and proof check, at the budget ceiling. The correct
    fix is the same one: extract the organ loading and the organ gate faces, which are a coherent
    unit, keeping the literal path inventory in `validate_checks.py` where the derivations read it.
    Sized as its own item, not smuggled into an unrelated change.
33. **`record_problems` in `.veldo/release_contract.py` has cyclomatic complexity 33 against a budget
    of 20**, reported by the shape gate's review lane and therefore non-blocking. Left standing with
    the number named rather than silently accepted, and handed to the adversarial review to check for
    an unreachable branch or two causes reported under different names.

### Found by the independent reviews of VELDO-0011 and VELDO-0012 (2026-08-12)
Both reviewers drove every declared falsification themselves rather than reading for it. Eleven of
the twelve criteria across the two items have PROVEN teeth: the mutation landed, was diffed, and
reddened the row its own field names, with the paired control staying green so no refusal is a
blanket one. The findings below are what survived that.

34. **A DECLARED FALSIFICATION CAN NAME AN ASSERTION THAT IS STRUCTURALLY INCAPABLE OF FAILING, AND
    THAT IS WORSE THAN DECLARING NONE.** VELDO-0012 AC7 said: delete the stand-down guard from
    `check_floors_dir` and the byte-identity assertion over `run_all`'s output must red. It cannot.
    On CPython `Path("missing").glob("*.yaml")` yields nothing and raises nothing, so with the guard
    deleted the function still returns 0 and still prints nothing - the two behaviours are
    OBSERVATIONALLY IDENTICAL in what that assertion measures. Driven: guard deleted in both twins,
    suite unchanged at 87/3. The field read as proof the leg was defended while nothing defended it.
    VELDO-0011 AC2 carried the same shape differently: its field named `.veldo/validate.py:669`, a
    line the item never changes, so applying it verbatim is a no-op and an auditor could have
    concluded a criterion with real teeth was vacuous. BOTH FIELDS ARE NOW CORRECTED AND BOTH KEEP
    THE ORIGINAL WORDING beside the correction, because the mistake is the instructive part.
    GENERALISED, and this is the load-bearing lesson for VELDO-0001: the rule makes an author name a
    falsification, and nothing checks that the named assertion CAN fail. The check that would is a
    real item - drive each declared mutation and require its named row to red - and it is what these
    two reviews did by hand.
35. **THE FIX FOR FINDING 30 RESTORED THE ONLY TEETH AC7 HAD, WHICH IS WHY THE ORDER MATTERED.**
    The reviewer measured that with the registry cardinality row red for an unrelated reason, the
    stand-down guard could be deleted with no change in the suite's verdict at all. Clearing the
    registry so the row measures one call rather than process-wide accumulation put the teeth back:
    driven again after the fix, deleting the guard reds exactly one named row. Two defects that each
    hid the other.
36. **AC3's CENTRAL PROPERTY WAS DEFENDED FOR ONE OF FOUR KEY SETS.** The floor's four key sets are
    CLOSED by design so a ruling or a location-scoped exemption is unrepresentable. Only `PIN_KEYS`
    was pinned by exact set equality; `FLOOR_KEYS`, `SCOPE_KEYS` and `OBSERVATION_KEYS` were guarded
    only by a substring blacklist that omitted **module** - the very word the module's own comment
    claims is unrepresentable - along with verdict, judgement, ruled, allow, legacy and grandfather.
    Driven: `SCOPE_KEYS | {"modules_not_pinned", "verdict"}` left the suite unchanged at 87/3, and a
    floor carrying `modules_not_pinned: legacy/**` and `verdict: incidental` then validated with
    ZERO errors. A module-scoped exemption and a ruling, both representable, both undetected, with
    the row that exists to forbid them green. FIXED with the three missing exact set equalities, and
    the exact mutation now reds the named row. **A CLOSED SET'S TEETH ARE ITS ENUMERATION, never a
    word list**: a blacklist can only forbid the words somebody thought of.
37. **USING THE FEATURE ONCE REDDENED THE GATE, for the fifth recorded time in this repository.**
    `not (ROOT / ".veldo" / "floors").exists()` was a conjunct of AC7's byte-identity row, so writing
    one valid floor took the suite from 3 failed to 4. Every other conjunct held with the floor
    present, so the clause contributed nothing to the property and only pinned today's emptiness.
    FIXED in the shape finding 26 prescribes: the stand-down and its record are now driven
    unconditionally over a path that CANNOT exist, and the live row states the property while
    REPORTING which state it measured. Proven by using the feature: a real floor written, `run_all`
    exit 0, the report reading `unknown / RULING_NOT_SETTLED`, full suite 4342 passed 0 failed.
38. **THE PERMANENT GUARD CANNOT SEE THIS FAMILY, AND NOT FOR A FIXABLE REASON.**
    `scripts/check_first_use.py` drives SANCTIONED WRITERS, deliberately, because a mutation reaching
    past the writer would prove nothing. `.veldo/behavior_floor.py` writes nothing, ever, by design -
    a floor is AUTHORED, not emitted - so there is no writer to drive and no `MUTATIONS` entry to
    add. The guard's own documented limit 1 therefore still applies to floors. **OPEN, and its own
    item:** extend the guard to a family whose use is authoring an artifact, which means letting an
    entry declare a file to write and building its content through the module's own canonicalization.
    Deliberately not smuggled into this change.
39. **A READER WITH NO REPORTER QUOTED COVERAGE OVER THE RECORDS THAT HAPPENED TO PARSE.**
    `floor_report` dropped an unreadable floor with a bare `continue` and then counted floors, pins
    and surfaces - a coverage figure without the weakness that produced it, which is the one thing
    the report's own contract forbids, and no row covered it. The sibling `continue` in `check_floor`
    is correct because that path has a reporter; this one had none. FIXED: an `unreadable` list in
    the report shape, named on the page and in the stand-down reason, with a driven row over two
    floors where one is unparseable. Also fixed alongside: a pin with no `language` surfaced the
    string `None` in `unanalyzed_languages`.

### Found building W1 to W6, by driving my own declared falsifications (2026-08-12)
Every criterion of VELDO-0002 through VELDO-0007 was driven: the mutation applied to a fresh copy,
proven landed, the named row required to red, then reverted. It found four defects in my own work
that reading would not have, and two of them were checks that could not fail.

40. **TWO OF VELDO-0007's OWN CRITERIA WERE VACUOUS, AND ONLY DRIVING SHOWED IT.** The
    adopter-gate criterion accepted either INIT_FAILED or ADOPTER_GATE_RED, so deleting the
    gate-status check entirely left the suite green - the mutation that proved its teeth broke init
    before the gate was ever consulted. The fix is a second mutation that init accepts HAPPILY (an
    invalid starter plan inside the composed pack) which the adopter's own gate then refuses, so the
    failure is attributable to the nested gate alone. The vacuous-run criterion was worse: the
    NO_PACKS_COMPOSED guard lives inside `check()` and every row tested `composed_packs()` over a
    fixture instead, so nothing reached the guard at all. **A guard against an empty set that nothing
    drives is itself the vacuous shape it exists to prevent.** Fixed by injecting a composer seam, the
    way fleet.py's spawner and waiter are injected.
41. **AN ASSERTION CAN BE WRONG ABOUT THE CODE RATHER THAN THE REVERSE, AND THE CODE WINS.** Two
    rows I wrote asserted properties the system does not have. VELDO-0003's claimed the fleet loop
    refuses to spawn over a concluded queue; driving it showed the loop spawning, because
    `work_remains` is consulted only at a zero target - that is its documented drain-versus-backoff
    distinction. VELDO-0005's claimed no file may NAME a module, which correctly caught the item's own
    lay-down entry: /veldo:init must name a module in order to ship it, and naming is not consulting.
    Both replaced with the property that exists, both of which are STRONGER than what I first wrote.
42. **MY OWN TEST CODE CARRIED AN `or True` TAUTOLOGY AND AN UNREACHABLE BRANCH.** In VELDO-0005's
    suite, one row ended `... is False or True`, which is the exact shape a review caught in this
    repository once already; and its stand-down branch was unreachable by the default path, because
    the capability manifest lives INSIDE the directory the modules leg scans. The branch is reachable
    through the manifest parameter, which is how an adopter with a manifest elsewhere reaches it, so
    the row drives it that way rather than asserting nothing.
43. **THE CAPABILITY MANIFEST'S OWN HONESTY CHECK CORRECTED A SPEC I HAD ALREADY WRITTEN.**
    VELDO-0007 declared that its stage belongs in BOTH this repository's gate and the shipped
    template, so an adopter would inherit it. The existing capability-honesty check refused: the
    script does not ship, and an adopter does not publish packs, so a required slot in their gate
    would be a check they cannot run. The capability is `scope: repo-only` and the criterion is scoped
    to this repository. **A check that already existed was right and my spec was wrong**, which is the
    outcome this project should want most often.

44. **THE INSTALL-AND-RUN CHECK CAUGHT ITS FIRST REAL DEFECT WITHIN MINUTES OF EXISTING, AND IT WAS
    MINE.** Building VELDO-0008 I added `.veldo/version.py` to the init scaffolder's lay-down list, so
    init began DEMANDING that template. The composed pack did not carry it, init failed with "template
    missing", and every scaffolded repository was uninstallable - **the exact 1.0 defect, reintroduced,
    and caught in the same session that built the check for it.**
    THE CAUSE IS A PROPERTY WORTH KNOWING: the publisher derives the public tree from TRACKED files,
    so a brand-new organ that is not yet committed does not exist for an adopter, while this
    repository's own gate sees it perfectly. **An organ the scaffolder requires must be tracked, or the
    only person who cannot use it is the person installing it.** Staging the two files took the same
    pack from INIT_FAILED to a green adopter gate, which is the whole loop this item exists to close.
    Every organ landed before it (work_state, tasks, promises, declared, budget_state) passed only
    because they were already committed when the check first ran - so this would have shipped.

45. **THE REPORT-UNTIL-APPROVED POSTURE HAS ITS OWN VACUOUS SHAPE, AND VELDO-0010 HAD IT.** Both
    VELDO-0007 and VELDO-0010 hold a protected-path edit for approval and let the criterion REPORT
    until it lands. Driving VELDO-0010's showed the flaw: with ONE flag meaning "does the gate mention
    a version", both branches were satisfiable, so adding a bare marker to the gate reddened nothing.
    **A posture derived from the live tree can be flipped by the mutation it is supposed to catch.**
    The fix is two facts rather than one - the gate MENTIONS a producing version, and the gate WRITES
    the key - with the invariant that mentioning without stamping is red in EITHER posture. That
    catches the real failure, which is a half-done registration: a marker in the gate with no field in
    the record it stamps. VELDO-0007's AC5 is the same shape and is worth the same treatment when its
    approval lands.

### Found by the twelve independent reviews of PLAN-0018 (2026-08-12)
Twelve L2 reviews, one per item: 0 pass, 2 pass_with_notes, 10 FAIL. 13 blockers, 44 majors, 48
minors, and of 61 criteria 43 confirmed, 11 REFUTED and 7 unevidenced. The reviews drove the
declared falsifications rather than reading them, which is why they found what reading did not.

46. **USING THE REVIEW FEATURE REDDENED THE GATE, AND THREE REVIEWERS FOUND IT INDEPENDENTLY.**
    WARP-0727 AC1 asserted raw set equality between the entitlement domain, a GIT enumeration, and
    the validated corpus, a DISK enumeration. An author who has written a verdict artifact and not
    yet committed it is in the second and not the first, so **one uncommitted verdict was the only
    red in a 4529-assertion run** and every L2 reviewer turned the gate red by doing their job.
    Reported as VELDO-0002 F8, VELDO-0005 F8 and VELDO-0007 F10, each against a different item and
    none of them the item under review, which is what independent means.
    THE SUITE CONTRADICTED THE MODULE IT TESTS, IN WRITING. `verdict_corpus.divergence()` already
    computes the population as its `untracked` bucket and its docstring already says "Expected and
    not red: an author validating before committing is the normal flow." The assertion disagreed
    with the contract it was asserting over.
    FIXED by setting aside exactly that bucket and nothing else. **The narrowing is safe for a
    reason that had to be checked in the code rather than taken from the docstring:** `untracked` is
    `disk_set - set(direct)` where `direct` is an INDEPENDENT `git ls-files` read, not the
    difference between the two sets under test, so subtracting it cannot make the equality true by
    construction. It can only forgive what git itself says it is not tracking. The forgiven set is
    then pinned to that independent read in both directions and required to be disjoint from the
    domain, so no later edit can widen the forgiveness without reddening the row, and the three
    harmful legs are untouched: entitled_not_validated, contradiction and overclaimed all still
    required empty. Driven three ways: forgiving every validated path REDS, a domain that drops a
    tracked member REDS, and the real flow of committing the artifact stays green.
    A FOURTH DRIVE WAS DISCARDED AND IS RECORDED AS DISCARDED, because it reddened for the wrong
    reason: narrowing `corpus_member` with a literal `startswith('VELDO-9')` reddened the row while
    `contradiction` measured empty, and the literal-scope guard fired on the mutation's own
    digit-bearing string. **A mutation that reds the right row for the wrong reason is not evidence,
    and the honest move is to say so rather than count it.**
    THE GENERAL LESSON, WHICH IS THE ONE WORTH KEEPING: **a gate check that reddens when a feature
    is USED is not gating that feature, it is refusing it.** Same family as findings 26 and 39, in
    its fourth dress: an assertion over live state whose required answer is an empty set or an exact
    equality, invisible to code review, and visible the first time somebody uses the thing.

47. **THE RULE SHIPPED TO ADOPTERS AND NOT TO US, SO LOCALLY IT SURVIVED ONLY WHERE SOMEBODY
    REMEMBERED.** VELDO-0001 F3. The falsification prompt went into `engine/specs/TEMPLATE.md`, the
    copy an adopter installs, and NOT into `specs/TEMPLATE.md`, which is the file `README.md` tells
    an author in this repository to copy. The local template additionally told them in writing that
    "Nothing checks this" **after `validate.py` had begun refusing it**, so the one document an
    author starts from stated the opposite of the rule. `engine/specs/TEMPLATE-standing.md`, offered
    by the spec skills as the alternative, declared acceptance criteria and no falsification field at
    all. No assertion in the repository read either local file.
    WHY IT COULD NEVER BE CAUGHT, and why the fix is not a sync check:
    `scripts/check_template_sync.sh` excepts `specs/TEMPLATE.md` PERMANENTLY as per-repo, and
    correctly, because the two copies legitimately differ - the local one carries the four-things
    block the shipped one does not. **Byte-identity was the wrong assertion, so it was waived
    forever, and the waiver is where the divergence lived.** Fixed by asserting the PROPERTY both
    copies must have, over every template the repository offers an author, DERIVED by glob rather
    than hand-listed so a third template cannot arrive unchecked. The glob immediately caught
    `TEMPLATE-standing.md`, which I had not fixed.
48. **I REPRODUCED THE DEFECT I WAS FIXING, INSIDE THE FIX, AND ONLY DRIVING CAUGHT IT.** The first
    version of finding 47's check tested `field in text`. It stayed GREEN with the field deleted from
    the template, **because the comment explaining the field still contains the field's name.** That
    is exactly VELDO-0010 F1 - a substring scan used to prove a presence - committed by the person
    who had read that finding an hour earlier, in the check written to close a different instance of
    it. Fixed by requiring the field as an uncommented KEY on its own line, with an additive control
    that a template carrying the name only inside a comment is refused.
    **THE LESSON IS ABOUT THE METHOD AND NOT ABOUT THE MISTAKE. Reading a finding does not
    inoculate you against it.** The reason this one cost minutes instead of shipping is that the
    mutation was driven rather than the check being read, and driving is the only step in this
    process that would have told me. Third recorded appearance of the substring-scan family, after
    VELDO-0010 F1 and VELDO-0008 F1's `version(ROOT)[0] in stdout`, which could not fail in the one
    state it existed to cover.

49. **TWO WORKERS COULD HOLD ONE TASK, AND A RELEASE BY ONE SILENTLY FREED THE OTHER.** VELDO-0003
    F1, a real defect and not a weak check. `tasks.py` validated no id FORMAT - its
    `TASK_ID_PREFIX` constant was declared and never used - and `.veldo/claim.py:_safe()` maps every
    character outside `[A-Za-z0-9._-]` to `_`, so `TASK_0001` and `TASK/0001` are **two distinct
    tasks to the contract and ONE file to the ledger.** Both harms measured on this tree: a live
    claim on one refused the other, producing the spec's own named risk of a task nobody can take;
    and worker-a holding both, then releasing only one, freed a task worker-a was still working,
    which worker-b was then GRANTED.
    FIXED WHERE IT BELONGS, which is the part worth keeping: the refusal lives in the one place that
    knows the id-to-path mapping, so **no caller can route around it**, rather than in a validator
    that every future caller would have to remember to consult. An id the ledger cannot store
    faithfully raises out of the ledger rather than becoming a fifth claim answer, because a
    malformed key is a bug to surface and not a claimant to arbitrate between.
    The reviewer's own example could not tell the namespace rule from the ledger rule, since
    `TASK_0001` violates both. A second pair carrying the `TASK-` prefix on both sides isolates them.
50. **A VERSION COULD BE INVENTED TWICE OVER, AND ONE OF THE TWO WAS A SUBSTRING SCAN AGAIN.**
    VELDO-0008 F1 and F2. An empty or non-version declaration was answered as this installation's
    identity with **exit 0 and a green gate**: with every manifest declaring `TBD` the CLI printed
    `TBD (from .claude-plugin/marketplace.json)`, and with `""` it printed a leading space and
    exited zero, defeating AC4's stated guarantee that a script capturing the output can never
    silently receive a guess. Separately the canonical read took `plugins[0]` POSITIONALLY and never
    matched the entry named veldo, so a co-hosted plugin listed first made the reader answer a
    version veldo does not declare **while naming both veldo packs as the ones disagreeing, which is
    the inverse of the diagnosis the criterion promises.**
    Now shape-checked where it is read, read BY IDENTITY, a top-level `version` beside the list is a
    schema version that does not shadow the entry, and two entries claiming the name is an
    AMBIGUITY that refuses rather than a tie-break to guess at.
    THE ROW THAT WAS SUPPOSED TO CATCH F1 WAS `version(ROOT)[0] in stdout`, **which cannot fail when
    the declaration is the empty string** - the one state it existed to cover. Second instance of the
    substring-scan family in this round, and see finding 48 for the third, which was mine.
51. **THE FIX SHAPE FOR A LIVE-STATE PIN, WHICH IS THE PART THAT GENERALISES.** VELDO-0005 F1. The
    item claimed it gates nothing and gated the whole repository: `_dc_live['unresolved'] == []` and
    `not (ROOT / 'design').is_dir()`, both over live state, both inside a required unit stage, and
    the suite docstring nine lines above said no row pins today's manifest. One correct declaration
    about a non-Claude pack root reddened the gate.
    **The wrong fix is a narrower pin. The right fix is to assert the PROPERTY the pin was standing
    in for:** NO ACCUSATION THIS ORGAN MAKES ABOUT THIS REPOSITORY IS FALSE, with every accused
    segment stat'ed independently under every root the tree declares, and the row saying in its own
    text that it requires none of the counts to be any particular value. A real stale declaration
    still reds it; growth does not. The design leg got the same treatment: instead of pinning the
    ABSENCE of a directory, it asserts that the finding kinds the module DECLARES are exactly the
    kinds a driven report EMITS, so naming a third kind without building its leg reds the row.
    AND THE STATED REASON HAD BEEN FALSE. "This repository has no design/ directory at all" was
    wrong: `docs/design/` holds 19 documents, one of which is the design PLAN-0018 observation 18
    names as having died with nothing noticing - the observation that produced this very work item.
    **Narrowing scope is legitimate; a false reason with a green assertion certifying it is not.**
52. **A HUMAN RULING WAS FORGEABLE, AND WORSE, TRANSFERABLE.** VELDO-0012 F1, the most serious
    blocker of the round. The behaviour floor exists so the machine may only DRAFT what the code does
    today while a human rules on it. Three fields in that chain were read at face value: the
    settlement's `bound_digest` (typed, never recomputed), the settlement's own `chosen` key, and a
    `request_id` checked only for schema, id, touchpoint and status. So a `ruled` disposition was
    reachable **with no human act at all, using only files the machine can author.**
    THE TRANSFER LEG IS THE ONE THAT SHOULD FRIGHTEN US: a settlement could name a REAL accepted
    request that a human had genuinely settled **about a different artifact**, and it ruled this pin.
    The comparison that closes it was free all along - the shipped receipt path already sets
    `bound_digest` FROM the request's own `bound_artifact.digest` - so nothing had to be built, only
    compared. Now every field in the join is compared against something else and none is trusted.
53. **A PROXY THAT COULD NOT SEE WHAT IT CLAIMED, AND THE THING ONLY DRIVING FOUND.** VELDO-0007 F1.
    AC4's headline - IT TOUCHES NOTHING OUTSIDE A TEMPORARY DIRECTORY - was proven with `git status
    --porcelain` on this repository, which is blind to **every path outside the repository and every
    git-ignored path inside it**, and the companion no-detached-process claim was an AST scan over
    identifiers, blind to keyword arguments. Three mutations the spec's own falsified_by describes
    each left the suite at 47 passed, 0 failed.
    Replaced with an observation instead of a proxy: a recursive inventory of path, size,
    modification time and sha256, over the repository under check AND over the process's own HOME,
    across a sandboxed run and an in-process run.
    **THE MTIME IS IN THERE BECAUSE DRIVING PUT IT THERE.** A content-only inventory was tried first
    and the reviewer's second mutation was INVISIBLE to it, because that mutation writes the same
    bytes on every run. Reading the mutation would never have shown this; running it did.
54. **A UNIVERSAL CLAIM ASSERTED FOR ONE FIFTH OF ITS DOMAIN.** VELDO-0004 F1. AC4 promises every
    CONTRADICTED settlement carries the predicate, the target read and what was found - the property
    the whole item exists for, since the 2026-08-10 audit had 5 of 15 accusations overturned on
    challenge. It was asserted for exactly one of five mechanical predicates, and `path_absent` did
    not appear once in the suite fragment, so evidence could be stripped from four contradiction
    paths with the suite fully green. F2 was worse in kind: `promise_report` raised an uncaught
    `TypeError` on an integer needle, taking the ENTIRE report down with it, because
    `parse_yamlish` coerces a digit scalar to int and `needle: 200` is the obvious way to claim a
    document says 200. The module has a six-name refusal taxonomy precisely so that class is named
    rather than thrown. Suite went from 53 rows to 82.
55. **THE NEWLY REQUIRED PACKAGING SLOT IS LOAD SENSITIVE, AND A FLAKY REQUIRED CHECK IS WORSE THAN A
    MISSING ONE.** Found by using it, not by reading it. VELDO-0007's stage composes seven packs and
    runs each scaffolded repository's OWN full gate, with a 900 second per-subprocess timeout. During
    the remediation round, with nine agents each running their own gates on the same machine, two of
    its rows went red in a run where the same suite passed 28/0 standalone moments later and
    `python3 scripts/check_install_and_run.py` passed all seven packs with every adopter gate GREEN.
    **CORRECTION, and the correction is the more useful half of this entry.** This first read "the
    cause is contention against that timeout." That was inference from timing, not evidence, and it
    was wrong. The run that DID reach the stage recorded the actual failure, in VELDO-0010's copy:
    `init said: /usr/bin/python3: can't open file '.../public/packs/opencode/.veldo/init_scaffold.py':
    [Errno 2] No such file or directory`. **The composed pack was missing the scaffolder.** Not a
    timeout: an incomplete pack. The publisher composes from `git ls-files`, so what ships is a
    function of the git INDEX at publication time, and concurrent work against that index is the
    mechanism. Finding 58 is the latent parse defect in the same function, and finding 59 is the index
    state that reproduced the symptom deterministically.
    WHY I REACHED FOR THE WRONG CAUSE, which is the part worth keeping: the row I was looking at
    prints nothing but its own name, so there was nothing to read, and **I filled the gap with a
    plausible story instead of going to find the run that had recorded something.** The reporting
    defect below is not a cosmetic complaint; it is what made a wrong diagnosis the path of least
    resistance.
    **This matters because the slot became REQUIRED today.** A required check that reddens for
    reasons unrelated to the change teaches people to re-run until green, and a gate people re-run
    until green has stopped being a gate. It is also the exact shape this plan warns about from the
    other direction: a check that fails when the repository is being USED.
    TWO THINGS TO FIX, both recorded rather than done, because both are design choices rather than
    typos: the timeout should be a declared budget the stage REPORTS against rather than a silent
    900, and the two failing rows print nothing but their own names, so a reader cannot tell a
    timeout from a genuinely red adopter gate. The CHECK already quotes the adopter's gate tail on
    failure; the SUITE ROW throws that away by reducing it to a boolean.

56. **FINDING 45's OWN FIX WAS STILL TWO READS OF ONE STRING, AND A COMMENT SATISFIED BOTH.** The two
    facts finding 45 prescribed were both substring scans over `scripts/verify.sh`'s text: `veldo_version`
    in it, and `"veldo_version":` in it. The second implies the first, so they are not independent, and
    neither is about the gate. An independent reviewer of VELDO-0010 deleted the field from the printf in
    BOTH gates and from `run_scope.verify_stamp_payload`, left one line reading
    `# TODO(VELDO-0010): the record still owes a "veldo_version": field`, and measured suite 27 at 44
    passed 0 failed and the FULL selftest at 4530 passed 0 failed, byte-identical to the baseline, while
    the record the gate writes lost the field entirely. **A substring scan used to prove a PRESENCE is
    the same defect as one used to prove an ABSENCE, which this ledger already records twice for
    absences.** The fix is to RUN THE ARTIFACT: each gate is copied into a throwaway tree with
    `.veldo/version.py`, executed twice (canonical declaration present, and absent), and the
    `.veldo/last_verify` it produced is PARSED. Mentioning versus stamping is now genuinely two facts,
    because one reads the source text and the other reads a file the source wrote. The general rule for a
    PROTECTED path: it cannot be proven by reading it, only by running it, precisely because the suite is
    not allowed to change it. VELDO-0007's AC5 inherits this, not just finding 45's version of it.
57. **AND THE MEASUREMENT PAID FOR ITSELF ON THE FIRST RUN.** The same review found the gate stamping
    `"veldo_version":"veldo"` in any tree that cannot read a version, because the derivation took the
    first word of `version.py`'s stdout and `version.py` prints its refusal there for all three causes
    it models. A fabricated identity in the record where it would be most believed, shipped identically
    to adopters. That defect existed for an hour under a recorded approval with a green gate and a row
    asserting the exact opposite property - because the row grepped the shell source for the string
    `VERSION_JSON=null` instead of reading a record. **A criterion that names a runtime property and
    checks it in source text is unevidenced, however precisely it is worded.**
    RENUMBERED ON MERGE: VELDO-0010's remediation wrote these as 46 and 47, which findings 46, 47 and
    48 above had already taken in the same round. Two numbers for one finding is how a ledger stops
    being citable, so they are 56 and 57 and the originals stand.

58. **THE SOLE WRITER OF WHAT ADOPTERS RECEIVE PARSED GIT FOR A DELIMITER IT NEVER ASKED FOR, AND HAD
    WORKED BY ACCIDENT SINCE IT WAS WRITTEN.** `scripts/publish.py:tracked_files()` ran `git ls-files`
    with NO `-z` and split the newline-delimited result on the literal two characters `\n0` - which is
    `\0` with a typo - and then on whitespace. Driven in a throwaway repository: a tracked
    `a file with spaces.md` comes back as the four fragments `a`, `file`, `spaces.md`, `with`, and the
    real path is GONE. A top-level path sorting at `0` truncates the list, dropping everything after it
    in git's own order from every composed pack.
    IT HAS NEVER FIRED. Measured: 1386 tracked paths here, none with a space, none starting with `0`,
    so the old parse and the correct one return identical sets today. **A defect that cannot fire in
    the only tree anybody tests is not a small defect, it is an invisible one**, and its blast radius
    is an incomplete pack that installs and then breaks in a stranger's tree - the class VELDO-0007
    exists to catch and the class that shipped 1.0 uninstallable.
    `scripts/migrate_to_veldo.py` and `scripts/rename_migration.py` already did it correctly, with
    `-z` and a NUL split. **Three implementations of one operation, and the one that differed was the
    one that decides what ships.** Fixed to match the other two.
59. **AN UNMERGED INDEX MAKES `git ls-files` ANSWER WRONGLY, AND SEVERAL GATE STAGES TAKE IT AS TRUTH.**
    Reproduced deterministically, by me, on the live tree: with `.veldo/version.py` left in the `UU`
    state after a three-way merge whose markers I had resolved in the working tree but never staged,
    `git ls-files .veldo/version.py` prints the path **THREE times** - one entry per merge stage. The
    gate went RED on three rows including WARP-0711's file-set equality against `ls-files`. Staging the
    resolution took the count to 1.
    **A conflicted merge is a completely ordinary state for a developer to be in**, and it is a state
    in which the publisher's view of what ships, the lint stage's file set, and the verdict domain are
    all quietly wrong. This is the same family as finding 46 from the opposite direction: there, a gate
    reddened because an author had not yet committed; here, several stages silently read a different
    set because a merge was half finished.
    RECORDED, NOT FIXED, and the reason is honest rather than convenient: the right fix is for every
    reader of the tracked set to refuse an unmerged index by name instead of consuming it, and that is
    one enumeration to build once rather than four patches. It belongs with VELDO-DEC-0002's
    one-enumeration question rather than being guessed at here.
60. **I WROTE A SECOND CHECK WITH NO TEETH WHILE FIXING THE FIRST ONE, IN THE SAME HOUR.** Finding 48
    was a substring scan that could not fail. Finding 58's guard was worse: its fixture row compared a
    value **against itself** (`_iar_want == sorted(p for p in _iar_zf.split("\0") if p)`) and computed
    the old parse inline, so it never called the publisher at all, while its live row asked about a tree
    that cannot exhibit the defect. Restoring the broken parse left the suite at 56 passed, 0 failed.
    Fixed by giving `tracked_files` a `root` parameter and asking the publisher itself about the
    fixture: the mutation now reds exactly one named row.
    **TWO LESSONS, and the second is the one I keep relearning.** A property that only a differently
    shaped tree can exhibit needs a SEAM to be asked about that tree, so the seam is part of the fix
    and not a convenience. And driving the mutation is the only step in this process that catches
    this class - it caught me twice tonight, on findings 48 and 60, both times within minutes, both
    times after I had just finished writing about the same mistake.

61. **THE FLAGSHIP COMMAND OF THIS PLAN CRASHES IN EVERY ADOPTER TREE, AND THE INSTALL CHECK CANNOT
    SEE IT.** Reported out of footprint by VELDO-0002's remediation and driven here to be sure.
    `.veldo/init_scaffold.py` lays down 25 `.veldo` modules including `work_state.py` and
    `verdict_corpus.py`, and NOT `executor.py`, `runlog.py` or `claim.py`. `work_state.py` loads
    `executor` for `PASSING_VERDICTS` and `runlog` for the run registry. MEASURED: a fixture carrying
    exactly the 25 modules init lays down answers
    `python3 .veldo/work_state.py report` with exit 1 and
    `FileNotFoundError: [Errno 2] No such file or directory: '.veldo/executor.py'`.
    So O1's whole promise - "ask Veldo what is done after a session died, and it answers without
    anyone grepping worktrees" - is a traceback for everybody who installs it. **It was already true
    before this round; the round made it worse by adding the `executor` dependency**, which is the
    dependency that closed the false-DONE defect, so the two are not separable by reverting.
    WHY VELDO-0007 DOES NOT CATCH IT, which is the more interesting half: the install-and-run stage
    requires the adopter's own GATE to exit zero, and the adopter's gate does not invoke
    `work_state.py`. **An install check that proves the gate runs does not prove the product runs.**
    Every organ init lays down that no gate stage invokes is in this blind spot, and the blind spot is
    derivable rather than a matter of opinion: it is the laid-down set minus the set the shipped gate
    reaches.
    NOT FIXED, and this one genuinely needs a decision rather than a patch, because the two repairs
    have different products. Either init ships `executor.py` and `runlog.py`, which widens what every
    adopter receives and needs its own look at whether an adopter is meant to have the loop at all; or
    `work_state` degrades honestly when a sibling is absent, standing the affected half down by name
    the way it already stands the run half down when no registry exists. The second matches this
    project's own posture and cannot express "which verdicts count as passing" without the executor, so
    it is probably both. Raised rather than guessed at.

62. **A CORRECT FIX BROKE ANOTHER ITEM'S FIXTURE, AND THE FIXTURE WAS THE THING THAT WAS WRONG.**
    Caught only by gating the nine patches TOGETHER rather than trusting nine separately green copies.
    VELDO-0006's AC4 control built a proof bundle whose verdict carried a schema and NO verdict field,
    and asserted `concluded_artifacts == 1`. That passed while VELDO-0002's `concluded()` only checked
    that a verdict FILE existed. Once 0002's remediation made it read what the verdict SAYS, the same
    fixture measured 0 and two rows went red.
    **Neither patch was wrong and the tightening is exactly what was wanted.** The row's subject is a
    real concluded bundle producing a real count, so the fixture was representing a state that had
    never actually been concluded; it now writes `"verdict": "pass"`. Measured both ways at
    integration: no verdict value gives 0, a passing verdict gives 1.
    THE PROCESS LESSON, which is why this is recorded rather than quietly patched: each of the nine
    remediation copies was GREEN on its own and the interaction existed only in the union.
    `budget_state.survival()` consumes VELDO-0002's concluded-artifact semantics, so a change to what
    "done" means necessarily moves it. **Nine green copies are not a green repository, and the only
    thing that found this was one gate over all of them at once.**

63. **THE FIX SHAPE FOR A POPULATION PIN, APPLIED TO THE ONE THAT WAS STILL LIVE.** VELDO-0003 AC5
    asserted `_ts_loaders == []` over a glob of `.veldo/*.py` and `scripts/*.py`. DRIVEN before the
    fix: adding `_load("tasks", ".veldo/tasks.py")` to `.veldo/work.py`, exactly how that file already
    loads frontier.py and claim.py, took the suite to 66 passed 1 failed on that row alone. **So the
    advisory consumers this organ EXISTS to serve were the thing that reddened the required unit
    stage.** Two earlier attempts to drive it stayed green and that is worth recording: the detector
    only inspects DIRECT `Constant` arguments, so a computed path or a prefixed module name is
    invisible to it, and my first two mutations used both. A detector nobody has driven is a detector
    whose reach is unknown.
    FIXED by changing the DOMAIN, not the comparison, per VELDO-DEC-0002: the subject is now the
    GATE'S OWN STAGES, derived from validate.run_all's module loads plus the stage scripts verify.sh
    names. A gate stage loading this organ is a DEFECT and its set may be required empty forever; the
    set of FILES that load it is a POPULATION a legitimate use joins. Driven both ways: the advisory
    consumer that used to red is now green, and a load added to `validate.run_all` reds the named row.
64. **THE REPAIR FOR A CRASH INTRODUCED A CRASH, AND ONLY A REAL FIXTURE FOUND IT.** Finding 61's fix
    gives `work_state` an unanswerable state when the organ declaring the passing verdicts is absent.
    Setting `state = None` then hit `rep["counts"][state] += 1` and raised `KeyError: None` out of the
    CLI. **The empty fixture I had been checking against never reached that line**, because it has no
    items; the crash needed one real proof bundle to appear. Fixed with an `unanswerable` bucket
    counted in no state.
    AND THE FIRST VERSION RECORDED THE STAND-DOWN WITHOUT REPORTING IT. The flag was set in the report
    dict and `report_lines` never printed it, so an operator saw three zeros that read exactly like a
    measurement. That is VELDO-0001 F2's defect in a new place. The stand-down now leads the report and
    names how many items are unanswerable.
    BOTH REPAIRS DMITRY DIRECTED ARE DONE AND DRIVEN: init lays down `executor.py` and `runlog.py`
    (both already tracked, which finding 44 requires), and the reader names an absent organ instead of
    dying. Measured on a fixture carrying exactly what init lays down: exit 0 where it was exit 1, and
    with `executor.py` removed the first line of the report is the stand-down rather than a zero.
65. **THE CHECK THAT REFUSES AN UNREVIEWED DECISION NEVER READS THE REVIEW'S VERDICT.** Found by the
    round-two reviewer of VELDO-DEC-0001. `decided_requires_review` counts bound reviews against the
    tier's requirement and never looks at `disposition`. **So a review whose disposition is `refuted`
    satisfies it, and the gate goes GREEN on a decision its own adversarial review rejects.** The
    reviewer's words: nothing mechanical stops this record, only the owner will.
    This is the same family as every other finding here, in the machinery built to enforce the family:
    a check whose subject is the EXISTENCE of an artifact rather than what the artifact SAYS. Ledger
    finding 49 is the identical shape in `work_state.concluded`, fixed the same day. **The gate that
    caught me twice tonight has the defect it caught me for.** Recorded, not fixed: the fix is a
    contract question about which dispositions may support a decided record, and it belongs with
    VELDO-DEC-0001 rather than being guessed at.
66. **ROUND TWO REFUTED BOTH REFRAMES, AND THE SECOND FAILURE WAS TAKING A PRESCRIPTION'S NAME WITHOUT
    ITS SUBSTANCE.** Both version-3 records came back `reframe` again.
    THE CHOSEN OPTION FOR DEC-0001 DOES NOT WORK, and the reviewer proved it by BUILDING it: mutation
    applied to an in-process copy of `validate_checks.py`, 0.0024 s per drive. **A module COPY is not
    the object the shipped assertion runs against** - fragment 17 drives `V._VC` deliberately, "the
    same object the validator uses rather than a second copy with test wiring" - so the control passes
    while every shipped row stays green. That reproduces finding 40's defect BY DEFAULT inside the
    mechanism meant to prevent it. Reaching the real row needs rebinding shared.py's single namespace,
    which leaks into every later fragment.
    AND THE REWRITE WAS NOT FAITHFUL. Measured by diff: the version-3 record is version 2 plus two
    blocks. All four prescribed assumption repairs were skipped, the assumption set is byte-identical
    to the refuted version, three of four missing options were dropped with no reason recorded, and the
    adopted option's own "under an injected seam" requirement was dropped in the copying. **The
    artifacts kept the refuted substance while the record took the new name**, including PLAN-0018's
    W11 title and specs/VELDO-0014, which still build the discriminator that was refuted.
    A COUNT WITHOUT ITS METHOD IS NOT A MEASUREMENT. The reviewer said my criterion census reproduces
    under no method; it reproduces exactly under mine (adjacency: 6 one, 80 none, 141 many, median 6,
    max 33) and theirs gives 10/81/136 under a looser reading. Both readings support the same
    conclusion. **The error was quoting the count without stating the method that produced it**, which
    is this ledger's own disease in a smaller size.

67. **THE CRASH'S TWIN SURVIVED BECAUSE ONLY ONE HALF WAS FIXED.** VELDO-0009 F2.
    `installed_version` called `data.get` with no isinstance guard, so a stamp file containing `[]`,
    `null`, `5` or a bare JSON string raised AttributeError out of the reader, out of `drift()` and out
    of the `--drift` CLI. That refutes AC5, which claims a TOTAL property over "a file at the stamp path
    that PARSES but is not a veldo.installed/v1 record". **The identical defect in the same file's
    provenance reader was closed by VELDO-0010's remediation and this one was not**, because no agent
    was assigned to VELDO-0009: it was the one FAIL verdict carrying no blocker, so the round that fixed
    twelve items skipped it. A remediation queue built from BLOCKERS leaves the refuted criteria of any
    item that had none.
    FIXED with a named cause carrying the type. Driven over all four non-object shapes, plus the valid
    record as a control. AND THE FIRST VERSION OF THE ASSERTION WAS WEAKER THAN IT LOOKED: with the
    guard removed the raise escaped the loop, the block wrapper reddened its own row, and six rows below
    vanished from the run. So the evidence was "some row went red" plus a shorter run, which is exactly
    what a mutation that DELETES coverage produces. The read is now captured per shape, and removing the
    guard reds the four NAMED rows with nothing lost.
68. **A PROOF BUNDLE CLAIMED FOUR DRIVEN FALSIFICATIONS UNDER EVERY CRITERION AND THE FILE RECORDS FOUR
    IN TOTAL.** VELDO-0009 F4. All five criteria of `proof/VELDO-0009/manifest.json` carried the
    identical string "AC<n>: 4 of 4 declared falsification(s) re-driven in this pass and each reddened
    its own row". The cited file records four mutations for the ITEM: one for AC1, one for AC2, two for
    AC3, and **none at all for AC4 or AC5**. So the two criteria with no driven record were the two
    claiming the strongest evidence, and one of them, AC5, is the criterion the review REFUTED, for the
    defect finding 67 just fixed.
    Corrected to what the file records, per criterion, including the two that say plainly that nothing
    was driven. **A bundle may not borrow its reviewer's work as its own evidence:** the independent
    review did drive all five and its verdict records that, which is a different artifact making a
    different claim on its own authority.
    WHY THIS IS THE CLASS THAT MATTERS FOR THE BOOK. A per-criterion evidence string is the exact
    surface a reader trusts when they audit an item, and this one was generated identically for five
    criteria rather than derived per criterion. Same family as the 2026-08-10 audit's 64 false claims
    across 8 documents: prose asserting coverage that the artifact behind it does not support.

69. **THE GATE RECORD NAMES A COMMIT AND VERIFIES A WORKING TREE, AND NOTHING SAYS WHICH.** Noticed in
    passing on 2026-08-13 and RECORDED RATHER THAN FIXED, per the standing rule, because no user gets a
    wrong answer from it: the gate really did pass over real content.
    `scripts/verify.sh` stamps `.veldo/last_verify` with `commit` from `git rev-parse HEAD` at run time,
    and the stamp's key set is exactly `at, checks_na, checks_run, commit, status, veldo_version`. It
    carries NO field for whether the working tree was clean, and the gate never asks: measured, there is
    not one `git status --porcelain` or equivalent in the script.
    So a reader of `{"commit": "c771092", "status": "green"}` concludes that c771092 passed. What passed
    was c771092 PLUS whatever was uncommitted, which through the whole of 2026-08-12 and 2026-08-13 was
    substantial - the record at the moment this was found described a run over c771092 plus 21 modified
    files. **Gate-then-commit is the correct order and it makes this record lag by one commit every
    time**, so the stamp systematically names a state it did not verify.
    WHY IT IS THE FAMILY THIS LEDGER KEEPS RECORDING: a record whose SUBJECT is not what it appears to
    name. Findings 46, 56 and 68 are the same shape in three other artifacts. The cheap repair is one
    more field, the dirty-path list or a digest of the verified tree, so the record says what it checked
    rather than where it was standing. That is a change to a PROTECTED path and to the shipped stamp
    contract, so it needed Dmitry rather than a decision taken at one in the morning.
    **FIXED 2026-08-13 under his recorded approval**, `proof/WARP-0727/approval-dmitry-finding-69.json`,
    granted twice: "Change verify, it's fine, I was wrong about it" and then "Finding 69, yes".
    HE CHALLENGED THE PREMISE FIRST AND WAS RIGHT IN PRINCIPLE: he asked why verify.sh needed touching
    when organs had been split out precisely so the big file would not be. Checked rather than defended.
    verify.sh is 183 lines; the 1000-line files are validate.py and validate_checks.py; the split did
    protect them and this touches neither. But verify.sh writes the stamp itself in shell at one printf
    and `run_scope.verify_stamp_payload` has no production caller by design, so the field could not go
    anywhere else without a SECOND file describing one gate run. **One command settled which of us was
    right about this file, and asking it was cheaper than either of us arguing.**
    The stamp now carries `tree`: "clean", a count of dirty paths, or null when git cannot answer, since
    an unanswered question and a clean tree invite opposite conclusions. A COUNT rather than the paths,
    because a filename can carry anything and this record is machine-read. The first thing it reported
    was the truth about its own run: `"tree":"6 dirty path(s)"`.
    THE COUPLING WORKED AGAIN, EXACTLY AS VELDO-0010 SAID IT WOULD. Adding the field to the gate reddened
    the shipped assertion that `run_scope`'s declared key set EQUALS verify.sh's own printf keys, and it
    stayed red until the payload carried it too. Second field to prove that coupling by breaking it.
    AND THE REPOSITORY CAUGHT ME AGAIN: my first approval record invented its own shape and
    `validate.py` refused it by name for five missing fields against the real `veldo.approval/v1`
    contract. Rewritten to the contract. **Third time in two days that this project's own machinery was
    right and I was wrong**, after the capability-honesty check refusing a spec of mine and the
    decided-requires-review gate refusing a decision I had already recorded.
    AND ONE MORE, ABOUT HOW THIS ENTRY ALMOST DID NOT EXIST. The commit that landed the fix was written
    with a script that ALSO meant to update this entry; the text match failed, the script raised, and the
    commit went through anyway. **So for one commit the code said fixed and the ledger said not fixed.**
    A compound step whose parts can fail independently needs its failure to stop the part that follows,
    and `&&` between them would have been enough.

70. **FINDING 65 FIXED UNDER DMITRY'S DECISION: THE GATE NOW READS THE REVIEW'S VERDICT, AND THE OWNER
    CAN OVERRIDE ON THE RECORD.** He decided this on 2026-08-13: "agree with review or explicit
    override".
    THE DEFECT: `decided_requires_review` counted that a bound review EXISTED and never read its
    `disposition`, so a review whose verdict is `refuted` satisfied the tier's requirement and the gate
    went GREEN on a decision its own adversarial review rejects. Found by the round-two reviewer of
    VELDO-DEC-0001, whose words were "nothing mechanical stops this record; only the owner will" - and
    it was right, because I had to revert both records by hand.
    THE SHAPE, THIRD APPEARANCE: a check whose subject is the EXISTENCE of an artifact rather than what
    the artifact SAYS. Ledger 49 was `work_state` calling an item done because a verdict FILE existed;
    ledger 68 was a bundle claiming evidence its own file does not carry; this is the same defect inside
    the machinery built to enforce against exactly that class.
    THE FIX, and the second half is his rather than mine. `SUPPORTING_DISPOSITIONS = {"defensible"}` is
    ONE enumeration so the gate and its refusal message cannot disagree. `reframe` is deliberately NOT
    supporting: it says the framing did not survive, and the honest response is a new version of the
    record, which makes that review stale by construction - accepting it would make a version bump
    cosmetic, which is precisely what the same reviewer caught me doing. **And clean-only would have
    DEADLOCKED us, measured: both records went to attack twice on 2026-08-12 and came back `reframe`
    both times.** So a `review_override` block lets him decide anyway, naming the review, himself and
    the reason. He keeps the authority; what changes is that overriding is an ARTIFACT rather than a
    silence.
    THE OVERRIDE IS ITSELF REFUSED WHEN IT LIES. It must name a review that is actually bound to the
    decision, and that review's disposition must NOT already support the record: overriding a review
    that agrees with you records an override that did not happen.
    **AND THE FIRST VERSION OF THAT CHECK WAS UNREACHABLE, found by driving all six cases rather than
    the two obvious ones.** It validated the override only when the supporting count was INSUFFICIENT,
    so a spurious override on a record that already passed was never examined - the misleading-record
    class, inside the check written to refuse it. The override is now validated whenever it is present.
    Six rows pin all of it; reverting to existence-counting reds the two that name it.

71. **A SHIPPED WRITER COULD DESTROY THE FILE THAT DECLARES WHICH FILES ARE PROTECTED.** The most
    serious defect found in this project's remediation, found by the independent review WARP-1402 had
    never had, and REPRODUCED here before anything was changed.
    MEASURED. A spec whose `id:` is `../policy` is accepted by `validate.check_spec` with ZERO errors.
    Run the shipped writer on it and `.veldo/policy.yaml` goes from **3977 bytes to 848**, replaced by an
    estimate record, with no `replace` flag and no refusal. **That file declares `protected_paths` and
    the risk tiers, so the writer could delete the policy that governs the writer.** Done in a throwaway
    copy on purpose; the live tree was never touched.
    THE CAUSE IS MUNDANE AND THE SHAPE IS FAMILIAR: `write_record` did
    `d / ("%s.yaml" % rec["spec"])`, and `spec` was validated only as a non-empty string. **This is
    ledger finding 49's family - an id used as a path without being checked as one - and we fixed the
    same class one layer down on 2026-08-12** when two task ids were found to collapse into one claim
    record. That fix produced `claim.unit_id_problem`, the ONE definition of an id that cannot be stored
    faithfully. This writer did not use it. **A rule we already own, in a module that did not ask for
    it.**
    AND THE OVERWRITE GUARD DID NOT FAIL, IT WAS ASKED TOO EARLY. `write_record` already refused to
    overwrite an existing record. The guard ran `p.exists()` BEFORE `d.mkdir()`, so for
    `.veldo/estimates/../policy.yaml` it asked about a path that could not resolve yet and got False;
    the write then ran after the mkdir, when the same path resolved perfectly. **A guard that is correct
    and consulted at the wrong moment is not a guard**, and it is a far quieter failure than a missing
    one, because the code reads as protected.
    FIXED both halves: the id is refused before it becomes a path, by delegation to the ledger's rule
    rather than a second copy of it, and the directory is created before the existence question.
    Four rows pin it. THE DRIVING TAUGHT ME SOMETHING ABOUT MY OWN ROWS: deleting the id rule reds the
    row that requires the refusal to NAME the id, and does NOT red the row that requires the victim file
    to survive - because with the ordering fixed, the overwrite guard now catches the traversal too.
    That is defence in depth working, and it means the two rows attribute correctly: one says the file
    lived, the other says WHICH rule saved it. A single row asserting only "it was refused" would have
    been satisfiable by either and attributable to neither.
    STILL OPEN AND RECORDED RATHER THAN FIXED: `validate.check_spec` accepts `id: ../policy` with zero
    errors. The writer is now safe, so no wrong answer is reachable through it, but a spec id that is a
    traversal is wrong on its own terms and the validator should say so. That touches the front-matter
    contract over 214 specs, so it is a change to ask for rather than to make at six in the morning.

72. **I WROTE A BRIEF USING A SEVERITY VOCABULARY THE VERDICT CONTRACT DOES NOT ACCEPT, AND AN AGENT
    HAD ALREADY FLAGGED THAT EXACT MISMATCH.** The six estimation verdicts landed and `validate.py`
    returned 53 problems: "list-shaped findings entries need severity blocking|note and text". I had
    instructed all six reviewers to use `severity_l2` with `blocker`, `major`, `minor` - and nothing
    else - because that is what the L2 review template says and what the twelve earlier verdicts used.
    The VALIDATOR requires `severity` from `blocking|note`.
    **THE MISMATCH WAS ALREADY ON RECORD.** A remediation agent reported it hours earlier and correctly
    declined to fix it: "the L2 template's blocker|major|minor against validate.py's blocking|note - the
    template is not in this tree at all and the validator is engine canon, so the reconciliation is
    somebody else's decision". I read that report, filed it as somebody else's decision, and then wrote a
    brief in the template's vocabulary rather than the validator's.
    Fixed without losing anything: every finding now carries the contract's `severity` AND the richer
    `severity_l2`, mapped blocker to blocking and major/minor to note.
    **THE LESSON IS ABOUT BRIEFS, and it is the third one this round.** My briefs have now produced: two
    paths for one patch file that resolved to a shared location and clobbered four agents' work; and a
    severity vocabulary the gate refuses. **A brief is code that runs on ten agents at once, and I have
    been writing it with less care than I would give a function.** The cheap discipline is to validate
    one instance of whatever the brief asks for BEFORE dispatching it, which in both cases would have
    taken under a minute.
    STILL UNRECONCILED, and still not mine to settle: the template and the validator disagree about the
    vocabulary. One of them should change. Recorded rather than chosen.

73. **A HOLD-BACK THAT SHIPPED HALF THE LAYER, SO ADOPTERS GOT THREE COMMANDS THAT DIE ON A MISSING
    FILE.** Found by the independent review of WARP-1405, confirmed by WARP-1402's and WARP-1403's
    reviewers independently, and MEASURED HERE IN THE REAL PUBLISHED PACK rather than reasoned about.
    `publish.py` withheld `estimate.py` and did NOT withhold four modules that load it, so every composed
    pack carried them. Measured by running the publisher and then the commands inside its own output:
    `toe_reconcile report`, `toe_reconcile fit` and `sizing_pass vocab` each exit 1 on
    `FileNotFoundError: .../.veldo/estimate.py`. `toe_analogy` and `toe_budget` load the same module and
    are held with them; that they break is INFERRED from the code rather than measured, and the
    difference between those two claims is stated rather than blurred.
    FIXED by completing the hold-back rather than by shipping the dependency, because shipping it is the
    decision Dmitry has not yet made and this breakage is wrong either way. Nothing that ships references
    the four: no pack, no engine doc, no engine spec mentions them, so no documented capability is
    removed.
    THE STATED REASON WAS ALSO FALSE ABOUT THE TREE, which the review also caught: the EXCLUDE comment
    gave "W3, W4, W5 and W8 are still to build" as the justification, while four of those items' modules
    were built and shipping. **A stated reason the tree contradicts is worse than no reason**, because it
    is the thing a reader checks instead of the code.
    AND I NEARLY REPORTED SOMETHING FALSE ON THE WAY TO FIXING IT. My first attempt to size the problem
    computed the dependency closure with a regex for `.veldo/<name>.py` over each file's TEXT, and it
    reported that 56 modules ship broken, including `validate.py`, `events.py`, `governor.py` and
    `init_scaffold.py`. **That is absurd on its face** - the install-and-run stage proves seven packs
    install and their own gates go green - and the cause is the defect this ledger records more than any
    other: a textual scan standing in for a real dependency, so a path MENTIONED in a comment or an error
    message counts as a path LOADED. The behavioural test, running the commands in the published pack,
    found exactly three broken and named them. **A number that fails the smell test gets checked before
    it gets repeated, and this one failed it loudly.**

74. **CHAPTER 13'S CAPABILITY SHIPS, AND THE PROOF IS THAT AN ADOPTER RAN IT.** Dmitry, 2026-08-13:
    "Chapter 13, run review and ship them" and "Estimation is one of the most important things, I don't
    want to cut anything". Nothing was cut.
    The sequence was: six independent reviews (all six FAIL, twelve blockers), close every blocker, lay
    the layer down, remove the exclusion as ONE set, then PROVE it. Measured in a tree produced by the
    real publisher and scaffolded by the pack's own installer: `toe_reconcile report`, `toe_reconcile fit`
    and `sizing_pass vocab` all exit 0. Before today all three exited 1 on a missing file. The installer
    lays 41 modules where it laid 28 this morning.
    **THE PROVING STEP FOUND WHAT EVERY CHECK MISSED, TWICE.** After laying down the closure the agents'
    handover notes named, the transitive-closure check went GREEN and `toe_reconcile report` still exited
    1, on `.veldo/metrics.py` - a module no list mentioned, reached at command time rather than at import.
    Laying that down, it failed again on `metrics_event_stream.py`. Both were found by installing the pack
    and running the command in a loop, laying down whatever it asked for next, until it exited zero.
    **A GREEN CHECK IS NOT AN INSTALLED PRODUCT.** Findings 61 and 73 are this same lesson from two other
    angles: 61 was an organ laid down without what it loads, 73 was a publisher shipping dependents
    without their dependency. This is the third, and the only thing that caught it was running the
    product as the adopter, in the tree the publisher produced. Every static check available said yes.
    THE HOLD-BACK IS VINDICATED RATHER THAN OVERTURNED, and the record says so where the exclusion used
    to be. It existed for one reason - these modules had never had their own independent review - and
    that review found a writer that could overwrite `.veldo/policy.yaml`, a reader that made three specs
    claim they touch no protected path when they do, and a spread floor reporting itself applied at 33
    percent against its own 50 percent minimum. Caution would have been shipping them; the hold-back was
    correctness.

75. **THE GATE DIED ON THE FIRST LEGITIMATE USE OF AN ORGAN IT SHIPS, AND FOUR MORE ROWS WERE WRONG
    BEHIND IT.** Dmitry, 2026-08-13: "Fix fix fix". The trigger was one operator action the product
    invites: recording the first incident and its reconciliation receipt. `.veldo/incidents` and
    `.veldo/reconciliations` do not exist in this repository today, which is the only reason five
    assertions across two suites were green.

    **Reproduced before it was diagnosed, and the reproduction is the whole finding.** One incident
    record, one receipt and one closing event written into a scratch copy the way an operator's own
    records land on disk. Result: `scripts/suites/12_warp_1210_hardening_four.py` raised
    `FileExistsError` out of a bare `mkdir()` on a store the `copytree` above it had just brought,
    taking the entire fragment down with it, and four assertions reddened - three in suite 11, one more
    in suite 12 once the crash stopped hiding them. **A gate check satisfied only while nobody has used
    the feature is the 35th sub-family of this ledger's dominant defect, and this instance is the worst
    shape of it: not a wrong answer but a CRASH, on the first real use, in the gate that is supposed to
    be the thing you trust.**

    **THE FIRST TWO REPAIRS WERE BOTH WRONG, AND THE SECOND WAS WRONG IN THE WAY THIS LEDGER EXISTS TO
    CATCH.** The first was `exist_ok=True` on the mkdir. It silences the crash and leaves the
    OPERATOR'S REAL RECORDS inside a fixture whose own docstring says its store holds "nothing else",
    trading a loud failure for a contaminated assertion - so the copies WITHHOLD the stores instead,
    named once for the fragment and used at every site, and the mkdir stays bare so a withholding that
    stops working still fails loud. It also went into the wrong function: a sweep of all seven copy
    sites showed the one that crashed was not the one edited, and the comment it carried claimed a
    reproduction that did not apply there. **The second was branching the empty-state row on what the
    live tree holds.** That keeps it green while quietly no longer exercising the empty state at all,
    which is the only reason the row exists. It renders over a root that is record-free BY
    CONSTRUCTION now, so the claim is true on every tree instead of on a new one.

    **DRIVEN FALSIFICATION CAUGHT A TAUTOLOGY IN THE FIX ITSELF, WHICH IS THE SECOND TIME TODAY.**
    The repaired render row selected its branch on `support_empty` and then checked a rendering that
    `support_empty` also decides. Mutating that function to always answer "empty" reddened 14 rows in
    one suite and 37 in the next - and left the repaired row GREEN, because one function lying
    consistently agrees with itself. The branch is selected by the COUNTS now, the independent fact,
    and the same mutation reds the row by name. **An assertion that cross-checks a function against
    its own output is not a check. Both new forms are driven: mutation applied, landing proven, the
    NAMED row red, and green again on revert.**

    Five rows repaired, all five proven in both directions - with an operator's records present and on
    an untouched tree - and the two organs that most invite this pin now read their own state instead
    of assuming it: the emptiness verdict must agree with the counts, the two CLI surfaces must agree
    with each other, and `read_skipped` must ACCOUNT FOR every skip its readers reported rather than
    be asserted empty.

    **THE OTHER SIX COPY SITES WERE DRIVEN, NOT REASONED ABOUT.** Seven places copy `.veldo` into a
    fixture; only one then created a store, which is why only one crashed. The remaining six can
    inherit an operator's records silently, which is the worse shape because nothing raises - so they
    were run with the records present rather than argued safe. All six stayed green, in suite 12 and in
    suite 15, so no wrong answer is reachable through them and they are recorded here rather than
    changed. That is a MEASUREMENT with a date on it, not a guarantee: any new assertion downstream of
    those copies inherits the exposure, and the withholding idiom above is what it should use.

76. **A HEARTBEAT IN THE FUTURE IS READ AS ALIVE, IN TWO MODULES, AND THE OBVIOUS FIX TRADES ONE SILENT
    HARM FOR THE OPPOSITE ONE. HIS CALL, NOT MINE.** Both freshness tests subtract in one direction:
    `runlog.classify` at `.veldo/runlog.py:284` (`now_epoch - hb_epoch > STALE_AFTER_SECONDS`, 30s) and
    `claim._is_stale` at `.veldo/claim.py:141` (`(now - hb_epoch) > STALE_AFTER_SECONDS`, 90s). A stamp
    ahead of now yields a negative difference, so it can never exceed the window and is reported
    **active** and **not stale** forever. Only the runlog half was on the ledger; **`claim.py` shares it
    and was unrecorded**, and that is the worse half: a claim whose heartbeat is in the future is never
    released, so **that unit is locked permanently and no other worker can ever take it** - in the one
    primitive the book names as the reason two workers never build the same unit.

    **WHY IT IS NOT FIXED TONIGHT, AND THIS IS THE POINT OF THE ENTRY.** The one-line fix is a symmetric
    window (`abs(now - hb_epoch)`). It is wrong in a way that is quieter than the defect: a worker whose
    clock runs two minutes fast writes heartbeats two minutes ahead, every one of them reads stale
    immediately, **and its live claim gets handed to a second worker.** Silent double-building is the
    exact failure the ledger exists to prevent, and it is worse than a locked unit, which at least an
    operator can see and clear. Trading a visible stall for an invisible collision is not an improvement,
    so it is not a decision to take while he is asleep. **The honest third answer is that clocks which
    disagree make liveness UNANSWERABLE, and this system already has a vocabulary for that - stand down
    and name the reason rather than answer** - but a third state changes a shipped boolean contract and
    every caller of it, which is a spec, and specs are stopped.

    My recommendation when he picks it up: the stand-down, scoped to the runlog reader first, where the
    consumer is a human reading a status and can be told "this run's clock disagrees with mine by 4
    minutes, so I cannot tell you whether it is alive" instead of being told "active". The claim ledger
    is second and needs the same answer, not a different one.

    **AND ONE ITEM ON THIS LEDGER WAS WRONG, WHICH IS WHY IT GETS CHECKED BEFORE IT GETS FIXED.** The
    same entry recorded `runlog.classify` as "accepting one timestamp spelling". That is the CONTRACT,
    not a defect: every stamp writer in the engine is `strftime("%Y-%m-%dT%H:%M:%SZ")` in eight modules,
    and `events.py:753` enforces it with a round-trip equality check. A foreign spelling is not something
    this system produces, and answering "liveness unconfirmed" for one is correct and fail-safe. Nothing
    to fix; the ledger line was overstated and is corrected here.

77. **THE VALIDATOR SAYS A SPEC IS FINE AND EVERY WRITER REFUSES IT - AND THE FIX CANNOT LAND, BECAUSE
    THE MODULE IS PINNED AT ITS CEILING. NOT FIXED; THE BUDGET IS NOW A BLOCKER RATHER THAN AN
    ANNOYANCE.** Both halves below were written, driven twice and then REVERTED, because the gate went
    RED for a reason that has nothing to do with the defect: `.veldo/validate.py` is **exactly 1000
    lines** and three separate criteria hard-assert `<= 1000` (WARP-1012 AC1, WARP-1102 AC3, WARP-1309
    AC6). A 13-line check takes it to 1013 and reds the unit stage. Its designated sibling,
    `.veldo/validate_checks.py` - the module whose entire purpose is checks - is at **999**.

    **A GOVERNED MODULE PINNED AT ITS EXACT CEILING IS A MODULE THAT CAN NEVER BE CORRECTED AGAIN.**
    That is the finding. The budget was described on this ledger as "declared advisory yet hard-asserted"
    and treated as cosmetic; it is not. Today it refused a correct fix to a real wrong answer, and the
    only homes for that fix are 1000 and 999 against a 1000 ceiling. Every future fix to spec validation
    hits the same wall. The honest options are all his: raise the budget for these two modules, split the
    validator (a spec, and specs are stopped), or accept that the wrong answer below stays. **I did not
    quietly trim someone else's code to make room, and I did not leave the gate red.**

    THE DEFECT ITSELF, reproduced and ready to re-apply the moment there is room: `validate.check_spec`
    reported **ZERO problems** for a spec whose front matter is `id: ../policy`, while
    `claim.unit_id_problem` - the ONE definition of an id that cannot be stored faithfully - refuses
    that id with a paragraph explaining that it collapses onto the basename `.._policy` and would share
    one claim record with every other id mapping there. Reproduced by copying a real spec and changing
    nothing but the id: 0 problems before, and the byte-identical control still 0 after, so the id was
    the only variable.

    **This is a wrong answer, not a missing nicety.** Two enumerations of one rule diverged: an author
    runs the validator, is told the spec is valid, and the tools then refuse to store anything keyed by
    it. The ledger this repository already keeps says which way that gets fixed - finding 71 established
    one definition, inherited, never re-spelled - so `check_spec` asks that function now rather than
    growing a third copy of the rule. The whole real corpus still validates clean, 214 specs and the two
    examples, so no existing id was relying on the gap.

    **DRIVEN TWICE BEFORE IT WAS REVERTED, and the second drive is the one that matters.** Removing the check reds the new row
    by name. Replacing it with a NEAR-MISS RE-SPELLING that still refuses the spec - "it has characters
    that cannot be a filename" - **also** reds it, because the row requires
    `claim.unit_id_problem`'s own text verbatim in what the validator reported. A row that only asserted
    "the spec was refused" would have passed that second mutation and been satisfied by a rule that had
    quietly forked again. Bound to the positive control that the same spec with its id untouched
    validates with zero problems.

78. **THE SITE'S LEAK GUARD WAS RED ON EVERY BUILD, SO THE BOOK'S FRONT DOOR SAT TWO DAYS STALE.**
    Dmitry, 2026-08-13, asked whether veldo was pushed "including website". It was not:
    `veldo.dev` is live but serving the 2026-08-11 `gh-pages` build, because `site/build_site.py`
    exits non-zero and refuses to certify its output. The reason is its own leak scan. Three entries on
    the forbidden-terms list are ordinary English - `support`, `infra`, `frontend` - and the scan was a
    plain substring test, so "infrastructure engineer" and "they support Veldo" were reported as company
    leaks. **A guard that fails on every build protects nothing: the terms that matter, `bcengi` and
    `sompo` and `travelpass`, would have arrived in exactly the same noise and been scrolled past.**

    **THE GUARD'S OWN OUTPUT HID HOW WIDE THE PROBLEM WAS.** It reported one hit per file and capped the
    list at twenty, so the first look showed only `support` and `infra` and made `frontend` look clean.
    It was not clean - `Frontend tickets on their own schedule` is in the web-developer document. I told
    him `frontend` could be kept on that first reading and was wrong; whole-word matching is what
    surfaced the third one. **An under-reporting failure message is how a red check stays unexplained
    for days.**

    Fixed as a rule rather than a list of exceptions: whole-word matching with a plural and possessive
    suffix group, `\b<term>(?:s|es|'s)?\b`. `\b` ALONE would have traded the false positives for false
    negatives, stopping `travelpasses` and `eSIMs` from matching at all. The three generic role words
    are dropped, because no matching rule can separate them from a leak - they are not leaks, they are
    the vocabulary of software roles, and a method for building software must use it. Driven: seeded
    `Bcengi`, `travelpasses`, `eSIMs`, `Sompo` and `Yesepkin` into a built page, each CAUGHT; the
    blocking `infrastructure engineer` no longer flagged; clean tree passes; the builder's own negative
    control still forces the check to fail as it must. Build exits 0 and is byte-identical twice over.

79. **EIGHT PROOF BUNDLES CLAIMED FIVE FALSIFICATIONS PER CRITERION WHEN EACH HAD ONE, AND ONE
    CRITERION CLAIMED FOUR WHILE HAVING NONE.** The ledger recorded this as one file. It was eight:
    `VELDO-0002` through `VELDO-0008` each repeat the SPEC-WIDE line "5 of 5 declared falsification(s)
    re-driven in this pass and each reddened its own row" verbatim under all five criteria, so read
    under AC1 - which is how a criterion's evidence is read - it claims five mutations for AC1 alone.
    The count equalling the criterion count is what gives it away. **`VELDO-0009` is the worst
    instance: its AC4 carried "4 of 4" and AC4 has no declared falsification at all**, so a criterion
    with zero evidence displayed four. The spec-wide total already sits ONCE in `checks[]`, which is
    its correct home; every per-criterion copy was a mis-scoped duplicate.

    Rewritten from each spec's own `driven-falsifications.txt`: the criterion's own count, its mutation
    BY NAME so a reader can re-run exactly that one, how many rows it reddened, and whether any was
    vacuous. `VELDO-0009` AC4's false line is REMOVED rather than replaced with an invented one, and
    its AC1, which already carried a correct per-criterion line, was left untouched. All twelve proof
    bundles still validate.

    **AND THE HALF OF THE REVIEWER'S FINDING THAT WAS NOT THE COUNTING.** F14 in
    `proof/VELDO-0004/verdict-l2.json` reported the overstatement "in two ways", and the second way is
    the serious one: applied literally, AC1's declared falsification raised `KeyError('looks_fine')`
    INSIDE the block, so the block wrapper reddened while **the row the `falsified_by` field names never
    ran**, and 11 of 27 rows stopped running. `HAS TEETH` was true of the suite and false of the check.
    **A mutation that DELETES coverage looks exactly like a mutation that works**, and the lost rows
    were recorded nowhere - the 35th family, a check satisfied by a crash, arriving inside a
    falsification record. That was a defect in `.veldo/promises.py` and it is fixed there: `PRED_NEEDS`
    is read with a default and its branch is not an `elif`, so a predicate outside the closed set is
    NAMED instead of raising out of a validator.

    **MY FIRST FIX PROPAGATED THE CLAIM THE REVIEWER HAD REFUTED.** The per-criterion sentence I
    generated for AC1 was sourced from the stale record, so it repeated `HAS TEETH` for a mutation that
    only reddened the wrapper. Caught by reading the reviewer's finding rather than the ledger's
    one-line summary of it. Re-driven today at `5ecab26`: the mutation reds THE NAMED ROW, and 83
    passed + 2 failed = 85 = the baseline, so no coverage is lost - asserted by arithmetic, which is
    the check the earlier pass never made. **The old record line is left exactly as written and
    SUPERSEDED in place: a proof record is a record of what a pass observed, so it is never edited into
    saying something that pass did not see.**

80. **THE TEMPLATE EXCEPTION'S STATED REASON IS NOT WHAT THE TEMPLATE ACTUALLY DIFFERS BY. RECORDED,
    NOT FIXED - no wrong answer is reachable, and the measurement that rules out the dangerous version
    of this is the point of the entry.** `scripts/check_template_sync.sh` permanently excepts
    `specs/TEMPLATE.md` from twin sync, reasoning that "the index is generated from this repository's own
    specs, and the template carries local conventions". That reason is exactly right for `specs/index.md`
    and `CLAUDE.md`, the other two exceptions. It is wrong about the template: the 20 lines the root copy
    carries and `engine/specs/TEMPLATE.md` does not are **generic method guidance, not local
    convention** - the four things a criterion carries (what is claimed, over what set, how completeness
    is known, what would refute it) and the clause saying a declared falsification is not enough, drive
    it. So an adopter receives the form without the two paragraphs this project paid weeks to learn.

    **WHAT WAS CHECKED BEFORE RECORDING IT, because the dangerous reading was that the SHIPPED template
    produces an invalid spec** - findings 61, 73 and 74 in one shape. It does not. `falsified_by` is
    present as a FIELD in the engine copy, not merely in a comment, so a criterion written from it
    carries what the gate requires. And both templates fail `validate.py spec` in exactly the same two
    places, on their own inline guidance comments being read as front-matter values, which is
    template-as-form behaviour in both trees and not drift. **A permanently excepted file was measured
    rather than assumed, and the measurement is what turns this from a blocker into a note.**

    Left alone under the stop rule: no user or gate can get a false answer from it, so copying the two
    paragraphs across is an improvement to make deliberately rather than at 13:30 unattended.

### Expected to grow
Dmitry, 2026-08-11: "I am sure between now and then you will find more." Findings are appended here
as they are found, and this plan is not done while one is unrecorded.
