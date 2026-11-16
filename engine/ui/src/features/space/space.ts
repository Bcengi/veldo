import type { PendingDecision } from '@/features/decisions/inbox'
import type { Watermark } from '@/api/types'

/** The Space screen's reads as the API serves them (control_api_models: space_pools, space_usage, space_pending
 * and space_removed, VELDO-0319). Every figure is a ledger record's; this module only shapes them for the eye. */

export interface SpaceScope {
  type: 'project' | 'plain_repository' | 'no_project'
  id: string | null
}

interface SpaceAnswer {
  schema: string
  view: string
  problems: { id: string; kind: string; refusal: string }[]
  redacted: string[]
  watermark: Watermark
  freshness: 'live' | 'stale'
}

/** A waiting or an advised hold, with the numbers its admission was judged on. */
export interface SpaceHold {
  id: string
  version: number
  state: 'waiting' | 'advised'
  pool: string
  scope: SpaceScope
  need: number | null
  free: number | null
  held: number | null
  floor: number | null
  source: string | null
  /** The run that carries the hold, once a dispatch record names it; a waiting hold has none yet. */
  run: { dispatch: string; unit: string | null; station: string | null } | null
}

export interface SpacePool {
  id: string
  version: number
  name: string
  host: string | null
  type: string | null
  engine: string | null
  backing: string | null
  floor: number | null
  returns_space: boolean | null
  held: number
  waiting: SpaceHold[]
  advised: SpaceHold[]
}
export interface PoolsAnswer extends SpaceAnswer {
  pools: SpacePool[]
}

export interface UsageFigures {
  bytes: number
  items: number
  unmeasured: number
}
export interface UsageKind extends UsageFigures {
  kind: string
  measured_at: string[]
}
export interface UsageTicket extends UsageFigures {
  ticket: string | null
  kinds: UsageKind[]
}
export interface UsageScope extends UsageFigures {
  scope: SpaceScope
  tickets: UsageTicket[]
}
/** A worktree the owner's Abandon can be sent for, at the version the command names. */
export interface SpaceWorktree {
  id: string
  version: number
  state: 'present' | 'kept' | 'deferred'
  owner: SpaceOwner
  locator: string
  branch: string | null
  bytes: number | null
  /** The owner answered Keep for it: nothing reaches it until the owner's Abandon. */
  owner_keep: boolean
}
export interface UsageAnswer extends SpaceAnswer {
  scopes: UsageScope[]
  total: UsageFigures
  worktrees: SpaceWorktree[]
}

export interface SpaceOwner {
  scope: SpaceScope
  ticket: string | null
  run: string | null
  station: string | null
  gate: string | null
  lane: string | null
  session: string | null
}

export interface PendingItem {
  id: string
  version: number
  state: 'due' | 'deferred'
  kind: string
  owner: SpaceOwner
  locator: string
  pool: string | null
  bytes: number | null
  measured_at: string | null
  due_event: string | null
  rule: string | null
  reason: string | null
  refused_at: string | null
  attempts: number | null
  retry: string[]
  request: string | null
  group: string | null
  index: number | null
}
export interface PendingRequest {
  alias: string
  group: string | null
  day: string | null
  sequence: number | null
  /** The member indexes the request offers an answer of their own for (VELDO-0342). */
  picks: number[]
  members: { item: string; index: number | null }[]
}
export interface PendingAnswer extends SpaceAnswer {
  items: PendingItem[]
  requests: PendingRequest[]
}

export interface RemovedItem {
  id: string
  version: number
  kind: string
  owner: SpaceOwner
  locator: string
  pool: string | null
  event: string | null
  emitter: unknown
  method: string | null
  bytes: number | null
  freed: number | null
  free_before: number | null
  free_after: number | null
  host: { pool?: string; freed?: number; free_before?: number; free_after?: number } | null
  kept_refs: number
  snapshots: number
  seq: number | null
  at: number | null
}
export interface RemovedAnswer extends SpaceAnswer {
  items: RemovedItem[]
}

/** The four reads of one screen load, taken one after another; the first one's watermark is the screen's. */
export interface SpaceRead {
  pools: PoolsAnswer
  usage: UsageAnswer
  pending: PendingAnswer
  removed: RemovedAnswer
}

const UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'] as const

/** Bytes as people read them, in binary units with one decimal above a kibibyte: 4.2 GiB, 512 B. A figure
 * that is not a whole number of bytes was not recorded. */
