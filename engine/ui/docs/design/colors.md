# Colors

All colors are CSS custom properties in `src/styles/tokens.css`, six-digit hex (Monaco's themes read
them and append an alpha byte). Components and views use the semantic tokens below, never a hex value.
Light is the default; `<html data-theme="dark">` switches to dark. The theme follows the system until
the person picks one on the You screen (`useTheme`).

## Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink` | `#0E1A2E` | `#E4EAF5` | Body text |
| `--ink-muted` | `#4A5772` | `#9BA8C2` | Secondary text; 6:1 or better on every surface |
| `--paper` | `#F2F5FA` | `#0D1626` | Base surface |
| `--paper-raised` | `#FFFFFF` | `#15213A` | Panels, the rail, the open decision, the terminal frame |
| `--paper-sunken` | `#E7ECF4` | `#0A1120` | The record body, skeletons, code chips |
| `--rule` | `#D5DCE8` | `#23314D` | Hairlines between unlike things |
| `--rule-strong` | `#7D8BA3` | `#5A6E94` | Control borders (3:1 or better), passed stations |
| `--cobalt` | `#2349D4` | `#2F5AE6` | Primary fill, selected radio and switch, the "here" lamp |
| `--cobalt-hover` | `#1B3BB0` | `#3D66EE` | Primary fill on hover |
| `--cobalt-ink` | `#FFFFFF` | `#FFFFFF` | Text on cobalt (7.1:1 light, 5.6:1 dark) |
| `--cobalt-text` | `#2349D4` | `#8EACFF` | Links, quiet buttons, the current nav entry, tool tags |
| `--cobalt-wash` | `#E3E9FB` | `#1A2B52` | Selected row, current nav entry, picked choice, tool tag |
| `--board` | `#0E1A2E` | `#142A5C` | The andon board |
| `--board-ink` | `#FFFFFF` | `#FFFFFF` | Lit counts on the board |
| `--board-muted` | `#9FB0D0` | `#C9D4EA` | Unlit counts and words on the board (7:1 or better) |
| `--board-rule` | `#23314D` | `#2A4380` | Lines between board cells |
| `--amber` | `#F2A900` | `#F2B52E` | Waiting on a person (lamp, badge, oldest decision rule) |
| `--amber-ink` | `#0E1A2E` | `#0E1A2E` | Text on amber (amber never carries white text) |
| `--amber-text` | `#8A5A00` | `#F5C04A` | Amber as text: due within three days, medium risk |
| `--amber-wash` | `#FBF0D6` | `#33291A` | Search matches, "this question changed" |
| `--live` | `#23A15C` | `#3CC27A` | Running (lamp only) |
| `--live-text` | `#1D7A47` | `#6FD39A` | Running as text |
| `--stop` | `#D63B2A` | `#F0705C` | Failed, refused, overdue (lamp, rule) |
| `--stop-text` | `#B42B1C` | `#FF8F7D` | Error as text: due within a day, high risk |
| `--stop-wash` | `#FBE6E2` | `#3A1D1D` | Behind a refusal and an error line |
| `--focus` | `#2349D4` | `#8EACFF` | Focus ring (2 px, offset 2 px) |
| `--lamp-off` | `#C5CEDC` | `#2E3D5C` | An unlit lamp's ring |
| `--diff-insert`, `--diff-remove` | `#D2F0DC`, `#F9DAD5` | `#173D2A`, `#4A2222` | Monaco diff lines |

## Urgency (the inbox)

A decision's lamp and due text follow how soon it is due (`inbox.ts urgencyOf`): overdue or within a
day, stop red; within three days, amber; later or no deadline, a cobalt "here" lamp and muted text. Risk
(`riskOf`, the word a risk statement opens with) is a word in red (high), amber (medium) or muted (low).

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
