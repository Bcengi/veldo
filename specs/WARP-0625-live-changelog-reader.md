---
schema: veldo.spec/v1
id: WARP-0625
title: The live changelog reader that does not exist - implement the read-only seam the whole inbound edge
  depends on, normalizing the tracker's nested shape into the flat attributed entries the safety core
  reads, carrying the actor KIND so machine-ness is structural, and BLOCKING rather than returning an
  empty list when the history cannot be read (Gap 2 from the WARP-0620 live proof)
status: shipped
risk: high - this implements the READ path the safety-critical inbound reconcile keys on. It writes
  nothing and can settle nothing, so it opens no execution or authorization path, but every downstream
  decision about WHO did WHAT is derived from what this returns, and the most dangerous thing it can do is
  return a PLAUSIBLE EMPTY LIST when the truth is that the history could not be read. It is high for that
  reason and not critical because it is read-only, it touches no protected path, and every behaviour is
  gate-proven offline against the REAL payload captured during the live proof
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W10
plan_revision: 1
depends_on: [WARP-0619, WARP-0620, WARP-0623]
placement: [tracker]
footprint:
  - .veldo/tracker_adapter.py
  - .veldo/tracker_jira_live.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - plans/PLAN-0016-human-decisions-through-jira.md
  - docs/design/held-back/WARP-0625-live-changelog-reader-NEEDS-PLAN-RECONCILIATION.md
  - scripts/suites/11_inbound_command_receipt_reconcile.py
  - specs/WARP-0625-live-changelog-reader.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: Every refusal and every skip is named through the adapter's error class - an unreachable issue, a
    response that is not the expected shape, an incomplete pagination walk, a non-monotonic entry order,
    and the count of non-status items deliberately skipped - so a reconcile that blocks is diagnosable from
    the reader's own output without reading the source.
  error_taxonomy: The failure names are closed: ISSUE_NOT_FOUND, CHANGELOG_UNREADABLE (present but not the
    expected shape), CHANGELOG_INCOMPLETE (the pagination walk did not account for every entry the tracker
    reported), and CHANGELOG_UNORDERED (the entries are not monotonic in recorded time). None of these ever
    degrades to an empty list.
