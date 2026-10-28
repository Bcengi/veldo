import type { PrimeVuePTOptions } from 'primevue/config'

/**
 * Veldo's pass-through preset for PrimeVue in unstyled mode: every PrimeVue part gets one of Veldo's own
 * classes (styles/components.css), and PrimeVue injects no style of its own, which the API's content
 * security policy would refuse. See docs/ui/README.md.
 */
export const veldoPreset: PrimeVuePTOptions = {
  button: {
    root: ({ props }: { props: { severity?: string; text?: boolean; size?: string } }) => ({
      class: [
        'vbtn',
        props.text ? 'vbtn-quiet' : `vbtn-${props.severity ?? 'primary'}`,
        props.size === 'small' ? 'vbtn-small' : null,
      ],
    }),
    label: { class: 'vbtn-label' },
    icon: { class: 'vbtn-icon' },
    loadingIcon: { class: 'vbtn-spinner' },
  },
  inputtext: { root: { class: 'vfield' } },
  textarea: { root: { class: 'vfield vfield-area' } },
  radiobutton: {
    root: { class: 'vradio' },
    input: { class: 'vradio-input' },
    box: { class: 'vradio-box' },
    icon: { class: 'vradio-dot' },
  },
  toggleswitch: {
    root: { class: 'vswitch' },
    input: { class: 'vswitch-input' },
    slider: { class: 'vswitch-slider' },
    handle: { class: 'vswitch-handle' },
  },
} as PrimeVuePTOptions
