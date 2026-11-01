import type { Binding, StoredServer } from '@/api/mcp'
import type { Item, ReadAnswer } from '@/api/types'
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

const text = (v: unknown) => (typeof v === 'string' ? v : '')

/** Every server the catalog read lists (its heads): id and current revision, by id. */
export function headsOf(answer: ReadAnswer | null): { id: string; revision: number }[] {
  return (answer?.items.mcp_server_head ?? [])
    .map((item) => ({ id: text(item.data.id), revision: typeof item.data.revision === 'number' ? item.data.revision : 0 }))
    .filter((h) => h.id && h.revision > 0)
    .sort((a, b) => a.id.localeCompare(b.id))
}

/** The keystore reference of a credential entity (control_credential: the entity id's digest, under keychain:veldo/).
 * Derived from the entity id, which the API serves whole, because the reference text may be redacted as entropy. */
export function referenceOfEntity(entityId: string): string {
  return 'keychain:veldo/' + entityId.replace(/^credential:/, '')
}

/** Every credential record of the catalog read, metadata only (label, set at, set by, deleted), by reference. */
export function credentialsOf(answer: ReadAnswer | null): CredentialMeta[] {
  return (answer?.items.credential ?? [])
    .map((item: Item) => ({
      id: text(item.data.id),
      label: text(item.data.label),
      setAt: typeof item.data.set_at === 'number' ? item.data.set_at : 0,
      setBy: text(item.data.set_by),
      reference: referenceOfEntity(item.id),
      version: item.version,
      deleted: item.data.deleted === true,
    }))
    .sort((a, b) => a.id.localeCompare(b.id))
}
