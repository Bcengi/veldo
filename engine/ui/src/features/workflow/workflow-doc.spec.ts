import { describe, expect, it } from 'vitest'
import { addNode, connect, nodeIds, orderedIds, problems, removeNode, reorder, setConfig, transitionOf, type Draft } from './workflow-doc'

const base: Draft = {
  definition: {
    schema: 'veldo.workflow/v1', id: 'w', entry: 'groom', terminal: ['finish'], references: {}, budget: { steps: 8 },
    nodes: { groom: { kind: 'grooming', config: {} }, finish: { kind: 'result_handling', config: {} } },
    transitions: [{ id: 't1', from: 'groom', port: 'groomed', to: 'finish' }],
  },
  layout: { nodes: { groom: { x: 0, y: 0 }, finish: { x: 200, y: 0 } } },
}

describe('workflow document', () => {
  it('adds a node with a free id and lists its unconnected ports', () => {
    const { draft, id } = addNode(base, 'owner_wait')
    expect(id).toBe('owner_wait_1')
    expect(problems(draft)).toEqual(['owner_wait_1: port admit is not connected.', 'owner_wait_1: port decline is not connected.'])
    expect(base.definition.nodes.owner_wait_1).toBeUndefined()
  })
  it('connects one transition per port and disconnects it', () => {
    const { draft, id } = addNode(base, 'owner_wait')
    const wired = connect(connect(draft, id, 'admit', 'finish'), id, 'decline', 'finish')
    expect(problems(wired)).toEqual([])
    expect(transitionOf(connect(wired, id, 'admit', 'groom'), id, 'admit')?.to).toBe('groom')
    expect(transitionOf(connect(wired, id, 'admit', ''), id, 'admit')).toBeNull()
  })
  it('reorders nodes and removes one with its transitions', () => {
    expect(orderedIds(base)).toEqual(['groom', 'finish'])
    const swapped = reorder(base, 'finish', -1)
    expect(orderedIds(swapped)).toEqual(['finish', 'groom'])
    expect(swapped.layout.nodes).toEqual({ groom: { x: 200, y: 0 }, finish: { x: 0, y: 0 } })
    expect(nodeIds(swapped)).toEqual(['groom', 'finish'])
    expect(removeNode(base, 'finish').definition.transitions).toEqual([])
  })
  it('sets and clears a node setting', () => {
    const { draft, id } = addNode(base, 'assignment')
    expect(setConfig(draft, id, 'role', 'general').definition.nodes[id]!.config).toEqual({ role: 'general' })
    expect(setConfig(setConfig(draft, id, 'role', 'general'), id, 'role', '').definition.nodes[id]!.config).toEqual({})
  })
})
