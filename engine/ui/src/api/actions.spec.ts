import { afterEach, describe, expect, it, vi } from 'vitest'
import { ACTION_ROUTES, published, reprioritize, setCap, stopWorker } from './actions'

afterEach(() => vi.unstubAllGlobals())

describe('owner work actions', () => {
  it('names a published route for each of the three commands', () => {
    expect(published(ACTION_ROUTES.worker_stop)).toBe(true)
    expect(published(ACTION_ROUTES.owner_priority)).toBe(true)
    expect(published(ACTION_ROUTES.worker_cap)).toBe(true)
  })

  it('sends nothing and names the route when the route is not published', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    expect(await stopWorker('dispatch/u/1', 3, 'workers.unpublished')).toEqual({ sent: false, route: 'workers.unpublished' })
    expect(await reprioritize('backlog:x', 2, 1, 'backlog.unpublished')).toEqual({ sent: false, route: 'backlog.unpublished' })
    expect(await setCap('plan', 2, 3, 'cap.unpublished')).toEqual({ sent: false, route: 'cap.unpublished' })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('posts to a published route the contract names, with the exact body', async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify({ outcome: 'ok' }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    // messages.send is published; its fields differ, so the client refuses the body before anything is sent.
    await expect(stopWorker('d', 1, 'messages.send')).rejects.toThrow(/takes no field/)
    await expect(setCap('plan', 1, 2, 'messages.send')).rejects.toThrow(/takes no field/)
    expect(fetch).not.toHaveBeenCalled()
  })
})
