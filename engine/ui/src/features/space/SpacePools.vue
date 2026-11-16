<script setup lang="ts">
import { bytesText, holdNumbers, scopeLabel, type SpaceHold, type SpacePool } from './space'

/** The pools (design 10): one card per pool with its floor and what is held on it, and under it the runs that
 * wait for space and, in report mode, the runs that would have waited, each with need, free, held and floor as
 * the ledger recorded them when the run was judged. */
const props = defineProps<{ pools: SpacePool[] }>()
const typeWords = (pool: SpacePool) =>
  pool.type === 'engine_image'
    ? `Engine image${pool.engine ? ` of ${pool.engine}` : ''}${pool.backing ? `, kept on ${pool.backing}` : ''}`
    : pool.type === 'filesystem'
      ? 'Filesystem'
      : 'Not recorded'
const lists = (pool: SpacePool): { id: string; title: string; none: string; holds: SpaceHold[] }[] => [
  { id: 'waiting', title: 'Waiting for space', none: 'No run waits for space here.', holds: pool.waiting },
  { id: 'advised', title: 'Would have waited (report mode)', none: 'No run was started on advice here.', holds: pool.advised },
]
</script>

<template>
  <section class="panel" aria-labelledby="space-pools-title" data-testid="space-pools">
    <h2 id="space-pools-title" class="panel-title">Pools <span class="panel-count">{{ props.pools.length }}</span></h2>
    <div class="factory-body">
      <p v-if="!props.pools.length" class="space-note" data-testid="space-pools-none">No pool is recorded yet. Pools appear after the first reconcile.</p>
      <ul class="factory-list">
        <li v-for="pool in props.pools" :key="pool.id" class="factory-card" :data-pool="pool.name">
          <div class="space-head">
            <span class="factory-card-title">{{ pool.name }}</span>
            <span v-if="pool.waiting.length" class="factory-tag is-waiting">{{ pool.waiting.length }} waiting</span>
          </div>
          <dl class="factory-facts">
            <dt>Floor</dt><dd data-testid="pool-floor">{{ bytesText(pool.floor) }} must stay free</dd>
            <dt>Held</dt><dd data-testid="pool-held">{{ bytesText(pool.held) }} promised to runs</dd>
            <dt>Type</dt><dd>{{ typeWords(pool) }}</dd>
            <dt>Host</dt><dd>{{ pool.host || 'not recorded' }}</dd>
            <template v-if="pool.returns_space === false">
              <dt>Note</dt><dd>A removal here does not grow the host's free space.</dd>
            </template>
          </dl>
          <section v-for="list in lists(pool)" :key="list.id" class="factory-list" :aria-label="`${list.title} on ${pool.name}`" :data-holds="list.id">
            <h3 class="space-sub">{{ list.title }} <span class="panel-count">{{ list.holds.length }}</span></h3>
            <p v-if="!list.holds.length" class="space-note">{{ list.none }}</p>
            <ul v-else class="factory-list">
              <li v-for="hold in list.holds" :key="hold.id" class="factory-card" :data-hold="hold.id" :data-state="hold.state">
                <div class="space-head">
                  <RouterLink v-if="hold.run" :to="{ name: 'run', params: { dispatch: hold.run.dispatch.split('/') } }" class="factory-card-title">
                    {{ hold.run.unit || 'Run' }}<template v-if="hold.run.station"> ({{ hold.run.station }})</template>
                  </RouterLink>
                  <span v-else class="factory-card-title">A run of {{ scopeLabel(hold.scope) }}, not dispatched yet</span>
                  <span class="factory-tag" :class="hold.state === 'waiting' ? 'is-waiting' : ''">{{ hold.state === 'waiting' ? 'Waiting' : 'Started on advice' }}</span>
                </div>
                <dl class="space-numbers" data-testid="hold-numbers">
                  <div v-for="n in holdNumbers(hold)" :key="n.label" :data-number="n.label.toLowerCase()"><dt>{{ n.label }}</dt><dd>{{ n.value }}</dd></div>
                </dl>
                <p class="space-note">{{ scopeLabel(hold.scope) }}<template v-if="hold.source">; the need is {{ hold.source }}</template></p>
              </li>
            </ul>
          </section>
        </li>
      </ul>
    </div>
  </section>
</template>
