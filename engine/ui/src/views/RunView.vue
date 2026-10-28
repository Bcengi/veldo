<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import CopyId from '@/components/CopyId.vue'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import { useNow } from '@/composables/useNow'
import { duration, runFacts } from '@/features/run/record'
import RunTerminal from '@/features/run/RunTerminal.vue'
import StationStrip from '@/features/run/StationStrip.vue'
import { useRecordFollower } from '@/features/run/useRecordFollower'
import { joinParam } from '@/router'
import { useRunsStore } from '@/stores/runs'

/** One run: its state, how long it has run, its engine, model, host and station as the headline; where its
 * unit is on the line; and its execution record as a live terminal. The dispatch id is a copyable detail. */
const route = useRoute()
const runs = useRunsStore()
const dispatch = computed(() => joinParam(route.params.dispatch as string | string[]))
const follower = useRecordFollower(() => dispatch.value)
const { record, state } = follower
const row = computed(() => runs.find(dispatch.value))
const unit = computed(() => record.run?.unit ?? row.value?.unit ?? dispatch.value.split('/')[1] ?? dispatch.value)
const facts = computed(() => runFacts(record.lines))
const now = useNow(1000)
const live = computed(() => state.value === 'live' || state.value === 'reconnecting')
const shown = computed(() => state.value !== 'error')
const status = computed(() => {
  switch (state.value) {
    case 'live':
      return { lamp: 'live' as const, word: 'Running' }
    case 'reconnecting':
      return { lamp: 'waiting' as const, word: 'Reconnecting' }
    case 'ended':
      return { lamp: 'done' as const, word: 'Done' }
    case 'stopped':
      return { lamp: 'off' as const, word: 'Not following' }
    case 'loading':
      return { lamp: 'off' as const, word: 'Loading' }
    default:
      return { lamp: 'stop' as const, word: 'Not shown' }
  }
})
const elapsed = computed(() => {
  const { startedAt, lastAt } = facts.value
  if (startedAt === null) return null
  const end = live.value ? now.value / 1000 : (lastAt ?? startedAt)
  return duration(end - startedAt)
})
const unitState = computed(() => row.value?.unitState ?? (unit.value ? (runs.units.get(unit.value) ?? null) : null))
const station = computed(() => record.run?.station ?? row.value?.station ?? null)
const host = computed(() => record.run?.host ?? row.value?.host ?? null)
const project = computed(() => record.run?.project ?? row.value?.project ?? null)
onMounted(() => {
  if (runs.state === 'idle') void runs.refresh()
})
</script>

<template>
  <section class="screen screen-run">
    <ScreenHeader :title="unit" :back="{ to: { name: 'runs' }, label: 'Runs' }">
      <template #aside>
        <p class="run-status" :class="`is-${status.lamp}`" data-testid="run-status">
          <Lamp :state="status.lamp" :label="status.word" size="sm" />
          <span>{{ status.word }}</span>
          <span v-if="elapsed && shown" class="run-elapsed" data-testid="elapsed">{{ elapsed }}</span>
        </p>
      </template>
      <div v-if="shown" class="run-head">
        <ul class="run-headline" data-testid="run-headline">
          <li v-if="facts.engine"><span class="sr-only">Engine </span>{{ facts.engine }}</li>
          <li v-if="facts.model" data-testid="run-model"><span class="sr-only">Model </span>{{ facts.model }}</li>
          <li v-if="host"><span class="run-head-word">on</span> {{ host }}</li>
          <li v-if="station" data-testid="run-station"><span class="run-head-word">at the</span> {{ station }} <span class="run-head-word">station</span></li>
          <li v-if="project" class="run-head-project">{{ project }}</li>
        </ul>
        <details class="run-details">
          <summary>Dispatch id</summary>
          <CopyId :value="dispatch" label="dispatch id" testid="dispatch-id" />
        </details>
      </div>
    </ScreenHeader>
    <RunTerminal :dispatch="dispatch" :follower="follower">
      <template #strip>
        <StationStrip :unit-state="unitState" :station="station" :live="live" />
      </template>
    </RunTerminal>
  </section>
</template>
