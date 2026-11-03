<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { readServer, type StoredServer } from '@/api/mcp'
import { readCatalog } from '@/api/reads'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import { catalogRow, credentialMeta, credentialsOf, headsOf } from '@/features/catalog/catalog'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { useServersStore } from '@/stores/servers'
import '@/styles/factory.css'

/** MCP servers and credentials (VELDO-0131): every server of the catalog (the catalog read's heads), each with its
 * revision history, transport, hosts, read-only tools and the credentials it references, and every credential
 * record, opening VELDO-0159's server form. A credential is shown by label, set at and set by only, from its
 * stored record's metadata; no value is ever served or read. */
const store = useServersStore()
const router = useRouter()
const desktop = useDesktop()
const servers = shallowRef<Record<string, StoredServer[]>>({})

const live = useLiveRead(
  async (signal) => {
    const answer = await readCatalog(signal)
    const found: Record<string, StoredServer[]> = {}
    // Each revision through mcp.read, which serves its environment and header bindings (the catalog read serves
    // those mappings by name only).
    for (const head of headsOf(answer)) {
      const list: StoredServer[] = []
      for (let n = 1; n <= head.revision; n += 1) list.push((await readServer(head.id, n)).server)
      found[head.id] = list
    }
    servers.value = found
    return answer
  },
  (a) => a.watermark,
  (a) => headsOf(a).length === 0 && credentialsOf(a).length === 0,
)
const picked = ref<Record<string, number>>({})
const rows = computed(() => Object.values(servers.value).map((list) => catalogRow(list, picked.value[list[0]?.id ?? ''] ?? null)).filter((r) => r !== null))
const openId = ref('')
const credentials = computed(() => credentialsOf(live.data.value))
const meta = (reference: string) =>
  credentials.value.find((c) => c.reference === reference) ?? credentialMeta(store.credentials, reference)
