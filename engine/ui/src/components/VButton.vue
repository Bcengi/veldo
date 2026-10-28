<script setup lang="ts">
import Button from 'primevue/button'

/** Veldo's button: PrimeVue's Button styled by the preset, with a pending state that keeps its place. */
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
defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <Button
    :type="props.type"
    :label="props.pending ? (props.pendingLabel ?? props.label) : props.label"
    :loading="props.pending"
    :disabled="props.disabled || props.pending"
    :severity="props.variant === 'quiet' ? undefined : props.variant"
    :text="props.variant === 'quiet'"
    :size="props.size === 'small' ? 'small' : undefined"
    :aria-busy="props.pending ? 'true' : undefined"
    :class="{ 'vbtn-block': props.block }"
    @click="$emit('click', $event)"
  >
    <template #loadingicon><span class="vbtn-spinner" aria-hidden="true" /></template>
  </Button>
</template>
