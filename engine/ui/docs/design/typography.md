# Typography

Three faces, all self-hosted from Fontsource packages (OFL-1.1) and imported in `src/main.ts`; no
font is fetched from another origin.

| Token | Face | Used for |
|---|---|---|
| `--font-display` | Big Shoulders Variable | Screen titles, station names in the strip, the wordmark |
| `--font-text` | Atkinson Hyperlegible Next Variable | All reading and operating text |
| `--font-mono` | Atkinson Hyperlegible Mono Variable | Record lines, commands, payloads, fingerprints, ids |

## Scale

A modular scale of 1.25 from a 16 px base (phone and desktop alike; nothing below 13 px).

| Token | Size / line height | Use |
|---|---|---|
| `--text-xs` | 13 / 18 | Record gutter (sequence, time), counts |
| `--text-sm` | 14 / 20 | Secondary text, toolbar controls, record lines |
| `--text-base` | 16 / 24 | Body, controls, choices |
| `--text-lg` | 20 / 28 | Section headings in Atkinson, the decision question |
| `--text-xl` | 25 / 30 | Screen titles on phone (Big Shoulders 700) |
| `--text-2xl` | 31 / 36 | Screen titles on desktop (Big Shoulders 700) |
| `--text-3xl` | 39 / 42 | The sign-in screen's wordmark |

## Rules

1. Sentence case everywhere. No all-caps labels and no letter-spaced capitals.
2. Line length for reading text stays under 75 characters (`max-width: 68ch` on prose blocks).
3. Weights: Atkinson 400 for text, 600 for emphasis and buttons; Big Shoulders 700 for titles, 600
   for station names. No other weights.
4. Mono is for machine text only. A label, a heading or a count is never mono, except the record's
   sequence and time gutter, which are machine text.
5. Numbers that update in place (counts, sequences) use `font-variant-numeric: tabular-nums`.
6. Fingerprints are set in mono at `--text-lg`, grouped as the host prints them, so the two can be
   compared group by group.
