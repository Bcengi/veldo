---
schema: veldo.spec/v1
id: WARP-0731
title: Delete the forgery-guard machinery WARP-0730 made non-authoritative, keeping the API-hygiene half
  of the refusal and dropping the git-enumeration half, so the log writer stops carrying a defence of a
  property nothing reads any more
status: shipped
risk: standard - it edits the ONE writer to an APPEND-ONLY log, where a mistake cannot be taken back, and
  it moves a command-line exit code. It is standard rather than high because `.veldo/events.py` is not a
  protected path, because WARP-0730 already removed the authority this machinery defended (so the change
  cannot reintroduce a live vulnerability, only delete a dead one), and because the deletion is
  subtractive - the failure mode is an append that should have been refused, not a lost line.
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-0730]
placement: [metrics]
footprint:
  - ".veldo/events.py"
  - "engine/.veldo/events.py"
  - "scripts/suites/13_warp_0623_codified_live.py"
  - "specs/WARP-0731-delete-the-forgery-guard-machinery.md"
acceptance_criteria:
  - id: AC1
    text: >
      `log_entitlement` IS GONE, and with it the git enumeration it performed on every reconciliation.
      No function in `.veldo/events.py` derives a set of permitted content keys from what git reports as
      tracked, and `reconcile_verdicts` no longer calls one. The engine's two homes (`.veldo/events.py`
      and `engine/.veldo/events.py`) stay byte-identical, which the conformance check already
      enforces; after PLAN-0008 there are no other copies to update.
  - id: AC2
    text: >
      THE API-HYGIENE HALF OF THE REFUSAL SURVIVES, AND THIS IS THE LOAD-BEARING CHOICE. Deleting the
      `entitled` frozenset outright would also delete the rule that only the reconciler's own append path
      may write a projection-owned event, which is worth keeping on its own merits: `emit()` and
      `--field type=verdict.recorded` must still be unable to mint a `verdict.recorded`. So the parameter
      becomes a BOOLEAN that only `reconcile_verdicts` sets, and `_append_events` and
      `refuse_reserved_envelope` refuse on `not entitled` instead of on set membership. A selftest asserts
      both refusals still bite, driven through the shipped CLI rather than by calling the functions.
  - id: AC3
    text: >
      THE WEAKENING IS DECLARED, NOT SMUGGLED. The boolean is deliberately weaker than the frozenset: it
      no longer checks that each appended key is a member of the enumeration the log's own repository
      produces, so `--repo-root` pointed at a directory of hand-written verdict artifacts can once again
      cause lines to be appended for reviews the domain does not hold. That is acceptable ONLY because
      WARP-0730 removed the value of forging one: nothing authoritative reads `verdict.recorded` any more.
      The docstring at the refusal says this in those terms, naming WARP-0730, so a later reader finds the
      reasoning at the code rather than in a spec they would have to go looking for.
  - id: AC4
    text: >
      `unentitled` LEAVES THE REPORT AND CLI EXIT CODE 2 GOES WITH IT. `reconcile-verdicts` exits 0 or 1,
      never 2, and `_report_line` no longer has a refused-keys clause. This is a command-line contract
      change and is called out as one; the gate script reads the exit code, and a selftest asserts the
      gate's own invocation still behaves.
  - id: AC5
    text: >
      THE WITNESS ASSERTIONS ARE DELETED ON PURPOSE AND THE DIFF SAYS WHY, AND THE COUNT IS MEASURED
      RATHER THAN ESTIMATED. **SIX** `expect()` calls in `13_warp_0623_codified_live.py` witness the
      forgery guard and are removed: WARP-0725 AC1 (set equality over the real corpus), AC4 (no stand-in
      in the module prose), two AC2 legs (the measured forgery and its harmful variant), the AC5 refusal
      placements, and AC3 (the inverse harm). ONE is added in their place, the surviving positive
      control, for a net of five - which is exactly the selftest total's movement, 3371 to 3366, and that
      agreement is the check that nothing else was dropped by accident. The live state's estimate of
      "12 expect() assertions" was wrong and is corrected here; it was a hand-typed number.
      Assertions covering AC2's surviving refusals are KEPT, and the ones testing key-membership are the
      only ones removed.
  - id: AC6
    text: >
      TWO DIFFERENT THINGS SHARE THE WORD ENTITLEMENT AND ONLY ONE IS REMOVED. `log_entitlement` in
      `events.py` is the forgery guard and goes. The "entitlement domain" prose in `verdict_corpus.py` and
      `validate_checks.py` names the CORPUS ENUMERATION - tracked versus validated verdict artifacts - and
      STAYS, as does `verdict_corpus.py` in full (662 lines that `validate.py`, `policy_check.py` and
      `intent_corpus.py` all need). A careless grep on "entitle" hits both concepts; this AC exists
      because that grep is the obvious way to do this job and it is wrong.
required_evidence: [unit]
rollback: >
  Revert the commit. The change is subtractive and touches no persisted state: the event log's FORMAT is
  unchanged, every line already written stays valid, and no migration runs. The only externally visible
  change is that `reconcile-verdicts` stops returning exit code 2, so a caller branching on 2 sees 0
  instead; nothing in this repository branches on it except the report line being removed here.
---

## Outcome

The forgery guard that nine build rounds went into is dead code defending a property nothing reads.
WARP-0730 moved verdict authority out of the agent: the gate is the authority for ordinary work and the
owner for protected paths, and `valid_verdict_for` is no longer consulted. What remains is machinery -
a git enumeration on every reconciliation, a frozenset threaded through four functions, a report field
and a CLI exit code - whose only job was to make a `verdict.recorded` line unforgeable. Forging one now
buys an attacker a row in a descriptive metric.

Removing it makes the writer readable again and removes a per-reconciliation git walk from the gate.

## Background

The measured scope, from the live state:

- The `entitled` parameter threads through `refuse_reserved_envelope`, `_append_events`,
  `_reconcile_pass` and `reconcile_verdicts`.
- The report carries `unentitled`; `events.py` returns CLI exit code 2 off it.
- PLAN-0008 consolidation (merged 2026-08-02) cut the engine from eight committed copies to two homes,
  so this is a two-file change where the earlier estimate assumed eight.

**Nothing authoritative reads `verdict.recorded`, verified rather than assumed.** The consumers are
`metrics.py` (a descriptive tally), `tracker_mirror.py` (maps it to an in_review tracker status),
`runstatus.py` (display), `validate.py:697` (a known-event-type whitelist) and `executor.py:500`
(emitter).

**The metrics tally does not need defending, and this dissolves an open question rather than answering
it.** `log_entitlement`'s own docstring already declares that a writer which never imports the module -
a shell append, a hand-edited log - can append directly. So the tally was never protected by the
entitlement check; only the reconciler's own derivation path was. Keeping 150 lines to guard a statistic
that a one-line shell append already defeats is not a trade worth making. Label the tally descriptive.

## Out of scope

- `verdict_corpus.py`. It is the corpus enumerator, not the forgery guard. See AC6.
- The `reviews` count in `risk_tiers`. Read only by `decision_review.py` for design-decision reviews,
  which floor at one by design. WARP-0730 already recorded an attempt to change this and the gate
  catching it.
- `valid_verdict_for`. Non-authoritative since WARP-0730 and left in place; removing it is a separate
  question about the review tooling, not about the log writer.

## Notes for the implementer

`refuse_reserved_envelope`'s producer clause and `_append_events`'s type clause are TWO refusals on the
same door and both must keep biting. The selftest discovers them by what they DO to a projection-owned
type rather than by name, so an implementation that collapses them into one will be caught.
