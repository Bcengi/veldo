<script setup lang="ts">
import { computed, ref } from 'vue'
import VButton from '@/components/VButton.vue'
import { KINDS, nodeIds, position, type Draft } from './workflow-doc'

/** The workflow editor's canvas (VELDO-0131): Veldo's own SVG control. Steps are boxes, transitions arrows
 * labeled with their port. Pan by dragging the background or with the arrow buttons, zoom with the buttons or
 * the wheel; drag a step to move it, or focus it and use the arrow keys. A step or an arrow is selected by
 * click, tap, Enter or Space. Every setting is edited in the property sheet beside the canvas, never here and
 * never on hover. */
const props = defineProps<{ draft: Draft; selected: { kind: 'node' | 'edge'; id: string } | null }>()
const emit = defineEmits<{ select: [target: { kind: 'node' | 'edge'; id: string }]; move: [id: string, x: number, y: number] }>()
const W = 180
const H = 64
const view = ref({ x: -20, y: -20, zoom: 1 })
const svg = ref<SVGSVGElement | null>(null)
const nodes = computed(() => nodeIds(props.draft).map((id) => ({ id, ...position(props.draft, id), kind: props.draft.definition.nodes[id]!.kind })))
const edges = computed(() => {
  const all = props.draft.definition.transitions
  return all
    .map((t) => {
      const a = nodes.value.find((n) => n.id === t.from)
      const b = nodes.value.find((n) => n.id === t.to)
      if (!a || !b) return null
      // Transitions between the same two steps fan out, so each arrow and its port label stand apart.
      const twins = all.filter((o) => o.from === t.from && o.to === t.to)
      const fan = (twins.indexOf(t) - (twins.length - 1) / 2) * 34
      const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2
      const back = x2 < x1
      const bend = (back ? Math.max(60, Math.abs(y2 - y1) / 2 + 40) : 0) + fan
      const mx = (x1 + x2) / 2
      const d = back
        ? `M${x1},${y1} C${x1 + 60},${y1 + bend} ${x2 - 60},${y2 + bend} ${x2},${y2}`
        : `M${x1},${y1} C${mx},${y1 + fan * 1.5} ${mx},${y2 + fan * 1.5} ${x2},${y2}`
      return { ...t, d, lx: mx, ly: (y1 + y2) / 2 + (back ? bend * 0.75 : fan * 1.2 - 6) }
    })
    .filter((e) => e !== null)
})
const box = computed(() => `${view.value.x} ${view.value.y} ${900 / view.value.zoom} ${420 / view.value.zoom}`)

let drag: { kind: 'node' | 'pan'; id?: string; sx: number; sy: number; ox: number; oy: number; moved: boolean } | null = null
function scale() {
  const rect = svg.value?.getBoundingClientRect()
  return rect && rect.width ? 900 / view.value.zoom / rect.width : 1
}
function down(event: PointerEvent, id?: string) {
  const start = id ? nodes.value.find((n) => n.id === id)! : { x: view.value.x, y: view.value.y }
  drag = { kind: id ? 'node' : 'pan', id, sx: event.clientX, sy: event.clientY, ox: start.x, oy: start.y, moved: false }
  ;(event.currentTarget as Element).setPointerCapture?.(event.pointerId)
}
function moveTo(event: PointerEvent) {
  if (!drag) return
  const k = scale()
  const dx = (event.clientX - drag.sx) * k
  const dy = (event.clientY - drag.sy) * k
  if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true
  if (!drag.moved) return
  if (drag.kind === 'node' && drag.id) emit('move', drag.id, drag.ox + dx, drag.oy + dy)
  else view.value = { ...view.value, x: drag.ox - dx, y: drag.oy - dy }
}
function up(id?: string) {
  if (drag && !drag.moved && id) emit('select', { kind: 'node', id })
  drag = null
}
function zoom(factor: number) {
  view.value = { ...view.value, zoom: Math.min(2.5, Math.max(0.4, view.value.zoom * factor)) }
}
function pan(dx: number, dy: number) {
  view.value = { ...view.value, x: view.value.x + dx, y: view.value.y + dy }
}
function fit() {
  if (!nodes.value.length) return
  const xs = nodes.value.map((n) => n.x)
  const ys = nodes.value.map((n) => n.y)
  const w = Math.max(...xs) - Math.min(...xs) + W + 80
  const h = Math.max(...ys) - Math.min(...ys) + H + 80
  const zoomed = Math.min(2.5, Math.max(0.4, Math.min(900 / w, 420 / h)))
  view.value = { x: Math.min(...xs) - 40, y: Math.min(...ys) - 40, zoom: zoomed }
}
function wheel(event: WheelEvent) {
  event.preventDefault()
  zoom(event.deltaY < 0 ? 1.1 : 1 / 1.1)
}
function key(event: KeyboardEvent, id: string) {
  const n = nodes.value.find((x) => x.id === id)!
  const step = event.shiftKey ? 60 : 20
  const moves: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('select', { kind: 'node', id })
  } else if (moves[event.key]) {
    event.preventDefault()
    emit('move', id, n.x + moves[event.key]![0], n.y + moves[event.key]![1])
  }
}
function edgeKey(event: KeyboardEvent, id: string) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('select', { kind: 'edge', id })
  }
}
const isSel = (kind: 'node' | 'edge', id: string) => props.selected?.kind === kind && props.selected.id === id
</script>

