import { request } from './client'
import type { MessageAnswer } from './messages'
import type { Watermark } from './types'

/** One of the owner's conversations as `conversations.read` lists it (VELDO-0178 AC1). */
export interface ConversationSummary {
  id: string
  status: 'open' | 'closed' | string
  role: string
  version: number
  turns: number
  last_activity: number | null
}

/** One turn as `conversations.read` serves it: his message as intake kept it, the reply as the engine wrote it. */
export interface ConversationTurn {
  sequence: number
  state: 'waiting' | 'dispatched' | 'ended' | string
  message: string | null
  reply: string | null
  outcome: string | null
  dispatch_id: string | null
  account: string | null
  created_at: number | null
  ended_at: number | null
}

export interface ConversationView {
  id: string
  status: 'open' | 'closed' | string
  role: string
  version: number
  opened_at: number | null
  closed_at: number | null
  project: string | null
  turns: number
  last_activity: number | null
  attachments: { project: string; commit: string | null; at: number | null }[]
}

export interface ConversationList {
  schema: string
  conversations: ConversationSummary[]
  watermark: Pick<Watermark, 'seq'>
  freshness: string
}

export interface ConversationRead {
  schema: string
  conversation: ConversationView
  turns: ConversationTurn[]
  watermark: Pick<Watermark, 'seq'>
  freshness: string
}

/** A conversation command's answer: the record's new version, joined to its command by the API request id. */
export interface ConversationAnswer {
  outcome: string
  conversation?: string
  version?: number
  role?: string
  project?: string
  status?: string
  api_request_id: string
}

export const listConversations = (signal?: AbortSignal) => request<ConversationList>('conversations.read', { signal })

export const readConversation = (conversation: string, signal?: AbortSignal) =>
  request<ConversationRead>('conversations.read', { fields: { conversation }, signal })

/** Open a conversation (in the default role when none is named). */
export const openConversation = () => request<ConversationAnswer>('conversations.open', { body: {} })

export const closeConversation = (conversation: string, version: number) =>
  request<ConversationAnswer>('conversations.close', { body: { conversation, version } })

export const setConversationRole = (conversation: string, version: number, role: string) =>
  request<ConversationAnswer>('conversations.set_role', { body: { conversation, version, role } })

export const attachConversationProject = (conversation: string, version: number, project: string) =>
  request<ConversationAnswer>('conversations.attach_project', { body: { conversation, version, project } })

/** The owner's message as the conversation's next turn (messages.send with the `conversation` field). */
export const sendToConversation = (text: string, conversation: string) =>
  request<MessageAnswer>('messages.send', { body: { text, conversation } })
