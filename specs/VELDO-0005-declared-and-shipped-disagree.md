---
schema: veldo.spec/v1
id: VELDO-0005
title: Where the manifest and the tree disagree - a declared capability whose home does not resolve
  and a shipped module nothing declares, both named, both carrying what the resolver tried
status: ready
risk: standard - it adds one read model over the capability manifest and the shipped tree, writes
  nothing, and no gate stage consumes its findings. It is NOT low because its product is an accusation
  against the one file documentation defers to, and the obvious implementation of its first half was
  MEASURED to accuse a third of the corpus falsely, so a resolver that hid what it tried would launder
  those into facts - and because its own suite runs in the required unit stage, a row that turned one
  of those accusations into a gate condition made the organ block after all, which is what independent
  review found and what AC5 now drives against. It is not high because it refuses no change and every
  leg stands down by name when its input is absent
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W4
placement: [contracts]
footprint:
  - ".veldo/declared.py"
  - "engine/.veldo/declared.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/22_veldo_0005_declared_vs_shipped.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0005-declared-and-shipped-disagree.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    Every unresolved home names the capability, the home as DECLARED, each segment that failed, and
    every root the resolver actually searched for it, so a reader can see the resolver was pointed
    wrong before editing the manifest. The report also names the roots AVAILABLE to the resolver and
    where they were derived from, which is a different fact from what any one home attempted. Every
    undeclared module names its path. Each leg reports its own stand-down reason separately, because
    an absent manifest and an absent tree are different absences. WHERE A HOME RESOLVED IS REPORTED
    TOO: a segment found under a root other than the one its declared string implies is named with
    that root and the path it was found at, because resolution accepts the FIRST root that has the
    path and a MIRROR COPY therefore satisfies a home whose declared file is gone. The exemption
    ledger reports its own state - NOT_READ, ABSENT, PRESENT or SUPPLIED, beside the path it looked
    at - and every refused or rotted entry, because "0 exempted" printed for an absent list and for
    a list that exempts nothing told a reader the same thing about two different facts.
  error_taxonomy: >
    Two findings, never merged, because they are opposite mistakes with opposite fixes: HOME_UNRESOLVED
    (the manifest claims a home the tree does not have - either the module moved or the declaration is
    stale) and UNDECLARED_MODULE (the tree ships a module the manifest never claims - either it needs a
    capability or it needs a recorded exemption). An exemption carries a REASON and the report counts
    exempted modules separately from declared ones, so an exemption list cannot quietly become the
    place undeclared modules go to be forgotten - and a refused exemption is REPORTED as refused,
    while an exemption naming a module that is already declared or no longer shipped is reported
    STALE, because refusing in silence is how a ledger rots. RESOLVED ELSEWHERE IS AN OBSERVATION AND
    NOT A THIRD FINDING, and that is a measurement rather than a preference: 36 segments of this
    repository's real manifest resolve under a root other than the one their string implies and NONE
    of them is stale, so accusing them would be the same false accusation this item exists to
    eliminate. It is reported, counted on the headline, and accuses nobody.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Reduce the resolver in .veldo/declared.py to a single ROOT and a single path segment, and the
      assertion that a COMPOUND home and a home under a pack root both resolve - measured over this
      repository's real manifest, where the naive resolver reported 42 unresolved of 167 and every one
      was false - must go red. SECOND, for the leg independent review added: drop the
      resolved_elsewhere record from declared_report, and the assertion that a home resolving under a
      MIRROR ROOT is named with that root must go red; record the root as the repository root instead
      of the one it was found under, and the live soundness row must go red too.
    text: >
      THE RESOLVER IS THE ITEM, AND THE NAIVE ONE IS WRONG A THIRD OF THE TIME. MEASURED on
      2026-08-12 against this repository's real manifest: checking each declared home as one path
      under the repository root reported 42 unresolved of 167, and ALL 42 WERE FALSE. A home may be
      COMPOUND (two paths joined by `+`), may be a DIRECTORY rather than a file, and may live under a
      pack root rather than the repository root. So the resolver splits compounds, tries every
      declared root, and accepts a directory. THE ROOTS ARE DERIVED FROM .veldo/packs.json AND THE
      TREE, NEVER HARDCODED, and that came from independent review: the first implementation carried
      the literal tuple ('.', 'engine', 'packs/claude') while the pack manifest declares SEVEN pack
      roots, so ONE CORRECT declaration whose home was a real Cursor driver under packs/cursor was
      reported HOME_UNRESOLVED - the same false accusation this item exists to eliminate, reachable
      for six of the seven tool drivers. NEGATIVE CONTROL: a home naming a path that genuinely
      exists nowhere IS reported unresolved, so the resolver is not one that resolves everything.
      OVER THE LIVE MANIFEST the assertion is SOUNDNESS, never content: every accused segment is
      stat'ed by the suite itself under every root the tree declares, and an accusation against a
      path that exists anywhere is the failure. No live row requires the unresolved set to be empty.
      AND WHERE A HOME RESOLVED IS REPORTED, because accepting the FIRST root that has the path means
      a MIRROR COPY satisfies a home whose declared file is GONE: independent review deleted
      .veldo/promises.py and the report read 0 unresolved, resolving it from engine/, with the
      substituted root recorded nowhere a reader would see - and the manifest itself says the .veldo
      modules are distributed byte-identical across the engine and every pack, so that is this
      repository's most common drift shape by construction. The silence is the defect and the silence
      is what is fixed: the record names the root and the path it was found at, and the count rides on
      the headline. IT IS AN OBSERVATION AND NOT A FINDING, MEASURED RATHER THAN PREFERRED: 36
      segments here resolve that way and none is stale, so the other half of what review proposed -
      calling resolution under a non-repository root a finding - would accuse 36 correct declarations,
      which is this organ's own defect in a third dress. Telling the two apart needs the manifest to
      declare WHICH root a home is relative to, a capabilities.yaml change that stays out of scope
      here, named rather than stubbed.
  - id: AC2
    falsified_by: >
      Drop the attempted-paths record from an unresolved finding in .veldo/declared.py, and the
      assertion that every HOME_UNRESOLVED finding carries the home as declared, the failing segment
      and every root tried must go red.
    text: >
      AN UNRESOLVED HOME CARRIES WHAT THE RESOLVER TRIED. The first half of this item is an accusation
      against the file documentation defers to, and its obvious implementation was wrong 42 times out
      of 167, so a finding that reported only its conclusion would have laundered every one of those
      into a fact. Each finding records the home AS DECLARED, which segment failed, and every root
      that was searched - the same discipline VELDO-0004 applies to a contradicted claim, for the same
      reason and from the same measurement. WHAT IS RECORDED IS WHAT WAS SEARCHED: the attempted
      roots are collected as the search runs, not copied from the list the resolver was handed, so a
      resolver that skipped a root cannot print a line naming it. The suite checks the record against
      a root derivation of its own rather than against the module's constant, because asserting a
      module's output equals that module's own constant asserts nothing about the work it did.
  - id: AC3
    falsified_by: >
      Make the undeclared-module scan in .veldo/declared.py compare against the raw home STRINGS
      instead of the resolved segments, and the assertion that a module declared inside a COMPOUND
      home counts as declared must go red.
    text: >
      A MODULE DECLARED INSIDE A COMPOUND HOME IS DECLARED. The second finding is the first read from
      the other end: the tree ships a module and the manifest claims no capability for it. It is
      derived by comparing the shipped set against the RESOLVED segments of every home, not against
      the home strings, because a module named as one half of `a.py + b.py` is declared and reporting
      it undeclared would be the same false accusation in the mirror. NEGATIVE CONTROL: a module named
      in no home at all IS reported, so the comparison is a measurement rather than a scan that finds
      nothing.
  - id: AC4
    falsified_by: >
      Fold exempted modules into the declared count in .veldo/declared.py, and the assertion that an
      exemption requires a reason and is counted in its OWN bucket must go red. AND FOR THE THREE
      SILENCES INDEPENDENT REVIEW FOUND, each with its own mutation and its own row: make the ledger
      report PRESENT when the file is absent, and the row that separates an absent input from a list
      that exempts nothing must go red; drop the refusal record, and the row requiring a refused
      exemption to be reported as refused must go red; drop the stale scan, and the row naming an
      exemption for an already-declared or no-longer-shipped module must go red.
    text: >
      AN EXEMPTION CARRIES A REASON AND IS COUNTED SEPARATELY. Whether an internal helper deserves a
      capability is a judgement, so a module may be exempted - and an exemption with no reason is
      refused, because an exemption list with no reasons is where undeclared modules go to be
      forgotten. Exempted modules are counted in their own bucket and never added to the declared
      count, so the report cannot be made clean by exempting everything: the number of exemptions is
      as visible as the number of findings.
      AND THE LEDGER REPORTS ITS OWN STATE, because three silences undercut exactly the anti-forgetting
      purpose this criterion is about and independent review found all three. An ABSENT list printed
      the same "0 exempted" as a list that exempts nothing, while the manifest leg is careful to say an
      absent input is NOT the same fact as agreement - so the input's state is NAMED beside the path it
      was looked for at. A REFUSED exemption was dropped in silence, so the human who wrote it saw the
      module still listed as undeclared with no hint the entry had been seen and refused - so every
      refusal is reported with the line it came from and why. AND AN EXEMPTION CAN ROT: one naming a
      module a capability already declares, or a module no longer shipped, reached no bucket at all -
      so both are named STALE with which of the two they are, because a rotted entry reported nowhere
      is precisely the forgetting place this criterion exists to prevent. The additive control is that
      a list whose every entry is a reasoned exemption of a shipped, undeclared module produces no
      refusal and no stale entry.
  - id: AC5
    falsified_by: >
      Remove the per-leg stand-downs from the report in .veldo/declared.py, and the assertion that an
      absent manifest stands the whole report down by name while an absent module directory stands
      only its own leg down must go red.
    text: >
      EACH LEG STANDS DOWN SEPARATELY AND ITS FINDINGS GATE NOTHING. An absent capability manifest
      stands the whole report down, because both findings are defined against it. An absent module
      directory stands only the undeclared leg down while the unresolved leg still answers.
      THE CLAIM THAT NO GATE STAGE LOADS THIS WAS FALSE AND IS RETRACTED, on independent review: the
      module is loaded by its own suite fragment, which runs inside verify.sh's required unit stage
      like every other fragment, and two of that fragment's rows pinned live repository state (an
      unresolved set required to be EMPTY and a design/ directory required to be ABSENT), so an
      ordinary repository change reddened the whole gate on this organ's heuristic verdict - the
      thing PLAN-0018 NG3 forbids. What is asserted now is the property that matters and it is
      DRIVEN rather than promised: the organ-produced findings of a fixture tree are spliced into the
      live report so every bucket carries one, and every claim the suite makes about a real tree is
      re-driven over THAT report and must still hold, so a row that pins emptiness again reds in
      front of its author. The loader scan is recursive over the whole tree and must find the
      fragment ITSELF, because a scan whose domain excludes the only loader reported an empty list.
      A DESIGN-WITH-NO-DESCENDANTS leg is DELIBERATELY NOT BUILT HERE and said so rather than
      stubbed. THE REASON RECORDED BEFORE WAS FALSE: it said this repository has no design/ directory
      at all, and only the literal top-level path is absent, while docs/design/ holds 19 design
      documents and PLAN-0018 observation 18, the observation that produced this work item, names
      docs/design/05-product-planning-layer-sol.md as a design that died with nothing noticing. The
      true reason is a scope decision: that leg needs a DESCENDANTS relation between a design and the
      specs or plan items it produced, a different corpus and a different judgement from comparing
      the manifest against the shipped modules. What is asserted instead is a property of the code
      that a half-built leg cannot satisfy: the finding kinds the module DECLARES are exactly the
      kinds a driven report EMITS.
