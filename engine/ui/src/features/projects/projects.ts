import type { Item, ReadAnswer } from '@/api/types'

export interface ObjectiveView {
  id: string
  project: string
  state: string
  outcome: string
  scope: string[]
  evidence: { id: string; kind: string }[]
  features: number
  assessment: string | null
  version: number
}

/** Where a project's landings end (VELDO-0235): pushed to its remote, or its local trunk moved with nothing pushed. */
export type LandingDestination = 'land_and_push' | 'land_locally'

export interface ProjectView {
  name: string
  state: string
  owner: string
  purpose: string
  objectives: ObjectiveView[]
  destination: LandingDestination
  destinationWords: string
}

/** A message the owner or a member sent to the common intake, as the intake recorded it. */
export interface IntakeEntry {
  id: string
  text: string
  project: string | null
  state: string
  principal: string
  kind: 'proposal' | 'question'
}

const str = (v: unknown, fallback = '') => (typeof v === 'string' ? v : fallback)

/** A project record's landing destination: its field, or land_and_push when the record names none (VELDO-0235). */
export function landingDestination(data: Record<string, unknown>): LandingDestination {
  return data.landing_destination === 'land_locally' ? 'land_locally' : 'land_and_push'
}

/** The destination in words, as every landing brief names it: "land and push to <remote>" or "land locally on
 * <trunk>, nothing pushed". A project record names neither its remote nor its trunk, so the view says "its". */
export function destinationWords(destination: LandingDestination, remote = 'its remote', trunk = 'its trunk'): string {
  return destination === 'land_locally' ? `land locally on ${trunk}, nothing pushed` : `land and push to ${remote}`
}

function objectiveOf(item: Item): ObjectiveView {
  const d = item.data as Record<string, any>
  const bound = (d.bound ?? {}) as Record<string, any>
  return {
    id: item.id,
    project: str(d.project),
    state: str(d.state, 'unknown'),
    outcome: str(bound.outcome, item.id),
    scope: Array.isArray(bound.scope) ? bound.scope.map(String) : [],
    evidence: Array.isArray(bound.evidence_requirements)
      ? bound.evidence_requirements.map((e: Record<string, unknown>) => ({ id: str(e.id), kind: str(e.kind) }))
      : [],
    features: Array.isArray(d.features) ? d.features.length : 0,
    assessment: d.assessment && typeof d.assessment === 'object' ? str((d.assessment as Record<string, unknown>).outcome, 'assessed') : null,
    version: item.version,
  }
}

/** The projects of the objectives read, each with its objectives, by name. */
export function projectsOf(answer: ReadAnswer | null): ProjectView[] {
  if (!answer) return []
  const objectives = (answer.items.objective ?? []).map(objectiveOf)
  return (answer.items.project ?? [])
    .map((item) => {
      const d = item.data as Record<string, any>
      const name = str(d.name, item.id.replace(/^project:/, ''))
      const destination = landingDestination(d)
      return {
        name,
        state: str(d.state, 'unknown'),
        owner: str(d.owner),
        purpose: str(d.charter?.purpose),
        objectives: objectives.filter((o) => o.project === name),
        destination,
        destinationWords: destinationWords(destination),
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
}

/** Projects whose name, purpose or any objective's outcome contains every word of `query`. */
export function searchProjects(projects: ProjectView[], query: string): ProjectView[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return projects
  return projects.filter((p) => {
    const text = [p.name, p.purpose, p.state, ...p.objectives.map((o) => `${o.outcome} ${o.state}`)].join(' ').toLowerCase()
    return words.every((w) => text.includes(w))
  })
}

/** The intake's records of messages (proposals and the questions it asked back), newest last. */
export function intakeOf(answer: ReadAnswer | null): IntakeEntry[] {
  if (!answer) return []
  const proposals = (answer.items.intake_proposal ?? []).map((item) => {
    const d = item.data as Record<string, unknown>
    return { id: item.id, text: str(d.text), project: typeof d.project === 'string' ? d.project : null, state: str(d.state), principal: str(d.principal), kind: 'proposal' as const }
  })
  const questions = (answer.items.intake_question ?? []).map((item) => {
    const d = item.data as Record<string, unknown>
    const candidates = Array.isArray(d.candidates) ? d.candidates.join(', ') : ''
    return { id: item.id, text: `Which project? ${candidates}`.trim(), project: typeof d.project === 'string' ? d.project : null, state: str(d.state), principal: 'intake', kind: 'question' as const }
  })
  return [...proposals, ...questions]
}
