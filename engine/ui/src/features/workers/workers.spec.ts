import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { familiesOf, machinesOf } from './workers'

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
