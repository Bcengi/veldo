<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { readServer, type StoredServer } from '@/api/mcp'
import { ApiRefusal } from '@/api/refusal'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import VTextField from '@/components/VTextField.vue'
import type { AsyncState } from '@/composables/useAsync'
import ServerForm from '@/features/servers/ServerForm.vue'

/** The MCP server form: a new server at /servers, a saved one at /servers/<id> opened at its latest revision. */
const route = useRoute()
const router = useRouter()
const id = computed(() => (typeof route.params.server === 'string' ? route.params.server : ''))
const state = ref<AsyncState>('ready')
const refusal = shallowRef<ApiRefusal | null>(null)
const server = shallowRef<StoredServer | null>(null)
/** Bumped to give the form a fresh start from what was loaded. */
const generation = ref(0)
const opening = ref('')

/** The latest revision of `server`: revisions are numbered from 1 with no gaps, so read upward until the catalog
 * route answers that the next one does not exist. */
async function latest(name: string): Promise<StoredServer | null> {
  let found: StoredServer | null = null
  for (let revision = 1; ; revision++) {
    try {
      found = (await readServer(name, revision)).server
    } catch (error) {
      if (error instanceof ApiRefusal && error.refusal === 'missing_evidence:mcp_server') return found
      throw error
    }
  }
}

async function load() {
  server.value = null
  refusal.value = null
  if (!id.value) {
    state.value = 'ready'
    generation.value++
    return
  }
  state.value = 'loading'
  try {
    server.value = await latest(id.value)
    state.value = server.value ? 'ready' : 'empty'
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
    state.value = 'error'
  }
  generation.value++
}

function saved(stored: StoredServer) {
  server.value = stored
  if (stored.id !== id.value) void router.replace({ name: 'server', params: { server: stored.id } })
}

function open() {
  const name = opening.value.trim()
  if (name) void router.push({ name: 'server', params: { server: name } })
  opening.value = ''
}

watch(id, (now, was) => {
  // A save of a new server moves to its own address; the form already holds what it saved.
  if (was === '' && server.value?.id === now) return
  void load()
}, { immediate: true })
</script>

<template>
  <section class="screen screen-narrow">
    <ScreenHeader :title="id ? `MCP server ${id}` : 'New MCP server'" :back="id ? { to: { name: 'servers' }, label: 'New server' } : undefined">
      <p class="screen-meta-text">A server is defined once here; each save is a new catalog revision. Credentials are write-only.</p>
    </ScreenHeader>
    <form class="server-open" @submit.prevent="open">
      <label for="server-open" class="field-label">Open a saved server by id</label>
      <div class="server-add-row">
        <VTextField id="server-open" v-model="opening" spellcheck="false" data-testid="server-open" />
        <VButton type="submit" label="Open" variant="secondary" data-testid="server-open-go" />
      </div>
    </form>
    <StatePanel
      :state="state"
      :refusal="refusal"
      empty-title="No such server"
      :empty-body="`The catalog has no revision of ${id}. Open a new server to define it.`"
      loading-label="Loading the server"
      shape="block"
      @retry="load()"
    >
      <ServerForm :key="generation" :server="server" @saved="saved" @reload="load()" />
    </StatePanel>
  </section>
</template>