export function bytesText(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return 'not recorded'
  let amount = value
  let unit = 0
  while (amount >= 1024 && unit < UNITS.length - 1) {
    amount /= 1024
    unit += 1
  }
  return unit === 0 ? `${amount} B` : `${amount.toFixed(1)} ${UNITS[unit]}`
}

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`

/** An event, a kind or a rule as words: underscores become spaces. */
export function words(name: string | null | undefined): string {
  return (name ?? '').replace(/_/g, ' ')
}

export function scopeLabel(scope: SpaceScope): string {
  if (scope.type === 'project') return scope.id ?? 'Unnamed project'
  if (scope.type === 'plain_repository') return scope.id ?? 'Unnamed repository'
  return 'No project'
}

/** What kind of row a scope is, beside its name. */
export function scopeKind(scope: SpaceScope): string {
  return scope.type === 'project' ? 'Project' : scope.type === 'plain_repository' ? 'Plain repository' : 'Sessions outside every project'
}

/** The size of a usage row: its bytes, or that nothing in it was ever measured (never a zero that was not read). */
export function sizeText(figures: UsageFigures): string {
  return figures.items > 0 && figures.unmeasured === figures.items ? 'not measured' : bytesText(figures.bytes)
}

export function countText(figures: UsageFigures): string {
  const base = plural(figures.items, 'item', 'items')
  return figures.unmeasured ? `${base}, ${figures.unmeasured} not measured` : base
}

/** One row of the usage table: a scope, a ticket under it or a kind under that. */
export interface UsageRow extends UsageFigures {
  key: string
  level: 0 | 1 | 2
  label: string
  detail: string
}

/** The usage tree as the rows of one table, each scope followed by its tickets and each ticket by its kinds. */
export function usageRows(usage: UsageAnswer | null): UsageRow[] {
  const rows: UsageRow[] = []
  for (const scope of usage?.scopes ?? []) {
    const scopeKey = `${scope.scope.type}:${scope.scope.id ?? ''}`
    rows.push({ key: scopeKey, level: 0, label: scopeLabel(scope.scope), detail: scopeKind(scope.scope), bytes: scope.bytes, items: scope.items, unmeasured: scope.unmeasured })
    for (const ticket of scope.tickets) {
      const ticketKey = `${scopeKey}/${ticket.ticket ?? ''}`
      rows.push({ key: ticketKey, level: 1, label: ticket.ticket ?? 'No ticket', detail: 'Ticket', bytes: ticket.bytes, items: ticket.items, unmeasured: ticket.unmeasured })
      for (const kind of ticket.kinds) {
        rows.push({
          key: `${ticketKey}/${kind.kind}`,
          level: 2,
          label: words(kind.kind),
          detail: kind.measured_at.length ? `measured at ${kind.measured_at.map(words).join(', ')}` : 'never measured',
          bytes: kind.bytes,
          items: kind.items,
          unmeasured: kind.unmeasured,
        })
      }
    }
  }
  return rows
}

/** Whose an item is, in one line: its scope, then its ticket and its run where it has them. */
export function ownerText(owner: SpaceOwner): string {
  const parts = [scopeLabel(owner.scope)]
  if (owner.ticket) parts.push(owner.ticket)
  if (owner.run) parts.push(`run ${owner.run}${owner.station ? ` (${owner.station})` : ''}`)
  else if (owner.gate) parts.push(`gate ${owner.gate}`)
  else if (owner.session) parts.push(`session ${owner.session}`)
  return parts.join(', ')
}

/** Why a pending item is still there, as one sentence. */
export function pendingReason(item: PendingItem): string {
  if (item.state === 'due') return `Due since ${words(item.due_event) || 'an event that was not recorded'}; the removal has not run yet`
  const reason = item.reason ?? 'no reason is recorded'
  return reason.charAt(0).toUpperCase() + reason.slice(1)
}

/** When a deferred item is judged again. */
export function retryText(item: PendingItem): string {
  if (item.state === 'due') return 'At the next event that reaches it'
  if (!item.retry.length) return 'No retry event is recorded'
  return `Retried at ${item.retry.map(words).join(', ')}`
}

/** The four numbers a waiting or advised run was judged on. */
export function holdNumbers(hold: Pick<SpaceHold, 'need' | 'free' | 'held' | 'floor'>): { label: string; value: string }[] {
  return [
    { label: 'Need', value: bytesText(hold.need) },
    { label: 'Free', value: bytesText(hold.free) },
    { label: 'Held', value: bytesText(hold.held) },
    { label: 'Floor', value: bytesText(hold.floor) },
  ]
}

/** One line for a run that waits, or that would have waited, for space. */
export function holdSentence(hold: SpaceHold): string {
  const lead = hold.state === 'waiting' ? 'Waiting for space' : 'Would have waited for space'
  return `${lead} on ${hold.pool}: ${holdNumbers(hold).map((n) => `${n.label.toLowerCase()} ${n.value}`).join(', ')}`
}

/** The runs list's view of the pools read: the advised hold of each run a dispatch record carries, by dispatch,
 * and the waiting holds, which have no dispatch yet. */
export function runHolds(pools: PoolsAnswer | null): { byDispatch: Map<string, SpaceHold>; waiting: SpaceHold[] } {
  const byDispatch = new Map<string, SpaceHold>()
  const waiting: SpaceHold[] = []
  for (const pool of pools?.pools ?? []) {
    for (const hold of [...pool.waiting, ...pool.advised]) {
      if (hold.run) byDispatch.set(hold.run.dispatch, hold)
      else if (hold.state === 'waiting') waiting.push(hold)
    }
  }
  return { byDispatch, waiting }
}

/** A decision request of the pending items with the rows it covers and, when the signed-in member's decisions
 * hold it, the pending decision it is answered through. */
export interface RequestGroup {
  request: PendingRequest
  items: PendingItem[]
  decision: PendingDecision | null
}

/** Pending removal as the screen lists it: each open request with its worktrees under it, in index order, then
 * the items that have no request. A request's rows are found by the alias their own record names. */
export function pendingGroups(pending: PendingAnswer | null, decisions: PendingDecision[]): { requests: RequestGroup[]; rest: PendingItem[] } {
  const items = pending?.items ?? []
  const requests = (pending?.requests ?? []).map((request) => ({
    request,
    items: items
      .filter((item) => item.request === request.alias)
      .sort((a, b) => (a.index ?? 0) - (b.index ?? 0) || a.locator.localeCompare(b.locator)),
    decision: decisions.find((d) => d.alias === request.alias) ?? null,
  }))
  const covered = new Set(requests.flatMap((group) => group.items.map((item) => item.id)))
  return { requests, rest: items.filter((item) => !covered.has(item.id)) }
}

/** The answers a member of a review group has for itself alone, as the request offers them (VELDO-0342):
 * the three picks with the letter w and the member's index. Empty when the request offers that member none. */
export function memberPicks(request: PendingRequest, index: number | null): string[] {
  if (index === null || !request.picks.includes(index)) return []
  return ['save', 'keep', 'discard'].map((choice) => `accept ${choice} w${index}`)
}

/** How a removal changed its pool's free space, and the note for an engine pool whose host figure is apart. */
export function removedSpace(item: RemovedItem): string {
  if (typeof item.free_before !== 'number' || typeof item.free_after !== 'number') return 'Free space was not recorded'
  return `${bytesText(item.free_before)} free before, ${bytesText(item.free_after)} after`
}

export function hostNote(item: RemovedItem): string | null {
  if (!item.host) return null
  if (typeof item.host.free_before === 'number' && typeof item.host.free_after === 'number') {
    const same = item.host.free_before === item.host.free_after
    return same
      ? `The host figure did not change (${bytesText(item.host.free_after)} free on ${item.host.pool ?? 'the host'})`
      : `On ${item.host.pool ?? 'the host'}: ${bytesText(item.host.free_before)} free before, ${bytesText(item.host.free_after)} after`
  }
  return null
}

/** What an accepted Abandon did, in words: what was removed, what waits, and what needs the owner's Discard. */
export function abandonText(answer: { state?: string | null; removed?: string[]; deferred?: { item: string }[]; discard_required?: string[] }): string {
  const parts = [`Abandoned: the worktree is ${words(answer.state) || 'recorded'} now`]
  if (answer.removed?.length) parts.push(`${plural(answer.removed.length, 'item', 'items')} removed`)
  if (answer.deferred?.length) parts.push(`${plural(answer.deferred.length, 'item', 'items')} deferred`)
  if (answer.discard_required?.length) parts.push(`${plural(answer.discard_required.length, 'worktree stays', 'worktrees stay')} until your Discard, which saves first`)
  return `${parts.join('; ')}.`
}

export const isEmpty = (read: SpaceRead) =>
  read.pools.pools.length === 0 && read.usage.total.items === 0 && read.pending.items.length === 0 && read.removed.items.length === 0
