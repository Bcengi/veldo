<script setup lang="ts">
import { useDesktop } from '@/composables/useMedia'
import { bytesText, hostNote, ownerText, removedSpace, words, type RemovedItem } from './space'

/** Removed (design 10): the removal history, newest first: what, whose, which event, how much, and the pool's
 * free space before and after; for an engine pool the host figure apart. For a worktree and a private
 * repository, how many refs were kept and whether a snapshot was saved. Nothing here has an action. */
const props = defineProps<{ removed: RemovedItem[] }>()
const desktop = useDesktop()
const when = (seconds: number | null) =>
  typeof seconds === 'number' ? new Date(seconds * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'time not recorded'
const kept = (item: RemovedItem) => {
  if (!item.kept_refs && !item.snapshots) return null
  const refs = `${item.kept_refs} ${item.kept_refs === 1 ? 'ref' : 'refs'} kept`
  return item.snapshots ? `${refs}, ${item.snapshots} ${item.snapshots === 1 ? 'snapshot' : 'snapshots'} saved` : `${refs}, no snapshot`
}
const size = (item: RemovedItem) => (item.bytes === null ? 'not measured' : bytesText(item.bytes))
</script>

<template>
  <section class="panel" aria-labelledby="space-removed-title" data-testid="space-removed">
    <h2 id="space-removed-title" class="panel-title">Removed <span class="panel-count">{{ props.removed.length }}</span></h2>
    <div class="factory-body">
      <p v-if="!props.removed.length" class="space-note" data-testid="space-removed-none">Nothing has been removed yet.</p>
      <div v-else-if="desktop" class="factory-table-wrap">
        <table class="factory-table" aria-label="Removals, newest first">
          <thead>
            <tr><th scope="col">What</th><th scope="col">Whose</th><th scope="col">Event</th><th scope="col" class="space-num">Size</th><th scope="col">Free space on its pool</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in props.removed" :key="item.id" :data-item="item.id">
              <td><span class="space-path">{{ item.locator }}</span><span class="space-detail">{{ words(item.kind) }}<template v-if="kept(item)">; {{ kept(item) }}</template></span></td>
              <td>{{ ownerText(item.owner) }}</td>
              <td data-testid="removed-event">{{ words(item.event) || 'not recorded' }}<span class="space-detail">{{ when(item.at) }}</span></td>
              <td class="space-num" data-testid="removed-size" :data-bytes="item.bytes ?? ''">{{ size(item) }}</td>
              <td data-testid="removed-free" :data-before="item.free_before ?? ''" :data-after="item.free_after ?? ''">{{ removedSpace(item) }}<span class="space-detail">{{ item.pool || 'pool not recorded' }}<template v-if="hostNote(item)">. {{ hostNote(item) }}</template></span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul v-else class="factory-list" aria-label="Removals, newest first">
        <li v-for="item in props.removed" :key="item.id" class="factory-card" :data-item="item.id">
          <div class="space-head">
            <span class="space-path">{{ item.locator }}</span>
            <span class="factory-tag">{{ words(item.kind) }}</span>
          </div>
          <dl class="factory-facts">
            <dt>Whose</dt><dd>{{ ownerText(item.owner) }}</dd>
            <dt>Event</dt><dd data-testid="removed-event">{{ words(item.event) || 'not recorded' }}, {{ when(item.at) }}</dd>
            <dt>Size</dt><dd data-testid="removed-size" :data-bytes="item.bytes ?? ''">{{ size(item) }}</dd>
            <dt>Free</dt><dd data-testid="removed-free" :data-before="item.free_before ?? ''" :data-after="item.free_after ?? ''">{{ removedSpace(item) }} on {{ item.pool || 'a pool that was not recorded' }}</dd>
            <template v-if="hostNote(item)"><dt>Host</dt><dd>{{ hostNote(item) }}</dd></template>
            <template v-if="kept(item)"><dt>Kept</dt><dd>{{ kept(item) }}</dd></template>
          </dl>
        </li>
      </ul>
    </div>
  </section>
</template>