required_evidence: [unit]
rollback: >
  Delete .veldo/declared.py and its suite fragment. The capability declarations it motivated stay
  valid on their own and no gate stage consumes its findings, so the retreat costs two files: the
  organ and the fragment that drives it, which is the only thing in the tree that loads it.
---

# Where the manifest and the tree disagree

## The measurement that designed this item

`.veldo/capabilities.yaml` is the machine-readable truth about what this plugin implements, and its
own header says documentation defers to it: **a claim in prose that contradicts a status here is a
documentation bug.** So the manifest and the tree disagreeing is a defect in whichever one is wrong,
and until now nothing looked.

Two measurements on 2026-08-12, both over the real manifest:

**26 of 108 shipped `.veldo` modules were claimed by no capability at all**, and five of them were
the organs built in the preceding three days. That half is real and was worth fixing immediately.

**A naive check of the other half reported 42 unresolved homes of 167, and every one was false.**
A home may be compound (`a.py + b.py`), may name a skills directory that lives under a pack root,
or may be a directory rather than a file. Resolving properly leaves zero.

That second number is why this item exists in the shape it does. The obvious implementation of a
completeness check accuses a third of the corpus wrongly, and an accusation against the file
documentation defers to would send somebody editing correct declarations. So the resolver is the
substance of the work, and every finding carries what the resolver tried.

