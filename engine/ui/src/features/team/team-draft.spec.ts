import { describe, expect, it } from 'vitest'
import type { Team, TeamRecord } from '@/api/configuration'
import { currentOf, editedFromOf, newRow, pendingOf, rowsOf, toTeam } from './team-draft'

const role = (configuration: string | null, kind: 'required' | 'specialist' = 'required') => ({
  kind,
  ...(configuration ? { capability_configuration: { role: configuration, revision: 1 } } : {}),
  workers: ['w-1'],
  responsibilities: ['report'],
  expertise: ['python'],
  proposal_permissions: ['finding'],
  engines: ['claude_code'],
  budget: { capacity: 1, invocations: 2, wall_seconds: 100 },
  independence: { distinct_from: [] },
})
const team = (extra: Record<string, ReturnType<typeof role>> = {}): Team => ({
  roles: { implementation: role('general'), project_manager: role('general'), ...extra },
})
const record = (over: Partial<TeamRecord> = {}): TeamRecord => ({ revision: 2, version: 3, team: team(), digest: 'd', proposal: null, ...over })

describe('team draft', () => {
  it('sends back the team it was read from, required roles first', () => {
    const value = team({ builder_jira: role('builder_jira', 'specialist') })
    const rows = rowsOf(value)
    expect(rows.map((r) => r.name)).toEqual(['project_manager', 'implementation', 'builder_jira'])
    expect(toTeam(rows)).toEqual(value)
  })

  it('sends a role whose configuration is left blank without a reference, for the authority to refuse by name', () => {
    const rows = rowsOf(team())
    rows[0]!.configRole = ''
    rows[0]!.configRevision = ''
    expect(toTeam(rows).roles.project_manager).not.toHaveProperty('capability_configuration')
  })

  it('adds a new role as a specialist with no configuration', () => {
    expect(newRow('builder_jira')).toMatchObject({ kind: 'specialist', configRole: '', configRevision: '' })
  })

  it('shows as current only the accepted revision, never a pending proposal', () => {
    const proposal = { revision: 3, team: team({ extra: role('general') }), digest: 'p', proposed_by: 'owner2' }
    const read = record({ proposal })
    expect(currentOf(read)).toEqual({ revision: 2, team: read.team })
    expect(pendingOf(read)).toEqual(proposal)
    expect(currentOf(null)).toBeNull()
  })

  it('binds a project team to its team version and the default team to its revision', () => {
    expect(editedFromOf(record(), false)).toBe(3)
    expect(editedFromOf(record(), true)).toBe(2)
    expect(editedFromOf(null, true)).toBe(0)
  })
})
