<script setup lang="ts">
import { computed } from 'vue'
import Lamp from '@/components/Lamp.vue'
import type { LiveState } from '@/composables/useLiveRead'

/** Where a screen's data comes from and how current it is: the journal sequence the API read it at, the
 * freshness the API named, when it was read, and whether the screen is following the journal live. */
const props = defineProps<{ live: LiveState; seq: number | null; freshness: string | null; readAt: number | null }>()
const words = computed(() => ({ idle: 'Not following', live: 'Live', reconnecting: 'Reconnecting', stopped: 'Stopped' })[props.live])
const lamp = computed(() => (props.live === 'live' ? 'live' : props.live === 'reconnecting' ? 'waiting' : 'off'))
const at = computed(() => (props.readAt ? new Date(props.readAt).toLocaleTimeString() : null))
</script>

<template>
  <p class="factory-meta" data-testid="live-meta" :data-live="props.live" :data-seq="props.seq ?? ''" role="status">
    <span class="factory-live"><Lamp :state="lamp" :label="words" size="sm" />{{ words }}</span>
    <span v-if="props.seq != null">Journal {{ props.seq }}</span>
    <span v-if="props.freshness" :class="{ 'is-stale': props.freshness !== 'live' }">{{ props.freshness === 'live' ? 'Read live' : `Stale (${props.freshness})` }}</span>
    <span v-if="at">Read at {{ at }}</span>
  </p>
</template>
