<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BarController, BarElement, CategoryScale, Chart, Legend, LinearScale, Tooltip } from 'chart.js'
import { useTheme } from '@/composables/useTheme'
import type { Bucket } from './usage'

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend)

/** Usage over time as a Chart.js bar chart (VELDO-0131): the known amount per hour and, stacked apart, the
 * invocations whose amount is not known yet, which are never drawn as zero usage. A tap or click on a bar
 * selects that hour (`select`); the screen's list of hours is the same selection by keyboard. */
const props = defineProps<{ buckets: Bucket[]; unit: string; selected: number | null; label: string }>()
const emit = defineEmits<{ select: [start: number] }>()
const canvas = ref<HTMLCanvasElement | null>(null)
const { theme } = useTheme()
let chart: Chart | null = null

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()
const hour = (start: number) => new Date(start * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

function config() {
  const accent = css('--accent')
  const amber = css('--amber')
  const ink = css('--ink-muted')
  const rule = css('--rule')
  return {
    labels: props.buckets.map((b) => hour(b.start)),
    datasets: [
      {
        label: `${props.unit.replace('_', ' ')} (known)`,
        data: props.buckets.map((b) => b.known),
        backgroundColor: props.buckets.map((b) => (b.start === props.selected ? css('--accent-hover') : accent)),
        yAxisID: 'y',
      },
      {
        label: 'invocations with unknown amount',
        data: props.buckets.map((b) => b.unknown),
        backgroundColor: amber,
        yAxisID: 'y2',
      },
    ],
    ink,
    rule,
  }
}

function render() {
  if (!canvas.value) return
  const c = config()
  chart?.destroy()
  chart = new Chart(canvas.value, {
    type: 'bar',
    data: { labels: c.labels, datasets: c.datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: 'index', intersect: false },
      onClick: (_event, elements) => {
        const index = elements[0]?.index
        const bucket = index != null ? props.buckets[index] : undefined
        if (bucket) emit('select', bucket.start)
      },
      plugins: { legend: { labels: { color: c.ink } } },
      scales: {
        x: { ticks: { color: c.ink, maxRotation: 0, autoSkip: true }, grid: { color: c.rule } },
        y: { beginAtZero: true, ticks: { color: c.ink }, grid: { color: c.rule }, title: { display: true, text: props.unit.replace('_', ' '), color: c.ink } },
        y2: { beginAtZero: true, position: 'right', ticks: { color: c.ink, precision: 0 }, grid: { display: false }, title: { display: true, text: 'unknown', color: c.ink } },
      },
    },
  })
}

onMounted(render)
watch(() => [props.buckets, props.unit, props.selected, theme.value], render)
onBeforeUnmount(() => chart?.destroy())
</script>

<template>
  <div class="usage-chart" data-testid="usage-chart">
    <canvas ref="canvas" role="img" :aria-label="props.label" />
  </div>
</template>
