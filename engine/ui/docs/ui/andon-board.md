# AndonBoard

The overview's board: one dark strip (`--board`) of four cells, running, blocked, failed and waiting on
you, each a lamp, a count and a word; a cell's lamp lights in its signal color while its count is above
zero. Each cell is a link to the screen behind it. Two by two on a phone, four across on desktop.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `counts` | `FactoryCounts` or null (`features/overview/overview.ts`) | null while loading |

`factoryCounts(rows, unitStates, waiting)`: running is the runs in a live dispatch state; blocked is the
units in `AWAITING_AUTHORITY`; failed is the units in `FAILED`; waiting is the decisions the member can
answer. A count whose read was refused is shown as "Not readable", never as zero.

## Rules

- This is the one bold element of the overview. Do not add a second board or stat cards elsewhere.
- Counts are tabular; words are lower case after the number ("3 running").
- `data-count` and `data-value` on each cell are for tests.
