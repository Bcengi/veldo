<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { KeepPacket } from '@/api/actions'
import { sendAnswer, type AnswerResult } from '@/api/decisions'
import { readSpacePending } from '@/api/reads'
import { ApiRefusal } from '@/api/refusal'
import UBadge from '@nuxt/ui/components/Badge.vue'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import VRadio from '@/components/VRadio.vue'
import VTextArea from '@/components/VTextArea.vue'
import { ceremonyMessage } from '@/features/signin/webauthn'
import { keepPick, keepTarget, sendKeep, signKeep } from '@/features/space/keep'
import { useDecisionsStore } from '@/stores/decisions'
import { useSessionStore } from '@/stores/session'
import { answerBody, choiceLabel, dueText, riskOf, urgencyOf, type PendingDecision, type Presentation } from './inbox'

/**
 * One pending decision exactly as it was presented, and its inline answer. What is shown is a snapshot of the
 * presentation taken when the decision opened, and the answer is bound to that snapshot (its id, digest and
 * version and the request's version). When the store later holds another version, nothing changes silently:
 * the screen says the question changed, clears the choice and offers the current version instead of sending.
 * The API settles an answer once, whichever channel answers first; any refusal is shown beside the action.
 *
 * A Keep answer to a space request (VELDO-0319 AC5) is applied with no second press. Keep is the one answer the
 * settlement cannot finish alone: the ledger takes it only as the owner's own signed command. So before the
 * answer is sent the owner's passkey signs the Keep command for the worktree the answer names, at the version
 * the space read shows; then the answer is sent; and once it has settled the signed packet is sent on space.keep.
 * A ceremony the owner closes sends nothing at all. A packet the ledger refuses leaves the answer settled and the
 * Keep unsigned: the refusal is shown by name, and the Space screen lists the worktree with Sign Keep.
 */
const props = defineProps<{ decision: PendingDecision }>()
const emit = defineEmits<{ settled: [result: AnswerResult] }>()
const store = useDecisionsStore()
const session = useSessionStore()
/** What became of the signed Keep: applied, refused by name, or settled with no packet this screen could sign. */
const keep = shallowRef<{ state: 'kept' | 'refused' | 'unsigned'; refusal: string | null } | null>(null)

/** The signed Keep packet for a Keep answer to a space request, before the answer is sent. Null when the answer
 * is not Keep, the request is no space request this member can sign for, or the space read is refused: the
 * answer is then sent as any other. A ceremony that does not finish throws, and nothing is sent. */
async function keepPacket(requestId: string, picked: string): Promise<{ space: boolean; packet: KeepPacket | null }> {
  const none = { space: false, packet: null }
  if (keepPick(picked) === undefined) return none
  const principal = session.principal
  const credentialId = session.view?.credential_id
  if (!principal || !credentialId) return none
  let pending
  try {
    pending = await readSpacePending()
  } catch (error) {
    if (error instanceof ApiRefusal) return none
    throw error
  }
  const target = keepTarget(pending, requestId, picked)
  if (!target) return none
  // A space request whose Keep this installation cannot take from a passkey: answered here, signed at the host.
  if (!pending.signing) return { space: true, packet: null }
  return { space: true, packet: await signKeep({ principal, credentialId, rpId: pending.signing }, target) }
}

/** The presentation this screen shows and an answer binds to. Replaced only by "Load the current version". */
const shown = shallowRef<Presentation | null>(props.decision.presentation)
const choice = ref<string | null>(null)
const rationale = ref('')
const pending = ref(false)
const loading = ref(false)
const refusal = shallowRef<ApiRefusal | null>(null)
const result = shallowRef<AnswerResult | null>(null)
const problem = ref<string | null>(null)

const latest = computed(() => props.decision.presentation)
/** The store holds a presentation other than the one shown: answering would answer a question not on screen. */
const changed = computed(() => {
  const now = latest.value
  const was = shown.value
  if (!was) return false
  return !now || now.id !== was.id || now.version !== was.version || now.digest !== was.digest || now.requestVersion !== was.requestVersion
})
/** The API said the shown presentation is no longer current. */
const stale = computed(() => refusal.value?.refusal === 'stale_version:stale_presentation')
const mustReload = computed(() => changed.value || stale.value)

