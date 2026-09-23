# VELDO-0065 proof

Release 1 revision 3 versioned Telegram presentation receipts and presentation-bound answers. The
specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent
review; it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

`.veldo/control_channel_presentation.py` (canonical and engine copies byte-identical, in
`init_scaffold._FILES`, not in `REQUIRED_SUBSTRATE` because no validator loads it). Standard library
only. It takes the store, membership and VELDO-0064 projection modules and the VELDO-0064 `Inbox` as
arguments, so a copy loads from any path.

**The request and its three digests.** The request is the inbox assignment at one request version.
`request_digest` covers the request id, the request version and every accepted content field (kind,
owner, scope, deadline, budget, brief, choices, subject, unit, requester), so two revisions with equal
content are two requests. `subject_digests` is the assignment's subject. The presentation digest
(`brief_digest`, the authority contract's field name) is the SHA-256 of the exact rendered bytes. The
presentation key is `presentation:telegram_chat:<request>:<request version>:<presentation digest>`.

**What is shown.** `render` produces plain text from the receipt's own bound fields: request id,
version and digest, presentation version, the supersession line when there is one, owner, scope,
deadline, budget, subject digests, the risk statement, the authority statement, the offered choices,
the brief, and how to answer. The risk statement comes from a `frame` command: the requester (or a
project owner) signs it for the current request version, and the store keeps the signed command.
A framing counts only when that signed command binds exactly this request, version and statement
and verifies against the key that accepted it, so a framing written by any other store command
frames nothing. The authority statement is derived from the owner's current membership, never
written by anyone.

**Receipts.** One immutable `channel_presentation` receipt per presentation key, committed as a
`pending` intent before the Bot API `sendMessage` call and completed once from what the platform
returned (chat id, message id, date, stored text, the message it replies to). Outcomes are
`published`, `anomaly` (`presentation_mismatch`, `chat_mismatch`, `supersession_mismatch`),
`refused` (only a definite Telegram 4xx error answer; the only outcome attempted again) and
`unknown_outcome`. A completed receipt is never written again. `receipt_problems` recomputes every
bound field from the receipt's own request snapshot and compares the rendered bytes and date with
what the platform holds at the recorded chat and message.

**Visible supersession.** A `channel_presentation_head` entity per request names the current
confirmed presentation, every published one in order and which one superseded which. When current
authority no longer matches the current presentation (any of request id, version or digest, subject
digests, risk or authority statement, choices, owner or enrolled chat), the next presentation names
the one it supersedes in its bytes and is sent as a Telegram reply to the superseded message
(`reply_parameters`). The platform's returned `reply_to_message` is checked, and the head moves in
the same transaction that confirms the replacement's publication. The superseded receipt is left
untouched. A current presentation that still binds current authority is never sent again.

**Answers.** An answer is a canonical Telegram assertion (`veldo.presentation_answer/v1`) that the
Telegram edge signs with the channel's restricted key (`authority_contract.CHANNELS` names it
`edge-telegram`). `canonical_answer` builds it from the Bot API message object of the owner's reply:
the presentation it addresses (id, digest, version), the ruling and rationale (`<choice>: <reason>`),
and the platform's message id, sender id, date, chat and replied-to message. A reply from a bot is
refused. `Presenter.answer` refuses by name, in this order: `invalid_input`, `not_authorized` (no
restricted edge key, a signature that does not verify, an edge that is not an active service member),
`missing_presentation`, `unknown_presentation`, `unseen_presentation` (no confirmed publication),
`evidence_mismatch` (the reply is not to the named message in its chat), `not_owner`,
`superseded_presentation`, `stale_presentation` (the receipt no longer binds current authority),
`invalid_input` (unoffered ruling), `missing_rationale`, `already_settled`. The first accepted answer
writes a `presentation_answer` record (ruling, rationale, presentation reference, platform
attribution, the signed assertion and its signature) and the one `presentation_settlement` of that
request version, in one store command that pins the version of every input the decision read.
Rejection is an ordinary ruling and is recorded the same way.

**Observability.** Every operation appends an observation with the authority coordinates, operation,
request, accepted input versions, outcome, named refusal and its error class (invalid input, missing
authority, missing evidence, stale subject, unavailable service, unknown outcome), never shown text,
rationale, signatures or the token. `metrics()` counts accepted and refused operations, pending
entries not presented as current authority requires, and unknown or anomalous receipts. Receipts,
the head and answer records join accepted inputs, platform observations and authority records by id.

## Narrowest seams for dependencies not on main

- **Canonical acquisition (VELDO-0066) and edge enrollment and delegation (VELDO-0067).** Nothing here
  pulls updates from Telegram. The suite's loopback platform holds the owner's reply as the Bot API
  message object it would deliver, and `canonical_answer` maps that object to the assertion. The
  edge's authority is its restricted key in the store keyring plus an active `service` membership;
  the per-channel delegation records of VELDO-0067 are not consulted. The sender is matched to the
  owner by the enrolled private chat id (for a Telegram private chat the chat id is the user id).
- **Settlement and quorum (VELDO-0068).** An accepted answer settles its request version once for the
  one owner who may answer. It does not move the inbox assignment to `SUBMITTED` and admits no
  blocked work; that consumer, principal quorum and decision effects are VELDO-0068.
- **Live edge qualification (VELDO-0073).** The suite runs a loopback Bot API server (real HTTP) that
  answers with the platform's `sendMessage` shape, links a reply as Telegram does and refuses a reply
  to a message it does not hold. No live network or real token was used.
- **The VELDO-0064 projection** is unchanged and still sends its inbox notice. The two are separate
  records; which one a deployment runs for decisions is the later journey's wiring.

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
baseline and a no-op copy, both green. `python3 -B proof/VELDO-0065/drive.py` regenerates both.

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
presentation's answer settles, a second answer is `already_settled`, and two other current
presentations settle with `reject` and `defer`. The second row checks the answer record keeps the
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

## Measurements

The suite runs in about 1.5 to 2.1 s (`VELDO-0065 suite seconds`), 7 rows. The gate's mutation stage
adds one baseline, one no-op and 13 mutant runs of that suite (about 2 s each, 8 in parallel), and
its budget grows by 2 s per case. `python3 -B scripts/check_teeth_mutations.py --finding 65` takes
about 50 s serially; `drive.py` took 30 to 38 s serially on a shared host.
