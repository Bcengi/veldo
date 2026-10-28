<script setup lang="ts">
import RadioButton from 'primevue/radiobutton'
import Textarea from 'primevue/textarea'
import { computed, ref, shallowRef, watch } from 'vue'
import { sendAnswer, type AnswerResult } from '@/api/decisions'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import { answerBody, choiceLabel, type PendingDecision } from './inbox'

/**
 * One pending decision exactly as it was presented, and its inline answer. The answer is bound to the
 * presentation shown here (its id, digest and version and the request's version); the API settles it
 * once, whichever channel answers first, and any refusal is shown beside the action.
 */
const props = defineProps<{ decision: PendingDecision }>()
const emit = defineEmits<{ settled: [result: AnswerResult] }>()

const choice = ref<string | null>(null)
const rationale = ref('')
const pending = ref(false)
const refusal = shallowRef<ApiRefusal | null>(null)
const result = shallowRef<AnswerResult | null>(null)
const problem = ref<string | null>(null)
/** The presentation as it was when this screen showed it: an answer is bound to this, never re-read. */
const shown = computed(() => props.decision.presentation)

watch(
  () => props.decision.requestId,
  () => {
    choice.value = null
    rationale.value = ''
    refusal.value = null
    result.value = null
    problem.value = null
  },
)

function onKey(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' && (target as HTMLInputElement).type === 'text') return
  const n = Number(event.key)
  const choices = shown.value?.choices ?? []
  if (Number.isInteger(n) && n >= 1 && n <= choices.length) choice.value = choices[n - 1] ?? null
}

async function send() {
  const presentation = shown.value
  if (!presentation) return
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
  try {
    result.value = await sendAnswer(answerBody(presentation, choice.value, rationale.value.trim()))
    emit('settled', result.value)
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <article class="decision" data-testid="decision" :data-request="props.decision.requestId" @keydown="onKey">
    <header class="decision-head">
      <p class="decision-alias">{{ props.decision.alias }}</p>
      <h2 class="decision-question" data-testid="question">{{ shown?.question || props.decision.brief }}</h2>
    </header>

    <p v-if="!shown" class="decision-unpresented" data-testid="unpresented">
      This request has not been presented yet. It can be answered here once it has been sent to you.
    </p>

    <template v-else>
      <dl class="decision-why">
        <div v-if="shown.risk"><dt>Risk</dt><dd data-testid="risk">{{ shown.risk }}</dd></div>
        <div v-if="shown.authority"><dt>Authority</dt><dd>{{ shown.authority }}</dd></div>
        <div v-if="shown.framedBy"><dt>Framed by</dt><dd>{{ shown.framedBy }}</dd></div>
      </dl>

      <details class="decision-shown">
        <summary>As it was presented in {{ shown.channel === 'telegram_chat' ? 'Telegram' : shown.channel }}</summary>
        <pre v-for="(part, i) in shown.rendered" :key="i" class="decision-rendered" data-testid="rendered">{{ part }}</pre>
      </details>

      <div v-if="result" class="decision-result" role="status" data-testid="answer-result">
        <p class="decision-result-title">Answer sent</p>
        <p>The factory recorded <strong>{{ choiceLabel(choice ?? '') }}</strong> as {{ result.ruling ?? result.outcome }}.</p>
        <p class="refusal-name"><code>{{ result.outcome }}</code></p>
      </div>

      <form v-else class="answer" @submit.prevent="send">
        <fieldset class="answer-choices">
          <legend class="answer-legend">Your answer</legend>
          <label v-for="(c, i) in shown.choices" :key="c" class="choice" :class="{ 'is-picked': choice === c }" :data-choice="c">
            <RadioButton v-model="choice" :input-id="`choice-${i}`" name="choice" :value="c" />
            <span class="choice-label">{{ choiceLabel(c) }}</span>
            <kbd class="choice-key" aria-hidden="true">{{ i + 1 }}</kbd>
          </label>
        </fieldset>
        <label class="field-label" for="rationale">Rationale, required: why this answer</label>
        <Textarea id="rationale" v-model="rationale" rows="3" auto-resize data-testid="rationale" />
        <p class="answer-binding">
          Answers presentation version {{ shown.version }} of request version {{ shown.requestVersion }}.
        </p>
        <div class="answer-bar" data-testid="answer-bar">
          <p v-if="problem" class="answer-problem" role="alert">{{ problem }}</p>
          <RefusalNotice v-if="refusal" :refusal="refusal" compact />
          <VButton type="submit" label="Send answer" pending-label="Sending answer" :pending="pending" block data-testid="send-answer" />
        </div>
      </form>
    </template>
  </article>
</template>
