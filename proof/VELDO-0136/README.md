# VELDO-0136 proof

An owner whose message replies to no presentation, while a request of his waits, is told once to
reply to the request message. The specification status, risk and `.veldo/policy.yaml` are unchanged.
This proof is for independent review; it is not a self-approval, and the canonical gate is run by the
lead, not recorded here.

## What was built

- **Presenter** (`.veldo/control_channel_presentation.py`, engine copy byte-identical). `waiting`
  lists the requests waiting for one principal in one chat: the current published presentation of
  each, shown to him in that chat, not answered at its version, and still binding current authority.
  `hint_owner` takes the refused message's identity from the VELDO-0066 evidence and sends one plain
  message, as a reply to his: why it counted for nothing, "press Reply on the request message itself
  and write <choice>: <your reason>", and each waiting request as `Request: <id> (version N), choices
  ...`. Only requests with no hint yet are named. A `presentation_hint` record (keyed by the inbound
  chat and message) and one `presentation_hinted` mark per request version are created once, in one
  transaction, before the send; the platform's answer is recorded on the hint after it, through the
  presenter's existing send path.
- **Acquirer** (`.veldo/control_channel_attribution.py`, engine copy byte-identical). After the
  refusal of an attributed current person's message as `missing_reply_reference` or
  `unknown_presentation` (NOT_A_REPLY) is recorded, it calls `hint_owner`. The decision, the reasons
  and VELDO-0066's binding are unchanged; strangers, revoked owners and bots are refused before a
  principal is known and get nothing.
- **Observability.** One `hint_owner` observation per such message (cause, evidence, update, hint id,
  named requests and presentations, outcome `sent`, `not_sent`, `already_hinted`, `nothing_pending`),
  never text. `Presenter.metrics()` adds `hints_sent` and `hints_not_sent`; `Acquirer.metrics()` adds
  `not_a_reply`.

"The bot's help message" is taken to be the presenter's existing reply to an answer naming no offered
choice (it lists the choices); "another bot message" is any other bot message in the chat.

## Rows, falsifiers and red record

Suite `scripts/suites/68_veldo_0136_hints.py` (1.5 s), real SQLite store, real OpenSSH signatures, a
loopback Bot API over real HTTP, everything through `Presenter.present` and `Acquirer.acquire`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `hint/tells-owner-to-reply` | AC1 | `plain-message-not-hinted`, `hint-names-first-only` |
| `hint/owner-only-never-an-answer` | AC2 | `plain-message-recorded-as-answer`, `hint-to-anyone-waiting`, `hint-kept-as-answer` |
| `hint/once-per-pending-request` | AC3 | `hint-every-message`, `hint-renames-hinted` |

`python3 -B proof/VELDO-0136/drive.py` wrote `mutations.json` and the diffs: every mutant reds its named
row by assertion (no section raised); the baseline and both no-op copies are green. The one-hint rule
is held in three places (the due filter, each mark's expected version 0, the transition's create-once),
so the two AC3 mutants remove all three.

**Red at 8dcdd34** (origin/main before this change): `drive.py --red 8dcdd34` ran the current suite
against that tree, extracted with `git archive`: `red-at-8dcdd34.json`, all three rows red by their
own assertions (21 failing checks), none raising. There the owner's messages are refused and nothing
is sent back.

## Known limits (not filed)

- A hint the platform refuses, or whose outcome is unknown, is not retried: its marks stay, so a later
  message is not hinted for those requests (Release 2 recovery).
- A request revised to a new version is hinted again once, as a new request version waiting for an answer.
- Waiting requests are found by scanning presentation heads, as VELDO-0065 scans receipts.
