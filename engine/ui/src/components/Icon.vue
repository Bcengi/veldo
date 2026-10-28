<script setup lang="ts">
/** The few line icons the shell uses, drawn for Veldo on a 24 unit grid. */
export type IconName = 'overview' | 'runs' | 'decisions' | 'you' | 'search' | 'follow' | 'key' | 'copy' | 'check' | 'close' | 'refresh'
const props = defineProps<{ name: IconName; size?: number }>()
const paths: Record<IconName, string[]> = {
  overview: ['M6.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z', 'M17.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z', 'M6.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z', 'M17.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z'],
  runs: ['M4 5h16v14H4z', 'M7.5 9.5 10 12l-2.5 2.5', 'M12 15h4.5'],
  decisions: ['M12 3v6', 'M12 9 6 15v6', 'M12 9l6 6v6', 'M9.5 5.5 12 3l2.5 2.5'],
  you: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5'],
  search: ['M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z', 'M15.5 15.5 20 20'],
  follow: ['M12 4v13', 'M6.5 11.5 12 17l5.5-5.5', 'M5 20.5h14'],
  key: ['M8 15a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M11.5 11H20', 'M17 11v3', 'M20 11v2.5'],
  copy: ['M9 9h10v11H9z', 'M5 15V4h10'],
  check: ['M5 12.5 10 17.5 19 7'],
  close: ['M6 6l12 12', 'M18 6 6 18'],
  refresh: ['M19 12a7 7 0 1 1-2.05-4.95', 'M19 4.5V9h-4.5'],
}
</script>

<template>
  <svg :width="props.size ?? 24" :height="props.size ?? 24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="icon">
    <path v-for="(d, i) in paths[props.name]" :key="i" :d="d" />
  </svg>
</template>
