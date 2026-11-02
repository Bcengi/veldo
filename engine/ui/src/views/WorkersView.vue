<script setup lang="ts">
import { computed, nextTick, onMounted, ref, shallowRef } from 'vue'
import { setCap, stopWorker } from '@/api/actions'
import { readSpend, readWorkers } from '@/api/reads'
import { ApiRefusal } from '@/api/refusal'
import type { ReadAnswer } from '@/api/types'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import VTextField from '@/components/VTextField.vue'
import { useLiveRead } from '@/composables/useLiveRead'
import { gapSentence } from '@/features/contract/gaps'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { useContract } from '@/features/factory/useContract'
import { CAP_MAX, CAP_MIN, capValue, capsOf, familiesOf, machinesOf, type AccountCap, type WorkerCard } from '@/features/workers/workers'
import '@/styles/factory.css'

/** Workers per machine (VELDO-0131): the machines the API's workers read derives from the recorded dispatches,
 * grouped Linux and Mac, each with its worker runs and their capability. Stop is confirmed inline and sent to
 * `workers.stop` (src/api/actions.ts); the card shows the stop request and its result only as the dispatch record
 * holds them. The accounts' run caps come from the spend read's account records, and Save cap sends `workers.cap`
 * at the version shown; a refusal is named beside the control. A machine's own cap waits on VELDO-0125's registry. */
const spend = shallowRef<ReadAnswer | null>(null)
const live = useLiveRead(
  async (signal) => {
    const workers = await readWorkers(signal)
    try {
      spend.value = await readSpend(signal)
    } catch (error) {
      if (!(error instanceof ApiRefusal) || error.error === 'unauthenticated') throw error
      spend.value = null
    }
    return workers
  },
  (a) => a.watermark,
  (a) => (a.items.dispatch ?? []).length === 0,
)
const { action } = useContract()
const stop = computed(() => action('worker_stop'))
const cap = computed(() => action('worker_cap'))
const caps = computed(() => capsOf(spend.value))
const capDraft = ref<Record<string, string>>({})
const capResult = ref<Record<string, { text: string; refusal: string | null }>>({})
const capSending = ref<string | null>(null)

function draftOf(entry: AccountCap): string {
  return capDraft.value[entry.account] ?? String(entry.concurrency ?? '')
}
async function saveCap(entry: AccountCap) {
  const value = capValue(draftOf(entry))
  if (value === null) {
    capResult.value = { ...capResult.value, [entry.account]: { text: `Not saved: a cap is a whole number from ${CAP_MIN} to ${CAP_MAX}.`, refusal: 'invalid_input:cap' } }
    return
  }
  capSending.value = entry.account
  let text: string
  let refusal: string | null = null
  try {
    const sent = await setCap(entry.account, entry.version, value, cap.value.route)
    text = sent.sent
      ? `Cap saved: ${String(sent.answer.concurrency ?? value)} concurrent runs (record version ${String(sent.answer.version ?? '')}).`
      : `Not saved: the API publishes no route ${sent.route}.`
    if (sent.sent) {
      const { [entry.account]: _done, ...rest } = capDraft.value
      capDraft.value = rest
    }
  } catch (error) {
    refusal = error instanceof ApiRefusal ? error.refusal : 'unavailable_service'
    text = error instanceof ApiRefusal ? `Not saved: ${error.refusal}` : `Not saved: ${(error as Error).message}`
  } finally {
    capSending.value = null
  }
  capResult.value = { ...capResult.value, [entry.account]: { text, refusal } }
}
const families = computed(() => familiesOf(machinesOf(live.data.value)))
const gaps = computed(() => ((live.data.value as unknown as { gaps?: { subject: string; spec: string | null; what: string }[] })?.gaps ?? []))
const confirming = ref<string | null>(null)
const result = ref<Record<string, string>>({})
const refusals = ref<Record<string, string>>({})
const sending = ref<string | null>(null)

