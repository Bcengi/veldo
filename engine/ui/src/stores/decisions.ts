import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { readDecisions } from '@/api/reads'
import type { Watermark } from '@/api/types'
import { useAsync } from '@/composables/useAsync'
import { oldestDecision, pendingDecisions, rankDecisions, type PendingDecision } from '@/features/decisions/inbox'
import { useNow } from '@/composables/useNow'
import { useSessionStore } from './session'

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
  const now = useNow(30_000)
  const session = useSessionStore()
  const principal = computed(() => session.principal)
  /** Ranked: the most urgent deadline first, then the higher risk (inbox.ts rankDecisions). */
  const pending = computed<PendingDecision[]>(() => rankDecisions(load.data.value ?? [], now.value))
  const oldest = computed(() => oldestDecision(pending.value))
  const waiting = computed(() => pending.value.filter((d) => d.presentation !== null).length)

  function find(requestId: string) {
    return pending.value.find((d) => d.requestId === requestId) ?? null
  }

  function reset() {
    load.reset()
    watermark.value = null
    freshness.value = null
  }

  return { state: load.state, refusal: load.refusal, pending, oldest, now, principal, waiting, watermark, freshness, refresh: load.run, find, reset }
})
