---
schema: veldo.spec/v1
id: WARP-0734
title: A spec belonging to no plan must SAY so - reading the plans to answer "what work is left" silently
  omitted every spec that named no plan, and the answer was wrong three times in one evening
status: shipped
risk: standard - one new refusal in the spec contract, closing a branch that returned 0. It is not low
  because a validator that refuses too much stops all work; the mitigation is that the refusal is
  satisfied by adding one already-defined field, and every existing spec was brought into compliance in
  this same change rather than left to fail later.
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [contracts]
footprint:
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - "specs/WARP-0100-adopt-veldo.md"
  - "specs/WARP-0113-review-findings-hardening.md"
  - "specs/WARP-0114-approval-range-binding.md"
  - "specs/WARP-1212-two-key-freshness-fail-closed.md"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-0734-no-undeclared-orphan-specs.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      A SPEC THAT NAMES NO PLAN AND NO STANDALONE LANE IS REFUSED. `check_spec_plan_binding` used to
      `return 0` for any spec without a plan, which made a deliberately standalone spec and one whose
      author simply never said indistinguishable. It now requires `lane: standalone` in that case and
      fails by name otherwise. A selftest drives all three shapes: no lane refused, `lane: planned`
      without a plan refused, `lane: standalone` permitted.
  - id: AC2
    text: >
      THE EXISTING CORPUS IS BROUGHT INTO COMPLIANCE IN THIS CHANGE, not left to fail later. Four specs
      declared neither - WARP-0100, WARP-0113, WARP-0114 and WARP-1212 - and each gains `lane:
      standalone`, which is true of all four. A validator that starts refusing without fixing what it
      refuses is a validator someone disables.
  - id: AC3
    text: >
      THE COUNT BECOMES TRUSTWORTHY, WHICH IS THE POINT. After this, every spec is either bound to a
      plan work item that exists (already enforced) or explicitly standalone, so "what work is left" has
      one answer reachable from the plans plus the declared-standalone set, with nothing able to sit
      outside both. A selftest asserts the real corpus has ZERO specs declaring neither.
required_evidence: [unit]
rollback: >
  Revert. The refusal is one branch and the four spec edits are one added line each; nothing executable
  changes and no state is written.
---

## Outcome

Asked what work remained, three different counts were given in one evening and all three were wrong,
in different directions. The cause was not carelessness in any single count. It was that the question
"what work exists" had no single answer the repository could give.

Work could live in a plan work list, or in a spec that named no plan, and nothing required the second
kind to announce itself. So reading the plans - the documented way to see the work - silently omitted
an entire category, and reading the specs folder instead over-counted, because a spec that merely
mentions a plan in its prose is not a work item of it.

**The method claims the repository is the system of record. A record you can read correctly and still
get a wrong answer from is a dashboard, not a record.** This closes that.

## What it does not fix

It does not make a spec's plan membership correct, only declared. A spec that should belong to a plan
and says `lane: standalone` is now visible but still mis-filed, and no validator can tell the
difference between a deliberate standalone and a mis-filed one. What it guarantees is that neither can
be INVISIBLE, which is the failure that actually happened.

It also does not reach artifacts held outside `specs/` entirely - `docs/design/held-back/` carries two
of those, quarantined deliberately and with a README naming the reason. That is a third place work can
live and this item does not enumerate it.
