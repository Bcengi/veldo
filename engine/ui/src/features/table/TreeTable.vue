<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTable } from '@tanstack/vue-table'
import { treeFeatures, type TreeColumn, type TreeRow } from './tree-table'

/** A hierarchy table on TanStack Table (VELDO-0131): rows with nested rows, each expandable by its own labeled
 * button, rendered as a native table on a desktop and as stacked cards on a phone (`.tree-cards`, by the
 * stylesheet's breakpoint), so the same controls work by keyboard and by touch. A cell's content can be
 * replaced through the `cell` slot; a row's own actions go in the `actions` slot. */
const props = withDefaults(
  defineProps<{
    rows: TreeRow[]
    columns: TreeColumn[]
    label: string
    expandedByDefault?: boolean
    rowClass?: (row: TreeRow) => string
    /** Top-level rows can be dragged onto another top-level row (desktop pointer). Never the only way: the
     * screen gives every move a button in the `actions` slot too. */
    reorderable?: boolean
  }>(),
  { expandedByDefault: false, rowClass: undefined, reorderable: false },
)
const emit = defineEmits<{ move: [id: string, to: number] }>()
const dragging = ref<string | null>(null)
const target = ref<string | null>(null)
function dragStart(event: DragEvent, id: string) {
  dragging.value = id
  event.dataTransfer?.setData('text/plain', id)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}
function dragOver(event: DragEvent, id: string) {
  if (!dragging.value) return
  event.preventDefault()
  target.value = id
}
function drop(event: DragEvent, id: string) {
  event.preventDefault()
  const moved = dragging.value
  dragging.value = null
  target.value = null
  if (!moved || moved === id) return
  emit('move', moved, props.rows.findIndex((r) => r.id === id))
}
function dragEnd() {
  dragging.value = null
  target.value = null
}
defineSlots<{
  cell(props: { row: TreeRow; column: TreeColumn; value: string }): unknown
  actions(props: { row: TreeRow; depth: number; index: number; siblings: number }): unknown
}>()
const expanded = ref<Record<string, boolean> | true>(props.expandedByDefault ? true : {})
const data = computed(() => props.rows)
const table = useTable({
  features: treeFeatures,
  columns: computed(() => props.columns.map((c) => ({ id: c.id, header: c.header, accessorFn: (r: TreeRow) => r.cells[c.id] ?? '' }))),
  data,
  getSubRows: (row: TreeRow) => row.children,
  getRowId: (row: TreeRow) => row.id,
  state: { get expanded() { return expanded.value } },
  onExpandedChange: (updater: unknown) => {
    expanded.value = typeof updater === 'function' ? (updater as (v: typeof expanded.value) => typeof expanded.value)(expanded.value) : (updater as typeof expanded.value)
  },
} as never)
type Shown = { row: TreeRow; depth: number; canExpand: boolean; isExpanded: boolean; toggle: () => void; index: number; siblings: number }
const shown = computed<Shown[]>(() => {
  void expanded.value
  void props.rows
  const model = (table as unknown as { getRowModel(): { rows: Array<{ original: TreeRow; depth: number; index: number; getCanExpand(): boolean; getIsExpanded(): boolean; toggleExpanded(): void; getParentRow(): { subRows: unknown[] } | undefined }> } }).getRowModel()
  return model.rows.map((r) => ({
    row: r.original,
    depth: r.depth,
    canExpand: r.getCanExpand(),
    isExpanded: r.getIsExpanded(),
    toggle: () => r.toggleExpanded(),
    index: r.index,
    siblings: r.getParentRow()?.subRows.length ?? props.rows.length,
  }))
})
const primary = computed<TreeColumn>(() => props.columns.find((c) => c.primary) ?? props.columns[0] ?? { id: '', header: '' })
</script>

