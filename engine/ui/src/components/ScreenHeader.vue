<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

/** A screen's title. It takes focus when the screen opens, so a screen reader announces the new screen. */
const props = defineProps<{ title: string; back?: { to: RouteLocationRaw; label: string } }>()
const heading = ref<HTMLElement | null>(null)
onMounted(() => heading.value?.focus({ preventScroll: true }))
</script>

<template>
  <header class="screen-header">
    <RouterLink v-if="props.back" :to="props.back.to" class="screen-back">
      <svg viewBox="0 0 20 20" aria-hidden="true" width="20" height="20"><path d="M12.5 4.5 7 10l5.5 5.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
      <span>{{ props.back.label }}</span>
    </RouterLink>
    <div class="screen-title-row">
      <h1 ref="heading" tabindex="-1" class="screen-title">{{ props.title }}</h1>
      <div v-if="$slots.aside" class="screen-aside"><slot name="aside" /></div>
    </div>
    <div v-if="$slots.default" class="screen-meta"><slot /></div>
  </header>
</template>
