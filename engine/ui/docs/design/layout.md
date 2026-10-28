# Layout, spacing and motion

## Breakpoints

| Name | Width | Shell |
|---|---|---|
| phone | below 768 px | The screen, and a bottom bar with four destinations |
| desktop | 768 px and up | Left rail (248 px), the screen |
| wide | 1024 px and up | Side by side: the overview's panels, the inbox and the open decision |

The screens are verified at 360, 390, 1280 and 1440 px.

## Width is a decision per screen

| Screen | Width |
|---|---|
| Overview, Runs | `.screen-wide`: up to 1440 px, filling the space |
| Run | The full width, and the full height: the record takes what the header leaves |
| Decisions | Up to 1440 px; inbox 2 parts, decision 3 parts; the decision's text at 72ch |
| You, not found | `.screen-narrow`: 920 px, centered with its title |
| Sign in | A cobalt field (5 parts) beside the panel (7 parts) on desktop; a cobalt band on a phone |

## Height

The run screen and the decisions screen (wide) are exactly the viewport's height; the record, the
inbox and the open decision each scroll on their own, so the page itself never scrolls and the
headers stay in view.

## Spacing

A 4 px base: `--space-1` 4, `--space-2` 8, `--space-3` 12, `--space-4` 16, `--space-5` 24,
`--space-6` 32, `--space-7` 48. Screen gutters: 16 px on a phone, 32 px on desktop, set once by the
shell's main region; a view never adds its own outer horizontal padding.

## Shape

Radius encodes hierarchy: controls 6 px, panels and the board 10 px, kind tags 4 px, lamps and badges
round. No drop shadow except the phone's pinned answer bar, which casts one upward because it floats.

## Phone rules

- The run screen: one header row (back, unit, state and elapsed), one facts line, a one-line strip
  (lamps, and only the current station's name), one control bar (count, Follow, Raw, a search button
  that opens the field in the same bar), then the record, which gets the rest (over 55 percent).
- An open decision puts its question and choices above the fold. The answer bar is in the flow until a
  choice is picked, then pins above the bottom bar.
- Edits render as unified diffs without wrapping; long lines scroll sideways inside the diff only.

## Overflow

The page never scrolls sideways. Long tokens (paths, ids, digests) break with `overflow-wrap:
anywhere`; record lines wrap.

## Motion

- One orchestrated moment: a lamp eases in when it lights (200 ms).
- Motion that answers an action: the switch handle slides, a button shows its spinner while pending.
- Nothing else moves on its own. With `prefers-reduced-motion: reduce` all transitions are instant.
