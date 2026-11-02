# ScreenHeader

The screen's slim top bar (Telegram 38255): 50 px, the full width of the screen, a bottom border. On desktop
the panel toggle (a Nuxt UI `UButton`, "Expand sidebar" or "Collapse sidebar", `aria-expanded`, controlling
the rail) comes first; then an optional back link, the screen title (`h1`, Plex Sans semibold, 18 px) and an
aside at the right (the screen's actions or its status, such as Refresh or the run's state). A meta slot
below the bar holds the screen's summary (the run's headline facts, the runs' KPI tiles).

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
