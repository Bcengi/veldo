# VELDO-0065 proof

Release 1 revision 3 versioned Telegram presentation receipts and presentation-bound answers. The
specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent
review; it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

`.veldo/control_channel_presentation.py` (canonical and engine copies byte-identical, in
`init_scaffold._FILES`, not in `REQUIRED_SUBSTRATE` because no validator loads it). Standard library
only. It takes the store, membership, VELDO-0064 projection and assignment modules and the VELDO-0064
`Inbox` as arguments, so a copy loads from any path. Since review r3 the VELDO-0064 projection
(`.veldo/control_channel_projection.py`, added to the footprint with a History line) sends nothing
for a request whose presentations are in use, which it decides from the store (see the second
review fixes below).

**The request and its three digests.** The request is the inbox assignment at one request version.
`request_digest` covers the request id, the request version and every accepted content field (kind,
owner, scope, deadline, budget, brief, choices, subject, unit, requester), so two revisions with equal
content are two requests. `subject_digests` is the assignment's subject. The presentation digest
(`brief_digest`, the authority contract's field name) is the SHA-256 of the canonical JSON list of the
exact rendered messages. The presentation key is
`presentation:telegram_chat:<request>:<request version>:<presentation digest>`.

**What is shown.** `render` produces plain text from the receipt's own bound fields: request id,
version and digest, presentation version, the supersession line when there is one, owner, scope,
deadline, budget, subject digests, the risk statement with who stated it, the authority statement,
the brief, the offered choices and how to answer. A presentation longer than Telegram's 4096 UTF-16
units is consecutive numbered messages, the last carrying the choices and how to answer (review r4).
The risk statement comes from a `frame` command that only the requester signs for the current
request version; the store keeps the signed command and the versions it pinned. A stored framing
counts only when the journal shows the frame operation wrote exactly it, by the requester, verified
with the key as the journal held it at the framing's own position; a key revoked or retired, or a
requester entered in the revocation ledger, earlier in the journal frames nothing (reviews r1, r2,
second review n6). The authority statement is
derived from the owner's current membership, never written by anyone.

**Receipts.** One immutable `channel_presentation` receipt per presentation key, committed as a
`pending` intent before the Bot API `sendMessage` calls and completed once from what the platform
returned for each part (chat id, message id, date, stored text, the message the first part replies
to). Outcomes are `published`, `anomaly` (`presentation_mismatch`, `chat_mismatch`,
`supersession_mismatch`, `incomplete_parts`), `refused` (only a definite Telegram 4xx error answer
before any part was published; the only outcome attempted again) and `unknown_outcome`. A completed
receipt is never written again. `receipt_problems` recomputes every bound field from the receipt's
own request snapshot and compares every part's bytes, the reply link and the publication date with
what the platform holds at the recorded chat and messages.

**Visible supersession.** A `channel_presentation_head` entity per request names the current
confirmed presentation, every published one in order and which one superseded which. When current
authority no longer matches the current presentation (any of request id, version or digest, subject
digests, risk or authority statement, choices, owner or enrolled chat), the next presentation names
the one it supersedes in its bytes and is sent as a Telegram reply to the superseded message
(`reply_parameters`, with `allow_sending_without_reply`, so a deleted superseded message never blocks
the replacement; the receipt records whether the link was made, review r6). The platform's returned
`reply_to_message` is checked, and the head moves in the same transaction that confirms the
replacement's publication. The superseded receipt is left untouched. A current presentation that
still binds current authority is never sent again. Release 1 presents only in a person's private
chat: a group chat enrollment is refused as `group_chat` (review r9).

**Answers.** An answer is a canonical Telegram assertion (`veldo.presentation_answer/v1`) that the
Telegram edge signs with the channel's restricted key (`authority_contract.CHANNELS` names it
`edge-telegram`). `canonical_answer` builds it from the Bot API message object of the owner's reply
to any part of the presentation: the presentation it addresses (id, digest, version), the choice the
owner typed and its ruling in `authority_contract.RULINGS` (mapped in `CHOICE_RULINGS` only), the
rationale (`<choice>: <reason>`), the assertion kind of the assignment kind, the authority scope, and
the platform's message id, sender id, date, chat and replied-to message. A reply from a bot is
refused. `Presenter.answer` refuses by name, in this order: `invalid_input`, `not_authorized` (no
restricted edge key, a signature that does not verify, an edge that is not an active service member),
`missing_presentation`, `unknown_presentation`, `unseen_presentation` (no confirmed publication),
`evidence_mismatch` (the reply is not to one of the named presentation's messages in its chat),
`answer_before_publication` (review r5), `not_owner`, `superseded_presentation`,
`stale_presentation` (the receipt no longer binds current authority), `invalid_input` (unoffered
choice, or a ruling, kind or scope that is not the contract's), `missing_rationale`,
`already_answered`. The accepted answer writes one `presentation_answer` record per principal per
request version, whose `assertion` is what `authority_contract.settle` consumes; no second
settlement record is written (review r7). Rejection is an ordinary ruling and is recorded the same
way.

**Observability.** Every operation appends an observation with the authority coordinates, operation,
request, accepted input versions, outcome, named refusal and its error class (invalid input, missing
authority, missing evidence, stale subject, unavailable service, unknown outcome), never shown text,
rationale, signatures or the token. `metrics()` counts accepted and refused operations, pending
entries not presented as current authority requires with each reason by count
(`unpresented_by_reason`), and unknown or anomalous receipts; a projection given the presenter
reports the same numbers. Receipts,
the head and answer records join accepted inputs, platform observations and authority records by id.

## Narrowest seams for dependencies not on main

- **Canonical acquisition (VELDO-0066) and edge enrollment and delegation (VELDO-0067).** Nothing here
  pulls updates from Telegram. The suite's loopback platform holds the owner's reply as the Bot API
  message object it would deliver, and `canonical_answer` maps that object to the assertion. The
  edge's authority is its restricted key in the store keyring plus an active `service` membership;
  the per-channel delegation records of VELDO-0067 are not consulted. The sender is matched to the
  owner by the enrolled private chat id (for a Telegram private chat the chat id is the user id).
- **Settlement and quorum (VELDO-0068).** An accepted answer is recorded once per owner per request
  version, as the assertion `authority_contract.settle` consumes; the suite shows `settle` settles it
  as recorded. Nothing here settles: the one settlement, the inbox assignment's move to `SUBMITTED`,
  principal quorum and decision effects are VELDO-0068. `present()` treats an answered version as
  answered.
- **Live edge qualification (VELDO-0073).** The suite runs a loopback Bot API server (real HTTP) that
  answers with the platform's `sendMessage` shape, links a reply as Telegram does and refuses a reply
  to a message it does not hold. No live network or real token was used.
- **Key validity is decided by the store's journal order.** Revocation of a key (its
  `verification_key` entity) and of a principal (the revocation organ's ledger,
  `authority:revocations`) are recorded in the same store, so the framing's journal sequence is
  compared with theirs; no time a caller supplies (the publication row's `committed_at`, or a
  record's own `revoked_at`) decides anything. A key version that carries any `revoked_at` or
  `retired_at` at the framing's position counts as revoked there, even one dated in the future.
- **Scale note for Release 2: journal and entity scans.** The stored-framing check reads the key
  and the revocation ledger as of the framing's journal position by scanning journal records that
  mention those entities, newest first, and the presenter and projection find a request's receipts,
  notices and framings by scanning entities of one kind. Each is correct and sufficient for Release
  1's volumes; an index by entity and journal position is Release 2 scale work, not a change of
  what is decided.
- **Open item for VELDO-0068: review dispositions.** `authority_contract.settle` currently consumes
  decision answers only. A `review_disposition` assignment is presented, answered and recorded with
  its ruling exactly like a decision, but `settle` refuses it today as `not_a_decision_answer`; its
  settlement is VELDO-0068's scope. An acknowledgement is recorded and settles nothing.

Not implemented, by the specification's History: interrupted publication recovery (Release 2),
extra channels (Release 4) and Jira presentation (dropped). `request.py`, `request_projection.py`,
`request_reconcile.py` and `authorization.py` (PLAN-0016 Jira surface) are unchanged.

## Criteria, rows and driven falsification

Suite: `scripts/suites/62_veldo_0065_presentations.py` (manifest name
`62_veldo_0065_presentations`), over a real SQLite store with real OpenSSH signatures on every
journal record, command, framing and edge assertion, and real HTTP. Registry:
`scripts/check_teeth_mutations.py`, finding 65 (added to the footprint with a History line). Every
mutant finished its assertion run: no exception, hang or missing row counts as a detection. The
`.diff` beside this README is the exact applied change; `mutations.json` lists every red row and the
suite's own failing check labels per mutant, with source and mutant SHA-256, plus the unmutated
baseline and a no-op copy of each mutated module, all green. It also records that no mutant turned a
row red by an exception (`all_by_assertion`). `python3 -B proof/VELDO-0065/drive.py` regenerates
them. Each criterion section of the suite runs in its own guard, so an exception reds only its own
row and every row still reports.

**AC1: immutable receipts bind the content actually shown.**
Rows `VELDO-0065 presentation/receipt-binds-shown-content` and `VELDO-0065 presentation/revision-identity`.
The first compares every R72 field of a published receipt with its source: request id and version
with the inbox record, the request digest with one the suite computes itself, subject digests with
the stored subject, rendered bytes and digest with the bytes the platform holds, risk statement with
the signed framing, the authority statement, the choices, channel, chat and message identity with the
platform's answer, and publication time with the platform date. The three digests are distinct and
the receipt carries every `authority_contract.PRESENTATION_FIELDS` field. Each of 14 bindings (and
the request content) is then changed separately in a copy and the receipt no longer verifies. An
unframed request and two forged framings (another principal's signature; another request's signed
framing) are not presented and send nothing; the requester's own framing is. The second row revises
the request with equal content: the two revisions have distinct request digests, the first receipt
no longer binds the revision, an answer to it is refused as stale and settles nothing, and the
revision is a new presentation while both receipts are retained.

- `request-digest-omits-version` (the declared falsifier) drops the version from the request digest.
  `presentation/revision-identity` turns red: equal revisions collide ("equal revisions have distinct
  request digests", "the first presentation does not bind the equal revision"). The receipt row is
  also red, because the digest no longer equals the suite's own.
- `bindings-ignore-request-identity` drops request id, version and digest from the bound fields.
  `presentation/revision-identity` turns red: the first presentation still binds the revision.
- `render-omits-risk` removes the risk line from the shown bytes; `framing-signature-unchecked`
  presents any stored framing; `published-at-from-clock` records the local clock as publication time.
  Each turns `presentation/receipt-binds-shown-content` red on its own check.

**AC2: every answer names the current presentation and records its ruling and rationale.**
Rows `VELDO-0065 answer/current-presentation-only` and `VELDO-0065 answer/ruling-and-rationale`.
Signed canonical answers built from the owner's replies are refused when the brief was replaced
under the same subject, the risk statement changed at the same request version, or the choices
changed (`stale_presentation`, nothing settled); when the presentation was superseded
(`superseded_presentation`); when the reference is omitted (`missing_presentation`); and when the
assertion names one presentation while replying to another (`evidence_mismatch`). The current
presentation's answer settles, a second answer is `already_answered`, and two other current
presentations settle with `reject` and `return_for_elaboration`. The second row checks the answer record keeps the
ruling, the rationale, the presentation reference and the platform's message, sender, time and
reply identity; the recorded assertion verifies with `ssh-keygen` against the edge's restricted key
alone; a rejection records its own ruling and rationale; a missing or blank rationale, an unoffered
ruling, an assertion changed after signing, an assertion signed with the edge's ordinary key or by
the owner, another sender and a bot reply are each refused by name, then the owner's answer settles.

- `answer-checks-subject-only` (the declared falsifier) compares only subject digests.
  `answer/current-presentation-only` turns red: the answer to the replaced brief's presentation
  settles ("the presentation of the replaced brief settles nothing" is red), and so do the changed
  risk and choices answers.
- `missing-reference-uses-current` fills an omitted reference from the current presentation.
  `answer/current-presentation-only` turns red: the unreferenced answer settles.
- `answer-drops-rationale` and `answer-skips-edge-signature` each turn
  `answer/ruling-and-rationale` red (rationale not recorded; the tampered assertion settles).

**AC3: a changed presentation is a new version that visibly supersedes, and unseen content is not answerable.**
Rows `VELDO-0065 presentation/visible-supersession` and `VELDO-0065 answer/unseen-refused`.
Two ordinary versions are published: the second is a Telegram reply to the first, names it in its
bytes, and the head (current, published list, superseded map) equals that link; the first receipt's
entity version and digest are unchanged and both still verify against the platform. A changed risk
statement at the same request version is a third presentation and message replying to the second.
A re-run sends nothing, and an answer to the first is refused as superseded. For unseen content, a
definite platform refusal, a lost answer and a completion that could not be written leave `refused`,
`unknown_outcome` and `pending` receipts; an answer naming each is `unseen_presentation` and settles
nothing. Only the refused one is sent again, and once confirmed published the same presentation
settles (additive control).

- `unsent-marked-published` (the declared falsifier) records a refused send as published.
  `answer/unseen-refused` turns red: the unseen-content refusal fails ("an answer to a refused
  presentation is refused as unseen"). The answer is then refused only later, as
  `unknown_presentation`, because the falsely published receipt carries no platform identity, and
  the refused send is never attempted again.
- `unseen-only-refused-outcome` treats only `refused` as unseen. `answer/unseen-refused` turns red
  for the lost and unrecorded presentations.
- `presentation-key-without-digest` keys a presentation by request version only.
  `presentation/visible-supersession` turns red: the revised text at the same request version is
  never presented.
- `replacement-without-reply-link` sends the replacement without the reply link.
  `presentation/visible-supersession` turns red: no visible link, recorded as `supersession_mismatch`.

`VELDO-0065 install/assets` checks scaffold registration, engine byte identity, installation by the
real `_lay` writer and that sampled journal signatures verify with `ssh-keygen`. It has no registered
mutation: it checks the installation and the journal signatures, which belong to the scaffold and the
store organs, not to the two modules the finding-65 mutations change, so no mutation of those
modules can make it red; the scaffold and store suites carry their own mutations.

## Review fixes, 2026-09-23

An independent reviewer reproduced nine defects at `f4361d1` with scripts over the suite's own
setup (their r1 to r9, with r2b and r7b). Each was fixed test first, in its own commit: a new suite
row, red at `f4361d1` by failing its own assertions, then green, with two mutations that reintroduce
the defect or a close variant, registered under finding 65. The branch had nothing to merge from
`origin/main`, which was still this branch's base `97b6961`, already carrying the VELDO-0064 alias fix.

| Review | Defect at f4361d1 | Fix | Row | Mutations | Commit |
| --- | --- | --- | --- | --- | --- |
| r1 | A project owner (here the answering owner) could replace the requester's risk statement, shown unattributed | Only the requester frames; the stored-framing check requires the requester; the shown line and the receipt name who stated it (`Risk (stated by pm): ...`, `framed_by`) | `framing/requester-only` | `project-owner-frames-again`, `stored-framing-any-framer` | `e1eadad` |
| r2, r2b | A framing written by a generic store write counted, including one signed with a key revoked before now (with a back-dated unsigned `framed_at`) or by a principal frame() refuses | The stored-framing check re-verifies everything frame() checks from the store's own records: the journal record that wrote the framing's current version must be the frame operation's (its command digest is recomputed from the framing and the versions it pinned), the signed command is the requester's frame command for this request version, the requester is still entitled, and the key was active at the store's acceptance time (`committed_at`); `framed_at` is gone | `framing/stored-framing-reverified` | `stored-framing-any-writer`, `stored-framing-key-at-any-time` | `a721dd7` |
| r3 | With the 0064 projection and the presenter both running, each request version produced two decision messages, and a reply to the first was refused with nothing sent back | A projection given the presenter sends no notice of its own: the presentation is the one message, reported as `presented` or `awaiting_presentation`, with the presenter's metrics. Without a presenter the projection is unchanged and every VELDO-0064 row stays green | `projection/one-message-per-version` | `projection-notice-beside-presentation`, `projection-defers-only-once-presented` | `6fe0b4b` |
| r4 | A brief longer than one Telegram message could never be presented; every run retried the same refusal | A presentation over 4096 UTF-16 units is consecutive numbered messages within the limit, the last carrying the choices and how to answer; the receipt binds every part's message id and bytes; an answer to any part names the same presentation; nothing is truncated or linked | `presentation/long-brief-split` | `part-length-in-characters`, `answer-only-to-last-part` | `7f82376` |
| r5 | An answer the platform dated an hour before the presentation's publication settled | Refused as `answer_before_publication`; the same second is accepted | `answer/not-before-publication` | `answer-time-unchecked`, `answer-time-same-second-refused` | `adf0407` |
| r6 | Once the superseded message was deleted, the replacement was refused on every run | Sent with `allow_sending_without_reply`; the text still names what it supersedes; the receipt records `reply_linked` | `presentation/replacement-without-reply-target` | `replacement-requires-reply-target`, `reply-link-always-claimed` | `f2357c6` |
| r7, r7b | The build wrote its own terminal `presentation_settlement`, which `authority_contract.settle` refused for the same answer (`accept` is not one of its rulings) | No second settlement record: one answer record per owner per request version whose assertion carries the ruling in the contract's RULINGS (mapped once, in `CHOICE_RULINGS`), the assertion kind and the authority scope, and `settle` settles it as recorded; a decision whose choices have no ruling is refused as `unmapped_choice` | `answer/settle-consumes-answer` | `answer-records-typed-choice-as-ruling`, `unmapped-choice-presented` | `927b462` |
| r8 | A receipt whose reply link fields were changed still verified | `receipt_problems` checks the reply target against the superseded message, the recorded link against what was sent, and each part's platform reply against the receipt | `presentation/reply-link-verified` | `receipt-reply-link-unchecked`, `receipt-platform-reply-unchecked` | `48734f3` |
| r9 | A decision was published to an enrolled group chat, where no owner reply could settle it | Release 1 presents only in a private chat: a group chat is refused as `group_chat` and counted in `unpresented_by_reason`, in the presenter's metrics and in a projection given the presenter | `presentation/private-chat-only` | `group-chat-presented`, `unpresented-reason-not-counted` | `1b0da99` |

`14c0b0d` first put each criterion section of the suite in its own guard and loaded the projection
through its production anchor, so the old code runs to its verdicts and projection mutants reach it.

**Red at f4361d1.** `python3 -B proof/VELDO-0065/drive.py --red f4361d1` runs the current suite once
against the presentation and projection modules of `f4361d1` and writes `red-at-f4361d1.json`. The
only change to the old code is that each old constructor accepts and ignores keyword arguments it
did not know (the presenter's `assignment`, the projection's `presenter`); the record names both
lines and the SHA-256 of each module it ran. All nine new rows fail by their own assertions, with no
section raising. Three existing rows are also red there, because the fixes changed what they check:
`presentation/receipt-binds-shown-content` (the shown risk line names its framer and the rendered
bytes are a list of messages), `answer/current-presentation-only` (`already_answered` and the
`return_for_elaboration` choice) and `answer/ruling-and-rationale` (the recorded ruling is `approve`).

**Contract changes a consumer will see.** `Presenter(..., *, assignment)` takes the assignment module.
`frame()` accepts only the requester. A receipt's `rendered` and `platform_texts` are lists of
messages, with `message_ids` (the last is `message_id`), `reply_linked`, `framed_by` and `rulings`;
`external_id` is `<chat>:<message ids>`. The answer record id is
`presentation-answer:<request>:<version>:<principal>` and carries `choice`, `ruling`, `assertion_kind`
and `authority_scope`; `presentation_settlement` and `Presenter.settlement` are gone
(`answer_record(request, version, principal)` replaces it). `Projection(..., *, presenter=None)`.
`receipt_problems(receipt, platform)` takes one platform view per part (a single mapping still works
for a one-message receipt).

**The reviewer's scripts, re-run.** They were run against the final tree with the harness pointed at
it. `review-r1-rerun.log` holds the output and `review-r1-rerun-adaptations.diff` the exact changes to
the adapted copies; none prints `BUG`. r2, r2b, r4, r5, r6 and r8 run unchanged. r1 matched the old
`Risk:` line prefix; r7, r7b and q1 read the removed `settlement`; r9 read a presentation that is now
refused; r3 built the projection without the presenter, which is the mode that keeps the VELDO-0064
notice. With those adapted, r3 shows one message per request version, r7 and r7b show `settle`
agreeing (`True []`), and every q1 probe holds.

## Second review fixes, 2026-09-23

A fresh review of `14c0b0d..753586c` reproduced five more items with scripts over the suite's own
setup (n1 to n7). Each was fixed test first in its own commit, with a new row red at `753586c` by its
own assertions, then green, and two registered mutations. Before the fixes the branch merged
`origin/main` (`c7379d9`); the one conflict was the `--finding` choices of the mutation driver, kept
from both sides (52 and 65), and `requires.json` was regenerated.

| Review | Defect at 753586c | Fix | Row | Mutations | Commits |
| --- | --- | --- | --- | --- | --- |
| n6 | `control_store.execute` takes `committed_at` from its caller, so a framing signed with a revoked key and executed with a back-dated time was accepted and shown | Key validity by the store's own order: the key and the revocation ledger as the journal held them at the framing's position; a later revocation strands nothing, an earlier one (in the key record or the ledger) refuses, whatever times the records carry | `framing/key-by-store-order` | `framing-key-read-now`, `framing-ledger-unchecked` | `5f42b88` |
| n1 | Whether the inbox projection sent its own notice was a constructor argument: a projection built the VELDO-0064 way (a restart) sent a second decision message, and a notice sent before presentations were in use was never superseded | Decided from the store: the projection sends nothing when the owner's enrollment says `presentations: enabled`, or the request is framed or has a presentation; it reports `presented` or `awaiting_presentation`. A notice sent before presentations were in use is superseded by the first presentation, which replies to it and names it, and the notice's record is marked `superseded_by` | `projection/silent-from-store`, `projection/notice-superseded` | `projection-ignores-presentations`, `projection-ignores-enrollment-setting`; `presentation-ignores-notice`, `notice-not-marked-superseded` | `82576d5`, `21e6f6e` |
| n2 | A later part Telegram definitely refused (a routine 429) left an anomaly that was never sent again: the owner had a part without choices and the version could never be presented | A definitely refused later part leaves the receipt `partial` with the parts already published; it is sent again on a later run, never before the platform's `retry_after`, and the presentation completes once every part is published | `presentation/refused-part-sent-again` | `partial-never-sent-again`, `retry-after-ignored` | `cf425fc` |
| n5 | "Accept: ..." (a phone's capitalization) was refused, and a reply that matched no choice was met with silence | Choices match whatever the phone did to case and spacing; a reply that names no offered choice (`unmatched_choice`) or gives no reason (`missing_rationale`) gets one short reply to the owner's message listing the valid choices | `answer/choice-matching-and-feedback` | `choice-match-case-sensitive`, `owner-not-told` | `98ffabe` |
| n5 | The docstring said every answer record is what `settle` consumes | Corrected: `settle` consumes decision answers today; review dispositions are recorded for VELDO-0068 to settle (the open item above) | none (documentation) | none | `842ec49` |

The one-message row's mutations were re-pointed at the store-decided code
(`projection-notice-beside-presentation`, `projection-never-reports-presented`). A framed request
counts as presentation-bound because its framing is the requester's own signed request to present
it: without that, a projection that ran between the framing and the first presentation still sent a
second message (n1 case A).

**Red at 753586c.** `python3 -B proof/VELDO-0065/drive.py --red 753586c` runs the current suite once
against the presentation and projection modules of `753586c`, unchanged (their constructors already
take the current arguments), and writes `red-at-753586c.json`. All five new rows fail by their own
assertions, with no section raising. One existing row is also red there because its expected refusal
changed: `answer/ruling-and-rationale` (an unoffered choice is now `unmatched_choice`).

**The second reviewer's scripts, re-run unchanged.** `review-r2-rerun.log` holds the output of n1 to
n7 run against the final tree with only the harness root pointed at it; nothing was adapted. n1 now
shows one message per request version in both of its cases, n2 shows the refused part waiting for
its `retry_after` (the script does not advance time; the new row does), n6 refuses the back-dated
forgery, and n3, n4 and n7 hold. The only `BUG` lines are n5's two review-disposition lines, the
open item for VELDO-0068 above; its capitalized "Accept" is accepted and its unmatched reply gets a
message back. The first review's r3 re-run adaptation passed `presenter=` to the projection, which
set the very thing under test; the store-decided behavior no longer depends on that argument.

**Contract changes a consumer will see.** A channel enrollment may carry `presentations: enabled`.
A projection record may carry `superseded_by`. A receipt may be `partial`, with `platform_parts` and
`retry_not_before`; `unmatched_choice` and `retry_after` are new named refusals.
`control_channel_projection.telegram_error_answer(reply, status)` returns Telegram's error answer
(`telegram_refusal` is built on it).

## Third review fixes, 2026-09-23

A third review (no blocking finding) left seven small items, probed by p1 to p5. Each was fixed
test first in its own commit, with a new row red at `8dec396` by its own assertions, then green, and
at least two registered mutations. Before the fixes the branch merged `origin/main` again
(`966f7da`, no conflicts; `requires.json` regenerated, unchanged).

| Item | Gap at 8dec396 | Fix | Row | Mutations | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 (p2 B, p5) | A notice still in flight or of unknown outcome when the first presentation went out was neither named nor superseded, and a framing landing between the projection's decision and its intent did not stop the notice | The notice intent pins the framing's absence, so a later framing refuses it; the first presentation names a pending or unknown notice in its text (no reply link), marks an unknown one superseded at once and a pending one on the next run once its outcome is known | `projection/in-flight-notice-superseded` | `notice-intent-without-framing-pin`, `unconfirmed-notice-not-named`, `pending-notice-never-marked` | `edb02b9` |
| 2 | After a version was answered, a reply got the no-match message | `already_answered` is checked first and the owner is told "already answered: <ruling>" | `answer/after-answered-reply` | `answered-checked-after-choice`, `answered-not-told` | `c91e735` |
| 3 | The message back was sent again on redelivery | Recorded by the inbound message's platform identity (`presentation_tell`) before it is sent; a redelivery is not told again | `answer/tell-once-per-message` | `tell-not-deduplicated`, `tell-keyed-by-text` | `726eb09` |
| 4 | frame() judged keys by time and ignored the ledger, so it could accept what the presenter refuses (and, per p1 K-3, a ledger revocation between its read and commit) | One key rule (`usable_key`): any recorded revocation or retirement counts whatever its date, `effective_at` is checked; frame() refuses a ledger-revoked principal and pins the ledger it read | `framing/frame-and-presenter-agree` | `frame-key-by-time`, `frame-ledger-unchecked`, `frame-ledger-unpinned` | `ed949f3`, `674805d` |
| 5 | Any non-negative number was honored as retry_after, including fractions, huge values and infinity | Only a whole number of seconds from 0 to one hour (`MAX_RETRY_AFTER`); anything else means the next run | `presentation/retry-after-bounded` | `retry-after-any-number`, `retry-after-unbounded` | `9393cfb` |
| 6 | Superseding a notice trusted the kind the intent named | Only the projection's own record kind, for the same request | `presentation/notice-kind-fixed` | `notice-kind-from-caller`, `notice-of-any-request` | `16725e5` |
| 8 | Full-width letters, a full-width colon and "return for elaboration" did not match | Unicode NFKC plus case folding, spaces, underscores and hyphens alike, the full-width colon accepted | `answer/choice-normalization` | `choice-without-nfkc`, `choice-separators-distinct` | `9fa823e` |

Item 7 (the cost of the journal scans) is the Release 2 scale note above.

**A defect of my own, found and fixed.** Commit `82576d5` replaced a block of mutation registrations
up to the next anchor and so dropped `framing-key-read-now` and `framing-ledger-unchecked`, the two
mutations registered for `framing/key-by-store-order` in `5f42b88`. The second review's record and
README named them though they were not registered. `9f865b7` restores both, and every row now has at
least two registered mutations (checked from the registry).

**Red at 8dec396.** `python3 -B proof/VELDO-0065/drive.py --red 8dec396` runs the current suite once
against the presentation and projection modules of `8dec396`, unchanged, and writes
`red-at-8dec396.json`. All seven new rows fail by their own assertions, with no section raising, and
no existing row is red there.

**The third reviewer's probes, re-run unchanged.** `review-r3-rerun.log` holds p1 to p5 against the
final tree. p1's frame() race (K-3) is now refused and agrees with the presenter; p2's in-flight
notice (B) is named by the presentation and marked superseded on the next run; p3 honors only the
bounded integer; p4 matches full-width letters and colons and "return for elaboration", tells a
redelivered message nothing, and answers "already answered: approve" after the answer; p5's unknown
notice is named. What the probes still show by design: two messages for a notice already on its way
(p2 B, p5), each named by the presentation; a zero-width space or a trailing period after the choice
does not match and is told the valid choices.

**Contract changes a consumer will see.** A receipt's `supersedes` for a notice carries
`notice_state` (`sent`, `pending` or `unknown_outcome`) and `message_id` None when unconfirmed; the
intent no longer names a notice kind. New operations `presentation_tell` and
`presentation_notice_superseded`; new entity kind `presentation_tell`. A projection notice intent pins
`presentation-framing:<request>` at version 0 (`control_channel_projection.framing_entity_id`).
`usable_key(key, principal, now)` is the one key rule.

## Fourth review fixes, 2026-09-23

A fourth review (no blocking finding) left eight items, probed by q1 to q7. Each was fixed test
first, with a new row (or, for item 1, new cases in an existing row) red at `fbf258a` by its own
assertions, then green, and at least two registered mutations. Items 3 and 4 are one change to the
list of notices a presentation names, so they share one commit. Before the fixes the branch merged
`origin/main` again (`357b07c`, no conflicts).

| Item | Gap at fbf258a | Fix | Row | Mutations | Commit |
| --- | --- | --- | --- | --- | --- |
| 1 (q1) | frame() pinned the key and ledger versions with separate reads after its checks, so a revocation landing in that gap was pinned as if read | Every authority input is pinned at its version in the one `authority_state` snapshot the checks read | `framing/frame-and-presenter-agree` (two new gap cases) | `frame-ledger-pin-read-later`, `frame-key-pin-read-later` | `d1cb40c` |
| 2 (q3) | The owner's accepted answer delivered again was told "already answered" | The recorded answer's own chat and platform message id get no reply | `answer/redelivered-answer-silent` | `redelivered-answer-told`, `redelivery-by-chat-only` | `311a926` |
| 3 (q2) | An older version's sent notice was preferred over the current version's unconfirmed one, which was neither named nor superseded | The first presentation of version N names and supersedes the notices of N and every older unsuperseded one, newest version first whatever its state | `projection/notices-per-version` | `older-sent-notice-preferred`, `only-first-notice-marked` | `19282f7` |
| 4 (q4) | A notice named while pending was never marked once the naming presentation was replaced | Each run reconciles every published presentation of the request that named a pending notice | `projection/pending-notice-reconciled-after-replacement` | `reconcile-current-only`, `reconcile-skips-replaced` | `19282f7` |
| 5 (q6) | A retry_after above the bound was ignored, so the next run sent into the flood window | Capped at `MAX_RETRY_AFTER` | `presentation/retry-after-capped` | `retry-after-unbounded`, `retry-after-above-bound-ignored` | `79dc7c8` |
| 6 (q7) | The colon was split before NFKC, so small and vertical colons were missed; Unicode hyphens did not separate a choice name | The whole reply is NFKC-normalized before the split; U+2010, U+2011, U+2012, U+2043 and U+2212 separate like `-` and `_` | `answer/reply-nfkc-before-split` | `split-before-nfkc`, `ascii-hyphen-only` | `bc46587` |
| 7 (q5) | A reply after the request left pending (answered in the inbox) met silence | Refused as `request_closed` and told once per message that it is no longer open | `answer/reply-after-closed` | `closed-not-told`, `closed-reported-as-stale` | `91784f8` |
| 8 | An unreadable revocation ledger record (another kind, a digest mismatch) was read as an empty ledger | The journal reader returns `UNREADABLE` and the stored-framing check refuses on it, as for a key | `framing/ledger-read-fails-closed` | `ledger-unreadable-as-empty`, `journal-reader-ignores-kind` | `03906f9` |

Two earlier registrations were re-pointed where the new code moved their anchor, with their rows
unchanged: `choice-without-nfkc` now removes the NFKC of the split, and the bounded row's second
mutation is `retry-after-boolean-accepted` because a huge value is now capped, not refused.

**Speed.** The suite's temporary store and keys now live in `/dev/shm` when it exists and is
writable, as suites 58 and 60 do, and in the platform's temporary directory elsewhere (the Mac):
`6581c72`, 6.4 to 7.9 s before, 4.6 to 4.8 s after, on the same host.

**Red at fbf258a.** `python3 -B proof/VELDO-0065/drive.py --red fbf258a` runs the current suite once
against the presentation and projection modules of `fbf258a`, unchanged, and writes
`red-at-fbf258a.json`. All seven new rows and the two new cases of `framing/frame-and-presenter-agree`
fail by their own assertions, with no section raising; no other row is red there.

**The fourth reviewer's probes, re-run unchanged.** `review-r4-rerun.log` holds q1 to q7 against the
final tree: q1's gap revocations are refused and agree with the presenter, q2 names and supersedes
both versions' notices, q3's redelivered answer gets no reply, q4's notice is marked by the
presentation that named it, q5 is told "no longer open", q6 waits after a long retry_after, and q7
matches every colon and hyphen NFKC folds. What q7 still shows by design: the ratio sign U+2236 is not a
colon and a dash is not a separator; a zero-width joiner after the choice does not match. None prints
`BUG`.

The committed probe logs escape every non-ASCII character as `\uXXXX` (the repository's docs check
allows only ASCII), so the full-width and hyphen probes read as their code points.

**Contract changes a consumer will see.** A receipt's notice `supersedes` carries `notices`, every
notice named, newest request version first, with `notice_id`, `notice_state` and `message_id` of the
first. New refusal `request_closed`. `control_channel_presentation.UNREADABLE` and `CHOICE_SEPARATORS`.

## Fifth review fixes, 2026-09-23

A fifth review found items 1 to 8 of the fourth holding, and left four items, a missing message and
six uncaught mutants, probed by p1 to p6. Each item was fixed test first in its own commit, with a new
row or row cases red at `be386e6` by their own assertions, then green, and two registered mutations.
The branch merged `origin/main` twice (`9bde509`, and `32e6ee2`, which brings the faster mutation
driver: one honest run per suite and parallel mutants with `--jobs`).

| Item | Gap at be386e6 | Fix | Row | Mutations | Commit |
| --- | --- | --- | --- | --- | --- |
| 1 (p2, blocking) | The accepted answer delivered again after the request left pending was told "no longer open" | The recorded answer (same chat and message id) is recognized before any message back | `answer/redelivered-after-closed` | `redelivery-silent-only-while-pending`, `redelivery-after-closed-told` | `ab760c6` |
| 2 (p3) | The "no longer open" message was sent before the edge scope check | The edge scope check comes before every message back | `answer/closed-tell-after-edge-scope` | `edge-scope-unchecked`, `edge-scope-against-itself` | `6223bed` |
| 3 (p1) | frame() accepted with a ledger of another kind, which the presenter refuses | frame() refuses a ledger of another kind or one that does not match its digest | `framing/ledger-read-fails-closed` (two frame() cases) | `frame-ledger-any-kind`, `frame-ledger-digest-unchecked` | `dc54e25` |
| 4 (p4) | The recorded rationale was the NFKC fold of the owner's words | Normalization only finds the split; both parts are the owner's original text | `answer/rationale-original-text` | `rationale-nfkc-folded`, `rationale-keeps-the-colon` | `e44418e` |
| message | A reply to a pending request whose presentation no longer binds met silence | Told once per message that a new presentation is coming | `answer/stale-current-told` | `stale-not-told`, `stale-told-only-on-mismatch`, `x-closed-any-refusal` | `44b6bb2` |

The reviewer's uncaught mutants now each fail a row by assertion and are registered under their
own names (`531a545`): `x-closed-any-refusal` (a pending request whose framing no longer counts is not
closed), `x-membership-pin-later` and `x-versions-pin-later` (a membership revocation and a change of
the membership versions inside frame()'s gap), `x-drop-2043` (a U+2043 choice), `x-notice-transition-any-notice`
(a presentation cannot mark a notice it did not name) and `x-reconcile-only-in-already-presented`
(reconciliation on a run that composes a new presentation). The redelivery mutations of the pending
row were re-pointed at the shared check (`_is_recorded_answer`).

**Red at be386e6.** `python3 -B proof/VELDO-0065/drive.py --red be386e6` runs the current suite once
against the modules of `be386e6`, unchanged, and writes `red-at-be386e6.json`: the five new rows and
the two new frame() cases fail by their own assertions, with no section raising, and no other row is
red there. The mutant-catching cases are green there, as they should be: the code already behaved;
they exist to make its mutants red.

**The fifth reviewer's probes, re-run unchanged.** `review-r5-rerun.log` (paths shortened to
`<probes>`, non-ASCII escaped): p1 refuses at frame() and at the presenter alike; p2's redelivered
answer gets no reply after an inbox answer or a cancel; p3 sends nothing for an edge out of scope;
p4 records the owner's own words; p5 runs every row with `/dev/shm` missing and with it unwritable,
in the platform's temporary directory, leaving nothing behind. p6 prints its `BUG (teeth)` lines
whenever a mutant behaves differently from the real module, which is its demonstration that the two
mutants are not equivalent; both are now registered and red (see above), so those lines no longer
describe a gap.

**Temporary directories.** The suite has no probe-style fixtures: its store, keys and loopback state
live in one `TemporaryDirectory` it removes itself; `drive.py` and the mutation driver likewise.

## Sixth review fixes, 2026-09-23

A sixth review found everything holding except one blocker, and asked for four more fixes and a
smaller gate cost, probed by q1 to q7. Each item was fixed test first in its own commit, with its row
or row cases red at `9319783` by their own assertions, then green.

| Item | Gap at 9319783 | Fix | Row | Mutations | Commit |
| --- | --- | --- | --- | --- | --- |
| 1 (q1, q2, q3, q6, blocking) | "A new presentation is coming" was sent where none would come (an unframed revision, a framing that no longer counts), and messages went to an owner whose membership or chat enrollment no longer held | One order for every message back: nothing at all for an owner no longer current (`owner_not_current`); a recorded answer is told "already answered: <ruling>" first; a new presentation is promised only when nothing refuses and only a bound field changed, otherwise the neutral "no longer current" | `answer/stale-current-told` (rewritten: it had asserted the promise for the framer-revoked case), `answer/owner-not-current-silent`, `answer/redelivered-after-closed` (its control now expects "already answered") | `stale-neutral-not-told`, `owner-enrollment-unchecked`, `owner-membership-unchecked`, `answered-told-only-while-pending` (plus the ones removed below) | `b570c09` |
| 2 (q7) | An out-of-scope edge re-sending the recorded answer learned `already_answered` | The edge scope check runs before the redelivery check | `answer/closed-tell-after-edge-scope` | `redelivery-before-edge-scope` | `20e0f15` |
| 3 (q4, q5) | A ledger whose `revoked` was a number raised a TypeError that took `publish()` down; a list or string was read as a set | frame() and the presenter refuse any `revoked` that is not a mapping | `framing/ledger-read-fails-closed` | `frame-ledger-any-shape` | `7cc42f5` |
| 4 | The docstring named four colons | It names the five characters it splits at, U+2A74 DOUBLE COLON EQUAL included | none (documentation) | none | `4ac1e92` |
| 5 | The mutation stage cost too much | 14 redundant mutations removed (below) | none | none | `47b1a11` |

**The removed mutations.** Every finding-65 mutation was run once on the current code
(`redundant-mutations.json` records the result). A mutation is redundant when another kept
mutation's set of failing checks is a subset of its own: every check that catches the other also
catches it, so it adds no teeth. For seven of the 14 the other's set is a strict subset; for the
other seven (the rows reading "2 of 2", "3 of 3" and "1 of 1") the two sets are equal, so the pair
were duplicates and one was kept. They were removed greedily, most failing checks first, and never
when that would leave a row with fewer than two mutations naming it; `notice-not-marked-superseded`
is kept by the lead's instruction. 84 of 98 remain, every one of the 39 criterion rows named by at
least two.

| Removed | Subsumed by | Its checks the other fails |
| --- | --- | --- |
| `published-at-from-clock` | `answer-drops-rationale` | 14 of 75 |
| `unconfirmed-notice-not-named` | `older-sent-notice-preferred` | 1 of 8 |
| `owner-currency-unchecked` | `owner-enrollment-unchecked` | 2 of 4 |
| `ascii-hyphen-only` | `x-drop-2043` | 1 of 3 |
| `edge-scope-against-itself` | `redelivery-before-edge-scope` | 1 of 3 |
| `redelivery-after-closed-told` | `redelivered-answer-told` | 3 of 3 |
| `frame-ledger-unpinned` | `frame-ledger-pin-read-later` | 1 of 2 |
| `ledger-unreadable-as-empty` | `journal-reader-ignores-kind` | 1 of 2 |
| `presenter-ledger-any-shape` | `frame-ledger-any-shape` | 2 of 2 |
| `stale-promise-on-any-refusal` | `stale-neutral-not-told` | 2 of 2 |
| `stale-told-only-on-mismatch` | `stale-neutral-not-told` | 2 of 2 |
| `x-closed-any-refusal` | `stale-neutral-not-told` | 2 of 2 |
| `reconcile-skips-replaced` | `reconcile-current-only` | 1 of 1 |
| `x-reconcile-only-in-already-presented` | `reconcile-current-only` | 1 of 1 |

Their `.diff` files remain in this directory from earlier rounds: the standing rule allows deleting
only files in the author's own scratch directory, so their removal is left to the lead;
`mutations.json` lists only the 84 registered mutations.

**Red at 9319783.** `python3 -B proof/VELDO-0065/drive.py --red 9319783` runs the current suite once
against the modules of `9319783`, unchanged, and writes `red-at-9319783.json`: the new and rewritten
cases of the five rows above fail by their own assertions, with no section raising, and no other row
is red there.

**The sixth reviewer's probes, re-run unchanged.** `review-r6-rerun.log`: q1 promises a new
presentation only where one then comes, answers "already answered" first and sends nothing to a
revoked owner; q2 sends nothing to an unenrolled chat and one message per inbound message; q3 sends
nothing for a closed request whose owner or enrollment was revoked; q4 and q5 refuse every ledger
shape by name; q7 refuses the out-of-scope edge as `not_authorized`. q6 prints its `BUG` line
whenever anything is sent after an unframed revision; what is sent there is now the neutral "no
longer current", not a promise, so that line no longer describes a defect.

## Measurements

The suite runs in about 7.5 to 9 s at the host's current load (7.60, 8.04 and 9.17 s measured at a
load average of 12 to 17 on 20 cores), 40 rows; on a quiet host it ran in about 6 s last round.
Finding 65 now has 84 mutations (98 before the redundancy cut). With the merged driver,
`python3 -B scripts/check_teeth_mutations.py --finding 65 --jobs 8` took 1 min 43 s
(`{"mutations_rejected": 84, ...}`); `drive.py`, which runs every case serially with a baseline and
a no-op per module, took 13 min 7 s. New stage estimate: the gate's mutation stage runs 88 suite
runs (84 mutants, a baseline and a no-op per mutated module) 8 in parallel, about 66 s at 6 s a run
and about 83 s at this load's 7.5 s, and its budget grows by 2 s per case (168 s); the unit stage
gains the suite's 6 to 9 s. That is about 72 to 92 s in all, still over the 60 s limit, and is
reported rather than assumed to fit.
