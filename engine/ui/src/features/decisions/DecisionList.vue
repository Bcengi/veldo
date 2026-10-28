<script setup lang="ts">
import Lamp from '@/components/Lamp.vue'
import type { PendingDecision } from './inbox'

/** The inbox: each pending decision with its question and deadline. A row opens the decision. */
const props = defineProps<{ decisions: PendingDecision[]; current: string | null }>()

function due(deadline: string | null) {
  if (!deadline) return null
  const d = new Date(deadline)
  return Number.isNaN(d.getTime()) ? deadline : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
</script>

<template>
  <ul class="inbox" data-testid="inbox">
    <li v-for="item in props.decisions" :key="item.requestId">
      <RouterLink
        :to="{ name: 'decision', params: { request: item.requestId.split('/') } }"
        class="inbox-row"
        :aria-current="item.requestId === props.current ? 'true' : undefined"
        :data-request="item.requestId"
      >
        <Lamp :state="item.presentation ? 'waiting' : 'off'" :label="item.presentation ? 'Waiting on you' : 'Not presented yet'" />
        <span class="inbox-main">
          <span class="inbox-question">{{ item.presentation?.question || item.brief || item.alias }}</span>
          <span class="inbox-facts">
            <span>{{ item.alias }}</span>
            <span v-if="item.scope.length">{{ item.scope.join(', ') }}</span>
            <span v-if="due(item.deadline)">Due {{ due(item.deadline) }}</span>
          </span>
        </span>
      </RouterLink>
    </li>
  </ul>
</template>
