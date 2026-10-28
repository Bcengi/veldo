import { describe, expect, it } from 'vitest'
import { line, page } from '@/test/builders'
import { applyPage, emptyRecord, matches, showLine } from './record'

const bash = { type: 'assistant', message: { content: [{ type: 'tool_use', id: 't1', name: 'Bash', input: { command: 'ls -la' } }] } }
const edit = {
  type: 'assistant',
  message: { content: [{ type: 'tool_use', id: 't2', name: 'Edit', input: { file_path: '/a.py', old_string: 'x = 1', new_string: 'x = 2' } }] },
}
const failed = { type: 'user', message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'Exit code 1\nboom', is_error: true }] } }

describe('showLine', () => {
  it('keeps the payload exactly as the record holds it', () => {
    const shown = showLine(line(3, bash))
    expect(shown.payload).toBe(JSON.stringify(bash))
    expect(shown.seq).toBe(3)
  })

  it('reads a tool call with its command', () => {
    const shown = showLine(line(1, bash))
    expect(shown.kind).toBe('tool call')
    expect(shown.blocks).toEqual([{ type: 'tool_call', id: 't1', name: 'Bash', summary: 'ls -la', input: { command: 'ls -la' } }])
  })

  it('reads an edit as old and new text for a diff', () => {
    expect(showLine(line(1, edit)).blocks).toEqual([{ type: 'edit', id: 't2', name: 'Edit', path: '/a.py', hunks: [{ before: 'x = 1', after: 'x = 2' }] }])
  })

  it('marks a failed tool result as an error', () => {
    const shown = showLine(line(1, failed))
    expect(shown.error).toBe(true)
    expect(shown.blocks[0]).toMatchObject({ type: 'tool_result', output: 'Exit code 1\nboom', isError: true })
  })

  it('shows an engine line that is not JSON, and an error stream line, as raw text', () => {
    expect(showLine(line(1, 'not json {')).blocks).toEqual([{ type: 'raw', text: 'not json {' }])
    expect(showLine(line(2, 'warning: x', 'stderr')).blocks).toEqual([{ type: 'raw', text: 'warning: x' }])
  })

  it('shows an engine event it does not know as its own JSON', () => {
    const shown = showLine(line(1, { type: 'brand_new', value: 1 }))
    expect(shown.blocks[0]).toMatchObject({ type: 'event', title: 'brand_new' })
  })

  it('reads Codex command executions with their exit code', () => {
    const shown = showLine(line(1, { type: 'item.completed', item: { type: 'command_execution', command: 'make', aggregated_output: 'ok', exit_code: 2 } }))
    expect(shown.blocks[0]).toEqual({ type: 'command', command: 'make', output: 'ok', exitCode: 2 })
    expect(shown.error).toBe(true)
  })
})

describe('applyPage', () => {
  it('appends every line in sequence', () => {
    const state = emptyRecord()
    const applied = applyPage(state, page([line(1, 'a'), line(2, 'b'), line(3, 'c')]))
    expect(applied).toEqual({ added: 3, repeats: 0, gapAfter: null })
    expect(state.lines.map((l) => l.seq)).toEqual([1, 2, 3])
    expect(state.cursor).toBe(3)
  })

  it('drops a line it already applied, so a resumed stream repeats nothing', () => {
    const state = emptyRecord()
    applyPage(state, page([line(1, 'a'), line(2, 'b')]))
    const applied = applyPage(state, page([line(2, 'b'), line(3, 'c')]))
    expect(applied.repeats).toBe(1)
    expect(state.lines.map((l) => l.seq)).toEqual([1, 2, 3])
  })

  it('stops at a gap and names the cursor it stopped at, so nothing is shown out of order', () => {
    const state = emptyRecord()
    applyPage(state, page([line(1, 'a')]))
    const applied = applyPage(state, page([line(3, 'c'), line(4, 'd')]))
    expect(applied.gapAfter).toBe(1)
    expect(state.lines.map((l) => l.seq)).toEqual([1])
  })

  it('records the end and the committed record only when no gap is pending', () => {
    const state = emptyRecord()
    applyPage(state, page([line(1, 'a')], { ended: true, total: 1, committed: { lines: 1, bytes: 9, digest: 'sha256:x' } }))
    expect(state.ended).toBe(true)
    expect(state.committed?.lines).toBe(1)
  })
})

describe('matches', () => {
  it('matches the payload text, case-insensitively', () => {
    const shown = showLine(line(1, bash))
    expect(matches(shown, 'LS -LA')).toBe(true)
    expect(matches(shown, '   ')).toBe(false)
  })
})

describe('the run header and the gutter', () => {
  it('reads the engine and model from the record, and the span of its lines', async () => {
    const { runFacts, showLine } = await import('./record')
    const lines = [
      { seq: 1, at: 100, stream: 'wrapper', redacted: [], payload: 'veldo-wrapper: engine claude-code, unit U, station build' },
      { seq: 2, at: 100.4, stream: 'engine', redacted: [], payload: JSON.stringify({ type: 'system', subtype: 'init', model: 'claude-opus-5-5' }) },
      { seq: 3, at: 172, stream: 'engine', redacted: [], payload: '{"type":"result","subtype":"success"}' },
    ].map(showLine)
    expect(runFacts(lines)).toEqual({ engine: 'Claude Code', model: 'claude-opus-5-5', startedAt: 100, lastAt: 172 })
    const codex = [{ seq: 1, at: 5, stream: 'engine', redacted: [], payload: '{"type":"item.completed","item":{"type":"agent_message","text":"hi"}}' }].map(showLine)
    expect(runFacts(codex).engine).toBe('Codex')
  })

  it('shows each line\'s time since the first line, compactly', async () => {
    const { since, duration } = await import('./record')
    expect([since(100.4, 100), since(112, 100), since(285, 100), since(3825, 100)]).toEqual(['+0.4 s', '+12 s', '+3:05', '+1:02:05'])
    expect([duration(42), duration(185), duration(3720)]).toEqual(['42 s', '3 min 05 s', '1 h 02 min'])
  })
})
