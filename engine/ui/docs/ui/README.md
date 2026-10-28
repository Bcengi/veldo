# Shared components

Shared components live in `src/components/`; components of one area live in `src/features/<area>/`
and are listed here too when another area may reuse them (the run terminal is reused by the
conversation screens of VELDO-0179). Each has its own page; read it before using or changing the
component, and update it in the same commit.

| Component | File | Page |
|---|---|---|
| `VButton` | `components/VButton.vue` | [vbutton.md](vbutton.md) |
| `Lamp` | `components/Lamp.vue` | [lamp.md](lamp.md) |
| `StatePanel` | `components/StatePanel.vue` | [state-panel.md](state-panel.md) |
| `RefusalNotice` | `components/RefusalNotice.vue` | [refusal-notice.md](refusal-notice.md) |
| `ScreenHeader` | `components/ScreenHeader.vue` | [screen-header.md](screen-header.md) |
| `Icon`, `Wordmark` | `components/Icon.vue`, `components/Wordmark.vue` | [icon-and-wordmark.md](icon-and-wordmark.md) |
| `RunTerminal` | `features/run/RunTerminal.vue` (with `TerminalLine`, `EditDiff`) | [run-terminal.md](run-terminal.md) |
| `StationStrip`, `LineLamps` | `features/run/StationStrip.vue`, `features/run/LineLamps.vue` | [station-strip.md](station-strip.md) |
| `DecisionDetail`, `DecisionList` | `features/decisions/` | [decision.md](decision.md) |
| PrimeVue preset | `ui/preset.ts` | [primevue-preset.md](primevue-preset.md) |

## Composables

| Composable | File | Page |
|---|---|---|
| `useAsync` | `composables/useAsync.ts` | [../patterns/api-layer.md#screen-state](../patterns/api-layer.md#screen-state) |
| `useRecordFollower` | `features/run/useRecordFollower.ts` | [../patterns/api-layer.md#live-streams](../patterns/api-layer.md#live-streams) |
| `useTheme` | `composables/useTheme.ts` | [../design/colors.md](../design/colors.md) |
| `useMedia`, `useDesktop` | `composables/useMedia.ts` | [../design/layout.md](../design/layout.md) |

## Rule

Check this list before writing a new component: extend an existing one with a prop when the job is
the same. A new shared component gets a page here with its props, emits, slots, states, accessibility
notes, an example, and when not to use it.
