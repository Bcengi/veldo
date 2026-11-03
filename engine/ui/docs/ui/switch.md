# VSwitch

An on and off switch: a native checkbox with `role="switch"`, laid over a 36 by 22 px track, so it is
focusable, toggled with Space and read as a switch. On is the inverted accent track (near-black on light, near-white on dark) with a contrasting handle.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `v-model` | boolean | On or off |
| `inputId` | string | The input's id (`#follow`, `#raw`, `#theme-switch`) |
| `label` | string, optional | The accessible name when no `label for` names it |

## Example

```vue
<label class="terminal-switch">
  <VSwitch v-model="following" input-id="follow" label="Follow the latest line" />
  <span aria-hidden="true">Follow</span>
</label>
```

The wrapping label makes the word a 44 px target too.
