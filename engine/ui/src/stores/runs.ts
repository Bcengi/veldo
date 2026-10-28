import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { ApiRefusal } from '@/api/refusal'
import { readWork, readWorkers } from '@/api/reads'
import type { ReadAnswer, Watermark } from '@/api/types'
import { useAsync } from '@/composables/useAsync'
import { runRows, unitStates, type RunRow } from '@/features/run/runs'

/** The worker runs the signed-in member can see, from reads.workers, with each unit's state from reads.work. */
export const useRunsStore = defineStore('runs', () => {
  const watermark = shallowRef<Watermark | null>(null)
  const work = shallowRef<ReadAnswer | null>(null)
  const load = useAsync(
    async (signal) => {
      const workers = await readWorkers(signal)
      watermark.value = workers.watermark
      try {
        work.value = await readWork(signal)
      } catch (error) {
        // The units' states only light the strip; a refused work read leaves it unlit, never fails the list.
        if (!(error instanceof ApiRefusal) || error.error === 'unauthenticated') throw error
        work.value = null
      }
      return runRows(workers, work.value)
    },
    (rows) => rows.length === 0,
  )
  const rows = computed<RunRow[]>(() => load.data.value ?? [])
  const units = computed(() => unitStates(work.value))

  function find(dispatch: string) {
    return rows.value.find((r) => r.dispatch === dispatch) ?? null
  }

  function reset() {
    load.reset()
    watermark.value = null
    work.value = null
  }

  return { state: load.state, refusal: load.refusal, rows, units, watermark, refresh: load.run, find, reset }
})
