<script setup lang="ts">
import { computed, reactive, ref, shallowRef } from 'vue'
import { saveServer, type StoredServer } from '@/api/mcp'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import VTextArea from '@/components/VTextArea.vue'
import VTextField from '@/components/VTextField.vue'
import { useServersStore } from '@/stores/servers'
import CredentialField from './CredentialField.vue'
import { emptyDraft, fromStored, toDefinition, type BindingRow } from './definition'

/**
 * The MCP server form (VELDO-0159 AC1): one server and its credential fields. Every save goes to the catalog route
 * as a new revision, carrying the revision the form was edited from; a save edited from an older revision is
 * refused stale and stores nothing, and the refusal is shown beside the save action.
 */
const props = defineProps<{ server: StoredServer | null }>()
const emit = defineEmits<{ saved: [server: StoredServer]; reload: [] }>()
const store = useServersStore()

const draft = reactive(props.server ? fromStored(props.server) : emptyDraft())
/** The revision this form was edited from: 0 for a new server. */
const editedFrom = ref(props.server?.revision ?? 0)
const pending = ref(false)
const refusal = shallowRef<ApiRefusal | null>(null)
const saved = ref<number | null>(null)
const stale = computed(() => refusal.value?.error === 'stale_version')
const newCredential = ref('')
const added = ref<string[]>([])
const credentialProblem = ref<string | null>(null)

/** The credentials this form manages: those written from the form in this session and those added here. */
const credentialIds = computed(() => [...new Set([...Object.keys(store.credentials), ...added.value])])
/** The references a variable or header can name: the live credentials, and a reference already in the revision. */
function referenceOptions(current: string) {
  const known = Object.values(store.credentials)
    .filter((c) => !c.deleted)
    .map((c) => ({ value: c.reference, text: `${c.id} (${c.label})` }))
  if (current && !known.some((k) => k.value === current)) known.push({ value: current, text: current })
  return known
}

function addRow(list: BindingRow[], kind: BindingRow['kind']) {
  list.push({ name: '', kind, value: '' })
}

function addCredential() {
  const id = newCredential.value.trim()
  credentialProblem.value = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(id) ? null : 'A credential id is letters, digits, dot, dash or underscore.'
  if (credentialProblem.value) return
  if (!credentialIds.value.includes(id)) added.value.push(id)
  newCredential.value = ''
}

