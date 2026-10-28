# Lamp

The andon lamp, the one lit element of the design ([direction](../design/README.md)).

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `state` | `off` `here` `live` `waiting` `stop` `done` | `off` | `here`: at a station, not running. `live`: running (green, glows). `waiting`: on a person (amber, glows). `stop`: error or refused. `done`: completed (enamel) |
| `label` | string | required | The words for the state; it is the lamp's accessible name (`role="img"`) |
| `size` | `sm` `md` | `md` | 10 or 14 px |

## Rules

- A lamp always has words nearby or as its label; color alone never tells the state.
- Only `live` and `waiting` glow. Do not add glow anywhere else.

## Example

```vue
<Lamp :state="runLamp(run.state).lamp" :label="runLamp(run.state).word" />
```
