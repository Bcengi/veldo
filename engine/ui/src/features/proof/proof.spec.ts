import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { bundlesOf, findingsOf, observationsOf } from './proof'

const item = (id: string, kind: string, data: Record<string, unknown>) => ({ id, kind, version: 1, digest: 'd', data })
const answer = {
  items: {
    proof_bundle: [item('proof-bundle:1', 'proof_bundle', { unit: 'u1', spec: { path: 's.md', revision: 2, criteria: ['AC1'] }, checks: [{ name: 'gate', status: 'passed' }, { name: 'review', status: 'failed', command: 'review' }], manifest: { path: 'm.json', body: { AC1: 'x' } } })],
    gate_observation: [item('g2', 'gate_observation', { commit: 'bbbbbbbbb', green: true, finished_at: 20, stdout: 'ok' }), item('g1', 'gate_observation', { commit: 'aaaaaaaaa', green: false, exit: 1, finished_at: 10, terminal: 'GATE: RED' })],
  },
} as unknown as ReadAnswer

describe('proof', () => {
  it('reads bundles with their checks and manifest', () => {
    const [bundle] = bundlesOf(answer)
    expect(bundle!.checks.map((c) => c.status)).toEqual(['passed', 'failed'])
    expect(bundle!.manifestBody).toContain('"AC1": "x"')
  })
  it('orders observations oldest first', () => {
    expect(observationsOf(answer).map((o) => o.id)).toEqual(['g1', 'g2'])
  })
  it('finds failed checks and red gates', () => {
    expect(findingsOf(bundlesOf(answer), observationsOf(answer)).map((f) => f.title)).toEqual(['u1: review failed', 'Gate not green at aaaaaaa'])
  })
})
