import { describe, expect, it } from 'vitest'
import type { PendingDecision } from '@/features/decisions/inbox'
import {
  abandonText, bytesText, countText, holdSentence, hostNote, isEmpty, memberPicks, ownerText, pendingGroups, pendingReason,
  removedSpace, retryText, runHolds, scopeLabel, usageRows,
  type PendingAnswer, type PendingItem, type PoolsAnswer, type RemovedItem, type SpaceHold, type SpaceRead, type UsageAnswer,
} from './space'

const meta = { schema: 'veldo.api_space/v1', problems: [], redacted: [], watermark: { seq: 7, record_digest: 'd', committed_at: 1 }, freshness: 'live' as const }
const GIB = 1024 ** 3

const hold = (over: Partial<SpaceHold> = {}): SpaceHold => ({
  id: 'space:hold:dispatch/abc', version: 2, state: 'waiting', pool: 'main', scope: { type: 'project', id: 'orchard' },
  need: 4 * GIB, free: 10 * GIB, held: 3 * GIB, floor: 5 * GIB, source: 'declared', run: null, ...over,
})

const item = (over: Partial<PendingItem> = {}): PendingItem => ({
  id: 'space:item:a', version: 3, state: 'deferred', kind: 'worktree',
  owner: { scope: { type: 'project', id: 'orchard' }, ticket: 'VELDO-9001', run: 'run-1', station: 'review', gate: null, lane: null, session: null },
  locator: '/srv/veldo/worktrees/orchard/review-1', pool: 'main', bytes: 2048, measured_at: 'run_finished', due_event: 'ticket_ended',
  rule: 'unique_work', reason: 'uncommitted changes in 3 files', refused_at: 'ticket_ended', attempts: 2, retry: ['ticket_ended', 'project_ended'],
  request: null, group: null, index: null, ...over,
})

describe('bytesText', () => {
  it('writes bytes in binary units with one decimal, and whole bytes as they are', () => {
    expect(bytesText(0)).toBe('0 B')
    expect(bytesText(512)).toBe('512 B')
    expect(bytesText(1536)).toBe('1.5 KiB')
    expect(bytesText(4 * GIB)).toBe('4.0 GiB')
    expect(bytesText(1024 ** 6)).toBe('1024.0 PiB')
  })
  it('never shows a figure that was not recorded as zero', () => {
    expect(bytesText(null)).toBe('not recorded')
    expect(bytesText(undefined)).toBe('not recorded')
    expect(bytesText(Number.NaN)).toBe('not recorded')
    expect(bytesText(-1)).toBe('not recorded')
  })
})

describe('usageRows', () => {
  const usage: UsageAnswer = {
    ...meta, view: 'usage', worktrees: [],
    total: { bytes: 60, items: 4, unmeasured: 1 },
    scopes: [
      { scope: { type: 'project', id: 'orchard' }, bytes: 30, items: 2, unmeasured: 0, tickets: [
        { ticket: 'VELDO-9001', bytes: 30, items: 2, unmeasured: 0, kinds: [
          { kind: 'build_output', bytes: 10, items: 1, unmeasured: 0, measured_at: ['run_finished'] },
          { kind: 'worktree', bytes: 20, items: 1, unmeasured: 0, measured_at: ['run_finished', 'ticket_ended'] }] }] },
      { scope: { type: 'plain_repository', id: '/srv/plain/tools' }, bytes: 25, items: 1, unmeasured: 0, tickets: [
        { ticket: null, bytes: 25, items: 1, unmeasured: 0, kinds: [{ kind: 'worktree', bytes: 25, items: 1, unmeasured: 0, measured_at: ['run_finished'] }] }] },
      { scope: { type: 'no_project', id: null }, bytes: 5, items: 1, unmeasured: 1, tickets: [
        { ticket: null, bytes: 5, items: 1, unmeasured: 1, kinds: [{ kind: 'scratch', bytes: 5, items: 1, unmeasured: 1, measured_at: [] }] }] },
    ],
  }
  it('lays the tree out as rows, each scope, then its tickets, then their kinds, with the figures the API gave', () => {
    const rows = usageRows(usage)
    expect(rows.map((r) => [r.level, r.label, r.bytes, r.items])).toEqual([
      [0, 'orchard', 30, 2], [1, 'VELDO-9001', 30, 2], [2, 'build output', 10, 1], [2, 'worktree', 20, 1],
      [0, '/srv/plain/tools', 25, 1], [1, 'No ticket', 25, 1], [2, 'worktree', 25, 1],
      [0, 'No project', 5, 1], [1, 'No ticket', 5, 1], [2, 'scratch', 5, 1],
    ])
    expect(new Set(rows.map((r) => r.key)).size).toBe(rows.length)
  })
  it('names what each row is and the event a kind was measured at', () => {
    const rows = usageRows(usage)
    expect(rows[0]!.detail).toBe('Project')
    expect(rows[4]!.detail).toBe('Plain repository')
    expect(rows[7]!.detail).toBe('Sessions outside every project')
    expect(rows[3]!.detail).toBe('measured at run finished, ticket ended')
    expect(rows[9]!.detail).toBe('never measured')
  })
  it('says how many items were never measured, and is empty for no read', () => {
    expect(countText(usage.total)).toBe('4 items, 1 not measured')
    expect(countText({ bytes: 1, items: 1, unmeasured: 0 })).toBe('1 item')
    expect(usageRows(null)).toEqual([])
  })
})

