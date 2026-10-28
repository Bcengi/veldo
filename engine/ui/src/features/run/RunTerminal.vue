<script setup lang="ts">
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import Lamp from '@/components/Lamp.vue'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import { matches } from './record'
import TerminalLine from './TerminalLine.vue'
import { useRecordFollower } from './useRecordFollower'

/**
 * A run's execution record as a live terminal: every kept line in sequence, followed live from its cursor.
 * Reusable: give it a dispatch id (the conversation screens of VELDO-0179 open it on a turn's dispatch).
 */
const props = defineProps<{ dispatch: string; unitState?: string | null }>()
const follower = useRecordFollower(() => props.dispatch)
const { record, state, refusal, stats } = follower

const body = ref<HTMLElement | null>(null)
const searchBox = ref<{ $el: HTMLInputElement } | null>(null)
const following = ref(true)
const raw = ref(false)
const query = ref('')
const at = ref(0)
const unseen = ref(0)

const hits = computed(() => (query.value.trim() ? record.lines.filter((l) => matches(l, query.value)).map((l) => l.seq) : []))
const currentHit = computed(() => hits.value[at.value] ?? null)
const live = computed(() => state.value === 'live' || state.value === 'reconnecting')
const status = computed(() => {
  switch (state.value) {
    case 'loading':
      return { lamp: 'off' as const, word: 'Loading the record' }
    case 'live':
      return { lamp: 'live' as const, word: 'Live' }
    case 'reconnecting':
      return { lamp: 'waiting' as const, word: 'Reconnecting' }
    case 'ended':
      return { lamp: 'done' as const, word: 'Ended' }
    case 'stopped':
      return { lamp: 'off' as const, word: 'Stopped following' }
    default:
      return { lamp: 'stop' as const, word: 'Not shown' }
  }
})

function scrollToEnd() {
  const el = body.value
  if (el) el.scrollTop = el.scrollHeight
  unseen.value = 0
}

function onScroll() {
  const el = body.value
  if (!el) return
  const atEnd = el.scrollHeight - el.scrollTop - el.clientHeight < 24
  if (!atEnd && following.value && state.value !== 'loading') following.value = false
  if (atEnd) unseen.value = 0
}

function jumpToLatest() {
  following.value = true
  void nextTick(scrollToEnd)
}

watch(
  () => record.lines.length,
  (now, before) => {
    if (following.value) void nextTick(scrollToEnd)
    else unseen.value += now - (before ?? 0)
  },
)
watch(following, (on) => {
  if (on) void nextTick(scrollToEnd)
})
watch(state, (s, before) => {
  // Follow is on for a running run and off for one that had already ended when it opened.
  if (s === 'ended' && before === 'loading') following.value = false
  if (s === 'ended') unseen.value = 0
})
watch(query, () => (at.value = 0))
watch(currentHit, (seq) => {
  if (seq === null) return
  following.value = false
  void nextTick(() => body.value?.querySelector(`[data-seq="${seq}"]`)?.scrollIntoView({ block: 'center' }))
})

function step(direction: 1 | -1) {
  const count = hits.value.length
  if (count) at.value = (at.value + direction + count) % count
}

function onKey(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  const typing = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'
  if (event.key === '/' && !typing) {
    event.preventDefault()
    searchBox.value?.$el?.focus()
  } else if (event.key === 'End' && !typing) {
    event.preventDefault()
    jumpToLatest()
  }
}

onMounted(() => void follower.start())
watch(() => props.dispatch, () => void follower.start())
</script>

<template>
  <div class="terminal" data-testid="terminal" :data-state="state" @keydown="onKey">
    <slot name="strip" :run="record.run" :live="live" />
    <div class="terminal-bar" role="toolbar" aria-label="Record controls">
      <p class="terminal-status" role="status" aria-live="polite" data-testid="terminal-status">
        <Lamp :state="status.lamp" :label="status.word" size="sm" />
        <span>{{ status.word }}</span>
        <span class="terminal-count" data-testid="line-count">{{ record.lines.length }} {{ record.lines.length === 1 ? 'line' : 'lines' }}</span>
        <span v-if="stats.reconnects" class="terminal-reconnects">{{ stats.reconnects }} {{ stats.reconnects === 1 ? 'reconnect' : 'reconnects' }}</span>
      </p>
      <div class="terminal-controls">
        <label class="terminal-switch">
          <ToggleSwitch v-model="following" input-id="follow" :aria-label="'Follow the latest line'" data-testid="follow" />
          <span>Follow</span>
        </label>
        <label class="terminal-switch">
          <ToggleSwitch v-model="raw" input-id="raw" aria-label="Show raw lines" data-testid="raw" />
          <span>Raw</span>
        </label>
        <div class="terminal-search">
          <label for="record-search" class="sr-only">Search the record</label>
          <InputText
            id="record-search"
            ref="searchBox"
            v-model="query"
            type="search"
            placeholder="Search the record"
            autocomplete="off"
            data-testid="search"
            @keydown.enter.exact.prevent="step(1)"
            @keydown.enter.shift.prevent="step(-1)"
          />
          <span v-if="query.trim()" class="terminal-hits" data-testid="search-hits">{{ hits.length ? `${at + 1} of ${hits.length}` : 'No match' }}</span>
          <VButton v-if="hits.length > 1" label="Previous" variant="quiet" size="small" @click="step(-1)" />
          <VButton v-if="hits.length > 1" label="Next" variant="quiet" size="small" @click="step(1)" />
        </div>
      </div>
    </div>
    <RefusalNotice v-if="state === 'error' && refusal" :refusal="refusal">
      <VButton label="Try again" variant="secondary" size="small" @click="follower.start()" />
    </RefusalNotice>
    <div v-else ref="body" class="terminal-body" role="log" aria-label="Execution record" tabindex="0" @scroll.passive="onScroll">
      <div v-if="state === 'loading'" class="state-loading" aria-hidden="true">
        <span v-for="n in 6" :key="n" class="skeleton" :style="{ width: `${88 - ((n * 13) % 45)}%` }" />
      </div>
      <p v-else-if="record.lines.length === 0" class="terminal-empty" data-testid="terminal-empty">
        {{ state === 'ended' ? 'This run printed nothing.' : 'No line yet. The first line appears here the moment the worker prints it.' }}
      </p>
      <ol v-else class="terminal-lines" data-testid="lines" :class="{ 'is-raw': raw }">
        <TerminalLine
          v-for="line in record.lines"
          :key="line.seq"
          :line="line"
          :raw="raw"
          :match="currentHit !== null && hits.includes(line.seq)"
          :current="line.seq === currentHit"
        />
      </ol>
    </div>
    <button v-if="!following && unseen > 0 && state !== 'error'" type="button" class="terminal-jump" data-testid="jump" @click="jumpToLatest">
      Jump to latest ({{ unseen }} new)
    </button>
    <p v-if="state === 'ended' && record.committed" class="terminal-committed">
      Ended with {{ record.committed.lines }} lines committed, digest <code class="break">{{ record.committed.digest }}</code>
    </p>
  </div>
</template>
