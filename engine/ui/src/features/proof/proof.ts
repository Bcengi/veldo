import type { Item, ReadAnswer } from '@/api/types'

export interface Check {
  name: string
  status: string
  command: string
  observation: string
}

export interface Artifact {
  criterion: string
  type: string
  path: string
  digest: string
}

export interface Bundle {
  id: string
  unit: string
  spec: string
  revision: number | null
  criteria: string[]
  checks: Check[]
  artifacts: Artifact[]
  manifestPath: string
  manifestBody: string
  commit: string
  accepted: string
  observation: string
}

export interface Observation {
  id: string
  commit: string
  terminal: string
  green: boolean
  exit: number | null
  finishedAt: number | null
  output: string
  command: string
}

/** A finding the owner should look at: a check that did not pass, or a gate observation that was not green. */
export interface Finding {
  id: string
  title: string
  detail: string
}

const str = (v: unknown, fallback = '') => (typeof v === 'string' ? v : fallback)

export function bundlesOf(answer: ReadAnswer | null): Bundle[] {
  return (answer?.items.proof_bundle ?? []).map((item: Item) => {
    const d = item.data as Record<string, any>
    return {
      id: item.id,
      unit: str(d.unit),
      spec: str(d.spec?.path),
      revision: typeof d.spec?.revision === 'number' ? d.spec.revision : null,
      criteria: Array.isArray(d.spec?.criteria) ? d.spec.criteria.map(String) : [],
      checks: (Array.isArray(d.checks) ? d.checks : []).map((c: Record<string, unknown>) => ({
        name: str(c.name), status: str(c.status, 'unknown'), command: str(c.command), observation: str(c.observation),
      })),
      artifacts: (Array.isArray(d.artifacts) ? d.artifacts : []).map((a: Record<string, unknown>) => ({
        criterion: str(a.criterion), type: str(a.type), path: str(a.path), digest: str(a.digest),
      })),
      manifestPath: str(d.manifest?.path),
      manifestBody: d.manifest?.body === undefined ? '' : JSON.stringify(d.manifest.body, null, 2),
      commit: str(d.implementation?.commit ?? d.source?.commit),
      accepted: d.accepted ? `${str(d.accepted.principal)}` : '',
      observation: str(d.observation?.id),
    }
  })
}

export function observationsOf(answer: ReadAnswer | null): Observation[] {
  return (answer?.items.gate_observation ?? [])
    .map((item: Item) => {
      const d = item.data as Record<string, any>
      return {
        id: item.id,
        commit: str(d.commit),
        terminal: str(d.terminal),
        green: d.green === true,
        exit: typeof d.exit === 'number' ? d.exit : null,
        finishedAt: typeof d.finished_at === 'number' ? d.finished_at : null,
        output: [str(d.stdout), str(d.stderr)].filter(Boolean).join('\n'),
        command: Array.isArray(d.command) ? d.command.join(' ') : str(d.command),
      }
    })
    .sort((a, b) => (a.finishedAt ?? 0) - (b.finishedAt ?? 0))
}

export function findingsOf(bundles: Bundle[], observations: Observation[]): Finding[] {
  const findings: Finding[] = []
  for (const b of bundles)
    for (const c of b.checks)
      if (c.status !== 'passed') findings.push({ id: `${b.id}:${c.name}`, title: `${b.unit}: ${c.name} ${c.status}`, detail: c.command })
  for (const o of observations)
    if (!o.green) findings.push({ id: o.id, title: `Gate not green at ${o.commit.slice(0, 7)}`, detail: o.terminal || `exit ${o.exit ?? 'unknown'}` })
  return findings
}
