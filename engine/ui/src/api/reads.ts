import { request } from './client'
import type { ReadAnswer } from './types'

export const readDecisions = (signal?: AbortSignal) => request<ReadAnswer>('reads.decisions', { signal })
export const readWorkers = (signal?: AbortSignal) => request<ReadAnswer>('reads.workers', { signal })
export const readWork = (signal?: AbortSignal) => request<ReadAnswer>('reads.work', { signal })
// VELDO-0131: the remaining published read models and the action contract.
export const readObjectives = (signal?: AbortSignal) => request<ReadAnswer>('reads.objectives', { signal })
export const readProof = (signal?: AbortSignal) => request<ReadAnswer>('reads.proof', { signal })
export const readSpend = (signal?: AbortSignal) => request<ReadAnswer>('reads.spend', { signal })
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
