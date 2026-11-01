<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import UCard from '@nuxt/ui/components/Card.vue'
import Lamp from '@/components/Lamp.vue'
import type { LampState } from '@/app/navigation'
import type { FactoryCounts } from './overview'

/** The factory's four signals in one joined summary panel (Nuxt UI's UCard): running, blocked, failed and
 * waiting on you, each a large count beside its word, its lamp lit in its signal color while the count is above
 * zero. Each cell opens the screen behind its count. Only counts the API's answers support are shown. */
const props = defineProps<{ counts: FactoryCounts | null }>()

interface Cell {
  id: string
  word: string
  count: number | null
  lamp: LampState
  tone: 'live' | 'waiting' | 'stop'
  to: RouteLocationRaw
}
const cells = computed<Cell[]>(() => {
  const c = props.counts
  return [
    { id: 'running', word: 'running', count: c?.running ?? null, lamp: 'live', tone: 'live', to: { name: 'runs' } },
    { id: 'blocked', word: 'blocked', count: c?.blocked ?? null, lamp: 'waiting', tone: 'waiting', to: { name: 'runs' } },
    { id: 'failed', word: 'failed', count: c?.failed ?? null, lamp: 'stop', tone: 'stop', to: { name: 'runs' } },
    { id: 'waiting', word: 'waiting on you', count: c?.waiting ?? null, lamp: 'waiting', tone: 'waiting', to: { name: 'decisions' } },
  ]
})
</script>

<template>
  <UCard class="andon-card">
    <ul class="andon" data-testid="andon" aria-label="The factory now">
      <li v-for="cell in cells" :key="cell.id">
        <RouterLink
          :to="cell.to"
          class="andon-cell"
          :class="[`tone-${cell.tone}`, { 'is-lit': (cell.count ?? 0) > 0, 'is-unread': cell.count === null }]"
          :data-count="cell.id"
          :data-value="cell.count ?? ''"
        >
          <span class="andon-word"><Lamp :state="(cell.count ?? 0) > 0 ? cell.lamp : 'off'" label="" aria-hidden="true" size="sm" />{{ cell.word }}</span>
          <span class="andon-count">{{ cell.count ?? 'Not readable' }}</span>
        </RouterLink>
      </li>
    </ul>
  </UCard>
</template>
