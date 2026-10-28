import type { LampState } from '@/app/navigation'

/** A dispatch state's lamp and word (control_dispatch states). */
export function runLamp(state: string): { lamp: LampState; word: string } {
  switch (state) {
    case 'running':
      return { lamp: 'live', word: 'Running' }
    case 'accepted':
    case 'prepared':
      return { lamp: 'waiting', word: 'Starting' }
    case 'exited':
      return { lamp: 'done', word: 'Ended' }
    case 'refused':
      return { lamp: 'stop', word: 'Refused' }
    default:
      return { lamp: 'stop', word: 'Unknown' }
  }
}

/** The line a unit moves along (entity_contract's states), as the station strip shows it. */
export const LINE: { states: string[]; label: string }[] = [
  { states: ['PLANNED', 'READY'], label: 'Ready' },
  { states: ['CLAIMED'], label: 'Claimed' },
  { states: ['DISPATCHING'], label: 'Dispatch' },
  { states: ['RUNNING'], label: 'Build' },
  { states: ['VERIFYING'], label: 'Verify' },
  { states: ['REVIEWING'], label: 'Review' },
  { states: ['READY_TO_LAND', 'LANDING'], label: 'Land' },
  { states: ['COMPLETED'], label: 'Done' },
]

/** States off the line: the unit stopped, or waits on authority. */
export const OFF_LINE: Record<string, { lamp: LampState; word: string }> = {
  FAILED: { lamp: 'stop', word: 'Failed' },
  CANCELED: { lamp: 'stop', word: 'Canceled' },
  AWAITING_AUTHORITY: { lamp: 'waiting', word: 'Waiting on authority' },
}

/** Which station of the line is lit for a unit state, or -1 when it is off the line or unknown. */
export function stationIndex(unitState: string | null): number {
  if (!unitState) return -1
  return LINE.findIndex((s) => s.states.includes(unitState))
}
