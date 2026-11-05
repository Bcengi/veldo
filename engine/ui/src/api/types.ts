/** The shapes the UI reads, as control_api_models and control_api_authority serve them. */

export interface Watermark {
  seq: number
  record_digest: string | null
  committed_at: number | null
}

export interface Item<D = Record<string, unknown>> {
  id: string
  kind: string
  version: number
  digest: string
  data: D
}

export interface ReadAnswer<K extends string = string> {
  schema: string
  model: string
  kinds: K[]
  items: Record<K, Item[]>
  problems: { id: string; kind: string; refusal: string }[]
  redacted: string[]
  watermark: Watermark
  freshness: 'live' | 'stale'
  /** VELDO-0236: the pacing read's pause, ceiling, resume and end records, read from the journal. */
  pacing?: Record<string, unknown>[]
}

export interface SessionView {
  principal: string
  credential_id: string
  domain: string
  csrf_token: string
  idle_expires_at: number
  expires_at: number
}

export interface RecordLine {
  seq: number
  at: number
  stream: 'engine' | 'stderr' | 'wrapper' | string
  redacted: string[]
  payload: string
}

export interface RecordRun {
  unit: string | null
  station: string | null
  project: string | null
  account: string | null
  host: string | null
  state: string | null
  process: Record<string, unknown> | null
}

export interface RecordPage {
  schema: string
  dispatch_id: string
  after: number
  run: RecordRun
  lines: RecordLine[]
  cursor: number
  total: number
  ended: boolean
  committed: { lines: number; bytes: number; digest: string } | null
}
