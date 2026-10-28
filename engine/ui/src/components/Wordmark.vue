<script setup lang="ts">
import Lamp from './Lamp.vue'

/** The Veldo wordmark: the name in the display face beside a lamp in the brand's enamel. */
const props = withDefaults(defineProps<{ size?: 'md' | 'lg' }>(), { size: 'md' })
</script>

<template>
  <span class="wordmark" :class="`wordmark-${props.size}`">
    <Lamp state="done" label="" size="sm" class="wordmark-lamp" aria-hidden="true" />
    <span>Veldo</span>
  </span>
</template>
