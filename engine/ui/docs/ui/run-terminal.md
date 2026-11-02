# RunTerminal

A run's execution record as a live terminal (VELDO-0145 AC2). Reusable anywhere a dispatch is known;
VELDO-0179 opens it on a conversation turn's dispatch.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `dispatch` | string | The dispatch id (`dispatch/<unit>/<hex>`) |
| `follower` | the return of `useRecordFollower`, optional | The follower the screen already holds, so its header reads the same record (the run screen passes it); without it the terminal makes its own |

## Slots

`strip` with `{ run, live }`: the station strip above the control bar.

## What it guarantees

- One row (`TerminalLine`, `li[data-seq]`) per kept line, in sequence, never merged or summarized. Raw
  view shows each payload exactly.
- A compact gutter: the sequence, the time since the record's first line (`+0.4 s`, `+12 s`, `+3:05`; the
  clock time is the title), and an inline kind tag (`tool`, `output`, `agent`, `error`, `stderr`,
  `system`, `wrapper`, `finished`) on the same row as the content. On desktop the tag has its own column;
  on a phone it floats at the start of the content.
- Follows live through `useRecordFollower` (see [api-layer.md](../patterns/api-layer.md#live-streams)):
  resumes from its cursor, drops repeats, fills gaps, closes on the API's named reason.
- Tool calls show the tool and its command or path; results show output in mono (`.tb-output`); edits
  render as read-only Monaco diffs (`EditDiff`) once on screen, side by side on desktop and unified on a
  phone, with the old and new text also in the DOM as text; error lines are marked (`data-error`, a red
  rule and an `error` tag).
- Search matches the payload text; Enter and Shift+Enter step through matches; `/` opens and focuses it.
- Follow is on for a running run, off for an ended one; scrolling up turns it off and offers
  "Jump to latest".
- One control bar: the line count (and reconnects), Follow, Raw, and search. On a phone search is a
  button that opens the field in the same bar.
- When the record is refused, only the refusal shows: no strip, no controls, no empty frame; Try again
  only when the refusal is retryable.

## States

`data-state`: `loading` (a gutter-shaped skeleton), `live`, `reconnecting`, `ended`, `stopped`, `error`.

## Monaco and the content security policy

The API's policy allows no inline style. `EditDiff` loads `monaco-env.ts` first, which routes Monaco's
style elements and style attributes through the CSS object model (`src/ui/monaco-stylesheets.ts`,
`src/ui/style-attributes.ts`). Do not create a Monaco editor any other way.
