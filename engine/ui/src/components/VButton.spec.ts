import { describe, expect, it } from 'vitest'
import { mountWith } from '@/test/mount'
import VButton from './VButton.vue'

/** VELDO-0229 AC1: VButton is adapted onto Nuxt UI's UButton with its interface unchanged. */
describe('VButton on UButton', () => {
  it('renders a Nuxt UI button with its label, type and passed attributes', () => {
    const wrapper = mountWith(VButton, { props: { label: 'Send answer', type: 'submit' }, attrs: { 'data-testid': 'send', 'aria-describedby': 'why' } })
    const button = wrapper.get('button')
    expect(button.attributes('data-slot')).toBe('base')
    expect(button.classes()).toContain('vbtn')
    expect(button.attributes('type')).toBe('submit')
    expect(button.attributes('data-testid')).toBe('send')
    expect(button.attributes('aria-describedby')).toBe('why')
    expect(button.text()).toBe('Send answer')
  })

  it('shows the pending label, disables the button and marks it busy while pending', () => {
    const wrapper = mountWith(VButton, { props: { label: 'Send answer', pendingLabel: 'Sending answer', pending: true } })
    const button = wrapper.get('button')
    expect(button.text()).toBe('Sending answer')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-busy')).toBe('true')
    expect(button.classes()).toContain('is-pending')
  })

  it('keeps the label when no pending label is given', () => {
    const wrapper = mountWith(VButton, { props: { label: 'Refresh', pending: true } })
    expect(wrapper.get('button').text()).toBe('Refresh')
  })

  it('is disabled when asked and emits no click then', async () => {
    const wrapper = mountWith(VButton, { props: { label: 'Save', disabled: true } })
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('click')).toBeUndefined()
  })

  it('emits click with the mouse event', async () => {
    const wrapper = mountWith(VButton, { props: { label: 'Save' } })
    await wrapper.get('button').trigger('click')
    const [event] = wrapper.emitted('click')![0] as [MouseEvent]
    expect(event).toBeInstanceOf(MouseEvent)
  })

  it('maps the variants and sizes onto Veldo classes, the default type being button', () => {
    const wrapper = mountWith(VButton, { props: { label: 'Sign out', variant: 'danger', size: 'small', block: true } })
    const button = wrapper.get('button')
    expect(button.attributes('type')).toBe('button')
    expect(button.classes()).toEqual(expect.arrayContaining(['vbtn-danger', 'vbtn-small', 'vbtn-block']))
  })
})
