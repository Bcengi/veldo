import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TreeTable from './TreeTable.vue'
import type { TreeRow } from './tree-table'

const rows: TreeRow[] = [
  { id: 'a', cells: { name: 'Spec A', state: 'open' }, children: [{ id: 'a1', cells: { name: 'Unit A1', state: 'running' } }] },
  { id: 'b', cells: { name: 'Spec B', state: 'done' } },
]
const columns = [{ id: 'name', header: 'Name', primary: true }, { id: 'state', header: 'State' }]

describe('TreeTable', () => {
  it('shows nested rows only after their parent is expanded', async () => {
    const wrapper = mount(TreeTable, { props: { rows, columns, label: 'Backlog' } })
    const grid = () => wrapper.findAll('table tbody tr').map((r) => r.attributes('data-row'))
    expect(grid()).toEqual(['a', 'b'])
    const toggle = wrapper.find('table button[aria-label="Expand Spec A"]')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')
    expect(grid()).toEqual(['a', 'a1', 'b'])
    expect(wrapper.find('table button[aria-label="Collapse Spec A"]').attributes('aria-expanded')).toBe('true')
  })
  it('renders every row as a phone card with the same expand control', async () => {
    const wrapper = mount(TreeTable, { props: { rows, columns, label: 'Backlog', expandedByDefault: true } })
    expect(wrapper.findAll('.tree-cards li').map((r) => r.attributes('data-row'))).toEqual(['a', 'a1', 'b'])
    expect(wrapper.find('.tree-cards button').attributes('aria-label')).toBe('Collapse Spec A')
  })
})

describe('TreeTable reorder', () => {
  it('emits a move when a top-level row is dropped on another', async () => {
    const wrapper = mount(TreeTable, { props: { rows, columns, label: 'Backlog', reorderable: true } })
    const [a, b] = wrapper.findAll('table tbody tr')
    expect(a!.attributes('draggable')).toBe('true')
    const dataTransfer = { setData: () => undefined, effectAllowed: '' }
    await b!.trigger('dragstart', { dataTransfer })
    await a!.trigger('dragover', { dataTransfer })
    await a!.trigger('drop', { dataTransfer })
    expect(wrapper.emitted('move')).toEqual([['b', 0]])
  })
})
