<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { reprioritize } from '@/api/actions'
import { readProof, readWork } from '@/api/reads'
import { ApiRefusal } from '@/api/refusal'
import type { ReadAnswer } from '@/api/types'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import { authorityOrder, backlogOf, backlogRows, moveBy, moveTo, rankChanges, type BacklogEntry } from '@/features/backlog/backlog'
import { landedUnits } from '@/features/backlog/completion'
import { gapSentence } from '@/features/contract/gaps'
import FactorySheet from '@/features/factory/FactorySheet.vue'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { useContract } from '@/features/factory/useContract'
import TreeTable from '@/features/table/TreeTable.vue'
import BacklogDetailBody from '@/features/backlog/BacklogDetail.vue'
import type { TreeRow } from '@/features/table/tree-table'
import '@/styles/factory.css'

/** The backlog (VELDO-0131): items in the authority's priority order with their blockers and the units taken from
 * them. Reorder is drag and drop on a desktop and Move up / Move down buttons everywhere (keyboard and touch);
 * Save sends one rank command per prioritized item whose rank changes to `backlog.reprioritize` (src/api/actions.ts,
 * control_backlog's own reprioritize through the API edge), each at the item version shown, in order, and stops at
 * the first refusal, which it names beside Save (a stale version among them). If the API published no priority
 * route nothing would be sent, the reordered list would stay the owner's draft and the result would name the route. */
const proof = shallowRef<ReadAnswer | null>(null)
const live = useLiveRead(
  async (signal) => {
    const work = await readWork(signal)
    try {
      proof.value = await readProof(signal)
    } catch (error) {
      if (!(error instanceof ApiRefusal) || error.error === 'unauthenticated') throw error
      proof.value = null
    }
    return work
  },
  (work) => work.watermark,
  (work) => (work.items.backlog_item ?? []).length === 0,
)
const { action } = useContract()
const priority = computed(() => action('owner_priority'))
const desktop = useDesktop()
const entries = computed<BacklogEntry[]>(() => backlogOf(live.data.value, landedUnits(proof.value)))
const draft = ref<string[] | null>(null)
const order = computed(() => {
  const base = authorityOrder(entries.value)
  if (!draft.value) return base
  const kept = draft.value.filter((id) => base.includes(id))
  return [...kept, ...base.filter((id) => !kept.includes(id))]
})
const changed = computed(() => draft.value !== null && order.value.join() !== authorityOrder(entries.value).join())
const rows = computed(() => backlogRows(entries.value, order.value))
const selected = ref<string | null>(null)
const detail = computed(() => entries.value.find((e) => e.id === selected.value) ?? null)
const announce = ref('')
const tried = ref(false)
const saving = ref(false)
const saveResult = ref('')
const saveRefusal = ref<string | null>(null)
const changes = computed(() => rankChanges(entries.value, order.value))

async function save() {
  saving.value = true
  saveResult.value = ''
  saveRefusal.value = null
  const done: string[] = []
  try {
    for (const change of changes.value) {
      const sent = await reprioritize(change.id, change.version, change.to, priority.value.route)
      if (!sent.sent) {
        saveResult.value = `Not saved: the API publishes no route ${sent.route} yet. ${gapSentence(priority.value)}`
        return
      }
      done.push(`${change.title} rank ${change.to}`)
    }
    saveResult.value = done.length
      ? `Saved: ${done.join('; ')}. The order shown follows the backlog read.`
      : 'Nothing to save: no prioritized item changes rank in this order.'
    draft.value = null
  } catch (error) {
    const named = error instanceof ApiRefusal ? error.refusal : (error as Error).message
    saveRefusal.value = error instanceof ApiRefusal ? error.refusal : 'unavailable_service'
    saveResult.value = `Not saved: ${named}${done.length ? ` (saved before it: ${done.join('; ')})` : ''}`
  } finally {
    saving.value = false
    tried.value = true
  }
}
const columns = [
  { id: 'title', header: 'Item', primary: true },
  { id: 'position', header: 'Order' },
  { id: 'rank', header: 'Priority' },
  { id: 'state', header: 'State' },
  { id: 'blockers', header: 'Blockers' },
]

