# Shared components

Shared components live in `src/components/`; components of one area live in `src/features/<area>/`
and are listed here too when another area may reuse them (the run terminal is reused by the
conversation screens of VELDO-0179). Each has its own page; read it before using or changing the
component, and update it in the same commit.

Shared buttons, cards, badges and the account avatar are Nuxt UI's (VELDO-0229, the owner's choice):
`UApp` at the root, `UButton` under `VButton`, `UCard` for panels, `UBadge` for status and counts,
`UAvatar` in the sidebar and on the You screen, `USwitch` for the sidebar's appearance switch. They are
imported explicitly from `@nuxt/ui/components/<Name>.vue` and themed from Veldo's tokens
(`src/styles/theme.css`; the card's corners and padding in `vite.config.ts`). The text fields, radios and
the account screen's switch stay Veldo's own on native elements, so keyboard, form and screen reader
behavior are the browser's. PrimeVue stays denied (free and paid tiers, PLAN-0019 C16).

## Controls

| Component | File | Page |
|---|---|---|
| `VButton` | `components/VButton.vue` | [vbutton.md](vbutton.md) |
| `VTextField`, `VTextArea` | `components/VTextField.vue`, `components/VTextArea.vue` | [text-field.md](text-field.md) |
| `VRadio` | `components/VRadio.vue` | [radio.md](radio.md) |
| `VSwitch` | `components/VSwitch.vue` | [switch.md](switch.md) |
| `CopyId` | `components/CopyId.vue` | [copy-id.md](copy-id.md) |

## Display and structure

| Component | File | Page |
|---|---|---|
| `Lamp` | `components/Lamp.vue` | [lamp.md](lamp.md) |
| `StatePanel` | `components/StatePanel.vue` | [state-panel.md](state-panel.md) |
| `RefusalNotice` | `components/RefusalNotice.vue` | [refusal-notice.md](refusal-notice.md) |
| `ScreenHeader` | `components/ScreenHeader.vue` | [screen-header.md](screen-header.md) |
| `Icon`, `Wordmark` | `components/Icon.vue`, `components/Wordmark.vue` | [icon-and-wordmark.md](icon-and-wordmark.md) |
| `AndonBoard` | `features/overview/AndonBoard.vue` | [andon-board.md](andon-board.md) |
| `RunList` | `features/run/RunList.vue` | [run-list.md](run-list.md) |
| `RunTerminal` | `features/run/RunTerminal.vue` (with `TerminalLine`, `EditDiff`) | [run-terminal.md](run-terminal.md) |
| `StationStrip`, `LineLamps` | `features/run/StationStrip.vue`, `features/run/LineLamps.vue` | [station-strip.md](station-strip.md) |
| `DecisionDetail`, `DecisionList` | `features/decisions/` | [decision.md](decision.md) |

## Composables

| Composable | File | Page |
|---|---|---|
| `useAsync` | `composables/useAsync.ts` | [../patterns/api-layer.md#screen-state](../patterns/api-layer.md#screen-state) |
| `useRecordFollower` | `features/run/useRecordFollower.ts` | [../patterns/api-layer.md#live-streams](../patterns/api-layer.md#live-streams) |
| `useNow` | `composables/useNow.ts` | The time, ticking at a chosen interval (elapsed time, "due in") |
| `useTheme` | `composables/useTheme.ts` | [../design/colors.md](../design/colors.md): the one theme preference, driving `data-theme` and Nuxt UI's class |
| `useMedia`, `useDesktop` | `composables/useMedia.ts` | [../design/layout.md](../design/layout.md) |

## Rule

Check this list before writing a new component: extend an existing one with a prop when the job is
the same. A new shared component gets a page here with its props, emits, slots, states, accessibility
notes, an example, and when not to use it.
