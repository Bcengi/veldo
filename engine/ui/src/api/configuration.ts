import { request } from './client'
import { isRefusal } from './refusal'

/** A role's capability configuration as VELDO-0127 stores it and VELDO-0162 AC1's route saves it. */
export type LoadMode = 'always' | 'when assigned'
export interface NativeTool { name: string; load: LoadMode }
export interface McpSelection { server: string; revision: number; tools: 'all' | string[]; load: LoadMode }
export interface SkillReference { skill: string; revision: number; load: LoadMode }
export interface InstructionFile { source: 'project' | 'factory'; path: string; load: LoadMode }
export interface Definition {
  role: string
  engine: 'claude_code' | 'codex'
  native_tools: NativeTool[]
  mcp: McpSelection[]
  skills: SkillReference[]
  instructions: InstructionFile[]
  settings: Record<string, unknown>
}
/** A stored revision: the definition with its revision, digest and the digest of the revision before it. */
export interface ConfigurationRevision extends Definition {
  revision: number
  digest: string
  previous: string | null
}

/** A catalog server revision (VELDO-0144), as the catalog read serves it. */
export interface CatalogServer {
  id: string
  label: string
  revision: number
  transport: string
  read_only_tools: string[]
}

/** One team role with VELDO-0089's role fields and VELDO-0151's kind and configuration reference. */
export interface TeamRole {
  kind?: 'required' | 'specialist'
  capability_configuration?: { role: string; revision: number }
  workers: string[]
  responsibilities: string[]
  expertise: string[]
  proposal_permissions: string[]
  engines: string[]
  budget: { capacity: number; invocations: number; wall_seconds: number }
  independence: { distinct_from: string[] }
}
export interface Team { roles: Record<string, TeamRole> }

/** A project's team record (VELDO-0089) or a default team revision (VELDO-0162 AC4), as the team route reads it. */
export interface TeamRecord {
  project?: string
  revision: number
  version?: number
  team: Team
  digest: string
  proposal?: { revision: number; team: Team; digest: string; proposed_by?: string } | null
  saved_by?: string
}

export interface SaveAnswer {
  outcome: string
  revision?: number
  version?: number
  role?: string
  digest?: string
  owner_request?: string | null
  team_application?: unknown
  api_request_id: string
}

export const readConfiguration = (role: string, revision: number, signal?: AbortSignal) =>
  request<{ configuration: ConfigurationRevision }>('configurations.read', { fields: { role, revision }, signal }).then(
    (answer) => answer.configuration,
  )

/** The newest stored revision of a role (0 when it has none): the revisions are read in turn until one is
 * missing, since the configuration route reads one named revision. */
export async function latestRevision(role: string, signal?: AbortSignal): Promise<number> {
  let revision = 0
  for (;;) {
    try {
      await readConfiguration(role, revision + 1, signal)
      revision += 1
    } catch (error) {
      if (isRefusal(error) && error.error === 'missing_evidence') return revision
      throw error
    }
  }
}

/** Save `definition` as the revision after `base`, the revision the form was edited from. */
export const saveConfiguration = (definition: Definition, base: number) =>
  request<SaveAnswer>('configurations.save', { body: { definition, base } })

export const readCatalogServer = (server: string, revision: number, signal?: AbortSignal) =>
  request<{ server: CatalogServer }>('mcp.read', { fields: { server, revision }, signal }).then((answer) => answer.server)

/** A catalog server's newest revision, or null when the catalog has none by that id. */
export async function latestCatalogServer(server: string, signal?: AbortSignal): Promise<CatalogServer | null> {
  let found: CatalogServer | null = null
  for (let revision = 1; ; revision += 1) {
    try {
      found = await readCatalogServer(server, revision, signal)
    } catch (error) {
      if (isRefusal(error) && error.error === 'missing_evidence') return found
      throw error
    }
  }
}

/** The project whose team the team route reads; `default` names the factory's default team. */
export const DEFAULT_TEAM = 'default'

export const readTeam = (project: string, signal?: AbortSignal) =>
  request<{ team: TeamRecord | null }>('teams.read', { fields: { project }, signal }).then((answer) => answer.team)

/** The default team's newest revision (0 when none is saved). */
export const latestDefaultRevision = (signal?: AbortSignal) =>
  readTeam(DEFAULT_TEAM, signal).then((record) => record?.revision ?? 0)

/** Save a project's team bound to the team version it was edited from. */
export const saveTeam = (project: string, team: Team, teamVersion: number) =>
  request<SaveAnswer>('teams.save', { body: { project, team, team_version: teamVersion } })

/** Save the default team as the revision after `base`, the revision it was edited from. */
export const saveDefaultTeam = (team: Team, base: number) =>
  request<SaveAnswer>('teams.default_save', { body: { team, base } })
