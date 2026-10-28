import { computed, type ComputedRef } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { useDecisionsStore } from '@/stores/decisions'

export type LampState = 'off' | 'live' | 'waiting' | 'stop' | 'done'

/** One destination of the shell's navigation. Later screens (VELDO-0131, 0159, 0163, 0179) add entries here;
 * the rail shows every entry, the phone's bottom bar only those marked `phone` (at most four). */
export interface NavEntry {
  id: string
  label: string
  to: RouteLocationRaw
  /** The route names that count as this destination being current. */
  matches: string[]
  icon: 'runs' | 'decisions' | 'you'
  phone: boolean
  /** The entry's lamp and its words, when it signals something. */
  signal?: () => { state: LampState; label: string; count: number } | null
}

export function useNavigation(): ComputedRef<NavEntry[]> {
  const decisions = useDecisionsStore()
  return computed(() => [
    { id: 'runs', label: 'Runs', to: { name: 'runs' }, matches: ['runs', 'run'], icon: 'runs', phone: true },
    {
      id: 'decisions',
      label: 'Decisions',
      to: { name: 'decisions' },
      matches: ['decisions', 'decision'],
      icon: 'decisions',
      phone: true,
      signal: () =>
        decisions.waiting > 0
          ? { state: 'waiting', label: `${decisions.waiting} waiting on you`, count: decisions.waiting }
          : null,
    },
    { id: 'you', label: 'You', to: { name: 'you' }, matches: ['you'], icon: 'you', phone: true },
  ])
}
