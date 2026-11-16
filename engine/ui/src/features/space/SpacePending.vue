<script setup lang="ts">
import { computed } from 'vue'
import type { PendingDecision } from '@/features/decisions/inbox'
import { bytesText, memberPicks, ownerText, pendingGroups, pendingReason, retryText, words, type PendingAnswer, type PendingItem, type RequestGroup } from './space'

/** Pending removal (design 10): every due and deferred item with its reason in words, the event that retries it
 * and its open decision request. The worktrees of one request are listed under it, each with its index and the
 * answers the request offers for it alone. An answer is given on the Decisions screen, through the settlement
 * the request already uses: this screen links there and sends no answer of its own. */
const props = defineProps<{ pending: PendingAnswer; decisions: PendingDecision[] }>()
const groups = computed(() => pendingGroups(props.pending, props.decisions))
const title = (group: RequestGroup) =>
  group.request.group
    ? `Review worktrees of ${group.request.day ?? 'one day'}${group.request.sequence && group.request.sequence > 1 ? `, group ${group.request.sequence}` : ''}`
    : 'One worktree'
const tag = (item: PendingItem) => (item.state === 'due' ? 'Due' : 'Deferred')
</script>

<template>
  <section class="panel" aria-labelledby="space-pending-title" data-testid="space-pending">
    <h2 id="space-pending-title" class="panel-title">Pending removal <span class="panel-count">{{ props.pending.items.length }}</span></h2>
    <div class="factory-body">
      <p v-if="!props.pending.items.length" class="space-note" data-testid="space-pending-none">Nothing is due and nothing is deferred.</p>
      <section v-for="group in groups.requests" :key="group.request.alias" class="factory-card space-request" :data-request="group.request.alias" :aria-label="`Decision request for ${title(group)}`">
        <div class="space-head">
          <span class="factory-card-title">Waiting on your decision: {{ title(group) }}</span>
          <span class="factory-tag is-waiting">{{ group.items.length }} {{ group.items.length === 1 ? 'worktree' : 'worktrees' }}</span>
        </div>
        <p class="space-note">Request <span class="space-path">{{ group.request.alias }}</span></p>
        <RouterLink
          v-if="group.decision?.presentation"
          :to="{ name: 'decision', params: { request: group.decision.requestId.split('/') } }"
          class="space-link"
          data-testid="space-answer"
        >Answer in Decisions</RouterLink>
        <p v-else-if="group.decision" class="space-note" data-testid="space-unpresented">This request has not been presented to you yet. It can be answered once it has been sent.</p>
        <p v-else class="space-note" data-testid="space-not-yours">This request is not among the decisions waiting on you.</p>
        <ul class="factory-list">
          <li v-for="item in group.items" :key="item.id" class="factory-card" :data-item="item.id" :data-state="item.state" :data-index="item.index ?? undefined">
            <div class="space-head">
              <span v-if="group.request.group && item.index !== null" class="factory-tag" data-testid="member-index">Worktree {{ item.index }}</span>
              <span class="space-path">{{ item.locator }}</span>
              <span class="factory-tag" :class="item.state === 'deferred' ? 'is-waiting' : ''">{{ tag(item) }}</span>
            </div>
            <dl class="factory-facts">
              <dt>Why</dt><dd data-testid="pending-reason">{{ pendingReason(item) }}</dd>
              <dt>Retry</dt><dd data-testid="pending-retry">{{ retryText(item) }}</dd>
              <dt>Owner</dt><dd>{{ ownerText(item.owner) }}</dd>
              <dt>Size</dt><dd>{{ item.bytes === null ? 'not measured' : bytesText(item.bytes) }}</dd>
              <template v-if="memberPicks(group.request, item.index).length">
                <dt>Its own answers</dt><dd data-testid="member-picks">{{ memberPicks(group.request, item.index).join(', ') }}</dd>
              </template>
              <template v-else-if="group.request.group">
                <dt>Its own answers</dt><dd data-testid="member-picks">None in this request: answer the group, or the worktrees before it first</dd>
              </template>
            </dl>
          </li>
        </ul>
      </section>
      <ul v-if="groups.rest.length" class="factory-list" aria-label="Items with no decision request">
        <li v-for="item in groups.rest" :key="item.id" class="factory-card" :data-item="item.id" :data-state="item.state">
          <div class="space-head">
            <span class="space-path">{{ item.locator }}</span>
            <span class="factory-tag">{{ words(item.kind) }}</span>
            <span class="factory-tag" :class="item.state === 'deferred' ? 'is-waiting' : ''">{{ tag(item) }}</span>
          </div>
          <dl class="factory-facts">
            <dt>Why</dt><dd data-testid="pending-reason">{{ pendingReason(item) }}</dd>
            <dt>Retry</dt><dd data-testid="pending-retry">{{ retryText(item) }}</dd>
            <dt>Owner</dt><dd>{{ ownerText(item.owner) }}</dd>
            <dt>Size</dt><dd>{{ item.bytes === null ? 'not measured' : bytesText(item.bytes) }}</dd>
            <template v-if="item.state === 'deferred'">
              <dt>Refused</dt><dd>At {{ words(item.refused_at) || 'an event that was not recorded' }}<template v-if="item.attempts">, {{ item.attempts }} {{ item.attempts === 1 ? 'time' : 'times' }}</template></dd>
              <dt>Decision</dt><dd data-testid="pending-request">No decision request is open for it</dd>
            </template>
          </dl>
        </li>
      </ul>
    </div>
  </section>
</template>