function move(id: string, to: number) {
  draft.value = moveTo(order.value, id, to)
  say(id)
}
function step(id: string, delta: number) {
  draft.value = moveBy(order.value, id, delta)
  say(id)
}
function say(id: string) {
  const entry = entries.value.find((e) => e.id === id)
  announce.value = `${entry?.title ?? id} is now number ${order.value.indexOf(id) + 1} of ${order.value.length} in your order.`
  tried.value = false
  saveResult.value = ''
}
function rowKey(event: KeyboardEvent, row: TreeRow) {
  if (!event.altKey) return
  if (event.key === 'ArrowUp') step(row.id, -1)
  else if (event.key === 'ArrowDown') step(row.id, 1)
  else return
  event.preventDefault()
}
const titleOf = (row: TreeRow) => row.cells.title
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Backlog">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="The backlog is empty"
      empty-body="Items appear here once the factory takes features from an objective into the backlog."
      loading-label="Loading the backlog"
      @retry="live.refresh()"
    >
      <div class="factory-grid factory-split">
        <section class="panel" aria-labelledby="backlog-title" data-testid="backlog">
          <h2 id="backlog-title" class="panel-title">Priority order <span class="panel-count">{{ rows.length }}</span></h2>
          <div class="factory-body">
            <p class="sr-only" aria-live="polite" data-testid="backlog-announce">{{ announce }}</p>
            <p class="factory-meta">Drag a row, or use Move up and Move down (Alt+Up and Alt+Down on a focused row's button), to set your order.</p>
            <TreeTable :rows="rows" :columns="columns" label="Backlog items and their units" :reorderable="desktop" @move="move">
              <template #actions="{ row, depth, index, siblings }">
                <template v-if="depth === 0">
                  <VButton
                    label="Move up"
                    variant="secondary"
                    size="small"
                    :disabled="index === 0"
                    :aria-label="`Move ${titleOf(row)} up`"
                    data-testid="move-up"
                    @click="step(row.id, -1)"
                    @keydown="rowKey($event, row)"
                  />
                  <VButton
                    label="Move down"
                    variant="secondary"
                    size="small"
                    :disabled="index === siblings - 1"
                    :aria-label="`Move ${titleOf(row)} down`"
                    data-testid="move-down"
                    @click="step(row.id, 1)"
                    @keydown="rowKey($event, row)"
                  />
                  <VButton label="Details" variant="quiet" size="small" :aria-label="`Details of ${titleOf(row)}`" data-testid="backlog-details" @click="selected = row.id" />
                </template>
              </template>
            </TreeTable>
            <div class="factory-actions">
              <VButton label="Save priority order" :disabled="!changed" :pending="saving" pending-label="Saving" data-testid="priority-save" @click="save()" />
              <VButton v-if="changed" label="Back to the stored order" variant="secondary" @click="draft = null" />
            </div>
            <p v-if="changed && !priority.route" class="factory-gap" role="status" data-testid="priority-gap">
              Your order is a draft on this screen. {{ gapSentence(priority) }}
            </p>
            <p v-if="tried && saveResult" class="factory-gap" role="alert" data-testid="priority-gap-result" :data-refusal="saveRefusal ?? undefined">{{ saveResult }}</p>
          </div>
        </section>
        <section v-if="detail && desktop" class="panel" aria-labelledby="backlog-detail-title" data-testid="backlog-detail">
          <h2 id="backlog-detail-title" class="panel-title">{{ detail.title }}</h2>
          <div class="factory-body"><BacklogDetailBody :entry="detail" /></div>
        </section>
      </div>
      <FactorySheet v-if="detail && !desktop" id="backlog-sheet" :title="detail.title" @close="selected = null">
        <BacklogDetailBody :entry="detail" />
      </FactorySheet>
    </StatePanel>
  </section>
</template>

