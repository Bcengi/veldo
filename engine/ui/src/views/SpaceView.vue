<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { readSpacePending, readSpacePools, readSpaceRemoved, readSpaceUsage } from '@/api/reads'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useLiveRead } from '@/composables/useLiveRead'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { useContract } from '@/features/factory/useContract'
import SpacePending from '@/features/space/SpacePending.vue'
import SpacePools from '@/features/space/SpacePools.vue'
import SpaceReconcile from '@/features/space/SpaceReconcile.vue'
import SpaceRemoved from '@/features/space/SpaceRemoved.vue'
import SpaceUsage from '@/features/space/SpaceUsage.vue'
import SpaceWorktrees from '@/features/space/SpaceWorktrees.vue'
import { isEmpty, type SpaceRead } from '@/features/space/space'
import { useDecisionsStore } from '@/stores/decisions'
import '@/styles/factory.css'
import '@/features/space/space.css'

/** Space (VELDO-0319, design 10): where the space is and what Veldo is about to do with it. The four space reads
 * (pools, usage, pending, removed) are loaded, then the committed journal is followed and every record re-reads
 * them (useLiveRead): no timer reads anything. The decisions waiting on the member are read beside them, so an
 * open request links to where it is answered. Reconcile, Abandon and Sign Keep are the owner's signed commands; the screen
 * removes nothing itself and shows a change only when the ledger's record holds it. */
const decisions = useDecisionsStore()
const live = useLiveRead<SpaceRead>(
  async (signal) => {
    const pools = await readSpacePools(signal)
    const usage = await readSpaceUsage(signal)
    const pending = await readSpacePending(signal)
    const removed = await readSpaceRemoved(signal)
    // The decisions only link a request to its answer; a refused read leaves the request unlinked.
    if (pending.requests.length) await decisions.refresh()
    return { pools, usage, pending, removed }
  },
  (read) => read.pools.watermark,
  isEmpty,
)
const { action } = useContract()
const reconcile = computed(() => action('space_reconcile'))
const abandon = computed(() => action('worktree_abandon'))
const keep = computed(() => action('worktree_keep'))
const projects = computed(() =>
  (live.data.value?.usage.scopes ?? []).filter((s) => s.scope.type === 'project' && s.scope.id).map((s) => s.scope.id as string),
)
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Space">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.pools.watermark.seq ?? null" :freshness="live.data.value?.pools.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="The space ledger holds nothing yet"
      empty-body="Pools, items and removals appear here once a reconcile has read this installation."
      loading-label="Loading space"
      @retry="live.refresh()"
    >
      <template #empty>
        <SpaceReconcile :projects="[]" :action="reconcile" />
      </template>
      <div v-if="live.data.value" class="factory-grid" data-testid="space">
        <SpacePools :pools="live.data.value.pools.pools" />
        <SpaceUsage :usage="live.data.value.usage" />
        <SpacePending :pending="live.data.value.pending" :decisions="decisions.pending" :action="keep" />
        <SpaceWorktrees :worktrees="live.data.value.usage.worktrees" :action="abandon" />
        <SpaceRemoved :removed="live.data.value.removed.items" />
        <SpaceReconcile :projects="projects" :action="reconcile" />
      </div>
    </StatePanel>
  </section>
</template>
