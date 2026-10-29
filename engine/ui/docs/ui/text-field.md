# VTextField and VTextArea

Native `input` and `textarea`, bound with `v-model` (`defineModel`), 44 px tall, cobalt focus.
`inheritAttrs` is off and every attribute (`id`, `type`, `placeholder`, `maxlength`, `autocomplete`,
`data-testid`, listeners) goes to the native element.

`VTextArea` grows with what is typed by CSS alone (`field-sizing: content`, between 4.5 and 14 lines),
so it needs no script and no inline style.

## Example

```vue
<label class="field-label" for="rationale">Why this answer</label>
<VTextArea id="rationale" v-model="rationale" rows="2" placeholder="Required. One or two sentences." />
```

`VTextField` exposes `focus()` (the terminal's `/` shortcut uses it).

## Accessibility

Always a visible `<label for>` or, in a toolbar, an `sr-only` one. A placeholder is a hint, never the
label.
