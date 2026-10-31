import type { Team, TeamRecord, TeamRole } from '@/api/configuration'
import { names } from '@/features/roles/role-draft'

/** VELDO-0089's required roles: a team without any of them is refused as an incomplete roster. */
export const REQUIRED_ROLES = ['project_manager', 'elaboration', 'implementation', 'independent_review'] as const
export const KINDS = ['required', 'specialist'] as const

/** One team role as the form edits it: list fields as comma separated text, numbers as text. */
export interface RoleRow {
  name: string
  kind: 'required' | 'specialist'
  configRole: string
  configRevision: string
  workers: string
  responsibilities: string
  expertise: string
  permissions: string
  engines: string
  capacity: string
  invocations: string
  wallSeconds: string
  distinctFrom: string
}

/** A team as the form edits it, bound to what it was edited from: a project's team version, or the default
 * team's revision. */
export interface TeamDraft {
  rows: RoleRow[]
  editedFrom: number
}

const list = (values: string[] | undefined) => (values ?? []).join(', ')

export function rowOf(name: string, role: TeamRole): RoleRow {
  return {
    name,
    kind: role.kind ?? 'required',
    configRole: role.capability_configuration?.role ?? '',
    configRevision: role.capability_configuration ? String(role.capability_configuration.revision) : '',
    workers: list(role.workers),
    responsibilities: list(role.responsibilities),
    expertise: list(role.expertise),
    permissions: list(role.proposal_permissions),
    engines: list(role.engines),
    capacity: String(role.budget?.capacity ?? ''),
    invocations: String(role.budget?.invocations ?? ''),
    wallSeconds: String(role.budget?.wall_seconds ?? ''),
    distinctFrom: list(role.independence?.distinct_from),
  }
}

/** A new role the owner adds: a specialist with no configuration yet. */
export function newRow(name: string): RoleRow {
  return {
    name,
    kind: 'specialist',
    configRole: '',
    configRevision: '',
    workers: '',
    responsibilities: '',
    expertise: '',
    permissions: '',
    engines: 'claude_code',
    capacity: '1',
    invocations: '1',
    wallSeconds: '600',
    distinctFrom: '',
  }
}

export function rowsOf(team: Team | null | undefined): RoleRow[] {
  const roles = team?.roles ?? {}
  const order = (name: string) => {
    const at = (REQUIRED_ROLES as readonly string[]).indexOf(name)
    return at < 0 ? REQUIRED_ROLES.length : at
  }
  return Object.keys(roles)
    .sort((a, b) => order(a) - order(b) || a.localeCompare(b))
    .map((name) => rowOf(name, roles[name]!))
}

/** A whole number, or NaN (sent as null) so the authority refuses it by name. */
const count = (text: string) => (/^\d+$/.test(text.trim()) ? Number(text.trim()) : Number.NaN)

/** Exactly the team the team route stores. A role whose configuration is left blank is sent without a
 * reference, so the authority refuses it by name rather than the form guessing one. */
export function toTeam(rows: RoleRow[]): Team {
  const roles: Record<string, TeamRole> = {}
  for (const row of rows) {
    const role: TeamRole = {
      kind: row.kind,
      workers: names(row.workers),
      responsibilities: names(row.responsibilities),
      expertise: names(row.expertise),
      proposal_permissions: names(row.permissions),
      engines: names(row.engines),
      budget: { capacity: count(row.capacity), invocations: count(row.invocations), wall_seconds: count(row.wallSeconds) },
      independence: { distinct_from: names(row.distinctFrom) },
    }
    if (row.configRole.trim() || row.configRevision.trim())
      role.capability_configuration = { role: row.configRole.trim(), revision: count(row.configRevision) }
    roles[row.name.trim()] = role
  }
  return { roles }
}

/** What the form shows as the current team: only what the authority accepted, read back through the team
 * route. A pending proposal is never current; it is shown apart as waiting (see `pendingOf`). */
export function currentOf(record: TeamRecord | null): { revision: number; team: Team } | null {
  if (!record) return null
  return { revision: record.revision, team: record.team }
}

/** The proposal waiting on the owner's answer, or null. */
export function pendingOf(record: TeamRecord | null): NonNullable<TeamRecord['proposal']> | null {
  return record?.proposal ?? null
}

/** What a draft is bound to: a project's team version, or the default team's revision. */
export function editedFromOf(record: TeamRecord | null, isDefault: boolean): number {
  if (!record) return 0
  return isDefault ? record.revision : (record.version ?? 0)
}