const due = computed(() => dueText(props.decision.deadline, store.now))
const urgency = computed(() => urgencyOf(props.decision.deadline, store.now))
const risk = computed(() => riskOf(shown.value?.risk))
const published = computed(() => {
  const at = shown.value?.publishedAt
  if (typeof at !== 'number') return null
  const d = new Date(at * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
})

/** The answer bar's height, so the decision keeps room for it where the bar is pinned (phone). */
const bar = ref<HTMLElement | null>(null)
const barHeight = ref(0)
let sizer: ResizeObserver | null = null
onMounted(() => {
  if (typeof ResizeObserver === 'undefined') return
  sizer = new ResizeObserver(() => (barHeight.value = bar.value?.offsetHeight ?? 0))
  watch(bar, (el, was) => {
    if (was) sizer?.unobserve(was)
    if (el) sizer?.observe(el)
  }, { immediate: true })
})
onBeforeUnmount(() => sizer?.disconnect())

watch(changed, (now) => {
  if (now) choice.value = null
})

function onKey(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.tagName === 'TEXTAREA' || (target.tagName === 'INPUT' && (target as HTMLInputElement).type === 'text')) return
  const n = Number(event.key)
  const choices = shown.value?.choices ?? []
  if (!mustReload.value && Number.isInteger(n) && n >= 1 && n <= choices.length) choice.value = choices[n - 1] ?? null
}

async function send() {
  const presentation = shown.value
  if (!presentation || mustReload.value) return
  refusal.value = null
  problem.value = null
  if (!choice.value) {
    problem.value = 'Pick one of the choices first.'
    return
  }
  if (!rationale.value.trim()) {
    problem.value = 'Add a rationale: say briefly why.'
    return
  }
  pending.value = true
  let signed: { space: boolean; packet: KeepPacket | null }
  try {
    signed = await keepPacket(presentation.requestId, choice.value)
  } catch (error) {
    problem.value = `Keep was not signed, so no answer was sent. ${ceremonyMessage(error)}`
    pending.value = false
    return
  }
  try {
    const answered = await sendAnswer(answerBody(presentation, choice.value, rationale.value.trim()))
    if (signed.space) keep.value = await applyKeep(signed.packet, answered)
    result.value = answered
    emit('settled', answered)
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
    if (stale.value) choice.value = null
  } finally {
    pending.value = false
  }
}

/** Once the answer has settled, send the signed packet. The answer stands whatever the ledger says of the packet. */
async function applyKeep(packet: KeepPacket | null, answered: AnswerResult) {
  if (answered.outcome !== 'settled') return null
  if (!packet) return { state: 'unsigned' as const, refusal: null }
  try {
    const sent = await sendKeep(packet)
    return sent ? { state: 'kept' as const, refusal: null } : { state: 'refused' as const, refusal: 'missing_evidence:route' }
  } catch (error) {
    return { state: 'refused' as const, refusal: error instanceof ApiRefusal ? error.refusal : 'unavailable_service' }
  }
}

/** Read the inbox again and show the presentation that is current now; the choice starts over. */
async function loadCurrent() {
  loading.value = true
  try {
    await store.refresh()
  } finally {
    loading.value = false
  }
  shown.value = store.find(props.decision.requestId)?.presentation ?? props.decision.presentation
  choice.value = null
  refusal.value = null
  problem.value = null
}
</script>

