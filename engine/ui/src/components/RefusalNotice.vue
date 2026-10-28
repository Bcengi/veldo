<script setup lang="ts">
import { computed } from 'vue'
import { describeRefusal, type ApiRefusal } from '@/api/refusal'

/** A named refusal shown where it happened: what happened, how to fix it, and the API's own name for it. */
const props = withDefaults(defineProps<{ refusal: Pick<ApiRefusal, 'refusal' | 'error'>; compact?: boolean }>(), { compact: false })
const text = computed(() => describeRefusal(props.refusal))
</script>

<template>
  <div class="refusal" :class="{ 'refusal-compact': props.compact }" role="alert" data-testid="refusal" :data-refusal="props.refusal.refusal">
    <p class="refusal-title">{{ text.title }}</p>
    <p class="refusal-fix">{{ text.fix }}</p>
    <p class="refusal-name"><code>{{ props.refusal.refusal }}</code></p>
    <div v-if="$slots.default" class="refusal-actions"><slot /></div>
  </div>
</template>
