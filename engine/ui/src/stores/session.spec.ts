import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '@/api/auth'
import { apiContext } from '@/api/context'
import * as reads from '@/api/reads'
import { read } from '@/test/builders'
import { useDecisionsStore } from './decisions'
import { wireSessionEnd } from './index'
import { useSessionStore } from './session'

const view = { principal: 'owner', credential_id: 'c', domain: 'd', csrf_token: 'tok', idle_expires_at: 1, expires_at: 2 }

describe('session store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('keeps the anti-forgery token in memory only, never in storage', async () => {
    vi.spyOn(auth, 'readSession').mockResolvedValue(view)
    const session = useSessionStore()
    await session.restore()
    expect(session.status).toBe('signed-in')
    expect(apiContext.token).toBe('tok')
    expect(JSON.stringify(session.view)).not.toContain('tok')
    expect(JSON.stringify({ ...localStorage })).not.toContain('tok')
    expect(JSON.stringify({ ...sessionStorage })).not.toContain('tok')
  })

  it('drops every store when the session ends', async () => {
    vi.spyOn(auth, 'readSession').mockResolvedValue(view)
    vi.spyOn(reads, 'readDecisions').mockResolvedValue(read({ assignment: [], channel_presentation: [] }))
    const session = useSessionStore()
    await session.restore()
    wireSessionEnd()
    const decisions = useDecisionsStore()
    await decisions.refresh()
    expect(decisions.state).toBe('empty')
    apiContext.onUnauthenticated!({ refusal: 'unauthenticated:session_expired', error: 'unauthenticated' } as never)
    expect(session.status).toBe('signed-out')
    expect(apiContext.token).toBeNull()
    expect(decisions.state).toBe('idle')
    expect(session.endedBy?.refusal).toBe('unauthenticated:session_expired')
  })
})
