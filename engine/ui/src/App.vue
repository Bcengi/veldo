<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import UApp from '@nuxt/ui/components/App.vue'
import AppShell from '@/app/AppShell.vue'
import { useSessionStore } from '@/stores/session'

/** Before sign-in only the sign-in screen exists: no navigation, no shell, no factory data. UApp is Nuxt UI's
 * root (its tooltip and overlay providers); the UI shows no toasts, so its toaster is off. */
const route = useRoute()
const session = useSessionStore()
const bare = computed(() => session.status !== 'signed-in' || route.name === 'sign-in')
</script>

<template>
  <UApp :toaster="null">
    <RouterView v-if="bare" />
    <AppShell v-else />
  </UApp>
</template>