**The first implementation made that same false accusation for six of seven pack roots**, and
independent review found it. `SEARCH_ROOTS` was the literal tuple `('.', 'engine', 'packs/claude')`
while `.veldo/packs.json` declares seven packs, so one correct declaration about a real Cursor driver
under `packs/cursor` was reported `HOME_UNRESOLVED`. The roots are now read from that manifest plus
the directories that exist under `packs/`, so a pack added later is covered by arriving.

## What the first version got wrong about gating, and what is asserted instead

The item said IT GATES NOTHING and that no gate stage loads the module. The second half was false.
The module is loaded by its own suite fragment, that fragment runs inside `scripts/verify.sh`'s
required `unit` stage, and two of its rows asserted over live repository state: the unresolved set
was required to be EMPTY, and a `design/` directory was required to be ABSENT. So `mkdir design`
reddened the whole gate, and so did adding one correct capability declaration. The evidence offered
for the no-loader claim could not have found the violation either: the AST scan globbed
`.veldo/*.py` and `scripts/*.py` non-recursively, which excludes `scripts/suites/` by construction.

What is asserted now, driven rather than promised:

- **Soundness, not content.** Every accusation the organ makes about this repository is stat'ed by
  the suite itself under every root the tree declares. A genuinely stale declaration keeps the row
  green and gets printed; a false accusation reds it.
