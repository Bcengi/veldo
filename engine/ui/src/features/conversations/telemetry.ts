import { reactive } from 'vue'
import { ApiRefusal } from '@/api/refusal'
import type { RouteName } from '@/api/routes'

/**
 * The conversation screens' client log, metrics and traces (VELDO-0179 observability). The log keeps each API
 * call's route, outcome and latency; never a message's text, a reply or a session cookie. The metrics count what
 * the screens sent; the traces join each message sent to the turn it became and the record the screen followed.
 * Kept in memory only and readable as `window.__veldoConversations` for the operator's console.
 */
export interface LogEntry {
  at: number
  route: RouteName
  outcome: string
  ms: number
}

export interface Trace {
  api_request_id: string | null
  conversation: string
  sequence: number | null
  dispatch: string | null
}

export const METRICS = [
  'messages_sent',
  'conversations_opened',
  'conversations_closed',
  'role_changes',
  'project_attaches',
  'terminal_reconnects',
] as const
export type Metric = (typeof METRICS)[number]

const LIMIT = 200

export const telemetry = reactive({
  log: [] as LogEntry[],
  metrics: Object.fromEntries(METRICS.map((m) => [m, 0])) as Record<Metric, number>,
  traces: [] as Trace[],
})

if (typeof window !== 'undefined') (window as unknown as { __veldoConversations: typeof telemetry }).__veldoConversations = telemetry

/** Run one API call of a conversation screen and log its route, outcome (ok or the refusal's name) and latency. */
export async function logged<T>(route: RouteName, call: () => Promise<T>): Promise<T> {
  const started = performance.now()
  let outcome = 'ok'
  try {
    return await call()
  } catch (error) {
    outcome = error instanceof ApiRefusal ? error.refusal : (error as Error)?.name === 'AbortError' ? 'aborted' : 'unavailable:network'
    throw error
  } finally {
    telemetry.log.push({ at: Date.now(), route, outcome, ms: Math.round(performance.now() - started) })
    if (telemetry.log.length > LIMIT) telemetry.log.splice(0, telemetry.log.length - LIMIT)
  }
}

export function count(metric: Metric, by = 1) {
  telemetry.metrics[metric] += by
}

/** A message sent from the screen: its trace, joined to its turn and record as the screen learns them. `after` is
 * the newest turn sequence the screen had read when it sent. */
export function traceSent(conversation: string, apiRequestId: string | null, after: number): Trace {
  const trace: Trace = { api_request_id: apiRequestId, conversation, sequence: null, dispatch: null }
  telemetry.traces.push(trace)
  if (telemetry.traces.length > LIMIT) telemetry.traces.splice(0, telemetry.traces.length - LIMIT)
  pending.set(telemetry.traces[telemetry.traces.length - 1]!, after)
  return telemetry.traces[telemetry.traces.length - 1]!
}

const pending = new WeakMap<Trace, number>()

/** Join each unjoined trace of a conversation to the first turn after the one it was sent after that no other trace
 * holds, and every joined trace to the dispatch its turn ran as. */
export function joinTraces(conversation: string, turns: { sequence: number; dispatch_id: string | null }[]) {
  const mine = telemetry.traces.filter((t) => t.conversation === conversation)
  const held = new Set(mine.map((t) => t.sequence).filter((s): s is number => s !== null))
  for (const trace of mine) {
    if (trace.sequence !== null) continue
    const after = pending.get(trace) ?? 0
    const turn = turns.find((t) => t.sequence > after && !held.has(t.sequence))
    if (!turn) continue
    trace.sequence = turn.sequence
    held.add(turn.sequence)
  }
  for (const trace of mine) {
    const turn = trace.sequence === null ? undefined : turns.find((t) => t.sequence === trace.sequence)
    if (turn?.dispatch_id) trace.dispatch = turn.dispatch_id
  }
}