async function ask(worker: WorkerCard) {
  confirming.value = worker.dispatch
  await nextTick()
  document.querySelector<HTMLElement>(`[data-confirm="${CSS.escape(worker.dispatch)}"] button`)?.focus()
}
async function confirmStop(worker: WorkerCard) {
  confirming.value = null
  sending.value = worker.dispatch
  const { [worker.dispatch]: _earlier, ...others } = refusals.value
  refusals.value = others
  let text: string
  try {
    const sent = await stopWorker(worker.dispatch, worker.version, stop.value.route)
    text = sent.sent
      ? `Stop requested (${String(sent.answer.outcome ?? 'accepted')}). The card shows the stop as the dispatch record holds it.`
      : `Not stopped: the API publishes no route ${sent.route}. ${gapSentence(stop.value)}`
  } catch (error) {
    text = error instanceof ApiRefusal ? `Not stopped: ${error.refusal}` : `Not stopped: ${(error as Error).message}`
    refusals.value = { ...refusals.value, [worker.dispatch]: error instanceof ApiRefusal ? error.refusal : 'unavailable_service' }
  } finally {
    sending.value = null
  }
  result.value = { ...result.value, [worker.dispatch]: text }
}
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Workers">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
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
                  <dt>Capability</dt><dd data-testid="worker-capability">{{ worker.capability || 'not recorded' }}</dd>
                  <dt>Account</dt><dd>{{ worker.account || 'not recorded' }}</dd>
                  <dt>Process</dt><dd>{{ worker.pid ?? 'not recorded' }}</dd>
                  <dt>Record</dt><dd>{{ worker.recordLines == null ? (worker.running ? 'being written' : 'not committed') : `${worker.recordLines} lines` }}</dd>
                  <template v-if="worker.stop">
                    <dt>Stop</dt>
                    <dd data-testid="worker-stop-state" :data-asked="String(worker.stop.asked)">
                      Requested by {{ worker.stop.by }};
                      {{ worker.stop.asked === null ? 'waiting for the runner to ask its receiver' : worker.stop.asked ? 'the receiver was asked to stop' : 'no receiver held this run to ask' }}
                    </dd>
                  </template>
                </dl>
                <div v-if="worker.running && !worker.stop" class="factory-actions">
                  <VButton v-if="confirming !== worker.dispatch" label="Stop" variant="danger" size="small" :pending="sending === worker.dispatch" pending-label="Stopping" :aria-label="`Stop ${worker.unit} on ${machine.host}`" data-testid="worker-stop" @click="ask(worker)" />
                  <div v-else class="factory-actions" :data-confirm="worker.dispatch" role="group" :aria-label="`Confirm stopping ${worker.unit}`">
                    <span>Stop {{ worker.unit }} on {{ machine.host }}?</span>
                    <VButton label="Stop the worker" variant="danger" size="small" data-testid="worker-stop-confirm" @click="confirmStop(worker)" />
                    <VButton label="Keep it running" variant="secondary" size="small" @click="confirming = null" />
                  </div>
                </div>
                <p v-if="result[worker.dispatch]" class="factory-gap" role="alert" data-testid="worker-stop-result" :data-refusal="refusals[worker.dispatch]">{{ result[worker.dispatch] }}</p>
              </li>
            </ul>
          </section>
        </section>
        <section class="panel" aria-labelledby="caps-title" data-testid="worker-caps">
          <h2 id="caps-title" class="panel-title">Run caps by account <span class="panel-count">{{ caps.length }}</span></h2>
          <p class="factory-gap" data-testid="workers-cap-gap">
            A machine's own cap waits on the machine registry (VELDO-0125); each account's cap is set here.
          </p>
          <ul class="factory-body factory-list">
            <li v-for="entry in caps" :key="entry.account" class="factory-card" :data-account="entry.account">
              <div class="factory-actions">
                <span class="factory-card-title">{{ entry.label || entry.account }}</span>
                <span class="factory-tag">{{ entry.provider || 'provider not recorded' }}</span>
              </div>
              <dl class="factory-facts">
                <dt>Cap</dt><dd data-testid="cap-current">{{ entry.concurrency == null ? 'not recorded' : `${entry.concurrency} concurrent runs` }}</dd>
                <dt>Record</dt><dd>version {{ entry.version }}</dd>
                <dt>Changed</dt><dd>{{ entry.history.length ? `${entry.history.length} times, last by ${entry.history[entry.history.length - 1]!.by}` : 'never' }}</dd>
              </dl>
              <div class="factory-actions">
                <label :for="`cap-${entry.account}`">New cap ({{ CAP_MIN }} to {{ CAP_MAX }})</label>
                <VTextField
                  :id="`cap-${entry.account}`"
                  :model-value="draftOf(entry)"
                  inputmode="numeric"
                  maxlength="2"
                  data-testid="cap-input"
                  @update:model-value="(value: string) => (capDraft = { ...capDraft, [entry.account]: value })"
                />
                <VButton label="Save cap" size="small" :pending="capSending === entry.account" pending-label="Saving" :aria-label="`Save the run cap of ${entry.label || entry.account}`" data-testid="cap-save" @click="saveCap(entry)" />
              </div>
              <p v-if="capResult[entry.account]" class="factory-gap" role="alert" data-testid="cap-result" :data-refusal="capResult[entry.account]!.refusal ?? undefined">{{ capResult[entry.account]!.text }}</p>
            </li>
          </ul>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
