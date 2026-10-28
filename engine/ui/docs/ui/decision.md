# DecisionDetail and DecisionList

`DecisionList` is the inbox: one `RouterLink` row per pending decision, with an amber lamp when it can
be answered, its question, alias, scope and deadline.

`DecisionDetail` shows one decision exactly as presented and answers it inline (VELDO-0145 AC3).

## DecisionDetail props and emits

| | |
|---|---|
| `decision` | a `PendingDecision` from `features/decisions/inbox.ts` |
| `settled(result)` | the API accepted the answer; the view re-reads the inbox |

## What it guarantees

- The question (`request.brief`), risk, authority, framer and the exact presented text (`rendered`,
  under "As it was presented in Telegram") come from the receipt, unchanged.
- The answer body is `answerBody(presentation, choice, rationale)`: the request id and version, the
  presentation id, digest and version as shown. It is never re-read before sending.
- Nothing changes before the API answers; a refusal shows in the answer bar by name; success shows
  "Answer sent" with the API's ruling.
- On a phone the answer bar is pinned above the bottom bar, and the decision keeps room for it.
- Keys 1 to 9 pick a choice when focus is not in the rationale.
