---
schema: veldo.spec/v1
id: VELDO-0118
title: Generate a shared grammar domain and independent YAML oracle observations
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0110]
placement: [contracts, runners, docs]
protected_paths: []
footprint:
  - "docs/yamlish-grammar.md"
  - "scripts/fixtures/yamlish_grammar.json"
  - "scripts/fixtures/grammar_cases.py"
  - "scripts/fixtures/yaml_oracle.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/*_veldo_0118_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0118-grammar-generated-oracle-fixture.md"
  - "specs/VELDO-0119-shared-reader-grammar-agreement.md"
  - "specs/VELDO-0120-policy-grammar-agreement.md"
  - "specs/index.md"
  - "proof/VELDO-0118/*"
behavior_bearing: true
observability:
  logs: >
    Record grammar revision, derivation, source bytes, coverage targets, oracle version and result or named stand-down for every case.
  metrics: >
    Report production/alternative coverage and expected/generated/compared input counts separately.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish grammar_inventory_gap, generation_incomplete, oracle_unavailable, oracle_error and dialect_difference.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Inputs are generated from a written grammar corresponding to the shared reader's documented syntax, not selected from current parser successes or seventeen regression examples.
      Set: Every production and lexical alternative in the versioned grammar, and every allowed direct parent/child production pair (k-path coverage with k = 2), including block/flow maps and sequences, scalar styles, escapes, continuations, comments and chomping.
      Completeness: Enumerate required production, lexical-alternative and pairwise nesting targets from the grammar itself. Construct witnesses, collect coverage from their derivation trees, and require every target to have a witness. Keep an independently counted target inventory and require equality with enumerated and witnessed inventories. Preserve duplicate-byte derivations as separate coverage records; no production-success filtering.
      Refutation: grammar/all-coverage-targets-exist is false if any production, lexical alternative or allowed parent/child pair lacks a witness or the independent inventory disagrees.
    falsified_by: >
      Omit folded-block productions from the generator; grammar/all-coverage-targets-exist must turn red.
  - id: AC2
    text: >
      Claim: The fixture generates inputs immediately outside the dialect and labels their expected refusal independently of the implementation.
      Set: Every exclusion rule applied at every production site where its grammar-declared applicability predicate holds, at least once per site: duplicate keys, bad indentation, missing delimiters, invalid escapes, unterminated quotes, tags, anchors, aliases, merge keys, directives, multiple documents, multiline quotes and explicit indentation indicators.
      Completeness: Enumerate required rule/site targets from the grammar's exclusion predicates and production graph; construct a local edit at each site and retain the original derivation, production site and edit id. Require exact equality with the independently counted target inventory and a witness for every target. Use the external oracle to distinguish valid general YAML outside the dialect from invalid YAML syntax.
      Refutation: grammar/all-boundary-sites-exist is false if any applicable rule/site target lacks its witness or the independent inventory disagrees.
    falsified_by: >
      Remove duplicate-key edits from generation; grammar/all-boundary-sites-exist must turn red.
  - id: AC3
    text: >
      Claim: The fixture obtains independent parse observations without importing the production reader or writer.
      Set: All generated accepted and boundary inputs, against PyYAML's parsing/composition interface when installed, recording structure, scalar spelling/style, source location and parser errors before dialect normalization.
      Completeness: Use the complete generated input digest inventory; preserve raw oracle observations and a separately specified dialect adapter. Boolean words and leading-zero integers retain the documented Veldo meaning instead of inheriting YAML 1.1 resolution; duplicate keys are detected from node pairs rather than a mapping that overwrites them. No production parse/serialize call may supply expected values.
      Refutation: grammar/oracle-is-independent is false if an intentionally wrong production result changes the oracle's recorded answer for the same bytes.
    falsified_by: >
      Delegate expected-value parsing to the production shared reader; grammar/oracle-is-independent must turn red under the fixture's fixed defective-reader control.
  - id: AC4
    text: >
      Claim: Missing PyYAML is an explicit oracle_unavailable stand-down and cannot count as independent agreement.
      Set: Full oracle installation, import absence, import-time failure and runtime oracle exception for both fixture consumers.
      Completeness: Exercise each capability outcome; emit generated, compared and unobserved counts and require compared=0 for absence. Stdlib generation/refusal checks still run. Only a provisioned oracle qualification run can close agreement; parser defects or crashes when installed are errors, not absence.
      Refutation: grammar/missing-oracle-is-unproven is false if an absent oracle yields an agreement pass or if an installed-but-broken oracle is silently skipped.
    falsified_by: >
      Mark all generated cases as independently agreed when importing PyYAML raises ImportError; grammar/missing-oracle-is-unproven must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Own the generated syntax domain and independent oracle once, so shared-reader and policy consumers compare the same bytes without duplicating fixtures.

