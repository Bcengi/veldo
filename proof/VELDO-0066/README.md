# VELDO-0066 proof

Release 1 revision 3 canonical Telegram attribution. The specification status, risk and
`.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a self-approval,
and the canonical gate is run by the lead, not recorded here.

**Pending, not done: AC1's live Telegram sandbox run.** The criterion asks for a real Telegram sandbox.
None was available, so every row runs against a loopback Bot API server (real HTTP) that answers in
the platform's documented shapes. This is not live qualification. The run is still owed and needs
the owner to provide a Telegram test-environment bot.

## What was built

`.veldo/control_channel_attribution.py` (engine copy byte-identical, in `init_scaffold._FILES`, not
in `REQUIRED_SUBSTRATE`). Standard library only.

- **Acquisition.** `TelegramAcquisitionEdge` calls `getMe` (the bot's own id) and `getUpdates`
  (offset from the cursor, `allowed_updates` message and edited_message). Only the Bot API's own
  successful JSON answer counts; a transcript body, a gateway page or an error answer keeps nothing.
- **Evidence.** One immutable `channel_evidence` record per (bot, update): the update as served, its
  digest, the digest of the whole response, and the canonical fields read from the platform's own
  typed fields (update id and type, message id, date, chat id and type, sender id and is_bot, replied
  message id, chat and date). The record and the cursor move in one store transaction, so an update
  is confirmed to the platform only once kept. It is decided once.
- **Identity.** Only a `message` update is attributed. It must carry every canonical field, come from
  a person account in person (no bot account, sender_chat, via_bot, sender_business_bot,
  is_from_offline or automatic forward), not be a forward, and be sent in the sender's own private
  chat (chat id equal to the sender's user id). The stable user id maps to exactly one valid VELDO-0064
  channel enrollment, and that principal must be an active person member (VELDO-0020 membership) the
  revocation ledger does not name. Display names, usernames and labels are never read for identity.
- **Binding.** The reply must be to a message in the same chat that is a published VELDO-0065
  presentation part, and the replied message the platform delivered must be that part as published
  (sent by this bot, same bytes, same platform date). The principal must be the presentation owner.
- **Reuse.** The assertion is built by `Presenter.canonical_answer` from the platform message and
  decided by `Presenter.answer` (receipt lookup, supersession, staleness, choices, rationale, tells,
  answer record), unchanged. The attribution adds the evidence id and digest, update id, bot id and
  sender type, and is signed by the edge's restricted key from the caller's custody.
- **Observability.** Observations carry operation, update, evidence, chat, sender id, principal,
  outcome, named refusal and error class, never text, display names or the token. `metrics()` counts
  accepted and refused operations, pending (kept, undecided) work, answers and refusals by reason.

## Rows, falsifiers and red record

Suite `scripts/suites/63_veldo_0066_attribution.py` (1.5 s), real SQLite store, real OpenSSH signatures
on every journal record and edge assertion. Registry: `scripts/check_teeth_mutations.py --finding 66`
(added to the footprint with a History line). `python3 -B proof/VELDO-0066/drive.py` regenerates
`mutations.json` and the diffs: 14 mutants, each reds its named row by assertion (no section raised),
baseline and no-op copy green, 25.8 s serial.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `acquisition/platform-fields-retained` | AC1 | `platform-date-from-clock`, `cursor-not-advanced` |
| `attribution/stable-sender-identity` | AC1 | `display-name-as-identity`, `ambiguous-sender-first-wins` |
| `attribution/binds-replied-presentation` | AC2 | `replied-content-unchecked`, `replied-sender-unchecked`, `reply-chat-unchecked`, `evidence-digest-unchecked`, `evidence-fields-unchecked` |
| `attribution/person-only-authority` | AC3 | `automation-sender-as-owner`, `inline-bot-as-owner`, `business-bot-as-owner`, `offline-message-as-person`, `service-member-as-person` |

`display-name-as-identity` attributes the stranger who copies the owner's display name to the owner and
loses the renamed owner. `replied-content-unchecked` accepts a reply in a second bot's chat (same chat
id, message ids numbered again) as an answer to the first bot's presentation holding those ids.
`automation-sender-as-owner` records inline-bot, business-bot and away messages from the owner's
account as the owner's answer. Every other mutant except one produces a wrong acceptance or a wrong
record; `service-member-as-person` reds by the refusal name only (the service's message is still
refused later as `unknown_presentation`).

`install/assets` checks scaffold registration, engine identity, installation by `_lay` and journal
signatures; it has no mutation because no change to the attribution module can affect it.

**Red at 894fa12.** `python3 -B proof/VELDO-0066/drive.py --red 894fa12` extracts that tree with
`git archive`, unchanged, and runs the current suite against it: `red-at-894fa12.json`. All five rows
are red by their own assertions (52 failing checks), none raising. The module does not exist there,
so the suite drives the path that tree has: VELDO-0065's `canonical_answer` over each delivered
message. On it an inline-bot message from the owner's account, a reply whose reference was altered to
another presentation and the second bot's colliding reply are all recorded as answers, and no
evidence is kept.

## Known limits (not filed as tickets)

- After a bot token is replaced by another bot, a reply whose chat and message id are also held by
  an older receipt refuses as `presentation_mismatch` rather than binding; binding it needs the
  publishing bot recorded on the VELDO-0065 receipt.
- An owner message that is not a reply refuses as `missing_reply_reference` and gets no message back.
- Business chats (whose ids may equal a bot chat's, per the Bot API) arrive as `business_message` and
  are refused as `unsupported_update`.
- Scale note for Release 2: undecided evidence, enrollments and receipts are found by scanning
  entities of one kind, as VELDO-0065 does.
