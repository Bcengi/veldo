---
schema: veldo.spec/v1
id: VELDO-0119
title: Measure shared-reader agreement over the generated grammar domain
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0110, VELDO-0118]
placement: [contracts]
protected_paths: []
footprint:
  - ".veldo/yamlish.py"
  - "engine/.veldo/yamlish.py"
  - "scripts/suites/*_veldo_0119_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0119-shared-reader-grammar-agreement.md"
  - "specs/index.md"
  - "proof/VELDO-0119/*"
behavior_bearing: true
observability:
  logs: >
    Name input digest, grammar derivation, differing field/type/value, refusal source/line and oracle qualification status.
  metrics: >
    Report exact generated, read, refused, compared and unobserved input counts.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish supported_input_refused, value_disagreement, unsupported_input_accepted and oracle_unavailable.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Both shipped copies of the shared reader preserve the structure, values and dialect-defined scalar types of every generated supported input.
      Set: Every accepted-domain input exported by VELDO-0118, run independently through .veldo/yamlish.py and engine/.veldo/yamlish.py.
      Completeness: Require each copy's executed digest/derivation inventory to equal the generator's inventory and compare exact typed trees to the external parser plus the fixture's independently specified dialect adapter. Preserve raw YAML observations so intentional boolean/leading-zero differences remain visible; no success filtering.
      Refutation: reader/generated-grammar-agrees is false on a missing case, unexpected refusal or any structural/value/type difference.
    falsified_by: >
      Strip a hash inside a quoted scalar in the production reader; reader/generated-grammar-agrees must turn red.
  - id: AC2
    text: >
      Claim: Generated out-of-dialect inputs refuse rather than silently produce a plausible document.
      Set: The complete generated boundary set from VELDO-0118, retaining separate classifications for invalid YAML and valid YAML outside the supported subset.
      Completeness: Require an observed refusal for every expected boundary input in each reader copy; source and physical line are checked where available. General YAML acceptance is not permission for the restricted reader to accept excluded syntax.
      Refutation: reader/generated-boundaries-refuse is false for any unsupported input accepted or collapsed into absent metadata.
    falsified_by: >
      Allow a duplicate mapping key to overwrite its earlier value; reader/generated-boundaries-refuse must turn red.
  - id: AC3
    text: >
      Claim: The grammar-agreement result names exactly the domain compared and never closes the gap without independent observations.
      Set: Complete fixture runs with PyYAML present, absent, broken and with one generated input deliberately omitted from execution.
      Completeness: Join both reader result inventories to the fixture inventory and require complete independent comparisons to emit qualified agreement. Without PyYAML, generated execution/refusal checks remain required and the agreement row stands down as oracle_unavailable; a provisioned qualification run remains outstanding.
      Refutation: reader/agreement-requires-full-oracle-domain is false if an omitted input or missing oracle yields qualified agreement.
    falsified_by: >
      Count oracle_unavailable inputs as successful comparisons in the reader report; reader/agreement-requires-full-oracle-domain must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Turn the shared reader's grammar agreement into a measured domain property with visible limits.

## Context

VELDO-0106's evidence gap refers to the shared reader introduced by VELDO-0110. VELDO-0110 AC6 and proof/VELDO-0110/README.md:69-73 describe generated writer round trips; they do not establish exhaustive coverage of the written reader grammar.

## Out of scope

Another generator or oracle adapter, policy-schema interpretation, writer coverage and changing the supported syntax.

## Notes

Consume VELDO-0118 verbatim. Report its finite bounds and grammar digest with results; this does not claim all unbounded strings have been checked. If a mismatch reveals a grammar ambiguity, resolve the written contract before altering expected data, rather than letting the implementation redefine the domain.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
