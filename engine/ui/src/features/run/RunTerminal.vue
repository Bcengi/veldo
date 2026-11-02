<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { isRetryable } from '@/api/refusal'
import Icon from '@/components/Icon.vue'
import RefusalNotice from '@/components/RefusalNotice.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import VSwitch from '@/components/VSwitch.vue'
import VTextField from '@/components/VTextField.vue'
import { matches } from './record'
import TerminalLine from './TerminalLine.vue'
import { useRecordFollower } from './useRecordFollower'

/**
 * A run's execution record as a live terminal: every kept line in sequence, followed live from its cursor.
 * Reusable: give it a dispatch id (the conversation screens of VELDO-0179 open it on a turn's dispatch), and
 * optionally the follower its screen already holds, so the screen's header reads the same record.
 */
const props = defineProps<{ dispatch: string; follower?: ReturnType<typeof useRecordFollower> }>()
const follower = props.follower ?? useRecordFollower(() => props.dispatch)
const { record, state, refusal, stats } = follower

const body = ref<HTMLElement | null>(null)
const searchBox = ref<{ focus: () => void } | null>(null)
/** On a phone the search field opens from the bar; on a desktop it is always there. */
const searching = ref(false)
const following = ref(true)
const raw = ref(false)
const query = ref('')
const at = ref(0)
const unseen = ref(0)

const hits = computed(() => (query.value.trim() ? record.lines.filter((l) => matches(l, query.value)).map((l) => l.seq) : []))
const currentHit = computed(() => hits.value[at.value] ?? null)
const live = computed(() => state.value === 'live' || state.value === 'reconnecting')
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
  // The lines render once loading ends; a following view starts at the end of them.
  if (before === 'loading' && following.value) void nextTick(scrollToEnd)
})
watch(query, () => (at.value = 0))
watch(currentHit, (seq) => {
  if (seq === null) return
  following.value = false
  void nextTick(() => body.value?.querySelector(`[data-seq="${seq}"]`)?.scrollIntoView({ block: 'center' }))
})

async function openSearch() {
  searching.value = true
  await nextTick()
  searchBox.value?.focus()
}

function closeSearch() {
  searching.value = false
  query.value = ''
}

function step(direction: 1 | -1) {
  const count = hits.value.length
  if (count) at.value = (at.value + direction + count) % count
}

function onKey(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  const typing = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'
  if (event.key === '/' && !typing) {
    event.preventDefault()
    void openSearch()
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
    <RefusalNotice v-if="state === 'error' && refusal" :refusal="refusal">
      <VButton v-if="isRetryable(refusal)" label="Try again" variant="secondary" size="small" data-testid="try-again" @click="follower.start()" />
    </RefusalNotice>
    <template v-else>
      <slot name="strip" :run="record.run" :live="live" />
      <div class="terminal-bar" :class="{ 'is-searching': searching }" role="toolbar" aria-label="Record controls">
        <p class="terminal-status" role="status" aria-live="polite" data-testid="terminal-status">
          <span class="terminal-count" data-testid="line-count">{{ record.lines.length }} {{ record.lines.length === 1 ? 'line' : 'lines' }}</span>
          <span v-if="stats.reconnects" class="terminal-reconnects">{{ stats.reconnects }} {{ stats.reconnects === 1 ? 'reconnect' : 'reconnects' }}</span>
        </p>
        <div class="terminal-switches">
          <label class="terminal-switch">
            <VSwitch v-model="following" input-id="follow" label="Follow the latest line" data-testid="follow" />
            <span aria-hidden="true">Follow</span>
          </label>
          <label class="terminal-switch">
            <VSwitch v-model="raw" input-id="raw" label="Show raw lines" data-testid="raw" />
            <span aria-hidden="true">Raw</span>
          </label>
        </div>
        <button type="button" class="terminal-search-open" aria-label="Search the record" data-testid="search-open" @click="openSearch">
          <Icon name="search" :size="20" />
        </button>
        <div class="terminal-search">
          <label for="record-search" class="sr-only">Search the record</label>
          <VTextField
            id="record-search"
            ref="searchBox"
            v-model="query"
            type="search"
            placeholder="Search the record"
            autocomplete="off"
            data-testid="search"
            @keydown.enter.exact.prevent="step(1)"
            @keydown.enter.shift.prevent="step(-1)"
            @keydown.esc="closeSearch"
          />
          <span v-if="query.trim()" class="terminal-hits" data-testid="search-hits">{{ hits.length ? `${at + 1} of ${hits.length}` : 'No match' }}</span>
          <VButton v-if="hits.length > 1" label="Previous" variant="quiet" size="small" @click="step(-1)" />
          <VButton v-if="hits.length > 1" label="Next" variant="quiet" size="small" @click="step(1)" />
          <button type="button" class="terminal-search-close" aria-label="Close search" @click="closeSearch">
            <Icon name="close" :size="20" />
          </button>
        </div>
      </div>
      <div ref="body" class="terminal-body" role="log" aria-label="Execution record" tabindex="0" @scroll.passive="onScroll">
        <StatePanel v-if="state === 'loading'" state="loading" shape="lines" :rows="9" loading-label="Loading the record" />
        <p v-else-if="record.lines.length === 0" class="terminal-empty" data-testid="terminal-empty">
          {{ state === 'ended' ? 'This run printed nothing.' : 'No line yet. The first line appears here the moment the worker prints it.' }}
        </p>
        <ol v-else class="terminal-lines" data-testid="lines" :class="{ 'is-raw': raw }">
          <TerminalLine
            v-for="line in record.lines"
            :key="line.seq"
            :line="line"
            :start="record.lines[0]!.at"
            :raw="raw"
            :match="currentHit !== null && hits.includes(line.seq)"
            :current="line.seq === currentHit"
          />
        </ol>
      </div>
      <button v-if="!following && unseen > 0" type="button" class="terminal-jump" data-testid="jump" @click="jumpToLatest">
        Jump to latest ({{ unseen }} new)
      </button>
      <p v-if="state === 'ended' && record.committed" class="terminal-committed">
        <span>{{ record.committed.lines }} lines committed</span>
        <span class="terminal-digest">digest <code class="break">{{ record.committed.digest }}</code></span>
      </p>
    </template>
  </div>
</template>
