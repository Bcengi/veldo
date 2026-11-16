<script setup lang="ts">
import { computed, onMounted } from 'vue'
import UCard from '@nuxt/ui/components/Card.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import RunList from '@/features/run/RunList.vue'
import { LIVE_STATES, runsSummary } from '@/features/run/runs'
import { useRunsStore } from '@/stores/runs'

const runs = useRunsStore()
/** Active runs come first, then the ones that have stopped (done, failed, refused or blocked). */
const groups = computed(() => {
  const live = runs.rows.filter((r) => LIVE_STATES.has(r.state))
  const done = runs.rows.filter((r) => !LIVE_STATES.has(r.state))
  return [
    { id: 'live', title: 'Active', rows: live },
    { id: 'done', title: 'Stopped', rows: done },
  ].filter((g) => g.rows.length > 0)
})
/** The header's summary, from the rows on screen. */
const summary = computed(() => runsSummary(runs.rows))
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`
onMounted(() => void runs.refresh())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Runs">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="runs.state === 'loading'" pending-label="Refreshing" @click="runs.refresh()" />
      </template>
      <ul v-if="runs.state === 'ready'" class="runs-summary" data-testid="runs-summary" aria-label="These runs">
        <li><strong>{{ summary.runs }}</strong> {{ summary.runs === 1 ? 'run' : 'runs' }}</li>
        <li><strong>{{ summary.projects }}</strong> {{ summary.projects === 1 ? 'project' : 'projects' }}</li>
        <li><strong>{{ summary.hosts }}</strong> {{ summary.hosts === 1 ? 'host' : 'hosts' }}</li>
      </ul>
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
        <UCard v-for="group in groups" :key="group.id" as="section" :aria-labelledby="`runs-${group.id}`">
          <template #header>
            <h2 :id="`runs-${group.id}`" class="panel-title">{{ group.title }} <span class="panel-count">{{ plural(group.rows.length, 'run', 'runs') }}</span></h2>
          </template>
          <RunList :runs="group.rows" />
        </UCard>
      </div>
    </StatePanel>
  </section>
</template>
