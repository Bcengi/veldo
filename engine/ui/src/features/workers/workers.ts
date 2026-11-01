import type { Item, ReadAnswer } from '@/api/types'

/** One worker run on a machine, from its dispatch record (reads.workers). */
export interface WorkerCard {
  dispatch: string
  unit: string
  station: string
  project: string
  account: string
  state: string
  running: boolean
  pid: number | null
  recordLines: number | null
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

function card(item: Item): WorkerCard {
  const d = item.data as Record<string, any>
  const contract = (d.contract ?? {}) as Record<string, any>
  const reservation = (contract.reservation ?? {}) as Record<string, any>
  const process = (d.process ?? {}) as Record<string, any>
  const record = (d.execution_record ?? null) as Record<string, any> | null
  return {
    dispatch: String(d.dispatch_id ?? item.id.replace(/^dispatch:/, '')),
    unit: String(contract.unit ?? 'unknown unit'),
    station: String(contract.station ?? ''),
    project: String(reservation.project ?? ''),
    account: String(reservation.account ?? ''),
    state: String(d.state ?? 'unknown'),
    running: d.state === 'running',
    pid: typeof process.pid === 'number' ? process.pid : null,
    recordLines: record && typeof record.lines === 'number' ? record.lines : null,
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
