import { describe, expect, it } from 'vitest'
import type { ConfigurationRevision } from '@/api/configuration'
import { emptyDraft, fromRevision, names, settingProblem, toDefinition } from './role-draft'

const stored: ConfigurationRevision = {
  role: 'builder_jira',
  engine: 'claude_code',
  native_tools: [{ name: 'Read', load: 'always' }],
  mcp: [{ server: 'atlassian', revision: 1, tools: 'all', load: 'when assigned' }],
  skills: [{ skill: 'coding', revision: 1, load: 'when assigned' }],
  instructions: [{ source: 'factory', path: 'instructions/build.md', load: 'always' }],
  settings: { model: 'sonnet', max_turns: 30 },
  revision: 4,
  digest: 'sha256:x',
  previous: 'sha256:w',
}

describe('role draft', () => {
  it('is edited from the stored revision and sends back every field exactly', () => {
    const draft = fromRevision(stored)
    expect(draft.editedFrom).toBe(4)
    const { revision: _r, digest: _d, previous: _p, ...definition } = stored
    expect(toDefinition(draft)).toEqual(definition)
  })

  it('starts a new role from revision 0 with nothing granted', () => {
    expect(emptyDraft('reviewer')).toMatchObject({ role: 'reviewer', editedFrom: 0, native_tools: [], mcp: [], settings: [] })
  })

  it('keeps a setting that was not text as JSON and names one that no longer parses', () => {
    const draft = fromRevision(stored)
    expect(draft.settings).toContainEqual({ key: 'max_turns', value: '30', json: true })
    expect(settingProblem({ key: 'max_turns', value: '3x', json: true })).toMatch(/not valid JSON/)
    expect(settingProblem({ key: '', value: 'x', json: false })).toMatch(/needs a name/)
  })

  it('reads a comma separated list without blanks or repeats', () => {
    expect(names(' jira_get_issue, ,jira_search, jira_get_issue ')).toEqual(['jira_get_issue', 'jira_search'])
  })
})
