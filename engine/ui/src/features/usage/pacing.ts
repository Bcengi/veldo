import type { ReadAnswer } from '@/api/types'

/** VELDO-0236: the owner's pacing of each account, read from the spend read's account records (their windows, pause
 * and ceilings) and its pacing history (the journal's own records). A pause or ceiling past its end is out of force
 * and is not shown as one: it ended at its window's reset with no command. */

export interface PaceWindow {
  id: string
  /** The window's last observed utilization as a percent, or null when the engine reported none. */
  utilization: number | null
  resetAt: number | null
}

export interface Pause {
  window: string
  until: number
}

export interface Ceiling {
  window: string
  value: number
  until: number
  /** The utilization percent the ceiling was read against when it was set. */
  readAt: number | null
}

export interface AccountPacing {
  account: string
  label: string
  status: string
  windows: PaceWindow[]
  pause: Pause | null
  ceilings: Ceiling[]
}

export interface PacingEvent {
  seq: number
  type: string
  account: string
  window: string
  until: number | null
  value: number | null
  principal: string
  route: string
  ended: { kind: string; window: string }[]
}

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)
const str = (v: unknown) => (typeof v === 'string' ? v : '')

/** A reported fraction as a percent, as control_accounts.percent does. */
export function percentOf(utilization: unknown): number | null {
  const u = num(utilization)
  return u == null ? null : Math.round(u * 100 * 1e6) / 1e6
}

/** Each account's windows with utilization and reset, and its pause and ceilings in force at `now` (seconds). */
export function pacingOf(spend: ReadAnswer | null, now: number): AccountPacing[] {
  const found: AccountPacing[] = []
  for (const item of spend?.items.account ?? []) {
    const d = item.data as Record<string, any>
    const windows: PaceWindow[] = Object.entries((d.windows ?? {}) as Record<string, Record<string, unknown>>)
      .map(([id, w]) => ({ id, utilization: percentOf(w.utilization), resetAt: num(w.reset_at) }))
      .sort((a, b) => a.id.localeCompare(b.id))
    const p = d.pause as Record<string, unknown> | null | undefined
    const pauseUntil = num(p?.until)
    const pause = p && pauseUntil != null && pauseUntil > now ? { window: str(p.window), until: pauseUntil } : null
    const ceilings: Ceiling[] = []
    for (const [window, c] of Object.entries((d.ceilings ?? {}) as Record<string, Record<string, unknown>>)) {
      const until = num(c.until)
      const value = num(c.value)
      if (until != null && value != null && until > now) ceilings.push({ window, value, until, readAt: num(c.utilization) })
    }
    ceilings.sort((a, b) => a.window.localeCompare(b.window))
    found.push({ account: str(d.id) || item.id.replace(/^account:/, ''), label: str(d.label), status: str(d.status), windows, pause, ceilings })
  }
  return found.sort((a, b) => a.account.localeCompare(b.account))
}

/** The pacing history of the read, in journal order: every pause, ceiling, resume and end. */
export function historyOf(spend: ReadAnswer | null): PacingEvent[] {
  return (spend?.pacing ?? [])
    .map((e) => ({
      seq: num(e.seq) ?? 0, type: str(e.type), account: str(e.account), window: str(e.window), until: num(e.until),
      value: num(e.value), principal: str(e.principal), route: str(e.route),
      ended: (Array.isArray(e.ended) ? e.ended : []).map((x: Record<string, unknown>) => ({ kind: str(x.kind), window: str(x.window) })),
    }))
    .sort((a, b) => a.seq - b.seq)
}

/** The ceiling the owner typed: a percent from 1 to 100 as a number, +N kept as the relative text; null otherwise. */
export function ceilingValue(text: string): number | string | null {
  const t = text.trim()
  const relative = /^\+\d+(\.\d+)?$/.test(t)
  if (!relative && !/^\d+(\.\d+)?$/.test(t)) return null
  const n = Number(t.replace('+', ''))
  if (relative) return n > 0 && n <= 100 ? t : null
  return n >= 1 && n <= 100 ? n : null
}

/** Whether a window can take a ceiling: one with an observed utilization and a reset ahead. */
export function canCap(window: PaceWindow, now: number): boolean {
  return window.utilization != null && window.resetAt != null && window.resetAt > now
}

/** Whether a window can be paused on: one whose reset is ahead. */
export function canPause(window: PaceWindow, now: number): boolean {
  return window.resetAt != null && window.resetAt > now
}

/** One history record in words. */
export function eventWords(e: PacingEvent, when: (seconds: number) => string): string {
  const by = e.route ? ` (${e.principal}, ${e.route})` : ''
  if (e.type === 'pause') return `${e.account} paused until ${e.until != null ? when(e.until) : 'its reset'}, when its ${e.window} window resets${by}`
  if (e.type === 'ceiling') return `${e.account} capped at ${e.value} percent of ${e.window} until ${e.until != null ? when(e.until) : 'its reset'}${by}`
  if (e.type === 'resume') return `${e.account} resumed${e.ended.length ? `: ${e.ended.map((x) => `${x.kind} on ${x.window}`).join(', ')} ended` : ''}${by}`
  return `${e.account}: ${e.ended.map((x) => x.kind).join(' and ') || 'nothing'} on ${e.window} ended at ${e.until != null ? when(e.until) : 'its reset'}`
}
