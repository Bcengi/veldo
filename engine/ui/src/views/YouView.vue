<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
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
      <section class="panel you-account" aria-labelledby="you-account">
        <h2 id="you-account" class="panel-title">Signed in</h2>
        <dl class="facts">
          <div><dt>Member</dt><dd data-testid="you-principal">{{ session.principal }}</dd></div>
          <div><dt>Factory</dt><dd>{{ session.domain }}</dd></div>
          <div v-if="ends"><dt>Session ends by</dt><dd>{{ ends }}</dd></div>
          <div v-if="session.view?.credential_id"><dt>Passkey</dt><dd><CopyId :value="session.view.credential_id" label="passkey id" /></dd></div>
        </dl>
      </section>
      <!-- VELDO-0163: the role and team forms, which the phone's bottom bar has no room for. -->
      <section class="panel you-setup" aria-labelledby="you-setup">
        <h2 id="you-setup" class="panel-title">Factory setup</h2>
        <nav class="you-actions" aria-label="Factory setup">
          <RouterLink :to="{ name: 'role' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-roles">Roles</RouterLink>
          <RouterLink :to="{ name: 'team' }" class="vbtn vbtn-secondary vbtn-block" data-testid="you-team">Team</RouterLink>
        </nav>
      </section>
      <section class="panel you-device" aria-labelledby="you-device">
        <h2 id="you-device" class="panel-title">This device</h2>
        <div class="you-row">
          <label for="theme-switch" class="you-row-label">Dark theme</label>
          <VSwitch v-model="dark" input-id="theme-switch" />
        </div>
        <div class="you-actions">
          <VButton label="Sign out" pending-label="Signing out" :pending="busy === 'one'" variant="secondary" block data-testid="sign-out" @click="out(false)" />
          <VButton label="Sign out on every device" pending-label="Signing out everywhere" :pending="busy === 'all'" variant="danger" block @click="out(true)" />
        </div>
      </section>
    </div>
  </section>
</template>
