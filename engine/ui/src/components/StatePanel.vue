<script setup lang="ts">
import { computed } from 'vue'
import { isRetryable, type ApiRefusal } from '@/api/refusal'
import type { AsyncState } from '@/composables/useAsync'
import RefusalNotice from './RefusalNotice.vue'
import VButton from './VButton.vue'

/** One screen region's loading, empty, error and ready states. Exactly one is rendered. The loading state
 * is shaped like what is coming (`shape`); an error offers Try again only when trying again can succeed. */
const props = withDefaults(
  defineProps<{
    state: AsyncState
    refusal?: ApiRefusal | null
    emptyTitle?: string
    emptyBody?: string
    loadingLabel?: string
    rows?: number
    shape?: 'rows' | 'lines' | 'block' | 'board'
  }>(),
  { refusal: null, emptyTitle: 'Nothing here yet', emptyBody: '', loadingLabel: 'Loading', rows: 4, shape: 'rows' },
)
const emit = defineEmits<{ retry: [] }>()
const retry = computed(() => !!props.refusal && isRetryable(props.refusal))
</script>

<template>
  <div v-if="props.state === 'loading' || props.state === 'idle'" class="state-loading" :class="`skeleton-${props.shape}`" role="status" :aria-label="props.loadingLabel" data-state="loading">
    <template v-if="props.shape === 'rows'">
      <span v-for="n in props.rows" :key="n" class="skeleton-row">
        <span class="skeleton skeleton-lamp" />
        <span class="skeleton-text">
          <span class="skeleton" :style="{ width: `${78 - ((n * 17) % 30)}%` }" />
          <span class="skeleton skeleton-thin" :style="{ width: `${44 - ((n * 7) % 18)}%` }" />
        </span>
        <span class="skeleton skeleton-strip" />
      </span>
    </template>
    <template v-else-if="props.shape === 'lines'">
      <span v-for="n in props.rows" :key="n" class="skeleton-line">
        <span class="skeleton skeleton-gutter" />
        <span class="skeleton" :style="{ width: `${82 - ((n * 13) % 45)}%` }" />
      </span>
    </template>
    <template v-else-if="props.shape === 'board'">
      <span v-for="n in 4" :key="`c${n}`" class="skeleton" />
    </template>
    <span v-for="n in props.shape === 'block' ? props.rows : 0" v-else :key="`b${n}`" class="skeleton" :style="{ width: `${92 - ((n * 17) % 40)}%` }" />
  </div>
  <div v-else-if="props.state === 'error' && props.refusal" class="state-error" data-state="error">
    <RefusalNotice :refusal="props.refusal">
      <VButton v-if="retry" label="Try again" variant="secondary" size="small" data-testid="try-again" @click="emit('retry')" />
      <slot name="error-actions" />
    </RefusalNotice>
  </div>
  <div v-else-if="props.state === 'empty'" class="state-empty" data-state="empty">
    <p class="state-empty-title">{{ props.emptyTitle }}</p>
    <p v-if="props.emptyBody" class="state-empty-body">{{ props.emptyBody }}</p>
    <div v-if="$slots.empty" class="state-empty-actions"><slot name="empty" /></div>
  </div>
  <div v-else data-state="ready" class="state-ready"><slot /></div>
</template>
