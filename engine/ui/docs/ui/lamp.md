# Lamp

The andon lamp ([direction](../design/README.md)): the one lit element of the design.

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `state` | `off` `here` `live` `waiting` `stop` `done` | `off` | `off`: a ring. `here`: at a station, not running, or due later (cobalt). `live`: running (green, glows). `waiting`: on a person (amber, glows). `stop`: failed, refused, overdue (red, glows). `done`: finished (grey, filled) |
| `label` | string | required | The words for the state; the lamp's accessible name (`role="img"`). Pass `''` with `aria-hidden="true"` when the words are right beside it |
| `size` | `sm` `md` | `md` | 9 or 12 px |

## Rules

- A lamp always has words nearby or as its label; color alone never tells the state.
- Only `live`, `waiting` and `stop` glow. Do not add glow anywhere else.

## Example

```vue
<Lamp :state="runSignal(run.state, run.unitState).lamp" :label="runSignal(run.state, run.unitState).word" />
```
