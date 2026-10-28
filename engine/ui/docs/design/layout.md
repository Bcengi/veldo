# Layout, spacing and motion

## Breakpoints

| Name | Width | Shell |
|---|---|---|
| phone | below 768 px | Top bar, screen, bottom bar with three destinations |
| desktop | 768 px and up | Left rail (232 px), screen |

The screens are verified at 360, 390, 1280 and 1440 px. Between 768 and 1279 px the desktop shell is
used with list and detail stacked where they would not fit side by side (decisions below 1024 px).

## Spacing

A 4 px base: `--space-1` 4, `--space-2` 8, `--space-3` 12, `--space-4` 16, `--space-5` 24,
`--space-6` 32, `--space-7` 48. Screen gutters: 16 px on phone, 32 px on desktop, set once by the
shell's main region; a view never adds its own outer horizontal padding.

## Shape

Radius encodes hierarchy, not habit: controls (buttons, inputs, choices) 8 px; panels 12 px; the
terminal body 0 inside its panel; lamps are circles. No drop shadows except the phone's pinned answer
bar, which casts one upward to show it floats above the content.

## Overflow

The page never scrolls horizontally. Long tokens (paths, ids, digests) break with
`overflow-wrap: anywhere`. Record lines wrap on phone and may wrap on desktop (a toggle); the Monaco
diff scrolls inside its own box.

## Motion

- One orchestrated moment: the lit lamp eases in when a station lights (200 ms).
- Motion that answers an action is welcome: a sheet slides from its edge, a sent answer's result
  fades in where the button was.
- Nothing else moves on its own. With `prefers-reduced-motion: reduce` all transitions are instant.
