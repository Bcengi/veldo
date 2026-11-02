<script setup lang="ts">
import Lamp from './Lamp.vue'

/** The Veldo wordmark: the name in the interface face, semibold, beside a lit "here" lamp. */
const props = withDefaults(defineProps<{ size?: 'md' | 'lg' }>(), { size: 'md' })
</script>

<template>
  <span class="wordmark" :class="`wordmark-${props.size}`">
    <Lamp state="here" label="" size="sm" class="wordmark-lamp" aria-hidden="true" />
    <span>Veldo</span>
  </span>
</template>
