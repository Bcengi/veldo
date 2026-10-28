<script setup lang="ts">
/** Veldo's button: a native button with a pending state that keeps its place and names what is happening. */
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
  <button
    :type="props.type"
    class="vbtn"
    :class="[`vbtn-${props.variant}`, { 'vbtn-small': props.size === 'small', 'vbtn-block': props.block, 'is-pending': props.pending }]"
    :disabled="props.disabled || props.pending"
    :aria-busy="props.pending ? 'true' : undefined"
    @click="$emit('click', $event)"
  >
    <span v-if="props.pending" class="vbtn-spinner" aria-hidden="true" />
    <slot name="icon" />
    <span class="vbtn-label">{{ props.pending ? (props.pendingLabel ?? props.label) : props.label }}</span>
  </button>
</template>
