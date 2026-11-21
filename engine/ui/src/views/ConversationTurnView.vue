<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { readConversation, type ConversationRead } from '@/api/conversations'
import Lamp from '@/components/Lamp.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import { useLiveRead } from '@/composables/useLiveRead'
import { turnMarker } from '@/features/conversations/conversations'
import { count, joinTraces, logged } from '@/features/conversations/telemetry'
import RunTerminal from '@/features/run/RunTerminal.vue'
import { useRecordFollower } from '@/features/run/useRecordFollower'
import { joinParam } from '@/router'
import '@/styles/factory.css'
import '@/styles/conversations.css'

/**
 * One turn of a conversation as a live terminal (VELDO-0179 AC2): VELDO-0145's run terminal on the turn's dispatch,
 * read through runs.record and followed through runs.record_stream from its cursor, every line in sequence with its
 * stream, receive time and redaction marks, live while the turn runs and complete after it with the record's line
 * count and digest. Never a summary: the reply is on the conversation screen, the record is here.
 */
const route = useRoute()
const id = computed(() => joinParam(route.params.conversation as string | string[]))
const sequence = computed(() => Number(route.params.sequence))
const live = useLiveRead<ConversationRead>(
  (signal) => logged('conversations.read', () => readConversation(id.value, signal)),
  (a) => a.watermark,
)
const turn = computed(() => live.data.value?.turns.find((t) => t.sequence === sequence.value) ?? null)
const dispatch = computed(() => turn.value?.dispatch_id ?? '')
const marker = computed(() => (turn.value ? turnMarker(turn.value) : null))
const follower = useRecordFollower(() => dispatch.value)
watch(
  () => follower.stats.reconnects,
  (now, before) => {
    if (now > (before ?? 0)) count('terminal_reconnects', now - (before ?? 0))
  },
)
watch(
  () => live.data.value?.turns,
  (turns) => turns && joinTraces(id.value, turns),
)
const STATUS = {
  waiting: { lamp: 'waiting' as const, word: 'Waiting for a worker' },
  running: { lamp: 'live' as const, word: 'Running' },
  ended: { lamp: 'done' as const, word: 'Ended' },
}
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-run" data-testid="turn-screen" :data-sequence="sequence">
    <ScreenHeader :title="`Turn ${sequence}`" :back="{ to: { name: 'conversation', params: { conversation: id } }, label: 'Conversation' }">
      <template #aside>
        <p v-if="marker" class="run-status" data-testid="turn-status" :data-marker="marker">
          <Lamp :state="STATUS[marker].lamp" :label="STATUS[marker].word" size="sm" />
          <span>{{ STATUS[marker].word }}</span>
          <span v-if="turn?.outcome" class="factory-tag">{{ turn.outcome }}</span>
        </p>
      </template>
    </ScreenHeader>
    <StatePanel :state="live.state.value" :refusal="live.refusal.value" loading-label="Loading the turn" shape="lines" @retry="live.refresh()">
      <p v-if="!turn" class="state-empty-body" data-testid="turn-unknown">This conversation has no turn {{ sequence }}.</p>
      <p v-else-if="!dispatch" class="state-empty-body" data-testid="turn-waiting">
        No worker has taken this turn yet. Its terminal opens here the moment one starts.
      </p>
      <RunTerminal v-else :dispatch="dispatch" :follower="follower" />
    </StatePanel>
  </section>
</template>
