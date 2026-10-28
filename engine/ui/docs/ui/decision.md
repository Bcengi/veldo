# DecisionDetail and DecisionList

`DecisionList` is the inbox, ranked by the store (`rankDecisions`): the most urgent deadline first
(overdue, within a day, within three days, later, none), then the higher risk, then the earlier
deadline; a request not presented yet goes last. Each row: a lamp colored by urgency, the question,
"due in 3 d" in the urgency's color, the risk word, the scope. Props: `decisions`, `current` (the open
request id, marked `aria-current`), `now` (milliseconds, from the store's ticking clock).

`DecisionDetail` shows one decision exactly as presented and answers it inline (VELDO-0145 AC3).

## DecisionDetail props and emits

| | |
|---|---|
| `decision` | a `PendingDecision` from `features/decisions/inbox.ts`, live from the store |
| `settled(result)` | the API accepted the answer; the view re-reads the inbox |

## What it guarantees

- **Snapshot binding.** What is shown is a snapshot of the presentation taken when the decision opened
  (`shown`), and the answer body is `answerBody(shown, choice, rationale)`: the request id and version and
  the presentation id, digest and version of that snapshot. When the store later holds another version
  (a Refresh, a revision), the screen keeps showing the snapshot, says "This question changed since you
  opened it", clears the choice, disables the choices and replaces Send answer with "Load the current
  version". Only that action replaces the snapshot. `data-presentation-version` carries the bound version.
- After `stale_version:stale_presentation` the same happens: a compact refusal, the choice cleared, and
  "Load the current version" in place of Send answer.
- The question (`request.brief`), the risk statement and the exact presented text (`rendered`, under
  "As it was presented in Telegram") come from the receipt, unchanged. The authority statement and the
  request alias are behind "Who can answer this", after a plain sentence; no internal identifier is in
  the main view.
- Nothing changes before the API answers; a refusal shows in the answer bar by name; success shows
  "Answer sent" with the API's ruling.
- On a phone the choices are above the fold; the answer bar is in the flow until a choice is picked,
  then pins above the bottom bar, and the decision keeps room for it.
- Keys 1 to 9 pick a choice when focus is not in the rationale (the key hints show on wide screens with
  a pointer).
