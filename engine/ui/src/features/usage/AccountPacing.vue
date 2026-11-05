<script setup lang="ts">
import { computed, ref } from 'vue'
import { pauseAccount, resumeAccount, setCeiling, type ActionResult } from '@/api/actions'
import { isRefusal } from '@/api/refusal'
import type { ReadAnswer } from '@/api/types'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import { canCap, canPause, ceilingValue, eventWords, historyOf, pacingOf } from './pacing'

/** VELDO-0236: each account's windows with utilization and reset, its pause and ceilings in force, the owner's
 * pause, ceiling and resume actions, and the history, all from the pacing read (accounts.pacing, from the journal). A refusal is shown beside the
 * action with its name; an action is shown done only when the API answers it. */
const props = defineProps<{ pacing: ReadAnswer | null; now: number }>()
const emit = defineEmits<{ changed: [] }>()

const accounts = computed(() => pacingOf(props.pacing, props.now))
const history = computed(() => historyOf(props.pacing))
const pending = ref<string | null>(null)
const answer = ref<{ key: string; words: string } | null>(null)
const refusal = ref<{ key: string; refusal: { refusal: string; error: string } } | null>(null)
const typed = ref<Record<string, string>>({})

const when = (seconds: number) => new Date(seconds * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })

async function act(key: string, send: () => Promise<ActionResult<Record<string, unknown>>>) {
  pending.value = key
  answer.value = null
  refusal.value = null
  try {
    const result = await send()
    if (!result.sent) refusal.value = { key, refusal: { refusal: `unpublished_route:${result.route}`, error: 'unknown_outcome' } }
    else {
      answer.value = { key, words: String(result.answer.words ?? result.answer.outcome ?? '') }
      emit('changed')
    }
  } catch (error) {
    if (isRefusal(error)) refusal.value = { key, refusal: { refusal: error.refusal, error: error.error } }
    else refusal.value = { key, refusal: { refusal: 'unavailable_service:api', error: 'unavailable_service' } }
  } finally {
    pending.value = null
  }
}

function cap(account: string, window: string) {
  const key = `ceiling:${account}:${window}`
  const value = ceilingValue(typed.value[key] ?? '')
  if (value == null) {
    refusal.value = { key, refusal: { refusal: 'invalid_input:ceiling', error: 'invalid_input' } }
    return
  }
  void act(key, () => setCeiling(account, window, value))
}
</script>

<template>
  <section class="panel" aria-labelledby="usage-pacing-title" data-testid="usage-pacing">
    <h2 id="usage-pacing-title" class="panel-title">Pacing <span class="panel-count">{{ accounts.length }}</span></h2>
    <p v-if="!accounts.length" class="factory-body factory-meta" data-testid="pacing-empty">No account is registered yet.</p>
    <ul v-else class="factory-body factory-list">
      <li v-for="a in accounts" :key="a.account" class="factory-card" :data-pacing-account="a.account">
        <span class="factory-card-title">{{ a.account }}
          <span v-if="a.pause" class="factory-tag is-stop" data-testid="pacing-paused">Paused until {{ when(a.pause.until) }}, when {{ a.pause.window }} resets</span>
          <span v-for="c in a.ceilings" :key="c.window" class="factory-tag is-waiting" data-testid="pacing-ceiling">Ceiling {{ c.value }}% on {{ c.window }} until {{ when(c.until) }}</span>
        </span>
        <ul class="factory-list" :aria-label="`Windows of ${a.account}`">
          <li v-for="w in a.windows" :key="w.id" class="factory-meta" :data-window="w.id">
            <span>{{ w.id }}: {{ w.utilization == null ? 'utilization not reported' : `${w.utilization}% used` }}, resets {{ w.resetAt ? when(w.resetAt) : 'at an unknown time' }}</span>
            <VButton :label="`Pause until ${w.id} resets`" variant="secondary" size="small" :disabled="!canPause(w, props.now)" :pending="pending === `pause:${a.account}:${w.id}`" pending-label="Pausing" data-testid="pacing-pause" @click="act(`pause:${a.account}:${w.id}`, () => pauseAccount(a.account, w.id))" />
            <label class="field-label" :for="`ceiling-${a.account}-${w.id}`">Ceiling on {{ w.id }} (50 or +10)</label>
            <input :id="`ceiling-${a.account}-${w.id}`" v-model="typed[`ceiling:${a.account}:${w.id}`]" class="factory-select" inputmode="decimal" :disabled="!canCap(w, props.now)" data-testid="pacing-ceiling-value" />
            <VButton label="Set ceiling" variant="secondary" size="small" :disabled="!canCap(w, props.now)" :pending="pending === `ceiling:${a.account}:${w.id}`" pending-label="Setting ceiling" data-testid="pacing-ceiling-set" @click="cap(a.account, w.id)" />
            <p v-if="answer && (answer.key === `pause:${a.account}:${w.id}` || answer.key === `ceiling:${a.account}:${w.id}`)" role="status" data-testid="pacing-answer">{{ answer.words }}</p>
            <RefusalNotice v-if="refusal && (refusal.key === `pause:${a.account}:${w.id}` || refusal.key === `ceiling:${a.account}:${w.id}`)" :refusal="refusal.refusal" compact />
          </li>
          <li v-if="!a.windows.length" class="factory-meta">No window observed yet: nothing to pause on or cap.</li>
        </ul>
        <VButton v-if="a.pause || a.ceilings.length" label="Resume now" size="small" :pending="pending === `resume:${a.account}`" pending-label="Resuming" data-testid="pacing-resume" @click="act(`resume:${a.account}`, () => resumeAccount(a.account))" />
        <p v-if="answer && answer.key === `resume:${a.account}`" role="status" data-testid="pacing-answer">{{ answer.words }}</p>
        <RefusalNotice v-if="refusal && refusal.key === `resume:${a.account}`" :refusal="refusal.refusal" compact />
      </li>
    </ul>
    <h3 class="panel-title">History</h3>
    <ol v-if="history.length" class="factory-body factory-list" aria-label="Pacing history" data-testid="pacing-history">
      <li v-for="e in history" :key="e.seq" class="factory-meta" :data-type="e.type">{{ eventWords(e, when) }}</li>
    </ol>
    <p v-else class="factory-body factory-meta" data-testid="pacing-history-empty">No pause or ceiling recorded yet.</p>
  </section>
</template>
