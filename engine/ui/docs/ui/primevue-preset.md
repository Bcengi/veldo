# PrimeVue preset

PrimeVue runs unstyled (`app.use(PrimeVue, { unstyled: true, pt: veldoPreset, theme: 'none' })`).
`src/ui/preset.ts` gives each part a Veldo class, styled in `styles/components.css`:

| Component | Parts and classes |
|---|---|
| Button | `root` `vbtn vbtn-<variant>`, `label` `vbtn-label`, `loadingIcon` `vbtn-spinner` |
| InputText | `root` `vfield` |
| Textarea | `root` `vfield vfield-area` |
| RadioButton | `root` `vradio`, `input` `vradio-input`, `box` `vradio-box`, `icon` `vradio-dot` |
| ToggleSwitch | `root` `vswitch`, `input` `vswitch-input`, `slider` `vswitch-slider`, `handle` `vswitch-handle` |

PrimeVue still writes a small base sheet through its `useStyle`; the build replaces that module with
`src/ui/primevue-use-style.ts`, which writes it through the CSS object model, so the API's policy is
never asked to allow inline style. To use another PrimeVue component: add its parts here and its
styles, and check the e2e policy-violation assertion stays empty.
