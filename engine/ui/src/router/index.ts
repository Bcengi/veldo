import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useSessionStore } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    /** The screen shows factory data, so it needs a passkey session. */
    session?: boolean
    title?: string
  }
}

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'overview', component: () => import('@/views/OverviewView.vue'), meta: { session: true, title: 'Overview' } },
  { path: '/sign-in', name: 'sign-in', component: () => import('@/views/SignInView.vue'), meta: { title: 'Sign in' } },
  { path: '/runs', name: 'runs', component: () => import('@/views/RunsView.vue'), meta: { session: true, title: 'Runs' } },
  {
    // A dispatch id carries slashes (dispatch/<unit>/<hex>), so the run is one repeatable segment.
    path: '/runs/:dispatch(.*)+',
    name: 'run',
    component: () => import('@/views/RunView.vue'),
    meta: { session: true, title: 'Run' },
  },
  { path: '/decisions', name: 'decisions', component: () => import('@/views/DecisionsView.vue'), meta: { session: true, title: 'Decisions' } },
  {
    path: '/decisions/:request(.*)+',
    name: 'decision',
    component: () => import('@/views/DecisionsView.vue'),
    meta: { session: true, title: 'Decision' },
  },
  // VELDO-0163: a role's capability configuration and a project's team roles (and the default team).
  { path: '/roles/:role?', name: 'role', component: () => import('@/views/RoleView.vue'), meta: { session: true, title: 'Roles' } },
  { path: '/teams/:project?', name: 'team', component: () => import('@/views/TeamView.vue'), meta: { session: true, title: 'Team' } },
  { path: '/you', name: 'you', component: () => import('@/views/YouView.vue'), meta: { session: true, title: 'You' } },
  { path: '/:rest(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue'), meta: { title: 'Not found' } },
]

export function makeRouter() {
  const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) })
  router.beforeEach(async (to) => {
    const session = useSessionStore()
    if (session.status === 'unknown') await session.restore()
    if (to.meta.session && session.status !== 'signed-in') {
      return { name: 'sign-in', query: { next: to.fullPath } }
    }
    if (to.name === 'sign-in' && session.status === 'signed-in') {
      return safeNext(to.query.next)
    }
    return true
  })
  router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} | Veldo` : 'Veldo'
  })
  return router
}

/** Where to go after sign-in: a path of this origin only. `//host` and `/\\host` name another origin to a
 * browser, so a `next` must be one slash followed by something other than a slash or a backslash. */
export const NEXT_PATTERN = /^\/(?![/\\])/
export function safeNext(value: unknown): string {
  return typeof value === 'string' && NEXT_PATTERN.test(value) ? value : '/'
}

/** The dispatch id of a run route's parameter. */
export function joinParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value.join('/') : (value ?? '')
}
