import { createExpandedRowModel, rowExpandingFeature, tableFeatures } from '@tanstack/vue-table'

/** One row of a hierarchy table: its own id, the text of each column, and the rows nested under it. */
export interface TreeRow {
  id: string
  cells: Record<string, string>
  children?: TreeRow[]
  /** Free data a screen keeps with the row (the item it came from). */
  ref?: unknown
}

export interface TreeColumn {
  id: string
  header: string
  /** The column a phone card shows as its title. */
  primary?: boolean
}

/** The TanStack Table features of every Veldo hierarchy table: expandable sub-rows, nothing else. */
export const treeFeatures = tableFeatures({
  rowExpandingFeature,
  expandedRowModel: createExpandedRowModel(),
})
