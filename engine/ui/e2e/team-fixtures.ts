import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { startHarness, withHarness, type Factory } from './fixtures'

export { expect, guard, routeOf, settled, signIn, unique, type Factory } from './fixtures'

/** VELDO-0163's browser tests run against e2e/team_harness.py: the VELDO-0145 factory harness with the real
 * configuration, catalog and team services of VELDO-0162 handed to the real API authority. */
const here = path.dirname(fileURLToPath(import.meta.url))
const UI = path.resolve(here, '..')

export interface TeamFactory extends Factory {
  team(project: string): Promise<Record<string, unknown> | null>
  defaultRevision(revision: number): Promise<Record<string, unknown> | null>
  configuration(role: string, revision: number): Promise<Record<string, unknown> | null>
}

async function start() {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  if (!existsSync(path.join(dist, 'index.html'))) throw new Error(`build the UI first: no ${dist}/index.html`)
  const harness = await startHarness('team_harness.py', ['--dist', dist], 'team harness')
  const control = harness.factory.control
  const factory: TeamFactory = {
    ...harness.factory,
    team: async (project) => (await control<{ team: Record<string, unknown> | null }>('/team/read', { project })).team,
    defaultRevision: async (revision) =>
      (await control<{ default: Record<string, unknown> | null }>('/team/default', { revision })).default,
    configuration: async (role, revision) =>
      (await control<{ configuration: Record<string, unknown> | null }>('/configuration/read', { role, revision })).configuration,
  }
  return { ...harness, factory }
}

export const test = withHarness(start)