<template>
  <div class="flow-canvas" data-testid="flow-canvas">
    <svg
      ref="svg"
      :viewBox="box"
      role="group"
      aria-label="Workflow canvas: steps and transitions"
      @pointerdown.self="down($event)"
      @pointermove="moveTo"
      @pointerup="up()"
      @pointercancel="up()"
      @wheel="wheel"
    >
      <defs>
        <marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" class="flow-arrowhead" />
        </marker>
      </defs>
      <rect :x="view.x - 2000" :y="view.y - 2000" width="6000" height="6000" fill="transparent" @pointerdown="down($event)" />
      <g v-for="e in edges" :key="e.id" :data-edge="e.id">
        <path
          :d="e.d"
          class="flow-edge"
          :class="{ 'is-selected': isSel('edge', e.id) }"
          marker-end="url(#flow-arrow)"
          tabindex="0"
          role="button"
          :aria-label="`Transition ${e.id}: ${e.from} ${e.port} to ${e.to}`"
          :aria-pressed="isSel('edge', e.id)"
          @click="emit('select', { kind: 'edge', id: e.id })"
          @keydown="edgeKey($event, e.id)"
        />
        <text :x="e.lx" :y="e.ly" class="flow-port" text-anchor="middle">{{ e.port }}</text>
      </g>
      <g
        v-for="n in nodes"
        :key="n.id"
        class="flow-node"
        :class="{ 'is-selected': isSel('node', n.id) }"
        :transform="`translate(${n.x},${n.y})`"
        tabindex="0"
        role="button"
        :aria-label="`Step ${n.id}, ${KINDS[n.kind]?.label ?? n.kind}${props.draft.definition.entry === n.id ? ', entry' : ''}. Arrow keys move it.`"
        :aria-pressed="isSel('node', n.id)"
        :data-node="n.id"
        @pointerdown.stop="down($event, n.id)"
        @pointerup.stop="up(n.id)"
        @keydown="key($event, n.id)"
      >
        <rect :width="W" :height="H" rx="8" />
        <text x="12" y="26" font-weight="600">{{ n.id }}</text>
        <text x="12" y="48" class="flow-kind">{{ KINDS[n.kind]?.label ?? n.kind }}{{ props.draft.definition.entry === n.id ? ' (entry)' : '' }}</text>
      </g>
    </svg>
    <div class="flow-zoom" role="group" aria-label="Canvas view">
      <VButton label="Zoom in" size="small" variant="secondary" data-testid="zoom-in" @click="zoom(1.25)" />
      <VButton label="Zoom out" size="small" variant="secondary" data-testid="zoom-out" @click="zoom(0.8)" />
      <VButton label="Fit" size="small" variant="secondary" data-testid="zoom-fit" @click="fit" />
    </div>
    <div class="flow-pan" role="group" aria-label="Pan the canvas">
      <VButton label="Pan left" size="small" variant="quiet" @click="pan(-80, 0)" />
      <VButton label="Pan right" size="small" variant="quiet" @click="pan(80, 0)" />
      <VButton label="Pan up" size="small" variant="quiet" @click="pan(0, -80)" />
      <VButton label="Pan down" size="small" variant="quiet" @click="pan(0, 80)" />
    </div>
  </div>
</template>
