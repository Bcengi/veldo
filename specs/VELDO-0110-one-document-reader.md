---
schema: veldo.spec/v1
id: VELDO-0110
title: One strict reader for repository documents
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: []
placement: [contracts]
protected_paths: [".veldo/policy_check.py", "engine/.veldo/policy_check.py"]
footprint:
  - "engine/.veldo/tracker_bridge.py"
  - "engine/.veldo/decision_reviews/REV3-DEC-0001.yaml"
  - "engine/.veldo/tracker_intake.py"
  - "engine/.veldo/budget.py"
  - "engine/.veldo/tracker_mirror.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "engine/.veldo/behavior_floor.py"
  - ".veldo/behavior_floor.py"
  - ".veldo/authorization.py"
  - ".veldo/budget.py"
  - ".veldo/capabilities.yaml"
  - ".veldo/contract_loader.py"
  - ".veldo/cost_to_change.py"
  - ".veldo/decision_review.py"
  - ".veldo/decision_reviews/REV3-DEC-0001.yaml"
  - ".veldo/declared.py"
  - ".veldo/dispatch.py"
  - ".veldo/entity_contract.py"
  - ".veldo/entropy.py"
  - ".veldo/estimate.py"
  - ".veldo/examples/decision-review-example.yaml"
  - ".veldo/examples/estimate-example.yaml"
  - ".veldo/examples/sizing-judgement-example.yaml"
  - ".veldo/examples/toe-reconciliation-example.yaml"
  - ".veldo/fix_validation_record.py"
  - ".veldo/frontier.py"
  - ".veldo/incident_reconcile.py"
  - ".veldo/init_scaffold.py"
  - ".veldo/intent_corpus.py"
  - ".veldo/observability.py"
  - ".veldo/plan.py"
  - ".veldo/policy_check.py"
  - ".veldo/release_contract.py"
  - ".veldo/shape_gate.py"
  - ".veldo/toe_budget.py"
  - ".veldo/toe_corpus.py"
  - ".veldo/tracker_bridge.py"
  - ".veldo/tracker_intake.py"
  - ".veldo/tracker_mirror.py"
  - ".veldo/validate.py"
  - ".veldo/validate_checks.py"
  - ".veldo/work_state.py"
  - ".veldo/yamlish.py"
  - "engine/.veldo/authorization.py"
  - "engine/.veldo/capabilities.yaml"
  - "engine/.veldo/contract_loader.py"
  - "engine/.veldo/cost_to_change.py"
  - "engine/.veldo/decision_review.py"
  - "engine/.veldo/declared.py"
  - "engine/.veldo/dispatch.py"
  - "engine/.veldo/entity_contract.py"
  - "engine/.veldo/entropy.py"
  - "engine/.veldo/estimate.py"
  - "engine/.veldo/examples/decision-review-example.yaml"
  - "engine/.veldo/examples/estimate-example.yaml"
  - "engine/.veldo/examples/sizing-judgement-example.yaml"
  - "engine/.veldo/examples/toe-reconciliation-example.yaml"
  - "engine/.veldo/fix_validation_record.py"
  - "engine/.veldo/frontier.py"
  - "engine/.veldo/incident_reconcile.py"
  - "engine/.veldo/init_scaffold.py"
  - "engine/.veldo/intent_corpus.py"
  - "engine/.veldo/observability.py"
  - "engine/.veldo/plan.py"
  - "engine/.veldo/policy_check.py"
  - "engine/.veldo/release_contract.py"
  - "engine/.veldo/shape_gate.py"
  - "engine/.veldo/toe_budget.py"
  - "engine/.veldo/toe_corpus.py"
  - "engine/.veldo/validate.py"
  - "engine/.veldo/validate_checks.py"
  - "engine/.veldo/work_state.py"
  - "engine/.veldo/yamlish.py"
  - "scripts/*"
  - "engine/scripts/*"
  - "specs/*"
  - "plans/*"
  - "engine/plans/*"
  - "engine/specs/*"
  - "proof/VELDO-0110/*"
behavior_bearing: true
observability:
  error_taxonomy: Refusals distinguish syntax errors, unsupported shapes, absent metadata, and schema errors.
  logs: Every syntax refusal carries its source and physical line where available.
acceptance_criteria:
  - id: AC1
    text: One standard-library parser preserves supported values and refuses ambiguous or unsupported syntax, duplicate keys, and malformed structures.
    falsified_by: Ignore a duplicate key or strip a hash inside quotes; the shared reader behavior tests must fail.
  - id: AC2
    text: Before migration, compare all 331 baseline documents against each existing reader and commit exact differences and refusals.
    falsified_by: Omit an input or change a recorded input hash; the complete baseline inventory assertion must fail.
  - id: AC3
    text: Every production reader uses the shared syntax boundary, and writers produce syntax the reader accepts. Both engine copies and init substrate lists include it.
    falsified_by: Restore a private reader or remove the shared module from an init list; the boundary or substrate assertion must fail.
  - id: AC4
    text: The full gate runs the boundary and reader regressions, and reports any failure without treating a partial run as success.
    falsified_by: Add a renamed copy of the old parser in a temporary tree; the boundary test must detect the new source file.
required_evidence: [unit, integration]
rollback: Revert the parser migration and document rewrites together; never restore just one reader.
---

The work contract is the owner's explicit one-parser request on branch one-parser.
The parser and corpus report were committed first, as that request requires. This
record binds the resulting evidence directory to the repository's spec roster; it
adds no approval and makes no claim of independent review or shipped status.
