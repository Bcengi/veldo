import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { intakeOf, projectsOf, searchProjects } from './projects'

const item = (id: string, kind: string, data: Record<string, unknown>) => ({ id, kind, version: 1, digest: 'd', data })
const answer = {
  items: {
    project: [item('project:b', 'project', { name: 'b', state: 'ACTIVE', charter: { purpose: 'Billing' } }), item('project:a', 'project', { name: 'a', state: 'PAUSED', charter: { purpose: 'Importer' } })],
    objective: [item('objective:1', 'objective', { project: 'a', state: 'ACTIVE', bound: { outcome: 'Parse files', scope: ['x'], evidence_requirements: [{ id: 'g', kind: 'gate_observation' }] } })],
    intake_proposal: [item('proposal:1', 'intake_proposal', { text: 'Add CSV export', project: 'a', state: 'PROPOSED', principal: 'owner' })],
    intake_question: [],
  },
} as unknown as ReadAnswer

describe('projects', () => {
  it('lists projects by name with their objectives', () => {
    const projects = projectsOf(answer)
    expect(projects.map((p) => p.name)).toEqual(['a', 'b'])
    expect(projects[0]!.objectives[0]!.evidence).toEqual([{ id: 'g', kind: 'gate_observation' }])
  })
  it('searches names, purposes and objective outcomes', () => {
    expect(searchProjects(projectsOf(answer), 'parse').map((p) => p.name)).toEqual(['a'])
    expect(searchProjects(projectsOf(answer), 'billing active').map((p) => p.name)).toEqual(['b'])
    expect(searchProjects(projectsOf(answer), '').length).toBe(2)
  })
  it('reads the intake\'s records of messages', () => {
    expect(intakeOf(answer)).toEqual([{ id: 'proposal:1', text: 'Add CSV export', project: 'a', state: 'PROPOSED', principal: 'owner', kind: 'proposal' }])
  })
})
