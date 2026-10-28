import type { Item, ReadAnswer, RecordLine, RecordPage } from '@/api/types'

export function line(seq: number, payload: unknown, stream = 'engine', redacted: string[] = []): RecordLine {
  return { seq, at: 1790000000 + seq, stream, redacted, payload: typeof payload === 'string' ? payload : JSON.stringify(payload) }
}

export function page(lines: RecordLine[], over: Partial<RecordPage> = {}): RecordPage {
  return {
    schema: 'veldo.api_execution_record/v1',
    dispatch_id: 'dispatch/VELDO-1/aa',
    after: 0,
    run: { unit: 'VELDO-1', station: 'build', project: 'p', account: 'a', host: 'h', state: 'running', process: null },
    lines,
    cursor: lines.length ? lines[lines.length - 1]!.seq : 0,
    total: lines.length ? lines[lines.length - 1]!.seq : 0,
    ended: false,
    committed: null,
    ...over,
  }
}

export function item(id: string, kind: string, data: Record<string, unknown>, version = 1): Item {
  return { id, kind, version, digest: 'sha256:' + id, data }
}

export function read(items: Record<string, Item[]>): ReadAnswer {
  return {
    schema: 'veldo.api_read/v1',
    model: 'm',
    kinds: Object.keys(items),
    items,
    problems: [],
    redacted: [],
    watermark: { seq: 7, record_digest: null, committed_at: null },
    freshness: 'live',
  }
}

export function receipt(request: string, over: Record<string, unknown> = {}) {
  return {
    request_id: request,
    request_version: 1,
    presentation_version: 1,
    presentation_id: `presentation:telegram_chat:${request}:1:ab`,
    brief_digest: 'sha256:brief',
    outcome: 'published',
    channel: 'telegram_chat',
    choices: ['accept', 'return_for_elaboration', 'reject'],
    rulings: ['approve', 'return_for_elaboration', 'reject'],
    risk_statement: 'Low risk.',
    authority_statement: 'Only owner answers this.',
    framed_by: 'pm',
    owner: 'owner',
    rendered: ['Veldo needs your decision\nChoices: accept | reject'],
    request: { brief: `Decide ${request}.` },
    ...over,
  }
}
