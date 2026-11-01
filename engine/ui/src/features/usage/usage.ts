import type { JournalEvent } from '@/api/events'
import type { ReadAnswer } from '@/api/types'

/** The units a subscription is measured in: what the CLI reports, never a price. */
export const UNITS = ['invocations', 'wall_seconds', 'tokens', 'messages'] as const
export type UsageUnit = (typeof UNITS)[number]

export interface Invocation {
  id: string
  account: string
  /** The account's provider from its account record (VELDO-0062), or '' when the spend read has no record of it. */
  provider: string
  project: string
  unit: string
  dispatch: string
  seq: number | null
  charge: Partial<Record<UsageUnit, number>>
  unknown: UsageUnit[]
  state: string
}

export interface Window {
  account: string
  id: string
  unit: string
  remaining: number | null
  resetAt: number | null
}

export interface AccountView {
  account: string
  /** The provider (claude_code or codex), label and status of the account's record; '' when not recorded. */
  provider: string
  label: string
  status: string
  windows: Window[]
  activeRuns: string[]
  /** When the account can take work again, if a window has run out and not yet reset; null when it can now. */
  blockedUntil: number | null
  totals: Partial<Record<UsageUnit, number>>
  unknown: Partial<Record<UsageUnit, number>>
}

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)
const str = (v: unknown) => (typeof v === 'string' ? v : '')

export interface AccountRecord {
  provider: string
  label: string
  status: string
}

/** The account records of the spend read (kind `account`), by account id. */
export function accountRecords(spend: ReadAnswer | null): Map<string, AccountRecord> {
  const records = new Map<string, AccountRecord>()
  for (const item of spend?.items.account ?? []) {
    const d = item.data as Record<string, unknown>
    const id = str(d.id) || item.id.replace(/^account:/, '')
    records.set(id, { provider: str(d.provider), label: str(d.label), status: str(d.status) })
  }
  return records
}

export function invocationsOf(spend: ReadAnswer | null): Invocation[] {
  const records = accountRecords(spend)
  return (spend?.items.subscription_reservation ?? [])
    .filter((i) => (i.data as { type?: unknown }).type === 'invocation')
    .map((i) => {
      const d = i.data as Record<string, any>
      const context = (d.context ?? {}) as Record<string, unknown>
      const charge: Partial<Record<UsageUnit, number>> = {}
      for (const u of UNITS) {
        const v = num(d.charge?.[u])
        if (v != null) charge[u] = v
      }
      return {
        id: i.id, account: str(context.account), provider: records.get(str(context.account))?.provider ?? '', project: str(context.project), unit: str(context.unit), dispatch: str(d.dispatch),
        seq: num(d.accepted_seq), charge, unknown: (Array.isArray(d.unknown) ? d.unknown : []).filter((u: string) => (UNITS as readonly string[]).includes(u)),
        state: str(d.state),
      }
    })
}

/** Each account's windows, active runs, totals and unknown counts, and when it can work again. */
export function accountsOf(spend: ReadAnswer | null, now: number): AccountView[] {
  const records = (spend?.items.subscription_reservation ?? []).map((i) => i.data as Record<string, any>)
  const known = accountRecords(spend)
  const accounts = new Map<string, AccountView>()
  const get = (account: string) => {
    const record = known.get(account)
    if (!accounts.has(account)) accounts.set(account, { account, provider: record?.provider ?? '', label: record?.label ?? '', status: record?.status ?? '', windows: [], activeRuns: [], blockedUntil: null, totals: {}, unknown: {} })
    return accounts.get(account)!
  }
  for (const r of records) {
    if (r.type === 'policy' && r.scope === 'account') {
      const view = get(str(r.subject))
      for (const w of Object.values((r.windows ?? {}) as Record<string, Record<string, unknown>>))
        view.windows.push({ account: view.account, id: str(w.window_id), unit: str(w.unit), remaining: num(w.remaining), resetAt: num(w.reset_at) })
    } else if (r.type === 'worker' && !r.retired) {
      get(str(r.context?.account)).activeRuns.push(str(r.dispatch))
    }
  }
  for (const inv of invocationsOf(spend)) {
    const view = get(inv.account)
    for (const u of UNITS) {
      if (inv.unknown.includes(u)) view.unknown[u] = (view.unknown[u] ?? 0) + 1
      else if (inv.charge[u] != null) view.totals[u] = (view.totals[u] ?? 0) + inv.charge[u]!
    }
  }
  for (const view of accounts.values()) {
    const blocking = view.windows.filter((w) => w.remaining != null && w.remaining <= 0 && w.resetAt != null && w.resetAt > now)
    view.blockedUntil = blocking.length ? Math.max(...blocking.map((w) => w.resetAt!)) : null
  }
  return [...accounts.values()].sort((a, b) => a.account.localeCompare(b.account))
}

