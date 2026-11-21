<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { DEFAULT_TEAM, readTeam } from '@/api/configuration'
import {
  attachConversationProject,
  closeConversation,
  readConversation,
  sendToConversation,
  setConversationRole,
  type ConversationRead,
} from '@/api/conversations'
import { readObjectives } from '@/api/reads'
import { ApiRefusal } from '@/api/refusal'
import type { RouteName } from '@/api/routes'
import Lamp from '@/components/Lamp.vue'
import RefusalNotice from '@/components/RefusalNotice.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import VTextArea from '@/components/VTextArea.vue'
import { useAsync } from '@/composables/useAsync'
import { useLiveRead } from '@/composables/useLiveRead'
import { activityTime, currentTurn, openingWords, scopeProjects, teamRoles, turnMarker } from '@/features/conversations/conversations'
import { count, joinTraces, logged, traceSent, type Metric } from '@/features/conversations/telemetry'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { joinParam } from '@/router'
import '@/styles/factory.css'
import '@/styles/conversations.css'

/**
 * One conversation (VELDO-0179 AC1): every turn in order with the owner's message, the reply and the outcome as the
 * API serves them (text, never markup), a waiting or running marker on the current turn with its live terminal one
 * tap away, the role and project controls and Close (each on the version the screen read, so a stale one is refused
 * by name beside it), and the message box, which sends through messages.send with the `conversation` field. The
 * screen follows the events stream, so a turn sent from Telegram and every reply appear without a reload.
 */
const route = useRoute()
const id = computed(() => joinParam(route.params.conversation as string | string[]))

const live = useLiveRead<ConversationRead>(
  (signal) => logged('conversations.read', () => readConversation(id.value, signal)),
  (a) => a.watermark,
)
const view = computed(() => live.data.value?.conversation ?? null)
const turns = computed(() => live.data.value?.turns ?? [])
const current = computed(() => currentTurn(turns.value))
const closed = computed(() => view.value?.status !== 'open')
const title = computed(() => openingWords(turns.value[0]?.message ?? null) ?? 'New conversation')

const team = useAsync((signal) => logged('teams.read', () => readTeam(DEFAULT_TEAM, signal)))
const scope = useAsync((signal) => logged('reads.objectives', () => readObjectives(signal)))
const roles = computed(() => teamRoles(team.data.value, view.value?.role ?? null))
const projects = computed(() => scopeProjects(scope.data.value))

const role = ref('')
const project = ref('')
watch(view, (v) => {
  if (v && !role.value) role.value = v.role
  if (v && !project.value) project.value = v.project ?? projects.value[0] ?? ''
})
watch(projects, (list) => {
  if (!project.value) project.value = view.value?.project ?? list[0] ?? ''
})
watch(turns, (list) => joinTraces(id.value, list))

type Action = 'send' | 'role' | 'project' | 'close'
const pending = ref<Action | null>(null)
const refusals = shallowRef<Partial<Record<Action, ApiRefusal>>>({})
const done = ref<{ action: Action; words: string } | null>(null)
const text = ref('')

