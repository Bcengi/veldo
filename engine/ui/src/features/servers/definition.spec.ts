import { describe, expect, it } from 'vitest'
import { emptyDraft, fromStored, lines, toDefinition } from './definition'

describe('server definition', () => {
  it('builds a stdio definition with literal and reference environment values and no url or headers', () => {
    const draft = {
      ...emptyDraft(),
      id: 'filesystem',
      label: 'Files',
      command: 'npx',
      argumentsText: '-y\n@modelcontextprotocol/server-filesystem\n\n/srv/projects\n',
      environment: [
        { name: 'LOG_LEVEL', kind: 'literal' as const, value: 'info' },
        { name: 'GITHUB_TOKEN', kind: 'reference' as const, value: 'keychain:veldo/abc' },
        { name: ' ', kind: 'literal' as const, value: 'ignored' },
      ],
      headers: [{ name: 'Authorization', kind: 'reference' as const, value: 'keychain:veldo/x' }],
      hostsText: 'veldo-linux-1',
      toolsText: 'read_file\nlist_directory',
    }
    expect(toDefinition(draft)).toEqual({
      id: 'filesystem',
      label: 'Files',
      transport: 'stdio',
      command: 'npx',
      arguments: ['-y', '@modelcontextprotocol/server-filesystem', '/srv/projects'],
      url: null,
      environment: { LOG_LEVEL: { literal: 'info' }, GITHUB_TOKEN: { reference: 'keychain:veldo/abc' } },
      headers: {},
      hosts: ['veldo-linux-1'],
      read_only_tools: ['read_file', 'list_directory'],
    })
  })

  it('builds an http definition whose headers are references only, and reads a stored revision back', () => {
    const draft = {
      ...emptyDraft(),
      id: 'atlassian',
      label: 'Atlassian',
      transport: 'http' as const,
      command: 'left over',
      argumentsText: 'left over',
      url: 'https://mcp.atlassian.com/v1/sse',
      headers: [{ name: 'Authorization', kind: 'literal' as const, value: 'keychain:veldo/def' }],
      hostsText: 'veldo-linux-1\nveldo-mac-1',
      toolsText: 'getJiraIssue',
    }
    const definition = toDefinition(draft)
    expect(definition).toMatchObject({ command: null, arguments: [], url: 'https://mcp.atlassian.com/v1/sse' })
    expect(definition.headers).toEqual({ Authorization: { reference: 'keychain:veldo/def' } })
    expect(toDefinition(fromStored({ ...definition, revision: 2 }))).toEqual(definition)
  })

  it('splits list fields into trimmed nonempty lines', () => {
    expect(lines(' a \n\n b\n')).toEqual(['a', 'b'])
  })
})
