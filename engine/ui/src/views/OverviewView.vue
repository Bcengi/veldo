<script setup lang="ts">
import { computed, onMounted } from 'vue'
import UBadge from '@nuxt/ui/components/Badge.vue'
import UButton from '@nuxt/ui/components/Button.vue'
import UCard from '@nuxt/ui/components/Card.vue'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import AndonBoard from '@/features/overview/AndonBoard.vue'
import { factoryCounts } from '@/features/overview/overview'
import DecisionList from '@/features/decisions/DecisionList.vue'
import { dueText, urgencyOf } from '@/features/decisions/inbox'
import RunList from '@/features/run/RunList.vue'
import { LIVE_STATES } from '@/features/run/runs'
import { useDecisionsStore } from '@/stores/decisions'
import { useRunsStore } from '@/stores/runs'
import { useSessionStore } from '@/stores/session'

/** The factory at a glance: the four signals in one summary panel (running, blocked, failed, waiting on you);
 * beneath it the decision that has waited longest and the host roster; then the ranked inbox and the current
 * worker runs as the two main panels. */
const session = useSessionStore()
const runs = useRunsStore()
const decisions = useDecisionsStore()
const loading = computed(() => runs.state === 'loading' || runs.state === 'idle' || decisions.state === 'loading' || decisions.state === 'idle')
const counts = computed(() =>
  runs.state === 'ready' || runs.state === 'empty' ? factoryCounts(runs.rows, runs.unitList, decisions.waiting) : null,
)
const oldest = computed(() => decisions.oldest)
/** Both reads refused (for example a member with no project here): one refusal for the screen, not three. */
const refused = computed(() => runs.state === 'error' && decisions.state === 'error')
const waited = computed(() => {
  const at = oldest.value?.presentation?.publishedAt
  if (!at) return null
  const hours = Math.max(0, (decisions.now / 1000 - at) / 3600)
  return hours >= 48 ? `waiting ${Math.round(hours / 24)} d` : hours >= 1 ? `waiting ${Math.round(hours)} h` : 'waiting under an hour'
})
const oldestDue = computed(() => (oldest.value ? dueText(oldest.value.deadline, decisions.now) : null))
const oldestUrgent = computed(() => {
  const u = oldest.value ? urgencyOf(oldest.value.deadline, decisions.now) : 'none'
  return u === 'overdue' || u === 'today'
})
/** The current worker runs: the ones still going first, as the runs store orders them. */
const liveRuns = computed(() => runs.rows.slice(0, 6))
const going = computed(() => runs.rows.filter((r) => LIVE_STATES.has(r.state)).length)
const topDecisions = computed(() => decisions.pending.slice(0, 5))
function refresh() {
  void runs.refresh()
  void decisions.refresh()
}
onMounted(refresh)
</script>

<template>
  <section class="screen screen-wide screen-overview">
    <ScreenHeader :title="session.domain ?? 'Your factory'">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="loading" pending-label="Refreshing" @click="refresh" />
      </template>
      <p class="screen-meta-text">The factory now: its runs, its hosts and the decisions waiting on you.</p>
    </ScreenHeader>

    <StatePanel v-if="refused" state="error" :refusal="runs.refusal" @retry="refresh" />
    <template v-else>
    <StatePanel :state="runs.state === 'empty' || runs.state === 'error' ? 'ready' : runs.state" shape="board" loading-label="Loading the factory">
      <AndonBoard :counts="counts" />
    </StatePanel>

    <div class="overview-lead">
      <UCard v-if="oldest" as="section" class="oldest" aria-labelledby="oldest-title" data-testid="oldest" :ui="{ body: 'p-5 sm:p-6' }">
        <h2 id="oldest-title" class="eyebrow">Waited longest</h2>
        <p class="oldest-question">{{ oldest.presentation?.question || oldest.brief }}</p>
        <p class="oldest-facts">
          <UBadge v-if="waited" color="warning" variant="subtle" :label="waited" class="status-badge" />
          <UBadge v-if="oldestDue" :color="oldestUrgent ? 'error' : 'neutral'" variant="subtle" :label="oldestDue" class="status-badge" />
        </p>
        <UButton
          :to="{ name: 'decision', params: { request: oldest.requestId.split('/') } }"
          label="Answer it"
          trailing-icon="i-lucide-arrow-right"
          color="primary"
          size="lg"
          class="vbtn vbtn-primary oldest-open font-medium text-(color:--accent-ink) hover:bg-(color:--accent-hover) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(color:--focus)"
        />
      </UCard>
      <UCard v-if="counts?.hosts.length" as="section" class="hosts" aria-labelledby="hosts-title" data-testid="hosts">
        <template #header>
          <h2 id="hosts-title" class="panel-title">Hosts <span class="panel-count">{{ counts.hosts.length }}</span></h2>
        </template>
        <ul class="hosts-list">
          <li v-for="host in counts.hosts" :key="host.name" class="host">
            <Lamp :state="host.running ? 'live' : 'off'" :label="host.running ? 'Running' : 'Idle'" size="sm" />
            <span class="host-name">{{ host.name }}</span>
            <span class="host-load">{{ host.runs }} {{ host.runs === 1 ? 'run' : 'runs' }}</span>
            <UBadge :color="host.running ? 'success' : 'neutral'" variant="subtle" :label="host.running ? `${host.running} running` : 'idle'" class="status-badge host-badge" />
          </li>
        </ul>
      </UCard>
    </div>

    <div class="overview-panels">
      <UCard as="section" class="panel-decisions" aria-labelledby="ov-decisions">
        <template #header>
          <div class="panel-head">
            <h2 id="ov-decisions" class="panel-title">Waiting on you <span v-if="decisions.pending.length" class="panel-count">{{ decisions.pending.length }}</span></h2>
            <RouterLink :to="{ name: 'decisions' }" class="panel-link">All decisions</RouterLink>
          </div>
        </template>
        <StatePanel
          :state="decisions.state"
          :refusal="decisions.refusal"
          :rows="3"
          empty-title="Nothing is waiting on you"
          empty-body="When the factory needs your decision it appears here and in Telegram."
          loading-label="Loading decisions"
          @retry="decisions.refresh()"
        >
          <DecisionList :decisions="topDecisions" :current="null" :now="decisions.now" />
        </StatePanel>
      </UCard>
      <UCard as="section" class="panel-runs" aria-labelledby="ov-runs">
        <template #header>
          <div class="panel-head">
            <h2 id="ov-runs" class="panel-title">Worker runs <span v-if="runs.rows.length" class="panel-count">{{ going }} running of {{ runs.rows.length }}</span></h2>
            <RouterLink :to="{ name: 'runs' }" class="panel-link">All runs</RouterLink>
          </div>
        </template>
        <StatePanel
          :state="runs.state"
          :refusal="runs.refusal"
          :rows="3"
          empty-title="No worker has run yet"
          empty-body="Runs appear here as soon as the factory dispatches a unit to a worker."
          loading-label="Loading runs"
          @retry="runs.refresh()"
        >
          <RunList :runs="liveRuns" />
        </StatePanel>
      </UCard>
    </div>
    </template>
  </section>
</template>
