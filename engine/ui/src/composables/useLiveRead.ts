import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { openEventStream } from '@/api/events'
import { ApiRefusal } from '@/api/refusal'
import type { Watermark } from '@/api/types'
import { useSessionStore } from '@/stores/session'
import { useAsync } from './useAsync'

const SESSION_ENDS = new Set(['signed_out', 'session_expired', 'revoked'])

export type LiveState = 'idle' | 'live' | 'reconnecting' | 'stopped'

/** A screen's read that stays current (VELDO-0131 AC2): the read model is loaded, then the committed journal is
 * followed (events.stream) from the watermark the read was taken at, and every frame re-reads the model. What
 * the screen shows is always the API's latest read, never a frame applied locally. `watermarkOf` names the
 * read's watermark; the time it was read and its freshness stay beside the data. */
export function useLiveRead<T>(
  load: (signal: AbortSignal) => Promise<T>,
  watermarkOf: (data: T) => Pick<Watermark, 'seq'> | null,
  isEmpty: (data: T) => boolean = () => false,
) {
  const session = useSessionStore()
  const read = useAsync(load, isEmpty)
  const live = ref<LiveState>('idle')
  const readAt = shallowRef<number | null>(null)
  let stream: { close(): void } | null = null
  let queued: Promise<void> = Promise.resolve()
  let stopped = false

  async function reread() {
    await read.run()
    if (read.state.value === 'ready' || read.state.value === 'empty') readAt.value = Date.now()
  }

  function follow(after: number) {
    stream?.close()
    stream = openEventStream(after, {
      frame(page) {
        live.value = 'live'
        if (page.events.length) queued = queued.then(reread)
      },
      closed(reason) {
        stream = null
        if (SESSION_ENDS.has(reason)) {
          live.value = 'stopped'
          session.end(new ApiRefusal(401, `unauthenticated:${reason}`, 'unauthenticated'))
        } else if (!stopped) {
          live.value = 'reconnecting'
          queued = queued.then(reread).then(() => follow(currentSeq()))
        }
      },
      dropped(retrying) {
        live.value = retrying ? 'reconnecting' : 'stopped'
        if (retrying) queued = queued.then(reread)
      },
    })
  }

  function currentSeq(): number {
    const data = read.data.value
    return data ? (watermarkOf(data)?.seq ?? 0) : 0
  }

  async function start() {
    stopped = false
    await reread()
    if (read.state.value === 'error' || stopped) return
    live.value = 'live'
    follow(currentSeq())
  }

  function stop() {
    stopped = true
    stream?.close()
    stream = null
    live.value = 'stopped'
  }

  onBeforeUnmount(stop)
  return { state: read.state, data: read.data, refusal: read.refusal, live, readAt, start, stop, refresh: reread }
}
