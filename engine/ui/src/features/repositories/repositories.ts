import type { IdentityMeta } from '@/api/reads'
import type { ReadAnswer } from '@/api/types'

/** One repository record (VELDO-0161, VELDO-0143) as the repositories read serves it. */
export interface RepositoryView {
  id: string
  name: string
  identity: string
  path: string
  remote: string
  /** adopted, or created by the provisioner. */
  origin: string
  /** provisioning, active or failed. */
  state: string
  /** The named reason of a failed record (and the step it failed at), else ''. */
  reason: string
}

const str = (v: unknown) => (typeof v === 'string' ? v : '')

function remoteOf(remote: unknown): string {
  if (typeof remote === 'string') return remote
  if (remote && typeof remote === 'object') {
    const r = remote as Record<string, unknown>
    return str(r.url) || [str(r.owner), str(r.name)].filter(Boolean).join('/')
  }
  return ''
}

/** The repository records of the read, by name. */
export function repositoriesOf(answer: ReadAnswer | null): RepositoryView[] {
  return (answer?.items.repository ?? [])
    .map((item) => {
      const d = item.data as Record<string, any>
      const history = Array.isArray(d.history) ? (d.history as Record<string, unknown>[]) : []
      const failed = [...history].reverse().find((h) => h.state === 'failed')
      const reason = str(d.reason) || str(failed?.reason)
      const step = str(failed?.step)
      return {
        id: item.id,
        name: str(d.name) || str(d.repository) || item.id,
        identity: str(d.identity),
        path: str(d.path),
        remote: remoteOf(d.remote),
        origin: str(d.origin),
        state: str(d.state) || 'unknown',
        reason: reason ? (step && d.state === 'failed' ? `${reason} (at ${step})` : reason) : '',
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
}

/** The identities of the read, by label. */
export function identitiesOf(answer: { identities?: IdentityMeta[] } | null): IdentityMeta[] {
  return [...(answer?.identities ?? [])].sort((a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
}

/** "Name <email>", the author an identity commits as. */
export const authorOf = (i: IdentityMeta) => `${i.author_name} <${i.author_email}>`
