---
schema: veldo.spec/v1
id: WARP-0622
title: The structural no-bypass proof, the end-to-end conformance suite, and PLAN-0016's release - a
  human decision must arrive as an attested record and never as an answer typed at a prompt
status: ready
risk: standard - the no-bypass check adds a gate stage over a property that already holds, so it
  cannot break work today. It is not low because a check that is wrong in the permissive direction
  would certify a bypass as absent, and this one is the last structural guard on the human-decision
  surface.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W9
depends_on: [WARP-0617, WARP-0618, WARP-0620, WARP-0621]
placement: [enforcement]
footprint:
  - ".veldo/no_bypass.py"
  - "engine/.veldo/no_bypass.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/11_inbound_command_receipt_reconcile.py"
  - "specs/WARP-0622-conformance-no-bypass-release.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      NO CODE PATH IN THE DECISION SURFACE READS A HUMAN DECISION FROM A TERMINAL. A structural check
      over a WRITTEN-DOWN surface of eleven modules refuses any call to `input`, `raw_input`, anything
      through `getpass`, a read on `sys.stdin`, or `builtins.input`. A module named in the surface that
      does not exist is itself reported, so deleting one cannot silently shrink what is checked.
  - id: AC2
    text: >
      IT PARSES RATHER THAN GREPS, AND THE DIFFERENCE IS PROVEN. A string search matches the word in a
      comment, in a docstring and in `n_inputs(`, and misses `builtins.input()`. The check walks the
      AST. A selftest drives every spelling that must be CAUGHT and every lookalike that must stay
      CLEAN, so the leg cannot pass by being either blind or hysterical. A module that will not parse
      is reported as unverifiable rather than passed.
  - id: AC3
    text: >
      THE LIMIT IS STATED IN THE MODULE, because this one is easy to overclaim. It proves no module in
      the surface CALLS a terminal read. It cannot prove a human decision did not arrive some other
      way - an environment variable, a file a person edited, an agent relaying what somebody said in
      chat. What it removes is the easiest and most tempting bypass, the one added at four in the
      morning because the approval flow is slow.
  - id: AC4
    text: >
      THE END-TO-END CONFORMANCE SUITE IS BUILT, over the fake tracker, driving the REAL reconcile:
      replay, spoofed actor, automation transitions, workflow edits, downtime, secret rotation,
      concurrent artifact changes, repository conflicts and revocation. Nine scenarios, enumerated
      once so dropping one is a failure rather than a quietly smaller suite, each with a control
      beside it and each pinning an EXACT outcome - an assertion that accepts either of two outcomes
      proves nothing.
  - id: AC5
    text: >
      WHAT THE SUITE FOUND IS RECORDED, NOT SMOOTHED OVER. A renamed board state settles nothing (the
      safety property holds) but reports the same reason as a genuinely pending request, so an
      operator reading it waits for a decision that already happened. The scenario pins that wording
      and names the gap, because a conformance suite that only confirms what was expected is a suite
      that was written to pass. Writing it also caught one of its own tests passing for the WRONG
      REASON - a fake raising an exception name that does not exist, so the outage scenario was
      testing an AttributeError - which is why every refusal here pins its reason and not just its
      outcome.
  - id: AC6
    text: >
      STILL NOT DONE, AND NAMED RATHER THAN QUIETLY DROPPED: the plan's release. It cannot happen
      while WARP-0620 is blocked on its live board run, which needs a human at a keyboard for about
      thirty minutes. Claiming this item shipped would be false, so this spec stays `ready`. The
      no-bypass check and the conformance suite are both done and green; the board run is the only
      thing left in the way.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It adds one read-only check over source text and changes
  no behaviour, writes no state and blocks nothing that passes today.
---

## Outcome

A human decision reaches this system as a RECORD: an attested approval, or a tracker transition with
an attributed changelog. Never as an answer typed at a terminal.

That is not style. A terminal answer has no approver identity that survives the process, no binding
to the artifact it approved, no expiry, and no audit trail. Every guard built on those four things -
separation of duties, the digest binding, the two-key rule, the execution binding - is bypassed the
moment one exists. The owner reached the same rule independently and stated it as an instruction:
never approve risky work by a terminal yes or no.

**Today no module does this, and that is precisely why the check is worth having.** Keeping a true
property true costs one gate stage. Discovering it stopped being true costs an approval nobody can
attribute, in a log nothing can rewrite.

## Why it parses instead of grepping

A grep for `input(` matches a comment, a docstring and `n_inputs(`, and misses `builtins.input()`
and an aliased import. The argument is not theoretical: three separate answers given during this
plan's work were wrong because they were grep-shaped, including two counts of the work itself. The
AST knows the difference between a call and prose.

## What is deliberately not done here

The conformance suite and the plan's release. The release depends on WARP-0620, which is blocked on
a live board run, so this spec stays `ready` rather than claiming a completion it has not earned.
Naming that in AC4 is the point: an item that quietly drops two of its four concerns looks finished
and is not.
