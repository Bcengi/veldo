---
schema: veldo.spec/v1
id: WARP-0725
title: A forged verdict still lands from a folder inside our own repository, because entitlement asks whether
  two paths share a work tree instead of whether the key came from the projection's own domain - state the
  property once and derive entitlement from the enumeration, never from a path comparison
status: ready
risk: critical - this is the guard that decides whether an agent can mark its own homework, which is the one
  claim the product is sold on, and it has now been defeated seven times in seven different spellings. The
  danger in the permissive direction is what is live today: a forged PASS that resolves, survives a fresh
  clone, is counted by our own metrics, and can never be withdrawn from an append-only log. The danger in the
  strict direction is worse than the defect, because an entitlement rule drawn too narrowly stops the
  projection recording GENUINE verdicts at all, and a review log that silently stops recording is
  indistinguishable from a repository where nobody reviewed anything. It is critical rather than high because
  no narrower framing has survived: rounds 4 to 9 of WARP-0722 each closed a route and each left the property
  unstated
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-07-29
approval_record: >
  GIVEN ON TELEGRAM, 2026-07-29 11:14 UTC, answering a question that put the uncomfortable possibility in
  front of him rather than hiding it. He was told: "It is the guard your product is sold on and it may turn
  out to be unfixable inside that module, in which case the answer becomes signing the log. Say yes and I
  build it, say no and the hole stays documented and open." His answer, verbatim, as item 2 of three:
  "Yes". So the approval is informed - he approved a CRITICAL item knowing its honest outcome may be a
  refusal to fix it in place.
  RECORDED, NOT PERFORMED. The agent writes down the decision the owner made and never makes one for him.
  Noted for a later reader: this is a Telegram instruction rather than a ticket transition, weaker evidence
  than the VEL-9 precedent on WARP-0712, and accepted because he had explicitly told the agent to stop
  seeking ceremony and finish.
lane: standalone
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/events.py"
  - "packs/*/.veldo/events.py"
  - "engine/.veldo/events.py"
  - "scripts/selftest.py"
  - "specs/WARP-0725-entitlement-is-the-projections-domain.md"
  - "proof/WARP-0725/**"
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      ENTITLEMENT IS MEMBERSHIP IN THE PROJECTION'S OWN DOMAIN, AND THE DOMAIN IS THE AUTHORITY. A derived key
      is entitled if and only if it is a member of the enumeration the projection derives from the verdict
      artifacts THIS LOG'S OWN REPOSITORY TRACKS - the repository being fixed by the LOG's path, and the
      enumeration being computed from what git reports as tracked under the declared proof root. Entitlement
      must NOT be decided by comparing two paths, two work trees, two toplevels, or any other relation
      between the artifacts and the log: that is a stand-in for the property, and every such stand-in has
      been defeated. A selftest asserts the entitled set EQUALS the enumeration in BOTH directions over this
      repository's real corpus, not merely that it covers a sample, because a one-directional check is what
      let the current hole through.
  - id: AC2
    text: >
      THE MEASURED FORGERY IS REFUSED, driven exactly as it was found. MEASURED at 18e6ca8 and reproduced
      independently at ecb1079: `mkdir -p tools/qa/proof/WARP-0712`, commit a verdict-shaped file there, then
      `python3 .veldo/events.py reconcile-verdicts --repo-root tools/qa --log .veldo/events.jsonl` exits 0 and
      appends a `verdict.recorded` declaring the reconciler's own producer, carrying a REAL 40-hex
      verdict_blob, log md5 054b25a1 -> 515047ce. A selftest drives that exact sequence and requires a
      non-zero exit with the log BYTE-UNCHANGED, proven by reading the log back. It also drives the variant
      that made it harmful: `git rm -r tools && git commit` afterwards leaves the blob reachable from history,
      so the forged event still resolves in a FRESH CLONE while `git ls-files 'proof/*/verdict*.json'` does
      not contain the artifact - the event asserts a pass for a review the enumeration does not contain, and
      THAT is the condition to refuse.
  - id: AC3
    text: >
      THE INVERSE HARM IS A REQUIRED LEG, NOT AN AFTERTHOUGHT, because it is worse than the defect. A
      selftest runs `reconcile-verdicts` over this repository's real committed artifacts and asserts all of
      them are appended, that a second run appends nothing and reports them already recorded, and that the
      gate's own review-events stage still reports zero derivable-but-not-appended. If the new rule withholds
      even one genuine verdict, the item FAILS, and the honest response is to say the property cannot be
      stated this way rather than to widen it until the forgery returns.
  - id: AC4
    text: >
      NO STAND-IN SURVIVES IN THE CODE OR IN THE PROSE. The words comparing artifacts to the log by work
      tree, toplevel or enclosure are DELETED from the module and its eight copies, not narrowed, because
      they describe a mechanism this item removes. Every remaining sentence about what cannot land states
      only what a driven route measured. The declared limits stay declared and are named as limits: a writer
      that never imports the module, and arbitrary in-process Python, neither of which this item can refuse
      and both of which can already append to the file directly.
  - id: AC5
    text: >
      THE GUARD IS DRIVEN AGAINST A COPY, and every route is generated FROM the module's own constants rather
      than written down here, so a future reserved name or event type is driven without editing this list. No
      count of routes, copies, keys or corpus items is asserted anywhere; only a property of each member.
