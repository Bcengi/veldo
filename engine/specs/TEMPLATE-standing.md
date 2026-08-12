---
schema: veldo.spec/v1
id: VELDO-STANDING-0000
title: <recurring change class, e.g. dependency updates>
status: ready
risk: standard
owner: <the human accountable for the class>
human_approval: not_required
protected_paths: []
# behavior_bearing (PLAN-0012 W9). Whether this class carries product behavior. When true, the
# spec declares observability criteria (logs, metrics, traces, error_taxonomy) and EVERY
# acceptance criterion below declares its own falsified_by. A standing spec is not exempt: a
# recurring change class that carries behaviour carries it on every instance.
# behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: <holds for EVERY instance of this class>
    # falsified_by is THE NEGATIVE CONTROL, declared in the criterion itself: the single change
    # to the implementation that must make this criterion's check fail. Required on every
    # criterion of a behavior_bearing spec, one statement, no exemption keyword. On a STANDING
    # spec it earns its place twice over, because the criteria are written once and then relied
    # on by every future instance, so a criterion that cannot fail here cannot fail for any of
    # them. Drive it rather than declaring it: apply the mutation, prove with a diff that it
    # landed, require the row this criterion names to go red, then revert.
    falsified_by: <the one change to the implementation that must turn this criterion red>
required_evidence: [unit]
rollback: <class-level rollback, e.g. revert the bump commit>
---

## Intent

A standing specification: defined once for a recurring, mechanical change
class. Each instance (a dependency bump, a copy correction) runs the normal
loop against these criteria without a fresh spec.

## Instances

Log instances here or reference them by commit.