## Context

The gap is in VELDO-0106 AC1 and proof/VELDO-0106/README.md:115-120; VELDO-0110 supplies the shared dialect and currently has writer-driven examples rather than this reader-grammar domain.

## Out of scope

Changing the accepted dialect, replacing the standard-library runtime dependency policy, consumer-specific assertions, and claiming exhaustive coverage of an unbounded language.

## Notes

The domain is coverage-based grammar generation, not an exhaustive cross-product of bounded derivations. The versioned grammar declares normalized productions, lexical alternatives, allowed direct child slots and exclusion applicability predicates. Every production and lexical alternative must have a witness; every allowed parent/child production pair must have a witness (k-path coverage, k = 2); every exclusion rule must be applied at every applicable production site at least once. A site is a grammar edge identified by parent production, child slot and child production, with a separate document-root site. Recursive occurrences share their grammar site; this is a finite coverage criterion, not a claim about all recursive contexts.

Witnesses are constructed by completing targets with terminating derivations and embedding them through a grammar-permitted root path. Lexical representatives retain the versioned length 0..2 payload alphabet, named integer/boolean/null/Unicode/control partitions, key classes, escapes, chomping and continuation alternatives. Formatting alternatives receive witnesses without taking their Cartesian product with every tree. Container arities and compact/wrapped forms are explicit grammar alternatives. Duplicate source bytes keep distinct target identities. Required targets are enumerated from grammar declarations, observed coverage is collected from emitted derivations, and a separate arithmetic counter must agree. Any missing target fails its named row; neither parser success nor timing can remove a target. Report grammar revision, target inventories, input digests, observations and limits. Larger coverage criteria require an explicit grammar revision. The retained exhaustive counter and control reproducer exist only to reproduce historical evidence.

AC3 and AC4 are unchanged: oracle observations remain independent, and missing PyYAML remains a named stand-down with no independent agreement. Reader disagreements belong to VELDO-0119 and are preserved in full, never used to filter the domain or repaired here.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.


## Implementation checkpoint (2026-09-22)

Stopped under the requested cost limit; status remains ready. The clean-tree
gate at 69def368bbf63e2735797df5496efbdcad0b883b was RED (5,569 unit assertions
passed, three failed). Its measured wall-time increase was 463.503151 seconds.
The direct new suite took 60.001075 seconds and generated 2,059,668 derivations
and 19,756,060 boundary edits before reporting generation_incomplete; full
baseline qualification remains unproven. The declared domain was not reduced.
All eight named mutation drives completed and detected their targets. A
separate control-domain comparison recorded 192 reader/oracle disagreements
in full for VELDO-0119; the reader is unchanged. Counts, digests, all findings,
regeneration commands and the stop record are in `proof/VELDO-0118/README.md`.

## History (2026-09-22, coverage revision)

The exhaustive domain was measured at 510,928,488 derivations and
5,013,490,520 boundary edits. It was replaced by coverage criteria on the
owner's approval: Telegram 28810, "Yes", answering 28808 about proposal
28805. The pre-rewrite measurement found 22 production targets, 934 lexical
alternatives, 132 direct parent/child pairs and 457 applicable boundary
rule/site targets. Generation and oracle/reader observation of 1,545 inputs
took 3.775353 seconds; two green-path gate invocations add 7.550706 seconds
of measured work. AC1, AC2 and Notes now specify this complete target domain;
AC3 and AC4 are unchanged. Status remains ready. The earlier checkpoint
above is historical evidence, not the current qualification result.
