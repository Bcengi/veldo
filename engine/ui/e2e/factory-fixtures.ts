import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test as base } from '@playwright/test'
import type { Factory } from './fixtures'

export { expect, guard, routeOf, signIn, type Factory } from './fixtures'

/** VELDO-0131's browser tests run against e2e/factory_harness.py: VELDO-0163's team harness (itself VELDO-0145's
 * real factory) with the journal feed, the workflow service and every read model the screens show. */
const here = path.dirname(fileURLToPath(import.meta.url))
const UI = path.resolve(here, '..')

export interface FactoryUi extends Factory {
  entity(id: string): Promise<{ kind: string; version: number; data: Record<string, any> } | null>
  kind(kind: string): Promise<{ id: string; version: number; data: Record<string, any> }[]>
  upsert(id: string, kind: string, data: Record<string, unknown>): Promise<void>
  land(unit: string): Promise<string>
  deliver(): Promise<void>
  workflow(): Promise<Record<string, any>>
}

async function start() {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  if (!existsSync(path.join(dist, 'index.html'))) throw new Error(`build the UI first: no ${dist}/index.html`)
  const args = ['-B', path.join(here, 'factory_harness.py'), '--dist', dist]
  if (process.env.VELDO_ORGANS) args.push('--organs', process.env.VELDO_ORGANS)
  const child = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'] })
  let errors = ''
  child.stderr.on('data', (chunk) => (errors += String(chunk)))
  const ready = await new Promise<{ origin: string; control: string; domain: string }>((resolve, reject) => {
    let out = ''
    const timer = setTimeout(() => reject(new Error(`factory harness did not start: ${errors}`)), 90_000)
    child.stdout.on('data', (chunk) => {
      out += String(chunk)
      const line = out.split('\n')[0]
      if (out.includes('\n') && line) {
        clearTimeout(timer)
        resolve(JSON.parse(line))
      }
    })
    child.on('exit', (code) => reject(new Error(`factory harness exited ${code}: ${errors}`)))
  })
  const control = async <T,>(route: string, body: Record<string, unknown> = {}) => {
    const response = await fetch(ready.control + route, { method: 'POST', body: JSON.stringify(body) })
    const value = (await response.json()) as T & { error?: string }
    if (!response.ok) throw new Error(`control ${route}: ${value.error}`)
    return value as T
  }
  const factory: FactoryUi = {
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
  }
  return { factory, child }
}

export const test = base.extend<object, { factory: FactoryUi }>({
  factory: [
    async ({}, use) => {
      const { factory, child } = await start()
      await use(factory)
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
    },
    { scope: 'worker' },
  ],
})