async function save() {
  refusal.value = null
  saved.value = null
  pending.value = true
  try {
    const definition = toDefinition(draft)
    const answer = await saveServer(definition, editedFrom.value)
    editedFrom.value = answer.revision
    saved.value = answer.revision
    emit('saved', { ...definition, revision: answer.revision })
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <form class="server-form" data-testid="server-form" :data-edited-from="editedFrom" @submit.prevent="save">
    <section class="panel server-section" aria-labelledby="server-identity">
      <h2 id="server-identity" class="panel-title">Server</h2>
      <div class="server-grid">
        <label for="server-id" class="field-label">Id</label>
        <VTextField id="server-id" v-model="draft.id" :disabled="editedFrom > 0" maxlength="128" spellcheck="false" data-testid="server-id" />
        <label for="server-label" class="field-label">Label</label>
        <VTextField id="server-label" v-model="draft.label" maxlength="200" data-testid="server-label" />
        <label for="server-transport" class="field-label">Transport</label>
        <select id="server-transport" v-model="draft.transport" class="vfield" data-testid="server-transport">
          <option value="stdio">stdio (a command on the host)</option>
          <option value="http">http (a URL)</option>
        </select>
        <template v-if="draft.transport === 'stdio'">
          <label for="server-command" class="field-label">Command</label>
          <VTextField id="server-command" v-model="draft.command" spellcheck="false" data-testid="server-command" />
          <label for="server-arguments" class="field-label">Arguments, one per line</label>
          <VTextArea id="server-arguments" v-model="draft.argumentsText" spellcheck="false" data-testid="server-arguments" />
        </template>
        <template v-else>
          <label for="server-url" class="field-label">URL</label>
          <VTextField id="server-url" v-model="draft.url" type="url" spellcheck="false" data-testid="server-url" />
        </template>
        <label for="server-hosts" class="field-label">Hosts it can run on, one per line</label>
        <VTextArea id="server-hosts" v-model="draft.hostsText" spellcheck="false" data-testid="server-hosts" />
        <label for="server-tools" class="field-label">Read-only tools, one per line</label>
        <VTextArea id="server-tools" v-model="draft.toolsText" spellcheck="false" data-testid="server-tools" />
      </div>
    </section>

    <section class="panel server-section" aria-labelledby="server-credentials">
      <h2 id="server-credentials" class="panel-title">Credentials</h2>
      <div class="server-credentials">
        <CredentialField v-for="id in credentialIds" :key="id" :credential-id="id" />
        <div class="server-add">
          <label for="credential-new" class="field-label">New credential id</label>
          <div class="server-add-row">
            <VTextField id="credential-new" v-model="newCredential" spellcheck="false" data-testid="credential-new" @keydown.enter.prevent="addCredential" />
            <VButton label="Add credential" variant="secondary" data-testid="credential-add" @click="addCredential" />
          </div>
          <p v-if="credentialProblem" class="form-problem" role="alert">{{ credentialProblem }}</p>
        </div>
      </div>
    </section>

    <section class="panel server-section" aria-labelledby="server-environment">
      <h2 id="server-environment" class="panel-title">Environment</h2>
      <ul class="binding-list">
        <li v-for="(row, i) in draft.environment" :key="i" class="binding-row" data-testid="environment-row">
          <label :for="`env-name-${i}`" class="sr-only">Variable name</label>
          <VTextField :id="`env-name-${i}`" v-model="row.name" placeholder="NAME" spellcheck="false" data-testid="binding-name" />
          <label :for="`env-kind-${i}`" class="sr-only">Kind of value</label>
          <select :id="`env-kind-${i}`" v-model="row.kind" class="vfield" data-testid="binding-kind" @change="row.value = ''">
            <option value="literal">Literal</option>
            <option value="reference">Credential</option>
          </select>
          <label :for="`env-value-${i}`" class="sr-only">{{ row.kind === 'literal' ? 'Value' : 'Credential' }}</label>
          <VTextField v-if="row.kind === 'literal'" :id="`env-value-${i}`" v-model="row.value" spellcheck="false" data-testid="binding-value" />
          <select v-else :id="`env-value-${i}`" v-model="row.value" class="vfield" data-testid="binding-reference">
            <option value="" disabled>Pick a credential</option>
            <option v-for="o in referenceOptions(row.value)" :key="o.value" :value="o.value">{{ o.text }}</option>
          </select>
          <VButton label="Remove" variant="quiet" size="small" @click="draft.environment.splice(i, 1)" />
        </li>
      </ul>
      <div class="binding-add"><VButton label="Add variable" variant="secondary" data-testid="environment-add" @click="addRow(draft.environment, 'literal')" /></div>
    </section>

    <section v-if="draft.transport === 'http'" class="panel server-section" aria-labelledby="server-headers">
      <h2 id="server-headers" class="panel-title">Headers</h2>
      <ul class="binding-list">
        <li v-for="(row, i) in draft.headers" :key="i" class="binding-row binding-row-header" data-testid="header-row">
          <label :for="`header-name-${i}`" class="sr-only">Header name</label>
          <VTextField :id="`header-name-${i}`" v-model="row.name" placeholder="Header" spellcheck="false" data-testid="binding-name" />
          <label :for="`header-value-${i}`" class="sr-only">Credential</label>
          <select :id="`header-value-${i}`" v-model="row.value" class="vfield" data-testid="binding-reference">
            <option value="" disabled>Pick a credential</option>
            <option v-for="o in referenceOptions(row.value)" :key="o.value" :value="o.value">{{ o.text }}</option>
          </select>
          <VButton label="Remove" variant="quiet" size="small" @click="draft.headers.splice(i, 1)" />
        </li>
      </ul>
      <div class="binding-add"><VButton label="Add header" variant="secondary" data-testid="header-add" @click="addRow(draft.headers, 'reference')" /></div>
    </section>

    <div class="server-save">
      <p class="server-revision" data-testid="server-revision">{{ editedFrom > 0 ? `Editing revision ${editedFrom}` : 'A new server' }}</p>
      <div v-if="saved !== null" class="server-saved" role="status" data-testid="server-saved">Saved as revision {{ saved }}</div>
      <RefusalNotice v-if="refusal" :refusal="refusal" compact data-action="save">
        <VButton v-if="stale" label="Load the current revision" variant="secondary" size="small" data-testid="server-reload" @click="emit('reload')" />
      </RefusalNotice>
      <VButton type="submit" label="Save server" pending-label="Saving" :pending="pending" block data-testid="server-save" />
    </div>
  </form>
</template>
