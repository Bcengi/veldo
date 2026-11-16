import { request } from './client'
import { ROUTES, type RouteName } from './routes'

/** The owner's work commands (VELDO-0131, owner Telegram 38184): each names the route it uses, the contract's own
 * when it names one, else this name. A route the API does not publish sends nothing and the result names it. */
export const ACTION_ROUTES = {
  /** The owner's stop request of one worker run (control_dispatch.request_stop). */
  worker_stop: 'workers.stop',
  /** The owner's rank of one backlog item (control_backlog's reprioritize, through the API edge). */
  owner_priority: 'backlog.reprioritize',
  /** The owner's cap of one account's concurrent runs (control_accounts.cap). */
  worker_cap: 'workers.cap',
  /** The owner's Reconcile of the space ledger, for one project or all (VELDO-0315, through VELDO-0319's screen). */
  space_reconcile: 'space.reconcile',
  /** The owner's Abandon of one worktree: worktree abandoned for that item (VELDO-0312). */
  worktree_abandon: 'space.abandon',
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

/** Set one account's run concurrency (1 to 16) at the version shown, by the owner's own command. */
export function setCap(account: string, accountVersion: number, concurrency: number, contractRoute: string | null = null) {
  return send<Record<string, unknown>>(contractRoute ?? ACTION_ROUTES.worker_cap, { account, account_version: accountVersion, concurrency })
}

/** What the API answers an accepted Abandon with: the item's state now, what was removed, what was deferred and
 * the worktrees that stay until the owner's Discard, which saves first. */
export interface AbandonAnswer {
  outcome: string
  item?: string
  version?: number | null
  state?: string | null
  removed?: string[]
  deferred?: { item: string; deferral: string | null }[]
  discard_required?: string[]
  api_request_id: string
}

/** Run a reconcile of the space ledger now, for one project or, with null, for all (the owner's signed command). */
export function reconcileSpace(project: string | null, contractRoute: string | null = null) {
  return send<{ outcome: string; api_request_id: string }>(contractRoute ?? ACTION_ROUTES.space_reconcile, { project })
}

/** Abandon one worktree: the item at the version shown (the owner's signed command). It removes no unique work. */
export function abandonWorktree(item: string, version: number, contractRoute: string | null = null) {
  return send<AbandonAnswer>(contractRoute ?? ACTION_ROUTES.worktree_abandon, { item, version })
}
