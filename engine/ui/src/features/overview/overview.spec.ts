import { describe, expect, it } from 'vitest'
import type { RunRow } from '@/features/run/runs'
import { factoryCounts } from './overview'

const row = (dispatch: string, state: string, host: string, unitState: string | null = null): RunRow => ({
  dispatch, unit: dispatch, station: 'build', project: 'p', state, host, platform: 'linux', unitState,
})

describe('factoryCounts', () => {
  const rows = [
    row('a', 'running', 'host-1'),
    row('b', 'accepted', 'host-1'),
    row('c', 'exited', 'host-2'),
    row('d', 'running', 'host-2'),
    row('e', 'refused', ''),
  ]

  it('counts running runs, blocked and failed units, and what waits on you', () => {
    const counts = factoryCounts(rows, ['RUNNING', 'AWAITING_AUTHORITY', 'FAILED', 'FAILED', 'COMPLETED', 'AWAITING_AUTHORITY'], 4)
    expect([counts.running, counts.blocked, counts.failed, counts.waiting]).toEqual([3, 2, 2, 4])
  })

  it('lists each host with how many of its runs are going, busiest first', () => {
    expect(factoryCounts(rows, [], 0).hosts).toEqual([
      { name: 'host-1', platform: 'linux', running: 2, runs: 2 },
      { name: 'host-2', platform: 'linux', running: 1, runs: 2 },
    ])
  })

  it('says a count is not readable, never zero, when the work read was refused', () => {
    const counts = factoryCounts(rows, null, 1)
    expect(counts.blocked).toBeNull()
    expect(counts.failed).toBeNull()
    expect(counts.running).toBe(3)
  })
})
