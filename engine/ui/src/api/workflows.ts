import { request } from './client'
import type { Watermark } from './types'

export interface WorkflowNode {
  kind: string
  config: Record<string, unknown>
}
export interface Transition {
  id: string
  from: string
  port: string
  to: string
}
/** VELDO-0132's workflow definition: data only. Saving it never runs it. */
export interface WorkflowDefinition {
  schema: string
  id: string
  entry: string
  terminal: string[]
  nodes: Record<string, WorkflowNode>
  transitions: Transition[]
  references: Record<string, unknown>
  budget: Record<string, unknown>
}
export interface WorkflowLayout {
  nodes?: Record<string, { x: number; y: number }>
  transitions?: Record<string, { points: [number, number][] }>
  viewport?: { x: number; y: number; zoom: number }
}
export interface WorkflowDocument {
  workflow: string
  version: number
  revision: string
  definition: WorkflowDefinition
  layout: WorkflowLayout | null
  definition_digest: string
  saved: { principal: string; at: number } | null
  watermark: Watermark
  freshness: string
}
export interface WorkflowSaved {
  outcome: string
  workflow: string
  version: number
  revision: string
  api_request_id: string
}

/** One stored revision of a workflow (its head when `version` is omitted). */
export const readWorkflow = (workflow: string, version?: number, signal?: AbortSignal) =>
  request<WorkflowDocument>('reads.workflow', { fields: version == null ? { workflow } : { workflow, version }, signal })

/** Save the edited definition and layout as the next version, edited from `base` (the version shown). A save
 * edited from a version that is no longer the head is refused `stale_version` and stores nothing. */
export const saveWorkflow = (workflow: string, base: number, definition: WorkflowDefinition, layout: WorkflowLayout) =>
  request<WorkflowSaved>('workflows.save', { body: { workflow, base, definition, layout } })
