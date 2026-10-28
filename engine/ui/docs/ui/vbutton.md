# VButton

A native `button` with Veldo's variants and a pending state. Every button that calls the API is a
`VButton` with `:pending`.

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `label` | string | required | What happens when pressed, as a verb: "Send answer" |
| `pendingLabel` | string | `label` | The progressive form shown while pending: "Sending answer" |
| `pending` | boolean | `false` | Disables the button, shows a spinner, sets `aria-busy` |
| `disabled` | boolean | `false` | |
| `variant` | `primary` `secondary` `danger` `quiet` | `primary` | One primary per region. Primary is cobalt with white text |
| `size` | `normal` `small` | `normal` | Normal is 44 px tall; `small` (36 px) only in toolbars and headers |
| `type` | `button` `submit` | `button` | |
| `block` | boolean | `false` | Full width (phone actions, sign-in) |

## Slots and emits

`icon` (before the label); `click(event)`.

## Example

```vue
<VButton label="Send answer" pending-label="Sending answer" :pending="sending" type="submit" block />
```

A link styled as a button uses the classes directly: `<RouterLink class="vbtn vbtn-primary">Answer it</RouterLink>`.

## Accessibility

The visible label is the accessible name. A pending button keeps its place and width and stays in the
tab order position it had.

## When not to use it

A navigation is a `RouterLink`, never a button.
