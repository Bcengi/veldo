# ScreenHeader

The screen title (`h1`, Big Shoulders), an optional back link, an aside (screen actions such as
Refresh) and meta text (journal record read at, the dispatch id).

## Props

| Prop | Type |
|---|---|
| `title` | string |
| `back` | `{ to, label }`, optional; shown as a 44 px link |

## Slots

`aside`, `default` (meta).

## Behavior

The heading takes focus on mount (`tabindex="-1"`, no visible ring), so a screen reader announces the
new screen after navigation.
