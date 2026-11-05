import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

/** VELDO-0239 AC1: the owner starts a project's batch from the project view. The view sends the batch command,
 * `/batch <project>`, through the same common intake the Telegram command reaches, and shows the intake's answer
 * (the batch's outcome) or its refusal; nothing is decided here. */
const item = (id: string, data: Record<string, unknown>) => ({ id, kind: 'project', version: 1, digest: 'd', data })
const answer = {
  items: { project: [item('project:core', { name: 'core', state: 'ACTIVE' })], objective: [], intake_proposal: [], intake_question: [] },
  landing: { core: { remote: 'origin', trunk: 'main' } },
  watermark: { seq: 1 },
}
const sent: Array<[string, string | undefined]> = []
const reply = { value: { outcome: 'batch', batch_outcome: 'green', batch: 'batch-1' } as Record<string, unknown> }
let refuse = false

vi.mock('@/composables/useLiveRead', () => ({
  useLiveRead: () => ({
    state: ref('ready'), data: ref(answer), refusal: ref(null), live: ref('live'), readAt: ref(null),
    start: () => undefined, stop: () => undefined, refresh: () => undefined,
  }),
}))
vi.mock('@/composables/useMedia', () => ({ useDesktop: () => ref(true), useMedia: () => ref(true) }))
vi.mock('@/api/messages', () => ({
  sendMessage: async (text: string, project?: string) => {
    sent.push([text, project])
    if (refuse) {
      const { ApiRefusal } = await import('@/api/refusal')
      throw new ApiRefusal(403, 'unauthorized:project_owner', 'unauthorized')
    }
    return reply.value
  },
}))

const { default: ProjectsView } = await import('@/views/ProjectsView.vue')
const { batchCommand } = await import('@/features/projects/projects')

async function screen(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/projects', name: 'projects', component: ProjectsView },
    { path: '/projects/:project', name: 'project', component: ProjectsView }] })
  await router.push(path)
  const wrapper = mount(ProjectsView, { global: { plugins: [router], stubs: { MessageBox: true, LiveMeta: true, FactorySheet: true } } })
  await flushPromises()
  return wrapper
}

describe('ProjectsView batch (VELDO-0239 AC1)', () => {
  it('words the batch command as the Telegram command', () => {
    expect(batchCommand('core')).toBe('/batch core')
  })
  it('starts the selected project\'s batch through the intake and shows its outcome', async () => {
    sent.length = 0
    refuse = false
    const wrapper = await screen('/projects/core')
    const detail = wrapper.get('[data-testid="project-detail"]')
    await detail.get('[data-testid="project-batch"]').trigger('click')
    await flushPromises()
    expect(sent).toEqual([['/batch core', 'core']])
    const shown = detail.get('[data-testid="project-batch-answer"]')
    expect(shown.attributes('data-outcome')).toBe('green')
    expect(shown.text()).toContain('batch-1')
  })
  it('shows the refusal when the batch is not started', async () => {
    sent.length = 0
    refuse = true
    const wrapper = await screen('/projects/core')
    await wrapper.get('[data-testid="project-batch"]').trigger('click')
    await flushPromises()
    expect(sent).toEqual([['/batch core', 'core']])
    expect(wrapper.find('[data-testid="project-batch-answer"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('unauthorized')
  })
})