- **Agreement, not counts.** The undeclared set must equal a derivation the suite performs itself.
- **The claims survive real findings.** Fixture-produced findings are spliced into the live report so
  unresolved, undeclared and exempted each carry one, and every live claim is re-driven over that
  report. A row that pins emptiness again reds there, in front of its author.
- **The loader scan proves its own domain** by finding the fragment itself, recursively over the tree.

## The mirror copy, which is the second thing independent review measured

Resolution accepts the FIRST root that has the path, so a home declared as `.veldo/x.py` keeps
resolving after that file is deleted, from `engine/.veldo/x.py`. Review drove it: `rm
.veldo/promises.py` left the report reading **0 unresolved, 110 modules**, resolving the home to
`engine/.veldo/promises.py`, and the suite fully green. The manifest itself says the `.veldo` modules
are distributed byte-identical across the engine and every pack, so this is the repository's most
common drift shape by construction, and nothing in the report distinguished **resolved where
declared** from **resolved somewhere else**.

**What is fixed is the silence.** Every segment that resolved under a root other than the one its
declared string implies is now a record naming the capability, the home as declared, the segment, the
root and the path it was found at, printed with the sentence that a mirror copy masks a stale
declaration this way, and counted on the headline.

**What is refused is the accusation, and that is a measurement.** Review offered a second fix:
treat resolution under a non-declared root as a finding. Measured over the real manifest, 36 declared
segments resolve that way and **not one of them is stale**: `skills/plan` is a real Claude pack
skill, `scripts/veldo-visual.py` legitimately lives only in `engine/`, and 24 runner homes are
engine-only by design. That fix would make 36 false accusations against the file documentation defers
to, which is the exact defect this item exists to eliminate, so the bucket informs and accuses
nobody. Telling a masked stale declaration from a legitimately engine-only home needs the manifest to
declare WHICH root a home is relative to - a `capabilities.yaml` change rather than a change to this
module - and it is named here rather than guessed at.

## What is deliberately not here

**A design with no descendants**, which is half of this work item's title in PLAN-0018. The reason
recorded in the first version was false: it said this repository has no `design/` directory, and only
the literal top-level path is absent, while `docs/design/` holds 19 design documents and PLAN-0018
observation 18, the observation that produced this work item, names
`docs/design/05-product-planning-layer-sol.md` as a design that died with nothing noticing. The leg
had a corpus and a known positive instance.

The true reason is a scope decision, and it is narrower: that leg needs a DESCENDANTS relation
between a design and the specs or plan items that came from it, which is a different corpus and a
different judgement from comparing the capability manifest against the shipped module set. Its one
known instance is already named in PLAN-0018 and in VELDO-0011, so nothing is being kept quiet by
leaving it out. Named as not built rather than stubbed, and the suite no longer certifies the absence
of a directory: it asserts that the finding kinds the module declares are exactly the kinds a driven
report emits, so a third kind named without a leg reds the row.
