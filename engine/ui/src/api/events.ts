import { request, routeUrl } from './client'
import type { Watermark } from './types'

/** One committed journal record as the events feed serves it: identities and kinds only, never data. */
export interface JournalEvent {
  seq: number
  command_id: string
  record_digest: string
  committed_at: number | null
  entities: { id: string; kind: string | null }[]
}
export interface EventsPage {
  schema: string
  after: number
  events: JournalEvent[]
  watermark: Pick<Watermark, 'seq' | 'record_digest'>
  publication: { watermark: number; head: number; pending_records: number; freshness: 'live' | 'stale' }
  cursor?: number
}

/** One page of the committed journal records after `after` (events.read). */
export const readEvents = (after: number, signal?: AbortSignal) =>
  request<EventsPage>('events.read', { fields: { after }, signal })

export interface EventStreamHandlers {
  /** A page of committed records the member may see. The screens re-read their models; nothing is applied
   * from the frame itself. */
  frame(page: EventsPage): void
  closed(reason: string): void
  dropped(retrying: boolean): void
}

/** Follow the committed journal live from `after` (events.stream). The browser resends the last frame's id
 * as Last-Event-ID when it reconnects, and the API resumes after it. */
export function openEventStream(after: number, on: EventStreamHandlers): { close(): void } {
  const source = new EventSource(routeUrl('events.stream', { after }))
  let done = false
  const finish = () => {
    done = true
    source.close()
  }
  source.addEventListener('events', (event) => {
    if (!done) on.frame(JSON.parse((event as MessageEvent<string>).data) as EventsPage)
  })
  source.addEventListener('closed', (event) => {
    if (done) return
    finish()
    let reason = 'closed'
    try {
      reason = String((JSON.parse((event as MessageEvent<string>).data) as { reason?: string }).reason ?? reason)
    } catch {
      /* the reason stays generic */
    }
    on.closed(reason)
  })
  source.addEventListener('error', () => {
    if (done) return
    const retrying = source.readyState === EventSource.CONNECTING
    if (!retrying) finish()
    on.dropped(retrying)
  })
  return { close: finish }
}
