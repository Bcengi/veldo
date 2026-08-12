---
schema: veldo.spec/v1
id: VELDO-0005
title: Where the manifest and the tree disagree - a declared capability whose home does not resolve
  and a shipped module nothing declares, both named, both carrying what the resolver tried
status: ready
risk: standard - it adds one read model over the capability manifest and the shipped tree, writes
  nothing and gates nothing. It is NOT low because its product is an accusation against the one file
  documentation defers to, and the obvious implementation of its first half was MEASURED to accuse a
  third of the corpus falsely, so a resolver that hid what it tried would launder those into facts.
  It is not high because it refuses no change and every leg stands down by name when its input is
  absent
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
    every root the resolver tried, so a reader can see the resolver was pointed wrong before editing
    the manifest. Every undeclared module names its path. Each leg reports its own stand-down reason
    separately, because an absent manifest and an absent tree are different absences.
  error_taxonomy: >
    Two findings, never merged, because they are opposite mistakes with opposite fixes: HOME_UNRESOLVED
    (the manifest claims a home the tree does not have - either the module moved or the declaration is
    stale) and UNDECLARED_MODULE (the tree ships a module the manifest never claims - either it needs a
    capability or it needs a recorded exemption). An exemption carries a REASON and the report counts
    exempted modules separately from declared ones, so an exemption list cannot quietly become the
    place undeclared modules go to be forgotten.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Reduce the resolver in .veldo/declared.py to a single ROOT and a single path segment, and the
      assertion that a COMPOUND home and a home under a pack root both resolve - measured over this
      repository's real manifest, where the naive resolver reported 42 unresolved of 167 and every one
      was false - must go red.
    text: >
      THE RESOLVER IS THE ITEM, AND THE NAIVE ONE IS WRONG A THIRD OF THE TIME. MEASURED on
      2026-08-12 against this repository's real manifest: checking each declared home as one path
      under the repository root reported 42 unresolved of 167, and ALL 42 WERE FALSE. A home may be
      COMPOUND (two paths joined by `+`), may be a DIRECTORY rather than a file, and may live under a
      pack root rather than the repository root. So the resolver splits compounds, tries every
      declared root, and accepts a directory. NEGATIVE CONTROL: a home naming a path that genuinely
      exists nowhere IS reported unresolved, so the resolver is not one that resolves everything.
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
      reason and from the same measurement.
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
      exemption requires a reason and is counted in its OWN bucket must go red.
    text: >
      AN EXEMPTION CARRIES A REASON AND IS COUNTED SEPARATELY. Whether an internal helper deserves a
      capability is a judgement, so a module may be exempted - and an exemption with no reason is
      refused, because an exemption list with no reasons is where undeclared modules go to be
      forgotten. Exempted modules are counted in their own bucket and never added to the declared
      count, so the report cannot be made clean by exempting everything: the number of exemptions is
      as visible as the number of findings.
  - id: AC5
    falsified_by: >
      Remove the per-leg stand-downs from the report in .veldo/declared.py, and the assertion that an
      absent manifest stands the whole report down by name while an absent module directory stands
      only its own leg down must go red.
    text: >
      EACH LEG STANDS DOWN SEPARATELY AND IT GATES NOTHING. An absent capability manifest stands the
      whole report down, because both findings are defined against it. An absent module directory
      stands only the undeclared leg down while the unresolved leg still answers. A DESIGN-WITH-NO-
      DESCENDANTS leg is DELIBERATELY NOT BUILT HERE and said so rather than stubbed: this repository
      has no design/ directory at all, so a leg for it would ship unexercised and its first real run
      would be its first test. No gate stage loads this (PLAN-0018 NG3: a completeness organ that
      blocked on a heuristic verdict would cut true sentences and stop real work).
required_evidence: [unit]
rollback: >
  Delete .veldo/declared.py and its suite fragment. The capability declarations it motivated stay
  valid on their own, nothing imports it and no gate stage runs it, so the retreat costs one file.
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

## What is deliberately not here

**A design with no descendants**, which is half of this work item's title in PLAN-0018. This
repository has no `design/` directory: the leg would ship with nothing to run against, its first real
execution would be its first test, and a check whose coverage is a promise about the future is the
shape this project keeps finding in its own history. Named as not built rather than stubbed, so
nobody reads its absence as coverage.
