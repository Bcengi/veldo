# VButton

PrimeVue's `Button` styled by the preset, with a pending state. Every button that calls the API is a
`VButton` with `:pending`.

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `label` | string | required | What happens when pressed, as a verb: "Send answer" |
| `pendingLabel` | string | `label` | The progressive form shown while pending: "Sending answer" |
| `pending` | boolean | `false` | Disables the button, shows a spinner, sets `aria-busy` |
| `disabled` | boolean | `false` | |
| `variant` | `primary` `secondary` `danger` `quiet` | `primary` | One primary per region |
| `size` | `normal` `small` | `normal` | `small` (32 px) only in dense desktop toolbars |
| `type` | `button` `submit` | `button` | |
| `block` | boolean | `false` | Full width (phone actions, sign-in) |

## Emits

`click(event)`.

## Example

```vue
<VButton label="Send answer" pending-label="Sending answer" :pending="sending" type="submit" block />
```

## Accessibility

The visible label is the accessible name. Normal size is 44 px tall. A pending button keeps its width
and focus.

## When not to use it

A navigation is a `RouterLink`, never a button.