const when = (seconds: number) => new Date(seconds * 1000).toLocaleString()
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="MCP catalog">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <form class="factory-actions" aria-label="Open a server" @submit.prevent="openId.trim() && router.push({ name: 'server', params: { server: openId.trim() } })">
      <div class="factory-search">
        <label for="catalog-open" class="field-label">Open a server by id</label>
        <input id="catalog-open" v-model="openId" class="factory-select" autocomplete="off" data-testid="catalog-open-id" />
      </div>
      <VButton type="submit" label="Open" variant="secondary" :disabled="!openId.trim()" />
      <RouterLink :to="{ name: 'servers' }" class="vbtn vbtn-secondary" data-testid="catalog-new">New server</RouterLink>
    </form>
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="The catalog is empty"
      empty-body="Servers and their credentials appear here once one is saved. Add a new server above."
      loading-label="Loading the catalog"
      @retry="live.refresh()"
    >
      <div class="factory-grid" data-testid="catalog">
        <div v-if="desktop" class="panel factory-table-wrap">
          <table class="factory-table" aria-label="MCP servers">
            <thead><tr><th scope="col">Server</th><th scope="col">Revision</th><th scope="col">Transport</th><th scope="col">Hosts</th><th scope="col">Read-only tools</th><th scope="col">Credentials</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id" :data-server="row.id" :data-revision="row.revision">
                <td><span class="factory-card-title">{{ row.label }}</span><br /><span class="factory-mono">{{ row.id }}</span></td>
                <td>
                  <label :for="`srv-${row.id}`" class="sr-only">Revision of {{ row.id }}</label>
                  <select :id="`srv-${row.id}`" class="factory-select" :value="row.revision" data-testid="server-revision" @change="picked = { ...picked, [row.id]: Number(($event.target as HTMLSelectElement).value) }">
                    <option v-for="r in row.history" :key="r" :value="r">{{ r }}{{ r === row.history[0] ? ' (current)' : '' }}</option>
                  </select>
                </td>
                <td>{{ row.transport }}<br /><span class="factory-mono">{{ row.target }}</span></td>
                <td>{{ row.hosts.join(', ') }}</td>
                <td>{{ row.readOnlyTools.join(', ') || 'none' }}</td>
                <td>
                  <ul class="factory-list">
                    <li v-for="c in row.credentials" :key="c.reference" :data-credential="c.reference">
                      {{ c.name }} ({{ c.where }}): <template v-if="meta(c.reference)">{{ meta(c.reference)!.label }}, set at {{ when(meta(c.reference)!.setAt) }} by {{ meta(c.reference)!.setBy }}</template><span v-else class="factory-mono">{{ c.reference }}</span>
                    </li>
                    <li v-if="!row.credentials.length">none</li>
                  </ul>
                </td>
                <td><RouterLink :to="{ name: 'server', params: { server: row.id } }" class="vbtn vbtn-secondary vbtn-small" :aria-label="`Edit ${row.label}`" data-testid="server-edit">Edit</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
        <ul v-else class="factory-list">
          <li v-for="row in rows" :key="row.id" class="factory-card" :data-server="row.id" :data-revision="row.revision">
            <span class="factory-card-title">{{ row.label }} <span class="factory-tag">{{ row.transport }}</span></span>
            <div class="factory-search">
              <label :for="`srv-p-${row.id}`" class="field-label">Revision</label>
              <select :id="`srv-p-${row.id}`" class="factory-select" :value="row.revision" data-testid="server-revision" @change="picked = { ...picked, [row.id]: Number(($event.target as HTMLSelectElement).value) }">
                <option v-for="r in row.history" :key="r" :value="r">{{ r }}{{ r === row.history[0] ? ' (current)' : '' }}</option>
              </select>
            </div>
            <dl class="factory-facts">
              <dt>Id</dt><dd class="factory-mono">{{ row.id }}</dd>
              <dt>Target</dt><dd class="factory-mono">{{ row.target }}</dd>
              <dt>Hosts</dt><dd>{{ row.hosts.join(', ') }}</dd>
              <dt>Read-only tools</dt><dd>{{ row.readOnlyTools.join(', ') || 'none' }}</dd>
              <dt>Credentials</dt>
              <dd>
                <span v-for="c in row.credentials" :key="c.reference" :data-credential="c.reference">{{ c.name }}: <template v-if="meta(c.reference)">{{ meta(c.reference)!.label }}, {{ when(meta(c.reference)!.setAt) }}, {{ meta(c.reference)!.setBy }}</template><span v-else class="factory-mono">{{ c.reference }}</span><br /></span>
                <template v-if="!row.credentials.length">none</template>
              </dd>
            </dl>
            <RouterLink :to="{ name: 'server', params: { server: row.id } }" class="vbtn vbtn-secondary vbtn-block" :aria-label="`Edit ${row.label}`" data-testid="server-edit">Edit</RouterLink>
          </li>
        </ul>
        <section class="panel" aria-labelledby="credentials-title" data-testid="credentials">
          <h2 id="credentials-title" class="panel-title">Credentials <span class="panel-count">{{ credentials.length }}</span></h2>
          <p class="factory-body factory-meta">Each credential's record: its label, when and by whom it was set. The value is write-only and never shown.</p>
          <p v-if="!credentials.length" class="factory-body factory-meta">No credential is stored yet.</p>
          <ul v-else class="factory-body factory-list">
            <li v-for="c in credentials" :key="c.reference" class="factory-card" :data-credential-record="c.id">
              <span class="factory-card-title">{{ c.label || c.id }} <span v-if="c.deleted" class="factory-tag is-done">Deleted</span></span>
              <dl class="factory-facts">
                <dt>Id</dt><dd class="factory-mono">{{ c.id }}</dd>
                <dt>Set at</dt><dd>{{ c.setAt ? when(c.setAt) : 'not recorded' }}</dd>
                <dt>Set by</dt><dd>{{ c.setBy || 'not recorded' }}</dd>
              </dl>
            </li>
          </ul>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
