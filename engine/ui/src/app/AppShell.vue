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
import { useNavigation, type NavEntry } from './navigation'
import { useRail } from './rail'

/** The signed-in shell (VELDO-0229, Telegram 38255): on desktop a narrow icon rail, its destinations grouped by
 * subtle separators and the account avatar at the bottom, which the panel toggle in each screen's top bar expands
 * to the labeled sidebar with the factory's identity, the hosts and their activity, the appearance switch and the
 * account (38234); on a phone a bottom bar with the same destinations. The screen fills the rest. */
const route = useRoute()
const nav = useNavigation()
const session = useSessionStore()
const decisions = useDecisionsStore()
const runs = useRunsStore()
const { expanded } = useRail()
const { theme, set } = useTheme()
const dark = computed({ get: () => theme.value === 'dark', set: (on: boolean) => set(on ? 'dark' : 'light') })
const current = (matches: string[]) => matches.includes(String(route.name ?? ''))
const phoneNav = computed(() => nav.value.filter((n) => n.phone))
/** The rail's groups in order; You is the account footer's avatar, not a list entry. */
const groups = computed(() => {
  const out: NavEntry[][] = []
  for (const g of ['operate', 'factory', 'setup'] as const) {
    const entries = nav.value.filter((n) => n.group === g && n.id !== 'you')
    if (entries.length) out.push(entries)
  }
  return out
})
const hosts = computed(() => (runs.state === 'ready' ? factoryCounts(runs.rows, null, 0).hosts : []))
const initials = computed(() => (session.principal ?? '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '?')
// The decisions badge and the hosts are live from the first screen, not only once their screens open.
onMounted(() => {
  if (decisions.state === 'idle') void decisions.refresh()
  if (runs.state === 'idle') void runs.refresh()
})
</script>

<template>
  <div class="shell" :class="{ 'is-expanded': expanded }">
    <a href="#main" class="skip-link">Skip to content</a>
    <nav id="rail" class="rail" :class="{ 'is-expanded': expanded }" aria-label="Main">
      <div class="rail-head">
        <RouterLink :to="{ name: 'overview' }" class="rail-brand" aria-label="Veldo overview">
          <Wordmark v-if="expanded" />
          <Lamp v-else state="here" label="" size="sm" class="rail-mark" aria-hidden="true" />
        </RouterLink>
        <p class="rail-factory" :class="{ 'sr-only': !expanded }"><span class="rail-factory-word">Factory</span> <span data-testid="factory-name" class="rail-factory-name">{{ session.domain }}</span></p>
      </div>
      <ul v-for="(entries, g) in groups" :key="g" class="rail-list">
        <li v-for="entry in entries" :key="entry.id">
          <RouterLink
            :to="entry.to"
            class="rail-link"
            :aria-current="current(entry.matches) ? 'page' : undefined"
            :data-nav="entry.id"
            :title="expanded ? undefined : entry.label"
          >
            <span class="rail-icon-box">
              <UIcon :name="entry.glyph" class="rail-icon" />
              <span v-if="!expanded && entry.badge?.()" class="badge badge-on-icon" :class="`badge-${entry.badge()!.tone}`" :aria-label="entry.badge()!.label">{{ entry.badge()!.count }}</span>
            </span>
            <span class="rail-label" :class="{ 'sr-only': !expanded }">{{ entry.label }}</span>
            <UBadge
              v-if="expanded && entry.badge?.()"
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
      <section v-if="expanded && hosts.length" class="rail-hosts" aria-labelledby="rail-hosts-title">
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
        <USwitch
          v-model="dark"
          label="Dark appearance"
          class="rail-appearance"
          :ui="{ wrapper: expanded ? '' : 'sr-only' }"
          data-testid="appearance"
          checked-icon="i-lucide-moon"
          unchecked-icon="i-lucide-sun"
          :title="expanded ? undefined : 'Dark appearance'"
        />
        <RouterLink
          :to="{ name: 'you' }"
          class="rail-account"
          data-nav="you"
          :aria-current="current(['you']) ? 'page' : undefined"
          :title="expanded ? undefined : `Signed in as ${session.principal}`"
        >
          <UAvatar :text="initials" alt="" size="sm" class="rail-avatar" aria-hidden="true" />
          <span class="rail-who" :class="{ 'sr-only': !expanded }" data-testid="principal">Signed in as <strong>{{ session.principal }}</strong></span>
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
