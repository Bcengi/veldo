import { describe, expect, it } from 'vitest'
import { item, read } from '@/test/builders'
import { runSignal } from './lamps'
import { LIVE_STATES, runRows, runsSummary, SPACE_WAIT, type RunRow } from './runs'

describe('runRows', () => {
  it('takes the dispatch from the entity id, which the read model never redacts', () => {
    const workers = read({ dispatch: [item('dispatch:dispatch/U-1/abc', 'dispatch', { dispatch_id: '[redacted]', state: 'running', contract: { unit: 'U-1' } })] })
    expect(runRows(workers, null)[0]!.dispatch).toBe('dispatch/U-1/abc')
  })

  it('lists live runs first and gives each its unit state', () => {
    const workers = read({
      dispatch: [
        item('dispatch:dispatch/A/1', 'dispatch', { state: 'exited', contract: { unit: 'A' } }),
        item('dispatch:dispatch/B/1', 'dispatch', { state: 'running', contract: { unit: 'B', station: 'build' } }),
      ],
    })
    const work = read({ execution_unit: [item('B', 'execution_unit', { state: 'RUNNING' })] })
    const rows = runRows(workers, work)
    expect(rows.map((r) => r.unit)).toEqual(['B', 'A'])
    expect(rows[0]!.unitState).toBe('RUNNING')
    expect(rows[1]!.unitState).toBeNull()
  })
})

describe('runs and space (VELDO-0319)', () => {
  it('gives a run the hold its dispatch carries, and no other run one', () => {
    const workers = read({
      dispatch: [
        item('dispatch:dispatch/A/1', 'dispatch', { state: 'running', contract: { unit: 'A' } }),
        item('dispatch:dispatch/B/1', 'dispatch', { state: 'running', contract: { unit: 'B' } }),
      ],
    })
    const hold = { id: 'space:hold:h', version: 1, state: 'advised' as const, pool: 'main', scope: { type: 'project' as const, id: 'p' },
      need: 4, free: 10, held: 3, floor: 5, source: 'declared', run: { dispatch: 'dispatch/B/1', unit: 'B', station: 'build' } }
    const pools = { pools: [{ name: 'main', waiting: [], advised: [hold] }] } as unknown as Parameters<typeof runRows>[2]
    const rows = runRows(workers, null, pools)
    expect(rows.find((r) => r.unit === 'B')!.space).toEqual(hold)
    expect(rows.find((r) => r.unit === 'A')!.space).toBeNull()
    expect(runRows(workers, null).every((r) => r.space === null)).toBe(true)
  })

  it('lists a run that waits for space as a row of its own, after the live runs, with no run to open', () => {
    const workers = read({
      dispatch: [
        item('dispatch:dispatch/A/1', 'dispatch', { state: 'exited', contract: { unit: 'A' } }),
        item('dispatch:dispatch/B/1', 'dispatch', { state: 'running', contract: { unit: 'B' } }),
      ],
    })
    const hold = { id: 'space:hold:w', version: 1, state: 'waiting' as const, pool: 'main', scope: { type: 'project' as const, id: 'orchard' },
      need: 4, free: 10, held: 3, floor: 5, source: 'default', run: null }
    const pools = { pools: [{ name: 'main', waiting: [hold], advised: [] }] } as unknown as Parameters<typeof runRows>[2]
    const rows = runRows(workers, null, pools)
    expect(rows.map((r) => [r.state, r.unit, r.dispatch, r.project])).toEqual([
      ['running', 'B', 'dispatch/B/1', ''], [SPACE_WAIT, 'Not dispatched yet', '', 'orchard'], ['exited', 'A', 'dispatch/A/1', ''],
    ])
    expect(rows[1]!.space).toEqual(hold)
    expect(LIVE_STATES.has(SPACE_WAIT)).toBe(false)
    expect(runSignal(SPACE_WAIT, null)).toEqual({ lamp: 'waiting', word: 'Waiting for space' })
  })
})

describe('runsSummary', () => {
  const row = (dispatch: string, project: string, host: string): RunRow => ({
    dispatch, unit: dispatch, station: '', project, state: 'running', host, platform: '', unitState: null,
  })

  it('counts the rows shown and their distinct projects and hosts, skipping blanks', () => {
    const rows = [row('a', 'p1', 'h1'), row('b', 'p1', 'h2'), row('c', 'p2', 'h2'), row('d', '', '')]
    expect(runsSummary(rows)).toEqual({ runs: 4, projects: 2, hosts: 2 })
  })

  it('is all zeros for no rows', () => {
    expect(runsSummary([])).toEqual({ runs: 0, projects: 0, hosts: 0 })
  })
})
