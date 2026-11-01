import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { authorityOrder, backlogOf, backlogRows, moveBy, moveTo } from './backlog'
import { completionOf, landedUnits } from './completion'

const item = (id: string, data: Record<string, unknown>, kind = 'backlog_item') => ({ id, kind, version: 1, digest: 'd', data })
const work = {
  items: {
    backlog_item: [
      item('b1', { title: 'One', state: 'ACTIVE', priority: { rank: 2 }, blocks: [] }),
      item('b2', { title: 'Two', state: 'BLOCKED', priority: { rank: 1 }, blocks: [{ block_id: 'block-1', reason: 'waiting', resolution: null }] }),
      item('b3', { title: 'Three', state: 'ADMITTED', priority: null }),
    ],
    execution_unit: [
      item('u1', { backlog_item_uuid: 'b1', state: 'COMPLETED', primary_specification: 'S-1' }, 'execution_unit'),
      item('u2', { backlog_item_uuid: 'b1', state: 'COMPLETED' }, 'execution_unit'),
    ],
  },
} as unknown as ReadAnswer
const proof = { items: { completion_receipt: [item('r1', { subject: { id: 'u1' } }, 'completion_receipt')] } } as unknown as ReadAnswer

describe('completion', () => {
  it('is landed only with the landing receipt', () => {
    const landed = landedUnits(proof)
    expect(completionOf('u1', 'COMPLETED', landed)).toBe('landed')
    expect(completionOf('u2', 'COMPLETED', landed)).toBe('built-unconfirmed')
    expect(completionOf('u3', 'RUNNING', landed)).toBe('not-complete')
  })
  it('reads no receipt from no proof read', () => {
    expect(landedUnits(null).size).toBe(0)
  })
})

describe('backlog', () => {
  const entries = backlogOf(work, landedUnits(proof))
  it('orders by the authority\'s rank, unranked last', () => {
    expect(authorityOrder(entries)).toEqual(['b2', 'b1', 'b3'])
  })
  it('names open blockers and nests units with their completion', () => {
    const rows = backlogRows(entries, authorityOrder(entries))
    expect(rows[0]!.cells.blockers).toBe('waiting')
    expect(rows[1]!.children?.map((c) => c.cells.state)).toEqual(['Landed', 'Built, landing not confirmed'])
  })
  it('moves an item by drag target, keyboard step or touch button alike', () => {
    expect(moveTo(['a', 'b', 'c'], 'c', 0)).toEqual(['c', 'a', 'b'])
    expect(moveBy(['a', 'b', 'c'], 'a', 1)).toEqual(['b', 'a', 'c'])
    expect(moveBy(['a', 'b', 'c'], 'a', -1)).toEqual(['a', 'b', 'c'])
    expect(moveBy(['a', 'b', 'c'], 'c', 5)).toEqual(['a', 'b', 'c'])
  })
})
