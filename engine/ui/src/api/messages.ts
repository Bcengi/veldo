import { request } from './client'

/** The intake's answer to a message: the proposal or question it recorded, never a reply invented here. */
export interface MessageAnswer {
  outcome: string
  api_request_id?: string
  [field: string]: unknown
}

/** Send the owner's message to the factory's common intake (messages.send), optionally about one project. */
export const sendMessage = (text: string, project?: string) =>
  request<MessageAnswer>('messages.send', { body: project ? { text, project } : { text } })
