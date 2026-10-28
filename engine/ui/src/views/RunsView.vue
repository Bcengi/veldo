<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { runLamp } from '@/features/run/lamps'
import LineLamps from '@/features/run/LineLamps.vue'
import { LIVE_STATES } from '@/features/run/runs'
import { useRunsStore } from '@/stores/runs'

const runs = useRunsStore()
/** Runs that are still going come first, then the ones that have ended. */
const groups = computed(() => {
  const live = runs.rows.filter((r) => LIVE_STATES.has(r.state))
  const done = runs.rows.filter((r) => !LIVE_STATES.has(r.state))
  return [
    { id: 'live', title: 'Running now', rows: live },
    { id: 'done', title: 'Ended', rows: done },
  ].filter((g) => g.rows.length > 0)
})
onMounted(() => void runs.refresh())
</script>

<template>
  <section class="screen">
    <ScreenHeader title="Runs">
      <template #aside>
        <VButton label="Refresh" variant="quiet" size="small" :pending="runs.state === 'loading'" pending-label="Refreshing" @click="runs.refresh()" />
      </template>
      <p v-if="runs.watermark" class="screen-meta-text">Read at journal record {{ runs.watermark.seq }}</p>
    </ScreenHeader>
    <StatePanel
      :state="runs.state"
      :refusal="runs.refusal"
      empty-title="No worker has run yet"
      empty-body="Runs appear here as soon as the factory dispatches a unit to a worker."
      loading-label="Loading runs"
    >
      <div class="runs-groups" data-testid="runs">
        <section v-for="group in groups" :key="group.id" class="runs-group" :aria-labelledby="`runs-${group.id}`">
          <h2 :id="`runs-${group.id}`" class="runs-group-title">{{ group.title }} <span class="runs-count">{{ group.rows.length }}</span></h2>
          <ul class="runs">
            <li v-for="run in group.rows" :key="run.dispatch">
              <RouterLink :to="{ name: 'run', params: { dispatch: run.dispatch.split('/') } }" class="run-row" :data-dispatch="run.dispatch">
                <Lamp :state="runLamp(run.state).lamp" :label="runLamp(run.state).word" />
                <span class="run-unit">{{ run.unit }}</span>
                <LineLamps class="run-line" :unit-state="run.unitState" :live="run.state === 'running'" />
                <span class="run-facts">
                  <span v-if="run.station">{{ run.station }} station</span>
                  <span v-if="run.project">{{ run.project }}</span>
                  <span v-if="run.host">{{ run.host }}</span>
                </span>
                <span class="run-state">{{ runLamp(run.state).word }}</span>
              </RouterLink>
            </li>
          </ul>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
