import type { Binding, StoredServer } from '@/api/mcp'
import type { CredentialMeta } from '@/stores/servers'

export interface CatalogRow {
  id: string
  label: string
  revision: number
  transport: string
  target: string
  hosts: string[]
  readOnlyTools: string[]
  /** Every credential reference the revision names, by environment variable or header. */
  credentials: { name: string; where: 'environment' | 'header'; reference: string }[]
  history: number[]
}

function referencesOf(map: Record<string, Binding> | undefined, where: 'environment' | 'header') {
  return Object.entries(map ?? {})
    .filter(([, b]) => b && typeof b === 'object' && 'reference' in b && typeof b.reference === 'string')
    .map(([name, b]) => ({ name, where, reference: (b as { reference: string }).reference }))
}

/** A catalog row from a server's revisions (oldest first), showing `shown` (the newest when null). */
export function catalogRow(revisions: StoredServer[], shown: number | null = null): CatalogRow | null {
  if (!revisions.length) return null
  const s = revisions.find((r) => r.revision === shown) ?? revisions[revisions.length - 1]!
  return {
    id: s.id,
    label: s.label,
    revision: s.revision,
    transport: s.transport,
    target: s.transport === 'http' ? (s.url ?? '') : [s.command ?? '', ...(s.arguments ?? [])].join(' ').trim(),
    hosts: s.hosts ?? [],
    readOnlyTools: s.read_only_tools ?? [],
    credentials: [...referencesOf(s.environment, 'environment'), ...referencesOf(s.headers, 'header')],
    history: revisions.map((r) => r.revision).sort((a, b) => b - a),
  }
}

/** The credential record this session wrote under `reference`, if any (label, set at, set by; never a value). */
export function credentialMeta(credentials: Record<string, CredentialMeta>, reference: string): CredentialMeta | null {
  return Object.values(credentials).find((c) => c.reference === reference) ?? null
}
