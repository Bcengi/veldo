<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { readWorkers } from '@/api/reads'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useLiveRead } from '@/composables/useLiveRead'
import { gapSentence } from '@/features/contract/gaps'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { useContract } from '@/features/factory/useContract'
import { familiesOf, machinesOf, type WorkerCard } from '@/features/workers/workers'
import '@/styles/factory.css'

/** Workers per machine (VELDO-0131): the machines the API's workers read derives from the recorded dispatches,
 * grouped Linux and Mac, each with its worker runs. Stop is confirmed inline; the result is the API's, and while
 * the API carries no stop action the result names that gap. */
const live = useLiveRead(readWorkers, (a) => a.watermark, (a) => (a.items.dispatch ?? []).length === 0)
const { action } = useContract()
const stop = computed(() => action('worker_stop'))
const families = computed(() => familiesOf(machinesOf(live.data.value)))
const gaps = computed(() => ((live.data.value as unknown as { gaps?: { subject: string; spec: string | null; what: string }[] })?.gaps ?? []))
const confirming = ref<string | null>(null)
const result = ref<Record<string, string>>({})

async function ask(worker: WorkerCard) {
  confirming.value = worker.dispatch
  await nextTick()
  document.querySelector<HTMLElement>(`[data-confirm="${CSS.escape(worker.dispatch)}"] button`)?.focus()
}
function confirmStop(worker: WorkerCard) {
  confirming.value = null
  result.value = { ...result.value, [worker.dispatch]: stop.value.route ? '' : `Not stopped. ${gapSentence(stop.value)}` }
}
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Workers">
      <template #aside>
        <VButton label="Refresh" variant="quiet" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No worker has run yet"
      empty-body="Machines appear here once the factory dispatches a unit to a worker on them."
      loading-label="Loading workers"
      @retry="live.refresh()"
    >
      <div class="factory-grid" data-testid="workers">
        <p v-for="gap in gaps" :key="gap.subject" class="factory-gap" data-testid="workers-gap">
          {{ gap.subject }}: {{ gap.what }}<template v-if="gap.spec"> ({{ gap.spec }})</template>
        </p>
        <section v-for="family in families" :key="family.family" class="factory-grid" :aria-labelledby="`family-${family.family}`">
          <h2 :id="`family-${family.family}`" class="panel-title">{{ family.family }} <span class="panel-count">{{ family.machines.length }}</span></h2>
          <section v-for="machine in family.machines" :key="machine.host" class="panel" :aria-labelledby="`host-${machine.host}`" :data-host="machine.host">
            <h3 :id="`host-${machine.host}`" class="panel-title">
              {{ machine.host }}
              <span class="factory-tag">{{ machine.family }}</span>
              <span class="panel-count">{{ machine.running }} running of {{ machine.workers.length }}</span>
            </h3>
            <ul class="factory-body factory-list">
              <li v-for="worker in machine.workers" :key="worker.dispatch" class="factory-card" :data-dispatch="worker.dispatch" :data-state="worker.state">
                <div class="factory-actions">
                  <Lamp :state="worker.running ? 'live' : 'off'" :label="worker.running ? 'Running' : worker.state" size="sm" />
                  <RouterLink :to="{ name: 'run', params: { dispatch: worker.dispatch.split('/') } }" class="factory-card-title">{{ worker.unit }}</RouterLink>
                  <span class="factory-tag" :class="{ 'is-done': !worker.running }">{{ worker.running ? 'Running' : worker.state }}</span>
                </div>
                <dl class="factory-facts">
                  <dt>Host</dt><dd>{{ machine.host }} ({{ machine.family }})</dd>
                  <dt>Station</dt><dd>{{ worker.station || 'not recorded' }}</dd>
                  <dt>Project</dt><dd>{{ worker.project || 'not recorded' }}</dd>
                  <dt>Account</dt><dd>{{ worker.account || 'not recorded' }}</dd>
                  <dt>Process</dt><dd>{{ worker.pid ?? 'not recorded' }}</dd>
                  <dt>Record</dt><dd>{{ worker.recordLines == null ? (worker.running ? 'being written' : 'not committed') : `${worker.recordLines} lines` }}</dd>
                </dl>
                <div v-if="worker.running" class="factory-actions">
                  <VButton v-if="confirming !== worker.dispatch" label="Stop" variant="danger" size="small" :aria-label="`Stop ${worker.unit} on ${machine.host}`" data-testid="worker-stop" @click="ask(worker)" />
                  <div v-else class="factory-actions" :data-confirm="worker.dispatch" role="group" :aria-label="`Confirm stopping ${worker.unit}`">
                    <span>Stop {{ worker.unit }} on {{ machine.host }}?</span>
                    <VButton label="Stop the worker" variant="danger" size="small" data-testid="worker-stop-confirm" @click="confirmStop(worker)" />
                    <VButton label="Keep it running" variant="secondary" size="small" @click="confirming = null" />
                  </div>
                </div>
                <p v-if="result[worker.dispatch]" class="factory-gap" role="alert" data-testid="worker-stop-result">{{ result[worker.dispatch] }}</p>
              </li>
            </ul>
          </section>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
