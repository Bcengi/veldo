import table from './routes.json'

export type Method = 'GET' | 'POST'

export interface RouteSpec {
  method: Method
  path: string
  required: readonly string[]
  optional: readonly string[]
}

export type RouteName = keyof typeof table.routes

/** Every API route the UI calls, by its published name (control_api.ROUTES). */
export const ROUTES = table.routes as Record<RouteName, RouteSpec>

/** The route's path with its domain filled in. */
export function routePath(name: RouteName, domain: string | null): string {
  const spec = ROUTES[name]
  if (!spec.path.includes('{domain}')) return spec.path
  if (!domain) throw new Error(`route ${name} needs a domain`)
  return spec.path.replace('{domain}', encodeURIComponent(domain))
}

/** The exact fields a request to the route may carry; anything else is a defect here, not a refusal there. */
export function fieldProblem(name: RouteName, fields: Record<string, unknown>): string | null {
  const spec = ROUTES[name]
  const keys = Object.keys(fields)
  const allowed = new Set([...spec.required, ...spec.optional])
  const extra = keys.filter((k) => !allowed.has(k))
  const missing = spec.required.filter((k) => !keys.includes(k))
  if (extra.length) return `${name} takes no field ${extra.join(', ')}`
  if (missing.length) return `${name} needs ${missing.join(', ')}`
  return null
}
