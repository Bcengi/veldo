import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

/** VELDO-0235 AC3: the project screen names each project's landing destination in words, on its card and in its
 * detail panel, with the remote and trunk the objectives read serves. */
const item = (id: string, data: Record<string, unknown>) => ({ id, kind: 'project', version: 1, digest: 'd', data })
const answer = {
  items: {
    project: [
      item('project:core', { name: 'core', state: 'ACTIVE', landing_destination: 'land_locally' }),
      item('project:site', { name: 'site', state: 'ACTIVE' })],
    objective: [], intake_proposal: [], intake_question: [],
  },
  landing: { core: { remote: 'origin', trunk: 'main' }, site: { remote: 'origin', trunk: 'main' } },
  watermark: { seq: 1 },
}

vi.mock('@/composables/useLiveRead', () => ({
  useLiveRead: () => ({
    state: ref('ready'), data: ref(answer), refusal: ref(null), live: ref('live'), readAt: ref(null),
    start: () => undefined, stop: () => undefined, refresh: () => undefined,
  }),
}))
vi.mock('@/composables/useMedia', () => ({ useDesktop: () => ref(true), useMedia: () => ref(true) }))

const { default: ProjectsView } = await import('@/views/ProjectsView.vue')

async function screen(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/projects', name: 'projects', component: ProjectsView },
    { path: '/projects/:project', name: 'project', component: ProjectsView }] })
  await router.push(path)
  const wrapper = mount(ProjectsView, { global: { plugins: [router], stubs: { MessageBox: true, LiveMeta: true, FactorySheet: true } } })
  await flushPromises()
  return wrapper
}

describe('ProjectsView landing destination (VELDO-0235 AC3)', () => {
  it('names each project\'s destination on its card', async () => {
    const wrapper = await screen('/projects')
    const named = Object.fromEntries(wrapper.findAll('[data-project]').filter((e) => e.element.tagName === 'LI')
      .map((card) => [card.attributes('data-project'), card.get('[data-testid="project-destination"]').text()]))
    expect(named).toEqual({ core: 'land locally on main, nothing pushed', site: 'land and push to origin' })
  })
  it('names the selected project\'s destination in its detail panel', async () => {
    const wrapper = await screen('/projects/core')
    const detail = wrapper.get('[data-testid="project-detail"]')
    expect(detail.attributes('data-project')).toBe('core')
    expect(detail.get('[data-testid="project-detail-destination"]').text()).toBe('land locally on main, nothing pushed')
    expect(detail.text()).not.toContain('its remote')
    expect(detail.text()).not.toContain('its trunk')
  })
})
