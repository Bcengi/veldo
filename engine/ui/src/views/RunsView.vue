<script setup lang="ts">
import { computed, onMounted } from 'vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import RunList from '@/features/run/RunList.vue'
import { LIVE_STATES } from '@/features/run/runs'
import { useRunsStore } from '@/stores/runs'

const runs = useRunsStore()
/** Runs that are still going come first, then the ones that are done. */
const groups = computed(() => {
  const live = runs.rows.filter((r) => LIVE_STATES.has(r.state))
  const done = runs.rows.filter((r) => !LIVE_STATES.has(r.state))
  return [
    { id: 'live', title: 'Running now', rows: live },
    { id: 'done', title: 'Done', rows: done },
  ].filter((g) => g.rows.length > 0)
})
onMounted(() => void runs.refresh())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Runs">
      <template #aside>
        <VButton label="Refresh" variant="quiet" size="small" :pending="runs.state === 'loading'" pending-label="Refreshing" @click="runs.refresh()" />
      </template>
    </ScreenHeader>
    <StatePanel
      :state="runs.state"
      :refusal="runs.refusal"
      empty-title="No worker has run yet"
      empty-body="Runs appear here as soon as the factory dispatches a unit to a worker."
      loading-label="Loading runs"
      @retry="runs.refresh()"
    >
      <div class="runs-groups" data-testid="runs">
        <section v-for="group in groups" :key="group.id" class="panel" :aria-labelledby="`runs-${group.id}`">
          <h2 :id="`runs-${group.id}`" class="panel-title">{{ group.title }} <span class="panel-count">{{ group.rows.length }}</span></h2>
          <RunList :runs="group.rows" />
        </section>
      </div>
    </StatePanel>
  </section>
</template>
