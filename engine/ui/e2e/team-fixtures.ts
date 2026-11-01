import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test as base } from '@playwright/test'
import type { Factory } from './fixtures'

export { expect, guard, routeOf, signIn, type Factory } from './fixtures'

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
  const args = ['-B', path.join(here, 'team_harness.py'), '--dist', dist]
  if (process.env.VELDO_ORGANS) args.push('--organs', process.env.VELDO_ORGANS)
  const child = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'] })
  let errors = ''
  child.stderr.on('data', (chunk) => (errors += String(chunk)))
  const ready = await new Promise<{ origin: string; control: string; domain: string }>((resolve, reject) => {
    let out = ''
    const timer = setTimeout(() => reject(new Error(`team harness did not start: ${errors}`)), 90_000)
    child.stdout.on('data', (chunk) => {
      out += String(chunk)
      const line = out.split('\n')[0]
      if (out.includes('\n') && line) {
        clearTimeout(timer)
        resolve(JSON.parse(line))
      }
    })
    child.on('exit', (code) => reject(new Error(`team harness exited ${code}: ${errors}`)))
  })
  const control = async <T,>(route: string, body: Record<string, unknown> = {}) => {
    const response = await fetch(ready.control + route, { method: 'POST', body: JSON.stringify(body) })
    const value = (await response.json()) as T & { error?: string }
    if (!response.ok) throw new Error(`control ${route}: ${value.error}`)
    return value as T
  }
  const factory: TeamFactory = {
    origin: ready.origin,
    domain: ready.domain,
    control,
    state: () => control('/state'),
    team: async (project) => (await control<{ team: Record<string, unknown> | null }>('/team/read', { project })).team,
    defaultRevision: async (revision) =>
      (await control<{ default: Record<string, unknown> | null }>('/team/default', { revision })).default,
    configuration: async (role, revision) =>
      (await control<{ configuration: Record<string, unknown> | null }>('/configuration/read', { role, revision })).configuration,
  }
  return { factory, child }
}

export const test = base.extend<object, { factory: TeamFactory }>({
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
