import type { ConversationSummary, ConversationTurn } from '@/api/conversations'
import type { TeamRecord } from '@/api/configuration'
import type { ReadAnswer } from '@/api/types'

/** How many words of a conversation's first message the list shows. */
export const OPENING_WORDS = 12

/** The first words of a conversation's first message, as written (never rendered as markup). */
export function openingWords(text: string | null | undefined, count = OPENING_WORDS): string | null {
  if (typeof text !== 'string') return null
  const words = text.trim().split(/\s+/).filter(Boolean)
  if (!words.length) return null
  return words.slice(0, count).join(' ') + (words.length > count ? ' ...' : '')
}

export interface ListedConversation extends ConversationSummary {
  opening: string | null
}

/** Open conversations first, then closed, each newest activity first. */
export function orderConversations<T extends ConversationSummary>(items: T[]): T[] {
  const rank = (c: T) => (c.status === 'open' ? 0 : 1)
  return [...items].sort(
    (a, b) => rank(a) - rank(b) || (b.last_activity ?? 0) - (a.last_activity ?? 0) || a.id.localeCompare(b.id),
  )
}

export type TurnMarker = 'waiting' | 'running' | 'ended'

/** A turn's marker: waiting for a worker, running, or ended with its outcome. */
export function turnMarker(turn: Pick<ConversationTurn, 'state'>): TurnMarker {
  if (turn.state === 'waiting') return 'waiting'
  if (turn.state === 'dispatched') return 'running'
  return 'ended'
}

/** The turn still in flight (waiting or running), the newest one when several are. */
export function currentTurn(turns: ConversationTurn[]): ConversationTurn | null {
  const live = turns.filter((t) => turnMarker(t) !== 'ended')
  return live.length ? live[live.length - 1]! : null
}

/** The default team's role names, sorted, with the current one present even if the team no longer has it. */
export function teamRoles(team: TeamRecord | null, current: string | null): string[] {
  const names = new Set(Object.keys(team?.team?.roles ?? {}))
  if (current) names.add(current)
  return [...names].sort()
}

/** The projects of the member's scope, by name, from the objectives read (its project items). */
export function scopeProjects(answer: ReadAnswer | null): string[] {
  const items = answer?.items?.project ?? []
  const names = items.map((item) => {
    const name = (item.data as Record<string, unknown>).name
    return typeof name === 'string' && name ? name : item.id.replace(/^project:/, '')
  })
  return [...new Set(names)].sort()
}

/** A time as the owner reads it: the clock today, else the day and the clock. */
export function activityTime(at: number | null, now = Date.now()): string {
  if (at === null || at === undefined) return 'no activity yet'
  const date = new Date(at * 1000)
  const today = new Date(now)
  const clock = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  if (date.toDateString() === today.toDateString()) return clock
  return `${date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} ${clock}`
}
