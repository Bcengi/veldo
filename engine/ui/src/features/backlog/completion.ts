import type { ReadAnswer } from '@/api/types'

/** What the owner may be told about a unit's end (VELDO-0131 AC2): "Landed" only when its landing's completion
 * receipt is in the authority's proof read (reads.proof, `completion_receipt`, naming the unit as its subject).
 * A unit whose own record says COMPLETED without a receipt was built, but its landing is not confirmed; it is
 * never shown as complete from that local build state. */
export type Completion = 'landed' | 'built-unconfirmed' | 'not-complete'

/** The units the proof read holds a completion receipt for. */
export function landedUnits(proof: ReadAnswer | null): Set<string> {
  const landed = new Set<string>()
  for (const item of proof?.items.completion_receipt ?? []) {
    const subject = (item.data as { subject?: { id?: unknown } }).subject
    if (typeof subject?.id === 'string') landed.add(subject.id)
  }
  return landed
}

export function completionOf(unit: string, state: string, landed: Set<string>): Completion {
  if (landed.has(unit)) return 'landed'
  if (state === 'COMPLETED') return 'built-unconfirmed'
  return 'not-complete'
}

export const COMPLETION_WORDS: Record<Completion, string> = {
  landed: 'Landed',
  'built-unconfirmed': 'Built, landing not confirmed',
  'not-complete': '',
}
