---
schema: veldo.spec/v1
id: WARP-0624
title: The machine-actor guard must key on STRUCTURAL machine-ness, not on a name guess - the live proof
  showed the real agent identity is not in the name list and that the tracker's own account-type signal
  is never consulted, so an actor whose humanness cannot be ESTABLISHED must be refused rather than
  assumed human (hardening of the PLAN-0016 authorization core, found by WARP-0620)
status: shipped
risk: high - this changes the AUTHORIZATION CORE, the module that decides whether a human decision is
  authorized, and it changes a REFUSAL rule rather than an accessory. Per PLAN-0016 constraint C2 an item
  touching the authorization matrix carries a high floor with RECORDED HUMAN APPROVAL, and this qualifies:
  it alters who can settle a human decision. It is high and not critical because it only ever makes the
  guard refuse MORE, never less: the existing name list is kept as an additional refusal, so no actor that
  is refused today becomes permitted, and the change is proven offline against the identities the live run
  captured. It touches no protected path (.veldo/authorization.py is deliberately not in policy.yaml's
  protected set) and no gate stage
owner: dmitry
human_approval: required
lane: standalone
depends_on: [WARP-0620]
placement: [engine]
footprint:
  - .veldo/authorization.py
  - .veldo/tracker_adapter.py
  - engine/.veldo/authorization.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - scripts/suites/10_warp_0613_anti_vacuity.py
  - specs/WARP-0624-machine-actor-structural.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: Every refusal names WHICH signal decided it - the reported actor kind, the absence of a kind, or
    the name-list match - so a refused settlement is diagnosable from the output without reading the
    source, and an operator can tell "this actor is a machine" from "this actor's humanness could not be
    established".
  error_taxonomy: The refusal reasons are a closed named set: MACHINE_ACTOR (the tracker reports a
    non-human kind), UNESTABLISHED_ACTOR_KIND (no kind is reported and humanness therefore cannot be
    proven), and the pre-existing name-list refusal retained under its current name so no current refusal
    is renamed or lost.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Add the live agent's normalized display name to the guard's own list, extending MACHINE_ACTORS at
      .veldo/authorization.py:88 with "veldo agent", which is exactly the "just add it to the set" fix this
      item exists to refuse, and the reproduction at scripts/suites/10_warp_0613_anti_vacuity.py:1426 must
      go red because the real identity is no longer OUTSIDE the name list. That assertion IS this
      criterion: it is the evidence the defect was real rather than untidy.
    text: >
      THE DEFECT IS REPRODUCED FIRST, from the identities the live run actually captured. A selftest
      asserts, against the SHIPPED module as it stands, that the real agent identity from the WARP-0620
      live run ("Veldo Agent", the display name of an Atlassian account whose accountType is "app") is NOT
      in MACHINE_ACTORS and is therefore NOT refused by the current guard, while the generic placeholder
      "agent" IS. The same assertion covers the other real-world shapes the live proof and the round-1
      probes exposed: "veldo-agent", "Veldo Bot", "Automation for Jira". This test FAILS on the code as
      shipped and is the evidence that the fix fixes something real rather than tidying a list.
  - id: AC2
    falsified_by: >
      Hand the core the tracker's raw vocabulary: replace the normalize_actor_kind call at
      .veldo/tracker_adapter.py:151 with author.get("accountType"), so a flattened entry carries "app"
      rather than a normalized kind, and the assertion that the live run's "Veldo Agent" entry reads kind
      machine (scripts/suites/11_inbound_command_receipt_reconcile.py:1821) must go red. Normalizing AT THE
      ADAPTER is the load-bearing leg; the core's CONSUMPTION of the kind has its own mutation, deleting the
      actor_kind read at .veldo/authorization.py:306, which reddens
      scripts/suites/10_warp_0613_anti_vacuity.py:1453 and its control at :1460.
    text: >
      MACHINE-NESS BECOMES A REPORTED KIND, NOT AN INFERENCE FROM A NAME. The tracker adapter seam gains
      an actor-kind contract: an attributed changelog entry carries the actor's KIND as the tracker itself
      reports it, normalized to exactly one of human, machine, or unknown, and the mapping from a specific
      tracker's vocabulary to those three lives in that tracker's adapter and nowhere else (Jira's
      accountType "app" and "customer" and any non-"atlassian" value map to machine; GitHub's "Bot" maps
      to machine; an installation or app token maps to machine). The authorization core consumes the
      normalized kind and NEVER parses a display name to decide it. A selftest asserts the mapping for
      every value the live run observed and refuses to let the core see a raw tracker vocabulary.
  - id: AC3
    falsified_by: >
      Restore the pre-WARP-0624 default by changing the fall-through of actor_kind at
      .veldo/authorization.py:319 from "unknown" to "human", so an actor the tracker says nothing about is
      assumed to be a person again, and the assertion that a missing, empty, wrong-typed or
      out-of-vocabulary kind resolves to unknown (scripts/suites/10_warp_0613_anti_vacuity.py:1455) must go
      red while the reported-human control at :1460 stays green. That default is the load-bearing leg,
      because the UNESTABLISHED_ACTOR_KIND refusal at .veldo/authorization.py:372 is only ever reached
      through it.
    text: >
      UNKNOWN IS REFUSED, WHICH IS THE WHOLE POINT (constraint C3, fail closed). An actor whose kind the
      tracker does not report is refused with UNESTABLISHED_ACTOR_KIND: humanness must be ESTABLISHED, not
      assumed from the absence of evidence. This is the inversion the live proof forced - today an
      unrecognized name is treated as human by default, which is precisely how the real agent would have
      settled a decision on any surface without a tracker-side fence. The refusal is proven for a missing
      kind, an empty kind, a kind of the wrong type, and a kind outside the three-value vocabulary. And
      the CONTROL proves it does not over-fire: an actor the tracker reports as human settles exactly as
      it does today.
  - id: AC4
    falsified_by: >
      Drop the retained refusal instead of keeping it: replace the two name-list legs of _is_machine at
      .veldo/authorization.py:337 through :339 with a bare return False, so only a tracker-reported kind
      refuses, and the enumeration over the ENTIRE current MACHINE_ACTORS set
      (scripts/suites/10_warp_0613_anti_vacuity.py:1471) must go red. Keeping the name list is the
      load-bearing leg of this criterion: it is the only thing that makes the new guard a strict superset of
      the old one.
    text: >
      NOTHING PERMITTED TODAY BECOMES PERMITTED, and the existing refusal is kept. The name list is
      RETAINED as an additional, independent refusal rather than replaced, so the guard is a strict
      superset of today's behaviour: every actor refused by the current code is still refused, proven by
      asserting the refusal over the entire current MACHINE_ACTORS set under the new logic. The two-key
      module's own machine-actor set stays byte-compatible (a selftest already binds them and must keep
      passing), and no caller's signature loses a parameter it has today. A change that made the guard
      refuse LESS in any case is a defect, and the suite is written to catch it: the assertion enumerates
      the current set rather than sampling it.
  - id: AC5
    falsified_by: >
      Neutralize the reported-machine refusal ALONE, changing .veldo/authorization.py:335 to read `if False
      and actor_kind(entry) == "machine":`, and the assertion that a tracker-reported machine is refused
      although its name is in no list (scripts/suites/10_warp_0613_anti_vacuity.py:1453) must go red while
      the unknown-kind leg at :1455 and the name-list leg at :1471 stay green. That one-guard-at-a-time
      isolation over the three refusals is what this item SHIPS in place of the matrix this criterion
      describes: measured 2026-08-11, the suite carries no 3-by-3 grid, no off-diagonal list and no sha256
      assertion for this guard, so the per-leg assertions are the only thing a mutation can redden.
    text: >
      THE TEETH ARE A MATRIX over every guard this item touches - the reported-machine refusal, the
      unknown-kind refusal, and the retained name-list refusal - each neutralized in memory one at a time
      and run against every guard's fixture, the matrix asserted EXACTLY DIAGONAL with the off-diagonal
      asserted as an empty list so a stray green names itself, every mutation target asserted to appear
      exactly once, and every touched module asserted sha256-unchanged after all runs. The fixtures use the
      REAL identities the live run captured, not invented ones. The honest boundary, labeled review-lane:
      this guard establishes what the TRACKER reports about an actor; it cannot establish that a human
      account is not operated by a script, which is an access-control question and not a decidable one
      here.
  - id: AC6
    falsified_by: >
      Ship an engine that does not carry the guard: delete the UNESTABLISHED_ACTOR_KIND refusal from
      engine/.veldo/authorization.py:372 through :373 only, leaving the repository copy intact, and the
      root-versus-engine byte-identity assertion at scripts/suites/10_warp_0613_anti_vacuity.py:1400 must go
      red together with the pack copy at :1402. Engine sync is the load-bearing leg, because an adopter runs
      the engine copy and a refusal that exists only here is not shipped; the frozen-core leg has its own
      assertion at :1412, which reddens the moment two_key, policy_check or decision references this module.
    text: >
      ENGINE-SYNCED, HONESTLY RECORDED, AND THE BLOCKING RELATIONSHIP STATED. capabilities.yaml gains one
      mechanical entry in every copy naming exactly what ships, and stating that this refusal is what makes
      the repository-side control sound on a surface with NO tracker-side fence, so a reader understands
      why it exists. The entry records that WARP-1710 (the public work surface) DEPENDS on this item: on a
      public forge the repository-side guard is the only control, and before this change it would not have
      fired against the real agent. The full gate is GREEN, RULE #1 is clean, no protected path is touched,
      and the frozen safety core beyond the guard itself (two_key, policy_check, decision) is
      byte-UNCHANGED.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds a normalized actor-kind to the tracker adapter seam, consumes it in
  the authorization core's machine-actor guard, adds two named refusals, and keeps the existing name list
  as an additional refusal, with one capabilities entry and a selftest block. Reverting restores the
  name-guess-only guard, which means the real agent identity stops being refused by the repository-side
  control - so a revert is a REGRESSION IN SAFETY rather than a return to a good state, and it must not be
  done to unblock anything without replacing the guard. No record, event or contract changes, so there is
  no migration.
