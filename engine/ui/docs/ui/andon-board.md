# AndonBoard

The overview's summary: one joined panel (a Nuxt UI `UCard`, VELDO-0229) of four cells, running, blocked,
failed and waiting on you, each a word with its lamp and a large count; while a count is above zero the
cell's lamp lights, its word takes its signal color and a rule of that color tops the cell. Each cell is
a link to the screen behind it. Two by two on a phone, four across on desktop.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `counts` | `FactoryCounts` or null (`features/overview/overview.ts`) | null while loading |

`factoryCounts(rows, unitStates, waiting)`: running is the runs in a live dispatch state; blocked is the
units in `AWAITING_AUTHORITY`; failed is the units in `FAILED`; waiting is the decisions the member can
answer. A count whose read was refused is shown as "Not readable", never as zero.

## Rules

- This is the one summary of the overview. Do not add a second board or stat cards elsewhere, and show
  no count the API's answers do not support.
- Counts are tabular; words are lower case after the number ("3 running").
- `data-count` and `data-value` on each cell are for tests.
