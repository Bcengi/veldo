import { request, routeUrl } from './client'
import type { RecordPage } from './types'

export const readRecord = (dispatch: string, after: number, signal?: AbortSignal) =>
  request<RecordPage>('runs.record', { fields: { dispatch, after }, signal })

/** The live record stream's URL from a cursor (an EventSource resends the last frame's id itself). */
export const recordStreamUrl = (dispatch: string, after: number) =>
  routeUrl('runs.record_stream', { dispatch, after })
