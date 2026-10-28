# Typography

One family in two members, self-hosted from Fontsource packages (OFL-1.1) and imported in
`src/main.ts`; no font is fetched from another origin.

| Token | Face | Used for |
|---|---|---|
| `--font-text` | IBM Plex Sans Variable | Every title, label, control and line of reading text |
| `--font-mono` | IBM Plex Mono (400, 500) | The record (gutter, commands, output, payloads), copyable ids, the fingerprint |

## Scale

From a 16 px base; nothing below 13 px.

| Token | Size | Use |
|---|---|---|
| `--text-xs` | 13 | Gutter numbers and times, kind tags, badges, the answer binding line |
| `--text-sm` | 14 | Secondary text, facts rows, toolbar controls, record lines |
| `--text-base` | 16 | Body, controls, choices, panel titles |
| `--text-lg` | 18 | The oldest decision's question, the run title on a phone |
| `--text-xl` | 22 | The decision question, the wordmark, the fingerprint |
| `--text-2xl` | 28 | Screen titles |
| `--text-3xl` | 36 | Andon counts on a phone (44 px on desktop), the sign-in wordmark |

## Rules

1. Sentence case everywhere. No all-caps labels and no letter-spaced capitals.
2. Reading text stays under 75 characters a line (`--measure`, 68ch).
3. Weights: 400 text, 500 secondary emphasis, 600 labels and buttons, 650 titles. Titles track at
   -0.015em; nothing is condensed.
4. Mono is for machine text and copied ids only. A label, heading, count or unit id is never mono.
5. Numbers that update in place (counts, elapsed time, gutter) use `font-variant-numeric: tabular-nums`.
6. The fingerprint is set in mono at `--text-xl`, four groups to a row, so it can be read aloud group by
   group against `veldo factory passkey`.
