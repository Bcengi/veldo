import type { Item, ReadAnswer } from '@/api/types'

/** One worker run as the runs list shows it, from a dispatch record (control_dispatch). */
export interface RunRow {
  dispatch: string
  unit: string
  station: string
  project: string
  state: string
  host: string
  platform: string
  /** The unit's own state (execution_unit), for the station strip, or null when not readable. */
  unitState: string | null
}

type Json = Record<string, unknown>
const str = (v: unknown) => (typeof v === 'string' ? v : '')
const obj = (v: unknown): Json => (typeof v === 'object' && v !== null && !Array.isArray(v) ? (v as Json) : {})

export const LIVE_STATES = new Set(['prepared', 'accepted', 'running'])
const ORDER: Record<string, number> = { running: 0, accepted: 1, prepared: 2, unknown: 3, refused: 4, exited: 5 }

/** The unit states by unit id, from a reads.work answer. */
export function unitStates(work: ReadAnswer | null): Map<string, string> {
  const states = new Map<string, string>()
  for (const item of work?.items.execution_unit ?? []) {
    const d = item.data as Json
    const state = str(d.state)
    if (state) {
      states.set(item.id, state)
      if (str(d.alias)) states.set(str(d.alias), state)
    }
  }
  return states
}

/** Each unit's state once (the map above also keys units by alias), or null when the work read was refused. */
export function unitStateList(work: ReadAnswer | null): string[] | null {
  if (!work) return null
  return (work.items.execution_unit ?? []).map((item) => str((item.data as Json).state)).filter(Boolean)
}

export function runRow(item: Item, units: Map<string, string>): RunRow {
  const d = item.data as Json
  const contract = obj(d.contract)
  const reservation = obj(contract.reservation)
  const process = obj(d.process)
  // The entity id names the dispatch; the data's own dispatch_id may be served redacted (its random part
  // can look like a secret to the read model's scanner), the id never is.
  const dispatch = item.id.startsWith('dispatch:') ? item.id.slice('dispatch:'.length) : str(d.dispatch_id)
  const unit = str(contract.unit) || dispatch.split('/')[1] || dispatch
  return {
    dispatch,
    unit,
    station: str(contract.station),
    project: str(reservation.project),
    state: str(d.state) || 'unknown',
    host: str(process.host),
    platform: str(process.platform),
    unitState: units.get(unit) ?? null,
  }
}

/** The runs list: live runs first, then by unit. */
export function runRows(workers: ReadAnswer, work: ReadAnswer | null): RunRow[] {
  const units = unitStates(work)
  return (workers.items.dispatch ?? [])
    .map((item) => runRow(item, units))
    .sort((a, b) => (ORDER[a.state] ?? 9) - (ORDER[b.state] ?? 9) || a.unit.localeCompare(b.unit) || a.dispatch.localeCompare(b.dispatch))
}

/** The runs screen's header summary, computed from the rows it shows: how many runs, and how many distinct
 * projects and hosts they ran for and on (a row without a project or host adds nothing to that count). */
export function runsSummary(rows: RunRow[]): { runs: number; projects: number; hosts: number } {
  return {
    runs: rows.length,
    projects: new Set(rows.map((r) => r.project).filter(Boolean)).size,
    hosts: new Set(rows.map((r) => r.host).filter(Boolean)).size,
  }
}
