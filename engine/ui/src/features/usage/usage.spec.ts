import { describe, expect, it } from 'vitest'
import type { ReadAnswer } from '@/api/types'
import { accountsOf, amount, breakdown, invocationsOf, noAccountUntil, seriesOf, timesOf } from './usage'

const r = (id: string, data: Record<string, unknown>) => ({ id, kind: 'subscription_reservation', version: 1, digest: 'd', data })
const ctx = { account: 'acc', project: 'p', unit: 'u' }
const spend = {
  items: {
    subscription_reservation: [
      r('pol', { type: 'policy', scope: 'account', subject: 'acc', windows: { w: { window_id: 'w', unit: 'messages', remaining: 0, reset_at: 500 }, v: { window_id: 'v', unit: 'messages', remaining: 4, reset_at: 900 } } }),
      r('wk', { type: 'worker', dispatch: 'd1', context: ctx, retired: false }),
      r('i1', { type: 'invocation', dispatch: 'd1', context: ctx, charge: { invocations: 1, tokens: 100 }, unknown: [], accepted_seq: 1 }),
      r('i2', { type: 'invocation', dispatch: 'd1', context: ctx, charge: { invocations: 1 }, unknown: ['tokens'], accepted_seq: 2 }),
      r('i3', { type: 'invocation', dispatch: 'd2', context: ctx, charge: { invocations: 1, tokens: 50 }, unknown: [], accepted_seq: 9 }),
    ],
  },
} as unknown as ReadAnswer

describe('usage', () => {
  it('keeps unknown usage apart from zero', () => {
    const [account] = accountsOf(spend, 100)
    expect(account!.totals.tokens).toBe(150)
    expect(account!.unknown.tokens).toBe(1)
    expect(amount(0, 2, 'tokens')).toBe('unknown (2 invocations)')
    expect(amount(150, 1, 'tokens')).toBe('150 tokens + 1 unknown')
  })
  it('names when a blocked account is free and the earliest free time of all', () => {
    const accounts = accountsOf(spend, 100)
    expect(accounts[0]!.blockedUntil).toBe(500)
    expect(accounts[0]!.activeRuns).toEqual(['d1'])
    expect(noAccountUntil(accounts)).toBe(500)
    expect(noAccountUntil(accountsOf(spend, 600))).toBeNull()
  })
  it('buckets by the journal commit time and counts untimed invocations', () => {
    const times = timesOf([{ seq: 1, committed_at: 3600 * 2 + 5 }, { seq: 2, committed_at: 3600 * 2 + 9 }] as never)
    const { buckets, untimed } = seriesOf(invocationsOf(spend), times, 'tokens')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]).toMatchObject({ start: 7200, known: 100, unknown: 1 })
    expect(untimed).toBe(1)
  })
  it('breaks usage down by run', () => {
    expect(breakdown(invocationsOf(spend), 'tokens', 'dispatch')).toEqual([
      { key: 'd1', known: 100, unknown: 1, count: 2 },
      { key: 'd2', known: 50, unknown: 0, count: 1 },
    ])
  })
})

describe('providers from the account records (fix round 2)', () => {
  it('names each invocation and account by its account record, and breaks usage down by provider', async () => {
    const { accountRecords } = await import('./usage')
    const item = (id: string, kind: string, data: Record<string, unknown>) => ({ id, kind, version: 1, digest: 'd', data })
    const spend = { items: {
      account: [item('account:a', 'account', { id: 'a', provider: 'codex', label: 'A', status: 'active' })],
      subscription_reservation: [
        item('r1', 'subscription_reservation', { type: 'invocation', context: { account: 'a' }, charge: { tokens: 5 }, unknown: [] }),
        item('r2', 'subscription_reservation', { type: 'invocation', context: { account: 'b' }, charge: {}, unknown: ['tokens'] }),
      ],
    } } as never
    expect(accountRecords(spend).get('a')).toEqual({ provider: 'codex', label: 'A', status: 'active' })
    expect(accountsOf(spend, 0).map((a) => [a.account, a.provider])).toEqual([['a', 'codex'], ['b', '']])
    expect(breakdown(invocationsOf(spend), 'tokens', 'provider').map((r) => [r.key, r.known, r.unknown])).toEqual([
      ['codex', 5, 0], ['not recorded', 0, 1],
    ])
  })
})
