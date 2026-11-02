# Interactivity

## Actions that call the API

- Use `VButton` with `:pending`. While pending the button keeps its width, shows a small spinner and
  the label in the progressive form ("Sending answer"), and is disabled; it is never hidden.
- The result appears where the person is looking: under the button, inside the same region, with
  `role="status"` for outcomes and `role="alert"` for refusals.
- The same action keeps the same verb through the flow: "Send answer" produces "Answer sent".

## Focus

- Every interactive element shows `--focus` as a 2 px outline offset 2 px on `:focus-visible`. Never
  remove an outline without this replacement.
- Opening a sheet or dialog moves focus into it; closing returns focus to what opened it.
- After navigation the screen title (an `h1` with `tabindex="-1"`) receives focus, so screen readers
  announce the new screen.
- After an answer is refused, focus stays on the action; the refusal is announced by its alert role.

## Keyboard

| Where | Key | Does |
|---|---|---|
| Run terminal | `/` | Focus search |
| Run terminal | `Enter` / `Shift+Enter` in search | Next / previous match |
| Run terminal | `End` | Jump to the latest line and turn follow on |
| Decision | `1` to `9` | Pick that choice (when focus is not in the rationale) |
| Anywhere | `Tab` order | Follows reading order; no positive `tabindex` |

Shortcuts are listed in the terminal's help popover and never the only way to do anything.

## Follow mode

The terminal follows the end of the record while follow is on. Scrolling up turns follow off and
shows "Jump to latest (n new)"; pressing it or `End` turns follow on again. Follow is on by default
for a running run and off for an ended one.

## Lists

Rows that open something are links (`<RouterLink>`), so they work with middle click, long press and
keyboard. The whole row is the target; there is no separate small "open" button.

## Hover

Hover may reveal nothing that is not also available by focus and by touch. A hover style is a quiet
background change, never a transform.