required_evidence: [unit, baseline]
rollback: revert the commit. The rule is one predicate and nothing persists, but note that any forged line
  already appended to a log cannot be rolled back by anything - which is the reason this item exists.
---

> **RETIRED 2026-08-02 BY WARP-0731. THIS SPEC IS HISTORY, NOT WORK.** Its rule was correct and it
> held. It is gone anyway, because WARP-0730 moved verdict authority out of the agent and so removed
> the value of the forgery this guard prevented: nothing authoritative reads `verdict.recorded` any
> more. WARP-0731 deleted `log_entitlement`, the frozenset threaded through four functions, the
> `unentitled` report field and CLI exit code 2, and with them the six `expect()` calls in
> `scripts/suites/13_warp_0623_codified_live.py` that witnessed this item's ACs.
>
> **What survives, and is still tested there:** the API-hygiene half - only the projection writes
> projection-owned events - now carried by a boolean on the reconciler's own append path, plus the
> positive control that the projection still records its own domain. **What does not survive:** the
> membership rule, so a key outside the log's own domain can be appended again. That weakening is
> deliberate and is declared in WARP-0731 AC3.
>
> The status field below still reads `ready` because the schema has no `superseded` value. Do not
> pick this up as work.

## Intent

WARP-0722 spent nine build rounds on one question and never wrote the question down. Each round closed a
route: the constructor, the type argument passed to `emit`, the type read off the assembled dict, the origin
compared by work tree, a cardinality, the write-surface discovery. **Every one of those guards a description
of the thing rather than the thing.** The property was never stated, so each fix was a patch and the next
attacker simply found the next spelling.

The property is this: **the review log is the projection of one repository's committed verdict artifacts, so
a line is entitled if and only if its key is a member of the enumeration that projection produces.** Not "if
the artifacts live near the log". Not "if the two paths share a work tree". Membership in the domain, with
the domain as the authority.

## Context

The live defect, reproduced twice: a directory INSIDE our own work tree passes the current work-tree
comparison, so `log_entitlement` entitles keys derived from any folder in the repository. The result is not a
curiosity. The forged line carries a real blob so it resolves as a **pass** rather than an error; deleting
the folder afterwards does not help because the blob stays reachable in history; `validate.py` exits 0 and
the suite prints its baseline count, so the gate cannot see it; and `.veldo/metrics.py` counts it, moving the
published tally from 38 passes to 39. An agent marks its own homework, the method's own numbers report it,
and the log is append-only so it can never be withdrawn.

What is NOT wrong is the machinery around it. An independent review drove **18 CLI routes and 9 in-process
routes** that were all refused with the log byte-identical, and every figure it recomputed was true. The
derivation, the content key, the readback assertion and the idempotence are sound. **It is the domain that is
wrong, and only the domain.**

## Out of scope

The reserved envelope keys are WARP-0723 and are landed. The frontier's dependency dispatch is WARP-0724 and
is landed. A writer that never imports the module - a shell append, a hand-edited log - is refusable by
nothing inside the module and belongs to the signed-log question. Arbitrary in-process Python is likewise
out of reach and already able to append directly; it is declared as a limit, not defended against.

## Approval

It is `critical` because it is the guard the product is sold on. The owner approved it having been told the
honest outcome may be that the property CANNOT be enforced from inside the module - in which case this item
must say so plainly and the signed-log question becomes the real work. **Reporting that conclusion, if it is
what the measurements support, is satisfying this spec and not failing it.** See `approval_record`.
