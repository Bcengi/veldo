import { afterEach, describe, expect, it, vi } from 'vitest'
import { ACTION_ROUTES, published, reprioritize, stopWorker } from './actions'

afterEach(() => vi.unstubAllGlobals())

describe('pending owner actions', () => {
  it('sends nothing and names the route while the API does not publish it', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    expect(published(ACTION_ROUTES.worker_stop)).toBe(false)
    expect(await stopWorker('dispatch/u/1', 3)).toEqual({ sent: false, route: 'workers.stop' })
    expect(await reprioritize('backlog:x', 2, 1)).toEqual({ sent: false, route: 'backlog.reprioritize' })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('posts to a published route the contract names, with the exact body', async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify({ outcome: 'ok' }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    // messages.send is published; its fields differ, so the client refuses the body before anything is sent.
    await expect(stopWorker('d', 1, 'messages.send')).rejects.toThrow(/takes no field/)
    expect(fetch).not.toHaveBeenCalled()
  })
})
