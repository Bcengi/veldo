import { request } from './client'
import { ROUTES, type RouteName } from './routes'

/** Owner actions whose API route is not published yet (VELDO-0131 fix round 2). Each names the route it will use,
 * so the screen's call works the moment the API publishes it: the contract's own route when it names one,
 * else this name. Until then nothing is sent and the result names the missing route. */
export const ACTION_ROUTES = {
  /** A signed stop command in the dispatch and launch authority (VELDO-0041), awaiting the owner. */
  worker_stop: 'workers.stop',
  /** The backlog's reprioritize command through the API edge (VELDO-0078), awaiting the owner. */
  owner_priority: 'backlog.reprioritize',
} as const

export type ActionResult<T> = { sent: true; answer: T } | { sent: false; route: string }

/** Whether the UI's route table (the mirror of the API's published ROUTES) carries `route`. */
export function published(route: string): route is RouteName {
  return Object.prototype.hasOwnProperty.call(ROUTES, route)
}

async function send<T>(route: string, body: Record<string, unknown>): Promise<ActionResult<T>> {
  if (!published(route)) return { sent: false, route }
  return { sent: true, answer: await request<T>(route, { body }) }
}

/** Stop one worker run: the dispatch at the version shown. */
export function stopWorker(dispatch: string, version: number, contractRoute: string | null = null) {
  return send<Record<string, unknown>>(contractRoute ?? ACTION_ROUTES.worker_stop, { dispatch, dispatch_version: version })
}

/** Set one backlog item's rank (1 to 5) at the version shown, by the owner's own command. */
export function reprioritize(item: string, itemVersion: number, rank: number, contractRoute: string | null = null) {
  return send<Record<string, unknown>>(contractRoute ?? ACTION_ROUTES.owner_priority, { item, item_version: itemVersion, rank })
}
