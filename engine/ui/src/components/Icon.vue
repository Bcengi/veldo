<script setup lang="ts">
/** The few line icons the shell uses, drawn for Veldo on a 24 unit grid. */
const props = defineProps<{ name: 'runs' | 'decisions' | 'you' | 'sun' | 'moon' | 'search' | 'follow' | 'key'; size?: number }>()
const paths: Record<string, string[]> = {
  runs: ['M4 5h16v14H4z', 'M7.5 9.5 10 12l-2.5 2.5', 'M12 15h4.5'],
  decisions: ['M12 3v6', 'M12 9 6 15v6', 'M12 9l6 6v6', 'M9.5 5.5 12 3l2.5 2.5'],
  you: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5'],
  sun: ['M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M12 2.5v2', 'M12 19.5v2', 'M2.5 12h2', 'M19.5 12h2', 'M5.3 5.3l1.4 1.4', 'M17.3 17.3l1.4 1.4', 'M5.3 18.7l1.4-1.4', 'M17.3 6.7l1.4-1.4'],
  moon: ['M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z'],
  search: ['M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z', 'M15.5 15.5 20 20'],
  follow: ['M12 4v13', 'M6.5 11.5 12 17l5.5-5.5', 'M5 20.5h14'],
  key: ['M8 15a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M11.5 11H20', 'M17 11v3', 'M20 11v2.5'],
}
</script>

<template>
  <svg :width="props.size ?? 24" :height="props.size ?? 24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="icon">
    <path v-for="(d, i) in paths[props.name]" :key="i" :d="d" />
  </svg>
</template>
