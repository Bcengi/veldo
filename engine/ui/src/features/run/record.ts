import type { RecordLine, RecordPage, RecordRun } from '@/api/types'

/**
 * One kept line of a run's execution record, read for display. The line itself is never replaced:
 * `payload` is exactly what the record holds, and `blocks` only say how to show it.
 */
export interface ShownLine {
  seq: number
  at: number
  stream: string
  redacted: string[]
  payload: string
  blocks: Block[]
  /** A short word for what the line is: assistant, tool call, result, error, stderr ... */
  kind: string
  error: boolean
}

export interface EditHunk {
  before: string
  after: string
}

export type Block =
  | { type: 'text'; text: string }
  | { type: 'thinking'; text: string }
  | { type: 'tool_call'; id: string; name: string; summary: string; input: unknown }
  | { type: 'edit'; id: string; name: string; path: string; hunks: EditHunk[] }
  | { type: 'tool_result'; toolUseId: string; output: string; isError: boolean }
  | { type: 'system'; title: string; detail: string }
  | { type: 'result'; isError: boolean; title: string; text: string }
  | { type: 'delta'; text: string }
  | { type: 'command'; command: string; output: string; exitCode: number | null }
  | { type: 'file_change'; paths: string[] }
  | { type: 'error'; text: string }
  | { type: 'raw'; text: string }
  | { type: 'event'; title: string; text: string }

type Json = Record<string, unknown>

const isObject = (value: unknown): value is Json => typeof value === 'object' && value !== null && !Array.isArray(value)
const str = (value: unknown): string => (typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value))

const EDIT_TOOLS = new Set(['Edit', 'MultiEdit', 'Write', 'NotebookEdit'])

/** The text a tool result carries: a string, or the text parts of a content list. */
function resultText(content: unknown): string {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((part) => (isObject(part) && part.type === 'text' ? str(part.text) : isObject(part) ? `[${str(part.type)}]` : str(part)))
      .join('\n')
  }
  return str(content)
}

/** The one-line form of a tool call's input, so a reader sees what it did before opening it. */
function toolSummary(name: string, input: Json): string {
  if (name === 'Bash' && typeof input.command === 'string') return input.command
  if (typeof input.file_path === 'string') return input.file_path
  if (typeof input.path === 'string') return input.path
  if (typeof input.pattern === 'string') return input.pattern
  if (typeof input.url === 'string') return input.url
  if (typeof input.description === 'string') return input.description
  if (typeof input.prompt === 'string') return input.prompt
  return JSON.stringify(input)
}

function editBlock(id: string, name: string, input: Json): Block {
  const path = str(input.file_path ?? input.notebook_path ?? input.path)
  let hunks: EditHunk[]
  if (name === 'Write') hunks = [{ before: '', after: str(input.content) }]
  else if (name === 'MultiEdit' && Array.isArray(input.edits))
    hunks = input.edits.filter(isObject).map((e) => ({ before: str(e.old_string), after: str(e.new_string) }))
  else if (name === 'NotebookEdit') hunks = [{ before: '', after: str(input.new_source) }]
  else hunks = [{ before: str(input.old_string), after: str(input.new_string) }]
  return { type: 'edit', id, name, path, hunks }
}

function contentBlocks(content: unknown): Block[] {
  if (typeof content === 'string') return [{ type: 'text', text: content }]
  if (!Array.isArray(content)) return []
  const blocks: Block[] = []
  for (const part of content) {
    if (!isObject(part)) continue
    if (part.type === 'text') blocks.push({ type: 'text', text: str(part.text) })
    else if (part.type === 'thinking') blocks.push({ type: 'thinking', text: str(part.thinking) })
    else if (part.type === 'tool_use') {
      const name = str(part.name)
      const input = isObject(part.input) ? part.input : {}
      blocks.push(
        EDIT_TOOLS.has(name)
          ? editBlock(str(part.id), name, input)
          : { type: 'tool_call', id: str(part.id), name, summary: toolSummary(name, input), input: part.input },
      )
    } else if (part.type === 'tool_result')
      blocks.push({
        type: 'tool_result',
        toolUseId: str(part.tool_use_id),
        output: resultText(part.content),
        isError: part.is_error === true,
      })
    else blocks.push({ type: 'event', title: str(part.type), text: JSON.stringify(part) })
  }
  return blocks
}

