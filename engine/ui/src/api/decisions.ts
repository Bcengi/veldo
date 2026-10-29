import { request } from './client'

export interface AnswerBody {
  request_id: string
  request_version: number
  presentation_id: string
  presentation_digest: string
  presentation_version: number
  choice: string
  rationale: string
}

export interface AnswerResult {
  outcome: string
  request_id?: string
  answer?: string
  ruling?: string
  api_request_id: string
}

export const sendAnswer = (body: AnswerBody) =>
  request<AnswerResult>('decisions.answer', { body: { ...body } })
