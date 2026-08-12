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

### Expected to grow
Dmitry, 2026-08-11: "I am sure between now and then you will find more." Findings are appended here
as they are found, and this plan is not done while one is unrecorded.
