import { recordStreamUrl } from './runs'
import type { RecordPage } from './types'

export interface RecordStreamHandlers {
  frame(page: RecordPage): void
  /** The API closed the stream and named why: ended, signed_out, session_expired, revoked, slow_reader. */
  closed(reason: string): void
  /** The connection dropped; `retrying` is true while the browser reconnects from the last frame's id. */
  dropped(retrying: boolean): void
  opened(): void
}

export interface RecordStream {
  close(): void
}

/** Follow one run's record live from `after` (runs.record_stream). The browser resends the last frame's
 * id as Last-Event-ID when it reconnects, and the API resumes after it. */
export function openRecordStream(dispatch: string, after: number, on: RecordStreamHandlers): RecordStream {
  const source = new EventSource(recordStreamUrl(dispatch, after), { withCredentials: false })
  let done = false
  const finish = () => {
    done = true
    source.close()
  }
  source.addEventListener('open', () => on.opened())
  source.addEventListener('record', (event) => {
    if (done) return
    on.frame(JSON.parse((event as MessageEvent<string>).data) as RecordPage)
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
