import { keepWorktree, type KeepAnswer, type KeepCommand, type KeepPacket } from '@/api/actions'
import { assertPasskey, toB64url } from '@/features/signin/webauthn'
import type { PendingAnswer, PendingItem } from './space'

/**
 * The owner's Keep, signed in the console (VELDO-0319 AC5 to AC7). Keep is the one answer the settlement cannot
 * finish alone: the Ledger takes it only as the owner's own signed packet. A browser holds no SSH key, and a
 * session proves only that the owner signed in, so each Keep gets a passkey ceremony of its own whose challenge
 * is SHA-256 of the Keep command's canonical bytes (control_store.canonical_bytes). The Ledger verifies that
 * assertion itself; nothing here decides anything.
 */

/** A choice that answers Keep: for every worktree the request lists, or for the member a pick names (w and its index). */
const KEEP_CHOICE = /^accept keep(?: w([1-9][0-9]*))?$/

/** Whether `choice` answers Keep, and for which member: null for the whole request. Undefined when it is not Keep. */
export function keepPick(choice: string | null): number | null | undefined {
  const found = KEEP_CHOICE.exec(choice ?? '')
  if (!found) return undefined
  return found[1] ? Number(found[1]) : null
}

/**
 * The worktree a Keep answer to `requestId` is signed for: a deferred item of the pending read whose own request
 * is that one. A member pick names its member by index. A Keep for a whole group is one packet naming any member:
 * the Ledger applies it to every member the settled terms list, so the first by index is named.
 */
export function keepTarget(pending: PendingAnswer | null, requestId: string, choice: string | null): PendingItem | null {
  const pick = keepPick(choice)
  if (pick === undefined || !pending) return null
  const members = pending.items
    .filter((item) => item.state === 'deferred' && item.request_id === requestId && (pick === null || item.index === pick))
    .sort((a, b) => (a.index ?? 0) - (b.index ?? 0) || a.id.localeCompare(b.id))
  return members[0] ?? null
}

/** The items whose Keep settled and was not applied: answered, not signed (AC7). */
export function unsignedKeeps(pending: PendingAnswer | null): PendingItem[] {
  return (pending?.items ?? []).filter((item) => item.answered === 'keep' && item.state === 'deferred' && !!item.request_id)
}

/** control_store.canonical_bytes as text: JSON with sorted keys, no spaces, and every character outside printable
 * ASCII escaped as \uXXXX (Python's json.dumps with sort_keys, compact separators and ensure_ascii). */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value === 'boolean') return String(value)
  if (typeof value === 'number') {
    if (!Number.isSafeInteger(value)) throw new Error('a signed command holds whole numbers only')
    return String(value)
  }
  if (typeof value === 'string') {
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`)
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    // Python sorts keys by code point; a command's keys are ASCII, where that is the order of this comparison.
    const keys = Object.keys(record).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
    return `{${keys.map((key) => `${canonicalJson(key)}:${canonicalJson(record[key])}`).join(',')}}`
  }
  throw new Error('a signed command holds JSON values only')
}

/** The ceremony's challenge for a command: SHA-256 of its canonical bytes, unpadded base64url. */
export async function commandChallenge(command: KeepCommand): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(command))
  return toB64url(await crypto.subtle.digest('SHA-256', bytes))
}

function fresh(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

/** The Keep command for one item, at the version the pending read shows, naming the item's own request. */
export function keepCommand(principal: string, item: PendingItem, ids: { commandId: string; nonce: string } | null = null): KeepCommand {
  if (!item.request_id) throw new Error('the item has no request a Keep could name')
  return {
    principal,
    operation: 'space_disposition',
    command_id: ids?.commandId ?? `console-keep-${fresh()}`,
    nonce: ids?.nonce ?? fresh(),
    parameters: { item: item.id, version: item.version, request: item.request_id },
  }
}

export interface Signer {
  principal: string
  /** The credential of the session: the ceremony is limited to it. */
  credentialId: string
  /** The relying-party id the pending read names (PendingAnswer.signing). */
  rpId: string
}

/** One passkey ceremony over the command's digest. A cancelled or refused ceremony throws; nothing was sent. */
export async function signKeep(signer: Signer, item: PendingItem): Promise<KeepPacket> {
  const command = keepCommand(signer.principal, item)
  const signature = await assertPasskey(await commandChallenge(command), signer.rpId, signer.credentialId)
  return { command, signature }
}

/** Send a signed packet on space.keep. A refusal is thrown as the API named it. */
export async function sendKeep(packet: KeepPacket, contractRoute: string | null = null): Promise<KeepAnswer | null> {
  const sent = await keepWorktree(packet, contractRoute)
  return sent.sent ? sent.answer : null
}
