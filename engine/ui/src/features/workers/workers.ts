import type { Item, ReadAnswer } from '@/api/types'

/** One worker run on a machine, from its dispatch record (reads.workers). */
export interface WorkerCard {
  dispatch: string
  /** The dispatch record's version, which a stop names. */
  version: number
  /** What the worker runs with, from its contract's capability: the adapter, then the configuration's role,
   * servers and tools when it names them. */
  capability: string
  unit: string
  station: string
  project: string
  account: string
  state: string
  running: boolean
  pid: number | null
  recordLines: number | null
  /** The owner's stop request as the dispatch record holds it (VELDO-0131), or null when none was made. */
  stop: StopState | null
}

/** A stop request read from the dispatch record: who asked, and whether the runner has asked the receiver yet. */
export interface StopState {
  by: string
  at: number | null
  /** true: the receiver was asked to stop; false: the runner held no receiver to ask; null: not asked yet. */
  asked: boolean | null
}

/** One account's run cap, from its account record in the spend read (VELDO-0062, set by VELDO-0131's command). */
export interface AccountCap {
  account: string
  label: string
  provider: string
  /** The record's version, which a cap change names. */
  version: number
  concurrency: number | null
  /** Each recorded change, newest last: the new cap, the previous one, who and when. */
  history: { concurrency: number; previous: number | null; by: string; at: number | null }[]
}

/** The lowest and highest run cap the account command accepts (control_accounts.CAP_LIMIT). */
export const CAP_MIN = 1
export const CAP_MAX = 16

/** Whether a typed cap is a whole number the command accepts. */
export function capValue(text: string): number | null {
  if (!/^\d{1,2}$/.test(text.trim())) return null
  const value = Number(text.trim())
  return value >= CAP_MIN && value <= CAP_MAX ? value : null
}

/** Every account record of the spend read with its cap, by account id. */
export function capsOf(spend: ReadAnswer | null): AccountCap[] {
  return (spend?.items.account ?? [])
    .map((item) => {
      const d = item.data as Record<string, any>
      const history = Array.isArray(d.concurrency_history) ? d.concurrency_history : []
      return {
        account: typeof d.id === 'string' && d.id ? d.id : item.id.replace(/^account:/, ''),
        label: typeof d.label === 'string' ? d.label : '',
        provider: typeof d.provider === 'string' ? d.provider : '',
        version: item.version,
        concurrency: typeof d.concurrency === 'number' ? d.concurrency : null,
        history: history.map((h: Record<string, any>) => ({
          concurrency: Number(h.concurrency), previous: typeof h.previous === 'number' ? h.previous : null,
          by: String(h.by ?? ''), at: typeof h.at === 'number' ? h.at : null,
        })),
      }
    })
    .sort((a, b) => a.account.localeCompare(b.account))
}

function stopOf(d: Record<string, any>): StopState | null {
  const request = d.stop_request
  if (!request || typeof request !== 'object') return null
  const result = request.result && typeof request.result === 'object' ? request.result : null
  return { by: String(request.by ?? ''), at: typeof request.at === 'number' ? request.at : null,
    asked: result && typeof result.asked === 'boolean' ? result.asked : null }
}

export interface Machine {
  platform: string
  /** Linux or Mac, as the owner reads it; anything else keeps its recorded name. */
  family: string
  host: string
  workers: WorkerCard[]
  running: number
}

const FAMILY: Record<string, string> = { linux: 'Linux', darwin: 'Mac', mac: 'Mac', macos: 'Mac' }

export function familyOf(platform: string | null | undefined): string {
  if (!platform) return 'Unknown platform'
  return FAMILY[platform.toLowerCase()] ?? platform
}

/** The capability sentence of a dispatch contract (control_launch: {adapter, configuration, configuration_digest}). */
export function capabilityOf(contract: Record<string, any>): string {
  const capability = (contract.capability ?? null) as Record<string, any> | null
  if (!capability || typeof capability !== 'object') return ''
  const configuration = (capability.configuration ?? {}) as Record<string, any>
  const parts: string[] = []
  if (typeof capability.adapter === 'string') parts.push(capability.adapter)
  if (typeof configuration.role === 'string') {
    parts.push(`role ${configuration.role}${configuration.revision != null ? ` r${String(configuration.revision)}` : ''}`)
  }
  const names = (list: unknown, key: string) =>
    Array.isArray(list) ? list.map((x) => (x && typeof x === 'object' ? (x as Record<string, unknown>)[key] : x)).filter((x): x is string => typeof x === 'string') : []
  const servers = names(configuration.mcp, 'server')
  const tools = names(configuration.native_tools, 'name')
  if (servers.length) parts.push(`servers ${servers.join(', ')}`)
  if (tools.length) parts.push(`tools ${tools.join(', ')}`)
  return parts.join('; ')
}

function card(item: Item): WorkerCard {
  const d = item.data as Record<string, any>
  const contract = (d.contract ?? {}) as Record<string, any>
  const reservation = (contract.reservation ?? {}) as Record<string, any>
  const process = (d.process ?? {}) as Record<string, any>
  const record = (d.execution_record ?? null) as Record<string, any> | null
  return {
    // The entity id carries the dispatch id whole; inside the data the API's secret scanner may redact its
    // random suffix (a high-entropy string), so the id is the one to link and to follow.
    dispatch: item.id.replace(/^dispatch:/, ''),
    version: item.version,
    capability: capabilityOf(contract),
    unit: String(contract.unit ?? 'unknown unit'),
    station: String(contract.station ?? ''),
    project: String(reservation.project ?? ''),
    account: String(reservation.account ?? ''),
    state: String(d.state ?? 'unknown'),
    running: d.state === 'running',
    pid: typeof process.pid === 'number' ? process.pid : null,
    recordLines: record && typeof record.lines === 'number' ? record.lines : null,
    stop: stopOf(d),
  }
}

/** The machines of the API's workers read, grouped as it grouped them (by recorded platform and host), with each
 * machine's worker runs, running ones first. A dispatch with no recorded process is on no machine. */
export function machinesOf(answer: ReadAnswer | null): Machine[] {
  if (!answer) return []
  const dispatches = new Map((answer.items.dispatch ?? []).map((i) => [i.id, i]))
  const machines = ((answer as unknown as { machines?: { platform: string; host: string; workers: string[] }[] }).machines ?? [])
  return machines.map((m) => {
    const workers = m.workers.map((id) => dispatches.get(id)).filter((i): i is Item => !!i).map(card)
    workers.sort((a, b) => Number(b.running) - Number(a.running) || a.unit.localeCompare(b.unit))
    return { platform: m.platform, family: familyOf(m.platform), host: m.host, workers, running: workers.filter((w) => w.running).length }
  })
}

/** Machines grouped by family (Linux, Mac, ...), families in that order. */
export function familiesOf(machines: Machine[]): { family: string; machines: Machine[] }[] {
  const order = ['Linux', 'Mac']
  const families = new Map<string, Machine[]>()
  for (const m of machines) families.set(m.family, [...(families.get(m.family) ?? []), m])
  return [...families.entries()]
    .sort(([a], [b]) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99) || a.localeCompare(b))
    .map(([family, list]) => ({ family, machines: list }))
}
