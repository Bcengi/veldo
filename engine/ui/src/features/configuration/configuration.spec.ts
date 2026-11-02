import { describe, expect, it } from 'vitest'
import type { ConfigurationRevision } from '@/api/configuration'
import type { ReadAnswer } from '@/api/types'
import { namedRoles, roleView, teamsOf } from './configuration'

const item = (id: string, kind: string, version: number, data: Record<string, unknown>) => ({ id, kind, version, digest: 'd', data })
const answer = {
  items: {
    team: [item('team:project-a', 'team', 3, { project: 'project-a', team: { roles: { builder: { capability_configuration: { role: 'general', revision: 2 } } } } })],
    default_team_revision: [item('d1', 'default_team_revision', 1, { revision: 1, team: { roles: { builder: { capability_configuration: { role: 'general', revision: 1 } } } } })],
  },
} as unknown as ReadAnswer
const rev = (revision: number, tools: string[]): ConfigurationRevision => ({
  role: 'general', engine: 'claude_code', revision, digest: `d${revision}`, previous: null, instructions: [], settings: {},
  native_tools: tools.map((name) => ({ name, load: 'always' })), skills: [],
  mcp: revision > 1 ? [{ server: 'atlassian', revision: 1, tools: ['jira_search'], load: 'always' }] : [],
})

describe('configuration', () => {
  it('lists project teams and the newest default team', () => {
    expect(teamsOf(answer).map((t) => [t.project, t.version, t.roles])).toEqual([['project-a', 3, ['builder']], ['default', 1, ['builder']]])
  })
  it('names each configuration the teams use, with the teams', () => {
    expect([...namedRoles(answer)]).toEqual([['general', ['project-a', 'default']]])
  })
  it('shows the newest revision with its exact tools and servers, history newest first', () => {
    const view = roleView('general', [rev(1, ['Read']), rev(2, ['Read', 'Bash'])], ['project-a'])
    expect(view!.current.tools).toEqual(['Read (always)', 'Bash (always)'])
    expect(view!.current.servers).toEqual(['atlassian r1: jira_search (always)'])
    expect(view!.history.map((r) => r.revision)).toEqual([2, 1])
  })
})

describe('stored configurations (fix round 2)', () => {
  it('lists every stored role revision and skill, named by a team or not', async () => {
    const { skillsOf, storedRoles } = await import('./configuration')
    const stored = { items: {
      agent_configuration: [item('c1', 'agent_configuration', 1, { ...rev(1, ['Read']), role: 'reviewer' }), item('c2', 'agent_configuration', 1, { ...rev(2, ['Read']) })],
      agent_skill: [item('s1', 'agent_skill', 1, { skill: 'coding', source: 'factory', path: 'skills/coding.md', revision: 1 })],
    } } as unknown as ReadAnswer
    expect([...storedRoles(stored).keys()].sort()).toEqual(['general', 'reviewer'])
    expect(skillsOf(stored)).toEqual([{ skill: 'coding', revision: 1, source: 'factory', path: 'skills/coding.md' }])
  })
})
