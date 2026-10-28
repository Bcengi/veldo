import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as decisions from '@/api/decisions'
import { ApiRefusal } from '@/api/refusal'
import { item, read, receipt } from '@/test/builders'
import { mountWith } from '@/test/mount'
import DecisionDetail from './DecisionDetail.vue'
import { pendingDecisions } from './inbox'

const decision = () =>
  pendingDecisions(
    read({
      assignment: [item('assignment:r:de1', 'assignment', { alias: 'de1', kind: 'decision', state: 'OFFERED', request_version: 1, owner: 'owner', scope: ['p'] })],
      channel_presentation: [item('p1', 'channel_presentation', receipt('assignment:r:de1', { presentation_version: 3, presentation_id: 'p-3' }))],
    }),
  )[0]!

async function answer(wrapper: ReturnType<typeof mountWith>, choice: string, rationale: string) {
  await wrapper.get(`[data-choice="${choice}"] input`).setValue(true)
  await wrapper.get('[data-testid="rationale"]').setValue(rationale)
  await wrapper.get('form').trigger('submit')
}

describe('DecisionDetail', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows the question, risk, choices and the presented text exactly as the receipt holds them', () => {
    const wrapper = mountWith(DecisionDetail, { props: { decision: decision() } })
    expect(wrapper.get('[data-testid="question"]').text()).toBe('Decide assignment:r:de1.')
    expect(wrapper.get('[data-testid="risk"]').text()).toBe('Low risk.')
    expect(wrapper.findAll('[data-choice]').map((c) => c.attributes('data-choice'))).toEqual(['accept', 'return_for_elaboration', 'reject'])
    expect(wrapper.get('[data-testid="rendered"]').text()).toBe('Veldo needs your decision\nChoices: accept | reject')
  })

  it('sends the answer bound to the presentation version shown', async () => {
    const send = vi.spyOn(decisions, 'sendAnswer').mockResolvedValue({ outcome: 'settled', ruling: 'approve', api_request_id: 'api-1' })
    const wrapper = mountWith(DecisionDetail, { props: { decision: decision() } })
    await answer(wrapper, 'accept', 'because')
    await flushPromises()
    expect(send).toHaveBeenCalledWith({
      request_id: 'assignment:r:de1',
      request_version: 1,
      presentation_id: 'p-3',
      presentation_digest: 'sha256:brief',
      presentation_version: 3,
      choice: 'accept',
      rationale: 'because',
    })
    expect(wrapper.get('[data-testid="answer-result"]').text()).toContain('Answer sent')
    expect(wrapper.emitted('settled')).toHaveLength(1)
  })

  it('shows a refusal by name beside the action and claims nothing', async () => {
    vi.spyOn(decisions, 'sendAnswer').mockRejectedValue(new ApiRefusal(409, 'stale_version:stale_presentation', 'stale_version'))
    const wrapper = mountWith(DecisionDetail, { props: { decision: decision() } })
    await answer(wrapper, 'reject', 'no')
    await flushPromises()
    const bar = wrapper.get('[data-testid="answer-bar"]')
    expect(bar.get('[data-testid="refusal"]').attributes('data-refusal')).toBe('stale_version:stale_presentation')
    expect(wrapper.find('[data-testid="answer-result"]').exists()).toBe(false)
    expect(wrapper.emitted('settled')).toBeUndefined()
  })

  it('keeps the action in place and disabled while the answer is in flight', async () => {
    let settle!: (v: decisions.AnswerResult) => void
    vi.spyOn(decisions, 'sendAnswer').mockReturnValue(new Promise((resolve) => (settle = resolve)))
    const wrapper = mountWith(DecisionDetail, { props: { decision: decision() } })
    await answer(wrapper, 'accept', 'why')
    const button = wrapper.get('[data-testid="send-answer"]')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.text()).toContain('Sending answer')
    settle({ outcome: 'settled', api_request_id: 'a' })
    await flushPromises()
  })

  it('sends nothing without a choice and a rationale', async () => {
    const send = vi.spyOn(decisions, 'sendAnswer')
    const wrapper = mountWith(DecisionDetail, { props: { decision: decision() } })
    await wrapper.get('form').trigger('submit')
    expect(wrapper.text()).toContain('Pick one of the choices first.')
    expect(send).not.toHaveBeenCalled()
  })

  it('offers no answer for a request not presented yet', () => {
    const unpresented = { ...decision(), presentation: null }
    const wrapper = mountWith(DecisionDetail, { props: { decision: unpresented } })
    expect(wrapper.find('[data-testid="unpresented"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="send-answer"]').exists()).toBe(false)
  })
})
