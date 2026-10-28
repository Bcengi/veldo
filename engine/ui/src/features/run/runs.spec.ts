import { describe, expect, it } from 'vitest'
import { item, read } from '@/test/builders'
import { runRows } from './runs'

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
