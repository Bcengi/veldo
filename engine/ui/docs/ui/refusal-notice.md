# RefusalNotice

A named refusal where it happened: a sentence, the fix, and the API's own name in small mono text.
`role="alert"`, `data-refusal` carries the full name for tests and support.

## Props

| Prop | Type | Default |
|---|---|---|
| `refusal` | `{ refusal, error }` (an `ApiRefusal`) | required |
| `compact` | boolean | `false`, for use inside an action bar |

## Slot

`default`: an action that fixes it ("Try again", "Reload").

## Rules

- Put it beside the action the refusal concerns (inside the answer bar, inside the terminal), never as
  a toast and never at the top of the page for an action lower down.
- Sentences come from `api/refusal.ts`; add one there for a new reason rather than writing text here.
