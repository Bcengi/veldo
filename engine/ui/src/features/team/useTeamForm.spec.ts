import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRefusal } from '@/api/refusal'

const api = vi.hoisted(() => ({
  DEFAULT_TEAM: 'default',
  latestDefaultRevision: vi.fn(),
  readTeam: vi.fn(),
  saveTeam: vi.fn(),
  saveDefaultTeam: vi.fn(),
}))
vi.mock('@/api/configuration', () => api)

import { useTeamForm } from './useTeamForm'

const roles = { roles: {} }
const proposal = { revision: 4, team: { roles: { x: {} } }, digest: 'p', proposed_by: 'owner2' }

describe('useTeamForm', () => {
  beforeEach(() => {
    api.latestDefaultRevision.mockResolvedValue(9)
  })

  it('saves the default team bound to the revision it was edited from', async () => {
    api.readTeam.mockResolvedValueOnce({ revision: 2, team: roles, digest: 'd' })
    api.readTeam.mockResolvedValueOnce({ revision: 3, team: roles, digest: 'e' })
    api.saveDefaultTeam.mockResolvedValue({ outcome: 'saved', revision: 3, api_request_id: 'a' })
    const form = useTeamForm()
    await form.open('default')
    await form.save()
    expect(api.saveDefaultTeam).toHaveBeenCalledWith(roles, 2)
    expect(form.current.value?.revision).toBe(3)
  })

  it('saves a project team bound to its team version and shows a proposal as pending, not current', async () => {
    api.readTeam.mockResolvedValueOnce({ revision: 3, version: 5, team: roles, digest: 'd', proposal: null })
    api.readTeam.mockResolvedValueOnce({ revision: 3, version: 6, team: roles, digest: 'd', proposal })
    api.saveTeam.mockResolvedValue({ outcome: 'proposed', revision: 4, owner_request: 'assignment:r:a', api_request_id: 'a' })
    const form = useTeamForm()
    await form.open('project-a')
    await form.save()
    expect(api.saveTeam).toHaveBeenCalledWith('project-a', roles, 5)
    expect(form.current.value?.revision).toBe(3)
    expect(form.pending.value?.revision).toBe(4)
  })

  it('keeps the earlier revision current when a save is refused', async () => {
    api.readTeam.mockResolvedValueOnce({ revision: 3, version: 5, team: roles, digest: 'd', proposal: null })
    api.saveTeam.mockRejectedValue(new ApiRefusal(409, 'stale_version:stale_subject:version', 'stale_version'))
    const form = useTeamForm()
    await form.open('project-a')
    await form.save()
    expect(form.saveRefusal.value?.refusal).toBe('stale_version:stale_subject:version')
    expect(form.current.value?.revision).toBe(3)
    expect(api.readTeam).toHaveBeenCalledTimes(1)
  })
})
