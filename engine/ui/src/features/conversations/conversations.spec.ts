import { describe, expect, it } from 'vitest'
import type { ConversationSummary } from '@/api/conversations'
import type { ReadAnswer } from '@/api/types'
import { currentTurn, openingWords, orderConversations, scopeProjects, teamRoles, turnMarker } from './conversations'
import { joinTraces, logged, telemetry, traceSent } from './telemetry'
import { ApiRefusal } from '@/api/refusal'

const summary = (id: string, status: string, last: number | null): ConversationSummary => ({ id, status, role: 'assistant', version: 1, turns: 1, last_activity: last })

describe('the conversation list', () => {
  it('shows open conversations first, then closed, each newest activity first', () => {
    const ordered = orderConversations([summary('a', 'closed', 50), summary('b', 'open', 10), summary('c', 'open', 30), summary('d', 'closed', 90)])
    expect(ordered.map((c) => c.id)).toEqual(['c', 'b', 'd', 'a'])
  })

  it('shows the opening words of the first message as written', () => {
    expect(openingWords('  why did the <b>deploy</b> fail ')).toBe('why did the <b>deploy</b> fail')
    expect(openingWords('one two three four five six seven eight nine ten eleven twelve thirteen')).toBe(
      'one two three four five six seven eight nine ten eleven twelve ...',
    )
    expect(openingWords(null)).toBeNull()
    expect(openingWords('   ')).toBeNull()
  })
})

describe('the turns', () => {
  it('marks a waiting turn, a running turn and an ended one, and finds the current one', () => {
    expect(turnMarker({ state: 'waiting' })).toBe('waiting')
    expect(turnMarker({ state: 'dispatched' })).toBe('running')
    expect(turnMarker({ state: 'ended' })).toBe('ended')
    const turn = (sequence: number, state: string) => ({ sequence, state, message: null, reply: null, outcome: null, dispatch_id: null, account: null, created_at: null, ended_at: null })
    expect(currentTurn([turn(1, 'ended'), turn(2, 'dispatched')])?.sequence).toBe(2)
    expect(currentTurn([turn(1, 'ended')])).toBeNull()
  })
})

describe('the controls', () => {
  it('lists the default team\'s roles with the current one present', () => {
    const team = { revision: 2, digest: 'd', team: { roles: { assistant_codex: {}, assistant: {} } } } as never
    expect(teamRoles(team, 'assistant')).toEqual(['assistant', 'assistant_codex'])
    expect(teamRoles(null, 'gone')).toEqual(['gone'])
  })

  it('lists the projects of the member\'s scope from the objectives read', () => {
    const answer = { items: { project: [{ id: 'project:veldo', data: { name: 'veldo' } }, { id: 'project:x', data: {} }] } } as unknown as ReadAnswer
    expect(scopeProjects(answer)).toEqual(['veldo', 'x'])
    expect(scopeProjects(null)).toEqual([])
  })
})

describe('the client log and traces', () => {
  it('logs route, outcome and latency, the refusal by its name, and never the text', async () => {
    const before = telemetry.log.length
    await logged('messages.send', async () => ({ outcome: 'turn' }))
    await expect(logged('conversations.set_role', async () => {
      throw new ApiRefusal(409, 'stale_version', 'stale_version')
    })).rejects.toBeInstanceOf(ApiRefusal)
    const entries = telemetry.log.slice(before)
    expect(entries.map((e) => [e.route, e.outcome])).toEqual([['messages.send', 'ok'], ['conversations.set_role', 'stale_version']])
    expect(Object.keys(entries[0]!).sort()).toEqual(['at', 'ms', 'outcome', 'route'])
  })

  it('joins each message sent to the turn it became and the dispatch it ran as', () => {
    traceSent('c-1', 'api-1', 2)
    traceSent('c-1', 'api-2', 2)
    joinTraces('c-1', [{ sequence: 3, dispatch_id: 'dispatch/c-1/3' }])
    joinTraces('c-1', [{ sequence: 3, dispatch_id: 'dispatch/c-1/3' }, { sequence: 4, dispatch_id: null }])
    const mine = telemetry.traces.filter((t) => t.conversation === 'c-1')
    expect(mine.map((t) => [t.api_request_id, t.sequence, t.dispatch])).toEqual([
      ['api-1', 3, 'dispatch/c-1/3'],
      ['api-2', 4, null],
    ])
  })
})
