# RunTerminal

A run's execution record as a live terminal (VELDO-0145 AC2). Reusable anywhere a dispatch is known;
VELDO-0179 opens it on a conversation turn's dispatch.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `dispatch` | string | The dispatch id (`dispatch/<unit>/<hex>`) |
| `unitState` | string or null | Passed through for the strip |

## Slots

`strip` with `{ run, live }`: the station strip above the toolbar (the run screen passes `StationStrip`).

## What it guarantees

- One row (`TerminalLine`, `li[data-seq]`) per kept line, in sequence, never merged or summarized. Raw
  view shows each payload exactly.
- Follows live through `useRecordFollower` (see [api-layer.md](../patterns/api-layer.md#live-streams)):
  resumes from its cursor, drops repeats, fills gaps, closes on the API's named reason.
- Tool calls show the tool and its command or path; results show output in mono (`.tb-output`); edits
  render as read-only Monaco diffs (`EditDiff`) once on screen, with the old and new text also in the
  DOM as text; error lines are marked (`data-error`, a red rule and the word "Error").
- Search matches the payload text; Enter and Shift+Enter step through matches.
- Follow is on for a running run, off for an ended one; scrolling up turns it off and offers
  "Jump to latest".

## States

`data-state`: `loading`, `live`, `reconnecting`, `ended`, `stopped`, `error` (with the refusal and no
lines).

## Monaco and the content security policy

The API's policy allows no inline style. `EditDiff` loads `monaco-env.ts` first, which routes Monaco's
style elements and style attributes through the CSS object model (`src/ui/monaco-stylesheets.ts`,
`src/ui/style-attributes.ts`). Do not create a Monaco editor any other way.
