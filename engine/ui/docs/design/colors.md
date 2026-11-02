# Colors

All colors are CSS custom properties in `src/styles/tokens.css`, six-digit hex (Monaco's themes read
them and append an alpha byte). Components and views use the semantic tokens below, never a hex value.
Light is the default; `<html data-theme="dark">` switches to dark. The theme follows the system until
the person picks one, in the sidebar's "Dark appearance" switch or on the You screen; both set the one
preference in `useTheme`, which puts `data-theme` and Nuxt UI's `dark` or `light` class on `<html>`
together. The look is the owner's style direction (VELDO-0229, Telegram 38255, which replaced the blue
palette of 38234): neutral surfaces, white page and panels in light, a near-black page with panels barely
lighter in dark, thin neutral borders, no shadows, and the main action solid inverted. Nuxt UI's own variables
(`--ui-primary`, `--ui-bg`, `--ui-text`, `--ui-border`, its neutral scale and the rest) are compiled from these
tokens in `src/styles/theme.css`.

## Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink` | `#171717` | `#F5F5F5` | Main text |
| `--ink-muted` | `#6E6E6E` | `#A3A3A3` | Secondary text; 4.6:1 or better on every surface |
| `--paper` | `#FFFFFF` | `#171717` | Page background, the sidebar and the top bars |
| `--paper-raised` | `#FFFFFF` | `#1C1C1C` | Panels and cards, the open decision, the terminal frame |
| `--paper-sunken` | `#FAFAFA` | `#121212` | The record body, skeletons, code chips, the risk box |
| `--rule` | `#E5E5E5` | `#2B2B2B` | The 1px borders of every panel, row dividers, the top bar's bottom border |
| `--rule-strong` | `#8F8F8F` | `#737373` | Control borders (3:1 or better), passed stations |
| `--accent` | `#171717` | `#F5F5F5` | The main action (solid inverted), selected radio, switch and segmented tab, the "here" lamp |
| `--accent-hover` | `#404040` | `#D4D4D4` | The main action on hover; contrast holds (10.4:1 light, 12.1:1 dark) |
| `--accent-ink` | `#FFFFFF` | `#171717` | Text on the action (17.9:1 light, 16.4:1 dark) |
| `--accent-text` | `#171717` | `#F5F5F5` | Links, quiet buttons, tool tags |
| `--accent-wash` | `#F2F2F2` | `#2B2B2B` | Hover and selection fill: the current nav entry, the selected row, the picked choice |
| `--board`, `--board-ink`, `--board-muted`, `--board-rule` | panel colors | panel colors | Kept for the summary panel, which sits on the panel color |
| `--amber` | `#F2A900` | `#F2B52E` | Waiting on a person (lamp, badge) |
| `--amber-ink` | `#171717` | `#171717` | Text on amber (amber never carries white text) |
| `--amber-text` | `#8A5A00` | `#F5C04A` | Amber as text: due within three days, medium risk |
| `--amber-wash` | `#FDF3DC` | `#2F2716` | Search matches, "this question changed" |
| `--live` | `#23A15C` | `#3CC27A` | Running (lamp) |
| `--live-text` | `#1D7A47` | `#6FD39A` | Running as text |
| `--live-wash` | `#E1F5E9` | `#15301F` | Reserved for a running highlight |
| `--stop` | `#D63B2A` | `#F0705C` | Failed, refused, overdue (lamp) |
| `--stop-text` | `#B42B1C` | `#FF8F7D` | Error as text: due within a day, high risk |
| `--stop-wash` | `#FBE6E2` | `#3A1D1D` | Behind a refusal and an error line |
| `--focus` | `#171717` | `#E5E5E5` | Focus ring (2 px, offset 2 px), also on Nuxt UI buttons |
| `--lamp-off` | `#D4D4D4` | `#474747` | An unlit lamp's ring |
| `--shadow-panel`, `--shadow-float` | none | none | The look has no shadows; borders separate surfaces |
| `--diff-insert`, `--diff-remove` | `#D2F0DC`, `#F9DAD5` | `#173D2A`, `#4A2222` | Monaco diff lines |

## Urgency (the inbox)

A decision's lamp and due text follow how soon it is due (`inbox.ts urgencyOf`): overdue or within a
day, stop red; within three days, amber; later or no deadline, a neutral "here" lamp and muted text. Risk
(`riskOf`, the word a risk statement opens with) is a badge with its word in red (high), amber (medium) or
neutral (low).

## Status badges

Run states and risk are Nuxt UI `UBadge`s, subtle variant, always with their word: green (`success`)
running, amber (`warning`) starting, blocked or waiting, red (`error`) failed, refused or high risk,
neutral done, idle or low risk. Actions and selection are neutral (Telegram 38255).

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
