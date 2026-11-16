import type { Item, ReadAnswer } from '@/api/types'
import { runHolds, scopeLabel, type PoolsAnswer, type SpaceHold } from '@/features/space/space'

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
  /** VELDO-0319: the run's hold when it would have waited for space (report mode: it was started on advice),
   * with need, free, held and floor as the ledger recorded them; null for every other run. */
  space?: SpaceHold | null
}

/** VELDO-0319: the state of a row that is a run waiting for space. Admission is asked before a dispatch is
 * prepared, so such a run has a hold and no dispatch yet: the row has no run to open. It is not a live state. */
export const SPACE_WAIT = 'space_wait'

type Json = Record<string, unknown>
const str = (v: unknown) => (typeof v === 'string' ? v : '')
const obj = (v: unknown): Json => (typeof v === 'object' && v !== null && !Array.isArray(v) ? (v as Json) : {})

export const LIVE_STATES = new Set(['prepared', 'accepted', 'running'])
const ORDER: Record<string, number> = { running: 0, accepted: 1, prepared: 2, [SPACE_WAIT]: 2.5, unknown: 3, refused: 4, exited: 5 }

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

export function runRow(item: Item, units: Map<string, string>, holds: Map<string, SpaceHold> = new Map()): RunRow {
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
    space: holds.get(dispatch) ?? null,
  }
}

/** The row of a run that waits for space: its hold names the project it belongs to and the numbers it was
 * judged on; the unit is on no record until the run is dispatched. */
export function waitingRow(hold: SpaceHold): RunRow {
  return { dispatch: '', unit: 'Not dispatched yet', station: '', project: scopeLabel(hold.scope), state: SPACE_WAIT, host: '', platform: '', unitState: null, space: hold }
}

/** The runs list: live runs first, then the runs that wait for space, then by unit. */
export function runRows(workers: ReadAnswer, work: ReadAnswer | null, pools: PoolsAnswer | null = null): RunRow[] {
  const units = unitStates(work)
  const holds = runHolds(pools)
  return (workers.items.dispatch ?? [])
    .map((item) => runRow(item, units, holds.byDispatch))
    .concat(holds.waiting.map(waitingRow))
    .sort((a, b) => (ORDER[a.state] ?? 9) - (ORDER[b.state] ?? 9) || a.unit.localeCompare(b.unit) || a.dispatch.localeCompare(b.dispatch) || (a.space?.id ?? '').localeCompare(b.space?.id ?? ''))
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