/** "No account until": when every account is blocked, the earliest time one is free again; otherwise null. */
export function noAccountUntil(accounts: AccountView[]): number | null {
  if (!accounts.length || accounts.some((a) => a.blockedUntil == null)) return null
  return Math.min(...accounts.map((a) => a.blockedUntil!))
}

/** The journal's commit time of each sequence, from the events feed (seconds since the epoch). */
export function timesOf(events: JournalEvent[]): Map<number, number> {
  const times = new Map<number, number>()
  for (const e of events) {
    const at = typeof e.committed_at === 'number' ? e.committed_at : Date.parse(String(e.committed_at)) / 1000
    if (Number.isFinite(at)) times.set(e.seq, at)
  }
  return times
}

export interface Bucket {
  start: number
  known: number
  /** Invocations in the bucket whose amount of the unit is not known yet: never counted as zero. */
  unknown: number
  invocations: Invocation[]
}

/** The time series of one unit: invocations bucketed by the hour their reservation was committed. An invocation
 * with no known commit time is left out of the series and counted in `untimed`. */
export function seriesOf(invocations: Invocation[], times: Map<number, number>, unit: UsageUnit, bucketSeconds = 3600) {
  const buckets = new Map<number, Bucket>()
  let untimed = 0
  for (const inv of invocations) {
    const at = inv.seq != null ? times.get(inv.seq) : undefined
    if (at === undefined) {
      untimed += 1
      continue
    }
    const start = Math.floor(at / bucketSeconds) * bucketSeconds
    const b = buckets.get(start) ?? { start, known: 0, unknown: 0, invocations: [] }
    if (inv.unknown.includes(unit) || inv.charge[unit] == null) b.unknown += 1
    else b.known += inv.charge[unit]!
    b.invocations.push(inv)
    buckets.set(start, b)
  }
  return { buckets: [...buckets.values()].sort((a, b) => a.start - b.start), untimed }
}

/** Totals of one unit by a breakdown key, with the unknown count beside each. */
export type BreakdownKey = 'provider' | 'account' | 'project' | 'dispatch'
export function breakdown(invocations: Invocation[], unit: UsageUnit, key: BreakdownKey) {
  const rows = new Map<string, { key: string; known: number; unknown: number; count: number }>()
  for (const inv of invocations) {
    const k = inv[key] || 'not recorded'
    const row = rows.get(k) ?? { key: k, known: 0, unknown: 0, count: 0 }
    row.count += 1
    if (inv.unknown.includes(unit) || inv.charge[unit] == null) row.unknown += 1
    else row.known += inv.charge[unit]!
    rows.set(k, row)
  }
  return [...rows.values()].sort((a, b) => a.key.localeCompare(b.key))
}

/** A value with its unknown part: "1,800 tokens", "1,800 tokens + 3 unknown", "unknown (3)"; never 0 for unknown. */
export function amount(known: number, unknown: number, unit: string): string {
  const words = unit.replace('_', ' ')
  if (unknown && !known) return `unknown (${unknown} invocation${unknown === 1 ? '' : 's'})`
  const base = `${known.toLocaleString('en-US')} ${words}`
  return unknown ? `${base} + ${unknown} unknown` : base
}
