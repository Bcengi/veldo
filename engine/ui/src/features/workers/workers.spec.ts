import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { capValue, capsOf, familiesOf, machinesOf } from './workers'

function dispatch(id: string, host: string, platform: string, state: string, unit: string) {
  return {
    id: `dispatch:${id}`, kind: 'dispatch', version: 1, digest: 'd',
    data: { dispatch_id: id, state, process: { platform, host, pid: 7 }, contract: { unit, station: 'build', reservation: { project: 'p', account: 'a' } } },
  }
}

const answer = {
  items: { dispatch: [dispatch('d1', 'l1', 'linux', 'exited', 'U1'), dispatch('d2', 'l1', 'linux', 'running', 'U2'), dispatch('d3', 'm1', 'darwin', 'running', 'U3')] },
  machines: [
    { platform: 'darwin', host: 'm1', workers: ['dispatch:d3'], running: ['dispatch:d3'] },
    { platform: 'linux', host: 'l1', workers: ['dispatch:d1', 'dispatch:d2'], running: ['dispatch:d2'] },
  ],
} as unknown as ReadAnswer

describe('machinesOf', () => {
  it('keeps the API\'s machines and puts running workers first', () => {
    const machines = machinesOf(answer)
    expect(machines.map((m) => [m.family, m.host, m.running])).toEqual([['Mac', 'm1', 1], ['Linux', 'l1', 1]])
    expect(machines[1]!.workers.map((w) => w.unit)).toEqual(['U2', 'U1'])
  })
  it('groups Linux before Mac', () => {
    expect(familiesOf(machinesOf(answer)).map((f) => f.family)).toEqual(['Linux', 'Mac'])
  })
  it('answers nothing for no read', () => {
    expect(machinesOf(null)).toEqual([])
  })
})

describe('worker capability (fix round 2)', () => {
  it('names the adapter, the configuration role and its servers and tools', async () => {
    const { capabilityOf } = await import('./workers')
    expect(capabilityOf({ capability: { adapter: 'claude_code', configuration: { role: 'general', revision: 2,
      mcp: [{ server: 'atlassian' }], native_tools: [{ name: 'Read' }] } } })).toBe('claude_code; role general r2; servers atlassian; tools Read')
    expect(capabilityOf({})).toBe('')
  })
})

describe('stop and cap from the records', () => {
  it('reads a stop request and its result from the dispatch record, never from the screen', () => {
    const asked = dispatch('d4', 'l1', 'linux', 'running', 'U4')
    ;(asked.data as Record<string, unknown>).stop_request = { by: 'owner', at: 5, result: null }
    const machines = machinesOf({ items: { dispatch: [asked] }, machines: [{ platform: 'linux', host: 'l1', workers: ['dispatch:d4'] }] } as unknown as ReadAnswer)
    expect(machines[0]!.workers[0]!.stop).toEqual({ by: 'owner', at: 5, asked: null })
    expect(machinesOf(answer)[1]!.workers[0]!.stop).toBeNull()
  })
  it('lists each account record with its cap, version and changes', () => {
    const spend = { items: { account: [
      { id: 'account:b', kind: 'account', version: 3, digest: 'd', data: { id: 'b', label: 'B', provider: 'codex', concurrency: 2,
        concurrency_history: [{ concurrency: 2, previous: 1, by: 'owner', at: 9 }] } },
      { id: 'account:a', kind: 'account', version: 1, digest: 'd', data: { id: 'a', label: 'A', provider: 'claude_code', concurrency: 1 } },
    ] } } as unknown as ReadAnswer
    expect(capsOf(spend).map((c) => [c.account, c.version, c.concurrency, c.history.length])).toEqual([['a', 1, 1, 0], ['b', 3, 2, 1]])
    expect(capsOf(null)).toEqual([])
  })
  it('accepts a cap from 1 to 16 only', () => {
    expect(['1', '16', ' 4 ', '0', '17', '2.5', 'x', ''].map(capValue)).toEqual([1, 16, 4, null, null, null, null, null])
  })
})
