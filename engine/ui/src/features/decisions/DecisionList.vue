<script setup lang="ts">
import UBadge from '@nuxt/ui/components/Badge.vue'
import Lamp from '@/components/Lamp.vue'
import type { LampState } from '@/app/navigation'
import { dueText, riskOf, urgencyOf, type PendingDecision, type Urgency } from './inbox'

/** The inbox: each pending decision with its question, how soon it is due and its risk, ranked by the store
 * (most urgent first). The lamp is colored by urgency; the risk is a badge with its word. A row opens the decision. */
const props = defineProps<{ decisions: PendingDecision[]; current: string | null; now: number }>()

const LAMP: Record<Urgency, { lamp: LampState; word: string }> = {
  overdue: { lamp: 'stop', word: 'Overdue' },
  today: { lamp: 'stop', word: 'Due within a day' },
  soon: { lamp: 'waiting', word: 'Due within three days' },
  later: { lamp: 'here', word: 'Due later' },
  none: { lamp: 'here', word: 'No deadline' },
}
const RISK = { high: 'High risk', medium: 'Medium risk', low: 'Low risk', unknown: '' } as const

function view(item: PendingDecision) {
  const urgency = item.presentation ? urgencyOf(item.deadline, props.now) : 'none'
  return {
    urgency,
    lamp: item.presentation ? LAMP[urgency] : { lamp: 'off' as LampState, word: 'Not presented yet' },
    due: dueText(item.deadline, props.now),
    risk: RISK[riskOf(item.presentation?.risk)],
    level: riskOf(item.presentation?.risk),
  }
}
</script>

<template>
  <ul class="inbox" data-testid="inbox">
    <li v-for="item in props.decisions" :key="item.requestId">
      <RouterLink
        :to="{ name: 'decision', params: { request: item.requestId.split('/') } }"
        class="inbox-row"
        :class="`is-${view(item).urgency}`"
        :aria-current="item.requestId === props.current ? 'true' : undefined"
        :data-request="item.requestId"
        :data-urgency="view(item).urgency"
      >
        <Lamp :state="view(item).lamp.lamp" :label="view(item).lamp.word" />
        <span class="inbox-main">
          <span class="inbox-question">{{ item.presentation?.question || item.brief || 'A decision not presented yet' }}</span>
          <span class="inbox-facts">
            <span v-if="view(item).due" class="inbox-due" data-testid="due">{{ view(item).due }}</span>
            <UBadge
              v-if="view(item).risk"
              class="inbox-risk status-badge"
              :class="`risk-${view(item).level}`"
              :color="view(item).level === 'high' ? 'error' : view(item).level === 'medium' ? 'warning' : 'neutral'"
              variant="subtle"
              size="sm"
              :label="view(item).risk"
            />
            <span v-if="!item.presentation">Not presented yet</span>
            <span v-if="item.scope.length" class="inbox-scope">{{ item.scope.join(', ') }}</span>
          </span>
        </span>
      </RouterLink>
    </li>
  </ul>
</template>
