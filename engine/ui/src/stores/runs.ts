import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { ApiRefusal } from '@/api/refusal'
import { readSpacePools, readWork, readWorkers } from '@/api/reads'
import type { ReadAnswer, Watermark } from '@/api/types'
import { useAsync } from '@/composables/useAsync'
import { runRows, unitStateList, unitStates, type RunRow } from '@/features/run/runs'
import { runHolds, type PoolsAnswer, type SpaceHold } from '@/features/space/space'

/** The worker runs the signed-in member can see, from reads.workers, with each unit's state from reads.work. */
export const useRunsStore = defineStore('runs', () => {
  const watermark = shallowRef<Watermark | null>(null)
  const work = shallowRef<ReadAnswer | null>(null)
  /** VELDO-0319: the pools read, for the runs that wait or would have waited for space. */
  const pools = shallowRef<PoolsAnswer | null>(null)
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
      try {
        pools.value = await readSpacePools(signal)
      } catch (error) {
        // The holds only add a line to a row; a refused pools read leaves the rows without it.
        if (!(error instanceof ApiRefusal) || error.error === 'unauthenticated') throw error
        pools.value = null
      }
      return runRows(workers, work.value, pools.value)
    },
    // A run that waits for space has no dispatch yet: the list is not empty while one waits.
    (rows) => rows.length === 0 && runHolds(pools.value).waiting.length === 0,
  )
  const rows = computed<RunRow[]>(() => load.data.value ?? [])
  const units = computed(() => unitStates(work.value))
  /** Every unit's state, or null when the work read was refused. */
  const unitList = computed(() => unitStateList(work.value))
  /** The holds that wait for space and have no dispatch yet. */
  const waitingForSpace = computed<SpaceHold[]>(() => runHolds(pools.value).waiting)

  function find(dispatch: string) {
    return rows.value.find((r) => r.dispatch === dispatch) ?? null
  }

  function reset() {
    load.reset()
    watermark.value = null
    work.value = null
    pools.value = null
  }

  return { state: load.state, refusal: load.refusal, rows, units, unitList, waitingForSpace, watermark, refresh: load.run, find, reset }
})
