import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as stream from '@/api/record-stream'
import { ApiRefusal } from '@/api/refusal'
import * as runs from '@/api/runs'
import { line, page } from '@/test/builders'
import { mountWith } from '@/test/mount'
import RunTerminal from './RunTerminal.vue'

const record = [
  line(1, 'veldo-wrapper: start', 'wrapper'),
  line(2, { type: 'assistant', message: { content: [{ type: 'text', text: 'Reading the test.' }] } }),
  line(3, { type: 'assistant', message: { content: [{ type: 'tool_use', id: 't', name: 'Bash', input: { command: 'pytest -q' } }] } }),
  line(4, { type: 'user', message: { content: [{ type: 'tool_result', tool_use_id: 't', content: '1 failed', is_error: true }] } }),
  line(5, 'warning: cache', 'stderr'),
]

afterEach(() => vi.restoreAllMocks())

function follow(handlers: { current?: stream.RecordStreamHandlers }) {
  return vi.spyOn(stream, 'openRecordStream').mockImplementation((_d, _a, on) => {
    handlers.current = on
    return { close: vi.fn() }
  })
}

describe('RunTerminal', () => {
  it('shows one row per kept line, in sequence, never a summary', async () => {
    vi.spyOn(runs, 'readRecord').mockResolvedValue(page(record, { ended: true, total: 5 }))
    const wrapper = mountWith(RunTerminal, { props: { dispatch: 'dispatch/VELDO-1/aa' } })
    await flushPromises()
    const rows = wrapper.findAll('[data-testid="lines"] > li')
    expect(rows.map((r) => Number(r.attributes('data-seq')))).toEqual([1, 2, 3, 4, 5])
    expect(rows[2]!.text()).toContain('pytest -q')
    expect(rows[3]!.attributes('data-error')).toBe('true')
    expect(rows[4]!.attributes('data-stream')).toBe('stderr')
  })

  it('shows each payload exactly in raw view', async () => {
    vi.spyOn(runs, 'readRecord').mockResolvedValue(page(record, { ended: true, total: 5 }))
    const wrapper = mountWith(RunTerminal, { props: { dispatch: 'd' } })
    await flushPromises()
    await wrapper.get('#raw').setValue(true)
    expect(wrapper.findAll('[data-testid="payload"]').map((p) => p.text())).toEqual(record.map((l) => l.payload))
  })

  it('follows live frames from the cursor, drops repeats and fills a gap from the record', async () => {
    const read = vi.spyOn(runs, 'readRecord')
    read.mockResolvedValueOnce(page(record.slice(0, 2), { total: 2 }))
    const handlers: { current?: stream.RecordStreamHandlers } = {}
    const open = follow(handlers)
    const wrapper = mountWith(RunTerminal, { props: { dispatch: 'd' } })
    await flushPromises()
    expect(open).toHaveBeenCalledWith('d', 2, expect.anything())
    handlers.current!.frame(page([record[1]!, record[2]!], { total: 3 }))
    await flushPromises()
    read.mockResolvedValueOnce(page([record[3]!, record[4]!], { total: 5 }))
    handlers.current!.frame(page([record[4]!], { total: 5 }))
    await flushPromises()
    expect(wrapper.findAll('[data-testid="lines"] > li').map((r) => Number(r.attributes('data-seq')))).toEqual([1, 2, 3, 4, 5])
    expect(read).toHaveBeenLastCalledWith('d', 3)
  })

  it('names the refusal and shows no line when the record is refused', async () => {
    vi.spyOn(runs, 'readRecord').mockRejectedValue(new ApiRefusal(403, 'unauthorized:out_of_scope', 'unauthorized'))
    const wrapper = mountWith(RunTerminal, { props: { dispatch: 'd' } })
    await flushPromises()
    expect(wrapper.get('[data-testid="refusal"]').attributes('data-refusal')).toBe('unauthorized:out_of_scope')
    expect(wrapper.find('[data-testid="lines"]').exists()).toBe(false)
  })

  it('says when there is no line yet', async () => {
    vi.spyOn(runs, 'readRecord').mockResolvedValue(page([], { total: 0 }))
    follow({})
    const wrapper = mountWith(RunTerminal, { props: { dispatch: 'd' } })
    await flushPromises()
    expect(wrapper.get('[data-testid="terminal-empty"]').text()).toContain('No line yet')
  })
})
