import type { AnswerBody } from '@/api/decisions'
import type { Item, ReadAnswer } from '@/api/types'

/** An assignment's states in which it still waits on its owner (control_assignment). */
export const PENDING_STATES = new Set(['OFFERED', 'ACCEPTED', 'IN_PROGRESS'])

/** The presentation of a request exactly as it was shown (control_channel_presentation's receipt). */
export interface Presentation {
  id: string
  requestId: string
  requestVersion: number
  version: number
  digest: string
  question: string
  choices: string[]
  rulings: string[]
  risk: string
  authority: string
  framedBy: string
  owner: string
  channel: string
  /** The text the channel showed, part by part, exactly. */
  rendered: string[]
  publishedAt: number | null
}

export interface PendingDecision {
  requestId: string
  alias: string
  requestVersion: number
  state: string
  owner: string
  scope: string[]
  deadline: string | null
  requestedBy: string
  brief: string
  /** The current presentation, or null when the request has not been presented yet. */
  presentation: Presentation | null
}

type Json = Record<string, unknown>
const str = (v: unknown) => (typeof v === 'string' ? v : '')
const num = (v: unknown) => (typeof v === 'number' ? v : 0)
const strings = (v: unknown) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

function presentationOf(item: Item): Presentation {
  const d = item.data as Json
  const request = (d.request ?? {}) as Json
  return {
    id: str(d.presentation_id) || item.id,
    requestId: str(d.request_id),
    requestVersion: num(d.request_version),
    version: num(d.presentation_version),
    digest: str(d.brief_digest),
    question: str(request.brief),
    choices: strings(d.choices),
    rulings: strings(d.rulings),
    risk: str(d.risk_statement),
    authority: str(d.authority_statement),
    framedBy: str(d.framed_by),
    owner: str(d.owner),
    channel: str(d.channel),
    rendered: strings(d.rendered),
    publishedAt: typeof d.published_at === 'number' ? d.published_at : null,
  }
}

/**
 * The pending decisions of one reads.decisions answer, each with its current presentation: the published
 * receipt for the request's current version with the highest presentation version. A request with none
 * is listed without one, so it is seen but cannot be answered.
 */
export function pendingDecisions(answer: ReadAnswer): PendingDecision[] {
  const assignments = answer.items.assignment ?? []
  const receipts = (answer.items.channel_presentation ?? []).filter((r) => (r.data as Json).outcome === 'published')
  const out: PendingDecision[] = []
  for (const item of assignments) {
    const d = item.data as Json
    if (!PENDING_STATES.has(str(d.state)) || str(d.kind) !== 'decision') continue
    const version = num(d.request_version)
    const current = receipts
      .filter((r) => str((r.data as Json).request_id) === item.id && num((r.data as Json).request_version) === version)
      .map(presentationOf)
      .sort((a, b) => b.version - a.version)[0]
    out.push({
      requestId: item.id,
      alias: str(d.alias) || item.id,
      requestVersion: version,
      state: str(d.state),
      owner: str(d.owner),
      scope: strings(d.scope),
      deadline: str(d.deadline) || null,
      requestedBy: str(d.requested_by),
      brief: str(d.brief),
      presentation: current ?? null,
    })
  }
  return out
}

export type Urgency = 'overdue' | 'today' | 'soon' | 'later' | 'none'
export type RiskLevel = 'high' | 'medium' | 'low' | 'unknown'

const HOUR = 3600_000
const URGENCY_RANK: Record<Urgency, number> = { overdue: 0, today: 1, soon: 2, later: 3, none: 4 }
const RISK_RANK: Record<RiskLevel, number> = { high: 0, medium: 1, low: 2, unknown: 3 }

/** How soon a deadline falls: past it, within a day, within three days, later, or no deadline. */
export function urgencyOf(deadline: string | null, now: number): Urgency {
  if (!deadline) return 'none'
  const at = Date.parse(deadline)
  if (Number.isNaN(at)) return 'none'
  const left = at - now
  if (left < 0) return 'overdue'
  if (left < 24 * HOUR) return 'today'
  if (left < 72 * HOUR) return 'soon'
  return 'later'
}

/** The risk level a framed risk statement opens with ("High: ...", "Low: ..."), else unknown. */
export function riskOf(statement: string | null | undefined): RiskLevel {
  const head = (statement ?? '').trim().toLowerCase()
  for (const level of ['high', 'medium', 'low'] as const) if (head.startsWith(level)) return level
  return 'unknown'
}

/** A deadline as people say it: "due in 3 d", "due in 5 h", "due in 20 min", "overdue by 2 h". */
export function dueText(deadline: string | null, now: number): string | null {
  if (!deadline) return null
  const at = Date.parse(deadline)
  if (Number.isNaN(at)) return null
  const left = at - now
  const span = Math.abs(left)
  const amount = span >= 48 * HOUR ? `${Math.round(span / (24 * HOUR))} d` : span >= HOUR ? `${Math.round(span / HOUR)} h` : `${Math.max(1, Math.round(span / 60_000))} min`
  return left < 0 ? `overdue by ${amount}` : `due in ${amount}`
}

/** The inbox's order: the most urgent deadline first, then the higher risk, then the earlier deadline. A
 * request not presented yet cannot be answered, so it goes last. */
export function rankDecisions(list: PendingDecision[], now: number): PendingDecision[] {
  const key = (d: PendingDecision) => [
    d.presentation ? 0 : 1,
    URGENCY_RANK[urgencyOf(d.deadline, now)],
    RISK_RANK[riskOf(d.presentation?.risk)],
    d.deadline ? Date.parse(d.deadline) || Infinity : Infinity,
  ]
  return [...list].sort((a, b) => {
    const ka = key(a)
    const kb = key(b)
    for (let i = 0; i < ka.length; i += 1) if (ka[i] !== kb[i]) return ka[i]! - kb[i]!
    return a.alias.localeCompare(b.alias)
  })
}

/** The decision that has waited longest: the earliest published presentation. */
export function oldestDecision(list: PendingDecision[]): PendingDecision | null {
  const presented = list.filter((d) => d.presentation)
  if (!presented.length) return null
  return presented.reduce((a, b) => ((b.presentation!.publishedAt ?? Infinity) < (a.presentation!.publishedAt ?? Infinity) ? b : a))
}

/** The answer to one presentation exactly as shown: its request, versions and digest, the choice and why. */
export function answerBody(shown: Presentation, choice: string, rationale: string): AnswerBody {
  return {
    request_id: shown.requestId,
    request_version: shown.requestVersion,
    presentation_id: shown.id,
    presentation_digest: shown.digest,
    presentation_version: shown.version,
    choice,
    rationale,
  }
}

/** A choice as people read it: underscores become spaces. The value sent is always the choice itself. */
export function choiceLabel(choice: string): string {
  const text = choice.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}
