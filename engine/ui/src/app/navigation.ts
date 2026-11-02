import { computed, type ComputedRef } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { IconName } from '@/components/Icon.vue'
import type { IconId } from '@/ui/icons'
import { useDecisionsStore } from '@/stores/decisions'

export type LampState = 'off' | 'here' | 'live' | 'waiting' | 'stop' | 'done'

/** One destination of the shell's navigation. Later screens (VELDO-0131, 0159, 0163, 0179) add entries here;
 * the rail shows every entry, the phone's bottom bar only those marked `phone` (at most four). */
export interface NavEntry {
  id: string
  label: string
  to: RouteLocationRaw
  /** The route names that count as this destination being current. */
  matches: string[]
  icon: IconName
  /** The sidebar's icon for this destination (Nuxt UI, bundled; VELDO-0229). */
  glyph: IconId
  phone: boolean
  /** The desktop rail's group; a subtle separator divides the groups. */
  group: 'operate' | 'factory' | 'setup'
  /** The entry's count badge and its words, when something waits there. */
  badge?: () => { count: number; label: string; tone: 'waiting' | 'stop' } | null
}

export function useNavigation(): ComputedRef<NavEntry[]> {
  const decisions = useDecisionsStore()
  return computed(() => [
    { id: 'overview', label: 'Overview', to: { name: 'overview' }, matches: ['overview'], icon: 'overview', glyph: 'i-lucide-layout-dashboard', phone: true, group: 'operate' },
    { id: 'runs', label: 'Runs', to: { name: 'runs' }, matches: ['runs', 'run'], icon: 'runs', glyph: 'i-lucide-square-terminal', phone: true, group: 'operate' },
    {
      id: 'decisions',
      label: 'Decisions',
      to: { name: 'decisions' },
      matches: ['decisions', 'decision'],
      icon: 'decisions',
      glyph: 'i-lucide-inbox',
      phone: true,
      group: 'operate',
      badge: () =>
        decisions.waiting > 0 ? { count: decisions.waiting, label: `${decisions.waiting} waiting on you`, tone: 'waiting' } : null,
    },
    { id: 'servers', label: 'MCP servers', to: { name: 'servers' }, matches: ['servers', 'server'], icon: 'key', glyph: 'i-lucide-server', phone: false, group: 'setup' },
    // VELDO-0163: rail entries; on a phone the You screen links to them.
    { id: 'roles', label: 'Roles', to: { name: 'role' }, matches: ['role'], icon: 'key', glyph: 'i-lucide-id-card', phone: false, group: 'setup' },
    { id: 'team', label: 'Team', to: { name: 'team' }, matches: ['team'], icon: 'overview', glyph: 'i-lucide-users', phone: false, group: 'setup' },
    // VELDO-0131: rail entries; on a phone the You screen links to them.
    { id: 'projects', label: 'Projects', to: { name: 'project' }, matches: ['project'], icon: 'overview', glyph: 'i-lucide-folder-kanban', phone: false, group: 'factory' },
    { id: 'backlog', label: 'Backlog', to: { name: 'backlog' }, matches: ['backlog'], icon: 'decisions', glyph: 'i-lucide-list-todo', phone: false, group: 'factory' },
    { id: 'workers', label: 'Workers', to: { name: 'workers' }, matches: ['workers'], icon: 'runs', glyph: 'i-lucide-cpu', phone: false, group: 'factory' },
    { id: 'proof', label: 'Gate and review', to: { name: 'proof' }, matches: ['proof'], icon: 'check', glyph: 'i-lucide-shield-check', phone: false, group: 'factory' },
    { id: 'usage', label: 'Usage', to: { name: 'usage' }, matches: ['usage'], icon: 'refresh', glyph: 'i-lucide-chart-column', phone: false, group: 'factory' },
    { id: 'configuration', label: 'Configuration', to: { name: 'configuration' }, matches: ['configuration'], icon: 'key', glyph: 'i-lucide-settings', phone: false, group: 'setup' },
    { id: 'catalog', label: 'MCP catalog', to: { name: 'catalog' }, matches: ['catalog'], icon: 'search', glyph: 'i-lucide-library', phone: false, group: 'setup' },
    { id: 'repositories', label: 'Repositories', to: { name: 'repositories' }, matches: ['repositories'], icon: 'overview', glyph: 'i-lucide-git-branch', phone: false, group: 'setup' },
    { id: 'workflows', label: 'Workflows', to: { name: 'workflow' }, matches: ['workflow'], icon: 'follow', glyph: 'i-lucide-workflow', phone: false, group: 'setup' },
    { id: 'you', label: 'You', to: { name: 'you' }, matches: ['you'], icon: 'you', glyph: 'i-lucide-circle-user', phone: true, group: 'setup' },
  ])
}
