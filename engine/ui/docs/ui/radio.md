# VRadio

One radio of a group: a native `input type="radio"` laid over Veldo's ring (20 px), so arrow keys,
Space, form submission and the accessible role are the browser's. Wrap it in the `label` that names it;
the whole label is the target (48 px choice rows in the decision).

## Props

| Prop | Type | Meaning |
|---|---|---|
| `v-model` | string or null | The picked value |
| `value` | string | This radio's value |
| `name` | string | The group name |
| `inputId` | string | The input's id (tests and keyboard checks use `#choice-0`) |

## Example

```vue
<label class="choice" :data-choice="c">
  <VRadio v-model="choice" :input-id="`choice-${i}`" name="choice" :value="c" />
  <span class="choice-label">{{ choiceLabel(c) }}</span>
</label>
```

Checked: a cobalt ring and dot. Focus: the focus ring around the box (`:focus-visible` on the input).
