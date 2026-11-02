<script setup lang="ts">
/** The andon lamp: the one lit element of the design. States: off, here (at a station, not running), live,
 * waiting (on a person), stop and done. */
const props = withDefaults(defineProps<{ state?: 'off' | 'here' | 'live' | 'waiting' | 'stop' | 'done'; label: string; size?: 'sm' | 'md' }>(), {
  state: 'off',
  size: 'md',
})
</script>

<template>
  <span class="lamp" :class="[`lamp-${props.state}`, `lamp-${props.size}`]" role="img" :aria-label="props.label" />
</template>
