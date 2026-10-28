import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { ApiRefusal } from '@/api/refusal'
import StatePanel from './StatePanel.vue'

describe('StatePanel', () => {
  it('renders exactly one state', () => {
    for (const state of ['loading', 'empty', 'ready'] as const) {
      const wrapper = mount(StatePanel, { props: { state, emptyTitle: 'Nothing yet' }, slots: { default: '<p class="data">data</p>' } })
      expect(wrapper.findAll('[data-state]').map((e) => e.attributes('data-state'))).toEqual([state])
      expect(wrapper.find('.data').exists()).toBe(state === 'ready')
    }
  })

  it('names the refusal of an error and shows no data', () => {
    const wrapper = mount(StatePanel, {
      props: { state: 'error', refusal: new ApiRefusal(401, 'unauthenticated:no_session', 'unauthenticated') },
      slots: { default: '<p class="data">data</p>' },
    })
    expect(wrapper.get('[data-testid="refusal"]').attributes('data-refusal')).toBe('unauthenticated:no_session')
    expect(wrapper.text()).toContain('unauthenticated:no_session')
    expect(wrapper.find('.data').exists()).toBe(false)
  })
})
