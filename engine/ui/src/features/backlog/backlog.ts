import type { Item, ReadAnswer } from '@/api/types'
import type { TreeRow } from '@/features/table/tree-table'
import { COMPLETION_WORDS, completionOf } from './completion'

export interface BacklogUnit {
  id: string
  state: string
  specification: string
  completion: ReturnType<typeof completionOf>
}

export interface Blocker {
  id: string
  phase: string
  reason: string
  by: string
  resolved: boolean
}

export interface BacklogEntry {
  id: string
  version: number
  title: string
  project: string
  objective: string
  state: string
  /** The owner's rank (1 is first) as the authority stored it, or null when the item has none yet. */
  rank: number | null
  blockers: Blocker[]
  units: BacklogUnit[]
}

const str = (v: unknown, fallback = '') => (typeof v === 'string' ? v : fallback)

function specOf(value: unknown): string {
  if (typeof value === 'string') return value
  if (value && typeof value === 'object') {
    const v = value as { alias?: unknown; revision?: unknown }
    return `${str(v.alias, 'specification')}${v.revision != null ? ` r${String(v.revision)}` : ''}`
  }
  return ''
}

/** The backlog of the work read: each item with its rank, open blockers and the execution units taken from it,
 * each unit's completion judged by the landing receipts of the proof read. */
export function backlogOf(work: ReadAnswer | null, landed: Set<string>): BacklogEntry[] {
  if (!work) return []
  const units = new Map<string, BacklogUnit[]>()
  for (const item of work.items.execution_unit ?? []) {
    const d = item.data as Record<string, unknown>
    const parent = str(d.backlog_item_uuid)
    if (!parent) continue
    const state = str(d.state, 'unknown')
    units.set(parent, [...(units.get(parent) ?? []), { id: item.id, state, specification: specOf(d.primary_specification), completion: completionOf(item.id, state, landed) }])
  }
  return (work.items.backlog_item ?? []).map((item: Item) => {
    const d = item.data as Record<string, any>
    const rank = d.priority && typeof d.priority.rank === 'number' ? (d.priority.rank as number) : null
    const blocks = Array.isArray(d.blocks) ? d.blocks : []
    return {
      id: item.id,
      version: item.version,
      title: str(d.title, item.id),
      project: str(d.project),
      objective: str(d.objective_uuid),
      state: str(d.state, 'unknown'),
      rank,
      blockers: blocks.map((b: Record<string, unknown>) => ({
        id: str(b.block_id), phase: str(b.phase), reason: str(b.reason), by: str(b.by), resolved: b.resolution != null,
      })),
      units: (units.get(item.id) ?? []).sort((a, b) => a.id.localeCompare(b.id)),
    }
  })
}

/** The authority's order: ranked items by rank, then unranked ones, each by title. */
export function authorityOrder(entries: BacklogEntry[]): string[] {
  return [...entries]
    .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99) || a.title.localeCompare(b.title))
    .map((e) => e.id)
}

/** `order` with `id` moved to `to` (clamped). Used by drag and drop, the keyboard and the touch buttons alike. */
export function moveTo(order: string[], id: string, to: number): string[] {
  const from = order.indexOf(id)
  if (from < 0) return order
  const next = order.filter((x) => x !== id)
  next.splice(Math.max(0, Math.min(to, next.length)), 0, id)
  return next
}

export function moveBy(order: string[], id: string, delta: number): string[] {
  return moveTo(order, id, order.indexOf(id) + delta)
}

/** The rows of the backlog table, in `order`: items, and under each its units. */
export function backlogRows(entries: BacklogEntry[], order: string[]): TreeRow[] {
  const byId = new Map(entries.map((e) => [e.id, e]))
  return order
    .map((id) => byId.get(id))
    .filter((e): e is BacklogEntry => !!e)
    .map((e, index) => ({
      id: e.id,
      ref: e,
      cells: {
        title: e.title,
        position: String(index + 1),
        rank: e.rank == null ? 'No rank' : `Rank ${e.rank}`,
        state: e.state,
        blockers: e.blockers.filter((b) => !b.resolved).map((b) => b.reason).join('; ') || 'None',
        project: e.project,
      },
      children: e.units.map((u) => ({
        id: u.id,
        ref: u,
        cells: {
          title: u.id,
          position: '',
          rank: u.specification,
          state: COMPLETION_WORDS[u.completion] || u.state,
          blockers: '',
          project: e.project,
        },
      })),
    }))
}
