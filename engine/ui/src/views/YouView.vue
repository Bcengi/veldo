<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import UAvatar from '@nuxt/ui/components/Avatar.vue'
import UCard from '@nuxt/ui/components/Card.vue'
import CopyId from '@/components/CopyId.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import VButton from '@/components/VButton.vue'
import VSwitch from '@/components/VSwitch.vue'
import { useTheme } from '@/composables/useTheme'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const { theme, set } = useTheme()
const busy = ref<'one' | 'all' | null>(null)
const initials = computed(() => (session.principal ?? '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '?')
const dark = computed({ get: () => theme.value === 'dark', set: (on: boolean) => set(on ? 'dark' : 'light') })
const ends = computed(() => {
  const at = session.view?.expires_at
  return typeof at === 'number' ? new Date(at * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : null
})

async function out(everywhere: boolean) {
  busy.value = everywhere ? 'all' : 'one'
  try {
    await session.signOut(everywhere)
  } finally {
    busy.value = null
    await router.replace({ name: 'sign-in' })
  }
}
</script>

<template>
  <section class="screen screen-narrow">
    <ScreenHeader title="You" />
    <div class="you">
      <UCard as="section" class="you-account" aria-labelledby="you-account" :ui="{ body: 'p-5 sm:p-6' }">
        <h2 id="you-account" class="eyebrow you-title">Signed in</h2>
        <div class="you-identity">
          <UAvatar :text="initials" alt="" size="xl" class="you-avatar" aria-hidden="true" />
          <p class="you-name">{{ session.principal }}</p>
        </div>
        <dl class="facts">
          <div><dt>Member</dt><dd data-testid="you-principal">{{ session.principal }}</dd></div>
          <div><dt>Factory</dt><dd>{{ session.domain }}</dd></div>
          <div v-if="ends"><dt>Session ends by</dt><dd>{{ ends }}</dd></div>
          <div v-if="session.view?.credential_id"><dt>Passkey</dt><dd><CopyId :value="session.view.credential_id" label="passkey id" /></dd></div>
        </dl>
      </UCard>
      <!-- VELDO-0159 and VELDO-0163: the server, role and team forms, which the phone's bottom bar has no room for. -->
      <UCard as="section" class="you-setup" aria-labelledby="you-setup" :ui="{ body: 'p-5 sm:p-6' }">
        <h2 id="you-setup" class="eyebrow you-title">Factory setup</h2>
        <nav class="you-actions" aria-label="Factory setup">
          <RouterLink :to="{ name: 'servers' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-servers">MCP servers and credentials</RouterLink>
          <RouterLink :to="{ name: 'role' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-roles">Roles</RouterLink>
          <RouterLink :to="{ name: 'team' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-team">Team</RouterLink>
        </nav>
      </UCard>
      <!-- VELDO-0131: the factory screens the phone's bottom bar has no room for. -->
      <UCard as="section" class="you-setup" aria-labelledby="you-factory" :ui="{ body: 'p-5 sm:p-6' }">
        <h2 id="you-factory" class="eyebrow you-title">Factory</h2>
        <nav class="you-actions" aria-label="Factory">
          <RouterLink :to="{ name: 'project' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-projects">Projects</RouterLink>
          <RouterLink :to="{ name: 'backlog' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-backlog">Backlog</RouterLink>
          <RouterLink :to="{ name: 'workers' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-workers">Workers</RouterLink>
          <RouterLink :to="{ name: 'proof' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-proof">Gate and review</RouterLink>
          <RouterLink :to="{ name: 'usage' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-usage">Usage</RouterLink>
          <RouterLink :to="{ name: 'configuration' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-configuration">Configuration</RouterLink>
          <RouterLink :to="{ name: 'catalog' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-catalog">MCP catalog</RouterLink>
          <RouterLink :to="{ name: 'repositories' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-repositories">Repositories and identities</RouterLink>
          <RouterLink :to="{ name: 'workflow' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-workflows">Workflows</RouterLink>
        </nav>
      </UCard>
      <UCard as="section" class="you-device" aria-labelledby="you-device" :ui="{ body: 'p-5 sm:p-6' }">
        <h2 id="you-device" class="eyebrow you-title">Appearance and this device</h2>
        <div class="you-row">
          <label for="theme-switch" class="you-row-label">Dark theme</label>
          <VSwitch v-model="dark" input-id="theme-switch" />
        </div>
        <div class="you-actions">
          <VButton label="Sign out" pending-label="Signing out" :pending="busy === 'one'" variant="secondary" block data-testid="sign-out" @click="out(false)" />
          <VButton label="Sign out on every device" pending-label="Signing out everywhere" :pending="busy === 'all'" variant="danger" block @click="out(true)" />
        </div>
      </UCard>
    </div>
  </section>
</template>
