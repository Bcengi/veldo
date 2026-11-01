import type { ConfigurationRevision } from '@/api/configuration'
import type { ReadAnswer } from '@/api/types'

export interface RoleRevision {
  role: string
  revision: number
  engine: string
  /** Every native tool with its load mode, exactly as the revision stores it. */
  tools: string[]
  /** Every MCP server selection: server, catalog revision, tools and load mode. */
  servers: string[]
  skills: string[]
  digest: string
}

export interface RoleView {
  role: string
  current: RoleRevision
  history: RoleRevision[]
  teams: string[]
}

export interface TeamView {
  id: string
  project: string
  version: number
  roles: string[]
  pending: boolean
}

const str = (v: unknown, fallback = '') => (typeof v === 'string' ? v : fallback)

/** The configuration read's teams (project teams and the newest default team revision). */
export function teamsOf(answer: ReadAnswer | null): TeamView[] {
  const teams = (answer?.items.team ?? []).map((item) => {
    const d = item.data as Record<string, any>
    return { id: item.id, project: str(d.project, item.id.replace(/^team:/, '')), version: item.version, roles: Object.keys(d.team?.roles ?? {}), pending: !!d.proposal }
  })
  const defaults = (answer?.items.default_team_revision ?? []).map((item) => {
    const d = item.data as Record<string, any>
    return { id: item.id, project: 'default', version: typeof d.revision === 'number' ? d.revision : item.version, roles: Object.keys(d.team?.roles ?? {}), pending: false }
  })
  const newestDefault = defaults.sort((a, b) => b.version - a.version)[0]
  return [...teams.sort((a, b) => a.project.localeCompare(b.project)), ...(newestDefault ? [newestDefault] : [])]
}

/** Every capability configuration a team names, with the teams that name it: the roles the table lists. The
 * configuration read serves teams; each named configuration's revisions are then read through
 * configurations.read (VELDO-0162). */
export function namedRoles(answer: ReadAnswer | null): Map<string, string[]> {
  const named = new Map<string, string[]>()
  const teams = teamsOf(answer)
  for (const item of [...(answer?.items.team ?? []), ...(answer?.items.default_team_revision ?? [])]) {
    const project = teams.find((t) => t.id === item.id)?.project ?? 'default'
    for (const role of Object.values(((item.data as Record<string, any>).team?.roles ?? {}) as Record<string, any>)) {
      const name = role?.capability_configuration?.role
      if (typeof name === 'string') named.set(name, [...new Set([...(named.get(name) ?? []), project])])
    }
  }
  return named
}

export function revisionView(r: ConfigurationRevision): RoleRevision {
  return {
    role: r.role,
    revision: r.revision,
    engine: r.engine,
    tools: r.native_tools.map((t) => `${t.name} (${t.load})`),
    servers: r.mcp.map((m) => `${m.server} r${m.revision}: ${m.tools === 'all' ? 'all tools' : m.tools.join(', ')} (${m.load})`),
    skills: r.skills.map((s) => `${s.skill} r${s.revision} (${s.load})`),
    digest: r.digest,
  }
}

export function roleView(role: string, revisions: ConfigurationRevision[], teams: string[]): RoleView | null {
  const history = revisions.map(revisionView).sort((a, b) => b.revision - a.revision)
  return history.length ? { role, current: history[0]!, history, teams } : null
}
