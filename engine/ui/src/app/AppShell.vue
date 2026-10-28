<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Icon from '@/components/Icon.vue'
import Lamp from '@/components/Lamp.vue'
import Wordmark from '@/components/Wordmark.vue'
import { useTheme } from '@/composables/useTheme'
import { useDecisionsStore } from '@/stores/decisions'
import { useSessionStore } from '@/stores/session'
import { useNavigation } from './navigation'

/** The signed-in shell: a rail on desktop, a bottom bar on phone, and the screen. */
const route = useRoute()
const nav = useNavigation()
const session = useSessionStore()
const decisions = useDecisionsStore()
const { theme, toggle } = useTheme()
const current = (matches: string[]) => matches.includes(String(route.name ?? ''))
const phoneNav = computed(() => nav.value.filter((n) => n.phone))
// The decisions lamp in the navigation is live from the first screen, not only once decisions open.
onMounted(() => {
  if (decisions.state === 'idle') void decisions.refresh()
})
</script>

<template>
  <div class="shell">
    <a href="#main" class="skip-link">Skip to content</a>
    <nav class="rail" aria-label="Main">
      <RouterLink to="/runs" class="rail-brand" aria-label="Veldo home"><Wordmark /></RouterLink>
      <ul class="rail-list">
        <li v-for="entry in nav" :key="entry.id">
          <RouterLink :to="entry.to" class="rail-link" :aria-current="current(entry.matches) ? 'page' : undefined" :data-nav="entry.id">
            <Icon :name="entry.icon" />
            <span class="rail-label">{{ entry.label }}</span>
            <span v-if="entry.signal?.()" class="nav-signal">
              <Lamp :state="entry.signal()!.state" :label="entry.signal()!.label" size="sm" />
              <span class="nav-count">{{ entry.signal()!.count }}</span>
            </span>
          </RouterLink>
        </li>
      </ul>
      <div class="rail-foot">
        <button type="button" class="rail-theme" :aria-label="theme === 'dark' ? 'Use light theme' : 'Use dark theme'" @click="toggle">
          <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="20" />
          <span>{{ theme === 'dark' ? 'Light theme' : 'Dark theme' }}</span>
        </button>
        <p class="rail-who" data-testid="principal"><span class="rail-who-label">Signed in as</span> {{ session.principal }}</p>
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
          <Icon :name="entry.icon" />
          <Lamp v-if="entry.signal?.()" :state="entry.signal()!.state" :label="entry.signal()!.label" size="sm" class="bottombar-lamp" />
        </span>
        <span>{{ entry.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
