---
schema: veldo.spec/v1
id: VELDO-0118
title: Generate a shared grammar domain and independent YAML oracle observations
status: draft
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
  - "scripts/suites/*_veldo_0118_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0118-grammar-generated-oracle-fixture.md"
  - "specs/index.md"
  - "proof/VELDO-0118/*"
behavior_bearing: true
observability:
  logs: >
    Record grammar revision, derivation, source bytes, domain bounds, oracle version and result or named stand-down for every case.
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
      Set: Every supported production and lexical alternative in a versioned EBNF grammar, exhaustively expanded within the finite domain defined in Notes, including block/flow maps and sequences, nesting, scalar styles, escapes, continuations, comments and chomping.
      Completeness: Reconcile grammar productions to the shared reader's written contract, publish a production/alternative inventory and independently counted bounded derivation total, then require equality with the generated derivation inventory. Preserve duplicate-byte derivations as coverage records; any production with zero witnesses or any unexpanded case fails.
      Refutation: grammar/all-bounded-derivations-exist is false on an omitted production alternative or derivation.
    falsified_by: >
      Omit folded-block productions from the generator; grammar/all-bounded-derivations-exist must turn red.
  - id: AC2
    text: >
      Claim: The fixture generates inputs immediately outside the dialect and labels their expected refusal independently of the implementation.
      Set: Every supported derivation crossed with each applicable single boundary edit from the grammar's exclusion rules: duplicate keys, bad indentation, missing delimiters, invalid escapes, unterminated quotes, tags, anchors, aliases, merge keys, directives, multiple documents, multiline quotes and explicit indentation indicators.
      Completeness: The exclusion-rule registry supplies the edit inventory and applicability predicates; every rule must produce a witness. Retain the original derivation and edit id, require expected/produced equality, and distinguish valid general YAML outside the dialect from invalid YAML syntax using the external oracle.
      Refutation: grammar/all-boundary-edits-exist is false if a rule lacks its expected generated neighbors.
    falsified_by: >
      Remove duplicate-key edits from generation; grammar/all-boundary-edits-exist must turn red.
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

The initial exhaustive domain contains all grammar derivations with at most three value nodes (containers and scalars), nesting depth at most two and at most two children per container. Scalar payloads enumerate length 0..2 over a, space, #, colon, single quote and double quote, plus one representative of every lexical partition: canonical positive/negative/zero integer, leading-zero digits, boolean words, null-like words, each escape, Unicode and control boundaries. Keys use every supported key class, with at most two distinct keys. Enumerate all grammar-permitted scalar styles, block chomping choices, one/two-space indentation units, LF/CRLF and absent/present trailing comments. Multi-line productions get their shortest valid witness and one extra continuation. Partition representatives and bounds are versioned grammar data, never discovered by asking the parser what it accepts. If a production needs a larger minimum derivation, include its shortest witnesses outside the base bound and report them separately. Completeness is exhaustive only over this declared finite domain and its generated neighbors; report limits plainly, preserve regressions, and permit explicit larger qualification domains without sampling or silently reducing the baseline domain. A future grammar revision changes the inventory digest and must regenerate it.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.

