# Lamp

The andon lamp ([direction](../design/README.md)): the one lit element of the design.

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `state` | `off` `here` `live` `waiting` `stop` `done` | `off` | `off`: a ring. `here`: at a station, not running, or due later (the accent, ink). `live`: running (green). `waiting`: on a person (amber). `stop`: failed, refused, overdue (red). `done`: finished (grey, filled) |
| `label` | string | required | The words for the state; the lamp's accessible name (`role="img"`). Pass `''` with `aria-hidden="true"` when the words are right beside it |
| `size` | `sm` `md` | `md` | 9 or 12 px |

## Rules

- A lamp always has words nearby or as its label; color alone never tells the state.
- No lamp glows (`--lamp-glow` is `none`, Telegram 38255).

## Example

```vue
<Lamp :state="runSignal(run.state, run.unitState).lamp" :label="runSignal(run.state, run.unitState).word" />
```
