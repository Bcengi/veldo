import { request } from './client'
import type { ReadAnswer } from './types'

export const readDecisions = (signal?: AbortSignal) => request<ReadAnswer>('reads.decisions', { signal })
export const readWorkers = (signal?: AbortSignal) => request<ReadAnswer>('reads.workers', { signal })
export const readWork = (signal?: AbortSignal) => request<ReadAnswer>('reads.work', { signal })
