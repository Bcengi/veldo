import { describe, expect, it } from 'vitest'
import type { KeepCommand } from '@/api/actions'
import { canonicalJson, commandChallenge, keepCommand, keepPick, keepTarget, unsignedKeeps } from './keep'
import type { PendingAnswer, PendingItem } from './space'

/** VELDO-0319 AC5 to AC7: the console's side of the owner's Keep. The canonical bytes and their digest below are
 * the store's own for this command (control_store.canonical_bytes); row ac5/console-bytes of suite
 * 150_veldo_0319_space_screen computes them with the store and requires this file to hold them. */
const COMMAND: KeepCommand = {
  principal: 'owner',
  operation: 'space_disposition',
  command_id: 'keep-0001',
  nonce: 'nonce-0001',
  parameters: { item: 'space:item:\u00e9t\u00e9/"quoted"', version: 7, request: 'assignment:r:alias-1' },
}
// prettier-ignore
const STORE_BYTES = "{\"command_id\":\"keep-0001\",\"nonce\":\"nonce-0001\",\"operation\":\"space_disposition\",\"parameters\":{\"item\":\"space:item:\\u00e9t\\u00e9/\\\"quoted\\\"\",\"request\":\"assignment:r:alias-1\",\"version\":7},\"principal\":\"owner\"}"
const STORE_DIGEST = 'aJf8ADwho1hwbHfb2CLq9B_J0yWQ9igmM4eqQ_5qXYo'

const meta = { schema: 'veldo.api_space/v1', view: 'pending', problems: [], redacted: [], watermark: { seq: 7, record_digest: 'd', committed_at: 1 }, freshness: 'live' as const }
const item = (over: Partial<PendingItem> = {}): PendingItem => ({
  id: 'space:item:a', version: 3, state: 'deferred', kind: 'worktree',
  owner: { scope: { type: 'project', id: 'orchard' }, ticket: null, run: 'review-1', station: 'review', gate: null, lane: null, session: null },
  locator: '/srv/veldo/worktrees/orchard/review-1', pool: 'main', bytes: 2048, measured_at: 'run_finished', due_event: 'ticket_ended',
  rule: 'unique_work', reason: 'uncommitted changes in 3 files', refused_at: 'ticket_ended', attempts: 1, retry: ['ticket_ended'],
  request: 'alias-1', group: null, index: null, request_id: 'assignment:r:alias-1', answered: null, ...over,
})
const pending = (items: PendingItem[]): PendingAnswer => ({ ...meta, items, requests: [], signing: 'console.example' })

describe('canonicalJson', () => {
  it('writes the bytes the store signs: sorted keys, no spaces, every character outside ASCII escaped', () => {
    expect(canonicalJson(COMMAND)).toBe(STORE_BYTES)
  })
  it('does not depend on the order the command was built in', () => {
    const { parameters, nonce, principal, operation, command_id } = COMMAND
    expect(canonicalJson({ nonce, parameters: { version: 7, request: parameters.request, item: parameters.item }, command_id, operation, principal })).toBe(STORE_BYTES)
  })
  it('escapes as the store does: control characters, DEL, and a character beyond the basic plane as its two halves', () => {
    expect(canonicalJson('a\n\t\u0001\u007f\u00ff')).toBe('"a\\n\\t\\u0001\\u007f\\u00ff"')
    expect(canonicalJson('\u{1f600}')).toBe('"\\ud83d\\ude00"')
    expect(canonicalJson([true, null, 3, 'x'])).toBe('[true,null,3,"x"]')
  })
  it('refuses a number that is not a whole number rather than write bytes the store would not', () => {
    expect(() => canonicalJson({ version: 1.5 })).toThrow()
  })
})

describe('commandChallenge', () => {
  it('is SHA-256 of the canonical bytes, unpadded base64url: the challenge the Ledger expects', async () => {
    expect(await commandChallenge(COMMAND)).toBe(STORE_DIGEST)
  })
  it('changes with the item, the version and the request, so an assertion is good for one command only', async () => {
    const other = (parameters: Partial<KeepCommand['parameters']>) => commandChallenge({ ...COMMAND, parameters: { ...COMMAND.parameters, ...parameters } })
    const made = await Promise.all([other({ item: 'space:item:b' }), other({ version: 8 }), other({ request: 'assignment:r:alias-2' })])
    expect(new Set([STORE_DIGEST, ...made]).size).toBe(4)
  })
})

