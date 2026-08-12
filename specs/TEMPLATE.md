---
schema: veldo.spec/v1
id: VELDO-0000
title: <short title>
status: draft            # draft | ready | in_progress | review | proven | shipped | blocked
risk: standard           # declared floor; policy may raise it, nothing may lower it
owner: <the human accountable for the intent>
human_approval: not_required
lane: standalone         # standalone (bug/isolated) | planned (bound to a Product Plan)
# For lane: planned, also set plan: PLAN-NNNN, work: Wn (mirrored to the plan),
# and plan_revision: N (the plan revision it was pulled against; run-check
# refuses to build against a stale revision).
# Placement and footprint (PLAN-0011 W3). When the repository carries an architecture
# contract (.veldo/architecture.yaml), a spec declares where its change lands (placement)
# and what it touches (footprint), validated against the contract's areas. MANDATORY
# once a contract exists: a spec may not reach ready and is never claimed without a
# placement that resolves to a contract area, and a footprint that crosses an area
# boundary raises the risk tier (nothing lowers it). When no contract exists, both stand
# down and the spec is unaffected. Run python3 .veldo/validate.py ready <file> before
# promoting to ready.
# placement: [<area-id>]         # one or more area ids the contract declares
# footprint: [<path-glob>, ...]  # the path globs this change is allowed to touch
protected_paths: []
# behavior_bearing (PLAN-0012 W9). Whether this change carries product behavior. When true,
# the spec declares observability criteria (logs, metrics, traces, error_taxonomy) and EVERY
# acceptance criterion below declares its own falsified_by.
# behavior_bearing: true
acceptance_criteria:
  # A criterion carries FOUR things, in the criterion itself. The fourth is CHECKED on a
  # behavior_bearing spec - `python3 .veldo/validate.py all` refuses a criterion with no
  # falsified_by, and `ready` refuses it before the spec can be claimed - so this is a prompt
  # for a rule that already bites, not advice. The other three are here because they are what
  # made a criterion checkable in practice, and because leaving any one out has cost this
  # project whole weeks:
  #   WHAT IS CLAIMED     the property that becomes true, stated so it could be false
  #   OVER WHAT SET       the domain it holds over, declared rather than implied
  #   HOW COMPLETENESS    why that set is the WHOLE set - by construction, or by
  #     IS KNOWN          measurement, never by having thought hard about it
  #   WHAT WOULD REFUTE   the observation that would prove the claim false, and
  #     IT                where the evidence looks for it
  # A criterion missing the domain is unfalsifiable, because any counterexample can
  # be ruled out of scope afterwards. One missing its completeness method is a list
  # someone believes is complete. One missing its refutation is ceremony.
  - id: AC1
    text: <observable, testable requirement>
    # falsified_by is THE NEGATIVE CONTROL, declared in the criterion itself: the single
    # change to the implementation that must make this criterion's check fail. Required on
    # every criterion of a behavior_bearing spec, one statement, no exemption keyword. A
    # criterion that names no way to be proven wrong leaves the implementer to invent the
    # falsification, and the cheapest invention is one that passes.
    # AND IT IS NOT ENOUGH TO DECLARE IT. Twelve independent reviews of PLAN-0018 drove these
    # clauses instead of reading them and found criteria whose declared mutation leaves the
    # suite fully green, so the check could not fail for the defect its own text names. Drive
    # your own: apply the mutation, prove with a diff that it landed, require the row this
    # criterion names to go red, then revert.
    falsified_by: <the one change to the implementation that must turn this criterion red>
required_evidence: [unit]
rollback: <how this change is reverted or disabled>
---

## Intent

What outcome should become true, and why it matters.

## Context

Relevant background: product, technical, operational.

## Out of scope

What this change must not touch.

## Notes

Anything the implementing or reviewing agent needs.
