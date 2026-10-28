<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import ScreenHeader from '@/components/ScreenHeader.vue'
import RunTerminal from '@/features/run/RunTerminal.vue'
import StationStrip from '@/features/run/StationStrip.vue'
import { joinParam } from '@/router'
import { useRunsStore } from '@/stores/runs'

/** One run: where its unit is on the line, and its execution record as a live terminal. */
const route = useRoute()
const runs = useRunsStore()
const dispatch = computed(() => joinParam(route.params.dispatch as string | string[]))
const row = computed(() => runs.find(dispatch.value))
const run = computed(() => ({ unit: row.value?.unit ?? dispatch.value.split('/')[1] ?? dispatch.value }))
onMounted(() => {
  if (runs.state === 'idle') void runs.refresh()
})
</script>

<template>
  <section class="screen screen-run">
    <ScreenHeader :title="run.unit" :back="{ to: { name: 'runs' }, label: 'Runs' }">
      <p class="screen-meta-text"><code class="break" data-testid="dispatch-id">{{ dispatch }}</code></p>
    </ScreenHeader>
    <RunTerminal :dispatch="dispatch" :unit-state="row?.unitState ?? (row ? runs.units.get(row.unit) ?? null : null)">
      <template #strip="{ run: recordRun, live }">
        <StationStrip :unit-state="row?.unitState ?? (recordRun?.unit ? runs.units.get(recordRun.unit) ?? null : null)" :station="recordRun?.station ?? row?.station ?? null" :live="live" />
      </template>
    </RunTerminal>
  </section>
</template>
