<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useMedia } from '@/composables/useMedia'
import DecisionDetail from '@/features/decisions/DecisionDetail.vue'
import DecisionList from '@/features/decisions/DecisionList.vue'
import type { PendingDecision } from '@/features/decisions/inbox'
import { joinParam } from '@/router'
import { useDecisionsStore } from '@/stores/decisions'

/** The decisions inbox and the open decision: side by side when wide, with the most urgent one open and the
 * list scrolling on its own; one at a time on a phone. */
const route = useRoute()
const router = useRouter()
const store = useDecisionsStore()
const wide = useMedia('(min-width: 1024px)')
const requestId = computed(() => (route.name === 'decision' ? joinParam(route.params.request as string | string[]) : null))
/** A decision answered here stays on screen with the API's outcome after the inbox no longer lists it. */
const held = shallowRef<PendingDecision | null>(null)
const open = computed(() => {
  if (!requestId.value) return null
  return store.find(requestId.value) ?? (held.value?.requestId === requestId.value ? held.value : null)
})
function settled() {
  held.value = open.value
  void store.refresh()
}
const showList = computed(() => wide.value || !requestId.value)
const showDetail = computed(() => wide.value || !!requestId.value)
/** A decision opened by its address that this member cannot see: not pending, or outside their scope. */
const missing = computed(() =>
  requestId.value && (store.state === 'ready' || store.state === 'empty') && !open.value
    ? new ApiRefusal(404, 'missing_evidence:not_pending_or_out_of_scope', 'missing_evidence')
    : null,
)
/** Wide, with nothing picked: open the most urgent decision rather than an empty pane. */
watch(
  [wide, requestId, () => store.state, () => store.pending[0]?.requestId],
  ([isWide, picked, state, first]) => {
    if (isWide && !picked && state === 'ready' && first)
      void router.replace({ name: 'decision', params: { request: first.split('/') } })
  },
  { immediate: true },
)
onMounted(() => void store.refresh())
</script>

<template>
  <section class="screen screen-decisions" :class="{ 'is-detail': !!requestId }">
    <ScreenHeader
      :title="!wide && requestId ? 'Decision' : 'Decisions'"
      :back="!wide && requestId ? { to: { name: 'decisions' }, label: 'Decisions' } : undefined"
    >
      <template #aside>
        <VButton label="Refresh" variant="quiet" size="small" :pending="store.state === 'loading'" pending-label="Refreshing" @click="store.refresh()" />
      </template>
      <p v-if="showList && store.pending.length" class="screen-meta-text">
        {{ store.waiting }} waiting on you, most urgent first<span v-if="store.freshness && store.freshness !== 'live'"> (as last read, {{ store.freshness }})</span>
      </p>
    </ScreenHeader>
    <div class="decisions-layout">
      <div v-if="showList" class="decisions-list">
        <StatePanel
          :state="store.state"
          :refusal="store.refusal"
          empty-title="Nothing is waiting on you"
          empty-body="When the factory needs your decision it appears here and in Telegram. Answer in either; it settles once."
          loading-label="Loading decisions"
          @retry="store.refresh()"
        >
          <DecisionList :decisions="store.pending" :current="requestId" :now="store.now" />
        </StatePanel>
      </div>
      <div v-if="showDetail && (open || missing)" class="decisions-detail">
        <DecisionDetail v-if="open" :key="open.requestId" :decision="open" @settled="settled" />
        <RefusalNotice v-else-if="missing" :refusal="missing" />
      </div>
    </div>
  </section>
</template>
