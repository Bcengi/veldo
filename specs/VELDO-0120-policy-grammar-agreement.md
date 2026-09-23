---
schema: veldo.spec/v1
id: VELDO-0120
title: Preserve policy settings across the generated shared-reader grammar
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0106, VELDO-0118]
placement: [engine, contracts]
protected_paths: []
footprint:
  - ".veldo/fix_validation_record.py"
  - "engine/.veldo/fix_validation_record.py"
  - "scripts/suites/45_veldo_0106_policyread.py"
  - "scripts/suites/*_veldo_0120_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0120-policy-grammar-agreement.md"
  - "specs/index.md"
  - "proof/VELDO-0120/*"
behavior_bearing: true
observability:
  logs: >
    Record policy derivation, required/from_commit outcomes, exact spelling differences and named syntax or schema refusals.
  metrics: >
    Report grammar-derived policy cases, oracle comparisons, refusals and unobserved cases.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish syntax_refused, policy_shape_refused, setting_disagreement and oracle_unavailable.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The two owner settings retain their schema-defined meaning across every supported generated policy spelling.
      Set: VELDO-0118's complete supported coverage-generated grammar witnesses embedded into the policy envelope at root, fix_validation and its required/from_commit fields; include block/flow forms, quoted and plain hashes, comments, BOM, line endings and all documented boolean spellings and commit-id lexical classes.
      Completeness: Construct the policy product mechanically from the shared grammar and the policy schema's field/value partitions; record expected and executed identities and compare exact flag and start-line outcomes to the independent oracle tree plus a separate schema adapter. Leading-zero commit ids stay strings and quoted hashes stay data; document intentional dialect differences rather than excluding them.
      Refutation: policyread/generated-settings-agree is false if any supported policy form loses or changes a setting or is unexpectedly refused.
    falsified_by: >
      Strip trailing hash text from quoted from_commit values before schema interpretation; policyread/generated-settings-agree must turn red.
  - id: AC2
    text: >
      Claim: Unsupported generated syntax and invalid policy shapes are refused and never interpreted as an absent enforcement setting.
      Set: Every VELDO-0118 boundary edit applicable to the generated policy envelopes, plus each schema-invalid field shape, including scalar/list where fix_validation must be a map and a mapping where a setting must be scalar.
      Completeness: Cross the shared exclusion rules with the schema's invalid-type partitions and require every generated case to terminate in its expected syntax or schema refusal. Inputs valid as general YAML but outside the shared dialect must still refuse; valid truly absent settings retain their documented defaults as positive controls.
      Refutation: policyread/generated-invalid-is-not-absent is false if malformed or unsupported content yields the default disabled flag or empty start line.
    falsified_by: >
      Catch a shared-reader syntax error and return an empty policy mapping; policyread/generated-invalid-is-not-absent must turn red.
  - id: AC3
    text: >
      Claim: Policy agreement evidence is complete over the declared generated product and honest about optional PyYAML.
      Set: The entire policy product with the oracle present, absent or broken, and a run missing one expected policy result.
      Completeness: Require exact expected/executed/compared inventory equality for qualified agreement. An absent oracle produces a named oracle_unavailable stand-down with zero comparisons, while required stdlib grammar and schema refusal checks run; independent qualification stays open until a provisioned run completes.
      Refutation: policyread/generated-oracle-coverage-is-honest is false if a missing comparison or absent oracle counts as agreement.
    falsified_by: >
      Report independent agreement when PyYAML is absent; policyread/generated-oracle-coverage-is-honest must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Replace the seventeen-example policy agreement claim with reproducible grammar-derived coverage.

## Context

VELDO-0106 AC1 and proof/VELDO-0106/README.md:115-120 explicitly leave grammar-wide agreement unproven. This consumer uses the VELDO-0118 generator and oracle, also consumed by VELDO-0119.

## Out of scope

A policy-specific YAML grammar/parser/generator, ancestry resolution behavior, writer round trips and mandatory runtime PyYAML.

## Notes

The policy envelope adds the schema's required nodes to every coverage-generated syntax witness from VELDO-0118; there is no exhaustive three-node base domain. Publish that deterministic construction and its complete count; never discard cases after seeing production answers. Compare syntax-preserved start-line values before commit-resolution checks, keeping lexical correctness distinct from whether an object is present in the repository.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.

## History (2026-09-22)

VELDO-0118's exhaustive bounded domain was replaced by owner-approved grammar
coverage criteria. Only AC1's domain reference and the Notes reference to the
three-node bound change here. The complete generated policy product and its
agreement, refusal and oracle-accounting obligations are unchanged.

## Implementation history (2026-09-22)

The owner-authorized footprint extension to `scripts/fixtures/*` adds the shared
policy consumer, using VELDO-0118 rendering, edits and oracle composition rather
than introducing a policy YAML grammar. The owner-authorized extension to
`scripts/check_teeth_mutations.py` registers two assertion-driven mutations per
criterion because the required gate mutation stage postdates this specification.

Measurement precedes suite rows: the naive product contains 1,668,600 inputs;
the first coverage construction contains 8,093, generated in 1.804 seconds and
checked through both readers and the oracle in 0.737 seconds. The projected
full-product checking time alone is 151.9 seconds, so construction uses coverage.
The initial measurement retains the root-scalar classification discrepancy;
root scalars require syntax refusal under the documented shared dialect.

The final coverage construction has 8,196 inputs: 6,180 witness/site embeddings,
1,792 direct scalar lexical placements, 133 schema partitions and spellings, and
91 additional edits directly on policy nodes. Both unchanged shipped readers
agree with every independent observation. Added gate work measured 22.882 seconds
(two suite executions plus the isolated required mutation stage), below the
owner's 60-second ceiling. The owner's policy file and its interpretation are
unchanged. This remains ready pending independent review and landing.
