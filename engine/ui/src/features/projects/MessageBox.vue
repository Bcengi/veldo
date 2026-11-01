<script setup lang="ts">
import { computed, ref } from 'vue'
import { sendMessage, type MessageAnswer } from '@/api/messages'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import VTextArea from '@/components/VTextArea.vue'
import type { IntakeEntry } from './projects'

/** The owner's message box to the factory (VELDO-0131): the conversation is the intake's own records of the
 * messages sent and the questions it asked back, and Send goes to the common intake through messages.send. The
 * answer shown is the API's (what the intake recorded); nothing is added to the conversation until the intake's
 * record of it is read back. */
const props = defineProps<{ entries: IntakeEntry[]; project: string | null; idPrefix: string }>()
const emit = defineEmits<{ sent: [answer: MessageAnswer] }>()
const text = ref('')
const pending = ref(false)
const answer = ref<MessageAnswer | null>(null)
const refusal = ref<ApiRefusal | null>(null)
const shown = computed(() => props.entries.filter((e) => !props.project || e.project === props.project || e.project === null))

async function send() {
  const body = text.value.trim()
  if (!body || pending.value) return
  pending.value = true
  answer.value = null
  refusal.value = null
  try {
    answer.value = await sendMessage(body, props.project ?? undefined)
    text.value = ''
    emit('sent', answer.value)
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="factory-grid" :data-testid="`${props.idPrefix}-chat`">
    <ol class="factory-list" :aria-label="props.project ? `Messages about ${props.project}` : 'Messages to the factory'" data-testid="chat-log">
      <li v-for="entry in shown" :key="entry.id" class="factory-card" :data-intake="entry.id" :data-state="entry.state">
        <span class="factory-meta">{{ entry.kind === 'question' ? 'The factory asks' : entry.principal }}<template v-if="entry.project">, {{ entry.project }}</template>, {{ entry.state }}</span>
        <span>{{ entry.text }}</span>
      </li>
      <li v-if="!shown.length" class="factory-meta">No message yet.</li>
    </ol>
    <form class="factory-grid" @submit.prevent="send">
      <label :for="`${props.idPrefix}-message`" class="field-label">Message to the factory<template v-if="props.project"> about {{ props.project }}</template></label>
      <VTextArea :id="`${props.idPrefix}-message`" v-model="text" rows="3" :disabled="pending" data-testid="message-text" />
      <div class="factory-actions">
        <VButton type="submit" label="Send message" pending-label="Sending" :pending="pending" :disabled="!text.trim()" data-testid="message-send" />
      </div>
      <p v-if="answer" class="factory-meta" role="status" data-testid="message-answer" :data-outcome="answer.outcome">
        The intake recorded it: {{ answer.outcome }}<template v-if="answer.proposal_id">, <code class="factory-mono">{{ answer.proposal_id }}</code></template>.
      </p>
      <RefusalNotice v-if="refusal" :refusal="refusal" compact />
    </form>
  </div>
</template>
