<script setup lang="ts">
import type { ApiRefusal } from '@/api/refusal'
import type { AsyncState } from '@/composables/useAsync'
import RefusalNotice from './RefusalNotice.vue'

/** One screen region's loading, empty, error and ready states. Exactly one is rendered. */
const props = withDefaults(
  defineProps<{
    state: AsyncState
    refusal?: ApiRefusal | null
    emptyTitle?: string
    emptyBody?: string
    loadingLabel?: string
    rows?: number
  }>(),
  { refusal: null, emptyTitle: 'Nothing here yet', emptyBody: '', loadingLabel: 'Loading', rows: 4 },
)
</script>

<template>
  <div v-if="props.state === 'loading' || props.state === 'idle'" class="state-loading" role="status" :aria-label="props.loadingLabel" data-state="loading">
    <span v-for="n in props.rows" :key="n" class="skeleton" :style="{ width: `${92 - ((n * 17) % 40)}%` }" />
  </div>
  <div v-else-if="props.state === 'error' && props.refusal" class="state-error" data-state="error">
    <RefusalNotice :refusal="props.refusal"><slot name="error-actions" /></RefusalNotice>
  </div>
  <div v-else-if="props.state === 'empty'" class="state-empty" data-state="empty">
    <p class="state-empty-title">{{ props.emptyTitle }}</p>
    <p v-if="props.emptyBody" class="state-empty-body">{{ props.emptyBody }}</p>
    <div v-if="$slots.empty" class="state-empty-actions"><slot name="empty" /></div>
  </div>
  <div v-else data-state="ready" class="state-ready"><slot /></div>
</template>
