<script setup lang="ts">
import { computed } from 'vue'
import Lamp from '@/components/Lamp.vue'
import { LINE, OFF_LINE, stationIndex } from './lamps'

/** The unit's place on the line: one lamp per station, the current one lit. The dispatch's own station
 * (build, review, coordination) names what the worker of this run does there. */
const props = defineProps<{ unitState: string | null; station: string | null; live: boolean }>()
const at = computed(() => stationIndex(props.unitState))
const off = computed(() => (props.unitState ? OFF_LINE[props.unitState] : undefined))
</script>

<template>
  <div class="strip" data-testid="station-strip" :data-unit-state="props.unitState ?? ''">
    <ol class="strip-line" aria-label="Where the unit is on the line">
      <li
        v-for="(stop, i) in LINE"
        :key="stop.label"
        class="strip-stop"
        :class="{ 'is-current': i === at, 'is-past': at >= 0 && i < at }"
        :aria-current="i === at ? 'step' : undefined"
      >
        <Lamp
          :state="i === at ? (stop.label === 'Done' ? 'done' : props.live ? 'live' : 'waiting') : 'off'"
          :label="i === at ? `${stop.label}, current` : at >= 0 && i < at ? `${stop.label}, passed` : stop.label"
          size="sm"
        />
        <span class="strip-name">{{ stop.label }}</span>
      </li>
    </ol>
    <p class="strip-note">
      <span v-if="props.station" data-testid="run-station">Station: <strong>{{ props.station }}</strong></span>
      <span v-if="off" class="strip-off"><Lamp :state="off.lamp" :label="off.word" size="sm" /> {{ off.word }}</span>
      <span v-else-if="at < 0" class="strip-unknown">{{ props.unitState ? `Unit state ${props.unitState}` : 'Unit state not readable' }}</span>
    </p>
  </div>
</template>
