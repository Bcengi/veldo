<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { listConversations, openConversation, readConversation } from '@/api/conversations'
import { ApiRefusal } from '@/api/refusal'
import Lamp from '@/components/Lamp.vue'
import RefusalNotice from '@/components/RefusalNotice.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useLiveRead } from '@/composables/useLiveRead'
import { activityTime, openingWords, orderConversations, type ListedConversation } from '@/features/conversations/conversations'
import { count, logged } from '@/features/conversations/telemetry'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import '@/styles/factory.css'
import '@/styles/conversations.css'

/** The owner's conversations (VELDO-0179 AC1): open ones first, then closed, each with its opening words, its role
 * and its last activity, read through conversations.read and kept current by the events stream. New conversation
 * opens one through conversations.open and goes to it. */
const router = useRouter()

async function load(signal: AbortSignal) {
  const list = await logged('conversations.read', () => listConversations(signal))
  const read = await Promise.all(
    list.conversations.map((c) =>
      c.turns > 0
        ? logged('conversations.read', () => readConversation(c.id, signal)).then(
            (one) => openingWords(one.turns[0]?.message ?? null),
            (error: unknown) => {
              if ((error as Error)?.name === 'AbortError') throw error
              return null
            },
          )
        : Promise.resolve(null),
    ),
  )
  const items: ListedConversation[] = list.conversations.map((c, i) => ({ ...c, opening: read[i] ?? null }))
  return { items: orderConversations(items), watermark: list.watermark, freshness: list.freshness }
}

const live = useLiveRead(load, (a) => a.watermark, (a) => a.items.length === 0)
const items = computed(() => live.data.value?.items ?? [])
const openCount = computed(() => items.value.filter((c) => c.status === 'open').length)
const opening = ref(false)
const refusal = shallowRef<ApiRefusal | null>(null)

async function start() {
  if (opening.value) return
  opening.value = true
  refusal.value = null
  try {
    const answer = await logged('conversations.open', () => openConversation())
    count('conversations_opened')
    if (answer.conversation) await router.push({ name: 'conversation', params: { conversation: answer.conversation } })
    else await live.refresh()
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
  } finally {
    opening.value = false
  }
}

onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide" data-testid="conversations-screen">
    <ScreenHeader title="Conversations">
      <template #aside>
        <VButton label="New conversation" pending-label="Opening" :pending="opening" data-testid="conversation-new" @click="start" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <RefusalNotice v-if="refusal" :refusal="refusal" compact />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No conversation yet"
      empty-body="Start one with New conversation, or write to the factory on Telegram."
      loading-label="Loading conversations"
      @retry="live.refresh()"
    >
      <section class="panel" aria-labelledby="conversations-title" data-testid="conversations">
        <h2 id="conversations-title" class="panel-title">
          Conversations <span class="panel-count">{{ openCount }} open of {{ items.length }}</span>
        </h2>
        <div class="factory-body">
          <ul class="factory-list" aria-label="Your conversations">
            <li v-for="c in items" :key="c.id" class="factory-card" :data-conversation="c.id" :data-status="c.status">
              <RouterLink :to="{ name: 'conversation', params: { conversation: c.id } }" class="factory-card-button conv-link" data-testid="conversation-link">
                <span class="factory-card-title" data-testid="conversation-opening">{{ c.opening ?? 'No message yet' }}</span>
                <span class="factory-meta">
                  <span class="factory-live">
                    <Lamp :state="c.status === 'open' ? 'live' : 'off'" :label="c.status === 'open' ? 'Open' : 'Closed'" size="sm" />
                    <span data-testid="conversation-status">{{ c.status === 'open' ? 'Open' : 'Closed' }}</span>
                  </span>
                  <span data-testid="conversation-role">Role {{ c.role }}</span>
                  <span>{{ c.turns }} turn{{ c.turns === 1 ? '' : 's' }}</span>
                  <span data-testid="conversation-activity">Last activity {{ activityTime(c.last_activity) }}</span>
                </span>
              </RouterLink>
            </li>
          </ul>
        </div>
      </section>
    </StatePanel>
  </section>
</template>
