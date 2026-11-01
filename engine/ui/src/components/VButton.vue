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

/** Veldo's variants on Nuxt UI's colors and variants. The overrides keep the owner's rules: white text on the
 * action blue in both themes, a darker (not lighter) hover so contrast holds, and a solid focus outline instead of
 * Nuxt UI's translucent one. */
const LOOK = {
  primary: { color: 'primary', variant: 'solid', class: 'text-(--cobalt-ink) hover:bg-(--cobalt-hover) active:bg-(--cobalt-hover)' },
  secondary: { color: 'neutral', variant: 'outline', class: '' },
  danger: { color: 'error', variant: 'outline', class: '' },
  quiet: { color: 'primary', variant: 'ghost', class: 'text-(--cobalt-text) hover:bg-(--cobalt-wash) active:bg-(--cobalt-wash)' },
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
    class="vbtn font-semibold justify-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--focus)"
    :class="[`vbtn-${props.variant}`, look.class, { 'vbtn-small': props.size === 'small', 'vbtn-block': props.block, 'is-pending': props.pending }]"
    :ui="{ label: 'vbtn-label' }"
    @click="(event: MouseEvent) => emit('click', event)"
  >
    <template v-if="$slots.icon" #leading><slot name="icon" /></template>
  </UButton>
</template>
