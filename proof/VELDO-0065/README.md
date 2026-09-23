# VELDO-0065 proof

Release 1 revision 3 versioned Telegram presentation receipts and presentation-bound answers. The
specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent
review; it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

`.veldo/control_channel_presentation.py` (canonical and engine copies byte-identical, in
`init_scaffold._FILES`, not in `REQUIRED_SUBSTRATE` because no validator loads it). Standard library
only. It takes the store, membership, VELDO-0064 projection and assignment modules and the VELDO-0064
`Inbox` as arguments, so a copy loads from any path. Since review r3 the VELDO-0064 projection
(`.veldo/control_channel_projection.py`, added to the footprint with a History line) defers to it
when presentations are enabled; see the review fixes below.

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
with the key active when the store accepted the command (reviews r1, r2). The authority statement is
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
- **The acceptance time of a framing** is the store's own publication record (`committed_at`),
  which the store writes in the same transaction. `control_store.execute` lets its caller supply
  that time, so it is only as trustworthy as the authority process that holds the store connection.

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
real `_lay` writer and that sampled journal signatures verify with `ssh-keygen`.

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

## Measurements

The suite runs in about 3.0 s (`VELDO-0065 suite seconds` 2.97, 3.00 and 3.04 on three runs), 16
rows. Finding 65 has 31 mutations, 18 of them added by the review fixes. The gate's mutation stage
runs one baseline and one no-op per mutated module (presentation and projection) and one run per
mutant: 35 runs of about 3 s, 8 in parallel, so about 13 s of wall time, and its budget grows by 2 s
per case (62 s). The unit stage gains the suite's 3 s. `python3 -B scripts/check_teeth_mutations.py
--finding 65` took 3 min 9 s serially (`{"mutations_rejected": 31, ...}`); `drive.py` took 2 min 0 s
serially on a shared host.
