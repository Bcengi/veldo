import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { startHarness, withHarness, type Factory } from './fixtures'

export { expect, guard, routeOf, settled, signIn, unique, type Factory } from './fixtures'

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
  const harness = await startHarness('factory_harness.py', ['--dist', dist], 'factory harness')
  const control = harness.factory.control
  const factory: FactoryUi = {
    ...harness.factory,
    entity: async (id) => (await control<{ entity: Awaited<ReturnType<FactoryUi['entity']>> }>('/factory/entity', { id })).entity,
    kind: async (kind) => (await control<{ entities: Awaited<ReturnType<FactoryUi['kind']>> }>('/factory/kind', { kind })).entities,
    upsert: async (id, kind, data) => void (await control('/factory/upsert', { id, kind, data })),
    land: async (unit) => (await control<{ receipt: string }>('/factory/land', { unit })).receipt,
    deliver: async () => void (await control('/factory/deliver')),
    workflow: async () => (await control<{ workflow: Record<string, any> }>('/factory/workflow')).workflow,
  }
  return { ...harness, factory }
}

export const test = withHarness(start)
