import { describe, expect, it } from 'vitest'
import { item, read, receipt } from '@/test/builders'
import { answerBody, choiceLabel, dueText, oldestDecision, pendingDecisions, rankDecisions, riskOf, urgencyOf } from './inbox'

const assignment = (alias: string, over: Record<string, unknown> = {}) =>
  item(`assignment:r:${alias}`, 'assignment', { alias, kind: 'decision', state: 'OFFERED', request_version: 1, owner: 'owner', scope: ['p'], brief: `Decide ${alias}.`, ...over })

describe('pendingDecisions', () => {
  it('lists pending decisions with their current published presentation', () => {
    const answer = read({
      assignment: [assignment('de1')],
      channel_presentation: [
        item('p1', 'channel_presentation', receipt('assignment:r:de1')),
        item('p2', 'channel_presentation', receipt('assignment:r:de1', { presentation_version: 2, presentation_id: 'p2' })),
        item('p3', 'channel_presentation', receipt('assignment:r:de1', { presentation_version: 3, outcome: 'refused' })),
      ],
    })
    const [first] = pendingDecisions(answer)
    expect(first!.presentation!.version).toBe(2)
    expect(first!.presentation!.id).toBe('p2')
  })

  it('ignores a presentation of an older request version', () => {
    const answer = read({
      assignment: [assignment('de1', { request_version: 2 })],
      channel_presentation: [item('p1', 'channel_presentation', receipt('assignment:r:de1'))],
    })
    expect(pendingDecisions(answer)[0]!.presentation).toBeNull()
  })

  it('leaves out settled requests and assignments that are not decisions', () => {
    const answer = read({ assignment: [assignment('a', { state: 'SATISFIED' }), assignment('b', { kind: 'review' })] })
    expect(pendingDecisions(answer)).toEqual([])
  })
})

describe('answerBody', () => {
  it('binds the answer to the presentation shown: its id, digest and version and the request version', () => {
    const answer = read({ assignment: [assignment('de1')], channel_presentation: [item('p1', 'channel_presentation', receipt('assignment:r:de1'))] })
    const shown = pendingDecisions(answer)[0]!.presentation!
    expect(answerBody(shown, 'accept', 'because')).toEqual({
      request_id: 'assignment:r:de1',
      request_version: 1,
      presentation_id: 'presentation:telegram_chat:assignment:r:de1:1:ab',
      presentation_digest: 'sha256:brief',
      presentation_version: 1,
      choice: 'accept',
      rationale: 'because',
    })
  })
})

describe('choiceLabel', () => {
  it('reads a choice for people without changing the value sent', () => {
    expect(choiceLabel('return_for_elaboration')).toBe('Return for elaboration')
  })
})

describe('the ranked inbox', () => {
  const now = Date.parse('2026-10-28T12:00:00Z')
  const at = (hours: number) => new Date(now + hours * 3600_000).toISOString()
  const inbox = (rows: { alias: string; hours: number | null; risk: string; published?: number }[]) =>
    pendingDecisions(
      read({
        assignment: rows.map((r) => assignment(r.alias, { deadline: r.hours === null ? '' : at(r.hours) })),
        channel_presentation: rows.map((r) =>
          item(`p-${r.alias}`, 'channel_presentation', receipt(`assignment:r:${r.alias}`, { risk_statement: r.risk, published_at: r.published ?? 0 })),
        ),
      }),
    )

  it('ranks by deadline urgency first, then risk, then the earlier deadline', () => {
    const ranked = rankDecisions(
      inbox([
        { alias: 'later-high', hours: 24 * 6, risk: 'High: a wrong admit costs a release.' },
        { alias: 'soon-low', hours: 50, risk: 'Low: one review cycle.' },
        { alias: 'soon-high', hours: 60, risk: 'High: blocks the line.' },
        { alias: 'today-low', hours: 5, risk: 'Low: cheap to undo.' },
        { alias: 'overdue', hours: -2, risk: 'Medium: late already.' },
        { alias: 'none', hours: null, risk: 'High: no deadline.' },
      ]),
      now,
    )
    expect(ranked.map((d) => d.alias)).toEqual(['overdue', 'today-low', 'soon-high', 'soon-low', 'later-high', 'none'])
  })

  it('says how soon a decision is due in plain words', () => {
    expect(dueText(at(24 * 3), now)).toBe('due in 3 d')
    expect(dueText(at(5), now)).toBe('due in 5 h')
    expect(dueText(at(0.25), now)).toBe('due in 15 min')
    expect(dueText(at(-2), now)).toBe('overdue by 2 h')
    expect(dueText(null, now)).toBeNull()
    expect([urgencyOf(at(-1), now), urgencyOf(at(5), now), urgencyOf(at(48), now), urgencyOf(at(100), now), urgencyOf(null, now)]).toEqual([
      'overdue', 'today', 'soon', 'later', 'none',
    ])
  })

  it('reads the risk level a risk statement opens with', () => {
    expect([riskOf('High: x'), riskOf('medium risk'), riskOf('Low.'), riskOf('Unclear'), riskOf(null)]).toEqual(['high', 'medium', 'low', 'unknown', 'unknown'])
  })

  it('names the decision that has waited longest', () => {
    const list = inbox([
      { alias: 'new', hours: 5, risk: 'Low', published: 1790000300 },
      { alias: 'old', hours: 90, risk: 'Low', published: 1790000100 },
    ])
    expect(oldestDecision(list)!.alias).toBe('old')
  })
})