<template>
  <article
    class="decision"
    data-testid="decision"
    :data-request="props.decision.requestId"
    :data-presentation-version="shown?.version"
    :data-request-version="shown?.requestVersion"
    :style="{ '--answer-bar': `${barHeight}px` }"
    @keydown="onKey"
  >
    <header class="decision-head">
      <p v-if="due || shown?.risk" class="decision-due">
        <span v-if="due" class="decision-when" :class="`is-${urgency}`" data-testid="decision-due">{{ due }}</span>
        <UBadge
          v-if="risk !== 'unknown'"
          class="inbox-risk status-badge"
          :class="`risk-${risk}`"
          :color="risk === 'high' ? 'error' : risk === 'medium' ? 'warning' : 'neutral'"
          variant="subtle"
          :label="`${risk.charAt(0).toUpperCase() + risk.slice(1)} risk`"
        />
      </p>
      <h2 class="decision-question" data-testid="question">{{ shown?.question || props.decision.brief }}</h2>
      <section v-if="shown?.risk" class="decision-risk-box" aria-label="Risk">
        <p class="eyebrow" aria-hidden="true">Risk</p>
        <p class="decision-risk" data-testid="risk">{{ shown.risk }}</p>
      </section>
    </header>

    <p v-if="!shown" class="decision-unpresented" data-testid="unpresented">
      This request has not been presented yet. It can be answered here once it has been sent to you.
    </p>

    <template v-else>
      <div v-if="result" class="decision-result" role="status" data-testid="answer-result">
        <p class="decision-result-title">Answer sent</p>
        <p>The factory recorded <strong>{{ choiceLabel(choice ?? '') }}</strong> as {{ result.ruling ?? result.outcome }}.</p>
        <p v-if="keep?.state === 'kept'" data-testid="keep-applied">Your passkey signed the Keep and the ledger marked the worktree Keep.</p>
        <p v-else-if="keep" class="answer-problem" role="alert" data-testid="keep-not-applied" :data-refusal="keep.refusal ?? undefined">
          Your answer is settled, but the Keep is not applied yet<span v-if="keep.refusal">: {{ keep.refusal }}</span>.
          <RouterLink to="/space">Sign Keep on the Space screen</RouterLink>
        </p>
      </div>

      <form v-else class="answer" :class="{ 'is-picked': choice !== null && !mustReload }" @submit.prevent="send">
        <fieldset class="answer-choices" :disabled="mustReload">
          <legend class="answer-legend">Your answer</legend>
          <label v-for="(c, i) in shown.choices" :key="c" class="choice" :class="{ 'is-picked': choice === c }" :data-choice="c">
            <VRadio v-model="choice" :input-id="`choice-${i}`" name="choice" :value="c" />
            <span class="choice-label">{{ choiceLabel(c) }}</span>
            <kbd class="choice-key" aria-hidden="true">{{ i + 1 }}</kbd>
          </label>
        </fieldset>
        <label class="field-label" for="rationale">Why this answer</label>
        <VTextArea id="rationale" v-model="rationale" rows="2" placeholder="Required. One or two sentences." data-testid="rationale" />
        <p class="answer-binding" data-testid="answer-binding">
          Answering version {{ shown.version }} of this question<span v-if="published">, presented at {{ published }}</span>.
        </p>
        <div ref="bar" class="answer-bar" data-testid="answer-bar">
          <p v-if="changed && !stale" class="answer-changed" role="status" data-testid="question-changed">
            This question changed since you opened it. Load the current version to answer it.
          </p>
          <p v-if="problem" class="answer-problem" role="alert">{{ problem }}</p>
          <RefusalNotice v-if="refusal" :refusal="refusal" compact />
          <VButton
            v-if="mustReload"
            label="Load the current version"
            pending-label="Loading the current version"
            :pending="loading"
            block
            data-testid="load-current"
            @click="loadCurrent"
          />
          <VButton v-else type="submit" label="Send answer" pending-label="Sending answer" :pending="pending" block data-testid="send-answer" />
        </div>
      </form>

      <details class="decision-more">
        <summary>Who can answer this</summary>
        <p class="decision-plain">
          Only {{ shown.owner === store.principal ? 'you' : shown.owner || 'the member it was presented to' }} can answer this. It settles once,
          here or in Telegram, whichever answers first.
        </p>
        <dl class="decision-why">
          <div v-if="shown.authority"><dt>Authority, as recorded</dt><dd class="decision-raw">{{ shown.authority }}</dd></div>
          <div v-if="shown.framedBy"><dt>Framed by</dt><dd>{{ shown.framedBy }}</dd></div>
          <div><dt>Request</dt><dd class="decision-raw">{{ props.decision.alias }}, version {{ shown.requestVersion }}</dd></div>
        </dl>
      </details>
      <details class="decision-more decision-shown">
        <summary>As it was presented in {{ shown.channel === 'telegram_chat' ? 'Telegram' : shown.channel }}</summary>
        <pre v-for="(part, i) in shown.rendered" :key="i" class="decision-rendered" data-testid="rendered">{{ part }}</pre>
      </details>
    </template>
  </article>
</template>
