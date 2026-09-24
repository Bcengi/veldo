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
- **One decision per message, after intake has seen it** (review of 3bb287d). The Acquirer
  (`.veldo/control_channel_attribution.py`) records its refusal and sends nothing. The VELDO-0126
  Telegram intake pass (`.veldo/control_intake.py`, `Intake._hint`) then decides, from the Acquirer's
  recorded decision (a NOT_A_REPLY refusal of an attributed current person, taken once when the
  message was acquired), what the owner is told, with at most one bot reply:
  - taken as a clarification, or as his Reply to intake's own question: nothing;
  - taken as a new proposal while his requests wait: one reply, "I took your message as new work, not
    as an answer to a request. To answer a waiting request, press Reply on the request message
    itself...", naming the waiting requests;
  - kept as an inbox proposal whose project question intake asks: that note merged into the question,
    sent once through the presenter's send path; the question's delivery is recorded from that one
    message;
  - not taken by intake (a message with no text, a sender who was not a member when he sent it): the
    plain hint, as before. A decision that sends nothing for such a message is kept at the hint's id
    (`presentation_hint_skipped`), so a later intake pass never reaches back to it when a request
    starts waiting.

  The once-per-pending-request marks and the owner-only rule are unchanged. `hint_owner` now takes
  `taken` and `lead`, keeps `taken` on the hint, and names an error reading the waiting requests
  (`unavailable_service`) instead of raising it after the refusal is recorded.
- **Observability.** One `hint_owner` observation per such message (cause, what intake made of it,
  evidence, update, hint id, named requests and presentations, outcome `sent`, `not_sent`,
  `already_hinted`, `nothing_pending`), never text. `Presenter.metrics()` adds `hints_sent` and `hints_not_sent`; `Acquirer.metrics()` adds
  `not_a_reply`.

"The bot's help message" is taken to be the presenter's existing reply to an answer naming no offered
choice (it lists the choices); "another bot message" is any other bot message in the chat.

## Rows, falsifiers and red record

Suite `scripts/suites/68_veldo_0136_hints.py` (about 11 s), real SQLite store, real OpenSSH signatures,
a loopback Bot API over real HTTP, everything through `Presenter.present`, `Acquirer.acquire` and
`Intake.take_telegram` (the owners now hold keys, so intake takes their messages).

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `hint/tells-owner-to-reply` | AC1 | `plain-message-not-hinted`, `hint-names-first-only` |
| `hint/owner-only-never-an-answer` | AC2 | `plain-message-recorded-as-answer`, `hint-to-anyone-waiting`, `hint-kept-as-answer` |
| `hint/once-per-pending-request` | AC3 | `hint-every-message`, `hint-renames-hinted` |
| `hint/new-work-one-reply` | AC1 | `new-work-told-answers-nothing` |
| `hint/answer-without-reply-one-reply` | AC1, AC2 | `hint-before-intake` (the finding itself) |
| `hint/two-projects-one-reply` | AC1 | `question-and-note-apart` |
| `hint/intake-replies-not-hinted` | AC1 | `intake-replies-hinted` |

`plain-message-not-hinted` now removes the plain message from the intake pass's decision
(`control_intake.py`), where the decision lives.

`python3 -B proof/VELDO-0136/drive.py` wrote `mutations.json` and the diffs: every mutant reds its named
row by assertion (no section raised); the baseline and both no-op copies are green. The one-hint rule
is held in three places (the due filter, each mark's expected version 0, the transition's create-once),
so the two AC3 mutants remove all three.

**Red at 3bb287d** (this branch before the review fix): `drive.py --red 3bb287d` wrote
`red-at-3bb287d.json`: exactly the four new rows red by their own assertions, none raising, the three
earlier rows green. There the Acquirer hints before intake, so new work is told it "answers nothing",
the two-project owner gets two replies, and his Reply to intake's question gets a false hint.

**Red at 8dcdd34** (origin/main before this change): `drive.py --red 8dcdd34` ran the current suite
against that tree, extracted with `git archive`: `red-at-8dcdd34.json`, all three rows red by their
own assertions (21 failing checks), none raising. There the owner's messages are refused and nothing
is sent back.

## Known limits (not filed)

- A hint the platform refuses, or whose outcome is unknown, is not retried: its marks stay, so a later
  message is not hinted for those requests (Release 2 recovery).
- A request revised to a new version is hinted again once, as a new request version waiting for an answer.
- Waiting requests are found by scanning presentation heads, as VELDO-0065 scans receipts.
