<script setup lang="ts">
import Lamp from '@/components/Lamp.vue'
import { runLamp } from './lamps'
import LineLamps from './LineLamps.vue'
import type { RunRow } from './runs'

/** Worker runs as rows: the run's lamp, its unit, where the unit is on the line, and where it runs. A row
 * opens the run. Used by the runs screen and the overview. */
const props = defineProps<{ runs: RunRow[] }>()
</script>

<template>
  <ul class="runs">
    <li v-for="run in props.runs" :key="run.dispatch">
      <RouterLink :to="{ name: 'run', params: { dispatch: run.dispatch.split('/') } }" class="run-row" :data-dispatch="run.dispatch">
        <Lamp :state="runLamp(run.state).lamp" :label="runLamp(run.state).word" />
        <span class="run-main">
          <span class="run-unit">{{ run.unit }}</span>
          <span class="run-facts">
            <span v-if="run.station">{{ run.station }}</span>
            <span v-if="run.project">{{ run.project }}</span>
            <span v-if="run.host">{{ run.host }}</span>
          </span>
        </span>
        <LineLamps class="run-line" :unit-state="run.unitState" :live="run.state === 'running'" />
        <span class="run-state" :class="`is-${runLamp(run.state).lamp}`">{{ runLamp(run.state).word }}</span>
      </RouterLink>
    </li>
  </ul>
</template>
