import { apiContext } from './context'
import { ApiRefusal } from './refusal'
import { ROUTES, fieldProblem, routePath, type RouteName } from './routes'

/** Routes whose 401 is the ceremony's own answer, not a session that ended. */
const CEREMONY: ReadonlySet<RouteName> = new Set([
  'auth.challenge',
  'auth.sign_in',
  'auth.registration_begin',
  'auth.registration_credential',
  'auth.registration_possession',
  'auth.session',
])

export interface RequestOptions {
  fields?: Record<string, string | number>
  body?: Record<string, unknown>
  signal?: AbortSignal
}

/** The URL of a GET route with its exact query fields. */
export function routeUrl(name: RouteName, fields: Record<string, string | number> = {}): string {
  const problem = fieldProblem(name, fields)
  if (problem) throw new Error(problem)
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(fields)) query.set(k, String(v))
  const text = query.toString()
  return routePath(name, apiContext.domain) + (text ? `?${text}` : '')
}

/** One request to one published route. The only caller of fetch in the UI. */
export async function request<T>(name: RouteName, options: RequestOptions = {}): Promise<T> {
  const spec = ROUTES[name]
  const headers: Record<string, string> = { Accept: 'application/json' }
  let url: string
  let payload: string | undefined
  if (spec.method === 'GET') {
    url = routeUrl(name, options.fields)
  } else {
    const body = options.body ?? {}
    const problem = fieldProblem(name, body)
    if (problem) throw new Error(problem)
    url = routePath(name, apiContext.domain)
    payload = JSON.stringify(body)
    headers['Content-Type'] = 'application/json'
    if (apiContext.token) headers['X-Veldo-Token'] = apiContext.token
  }
  let response: Response
  try {
    response = await fetch(url, {
      method: spec.method,
      headers,
      body: payload,
      credentials: 'same-origin',
      cache: 'no-store',
      signal: options.signal,
    })
  } catch (error) {
    if ((error as Error)?.name === 'AbortError') throw error
    throw new ApiRefusal(0, 'unavailable:network', 'unavailable')
  }
  let value: unknown = null
  try {
    value = await response.json()
  } catch {
    value = null
  }
  if (response.ok) return value as T
  const named = (value ?? {}) as { refusal?: string; error?: string; owner_request?: unknown }
  const refusal = new ApiRefusal(
    response.status,
    named.refusal ?? `unknown_outcome:http_${response.status}`,
    named.error ?? 'unknown_outcome',
    named.owner_request ?? null,
  )
  if (refusal.error === 'unauthenticated' && !CEREMONY.has(name)) apiContext.onUnauthenticated?.(refusal)
  throw refusal
}
