import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { readDecisions } from '@/api/reads'
import type { Watermark } from '@/api/types'
import { useAsync } from '@/composables/useAsync'
import { pendingDecisions, type PendingDecision } from '@/features/decisions/inbox'

/** The decisions waiting on the signed-in member, as reads.decisions last answered. */
export const useDecisionsStore = defineStore('decisions', () => {
  const watermark = shallowRef<Watermark | null>(null)
  const freshness = shallowRef<string | null>(null)
  const load = useAsync(
    async (signal) => {
      const answer = await readDecisions(signal)
      watermark.value = answer.watermark
      freshness.value = answer.freshness
      return pendingDecisions(answer)
    },
    (list) => list.length === 0,
  )
  const pending = computed<PendingDecision[]>(() => load.data.value ?? [])
  const waiting = computed(() => pending.value.filter((d) => d.presentation !== null).length)

  function find(requestId: string) {
    return pending.value.find((d) => d.requestId === requestId) ?? null
  }

  function reset() {
    load.reset()
    watermark.value = null
    freshness.value = null
  }

  return { state: load.state, refusal: load.refusal, pending, waiting, watermark, freshness, refresh: load.run, find, reset }
})