/** Claude Code's stream JSON and Codex's exec JSON, one event per engine line. */
function engineBlocks(event: Json): { blocks: Block[]; kind: string } {
  const type = str(event.type)
  const message = isObject(event.message) ? event.message : null
  if (type === 'assistant' && message) {
    const blocks = contentBlocks(message.content)
    const calls = blocks.some((b) => b.type === 'tool_call' || b.type === 'edit')
    return { blocks, kind: calls ? 'tool call' : 'assistant' }
  }
  if (type === 'user' && message) {
    const blocks = contentBlocks(message.content)
    return { blocks, kind: blocks.some((b) => b.type === 'tool_result') ? 'result' : 'user' }
  }
  if (type === 'system') {
    const subtype = str(event.subtype)
    const detail =
      subtype === 'init'
        ? [event.model && `model ${str(event.model)}`, Array.isArray(event.tools) && `${event.tools.length} tools`, event.cwd && `in ${str(event.cwd)}`]
            .filter(Boolean)
            .join(', ')
        : JSON.stringify(event)
    return { blocks: [{ type: 'system', title: subtype || 'system', detail }], kind: 'system' }
  }
  if (type === 'result') {
    const isError = event.is_error === true || (typeof event.subtype === 'string' && event.subtype.startsWith('error'))
    const turns = typeof event.num_turns === 'number' ? `${event.num_turns} turns` : ''
    return {
      blocks: [{ type: 'result', isError, title: str(event.subtype) || 'result', text: [str(event.result), turns].filter(Boolean).join('\n') }],
      kind: isError ? 'run failed' : 'run result',
    }
  }
  if (type === 'stream_event' && isObject(event.event)) {
    const inner = event.event
    const delta = isObject(inner.delta) ? inner.delta : null
    const text = delta ? str(delta.text ?? delta.partial_json ?? delta.thinking ?? '') : ''
    return { blocks: [{ type: 'delta', text: text || str(inner.type) }], kind: 'partial' }
  }
  if (type === 'control_request' || type === 'control_response') {
    const inner = isObject(event.response) ? event.response : isObject(event.request) ? event.request : {}
    return { blocks: [{ type: 'event', title: type.replace('_', ' '), text: str(inner.subtype) || JSON.stringify(event) }], kind: 'control' }
  }
  // Codex exec JSON.
  if (type.startsWith('item.') && isObject(event.item)) {
    const item = event.item
    const itemType = str(item.type)
    if (itemType === 'command_execution')
      return {
        blocks: [{ type: 'command', command: str(item.command), output: str(item.aggregated_output), exitCode: typeof item.exit_code === 'number' ? item.exit_code : null }],
        kind: 'command',
      }
    if (itemType === 'file_change')
      return {
        blocks: [{ type: 'file_change', paths: Array.isArray(item.changes) ? item.changes.filter(isObject).map((c) => `${str(c.kind)} ${str(c.path)}`) : [] }],
        kind: 'edit',
      }
    if (itemType === 'error') return { blocks: [{ type: 'error', text: str(item.message) }], kind: 'error' }
    if (itemType === 'agent_message' || itemType === 'reasoning')
      return { blocks: [{ type: 'text', text: str(item.text) }], kind: itemType === 'reasoning' ? 'reasoning' : 'assistant' }
  }
  if (type === 'error') return { blocks: [{ type: 'error', text: str(event.message ?? event.error) }], kind: 'error' }
  return { blocks: [{ type: 'event', title: type || 'event', text: JSON.stringify(event) }], kind: type || 'event' }
}

function blockIsError(block: Block): boolean {
  return (
    (block.type === 'tool_result' && block.isError) ||
    (block.type === 'result' && block.isError) ||
    block.type === 'error' ||
    (block.type === 'command' && block.exitCode !== null && block.exitCode !== 0)
  )
}

/** How one kept line is shown. A line that is not an engine event, or not JSON, is shown as raw text. */
export function showLine(line: RecordLine): ShownLine {
  let blocks: Block[] = []
  let kind = line.stream
  if (line.stream === 'engine') {
    let event: unknown
    try {
      event = JSON.parse(line.payload)
    } catch {
      event = undefined
    }
    if (isObject(event)) ({ blocks, kind } = engineBlocks(event))
    else blocks = [{ type: 'raw', text: line.payload }]
  } else {
    blocks = [{ type: 'raw', text: line.payload }]
  }
  const error = blocks.some(blockIsError)
  return { ...line, blocks, kind: error && kind === line.stream ? 'error' : kind, error }
}

