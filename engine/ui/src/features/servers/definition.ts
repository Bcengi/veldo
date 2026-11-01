import type { Binding, ServerDefinition, StoredServer } from '@/api/mcp'

/** One environment variable or header row of the form. A header is always a credential reference. */
export interface BindingRow {
  name: string
  kind: 'literal' | 'reference'
  value: string
}

/** What the server form edits. Lists are one item per line, as typed. */
export interface ServerDraft {
  id: string
  label: string
  transport: 'stdio' | 'http'
  command: string
  argumentsText: string
  url: string
  environment: BindingRow[]
  headers: BindingRow[]
  hostsText: string
  toolsText: string
}

export function emptyDraft(): ServerDraft {
  return {
    id: '',
    label: '',
    transport: 'stdio',
    command: '',
    argumentsText: '',
    url: '',
    environment: [],
    headers: [],
    hostsText: '',
    toolsText: '',
  }
}

/** The lines of a list field, trimmed, without empty lines. Arguments keep their inner spaces. */
export function lines(text: string): string[] {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
}

function bindings(rows: BindingRow[], referencesOnly: boolean): Record<string, Binding> {
  const out: Record<string, Binding> = {}
  for (const row of rows) {
    const name = row.name.trim()
    if (!name) continue
    out[name] = !referencesOnly && row.kind === 'literal' ? { literal: row.value } : { reference: row.value }
  }
  return out
}

/** The definition the catalog route takes, from what the form holds. The transport decides which fields carry
 * values: a stdio server has no url or headers, an http server no command or arguments. */
export function toDefinition(draft: ServerDraft): ServerDefinition {
  const stdio = draft.transport === 'stdio'
  return {
    id: draft.id.trim(),
    label: draft.label.trim(),
    transport: draft.transport,
    command: stdio ? draft.command.trim() : null,
    arguments: stdio ? lines(draft.argumentsText) : [],
    url: stdio ? null : draft.url.trim(),
    environment: bindings(draft.environment, false),
    headers: stdio ? {} : bindings(draft.headers, true),
    hosts: lines(draft.hostsText),
    read_only_tools: lines(draft.toolsText),
  }
}

function rows(values: Record<string, Binding>): BindingRow[] {
  return Object.entries(values).map(([name, b]) =>
    'literal' in b ? { name, kind: 'literal' as const, value: b.literal } : { name, kind: 'reference' as const, value: b.reference },
  )
}

/** The form's draft of a stored revision, to edit it. */
export function fromStored(stored: StoredServer): ServerDraft {
  return {
    id: stored.id,
    label: stored.label,
    transport: stored.transport,
    command: stored.command ?? '',
    argumentsText: stored.arguments.join('\n'),
    url: stored.url ?? '',
    environment: rows(stored.environment),
    headers: rows(stored.headers),
    hostsText: stored.hosts.join('\n'),
    toolsText: stored.read_only_tools.join('\n'),
  }
}
