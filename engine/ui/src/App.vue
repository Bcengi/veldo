<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '@/app/AppShell.vue'
import { useSessionStore } from '@/stores/session'

/** Before sign-in only the sign-in screen exists: no navigation, no shell, no factory data. */
const route = useRoute()
const session = useSessionStore()
const bare = computed(() => session.status !== 'signed-in' || route.name === 'sign-in')
</script>

<template>
  <RouterView v-if="bare" />
  <AppShell v-else />
</template>