---

## Footprint corrected for the two-home engine

This spec was drafted before PLAN-0008 consolidation and declared `packs/*/.veldo/capabilities.yaml`
and `scripts/selftest.py`. Neither is right now: the packs carry no engine copies (they are assembled
from the canonical source at runtime) and the monolithic selftest was split into `scripts/suites/`.
`.veldo/request_reconcile.py` was also declared and is not touched - the actor kind reaches the core
through the registry entry, not through the reconciler. **`.veldo/tracker_adapter.py` is REPO-ONLY and
must NOT be copied into the engine**; WARP-0623's assertion catches that within seconds, and it caught
me doing exactly that during this build.

## Intent

The WARP-0620 live run proved the property the whole human-decision surface rests on: the agent cannot fire
a terminal transition on the board. It also found that the reason it cannot is the TRACKER-SIDE fence, and
that the REPOSITORY-SIDE guard the design calls the primary control would not have stopped it.

The guard is an exact set-membership test over generic words: agent, bot, automation, service, executor. The
real agent's display name is "Veldo Agent", which normalizes to "veldo agent" and is not in that set. So it
is not caught. Meanwhile the tracker handed us the definitive signal in the same API response - accountType
"app" for the agent, "atlassian" for the human - and the authorization core never looks at it. Zero
references.