const named = (error: unknown) => (error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable'))

async function act(action: Action, routeName: RouteName, metric: Metric, call: () => Promise<unknown>, words: string) {
  if (pending.value) return false
  pending.value = action
  refusals.value = { ...refusals.value, [action]: undefined }
  done.value = null
  try {
    await logged(routeName, call)
    count(metric)
    done.value = { action, words }
    return true
  } catch (error) {
    refusals.value = { ...refusals.value, [action]: named(error) }
    return false
  } finally {
    pending.value = null
    // The screen shows what the API now holds: the version a stale command missed, or the change it made.
    await live.refresh()
  }
}

async function send() {
  const body = text.value.trim()
  if (!body || pending.value || !view.value) return
  const after = turns.value.reduce((m, t) => Math.max(m, t.sequence), 0)
  let requestId: string | null = null
  const ok = await act(
    'send',
    'messages.send',
    'messages_sent',
    async () => {
      const answer = await sendToConversation(body, id.value)
      requestId = typeof answer.api_request_id === 'string' ? answer.api_request_id : null
    },
    'Sent.',
  )
  if (ok) {
    text.value = ''
    traceSent(id.value, requestId, after)
    joinTraces(id.value, turns.value)
  }
}

const changeRole = () =>
  view.value &&
  act('role', 'conversations.set_role', 'role_changes', () => setConversationRole(id.value, view.value!.version, role.value), `Role changed to ${role.value}.`)
const attach = () =>
  view.value &&
  act('project', 'conversations.attach_project', 'project_attaches', () => attachConversationProject(id.value, view.value!.version, project.value), `Attached ${project.value}.`)
const close = () =>
  view.value && act('close', 'conversations.close', 'conversations_closed', () => closeConversation(id.value, view.value!.version), 'Conversation closed.')

const turnRoute = (sequence: number) => ({ name: 'conversation-turn', params: { conversation: id.value, sequence: String(sequence) } })
const OUTCOME_TONE: Record<string, string> = { completed: 'is-done' }

onMounted(() => {
  void live.start()
  void team.run()
  void scope.run()
})
watch(id, () => void live.refresh())
</script>

<template>
  <section class="screen screen-wide conv-screen" data-testid="conversation-screen" :data-conversation="id">
    <ScreenHeader :title="title" :back="{ to: { name: 'conversations' }, label: 'Conversations' }">
      <template #aside>
        <span v-if="view" class="factory-tag" :class="closed ? 'is-stop' : 'is-done'" data-testid="conversation-state">{{ closed ? 'Closed' : 'Open' }}</span>
      </template>
      <p v-if="view" class="factory-meta">
        <span data-testid="conversation-current-role">Role {{ view.role }}</span>
        <span v-if="view.project" data-testid="conversation-project">Project {{ view.project }}</span>
        <span>Version {{ view.version }}</span>
        <span>Last activity {{ activityTime(view.last_activity) }}</span>
      </p>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel :state="live.state.value" :refusal="live.refusal.value" loading-label="Loading the conversation" shape="block" @retry="live.refresh()">
      <div class="factory-grid factory-split">
        <section class="panel conv-turns-panel" aria-labelledby="turns-title" data-testid="turns-panel">
          <h2 id="turns-title" class="panel-title">Turns <span class="panel-count">{{ turns.length }}</span></h2>
          <div class="factory-body">
            <p v-if="!turns.length" class="state-empty-body" data-testid="turns-empty">No message yet. Write the first one below.</p>
            <ol v-else class="conv-turns" aria-label="Turns in order" data-testid="turns">
              <li
                v-for="turn in turns"
                :key="turn.sequence"
                class="conv-turn"
                :data-sequence="turn.sequence"
                :data-state="turnMarker(turn)"
                :data-testid="`turn-${turn.sequence}`"
              >
                <div class="conv-bubble conv-mine">
                  <p class="conv-who">You, turn {{ turn.sequence }}</p>
                  <p class="conv-text" data-testid="turn-message">{{ turn.message ?? '' }}</p>
                </div>
                <div v-if="turnMarker(turn) === 'waiting'" class="conv-marker" role="status" data-testid="turn-marker" data-marker="waiting">
                  <Lamp state="waiting" label="Waiting" size="sm" /><span>Waiting for a worker</span>
                </div>
                <div v-else-if="turnMarker(turn) === 'running'" class="conv-marker" role="status" data-testid="turn-marker" data-marker="running">
                  <Lamp state="live" label="Running" size="sm" /><span>Running</span>
                  <RouterLink :to="turnRoute(turn.sequence)" class="vbtn vbtn-secondary conv-watch" data-testid="turn-watch">Watch live</RouterLink>
                </div>
                <div v-else class="conv-bubble conv-reply">
                  <p class="conv-who">
                    Reply
                    <span class="factory-tag" :class="OUTCOME_TONE[turn.outcome ?? ''] ?? 'is-stop'" data-testid="turn-outcome">{{ turn.outcome ?? 'ended' }}</span>
                  </p>
                  <p v-if="turn.reply !== null" class="conv-text" data-testid="turn-reply">{{ turn.reply }}</p>
                  <p v-else class="factory-meta" data-testid="turn-no-reply">No reply text for this turn.</p>
                </div>
                <RouterLink v-if="turn.dispatch_id && turnMarker(turn) !== 'running'" :to="turnRoute(turn.sequence)" class="conv-terminal-link" data-testid="turn-terminal">
                  Open the terminal of turn {{ turn.sequence }}
                </RouterLink>
              </li>
            </ol>
          </div>
        </section>
        <section class="panel" aria-labelledby="controls-title" data-testid="conversation-controls">
          <h2 id="controls-title" class="panel-title">Conversation</h2>
          <div class="factory-body">
            <div class="conv-control">
              <label for="conv-role" class="field-label">Role</label>
              <select id="conv-role" v-model="role" class="factory-select" :disabled="closed || pending !== null" data-testid="role-select">
                <option v-for="name in roles" :key="name" :value="name">{{ name }}{{ name === view?.role ? ' (current)' : '' }}</option>
              </select>
              <VButton label="Change role" pending-label="Changing role" variant="secondary" :pending="pending === 'role'" :disabled="closed || !role || role === view?.role" data-testid="role-change" @click="changeRole" />
              <RefusalNotice v-if="team.refusal.value" :refusal="team.refusal.value" compact />
              <RefusalNotice v-if="refusals.role" :refusal="refusals.role" compact data-testid="role-refusal" />
            </div>
            <div class="conv-control">
              <label for="conv-project" class="field-label">Project</label>
              <select id="conv-project" v-model="project" class="factory-select" :disabled="closed || pending !== null || !projects.length" data-testid="project-select">
                <option v-for="name in projects" :key="name" :value="name">{{ name }}{{ name === view?.project ? ' (attached)' : '' }}</option>
              </select>
              <VButton label="Attach project" pending-label="Attaching" variant="secondary" :pending="pending === 'project'" :disabled="closed || !project" data-testid="project-attach" @click="attach" />
              <RefusalNotice v-if="scope.refusal.value" :refusal="scope.refusal.value" compact />
              <RefusalNotice v-if="refusals.project" :refusal="refusals.project" compact data-testid="project-refusal" />
            </div>
            <div class="conv-control">
              <VButton label="Close conversation" pending-label="Closing" variant="danger" :pending="pending === 'close'" :disabled="closed" data-testid="conversation-close" @click="close" />
              <RefusalNotice v-if="refusals.close" :refusal="refusals.close" compact data-testid="close-refusal" />
            </div>
            <p v-if="done && done.action !== 'send'" class="factory-meta" role="status" data-testid="control-done">{{ done.words }}</p>
          </div>
        </section>
      </div>
      <form class="conv-composer" aria-label="Message" data-testid="composer" @submit.prevent="send">
        <label for="conv-message" class="field-label">{{ closed ? 'This conversation is closed' : 'Message' }}</label>
        <div class="conv-composer-row">
          <VTextArea id="conv-message" v-model="text" rows="2" :disabled="closed || pending === 'send'" data-testid="message-text" @keydown.enter.ctrl.prevent="send" @keydown.enter.meta.prevent="send" />
          <VButton type="submit" label="Send" pending-label="Sending" :pending="pending === 'send'" :disabled="closed || !text.trim()" data-testid="message-send" />
        </div>
        <RefusalNotice v-if="refusals.send" :refusal="refusals.send" compact data-testid="send-refusal" />
        <p v-if="current" class="sr-only" role="status">Turn {{ current.sequence }} is {{ turnMarker(current) }}.</p>
      </form>
    </StatePanel>
  </section>
</template>
