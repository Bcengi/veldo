<script setup lang="ts">
import UBadge from '@nuxt/ui/components/Badge.vue'
import Lamp from '@/components/Lamp.vue'
import { runSignal } from './lamps'
import LineLamps from './LineLamps.vue'
import type { RunRow } from './runs'

/** Worker runs as rows: the run's lamp, its unit, its project and host, where the unit is on the line, and its
 * status as a badge with its word. A row opens the run. Used by the runs screen and the overview. */
const props = defineProps<{ runs: RunRow[] }>()
const BADGE = { live: 'success', waiting: 'warning', stop: 'error', done: 'neutral', here: 'primary', off: 'neutral' } as const
</script>

<template>
  <ul class="runs">
    <li v-for="run in props.runs" :key="run.dispatch">
      <RouterLink :to="{ name: 'run', params: { dispatch: run.dispatch.split('/') } }" class="run-row" :data-dispatch="run.dispatch">
        <Lamp :state="runSignal(run.state, run.unitState).lamp" :label="runSignal(run.state, run.unitState).word" />
        <span class="run-main">
          <span class="run-unit">{{ run.unit }}</span>
          <span class="run-facts">
            <span v-if="run.project" class="run-project">{{ run.project }}</span>
            <span v-if="run.host" class="run-host">{{ run.host }}</span>
            <span v-if="run.station" class="run-station">{{ run.station }}</span>
          </span>
        </span>
        <LineLamps class="run-line" :unit-state="run.unitState" :live="run.state === 'running'" />
        <UBadge
          class="run-state status-badge"
          :class="`is-${runSignal(run.state, run.unitState).lamp}`"
          :color="BADGE[runSignal(run.state, run.unitState).lamp]"
          variant="subtle"
          :label="runSignal(run.state, run.unitState).word"
        />
      </RouterLink>
    </li>
  </ul>
</template>