<template>
  <div class="tree-table" data-testid="tree-table">
    <table class="tree-grid" :aria-label="props.label">
      <thead>
        <tr>
          <th v-for="column in props.columns" :key="column.id" scope="col">{{ column.header }}</th>
          <th v-if="$slots.actions" scope="col"><span class="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in shown"
          :key="item.row.id"
          :data-row="item.row.id"
          :data-depth="item.depth"
          :class="[props.rowClass?.(item.row), { 'tree-row-dragging': dragging === item.row.id, 'tree-row-target': target === item.row.id && dragging !== item.row.id }]"
          :draggable="props.reorderable && item.depth === 0 ? 'true' : undefined"
          @dragstart="props.reorderable && item.depth === 0 && dragStart($event, item.row.id)"
          @dragover="props.reorderable && item.depth === 0 && dragOver($event, item.row.id)"
          @drop="props.reorderable && item.depth === 0 && drop($event, item.row.id)"
          @dragend="dragEnd"
        >
          <td v-for="column in props.columns" :key="column.id" :class="{ 'tree-primary': column === primary }">
            <span v-if="column === primary" class="tree-indent" :style="{ paddingInlineStart: `${item.depth * 1.25}rem` }">
              <button
                v-if="item.canExpand"
                type="button"
                class="tree-toggle"
                :aria-expanded="item.isExpanded"
                :aria-label="`${item.isExpanded ? 'Collapse' : 'Expand'} ${item.row.cells[column.id]}`"
                @click="item.toggle()"
              >
                <svg viewBox="0 0 20 20" aria-hidden="true" width="16" height="16"><path :d="item.isExpanded ? 'M5 8l5 5 5-5' : 'M8 5l5 5-5 5'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
              </button>
              <span v-else class="tree-toggle-space" aria-hidden="true" />
              <slot name="cell" :row="item.row" :column="column" :value="item.row.cells[column.id] ?? ''">{{ item.row.cells[column.id] }}</slot>
            </span>
            <slot v-else name="cell" :row="item.row" :column="column" :value="item.row.cells[column.id] ?? ''">{{ item.row.cells[column.id] }}</slot>
          </td>
          <td v-if="$slots.actions" class="tree-actions"><slot name="actions" :row="item.row" :depth="item.depth" :index="item.index" :siblings="item.siblings" /></td>
        </tr>
      </tbody>
    </table>
    <ul class="tree-cards" :aria-label="props.label">
      <li v-for="item in shown" :key="item.row.id" class="tree-card" :data-row="item.row.id" :data-depth="item.depth" :class="props.rowClass?.(item.row)" :style="{ marginInlineStart: `${Math.min(item.depth, 3) * 0.75}rem` }">
        <div class="tree-card-head">
          <button
            v-if="item.canExpand"
            type="button"
            class="tree-toggle"
            :aria-expanded="item.isExpanded"
            :aria-label="`${item.isExpanded ? 'Collapse' : 'Expand'} ${item.row.cells[primary.id]}`"
            @click="item.toggle()"
          >
            <svg viewBox="0 0 20 20" aria-hidden="true" width="16" height="16"><path :d="item.isExpanded ? 'M5 8l5 5 5-5' : 'M8 5l5 5-5 5'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </button>
          <span class="tree-card-title"><slot name="cell" :row="item.row" :column="primary" :value="item.row.cells[primary.id] ?? ''">{{ item.row.cells[primary.id] }}</slot></span>
        </div>
        <dl class="tree-card-facts">
          <div v-for="column in props.columns.filter((c) => c !== primary)" :key="column.id">
            <dt>{{ column.header }}</dt>
            <dd><slot name="cell" :row="item.row" :column="column" :value="item.row.cells[column.id] ?? ''">{{ item.row.cells[column.id] }}</slot></dd>
          </div>
        </dl>
        <div v-if="$slots.actions" class="tree-card-actions"><slot name="actions" :row="item.row" :depth="item.depth" :index="item.index" :siblings="item.siblings" /></div>
      </li>
    </ul>
  </div>
</template>