describe('pending removal', () => {
  it('says why in a sentence and when the item is judged again', () => {
    expect(pendingReason(item())).toBe('Uncommitted changes in 3 files')
    expect(retryText(item())).toBe('Retried at ticket ended, project ended')
    expect(retryText(item({ retry: [] }))).toBe('No retry event is recorded')
    expect(pendingReason(item({ state: 'due', reason: null }))).toBe('Due since ticket ended; the removal has not run yet')
    expect(retryText(item({ state: 'due' }))).toBe('At the next event that reaches it')
    expect(pendingReason(item({ reason: null }))).toBe('No reason is recorded')
  })
  it('names the owner by scope, ticket and run', () => {
    expect(ownerText(item().owner)).toBe('orchard, VELDO-9001, run run-1 (review)')
    expect(ownerText({ scope: { type: 'no_project', id: null }, ticket: null, run: null, station: null, gate: null, lane: null, session: 's-1' })).toBe('No project, session s-1')
    expect(scopeLabel({ type: 'plain_repository', id: null })).toBe('Unnamed repository')
  })
  it('lists the worktrees of one request under it by index, and the rest apart', () => {
    const pending: PendingAnswer = {
      ...meta, view: 'pending',
      items: [
        item({ id: 'space:item:c', request: 'group-1', group: 'space:group:g', index: 3 }),
        item({ id: 'space:item:b', request: 'group-1', group: 'space:group:g', index: 1 }),
        item({ id: 'space:item:solo', request: 'solo-1' }),
        item({ id: 'space:item:busy', kind: 'build_output', rule: 'in_use', reason: 'in use by process 4412' }),
      ],
      requests: [
        { alias: 'group-1', group: 'space:group:g', day: '2026-11-16', sequence: 1, picks: [1], members: [{ item: 'space:item:b', index: 1 }, { item: 'space:item:c', index: 3 }] },
        { alias: 'solo-1', group: null, day: null, sequence: null, picks: [], members: [{ item: 'space:item:solo', index: null }] },
      ],
    }
    const decision = { requestId: 'assignment:x:group-1', alias: 'group-1', presentation: null } as unknown as PendingDecision
    const groups = pendingGroups(pending, [decision])
    expect(groups.requests.map((g) => [g.request.alias, g.items.map((i) => i.id), g.decision?.requestId ?? null])).toEqual([
      ['group-1', ['space:item:b', 'space:item:c'], 'assignment:x:group-1'],
      ['solo-1', ['space:item:solo'], null],
    ])
    expect(groups.rest.map((i) => i.id)).toEqual(['space:item:busy'])
    expect(memberPicks(pending.requests[0]!, 1)).toEqual(['accept save w1', 'accept keep w1', 'accept discard w1'])
    expect(memberPicks(pending.requests[0]!, 3)).toEqual([])
    expect(memberPicks(pending.requests[1]!, null)).toEqual([])
    expect(pendingGroups(null, [])).toEqual({ requests: [], rest: [] })
  })
})

