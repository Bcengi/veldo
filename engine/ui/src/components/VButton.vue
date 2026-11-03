<script setup lang="ts">
import { computed } from 'vue'
import UButton from '@nuxt/ui/components/Button.vue'

/** Veldo's button, built on Nuxt UI's UButton (VELDO-0229). Its interface is unchanged: the label, the progressive
 * pending label that keeps the button's place and names what is happening, disabled, variant, size, block, the
 * button type, every passed attribute (data-testid, aria-*) and the click event. Pending disables the button and
 * marks it busy; Nuxt UI's own loading indicator (a bundled icon) shows while it is. */
defineOptions({ inheritAttrs: false })
const props = withDefaults(
  defineProps<{
    label: string
    /** The progressive label shown while the action runs, for example "Sending answer". */
    pendingLabel?: string
    pending?: boolean
    disabled?: boolean
    variant?: 'primary' | 'secondary' | 'danger' | 'quiet'
    size?: 'normal' | 'small'
    type?: 'button' | 'submit'
    block?: boolean
  }>(),
  { pendingLabel: undefined, pending: false, disabled: false, variant: 'primary', size: 'normal', type: 'button', block: false },
)
const emit = defineEmits<{ click: [event: MouseEvent] }>()

/** Veldo's variants on Nuxt UI's colors and variants, in the neutral look of Telegram 38255: the main action solid
 * inverted (near-black on light, near-white on dark) with a hover that keeps its contrast, the rest bordered
 * neutral, danger bordered red, quiet a plain neutral text button. The focus outline is solid instead of Nuxt UI's
 * translucent ring. */
const LOOK = {
  primary: { color: 'primary', variant: 'solid', class: 'text-(color:--accent-ink) hover:bg-(color:--accent-hover) active:bg-(color:--accent-hover)' },
  secondary: { color: 'neutral', variant: 'outline', class: '' },
  danger: { color: 'error', variant: 'outline', class: '' },
  quiet: { color: 'neutral', variant: 'ghost', class: 'text-(color:--ink) hover:bg-(color:--accent-wash) active:bg-(color:--accent-wash)' },
} as const
const look = computed(() => LOOK[props.variant])
const shown = computed(() => (props.pending ? (props.pendingLabel ?? props.label) : props.label))
</script>

<template>
  <UButton
    v-bind="$attrs"
    :type="props.type"
    :label="shown"
    :color="look.color"
    :variant="look.variant"
    :size="props.size === 'small' ? 'md' : 'lg'"
    :block="props.block"
    :loading="props.pending"
    :disabled="props.disabled"
    :aria-busy="props.pending ? 'true' : undefined"
    class="vbtn font-medium justify-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(color:--focus)"
    :class="[`vbtn-${props.variant}`, look.class, { 'vbtn-small': props.size === 'small', 'vbtn-block': props.block, 'is-pending': props.pending }]"
    :ui="{ label: 'vbtn-label' }"
    @click="(event: MouseEvent) => emit('click', event)"
  >
    <template v-if="$slots.icon" #leading><slot name="icon" /></template>
  </UButton>
</template>
