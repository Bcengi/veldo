<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import { deleteCredential, setCredential } from '@/api/mcp'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import VTextField from '@/components/VTextField.vue'
import { useServersStore } from '@/stores/servers'
import { useSessionStore } from '@/stores/session'

/**
 * One credential's write-only field (VELDO-0159 AC2). A value typed here goes once, in the body of one request to
 * the credential route, and is cleared from the field as that request leaves; it is never shown, kept or read back.
 * What the field shows afterwards is the credential's label, set at and set by, from the route's answer and the
 * session, since the API refuses every read-back. A refusal is shown beside the action it concerns.
 */
const props = defineProps<{ credentialId: string }>()
const store = useServersStore()
const session = useSessionStore()
const meta = computed(() => store.credentials[props.credentialId] ?? null)
const label = ref(meta.value?.label ?? '')
/** The typed value while it is being typed. Emptied before the request is sent, on success and on refusal. */
const value = ref('')
const pending = ref<'set' | 'delete' | null>(null)
const refusal = shallowRef<{ action: 'set' | 'delete'; refusal: ApiRefusal } | null>(null)
const problem = ref<string | null>(null)
const live = computed(() => !!meta.value && !meta.value.deleted)
const field = computed(() => `credential-${props.credentialId}`)
const setAt = computed(() => (meta.value ? new Date(meta.value.setAt * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' }) : ''))

function failed(action: 'set' | 'delete', error: unknown) {
  refusal.value = { action, refusal: error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable') }
}

async function write() {
  refusal.value = null
  problem.value = null
  if (!label.value.trim()) return void (problem.value = 'Give the credential a label.')
  if (!value.value) return void (problem.value = 'Type the value to store.')
  const typed = value.value
  value.value = ''
  pending.value = 'set'
  try {
    const answer = await setCredential(props.credentialId, label.value.trim(), meta.value?.version ?? 0, typed)
    store.recordCredential({ id: answer.id, label: label.value.trim(), setAt: Date.now() / 1000, setBy: session.principal ?? '', reference: answer.reference, version: answer.version, deleted: false })
  } catch (error) {
    failed('set', error)
  } finally {
    pending.value = null
  }
}

async function remove() {
  const known = meta.value
  if (!known) return
  refusal.value = null
  problem.value = null
  value.value = ''
  pending.value = 'delete'
  try {
    const answer = await deleteCredential(props.credentialId, known.version)
    store.recordCredential({ ...known, setAt: Date.now() / 1000, setBy: session.principal ?? '', version: answer.version, deleted: true })
  } catch (error) {
    failed('delete', error)
  } finally {
    pending.value = null
  }
}
</script>

<template>
  <section class="credential" data-testid="credential" :data-credential="props.credentialId" :aria-labelledby="`${field}-title`">
    <h3 :id="`${field}-title`" class="credential-title"><code>{{ props.credentialId }}</code></h3>
    <dl v-if="meta" class="facts credential-facts" data-testid="credential-meta">
      <div><dt>Label</dt><dd data-testid="credential-label">{{ meta.label }}</dd></div>
      <div><dt>{{ meta.deleted ? 'Deleted at' : 'Set at' }}</dt><dd data-testid="credential-set-at" :data-set-at="meta.setAt">{{ setAt }}</dd></div>
      <div><dt>{{ meta.deleted ? 'Deleted by' : 'Set by' }}</dt><dd data-testid="credential-set-by">{{ meta.setBy }}</dd></div>
    </dl>
    <p v-else class="credential-note">No value set from this form yet.</p>
    <div class="credential-fields">
      <label :for="`${field}-label`" class="field-label">Label</label>
      <VTextField :id="`${field}-label`" v-model="label" maxlength="200" data-testid="credential-label-input" @keydown.enter.prevent="write" />
      <label :for="`${field}-value`" class="field-label">{{ live ? 'New value' : 'Value' }}</label>
      <VTextField
        :id="`${field}-value`"
        v-model="value"
        type="password"
        autocomplete="new-password"
        spellcheck="false"
        :aria-describedby="`${field}-help`"
        data-testid="credential-value"
        @keydown.enter.prevent="write"
      />
      <p :id="`${field}-help`" class="credential-note">Write-only: the value goes once to the keystore and is never shown again.</p>
    </div>
    <p v-if="problem" class="form-problem" role="alert">{{ problem }}</p>
    <div class="credential-actions">
      <VButton :label="live ? 'Replace value' : 'Set value'" :pending-label="live ? 'Replacing' : 'Setting'" :pending="pending === 'set'" :disabled="pending !== null" data-testid="credential-set" @click="write" />
      <VButton v-if="live" label="Delete value" pending-label="Deleting" variant="danger" :pending="pending === 'delete'" :disabled="pending !== null" data-testid="credential-delete" @click="remove" />
    </div>
    <RefusalNotice v-if="refusal" :refusal="refusal.refusal" compact :data-action="refusal.action" />
  </section>
</template>
