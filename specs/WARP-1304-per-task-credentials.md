---
schema: veldo.spec/v1
id: WARP-1304
title: Scope is derived from the task, never requested by the agent - because an agent that widens its
  own request until the work succeeds is how least privilege actually dies
status: shipped
risk: standard - a pure issuance model over a fake issuer that mints nothing real. It is not low
  because it decides what an agent may reach, and a permissive error here hands out exactly the
  organization-wide key the whole model exists to prevent.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W4
depends_on: [WARP-1301]
placement: [contracts]
footprint:
  - ".veldo/credential_issue.py"
  - "engine/.veldo/credential_issue.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1304-per-task-credentials.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      SCOPE IS DERIVED FROM THE TASK'S DECLARATION, AND A REQUEST CANNOT EXCEED IT. Anything asked
      for that the task did not declare refuses `scope_exceeds_task_declaration`. The failure mode
      being prevented is not malice: it is an agent that hits a permission error, widens the
      request, and succeeds. The declaration is written when the work is specified, by somebody
      thinking about the work rather than about getting unblocked.
  - id: AC2
    text: >
      A FLOOR EXISTS UNDER THE DECLARATION ITSELF. `*`, `admin`, `owner`, `root`, `org:admin` and
      `billing` are never issuable to an agent whatever a task declares, because a person in a hurry
      can write `*` and the declaration is written by a person. A task declaring nothing at all also
      refuses, since there is nothing to derive from.
  - id: AC3
    text: >
      EXPIRY IS ENFORCED AT USE, NOT ONLY AT ISSUE. A credential checked only when handed out works
      forever in practice, because the check happens at the moment nobody is worried.
      `authorize_use` re-checks expiry, the scope, and optionally the task, each refusing by its own
      name. A selftest drives each separately with the working case beside them.
  - id: AC4
    text: >
      ATTRIBUTION IS PART OF THE CREDENTIAL, NOT A LOG LINE BESIDE IT. Agent and task are fields, so
      an audit answers "who did this" from the credential itself rather than by correlating
      timestamps across two systems. The token is opaque: `__repr__` shows agent, task, scopes and
      expiry and never the token, for the same reason the secret handle does not render its value.
  - id: AC5
    text: >
      FAKE ISSUER ONLY. The module mints nothing real and reaches nothing; `Issuer` is the seam a
      real one is wired to, per system, deliberately, by a person. A selftest asserts it imports
      nothing that could reach a credential service.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It issues nothing real, holds no state beyond the
  fake issuer's list, and no caller depends on it yet.
---

## Outcome

A credential is issued FOR one task, scoped to what that task declared, expiring on its own, and
attributable to the agent that used it.

## The inversion that is the whole design

**Scope is derived from the task, not requested by the agent.**

If an agent asks for scopes, it will ask for the ones that make its work succeed. The honest failure
mode is not an agent trying to over-reach: it is an agent hitting a permission error, widening the
request, and getting on with the job. Everyone has done this. It is reasonable behaviour and it is
exactly how least privilege dies, one unblocked task at a time.

So the declaration comes from the specification, written by somebody thinking about what the work
needs rather than about getting unblocked, and a request can only ever be a subset of it.

## And a floor under the declaration

The declaration is also written by a person, and a person in a hurry writes `*`. So there is a set
of scopes no agent is ever issued regardless of what any task declares. A rule that can be widened
by editing one line of the thing it governs is not a rule.

## Expiry where it actually bites

At USE, not only at issue. A credential validated when handed out and never again works forever in
practice, because the only check happens at the moment nobody is worried about it.
