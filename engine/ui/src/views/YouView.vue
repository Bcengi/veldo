<script setup lang="ts">
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import ScreenHeader from '@/components/ScreenHeader.vue'
import VButton from '@/components/VButton.vue'
import { useTheme } from '@/composables/useTheme'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const { theme, set } = useTheme()
const busy = ref<'one' | 'all' | null>(null)
const dark = computed({ get: () => theme.value === 'dark', set: (on: boolean) => set(on ? 'dark' : 'light') })
const ends = computed(() => {
  const at = session.view?.expires_at
  return typeof at === 'number' ? new Date(at * 1000).toLocaleString() : null
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
  <section class="screen">
    <ScreenHeader title="You" />
    <div class="you">
      <dl class="facts">
        <div><dt>Member</dt><dd data-testid="you-principal">{{ session.principal }}</dd></div>
        <div><dt>Passkey</dt><dd><code class="break">{{ session.view?.credential_id }}</code></dd></div>
        <div v-if="ends"><dt>Session ends by</dt><dd>{{ ends }}</dd></div>
      </dl>
      <div class="you-row">
        <label for="theme-switch" class="you-row-label">Dark theme</label>
        <ToggleSwitch v-model="dark" input-id="theme-switch" />
      </div>
      <div class="you-actions">
        <VButton label="Sign out" pending-label="Signing out" :pending="busy === 'one'" variant="secondary" block data-testid="sign-out" @click="out(false)" />
        <VButton label="Sign out on every device" pending-label="Signing out everywhere" :pending="busy === 'all'" variant="danger" block @click="out(true)" />
      </div>
    </div>
  </section>
</template>
