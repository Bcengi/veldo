<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import UButton from '@nuxt/ui/components/Button.vue'
import { useRail } from '@/app/rail'

/** A screen's slim top bar (VELDO-0229, Telegram 38255): on desktop the panel toggle that expands or collapses the
 * sidebar, the back link where there is one, the title and the screen's actions at the right, over a bottom
 * border; the screen's summary follows below it. The title takes focus when the screen opens, so a screen reader
 * announces the new screen. */
const props = defineProps<{ title: string; back?: { to: RouteLocationRaw; label: string } }>()
const heading = ref<HTMLElement | null>(null)
const rail = useRail()
onMounted(() => heading.value?.focus({ preventScroll: true }))
</script>

<template>
  <header class="screen-header">
    <div class="screen-bar">
      <span class="screen-rail-toggle">
        <UButton
          icon="i-lucide-panel-left"
          color="neutral"
          variant="ghost"
          :aria-label="rail.expanded.value ? 'Collapse sidebar' : 'Expand sidebar'"
          :aria-expanded="rail.expanded.value ? 'true' : 'false'"
          aria-controls="rail"
          data-testid="rail-toggle"
          @click="rail.toggle()"
        />
      </span>
      <RouterLink v-if="props.back" :to="props.back.to" class="screen-back">
        <svg viewBox="0 0 20 20" aria-hidden="true" width="20" height="20"><path d="M12.5 4.5 7 10l5.5 5.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
        <span>{{ props.back.label }}</span>
      </RouterLink>
      <h1 ref="heading" tabindex="-1" class="screen-title">{{ props.title }}</h1>
      <div v-if="$slots.aside" class="screen-aside"><slot name="aside" /></div>
    </div>
    <div v-if="$slots.default" class="screen-meta"><slot /></div>
  </header>
</template>
