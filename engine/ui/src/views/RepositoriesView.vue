<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { readRepositories } from '@/api/reads'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { authorOf, identitiesOf, repositoriesOf } from '@/features/repositories/repositories'
import '@/styles/factory.css'

/** Repositories and identities (VELDO-0131): the Git identities (VELDO-0142: label, author, remote owner, projects
 * root, default visibility) and the repository records (VELDO-0161, VELDO-0143: identity, path, remote, origin
 * created or adopted, state with its named reason), from the API's metadata-only repositories read. Read-only:
 * tables on a desktop, cards on a phone. An identity's credential references are never served. */
const live = useLiveRead(readRepositories, (a) => a.watermark, (a) => (a.items.repository ?? []).length === 0 && !(a.identities ?? []).length)
const desktop = useDesktop()
const identities = computed(() => identitiesOf(live.data.value))
const repositories = computed(() => repositoriesOf(live.data.value))
const tone = (state: string) => (state === 'active' ? 'is-done' : state === 'failed' ? 'is-stop' : 'is-waiting')
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Repositories and identities">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No repository or identity yet"
      empty-body="Git identities appear here once setup records them, and repositories once the factory creates or adopts one."
      loading-label="Loading repositories and identities"
      @retry="live.refresh()"
    >
      <div class="factory-grid" data-testid="repositories">
        <section class="panel" aria-labelledby="identities-title" data-testid="identities">
          <h2 id="identities-title" class="panel-title">Git identities <span class="panel-count">{{ identities.length }}</span></h2>
          <p v-if="!identities.length" class="factory-body factory-meta">No Git identity is recorded yet.</p>
          <div v-else-if="desktop" class="factory-body factory-table-wrap">
            <table class="factory-table" aria-label="Git identities">
              <thead><tr><th scope="col">Label</th><th scope="col">Author</th><th scope="col">Remote owner</th><th scope="col">Projects root</th><th scope="col">Default visibility</th><th scope="col">Repositories</th></tr></thead>
              <tbody>
                <tr v-for="i in identities" :key="i.id" :data-identity="i.id">
                  <td>{{ i.label }}<br /><span class="factory-mono">{{ i.id }}</span></td>
                  <td>{{ authorOf(i) }}</td>
                  <td>{{ i.remote_host }}/{{ i.remote_owner }}</td>
                  <td class="factory-mono">{{ i.projects_root }}</td>
                  <td>{{ i.default_visibility }}</td>
                  <td>{{ i.repositories.length }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <ul v-else class="factory-body factory-list">
            <li v-for="i in identities" :key="i.id" class="factory-card" :data-identity="i.id">
              <span class="factory-card-title">{{ i.label }} <span class="factory-tag">{{ i.default_visibility }}</span></span>
              <dl class="factory-facts">
                <dt>Id</dt><dd class="factory-mono">{{ i.id }}</dd>
                <dt>Author</dt><dd>{{ authorOf(i) }}</dd>
                <dt>Remote owner</dt><dd>{{ i.remote_host }}/{{ i.remote_owner }}</dd>
                <dt>Projects root</dt><dd class="factory-mono">{{ i.projects_root }}</dd>
                <dt>Default visibility</dt><dd>{{ i.default_visibility }}</dd>
                <dt>Repositories</dt><dd>{{ i.repositories.length }}</dd>
              </dl>
            </li>
          </ul>
        </section>
        <section class="panel" aria-labelledby="repos-title" data-testid="repository-list">
          <h2 id="repos-title" class="panel-title">Repositories <span class="panel-count">{{ repositories.length }}</span></h2>
          <p v-if="!repositories.length" class="factory-body factory-meta">No repository is recorded yet.</p>
          <div v-else-if="desktop" class="factory-body factory-table-wrap">
            <table class="factory-table" aria-label="Repositories">
              <thead><tr><th scope="col">Repository</th><th scope="col">Identity</th><th scope="col">Path</th><th scope="col">Remote</th><th scope="col">Origin</th><th scope="col">State</th></tr></thead>
              <tbody>
                <tr v-for="r in repositories" :key="r.id" :data-repository="r.name" :data-state="r.state">
                  <td>{{ r.name }}</td>
                  <td>{{ r.identity || 'not recorded' }}</td>
                  <td class="factory-mono">{{ r.path || 'not recorded' }}</td>
                  <td class="factory-mono">{{ r.remote || 'not recorded' }}</td>
                  <td>{{ r.origin || 'not recorded' }}</td>
                  <td><span class="factory-tag" :class="tone(r.state)">{{ r.state }}</span><template v-if="r.reason"><br /><span data-testid="repository-reason">{{ r.reason }}</span></template></td>
                </tr>
              </tbody>
            </table>
          </div>
          <ul v-else class="factory-body factory-list">
            <li v-for="r in repositories" :key="r.id" class="factory-card" :data-repository="r.name" :data-state="r.state">
              <span class="factory-card-title">{{ r.name }} <span class="factory-tag" :class="tone(r.state)">{{ r.state }}</span></span>
              <dl class="factory-facts">
                <dt>Identity</dt><dd>{{ r.identity || 'not recorded' }}</dd>
                <dt>Path</dt><dd class="factory-mono">{{ r.path || 'not recorded' }}</dd>
                <dt>Remote</dt><dd class="factory-mono">{{ r.remote || 'not recorded' }}</dd>
                <dt>Origin</dt><dd>{{ r.origin || 'not recorded' }}</dd>
                <dt v-if="r.reason">Reason</dt><dd v-if="r.reason" data-testid="repository-reason">{{ r.reason }}</dd>
              </dl>
            </li>
          </ul>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
