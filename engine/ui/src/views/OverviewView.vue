<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import AndonBoard from '@/features/overview/AndonBoard.vue'
import { factoryCounts } from '@/features/overview/overview'
import DecisionList from '@/features/decisions/DecisionList.vue'
import { dueText } from '@/features/decisions/inbox'
import RunList from '@/features/run/RunList.vue'
import { useDecisionsStore } from '@/stores/decisions'
import { useRunsStore } from '@/stores/runs'
import { useSessionStore } from '@/stores/session'

/** The factory at a glance: the andon board (running, blocked, failed, waiting on you), the hosts, the
 * decision that has waited longest, and the runs and the inbox as the two main panels. */
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
const liveRuns = computed(() => runs.rows.slice(0, 6))
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
        <VButton label="Refresh" variant="quiet" size="small" :pending="loading" pending-label="Refreshing" @click="refresh" />
      </template>
    </ScreenHeader>

    <StatePanel v-if="refused" state="error" :refusal="runs.refusal" @retry="refresh" />
    <template v-else>
    <StatePanel :state="runs.state === 'empty' || runs.state === 'error' ? 'ready' : runs.state" shape="board" loading-label="Loading the factory">
      <AndonBoard :counts="counts" />
    </StatePanel>

    <div class="overview-lead">
      <section v-if="oldest" class="oldest" aria-labelledby="oldest-title" data-testid="oldest">
        <h2 id="oldest-title" class="oldest-title">Waited longest</h2>
        <p class="oldest-question">{{ oldest.presentation?.question || oldest.brief }}</p>
        <p class="oldest-facts">
          <span v-if="waited">{{ waited }}</span>
          <span v-if="dueText(oldest.deadline, decisions.now)">{{ dueText(oldest.deadline, decisions.now) }}</span>
        </p>
        <RouterLink :to="{ name: 'decision', params: { request: oldest.requestId.split('/') } }" class="vbtn vbtn-primary oldest-open">
          Answer it
        </RouterLink>
      </section>
      <section v-if="counts?.hosts.length" class="hosts" aria-labelledby="hosts-title" data-testid="hosts">
        <h2 id="hosts-title" class="oldest-title">Hosts</h2>
        <ul class="hosts-list">
          <li v-for="host in counts.hosts" :key="host.name" class="host">
            <Lamp :state="host.running ? 'live' : 'off'" :label="host.running ? 'Running' : 'Idle'" size="sm" />
            <span class="host-name">{{ host.name }}</span>
            <span class="host-load">{{ host.running ? `${host.running} running` : 'idle' }}, {{ host.runs }} {{ host.runs === 1 ? 'run' : 'runs' }}</span>
          </li>
        </ul>
      </section>
    </div>

    <div class="overview-panels">
      <section class="panel panel-decisions" aria-labelledby="ov-decisions">
        <header class="panel-head">
          <h2 id="ov-decisions" class="panel-title">Waiting on you <span v-if="decisions.pending.length" class="panel-count">{{ decisions.pending.length }}</span></h2>
          <RouterLink :to="{ name: 'decisions' }" class="panel-link">All decisions</RouterLink>
        </header>
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
      </section>
      <section class="panel panel-runs" aria-labelledby="ov-runs">
        <header class="panel-head">
          <h2 id="ov-runs" class="panel-title">Runs <span v-if="runs.rows.length" class="panel-count">{{ runs.rows.length }}</span></h2>
          <RouterLink :to="{ name: 'runs' }" class="panel-link">All runs</RouterLink>
        </header>
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
      </section>
    </div>
    </template>
  </section>
</template>
