# Colors

All colors are CSS custom properties in `src/styles/tokens.css`, six-digit hex (Monaco's themes read
them and append an alpha byte). Components and views use the semantic tokens below, never a hex value.
Light is the default; `<html data-theme="dark">` switches to dark. The theme follows the system until
the person picks one, in the sidebar's "Dark appearance" switch or on the You screen; both set the one
preference in `useTheme`, which puts `data-theme` and Nuxt UI's `dark` or `light` class on `<html>`
together. The palette is the owner's (VELDO-0229, Telegram 38234): page, panel, text, secondary text,
borders and the action blue below. Nuxt UI's own variables (`--ui-primary`, `--ui-bg`, `--ui-text`,
`--ui-border` and the rest) are compiled from these tokens in `src/styles/theme.css`.

## Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink` | `#1B263C` | `#E7EDF7` | Main text |
| `--ink-muted` | `#59667B` | `#A1ACC0` | Secondary text; 5.4:1 or better on every surface |
| `--paper` | `#F6F8FC` | `#10141C` | Page background |
| `--paper-raised` | `#FFFFFF` | `#181E29` | Panels, the sidebar, the open decision, the terminal frame |
| `--paper-sunken` | `#EEF2F8` | `#0C1017` | The record body, skeletons, code chips, the risk box |
| `--rule` | `#E0E6EF` | `#2A3342` | Borders and hairlines |
| `--rule-strong` | `#7D8BA3` | `#64718A` | Control borders (3:1 or better), passed stations |
| `--cobalt` | `#3956DF` | `#4862E8` | Primary action, selected radio and switch, the "here" lamp |
| `--cobalt-hover` | `#2E47C2` | `#3A52D6` | Primary action on hover: darker in both themes, so contrast holds |
| `--cobalt-ink` | `#FFFFFF` | `#FFFFFF` | Text on the action (5.9:1 light, 5.0:1 dark; 7.5:1 and 6.3:1 on hover) |
| `--cobalt-text` | `#3956DF` | `#8EA2FF` | Links, quiet buttons, the current nav entry, tool tags |
| `--cobalt-wash` | `#E8EDFC` | `#1E2950` | Selected row, current nav entry, picked choice, tool tag |
| `--board`, `--board-ink`, `--board-muted`, `--board-rule` | panel colors | panel colors | Kept for the summary panel, which now sits on the panel color |
| `--amber` | `#F2A900` | `#F2B52E` | Waiting on a person (lamp, badge, oldest decision rule) |
| `--amber-ink` | `#1B263C` | `#10141C` | Text on amber (amber never carries white text) |
| `--amber-text` | `#8A5A00` | `#F5C04A` | Amber as text: due within three days, medium risk |
| `--amber-wash` | `#FDF3DC` | `#2F2716` | Search matches, "this question changed" |
| `--live` | `#23A15C` | `#3CC27A` | Running (lamp, the summary cell's rule) |
| `--live-text` | `#1D7A47` | `#6FD39A` | Running as text |
| `--live-wash` | `#E1F5E9` | `#15301F` | Reserved for a running highlight |
| `--stop` | `#D63B2A` | `#F0705C` | Failed, refused, overdue (lamp, rule) |
| `--stop-text` | `#B42B1C` | `#FF8F7D` | Error as text: due within a day, high risk |
| `--stop-wash` | `#FBE6E2` | `#3A1D1D` | Behind a refusal and an error line |
| `--focus` | `#3956DF` | `#8EA2FF` | Focus ring (2 px, offset 2 px), also on Nuxt UI buttons |
| `--lamp-off` | `#C5CEDC` | `#3A4558` | An unlit lamp's ring |
| `--shadow-panel` | faint | faint | Under panels and cards |
| `--diff-insert`, `--diff-remove` | `#D2F0DC`, `#F9DAD5` | `#173D2A`, `#4A2222` | Monaco diff lines |

## Urgency (the inbox)

A decision's lamp and due text follow how soon it is due (`inbox.ts urgencyOf`): overdue or within a
day, stop red; within three days, amber; later or no deadline, a cobalt "here" lamp and muted text. Risk
(`riskOf`, the word a risk statement opens with) is a badge with its word in red (high), amber (medium) or
neutral (low).

## Status badges

Run states and risk are Nuxt UI `UBadge`s, subtle variant, always with their word: green (`success`)
running, amber (`warning`) starting, blocked or waiting, red (`error`) failed, refused or high risk,
neutral done, idle or low risk. Blue stays for actions and selection.

## Rules

1. **Signal colors carry state only.** Amber: a person is needed. Green: running. Red: failed, refused or
   overdue. Never emphasis or decoration.
2. **Never color alone.** Every state shown in color also has a word, an icon shape or a pattern.
3. **Contrast** is at least 4.5:1 for text and 3:1 for large text and control borders, in both themes.
   The values above were measured; the browser tests run axe on every screen and state.
4. **The lit lamp** is the only element with a glow (`--lamp-glow`), and only `live`, `waiting` and
   `stop`.
5. **Monaco** gets its colors from two themes in `features/run/monaco.ts` that read these tokens.
6. **Adding a token**: both themes, a row here, contrast checked in both.
