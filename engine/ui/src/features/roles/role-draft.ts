import type {
  ConfigurationRevision,
  Definition,
  InstructionFile,
  LoadMode,
  McpSelection,
  NativeTool,
  SkillReference,
} from '@/api/configuration'

export const LOAD_MODES: readonly LoadMode[] = ['always', 'when assigned']
export const ENGINES: readonly Definition['engine'][] = ['claude_code', 'codex']

/** One engine setting as the form edits it: its value as text, parsed back as JSON when it was not text. */
export interface SettingRow { key: string; value: string; json: boolean }

/** A role's configuration as the form edits it, with the revision it was edited from (0 for a new role). */
export interface RoleDraft {
  role: string
  engine: Definition['engine']
  native_tools: NativeTool[]
  mcp: McpSelection[]
  skills: SkillReference[]
  instructions: InstructionFile[]
  settings: SettingRow[]
  editedFrom: number
}

export function emptyDraft(role: string): RoleDraft {
  return { role, engine: 'claude_code', native_tools: [], mcp: [], skills: [], instructions: [], settings: [], editedFrom: 0 }
}

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

/** The draft of a stored revision: every field as stored, edited from that revision. */
export function fromRevision(stored: ConfigurationRevision): RoleDraft {
  return {
    role: stored.role,
    engine: stored.engine,
    native_tools: copy(stored.native_tools),
    mcp: copy(stored.mcp),
    skills: copy(stored.skills),
    instructions: copy(stored.instructions),
    settings: Object.entries(stored.settings).map(([key, value]) =>
      typeof value === 'string' ? { key, value, json: false } : { key, value: JSON.stringify(value), json: true },
    ),
    editedFrom: stored.revision,
  }
}

/** Why a setting row cannot be sent, or null. A JSON setting must still parse. */
export function settingProblem(row: SettingRow): string | null {
  if (!row.key.trim()) return 'A setting needs a name.'
  if (!row.json) return null
  try {
    JSON.parse(row.value)
    return null
  } catch {
    return `The setting ${row.key} is not valid JSON.`
  }
}

/** Exactly the definition the configuration route stores: the draft's fields in VELDO-0127's shape. */
export function toDefinition(draft: RoleDraft): Definition {
  const settings: Record<string, unknown> = {}
  for (const row of draft.settings) settings[row.key.trim()] = row.json ? JSON.parse(row.value) : row.value
  return {
    role: draft.role.trim(),
    engine: draft.engine,
    native_tools: copy(draft.native_tools),
    mcp: copy(draft.mcp),
    skills: copy(draft.skills),
    instructions: copy(draft.instructions),
    settings,
  }
}

/** A comma separated list as names, without blanks or repeats. */
export function names(text: string): string[] {
  const out: string[] = []
  for (const part of text.split(',')) {
    const name = part.trim()
    if (name && !out.includes(name)) out.push(name)
  }
  return out
}
