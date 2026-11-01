import type { Transition, WorkflowDefinition, WorkflowLayout } from '@/api/workflows'

/** The step kinds of VELDO-0132 and the ports each must connect (control_workflow.STEP_KINDS). */
export const KINDS: Record<string, { label: string; ports: string[] }> = {
  grooming: { label: 'Grooming', ports: ['groomed'] },
  owner_wait: { label: 'Owner wait', ports: ['admit', 'decline'] },
  assignment: { label: 'Assignment', ports: ['done'] },
  result_handling: { label: 'Result handling', ports: [] },
}

export interface Draft {
  definition: WorkflowDefinition
  layout: WorkflowLayout
}

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

export function nodeIds(d: Draft): string[] {
  return Object.keys(d.definition.nodes)
}

export function position(d: Draft, id: string): { x: number; y: number } {
  const index = nodeIds(d).indexOf(id)
  return d.layout.nodes?.[id] ?? { x: 40 + (index % 4) * 220, y: 40 + Math.floor(index / 4) * 140 }
}

/** A new node of `kind` with the next free id, placed after the others. */
export function addNode(d: Draft, kind: string): { draft: Draft; id: string } {
  const next = clone(d)
  let n = 1
  while (next.definition.nodes[`${kind}_${n}`]) n += 1
  const id = `${kind}_${n}`
  const count = nodeIds(next).length
  next.definition.nodes[id] = { kind, config: {} }
  next.layout.nodes = { ...(next.layout.nodes ?? {}), [id]: { x: 40 + (count % 4) * 220, y: 220 + Math.floor(count / 4) * 140 } }
  if (kind === 'result_handling') next.definition.terminal = [...new Set([...next.definition.terminal, id])]
  return { draft: next, id }
}

export function removeNode(d: Draft, id: string): Draft {
  const next = clone(d)
  delete next.definition.nodes[id]
  if (next.layout.nodes) delete next.layout.nodes[id]
  next.definition.transitions = next.definition.transitions.filter((t) => t.from !== id && t.to !== id)
  next.definition.terminal = next.definition.terminal.filter((t) => t !== id)
  if (next.definition.entry === id) next.definition.entry = nodeIds(next)[0] ?? ''
  return next
}

/** Connect `from`'s `port` to `to` (one transition per port), or disconnect it when `to` is empty. */
export function connect(d: Draft, from: string, port: string, to: string): Draft {
  const next = clone(d)
  const rest = next.definition.transitions.filter((t) => !(t.from === from && t.port === port))
  if (to) {
    const existing = d.definition.transitions.find((t) => t.from === from && t.port === port)
    let id = existing?.id
    if (!id) {
      let n = 1
      while (rest.some((t) => t.id === `t${n}`)) n += 1
      id = `t${n}`
    }
    rest.push({ id, from, port, to })
  }
  next.definition.transitions = rest
  return next
}

export function transitionOf(d: Draft, from: string, port: string): Transition | null {
  return d.definition.transitions.find((t) => t.from === from && t.port === port) ?? null
}

/** Move node `id` by `delta` places in the definition's node order (the ordered list). */
export function reorder(d: Draft, id: string, delta: number): Draft {
  const ids = nodeIds(d)
  const from = ids.indexOf(id)
  const to = Math.max(0, Math.min(ids.length - 1, from + delta))
  if (from < 0 || from === to) return d
  ids.splice(to, 0, ...ids.splice(from, 1))
  const next = clone(d)
  next.definition.nodes = Object.fromEntries(ids.map((k) => [k, d.definition.nodes[k]!]))
  return next
}

export function moveNode(d: Draft, id: string, x: number, y: number): Draft {
  const next = clone(d)
  next.layout.nodes = { ...(next.layout.nodes ?? {}), [id]: { x: Math.round(x), y: Math.round(y) } }
  return next
}

export function setConfig(d: Draft, id: string, key: string, value: unknown): Draft {
  const next = clone(d)
  const node = next.definition.nodes[id]
  if (!node) return d
  if (value === '' || value == null) delete node.config[key]
  else node.config[key] = value
  return next
}

export function setEntry(d: Draft, id: string): Draft {
  const next = clone(d)
  next.definition.entry = id
  return next
}

/** What the API would refuse before saving: a port with no transition, an entry that is not a node. Shown
 * beside the save action; the API's own validation is still the judge. */
export function problems(d: Draft): string[] {
  const out: string[] = []
  if (!d.definition.nodes[d.definition.entry]) out.push('The entry step is not set.')
  for (const [id, node] of Object.entries(d.definition.nodes))
    for (const port of KINDS[node.kind]?.ports ?? [])
      if (!transitionOf(d, id, port)) out.push(`${id}: port ${port} is not connected.`)
  return out
}

export function same(a: Draft, b: Draft): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}