describe('pools and runs', () => {
  it('says in one line what a waiting and an advised run were judged on', () => {
    expect(holdSentence(hold())).toBe('Waiting for space on main: need 4.0 GiB, free 10.0 GiB, held 3.0 GiB, floor 5.0 GiB')
    expect(holdSentence(hold({ state: 'advised' }))).toMatch(/^Would have waited for space on main: need 4\.0 GiB/)
  })
  it('gives the runs list each carried hold by its dispatch and the waiting holds that have no run yet', () => {
    const advised = hold({ id: 'space:hold:b', state: 'advised', run: { dispatch: 'dispatch/U-1/abc', unit: 'U-1', station: 'build' } })
    const pools: PoolsAnswer = {
      ...meta, view: 'pools',
      pools: [{ id: 'space:pool:h:main', version: 1, name: 'main', host: 'h', type: 'filesystem', engine: null, backing: null, floor: 5 * GIB, returns_space: true, held: 4 * GIB, waiting: [hold()], advised: [advised] }],
    }
    const found = runHolds(pools)
    expect([...found.byDispatch.keys()]).toEqual(['dispatch/U-1/abc'])
    expect(found.waiting.map((h) => h.id)).toEqual(['space:hold:dispatch/abc'])
    expect(runHolds(null)).toEqual({ byDispatch: new Map(), waiting: [] })
  })
})

describe('removed', () => {
  const removed = (over: Partial<RemovedItem> = {}): RemovedItem => ({
    id: 'space:item:r', version: 5, kind: 'build_output', owner: item().owner, locator: '/srv/build', pool: 'main', event: 'run_finished',
    emitter: null, method: 'rmtree', bytes: GIB, freed: GIB, free_before: 9 * GIB, free_after: 10 * GIB, host: null, kept_refs: 0, snapshots: 0, seq: 12, at: 1, ...over,
  })
  it('gives the free space before and after, and says when it was not recorded', () => {
    expect(removedSpace(removed())).toBe('9.0 GiB free before, 10.0 GiB after')
    expect(removedSpace(removed({ free_before: null }))).toBe('Free space was not recorded')
  })
  it('notes an engine pool whose host figure did not change', () => {
    expect(hostNote(removed())).toBeNull()
    expect(hostNote(removed({ host: { pool: 'main', free_before: GIB, free_after: GIB } }))).toBe('The host figure did not change (1.0 GiB free on main)')
    expect(hostNote(removed({ host: { pool: 'main', free_before: GIB, free_after: 2 * GIB } }))).toBe('On main: 1.0 GiB free before, 2.0 GiB after')
  })
})

describe('abandon and empty', () => {
  it('says what an accepted Abandon did and what stays for the owner', () => {
    expect(abandonText({ state: 'removed', removed: ['a', 'b'], deferred: [], discard_required: [] })).toBe('Abandoned: the worktree is removed now; 2 items removed.')
    expect(abandonText({ state: 'deferred', removed: [], deferred: [{ item: 'a' }], discard_required: ['a'] }))
      .toBe('Abandoned: the worktree is deferred now; 1 item deferred; 1 worktree stays until your Discard, which saves first.')
  })
  it('is empty only when no pool, item, pending row or removal is recorded', () => {
    const read = {
      pools: { ...meta, view: 'pools', pools: [] }, usage: { ...meta, view: 'usage', scopes: [], total: { bytes: 0, items: 0, unmeasured: 0 }, worktrees: [] },
      pending: { ...meta, view: 'pending', items: [], requests: [] }, removed: { ...meta, view: 'removed', items: [] },
    } as SpaceRead
    expect(isEmpty(read)).toBe(true)
    expect(isEmpty({ ...read, removed: { ...read.removed, items: [{} as RemovedItem] } })).toBe(false)
  })
})
