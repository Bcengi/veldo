import { ref, shallowRef } from 'vue'
import { ApiRefusal } from '@/api/refusal'

export type AsyncState = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

/** One screen's load: its state, the data, and the named refusal when it failed. A load that finishes
 * after a newer one started is dropped. */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, isEmpty: (data: T) => boolean = () => false) {
  const state = ref<AsyncState>('idle')
  const data = shallowRef<T | null>(null)
  const refusal = shallowRef<ApiRefusal | null>(null)
  let current: AbortController | null = null

  async function run() {
    current?.abort()
    const mine = new AbortController()
    current = mine
    if (state.value !== 'ready' && state.value !== 'empty') state.value = 'loading'
    try {
      const value = await load(mine.signal)
      if (current !== mine) return
      data.value = value
      refusal.value = null
      state.value = isEmpty(value) ? 'empty' : 'ready'
    } catch (error) {
      if (current !== mine || (error as Error)?.name === 'AbortError') return
      data.value = null
      refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
      state.value = 'error'
    }
  }

  function reset() {
    current?.abort()
    current = null
    data.value = null
    refusal.value = null
    state.value = 'idle'
  }

  return { state, data, refusal, run, reset }
}