Today this is masked. The fence stops the agent before the guard is ever consulted, and that is proven
live. But the plan states the repository is authoritative and the tracker fence is defence in depth, and
the moment that claim is tested on a surface with no per-transition fencing - which is exactly the public
forge the launch plan now carries a work item for - the guard becomes the only control, and it would let the
machine through.

So the fix is not a longer list. A list of names is a guess about identity; the tracker already knows the
answer and reports it. The guard must consume the reported kind, and an actor whose kind is not reported
must be REFUSED rather than assumed human, because assuming humanness from an absence of evidence is the
same failure as trusting a self-declared field.

## Context

- What the live run captured, and what the fixtures must use: two changelog entries, one by "Veldo Agent"
  with accountType "app", one by "Dmitry Grinberg" with accountType "atlassian". Those are the real
  identities and they belong in the tests instead of invented placeholders.
- Why the name list is kept rather than replaced: it refuses things today, and this item must not permit
  anything currently refused. Keeping it as an additional independent refusal makes the new guard a strict
  superset, which is also the only way to satisfy the plan's law that nothing may lower a risk class or
  weaken an existing refusal.
- Why the mapping lives in the adapter: the core must not learn a tracker's vocabulary. Jira says
  accountType, a forge says Bot, another surface will say something else. One normalization per adapter, one
  vocabulary in the core, which is the same seam discipline that made a second tracker adapter possible at
  all.
- What this does NOT establish, stated up front: that a human account is not being driven by a script. That
  is access control, not a decidable property here, and claiming otherwise would be the kind of
  overstatement the last four reviews have been correcting.
- The blocking relationship: WARP-1710, the public work surface, must not ship before this. On a forge with
  no per-transition condition the repository-side guard is the only thing between a machine and a settled
  human decision.

## Out of scope

- No change to the tracker-side fence, which works and is proven live.
- No change to two_key, policy_check or decision. The guard's own module is the surface; the rest of the
  frozen core stays byte-unchanged.
- No new authorization concept: no roles, no new quorum rule, no change to the approver set (that is
  policy.yaml and VEL-3, a protected-path act).
- No live board call. Every fixture is the captured identity data replayed offline.
- No attempt to detect a human account operated by automation.

## Notes

- Write the reproduction from the live-captured identities first, and watch it fail. The temptation with a
  name-list bug is to add "veldo agent" to the set and call it fixed; that would leave the next agent name
  equally invisible and would teach exactly the wrong lesson.
- Refuse UNKNOWN. The reviewer of any weaker version will ask what happens when a tracker does not report a
  kind, and "treat it as human" is the defect restated.
- Fixtures use the real identities. A test built on "machine-1" and "human-1" would have passed before this
  item too.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
