# Colors

All colors are CSS custom properties in `src/styles/tokens.css`. Components and views use the
semantic tokens below, never a hex value and never a palette step directly. Light is the default;
`<html data-theme="dark">` switches to dark. The theme follows the system until the person picks one
(see `useTheme` in [../ui/README.md](../ui/README.md)).

## Palette steps

The named colors of the [direction](README.md) and the steps derived from them.

| Token | Light | Dark | Note |
|---|---|---|---|
| `--ink` | `#16242C` | `#E3E8E2` | Body text |
| `--ink-muted` | `#4A5A61` | `#A3B1B4` | Secondary text; 4.5:1 or better on every surface |
| `--paper` | `#EDF0EA` | `#16242C` | Base surface |
| `--paper-raised` | `#F8F9F6` | `#1D2E37` | Panels, the open decision, the terminal toolbar |
| `--paper-sunken` | `#E2E6DF` | `#111C22` | The terminal body, inputs |
| `--rule` | `#C9D0C8` | `#2C414C` | Hairlines that separate unlike things |
| `--enamel` | `#2E5E4E` | `#86C2AA` | Brand, primary action fill (light), links |
| `--enamel-ink` | `#F8F9F6` | `#10201A` | Text on an enamel fill |
| `--amber` | `#F2A900` | `#F2B52E` | Waiting on a person |
| `--amber-ink` | `#16242C` | `#16242C` | Text on amber (amber never carries white text) |
| `--amber-text` | `#8A5D00` | `#F2C35C` | Amber used as text on paper |
| `--live` | `#3FAE6A` | `#56C783` | Running, open stream |
| `--live-text` | `#1F6B3E` | `#7AD89F` | Live state as text |
| `--stop` | `#D2412C` | `#F0705C` | Error, refusal, stopped |
| `--stop-text` | `#A3301F` | `#FF9583` | Error as text |
| `--stop-wash` | `#F7E2DD` | `#3A2420` | Background behind an inline refusal |
| `--focus` | `#1F6FD1` | `#7FB3FF` | Focus ring, never used for anything else |

## Rules

1. **Signal colors carry state only.** Amber means a person is needed, live green means running,
   stop red means stopped with an error or refused. Never use them for emphasis or decoration.
2. **Never color alone.** Every state shown in color also has a word, an icon shape or a pattern.
3. **Text contrast** is at least 4.5:1 for body text and 3:1 for large text and control borders, in
   both themes. The accessibility e2e test measures the real page with axe.
4. **The lit lamp** is the only element with a glow (`--lamp-glow`), and only while lit.
5. **Monaco** gets its colors from two themes defined in `features/run/monaco-theme.ts` that read
   these tokens' hex values, so the diff matches the page in both themes.
6. **Adding a token**: add it in both themes, give it a row here, and check contrast in both.