export interface RecordState {
  lines: ShownLine[]
  cursor: number
  total: number
  ended: boolean
  run: RecordRun | null
  committed: RecordPage['committed']
}

export const emptyRecord = (): RecordState => ({ lines: [], cursor: 0, total: 0, ended: false, run: null, committed: null })

export interface Applied {
  /** Lines appended, in sequence order. */
  added: number
  /** Lines at or below the cursor that were already shown and were dropped. */
  repeats: number
  /** The cursor at which a sequence was missing, or null: the lines after it wait for the gap to fill. */
  gapAfter: number | null
}

/**
 * Apply one page or frame: append each line whose sequence is exactly the next, drop a repeat, and stop
 * at a gap. Never reorders, merges or drops a new line. Mutates `state` in place.
 */
export function applyPage(state: RecordState, page: Pick<RecordPage, 'lines' | 'total' | 'ended' | 'run' | 'committed'>): Applied {
  const applied: Applied = { added: 0, repeats: 0, gapAfter: null }
  for (const line of page.lines) {
    if (line.seq <= state.cursor) {
      applied.repeats += 1
      continue
    }
    if (line.seq !== state.cursor + 1) {
      applied.gapAfter = state.cursor
      break
    }
    state.lines.push(showLine(line))
    state.cursor = line.seq
    applied.added += 1
  }
  state.total = Math.max(state.total, page.total)
  if (page.run) state.run = page.run
  if (applied.gapAfter === null) {
    state.ended = page.ended
    state.committed = page.committed
  }
  return applied
}

/** The text a search matches: the line's own payload, so a search finds what the engine printed. */
export function matches(line: ShownLine, query: string): boolean {
  const q = query.trim().toLowerCase()
  return q.length > 0 && line.payload.toLowerCase().includes(q)
}

/** A receive time as the record's gutter shows it: local hours, minutes, seconds. */
export function clock(at: number): string {
  const date = new Date(at * 1000)
  const two = (n: number) => String(n).padStart(2, '0')
  return `${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}`
}

/** A line's time since the record's first line, as the gutter shows it: +0.4 s, +12 s, +3:05, +1:02:05. */
export function since(at: number, start: number): string {
  const s = Math.max(0, at - start)
  if (s < 10) return `+${s.toFixed(1)} s`
  if (s < 60) return `+${Math.floor(s)} s`
  const two = (n: number) => String(n).padStart(2, '0')
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = Math.floor(s % 60)
  return h ? `+${h}:${two(m)}:${two(sec)}` : `+${m}:${two(sec)}`
}

/** A span of seconds as the run header shows it: 42 s, 3 min 05 s, 1 h 02 min. */
export function duration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  if (s < 60) return `${s} s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m} min ${String(s % 60).padStart(2, '0')} s`
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')} min`
}

/** What the record says about the run itself: the engine that ran it, its model, and when its first and last
 * lines arrived. Read from the first lines only (the engine's start and the wrapper's line come first). */
export interface RunFacts {
  engine: string | null
  model: string | null
  startedAt: number | null
  lastAt: number | null
}

const ENGINES: Record<string, string> = { 'claude-code': 'Claude Code', claude: 'Claude Code', codex: 'Codex' }

export function runFacts(lines: ShownLine[]): RunFacts {
  let engine: string | null = null
  let model: string | null = null
  for (const line of lines.slice(0, 50)) {
    if (line.stream === 'wrapper' && !engine) {
      const named = /\bengine ([\w.-]+)/.exec(line.payload)?.[1]
      if (named) engine = ENGINES[named] ?? named
    }
    if (line.stream !== 'engine' || (engine && model)) continue
    let event: unknown
    try {
      event = JSON.parse(line.payload)
    } catch {
      continue
    }
    if (!isObject(event)) continue
    if (event.type === 'system' && event.subtype === 'init') {
      engine ??= 'Claude Code'
      if (typeof event.model === 'string') model ??= event.model
    } else if (typeof event.type === 'string' && (event.type.startsWith('item.') || event.type.startsWith('thread.'))) {
      engine ??= 'Codex'
      if (typeof event.model === 'string') model ??= event.model
    }
  }
  return { engine, model, startedAt: lines[0]?.at ?? null, lastAt: lines.at(-1)?.at ?? null }
}
