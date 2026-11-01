import { describe, expect, it } from 'vitest'
import type { StoredServer } from '@/api/mcp'
import { catalogRow, credentialMeta } from './catalog'

const server = (revision: number, extra: Partial<StoredServer> = {}): StoredServer => ({
  id: 'atlassian', label: 'Atlassian', transport: 'http', command: null, arguments: [], url: 'https://mcp.example/v1',
  environment: {}, headers: { Authorization: { reference: 'veldo-credential:atl' } }, hosts: ['linux'], read_only_tools: ['jira_search'], revision, ...extra,
})

describe('catalog', () => {
  it('shows the newest revision with its history and credential references', () => {
    const row = catalogRow([server(1), server(2, { hosts: ['linux', 'mac'] })])
    expect(row).toMatchObject({ revision: 2, hosts: ['linux', 'mac'], history: [2, 1], target: 'https://mcp.example/v1' })
    expect(row!.credentials).toEqual([{ name: 'Authorization', where: 'header', reference: 'veldo-credential:atl' }])
  })
  it('shows an older revision when asked', () => {
    expect(catalogRow([server(1), server(2, { hosts: ['mac'] })], 1)!.hosts).toEqual(['linux'])
  })
  it('finds this session\'s credential record by reference, never a value', () => {
    const meta = { id: 'atl', label: 'Atlassian token', setAt: 1, setBy: 'owner', reference: 'veldo-credential:atl', version: 1, deleted: false }
    expect(credentialMeta({ atl: meta }, 'veldo-credential:atl')).toBe(meta)
    expect(credentialMeta({}, 'x')).toBeNull()
  })
})

describe('the catalog read (fix round 2)', () => {
  it('lists every head and every credential record by metadata, its reference derived from the entity id', async () => {
    const { credentialsOf, headsOf, referenceOfEntity } = await import('./catalog')
    const item = (id: string, kind: string, data: Record<string, unknown>) => ({ id, kind, version: 2, digest: 'd', data })
    const answer = { items: {
      mcp_server_head: [item('mcp-head:2', 'mcp_server_head', { id: 'github', revision: 1 }), item('mcp-head:1', 'mcp_server_head', { id: 'atlassian', revision: 2 })],
      credential: [item('credential:abc', 'credential', { id: 'github-token', label: 'GitHub', set_at: 5, set_by: 'owner', reference: '[redacted]' })],
    } } as never
    expect(headsOf(answer)).toEqual([{ id: 'atlassian', revision: 2 }, { id: 'github', revision: 1 }])
    expect(credentialsOf(answer)).toEqual([{ id: 'github-token', label: 'GitHub', setAt: 5, setBy: 'owner', reference: 'keychain:veldo/abc', version: 2, deleted: false }])
    expect(referenceOfEntity('credential:abc')).toBe('keychain:veldo/abc')
  })
})