acceptance_criteria:
  - id: AC1
    text: >
      THE SEAM IS IMPLEMENTED FOR THE LIVE TRACKER, and the docstring stops lying. _read_changelog is
      implemented on the live Jira adapter, fetching the issue changelog through the authenticated API and
      returning the ORDERED ATTRIBUTED entries the base seam declares. The base's current claim that a live
      adapter reads the real board through this same seam "reference-wired" is FALSE TODAY - the only
      implementation is on the FakeTracker, which is what the WARP-0620 live proof discovered when the
      normalization had to be hand-written to run the proof at all - and this item makes the claim true. A
      selftest asserts the live adapter class actually defines the method and that the base's docstring no
      longer describes a wiring that does not exist.
  - id: AC2
    text: >
      THE NORMALIZATION LIVES IN THE ADAPTER AND IS PROVEN AGAINST THE REAL CAPTURED PAYLOAD, not an
      invented shape. The tracker returns a NESTED structure (each history entry carries an author object
      and a list of field items, with the status change expressed as fromString and toString) while the
      safety core reads a FLAT entry (id, timestamp, actor, from-state, to-state). The mapping between them
      is implemented in the tracker's own adapter and NOWHERE ELSE, so the core never learns a tracker's
      vocabulary. The offline fixture is the VERBATIM PAYLOAD captured from the real board during the live
      proof (proof/WARP-0620/te1-changelog-raw.json), so the test is grounded in what the tracker really
      sent rather than in what anyone assumed it sends. A selftest asserts the flat entries derived from
      that real payload are exactly the ones the live run derived by hand, field for field.
  - id: AC3
    text: >
      THE ENTRY CARRIES THE ACTOR KIND, so machine-ness becomes structural rather than a name guess. Each
      normalized entry carries the actor's kind as the tracker reports it, mapped by the adapter to exactly
      one of human, machine or unknown (the tracker's account-type vocabulary is the adapter's business:
      the value it reported for the service account in the live proof maps to machine, the value it
      reported for the human maps to human, and anything unrecognized maps to unknown rather than to
      human). This is the field WARP-0624 consumes to refuse a machine settlement, and the two items are
      designed together: this one SUPPLIES the signal, that one ENFORCES on it. A selftest asserts the kind
      derived from the real captured payload is machine for the agent entry and human for the owner entry,
      and that an unrecognized account type maps to unknown and never to human.
  - id: AC4
    text: >
      AN UNREADABLE HISTORY NEVER LOOKS LIKE AN EMPTY ONE, which is the whole safety point of this item and
      the defect class this repository has now been bitten by three times. A response that is present but
      not the expected shape raises CHANGELOG_UNREADABLE; a pagination walk that does not account for every
      entry the tracker reported raises CHANGELOG_INCOMPLETE; entries that are not monotonic in recorded
      time raise CHANGELOG_UNORDERED; and an issue the tracker does not hold raises ISSUE_NOT_FOUND. NONE of
      these returns an empty list, because an empty list is indistinguishable from an issue that genuinely
      has no transitions, and the reconcile would then read "no terminal transition yet" and skip a request
      that had in fact been decided. The CONTROL proves the distinction is real in both directions: an issue
      that genuinely has no status transitions returns an EMPTY LIST and does not raise. Each refusal is
      proven by a selftest over a mutated copy of the real payload.
  - id: AC5
    text: >
      PAGINATION AND ORDER ARE LOAD-BEARING AND PROVEN. The reader walks every page and verifies the walk
      is complete against the total the tracker reports, because a truncated changelog most plausibly loses
      the LAST entry, which is exactly the terminal transition the whole edge keys on. Order is verified
      rather than assumed: the entries are returned oldest first and monotonic in recorded time, and a
      response that violates that is refused by name rather than silently sorted, because a tracker that
      reports an order this reader does not understand is an ambiguity the design says to BLOCK on. Non-status
      items are skipped deliberately and the count of skips is reported, so a reader can tell "no status
      change in this entry" from "this entry was dropped". Selftests prove: a multi-page walk assembles in
      order, a short page count refuses, a reordered payload refuses, and the skip count is reported.
  - id: AC6
    text: >
      READ-ONLY, ENGINE-SYNCED, AND HONEST ABOUT WHAT IS STILL NOT PROVEN. The reader performs no write and
      touches no write audit, asserted structurally rather than promised. capabilities.yaml gains one
      mechanical entry in every copy naming exactly what ships, and stating plainly that the LOGIC is
      gate-proven offline against a captured real payload while the LIVE FETCH ITSELF remains exercised only
      by a human-run proof, in the same honest posture the sibling live paths carry. It also records that
      this item makes the inbound reconcile drivable against a real board for the first time, which is the
      precondition for the parts of WARP-0620 that had to be recorded as PARTIAL. The full gate is GREEN,
      RULE #1 is clean, no protected path is touched, and the frozen safety core is byte-UNCHANGED.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds a read-only method to the live adapter, a normalization function
  beside it, an actor-kind mapping, four named refusals and a selftest block, plus one capabilities entry
  re-synced byte-identical across engine and the packs. Reverting returns the seam to
  FakeTracker-only, which means the inbound reconcile cannot be driven against a real board - a loss of
  capability rather than a return to a working state, since nothing depends on the reader today. No record,
  event, contract or write path changes, so there is no migration.
---

## COMPLETE as of 2026-08-02, and the earlier reasoning for stopping was wrong

An earlier pass of this item shipped the normalization and declined to write the fetch, arguing it
could not be gate-tested without live credentials. **That was wrong, and the mistake is worth
keeping.** What cannot be tested is a fetch that owns its own transport. A fetch that takes the
adapter's `request` callable is fully testable: the gate drives paging, accumulation, the stop
conditions and the hand-off to the normalizer against canned pages, and only the socket goes
unexercised.

So `fetch_changelog` is wired. **Paging is not a nicety**: Jira returns the changelog 100 at a
time, and a truncated history does not error - it silently loses the EARLIEST transitions, which
are exactly the ones the opening-actor derivation reads. It stops on the server's own `isLast`,
falls back to an empty page, and is bounded by a page cap so a malformed response cannot hang it.

GAP 2 named two missing things and they are separable. **The normalization is built and proven**:
`normalize_changelog` turns Jira's nested payload into the flat ordered attributed records every
shipped accessor reads, splitting several items per entry, excluding non-status items, and ordering
by `created` rather than by `id` - and it **reproduces, field for field, the records the WARP-0620
live run actually recorded**.

