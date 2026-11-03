import { describe, expect, it } from 'vitest'
import { item, read } from '@/test/builders'
import { runRows, runsSummary, type RunRow } from './runs'

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
