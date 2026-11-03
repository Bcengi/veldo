# VButton

Veldo's button, built on Nuxt UI's `UButton` (VELDO-0229) with its interface unchanged: it renders one
`button` with Veldo's variants and a pending state. Every button that calls the API is a `VButton` with
`:pending`. Every attribute passed (`data-testid`, `aria-*`) lands on the button. The variants map onto
Nuxt UI: primary is `primary` solid with white text and a darker hover (`--accent-hover`, so contrast
holds), secondary is `neutral` outline, danger is `error` outline, quiet is `primary` ghost; normal is
Nuxt UI's `lg` size held to 44 px, small is `md` held to 36 px. Nuxt UI's translucent focus outline is
replaced by Veldo's solid 2 px `--focus` outline. Tested in `VButton.spec.ts`.

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `label` | string | required | What happens when pressed, as a verb: "Send answer" |
| `pendingLabel` | string | `label` | The progressive form shown while pending: "Sending answer" |
| `pending` | boolean | `false` | Disables the button, shows Nuxt UI's loading icon (bundled), sets `aria-busy` |
| `disabled` | boolean | `false` | |
| `variant` | `primary` `secondary` `danger` `quiet` | `primary` | One primary per region. Primary is solid inverted (near-black with white text on light, near-white with dark text on dark); secondary bordered neutral; quiet plain (Telegram 38255) |
| `size` | `normal` `small` | `normal` | Normal is 44 px tall; `small` (36 px) only in toolbars and headers |
| `type` | `button` `submit` | `button` | |
| `block` | boolean | `false` | Full width (phone actions, sign-in) |

## Slots and emits

`icon` (before the label); `click(event)`.

## Example

```vue
<VButton label="Send answer" pending-label="Sending answer" :pending="sending" type="submit" block />
```

A link styled as a button uses the classes directly: `<RouterLink class="vbtn vbtn-primary">Answer it</RouterLink>`,
or is a `UButton` with `to` and the same overrides (the overview's "Answer it").

## Accessibility

The visible label is the accessible name. A pending button keeps its place and width and stays in the
tab order position it had.

## When not to use it

A navigation is a `RouterLink`, never a button.
