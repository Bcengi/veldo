<script setup lang="ts">
import { onMounted } from 'vue'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { runLamp } from '@/features/run/lamps'
import { useRunsStore } from '@/stores/runs'

const runs = useRunsStore()
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
      <ul class="runs" data-testid="runs">
        <li v-for="run in runs.rows" :key="run.dispatch">
          <RouterLink :to="{ name: 'run', params: { dispatch: run.dispatch.split('/') } }" class="run-row" :data-dispatch="run.dispatch">
            <Lamp :state="runLamp(run.state).lamp" :label="runLamp(run.state).word" />
            <span class="run-unit">{{ run.unit }}</span>
            <span class="run-state">{{ runLamp(run.state).word }}</span>
            <span class="run-facts">
              <span v-if="run.station">{{ run.station }}</span>
              <span v-if="run.project">{{ run.project }}</span>
              <span v-if="run.host">{{ run.host }}</span>
            </span>
          </RouterLink>
        </li>
      </ul>
    </StatePanel>
  </section>
</template>
