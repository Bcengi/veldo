import { onScopeDispose, reactive, ref, shallowRef } from 'vue'
import { openRecordStream, type RecordStream } from '@/api/record-stream'
import { ApiRefusal } from '@/api/refusal'
import { readRecord } from '@/api/runs'
import { useSessionStore } from '@/stores/session'
import { applyPage, emptyRecord, type RecordState } from './record'

export type FollowState = 'loading' | 'live' | 'reconnecting' | 'ended' | 'stopped' | 'error'

/** The session-ending close reasons of a stream, as the API names them. */
const SESSION_ENDS = new Set(['signed_out', 'session_expired', 'revoked'])

/**
 * Follow one run's execution record: read it from the start, then follow it live from the cursor, applying
 * every line exactly once in sequence. A gap is filled by reading from the cursor; a repeat is dropped.
 */
export function useRecordFollower(dispatch: () => string) {
  const record = reactive<RecordState>(emptyRecord())
  const state = ref<FollowState>('loading')
  const refusal = shallowRef<ApiRefusal | null>(null)
  const stats = reactive({ reconnects: 0, repeats: 0, gapsFilled: 0 })
  const session = useSessionStore()
  let stream: RecordStream | null = null
  let generation = 0
  let filling: Promise<void> = Promise.resolve()

  async function catchUp(id: string, mine: number) {
    for (;;) {
      const page = await readRecord(id, record.cursor)
      if (mine !== generation) return
      const applied = applyPage(record, page)
      stats.repeats += applied.repeats
      if (applied.added === 0 || record.cursor >= page.total) return
    }
  }

  function fail(error: unknown, mine: number) {
    if (mine !== generation) return
    stream?.close()
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
    state.value = 'error'
  }

  function follow(id: string, mine: number) {
    stream = openRecordStream(id, record.cursor, {
      opened() {
        if (mine === generation && state.value === 'reconnecting') state.value = 'live'
      },
      frame(page) {
        filling = filling.then(async () => {
          if (mine !== generation) return
          let applied = applyPage(record, page)
          stats.repeats += applied.repeats
          if (applied.gapAfter !== null) {
            stats.gapsFilled += 1
            await catchUp(id, mine)
            applied = applyPage(record, page)
            stats.repeats += applied.repeats
          }
          if (state.value === 'reconnecting') state.value = 'live'
        }).catch((error) => fail(error, mine))
      },
      closed(reason) {
        filling = filling.then(async () => {
          if (mine !== generation) return
          if (reason === 'ended') {
            await catchUp(id, mine)
            record.ended = true
            state.value = 'ended'
          } else if (SESSION_ENDS.has(reason)) {
            const ended = new ApiRefusal(401, `unauthenticated:${reason}`, 'unauthenticated')
            refusal.value = ended
            state.value = 'error'
            session.end(ended)
          } else {
            // slow_reader, disconnected: start again from the cursor.
            stats.reconnects += 1
            state.value = 'reconnecting'
            follow(id, mine)
          }
        }).catch((error) => fail(error, mine))
      },
      dropped(retrying) {
        if (mine !== generation) return
        if (retrying) {
          stats.reconnects += 1
          state.value = 'reconnecting'
          return
        }
        // The browser gave up (the API refused the reconnect): read once to learn the named refusal.
        filling = filling.then(() => catchUp(id, mine)).then(
          () => {
            if (mine !== generation) return
            stats.reconnects += 1
            state.value = 'reconnecting'
            follow(id, mine)
          },
          (error) => fail(error, mine),
        )
      },
    })
  }

  async function start() {
    const mine = ++generation
    stream?.close()
    stream = null
    Object.assign(record, emptyRecord())
    refusal.value = null
    state.value = 'loading'
    const id = dispatch()
    try {
      await catchUp(id, mine)
    } catch (error) {
      fail(error, mine)
      return
    }
    if (mine !== generation) return
    if (record.ended && record.cursor >= record.total) {
      state.value = 'ended'
      return
    }
    state.value = 'live'
    follow(id, mine)
  }

  function stop() {
    generation += 1
    stream?.close()
    stream = null
    if (state.value === 'live' || state.value === 'reconnecting') state.value = 'stopped'
  }

  onScopeDispose(stop)

  return { record, state, refusal, stats, start, stop }
}
