---
schema: veldo.spec/v1
id: VELDO-STANDING-0000
title: <recurring change class, e.g. dependency updates>
status: ready
risk: standard
owner: <the human accountable for the class>
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: <holds for EVERY instance of this class>
required_evidence: [unit]
rollback: <class-level rollback, e.g. revert the bump commit>
---

## Intent

A standing specification: defined once for a recurring, mechanical change
class. Each instance (a dependency bump, a copy correction) runs the normal
loop against these criteria without a fresh spec.

## Instances

Log instances here or reference them by commit.
