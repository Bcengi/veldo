# ScreenHeader

The screen title (`h1`, Plex Sans semibold), an optional back link, an aside (the screen's actions or its
status, such as Refresh or the run's state) and a meta slot (the run's headline facts).

## Props

| Prop | Type |
|---|---|
| `title` | string |
| `back` | `{ to, label }`, optional; a 44 px link on a phone |

## Slots

`aside`, `default` (meta).

## Behavior

The heading takes focus on mount (`tabindex="-1"`, no visible ring), so a screen reader announces the
new screen after navigation. On a phone the run screen puts back, title and aside in one row and keeps
the back link's name for screen readers only.
