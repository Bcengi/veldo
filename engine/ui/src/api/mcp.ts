import { request } from './client'

/** One environment variable or header of a server: a literal, or a reference to a credential in the keystore. */
export type Binding = { literal: string } | { reference: string }

/** An MCP server definition exactly as the catalog route (VELDO-0144 AC1) takes and stores it. */
export interface ServerDefinition {
  id: string
  label: string
  transport: 'stdio' | 'http'
  command: string | null
  arguments: string[]
  url: string | null
  environment: Record<string, Binding>
  headers: Record<string, Binding>
  hosts: string[]
  read_only_tools: string[]
}

export interface StoredServer extends ServerDefinition {
  revision: number
}

export interface SaveResult {
  outcome: string
  server: string
  revision: number
  api_request_id: string
}

export interface CredentialResult {
  outcome: 'written' | 'replaced' | 'deleted'
  id: string
  reference: string
  version: number
  /** The stored credential record's set at (seconds since the epoch) and set by, never the value. */
  set_at: number
  set_by: string
  api_request_id: string
}

/** Save `definition` as a new revision, edited from revision `base` (0 for a new server). A save edited from a
 * revision that is no longer the head is refused `stale_version:mcp_server` and stores nothing. */
export const saveServer = (definition: ServerDefinition, base: number) =>
  request<SaveResult>('mcp.save', { body: { definition, base } })

/** One stored revision of one server. */
export const readServer = (server: string, revision: number) =>
  request<{ server: StoredServer }>('mcp.read', { fields: { server, revision } })

/** Write a credential's value to the keystore through the credential route. The value is in this one request's
 * body and nowhere else; the answer carries the record's reference and version, never the value. */
export const setCredential = (id: string, label: string, base: number, value: string) =>
  request<CredentialResult>('mcp.credential_set', { body: { id, label, base, value } })

export const deleteCredential = (id: string, base: number) =>
  request<CredentialResult>('mcp.credential_delete', { body: { id, base } })
