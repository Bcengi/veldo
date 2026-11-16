import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test as base } from '@playwright/test'
import type { FactoryUi } from './factory-fixtures'

export { expect, guard, routeOf, signIn } from './fixtures'
export type { FactoryUi } from './factory-fixtures'

/** VELDO-0319's browser tests run against e2e/space_harness.py: VELDO-0131's factory harness with the space
 * ledger's records and the stand-ins of the service's reconcile and abandon entries. `factory` is seeded; `bare`
 * is the same harness with no space record at all (VELDO_SPACE_SEED=0), for the screen's empty state, and is
 * started only by a test that asks for it. */
const here = path.dirname(fileURLToPath(import.meta.url))
const UI = path.resolve(here, '..')

/** The names e2e/space_harness.py gives what it seeds. */
export type SpaceIds = Record<
  | 'pool_main' | 'pool_engine' | 'hold_waiting' | 'hold_advised' | 'hold_admitted' | 'hold_released'
  | 'tree' | 'build' | 'agent' | 'unmeasured' | 'kept' | 'due' | 'busy' | 'solo' | 'review1' | 'review2' | 'review3'
  | 'gone-build' | 'gone-tree' | 'gone-volume' | 'vanished' | 'b-tree' | 'plain' | 'scratch'
  | 'group' | 'request' | 'group_alias' | 'solo_alias',
  string
>

export interface SpaceFactory extends FactoryUi {
  /** The identities the harness seeded, by the names of e2e/space_harness.py. */
  ids(): Promise<SpaceIds>
}

async function start(seed: boolean) {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  if (!existsSync(path.join(dist, 'index.html'))) throw new Error(`build the UI first: no ${dist}/index.html`)
  const args = ['-B', path.join(here, 'space_harness.py'), '--dist', dist]
  if (process.env.VELDO_ORGANS) args.push('--organs', process.env.VELDO_ORGANS)
  const child = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, VELDO_SPACE_SEED: seed ? '1' : '0' } })
  let errors = ''
  child.stderr.on('data', (chunk) => (errors += String(chunk)))
  const ready = await new Promise<{ origin: string; control: string; domain: string }>((resolve, reject) => {
    let out = ''
    const timer = setTimeout(() => reject(new Error(`space harness did not start: ${errors}`)), 90_000)
    child.stdout.on('data', (chunk) => {
      out += String(chunk)
      const line = out.split('\n')[0]
      if (out.includes('\n') && line) {
        clearTimeout(timer)
        resolve(JSON.parse(line))
      }
    })
    child.on('exit', (code) => reject(new Error(`space harness exited ${code}: ${errors}`)))
  })
  const control = async <T,>(route: string, body: Record<string, unknown> = {}) => {
    const response = await fetch(ready.control + route, { method: 'POST', body: JSON.stringify(body) })
    const value = (await response.json()) as T & { error?: string }
    if (!response.ok) throw new Error(`control ${route}: ${value.error}`)
    return value as T
  }
  const factory: SpaceFactory = {
    origin: ready.origin,
    domain: ready.domain,
    control,
    state: () => control('/state'),
    entity: async (id) => (await control<{ entity: Awaited<ReturnType<FactoryUi['entity']>> }>('/factory/entity', { id })).entity,
    kind: async (kind) => (await control<{ entities: Awaited<ReturnType<FactoryUi['kind']>> }>('/factory/kind', { kind })).entities,
    upsert: async (id, kind, data) => void (await control('/factory/upsert', { id, kind, data })),
    land: async (unit) => (await control<{ receipt: string }>('/factory/land', { unit })).receipt,
    deliver: async () => void (await control('/factory/deliver')),
    workflow: async () => (await control<{ workflow: Record<string, any> }>('/factory/workflow')).workflow,
    ids: async () => (await control<{ ids: SpaceIds }>('/space/ids')).ids,
  }
  const stop = async () => {
    child.stdin.end()
    await new Promise((resolve) => {
      const timer = setTimeout(() => {
        child.kill('SIGTERM')
        resolve(null)
      }, 10_000)
      child.on('exit', () => {
        clearTimeout(timer)
        resolve(null)
      })
    })
  }
  return { factory, stop }
}

export const test = base.extend<object, { factory: SpaceFactory; bare: SpaceFactory }>({
  factory: [
    async ({}, use) => {
      const { factory, stop } = await start(true)
      await use(factory)
      await stop()
    },
    { scope: 'worker' },
  ],
  bare: [
    async ({}, use) => {
      const { factory, stop } = await start(false)
      await use(factory)
      await stop()
    },
    { scope: 'worker' },
  ],
})