**What remains is only the live board run**, which needs the sandbox credentials and is the same
kind of act WARP-0620 was: a proof against a real board, not a build.

**HONEST LIMIT ON THE FIXTURE.** The live run captured the NORMALIZED output, not the raw wire
body, so the test's nested payload is a reconstruction per the run record's description of the
shape. It proves the flattening, filtering and ordering; it does not prove Jira's wire format is
exactly that.

## Plan reconciliation, resolved 2026-08-02

This spec was drafted against a STALE copy of PLAN-0016 and claimed W5, which the authoritative plan
assigns to WARP-0616 (and W4 to WARP-0619). The gate refused it by name and it was held in
`docs/design/held-back/` rather than fudged into passing, which was correct.

**Resolved by giving it a work item that is actually free.** The three options the held-back README
named were: take a free work id, have the plan gain an item, or drop it as covered by WARP-0619.
**Dropping it is wrong** - WARP-0619's own title says it is the OFFLINE logic over a fake tracker and
names WARP-0620 as the live proof, so it does not implement a live reader and never claimed to. The
work is real and distinct, so PLAN-0016 gains **W10 at order 75**, between the execution binding
(W8) and the conformance-and-release item (W9), because the reader must exist before the edge can be
conformance-tested end to end.

## Intent

The WARP-0620 live proof found that the authenticated pull the entire inbound edge depends on does not
exist. The seam is declared on the adapter base, its docstring says a live adapter reads the real board
through it, and the only implementation is on the FakeTracker. To run the proof at all, the REST fetch and
the nested-to-flat normalization had to be written by hand in a throwaway script.

So this item is not new capability, it is the missing half of a capability the repository already claims to
have. And the claim is the interesting part: a docstring that says "reference-wired" implies an
implementation exists. That phrase is now a thing this project does not write unless a live path has
actually run.

The safety property that matters here is narrow and easy to get wrong. This reader's most dangerous
possible behaviour is not a crash: it is returning a plausible EMPTY LIST when the truth is that the
history could not be read. An empty list means "this issue has no transitions", the reconcile reads that as
"not decided yet", and a request that a human actually approved is silently skipped. That is the same
absent-versus-unreadable conflation that has now blocked two separate items in this repository, so it is
built in from the start here rather than found by a reviewer.

## Context

- What the live proof captured, and why it is the right fixture: the verbatim payload from a real board,
  two entries, one by the service account and one by the human, each carrying an author with an account
  type, an entry id and a timestamp, with the status change expressed as fromString and toString inside a
  list of field items. Testing the normalization against THAT rather than against an invented shape is the
  difference between proving the mapping and proving an assumption.
- Why the actor kind belongs here rather than in the core: the tracker's account-type vocabulary is the
  tracker's business. WARP-0624 refuses a machine settlement; this item supplies the signal it refuses on,
  normalized to three values. Designed as a pair, and 0624 must not consume a raw tracker vocabulary.
- Why order and pagination are load-bearing: the design derives the terminal actor from the LAST entry, so
  a truncated walk most plausibly loses exactly the entry the decision rests on, and a reordered response
  would make a rejected-then-approved history read backwards. Both are refusals, not repairs, because the
  plan says to block on ambiguity rather than infer.
- What this unblocks: the parts of WARP-0620 recorded as PARTIAL, where the reconcile could not be driven
  end to end against a real board because there was no reader. With this in place that becomes possible,
  as a separate human-run proof.

## Out of scope

- No write of any kind, and no change to the write audit.
- No change to the reconcile itself. This item supplies its input; the derivation is WARP-0619's and stays
  byte-unchanged.
- No enforcement on the actor kind. Supplying the field is this item; refusing on it is WARP-0624.
- No second tracker. The public-forge adapter is PLAN-0017's work item and will implement this same seam
  with its own vocabulary mapping.
- No live run. The logic is gate-proven offline against the captured payload; exercising the real fetch is
  a human-run act like every other live path here.

## Notes

- Use the captured payload verbatim as the fixture and mutate COPIES of it for the refusals. A fixture
  someone typed by hand would have passed before this item existed too.
- Refuse rather than sort. The temptation with an ordering requirement is to sort defensively, which turns
  a tracker whose semantics we do not understand into silently-accepted data.
- Report the skip count for non-status items. Without it, "this entry had no status change" and "this entry
  was dropped" look identical, which is the same conflation class in miniature.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
