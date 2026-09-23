---
schema: veldo.spec/v1
id: VELDO-0065
title: Versioned presentation receipts for every enrolled channel
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W50
plan_revision: 3
depends_on: [VELDO-0064]
placement: [contracts, tracker, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "packs/*/.veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_channel_projection.py"
  - ".veldo/control_channel_projection.py"
  - "packs/*/.veldo/control_channel_projection.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0065_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0065-versioned-channel-presentations.md"
  - "specs/index.md"
  - "proof/VELDO-0065/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Immutable Telegram presentation receipts bind the actual content shown to the owner.
      Set and completeness: Compare receipt fields with R72: request ID/version/full digest, subject
      digests, rendered brief bytes, risk/authority statements, choices, channel, chat/message
      identity and publication time. Send real bytes, retrieve them and mutate each binding
      separately. Falsifier: Omit request version from its digest; otherwise equal revisions must
      collide and fail the identity check.
    falsified_by: >
      Omit request version from its digest; otherwise equal revisions must collide and fail the
      identity check.
  - id: AC2
    text: >
      Claim: Every answer, including rejection, names the current presentation and records its own
      ruling and rationale. Set and completeness: Submit signed canonical Telegram answers, then
      omit the reference, alter brief/risk/choices under the same subject or use a stale/superseded
      presentation. Only the current shown presentation may settle. Falsifier: Check only subject
      digest after replacing the brief; the stale-presentation answer must settle and fail the
      check.
    falsified_by: >
      Check only subject digest after replacing the brief; the stale-presentation answer must settle
      and fail the check.
  - id: AC3
    text: >
      Claim: A changed presentation creates a new version and visibly supersedes the previous shown
      content. Set and completeness: Publish two ordinary versions through Telegram, retain both
      immutable receipts and compare the visible supersession link to current authority; refuse
      answers to content with no confirmed publication. Falsifier: Mark an unsent presentation as
      published; the unseen-content refusal check must fail.
    falsified_by: >
      Mark an unsent presentation as published; the unseen-content refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Versioned presentation receipts for every enrolled channel. Deliver the normal function needed by the running factory journey.

## Context

W50 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Request content digest, rendered presentation digest and bound subject digest are distinct.
Telegram is the initial channel; the later authenticated UI/API must create and answer the
same receipt contract. No Jira brief-comment repair is required.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3 interrupted
publication moved to Release 2; extra-channel coverage moved to Release 4. Jira-specific work
is dropped. Shown bytes, request/presentation identity and version-bound answers remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.

2026-09-23, implementation: `scripts/check_teeth_mutations.py` was added to the footprint so the
declared falsifiers can be registered as finding 65 of the existing teeth mutation driver. The
criteria, status and risk are unchanged.

2026-09-23, review r3: `.veldo/control_channel_projection.py` (VELDO-0064, and its engine copy)
was added to the footprint because the owner must receive one decision message per request
version. With presentations enabled the presentation is that message: a projection given the
presenter sends no notice of its own and reports each entry as presented or awaiting
presentation, and its metrics are the presenter's. A projection built without a presenter is
unchanged, so no VELDO-0064 row was changed. The criteria, status and risk are unchanged.

2026-09-23, review r1: an independent review reproduced nine defects at `f4361d1`. Each was fixed
test first with its own suite row and two registered mutations, recorded in the proof README: only
the requester frames and the framer is named; a stored framing counts only as the frame operation
accepted it, verified with the key active at the store's acceptance; one decision message per request
version when presentations are enabled; long presentations are split, never truncated; an answer
cannot predate its presentation; a replacement publishes without its deleted reply target; receipt
verification binds the reply link; decisions go only to a private chat; and the answer is recorded
in the authority contract's vocabulary for its one settlement, with no second settlement record. The
criteria, status and risk are unchanged.

2026-09-23, review r2: a fresh review of the fixes reproduced five more items, each fixed test first
with its own row and two registered mutations, recorded in the proof README: a framing key is judged
by the store's journal order, never by a caller-supplied time; whether the inbox projection sends is
decided from the store (presentations enabled on the enrollment, or the request framed or presented),
and a notice sent before presentations were in use is visibly superseded by the first presentation;
a definitely refused part is sent again after its retry_after; choices match regardless of case and
spacing and an unmatched reply gets a message back. This supersedes the review r3 line above where
it said a projection given the presenter decides. Review disposition settlement is recorded as an
open item for VELDO-0068. The criteria, status and risk are unchanged.

2026-09-23, review r3: a third review left seven small items, each fixed test first with its own row
and registered mutations, recorded in the proof README: a notice in flight or of unknown outcome is
named by the first presentation and superseded once its outcome is known, and a framing landing
after the projection's decision refuses its notice; a reply after the answer is told the ruling; the
message back is sent once per inbound message; frame() and the presenter share one key rule and
frame() pins the ledger it read; retry_after is honored only as a bounded integer; only the
projection's own notice of the same request is superseded; choices match under NFKC. The journal
scan cost is a Release 2 scale note. The criteria, status and risk are unchanged.

2026-09-23, review r4: a fourth review left eight items, each fixed test first with its own row or
row cases and registered mutations, recorded in the proof README: frame() pins every authority input
from the snapshot its checks read; a redelivered accepted answer gets no reply; the first
presentation supersedes the notices of its request version and older ones, current version first;
a pending notice is reconciled against every presentation that named it; an overlong retry_after is
capped; the whole reply is NFKC-normalized before the split and Unicode hyphens separate; a reply
after the request left pending is told it is no longer open; an unreadable ledger fails closed. The
criteria, status and risk are unchanged.

2026-09-23, review r5: a fifth review left four items and a missing message, each fixed test first
with its own row or row cases and registered mutations, recorded in the proof README: the recorded
answer delivered again is silent even after the request closed; the edge scope check precedes every
message back; frame() refuses an unreadable ledger as the presenter does; the recorded rationale is
the owner's own text; a reply to a presentation that no longer binds is told a new one is coming.
The reviewer's uncaught mutants now fail rows and are registered. The criteria, status and risk are
unchanged.

2026-09-23, review r6: a sixth review left one blocker and four items, each fixed test first,
recorded in the proof README: messages back follow one order (nothing to an owner no longer current,
"already answered" first, a new presentation promised only when one will come); the edge scope check
precedes the redelivery check; a ledger of the wrong shape is refused by name (frame() as not_authorized, the presenter refusing to publish with missing_framing); the split docstring
names its characters. To reduce the gate cost, 14 redundant finding-65 mutations were
removed (each one's failing checks contain another kept mutation's, seven of them an equal set), keeping at least two
per row; the list and reason are in the proof README. The criteria, status and risk are unchanged.

2026-09-23, review r7: a seventh review found that an owner revoked through the revocation ledger
still got replies and had an answer accepted. The owner-current check and the presentation bindings
now read the ledger as frame() does, failing closed: such an owner is refused owner_not_current with
nothing sent, and a new request of that owner is not presented. Fixed test first with its own row
and three registered mutations, recorded in the proof README. The criteria, status and risk are
unchanged.
