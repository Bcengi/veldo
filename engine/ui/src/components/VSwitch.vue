<script setup lang="ts">
/** An on and off switch: a native checkbox with the switch role, so it is checked, focusable and toggled with
 * Space like any checkbox. Name it with a wrapping `<label>` or `label`. */
const props = defineProps<{ inputId: string; label?: string }>()
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <span class="vswitch">
    <input :id="props.inputId" v-model="model" type="checkbox" role="switch" class="vswitch-input" :aria-label="props.label" />
    <span class="vswitch-slider" aria-hidden="true"><span class="vswitch-handle" /></span>
  </span>
</template>
