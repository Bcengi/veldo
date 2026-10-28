import { afterEach, describe, expect, it, vi } from 'vitest'
import { request } from './client'
import { apiContext } from './context'
import { ApiRefusal, describeRefusal } from './refusal'

function answer(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))
}

afterEach(() => {
  apiContext.token = null
  apiContext.domain = null
  apiContext.onUnauthenticated = null
})

describe('request', () => {
  it('sends a write with the in-memory token, same-origin credentials and exactly its fields', async () => {
    const fetcher = answer(200, { outcome: 'settled' })
    vi.stubGlobal('fetch', fetcher)
    apiContext.token = 'tok'
    apiContext.domain = 'd'
    const body = { request_id: 'r', request_version: 1, presentation_id: 'p', presentation_digest: 'g', presentation_version: 2, choice: 'accept', rationale: 'why' }
    await request('decisions.answer', { body })
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/v1/domains/d/decisions/answer')
    expect(init.credentials).toBe('same-origin')
    expect((init.headers as Record<string, string>)['X-Veldo-Token']).toBe('tok')
    expect(JSON.parse(init.body as string)).toEqual(body)
  })

  it('refuses to send a field the route does not take', async () => {
    vi.stubGlobal('fetch', answer(200, {}))
    await expect(request('auth.registration_begin', { body: { label: 'x', principal: 'me' } })).rejects.toThrow(/takes no field principal/)
  })

  it('turns a refusal into a named ApiRefusal and reports a session that ended', async () => {
    vi.stubGlobal('fetch', answer(401, { refusal: 'unauthenticated:session_expired', error: 'unauthenticated' }))
    apiContext.domain = 'd'
    const ended = vi.fn()
    apiContext.onUnauthenticated = ended
    const error = await request('reads.decisions').catch((e) => e)
    expect(error).toBeInstanceOf(ApiRefusal)
    expect(error.refusal).toBe('unauthenticated:session_expired')
    expect(ended).toHaveBeenCalledOnce()
  })

  it('does not treat a refused sign-in ceremony as a session ending', async () => {
    vi.stubGlobal('fetch', answer(401, { refusal: 'unauthenticated:unknown_credential', error: 'unauthenticated' }))
    const ended = vi.fn()
    apiContext.onUnauthenticated = ended
    await expect(request('auth.sign_in', { body: { credential_id: 'c', client_data_json: 'j', authenticator_data: 'a', signature: 's', user_handle: 'u' } })).rejects.toBeInstanceOf(ApiRefusal)
    expect(ended).not.toHaveBeenCalled()
  })

  it('names an unreachable API as unavailable, never as an answer', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('network'))))
    const error = await request('auth.session').catch((e) => e)
    expect(error.error).toBe('unavailable')
  })
})

describe('describeRefusal', () => {
  it('names the specific reason when it knows it, else the class', () => {
    expect(describeRefusal({ refusal: 'stale_version:stale_presentation', error: 'stale_version' }).title).toBe('The question changed after you opened it')
    expect(describeRefusal({ refusal: 'stale_version:something_new', error: 'stale_version' }).title).toBe('This changed since you opened it')
  })
})
