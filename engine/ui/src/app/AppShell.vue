<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import UAvatar from '@nuxt/ui/components/Avatar.vue'
import UBadge from '@nuxt/ui/components/Badge.vue'
import UIcon from '@nuxt/ui/components/Icon.vue'
import USwitch from '@nuxt/ui/components/Switch.vue'
import Lamp from '@/components/Lamp.vue'
import Wordmark from '@/components/Wordmark.vue'
import { useTheme } from '@/composables/useTheme'
import { factoryCounts } from '@/features/overview/overview'
import { useDecisionsStore } from '@/stores/decisions'
import { useRunsStore } from '@/stores/runs'
import { useSessionStore } from '@/stores/session'
import { useNavigation } from './navigation'

/** The signed-in shell: on desktop a restrained sidebar with the factory's identity, the destinations, the hosts
 * and their activity, the appearance switch and the account; on a phone a bottom bar with the same destinations.
 * The screen fills the rest. */
const route = useRoute()
const nav = useNavigation()
const session = useSessionStore()
const decisions = useDecisionsStore()
const runs = useRunsStore()
const { theme, set } = useTheme()
const dark = computed({ get: () => theme.value === 'dark', set: (on: boolean) => set(on ? 'dark' : 'light') })
const current = (matches: string[]) => matches.includes(String(route.name ?? ''))
const phoneNav = computed(() => nav.value.filter((n) => n.phone))
const hosts = computed(() => (runs.state === 'ready' ? factoryCounts(runs.rows, null, 0).hosts : []))
const initials = computed(() => (session.principal ?? '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '?')
// The decisions badge and the hosts are live from the first screen, not only once their screens open.
onMounted(() => {
  if (decisions.state === 'idle') void decisions.refresh()
  if (runs.state === 'idle') void runs.refresh()
})
</script>

<template>
  <div class="shell">
    <a href="#main" class="skip-link">Skip to content</a>
    <nav class="rail" aria-label="Main">
      <div class="rail-head">
        <RouterLink :to="{ name: 'overview' }" class="rail-brand" aria-label="Veldo overview"><Wordmark /></RouterLink>
        <p class="rail-factory"><span class="rail-factory-word">Factory</span> <span data-testid="factory-name" class="rail-factory-name">{{ session.domain }}</span></p>
      </div>
      <ul class="rail-list">
        <li v-for="entry in nav" :key="entry.id">
          <RouterLink :to="entry.to" class="rail-link" :aria-current="current(entry.matches) ? 'page' : undefined" :data-nav="entry.id">
            <UIcon :name="entry.glyph" class="rail-icon" />
            <span class="rail-label">{{ entry.label }}</span>
            <UBadge
              v-if="entry.badge?.()"
              class="badge"
              :class="`badge-${entry.badge()!.tone}`"
              :aria-label="entry.badge()!.label"
              :label="String(entry.badge()!.count)"
              :color="entry.badge()!.tone === 'stop' ? 'error' : 'warning'"
              variant="solid"
              size="sm"
            />
          </RouterLink>
        </li>
      </ul>
      <section v-if="hosts.length" class="rail-hosts" aria-labelledby="rail-hosts-title">
        <h2 id="rail-hosts-title" class="rail-section">Hosts</h2>
        <ul>
          <li v-for="host in hosts" :key="host.name" class="rail-host">
            <Lamp :state="host.running ? 'live' : 'off'" :label="host.running ? 'Running' : 'Idle'" size="sm" />
            <span class="rail-host-name">{{ host.name }}</span>
            <span class="rail-host-load">{{ host.running ? `${host.running} running` : 'idle' }}</span>
          </li>
        </ul>
      </section>
      <div class="rail-foot">
        <USwitch v-model="dark" label="Dark appearance" class="rail-appearance" data-testid="appearance" checked-icon="i-lucide-moon" unchecked-icon="i-lucide-sun" />
        <RouterLink :to="{ name: 'you' }" class="rail-account">
          <UAvatar :text="initials" alt="" size="md" class="rail-avatar" aria-hidden="true" />
          <span class="rail-who" data-testid="principal">Signed in as <strong>{{ session.principal }}</strong></span>
        </RouterLink>
      </div>
    </nav>
    <main id="main" class="shell-main">
      <RouterView />
    </main>
    <nav class="bottombar" aria-label="Main">
      <RouterLink
        v-for="entry in phoneNav"
        :key="entry.id"
        :to="entry.to"
        class="bottombar-link"
        :aria-current="current(entry.matches) ? 'page' : undefined"
        :data-nav="entry.id"
      >
        <span class="bottombar-icon">
          <UIcon :name="entry.glyph" class="bottombar-glyph" />
          <span v-if="entry.badge?.()" class="badge badge-on-icon" :class="`badge-${entry.badge()!.tone}`" :aria-label="entry.badge()!.label">{{ entry.badge()!.count }}</span>
        </span>
        <span>{{ entry.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
