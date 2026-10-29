import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { fieldProblem, routePath } from './routes'

describe('routes', () => {
  it('fills the domain into a domain route', () => {
    expect(routePath('reads.decisions', 'veldo')).toBe('/api/v1/domains/veldo/decisions')
    expect(routePath('auth.session', null)).toBe('/api/v1/auth/session')
  })

  it('refuses a field the route does not take and names a missing one', () => {
    expect(fieldProblem('runs.record', { dispatch: 'd', after: 0 })).toBeNull()
    expect(fieldProblem('runs.record', { dispatch: 'd', principal: 'x' })).toMatch(/takes no field principal/)
    expect(fieldProblem('decisions.answer', { choice: 'accept' })).toMatch(/needs request_id/)
  })

  it('is the only way the UI reaches the network: no fetch or EventSource outside src/api', () => {
    const root = path.resolve(__dirname, '..')
    const offenders: string[] = []
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const full = path.join(dir, name)
        if (statSync(full).isDirectory()) walk(full)
        else if (/\.(ts|vue)$/.test(name) && !name.endsWith('.spec.ts') && !full.includes(`${path.sep}api${path.sep}`)) {
          const text = readFileSync(full, 'utf8')
          if (/\bfetch\(|new EventSource\(|XMLHttpRequest|navigator\.sendBeacon/.test(text)) offenders.push(path.relative(root, full))
        }
      }
    }
    walk(root)
    expect(offenders).toEqual([])
  })
})
