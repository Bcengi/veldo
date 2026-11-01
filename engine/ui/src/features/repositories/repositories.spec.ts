import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { authorOf, identitiesOf, repositoriesOf } from './repositories'

const item = (id: string, data: Record<string, unknown>) => ({ id, kind: 'repository', version: 1, digest: 'd', data })

describe('repositories and identities', () => {
  it('reads each repository record with its remote, origin and state, a failure with its named reason', () => {
    const answer = { items: { repository: [
      item('repository:b', { name: 'importer', identity: 'work', path: '/srv/importer', remote: { url: 'git@github.com:acme/importer.git' }, origin: 'adopted', state: 'active', history: [] }),
      item('repository:a', { name: 'billing', identity: 'work', path: '/srv/billing', remote: { owner: 'acme', name: 'billing' }, origin: 'created', state: 'failed', reason: 'remote_exists', history: [{ step: 'remote', state: 'failed', reason: 'remote_exists' }] }),
    ] } } as unknown as ReadAnswer
    expect(repositoriesOf(answer).map((r) => [r.name, r.remote, r.origin, r.state, r.reason])).toEqual([
      ['billing', 'acme/billing', 'created', 'failed', 'remote_exists (at remote)'],
      ['importer', 'git@github.com:acme/importer.git', 'adopted', 'active', ''],
    ])
  })
  it('lists identities by label with their author', () => {
    const identities = [
      { id: 'b', label: 'Work', author_name: 'Owner', author_email: 'o@example.com', remote_host: 'github.com', remote_owner: 'acme', projects_root: '/srv', default_visibility: 'private', repositories: [] },
      { id: 'a', label: 'Personal', author_name: 'Owner', author_email: 'p@example.com', remote_host: 'github.com', remote_owner: 'me', projects_root: '/home', default_visibility: 'public', repositories: [] },
    ]
    expect(identitiesOf({ identities }).map((i) => i.label)).toEqual(['Personal', 'Work'])
    expect(authorOf(identities[0]!)).toBe('Owner <o@example.com>')
  })
})
