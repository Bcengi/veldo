import { LIVE_STATES, type RunRow } from '@/features/run/runs'

/** One host the factory's runs were dispatched to, and how many of them are going now. */
export interface HostHealth {
  name: string
  platform: string
  running: number
  runs: number
}

/** The factory at a glance: the andon board's four counts and the hosts. A count the member cannot read
 * (the work read was refused) is null, shown as not readable rather than as zero. */
export interface FactoryCounts {
  running: number
  blocked: number | null
  failed: number | null
  waiting: number
  hosts: HostHealth[]
}

/** Unit states that stop a unit until someone acts (entity_contract). */
export const BLOCKED_STATES = new Set(['AWAITING_AUTHORITY'])
export const FAILED_STATES = new Set(['FAILED'])

export function factoryCounts(rows: RunRow[], unitStates: string[] | null, waiting: number): FactoryCounts {
  const hosts = new Map<string, HostHealth>()
  for (const row of rows) {
    if (!row.host) continue
    const host = hosts.get(row.host) ?? { name: row.host, platform: row.platform, running: 0, runs: 0 }
    host.runs += 1
    if (LIVE_STATES.has(row.state)) host.running += 1
    hosts.set(row.host, host)
  }
  return {
    running: rows.filter((r) => LIVE_STATES.has(r.state)).length,
    blocked: unitStates ? unitStates.filter((s) => BLOCKED_STATES.has(s)).length : null,
    failed: unitStates ? unitStates.filter((s) => FAILED_STATES.has(s)).length : null,
    waiting,
    hosts: [...hosts.values()].sort((a, b) => b.running - a.running || a.name.localeCompare(b.name)),
  }
}
