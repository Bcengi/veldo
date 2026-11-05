import { request } from './client'
import type { ReadAnswer } from './types'

export const readDecisions = (signal?: AbortSignal) => request<ReadAnswer>('reads.decisions', { signal })
export const readWorkers = (signal?: AbortSignal) => request<ReadAnswer>('reads.workers', { signal })
export const readWork = (signal?: AbortSignal) => request<ReadAnswer>('reads.work', { signal })
// VELDO-0131: the remaining published read models and the action contract.
export const readObjectives = (signal?: AbortSignal) => request<ReadAnswer>('reads.objectives', { signal })
export const readProof = (signal?: AbortSignal) => request<ReadAnswer>('reads.proof', { signal })
export const readSpend = (signal?: AbortSignal) => request<ReadAnswer>('reads.spend', { signal })
/** VELDO-0236: the accounts with their pauses and ceilings, and every pause, ceiling, resume and end from the journal. */
export const readPacing = (signal?: AbortSignal) => request<ReadAnswer>('accounts.pacing', { signal })
export const readConfigurationModel = (signal?: AbortSignal) => request<ReadAnswer>('reads.configuration', { signal })

/** One action of the API's published UI action contract (control_api_models.ACTIONS). An action whose `route`
 * is null has no typed authority command yet; `spec` names the specification that owns it. */
export interface ContractAction {
  name: string
  route: string | null
  operation: string | null
  spec: string | null
}
export interface Contract {
  schema: string
  actions: ContractAction[]
  gaps: { criterion: string; subject: string; spec: string | null; what: string }[]
}
export const readContract = (signal?: AbortSignal) => request<Contract>('reads.contract', { signal })

// VELDO-0131 fix round 2: the metadata-only reads (control_api_models.METADATA_READS), served like a read model.
/** The whole MCP catalog (heads and revisions) and every credential record's metadata (never a value). */
export const readCatalog = (signal?: AbortSignal) => request<ReadAnswer>('mcp.list', { signal })
/** One Git identity as the repositories read serves it: metadata only, never its credential references. */
export interface IdentityMeta {
  id: string
  label: string
  author_name: string
  author_email: string
  remote_host: string
  remote_owner: string
  projects_root: string
  default_visibility: string
  repositories: string[]
}
/** The repository records and the Git identities. */
export const readRepositories = (signal?: AbortSignal) =>
  request<ReadAnswer & { identities: IdentityMeta[] }>('repositories.read', { signal })
