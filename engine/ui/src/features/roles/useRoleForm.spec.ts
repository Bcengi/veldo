import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRefusal } from '@/api/refusal'

const api = vi.hoisted(() => ({
  latestRevision: vi.fn(),
  readConfiguration: vi.fn(),
  saveConfiguration: vi.fn(),
}))
vi.mock('@/api/configuration', () => api)

import { useRoleForm } from './useRoleForm'

const revision = (n: number) => ({
  role: 'builder_jira', engine: 'claude_code', native_tools: [], mcp: [], skills: [], instructions: [], settings: {},
  revision: n, digest: `sha256:${n}`, previous: null,
})

describe('useRoleForm', () => {
  beforeEach(() => {
    api.latestRevision.mockResolvedValue(1)
    api.readConfiguration.mockImplementation(async (_role: string, n: number) => revision(n))
  })

  it('saves bound to the revision the draft was edited from and shows the revision read back', async () => {
    api.saveConfiguration.mockResolvedValue({ outcome: 'saved', revision: 2, api_request_id: 'a' })
    const form = useRoleForm()
    await form.open('builder_jira')
    api.latestRevision.mockResolvedValue(7)
    await form.save()
    expect(api.saveConfiguration).toHaveBeenCalledWith(expect.objectContaining({ role: 'builder_jira' }), 1)
    expect(form.saved.value?.revision).toBe(2)
    expect(form.draft.value?.editedFrom).toBe(2)
  })

  it('keeps a stale refusal beside the save and the draft on the revision it was edited from', async () => {
    api.saveConfiguration.mockRejectedValue(new ApiRefusal(409, 'stale_version', 'stale_version'))
    const form = useRoleForm()
    await form.open('builder_jira')
    await form.save()
    expect(form.saveRefusal.value?.refusal).toBe('stale_version')
    expect(form.saved.value).toBeNull()
    expect(form.draft.value?.editedFrom).toBe(1)
  })
})
