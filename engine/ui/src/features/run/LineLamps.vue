<script setup lang="ts">
import { computed } from 'vue'
import { LINE, stationIndex } from './lamps'

/** The station strip in miniature for a list row: one dot per station, the unit's own lit. */
const props = defineProps<{ unitState: string | null; live: boolean }>()
const at = computed(() => stationIndex(props.unitState))
const word = computed(() => (at.value < 0 ? '' : LINE[at.value]!.label === 'Done' ? 'Completed' : LINE[at.value]!.label))
const label = computed(() => (at.value < 0 ? 'Station not readable' : word.value === 'Completed' ? 'Completed' : `At ${word.value}`))
</script>

<template>
  <span class="line-lamps" role="img" :aria-label="label">
    <span
      v-for="(stop, i) in LINE"
      :key="stop.label"
      class="line-dot"
      :class="{ 'is-current': i === at && !(stop.label === 'Done'),
        'is-past': (at >= 0 && i < at) || (i === at && stop.label === 'Done'), 'is-live': i === at && props.live && stop.label !== 'Done' }"
    />
    <span class="line-at" aria-hidden="true">{{ word }}</span>
  </span>
</template>