describe('keepPick', () => {
  it('reads a Keep for the whole request, a Keep for one member, and nothing else', () => {
    expect(keepPick('accept keep')).toBeNull()
    expect(keepPick('accept keep w2')).toBe(2)
    expect(keepPick('accept save')).toBeUndefined()
    expect(keepPick('accept discard w2')).toBeUndefined()
    expect(keepPick('accept keep w0')).toBeUndefined()
    expect(keepPick('accept keep 2')).toBeUndefined()
    expect(keepPick(null)).toBeUndefined()
  })
})

describe('keepTarget', () => {
  const group = [
    item({ id: 'space:item:m1', index: 1, group: 'g', request: 'old', request_id: 'assignment:r:old' }),
    item({ id: 'space:item:m2', index: 2, group: 'g', request: 'new', request_id: 'assignment:r:new' }),
    item({ id: 'space:item:m3', index: 3, group: 'g', request: 'new', request_id: 'assignment:r:new' }),
  ]
  it('names the one worktree of a request of its own', () => {
    expect(keepTarget(pending([item()]), 'assignment:r:alias-1', 'accept keep')?.id).toBe('space:item:a')
  })
  it('names the member a pick names, and no other member of the request', () => {
    expect(keepTarget(pending(group), 'assignment:r:new', 'accept keep w3')?.id).toBe('space:item:m3')
    expect(keepTarget(pending(group), 'assignment:r:new', 'accept keep w1')).toBeNull()
  })
  it('names the first member for a Keep of the whole request', () => {
    expect(keepTarget(pending(group), 'assignment:r:new', 'accept keep')?.id).toBe('space:item:m2')
  })
  it('finds nothing for an answer that is not Keep, a request no item holds, or an item that is no longer deferred', () => {
    expect(keepTarget(pending([item()]), 'assignment:r:alias-1', 'accept discard')).toBeNull()
    expect(keepTarget(pending([item()]), 'assignment:r:other', 'accept keep')).toBeNull()
    expect(keepTarget(pending([item({ state: 'due' })]), 'assignment:r:alias-1', 'accept keep')).toBeNull()
    expect(keepTarget(null, 'assignment:r:alias-1', 'accept keep')).toBeNull()
  })
})

describe('keepCommand', () => {
  it('names the item at the version the read shows and the request of the item', () => {
    const command = keepCommand('owner', item({ version: 9 }), { commandId: 'c', nonce: 'n' })
    expect(command).toEqual({ principal: 'owner', operation: 'space_disposition', command_id: 'c', nonce: 'n', parameters: { item: 'space:item:a', version: 9, request: 'assignment:r:alias-1' } })
  })
  it('for a member whose group moved on, names the member\'s own request and not the group\'s current one', () => {
    const member = item({ id: 'space:item:m1', index: 1, group: 'g', request: 'old', request_id: 'assignment:r:old', answered: 'keep' })
    const others = [item({ id: 'space:item:m2', index: 2, group: 'g', request: 'new', request_id: 'assignment:r:new' })]
    expect(unsignedKeeps(pending([member, ...others])).map((one) => one.id)).toEqual(['space:item:m1'])
    expect(keepCommand('owner', member, { commandId: 'c', nonce: 'n' }).parameters.request).toBe('assignment:r:old')
  })
  it('gives each command an id and a nonce of its own', () => {
    const a = keepCommand('owner', item())
    const b = keepCommand('owner', item())
    expect(a.command_id).not.toBe(b.command_id)
    expect(a.nonce).not.toBe(b.nonce)
    expect(a.command_id.startsWith('console-keep-')).toBe(true)
  })
  it('makes no command for an item with no request', () => {
    expect(() => keepCommand('owner', item({ request_id: null }))).toThrow()
  })
})

describe('unsignedKeeps', () => {
  it('lists the items answered Keep that are still deferred, and no other', () => {
    const items = [item({ id: 'a', answered: 'keep' }), item({ id: 'b' }), item({ id: 'c', answered: 'keep', state: 'due' }), item({ id: 'd', answered: 'keep', request_id: null })]
    expect(unsignedKeeps(pending(items)).map((one) => one.id)).toEqual(['a'])
    expect(unsignedKeeps(null)).toEqual([])
  })
})
