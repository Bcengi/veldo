<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import Lamp from '@/components/Lamp.vue'
import type { LampState } from '@/app/navigation'
import type { FactoryCounts } from './overview'

/** The andon board: the factory's four signals in one dark strip, each cell lit in its signal color while its
 * count is above zero. The one bold element of the overview; each cell opens the screen behind its count. */
const props = defineProps<{ counts: FactoryCounts | null }>()

interface Cell {
  id: string
  word: string
  count: number | null
  lamp: LampState
  to: RouteLocationRaw
}
const cells = computed<Cell[]>(() => {
  const c = props.counts
  return [
    { id: 'running', word: 'running', count: c?.running ?? null, lamp: 'live', to: { name: 'runs' } },
    { id: 'blocked', word: 'blocked', count: c?.blocked ?? null, lamp: 'waiting', to: { name: 'runs' } },
    { id: 'failed', word: 'failed', count: c?.failed ?? null, lamp: 'stop', to: { name: 'runs' } },
    { id: 'waiting', word: 'waiting on you', count: c?.waiting ?? null, lamp: 'waiting', to: { name: 'decisions' } },
  ]
})
</script>

<template>
  <ul class="andon" data-testid="andon" aria-label="The factory now">
    <li v-for="cell in cells" :key="cell.id">
      <RouterLink
        :to="cell.to"
        class="andon-cell"
        :class="{ 'is-lit': (cell.count ?? 0) > 0, 'is-unread': cell.count === null }"
        :data-count="cell.id"
        :data-value="cell.count ?? ''"
      >
        <Lamp :state="(cell.count ?? 0) > 0 ? cell.lamp : 'off'" label="" aria-hidden="true" />
        <span class="andon-count">{{ cell.count ?? 'Not readable' }}</span>
        <span class="andon-word">{{ cell.word }}</span>
      </RouterLink>
    </li>
  </ul>
</template>
