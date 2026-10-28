import { describe, expect, it } from 'vitest'
import { item, read, receipt } from '@/test/builders'
import { answerBody, choiceLabel, pendingDecisions } from './inbox'

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
